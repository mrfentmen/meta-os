//! Port of `os/intel/soak_review.py` — seven-day soak journal
//! review (OS-074).
//!
//! The review half only, as pure functions of fixture journal
//! entries: given a journal, it names exactly which failures
//! are covered (an alert or a bug naming the failure id) and
//! which are unexplained gaps, which cover records are
//! orphans, which failures are undated, and which soak days
//! are present or missing. Malformed entries are counted in
//! skipped, never a crash. Inputs are never mutated. The soak
//! itself is not claimed here — see the source docstring.

use super::value::Value;

pub const SOAK_DAYS: [i64; 7] = [1, 2, 3, 4, 5, 6, 7];

fn is_failure(entry: &Value) -> bool {
    entry.is_dict()
        && entry.get("kind").as_str() == Some("silent_failure")
        && matches!(entry.get("id"), Value::Str(ref s) if !s.is_empty())
}

fn is_cover(entry: &Value) -> bool {
    entry.is_dict()
        && matches!(entry.get("kind").as_str(), Some("alert") | Some("bug"))
        && matches!(entry.get("failure_id"), Value::Str(ref s) if !s.is_empty())
}

/// A usable soak day: a real int (never a bool) inside 1..=7.
fn usable_day(entry: &Value) -> Option<i64> {
    match entry.get("day") {
        Value::Int(d) if SOAK_DAYS.contains(&d) => Some(d),
        _ => None,
    }
}

/// `review_journal(entries)` — the report dict, keys in the
/// source's order.
pub fn review_journal(entries: &Value) -> Value {
    let empty: Vec<Value> = Vec::new();
    let entries = entries.as_list().unwrap_or(&empty);
    let mut failure_order: Vec<String> = Vec::new();
    let mut undated: Vec<String> = Vec::new();
    let mut days_present: Vec<i64> = Vec::new();
    let mut covers: Vec<(String, Vec<Value>)> = Vec::new();
    let mut skipped: i64 = 0;
    for entry in entries {
        if is_failure(entry) {
            let failure_id = entry.get("id").py_str();
            if !failure_order.contains(&failure_id) {
                failure_order.push(failure_id.clone());
            }
            match usable_day(entry) {
                Some(day) => {
                    if !days_present.contains(&day) {
                        days_present.push(day);
                    }
                }
                None => {
                    if !undated.contains(&failure_id) {
                        undated.push(failure_id);
                    }
                }
            }
        } else if is_cover(entry) {
            if let Some(day) = usable_day(entry) {
                if !days_present.contains(&day) {
                    days_present.push(day);
                }
            }
            let failure_id = entry.get("failure_id").py_str();
            if let Some(slot) = covers.iter_mut().find(|(k, _)| *k == failure_id) {
                slot.1.push(entry.clone());
            } else {
                covers.push((failure_id, vec![entry.clone()]));
            }
        } else {
            // Both the source's elif (alert/bug kind that
            // failed the cover shape) and its else land here.
            skipped += 1;
        }
    }
    let mut coverage: Vec<(String, Value)> = Vec::new();
    let mut covered: Vec<String> = Vec::new();
    let mut gaps: Vec<String> = Vec::new();
    for failure_id in &failure_order {
        let records: &[Value] = covers
            .iter()
            .find(|(k, _)| k == failure_id)
            .map(|(_, v)| v.as_slice())
            .unwrap_or(&[]);
        let ids_of = |kind: &str| -> Vec<Value> {
            records
                .iter()
                .filter(|r| r.get("kind").as_str() == Some(kind))
                .filter_map(|r| match r.get("id") {
                    Value::Str(_) => Some(r.get("id")),
                    _ => None,
                })
                .collect()
        };
        let named = !records.is_empty();
        coverage.push((
            failure_id.clone(),
            Value::obj(vec![
                ("alerts", Value::List(ids_of("alert"))),
                ("bugs", Value::List(ids_of("bug"))),
                ("covered", Value::Bool(named)),
            ]),
        ));
        if named {
            covered.push(failure_id.clone());
        } else {
            gaps.push(failure_id.clone());
        }
    }
    let mut orphans: Vec<Value> = Vec::new();
    for (failure_id, records) in &covers {
        if !failure_order.contains(failure_id) {
            for record in records {
                orphans.push(Value::obj(vec![
                    ("failure_id", Value::s(failure_id)),
                    ("kind", record.get("kind")),
                    ("id", record.get("id")),
                ]));
            }
        }
    }
    let mut present_sorted = days_present.clone();
    present_sorted.sort();
    let days_missing: Vec<Value> = SOAK_DAYS
        .iter()
        .filter(|d| !days_present.contains(d))
        .map(|d| Value::Int(*d))
        .collect();
    Value::obj(vec![
        ("total_failures", Value::Int(failure_order.len() as i64)),
        ("covered_failures", Value::Int(covered.len() as i64)),
        (
            "covered",
            Value::List(covered.iter().map(|s| Value::s(s)).collect()),
        ),
        (
            "unexplained_gaps",
            Value::List(gaps.iter().map(|s| Value::s(s)).collect()),
        ),
        ("coverage", Value::Map(coverage)),
        ("orphans", Value::List(orphans)),
        (
            "undated",
            Value::List(undated.iter().map(|s| Value::s(s)).collect()),
        ),
        (
            "days_present",
            Value::List(present_sorted.iter().map(|d| Value::Int(*d)).collect()),
        ),
        ("days_missing", Value::List(days_missing)),
        ("skipped", Value::Int(skipped)),
        (
            "verdict",
            Value::s(if gaps.is_empty() { "clean" } else { "gaps" }),
        ),
    ])
}

/// `soak_brief_lines(report)` — the plain brief lines.
pub fn soak_brief_lines(report: &Value) -> Vec<String> {
    let gaps = report.get("unexplained_gaps");
    let gap_items = gaps.as_list().cloned().unwrap_or_default();
    let mut lines = vec![
        format!(
            "Soak review: {} failures, {} covered, {} unexplained gaps.",
            report.get("total_failures").py_str(),
            report.get("covered_failures").py_str(),
            gap_items.len()
        ),
        format!("Soak verdict: {}.", report.get("verdict").py_str()),
    ];
    for failure_id in &gap_items {
        lines.push(format!(
            "Unexplained gap: failure {} has no alert and no bug.",
            failure_id.py_str()
        ));
    }
    let missing = report.get("days_missing");
    let missing_items = missing.as_list().cloned().unwrap_or_default();
    if !missing_items.is_empty() {
        let joined = missing_items
            .iter()
            .map(|d| d.py_str())
            .collect::<Vec<_>>()
            .join(", ");
        lines.push(format!("Soak days missing: {}.", joined));
    } else {
        lines.push("Soak days: all 7 days present.".to_string());
    }
    lines
}
