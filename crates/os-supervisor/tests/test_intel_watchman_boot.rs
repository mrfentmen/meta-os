//! Parity tests for `os/tests/test_intel_watchman_boot.py`.
//!
//! OS-129: arrivals ring and only arrivals ring; pre-window, post
//! boot, live lease, done, and malformed records never ring;
//! duplicates ring once; the ledger silences repeats; a corrupted
//! counter changes nothing; sweep reconciliation agrees or names
//! the mismatch; inputs never mutate; the note carries no push.

use os_supervisor::watchman_boot::*;
use serde_json::{json, Value};

fn jobs() -> Value {
    json!([
        {"id": "job-arrive-1", "status": "open", "posted_at": 100100.0},
        {"id": "job-arrive-2", "status": "open", "posted_at": 100500.0},
        {"id": "job-before", "status": "open", "posted_at": 99950.0},
        {"id": "job-after", "status": "open", "posted_at": 100610.0},
        {"id": "job-lease-dead", "status": "claimed", "claimed_by": "hana", "lease_expires_at": 100300.0},
        {"id": "job-lease-live", "status": "claimed", "claimed_by": "rowan", "lease_expires_at": 101500.0},
        {"id": "job-done", "status": "done", "lease_expires_at": 100200.0},
        {"bad-record": "open"},
        "not-a-record",
        {"status": "open", "posted_at": 100010.0},
    ])
}

const T0: f64 = 100_000.0;
const T1: f64 = 100_600.0;

fn ring_ids(rings: &[Ring]) -> Vec<&str> {
    rings.iter().map(|r| r.job_id.as_str()).collect()
}

#[test]
fn arrivals_ring_and_only_arrivals_ring() {
    let rings = post_boot_rings(&jobs(), T0, T1, None);
    let ids = ring_ids(&rings);
    assert_eq!(ids, vec!["job-arrive-1", "job-arrive-2", "job-lease-dead"]);
    let reasons: std::collections::HashMap<&str, &str> =
        rings.iter().map(|r| (r.job_id.as_str(), r.reason.as_str())).collect();
    assert_eq!(reasons["job-arrive-1"], "arrived_during_downtime");
    assert_eq!(reasons["job-arrive-2"], "arrived_during_downtime");
    assert_eq!(reasons["job-lease-dead"], "lease_expired_during_downtime");
}

#[test]
fn pre_window_post_boot_live_lease_and_done_do_not_ring() {
    let rings = post_boot_rings(&jobs(), T0, T1, None);
    let ids = ring_ids(&rings);
    assert!(!ids.contains(&"job-before"));
    assert!(!ids.contains(&"job-after"));
    assert!(!ids.contains(&"job-lease-live"));
    assert!(!ids.contains(&"job-done"));
}

#[test]
fn malformed_records_never_ring_and_never_crash() {
    let rings = post_boot_rings(&jobs(), T0, T1, None);
    assert!(!ring_ids(&rings).contains(&"bad-record"));
    // Non-list input yields no rings, never a crash.
    assert!(post_boot_rings(&json!(null), T0, T1, None).is_empty());
    assert!(post_boot_rings(&json!({"jobs": []}), T0, T1, None).is_empty());
}

#[test]
fn duplicate_input_rings_once() {
    let mut doubled = jobs().as_array().cloned().unwrap_or_default();
    doubled.push(json!({"id": "job-arrive-1", "status": "open", "posted_at": T0 + 100.0}));
    let rings = post_boot_rings(&Value::Array(doubled), T0, T1, None);
    assert_eq!(
        rings.iter().filter(|r| r.job_id == "job-arrive-1").count(),
        1
    );
}

#[test]
fn second_cycle_with_ledger_rings_nothing_new() {
    let rings = post_boot_rings(&jobs(), T0, T1, None);
    let ids: Vec<String> = rings.iter().map(|r| r.job_id.clone()).collect();
    let second = post_boot_rings(&jobs(), T0, T1, Some(&ids));
    assert!(second.is_empty());
}

#[test]
fn corrupted_counter_changes_nothing() {
    let rings = post_boot_rings(&jobs(), T0, T1, None);
    let ids: Vec<String> = rings.iter().map(|r| r.job_id.clone()).collect();
    let mut poisoned = jobs().as_array().cloned().unwrap_or_default();
    for job in poisoned.iter_mut() {
        if let Some(obj) = job.as_object_mut() {
            obj.insert("seen_counter".to_string(), json!(999999));
        }
    }
    let reproof: Vec<String> = post_boot_rings(&Value::Array(poisoned), T0, T1, None)
        .into_iter()
        .map(|r| r.job_id)
        .collect();
    assert_eq!(reproof, ids);
}

#[test]
fn sweep_reconciliation_agrees() {
    let note = verify_boot_cycle(&jobs(), T0, T1, &[json!("job-lease-dead")], None);
    assert!(note.reconciled);
    assert_eq!(note.total_rings, 3);
    assert_eq!(note.arrived_count, 2);
    assert_eq!(note.lease_expired_count, 1);
    assert!(note.counter_ignored);
}

#[test]
fn sweep_mismatch_named_never_fudged() {
    let note = verify_boot_cycle(&jobs(), T0, T1, &[json!("job-stranger")], None);
    assert!(!note.reconciled);
    assert_eq!(note.mismatch.missing, vec!["job-lease-dead".to_string()]);
    assert_eq!(note.mismatch.extra, vec!["job-stranger".to_string()]);
}

#[test]
fn inputs_never_mutated() {
    let jobs = jobs();
    let before = jobs.clone();
    let ledger = vec!["job-arrive-1".to_string()];
    post_boot_rings(&jobs, T0, T1, Some(&ledger));
    verify_boot_cycle(&jobs, T0, T1, &[json!("job-lease-dead")], None);
    assert_eq!(jobs, before);
    assert_eq!(ledger, vec!["job-arrive-1".to_string()]);
}

#[test]
fn note_carries_no_push_or_announcement() {
    let note = verify_boot_cycle(&jobs(), T0, T1, &[json!("job-lease-dead")], None);
    let debug = format!("{note:?}");
    assert!(!debug.contains("\"push\""), "{debug}");
    assert!(!debug.contains("\"announcement\""), "{debug}");
    assert!(!debug.contains("socket"), "{debug}");
}

#[test]
fn module_carries_no_push_path() {
    let manifest = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    for file in ["src/watchman_boot.rs"] {
        let text = std::fs::read_to_string(manifest.join(file)).unwrap();
        assert!(!text.contains("import push"), "{file}");
        assert!(!text.contains("from intel import push"), "{file}");
        assert!(!text.contains("socket"), "{file}");
        assert!(!text.contains("urllib"), "{file}");
    }
}

#[test]
fn drill_passes() {
    // 14 phase checks in the runner; the no-push-import source
    // scan is the 15th check, asserted by
    // module_carries_no_push_path above.
    let (passed, failed, _log) = os_supervisor::drills::run_watchman_boot_drill();
    assert_eq!(failed, 0);
    assert_eq!(passed + failed, 14);
}

#[test]
fn new_files_carry_no_em_dash() {
    // Python NEW_FILES for this batch item: the module, its drill,
    // and its eval note. The eval note (intel/evals/*.md) is
    // Hana's B12 territory; the drill runners live in the shared
    // drills.rs/drills_watchman.rs, scanned here alongside.
    let manifest = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    for file in [
        "src/watchman_boot.rs",
        "src/drills.rs",
        "src/drills_watchman.rs",
        "tests/test_intel_watchman_boot.rs",
    ] {
        let text = std::fs::read_to_string(manifest.join(file)).unwrap();
        assert!(!text.contains('\u{2014}'), "{file}");
    }
}
