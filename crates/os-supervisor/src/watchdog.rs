//! Watchdog loop: tick, journal watch, announcements, CLI.
//! (`os/intel/watchdog.py` loop half)
//!
//! Detectors live in `watchdog_detectors`; the budget-warning
//! detector lives in `budget_gate` (same pure function the live
//! path calls). `tick` evaluates every registered detector over
//! one snapshot and returns the alert dicts found. Never raises
//! on a bad detector: a crashing detector is skipped, because
//! one broken detector must not blind the rest of the loop.
//!
//! The canonical severity mapping (WDG-024):
//! presence-stall / progress-stall / dead-dep / missing-dep /
//! file-collision / attempt-exhaustion / rejected-dispatch /
//! system-failure = critical; lease-risk / attempt-warning /
//! budget-warning = warning; silent-room / worker-restart = info.

use serde_json::{Map, Value};

use crate::thresholds;
use crate::watchdog_detectors::{self};
pub use crate::watchdog_detectors::Alert;
use crate::budget_gate;

pub use watchdog_detectors::{
    detect_attempt_exhaustion, detect_dead_dep, detect_file_collision, detect_lease_risk,
    detect_missing_dep, detect_presence_stall, detect_progress_stall, detect_silent_room,
    detect_walk_on_workers,
};

/// WDG-024: the canonical severity mapping.
pub fn severity_by_kind(kind: &str) -> Option<&'static str> {
    match kind {
        "presence-stall" => Some("critical"),
        "progress-stall" => Some("critical"),
        "lease-risk" => Some("warning"),
        "dead-dep" => Some("critical"),
        "missing-dep" => Some("critical"),
        "file-collision" => Some("critical"),
        "attempt-warning" => Some("warning"),
        "attempt-exhaustion" => Some("critical"),
        "silent-room" => Some("info"),
        "rejected-dispatch" => Some("critical"),
        "budget-warning" => Some("warning"),
        _ => None,
    }
}

fn message_text(message: &Value) -> String {
    match message {
        Value::Object(o) => o
            .get("text")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string(),
        Value::String(s) => s.clone(),
        _ => String::new(),
    }
}

/// Scan one message for REJECTED:<job> <BAD|EXPIRED> refusal
/// lines. Yields (job_id, verdict, signed_by, rejected_by).
fn scan_rejected(text: &str) -> Vec<(String, String, String, String)> {
    let mut out = Vec::new();
    // Mirrors _REJECTED_LINE: REJECTED:(\d+) (BAD|EXPIRED)\b
    // (?:\s+signed_by=(\S+))?(?:\s+rejected_by=(\S+))?
    let bytes = text.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        match text[i..].find("REJECTED:") {
            Some(off) => {
                i += off + "REJECTED:".len();
                let rest = &text[i..];
                let mut j = 0;
                while j < rest.len() && rest.as_bytes()[j].is_ascii_digit() {
                    j += 1;
                }
                if j == 0 {
                    continue;
                }
                let job_id = rest[..j].to_string();
                let after = &rest[j..];
                // Word boundary after the verdict: the next char is
                // not a word char, or the verdict ends the line
                // (Python \b matches at end of string too).
                let boundary = |tail: &str| {
                    tail.is_empty()
                        || tail.starts_with(|c: char| !c.is_alphanumeric() && c != '_')
                };
                let verdict = if after.starts_with(" BAD") && boundary(&after[4..]) {
                    "BAD"
                } else if after.starts_with(" EXPIRED") && boundary(&after[8..]) {
                    "EXPIRED"
                } else {
                    continue;
                };
                let tail = &after[verdict.len() + 1..];
                let signed_by = field_after(tail, "signed_by=").unwrap_or_else(|| "?".to_string());
                let rejected_by =
                    field_after(tail, "rejected_by=").unwrap_or_else(|| "?".to_string());
                out.push((job_id, verdict.to_string(), signed_by, rejected_by));
            }
            None => break,
        }
    }
    out
}

fn field_after(text: &str, key: &str) -> Option<String> {
    let mut search = text;
    loop {
        let i = search.find(key)?;
        let before_ok = i == 0 || search.as_bytes()[i - 1].is_ascii_whitespace();
        if !before_ok {
            search = &search[i + key.len()..];
            continue;
        }
        let rest = &search[i + key.len()..];
        let end = rest
            .find(|c: char| c.is_whitespace())
            .unwrap_or(rest.len());
        if end == 0 {
            search = &search[i + key.len()..];
            continue;
        }
        return Some(rest[..end].to_string());
    }
}

/// INT-010: refused-dispatch detector. One critical alert per
/// (job, verdict) per tick.
pub fn detect_rejected_dispatch(snapshot: &Value, now: i64) -> Vec<Alert> {
    let messages = match snapshot.get("messages").and_then(|v| v.as_array()) {
        Some(items) => items,
        None => return Vec::new(),
    };
    let mut seen = std::collections::HashSet::new();
    let mut alerts = Vec::new();
    for message in messages {
        let text = message_text(message);
        if text.is_empty() {
            continue;
        }
        for (job_id, verdict, signed_by, rejected_by) in scan_rejected(&text) {
            let key = format!("rejected-dispatch:{job_id}:{verdict}");
            if !seen.insert(key.clone()) {
                continue;
            }
            let (explanation, suggested_fix) = crate::explanations::render(
                "rejected-dispatch",
                &[
                    ("job", job_id.clone()),
                    ("verdict", verdict.clone()),
                    ("signed_by", signed_by.clone()),
                    ("rejected_by", rejected_by.clone()),
                ]
                .into_iter()
                .collect::<std::collections::BTreeMap<_, _>>(),
            )
            .unwrap_or((key.clone(), key.clone()));
            alerts.push(
                Alert::new("rejected-dispatch", "critical")
                    .set("job", Value::String(job_id.clone()))
                    .set("verdict", Value::String(verdict))
                    .set("signed_by", Value::String(signed_by))
                    .set("rejected_by", Value::String(rejected_by))
                    .set("explanation", Value::String(explanation))
                    .set("suggested_fix", Value::String(suggested_fix))
                    .set("dedupe_key", Value::String(key))
                    .set("created_at", Value::Number(now.into())),
            );
        }
    }
    alerts
}

/// Budget warning threshold for this crate: the same
/// WATCHDOG_BUDGET_WARN_PERCENT rule (default 80).
pub fn budget_warn_percent() -> u64 {
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

fn budget_warning_alerts(snapshot: &Value, now: i64) -> Vec<Alert> {
    budget_gate::detect_budget_warning(snapshot, now, budget_warn_percent())
}

/// WDG-015: one frozen-format announcement line for an alert.
/// Format: "ALERT:<id> <kind>: <explanation>", exactly one line.
/// Only severity "critical" announces. Anything else yields None.
pub fn format_announcement(alert: &Value) -> Option<String> {
    let obj = alert.as_object()?;
    if obj.get("severity").and_then(|v| v.as_str()) != Some("critical") {
        return None;
    }
    let id = obj
        .get("id")
        .and_then(|v| v.as_str())
        .filter(|s| !s.is_empty())
        .or_else(|| {
            obj.get("dedupe_key")
                .and_then(|v| v.as_str())
                .filter(|s| !s.is_empty())
        })?;
    let kind = obj.get("kind").and_then(|v| v.as_str()).unwrap_or("alert");
    let explanation = match obj.get("explanation") {
        Some(Value::String(s)) if !s.is_empty() => s.clone(),
        _ => kind.to_string(),
    };
    let line = format!("ALERT:{id} {kind}: {explanation}");
    Some(line.split('\n').collect::<Vec<_>>().join(" "))
}

/// The announcement lines for an alert list, in list order.
pub fn announcements_for(alerts: &[Value]) -> Vec<String> {
    alerts.iter().filter_map(format_announcement).collect()
}

/// WDG-017: yield successive pages of a sequence, oldest first.
/// A non-positive page size raises (Value error as string).
pub fn paginate<T: Clone>(items: &[T], page_size: usize) -> Result<Vec<Vec<T>>, String> {
    if page_size == 0 {
        return Err("page_size must be a positive int".to_string());
    }
    Ok(items.chunks(page_size).map(|c| c.to_vec()).collect())
}

/// WDG-017: cap a snapshot's message window before a tick.
/// Returns a new snapshot whose messages are the newest
/// max_messages, plus a tick_window record. Jobs, presence,
/// caps, and alerts pass through unchanged.
pub fn cap_tick_snapshot(
    snapshot: &Value,
    max_messages: Option<usize>,
    page_size: Option<usize>,
) -> Value {
    let max = max_messages.unwrap_or_else(|| thresholds::tick_max_messages() as usize);
    let page = page_size.unwrap_or_else(|| thresholds::tick_page_size() as usize);
    let page = page.max(1);
    let mut messages: Vec<Value> = match snapshot.get("messages").and_then(|v| v.as_array()) {
        Some(items) => items.clone(),
        None => Vec::new(),
    };
    let total = messages.len();
    let mut kept: Vec<Value> = Vec::new();
    for chunk in messages.chunks(page) {
        kept.extend_from_slice(chunk);
        if kept.len() > max {
            let drop = kept.len() - max;
            kept.drain(..drop);
        }
    }
    if max == 0 {
        kept.clear();
    }
    let mut dropped = total.saturating_sub(kept.len());
    if let Some(Value::Object(prior)) = snapshot.get("tick_window") {
        if let Some(Value::Number(n)) = prior.get("messages_dropped") {
            if let Some(p) = n.as_u64() {
                dropped += p as usize;
            }
        }
    }
    messages = kept;
    let mut out = snapshot.as_object().cloned().unwrap_or_default();
    out.insert("messages".to_string(), Value::Array(messages.clone()));
    let mut window = Map::new();
    window.insert("max_messages".to_string(), Value::Number((max as u64).into()));
    window.insert("page_size".to_string(), Value::Number((page as u64).into()));
    window.insert(
        "messages_kept".to_string(),
        Value::Number((messages.len() as u64).into()),
    );
    window.insert(
        "messages_dropped".to_string(),
        Value::Number((dropped as u64).into()),
    );
    out.insert("tick_window".to_string(), Value::Object(window));
    Value::Object(out)
}

/// WDG-026: the one "now" a tick computes ages from.
/// Returns (timestamp, source): "explicit", "server_time", or
/// "wall_clock".
pub fn resolve_tick_now(snapshot: &Value, now: Option<i64>, wall_clock: i64) -> (i64, &'static str) {
    if let Some(t) = now {
        return (t, "explicit");
    }
    if let Some(server) = parse_server_time(snapshot.get("server_time").unwrap_or(&Value::Null)) {
        return (server, "server_time");
    }
    (wall_clock, "wall_clock")
}

fn parse_server_time(value: &Value) -> Option<i64> {
    match value {
        Value::Bool(_) => None,
        Value::Number(n) => n.as_i64().or_else(|| n.as_f64().map(|f| f as i64)),
        Value::String(s) => {
            let t = s.trim();
            if t.is_empty() {
                return None;
            }
            t.parse::<i64>().ok().or_else(|| t.parse::<f64>().ok().map(|f| f as i64))
        }
        Value::Array(items) if items.len() == 2 => {
            let seconds = parse_server_time(&items[0])?;
            parse_server_time(&items[1])?;
            Some(seconds)
        }
        _ => None,
    }
}

/// OS-034: the watchdog's event note for a systemd-restarted worker.
/// An INFO record, never a stall alert: severity info, so
/// format_announcement yields nothing for it.
pub fn restart_event_note(
    nick: &str,
    job_id: &str,
    now: i64,
    downtime_seconds: Option<i64>,
) -> Result<Value, String> {
    if nick.is_empty() || job_id.is_empty() {
        return Err("restart_event_note needs a nick and a job id".to_string());
    }
    let down = match downtime_seconds {
        None => "after a brief absence".to_string(),
        Some(s) => format!("after {}s down", s.max(0)),
    };
    let explanation = format!(
        "Worker {nick} on job {job_id} died and was restarted by systemd {down}; no stall alert fired because the worker is back and progressing."
    );
    let mut map = Map::new();
    map.insert("kind".to_string(), Value::String("worker-restart".to_string()));
    map.insert("severity".to_string(), Value::String("info".to_string()));
    map.insert("nick".to_string(), Value::String(nick.to_string()));
    map.insert("job".to_string(), Value::String(job_id.to_string()));
    map.insert("job_title".to_string(), Value::String(String::new()));
    map.insert("explanation".to_string(), Value::String(explanation));
    map.insert(
        "suggested_fix".to_string(),
        Value::String(
            "No action: systemd handled the death. Investigate only if restarts repeat.".to_string(),
        ),
    );
    map.insert(
        "dedupe_key".to_string(),
        Value::String(format!("worker-restart:{nick}:{job_id}")),
    );
    map.insert("created_at".to_string(), Value::Number(now.into()));
    if let Some(s) = downtime_seconds {
        map.insert("downtime_seconds".to_string(), Value::Number(s.into()));
    } else {
        map.insert("downtime_seconds".to_string(), Value::Null);
    }
    Ok(Value::Object(map))
}

// --- journal watch (OS-037) ---

pub const JOURNAL_RELAY_UNIT_PREFIX: &str = "relay-";

/// Normalize one journal entry to (unit, message, priority).
/// Accepts journalctl -o json dicts and plain-keyed equivalents,
/// plus JSON strings of either shape. None for anything
/// unusable: no invented attribution.
pub fn journal_entry_fields(entry: &Value) -> Option<(String, String, Option<i64>)> {
    let obj = match entry {
        Value::String(text) => {
            let text = text.trim();
            if text.is_empty() {
                return None;
            }
            match serde_json::from_str::<Value>(text) {
                Ok(Value::Object(o)) => o,
                _ => return None,
            }
        }
        Value::Object(o) => o.clone(),
        _ => return None,
    };
    let unit = obj
        .get("_SYSTEMD_UNIT")
        .or_else(|| obj.get("SYSTEMD_UNIT"))
        .or_else(|| obj.get("unit"))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .trim()
        .to_string();
    if unit.is_empty() {
        return None;
    }
    let message = match obj.get("MESSAGE").or_else(|| obj.get("message")) {
        Some(Value::String(s)) => s.clone(),
        Some(other) => other.to_string().trim_matches('"').to_string(),
        None => String::new(),
    };
    let priority = obj
        .get("PRIORITY")
        .or_else(|| obj.get("priority"))
        .and_then(|v| match v {
            Value::Bool(_) => None,
            Value::Number(n) => n.as_i64(),
            Value::String(s) => {
                let t = s.trim();
                if t.is_empty() {
                    None
                } else {
                    t.parse::<i64>().ok()
                }
            }
            _ => None,
        });
    Some((unit, message, priority))
}

fn journal_failure_patterns(message: &str) -> bool {
    let lower = message.to_lowercase();
    lower.contains("failed with result")
        || lower.contains("main process exited")
        || lower.contains("failed to start")
        || lower.contains("entered failed state")
}

/// OS-037: is this journal entry a relay unit failure?
pub fn journal_entry_is_failure(entry: &Value) -> bool {
    let (unit, message, priority) = match journal_entry_fields(entry) {
        Some(f) => f,
        None => return false,
    };
    if !unit.starts_with(JOURNAL_RELAY_UNIT_PREFIX) {
        return false;
    }
    if let Some(p) = priority {
        if p <= 3 {
            return true;
        }
    }
    journal_failure_patterns(&message)
}

/// Parse journalctl -o json output into normalized entries.
pub fn parse_journal_entries(text: &Value) -> Vec<(String, String, Option<i64>)> {
    let text = match text.as_str() {
        Some(t) => t,
        None => return Vec::new(),
    };
    let mut entries = Vec::new();
    for line in text.lines() {
        // journal_entry_fields parses JSON strings itself; a
        // corrupt line is skipped, never fatal.
        if let Some(fields) = journal_entry_fields(&Value::String(line.to_string())) {
            entries.push(fields);
        }
    }
    entries
}

/// OS-037: relay unit failures to one SYSTEM alert per unit.
pub fn detect_journal_failures(entries: &Value, now: i64) -> Vec<Value> {
    let parsed: Vec<(String, String, Option<i64>)> = match entries {
        Value::String(_) => parse_journal_entries(entries),
        Value::Array(items) => items
            .iter()
            .filter_map(journal_entry_fields)
            .collect(),
        _ => Vec::new(),
    };
    let mut by_unit: Vec<(String, String, usize)> = Vec::new();
    let mut index_of: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
    for (unit, message, priority) in parsed {
        if !unit.starts_with(JOURNAL_RELAY_UNIT_PREFIX) {
            continue;
        }
        let failed = match priority {
            Some(p) if p <= 3 => true,
            _ => journal_failure_patterns(&message),
        };
        if !failed {
            continue;
        }
        match index_of.get(&unit) {
            Some(&i) => by_unit[i].2 += 1,
            None => {
                index_of.insert(unit.clone(), by_unit.len());
                by_unit.push((unit, message, 1));
            }
        }
    }
    by_unit
        .into_iter()
        .map(|(unit, first, count)| {
            let excerpt = if first.chars().count() <= 300 {
                first.clone()
            } else {
                first.chars().take(297).collect::<String>() + "..."
            };
            let explanation = if excerpt.is_empty() {
                format!("System unit {unit} failed (no message logged).")
            } else {
                format!("System unit {unit} failed: {excerpt}")
            };
            serde_json::json!({
                "kind": "system-failure",
                "severity": "critical",
                "subjects": [unit],
                "unit": unit,
                "system_alert": true,
                "failure_count": count,
                "journal_message": first,
                "explanation": explanation,
                "suggested_fix": format!("Check journalctl -u {unit} for the failure, then restart the unit; the watchdog reports unit failures but never restarts units itself."),
                "dedupe_key": format!("system-failure:{unit}"),
                "created_at": now,
            })
        })
        .collect()
}

/// OS-037: one journal-watch loop iteration. Emit failures
/// are contained per alert (a failing emit never hides the next
/// unit's failure).
pub fn journal_watch_tick(
    entries: &Value,
    now: i64,
    emit: &mut dyn FnMut(Value),
) -> Vec<Value> {
    let alerts = detect_journal_failures(entries, now);
    for alert in &alerts {
        let outcome = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            emit(alert.clone());
        }));
        let _ = outcome;
    }
    alerts
}

// --- tick ---

/// Tick callbacks: emit per alert, polish switch, announce sink,
/// beat sink.
pub struct TickCallbacks<'a> {
    pub emit: Option<&'a mut dyn FnMut(Value)>,
    pub polish: Option<&'a dyn Fn(&str) -> Option<String>>,
    pub announce: Option<&'a mut dyn FnMut(String)>,
    pub beat: Option<&'a mut dyn FnMut(i64)>,
}

/// WDG-001: evaluate one snapshot, return the alerts found.
/// `wall_clock` is used only when neither explicit now nor
/// server_time resolves (WDG-026). Never raises on a bad
/// detector: a crashing detector is skipped, because one broken
/// detector must not blind the rest of the loop. A beat callback
/// that raises is swallowed, not propagated.
pub fn tick(
    snapshot: &Value,
    now: Option<i64>,
    wall_clock: i64,
    max_messages: Option<usize>,
    mut callbacks: TickCallbacks<'_>,
) -> Vec<Value> {
    let (current, _source) = resolve_tick_now(snapshot, now, wall_clock);
    let snapshot = cap_tick_snapshot(snapshot, max_messages, None);
    let mut alerts = Vec::new();
    let detectors: Vec<fn(&Value, i64) -> Vec<Alert>> = vec![
        watchdog_detectors::detect_presence_stall,
        watchdog_detectors::detect_progress_stall,
        watchdog_detectors::detect_lease_risk,
        watchdog_detectors::detect_dead_dep,
        watchdog_detectors::detect_missing_dep,
        watchdog_detectors::detect_file_collision,
        watchdog_detectors::detect_attempt_exhaustion,
        watchdog_detectors::detect_silent_room,
    ];
    for detector in detectors {
        // Contained per detector: a panic here skips the detector.
        let found = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            detector(&snapshot, current)
        }))
        .unwrap_or_default();
        for alert in found {
            push_alert(&alert, &mut alerts, &mut callbacks);
        }
    }
    for alert in detect_rejected_dispatch(&snapshot, current) {
        push_alert(&alert, &mut alerts, &mut callbacks);
    }
    for alert in budget_warning_alerts(&snapshot, current) {
        push_alert(&alert, &mut alerts, &mut callbacks);
    }
    if let Some(beat) = callbacks.beat.as_mut() {
        let outcome = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            beat(current);
        }));
        let _ = outcome;
    }
    alerts
}

fn push_alert(alert: &Alert, alerts: &mut Vec<Value>, callbacks: &mut TickCallbacks<'_>) {
    let mut map = alert.fields.clone();
    map.insert("kind".to_string(), Value::String(alert.kind.clone()));
    map.insert(
        "severity".to_string(),
        Value::String(alert.severity.clone()),
    );
    let mut record = Value::Object(map);
    if let Some(polish) = callbacks.polish {
        if let Some(Value::String(exp)) = record.get("explanation").cloned() {
            if !exp.is_empty() {
                let polished = crate::explanations::polish_explanation(&exp, Some(polish));
                record["explanation"] = Value::String(polished);
            }
        }
    }
    alerts.push(record.clone());
    if let Some(emit) = callbacks.emit.as_mut() {
        emit(record.clone());
    }
    if let Some(announce) = callbacks.announce.as_mut() {
        if let Some(line) = format_announcement(&record) {
            announce(line);
        }
    }
}

/// Tick alert dicts to plain store-shaped values (kind, severity,
/// and detector fields at top level).
pub fn alert_to_value(alert: &Alert) -> Value {
    let mut map = alert.fields.clone();
    map.insert("kind".to_string(), Value::String(alert.kind.clone()));
    map.insert("severity".to_string(), Value::String(alert.severity.clone()));
    Value::Object(map)
}

// --- CLI ---

/// CLI argument shape for the watchdog.
pub struct WatchdogArgs {
    pub once: bool,
    pub is_loop: bool,
    pub snapshot: Option<String>,
    pub journal: Option<String>,
    pub interval: f64,
    pub max_ticks: Option<u64>,
    pub room: String,
    pub announce: bool,
    pub beat: bool,
}

impl WatchdogArgs {
    /// Parse argv. Needs --once or --loop (parser error otherwise,
    /// exit 2 in the binary).
    pub fn parse(argv: &[String]) -> Result<Self, String> {
        let mut args = WatchdogArgs {
            once: false,
            is_loop: false,
            snapshot: None,
            journal: None,
            interval: 60.0,
            max_ticks: None,
            room: "main".to_string(),
            announce: false,
            beat: false,
        };
        let mut it = argv.iter().peekable();
        while let Some(arg) = it.next() {
            match arg.as_str() {
                "--once" => args.once = true,
                "--loop" => args.is_loop = true,
                "--snapshot" => {
                    args.snapshot = Some(
                        it.next()
                            .ok_or_else(|| "watchdog: --snapshot needs a value".to_string())?
                            .clone(),
                    );
                }
                "--journal" => {
                    args.journal = Some(
                        it.next()
                            .ok_or_else(|| "watchdog: --journal needs a value".to_string())?
                            .clone(),
                    );
                }
                "--interval" => {
                    args.interval = it
                        .next()
                        .ok_or_else(|| "watchdog: --interval needs a value".to_string())?
                        .parse::<f64>()
                        .map_err(|_| "watchdog: --interval must be a number".to_string())?;
                }
                "--max-ticks" => {
                    args.max_ticks = Some(
                        it.next()
                            .ok_or_else(|| "watchdog: --max-ticks needs a value".to_string())?
                            .parse::<u64>()
                            .map_err(|_| "watchdog: --max-ticks must be a number".to_string())?,
                    );
                }
                "--room" => {
                    args.room = it
                        .next()
                        .ok_or_else(|| "watchdog: --room needs a value".to_string())?
                        .clone();
                }
                "--announce" => args.announce = true,
                "--beat" => args.beat = true,
                other => return Err(format!("watchdog: unknown argument {other}")),
            }
        }
        if !args.once && !args.is_loop {
            return Err("watchdog needs --once or --loop".to_string());
        }
        Ok(args)
    }
}

fn load_snapshot_file(path: &str) -> Result<Value, String> {
    let text = std::fs::read_to_string(path)
        .map_err(|e| format!("watchdog: cannot load snapshot: {e}"))?;
    let value: Value = serde_json::from_str(&text)
        .map_err(|e| format!("watchdog: cannot load snapshot: {e}"))?;
    if value.as_object().is_none() {
        return Err("watchdog: cannot load snapshot: snapshot file must hold a JSON object".to_string());
    }
    Ok(value)
}

/// CLI entry: --once runs one tick, --loop repeats. Returns the
/// exit code (0 clean, 1 only when the snapshot/journal file is
/// unusable). Journal alerts report alongside the snapshot tick
/// (stdout only, never a bus post). --announce prints each
/// critical alert's line after the count (stdout only).
#[allow(clippy::too_many_arguments)]
pub fn cli(
    argv: &[String],
    wall_clock: i64,
    beat: &mut dyn FnMut(i64),
    out_line: &mut dyn FnMut(String),
    err_line: &mut dyn FnMut(String),
    sleep_secs: &mut dyn FnMut(f64),
) -> i32 {
    let args = match WatchdogArgs::parse(argv) {
        Ok(a) => a,
        Err(e) => {
            err_line(e);
            return 2;
        }
    };
    let snapshot = match args.snapshot.as_deref() {
        None => Value::Object(Map::new()),
        Some(path) => match load_snapshot_file(path) {
            Ok(s) => s,
            Err(e) => {
                err_line(e);
                return 1;
            }
        },
    };
    let journal_alerts = match args.journal.as_deref() {
        None => Vec::new(),
        Some(path) => match std::fs::read_to_string(path) {
            Ok(text) => journal_watch_tick(
                &Value::String(text),
                wall_clock,
                &mut |_| {},
            ),
            Err(e) => {
                err_line(format!("watchdog: cannot load journal: {e}"));
                return 1;
            }
        },
    };
    let mut report = |alerts: &[Value]| {
        out_line(format!("watchdog: {} alert(s)", alerts.len()));
        if args.announce {
            for line in announcements_for(alerts) {
                out_line(line);
            }
        }
    };
    if args.once {
        let mut alerts = tick(&snapshot, None, wall_clock, None, TickCallbacks {
            emit: None,
            polish: None,
            announce: None,
            beat: if args.beat { Some(beat) } else { None },
        });
        alerts.extend(journal_alerts);
        report(&alerts);
        return 0;
    }
    let mut count = 0u64;
    loop {
        let alerts = tick(&snapshot, None, wall_clock, None, TickCallbacks {
            emit: None,
            polish: None,
            announce: None,
            beat: if args.beat { Some(beat) } else { None },
        });
        report(&alerts);
        count += 1;
        if let Some(max) = args.max_ticks {
            if count >= max {
                break;
            }
        } else {
            break;
        }
        sleep_secs(args.interval);
    }
    0
}
