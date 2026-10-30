//! Crate `os-budget` — Meta OS Rust rebuild skeleton (B00).
//!
//! Batch B20 — Budget & resource policy. Owner: Milo.
//! Source files this batch ports:
//! - `os/intel/brief_cost_check.py`
//! - `os/intel/budgets.py`
//! - `os/intel/cost_check.py`
//! - `os/intel/drills/budget_forecast.py`
//! - `os/intel/drills/budget_gate.py`
//! - `os/intel/drills/cgroup_limits.py`
//! - `os/mos/disk_audit.py`
//! - `os/tests/test_intel_brief_cost.py`
//! - `os/tests/test_intel_brief_environment_budget.py`
//! - `os/tests/test_intel_brief_memory_budget_caller.py`
//! - `os/tests/test_intel_budget_forecast.py`
//! - `os/tests/test_intel_budget_gate.py`
//! - `os/tests/test_intel_cost.py`
//!
//! Skeleton only: no logic yet. The Python/Node sources listed above are
//! the spec — port behavior, do not redesign. See BATCHES.md for the
//! compile gates and the parity rule.

// B20 port (Milo): the implementation below the B00 header ports the
// batch's seven source modules into this single lib.rs, in the same
// single-file shape as the B16-B19 ports. Sections, in order:
// value model, budgets, forecast, brief-measure helpers, cost_check,
// brief_cost_check, budget gate, cgroup limits, disk audit, tests.
//
// Cross-batch notes (read before refactoring): the forecast helpers
// mirror intel/forecast.py (B10, intel crate) because B20's own
// budget_forecast drill script calls them; the brief-measure helpers
// mirror the pure measurement path of intel/brief.py (B09/B10) and
// intel/spark_client.py (B11) because the two cost checks measure
// prompts through them; the budget-warning detector branch mirrors
// intel/watchdog.py (B21) and the spend-line helper mirrors the
// spend lines of brief.memory_budget_lines (B09/B10). When the
// owning crates land, os-budget should depend on them instead of
// carrying these mirrors. The mirrors are faithful ports, not
// redesigns, and the pinned tests below prove the numbers.

use std::collections::{BTreeMap, HashMap, HashSet};

// ---------------------------------------------------------------------------
// Value model: the dynamic dict shape Python passes around (job records,
// budget entries, snapshots, forecast entries). No serde (std-only), so
// this small enum carries the shapes the ports need.
// ---------------------------------------------------------------------------

/// A Python-like dynamic value: null, bool, int, float, string, list, dict.
/// Dicts keep insertion order (Python dict order matters for `repr`).
#[derive(Clone, Debug, PartialEq)]
pub enum Value {
    Null,
    Bool(bool),
    Int(i64),
    Float(f64),
    Str(String),
    List(Vec<Value>),
    Dict(Vec<(String, Value)>),
}

/// Build a string value.
pub fn v_str(s: &str) -> Value {
    Value::Str(s.to_string())
}

/// Build an int value.
pub fn v_int(i: i64) -> Value {
    Value::Int(i)
}

/// Build a dict value from (key, value) pairs, in order.
pub fn v_dict(pairs: Vec<(&str, Value)>) -> Value {
    Value::Dict(pairs.into_iter().map(|(k, v)| (k.to_string(), v)).collect())
}

impl Value {
    /// Dict lookup by key (first match), else None.
    pub fn get(&self, key: &str) -> Option<&Value> {
        match self {
            Value::Dict(pairs) => pairs.iter().find(|(k, _)| k == key).map(|(_, v)| v),
            _ => None,
        }
    }

    /// A stripped string, else None: empty text is not a value.
    /// Mirrors disk_audit._text.
    pub fn as_text(&self) -> Option<String> {
        match self {
            Value::Str(s) => {
                let t = s.trim();
                if t.is_empty() {
                    None
                } else {
                    Some(t.to_string())
                }
            }
            _ => None,
        }
    }

    /// A list of non-empty strings, else empty: never guesses a shape.
    /// Mirrors disk_audit._str_list.
    pub fn as_str_list(&self) -> Vec<String> {
        match self {
            Value::List(items) => items
                .iter()
                .filter_map(|item| match item {
                    Value::Str(s) if !s.is_empty() => Some(s.clone()),
                    _ => None,
                })
                .collect(),
            Value::Str(s) if !s.is_empty() => vec![s.clone()],
            _ => vec![],
        }
    }

    /// A usable integer: an int that is not a bool. Mirrors
    /// budgets._usable_int (Python bools are ints; Rust bools are not,
    /// so Bool is excluded here for the same reason).
    pub fn usable_int(&self) -> Option<i64> {
        match self {
            Value::Int(i) => Some(*i),
            _ => None,
        }
    }

    /// A usable number: int or float, never a bool. Mirrors
    /// forecast._usable_number.
    pub fn usable_number(&self) -> Option<f64> {
        match self {
            Value::Int(i) => Some(*i as f64),
            Value::Float(f) => Some(*f),
            _ => None,
        }
    }

    /// Format like Python `str()` for numbers and strings: ints plain,
    /// floats with a `.0` when integral (Python repr of 240.0 is
    /// "240.0", Rust's Display would print "240").
    pub fn py_num_str(&self) -> String {
        match self {
            Value::Int(i) => i.to_string(),
            Value::Float(f) => py_float_str(*f),
            Value::Str(s) => s.clone(),
            Value::Bool(true) => "True".to_string(),
            Value::Bool(false) => "False".to_string(),
            Value::Null => "None".to_string(),
            other => other.py_repr(),
        }
    }

    /// Format like Python `repr()`: dicts `{'k': v, ...}` in order,
    /// strings single-quoted with Python escapes, True/False/None.
    pub fn py_repr(&self) -> String {
        match self {
            Value::Null => "None".to_string(),
            Value::Bool(true) => "True".to_string(),
            Value::Bool(false) => "False".to_string(),
            Value::Int(i) => i.to_string(),
            Value::Float(f) => py_float_str(*f),
            Value::Str(s) => py_str_repr(s),
            Value::List(items) => {
                let inner: Vec<String> = items.iter().map(|v| v.py_repr()).collect();
                format!("[{}]", inner.join(", "))
            }
            Value::Dict(pairs) => {
                let inner: Vec<String> = pairs
                    .iter()
                    .map(|(k, v)| format!("{}: {}", py_str_repr(k), v.py_repr()))
                    .collect();
                format!("{{{}}}", inner.join(", "))
            }
        }
    }
}

/// Python float repr: integral floats print with `.0`; other floats
/// print via Rust Display (shortest round-trip, matching Python repr
/// for the small magnitudes this crate handles).
pub fn py_float_str(f: f64) -> String {
    if f.is_finite() && f.fract() == 0.0 {
        format!("{:.1}", f)
    } else {
        format!("{}", f)
    }
}

/// Python string repr: single quotes, backslash and quote escaped,
/// plus \n \r \t escapes. Printable Unicode passes through, as in
/// Python 3 repr.
pub fn py_str_repr(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('\'');
    for ch in s.chars() {
        match ch {
            '\\' => out.push_str("\\\\"),
            '\'' => out.push_str("\\'"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            _ => out.push(ch),
        }
    }
    out.push('\'');
    out
}

// ---------------------------------------------------------------------------
// budgets (os/intel/budgets.py, OS-085, Milo)
// ---------------------------------------------------------------------------

/// One env-overridable integer, falling back on bad input: blank,
/// unparseable, or out-of-range values return the default rather
/// than raising. Mirrors budgets._env_int (and thresholds._env_int).
/// Pure over the raw string so tests never mutate the environment.
pub fn env_int_value(raw: Option<&str>, default: i64, minimum: i64, maximum: i64) -> i64 {
    let raw = match raw {
        None => return default,
        Some(r) => r.trim(),
    };
    if raw.is_empty() {
        return default;
    }
    let value: i64 = match raw.parse() {
        Ok(v) => v,
        Err(_) => return default,
    };
    if value < minimum || value > maximum {
        return default;
    }
    value
}

/// Budget warning threshold (OS-085): warn when a lane has spent
/// this percentage of its cap. Env: WATCHDOG_BUDGET_WARN_PERCENT,
/// range 1-100. Python computes this once at import; this reads the
/// environment per call, which is equivalent for every caller here.
pub fn budget_warn_percent() -> i64 {
    env_int_value(
        std::env::var("WATCHDOG_BUDGET_WARN_PERCENT").ok().as_deref(),
        80,
        1,
        100,
    )
}

/// Spent as a fraction of cap, or None when unusable: spent or cap
/// is not a usable integer, cap is zero or negative, or spent is
/// negative. A lane with no usable cap has no ratio.
pub fn spend_ratio(spent: &Value, cap: &Value) -> Option<f64> {
    let spent = spent.usable_int()?;
    let cap = cap.usable_int()?;
    if cap <= 0 || spent < 0 {
        return None;
    }
    Some(spent as f64 / cap as f64)
}

/// True when spent has reached the warning threshold but not cap.
/// The warning band is [warn_percent, 100%) of cap: at cap the lane
/// is held, not warned.
pub fn at_warning(spent: &Value, cap: &Value, warn_percent: Option<i64>) -> bool {
    let warn_percent = warn_percent.unwrap_or_else(budget_warn_percent);
    let ratio = match spend_ratio(spent, cap) {
        Some(r) => r,
        None => return false,
    };
    let spent_i = spent.usable_int().unwrap_or(0);
    let cap_i = cap.usable_int().unwrap_or(0);
    ratio >= warn_percent as f64 / 100.0 && spent_i < cap_i
}

/// True when spent has reached or passed cap. Overspend counts.
pub fn at_cap(spent: &Value, cap: &Value) -> bool {
    if spend_ratio(spent, cap).is_none() {
        return false;
    }
    spent.usable_int().unwrap_or(0) >= cap.usable_int().unwrap_or(0)
}

/// The queue gate (OS-085): False only when the lane is at cap.
/// Unbudgeted lanes always allow claims.
pub fn claim_allowed(spent: &Value, cap: &Value) -> bool {
    !at_cap(spent, cap)
}

/// One of "warning", "capped", "ok", or "unbudgeted" for a dict
/// entry; a non-dict is unbudgeted.
pub fn budget_state(entry: &Value) -> &'static str {
    match entry {
        Value::Dict(_) => {
            let spent = entry.get("spent").cloned().unwrap_or(Value::Null);
            let cap = entry.get("cap").cloned().unwrap_or(Value::Null);
            if at_cap(&spent, &cap) {
                "capped"
            } else if at_warning(&spent, &cap, None) {
                "warning"
            } else if spend_ratio(&spent, &cap).is_some() {
                "ok"
            } else {
                "unbudgeted"
            }
        }
        _ => "unbudgeted",
    }
}

/// The budget entries a snapshot carries, as usable dicts: the
/// snapshot key is "budgets", a list of OS-079-shaped entries.
/// Non-list values, non-dict items, and entries without a
/// non-empty lane name are skipped, never guessed.
pub fn budgets_from_snapshot(snapshot: &Value) -> Vec<Value> {
    let items = match snapshot.get("budgets") {
        Some(Value::List(items)) => items,
        _ => return vec![],
    };
    items
        .iter()
        .filter(|entry| match entry {
            Value::Dict(_) => matches!(entry.get("lane"), Some(Value::Str(s)) if !s.is_empty()),
            _ => false,
        })
        .cloned()
        .collect()
}

/// An OS-079 budgets entry for a lane, with its hold flag set.
/// A lane under cap gets held False, so the same builder serves
/// both states.
pub fn hold_entry(lane: &str, spent: Value, cap: Value) -> Value {
    let held = at_cap(&spent, &cap);
    v_dict(vec![
        ("lane", v_str(lane)),
        ("spent", spent),
        ("cap", cap),
        ("held", Value::Bool(held)),
    ])
}

// ---------------------------------------------------------------------------
// forecast (mirrors os/intel/forecast.py, OS-091, Milo)
// Canonical home is B10's intel crate; this faithful local copy exists
// because B20's own budget_forecast drill script calls these functions.
// ---------------------------------------------------------------------------

/// Hours in a forecast day.
pub const FORECAST_DAY_HOURS: i64 = 24;
/// Confidence is low under this many elapsed hours.
pub const FORECAST_LOW_BELOW: i64 = 4;
/// Confidence is high at or above this many elapsed hours.
pub const FORECAST_HIGH_AT: i64 = 12;

/// Projected end-of-day spend, or None when unprojectable: spent
/// negative or not a number, elapsed hours not positive, or day
/// hours not positive. Elapsed hours at or past the full day
/// project to spent itself.
pub fn project_end_of_day(spent: &Value, elapsed_hours: &Value, day_hours: &Value) -> Option<f64> {
    let spent = spent.usable_number()?;
    if spent < 0.0 {
        return None;
    }
    let elapsed = elapsed_hours.usable_number()?;
    if elapsed <= 0.0 {
        return None;
    }
    let day = day_hours.usable_number()?;
    if day <= 0.0 {
        return None;
    }
    if elapsed >= day {
        return Some(spent);
    }
    Some(spent * day / elapsed)
}

/// The confidence word for a forecast, from elapsed hours alone:
/// low under 4, medium from 4 to under 12, high at 12 or more,
/// "unknown" for unusable elapsed hours.
pub fn confidence_for(elapsed_hours: &Value) -> &'static str {
    let elapsed = match elapsed_hours.usable_number() {
        Some(e) if e > 0.0 => e,
        _ => return "unknown",
    };
    if elapsed < FORECAST_LOW_BELOW as f64 {
        "low"
    } else if elapsed < FORECAST_HIGH_AT as f64 {
        "medium"
    } else {
        "high"
    }
}

/// Format elapsed/day hours the way forecast_entry's basis does:
/// integral floats print as ints ("8"), ints print plain.
pub fn format_hours(value: &Value) -> String {
    match value {
        Value::Float(f) if f.fract() == 0.0 => format!("{}", *f as i64),
        Value::Int(i) => i.to_string(),
        other => other.py_num_str(),
    }
}

/// One lane's forecast entry: lane, spent, cap, projected
/// end-of-day spend (float), over_cap, confidence, basis. None
/// when it cannot be made: no usable lane, cap, spend, or
/// projection.
#[derive(Clone, Debug, PartialEq)]
pub struct ForecastEntry {
    pub lane: String,
    pub spent: Value,
    pub cap: Value,
    pub projected: f64,
    pub over_cap: bool,
    pub confidence: String,
    pub basis: String,
}

pub fn forecast_entry(
    lane: &Value,
    spent: &Value,
    cap: &Value,
    elapsed_hours: &Value,
    day_hours: &Value,
) -> Option<ForecastEntry> {
    let lane_s = match lane {
        Value::Str(s) if !s.is_empty() => s.clone(),
        _ => return None,
    };
    let cap_n = cap.usable_number()?;
    if cap_n <= 0.0 {
        return None;
    }
    let spent_n = spent.usable_number()?;
    if spent_n < 0.0 {
        return None;
    }
    let projected = project_end_of_day(spent, elapsed_hours, day_hours)?;
    let confidence = confidence_for(elapsed_hours).to_string();
    let basis = format!(
        "based on {} hours of ledger in a {}-hour day",
        format_hours(elapsed_hours),
        format_hours(day_hours)
    );
    Some(ForecastEntry {
        lane: lane_s,
        spent: spent.clone(),
        cap: cap.clone(),
        projected,
        over_cap: projected > cap_n,
        confidence,
        basis,
    })
}

/// Plain brief lines for a list of forecast entries. Each usable
/// entry yields one line: lane, spent, cap, projected spend
/// rounded DOWN to a whole number, basis, confidence, and the
/// verdict ("breach expected before end of day" or "within cap").
/// Unusable entries are skipped; an empty input yields no lines.
/// Lines are not bullets, so the BRF-007 trim keeps them.
pub fn forecast_lines(entries: &Value) -> Vec<String> {
    let items = match entries {
        Value::List(items) => items,
        _ => return vec![],
    };
    let mut lines = Vec::new();
    for entry in items {
        if !matches!(entry, Value::Dict(_)) {
            continue;
        }
        let day = entry
            .get("day_hours")
            .cloned()
            .unwrap_or(Value::Int(FORECAST_DAY_HOURS));
        let forecast = match forecast_entry(
            &entry.get("lane").cloned().unwrap_or(Value::Null),
            &entry.get("spent").cloned().unwrap_or(Value::Null),
            &entry.get("cap").cloned().unwrap_or(Value::Null),
            &entry.get("elapsed_hours").cloned().unwrap_or(Value::Null),
            &day,
        ) {
            Some(f) => f,
            None => continue,
        };
        // Python int() truncates toward zero; projections here are
        // never negative, so truncation is a floor.
        let projected = forecast.projected as i64;
        let verdict = if forecast.over_cap {
            "breach expected before end of day"
        } else {
            "within cap"
        };
        lines.push(format!(
            "Budget forecast for lane {}: {} spent of {} cap, projected {} by end of day, {} ({} confidence) - {}.",
            forecast.lane,
            forecast.spent.py_num_str(),
            forecast.cap.py_num_str(),
            projected,
            forecast.basis,
            forecast.confidence,
            verdict
        ));
    }
    lines
}

/// "pause", "resume", or None for one job in one lane state.
/// Pause only when the job is running, low priority, and the lane
/// is at warning. Resume only when the job is paused and the lane
/// is back below warning ("ok" or "unbudgeted"). Anything else
/// yields None, never a guessed action.
pub fn preempt_decision(job: &Value, lane_state: &str) -> Option<&'static str> {
    if !matches!(job, Value::Dict(_)) {
        return None;
    }
    let status = job.get("status").and_then(|v| match v {
        Value::Str(s) => Some(s.as_str()),
        _ => None,
    });
    let priority = job.get("priority").and_then(|v| match v {
        Value::Str(s) => Some(s.as_str()),
        _ => None,
    });
    if status == Some("running") && priority == Some("low") && lane_state == "warning" {
        return Some("pause");
    }
    if status == Some("paused") && (lane_state == "ok" || lane_state == "unbudgeted") {
        return Some("resume");
    }
    None
}

/// A journal record for a pause or resume, nothing more: job,
/// lane, action, reason in plain words.
pub fn preempt_record(job_id: &str, lane: &str, action: &str, reason: &str) -> Value {
    v_dict(vec![
        ("job", v_str(job_id)),
        ("lane", v_str(lane)),
        ("action", v_str(action)),
        ("reason", v_str(reason)),
    ])
}

// ---------------------------------------------------------------------------
// Brief-measure helpers (mirror the pure measurement path of
// intel/brief.py and intel/spark_client.py; canonical homes are
// B09/B10 and B11). Only the core morning path is ported: the
// optional-record sections (previous_brief, memory_budget, daily,
// memory_depth, federation, held_decisions, source_pointers,
// priority_order, blocked_contacts, screenshots) and the WDG-028
// watchdog status line are not, because no B20 pinned case carries
// them. The WDG-028 line only fires for severity-carrying alerts;
// B20's snapshots carry none, so omitting it changes nothing here.
// ---------------------------------------------------------------------------

/// Word budgets per brief kind (brief.BRIEF_BUDGETS).
pub fn brief_budget(kind: &str) -> i64 {
    match kind {
        "onjoin" => 150,
        "ondemand" => 300,
        _ => 220,
    }
}

/// Rough token estimate (~4 chars/token) for pre-call costing.
/// Mirrors spark_client._estimate_tokens: 0 for empty text, else
/// max(1, ceil(len/4)). Python len() counts characters, not
/// bytes, so this counts chars too: dispatch.md carries em
/// dashes (3 bytes each), and a byte count overestimates by
/// 11 tokens on the INT-007 dispatch row.
pub fn estimate_tokens(text: &str) -> i64 {
    if text.is_empty() {
        return 0;
    }
    ((text.chars().count() as f64 / 4.0).ceil() as i64).max(1)
}

/// (nick, text) for a store entry dict or a bus string.
/// Mirrors brief._message_parts.
pub fn message_parts(message: &Value) -> (String, String) {
    match message {
        Value::Dict(_) => (
            match message.get("nick") {
                Some(Value::Str(s)) => s.clone(),
                _ => String::new(),
            },
            match message.get("text") {
                Some(Value::Str(s)) => s.clone(),
                _ => String::new(),
            },
        ),
        Value::Str(s) => match s.split_once(": ") {
            Some((nick, text)) => (nick.to_string(), text.to_string()),
            None => (String::new(), s.clone()),
        },
        _ => (String::new(), String::new()),
    }
}

/// Match the decision marker regex
/// `^\s*(DONE|BLOCKED|DECISION)\s*:\s*(.+?)\s*$` (case-insensitive)
/// and return (kind-lowercased, text). Hand-rolled: no regex crate.
pub fn match_decision(text: &str) -> Option<(String, String)> {
    let rest = text.trim_start();
    let word_end = rest.find(|c: char| !c.is_ascii_alphabetic()).unwrap_or(rest.len());
    let (word, after) = rest.split_at(word_end);
    let kind = word.to_ascii_lowercase();
    if kind != "done" && kind != "blocked" && kind != "decision" {
        return None;
    }
    let after = after.trim_start();
    let after = after.strip_prefix(':')?;
    let captured = after.trim();
    if captured.is_empty() {
        return None;
    }
    Some((kind, captured.to_string()))
}

/// Decisions from message markers, in snapshot order:
/// {kind, text, nick, index}. Mirrors brief.extract_decisions.
pub fn extract_decisions(snapshot: &Value) -> Vec<Value> {
    let messages = match snapshot.get("messages") {
        Some(Value::List(m)) => m.clone(),
        _ => vec![],
    };
    let mut out = Vec::new();
    for (index, message) in messages.iter().enumerate() {
        let (nick, text) = message_parts(message);
        if let Some((kind, text)) = match_decision(&text) {
            out.push(v_dict(vec![
                ("kind", v_str(&kind)),
                ("text", v_str(&text)),
                ("nick", v_str(&nick)),
                ("index", Value::Int(index as i64)),
            ]));
        }
    }
    out
}

/// Claimed jobs mapped claim nick -> jobs, in first-claim order:
/// {nick, jobs: [{id, title, last_progress_age}]}. Only jobs whose
/// status is exactly "claimed" count. Mirrors brief.extract_owners.
pub fn extract_owners(snapshot: &Value) -> Vec<Value> {
    let jobs = match snapshot.get("jobs") {
        Some(Value::List(j)) => j.clone(),
        _ => vec![],
    };
    let mut owners: Vec<Value> = Vec::new();
    let mut index_by_nick: HashMap<String, usize> = HashMap::new();
    for job in &jobs {
        if !matches!(job, Value::Dict(_)) {
            continue;
        }
        let nick = match job.get("claim") {
            Some(Value::Str(s)) if !s.is_empty() => s.clone(),
            _ => continue,
        };
        if job.get("status") != Some(&Value::Str("claimed".to_string())) {
            continue;
        }
        let age = job
            .get("last_progress_at")
            .cloned()
            .unwrap_or_else(|| job.get("claimed_at").cloned().unwrap_or(Value::Null));
        let job_entry = v_dict(vec![
            ("id", job.get("id").cloned().unwrap_or(v_str(""))),
            ("title", job.get("title").cloned().unwrap_or(v_str(""))),
            ("last_progress_age", age),
        ]);
        if let Some(&i) = index_by_nick.get(&nick) {
            if let Value::Dict(pairs) = &mut owners[i] {
                if let Some((_, Value::List(jobs))) =
                    pairs.iter_mut().find(|(k, _)| k.as_str() == "jobs")
                {
                    jobs.push(job_entry);
                }
            }
        } else {
            index_by_nick.insert(nick.clone(), owners.len());
            owners.push(v_dict(vec![
                ("nick", v_str(&nick)),
                ("jobs", Value::List(vec![job_entry])),
            ]));
        }
    }
    owners
}

/// Every blocked job, with its reason verbatim: {id, title, reason}.
/// Mirrors brief.extract_blocked.
pub fn extract_blocked(snapshot: &Value) -> Vec<Value> {
    let jobs = match snapshot.get("jobs") {
        Some(Value::List(j)) => j.clone(),
        _ => vec![],
    };
    let mut out = Vec::new();
    for job in &jobs {
        if !matches!(job, Value::Dict(_)) {
            continue;
        }
        if job.get("status") != Some(&Value::Str("blocked".to_string())) {
            continue;
        }
        let reason = match job.get("note") {
            Some(Value::Str(s)) => s.clone(),
            _ => String::new(),
        };
        out.push(v_dict(vec![
            ("id", job.get("id").cloned().unwrap_or(v_str(""))),
            ("title", job.get("title").cloned().unwrap_or(v_str(""))),
            ("reason", v_str(&reason)),
        ]));
    }
    out
}

/// Open watchdog alerts, by reference: {id, summary}. An alert with
/// no summary falls back to the first line of its explanation; an
/// alert with neither renders an empty summary. Alerts with no id
/// are skipped. Mirrors brief.extract_watch_items.
pub fn extract_watch_items(snapshot: &Value) -> Vec<Value> {
    let alerts = match snapshot.get("alerts") {
        Some(Value::List(a)) => a.clone(),
        _ => vec![],
    };
    let mut out = Vec::new();
    for alert in &alerts {
        if !matches!(alert, Value::Dict(_)) {
            continue;
        }
        let id = match alert.get("id") {
            Some(Value::Str(s)) if !s.is_empty() => s.clone(),
            _ => continue,
        };
        let summary = match alert.get("summary") {
            Some(Value::Str(s)) if !s.trim().is_empty() => s.clone(),
            _ => match alert.get("explanation") {
                Some(Value::Str(e)) if !e.trim().is_empty() => {
                    e.lines().next().unwrap_or("").trim().to_string()
                }
                _ => String::new(),
            },
        };
        out.push(v_dict(vec![("id", v_str(&id)), ("summary", v_str(&summary))]));
    }
    out
}

/// The window line a brief opens with. Mirrors brief._window_line:
/// a stated dict window renders its cap record; a stated string
/// window renders verbatim; a window_start renders the from-onward
/// line; otherwise "not stated".
pub fn window_line(snapshot: &Value) -> String {
    match snapshot.get("source_window") {
        Some(Value::Dict(_)) => {
            let w = snapshot.get("source_window").unwrap();
            let max_hours = match w.get("max_hours") {
                Some(Value::Float(f)) if f.fract() == 0.0 => (*f as i64).to_string(),
                Some(v) => v.py_num_str(),
                None => "None".to_string(),
            };
            let max_messages = w
                .get("max_messages")
                .map(|v| v.py_num_str())
                .unwrap_or_else(|| "None".to_string());
            let kept = w
                .get("messages_kept")
                .map(|v| v.py_num_str())
                .unwrap_or_else(|| "None".to_string());
            let dropped = w
                .get("messages_dropped")
                .map(|v| v.py_num_str())
                .unwrap_or_else(|| "None".to_string());
            format!(
                "Window: last {} messages or last {} hours, {} kept, {} dropped",
                max_messages, max_hours, kept, dropped
            )
        }
        Some(Value::Str(s)) if !s.is_empty() => format!("Window: {}", s),
        _ => match snapshot.get("window_start") {
            Some(Value::Str(s)) if !s.is_empty() => format!(
                "Window: from {} onward. Earlier history is not in this window.",
                s
            ),
            _ => "Window: not stated in this snapshot".to_string(),
        },
    }
}

/// BRF-007 rewrite pass: cut a brief to its word budget. Drops
/// bullet lines from the end first; if still over budget with no
/// bullets left, truncates by words with a " (trimmed)" tail.
/// A brief already within budget returns unchanged.
pub fn trim_to_budget(text: &str, budget: i64) -> String {
    let word_count = |t: &str| t.split_whitespace().count() as i64;
    if word_count(text) <= budget {
        return text.to_string();
    }
    let mut lines: Vec<String> = text.split('\n').map(|s| s.to_string()).collect();
    while word_count(&lines.join("\n")) > budget {
        let last_bullet = lines.iter().rposition(|l| l.starts_with("- "));
        match last_bullet {
            Some(i) => {
                lines.remove(i);
            }
            None => break,
        }
    }
    let trimmed = lines.join("\n");
    if word_count(&trimmed) > budget {
        let words: Vec<&str> = trimmed.split_whitespace().collect();
        let keep = (budget - 1).max(0) as usize;
        let mut out = words[..keep.min(words.len())].join(" ");
        out.push_str(" (trimmed)");
        out
    } else {
        trimmed
    }
}

/// Cap a snapshot's source window (BRF-023): last 500 messages or
/// last 24 hours, whichever is smaller. Messages without a numeric
/// ts are kept (they cannot be aged out by time, only by the count
/// cap). Returns a new snapshot dict with the capped messages and
/// a source_window record naming the cap values applied. `now_secs`
/// is the caller's "now" (Python uses time.time() when None).
pub fn cap_snapshot_window(
    snapshot: &Value,
    max_messages: i64,
    max_hours: i64,
    now_secs: f64,
) -> Value {
    let mut messages: Vec<Value> = match snapshot.get("messages") {
        Some(Value::List(m)) => m.clone(),
        _ => vec![],
    };
    let mut dropped: i64 = 0;
    let cutoff = now_secs - max_hours as f64 * 3600.0;
    let kept: Vec<Value> = messages
        .iter()
        .filter(|m| {
            let ts = match m {
                Value::Dict(_) => m.get("ts").and_then(|v| v.usable_number()),
                _ => None,
            };
            match ts {
                Some(t) => t >= cutoff,
                None => true,
            }
        })
        .cloned()
        .collect();
    dropped += messages.len() as i64 - kept.len() as i64;
    messages = kept;
    if messages.len() as i64 > max_messages {
        dropped += messages.len() as i64 - max_messages;
        messages = messages[(messages.len() as i64 - max_messages) as usize..].to_vec();
    }
    if let Some(Value::Dict(_)) = snapshot.get("source_window") {
        if let Some(Value::Int(prior)) =
            snapshot.get("source_window").and_then(|w| w.get("messages_dropped"))
        {
            dropped += *prior;
        }
    }
    let mut pairs: Vec<(String, Value)> = match snapshot {
        Value::Dict(p) => p.clone(),
        _ => vec![],
    };
    pairs.retain(|(k, _)| k != "messages" && k != "source_window");
    pairs.push(("messages".to_string(), Value::List(messages.clone())));
    pairs.push((
        "source_window".to_string(),
        v_dict(vec![
            ("max_messages", Value::Int(max_messages)),
            ("max_hours", Value::Int(max_hours)),
            ("messages_kept", Value::Int(messages.len() as i64)),
            ("messages_dropped", Value::Int(dropped)),
        ]),
    ));
    Value::Dict(pairs)
}

/// The core morning template brief (BRF-008), for snapshots without
/// the optional records listed in the section header. Every fact
/// comes from the extractors; nothing is invented. The output is
/// marked TEMPLATE in its first line.
pub fn morning_template_brief(snapshot: &Value, kind: &str) -> String {
    let kind = if matches!(kind, "morning" | "onjoin" | "ondemand") {
        kind
    } else {
        "morning"
    };
    if kind == "onjoin" {
        // On-join rendering lives in brief.py's onjoin path; B20's
        // pinned cases never use it. Keep the morning shape's
        // first line contract rather than inventing on-join lines.
        return format!("TEMPLATE\n\n{}\n", window_line(snapshot));
    }
    let mut lines: Vec<String> = vec!["TEMPLATE".to_string(), window_line(snapshot)];
    lines.push(String::new());
    lines.push("Decisions".to_string());
    let decisions = extract_decisions(snapshot);
    if decisions.is_empty() {
        lines.push("Nothing reported in this window".to_string());
    } else {
        for d in &decisions {
            let kind_s = d.get("kind").map(|v| v.py_num_str()).unwrap_or_default();
            let text = d.get("text").map(|v| v.py_num_str()).unwrap_or_default();
            lines.push(format!("- {}: {}", kind_s, text));
        }
    }
    lines.push(String::new());
    lines.push("In flight".to_string());
    let jobs = match snapshot.get("jobs") {
        Some(Value::List(j)) => j.clone(),
        _ => vec![],
    };
    let in_flight: Vec<&Value> = jobs
        .iter()
        .filter(|j| {
            matches!(j, Value::Dict(_))
                && matches!(j.get("status"), Some(Value::Str(s)) if s == "open" || s == "claimed")
        })
        .collect();
    if in_flight.is_empty() {
        lines.push("Nothing reported in this window".to_string());
    } else {
        for job in in_flight {
            let id = job.get("id").map(|v| v.py_num_str()).unwrap_or_default();
            let title = job.get("title").map(|v| v.py_num_str()).unwrap_or_default();
            let status = job.get("status").map(|v| v.py_num_str()).unwrap_or_default();
            lines.push(format!("- {} {} ({})", id, title, status));
        }
    }
    lines.push(String::new());
    lines.push("Owners".to_string());
    let owners = extract_owners(snapshot);
    if owners.is_empty() {
        lines.push("Nothing reported in this window".to_string());
    } else {
        for owner in &owners {
            let nick = owner.get("nick").map(|v| v.py_num_str()).unwrap_or_default();
            let titles: Vec<String> = match owner.get("jobs") {
                Some(Value::List(js)) => js
                    .iter()
                    .map(|j| j.get("title").map(|v| v.py_num_str()).unwrap_or_default())
                    .collect(),
                _ => vec![],
            };
            lines.push(format!("- {}: {}", nick, titles.join(", ")));
        }
    }
    lines.push(String::new());
    lines.push("Blocked and why".to_string());
    let blocked = extract_blocked(snapshot);
    if blocked.is_empty() {
        lines.push("Nothing blocked in this window".to_string());
    } else {
        for job in &blocked {
            let id = job.get("id").map(|v| v.py_num_str()).unwrap_or_default();
            let title = job.get("title").map(|v| v.py_num_str()).unwrap_or_default();
            let reason = job.get("reason").map(|v| v.py_num_str()).unwrap_or_default();
            lines.push(format!("- {} {}: {}", id, title, reason));
        }
    }
    lines.push(String::new());
    lines.push("Watch items".to_string());
    let watch_items = extract_watch_items(snapshot);
    if watch_items.is_empty() {
        lines.push("Nothing to watch in this window".to_string());
    } else {
        for item in &watch_items {
            let id = item.get("id").map(|v| v.py_num_str()).unwrap_or_default();
            let summary = item.get("summary").map(|v| v.py_num_str()).unwrap_or_default();
            lines.push(format!("- {}: {}", id, summary));
        }
    }
    redact_secrets(&format!("{}\n", lines.join("\n")))
}

/// Spark composer with template fallback and budget (BRF-007),
/// client=None path only: the template brief, trimmed to the kind
/// budget. (The live-Spark path needs a client; B20's pinned cases
/// never take it.)
pub fn compose_brief_no_client(snapshot: &Value, kind: &str, now_secs: f64) -> String {
    let capped = cap_snapshot_window(snapshot, 500, 24, now_secs);
    let kind = if matches!(kind, "morning" | "onjoin" | "ondemand") {
        kind
    } else {
        "morning"
    };
    let budget = brief_budget(kind);
    trim_to_budget(&morning_template_brief(&capped, kind), budget)
}

/// Strip credential-shaped strings from brief text (BRF-014),
/// replacing each match with "`[redacted]`". Patterns: GitHub
/// tokens, OpenAI-style sk- keys, AWS access key ids, Bearer
/// tokens, and named key/token/secret/password assignments.
/// Hand-rolled scanning (std-only, no regex crate). Plain hex
/// strings are deliberately NOT redacted, so commit hashes survive.
pub fn redact_secrets(text: &str) -> String {
    if text.is_empty() {
        return text.to_string();
    }
    let bytes = text.as_bytes();
    let mut out = String::with_capacity(text.len());
    let mut i = 0usize;
    let is_alnum = |b: u8| b.is_ascii_alphanumeric();
    let is_token_char = |b: u8| b.is_ascii_alphanumeric() || b == b'.' || b == b'_' || b == b'-';
    while i < bytes.len() {
        let rest = &text[i..];
        // GitHub tokens: ghp_/gho_/ghu_/ghs_/ghr_ + 20+ alnum.
        let mut matched: Option<usize> = None;
        for prefix in ["ghp_", "gho_", "ghu_", "ghs_", "ghr_"] {
            if rest.starts_with(prefix) {
                let mut j = prefix.len();
                while j < rest.len() && is_alnum(rest.as_bytes()[j]) {
                    j += 1;
                }
                if j - prefix.len() >= 20 {
                    matched = Some(j);
                }
                break;
            }
        }
        if matched.is_none() && rest.starts_with("github_pat_") {
            let mut j = "github_pat_".len();
            while j < rest.len() && is_token_char(rest.as_bytes()[j]) {
                j += 1;
            }
            if j - "github_pat_".len() >= 20 {
                matched = Some(j);
            }
        }
        if matched.is_none() && rest.starts_with("sk-") {
            let mut j = 3;
            while j < rest.len() && is_alnum(rest.as_bytes()[j]) {
                j += 1;
            }
            if j - 3 >= 20 {
                matched = Some(j);
            }
        }
        if matched.is_none() && rest.starts_with("AKIA") {
            let mut j = 4;
            while j < rest.len() && rest.as_bytes()[j].is_ascii_uppercase()
                || (j < rest.len() && rest.as_bytes()[j].is_ascii_digit())
            {
                j += 1;
            }
            if j - 4 == 16 {
                matched = Some(j);
            }
        }
        if matched.is_none() && rest.starts_with("Bearer ") {
            let mut j = "Bearer ".len();
            while j < rest.len() && is_token_char(rest.as_bytes()[j]) {
                j += 1;
            }
            if j - "Bearer ".len() >= 10 {
                matched = Some(j);
            }
        }
        if let Some(len) = matched {
            out.push_str("[redacted]");
            i += len;
            continue;
        }
        // Named assignments: api_key / api-key / access_token /
        // access-token / secret / password, case-insensitive,
        // then [: =] with optional spaces, then a value token.
        let lower = rest.to_ascii_lowercase();
        let mut key_match: Option<usize> = None;
        for key in ["api_key", "api-key", "access_token", "access-token", "secret", "password"] {
            if lower.starts_with(key) {
                // A key must not be a prefix of a longer word.
                let after = rest.as_bytes().get(key.len());
                if let Some(&b) = after {
                    if b.is_ascii_alphanumeric() || b == b'_' {
                        continue;
                    }
                }
                key_match = Some(key.len());
                break;
            }
        }
        if let Some(klen) = key_match {
            let mut j = klen;
            while j < rest.len() && (rest.as_bytes()[j] == b' ' || rest.as_bytes()[j] == b'\t') {
                j += 1;
            }
            if j < rest.len() && (rest.as_bytes()[j] == b':' || rest.as_bytes()[j] == b'=') {
                j += 1;
                while j < rest.len() && (rest.as_bytes()[j] == b' ' || rest.as_bytes()[j] == b'\t') {
                    j += 1;
                }
                let mut q = j;
                let mut quote: Option<u8> = None;
                if q < rest.len() && (rest.as_bytes()[q] == b'"' || rest.as_bytes()[q] == b'\'') {
                    quote = Some(rest.as_bytes()[q]);
                    q += 1;
                }
                let mut k = q;
                while k < rest.len() {
                    let b = rest.as_bytes()[k];
                    if let Some(qt) = quote {
                        if b == qt {
                            break;
                        }
                    } else if b.is_ascii_whitespace() || b == b'"' || b == b'\'' {
                        break;
                    }
                    k += 1;
                }
                if k > q {
                    let mut end = k;
                    if let Some(qt) = quote {
                        if end < rest.len() && rest.as_bytes()[end] == qt {
                            end += 1;
                        }
                    }
                    out.push_str("[redacted]");
                    i += end;
                    continue;
                }
            }
        }
        // No pattern matched: copy one char.
        let ch_len = rest.chars().next().map(|c| c.len_utf8()).unwrap_or(1);
        out.push_str(&rest[..ch_len]);
        i += ch_len;
    }
    out
}

// ---------------------------------------------------------------------------
// cost_check (os/intel/cost_check.py, INT-007, PAX lane)
// ---------------------------------------------------------------------------

/// Demo-day credit, USD.
pub const CREDIT_USD: f64 = 150.0;
/// Reserved half of the credit (GOV-001), USD.
pub const RESERVED_HALF_USD: f64 = 75.0;
/// Worst-case output tokens per call: the default max_tokens every
/// call site passes to complete().
pub const WORST_OUTPUT_TOKENS: i64 = 1024;
/// Dispatch expected output, brief-style proxy of 300 tokens
/// (a dispatch plan JSON of the golden shape is not measured).
pub const DISPATCH_EXPECTED_OUTPUT_TOKENS: i64 = 300;

/// The locked demo goal (DEM-001/DEM-025: 5 jobs).
pub const DEMO_GOAL: &str = "Build a small status page feature for the relay repo: an intel status module with tests, a viewer panel stub, docs for both, and a review pass -- each as separate jobs with clear file ownership.";

fn demo_job(id: &str, title: &str, status: &str, claim: Option<&str>, claimed_at: Option<i64>, note: Option<&str>) -> Value {
    let mut pairs: Vec<(&str, Value)> = vec![
        ("id", v_str(id)),
        ("title", v_str(title)),
        ("status", v_str(status)),
    ];
    if let Some(c) = claim {
        pairs.push(("claim", v_str(c)));
    }
    if let Some(t) = claimed_at {
        pairs.push(("claimed_at", Value::Int(t)));
    }
    if let Some(n) = note {
        pairs.push(("note", v_str(n)));
    }
    v_dict(pairs)
}

/// Demo state: 5 jobs, 1 blocked, 2 alerts, marker messages.
pub fn demo_snapshot() -> Value {
    v_dict(vec![
        (
            "messages",
            Value::List(vec![
                v_str("pax: DECISION: status page goes in intel/status.py"),
                v_str("milo: DONE: stall drill seeded"),
                v_str("del: BLOCKED: viewer panel stub waits on intel/status.py"),
            ]),
        ),
        (
            "jobs",
            Value::List(vec![
                demo_job("1", "intel status module", "claimed", Some("milo"), Some(1000), None),
                demo_job("2", "status module tests", "claimed", Some("mute"), Some(1000), None),
                demo_job("3", "viewer panel stub", "blocked", None, None, Some("waits on intel/status.py from job 1")),
                demo_job("4", "docs for status module and panel", "open", None, None, None),
                demo_job("5", "review pass over the status feature", "open", None, None, None),
            ]),
        ),
        (
            "alerts",
            Value::List(vec![
                v_dict(vec![
                    ("id", v_str("presence-stall:milo:1")),
                    ("explanation", v_str("milo claimed job 1 and has not progressed it for 90 seconds.")),
                ]),
                v_dict(vec![
                    ("id", v_str("capability-refusal:worker:1")),
                    ("explanation", v_str("a crew process tried to post to the bus without a posting grant and was refused.")),
                ]),
            ]),
        ),
        (
            "presence",
            Value::List(vec![v_str("pax"), v_str("del"), v_str("mute"), v_str("milo")]),
        ),
    ])
}

/// The exact prompt compose_brief sends, built its way (INT-007's
/// brief_prompt): instruction + sections repr from the extractors.
pub fn brief_prompt(snapshot: &Value, kind: &str) -> String {
    let budget = brief_budget(kind);
    let sections = v_dict(vec![
        ("Decisions", Value::List(extract_decisions(snapshot))),
        ("Blocked", Value::List(extract_blocked(snapshot))),
        ("Owners", Value::List(extract_owners(snapshot))),
        (
            "Alerts",
            snapshot.get("alerts").cloned().unwrap_or(Value::List(vec![])),
        ),
    ]);
    format!(
        "Write a {} brief from this section data only. Do not invent facts. Keep it under {} words. Sections: {}",
        kind,
        budget,
        sections.py_repr()
    )
}

/// The exact prompt polish_explanation sends, built its way.
pub fn polish_prompt(explanation: &str) -> String {
    format!(
        "Rewrite this alert explanation for clarity, in plain English, in one sentence. Do not add, remove, or change any facts, names, job ids, paths, or numbers: {}",
        explanation
    )
}

/// One env-overridable rate: blank or unparseable values fall back
/// to the default. Pure over the raw string so tests never mutate
/// the environment. Returns (rate, source).
pub fn rate_value(raw: Option<&str>, default: f64, env_name: &str) -> (f64, String) {
    let raw = match raw {
        None => return (default, "default".to_string()),
        Some(r) => r.trim(),
    };
    if raw.is_empty() {
        return (default, "default".to_string());
    }
    match raw.parse::<f64>() {
        Ok(v) => (v, format!("env:{}", env_name)),
        Err(_) => (default, "default".to_string()),
    }
}

/// (in_rate, out_rate, sources) from env overrides or defaults.
/// Env: META_MODEL_API_INPUT_USD_PER_MTOK and
/// META_MODEL_API_OUTPUT_USD_PER_MTOK; defaults are the client's
/// estimate rates (3.0 / 15.0), labeled "planning placeholders
/// for cost estimates only -- NOT pricing facts".
pub fn rates() -> (f64, f64, BTreeMap<String, String>) {
    let (rate_in, src_in) = rate_value(
        std::env::var("META_MODEL_API_INPUT_USD_PER_MTOK").ok().as_deref(),
        3.0,
        "META_MODEL_API_INPUT_USD_PER_MTOK",
    );
    let (rate_out, src_out) = rate_value(
        std::env::var("META_MODEL_API_OUTPUT_USD_PER_MTOK").ok().as_deref(),
        15.0,
        "META_MODEL_API_OUTPUT_USD_PER_MTOK",
    );
    let mut sources = BTreeMap::new();
    sources.insert("in".to_string(), src_in);
    sources.insert("out".to_string(), src_out);
    (rate_in, rate_out, sources)
}

/// Dollar cost of a token count pair, rounded to 6 decimals.
/// (Python round() is half-even; Rust round() is half-away. No
/// pinned figure sits on a rounding tie, so the two agree here.)
pub fn cost(tokens_in: i64, tokens_out: i64, rate_in: f64, rate_out: f64) -> f64 {
    round6(tokens_in as f64 * rate_in / 1_000_000.0 + tokens_out as f64 * rate_out / 1_000_000.0)
}

/// Round to 6 decimals.
pub fn round6(x: f64) -> f64 {
    (x * 1_000_000.0).round() / 1_000_000.0
}

/// One demo-day call class row.
#[derive(Clone, Debug, PartialEq)]
pub struct CostRow {
    pub call: String,
    pub count_base: i64,
    pub count_worst: i64,
    pub tokens_in: i64,
    pub tokens_out_expected: i64,
    pub tokens_out_worst: i64,
    pub cost_expected: f64,
    pub cost_worst: f64,
}

/// Headline totals; the boot brief is kept out of the headline.
#[derive(Clone, Debug, PartialEq)]
pub struct CostSummary {
    pub expected_usd: f64,
    pub worst_usd: f64,
    pub worst_with_boot_usd: f64,
    pub reserved_half_usd: f64,
    pub credit_usd: f64,
    pub headroom_vs_reserved_usd: f64,
    pub breakeven_multiplier_vs_reserved: i64,
    pub passed: bool,
}

/// One row per demo-day call class, measured, no Spark call.
/// `dispatch_text` is the dispatch prompt file content (Python
/// reads intel/prompts/dispatch.md from disk); the caller supplies
/// it so this stays pure. See build_rows_from_disk for the
/// repo-relative file read.
pub fn build_rows(dispatch_text: &str) -> (Vec<CostRow>, f64, f64, BTreeMap<String, String>) {
    let (rate_in, rate_out, sources) = rates();
    let dispatch_prompt = format!("{}\n{}", dispatch_text, DEMO_GOAL);
    let snapshot = demo_snapshot();
    let prompt = brief_prompt(&snapshot, "morning");
    let brief_in = estimate_tokens(&prompt);
    let template = morning_template_brief(&snapshot, "morning");
    let brief_out = estimate_tokens(&template);
    let alerts = match snapshot.get("alerts") {
        Some(Value::List(a)) => a.clone(),
        _ => vec![],
    };
    let collision = v_dict(vec![
        ("id", v_str("collision:plan:1")),
        (
            "explanation",
            v_str("two jobs in the staged plan claim the same file intel/status.py."),
        ),
    ]);
    let mut all_alerts = alerts;
    all_alerts.push(collision);
    let mut polish_rows: Vec<(i64, i64)> = Vec::new();
    for alert in &all_alerts {
        let explanation = match alert.get("explanation") {
            Some(Value::Str(s)) => s.clone(),
            _ => String::new(),
        };
        polish_rows.push((
            estimate_tokens(&polish_prompt(&explanation)),
            estimate_tokens(&explanation),
        ));
    }
    let mut rows = vec![
        CostRow {
            call: "morning brief (Shot 2)".to_string(),
            count_base: 1,
            count_worst: 1,
            tokens_in: brief_in,
            tokens_out_expected: brief_out,
            tokens_out_worst: WORST_OUTPUT_TOKENS,
            cost_expected: 0.0,
            cost_worst: 0.0,
        },
        CostRow {
            call: "dispatch plan (Shot 5)".to_string(),
            count_base: 1,
            count_worst: 2,
            tokens_in: estimate_tokens(&dispatch_prompt),
            tokens_out_expected: DISPATCH_EXPECTED_OUTPUT_TOKENS,
            tokens_out_worst: WORST_OUTPUT_TOKENS,
            cost_expected: 0.0,
            cost_worst: 0.0,
        },
        CostRow {
            call: "closing brief (Shot 11)".to_string(),
            count_base: 1,
            count_worst: 1,
            tokens_in: brief_in,
            tokens_out_expected: brief_out,
            tokens_out_worst: WORST_OUTPUT_TOKENS,
            cost_expected: 0.0,
            cost_worst: 0.0,
        },
        CostRow {
            call: "alert polish (Shots 8/8b)".to_string(),
            count_base: 2,
            count_worst: 3,
            tokens_in: polish_rows[0].0,
            tokens_out_expected: polish_rows[0].1,
            tokens_out_worst: WORST_OUTPUT_TOKENS,
            cost_expected: 0.0,
            cost_worst: 0.0,
        },
        CostRow {
            call: "boot brief (Shot 0, OS-004 go only)".to_string(),
            count_base: 0,
            count_worst: 1,
            tokens_in: brief_in,
            tokens_out_expected: brief_out,
            tokens_out_worst: WORST_OUTPUT_TOKENS,
            cost_expected: 0.0,
            cost_worst: 0.0,
        },
    ];
    for row in rows.iter_mut() {
        row.cost_expected = cost(
            row.tokens_in * row.count_base,
            row.tokens_out_expected * row.count_base,
            rate_in,
            rate_out,
        );
        row.cost_worst = cost(
            row.tokens_in * row.count_worst,
            row.tokens_out_worst * row.count_worst,
            rate_in,
            rate_out,
        );
    }
    (rows, rate_in, rate_out, sources)
}

/// Build rows reading dispatch.md from the repo checkout:
/// `<crate-dir>/../../os/intel/prompts/dispatch.md`. Errors when
/// the file cannot be read (Python would raise the same way).
pub fn build_rows_from_disk() -> Result<(Vec<CostRow>, f64, f64, BTreeMap<String, String>), String> {
    let path = format!(
        "{}/../../os/intel/prompts/dispatch.md",
        env!("CARGO_MANIFEST_DIR")
    );
    let text = std::fs::read_to_string(&path)
        .map_err(|e| format!("cannot read {}: {}", path, e))?;
    Ok(build_rows(&text))
}

/// Headline totals for cost_check rows.
pub fn cost_totals(rows: &[CostRow]) -> CostSummary {
    let core: Vec<&CostRow> = rows.iter().filter(|r| r.count_base > 0).collect();
    let expected = round6(core.iter().map(|r| r.cost_expected).sum());
    let worst = round6(core.iter().map(|r| r.cost_worst).sum());
    let boot = rows.iter().find(|r| r.count_base == 0).expect("boot row");
    let worst_with_boot = round6(worst + boot.cost_worst);
    let breakeven = if worst_with_boot > 0.0 {
        (RESERVED_HALF_USD / worst_with_boot).floor() as i64
    } else {
        0
    };
    CostSummary {
        expected_usd: expected,
        worst_usd: worst,
        worst_with_boot_usd: worst_with_boot,
        reserved_half_usd: RESERVED_HALF_USD,
        credit_usd: CREDIT_USD,
        headroom_vs_reserved_usd: round6(RESERVED_HALF_USD - worst_with_boot),
        breakeven_multiplier_vs_reserved: breakeven,
        passed: worst_with_boot < RESERVED_HALF_USD && worst_with_boot < CREDIT_USD,
    }
}

/// The cost table, as text.
pub fn render_cost_table(
    rows: &[CostRow],
    summary: &CostSummary,
    rate_in: f64,
    rate_out: f64,
    sources: &BTreeMap<String, String>,
) -> String {
    let mut lines: Vec<String> = vec![
        "INT-007 demo-day Spark cost check".to_string(),
        format!(
            "rates: in ${}/Mtok ({}), out ${}/Mtok ({}) -- client defaults are planning placeholders, NOT pricing facts (see module docstring)",
            rate_in,
            sources.get("in").cloned().unwrap_or_default(),
            rate_out,
            sources.get("out").cloned().unwrap_or_default()
        ),
        "transport note: primary agent transport carries no API cost; totals below are the HTTP fallback case".to_string(),
        String::new(),
        format!(
            "{:<38} {:>4} {:>5} {:>7} {:>11} {:>9} {:>9}",
            "call", "base", "worst", "tok_in", "tok_out_exp", "$exp", "$worst"
        ),
    ];
    for row in rows {
        lines.push(format!(
            "{:<38} {:>4} {:>5} {:>7} {:>11} {:>9.4} {:>9.4}",
            row.call,
            row.count_base,
            row.count_worst,
            row.tokens_in,
            row.tokens_out_expected,
            row.cost_expected,
            row.cost_worst
        ));
    }
    lines.push(String::new());
    lines.push(format!("expected demo day: ${:.4}", summary.expected_usd));
    lines.push(format!("worst demo day: ${:.4}", summary.worst_usd));
    lines.push(format!("worst with boot brief: ${:.4}", summary.worst_with_boot_usd));
    lines.push(format!(
        "reserved half (GOV-001): ${:.2}; headroom: ${:.4}",
        summary.reserved_half_usd, summary.headroom_vs_reserved_usd
    ));
    lines.push(format!(
        "credit: ${:.2}; real rates would have to exceed placeholder rates by {}x before the reserved half is breached",
        summary.credit_usd, summary.breakeven_multiplier_vs_reserved
    ));
    lines.push(if summary.passed { "PASS".to_string() } else { "FAIL".to_string() });
    format!("{}\n", lines.join("\n"))
}

/// Run the check: rows, summary, table, exit code (0 pass, 1 breach).
/// Mirrors cost_check.main (without printing; the caller prints).
pub fn run_cost_check(dispatch_text: &str) -> (Vec<CostRow>, CostSummary, String, i32) {
    let (rows, rate_in, rate_out, sources) = build_rows(dispatch_text);
    let summary = cost_totals(&rows);
    let table = render_cost_table(&rows, &summary, rate_in, rate_out, &sources);
    let code = if summary.passed { 0 } else { 1 };
    (rows, summary, table, code)
}

// ---------------------------------------------------------------------------
// brief_cost_check (os/intel/brief_cost_check.py, BRF-027)
// ---------------------------------------------------------------------------

/// Claimed jobs per owner, matching the BRF-017 manifest:
/// milo 2, rowan 2, buffy 2, del 2, hana 1, pax 1 = 10 claimed.
pub const BRIEF_COST_CLAIMS: [(&str, &str); 10] = [
    ("milo", "brief panel"),
    ("milo", "dispatch poster"),
    ("rowan", "watchdog drill"),
    ("rowan", "viewer stub"),
    ("buffy", "cost table"),
    ("buffy", "alert polish"),
    ("del", "job sweep"),
    ("del", "plan preview"),
    ("hana", "crew board"),
    ("pax", "status page"),
];
/// Open jobs in the BRF-017 busy snapshot.
pub const BRIEF_COST_OPEN: [&str; 6] = [
    "demo script",
    "help text",
    "panel stub",
    "queue view",
    "lease sweep",
    "board chips",
];
/// Blocked jobs (note, base title) in the BRF-017 busy snapshot.
pub const BRIEF_COST_BLOCKED: [(&str, &str); 3] = [
    ("waiting on the real Spark endpoint", "spark client"),
    ("waiting on the test image", "boot service"),
    ("waiting on the busy fixture", "eval rerun"),
];
/// Done jobs in the BRF-017 busy snapshot.
pub const BRIEF_COST_DONE: [&str; 3] = ["morning schedule", "failure copy", "owners list"];

/// BRF-017-shape busy snapshot; long_titles=True is the 9-word-title
/// stress variant from the BRF-017 trial.
pub fn busy_snapshot(long_titles: bool) -> Value {
    let title = |base: &str| -> String {
        if long_titles {
            format!("{} with a long descriptive title here now", base)
        } else {
            base.to_string()
        }
    };
    let mut jobs: Vec<Value> = Vec::new();
    for (i, (nick, base)) in BRIEF_COST_CLAIMS.iter().enumerate() {
        jobs.push(v_dict(vec![
            ("id", v_str(&(i + 1).to_string())),
            ("title", v_str(&title(base))),
            ("status", v_str("claimed")),
            ("claim", v_str(nick)),
            ("claimed_at", Value::Int(1000)),
        ]));
    }
    for (j, base) in BRIEF_COST_OPEN.iter().enumerate() {
        jobs.push(v_dict(vec![
            ("id", v_str(&(11 + j).to_string())),
            ("title", v_str(&title(base))),
            ("status", v_str("open")),
        ]));
    }
    for (k, (note, base)) in BRIEF_COST_BLOCKED.iter().enumerate() {
        jobs.push(v_dict(vec![
            ("id", v_str(&(17 + k).to_string())),
            ("title", v_str(&title(base))),
            ("status", v_str("blocked")),
            ("note", v_str(note)),
        ]));
    }
    for (k, base) in BRIEF_COST_DONE.iter().enumerate() {
        jobs.push(v_dict(vec![
            ("id", v_str(&(20 + k).to_string())),
            ("title", v_str(&title(base))),
            ("status", v_str("done")),
        ]));
    }
    v_dict(vec![
        (
            "messages",
            Value::List(vec![
                v_dict(vec![
                    ("nick", v_str("pax")),
                    ("text", v_str("DECISION: ship the brief panel first")),
                ]),
                v_dict(vec![
                    ("nick", v_str("milo")),
                    ("text", v_str("DECISION: keep the 2s core poll")),
                ]),
                v_dict(vec![
                    ("nick", v_str("del")),
                    ("text", v_str("DONE: morning schedule shipped")),
                ]),
                v_dict(vec![
                    ("nick", v_str("rowan")),
                    ("text", v_str("BLOCKED: boot service waits on the test image")),
                ]),
            ]),
        ),
        ("jobs", Value::List(jobs)),
        (
            "alerts",
            Value::List(vec![
                v_dict(vec![("id", v_str("ALERT-1")), ("summary", v_str("stall on job 2"))]),
                v_dict(vec![("id", v_str("ALERT-2")), ("summary", v_str("stall on job 7"))]),
            ]),
        ),
        (
            "presence",
            Value::List(vec![
                v_str("pax"),
                v_str("del"),
                v_str("mute"),
                v_str("milo"),
                v_str("rowan"),
                v_str("buffy"),
            ]),
        ),
        ("source_window", v_str("2026-10-27 08:00 ET onward, last 24 hours")),
    ])
}

/// One measured busy-brief row: template actual ($0) plus the
/// Spark-call estimate (expected and worst case) for one variant.
#[derive(Clone, Debug, PartialEq)]
pub struct BriefCostRow {
    pub variant: String,
    pub jobs: i64,
    pub template_words: i64,
    pub template_actual_usd: f64,
    pub tokens_in: i64,
    pub tokens_out_expected: i64,
    pub tokens_out_worst: i64,
    pub cost_expected: f64,
    pub cost_worst: f64,
    pub rate_sources: BTreeMap<String, String>,
}

/// Measure one busy variant. `now_secs` is the cap window's "now"
/// (Python uses time.time()); busy messages carry no ts, so the
/// cap keeps all four and the result does not depend on it.
pub fn measure_brief_cost(long_titles: bool, now_secs: f64) -> (BriefCostRow, f64, f64) {
    let (rate_in, rate_out, sources) = rates();
    let snapshot = busy_snapshot(long_titles);
    let prompt = brief_prompt(&snapshot, "morning");
    let tokens_in = estimate_tokens(&prompt);
    // Expected Spark output: the template brief for the same
    // snapshot, trimmed to the morning budget by compose_brief
    // with no client, the same trim a Spark brief gets.
    let template = compose_brief_no_client(&snapshot, "morning", now_secs);
    let tokens_out = estimate_tokens(&template);
    let row = BriefCostRow {
        variant: if long_titles {
            "long-title stress".to_string()
        } else {
            "scored 2-word titles".to_string()
        },
        jobs: match snapshot.get("jobs") {
            Some(Value::List(j)) => j.len() as i64,
            _ => 0,
        },
        template_words: template.split_whitespace().count() as i64,
        template_actual_usd: 0.0,
        tokens_in,
        tokens_out_expected: tokens_out,
        tokens_out_worst: WORST_OUTPUT_TOKENS,
        cost_expected: cost(tokens_in, tokens_out, rate_in, rate_out),
        cost_worst: cost(tokens_in, WORST_OUTPUT_TOKENS, rate_in, rate_out),
        rate_sources: sources,
    };
    (row, rate_in, rate_out)
}

/// Both variants, measured, no Spark call.
pub fn build_brief_cost_rows(now_secs: f64) -> (Vec<BriefCostRow>, f64, f64) {
    let mut rows = Vec::new();
    let (mut rate_in, mut rate_out) = (0.0, 0.0);
    for long_titles in [false, true] {
        let (row, ri, ro) = measure_brief_cost(long_titles, now_secs);
        rate_in = ri;
        rate_out = ro;
        rows.push(row);
    }
    (rows, rate_in, rate_out)
}

/// The cost table, as text, plus the pass flag.
pub fn render_brief_cost_table(rows: &[BriefCostRow], rate_in: f64, rate_out: f64) -> (String, bool) {
    let sources = &rows[0].rate_sources;
    let worst = rows.iter().map(|r| r.cost_worst).fold(0.0f64, f64::max);
    let breakeven = if worst > 0.0 {
        (RESERVED_HALF_USD / worst).floor() as i64
    } else {
        0
    };
    let passed = rows
        .iter()
        .all(|r| r.cost_worst < RESERVED_HALF_USD && r.cost_worst < CREDIT_USD);
    let mut lines: Vec<String> = vec![
        "BRF-027 busy-fixture brief cost check".to_string(),
        format!(
            "rates: in ${}/Mtok ({}), out ${}/Mtok ({}) -- client defaults are planning placeholders, NOT pricing facts (see module docstring)",
            rate_in,
            sources.get("in").cloned().unwrap_or_default(),
            rate_out,
            sources.get("out").cloned().unwrap_or_default()
        ),
        "transport note: primary agent transport carries no API cost; totals below are the HTTP fallback case".to_string(),
        "ledger note: no ledger entry written -- this run made no Spark call, so there is no actual spend to record".to_string(),
        String::new(),
        format!(
            "{:<22} {:>4} {:>10} {:>7} {:>11} {:>9} {:>9}",
            "variant", "jobs", "tmpl_words", "tok_in", "tok_out_exp", "$exp", "$worst"
        ),
    ];
    for row in rows {
        lines.push(format!(
            "{:<22} {:>4} {:>10} {:>7} {:>11} {:>9.4} {:>9.4}",
            row.variant,
            row.jobs,
            row.template_words,
            row.tokens_in,
            row.tokens_out_expected,
            row.cost_expected,
            row.cost_worst
        ));
    }
    lines.push(String::new());
    lines.push("template actual (both variants): $0.0000 (no Spark call, spend_id null)".to_string());
    lines.push(format!("worst single busy brief: ${:.4}", worst));
    lines.push(format!(
        "reserved half (GOV-001): ${:.2}; credit: ${:.2}; real rates would have to exceed placeholder rates by {}x before one busy brief breaches the reserved half",
        RESERVED_HALF_USD, CREDIT_USD, breakeven
    ));
    lines.push(if passed { "PASS".to_string() } else { "FAIL".to_string() });
    (format!("{}\n", lines.join("\n")), passed)
}

/// Run the check: rows, pass flag, table, exit code.
pub fn run_brief_cost_check(now_secs: f64) -> (Vec<BriefCostRow>, bool, String, i32) {
    let (rows, rate_in, rate_out) = build_brief_cost_rows(now_secs);
    let (text, passed) = render_brief_cost_table(&rows, rate_in, rate_out);
    let code = if passed { 0 } else { 1 };
    (rows, passed, text, code)
}

/// A brief record for a template (dry-run) brief, mirroring the
/// contract of brief.generate_brief with client=None and dry_run:
/// the text starts with TEMPLATE, model is "template", spend_id is
/// null, kind passes through. This assumes no stored recent brief
/// for the room (the Python test's room has none); the store
/// lookup itself lives in brief.py (B09/B10) and is not ported.
#[derive(Clone, Debug, PartialEq)]
pub struct TemplateBriefRecord {
    pub text: String,
    pub model: String,
    pub spend_id: Option<String>,
    pub kind: String,
}

pub fn template_brief_record(snapshot: &Value, kind: &str, now_secs: f64) -> (String, TemplateBriefRecord) {
    let text = compose_brief_no_client(snapshot, kind, now_secs);
    let record = TemplateBriefRecord {
        text: text.clone(),
        model: "template".to_string(),
        spend_id: None,
        kind: kind.to_string(),
    };
    (text, record)
}

// ---------------------------------------------------------------------------
// budget gate (os/intel/drills/budget_gate.py, OS-085)
// ---------------------------------------------------------------------------

/// A fixture job queue with the OS-085 budget gate. claim()
/// mirrors jobs.py's outcome shape: a granted claim marks the job
/// claimed; a refused claim leaves the job open and records the
/// hold. The gate itself is claim_allowed — the drill never
/// re-implements "at cap".
#[derive(Clone, Debug, Default)]
pub struct FakeQueue {
    pub jobs: BTreeMap<String, Value>,
    pub holds: Vec<String>,
}

impl FakeQueue {
    pub fn new() -> Self {
        Self::default()
    }

    /// Post a job in the open state.
    pub fn post(&mut self, job_id: &str, lane: &str) -> Value {
        let job = v_dict(vec![
            ("id", v_str(job_id)),
            ("lane", v_str(lane)),
            ("status", v_str("open")),
        ]);
        self.jobs.insert(job_id.to_string(), job.clone());
        job
    }

    /// Claim a job under a lane's spent/cap: granted marks it
    /// claimed and returns true; refused leaves it open, records
    /// the hold, and returns false.
    pub fn claim(&mut self, job_id: &str, spent: &Value, cap: &Value) -> bool {
        if !claim_allowed(spent, cap) {
            self.holds.push(job_id.to_string());
            return false;
        }
        if let Some(Value::Dict(pairs)) = self.jobs.get_mut(job_id) {
            for (k, v) in pairs.iter_mut() {
                if k.as_str() == "status" {
                    *v = v_str("claimed");
                }
            }
        }
        true
    }

    /// A job's status string, if the job exists.
    pub fn status_of(&self, job_id: &str) -> Option<String> {
        self.jobs.get(job_id).and_then(|j| match j.get("status") {
            Some(Value::Str(s)) => Some(s.clone()),
            _ => None,
        })
    }
}

/// The budget-warning detector branch of watchdog.tick (OS-085).
/// Canonical home is B21's supervisor crate; this faithful local
/// copy exists because B20's budget_gate drill and tests exercise
/// it. One alert per lane per tick (first entry wins); the dedupe
/// key is `budget-warning:<lane>`; warnings never announce (the
/// announce list is the caller's; this returns alerts only).
/// `now` is the tick time (Python int(now)).
pub fn budget_warning_alerts(snapshot: &Value, now: i64) -> Vec<Value> {
    let warn_percent = budget_warn_percent();
    let mut alerts = Vec::new();
    let mut seen: HashSet<String> = HashSet::new();
    for entry in budgets_from_snapshot(snapshot) {
        let lane = match entry.get("lane") {
            Some(Value::Str(s)) => s.clone(),
            _ => continue,
        };
        if !seen.insert(lane.clone()) {
            continue;
        }
        let spent = entry.get("spent").cloned().unwrap_or(Value::Null);
        let cap = entry.get("cap").cloned().unwrap_or(Value::Null);
        if !at_warning(&spent, &cap, Some(warn_percent)) {
            continue;
        }
        let spent_i = spent.usable_int().unwrap_or(0);
        let cap_i = cap.usable_int().unwrap_or(0);
        let remaining = cap_i - spent_i;
        let explanation = format!(
            "The {} lane has spent {} of its {} budget ({} remaining): it is past the {}% warning threshold, so the next claims could hit the cap and stop the lane silently.",
            lane, spent_i, cap_i, remaining, warn_percent
        );
        let suggested_fix = format!(
            "Slow new {} claims, raise the lane cap, or let the lane finish its current work before posting more — at cap, new claims are held and the job stays open.",
            lane
        );
        alerts.push(v_dict(vec![
            ("kind", v_str("budget-warning")),
            ("severity", v_str("warning")),
            ("lane", v_str(&lane)),
            ("spent", spent.clone()),
            ("cap", cap.clone()),
            ("remaining", Value::Int(remaining)),
            ("explanation", v_str(&explanation)),
            ("suggested_fix", v_str(&suggested_fix)),
            ("dedupe_key", v_str(&format!("budget-warning:{}", lane))),
            ("created_at", Value::Int(now)),
        ]));
    }
    alerts
}

/// One spend-vs-budget line for a budget entry, mirroring the
/// spend lines of brief.memory_budget_lines (OS-079, B09/B10):
/// spent+cap renders "Spend: {lane} lane: {spent} of {cap}
/// budget ({remaining} remaining)"; remaining+cap renders
/// "Spend: {lane} lane: {remaining} remaining of {cap} cap";
/// remaining alone renders "Spend: {lane} lane: {remaining}
/// remaining". A held entry (held True) appends " — new claims
/// held". `age_label` is the caller-supplied age suffix (brief.py
/// appends " (as of YYYY-MM-DD HH:MM ET)" or " (snapshot time
/// not reported)"; the ET formatting itself lives in brief.py
/// and is not ported). Entries with no usable figure render
/// nothing (None).
pub fn budget_spend_line(entry: &Value, age_label: &str) -> Option<String> {
    if !matches!(entry, Value::Dict(_)) {
        return None;
    }
    let lane = match entry.get("lane") {
        Some(Value::Str(s)) if !s.is_empty() => s.clone(),
        _ => return None,
    };
    let cap = entry.get("cap").cloned().unwrap_or(Value::Null);
    let spent = entry.get("spent").cloned().unwrap_or(Value::Null);
    let remaining_v = entry.get("remaining").cloned().unwrap_or(Value::Null);
    let text = if let (Some(s), Some(c)) = (spent.usable_int(), cap.usable_int()) {
        format!(
            "Spend: {} lane: {} of {} budget ({} remaining)",
            lane,
            s,
            c,
            c - s
        )
    } else if let (Some(r), Some(c)) = (remaining_v.usable_int(), cap.usable_int()) {
        format!("Spend: {} lane: {} remaining of {} cap", lane, r, c)
    } else if let Some(r) = remaining_v.usable_int() {
        format!("Spend: {} lane: {} remaining", lane, r)
    } else {
        return None;
    };
    let held = matches!(entry.get("held"), Some(Value::Bool(true)));
    let mut line = text;
    if held {
        line.push_str(" — new claims held");
    }
    line.push_str(age_label);
    Some(line)
}

// ---------------------------------------------------------------------------
// cgroup limits (os/intel/drills/cgroup_limits.py, OS-035)
// The systemd-run enforcement phase needs a live host (transient
// units, /run writes, cgroup controllers) and has no unit-test
// equivalent here; the portable parts are the slice parser, the
// expected values, and the controller gate.
// ---------------------------------------------------------------------------

/// Expected slice values: CPUQuota=100%, MemoryMax=1G.
pub const CGROUP_EXPECTED: [(&str, &str); 2] = [("CPUQuota", "100%"), ("MemoryMax", "1G")];
/// Hog target: 20 chunks of 10 MB.
pub const HOG_TARGET_CHUNKS: i64 = 20;
/// Hog chunk size in MB.
pub const HOG_CHUNK_MB: i64 = 10;
/// Hog test cap (the slice's own 1G ceiling stays above it).
pub const HOG_TEST_CAP: &str = "50M";

/// Parse a systemd slice file: `[Slice]` section key=value pairs.
/// Mirrors cgroup_limits.parse_slice.
pub fn parse_slice(text: &str) -> Vec<(String, String)> {
    let mut values = Vec::new();
    let mut section = String::new();
    for raw_line in text.lines() {
        let line = raw_line.trim();
        if line.starts_with('[') && line.ends_with(']') {
            section = line[1..line.len() - 1].to_string();
            continue;
        }
        if section == "Slice" {
            if let Some((key, val)) = line.split_once('=') {
                values.push((key.trim().to_string(), val.trim().to_string()));
            }
        }
    }
    values
}

/// Look up a parsed slice value by key.
pub fn slice_value<'a>(values: &'a [(String, String)], key: &str) -> Option<&'a str> {
    values.iter().find(|(k, _)| k == key).map(|(_, v)| v.as_str())
}

/// The file phase: every expected value matches the parsed slice.
pub fn slice_file_passes(values: &[(String, String)]) -> bool {
    CGROUP_EXPECTED
        .iter()
        .all(|(key, want)| slice_value(values, key) == Some(*want))
}

/// The gate phase over a cgroup.controllers listing: the host
/// cgroup hierarchy must expose the cpu and memory controllers.
/// Returns the missing controllers (empty means the gate passes).
/// A host that cannot read the listing is ENVIRONMENT-BLOCKED,
/// which the caller models as a missing read (None input).
pub fn cgroup_gate_missing(controllers: Option<&str>) -> Vec<String> {
    let present: HashSet<String> = match controllers {
        Some(text) => text.split_whitespace().map(|s| s.to_string()).collect(),
        None => HashSet::new(),
    };
    ["cpu", "memory"]
        .iter()
        .filter(|c| !present.contains(**c))
        .map(|c| c.to_string())
        .collect()
}

// ---------------------------------------------------------------------------
// disk audit (os/mos/disk_audit.py, OS-128)
// The on-disk stores live in B17 (memory) and B19 (artifact store).
// This port takes them as traits so the audit logic stays faithful
// without duplicating the store formats; the owning crates supply
// the real backends. A missing store root reads as empty, not as
// an error: that rule belongs to the backend (the fakes below do
// it), never to the audit.
// ---------------------------------------------------------------------------

/// One artifact manifest entry (OS-083): name and version.
#[derive(Clone, Debug, PartialEq)]
pub struct ArtifactEntry {
    pub name: String,
    pub version: i64,
}

/// The OS-083 artifact store surface disk_audit reads.
pub trait ArtifactStore {
    /// Manifest entries for one job's artifacts.
    fn list_artifacts(&self, job: &str) -> Result<Vec<ArtifactEntry>, String>;
    /// Artifact bytes for one manifest entry.
    fn read(&self, job: &str, name: &str, version: i64) -> Result<Vec<u8>, String>;
}

/// The OS-078 memory journal surface disk_audit reads.
pub trait MemoryStore {
    /// Latest shared decision keys.
    fn list_shared_keys(&self) -> Result<Vec<String>, String>;
    /// Latest own decision keys for one agent.
    fn list_keys(&self, agent: &str) -> Result<Vec<String>, String>;
}

/// Parse an OS-083 reference `artifact:<job>/<name>@v<version>`,
/// else None. Mirrors ARTIFACT_REF_RE (greedy name: the LAST
/// "`@v<digits>`" suffix wins).
pub fn parse_artifact_ref(reference: &str) -> Option<(String, String, i64)> {
    let rest = reference.strip_prefix("artifact:")?;
    let slash = rest.find('/')?;
    let job = &rest[..slash];
    let tail = &rest[slash + 1..];
    let at = tail.rfind("@v")?;
    let name = &tail[..at];
    let version_text = &tail[at + 2..];
    if name.is_empty() || version_text.is_empty() || !version_text.bytes().all(|b| b.is_ascii_digit()) {
        return None;
    }
    let version: i64 = version_text.parse().ok()?;
    Some((job.to_string(), name.to_string(), version))
}

/// Goal key, else the Goal: line of spec text, else None.
/// Mirrors disk_audit._goal (the DSP spec standard, same rule
/// intel/baton.py uses).
pub fn audit_goal(record: &Value) -> Option<String> {
    if let Some(g) = record.get("goal").and_then(|v| v.as_text()) {
        return Some(g);
    }
    if let Some(Value::Str(spec)) = record.get("spec") {
        for line in spec.lines() {
            let stripped = line.trim();
            if stripped.to_ascii_lowercase().starts_with("goal:") {
                // Python returns _text(remainder) at the FIRST
                // Goal: line: an empty remainder is None, and
                // scanning stops there rather than continuing.
                let rest = stripped["goal:".len()..].trim();
                if rest.is_empty() {
                    return None;
                }
                return Some(rest.to_string());
            }
        }
    }
    None
}

/// Deposited progress: progress_notes, else the latest note.
/// Mirrors disk_audit._progress_notes.
pub fn audit_progress_notes(record: &Value) -> Vec<String> {
    let notes = record.get("progress_notes").map(|v| v.as_str_list()).unwrap_or_default();
    if !notes.is_empty() {
        return notes;
    }
    match record.get("note").and_then(|v| v.as_text()) {
        Some(note) => vec![note],
        None => vec![],
    }
}

/// Files still to touch: files minus completed_files, in order.
pub fn audit_remaining_files(record: &Value) -> Vec<String> {
    let files = record.get("files").map(|v| v.as_str_list()).unwrap_or_default();
    let completed: HashSet<String> = record
        .get("completed_files")
        .map(|v| v.as_str_list())
        .unwrap_or_default()
        .into_iter()
        .collect();
    files.into_iter().filter(|p| !completed.contains(p)).collect()
}

/// One reconstructed job record, as Value.
pub fn audit_job_out(
    id: &str,
    status: Option<String>,
    title: Option<String>,
    spec: Option<String>,
    goal: Option<String>,
    progress_notes: Vec<String>,
    remaining_files: Vec<String>,
    accept: Value,
    artifacts: Vec<String>,
    decisions: Vec<String>,
) -> Value {
    v_dict(vec![
        ("id", v_str(id)),
        (
            "status",
            status.map(|s| v_str(&s)).unwrap_or(Value::Null),
        ),
        ("title", title.map(|s| v_str(&s)).unwrap_or(Value::Null)),
        ("spec", spec.map(|s| v_str(&s)).unwrap_or(Value::Null)),
        ("goal", goal.map(|s| v_str(&s)).unwrap_or(Value::Null)),
        (
            "progress_notes",
            Value::List(progress_notes.into_iter().map(|s| v_str(&s)).collect()),
        ),
        (
            "remaining_files",
            Value::List(remaining_files.into_iter().map(|s| v_str(&s)).collect()),
        ),
        ("accept", accept),
        (
            "artifacts",
            Value::List(artifacts.into_iter().map(|s| v_str(&s)).collect()),
        ),
        (
            "decisions",
            Value::List(decisions.into_iter().map(|s| v_str(&s)).collect()),
        ),
    ])
}

/// The audit result: reconstructed jobs, sorted shared decision
/// keys, leaks (empty exactly when every job's state is fully
/// reconstructable), and the pass flag.
#[derive(Clone, Debug, PartialEq)]
pub struct AuditResult {
    pub jobs: Vec<Value>,
    pub decisions: Vec<String>,
    pub leaks: Vec<Value>,
    pub passed: bool,
}

fn leak(job: Option<&str>, layer: &str, detail: &str) -> Value {
    v_dict(vec![
        ("job", job.map(|j| v_str(j)).unwrap_or(Value::Null)),
        ("layer", v_str(layer)),
        ("detail", v_str(detail)),
    ])
}

/// Audit job records against the on-disk stores (via traits).
/// Returns Err("job records must be a list") for a non-list input,
/// mirroring DiskAuditError. A corrupt memory journal is a loud
/// failure, never a skipped memory: it is filed as a
/// memory-journal leak (once per agent).
pub fn audit(
    memory: &dyn MemoryStore,
    artifacts: &dyn ArtifactStore,
    job_records: &Value,
) -> Result<AuditResult, String> {
    let records = match job_records {
        Value::List(r) => r,
        _ => return Err("job records must be a list".to_string()),
    };
    let mut leaks: Vec<Value> = Vec::new();
    let shared: HashSet<String> = match memory.list_shared_keys() {
        Ok(keys) => keys.into_iter().collect(),
        Err(exc) => {
            leaks.push(leak(
                None,
                "memory-journal",
                &format!("shared journal unreadable: {}", exc),
            ));
            HashSet::new()
        }
    };
    let mut journal_leaked: HashSet<String> = HashSet::new();
    let mut agent_cache: HashMap<String, HashSet<String>> = HashMap::new();
    let mut jobs_out: Vec<Value> = Vec::new();
    for record in records {
        if !matches!(record, Value::Dict(_)) {
            leaks.push(leak(None, "record", "job record is not an object"));
            continue;
        }
        let job_id = record
            .get("id")
            .and_then(|v| v.as_text())
            .or_else(|| record.get("job_id").and_then(|v| v.as_text()));
        let job_id = match job_id {
            Some(id) => id,
            None => {
                leaks.push(leak(None, "record", "job record carries no id"));
                continue;
            }
        };
        let spec = record.get("spec").and_then(|v| v.as_text());
        let title = record.get("title").and_then(|v| v.as_text());
        if title.is_none() || spec.is_none() {
            leaks.push(leak(
                Some(&job_id),
                "spec",
                "cold reader cannot tell what this job is",
            ));
        }
        let status = record.get("status").and_then(|v| v.as_text());
        let goal = audit_goal(record);
        if status.as_deref() == Some("claimed") && goal.is_none() {
            leaks.push(leak(
                Some(&job_id),
                "baton",
                "claimed job has no goal for the next worker",
            ));
        }
        let claimer = record.get("claim").and_then(|v| v.as_text());
        if status.as_deref() == Some("claimed") && claimer.is_none() {
            leaks.push(leak(
                Some(&job_id),
                "claim",
                "claimed job names no holder or lease",
            ));
        }
        // Artifacts: every reference checked against the store.
        let mut verified: Vec<String> = Vec::new();
        for reference in record.get("artifacts").map(|v| v.as_str_list()).unwrap_or_default() {
            let (ref_job, name, version) = match parse_artifact_ref(&reference) {
                Some(p) => p,
                None => {
                    leaks.push(leak(
                        Some(&job_id),
                        "artifacts",
                        &format!("unparseable artifact reference: {}", reference),
                    ));
                    continue;
                }
            };
            let entries = match artifacts.list_artifacts(&ref_job) {
                Ok(e) => e,
                Err(exc) => {
                    leaks.push(leak(
                        Some(&job_id),
                        "artifacts",
                        &format!("store unreadable for {}: {}", reference, exc),
                    ));
                    continue;
                }
            };
            let entry = entries.iter().find(|e| e.name == name);
            let entry = match entry {
                Some(e) => e,
                None => {
                    leaks.push(leak(
                        Some(&job_id),
                        "artifacts",
                        &format!("no manifest entry for {}", reference),
                    ));
                    continue;
                }
            };
            if entry.version != version {
                leaks.push(leak(
                    Some(&job_id),
                    "artifacts",
                    &format!("manifest holds v{}, record references {}", entry.version, reference),
                ));
                continue;
            }
            if let Err(exc) = artifacts.read(&ref_job, &name, version) {
                leaks.push(leak(
                    Some(&job_id),
                    "artifacts",
                    &format!("artifact bytes unreadable for {}: {}", reference, exc),
                ));
                continue;
            }
            verified.push(reference);
        }
        // Settled decisions: shared journal, else the claiming
        // agent's own journal. A key in neither is a leak.
        let mut decisions_ok: Vec<String> = Vec::new();
        for key in record.get("decisions").map(|v| v.as_str_list()).unwrap_or_default() {
            let mut found = shared.contains(&key);
            if !found {
                if let Some(claimer) = &claimer {
                    if !agent_cache.contains_key(claimer) {
                        let keys = match memory.list_keys(claimer) {
                            Ok(keys) => keys.into_iter().collect(),
                            Err(exc) => {
                                if journal_leaked.insert(claimer.clone()) {
                                    leaks.push(leak(
                                        None,
                                        "memory-journal",
                                        &format!("journal for {} unreadable: {}", claimer, exc),
                                    ));
                                }
                                HashSet::new()
                            }
                        };
                        agent_cache.insert(claimer.clone(), keys);
                    }
                    found = agent_cache
                        .get(claimer)
                        .map(|keys| keys.contains(&key))
                        .unwrap_or(false);
                }
            }
            if found {
                decisions_ok.push(key.clone());
            } else {
                leaks.push(leak(
                    Some(&job_id),
                    "memory",
                    &format!("decision {} in no journal the reader can see", key),
                ));
            }
        }
        jobs_out.push(audit_job_out(
            &job_id,
            status,
            title,
            spec,
            goal,
            audit_progress_notes(record),
            audit_remaining_files(record),
            record.get("accept").cloned().unwrap_or(Value::Null),
            verified,
            decisions_ok,
        ));
    }
    let mut decisions_sorted: Vec<String> = shared.into_iter().collect();
    decisions_sorted.sort();
    let passed = leaks.is_empty();
    Ok(AuditResult {
        jobs: jobs_out,
        decisions: decisions_sorted,
        leaks,
        passed,
    })
}

/// In-memory fake stores for tests (and for callers that hold
/// their stores in memory): shared keys, per-agent keys, artifact
/// manifests, readable bytes, and error switches for the unreadable
/// paths. A missing root reads as empty, per the audit's rule.
#[derive(Clone, Debug, Default)]
pub struct FakeStores {
    pub shared_keys: Vec<String>,
    pub agent_keys: HashMap<String, Vec<String>>,
    pub manifests: HashMap<String, Vec<ArtifactEntry>>,
    pub unreadable_bytes: HashSet<(String, String, i64)>,
    pub unreadable_store_jobs: HashSet<String>,
    pub shared_journal_error: Option<String>,
    pub agent_journal_errors: HashSet<String>,
}

impl MemoryStore for FakeStores {
    fn list_shared_keys(&self) -> Result<Vec<String>, String> {
        match &self.shared_journal_error {
            Some(e) => Err(e.clone()),
            None => Ok(self.shared_keys.clone()),
        }
    }

    fn list_keys(&self, agent: &str) -> Result<Vec<String>, String> {
        if self.agent_journal_errors.contains(agent) {
            return Err(format!("corrupt journal for {}", agent));
        }
        Ok(self.agent_keys.get(agent).cloned().unwrap_or_default())
    }
}

impl ArtifactStore for FakeStores {
    fn list_artifacts(&self, job: &str) -> Result<Vec<ArtifactEntry>, String> {
        if self.unreadable_store_jobs.contains(job) {
            return Err(format!("store unreadable for {}", job));
        }
        Ok(self.manifests.get(job).cloned().unwrap_or_default())
    }

    fn read(&self, job: &str, name: &str, version: i64) -> Result<Vec<u8>, String> {
        if self
            .unreadable_bytes
            .contains(&(job.to_string(), name.to_string(), version))
        {
            return Err("bytes unreadable".to_string());
        }
        Ok(b"artifact-bytes".to_vec())
    }
}

// ---------------------------------------------------------------------------
// Tests, organized by the Python test file they mirror. Names carry
// the Python test they mirror; where a Python case belongs to
// another batch's module it is NOT faked here (see the report for
// the named other-batch cases).
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap as StdHashMap;

    fn close(a: f64, b: f64) -> bool {
        (a - b).abs() < 1e-9
    }

    fn dispatch_text() -> String {
        let path = format!(
            "{}/../../os/intel/prompts/dispatch.md",
            env!("CARGO_MANIFEST_DIR")
        );
        std::fs::read_to_string(&path).expect("dispatch.md readable in checkout")
    }

    fn snapshot_with_budgets(entries: Vec<Value>) -> Value {
        v_dict(vec![
            ("jobs", Value::List(vec![])),
            ("messages", Value::List(vec![])),
            ("presence", Value::List(vec![])),
            ("caps", v_dict(vec![])),
            ("budgets", Value::List(entries)),
        ])
    }

    fn budget_entry(lane: &str, spent: Value, cap: Value) -> Value {
        v_dict(vec![("lane", v_str(lane)), ("spent", spent), ("cap", cap)])
    }

    // --- test_intel_budget_gate.py: BudgetGateFunctionsTest, plus
    // budgets.py behavior (test_intel_budget_gate pins budgets.py).
    #[test]
    fn gate_warning_band_is_threshold_to_cap_exclusive() {
        assert!(!at_warning(&v_int(79), &v_int(100), None));
        assert!(at_warning(&v_int(80), &v_int(100), None));
        assert!(at_warning(&v_int(99), &v_int(100), None));
        assert!(!at_warning(&v_int(100), &v_int(100), None));
    }

    #[test]
    fn gate_cap_includes_overspend() {
        assert!(!at_cap(&v_int(99), &v_int(100)));
        assert!(at_cap(&v_int(100), &v_int(100)));
        assert!(at_cap(&v_int(150), &v_int(100)));
    }

    #[test]
    fn gate_claim_gate_follows_cap_only() {
        assert!(claim_allowed(&v_int(99), &v_int(100)));
        assert!(claim_allowed(&v_int(80), &v_int(100)));
        assert!(!claim_allowed(&v_int(100), &v_int(100)));
        assert!(claim_allowed(&Value::Null, &Value::Null));
    }

    #[test]
    fn gate_unbudgeted_and_malformed_never_warned_or_held() {
        assert!(!at_warning(&Value::Null, &Value::Null, None));
        assert!(!at_cap(&Value::Null, &Value::Null));
        assert!(!at_warning(&v_str("lots"), &v_str("none"), None));
        assert!(!at_cap(&v_int(90), &v_int(0)));
        assert!(!at_cap(&v_int(-5), &v_int(100)));
        assert_eq!(budget_state(&v_dict(vec![("lane", v_str("x"))])), "unbudgeted");
        assert_eq!(budget_state(&v_str("not-a-dict")), "unbudgeted");
    }

    #[test]
    fn gate_budget_state_names_all_three_states() {
        assert_eq!(
            budget_state(&budget_entry("s", v_int(50), v_int(100))),
            "ok"
        );
        assert_eq!(
            budget_state(&budget_entry("s", v_int(80), v_int(100))),
            "warning"
        );
        assert_eq!(
            budget_state(&budget_entry("s", v_int(100), v_int(100))),
            "capped"
        );
    }

    #[test]
    fn gate_hold_entry_flags_only_at_cap() {
        assert_eq!(
            hold_entry("s", v_int(80), v_int(100)).get("held"),
            Some(&Value::Bool(false))
        );
        assert_eq!(
            hold_entry("s", v_int(100), v_int(100)).get("held"),
            Some(&Value::Bool(true))
        );
    }

    #[test]
    fn budgets_env_int_falls_back_on_bad_input() {
        assert_eq!(env_int_value(None, 80, 1, 100), 80);
        assert_eq!(env_int_value(Some(""), 80, 1, 100), 80);
        assert_eq!(env_int_value(Some("   "), 80, 1, 100), 80);
        assert_eq!(env_int_value(Some("abc"), 80, 1, 100), 80);
        assert_eq!(env_int_value(Some("0"), 80, 1, 100), 80);
        assert_eq!(env_int_value(Some("101"), 80, 1, 100), 80);
        assert_eq!(env_int_value(Some("80"), 80, 1, 100), 80);
        assert_eq!(env_int_value(Some(" 95 "), 80, 1, 100), 95);
    }

    #[test]
    fn budgets_spend_ratio_edges() {
        assert!(close(spend_ratio(&v_int(50), &v_int(100)).unwrap(), 0.5));
        assert_eq!(spend_ratio(&Value::Bool(true), &v_int(100)), None);
        assert_eq!(spend_ratio(&Value::Float(50.0), &v_int(100)), None);
        assert_eq!(spend_ratio(&v_int(50), &v_int(0)), None);
        assert_eq!(spend_ratio(&v_int(-5), &v_int(100)), None);
        assert_eq!(spend_ratio(&v_str("lots"), &v_int(100)), None);
    }

    #[test]
    fn budgets_from_snapshot_skips_malformed() {
        let snap = snapshot_with_budgets(vec![
            budget_entry("ok", v_int(10), v_int(100)),
            v_str("not-a-dict"),
            v_dict(vec![("spent", v_int(90)), ("cap", v_int(100))]),
            v_dict(vec![
                ("lane", v_str("")),
                ("spent", v_int(1)),
                ("cap", v_int(2)),
            ]),
        ]);
        let entries = budgets_from_snapshot(&snap);
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].get("lane"), Some(&v_str("ok")));
        assert!(budgets_from_snapshot(&v_dict(vec![])).is_empty());
        assert!(budgets_from_snapshot(&v_dict(vec![("budgets", v_str("nope"))])).is_empty());
    }

    // --- test_intel_budget_gate.py: BudgetWarningDetectorTest
    // (detector branch mirror; canonical home B21 watchdog.py).
    #[test]
    fn gate_warning_fires_at_threshold_with_lane_figures() {
        let snap = snapshot_with_budgets(vec![budget_entry("spark", v_int(80), v_int(100))]);
        let alerts = budget_warning_alerts(&snap, 100000);
        assert_eq!(alerts.len(), 1);
        let alert = &alerts[0];
        assert_eq!(alert.get("severity"), Some(&v_str("warning")));
        assert_eq!(alert.get("lane"), Some(&v_str("spark")));
        assert_eq!(alert.get("spent"), Some(&v_int(80)));
        assert_eq!(alert.get("cap"), Some(&v_int(100)));
        assert_eq!(alert.get("remaining"), Some(&v_int(20)));
        assert_eq!(alert.get("dedupe_key"), Some(&v_str("budget-warning:spark")));
        let explanation = match alert.get("explanation") {
            Some(Value::Str(s)) => s.clone(),
            _ => panic!("explanation"),
        };
        assert!(explanation.contains("spark"));
        assert!(explanation.contains("80"));
    }

    #[test]
    fn gate_no_warning_below_threshold_or_at_cap() {
        for spent in [0, 70, 100, 150] {
            let snap = snapshot_with_budgets(vec![budget_entry("spark", v_int(spent), v_int(100))]);
            assert!(budget_warning_alerts(&snap, 100000).is_empty(), "spent={}", spent);
        }
    }

    #[test]
    fn gate_malformed_budget_entries_do_not_crash_detector() {
        let snap = snapshot_with_budgets(vec![
            v_dict(vec![
                ("lane", v_str("bad")),
                ("spent", v_str("lots")),
                ("cap", v_str("none")),
            ]),
            v_dict(vec![("spent", v_int(90)), ("cap", v_int(100))]),
            v_str("not-a-dict"),
        ]);
        assert!(budget_warning_alerts(&snap, 100000).is_empty());
    }

    #[test]
    fn gate_duplicate_lane_warns_once() {
        let snap = snapshot_with_budgets(vec![
            budget_entry("spark", v_int(80), v_int(100)),
            budget_entry("spark", v_int(90), v_int(100)),
        ]);
        assert_eq!(budget_warning_alerts(&snap, 100000).len(), 1);
    }

    // --- test_intel_budget_gate.py: BudgetHoldBriefLineTest
    // (spend-line helper mirror; canonical home B09/B10 brief.py).
    #[test]
    fn gate_held_lane_line_names_the_hold() {
        let line = budget_spend_line(
            &hold_entry("spark", v_int(100), v_int(100)),
            " (snapshot time not reported)",
        )
        .unwrap();
        assert!(line.contains("spark"));
        assert!(line.contains("new claims held"));
        assert!(line.contains("100 of 100"));
    }

    #[test]
    fn gate_unheld_lane_line_unchanged() {
        let line = budget_spend_line(
            &hold_entry("spark", v_int(80), v_int(100)),
            " (snapshot time not reported)",
        )
        .unwrap();
        assert!(line.contains("spark"));
        assert!(!line.contains("held"));
    }

    #[test]
    fn gate_entry_without_flag_renders_as_before() {
        let line = budget_spend_line(
            &budget_entry("spark", v_int(50), v_int(100)),
            " (snapshot time not reported)",
        )
        .unwrap();
        assert!(line.contains("spark"));
        assert!(!line.contains("held"));
    }

    #[test]
    fn spend_line_formats_match_brief_renderer() {
        // Formats pinned by test_intel_brief_memory_budget_caller
        // (spend lines); the with_memory_budget record itself is
        // other-batch (brief.py), but the line formats are the
        // same strings this helper renders.
        let hana = budget_spend_line(
            &budget_entry("HANA", v_int(120), v_int(300)),
            " (snapshot time not reported)",
        )
        .unwrap();
        assert!(hana.contains("Spend: HANA lane: 120 of 300 budget (180 remaining)"));
        let milo = budget_spend_line(
            &v_dict(vec![
                ("lane", v_str("MILO")),
                ("remaining", v_int(90)),
                ("cap", v_int(200)),
            ]),
            " (snapshot time not reported)",
        )
        .unwrap();
        assert!(milo.contains("Spend: MILO lane: 90 remaining of 200 cap"));
        let remaining_only = budget_spend_line(
            &v_dict(vec![("lane", v_str("HANA")), ("remaining", v_int(75))]),
            " (snapshot time not reported)",
        )
        .unwrap();
        assert!(remaining_only.contains("Spend: HANA lane: 75 remaining"));
        assert!(!remaining_only.contains("cap"));
    }

    // --- test_intel_budget_gate.py: BudgetGateDrillTest, as Rust
    // phases (the Python drill runs watchdog.tick + brief rendering;
    // here the gate, detector, and spend-line mirrors stand in).
    #[test]
    fn gate_drill_phases() {
        let mut queue = FakeQueue::new();
        queue.post("1", "spark");
        // Phase 1: 70/100: no warning, claim granted.
        assert!(budget_warning_alerts(
            &snapshot_with_budgets(vec![budget_entry("spark", v_int(70), v_int(100))]),
            100000
        )
        .is_empty());
        assert!(queue.claim("1", &v_int(70), &v_int(100)));
        assert_eq!(queue.status_of("1").as_deref(), Some("claimed"));
        // Phase 2: 80/100: exactly one warning, claim still granted.
        let warnings = budget_warning_alerts(
            &snapshot_with_budgets(vec![budget_entry("spark", v_int(80), v_int(100))]),
            100000,
        );
        assert_eq!(warnings.len(), 1);
        queue.post("2", "spark");
        assert!(queue.claim("2", &v_int(80), &v_int(100)));
        // Phase 3: 100/100: no warning, claim held, job stays open.
        assert!(budget_warning_alerts(
            &snapshot_with_budgets(vec![budget_entry("spark", v_int(100), v_int(100))]),
            100000
        )
        .is_empty());
        queue.post("3", "spark");
        assert!(!queue.claim("3", &v_int(100), &v_int(100)));
        assert_eq!(queue.status_of("3").as_deref(), Some("open"));
        assert_eq!(queue.holds, vec!["3".to_string()]);
        let held_line = budget_spend_line(
            &hold_entry("spark", v_int(100), v_int(100)),
            " (snapshot time not reported)",
        )
        .unwrap();
        assert!(held_line.contains("new claims held"));
        // Phase 4: unbudgeted and malformed: no warning, no hold.
        assert!(budget_warning_alerts(
            &snapshot_with_budgets(vec![v_dict(vec![("lane", v_str("unbudgeted"))])]),
            100000
        )
        .is_empty());
        assert!(claim_allowed(&Value::Null, &Value::Null));
    }

    // --- test_intel_budget_forecast.py: ForecastMathTest
    #[test]
    fn forecast_projection_scales_the_ledger_rate() {
        assert_eq!(
            project_end_of_day(&v_int(80), &v_int(8), &v_int(24)),
            Some(240.0)
        );
        assert_eq!(
            project_end_of_day(&v_int(50), &v_int(12), &v_int(24)),
            Some(100.0)
        );
    }

    #[test]
    fn forecast_projection_at_or_past_day_end_is_spent() {
        assert_eq!(
            project_end_of_day(&v_int(90), &v_int(24), &v_int(24)),
            Some(90.0)
        );
        assert_eq!(
            project_end_of_day(&v_int(90), &v_int(30), &v_int(24)),
            Some(90.0)
        );
    }

    #[test]
    fn forecast_unprojectable_inputs_yield_none() {
        assert_eq!(project_end_of_day(&v_int(-5), &v_int(8), &v_int(24)), None);
        assert_eq!(project_end_of_day(&v_int(80), &v_int(0), &v_int(24)), None);
        assert_eq!(project_end_of_day(&v_int(80), &v_int(-2), &v_int(24)), None);
        assert_eq!(project_end_of_day(&v_str("lots"), &v_int(8), &v_int(24)), None);
        assert_eq!(project_end_of_day(&v_int(80), &v_int(8), &v_int(0)), None);
    }

    #[test]
    fn forecast_confidence_comes_from_elapsed_hours_alone() {
        assert_eq!(confidence_for(&v_int(2)), "low");
        assert_eq!(confidence_for(&v_int(4)), "medium");
        assert_eq!(confidence_for(&v_int(8)), "medium");
        assert_eq!(confidence_for(&v_int(12)), "high");
        assert_eq!(confidence_for(&v_int(0)), "unknown");
        assert_eq!(confidence_for(&v_str("soon")), "unknown");
    }

    // --- test_intel_budget_forecast.py: ForecastEntryTest
    #[test]
    fn forecast_entry_carries_basis_and_verdict() {
        let entry = forecast_entry(&v_str("spark"), &v_int(80), &v_int(100), &v_int(8), &v_int(24))
            .unwrap();
        assert_eq!(entry.projected, 240.0);
        assert!(entry.over_cap);
        assert_eq!(entry.confidence, "medium");
        assert!(entry.basis.contains("8 hours of ledger"));
    }

    #[test]
    fn forecast_within_cap_entry_has_no_breach() {
        let entry = forecast_entry(&v_str("spark"), &v_int(20), &v_int(100), &v_int(8), &v_int(24))
            .unwrap();
        assert_eq!(entry.projected, 60.0);
        assert!(!entry.over_cap);
    }

    #[test]
    fn forecast_unusable_entries_yield_none() {
        assert_eq!(
            forecast_entry(&v_str(""), &v_int(80), &v_int(100), &v_int(8), &v_int(24)),
            None
        );
        assert_eq!(
            forecast_entry(&v_str("spark"), &v_int(80), &v_int(0), &v_int(8), &v_int(24)),
            None
        );
        assert_eq!(
            forecast_entry(&v_str("spark"), &v_int(80), &v_int(100), &v_int(0), &v_int(24)),
            None
        );
        assert_eq!(
            forecast_entry(&v_str("spark"), &Value::Null, &v_int(100), &v_int(8), &v_int(24)),
            None
        );
    }

    // --- test_intel_budget_forecast.py: ForecastLinesTest
    #[test]
    fn forecast_line_names_figures_basis_confidence_verdict() {
        let lines = forecast_lines(&Value::List(vec![v_dict(vec![
            ("lane", v_str("spark")),
            ("spent", v_int(80)),
            ("cap", v_int(100)),
            ("elapsed_hours", v_int(8)),
        ])]));
        assert_eq!(lines.len(), 1);
        assert!(lines[0].contains("80 spent of 100 cap"));
        assert!(lines[0].contains("projected 240"));
        assert!(lines[0].contains("8 hours of ledger"));
        assert!(lines[0].contains("medium confidence"));
        assert!(lines[0].contains("breach expected before end of day"));
        assert!(!lines[0].trim_start().starts_with('-') && !lines[0].trim_start().starts_with('*'));
    }

    #[test]
    fn forecast_within_cap_line_says_within_cap() {
        let lines = forecast_lines(&Value::List(vec![v_dict(vec![
            ("lane", v_str("spark")),
            ("spent", v_int(20)),
            ("cap", v_int(100)),
            ("elapsed_hours", v_int(8)),
        ])]));
        assert!(lines[0].contains("within cap"));
    }

    #[test]
    fn forecast_unusable_entries_and_empty_input_yield_no_lines() {
        let lines = forecast_lines(&Value::List(vec![
            v_dict(vec![
                ("lane", v_str("spark")),
                ("spent", v_int(80)),
                ("cap", v_int(100)),
                ("elapsed_hours", v_int(0)),
            ]),
            v_dict(vec![
                ("lane", v_str("")),
                ("spent", v_int(80)),
                ("cap", v_int(100)),
                ("elapsed_hours", v_int(8)),
            ]),
            v_str("not-a-dict"),
        ]));
        assert!(lines.is_empty());
        assert!(forecast_lines(&Value::List(vec![])).is_empty());
    }

    // --- test_intel_budget_forecast.py: PreemptDecisionTest
    #[test]
    fn forecast_pause_only_low_running_in_warning_lane() {
        let low = v_dict(vec![("priority", v_str("low")), ("status", v_str("running"))]);
        assert_eq!(preempt_decision(&low, "warning"), Some("pause"));
        assert_eq!(preempt_decision(&low, "ok"), None);
        assert_eq!(preempt_decision(&low, "capped"), None);
        assert_eq!(preempt_decision(&low, "unbudgeted"), None);
    }

    #[test]
    fn forecast_high_priority_never_paused() {
        let high = v_dict(vec![("priority", v_str("high")), ("status", v_str("running"))]);
        assert_eq!(preempt_decision(&high, "warning"), None);
    }

    #[test]
    fn forecast_already_paused_never_paused_twice() {
        let paused = v_dict(vec![("priority", v_str("low")), ("status", v_str("paused"))]);
        assert_eq!(preempt_decision(&paused, "warning"), None);
    }

    #[test]
    fn forecast_resume_only_when_budget_freed() {
        let paused = v_dict(vec![("priority", v_str("low")), ("status", v_str("paused"))]);
        assert_eq!(preempt_decision(&paused, "ok"), Some("resume"));
        assert_eq!(preempt_decision(&paused, "unbudgeted"), Some("resume"));
        assert_eq!(preempt_decision(&paused, "warning"), None);
        assert_eq!(preempt_decision(&paused, "capped"), None);
    }

    #[test]
    fn forecast_malformed_job_yields_none() {
        assert_eq!(preempt_decision(&Value::Null, "warning"), None);
        assert_eq!(
            preempt_decision(
                &v_dict(vec![("status", v_str("running"))]),
                "warning"
            ),
            None
        );
    }

    #[test]
    fn forecast_pause_decision_uses_the_os085_warning_band() {
        assert_eq!(
            budget_state(&budget_entry("x", v_int(80), v_int(100))),
            "warning"
        );
        assert_eq!(
            preempt_decision(
                &v_dict(vec![("priority", v_str("low")), ("status", v_str("running"))]),
                budget_state(&budget_entry("x", v_int(80), v_int(100)))
            ),
            Some("pause")
        );
    }

    #[test]
    fn forecast_preempt_record_names_job_lane_action() {
        let record = preempt_record("job-1", "spark", "paused", "lane at warning");
        assert_eq!(record.get("job"), Some(&v_str("job-1")));
        assert_eq!(record.get("lane"), Some(&v_str("spark")));
        assert_eq!(record.get("action"), Some(&v_str("paused")));
    }

    // --- test_intel_budget_forecast.py: BudgetForecastDrillTest,
    // as Rust phases (the Python drill runs as a subprocess; the
    // same five phases run here against the ported functions).
    #[test]
    fn forecast_drill_phases() {
        let lane = budget_entry("spark", v_int(80), v_int(100));
        let state = budget_state(&lane);
        assert_eq!(state, "warning");
        // Phase 1: forecast.
        let entry = forecast_entry(&v_str("spark"), &v_int(80), &v_int(100), &v_int(8), &v_int(24))
            .unwrap();
        assert_eq!(entry.projected, 240.0);
        assert!(entry.over_cap);
        assert_eq!(entry.confidence, "medium");
        assert!(entry.basis.contains("8 hours of ledger"));
        // Phase 2: preempt the low-priority running job.
        let low_job = v_dict(vec![
            ("id", v_str("job-low")),
            ("priority", v_str("low")),
            ("status", v_str("running")),
            ("progress", v_str("step 3 of 5 done")),
        ]);
        assert_eq!(preempt_decision(&low_job, state), Some("pause"));
        let paused = v_dict(vec![
            ("id", v_str("job-low")),
            ("priority", v_str("low")),
            ("status", v_str("paused")),
            ("progress", v_str("step 3 of 5 done")),
        ]);
        assert_eq!(
            paused.get("progress"),
            Some(&v_str("step 3 of 5 done"))
        );
        assert_ne!(paused.get("status"), Some(&v_str("failed")));
        let record = preempt_record("job-low", "spark", "paused", "lane at warning, low priority");
        assert_eq!(record.get("job"), Some(&v_str("job-low")));
        assert_eq!(record.get("lane"), Some(&v_str("spark")));
        assert_eq!(record.get("action"), Some(&v_str("paused")));
        // Phase 3: high-priority work is never preempted.
        let high_job = v_dict(vec![
            ("id", v_str("job-high")),
            ("priority", v_str("high")),
            ("status", v_str("running")),
            ("progress", v_str("step 1 of 2 done")),
        ]);
        assert_eq!(preempt_decision(&high_job, state), None);
        // Phase 4: budget frees, the paused job resumes cleanly.
        let freed = budget_state(&budget_entry("spark", v_int(10), v_int(100)));
        assert_eq!(freed, "ok");
        assert_eq!(preempt_decision(&paused, freed), Some("resume"));
        // Phase 5: brief line.
        let lines = forecast_lines(&Value::List(vec![v_dict(vec![
            ("lane", v_str("spark")),
            ("spent", v_int(80)),
            ("cap", v_int(100)),
            ("elapsed_hours", v_int(8)),
        ])]));
        assert_eq!(lines.len(), 1);
        assert!(lines[0].starts_with(
            "Budget forecast for lane spark: 80 spent of 100 cap, projected 240 by end of day"
        ));
        assert!(lines[0].contains("8 hours of ledger"));
        assert!(lines[0].contains("medium confidence"));
        assert!(lines[0].contains("breach expected before end of day"));
        assert!(!lines[0].trim_start().starts_with('-'));
    }

    // --- test_intel_cost.py: CostCheckTest
    #[test]
    fn cost_check_passes_with_exact_totals() {
        let (rows, rate_in, rate_out, _sources) = build_rows(&dispatch_text());
        let summary = cost_totals(&rows);
        assert!(summary.passed);
        assert_eq!(rate_in, 3.0);
        assert_eq!(rate_out, 15.0);
        assert!(close(summary.expected_usd, 0.021258), "expected {}", summary.expected_usd);
        assert!(close(summary.worst_usd, 0.12789), "worst {}", summary.worst_usd);
        assert!(
            close(summary.worst_with_boot_usd, 0.143982),
            "worst+boot {}",
            summary.worst_with_boot_usd
        );
        assert!(
            close(summary.headroom_vs_reserved_usd, 74.856018),
            "headroom {}",
            summary.headroom_vs_reserved_usd
        );
        assert_eq!(summary.breakeven_multiplier_vs_reserved, 520);
        assert_eq!(rows.len(), 5);
        assert_eq!(rows.iter().map(|r| r.count_base).sum::<i64>(), 5);
        assert_eq!(rows.iter().map(|r| r.count_worst).sum::<i64>(), 8);
    }

    #[test]
    fn cost_check_twice_identical() {
        let (first, _, _, _) = build_rows(&dispatch_text());
        let (second, _, _, _) = build_rows(&dispatch_text());
        assert_eq!(cost_totals(&first), cost_totals(&second));
        let shape = |rows: &[CostRow]| {
            rows.iter()
                .map(|r| (r.call.clone(), r.tokens_in, r.tokens_out_expected))
                .collect::<Vec<_>>()
        };
        assert_eq!(shape(&first), shape(&second));
    }

    #[test]
    fn cost_table_renders_rows_budgets_and_headroom() {
        let (rows, rate_in, rate_out, sources) = build_rows(&dispatch_text());
        let summary = cost_totals(&rows);
        let table = render_cost_table(&rows, &summary, rate_in, rate_out, &sources);
        for name in [
            "morning brief (Shot 2)",
            "dispatch plan (Shot 5)",
            "closing brief (Shot 11)",
            "alert polish (Shots 8/8b)",
            "boot brief (Shot 0, OS-004 go only)",
        ] {
            assert!(table.contains(name), "missing {}", name);
        }
        assert!(table.contains("$0.1440"));
        assert!(table.contains("$74.8560"));
        assert!(table.contains("520x"));
        assert!(table.contains("NOT pricing facts"));
        assert!(table.contains("PASS"));
    }

    // --- test_intel_brief_cost.py: BriefCostCheckTest
    #[test]
    fn brief_cost_check_passes_with_exact_totals() {
        let now = 1_793_093_400.0;
        let (rows, rate_in, rate_out) = build_brief_cost_rows(now);
        let (text, passed) = render_brief_cost_table(&rows, rate_in, rate_out);
        assert!(passed, "{}", text);
        assert!(text.contains("PASS"));
        assert_eq!(rate_in, 3.0);
        assert_eq!(rate_out, 15.0);
        assert_eq!(rows.len(), 2);
        let scored = &rows[0];
        let stress = &rows[1];
        assert_eq!(scored.variant, "scored 2-word titles");
        assert_eq!(scored.jobs, 22);
        assert_eq!(scored.template_words, 202);
        assert_eq!(scored.tokens_in, 416);
        assert_eq!(scored.tokens_out_expected, 266);
        assert!(close(scored.cost_expected, 0.005238), "scored exp {}", scored.cost_expected);
        assert!(close(scored.cost_worst, 0.016608), "scored worst {}", scored.cost_worst);
        assert_eq!(stress.variant, "long-title stress");
        assert_eq!(stress.jobs, 22);
        assert_eq!(stress.template_words, 218);
        assert_eq!(stress.tokens_in, 542);
        assert_eq!(stress.tokens_out_expected, 298);
        assert!(close(stress.cost_expected, 0.006096), "stress exp {}", stress.cost_expected);
        assert!(close(stress.cost_worst, 0.016986), "stress worst {}", stress.cost_worst);
        for row in &rows {
            assert_eq!(row.template_actual_usd, 0.0);
            assert!(row.cost_worst < 75.0);
            assert!(row.cost_worst < 150.0);
            assert!(row.template_words <= 220);
        }
        assert!(text.contains("4415x"));
    }

    #[test]
    fn brief_cost_script_main_passes() {
        let (_rows, passed, _text, code) = run_brief_cost_check(1_793_093_400.0);
        assert_eq!(code, 0);
        assert!(passed);
    }

    #[test]
    fn brief_template_record_carries_null_spend() {
        // Mirrors test_template_brief_record_carries_null_spend,
        // which calls brief.generate_brief(dry_run=True): the
        // dry-run contract is text starting with TEMPLATE,
        // model "template", spend_id null, kind passthrough.
        // Canonical generate_brief lives in brief.py (B09/B10);
        // this exercises the local dry-run equivalent.
        let snapshot = busy_snapshot(false);
        let (text, record) = template_brief_record(&snapshot, "morning", 1_793_093_400.0);
        assert!(text.starts_with("TEMPLATE"));
        assert_eq!(record.model, "template");
        assert_eq!(record.spend_id, None);
        assert_eq!(record.kind, "morning");
    }

    // --- cgroup_limits.py: derived from the module's own behavior
    // (no B20 test file covers it).
    #[test]
    fn cgroup_slice_parses_expected_values() {
        let text = "# a comment\n[Unit]\nDescription=x\n\n[Slice]\nCPUQuota=100%\nMemoryMax=1G\n\n[Service]\nExecStart=/bin/true\n";
        let values = parse_slice(text);
        assert_eq!(slice_value(&values, "CPUQuota"), Some("100%"));
        assert_eq!(slice_value(&values, "MemoryMax"), Some("1G"));
        assert!(slice_file_passes(&values));
    }

    #[test]
    fn cgroup_slice_mismatch_fails_file_phase() {
        let values = parse_slice("[Slice]\nCPUQuota=50%\nMemoryMax=1G\n");
        assert!(!slice_file_passes(&values));
        let values = parse_slice("[Slice]\nCPUQuota=100%\n");
        assert!(!slice_file_passes(&values));
    }

    #[test]
    fn cgroup_gate_needs_cpu_and_memory() {
        assert!(cgroup_gate_missing(Some("cpu memory pids")).is_empty());
        assert_eq!(cgroup_gate_missing(Some("cpu")), vec!["memory".to_string()]);
        assert_eq!(
            cgroup_gate_missing(None),
            vec!["cpu".to_string(), "memory".to_string()]
        );
        assert_eq!(
            cgroup_gate_missing(Some("")),
            vec!["cpu".to_string(), "memory".to_string()]
        );
    }

    #[test]
    fn cgroup_real_slice_file_carries_expected_values() {
        let path = format!(
            "{}/../../os/os/services/relay-workers.slice",
            env!("CARGO_MANIFEST_DIR")
        );
        let text = std::fs::read_to_string(&path).expect("slice file readable in checkout");
        assert!(slice_file_passes(&parse_slice(&text)));
    }

    // --- disk_audit.py: derived from the module's own behavior
    // (no B20 test file covers it).
    fn audit_job(
        id: &str,
        status: &str,
        title: Option<&str>,
        spec: Option<&str>,
        goal: Option<&str>,
        claim: Option<&str>,
    ) -> Value {
        let mut pairs: Vec<(&str, Value)> = vec![
            ("id", v_str(id)),
            ("status", v_str(status)),
            ("files", Value::List(vec![v_str("a.py"), v_str("b.py")])),
            ("completed_files", Value::List(vec![v_str("a.py")])),
            ("progress_notes", Value::List(vec![v_str("step 1 done")])),
            ("note", v_str("older note")),
            ("accept", v_str("tests-pass: tests.test_x")),
        ];
        if let Some(t) = title {
            pairs.push(("title", v_str(t)));
        }
        if let Some(s) = spec {
            pairs.push(("spec", v_str(s)));
        }
        if let Some(g) = goal {
            pairs.push(("goal", v_str(g)));
        }
        if let Some(c) = claim {
            pairs.push(("claim", v_str(c)));
        }
        v_dict(pairs)
    }

    #[test]
    fn disk_audit_clean_job_passes_and_reconstructs() {
        let stores = FakeStores {
            shared_keys: vec!["decide-1".to_string()],
            ..Default::default()
        };
        let job = audit_job("job-1", "open", Some("Do a thing"), Some("Goal: ship it\nbody"), None, None);
        let mut job = job;
        if let Value::Dict(pairs) = &mut job {
            pairs.push(("decisions".to_string(), Value::List(vec![v_str("decide-1")])));
        }
        let result = audit(&stores, &stores, &Value::List(vec![job])).unwrap();
        assert!(result.passed);
        assert!(result.leaks.is_empty());
        assert_eq!(result.decisions, vec!["decide-1".to_string()]);
        let out = &result.jobs[0];
        assert_eq!(out.get("goal"), Some(&v_str("ship it")));
        assert_eq!(
            out.get("remaining_files"),
            Some(&Value::List(vec![v_str("b.py")]))
        );
        assert_eq!(
            out.get("progress_notes"),
            Some(&Value::List(vec![v_str("step 1 done")]))
        );
        assert_eq!(out.get("accept"), Some(&v_str("tests-pass: tests.test_x")));
    }

    #[test]
    fn disk_audit_progress_falls_back_to_latest_note() {
        let stores = FakeStores::default();
        let job = v_dict(vec![
            ("id", v_str("job-2")),
            ("status", v_str("open")),
            ("title", v_str("T")),
            ("spec", v_str("S")),
            ("note", v_str("  latest note  ")),
        ]);
        let result = audit(&stores, &stores, &Value::List(vec![job])).unwrap();
        assert!(result.passed);
        assert_eq!(
            result.jobs[0].get("progress_notes"),
            Some(&Value::List(vec![v_str("latest note")]))
        );
    }

    #[test]
    fn disk_audit_goal_from_spec_line() {
        let stores = FakeStores::default();
        let job = v_dict(vec![
            ("id", v_str("job-3")),
            ("status", v_str("open")),
            ("title", v_str("T")),
            ("spec", v_str("Context: x\nGoal:  launch it \nSteps: y")),
        ]);
        let result = audit(&stores, &stores, &Value::List(vec![job])).unwrap();
        assert_eq!(result.jobs[0].get("goal"), Some(&v_str("launch it")));
    }

    #[test]
    fn disk_audit_spec_baton_and_claim_leaks() {
        let stores = FakeStores::default();
        let no_title = audit_job("job-4", "open", None, Some("S"), None, None);
        let result = audit(&stores, &stores, &Value::List(vec![no_title])).unwrap();
        assert!(!result.passed);
        assert!(result.leaks.iter().any(|l| l.get("layer") == Some(&v_str("spec"))));
        let claimed = audit_job("job-5", "claimed", Some("T"), Some("S"), None, None);
        let result = audit(&stores, &stores, &Value::List(vec![claimed])).unwrap();
        let layers: Vec<&str> = result
            .leaks
            .iter()
            .filter_map(|l| match l.get("layer") {
                Some(Value::Str(s)) => Some(s.as_str()),
                _ => None,
            })
            .collect();
        assert!(layers.contains(&"baton"));
        assert!(layers.contains(&"claim"));
    }

    #[test]
    fn disk_audit_record_shape_errors() {
        let stores = FakeStores::default();
        assert_eq!(
            audit(&stores, &stores, &v_str("not a list")),
            Err("job records must be a list".to_string())
        );
        let result = audit(
            &stores,
            &stores,
            &Value::List(vec![v_str("not-a-dict"), v_dict(vec![("status", v_str("open"))])]),
        )
        .unwrap();
        assert_eq!(result.leaks.len(), 2);
        assert!(result.leaks.iter().all(|l| l.get("layer") == Some(&v_str("record"))));
    }

    #[test]
    fn disk_audit_artifact_verification_layers() {
        let mut manifests: StdHashMap<String, Vec<ArtifactEntry>> = StdHashMap::new();
        manifests.insert(
            "job-1".to_string(),
            vec![ArtifactEntry {
                name: "out".to_string(),
                version: 2,
            }],
        );
        let stores = FakeStores {
            manifests,
            ..Default::default()
        };
        let job = |artifacts: Vec<&str>| {
            let mut j = audit_job("job-9", "open", Some("T"), Some("S"), None, None);
            if let Value::Dict(pairs) = &mut j {
                pairs.push((
                    "artifacts".to_string(),
                    Value::List(artifacts.into_iter().map(|a| v_str(a)).collect()),
                ));
            }
            j
        };
        let ok = audit(
            &stores,
            &stores,
            &Value::List(vec![job(vec!["artifact:job-1/out@v2"])]),
        )
        .unwrap();
        assert!(ok.passed);
        assert_eq!(
            ok.jobs[0].get("artifacts"),
            Some(&Value::List(vec![v_str("artifact:job-1/out@v2")]))
        );
        let wrong_version = audit(
            &stores,
            &stores,
            &Value::List(vec![job(vec!["artifact:job-1/out@v3"])]),
        )
        .unwrap();
        assert!(wrong_version.leaks.iter().any(|l| {
            l.get("layer") == Some(&v_str("artifacts"))
                && match l.get("detail") {
                    Some(Value::Str(d)) => d.contains("manifest holds v2"),
                    _ => false,
                }
        }));
        let missing = audit(
            &stores,
            &stores,
            &Value::List(vec![job(vec!["artifact:job-1/nope@v1"])]),
        )
        .unwrap();
        assert!(missing.leaks.iter().any(|l| {
            l.get("layer") == Some(&v_str("artifacts"))
                && match l.get("detail") {
                    Some(Value::Str(d)) => d.contains("no manifest entry"),
                    _ => false,
                }
        }));
        let unparseable = audit(
            &stores,
            &stores,
            &Value::List(vec![job(vec!["not-a-ref"])]),
        )
        .unwrap();
        assert!(unparseable.leaks.iter().any(|l| {
            l.get("layer") == Some(&v_str("artifacts"))
                && match l.get("detail") {
                    Some(Value::Str(d)) => d.contains("unparseable"),
                    _ => false,
                }
        }));
    }

    #[test]
    fn disk_audit_artifact_bytes_unreadable_is_a_leak() {
        let mut manifests: StdHashMap<String, Vec<ArtifactEntry>> = StdHashMap::new();
        manifests.insert(
            "job-1".to_string(),
            vec![ArtifactEntry {
                name: "out".to_string(),
                version: 1,
            }],
        );
        let mut unreadable = std::collections::HashSet::new();
        unreadable.insert(("job-1".to_string(), "out".to_string(), 1));
        let stores = FakeStores {
            manifests,
            unreadable_bytes: unreadable,
            ..Default::default()
        };
        let mut job = audit_job("job-9", "open", Some("T"), Some("S"), None, None);
        if let Value::Dict(pairs) = &mut job {
            pairs.push((
                "artifacts".to_string(),
                Value::List(vec![v_str("artifact:job-1/out@v1")]),
            ));
        }
        let result = audit(&stores, &stores, &Value::List(vec![job])).unwrap();
        assert!(!result.passed);
        assert!(result.leaks.iter().any(|l| {
            l.get("layer") == Some(&v_str("artifacts"))
                && match l.get("detail") {
                    Some(Value::Str(d)) => d.contains("unreadable"),
                    _ => false,
                }
        }));
    }

    #[test]
    fn disk_audit_decisions_shared_agent_and_missing() {
        let mut agent_keys: StdHashMap<String, Vec<String>> = StdHashMap::new();
        agent_keys.insert("milo".to_string(), vec!["agent-decision".to_string()]);
        let stores = FakeStores {
            shared_keys: vec!["shared-decision".to_string()],
            agent_keys,
            ..Default::default()
        };
        let mut job = audit_job(
            "job-7",
            "claimed",
            Some("T"),
            Some("Goal: g"),
            Some("g"),
            Some("milo"),
        );
        if let Value::Dict(pairs) = &mut job {
            pairs.push((
                "decisions".to_string(),
                Value::List(vec![
                    v_str("shared-decision"),
                    v_str("agent-decision"),
                    v_str("ghost-decision"),
                ]),
            ));
        }
        let result = audit(&stores, &stores, &Value::List(vec![job])).unwrap();
        assert!(!result.passed);
        assert_eq!(
            result.jobs[0].get("decisions"),
            Some(&Value::List(vec![
                v_str("shared-decision"),
                v_str("agent-decision")
            ]))
        );
        assert_eq!(result.leaks.len(), 1);
        assert_eq!(result.leaks[0].get("layer"), Some(&v_str("memory")));
    }

    #[test]
    fn disk_audit_journal_leaks_filed_once_per_agent() {
        let mut agent_errors = std::collections::HashSet::new();
        agent_errors.insert("milo".to_string());
        let stores = FakeStores {
            agent_journal_errors: agent_errors,
            ..Default::default()
        };
        let mut job1 = audit_job("job-a", "claimed", Some("T"), Some("Goal: g"), Some("g"), Some("milo"));
        let mut job2 = audit_job("job-b", "claimed", Some("T"), Some("Goal: g"), Some("g"), Some("milo"));
        for j in [&mut job1, &mut job2] {
            if let Value::Dict(pairs) = j {
                pairs.push((
                    "decisions".to_string(),
                    Value::List(vec![v_str("k")]),
                ));
            }
        }
        let result = audit(&stores, &stores, &Value::List(vec![job1, job2])).unwrap();
        let journal_leaks: Vec<&Value> = result
            .leaks
            .iter()
            .filter(|l| l.get("layer") == Some(&v_str("memory-journal")))
            .collect();
        assert_eq!(journal_leaks.len(), 1);
    }

    #[test]
    fn disk_audit_shared_journal_error_is_a_leak() {
        let stores = FakeStores {
            shared_journal_error: Some("corrupt line 3".to_string()),
            ..Default::default()
        };
        let job = audit_job("job-c", "open", Some("T"), Some("S"), None, None);
        let result = audit(&stores, &stores, &Value::List(vec![job])).unwrap();
        assert!(!result.passed);
        assert!(result.leaks.iter().any(|l| l.get("layer") == Some(&v_str("memory-journal"))));
    }

    // --- value model helpers
    #[test]
    fn value_py_repr_matches_python() {
        let v = v_dict(vec![
            ("kind", v_str("decision")),
            ("text", v_str("it's fine")),
            ("index", v_int(0)),
            ("flag", Value::Bool(true)),
            ("missing", Value::Null),
        ]);
        assert_eq!(
            v.py_repr(),
            "{'kind': 'decision', 'text': 'it\\'s fine', 'index': 0, 'flag': True, 'missing': None}"
        );
        assert_eq!(v_str("a\nb").py_repr(), "'a\\nb'");
        assert_eq!(Value::Float(240.0).py_num_str(), "240.0");
        assert_eq!(Value::Int(80).py_num_str(), "80");
    }

    #[test]
    fn value_estimate_tokens_matches_client() {
        assert_eq!(estimate_tokens(""), 0);
        assert_eq!(estimate_tokens("a"), 1);
        assert_eq!(estimate_tokens("abcd"), 1);
        assert_eq!(estimate_tokens("abcde"), 2);
    }

    #[test]
    fn value_trim_to_budget_drops_bullets_from_the_end() {
        let text = "TEMPLATE\n\nDecisions\n- one two three four five six seven eight nine ten\n- eleven twelve\n\nWatch items\n- watch one";
        let trimmed = trim_to_budget(text, 10);
        assert!(trimmed.split_whitespace().count() <= 10);
        assert!(!trimmed.contains("watch one"));
    }

    #[test]
    fn value_rate_parsing_falls_back() {
        assert_eq!(rate_value(None, 3.0, "X"), (3.0, "default".to_string()));
        assert_eq!(rate_value(Some(""), 3.0, "X"), (3.0, "default".to_string()));
        assert_eq!(rate_value(Some("junk"), 3.0, "X"), (3.0, "default".to_string()));
        assert_eq!(rate_value(Some(" 2.5 "), 3.0, "X"), (2.5, "env:X".to_string()));
    }
}

