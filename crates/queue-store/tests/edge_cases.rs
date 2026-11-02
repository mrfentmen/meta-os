//! Edge-case tests for `queue-store` (B123): empty input, maximum
//! input, duplicate input, out-of-order input — one named test each,
//! plus the tie/ordering cases the in-memory index actually has.
//!
//! All assertions are read from `src/lib.rs`; none invent behaviour.

use queue_store::{InMemoryStore, JobStore, StoreBackend};
use serde_json::json;

fn jobs() -> JobStore<InMemoryStore> {
    JobStore::new(InMemoryStore::default(), "trio-edge")
}

#[test]
fn empty_envelope_files_under_the_empty_job_id() {
    let mut j = jobs();
    let (jid, created) = j.submit(&json!({}));
    assert_eq!(jid, "");
    assert!(created);
    let fields = j.job_fields("");
    assert_eq!(fields.get("status").map(String::as_str), Some("open"));
    // hset skips empty strings, so the absent envelope fields are not
    // written at all (lib.rs:241-250).
    assert!(fields.get("kind").is_none());
    assert_eq!(j.open_job_ids(), vec!["".to_string()]);
    assert!(j.job_envelope("").is_some(), "the empty envelope object is stored");
}

#[test]
fn empty_envelope_is_idempotent_on_second_submit() {
    let mut j = jobs();
    assert!(j.submit(&json!({})).1);
    let (jid, created) = j.submit(&json!({}));
    assert_eq!(jid, "");
    assert!(!created, "the empty id is already filed");
    assert_eq!(j.open_job_ids().len(), 1);
}

#[test]
fn maximum_envelope_round_trips_intact() {
    let mut j = jobs();
    let blob = "x".repeat(1_000_000);
    let env = json!({
        "id": "trio-max",
        "kind": "trio-assessment",
        "version": 1,
        "product": "ignis",
        "timestamp": "2026-10-30T06:00:00.000Z",
        "blob": blob,
    });
    let (jid, created) = j.submit(&env);
    assert_eq!(jid, "trio-max");
    assert!(created);
    let got = j.job_envelope(&jid).expect("large envelope is stored");
    assert_eq!(
        got.get("blob").and_then(|v| v.as_str()).map(str::len),
        Some(1_000_000)
    );
    assert_eq!(got, env);
}

#[test]
fn duplicate_submit_keeps_the_first_envelope() {
    let mut j = jobs();
    let first = json!({
        "id": "trio-dup", "kind": "trio-assessment", "version": 1,
        "product": "ignis", "timestamp": "first"
    });
    let second = json!({
        "id": "trio-dup", "kind": "trio-assessment", "version": 1,
        "product": "medicus", "timestamp": "second"
    });
    assert!(j.submit(&first).1);
    let (jid, created) = j.submit(&second);
    assert_eq!(jid, "trio-dup");
    assert!(!created);
    assert_eq!(
        j.job_envelope(&jid).unwrap()["product"],
        json!("ignis"),
        "the duplicate must not overwrite the filed envelope"
    );
    assert_eq!(
        j.job_fields(&jid).get("product").map(String::as_str),
        Some("ignis")
    );
    assert_eq!(j.open_job_ids().len(), 1);
}

#[test]
fn out_of_order_index_scores_sort_by_score() {
    let mut backend = InMemoryStore::default();
    backend.zadd("idx", 20, "b");
    backend.zadd("idx", 10, "a");
    backend.zadd("idx", 15, "c");
    let range = backend.zrange("idx");
    let order: Vec<&str> = range.iter().map(String::as_str).collect();
    assert_eq!(order, vec!["a", "c", "b"]);
}

#[test]
fn equal_index_scores_fall_back_to_member_order() {
    let mut backend = InMemoryStore::default();
    backend.zadd("idx", 5, "z");
    backend.zadd("idx", 5, "a");
    let range = backend.zrange("idx");
    let order: Vec<&str> = range.iter().map(String::as_str).collect();
    assert_eq!(order, vec!["a", "z"], "BTreeMap order breaks the tie");
}

#[test]
fn result_key_ignores_the_job_namespace() {
    // The bus-424 ruling: results always live under the `trio` prefix,
    // even when jobs were filed under another namespace.
    assert_eq!(queue_store::job_key("other", "x"), "other:x");
    assert_eq!(queue_store::result_key("x"), "trio:x:result");
}

#[test]
fn claim_lease_fields_are_internally_consistent() {
    let mut j = jobs();
    j.submit(&json!({"id": "trio-lease"}));
    assert!(j.claim("trio-lease", "worker-a", 60));
    let fields = j.job_fields("trio-lease");
    assert_eq!(fields.get("claim").map(String::as_str), Some("worker-a"));
    assert_eq!(fields.get("lease").map(String::as_str), Some("60"));
    let claimed: i64 = fields["claimed_at"]
        .as_str()
        .parse()
        .expect("claimed_at is an integer");
    let until: i64 = fields["lease_until"]
        .as_str()
        .parse()
        .expect("lease_until is an integer");
    assert_eq!(until - claimed, 60);
}

#[test]
fn empty_hash_values_are_not_written() {
    let mut backend = InMemoryStore::default();
    let mut mapping = std::collections::HashMap::new();
    mapping.insert("empty".to_string(), String::new());
    mapping.insert("kept".to_string(), "value".to_string());
    assert_eq!(backend.hset("h", &mapping), 1);
    let stored = backend.hgetall("h");
    assert_eq!(stored.len(), 1);
    assert_eq!(stored.get("kept").map(String::as_str), Some("value"));
}
