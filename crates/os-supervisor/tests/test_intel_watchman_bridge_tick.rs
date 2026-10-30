//! Parity tests for `os/tests/test_intel_watchman_bridge_tick.py`.
//!
//! The service-loop entry point over every machine's events:
//! ring/quiet/no-restart-fact/recovery/second-episode/malformed/
//! absent-machine, inputs never mutated.

use os_supervisor::watchman;
use os_supervisor::watchman_bridge as bridge;
use os_supervisor::watchman_watch as ww;
use serde_json::{json, Value};
use std::collections::HashSet;

const NOW: f64 = 1_000_000.0;

fn stale() -> f64 {
    os_supervisor::thresholds::watchman_stale_minutes() as f64 * 60.0
}

fn agents() -> std::collections::BTreeMap<String, serde_json::Map<String, Value>> {
    watchman::normalize_agents(&json!({"hana": {"nick": "hana", "heartbeat_at": NOW - 3600.0}}))
}

fn jobs() -> Vec<Value> {
    vec![json!({"id": "job-1", "status": "open", "addressed_to": "hana", "title": "Demo job"})]
}

fn tick_jobs(at: i64) -> Vec<Value> {
    let (events, _) = watchman::tick(&jobs(), &agents(), &HashSet::new(), at, 300);
    events
}

#[test]
fn ring_alive_quiet_unknown_no_journal() {
    let events = json!({"m1": tick_jobs(NOW as i64), "m2": []});
    let events_before = events.clone();
    let (records, journal) = bridge::watchman_tick(&events, NOW, None, None, None);
    assert_eq!(events, events_before);
    let states = ww::current_states(
        &bridge::machines_snapshot(&serde_json::to_value(&records).unwrap()),
        NOW,
    );
    let by: std::collections::HashMap<String, String> = states
        .iter()
        .map(|s| {
            (
                s["machine"].as_str().unwrap_or("").to_string(),
                s["state"].as_str().unwrap_or("").to_string(),
            )
        })
        .collect();
    assert_eq!(records["m1"]["last_bell"], json!(NOW));
    assert_eq!(records["m2"]["last_bell"], Value::Null);
    assert_eq!(by.get("m1").map(|s| s.as_str()), Some("alive"));
    assert_eq!(by.get("m2").map(|s| s.as_str()), Some("unknown"));
    assert!(journal.is_empty());
}

#[test]
fn silence_journals_dark_and_restart_only_for_dark() {
    let (records, _) = bridge::watchman_tick(&json!({"m1": tick_jobs(NOW as i64), "m2": []}), NOW, None, None, None);
    let priors = serde_json::to_value(&records).unwrap();
    let priors_before = priors.clone();
    let late = NOW + stale() + 60.0;
    let (dark_records, dark) = bridge::watchman_tick(
        &json!({"m1": [], "m2": []}),
        late,
        Some(&priors),
        Some(&[]),
        Some(&json!({"m1": true})),
    );
    assert_eq!(
        dark.iter().map(|e| e["kind"].clone()).collect::<Vec<_>>(),
        vec![json!("crew-dark"), json!("watchman-restart")]
    );
    assert!(dark.iter().all(|e| e["machine"] == json!("m1")));
    assert_eq!(dark[1]["restart_ok"], json!(true));
    assert_eq!(priors, priors_before);
    // Ring again: recovery.
    let (rc, recovered) = bridge::watchman_tick(
        &json!({"m1": tick_jobs((late + 60.0) as i64), "m2": []}),
        late + 60.0,
        Some(&serde_json::to_value(&dark_records).unwrap()),
        Some(&dark),
        None,
    );
    assert_eq!(
        recovered.iter().map(|e| e["kind"].clone()).collect::<Vec<_>>(),
        vec![json!("watchman-recovered")]
    );
    assert_eq!(recovered[0]["machine"], json!("m1"));
    let _ = rc;
}

#[test]
fn no_restart_fact_escalates_once() {
    // No restart_ok supplied: the dark machine reads restart
    // failed and escalates once (fail closed toward Dale).
    let (records, _) = bridge::watchman_tick(&json!({"m1": tick_jobs(NOW as i64)}), NOW, None, None, None);
    let late = NOW + stale() + 60.0;
    let (_records, dark) = bridge::watchman_tick(
        &json!({"m1": []}),
        late,
        Some(&serde_json::to_value(&records).unwrap()),
        Some(&[]),
        None,
    );
    assert_eq!(
        dark.iter().map(|e| e["kind"].clone()).collect::<Vec<_>>(),
        vec![json!("crew-dark"), json!("watchman-restart"), json!("escalation")]
    );
}

#[test]
fn recovery_then_second_episode_realerts() {
    let (records, _) = bridge::watchman_tick(&json!({"m1": tick_jobs(NOW as i64)}), NOW, None, None, None);
    let late = NOW + stale() + 60.0;
    let (dark_records, dark) = bridge::watchman_tick(
        &json!({"m1": []}),
        late,
        Some(&serde_json::to_value(&records).unwrap()),
        Some(&[]),
        Some(&json!({"m1": true})),
    );
    let mut journal = dark.clone();
    let (recovered_records, recovered) = bridge::watchman_tick(
        &json!({"m1": tick_jobs((late + 60.0) as i64)}),
        late + 60.0,
        Some(&serde_json::to_value(&dark_records).unwrap()),
        Some(&journal),
        None,
    );
    assert_eq!(recovered.len(), 1);
    journal.extend(recovered);
    let later = late + 2.0 * stale() + 120.0;
    let (dark2_records, dark2) = bridge::watchman_tick(
        &json!({"m1": []}),
        later,
        Some(&serde_json::to_value(&recovered_records).unwrap()),
        Some(&journal),
        Some(&json!({"m1": false})),
    );
    assert_eq!(
        dark2.iter().map(|e| e["kind"].clone()).collect::<Vec<_>>(),
        vec![json!("crew-dark"), json!("watchman-restart"), json!("escalation")]
    );
    assert_eq!(dark2[1]["restart_ok"], json!(false));
    let journal2: Vec<Value> = journal.iter().cloned().chain(dark2.iter().cloned()).collect();
    let (_again_records, again) = bridge::watchman_tick(
        &json!({"m1": []}),
        later + 60.0,
        Some(&serde_json::to_value(&dark2_records).unwrap()),
        Some(&journal2),
        None,
    );
    assert!(again.is_empty());
}

#[test]
fn malformed_input_contained_per_machine() {
    let (bad_records, bad_journal) = bridge::watchman_tick(&json!("junk"), NOW, None, None, None);
    assert!(bad_records.is_empty() && bad_journal.is_empty());
    let (mixed_records, mixed_journal) = bridge::watchman_tick(
        &json!({"m1": "junk", "m2": []}),
        NOW,
        None,
        None,
        None,
    );
    assert_eq!(mixed_records["m1"]["last_bell"], Value::Null);
    assert_eq!(mixed_records["m2"]["last_bell"], Value::Null);
    let states = ww::current_states(
        &bridge::machines_snapshot(&serde_json::to_value(&mixed_records).unwrap()),
        NOW,
    );
    assert!(states.iter().all(|s| s["state"] == json!("unknown")));
    assert!(mixed_journal.is_empty());
}

#[test]
fn absent_machine_unjudged() {
    let (records, journal) =
        bridge::watchman_tick(&json!({"m2": []}), NOW, None, None, None);
    assert_eq!(records.keys().cloned().collect::<Vec<_>>(), vec!["m2".to_string()]);
    assert!(journal.is_empty());
}

#[test]
fn inputs_never_mutated() {
    let events = json!({"m1": tick_jobs(NOW as i64), "m2": []});
    let events_before = events.clone();
    let priors = json!({});
    let priors_before = priors.clone();
    let journal: Vec<Value> = Vec::new();
    bridge::watchman_tick(&events, NOW, Some(&priors), Some(&journal), None);
    assert_eq!(events, events_before);
    assert_eq!(priors, priors_before);
}
