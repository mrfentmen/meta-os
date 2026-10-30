//! Parity tests for `os/tests/test_intel_watchman_bridge.py`.
//!
//! The bridge: a tick proves the watchman alive, a wake event is
//! the only bell, quiet ticks keep last_bell None (UNKNOWN, never
//! ALIVE), malformed events/priors contained, non-dict records
//! skipped, and the bridge record reads ALIVE then dark.

use os_supervisor::watchman;
use os_supervisor::watchman_bridge as bridge;
use os_supervisor::watchman_watch as ww;
use serde_json::{json, Value};
use std::collections::HashSet;

const NOW: f64 = 1_000_000.0;

fn agents() -> std::collections::BTreeMap<String, serde_json::Map<String, Value>> {
    watchman::normalize_agents(&json!({"hana": {"nick": "hana", "heartbeat_at": NOW - 3600.0}}))
}

fn jobs() -> Vec<Value> {
    vec![json!({"id": "job-1", "status": "open", "addressed_to": "hana", "title": "Demo job"})]
}

#[test]
fn wake_advances_bell() {
    let (events, _) = watchman::tick(&jobs(), &agents(), &HashSet::new(), NOW as i64, 300);
    assert_eq!(events.len(), 1);
    let record = bridge::fold_tick(&Value::Array(events), NOW, None);
    assert_eq!(record["watchman_alive"], json!(true));
    assert_eq!(record["last_bell"], json!(NOW));
    assert_eq!(record["last_wake"], json!(NOW));
}

#[test]
fn nudge_is_not_a_bell() {
    // A nudge event is not a wake event: folding it invents no bell.
    let nudge = json!({"kind": "nudge", "job_id": "4", "ts": NOW});
    let record = bridge::fold_tick(&json!([nudge]), NOW, None);
    assert_eq!(record["watchman_alive"], json!(true));
    assert_eq!(record["last_bell"], Value::Null);
}

#[test]
fn prior_bell_kept_without_new_wake() {
    let (events, _) = watchman::tick(&jobs(), &agents(), &HashSet::new(), NOW as i64, 300);
    let record = bridge::fold_tick(&Value::Array(events), NOW, None);
    let quiet = bridge::fold_tick(&json!([]), NOW + 10.0, Some(&record));
    assert_eq!(quiet["last_bell"], json!(NOW));
}

#[test]
fn malformed_events_and_prior_ignored() {
    let record = bridge::fold_tick(&json!("junk"), NOW, Some(&json!("junk")));
    assert_eq!(record["watchman_alive"], json!(true));
    assert_eq!(record["last_bell"], Value::Null);
    let record = bridge::fold_tick(
        &json!([42, "junk", {"kind": "wake"}]),
        NOW,
        None,
    );
    // Wake without a usable ts invents no bell.
    assert_eq!(record["last_bell"], Value::Null);
}

#[test]
fn snapshot_skips_non_dict_records() {
    let snapshot = bridge::machines_snapshot(&json!({"m1": [1, 2], "m2": {"watchman_alive": true}}));
    assert!(snapshot["machines"].as_object().unwrap().contains_key("m2"));
    assert!(!snapshot["machines"].as_object().unwrap().contains_key("m1"));
    let snapshot = bridge::machines_snapshot(&json!("junk"));
    assert_eq!(snapshot, json!({"machines": {}}));
}

#[test]
fn bridge_record_reads_alive_then_dark() {
    // A ticking watchman with a fresh bell reads ALIVE; the same
    // record aged past the stale window reads DEAD.
    let stale_secs = os_supervisor::thresholds::watchman_stale_minutes() as f64 * 60.0;
    let (events, _) = watchman::tick(&jobs(), &agents(), &HashSet::new(), NOW as i64, 300);
    let record = bridge::fold_tick(&Value::Array(events), NOW, None);
    let snapshot = bridge::machines_snapshot(&json!({"m1": record}));
    assert_eq!(ww::machine_state(&snapshot["machines"]["m1"], NOW, None), "alive");
    let late = NOW + stale_secs + 60.0;
    assert_eq!(ww::machine_state(&snapshot["machines"]["m1"], late, None), "dead");
    // The judge journals one dark episode for the aged record (a
    // revivable restart journals dark + restart, no escalation).
    let mut aged = record.as_object().cloned().unwrap_or_default();
    aged.insert("restart_ok".to_string(), json!(true));
    let aged_snapshot = bridge::machines_snapshot(&json!({"m1": aged}));
    let journal = ww::watchman_watch_tick(&aged_snapshot, &[], late);
    assert_eq!(journal.len(), 2);
    assert_eq!(journal[0]["kind"], json!("crew-dark"));
    assert_eq!(journal[1]["kind"], json!("watchman-restart"));
}
