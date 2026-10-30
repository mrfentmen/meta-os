//! Parity tests for `os/tests/test_intel_budget_gate.py` (OS-085).
//!
//! The pure gate functions, the budget-warning detector through a
//! tick-equivalent, the brief hold line through the real
//! renderer, and the drill phases. The live `jobs.py` claim path
//! and the WDG-013 cooldown store are B21 (`os-supervisor`)
//! territory; the detector here is the same pure function the
//! live path calls.

use os_budget::brief_budget::memory_budget_lines;
use os_budget::budgets::{
    at_cap_value, at_warning_value, budget_state, budgets_from_snapshot, claim_allowed,
    claim_allowed_value, hold_entry, BUDGET_WARN_PERCENT,
};
use os_budget::drills::run_budget_gate;
use os_budget::watch_budget::detect_budget_warning;
use serde_json::json;

#[test]
fn warning_band_is_threshold_to_cap_exclusive() {
    assert!(!at_warning_value(&json!(79), &json!(100), 80));
    assert!(at_warning_value(&json!(80), &json!(100), 80));
    assert!(at_warning_value(&json!(99), &json!(100), 80));
    assert!(!at_warning_value(&json!(100), &json!(100), 80));
}

#[test]
fn cap_includes_overspend() {
    assert!(!at_cap_value(&json!(99), &json!(100)));
    assert!(at_cap_value(&json!(100), &json!(100)));
    assert!(at_cap_value(&json!(150), &json!(100)));
}

#[test]
fn claim_gate_follows_cap_only() {
    assert!(claim_allowed(99, 100));
    assert!(claim_allowed(80, 100));
    assert!(!claim_allowed(100, 100));
    assert!(claim_allowed_value(&json!(null), &json!(null)));
}

#[test]
fn unbudgeted_and_malformed_are_never_warned_or_held() {
    let none = json!(null);
    assert!(!at_warning_value(&none, &none, 80));
    assert!(!at_cap_value(&none, &none));
    assert!(!at_warning_value(&json!("lots"), &json!("none"), 80));
    assert!(!at_cap_value(&json!(90), &json!(0)));
    assert!(!at_cap_value(&json!(-5), &json!(100)));
    assert_eq!(budget_state(&json!({"lane": "x"})), "unbudgeted");
    assert_eq!(budget_state(&json!("not-a-dict")), "unbudgeted");
}

#[test]
fn budget_state_names_all_three_states() {
    assert_eq!(budget_state(&json!({"lane": "s", "spent": 50, "cap": 100})), "ok");
    assert_eq!(budget_state(&json!({"lane": "s", "spent": 80, "cap": 100})), "warning");
    assert_eq!(budget_state(&json!({"lane": "s", "spent": 100, "cap": 100})), "capped");
}

#[test]
fn hold_entry_flags_only_at_cap() {
    assert!(!hold_entry("s", 80, 100)["held"].as_bool().unwrap());
    assert!(hold_entry("s", 100, 100)["held"].as_bool().unwrap());
}

fn snapshot(spent: i64, cap: i64) -> serde_json::Value {
    json!({"jobs": [], "messages": [], "presence": [], "caps": {},
           "budgets": [{"lane": "spark", "spent": spent, "cap": cap}]})
}

#[test]
fn warning_fires_at_threshold_with_lane_figures() {
    let alerts = detect_budget_warning(&snapshot(80, 100), 100_000, BUDGET_WARN_PERCENT);
    assert_eq!(alerts.len(), 1);
    let alert = &alerts[0];
    assert_eq!(alert.severity, "warning");
    assert_eq!(alert.lane, "spark");
    assert_eq!(alert.spent, 80);
    assert_eq!(alert.cap, 100);
    assert_eq!(alert.remaining, 20);
    assert_eq!(alert.dedupe_key, "budget-warning:spark");
    assert!(alert.explanation.contains("spark"), "{}", alert.explanation);
    assert!(alert.explanation.contains("80"), "{}", alert.explanation);
}

#[test]
fn no_warning_below_threshold_or_at_cap() {
    for spent in [0, 70, 100, 150] {
        let alerts = detect_budget_warning(&snapshot(spent, 100), 100_000, BUDGET_WARN_PERCENT);
        assert!(alerts.is_empty(), "spent={spent}");
    }
}

#[test]
fn warning_is_never_critical_so_never_announced() {
    // WDG-015 announces critical alerts only; a warning severity
    // accumulates silently. The gate is the severity itself.
    let alerts = detect_budget_warning(&snapshot(80, 100), 100_000, BUDGET_WARN_PERCENT);
    assert_eq!(alerts.len(), 1);
    assert_ne!(alerts[0].severity, "critical");
}

#[test]
fn malformed_budget_entries_do_not_crash_the_tick() {
    let snapshot = json!({"jobs": [], "messages": [], "presence": [], "caps": {},
        "budgets": [{"lane": "bad", "spent": "lots", "cap": "none"},
                    {"spent": 90, "cap": 100},
                    "not-a-dict"]});
    // Malformed figures are skipped by the detector's gate, and
    // laneness entries are kept by from_snapshot (a lane with no
    // usable cap is unbudgeted, never warned): the detector
    // yields nothing and never crashes.
    assert_eq!(budgets_from_snapshot(&snapshot).len(), 1);
    assert!(detect_budget_warning(&snapshot, 100_000, BUDGET_WARN_PERCENT).is_empty());
}

#[test]
fn held_lane_line_names_the_hold() {
    let lines = memory_budget_lines(&json!({"budgets": [hold_entry("spark", 100, 100)]}));
    let held: Vec<&String> = lines.iter().filter(|l| l.contains("spark")).collect();
    assert_eq!(held.len(), 1);
    assert!(held[0].contains("new claims held"), "{}", held[0]);
    assert!(held[0].contains("100 of 100"), "{}", held[0]);
}

#[test]
fn unheld_lane_line_unchanged() {
    let lines = memory_budget_lines(&json!({"budgets": [hold_entry("spark", 80, 100)]}));
    let held: Vec<&String> = lines.iter().filter(|l| l.contains("spark")).collect();
    assert_eq!(held.len(), 1);
    assert!(!held[0].contains("held"), "{}", held[0]);
}

#[test]
fn entry_without_flag_renders_as_before() {
    let lines = memory_budget_lines(&json!({"budgets": [{"lane": "spark", "spent": 50, "cap": 100}]}));
    let spark: Vec<&String> = lines.iter().filter(|l| l.contains("spark")).collect();
    assert_eq!(spark.len(), 1);
    assert!(!spark[0].contains("held"), "{}", spark[0]);
}

#[test]
fn drill_exits_zero_and_passes() {
    let log = run_budget_gate().expect("budget_gate drill");
    assert_eq!(log.len(), 4);
    assert!(log[0].contains("phase 1"));
    assert!(log[1].contains("phase 2"));
    assert!(log[2].contains("phase 3"));
    assert!(log[3].contains("phase 4"));
}
