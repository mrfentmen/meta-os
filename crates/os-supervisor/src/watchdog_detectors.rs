//! Silent-failure detectors (WDG workstream, Milo).
//! (`os/intel/watchdog.py`)
//!
//! Watches claims, leases, and heartbeats through ingest
//! snapshots; flags stalled workers, dead dependencies, and file
//! collisions as alert records with a plain explanation and a
//! suggested fix. Thresholds live in `thresholds`. The watchdog
//! never mutates job state - it alerts; humans (or mos tick) act.
//!
//! Detectors land one per task and register themselves in
//! DETECTORS; the loop itself never hardcodes a detector. The
//! store writer, the Spark polish client, the announce gate, and
//! the beat writer are caller-supplied callbacks: this loop posts
//! nothing and writes nothing on its own. Every age in a tick is
//! computed from one resolved now (WDG-026): an explicit now
//! wins, else the snapshot's server_time, else the wall clock.

use serde_json::{Map, Value};

use crate::explanations;
use crate::thresholds;

/// One detector alert in detector-dict shape.
#[derive(Debug, Clone)]
pub struct Alert {
    pub kind: String,
    pub severity: String,
    pub fields: Map<String, Value>,
}

impl Alert {
    pub fn new(kind: &str, severity: &str) -> Self {
        Alert {
            kind: kind.to_string(),
            severity: severity.to_string(),
            fields: Map::new(),
        }
    }

    pub fn set(mut self, key: &str, value: Value) -> Self {
        self.fields.insert(key.to_string(), value);
        self
    }

    pub fn get(&self, key: &str) -> Option<&Value> {
        if key == "kind" || key == "severity" {
            return None;
        }
        self.fields.get(key)
    }

    pub fn kind(&self) -> &str {
        &self.kind
    }

    pub fn severity(&self) -> &str {
        &self.severity
    }

    pub fn dedupe_key(&self) -> String {
        self.fields
            .get("dedupe_key")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string()
    }
}

fn explain(kind: &str, pairs: &[(&str, String)]) -> (String, String) {
    let mut fields = std::collections::BTreeMap::new();
    for (k, v) in pairs {
        fields.insert(*k, v.clone());
    }
    explanations::render(kind, &fields).unwrap_or_else(|_| (kind.to_string(), kind.to_string()))
}

fn last_activity(job: &Map<String, Value>) -> Option<i64> {
    for field in ["last_progress", "progress_at", "note_ts", "last_progress_at", "claimed_at"] {
        if let Some(Value::Number(n)) = job.get(field) {
            if let Some(v) = n.as_i64() {
                return Some(v);
            }
        }
    }
    None
}

fn snapshot_jobs(snapshot: &Value) -> Vec<Map<String, Value>> {
    match snapshot.get("jobs").and_then(|v| v.as_array()) {
        Some(items) => items
            .iter()
            .filter_map(|j| j.as_object().cloned())
            .collect(),
        None => Vec::new(),
    }
}

fn snapshot_caps(snapshot: &Value) -> Map<String, Value> {
    match snapshot.get("caps").and_then(|v| v.as_object()) {
        Some(map) => map.clone(),
        None => Map::new(),
    }
}

fn snapshot_presence(snapshot: &Value) -> Vec<String> {
    match snapshot.get("presence") {
        Some(Value::Array(items)) => items
            .iter()
            .filter_map(|v| v.as_str().map(|s| s.to_string()))
            .collect(),
        _ => Vec::new(),
    }
}

/// WDG-002: presence-stall detector.
pub fn detect_presence_stall(snapshot: &Value, now: i64) -> Vec<Alert> {
    let caps = snapshot_caps(snapshot);
    let present: std::collections::HashSet<String> =
        snapshot_presence(snapshot).into_iter().collect();
    let threshold = thresholds::stall_minutes() as i64 * 60;
    let mut alerts = Vec::new();
    for job in snapshot_jobs(snapshot) {
        if job.get("status").and_then(|v| v.as_str()) != Some("claimed") {
            continue;
        }
        let nick = match job.get("claim").and_then(|v| v.as_str()) {
            Some(n) if !n.is_empty() => n.to_string(),
            _ => continue,
        };
        if !caps.contains_key(&nick) || present.contains(&nick) {
            continue;
        }
        let last = match last_activity(&job) {
            Some(t) => t,
            None => continue,
        };
        let age = now - last;
        if age <= threshold {
            continue;
        }
        let job_id = job.get("id").and_then(|v| v.as_str()).unwrap_or("").to_string();
        let (explanation, suggested_fix) = explain(
            "presence-stall",
            &[
                ("nick", nick.clone()),
                ("job", job_id.clone()),
                ("stall_minutes", thresholds::stall_minutes().to_string()),
                ("age_minutes", (age / 60).to_string()),
            ],
        );
        alerts.push(
            Alert::new("presence-stall", "critical")
                .set("nick", Value::String(nick.clone()))
                .set("job", Value::String(job_id.clone()))
                .set(
                    "job_title",
                    job.get("title").cloned().unwrap_or(Value::String(String::new())),
                )
                .set("last_progress_age_seconds", Value::Number(age.into()))
                .set("last_progress_age_minutes", Value::Number((age / 60).into()))
                .set("explanation", Value::String(explanation))
                .set("suggested_fix", Value::String(suggested_fix))
                .set(
                    "dedupe_key",
                    Value::String(format!("presence-stall:{nick}:{job_id}")),
                )
                .set("created_at", Value::Number(now.into())),
        );
    }
    alerts
}

/// WDG-003: progress-stall detector.
pub fn detect_progress_stall(snapshot: &Value, now: i64) -> Vec<Alert> {
    let caps = snapshot_caps(snapshot);
    let present: std::collections::HashSet<String> =
        snapshot_presence(snapshot).into_iter().collect();
    let threshold = thresholds::progress_stall_minutes() as i64 * 60;
    let mut alerts = Vec::new();
    for job in snapshot_jobs(snapshot) {
        if job.get("status").and_then(|v| v.as_str()) != Some("claimed") {
            continue;
        }
        let nick = match job.get("claim").and_then(|v| v.as_str()) {
            Some(n) if !n.is_empty() => n.to_string(),
            _ => continue,
        };
        if !caps.contains_key(&nick) || !present.contains(&nick) {
            continue;
        }
        let last = match last_activity(&job) {
            Some(t) => t,
            None => continue,
        };
        let age = now - last;
        if age <= threshold {
            continue;
        }
        let job_id = job.get("id").and_then(|v| v.as_str()).unwrap_or("").to_string();
        let (explanation, suggested_fix) = explain(
            "progress-stall",
            &[
                ("nick", nick.clone()),
                ("job", job_id.clone()),
                ("age_minutes", (age / 60).to_string()),
                ("window_minutes", thresholds::progress_stall_minutes().to_string()),
            ],
        );
        alerts.push(
            Alert::new("progress-stall", "critical")
                .set("nick", Value::String(nick.clone()))
                .set("job", Value::String(job_id.clone()))
                .set(
                    "job_title",
                    job.get("title").cloned().unwrap_or(Value::String(String::new())),
                )
                .set("last_progress_age_seconds", Value::Number(age.into()))
                .set("last_progress_age_minutes", Value::Number((age / 60).into()))
                .set("explanation", Value::String(explanation))
                .set("suggested_fix", Value::String(suggested_fix))
                .set(
                    "dedupe_key",
                    Value::String(format!("progress-stall:{nick}:{job_id}")),
                )
                .set("created_at", Value::Number(now.into())),
        );
    }
    alerts
}

/// WDG-025: walk-on worker tracking records (not a detector).
pub fn detect_walk_on_workers(snapshot: &Value, now: i64) -> Vec<Alert> {
    let caps = snapshot_caps(snapshot);
    let mut records = Vec::new();
    for job in snapshot_jobs(snapshot) {
        if job.get("status").and_then(|v| v.as_str()) != Some("claimed") {
            continue;
        }
        let nick = match job.get("claim").and_then(|v| v.as_str()) {
            Some(n) if !n.is_empty() => n.to_string(),
            _ => continue,
        };
        if caps.contains_key(&nick) {
            continue;
        }
        let last = last_activity(&job);
        let age = last.map(|t| now - t);
        let job_id = job.get("id").and_then(|v| v.as_str()).unwrap_or("").to_string();
        let mut record = Alert::new("walk-on-worker", "tracking")
            .set("nick", Value::String(nick))
            .set("job", Value::String(job_id))
            .set(
                "job_title",
                job.get("title").cloned().unwrap_or(Value::String(String::new())),
            )
            .set("tracked_from", Value::String("jobs".to_string()))
            .set("created_at", Value::Number(now.into()));
        record = record.set(
            "last_progress_age_seconds",
            age.map(|a| Value::Number(a.into())).unwrap_or(Value::Null),
        );
        record = record.set(
            "last_progress_age_minutes",
            age.map(|a| Value::Number((a / 60).into())).unwrap_or(Value::Null),
        );
        records.push(record);
    }
    records
}

/// WDG-004: lease-risk detector.
pub fn detect_lease_risk(snapshot: &Value, now: i64) -> Vec<Alert> {
    let window = thresholds::lease_risk_window_minutes() as i64 * 60;
    let quiet = thresholds::lease_risk_quiet_minutes() as i64 * 60;
    let mut alerts = Vec::new();
    for job in snapshot_jobs(snapshot) {
        if job.get("status").and_then(|v| v.as_str()) != Some("claimed") {
            continue;
        }
        let lease_until = match job.get("lease_until").and_then(|v| v.as_i64()) {
            Some(v) => v,
            None => continue,
        };
        let seconds_to_expiry = lease_until - now;
        if seconds_to_expiry <= 0 || seconds_to_expiry > window {
            continue;
        }
        let mut heartbeat: Option<i64> = None;
        for field in ["heartbeat_at", "last_heartbeat"] {
            if let Some(Value::Number(n)) = job.get(field) {
                if let Some(v) = n.as_i64() {
                    heartbeat = Some(v);
                    break;
                }
            }
        }
        let heartbeat = heartbeat.unwrap_or_else(|| {
            let lease = job
                .get("lease")
                .and_then(|v| v.as_i64())
                .unwrap_or(thresholds::LEASE_DEFAULT_SECONDS as i64);
            lease_until - lease
        });
        if now - heartbeat < quiet {
            continue;
        }
        let nick = job
            .get("claim")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let job_id = job.get("id").and_then(|v| v.as_str()).unwrap_or("").to_string();
        let (explanation, suggested_fix) = explain(
            "lease-risk",
            &[
                ("job", job_id.clone()),
                ("nick", nick.clone()),
                ("minutes_to_expiry", (seconds_to_expiry / 60).to_string()),
                ("quiet_minutes", thresholds::lease_risk_quiet_minutes().to_string()),
            ],
        );
        alerts.push(
            Alert::new("lease-risk", "warning")
                .set("nick", Value::String(nick.clone()))
                .set("job", Value::String(job_id.clone()))
                .set(
                    "job_title",
                    job.get("title").cloned().unwrap_or(Value::String(String::new())),
                )
                .set(
                    "seconds_to_expiry",
                    Value::Number(seconds_to_expiry.into()),
                )
                .set(
                    "minutes_to_expiry",
                    Value::Number((seconds_to_expiry / 60).into()),
                )
                .set(
                    "last_heartbeat_age_seconds",
                    Value::Number((now - heartbeat).into()),
                )
                .set("explanation", Value::String(explanation))
                .set("suggested_fix", Value::String(suggested_fix))
                .set(
                    "dedupe_key",
                    Value::String(format!("lease-risk:{nick}:{job_id}")),
                )
                .set("created_at", Value::Number(now.into())),
        );
    }
    alerts
}

fn parse_deps(value: &Value) -> Vec<String> {
    match value {
        Value::Array(items) => items
            .iter()
            .map(|d| match d {
                Value::String(s) => s.trim().to_string(),
                other => other.to_string().trim().trim_matches('"').to_string(),
            })
            .filter(|d| !d.is_empty())
            .collect(),
        Value::String(s) => s
            .split(',')
            .map(|d| d.trim().to_string())
            .filter(|d| !d.is_empty())
            .collect(),
        _ => Vec::new(),
    }
}

/// WDG-005: dead-dependency detector.
pub fn detect_dead_dep(snapshot: &Value, now: i64) -> Vec<Alert> {
    let jobs = snapshot_jobs(snapshot);
    let mut by_id = std::collections::HashMap::new();
    for job in &jobs {
        if let Some(id) = job.get("id").and_then(|v| v.as_str()) {
            by_id.entry(id.to_string()).or_insert(job);
        }
    }
    let mut alerts = Vec::new();
    for job in &jobs {
        if !matches!(
            job.get("status").and_then(|v| v.as_str()),
            Some("open") | Some("claimed")
        ) {
            continue;
        }
        let job_id = job.get("id").and_then(|v| v.as_str()).unwrap_or("").to_string();
        for dep_id in parse_deps(job.get("deps").unwrap_or(&Value::Null)) {
            let dep = match by_id.get(&dep_id) {
                Some(d) => d,
                None => continue,
            };
            let dep_status = dep.get("status").and_then(|v| v.as_str()).unwrap_or("");
            if dep_status != "blocked" && dep_status != "failed-final" {
                continue;
            }
            let note = dep.get("note").and_then(|v| v.as_str()).unwrap_or("");
            let reason = if !note.is_empty() {
                note.to_string()
            } else {
                dep_status.to_string()
            };
            let blocking_note = if !note.is_empty() {
                format!(" Blocking reason: {note}")
            } else {
                String::new()
            };
            let (explanation, suggested_fix) = explain(
                "dead-dep",
                &[
                    ("job", job_id.clone()),
                    ("dep", dep_id.clone()),
                    ("dep_status", dep_status.to_string()),
                    ("blocking_note", blocking_note),
                ],
            );
            alerts.push(
                Alert::new("dead-dep", "critical")
                    .set(
                        "nick",
                        job.get("claim").cloned().unwrap_or(Value::String(String::new())),
                    )
                    .set("job", Value::String(job_id.clone()))
                    .set(
                        "job_title",
                        job.get("title").cloned().unwrap_or(Value::String(String::new())),
                    )
                    .set("dep", Value::String(dep_id.clone()))
                    .set("dep_status", Value::String(dep_status.to_string()))
                    .set("blocking_reason", Value::String(reason))
                    .set("explanation", Value::String(explanation))
                    .set("suggested_fix", Value::String(suggested_fix))
                    .set(
                        "dedupe_key",
                        Value::String(format!("dead-dep:{job_id}:{dep_id}")),
                    )
                    .set("created_at", Value::Number(now.into())),
            );
        }
    }
    alerts
}

/// WDG-006: missing-dependency detector.
pub fn detect_missing_dep(snapshot: &Value, now: i64) -> Vec<Alert> {
    let jobs = snapshot_jobs(snapshot);
    let known: std::collections::HashSet<String> = jobs
        .iter()
        .filter_map(|j| j.get("id").and_then(|v| v.as_str()).map(|s| s.to_string()))
        .collect();
    let mut alerts = Vec::new();
    for job in &jobs {
        if !matches!(
            job.get("status").and_then(|v| v.as_str()),
            Some("open") | Some("claimed")
        ) {
            continue;
        }
        let job_id = job.get("id").and_then(|v| v.as_str()).unwrap_or("").to_string();
        for dep_id in parse_deps(job.get("deps").unwrap_or(&Value::Null)) {
            if known.contains(&dep_id) {
                continue;
            }
            let (explanation, suggested_fix) = explain(
                "missing-dep",
                &[("job", job_id.clone()), ("dep", dep_id.clone())],
            );
            alerts.push(
                Alert::new("missing-dep", "critical")
                    .set(
                        "nick",
                        job.get("claim").cloned().unwrap_or(Value::String(String::new())),
                    )
                    .set("job", Value::String(job_id.clone()))
                    .set(
                        "job_title",
                        job.get("title").cloned().unwrap_or(Value::String(String::new())),
                    )
                    .set("dep", Value::String(dep_id.clone()))
                    .set("explanation", Value::String(explanation))
                    .set("suggested_fix", Value::String(suggested_fix))
                    .set(
                        "dedupe_key",
                        Value::String(format!("missing-dep:{job_id}:{dep_id}")),
                    )
                    .set("created_at", Value::Number(now.into())),
            );
        }
    }
    alerts
}

fn parse_files(value: &Value) -> Vec<String> {
    let raw: Vec<String> = match value {
        Value::Array(items) => items
            .iter()
            .map(|f| match f {
                Value::String(s) => s.trim().to_string(),
                other => other.to_string().trim().trim_matches('"').to_string(),
            })
            .filter(|f| !f.is_empty())
            .collect(),
        Value::String(s) => s
            .split(',')
            .map(|f| f.trim().to_string())
            .filter(|f| !f.is_empty())
            .collect(),
        _ => Vec::new(),
    };
    let mut seen = std::collections::HashSet::new();
    let mut out = Vec::new();
    for path in raw {
        if seen.insert(path.clone()) {
            out.push(path);
        }
    }
    out
}

/// WDG-007: file-collision detector.
pub fn detect_file_collision(snapshot: &Value, now: i64) -> Vec<Alert> {
    let jobs = snapshot_jobs(snapshot);
    let claimed: Vec<&Map<String, Value>> = jobs
        .iter()
        .filter(|j| j.get("status").and_then(|v| v.as_str()) == Some("claimed"))
        .collect();
    let done_branches: Vec<&Map<String, Value>> = jobs
        .iter()
        .filter(|j| {
            j.get("status").and_then(|v| v.as_str()) == Some("done")
                && matches!(j.get("branch").and_then(|v| v.as_str()), Some(b) if !b.is_empty())
        })
        .collect();
    let mut alerts = Vec::new();
    let push_alert = |first: &Map<String, Value>,
                          second: &Map<String, Value>,
                          path: &str,
                          other_status: Option<&str>,
                          branch: Option<&str>,
                          alerts: &mut Vec<Alert>| {
        let first_id = first.get("id").and_then(|v| v.as_str()).unwrap_or("").to_string();
        let second_id = second.get("id").and_then(|v| v.as_str()).unwrap_or("").to_string();
        let (kind, explanation, suggested_fix) = if other_status == Some("done") {
            let (e, s) = explain(
                "file-collision-done",
                &[
                    ("job", first_id.clone()),
                    ("other_job", second_id.clone()),
                    ("shared_path", path.to_string()),
                    ("branch", branch.unwrap_or("").to_string()),
                ],
            );
            ("file-collision", e, s)
        } else {
            let (e, s) = explain(
                "file-collision",
                &[
                    ("job", first_id.clone()),
                    ("other_job", second_id.clone()),
                    ("shared_path", path.to_string()),
                ],
            );
            ("file-collision", e, s)
        };
        alerts.push(
            Alert::new(kind, "critical")
                .set(
                    "nick",
                    first.get("claim").cloned().unwrap_or(Value::String(String::new())),
                )
                .set("job", Value::String(first_id.clone()))
                .set("other_job", Value::String(second_id.clone()))
                .set(
                    "job_title",
                    first.get("title").cloned().unwrap_or(Value::String(String::new())),
                )
                .set(
                    "other_title",
                    second.get("title").cloned().unwrap_or(Value::String(String::new())),
                )
                .set("shared_path", Value::String(path.to_string()))
                .set("explanation", Value::String(explanation))
                .set("suggested_fix", Value::String(suggested_fix))
                .set(
                    "dedupe_key",
                    Value::String(format!("file-collision:{first_id}:{second_id}:{path}")),
                )
                .set("created_at", Value::Number(now.into())),
        );
    };
    for (i, first) in claimed.iter().enumerate() {
        let first_files = parse_files(first.get("files").unwrap_or(&Value::Null));
        if first_files.is_empty() {
            continue;
        }
        for second in &claimed[i + 1..] {
            for path in &first_files {
                if parse_files(second.get("files").unwrap_or(&Value::Null)).contains(path) {
                    push_alert(first, second, path, None, None, &mut alerts);
                }
            }
        }
        for done in &done_branches {
            let branch = done.get("branch").and_then(|v| v.as_str()).unwrap_or("");
            for path in &first_files {
                if parse_files(done.get("files").unwrap_or(&Value::Null)).contains(path) {
                    push_alert(first, done, path, Some("done"), Some(branch), &mut alerts);
                }
            }
        }
    }
    alerts
}

fn as_int(value: &Value) -> Option<i64> {
    match value {
        Value::Bool(_) => None,
        Value::Number(n) => n.as_i64().or_else(|| n.as_f64().map(|f| f as i64)),
        Value::String(s) => {
            let t = s.trim();
            if t.is_empty() {
                None
            } else {
                t.parse::<i64>().ok()
            }
        }
        _ => None,
    }
}

/// WDG-008: attempt-exhaustion detector.
pub fn detect_attempt_exhaustion(snapshot: &Value, now: i64) -> Vec<Alert> {
    let mut alerts = Vec::new();
    for job in snapshot_jobs(snapshot) {
        if !matches!(
            job.get("status").and_then(|v| v.as_str()),
            Some("open") | Some("claimed") | Some("blocked") | Some("failed-final")
        ) {
            continue;
        }
        let max_attempts = match as_int(job.get("max_attempts").unwrap_or(&Value::Null)) {
            Some(m) => m,
            None => continue,
        };
        let attempts = as_int(job.get("attempts").unwrap_or(&Value::Null)).unwrap_or(0);
        let job_id = job.get("id").and_then(|v| v.as_str()).unwrap_or("").to_string();
        let nick = job
            .get("claim")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let title = job
            .get("title")
            .cloned()
            .unwrap_or(Value::String(String::new()));
        if attempts >= max_attempts {
            let (explanation, suggested_fix) = explain(
                "attempt-exhaustion",
                &[
                    ("job", job_id.clone()),
                    ("attempts", attempts.to_string()),
                    ("max_attempts", max_attempts.to_string()),
                ],
            );
            alerts.push(
                Alert::new("attempt-exhaustion", "critical")
                    .set("nick", Value::String(nick))
                    .set("job", Value::String(job_id.clone()))
                    .set("job_title", title)
                    .set("attempts", Value::Number(attempts.into()))
                    .set("max_attempts", Value::Number(max_attempts.into()))
                    .set("attempts_remaining", Value::Number(0.into()))
                    .set("explanation", Value::String(explanation))
                    .set("suggested_fix", Value::String(suggested_fix))
                    .set(
                        "dedupe_key",
                        Value::String(format!("attempt-exhaustion:{job_id}")),
                    )
                    .set("created_at", Value::Number(now.into())),
            );
        } else if attempts == max_attempts - 1 {
            let (explanation, suggested_fix) = explain(
                "attempt-warning",
                &[
                    ("job", job_id.clone()),
                    ("attempts", attempts.to_string()),
                    ("max_attempts", max_attempts.to_string()),
                ],
            );
            alerts.push(
                Alert::new("attempt-warning", "warning")
                    .set("nick", Value::String(nick))
                    .set("job", Value::String(job_id.clone()))
                    .set("job_title", title)
                    .set("attempts", Value::Number(attempts.into()))
                    .set("max_attempts", Value::Number(max_attempts.into()))
                    .set("attempts_remaining", Value::Number(1.into()))
                    .set("explanation", Value::String(explanation))
                    .set("suggested_fix", Value::String(suggested_fix))
                    .set(
                        "dedupe_key",
                        Value::String(format!("attempt-warning:{job_id}")),
                    )
                    .set("created_at", Value::Number(now.into())),
            );
        }
    }
    alerts
}

/// WDG-009: silent-room detector (informational, never an alert).
pub fn detect_silent_room(snapshot: &Value, now: i64) -> Vec<Alert> {
    let jobs = snapshot_jobs(snapshot);
    let claimed: Vec<&Map<String, Value>> = jobs
        .iter()
        .filter(|j| j.get("status").and_then(|v| v.as_str()) == Some("claimed"))
        .collect();
    if claimed.is_empty() {
        return Vec::new();
    }
    let messages = match snapshot.get("messages").and_then(|v| v.as_array()) {
        Some(items) => items,
        None => return Vec::new(),
    };
    let mut last_ts: Option<i64> = None;
    for message in messages {
        let ts = match message.as_object() {
            Some(o) => as_int(o.get("ts").unwrap_or(&Value::Null)),
            None => continue,
        };
        if let Some(t) = ts {
            if last_ts.map(|l| t > l).unwrap_or(true) {
                last_ts = Some(t);
            }
        }
    }
    let last_ts = match last_ts {
        Some(t) => t,
        None => return Vec::new(),
    };
    let age = now - last_ts;
    if age <= thresholds::silent_room_minutes() as i64 * 60 {
        return Vec::new();
    }
    let claimed_ids: Vec<String> = claimed
        .iter()
        .map(|j| j.get("id").and_then(|v| v.as_str()).unwrap_or("").to_string())
        .collect();
    let room = snapshot.get("room").and_then(|v| v.as_str());
    let dedupe_key = match room {
        Some(r) if !r.is_empty() => format!("silent-room:{r}"),
        _ => "silent-room".to_string(),
    };
    let (explanation, suggested_fix) = explain(
        "silent-room",
        &[
            ("claimed_ids", claimed_ids.join(", ")),
            ("age_minutes", (age / 60).to_string()),
            ("window_minutes", thresholds::silent_room_minutes().to_string()),
        ],
    );
    let mut record = Alert::new("silent-room", "info")
        .set("claimed_jobs", Value::Array(claimed_ids.iter().map(|s| Value::String(s.clone())).collect()))
        .set("claimed_count", Value::Number((claimed_ids.len() as u64).into()))
        .set("last_message_age_seconds", Value::Number(age.into()))
        .set("last_message_age_minutes", Value::Number((age / 60).into()))
        .set("explanation", Value::String(explanation))
        .set("suggested_fix", Value::String(suggested_fix))
        .set("dedupe_key", Value::String(dedupe_key))
        .set("created_at", Value::Number(now.into()));
    if let Some(r) = room {
        if !r.is_empty() {
            record = record.set("room", Value::String(r.to_string()));
        }
    }
    vec![record]
}
