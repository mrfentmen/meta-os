//! OS-085 budget-warning detection (watchdog half owned by B21).
//!
//! The detector scans the snapshot's `budgets` list (OS-079
//! entries: lane, spent, cap); entries without a usable cap are
//! unbudgeted and yield nothing, malformed entries are skipped,
//! never guessed. One alert per lane per tick; the dedupe key is
//! `budget-warning:<lane>`. A lane at cap yields no warning here:
//! the cap hold is the louder signal.
//!
//! The tick loop, cooldown store, and announcement gate live in
//! `os-supervisor` (B21); this module ports the pure detection
//! and the alert shape the B20 tests pin.

use crate::budgets::{at_warning, budgets_from_snapshot, BUDGET_WARN_PERCENT};

/// One budget-warning alert in detector-dict shape.
#[derive(Debug, Clone)]
pub struct BudgetAlert {
    pub kind: String,
    pub severity: String,
    pub lane: String,
    pub spent: i64,
    pub cap: i64,
    pub remaining: i64,
    pub explanation: String,
    pub suggested_fix: String,
    pub dedupe_key: String,
    pub created_at: i64,
}

fn render_warning(lane: &str, spent: i64, cap: i64, remaining: i64, warn_percent: u64) -> (String, String) {
    // Templates from intel/explanations.py ("budget-warning"),
    // the same strings the suite asserts substrings of.
    let explanation = format!(
        "The {lane} lane has spent {spent} of its {cap} budget ({remaining} remaining): it is past the {warn_percent}% warning threshold, so the next claims could hit the cap and stop the lane silently."
    );
    let suggested_fix = format!(
        "Slow new {lane} claims, raise the lane cap, or let the lane finish its current work before posting more — at cap, new claims are held and the job stays open."
    );
    (explanation, suggested_fix)
}

fn usable_int(value: &serde_json::Value) -> Option<i64> {
    match value {
        serde_json::Value::Number(n) => n.as_i64(),
        _ => None,
    }
}

/// Budget-warning alerts for one snapshot tick.
pub fn detect_budget_warning(
    snapshot: &serde_json::Value,
    now: i64,
    warn_percent: u64,
) -> Vec<BudgetAlert> {
    let mut alerts = Vec::new();
    let mut seen = std::collections::HashSet::new();
    for entry in budgets_from_snapshot(snapshot) {
        let lane = match entry.get("lane").and_then(|v| v.as_str()) {
            Some(l) => l,
            None => continue,
        };
        if !seen.insert(lane.to_string()) {
            continue;
        }
        let (spent, cap) = match (entry.get("spent").and_then(usable_int), entry.get("cap").and_then(usable_int)) {
            (Some(s), Some(c)) => (s, c),
            _ => continue,
        };
        if !at_warning(spent, cap, warn_percent) {
            continue;
        }
        let (explanation, suggested_fix) =
            render_warning(lane, spent, cap, cap - spent, warn_percent);
        alerts.push(BudgetAlert {
            kind: "budget-warning".to_string(),
            severity: "warning".to_string(),
            lane: lane.to_string(),
            spent,
            cap,
            remaining: cap - spent,
            explanation,
            suggested_fix,
            dedupe_key: format!("budget-warning:{lane}"),
            created_at: now,
        });
    }
    alerts
}

/// Default-threshold entry point (reads `BUDGET_WARN_PERCENT`,
/// i.e. the `WATCHDOG_BUDGET_WARN_PERCENT` env or 80).
pub fn detect_budget_warning_default(snapshot: &serde_json::Value, now: i64) -> Vec<BudgetAlert> {
    detect_budget_warning(snapshot, now, BUDGET_WARN_PERCENT)
}
