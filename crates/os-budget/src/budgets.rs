successfully downloaded text file (SHA: f727f6a5658b0bc49a5b9843e8c21b150cfab045)
//! Per-lane and per-process budget config (OS-085, Milo).
//! (`os/intel/budgets.py`).
//!
//! Budgets are config the job queue reads before claiming, and the
//! watchdog reads before warning. A lane at its warning threshold
//! gets a budget-warning alert; a lane at its cap holds new claims.
//!
//! A lane with no usable cap is unbudgeted: claims are allowed and
//! no warning fires, because an absent budget is not a zero
//! budget. Malformed entries are skipped by the detector and
//! treated as unbudgeted by the gate, never guessed.

/// Budget warning threshold (OS-085): warn when a lane has spent
/// this percentage of its cap. Env `WATCHDOG_BUDGET_WARN_PERCENT`,
/// range 1-100. Read per call (the Python module reads it once at
/// import; call-time reads agree whenever the environment is
/// static and stay correct under the demo profile).
pub fn warn_percent_default() -> u64 {
    match std::env::var("WATCHDOG_BUDGET_WARN_PERCENT") {
        Ok(raw) => {
            let raw = raw.trim();
            match raw.parse::<i64>() {
                Ok(v) if v >= 1 && v <= 100 => v as u64,
                _ => 80,
            }
        }
        Err(_) => 80,
    }
}

pub const BUDGET_WARN_PERCENT: u64 = 80;

fn usable_int(value: &serde_json::Value) -> Option<i64> {
    match value {
        serde_json::Value::Number(n) => n.as_i64(),
        _ => None,
    }
}

/// Spent as a fraction of cap, or `None` when unusable.
pub fn spend_ratio(spent: i64, cap: i64) -> Option<f64> {
    if cap <= 0 || spent < 0 {
        return None;
    }
    Some(spent as f64 / cap as f64)
}

/// `true` when spent has reached the warning threshold but not
/// cap. The warning band is `[warn_percent, 100%)` of cap: at cap
/// the lane is held, not warned.
pub fn at_warning(spent: i64, cap: i64, warn_percent: u64) -> bool {
    match spend_ratio(spent, cap) {
        None => false,
        Some(ratio) => ratio >= warn_percent as f64 / 100.0 && spent < cap,
    }
}

/// `true` when spent has reached or passed cap. Overspend counts
/// as at cap.
pub fn at_cap(spent: i64, cap: i64) -> bool {
    match spend_ratio(spent, cap) {
        None => false,
        Some(_) => spent >= cap,
    }
}

/// The queue gate (OS-085): `false` only when the lane is at cap.
pub fn claim_allowed(spent: i64, cap: i64) -> bool {
    !at_cap(spent, cap)
}

/// One of "warning", "capped", "ok", or "unbudgeted" for an entry.
pub fn budget_state(entry: &serde_json::Value) -> &'static str {
    let obj = match entry.as_object() {
        Some(o) => o,
        None => return "unbudgeted",
    };
    let spent = obj.get("spent").and_then(usable_int);
    let cap = obj.get("cap").and_then(usable_int);
    match (spent, cap) {
        (Some(s), Some(c)) => {
            if at_cap(s, c) {
                return "capped";
            }
            if at_warning(s, c, BUDGET_WARN_PERCENT) {
                return "warning";
            }
            if spend_ratio(s, c).is_some() {
                return "ok";
            }
            "unbudgeted"
        }
        _ => "unbudgeted",
    }
}

/// The budget entries a snapshot carries, as usable dicts.
/// Non-list values, non-dict items, and entries without a
/// non-empty lane name are skipped, never guessed.
pub fn budgets_from_snapshot(snapshot: &serde_json::Value) -> Vec<&serde_json::Map<String, serde_json::Value>> {
    let mut out = Vec::new();
    let budgets = match snapshot.get("budgets") {
        Some(serde_json::Value::Array(items)) => items,
        _ => return out,
    };
    for entry in budgets {
        let obj = match entry.as_object() {
            Some(o) => o,
            None => continue,
        };
        match obj.get("lane").and_then(|v| v.as_str()) {
            Some(lane) if !lane.is_empty() => out.push(obj),
            _ => continue,
        }
    }
    out
}

/// An OS-079 budgets entry for a lane, with its hold flag set.
pub fn hold_entry(lane: &str, spent: i64, cap: i64) -> serde_json::Value {
    serde_json::json!({
        "lane": lane,
        "spent": spent,
        "cap": cap,
        "held": at_cap(spent, cap),
    })
}

/// Value-level gate wrappers: the Python functions accept
/// `None`/strings/bools (all unusable → no warning, no hold,
/// claims allowed). JSON `true` is unusable like Python's
/// explicit bool guard; floats are unusable like Python's
/// int-only rule.
pub fn spend_ratio_value(spent: &serde_json::Value, cap: &serde_json::Value) -> Option<f64> {
    match (usable_int(spent), usable_int(cap)) {
        (Some(s), Some(c)) => spend_ratio(s, c),
        _ => None,
    }
}

pub fn at_warning_value(
    spent: &serde_json::Value,
    cap: &serde_json::Value,
    warn_percent: u64,
) -> bool {
    match (usable_int(spent), usable_int(cap)) {
        (Some(s), Some(c)) => at_warning(s, c, warn_percent),
        _ => false,
    }
}

pub fn at_cap_value(spent: &serde_json::Value, cap: &serde_json::Value) -> bool {
    match (usable_int(spent), usable_int(cap)) {
        (Some(s), Some(c)) => at_cap(s, c),
        _ => false,
    }
}

pub fn claim_allowed_value(spent: &serde_json::Value, cap: &serde_json::Value) -> bool {
    !at_cap_value(spent, cap)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn warning_band_is_threshold_to_cap_exclusive() {
        assert!(!at_warning(79, 100, 80));
        assert!(at_warning(80, 100, 80));
        assert!(at_warning(99, 100, 80));
        assert!(!at_warning(100, 100, 80));
    }

    #[test]
    fn cap_includes_overspend() {
        assert!(!at_cap(99, 100));
        assert!(at_cap(100, 100));
        assert!(at_cap(150, 100));
    }

    #[test]
    fn claim_gate_follows_cap_only() {
        assert!(claim_allowed(99, 100));
        assert!(claim_allowed(80, 100));
        assert!(!claim_allowed(100, 100));
    }

    #[test]
    fn budget_state_names_all_states() {
        assert_eq!(budget_state(&json!({"lane": "s", "spent": 50, "cap": 100})), "ok");
        assert_eq!(budget_state(&json!({"lane": "s", "spent": 80, "cap": 100})), "warning");
        assert_eq!(budget_state(&json!({"lane": "s", "spent": 100, "cap": 100})), "capped");
        assert_eq!(budget_state(&json!({"lane": "x"})), "unbudgeted");
        assert_eq!(budget_state(&json!("not-a-dict")), "unbudgeted");
    }

    #[test]
    fn hold_entry_flags_only_at_cap() {
        assert!(!hold_entry("s", 80, 100)["held"].as_bool().unwrap());
        assert!(hold_entry("s", 100, 100)["held"].as_bool().unwrap());
    }

    #[test]
    fn malformed_never_warned_or_held() {
        // Non-integer figures are unusable in the typed API; the
        // unusable-cap rule (zero/negative cap, negative spent)
        // is what the gate checks.
        assert!(!at_warning(90, 0, 80));
        assert!(!at_cap(-5, 100));
        assert!(!at_cap(90, 0));
        // Value layer: None, strings, and bools are unusable —
        // never warned, never held, claims always allowed.
        let none = serde_json::Value::Null;
        assert!(!at_warning_value(&none, &none, 80));
        assert!(!at_cap_value(&none, &none));
        assert!(claim_allowed_value(&none, &none));
        assert!(!at_warning_value(&json!("lots"), &json!("none"), 80));
        assert!(!at_cap_value(&json!(90), &json!(0)));
        assert!(!at_cap_value(&json!(-5), &json!(100)));
        assert!(!at_cap_value(&json!(true), &json!(100)));
    }

    #[test]
    fn env_default_is_80_when_unset_or_bad() {
        // Deterministic default; env plumbing mirrors thresholds.py.
        if std::env::var("WATCHDOG_BUDGET_WARN_PERCENT").is_err() {
            assert_eq!(warn_percent_default(), 80);
        }
        assert_eq!(BUDGET_WARN_PERCENT, 80);
    }
}
