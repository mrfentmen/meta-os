//! Parity tests for
//! `os/tests/test_intel_brief_memory_budget_caller.py` (OS-079).
//!
//! The brief-path caller fills `memory_budget` from the
//! snapshot's own budgets list plus stated settled decisions,
//! with one stamp; a hand-stated record wins untouched; a
//! snapshot with nothing usable gets no record; memory-down
//! passes through alone.

use os_budget::brief_budget::{memory_budget_lines, with_memory_budget};
use serde_json::{json, Value};

fn snapshot() -> Value {
    json!({
        "messages": [],
        "jobs": [],
        "budgets": [{"lane": "HANA", "spent": 120, "cap": 300},
                    {"lane": "MILO", "remaining": 90, "cap": 200}],
        "settled_decisions": ["Morning brief format is final"]
    })
}

#[test]
fn fills_budgets_and_decisions_with_one_stamp() {
    let filled = with_memory_budget(&snapshot(), Some(1_793_093_400));
    let record = &filled["memory_budget"];
    assert_eq!(record["as_of"], json!(1_793_093_400));
    assert_eq!(record["settled_decisions"], json!(["Morning brief format is final"]));
    assert_eq!(
        record["budgets"],
        json!([{"lane": "HANA", "spent": 120, "cap": 300},
               {"lane": "MILO", "remaining": 90, "cap": 200}])
    );
}

#[test]
fn filled_record_renders_settled_and_spend_lines() {
    let filled = with_memory_budget(&snapshot(), Some(1_793_093_400));
    let lines = memory_budget_lines(&filled["memory_budget"]);
    assert!(lines[0].contains("Morning brief format is final"), "{lines:?}");
    assert!(lines[1].contains("Spend: HANA lane: 120 of 300 budget (180 remaining)"), "{lines:?}");
    assert!(lines[2].contains("Spend: MILO lane: 90 remaining of 200 cap"), "{lines:?}");
}

#[test]
fn hand_stated_record_wins_unchanged() {
    let stated = json!({"settled_decisions": ["Hand-stated call"],
                        "budgets": [{"lane": "HANA", "spent": 1, "cap": 2}],
                        "as_of": 1_793_093_400});
    let snap = json!({"memory_budget": stated,
                      "budgets": [{"lane": "MILO", "spent": 9, "cap": 9}]});
    let filled = with_memory_budget(&snap, Some(1_793_093_400));
    assert_eq!(
        filled["memory_budget"],
        json!({"settled_decisions": ["Hand-stated call"],
               "budgets": [{"lane": "HANA", "spent": 1, "cap": 2}],
               "as_of": 1_793_093_400})
    );
}

#[test]
fn caller_snapshot_is_never_mutated() {
    let original = snapshot();
    let before = original.clone();
    with_memory_budget(&original, Some(1_793_093_400));
    assert_eq!(original, before);
    assert!(original.get("memory_budget").is_none());
}

#[test]
fn snapshot_with_nothing_usable_gets_no_record() {
    let filled = with_memory_budget(&json!({"messages": [], "jobs": []}), Some(1_793_093_400));
    assert!(filled.get("memory_budget").is_none());
    let mut keys: Vec<&str> = filled.as_object().unwrap().keys().map(|k| k.as_str()).collect();
    keys.sort();
    assert_eq!(keys, vec!["jobs", "messages"]);
}

#[test]
fn malformed_budget_entries_skipped_never_guessed() {
    let filled = with_memory_budget(
        &json!({"budgets": [{"lane": "HANA", "spent": true, "cap": 300},
                            {"lane": "MILO", "spent": -5, "cap": 300},
                            {"lane": "BUFFY", "spent": 10, "cap": 0},
                            {"spent": 10, "cap": 300},
                            {"lane": "ROWAN", "remaining": 40},
                            {"lane": "PAX", "spent": 350, "cap": 300},
                            "not a dict",
                            {"lane": "DEEP", "remaining": true}]}),
        Some(1_793_093_400),
    );
    assert_eq!(
        filled["memory_budget"]["budgets"],
        json!([{"lane": "ROWAN", "remaining": 40},
               {"lane": "PAX", "spent": 350, "cap": 300}])
    );
}

#[test]
fn memory_down_passes_through_and_shows_no_decision() {
    let filled = with_memory_budget(
        &json!({"memory_down": true,
                "settled_decisions": ["Must not appear"],
                "budgets": [{"lane": "HANA", "spent": 10, "cap": 100}]}),
        Some(1_793_093_400),
    );
    let record = &filled["memory_budget"];
    assert_eq!(record["memory_down"], json!(true));
    let lines = memory_budget_lines(record);
    assert!(lines[0].contains("memory service down"), "{lines:?}");
    assert!(!lines.join("\n").contains("Must not appear"));
}

#[test]
fn section_lines_carry_brief_content_for_morning_brief() {
    // The morning template brief over the filled snapshot carries
    // the settled/spend lines: the record plus its rendered lines
    // are the section (composition itself is B10).
    let filled = with_memory_budget(&snapshot(), Some(1_793_093_400));
    let lines = memory_budget_lines(&filled["memory_budget"]);
    let section = lines.join("\n");
    assert!(section.contains("Morning brief format is final"), "{section}");
    assert!(section.contains("Spend: HANA lane: 120 of 300 budget"), "{section}");
}

#[test]
fn default_stamp_is_an_int_when_now_is_not_given() {
    let filled = with_memory_budget(&snapshot(), None);
    assert!(filled["memory_budget"]["as_of"].is_i64());
}

#[test]
fn non_dict_snapshot_gets_no_record() {
    assert_eq!(with_memory_budget(&Value::Null, Some(1)), json!({}));
}
