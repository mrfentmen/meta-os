//! Test-gap close for `queue-store` (B131).
//!
//! The crate has one source module and five unit tests, all inside
//! `src/lib.rs`. Those five cover host resolution, the result round
//! trip, and a single store round trip. This file adds the missing
//! cases for the repo layer, the key layout, job filtering/finish, and
//! the SQLite backend so both backends are exercised the same way.

use queue_store::{
    envelope_key, index_key, job_key, product_ids, product_profile, result_key, InMemoryStore,
    JobStore, SqliteStore, StoreBackend, PRODUCTS,
};
use serde_json::json;
use std::time::{SystemTime, UNIX_EPOCH};

fn temp_db(tag: &str) -> std::path::PathBuf {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    std::env::temp_dir().join(format!(
        "queue-store-{tag}-{}-{nanos}.db",
        std::process::id()
    ))
}

#[test]
fn the_repo_layer_has_exactly_the_three_products() {
    assert_eq!(PRODUCTS.len(), 3);
    let ids = product_ids();
    assert_eq!(ids.len(), 3);
    for id in ["vigiles", "ignis", "medicus"] {
        assert!(ids.contains_key(id), "missing product id {id}");
        let profile = product_profile(id).expect("profile for a listed id");
        assert_eq!(profile.id, id);
        assert!(!profile.display_name.is_empty());
        assert!(!profile.department.is_empty());
        assert!(!profile.categories.is_empty());
        assert!(!profile.limitations.is_empty());
    }
    assert!(product_profile("not-a-product").is_none());
}

#[test]
fn category_lists_carry_the_source_values() {
    let ignis = product_profile("ignis").unwrap();
    assert!(ignis.categories.contains(&"visible smoke"));
    assert!(ignis.categories.contains(&"visible flame"));

    let medicus = product_profile("medicus").unwrap();
    assert!(medicus
        .categories
        .contains(&"crowd gathered around a person"));

    let vigiles = product_profile("vigiles").unwrap();
    assert!(vigiles.categories.contains(&"possible altercation"));
}

#[test]
fn finish_filters_the_job_out_of_open_job_ids() {
    let mut j = JobStore::new(InMemoryStore::default(), "trio-gap");
    j.submit(&json!({"id": "trio-open"}));
    j.submit(&json!({"id": "trio-done"}));
    j.finish("trio-done", "done", "answered");

    let open = j.open_job_ids();
    assert_eq!(open, vec!["trio-open".to_string()]);
    let fields = j.job_fields("trio-done");
    assert_eq!(fields.get("status").map(String::as_str), Some("done"));
    assert_eq!(fields.get("note").map(String::as_str), Some("answered"));
    assert!(fields.get("done_at").is_some());
}

#[test]
fn finish_releases_the_claim() {
    let mut j = JobStore::new(InMemoryStore::default(), "trio-gap");
    j.submit(&json!({"id": "trio-claim"}));
    assert!(j.claim("trio-claim", "worker-a", 60));
    assert!(!j.claim("trio-claim", "worker-b", 60));
    j.finish("trio-claim", "done", "");
    assert!(
        !j.renew_claim("trio-claim", "worker-a", 60),
        "the claim key is gone after finish"
    );
    assert!(
        j.claim("trio-claim", "worker-b", 60),
        "a finished job's claim can be taken again (no status guard)"
    );
}

#[test]
fn sqlite_backend_runs_the_full_job_round_trip() {
    let path = temp_db("round-trip");
    {
        let mut j = JobStore::new(
            SqliteStore::open(path.to_str().unwrap()).expect("open sqlite store"),
            "trio-gap",
        );
        let env = json!({
            "id": "trio-sqlite", "kind": "trio-assessment", "version": 1,
            "product": "medicus", "timestamp": "2026-10-30T06:00:00.000Z"
        });
        assert_eq!(j.submit(&env), ("trio-sqlite".to_string(), true));
        assert_eq!(j.job_envelope("trio-sqlite").unwrap(), env);

        assert!(j.claim("trio-sqlite", "worker-a", 60));
        assert!(!j.claim("trio-sqlite", "worker-b", 60));

        let result = json!({
            "job_id": "trio-sqlite", "status": "ok", "assessment": {"x": 1},
            "error": null, "model": "muse-spark-1.3", "latency_ms": 12
        });
        j.put_result(&result);
        assert_eq!(j.get_result("trio-sqlite").unwrap(), result);

        j.finish("trio-sqlite", "done", "sqlite");
        assert_eq!(
            j.job_fields("trio-sqlite").get("status").map(String::as_str),
            Some("done")
        );
        assert!(j.open_job_ids().is_empty());
    }
    let _ = std::fs::remove_file(&path);
}

#[test]
fn sqlite_hash_write_skips_empty_values() {
    let path = temp_db("hash");
    {
        let mut store = SqliteStore::open(path.to_str().unwrap()).expect("open sqlite store");
        let mut mapping = std::collections::HashMap::new();
        mapping.insert("empty".to_string(), String::new());
        mapping.insert("kept".to_string(), "value".to_string());
        assert_eq!(store.hset("h", &mapping), 1);
        let stored = store.hgetall("h");
        assert_eq!(stored.len(), 1);
        assert_eq!(stored.get("kept").map(String::as_str), Some("value"));
    }
    let _ = std::fs::remove_file(&path);
}

#[test]
fn sqlite_index_orders_by_score() {
    let path = temp_db("zset");
    {
        let mut store = SqliteStore::open(path.to_str().unwrap()).expect("open sqlite store");
        store.zadd("idx", 30, "c");
        store.zadd("idx", 10, "a");
        store.zadd("idx", 20, "b");
        let range = store.zrange("idx");
        let order: Vec<&str> = range.iter().map(String::as_str).collect();
        assert_eq!(order, vec!["a", "b", "c"]);
    }
    let _ = std::fs::remove_file(&path);
}

#[test]
fn every_key_helper_uses_the_expected_shape() {
    assert_eq!(job_key("trio-gap", "jid"), "trio-gap:jid");
    assert_eq!(envelope_key("trio-gap", "jid"), "trio-gap:jid:job");
    assert_eq!(index_key("trio-gap"), "trio-gapindex");
    assert_eq!(result_key("jid"), "trio:jid:result");
}

#[test]
fn ping_is_honest_on_both_backends() {
    let mut memory = InMemoryStore::default();
    assert!(memory.ping());

    let path = temp_db("ping");
    {
        let mut sqlite = SqliteStore::open(path.to_str().unwrap()).expect("open sqlite store");
        assert!(sqlite.ping());
    }
    let _ = std::fs::remove_file(&path);
}
