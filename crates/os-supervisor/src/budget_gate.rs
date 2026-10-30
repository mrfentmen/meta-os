//! Budget-warning detection for the supervisor tick.
//!
//! The pure gate (warning band vs cap) canonically lives in
//! `os-budget` (B20, `budgets.py` behavior); this module carries
//! the same pure function the live tick calls, so the supervisor
//! crate stays self-contained on its branch. Behavior is
//! identical: a lane past its warning threshold of cap yields one
//! warning alert; a lane at cap yields none (the hold is the
//! louder signal); entries without a usable cap are unbudgeted;
//! malformed entries are skipped.

use serde_json::Value;

use crate::watchdog::Alert;

/// Warning threshold percent: WATCHDOG_BUDGET_WARN_PERCENT or 80.
pub fn warn_percent_default() -> u64 {
    crate::watchdog::budget_warn_percent()
}

fn usable_int(value: &Value) -> Option<i64> {
    match value {
        Value::Number(n) => n.as_i64(),
        _ => None,
    }
}

fn at_warning(spent: i64, cap: i64, warn_percent: u64) -> bool {
    if cap <= 0 || spent < 0 {
        return false;
    }
    spent as f64 / cap as f64 >= warn_percent as f64 / 100.0 && spent < cap
}

/// Budget-warning alerts for one snapshot tick.
pub fn detect_budget_warning(snapshot: &Value, now: i64, warn_percent: u64) -> Vec<Alert> {
    let budgets = match snapshot.get("budgets").and_then(|v| v.as_array()) {
        Some(items) => items,
        None => return Vec::new(),
    };
    let mut alerts = Vec::new();
    let mut seen = std::collections::HashSet::new();
    for entry in budgets {
        let obj = match entry.as_object() {
            Some(o) => o,
            None => continue,
        };
        let lane = match obj.get("lane").and_then(|v| v.as_str()) {
            Some(l) if !l.is_empty() => l.to_string(),
            _ => continue,
        };
        if !seen.insert(lane.clone()) {
            continue;
        }
        let (spent, cap) = match (
            obj.get("spent").and_then(usable_int),
            obj.get("cap").and_then(usable_int),
        ) {
            (Some(s), Some(c)) => (s, c),
            _ => continue,
        };
        if !at_warning(spent, cap, warn_percent) {
            continue;
        }
        let (explanation, suggested_fix) = crate::explanations::render(
            "budget-warning",
            &[
                ("lane", lane.clone()),
                ("spent", spent.to_string()),
                ("cap", cap.to_string()),
                ("remaining", (cap - spent).to_string()),
                ("warn_percent", warn_percent.to_string()),
            ]
            .into_iter()
            .collect::<std::collections::BTreeMap<_, _>>(),
        )
        .unwrap_or((format!("budget-warning:{lane}"), format!("budget-warning:{lane}")));
        alerts.push(
            Alert::new("budget-warning", "warning")
                .set("lane", Value::String(lane.clone()))
                .set("spent", Value::Number(spent.into()))
                .set("cap", Value::Number(cap.into()))
                .set("remaining", Value::Number((cap - spent).into()))
                .set("explanation", Value::String(explanation))
                .set("suggested_fix", Value::String(suggested_fix))
                .set(
                    "dedupe_key",
                    Value::String(format!("budget-warning:{lane}")),
                )
                .set("created_at", Value::Number(now.into())),
        );
    }
    alerts
}
