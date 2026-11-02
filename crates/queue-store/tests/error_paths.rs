//! Error-path tests for `queue-store` (B122).
//!
//! Every refusal and failure branch the crate actually has, asserted
//! against the behaviour in `src/lib.rs`:
//! - the one typed refusal (host resolution);
//! - the `false` / `None` / empty results that stand in for errors;
//! - the two silent write paths recorded as findings.
//!
//! These tests use the real public API. No mocks of the crate itself.

use queue_store::{
    claim_key, envelope_key, job_key, resolve_upstash_host, result_key, InMemoryStore,
    JobStore, SqliteStore, StoreBackend,
};
use serde_json::json;
use std::time::{SystemTime, UNIX_EPOCH};

fn jobs() -> JobStore<InMemoryStore> {
    JobStore::new(InMemoryStore::default(), "trio-test")
}

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
fn unconfigured_host_is_a_typed_refusal() {
    let err = resolve_upstash_host("", None).unwrap_err();
    assert!(
        err.0.contains("TRIO_UPSTASH_HOST"),
        "refusal must name the variable, got: {}",
        err.0
    );
    assert!(err.0.contains("never hardcoded"));
}

#[test]
fn whitespace_host_falls_through_to_the_same_refusal() {
    assert!(resolve_upstash_host("   ", None).is_err());
}

#[test]
fn credential_url_supplies_the_host_when_env_is_empty() {
    assert_eq!(
        resolve_upstash_host("", Some("https://cred.example.invalid/path")).unwrap(),
        "cred.example.invalid"
    );
}

#[test]
fn malformed_credential_url_is_refused() {
    // "https:///no-host" parses to an empty host with the crate's
    // minimal parser, and an empty string is empty by definition.
    assert!(resolve_upstash_host("", Some("https:///no-host")).is_err());
    assert!(resolve_upstash_host("", Some("   ")).is_err());
}

#[test]
fn unknown_job_fields_are_an_empty_map_not_an_error() {
    let mut j = jobs();
    assert!(j.job_fields("no-such-job").is_empty());
}

#[test]
fn missing_envelope_and_result_are_none() {
    let mut j = jobs();
    assert!(j.job_envelope("no-such-job").is_none());
    assert!(j.get_result("no-such-job").is_none());
}

#[test]
fn invalid_json_envelope_is_none() {
    let mut j = jobs();
    j.backend
        .set_body(&envelope_key("trio-test", "bad-json"), "{not json");
    assert!(j.job_envelope("bad-json").is_none());
}

#[test]
fn non_object_envelope_is_none() {
    let mut j = jobs();
    j.backend
        .set_body(&envelope_key("trio-test", "array"), "[1,2,3]");
    assert!(j.job_envelope("array").is_none());

    j.backend
        .set_body(&envelope_key("trio-test", "scalar"), "\"text\"");
    assert!(j.job_envelope("scalar").is_none());
}

#[test]
fn non_object_result_is_none() {
    let mut j = jobs();
    j.backend.set_body(&result_key("array"), "[1,2,3]");
    assert!(j.get_result("array").is_none());
}

#[test]
fn claim_on_a_missing_job_is_not_refused() {
    // Ported oddity: the NX key is the only check, so a claim can win
    // for a job that was never submitted. Recorded, not celebrated.
    let mut j = jobs();
    assert!(j.claim("never-submitted", "worker-a", 60));
    let fields = j.job_fields("never-submitted");
    assert_eq!(fields.get("status").map(String::as_str), Some("claimed"));
}

#[test]
fn duplicate_claim_is_refused() {
    let mut j = jobs();
    assert!(j.claim("race", "worker-a", 60));
    assert!(!j.claim("race", "worker-b", 60));
}

#[test]
fn renew_without_a_claim_is_false() {
    let mut j = jobs();
    assert!(!j.renew_claim("missing", "worker-a", 60));
}

#[test]
fn put_result_without_job_id_writes_the_empty_key() {
    // Finding: the Python original raises KeyError here; the port
    // accepts the empty id and writes `trio::result`.
    let mut j = jobs();
    j.put_result(&json!({"status": "ok"}));
    assert_eq!(j.get_result("").unwrap()["status"], "ok");
    assert_eq!(result_key(""), "trio::result");
}

#[test]
fn sqlite_nx_and_xx_lease_refusals() {
    let path = temp_db("nx-xx");
    {
        let mut store = SqliteStore::open(path.to_str().unwrap()).expect("open sqlite store");
        assert!(store.set_nx_ex("k", "first", 60));
        assert!(!store.set_nx_ex("k", "second", 60));
        assert!(store.set_xx_ex("k", "third", 60));
        assert_eq!(store.get("k").as_deref(), Some("third"));
        assert!(!store.set_xx_ex("absent", "value", 60));
    }
    let _ = std::fs::remove_file(&path);
}

#[test]
fn sqlite_delete_counts_only_kv_rows() {
    let path = temp_db("delete");
    {
        let mut store = SqliteStore::open(path.to_str().unwrap()).expect("open sqlite store");
        store.set_body("j", "envelope");
        let mut hash = std::collections::HashMap::new();
        hash.insert("status".to_string(), "open".to_string());
        assert_eq!(store.hset("j", &hash), 1);
        assert_eq!(store.zadd("j", 1, "j"), 1);
        assert_eq!(store.delete(&["j"]), 1, "only the kv row is counted");
        assert!(store.get("j").is_none());
        assert!(store.hgetall("j").is_empty());
        assert!(store.zrange("j").is_empty());
    }
    let _ = std::fs::remove_file(&path);
}

#[test]
fn key_helpers_match_the_documented_layout() {
    assert_eq!(job_key("trio", "abc"), "trio:abc");
    assert_eq!(envelope_key("trio", "abc"), "trio:abc:job");
    assert_eq!(claim_key("trio", "abc"), "trio:abc:claim");
    assert_eq!(result_key("abc"), "trio:abc:result");
}
