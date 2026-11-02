//! B119 — the least-covered area was `MemoryBackend`: the crate's 12 unit
//! tests only reach it through `JobStore`. These cases pin its command
//! surface directly, including the count semantics `LocalSqliteStore.delete`
//! has in Python (delete removes hashes/zsets but counts only string keys).

use queue_core::{Backend, MemoryBackend};

#[test]
fn memory_backend_starts_empty() {
    let mut b = MemoryBackend::new();
    assert_eq!(b.get("nope"), None);
    assert!(b.hgetall("nope").is_empty());
    assert!(b.zrange("nope").is_empty());
    assert_eq!(b.delete(&["nope"]), 0);
}

#[test]
fn set_body_and_get_round_trip() {
    let mut b = MemoryBackend::new();
    b.set_body("k", "v");
    assert_eq!(b.get("k").as_deref(), Some("v"));
    b.set_body("k", "overwritten");
    assert_eq!(b.get("k").as_deref(), Some("overwritten"));
}

#[test]
fn delete_counts_only_live_string_keys() {
    let mut b = MemoryBackend::new();
    b.set_body("k", "v");
    b.hset("k", &[("field", "value".to_string())]);
    b.zadd("k", 1, "member");
    assert_eq!(b.delete(&["k"]), 1);
    assert_eq!(b.get("k"), None);
    assert!(b.hgetall("k").is_empty());
    assert!(b.zrange("k").is_empty());
}

#[test]
fn delete_of_a_hash_only_key_counts_zero_but_removes_it() {
    let mut b = MemoryBackend::new();
    b.hset("h", &[("field", "value".to_string())]);
    assert_eq!(b.delete(&["h"]), 0);
    assert!(b.hgetall("h").is_empty());
}

#[test]
fn hset_skips_empty_values_and_counts_only_stored_fields() {
    let mut b = MemoryBackend::new();
    let written = b.hset(
        "h",
        &[
            ("a", "1".to_string()),
            ("empty", String::new()),
            ("b", "2".to_string()),
        ],
    );
    assert_eq!(written, 2);
    let all = b.hgetall("h");
    assert_eq!(all.len(), 2);
    assert!(!all.contains_key("empty"));
}

#[test]
fn zrange_orders_by_score_then_member() {
    let mut b = MemoryBackend::new();
    b.zadd("z", 20, "b");
    b.zadd("z", 10, "c");
    b.zadd("z", 10, "a");
    assert_eq!(b.zrange("z"), vec!["a", "c", "b"]);
}

#[test]
fn set_nx_ex_holds_while_the_key_is_live() {
    let mut b = MemoryBackend::new();
    assert!(b.set_nx_ex("lock", "first", 60));
    assert!(!b.set_nx_ex("lock", "second", 60));
    assert_eq!(b.get("lock").as_deref(), Some("first"));
}

#[test]
fn set_xx_ex_requires_a_live_key() {
    let mut b = MemoryBackend::new();
    assert!(!b.set_xx_ex("lock", "who", 60));
    b.set_nx_ex("lock", "who", 60);
    assert!(b.set_xx_ex("lock", "who-again", 60));
    assert_eq!(b.get("lock").as_deref(), Some("who-again"));
}
