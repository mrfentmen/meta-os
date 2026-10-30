//! Parity tests for
//! `os/tests/test_intel_brief_environment_budget.py` (OS-103).
//!
//! The environment record's budget part, read from a budgets
//! list: spent/cap renders remaining with cap, remaining-direct
//! renders without the cap part, malformed entries are skipped,
//! overspend stays honestly negative.

use os_budget::brief_budget::{age_label, budget_line, environment_budget_record};
use serde_json::{json, Value};

fn budgets() -> Value {
    json!([
        {"lane": "HANA", "spent": 120, "cap": 300},
        {"lane": "MILO", "spent": 50, "cap": 200},
    ])
}

#[test]
fn spent_and_cap_record_renders_remaining_with_cap() {
    let record = environment_budget_record(&budgets(), Some("HANA"), Some(1_793_093_400)).unwrap();
    assert_eq!(record["lane"], json!("HANA"));
    assert_eq!(record["spent"], json!(120));
    assert_eq!(record["cap"], json!(300));
    assert_eq!(record["as_of"], json!(1_793_093_400));
    let line = budget_line(Some(&record), record.get("as_of"));
    assert!(line.contains("Budget: HANA lane: 180 remaining of 300 cap"), "{line}");
}

#[test]
fn named_lane_picked_among_many_unknown_lane_is_none() {
    let record = environment_budget_record(&budgets(), Some("MILO"), Some(1_793_093_400)).unwrap();
    assert_eq!(record["lane"], json!("MILO"));
    let line = budget_line(Some(&record), record.get("as_of"));
    assert!(line.contains("Budget: MILO lane: 150 remaining of 200 cap"), "{line}");
    assert!(environment_budget_record(&budgets(), Some("PAX"), Some(1_793_093_400)).is_none());
}

#[test]
fn no_lane_takes_first_usable_entry() {
    let milo = budgets().as_array().unwrap()[1].clone();
    let record = environment_budget_record(
        &json!([{"lane": "", "spent": 1, "cap": 2}, milo]),
        None,
        Some(1_793_093_400),
    )
    .unwrap();
    assert_eq!(record["lane"], json!("MILO"));
}

#[test]
fn remaining_direct_renders_without_cap_part() {
    let record =
        environment_budget_record(&json!([{"lane": "HANA", "remaining": 75}]), None, Some(1_793_093_400))
            .unwrap();
    assert_eq!(record["remaining"], json!(75));
    assert!(record.get("cap").is_none());
    let line = budget_line(Some(&record), record.get("as_of"));
    assert!(line.contains("Budget: HANA lane: 75 remaining"), "{line}");
    assert!(!line.contains("cap"), "{line}");
}

#[test]
fn malformed_entries_skipped_never_guessed() {
    let malformed = json!([
        {"lane": "HANA", "spent": true, "cap": 300},
        {"lane": "HANA", "spent": -5, "cap": 300},
        {"lane": "HANA", "spent": 10, "cap": 0},
        {"lane": "HANA", "spent": "120", "cap": 300},
        {"lane": "HANA", "cap": 300},
        {"spent": 10, "cap": 300},
        "HANA",
        null,
    ]);
    assert!(environment_budget_record(&malformed, Some("HANA"), Some(1_793_093_400)).is_none());
    assert!(environment_budget_record(&Value::Null, None, Some(1_793_093_400)).is_none());
    assert!(environment_budget_record(&json!([]), None, Some(1_793_093_400)).is_none());
    let line = budget_line(None, None);
    assert!(line.contains("not reported"), "{line}");
}

#[test]
fn overspend_kept_as_honest_negative_remaining() {
    let record = environment_budget_record(
        &json!([{"lane": "HANA", "spent": 310, "cap": 300}]),
        None,
        Some(1_793_093_400),
    )
    .unwrap();
    let line = budget_line(Some(&record), record.get("as_of"));
    assert!(line.contains("Budget: HANA lane: -10 remaining of 300 cap"), "{line}");
}

#[test]
fn builder_record_renders_budget_line_and_others_not_reported() {
    // A record carrying only the budget part renders the budget
    // line; the repo/bus/working lines are composer-owned (B10)
    // and read not reported there.
    let record = environment_budget_record(&budgets(), Some("HANA"), Some(1_793_093_400)).unwrap();
    let line = budget_line(Some(&record), record.get("as_of"));
    assert!(line.contains("Budget: HANA lane: 180 remaining"), "{line}");
    assert!(age_label(record.get("as_of")).contains("2026-10-27"), "{}", age_label(record.get("as_of")));
}

#[test]
fn merged_part_carries_budget_with_one_stamp() {
    // build_environment_record merges the budget part in with one
    // stamp (repo/bus/jobs quarters are Hana's B10): the budget
    // part carries the merged stamp, and a snapshot without
    // budgets leaves budget out.
    let record = environment_budget_record(&budgets(), Some("HANA"), Some(1_793_093_400)).unwrap();
    assert_eq!(record["as_of"], json!(1_793_093_400));
    assert_eq!(record["lane"], json!("HANA"));
    let line = budget_line(Some(&record), Some(&json!(1_793_093_400)));
    assert!(line.contains("Budget: HANA lane: 180 remaining of 300 cap"), "{line}");
}

#[test]
fn merged_part_without_budgets_leaves_budget_out() {
    assert!(environment_budget_record(&json!([]), None, Some(1_793_093_400)).is_none());
    let line = budget_line(None, None);
    assert!(line.contains("not reported"), "{line}");
}

#[test]
fn budget_line_carries_merged_record_into_boot_brief() {
    // The boot template brief carries "Budget: HANA lane: 180
    // remaining of 300 cap": the budget quarter renders the same
    // text the composer embeds (composition itself is B10).
    let record = environment_budget_record(&budgets(), Some("HANA"), Some(1_793_093_400)).unwrap();
    let line = budget_line(Some(&record), record.get("as_of"));
    assert!(line.contains("Budget: HANA lane: 180 remaining of 300 cap"), "{line}");
}
