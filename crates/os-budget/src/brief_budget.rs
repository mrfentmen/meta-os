//! Brief-side budget records and lines (`os/intel/brief.py`,
//! OS-079/OS-103, as pinned by B20's brief tests).
//!
//! The full brief composers (`compose_template_brief`,
//! `generate_morning_brief`, `build_environment_record`'s
//! repo/bus/jobs quarters) are Hana's B10 territory. This module
//! ports exactly the budget quarters B20's assigned tests pin:
//! `environment_budget_record`, `with_memory_budget`,
//! `memory_budget_lines`, and the Budget line rule, so the budget
//! crate verifies its own contribution without reaching into
//! another batch's subtree.

use serde_json::{Map, Value};

fn system_now() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0)
}

fn usable_int(value: &Value) -> Option<i64> {
    match value {
        Value::Number(n) => n.as_i64(),
        _ => None,
    }
}

fn non_empty_str(value: &Value) -> Option<&str> {
    match value {
        Value::String(s) if !s.is_empty() => Some(s.as_str()),
        _ => None,
    }
}

/// The "budget" part of an environment record, read from a stated
/// budgets list. Returns `None` when no entry is usable, so the
/// caller leaves "budget" out and the Budget line reads not
/// reported. Mirrors `brief.environment_budget_record`.
pub fn environment_budget_record(
    budgets: &Value,
    lane: Option<&str>,
    now: Option<i64>,
) -> Option<Value> {
    let items = budgets.as_array()?;
    let stamp = now.unwrap_or_else(system_now);
    let wanted = match lane {
        Some(l) if !l.is_empty() => Some(l),
        _ => None,
    };
    for entry in items {
        let obj = match entry.as_object() {
            Some(o) => o,
            None => continue,
        };
        let entry_lane = match obj.get("lane").and_then(non_empty_str) {
            Some(l) => l,
            None => continue,
        };
        if let Some(w) = wanted {
            if entry_lane != w {
                continue;
            }
        }
        let spent = obj.get("spent").and_then(usable_int);
        let cap = obj.get("cap").and_then(usable_int);
        let remaining = obj.get("remaining").and_then(usable_int);
        let mut record = Map::new();
        record.insert("lane".to_string(), Value::String(entry_lane.to_string()));
        record.insert("as_of".to_string(), Value::Number(stamp.into()));
        if let (Some(s), Some(c)) = (spent, cap) {
            if s >= 0 && c > 0 {
                record.insert("spent".to_string(), Value::Number(s.into()));
                record.insert("cap".to_string(), Value::Number(c.into()));
            }
        }
        if let Some(rem) = remaining {
            record.insert("remaining".to_string(), Value::Number(rem.into()));
        }
        if record.contains_key("spent") || record.contains_key("remaining") {
            return Some(Value::Object(record));
        }
    }
    None
}

/// Fill a snapshot's `memory_budget` record (copy; never
/// mutates). Mirrors `brief.with_memory_budget`.
pub fn with_memory_budget(snapshot: &Value, now: Option<i64>) -> Value {
    let mut filled = match snapshot {
        Value::Object(_) => snapshot.clone(),
        _ => Value::Object(Map::new()),
    };
    if filled.get("memory_budget").is_some() {
        return filled;
    }
    let stamp = now.unwrap_or_else(system_now);
    let mut record = Map::new();
    record.insert("as_of".to_string(), Value::Number(stamp.into()));
    let mut added = false;
    if let Value::Object(map) = snapshot {
        if map.get("memory_down") == Some(&Value::Bool(true)) {
            record.insert("memory_down".to_string(), Value::Bool(true));
            added = true;
        } else {
            if let Some(Value::Array(decisions)) = map.get("settled_decisions") {
                let usable: Vec<Value> = decisions
                    .iter()
                    .filter_map(|d| match d {
                        Value::String(s) if !s.is_empty() => {
                            Some(Value::String(s.clone()))
                        }
                        _ => None,
                    })
                    .collect();
                // Ported oddity: a stated (even empty) decisions
                // list still marks the record added, exactly like
                // the Python caller.
                record.insert(
                    "settled_decisions".to_string(),
                    Value::Array(usable),
                );
                added = true;
            }
            if let Some(Value::Array(budgets)) = map.get("budgets") {
                let mut usable = Vec::new();
                for entry in budgets {
                    let obj = match entry.as_object() {
                        Some(o) => o,
                        None => continue,
                    };
                    let lane = match obj.get("lane").and_then(non_empty_str) {
                        Some(l) => l,
                        None => continue,
                    };
                    let spent = obj.get("spent").and_then(usable_int);
                    let cap = obj.get("cap").and_then(usable_int);
                    let remaining = obj.get("remaining").and_then(usable_int);
                    let mut built: Option<Map<String, Value>> = None;
                    if let (Some(s), Some(c)) = (spent, cap) {
                        if s >= 0 && c > 0 {
                            let mut m = Map::new();
                            m.insert("lane".to_string(), Value::String(lane.to_string()));
                            m.insert("spent".to_string(), Value::Number(s.into()));
                            m.insert("cap".to_string(), Value::Number(c.into()));
                            built = Some(m);
                        }
                    }
                    if built.is_none() {
                        if let (Some(rem), Some(c)) = (remaining, cap) {
                            if rem >= 0 && c > 0 {
                                let mut m = Map::new();
                                m.insert("lane".to_string(), Value::String(lane.to_string()));
                                m.insert("remaining".to_string(), Value::Number(rem.into()));
                                m.insert("cap".to_string(), Value::Number(c.into()));
                                built = Some(m);
                            }
                        }
                    }
                    if built.is_none() {
                        if let Some(rem) = remaining {
                            if rem >= 0 {
                                let mut m = Map::new();
                                m.insert("lane".to_string(), Value::String(lane.to_string()));
                                m.insert("remaining".to_string(), Value::Number(rem.into()));
                                built = Some(m);
                            }
                        }
                    }
                    let mut built = match built {
                        Some(b) => b,
                        None => continue,
                    };
                    if obj.get("held") == Some(&Value::Bool(true)) {
                        built.insert("held".to_string(), Value::Bool(true));
                    }
                    usable.push(Value::Object(built));
                }
                if !usable.is_empty() {
                    record.insert("budgets".to_string(), Value::Array(usable));
                    added = true;
                }
            }
        }
    }
    if added {
        filled["memory_budget"] = Value::Object(record);
    }
    filled
}

/// ET age label for one record.
pub fn age_label(as_of: Option<&Value>) -> String {
    match as_of.and_then(|v| v.as_i64()) {
        Some(ts) => format!(" (as of {})", render_et(ts)),
        None => " (snapshot time not reported)".to_string(),
    }
}

/// The settled-decisions line plus one spend-vs-budget line per
/// lane. Mirrors `brief.memory_budget_lines`.
pub fn memory_budget_lines(record: &Value) -> Vec<String> {
    let record = match record.as_object() {
        Some(o) => o.clone(),
        None => Map::new(),
    };
    let settled = if record.get("memory_down") == Some(&Value::Bool(true)) {
        "Settled decisions from memory: memory service down, so no settled decisions are shown"
            .to_string()
    } else if !record.contains_key("settled_decisions") {
        "Settled decisions from memory: not reported in this snapshot".to_string()
    } else {
        let decisions: Vec<&str> = match record.get("settled_decisions") {
            Some(Value::Array(items)) => items.iter().filter_map(non_empty_str).collect(),
            _ => Vec::new(),
        };
        if decisions.is_empty() {
            "Settled decisions from memory: none reported".to_string()
        } else {
            format!("Settled decisions from memory: {}", decisions.join("; "))
        }
    };
    let mut lines = vec![format!("{settled}{}", age_label(record.get("as_of")))];
    let mut budget_lines = Vec::new();
    if let Some(Value::Array(budgets)) = record.get("budgets") {
        for entry in budgets {
            let obj = match entry.as_object() {
                Some(o) => o,
                None => continue,
            };
            let lane = match obj.get("lane").and_then(non_empty_str) {
                Some(l) => l,
                None => continue,
            };
            let cap = obj.get("cap").and_then(usable_int);
            let spent = obj.get("spent").and_then(usable_int);
            let remaining = obj.get("remaining").and_then(usable_int);
            let text = if let (Some(s), Some(c)) = (spent, cap) {
                let rem = c - s;
                format!("Spend: {lane} lane: {s} of {c} budget ({rem} remaining)")
            } else if let (Some(rem), Some(c)) = (remaining, cap) {
                format!("Spend: {lane} lane: {rem} remaining of {c} cap")
            } else if let Some(rem) = remaining {
                format!("Spend: {lane} lane: {rem} remaining")
            } else {
                continue;
            };
            let age = age_label(obj.get("as_of").or_else(|| record.get("as_of")));
            let held = if obj.get("held") == Some(&Value::Bool(true)) {
                " — new claims held"
            } else {
                ""
            };
            budget_lines.push(format!("{text}{held}{age}"));
        }
    }
    if budget_lines.is_empty() {
        lines.push("Spend vs budget: not reported in this snapshot".to_string());
    } else {
        lines.extend(budget_lines);
    }
    lines
}

/// The Budget line quarter of `brief.environment_lines` (index 3).
/// A record carrying only this part still renders the other three
/// lines as not reported (composer-owned); this is the budget
/// quarter the B20 tests pin.
pub fn budget_line(budget: Option<&Value>, as_of: Option<&Value>) -> String {
    let age = age_label(as_of);
    let obj = match budget.and_then(|v| v.as_object()) {
        Some(o) => o,
        None => return "Budget: not reported in this snapshot".to_string(),
    };
    let lane = match obj.get("lane").and_then(non_empty_str) {
        Some(l) => l,
        None => return "Budget: not reported in this snapshot".to_string(),
    };
    let cap = obj.get("cap").and_then(usable_int);
    let mut remaining = obj.get("remaining").and_then(usable_int);
    if remaining.is_none() {
        if let (Some(spent), Some(c)) = (obj.get("spent").and_then(usable_int), cap) {
            remaining = Some(c - spent);
        }
    }
    match remaining {
        Some(rem) => {
            let cap_part = match cap {
                Some(c) => format!(" of {c} cap"),
                None => String::new(),
            };
            format!("Budget: {lane} lane: {rem} remaining{cap_part}{age}")
        }
        None => "Budget: not reported in this snapshot".to_string(),
    }
}

// --- America/New_York rendering (same rule as os-jobs brief_env) ---

fn civil_date(z: i64) -> (i64, i64, i64) {
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = (z - era * 146_097) as u64;
    let yoe = (doe - doe / 1_460 + doe / 36_524 - doe / 146_096) / 365;
    let mut y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as i64;
    let mut m = (mp + 3) as i64;
    if m > 12 {
        m -= 12;
        y += 1;
    }
    (y, m, d)
}

fn weekday(year: i64, month: i64, day: i64) -> i64 {
    let (y, m) = if month <= 2 {
        (year - 1, month + 12)
    } else {
        (year, month)
    };
    let k = y % 100;
    let j = y.div_euclid(100);
    let h = (day + (13 * (m + 1)) / 5 + k + k / 4 + j / 4 + 5 * j) % 7;
    (h + 5) % 7
}

fn ny_offset_seconds(ts: i64) -> i32 {
    let (year, m, d) = civil_date(ts.div_euclid(86_400) + 719_468);
    let march_first = weekday(year, 3, 1);
    let dst_start = 1 + ((7 - march_first) % 7) + 7;
    let nov_first = weekday(year, 11, 1);
    let dst_end = 1 + ((7 - nov_first) % 7);
    let after_start = (m > 3) || (m == 3 && d >= dst_start);
    let before_end = (m < 11) || (m == 11 && d < dst_end);
    if after_start && before_end {
        -4 * 3_600
    } else {
        -5 * 3_600
    }
}

/// `YYYY-MM-DD HH:MM ET` for a numeric timestamp.
pub fn render_et(ts: i64) -> String {
    let local = ts + ny_offset_seconds(ts) as i64;
    let (y, m, d) = civil_date(local.div_euclid(86_400) + 719_468);
    let secs = local.rem_euclid(86_400);
    format!(
        "{:04}-{:02}-{:02} {:02}:{:02} ET",
        y,
        m,
        d,
        secs / 3_600,
        (secs % 3_600) / 60
    )
}
