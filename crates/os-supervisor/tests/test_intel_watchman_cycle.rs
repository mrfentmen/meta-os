//! Parity tests for `os/tests/test_intel_watchman_cycle.py`.
//!
//! The runner adapter: pair validation, not-callable handling,
//! truthy rejection, carried priors that age honestly,
//! restart_ok stripping, and input immutability.

use os_supervisor::watchman;
use os_supervisor::watchman_cycle as cycle;
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

fn ok_run(stdout: String) -> Value {
    json!([true, stdout])
}

// --- cycle tests ---

#[test]
fn ring_and_quiet_clean_diagnostics() {
    let good = |name: &str| -> Result<Value, String> {
        if name == "alpha" {
            Ok(ok_run(stdout_for(NOW as i64)))
        } else {
            Ok(json!([true, ""]))
        }
    };
    let (records, new, diagnostics, runner_errors) = cycle::run_cycle(
        Some(&good),
        &json!(["alpha", "beta"]),
        NOW,
        None,
        Some(&[]),
        Some(&json!({"alpha": true})),
    );
    assert_eq!(records["alpha"]["last_bell"], json!(NOW));
    assert_eq!(records["beta"]["last_bell"], Value::Null);
    assert!(new.is_empty() && diagnostics.run_failures.is_empty() && runner_errors.is_empty());
}

#[test]
fn list_pair_accepted_as_success() {
    let list_ok = |_: &str| -> Result<Value, String> { Ok(json!([[true, "x"]])) };
    // A nested pair is not a pair: the outer first element is a
    // list, not True/False -> bad-return.
    let (_records, _new, _diagnostics, runner_errors) =
        cycle::run_cycle(Some(&list_ok), &json!(["a"]), NOW, None, Some(&[]), None);
    assert_eq!(runner_errors.get("a").map(|s| s.as_str()), Some("bad-return"));
}

#[test]
fn false_pair_is_failed_not_runner_error() {
    let false_ok = |_: &str| -> Result<Value, String> { Ok(json!([false, "unused"])) };
    let (records, new, diagnostics, runner_errors) =
        cycle::run_cycle(Some(&false_ok), &json!(["a"]), NOW, None, Some(&[]), None);
    assert_eq!(diagnostics.run_failures, vec!["a".to_string()]);
    assert!(runner_errors.is_empty());
    assert!(records.is_empty() && new.is_empty());
}

#[test]
fn string_machines_is_one_machine() {
    let good = |_: &str| -> Result<Value, String> { Ok(json!([true, ""])) };
    let (records, _new, diagnostics, _errors) =
        cycle::run_cycle(Some(&good), &json!("solo"), NOW, None, Some(&[]), None);
    assert!(records.contains_key("solo"));
    assert!(diagnostics.run_failures.is_empty());
}

#[test]
fn none_machines_is_empty_cycle() {
    let good = |_: &str| -> Result<Value, String> { Ok(json!([true, ""])) };
    let (records, new, diagnostics, runner_errors) =
        cycle::run_cycle(Some(&good), &Value::Null, NOW, None, Some(&[]), None);
    assert!(records.is_empty() && new.is_empty());
    assert!(diagnostics.run_failures.is_empty() && runner_errors.is_empty());
}

#[test]
fn raising_runner_carries_prior_and_names_error() {
    let priors = json!({"alpha": {"watchman_alive": true, "last_tick": NOW, "last_bell": NOW, "restart_ok": true}});
    let raising = |name: &str| -> Result<Value, String> {
        if name == "alpha" {
            Err("RuntimeError".to_string())
        } else {
            Ok(json!([true, ""]))
        }
    };
    let priors_before = priors.clone();
    let (records, new, diagnostics, runner_errors) = cycle::run_cycle(
        Some(&raising),
        &json!(["alpha", "beta"]),
        NOW + stale() + 100.0,
        Some(&priors),
        Some(&[]),
        None,
    );
    assert_eq!(diagnostics.run_failures, vec!["alpha".to_string()]);
    assert_eq!(runner_errors.get("alpha").map(|s| s.as_str()), Some("RuntimeError"));
    assert!(records["alpha"].get("restart_ok").is_none());
    assert_eq!(records["alpha"]["last_bell"], json!(NOW));
    assert_ne!(records["alpha"], priors["alpha"]);
    assert_eq!(
        new.iter().map(|e| e["kind"].clone()).collect::<Vec<_>>(),
        vec![json!("crew-dark"), json!("watchman-restart"), json!("escalation")]
    );
    assert_eq!(priors, priors_before);
}

#[test]
fn garbage_string_is_bad_return_unjudged() {
    let garbage = |_: &str| -> Result<Value, String> { Ok(json!("oops, not a pair")) };
    let (records, new, diagnostics, runner_errors) =
        cycle::run_cycle(Some(&garbage), &json!(["gamma"]), NOW, None, Some(&[]), None);
    assert!(records.get("gamma").is_none() && new.is_empty());
    assert_eq!(diagnostics.run_failures, vec!["gamma".to_string()]);
    assert_eq!(runner_errors.get("gamma").map(|s| s.as_str()), Some("bad-return"));
}

#[test]
fn short_pair_is_bad_return() {
    let short = |_: &str| -> Result<Value, String> { Ok(json!([true])) };
    let (_records, _new, _diagnostics, runner_errors) =
        cycle::run_cycle(Some(&short), &json!(["a"]), NOW, None, Some(&[]), None);
    assert_eq!(runner_errors.get("a").map(|s| s.as_str()), Some("bad-return"));
}

#[test]
fn truthy_one_is_not_true() {
    let tricky = |_: &str| -> Result<Value, String> { Ok(json!([1, "x"])) };
    let (_records, _new, _diagnostics, runner_errors) =
        cycle::run_cycle(Some(&tricky), &json!(["a"]), NOW, None, Some(&[]), None);
    assert_eq!(runner_errors.get("a").map(|s| s.as_str()), Some("bad-return"));
}

#[test]
fn non_callable_fails_every_machine() {
    let (records, new, _diagnostics, runner_errors) =
        cycle::run_cycle(None, &json!(["alpha", "beta"]), NOW, None, Some(&[]), None);
    assert!(records.is_empty() && new.is_empty());
    assert_eq!(runner_errors.get("alpha").map(|s| s.as_str()), Some("not-callable"));
    assert_eq!(runner_errors.get("beta").map(|s| s.as_str()), Some("not-callable"));
}

#[test]
fn empty_machines_never_calls_runner() {
    let calls = std::cell::Cell::new(0usize);
    let counting = |_: &str| -> Result<Value, String> {
        calls.set(calls.get() + 1);
        Ok(json!([true, ""]))
    };
    // The empty machine list means no invocation happens at all.
    let (records, new, diagnostics, runner_errors) =
        cycle::run_cycle(Some(&counting), &json!([]), NOW, None, Some(&[]), None);
    assert!(records.is_empty() && new.is_empty());
    assert!(diagnostics.run_failures.is_empty() && runner_errors.is_empty());
    assert_eq!(calls.get(), 0);
}

#[test]
fn priors_and_journal_unchanged() {
    let priors = json!({"alpha": {"watchman_alive": true, "last_bell": NOW}});
    let journal = vec![json!({"kind": "crew-dark", "machine": "beta"})];
    let priors_before = priors.clone();
    let journal_before = journal.clone();
    let good = |_: &str| -> Result<Value, String> { Ok(json!([true, ""])) };
    cycle::run_cycle(Some(&good), &json!(["alpha"]), NOW, Some(&priors), Some(&journal), None);
    assert_eq!(priors, priors_before);
    assert_eq!(journal, journal_before);
}

