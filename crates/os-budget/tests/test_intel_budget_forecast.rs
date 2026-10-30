//! Parity tests for `os/tests/test_intel_budget_forecast.py` (OS-091).
//!
//! The pure forecast math, preempt/resume decisions, the brief
//! line through the renderer, and the drill phases. The drill
//! subprocess half is ported as the in-process
//! [`os_budget::drills::run_budget_forecast`] runner asserting the
//! same PASS phases.

use os_budget::budgets::budget_state;
use os_budget::drills::run_budget_forecast;
use os_budget::forecast::{
    confidence_for, confidence_for_value, forecast_entry, forecast_entry_value,
    forecast_lines, preempt_decision, preempt_record, project_end_of_day,
    project_end_of_day_value,
};
use serde_json::{json, Value};

#[test]
fn projection_scales_the_ledger_rate() {
    assert_eq!(project_end_of_day(80.0, 8.0, 24.0), Some(240.0));
    assert_eq!(project_end_of_day(50.0, 12.0, 24.0), Some(100.0));
}

#[test]
fn projection_at_or_past_day_end_is_spent() {
    assert_eq!(project_end_of_day(90.0, 24.0, 24.0), Some(90.0));
    assert_eq!(project_end_of_day(90.0, 30.0, 24.0), Some(90.0));
}

#[test]
fn unprojectable_inputs_yield_none() {
    assert_eq!(project_end_of_day(-5.0, 8.0, 24.0), None);
    assert_eq!(project_end_of_day(80.0, 0.0, 24.0), None);
    assert_eq!(project_end_of_day(80.0, -2.0, 24.0), None);
    assert_eq!(project_end_of_day(80.0, 8.0, 0.0), None);
    assert_eq!(
        project_end_of_day_value(&json!("lots"), &json!(8), &json!(24)),
        None
    );
}

#[test]
fn confidence_comes_from_elapsed_hours_alone() {
    assert_eq!(confidence_for(2.0), "low");
    assert_eq!(confidence_for(4.0), "medium");
    assert_eq!(confidence_for(8.0), "medium");
    assert_eq!(confidence_for(12.0), "high");
    assert_eq!(confidence_for(0.0), "unknown");
    assert_eq!(confidence_for_value(&json!("soon")), "unknown");
}

#[test]
fn entry_carries_basis_and_verdict() {
    let entry = forecast_entry("spark", 80.0, 100.0, 8.0, 24.0).unwrap();
    assert_eq!(entry.projected, 240.0);
    assert!(entry.over_cap);
    assert_eq!(entry.confidence, "medium");
    assert!(entry.basis.contains("8 hours of ledger"), "{}", entry.basis);
}

#[test]
fn within_cap_entry_has_no_breach() {
    let entry = forecast_entry("spark", 20.0, 100.0, 8.0, 24.0).unwrap();
    assert_eq!(entry.projected, 60.0);
    assert!(!entry.over_cap);
}

#[test]
fn unusable_entries_yield_none() {
    assert!(forecast_entry("", 80.0, 100.0, 8.0, 24.0).is_none());
    assert!(forecast_entry("spark", 80.0, 0.0, 8.0, 24.0).is_none());
    assert!(forecast_entry("spark", 80.0, 100.0, 0.0, 24.0).is_none());
    assert!(forecast_entry_value(&json!({"lane": "spark", "spent": null, "cap": 100, "elapsed_hours": 8})).is_none());
}

#[test]
fn line_names_figures_basis_confidence_verdict() {
    let lines = forecast_lines(&json!([{"lane": "spark", "spent": 80, "cap": 100, "elapsed_hours": 8}]));
    assert_eq!(lines.len(), 1);
    assert!(lines[0].contains("80 spent of 100 cap"), "{}", lines[0]);
    assert!(lines[0].contains("projected 240"), "{}", lines[0]);
    assert!(lines[0].contains("8 hours of ledger"), "{}", lines[0]);
    assert!(lines[0].contains("medium confidence"), "{}", lines[0]);
    assert!(lines[0].contains("breach expected before end of day"), "{}", lines[0]);
    assert!(!lines[0].trim_start().starts_with('-'));
    assert!(!lines[0].trim_start().starts_with('*'));
}

#[test]
fn within_cap_line_says_within_cap() {
    let lines = forecast_lines(&json!([{"lane": "spark", "spent": 20, "cap": 100, "elapsed_hours": 8}]));
    assert!(lines[0].contains("within cap"), "{}", lines[0]);
}

#[test]
fn unusable_entries_and_empty_input_yield_no_lines() {
    let lines = forecast_lines(&json!([
        {"lane": "spark", "spent": 80, "cap": 100, "elapsed_hours": 0},
        {"lane": "", "spent": 80, "cap": 100, "elapsed_hours": 8},
        "not-a-dict",
    ]));
    assert_eq!(lines, Vec::<String>::new());
    assert_eq!(forecast_lines(&json!([])), Vec::<String>::new());
}

#[test]
fn pause_only_low_running_in_warning_lane() {
    let low = json!({"priority": "low", "status": "running"});
    assert_eq!(preempt_decision(&low, "warning"), Some("pause"));
    assert_eq!(preempt_decision(&low, "ok"), None);
    assert_eq!(preempt_decision(&low, "capped"), None);
    assert_eq!(preempt_decision(&low, "unbudgeted"), None);
}

#[test]
fn high_priority_never_paused() {
    let high = json!({"priority": "high", "status": "running"});
    assert_eq!(preempt_decision(&high, "warning"), None);
}

#[test]
fn already_paused_never_paused_twice() {
    let paused = json!({"priority": "low", "status": "paused"});
    assert_eq!(preempt_decision(&paused, "warning"), None);
}

#[test]
fn resume_only_when_budget_freed() {
    let paused = json!({"priority": "low", "status": "paused"});
    assert_eq!(preempt_decision(&paused, "ok"), Some("resume"));
    assert_eq!(preempt_decision(&paused, "unbudgeted"), Some("resume"));
    assert_eq!(preempt_decision(&paused, "warning"), None);
    assert_eq!(preempt_decision(&paused, "capped"), None);
}

#[test]
fn malformed_job_yields_none() {
    assert_eq!(preempt_decision(&Value::Null, "warning"), None);
    assert_eq!(preempt_decision(&json!({"status": "running"}), "warning"), None);
}

#[test]
fn pause_decision_uses_the_os085_warning_band() {
    // The decision's "warning" state is exactly budgets.py's:
    // 80/100 is warning, 79/100 is ok, 100/100 is capped.
    assert_eq!(budget_state(&json!({"lane": "x", "spent": 80, "cap": 100})), "warning");
    assert_eq!(
        preempt_decision(
            &json!({"priority": "low", "status": "running"}),
            budget_state(&json!({"lane": "x", "spent": 80, "cap": 100})),
        ),
        Some("pause")
    );
}

#[test]
fn preempt_record_names_job_lane_action() {
    let record = preempt_record("job-1", "spark", "paused", "lane at warning");
    assert_eq!(record["job"], json!("job-1"));
    assert_eq!(record["lane"], json!("spark"));
    assert_eq!(record["action"], json!("paused"));
}

#[test]
fn drill_passes() {
    let log = run_budget_forecast().expect("budget forecast drill (5/5 phases)");
    assert_eq!(log.len(), 5);
}
