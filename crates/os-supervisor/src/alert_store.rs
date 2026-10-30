//! In-memory alert store (WDG-010/WDG-013/WDG-014/WDG-023/WDG-028).
//!
//! Canonical home is Hana's `intel` crate (`intel/store.py`,
//! B09): the Redis-backed writer, lifecycle, history index, and
//! status records. This module carries the exact store semantics
//! B21's tick-adjacent tests pin, over an in-memory map with the
//! same rules: one live record per id (defaulting to the
//! dedupe_key), cooldown dedupe advancing last_seen only,
//! fresh occurrences at/past the cooldown or after resolve,
//! open to acknowledged to resolved lifecycle, auto-resolve of
//! cleared conditions, oldest-first queries, and the WDG-028
//! status line. The tick's emit seat writes here.

use serde_json::{Map, Value};
use std::collections::BTreeMap;

pub const ALERT_SEVERITIES: &[&str] = &["critical", "warning", "info"];
pub const ALERT_STATUSES: &[&str] = &["open", "acknowledged", "resolved"];

/// Validate a WDG-010 alert record; returns the record or an
/// error string. Mirrors `store.validate_alert`.
pub fn validate_alert(record: &Map<String, Value>) -> Result<(), String> {
    for field in [
        "id", "kind", "severity", "room", "subjects", "explanation", "suggested_fix",
        "created_at", "resolved_at", "dedupe_key",
    ] {
        if !record.contains_key(field) {
            return Err(format!("alert record missing required fields: {field}"));
        }
    }
    for field in ["id", "kind", "severity", "room", "explanation", "suggested_fix", "dedupe_key"] {
        match record.get(field) {
            Some(Value::String(s)) if !s.is_empty() => {}
            _ => return Err(format!("alert record field {field:?} must be a non-empty string")),
        }
    }
    match record.get("severity").and_then(|v| v.as_str()) {
        Some("critical") | Some("warning") | Some("info") => {}
        _ => return Err("alert record severity must be one of critical/warning/info".to_string()),
    }
    match record.get("subjects") {
        Some(Value::Array(items)) if !items.is_empty() && items.iter().all(|s| matches!(s, Value::String(x) if !x.is_empty())) => {}
        _ => {
            return Err(
                "alert record subjects must be a non-empty list of non-empty strings".to_string(),
            )
        }
    }
    match record.get("created_at") {
        Some(Value::Number(n)) if n.as_i64().is_some() => {}
        _ => return Err("alert record created_at must be an int".to_string()),
    }
    match record.get("resolved_at") {
        Some(Value::Null) => {}
        Some(Value::Number(n)) if n.as_i64().is_some() => {}
        _ => return Err("alert record resolved_at must be null or an int".to_string()),
    }
    let status = record.get("status").and_then(|v| v.as_str());
    if let Some(s) = status {
        if !ALERT_STATUSES.contains(&s) {
            return Err("alert record status must be one of open/acknowledged/resolved".to_string());
        }
    }
    let acknowledged = record.get("acknowledged_at");
    let acknowledged_ok = match acknowledged {
        None | Some(Value::Null) => true,
        Some(Value::Number(n)) => n.as_i64().is_some(),
        _ => false,
    };
    if !acknowledged_ok {
        return Err("alert record acknowledged_at must be null or an int".to_string());
    }
    match status {
        Some("open") => {
            if !(matches!(acknowledged, None | Some(Value::Null))
                && matches!(record.get("resolved_at"), Some(Value::Null)))
            {
                return Err("alert record status 'open' requires null acknowledged_at and resolved_at".to_string());
            }
        }
        Some("acknowledged") => {
            if !(matches!(acknowledged, Some(Value::Number(_)))
                && matches!(record.get("resolved_at"), Some(Value::Null)))
            {
                return Err("alert record status 'acknowledged' requires an acknowledged_at and a null resolved_at".to_string());
            }
        }
        Some("resolved") => {
            if !matches!(record.get("resolved_at"), Some(Value::Number(_))) {
                return Err("alert record status 'resolved' requires a resolved_at".to_string());
            }
        }
        _ => {}
    }
    Ok(())
}

/// Lifecycle status of a record, legacy-safe.
pub fn alert_status(record: &Map<String, Value>) -> &'static str {
    match record.get("status").and_then(|v| v.as_str()) {
        Some("open") => "open",
        Some("acknowledged") => "acknowledged",
        Some("resolved") => "resolved",
        _ => {
            if !matches!(record.get("resolved_at"), None | Some(Value::Null)) {
                "resolved"
            } else if !matches!(record.get("acknowledged_at"), None | Some(Value::Null)) {
                "acknowledged"
            } else {
                "open"
            }
        }
    }
}

fn alert_subjects(detector_alert: &Map<String, Value>) -> Vec<Value> {
    if let Some(Value::Array(existing)) = detector_alert.get("subjects") {
        return existing.clone();
    }
    let mut subjects = Vec::new();
    for field in ["nick", "job", "dep", "other_job", "shared_path"] {
        if let Some(Value::String(value)) = detector_alert.get(field) {
            if !value.is_empty() && !subjects.iter().any(|s| s == value) {
                subjects.push(Value::String(value.clone()));
            }
        }
    }
    if let Some(Value::Array(claimed)) = detector_alert.get("claimed_jobs") {
        for job_id in claimed {
            let value = match job_id {
                Value::String(s) => s.clone(),
                other => other.to_string().trim_matches('"').to_string(),
            };
            if !value.is_empty() && !subjects.iter().any(|s| s == &Value::String(value.clone())) {
                subjects.push(Value::String(value));
            }
        }
    }
    subjects
}

/// Build a WDG-010 record from a watchdog detector dict.
pub fn build_alert_record(
    detector_alert: &Value,
    room: &str,
    alert_id: Option<&str>,
    now: i64,
) -> Result<Value, String> {
    let detector = detector_alert
        .as_object()
        .ok_or_else(|| "detector alert must be a dict".to_string())?;
    let mut record = detector.clone();
    let id = alert_id
        .map(|s| s.to_string())
        .or_else(|| detector.get("id").and_then(|v| v.as_str()).map(|s| s.to_string()))
        .or_else(|| {
            detector
                .get("dedupe_key")
                .and_then(|v| v.as_str())
                .map(|s| s.to_string())
        })
        .ok_or_else(|| "alert record missing required fields: id".to_string())?;
    record.insert("id".to_string(), Value::String(id));
    let clean_room = clean_room_name(room);
    let room = if clean_room.is_empty() { "main".to_string() } else { clean_room };
    record.insert("room".to_string(), Value::String(room));
    record.insert("subjects".to_string(), Value::Array(alert_subjects(detector)));
    let created_at = match detector.get("created_at").and_then(|v| v.as_i64()) {
        Some(t) => t,
        None => {
            record.insert("created_at".to_string(), Value::Number(now.into()));
            now
        }
    };
    record.insert("status".to_string(), Value::String("open".to_string()));
    record.insert("acknowledged_at".to_string(), Value::Null);
    record.insert("resolved_at".to_string(), Value::Null);
    let last_seen = match record.get("last_seen").and_then(|v| v.as_i64()) {
        Some(t) => t,
        None => {
            record.insert("last_seen".to_string(), Value::Number(created_at.into()));
            created_at
        }
    };
    let _ = last_seen;
    validate_alert(&record)?;
    Ok(Value::Object(record))
}

fn clean_room_name(room: &str) -> String {
    room.trim().to_lowercase().replace(|c: char| !(c.is_alphanumeric() || c == '-' || c == '_'), "")
}

/// The in-memory alert store: id to validated record, plus the
/// history index (id scored by created_at).
pub struct AlertStore {
    records: BTreeMap<String, Map<String, Value>>,
    index: BTreeMap<String, i64>,
    pub dedupe_cooldown_secs: u64,
    pub beat: Option<i64>,
}

impl AlertStore {
    pub fn new(dedupe_cooldown_minutes: u64) -> Self {
        AlertStore {
            records: BTreeMap::new(),
            index: BTreeMap::new(),
            dedupe_cooldown_secs: dedupe_cooldown_minutes * 60,
            beat: None,
        }
    }

    pub fn get_alert(&self, alert_id: &str) -> Option<&Map<String, Value>> {
        self.records.get(alert_id)
    }

    /// Raw storage (unvalidated, unindexed): the queryable writer
    /// is `write_alert`. Mirrors `store.put_alert`.
    pub fn put_alert(&mut self, alert_id: &str, record: Map<String, Value>) {
        self.records.insert(alert_id.to_string(), record);
    }

    /// Validate a detector alert and store it; returns the record.
    /// WDG-013 dedupe: one live record per id; a report inside
    /// the cooldown advances last_seen only; at/past the cooldown
    /// or after resolve starts a fresh occurrence.
    pub fn write_alert(
        &mut self,
        detector_alert: &Value,
        room: &str,
        alert_id: Option<&str>,
        now: i64,
    ) -> Result<Value, String> {
        let record = build_alert_record(detector_alert, room, alert_id, now)?;
        let id = record["id"].as_str().unwrap_or("").to_string();
        let created_at = record["created_at"].as_i64().unwrap_or(now);
        if let Some(existing) = self.records.get(&id).cloned() {
            let resolved = !matches!(existing.get("resolved_at"), Some(Value::Null) | None);
            if !resolved {
                let last = existing
                    .get("last_seen")
                    .and_then(|v| v.as_i64())
                    .or_else(|| existing.get("created_at").and_then(|v| v.as_i64()))
                    .unwrap_or(created_at);
                if created_at - last < self.dedupe_cooldown_secs as i64 {
                    if created_at > last {
                        let mut updated = existing.clone();
                        updated.insert("last_seen".to_string(), Value::Number(created_at.into()));
                        updated.entry("status".to_string()).or_insert(Value::String("open".to_string()));
                        updated
                            .entry("acknowledged_at".to_string())
                            .or_insert(Value::Null);
                        self.records.insert(id.clone(), updated.clone());
                        self.index_alert(&id, created_at);
                        return Ok(Value::Object(updated));
                    }
                    return Ok(Value::Object(existing));
                }
            }
        }
        let mut stored = record.as_object().cloned().unwrap_or_default();
        self.records.insert(id.clone(), stored.clone());
        self.index_alert(&id, created_at);
        stored = self.records.get(&id).cloned().unwrap_or(stored);
        Ok(Value::Object(stored))
    }

    fn index_alert(&mut self, id: &str, created_at: i64) {
        self.index.insert(id.to_string(), created_at);
    }

    /// WDG-023: alert history query, oldest first.
    pub fn query_alerts(
        &self,
        room: Option<&str>,
        since: Option<i64>,
        kind: Option<&str>,
    ) -> Vec<Value> {
        let mut ids: Vec<(&String, &i64)> = self.index.iter().collect();
        ids.sort_by(|a, b| a.1.cmp(b.1).then_with(|| a.0.cmp(b.0)));
        let mut out = Vec::new();
        for (id, _) in ids {
            let record = match self.records.get(id) {
                Some(r) => r,
                None => continue,
            };
            if let Some(room_filter) = room {
                if record.get("room").and_then(|v| v.as_str()) != Some(room_filter) {
                    continue;
                }
            }
            if let Some(kind_filter) = kind {
                if record.get("kind").and_then(|v| v.as_str()) != Some(kind_filter) {
                    continue;
                }
            }
            if let Some(since_ts) = since {
                match record.get("created_at").and_then(|v| v.as_i64()) {
                    Some(created) if created >= since_ts => {}
                    _ => continue,
                }
            }
            out.push(Value::Object(record.clone()));
        }
        out.sort_by(|a, b| {
            let ca = a.get("created_at").and_then(|v| v.as_i64()).unwrap_or(0);
            let cb = b.get("created_at").and_then(|v| v.as_i64()).unwrap_or(0);
            ca.cmp(&cb)
        });
        out
    }

    /// WDG-014: move an alert open to acknowledged; returns it.
    pub fn acknowledge_alert(&mut self, alert_id: &str, now: i64) -> Result<Option<Value>, String> {
        let record = match self.records.get(alert_id).cloned() {
            Some(r) => r,
            None => return Ok(None),
        };
        match alert_status(&record) {
            "resolved" => return Err("cannot acknowledge a resolved alert".to_string()),
            "acknowledged" => return Ok(Some(Value::Object(record))),
            _ => {}
        }
        let mut updated = record;
        updated.insert("status".to_string(), Value::String("acknowledged".to_string()));
        updated.insert("acknowledged_at".to_string(), Value::Number(now.into()));
        updated.entry("resolved_at".to_string()).or_insert(Value::Null);
        validate_alert(&updated).map_err(|e| e)?;
        self.records.insert(alert_id.to_string(), updated.clone());
        Ok(Some(Value::Object(updated)))
    }

    /// WDG-014: move an alert open/acknowledged to resolved.
    pub fn resolve_alert(&mut self, alert_id: &str, now: i64) -> Option<Value> {
        let record = self.records.get(alert_id).cloned()?;
        if alert_status(&record) == "resolved" {
            return Some(Value::Object(record));
        }
        let mut updated = record;
        updated.insert("status".to_string(), Value::String("resolved".to_string()));
        updated.insert("resolved_at".to_string(), Value::Number(now.into()));
        updated
            .entry("acknowledged_at".to_string())
            .or_insert(Value::Null);
        if validate_alert(&updated).is_err() {
            return None;
        }
        self.records.insert(alert_id.to_string(), updated.clone());
        Some(Value::Object(updated))
    }

    /// WDG-014: auto-resolve the alerts a tick no longer fires.
    pub fn auto_resolve_cleared(&mut self, known_ids: &[String], live_ids: &[String], now: i64) -> Vec<Value> {
        let live: std::collections::HashSet<&str> =
            live_ids.iter().map(|s| s.as_str()).collect();
        let mut resolved = Vec::new();
        for alert_id in known_ids {
            if live.contains(alert_id.as_str()) {
                continue;
            }
            let needs = match self.records.get(alert_id) {
                Some(r) => alert_status(r) != "resolved",
                None => false,
            };
            if needs {
                if let Some(record) = self.resolve_alert(alert_id, now) {
                    resolved.push(record);
                }
            }
        }
        resolved
    }

    /// WDG-016: renew the self-heartbeat key.
    pub fn wd_self_beat(&mut self, now: i64) {
        self.beat = Some(now);
    }

    /// Age of the self-heartbeat, or None when never beaten.
    pub fn wd_self_beat_age(&self, now: i64) -> Option<i64> {
        self.beat.map(|b| now - b)
    }

    /// WDG-028: the watchdog status line, as a record.
    pub fn build_watchdog_status(&self, room: &str, ts: i64) -> Value {
        let mut counts = Map::new();
        counts.insert("critical".to_string(), Value::Number(0.into()));
        counts.insert("warning".to_string(), Value::Number(0.into()));
        counts.insert("info".to_string(), Value::Number(0.into()));
        let rank = |s: &str| match s {
            "critical" => Some(0),
            "warning" => Some(1),
            "info" => Some(2),
            _ => None,
        };
        let mut open_count = 0u64;
        let mut resolved_count = 0u64;
        let mut total = 0u64;
        let mut best: Option<(u8, bool, i64, String)> = None;
        for record in self.records.values() {
            total += 1;
            if alert_status(record) == "resolved" {
                resolved_count += 1;
                continue;
            }
            open_count += 1;
            let severity = record.get("severity").and_then(|v| v.as_str()).unwrap_or("");
            let r = match rank(severity) {
                Some(r) => r,
                None => continue,
            };
            let key = format!("{severity}");
            if let Some(Value::Number(n)) = counts.get(&key) {
                counts.insert(key, Value::Number((n.as_u64().unwrap_or(0) + 1).into()));
            }
            let alert_id = match record.get("id").and_then(|v| v.as_str()) {
                Some(id) if !id.is_empty() => id.to_string(),
                _ => continue,
            };
            let created = record.get("created_at").and_then(|v| v.as_i64());
            let candidate = (
                r,
                created.is_none(),
                created.unwrap_or(0),
                alert_id.clone(),
            );
            if best.as_ref().map(|b| candidate < *b).unwrap_or(true) {
                best = Some(candidate);
            }
        }
        let top_alert = best.map(|(_, _, _, id)| id);
        let line = format!(
            "Watchdog: {} critical, {} warning, {} info open{}",
            counts["critical"].as_u64().unwrap_or(0),
            counts["warning"].as_u64().unwrap_or(0),
            counts["info"].as_u64().unwrap_or(0),
            match &top_alert {
                Some(id) => format!(" - top alert: {id}"),
                None => " - no open alerts".to_string(),
            }
        );
        serde_json::json!({
            "room": if clean_room_name(room).is_empty() { "main".to_string() } else { clean_room_name(room) },
            "ts": ts,
            "counts": counts,
            "open": open_count,
            "resolved": resolved_count,
            "total": total,
            "top_alert": top_alert.map(Value::String).unwrap_or(Value::Null),
            "line": line,
        })
    }
}
