//! Parity tests for `os/tests/test_intel_watchman_loop.py`.
//!
//! The service-loop caller: judgement, carry-forward, diagnostics,
//! and input immutability.

use os_supervisor::watchman;
use os_supervisor::watchman_loop as loop_mod;
use serde_json::{json, Value};
use std::collections::HashSet;

const NOW: f64 = 1_000_000.0;

fn stale() -> f64 {
    os_supervisor::thresholds::watchman_stale_minutes() as f64 * 60.0
}

fn stdout_for(at: i64) -> String {
    let jobs = json!([{"id": "j1", "status": "open", "addressed_to": "hana"}]);
    let agents = json!({"hana": {"nick": "hana", "heartbeat_at": NOW - 3600.0}});
    let agents_map = watchman::normalize_agents(&agents);
    let (events, _) = watchman::tick(jobs.as_array().unwrap(), &agents_map, &HashSet::new(), at, 300);
    events
        .iter()
        .map(|e| serde_json::to_string(e).unwrap())
        .collect::<Vec<_>>()
        .join("\n")
        + "\n"
}

// --- loop tests ---

#[test]
fn valid_lines_parse() {
    let (events, malformed) = loop_mod::parse_event_lines(
        &json!("{\"kind\": \"wake\", \"ts\": 7}\n\n{\"kind\": \"nudge\"}\n"),
    );
    assert_eq!(events.len(), 2);
    assert_eq!(malformed, 0);
}

#[test]
fn junk_and_non_object_lines_counted() {
    let (events, malformed) =
        loop_mod::parse_event_lines(&json!("junk\n[1, 2]\n{\"kind\": \"wake\"}\n"));
    assert_eq!(events.len(), 1);
    assert_eq!(malformed, 2);
}

#[test]
fn non_string_input_is_one_malformed() {
    let (events, malformed) = loop_mod::parse_event_lines(&Value::Null);
    assert!(events.is_empty());
    assert_eq!(malformed, 1);
}

#[test]
fn successful_ring_and_quiet() {
    let runs = json!({"alpha": [true, stdout_for(NOW as i64)], "beta": [true, ""]});
    let (records, new, diagnostics) =
        loop_mod::loop_cycle(&runs, NOW, None, Some(&[]), Some(&json!({"alpha": true})));
    assert_eq!(records["alpha"]["last_bell"], json!(NOW));
    assert_eq!(records["beta"]["last_bell"], Value::Null);
    assert!(new.is_empty() && diagnostics.run_failures.is_empty());
}

#[test]
fn failed_run_carries_prior_and_ages_dark() {
    let priors = json!({"alpha": {"watchman_alive": true, "last_tick": NOW, "last_bell": NOW}});
    let (records, new, diagnostics) = loop_mod::loop_cycle(
        &json!({"alpha": [false, "unused"], "beta": [true, ""]}),
        NOW + stale() + 100.0,
        Some(&priors),
        Some(&[]),
        None,
    );
    assert_eq!(diagnostics.run_failures, vec!["alpha".to_string()]);
    assert!(records["alpha"].get("restart_ok").is_none());
    assert_eq!(records["alpha"]["last_bell"], json!(NOW));
    assert_eq!(
        new.iter().map(|e| e["kind"].clone()).collect::<Vec<_>>(),
        vec![json!("crew-dark"), json!("watchman-restart"), json!("escalation")]
    );
}

#[test]
fn open_episode_stays_silent_on_repeat_failure() {
    let priors = json!({"alpha": {"watchman_alive": true, "last_tick": NOW, "last_bell": NOW}});
    let (_, new, _) = loop_mod::loop_cycle(
        &json!({"alpha": [false, "unused"]}),
        NOW + stale() + 100.0,
        Some(&priors),
        Some(&[]),
        None,
    );
    let mut journal = new;
    let (_, new2, _) = loop_mod::loop_cycle(
        &json!({"alpha": [false, "unused"]}),
        NOW + stale() + 200.0,
        Some(&priors),
        Some(&journal),
        None,
    );
    journal.extend(new2.clone());
    assert!(!journal.is_empty());
    // A further failed cycle journals nothing new.
    let (_, new3, _) = loop_mod::loop_cycle(
        &json!({"alpha": [false, "unused"]}),
        NOW + stale() + 300.0,
        Some(&priors),
        Some(&journal),
        None,
    );
    assert!(new3.is_empty());
}

#[test]
fn fresh_ring_recovers_after_failed_runs() {
    let priors = json!({"alpha": {"watchman_alive": true, "last_tick": NOW, "last_bell": NOW}});
    let (records, new, _) = loop_mod::loop_cycle(
        &json!({"alpha": [false, "unused"]}),
        NOW + stale() + 100.0,
        Some(&priors),
        Some(&[]),
        None,
    );
    let priors2 = serde_json::to_value(&records).unwrap();
    let journal: Vec<Value> = new;
    let (_, new2, _) = loop_mod::loop_cycle(
        &json!({"alpha": [true, stdout_for((NOW + stale() + 300.0) as i64)]}),
        NOW + stale() + 300.0,
        Some(&priors2),
        Some(&journal),
        None,
    );
    assert_eq!(
        new2.iter().map(|e| e["kind"].clone()).collect::<Vec<_>>(),
        vec![json!("watchman-recovered")]
    );
}

#[test]
fn malformed_stdout_contained_per_machine() {
    let dirty = stdout_for((NOW + stale() + 400.0) as i64) + "this is not json\n";
    let priors = json!({"alpha": {"watchman_alive": true, "last_tick": NOW, "last_bell": NOW}});
    let (records, new, diagnostics) = loop_mod::loop_cycle(
        &json!({"alpha": [true, dirty], "beta": [true, ""]}),
        NOW + stale() + 400.0,
        Some(&priors),
        Some(&[]),
        None,
    );
    assert_eq!(diagnostics.malformed_lines.get("alpha"), Some(&1));
    assert_eq!(records["alpha"]["last_bell"], json!(NOW + stale() + 400.0));
    assert!(new.is_empty());
}

#[test]
fn no_prior_failure_unjudged() {
    let (records, new, diagnostics) =
        loop_mod::loop_cycle(&json!({"gamma": [false, ""]}), NOW, None, Some(&[]), None);
    assert!(records.get("gamma").is_none() && new.is_empty());
    assert_eq!(diagnostics.run_failures, vec!["gamma".to_string()]);
}

#[test]
fn failed_run_stdout_ignored() {
    let priors = json!({"alpha": {"watchman_alive": true, "last_tick": NOW, "last_bell": NOW}});
    let (records, _new, _diagnostics) = loop_mod::loop_cycle(
        &json!({"alpha": [false, stdout_for((NOW + 500.0) as i64)]}),
        NOW + 500.0,
        Some(&priors),
        Some(&[]),
        None,
    );
    // Failed run folds nothing fresh: the carried bell is the old one.
    assert_eq!(records["alpha"]["last_bell"], json!(NOW));
}

#[test]
fn loop_inputs_never_mutated() {
    let runs = json!({"alpha": [true, stdout_for((NOW + 500.0) as i64)], "beta": [false, ""]});
    let runs_before = runs.clone();
    let priors = json!({"alpha": {"watchman_alive": true, "last_tick": NOW, "last_bell": NOW}});
    let priors_before = priors.clone();
    let journal: Vec<Value> = vec![json!({"kind": "crew-dark", "machine": "beta"})];
    let journal_before = journal.clone();
    loop_mod::loop_cycle(&runs, NOW + 500.0, Some(&priors), Some(&journal), None);
    assert_eq!(runs, runs_before);
    assert_eq!(priors, priors_before);
    assert_eq!(journal, journal_before);
}
