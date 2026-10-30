//! Parity tests for
//! `os/tests/test_intel_brief_memory_depth_caller.py` (OS-092).
//!
//! The morning-path caller fills `memory_depth` from the
//! snapshot's own stated lists with one stamp; a hand-stated
//! record wins untouched; unusable snapshots get no record; a
//! down memory service is said alone. The morning-template
//! composer half is Hana's B10 territory — the cases below pin
//! the filled record plus the rendered section lines the brief
//! carries.

use os_memory::brief_depth::{memory_depth_lines, with_memory_depth};
use serde_json::{json, Value};

fn snapshot() -> Value {
    json!({
        "messages": [],
        "aged_decisions": [{"decision": "freeze the demo fixture at noon",
                            "original_date": "2026-10-01"}],
        "due_commitments": [{"commitment": "ship the demo cut",
                             "due": "2026-11-03"}],
        "fresh_context": ["the demo room is build only, never a posting room"]
    })
}

#[test]
fn fills_all_three_categories_with_one_stamp() {
    let filled = with_memory_depth(&snapshot(), Some(1_793_093_400));
    let record = &filled["memory_depth"];
    assert_eq!(record["as_of"], json!(1_793_093_400));
    assert_eq!(
        record["aged_decisions"],
        json!([{"decision": "freeze the demo fixture at noon",
                "original_date": "2026-10-01"}])
    );
    assert_eq!(
        record["due_commitments"],
        json!([{"commitment": "ship the demo cut",
                "due": "2026-11-03"}])
    );
    assert_eq!(
        record["fresh_context"],
        json!(["the demo room is build only, never a posting room"])
    );
}

#[test]
fn filled_record_renders_memory_depth_lines() {
    let filled = with_memory_depth(&snapshot(), Some(1_793_093_400));
    let lines = memory_depth_lines(&filled["memory_depth"]);
    assert!(
        lines[0].contains("Aged decision: freeze the demo fixture at noon (from 2026-10-01)"),
        "{lines:?}"
    );
    assert!(
        lines[1].contains("Due commitment: ship the demo cut (due 2026-11-03)"),
        "{lines:?}"
    );
    assert!(
        lines[2].contains("Fresh-agent context: the demo room is build only, never a posting room"),
        "{lines:?}"
    );
}

#[test]
fn hand_stated_record_wins_unchanged() {
    let stated = json!({"aged_decisions": [{"decision": "Hand-stated decision",
                                             "original_date": "2026-09-01"}],
                        "as_of": 1_793_093_400});
    let snap = json!({"memory_depth": stated,
                      "aged_decisions": [{"decision": "stated list decision",
                                          "original_date": "2026-10-01"}]});
    let filled = with_memory_depth(&snap, Some(1_793_093_400));
    assert_eq!(
        filled["memory_depth"],
        json!({"aged_decisions": [{"decision": "Hand-stated decision",
                                   "original_date": "2026-09-01"}],
               "as_of": 1_793_093_400})
    );
}

#[test]
fn caller_snapshot_is_never_mutated() {
    let original = snapshot();
    let before = original.clone();
    with_memory_depth(&original, Some(1_793_093_400));
    assert_eq!(original, before);
    assert!(original.get("memory_depth").is_none());
}

#[test]
fn snapshot_with_nothing_usable_gets_no_record() {
    let filled = with_memory_depth(&json!({"messages": []}), Some(1_793_093_400));
    assert!(filled.get("memory_depth").is_none());
    let keys: Vec<&str> = filled
        .as_object()
        .unwrap()
        .keys()
        .map(|k| k.as_str())
        .collect();
    assert_eq!(keys, vec!["messages"]);
}

#[test]
fn malformed_entries_skipped_never_guessed() {
    let filled = with_memory_depth(
        &json!({
            "aged_decisions": [{"decision": ""},
                               {"original_date": "2026-10-01"},
                               "not a dict",
                               42,
                               {"decision": "dateless decision",
                                "original_date": ""},
                               {"decision": "dated decision",
                                "original_date": 20261001}],
            "due_commitments": [{"commitment": ""},
                                {"due": "2026-11-03"},
                                {"commitment": "dateless commitment",
                                 "due": ""},
                                {"commitment": "dated commitment",
                                 "due": 20261103}],
            "fresh_context": ["real context", "", 42, Value::Null]}),
        Some(1_793_093_400),
    );
    let record = &filled["memory_depth"];
    assert_eq!(
        record["aged_decisions"],
        json!([{"decision": "dateless decision"},
               {"decision": "dated decision"}])
    );
    assert_eq!(
        record["due_commitments"],
        json!([{"commitment": "dateless commitment"},
               {"commitment": "dated commitment"}])
    );
    assert_eq!(record["fresh_context"], json!(["real context"]));
    let lines = memory_depth_lines(record);
    assert!(lines[0].contains("Aged decision: dateless decision (original date not reported)"), "{lines:?}");
    assert!(lines[1].contains("Aged decision: dated decision (original date not reported)"), "{lines:?}");
    assert!(lines[2].contains("Due commitment: dateless commitment (due date not reported)"), "{lines:?}");
    assert!(lines[3].contains("Due commitment: dated commitment (due date not reported)"), "{lines:?}");
}

#[test]
fn memory_down_record_carries_no_item_beside_it() {
    let filled = with_memory_depth(
        &json!({"memory_down": true,
                "aged_decisions": [{"decision": "should not show",
                                    "original_date": "2026-10-01"}],
                "fresh_context": ["should not show"]}),
        Some(1_793_093_400),
    );
    assert_eq!(
        filled["memory_depth"],
        json!({"as_of": 1_793_093_400, "memory_down": true})
    );
    assert_eq!(
        memory_depth_lines(&filled["memory_depth"]),
        vec!["Long-term memory: memory service down, so no aged decisions, due commitments, or fresh-agent context are shown".to_string()]
    );
}

#[test]
fn single_category_record_reads_other_categories_none_reported() {
    let filled = with_memory_depth(
        &json!({"aged_decisions": [{"decision": "freeze the demo fixture",
                                    "original_date": "2026-10-01"}]}),
        Some(1_793_093_400),
    );
    let lines = memory_depth_lines(&filled["memory_depth"]);
    assert!(lines[0].contains("Aged decision: freeze the demo fixture (from 2026-10-01)"), "{lines:?}");
    assert!(lines[1].contains("Due commitments: none reported"), "{lines:?}");
    assert!(lines[2].contains("Fresh-agent context: none reported"), "{lines:?}");
}

#[test]
fn section_lines_carry_long_term_memory_content_for_brief() {
    // The morning template brief over the filled snapshot carries
    // the Long-term memory section: the record plus its rendered
    // lines are the section (composition itself is B10).
    let filled = with_memory_depth(&snapshot(), Some(1_793_093_400));
    let lines = memory_depth_lines(&filled["memory_depth"]);
    let section = lines.join("\n");
    assert!(section.contains("Aged decision: freeze the demo fixture at noon (from 2026-10-01)"), "{section}");
    assert!(section.contains("Due commitment: ship the demo cut (due 2026-11-03)"), "{section}");
    assert!(section.contains("Fresh-agent context: the demo room is build only, never a posting room"), "{section}");
}

#[test]
fn default_stamp_is_an_int_when_now_is_not_given() {
    let filled = with_memory_depth(&snapshot(), None);
    assert!(filled["memory_depth"]["as_of"].is_i64());
}

#[test]
fn non_dict_snapshot_gets_no_record() {
    assert_eq!(with_memory_depth(&Value::Null, Some(1)), json!({}));
}
