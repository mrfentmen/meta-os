//! Morning-path memory-depth caller (`os/intel/brief.py`, OS-092,
//! as pinned by `os/tests/test_intel_brief_memory_depth_caller.py`).
//!
//! Before this change no caller in the repo filled
//! `memory_depth`: a morning brief carried its Long-term memory
//! section only when the snapshot hand-stated a record. Now the
//! morning path fills the record first: aged decisions from the
//! snapshot's own stated aged_decisions list, due commitments
//! from its own stated due_commitments list, and fresh-agent
//! context from its own stated fresh_context list, with one
//! as_of stamp for the whole record. Dates are never guessed: a
//! dateless decision reads "original date not reported".
//!
//! The morning brief composer that consumes the record is Hana's
//! B10 territory; this module ports exactly the caller plus the
//! Long-term-memory line renderer the B17 tests pin.

use serde_json::{Map, Value};

fn system_now() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0)
}

fn non_empty_str(value: &Value) -> Option<&str> {
    match value {
        Value::String(s) if !s.is_empty() => Some(s.as_str()),
        _ => None,
    }
}

/// Fill a snapshot's `memory_depth` record (copy; never mutates).
/// Mirrors `brief.with_memory_depth`.
pub fn with_memory_depth(snapshot: &Value, now: Option<i64>) -> Value {
    let mut filled = match snapshot {
        Value::Object(_) => snapshot.clone(),
        _ => Value::Object(Map::new()),
    };
    if filled.get("memory_depth").is_some() {
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
            if let Some(Value::Array(aged)) = map.get("aged_decisions") {
                let mut usable = Vec::new();
                for entry in aged {
                    if let Value::Object(e) = entry {
                        let decision = match e.get("decision") {
                            Some(Value::String(s)) if !s.is_empty() => s.clone(),
                            _ => continue,
                        };
                        let mut built = Map::new();
                        built.insert("decision".to_string(), Value::String(decision));
                        if let Some(date) = e.get("original_date").and_then(non_empty_str) {
                            built.insert(
                                "original_date".to_string(),
                                Value::String(date.to_string()),
                            );
                        }
                        usable.push(Value::Object(built));
                    }
                }
                if !usable.is_empty() {
                    record.insert("aged_decisions".to_string(), Value::Array(usable));
                    added = true;
                }
            }
            if let Some(Value::Array(due)) = map.get("due_commitments") {
                let mut usable = Vec::new();
                for entry in due {
                    if let Value::Object(e) = entry {
                        let commitment = match e.get("commitment") {
                            Some(Value::String(s)) if !s.is_empty() => s.clone(),
                            _ => continue,
                        };
                        let mut built = Map::new();
                        built.insert(
                            "commitment".to_string(),
                            Value::String(commitment),
                        );
                        if let Some(date) = e.get("due").and_then(non_empty_str) {
                            built.insert("due".to_string(), Value::String(date.to_string()));
                        }
                        usable.push(Value::Object(built));
                    }
                }
                if !usable.is_empty() {
                    record.insert("due_commitments".to_string(), Value::Array(usable));
                    added = true;
                }
            }
            if let Some(Value::Array(context)) = map.get("fresh_context") {
                let usable: Vec<Value> = context
                    .iter()
                    .filter_map(|item| {
                        if let Value::String(s) = item {
                            if !s.is_empty() {
                                return Some(Value::String(s.clone()));
                            }
                        }
                        None
                    })
                    .collect();
                if !usable.is_empty() {
                    record.insert("fresh_context".to_string(), Value::Array(usable));
                    added = true;
                }
            }
        }
    }
    if added {
        filled["memory_depth"] = Value::Object(record);
    }
    filled
}

/// ET age label, same rule as the environment lines: numeric time
/// formats as "(as of YYYY-MM-DD HH:MM ET)", anything else reads
/// "(snapshot time not reported)".
pub fn age_label(as_of: Option<&Value>) -> String {
    match as_of.and_then(|v| v.as_i64()) {
        Some(ts) => format!(" (as of {})", render_et(ts)),
        None => " (snapshot time not reported)".to_string(),
    }
}

/// The long-term-memory lines for a `memory_depth` record.
/// Mirrors `brief.memory_depth_lines`.
pub fn memory_depth_lines(record: &Value) -> Vec<String> {
    let record = match record {
        Value::Object(_) => record.clone(),
        _ => Value::Object(Map::new()),
    };
    if record.get("memory_down") == Some(&Value::Bool(true)) {
        return vec![
            "Long-term memory: memory service down, so no aged decisions, due commitments, or fresh-agent context are shown"
                .to_string(),
        ];
    }
    let age = age_label(record.get("as_of"));
    let mut lines = Vec::new();
    let mut usable_aged = Vec::new();
    if let Some(Value::Array(aged)) = record.get("aged_decisions") {
        for entry in aged {
            if let Value::Object(e) = entry {
                let decision = match e.get("decision") {
                    Some(Value::String(s)) if !s.is_empty() => s,
                    _ => continue,
                };
                match e.get("original_date").and_then(non_empty_str) {
                    Some(date) => usable_aged.push(format!(
                        "Aged decision: {decision} (from {date})"
                    )),
                    None => usable_aged.push(format!(
                        "Aged decision: {decision} (original date not reported)"
                    )),
                }
            }
        }
    }
    if usable_aged.is_empty() {
        lines.push(format!("Aged decisions: none reported{age}"));
    } else {
        lines.extend(usable_aged.into_iter().map(|l| format!("{l}{age}")));
    }
    let mut usable_due = Vec::new();
    if let Some(Value::Array(due)) = record.get("due_commitments") {
        for entry in due {
            if let Value::Object(e) = entry {
                let commitment = match e.get("commitment") {
                    Some(Value::String(s)) if !s.is_empty() => s,
                    _ => continue,
                };
                match e.get("due").and_then(non_empty_str) {
                    Some(date) => usable_due.push(format!(
                        "Due commitment: {commitment} (due {date})"
                    )),
                    None => usable_due.push(format!(
                        "Due commitment: {commitment} (due date not reported)"
                    )),
                }
            }
        }
    }
    if usable_due.is_empty() {
        lines.push(format!("Due commitments: none reported{age}"));
    } else {
        lines.extend(usable_due.into_iter().map(|l| format!("{l}{age}")));
    }
    let usable_context: Vec<&str> = match record.get("fresh_context") {
        Some(Value::Array(items)) => items.iter().filter_map(non_empty_str).collect(),
        _ => Vec::new(),
    };
    if usable_context.is_empty() {
        lines.push(format!("Fresh-agent context: none reported{age}"));
    } else {
        lines.extend(
            usable_context
                .into_iter()
                .map(|item| format!("Fresh-agent context: {item}{age}")),
        );
    }
    lines
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
