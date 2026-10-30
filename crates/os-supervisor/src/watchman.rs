//! OS-118 relay-watchman, the resident bell for one machine
//! (`os/os/watchman/relay_watchman.py`).
//!
//! A small CLI program, not an agent. It watches the job queue
//! for work addressed to this machine's agents, watches those
//! agents' heartbeats once they are working, and rings the bell:
//! wake events for sleeping agents with newly posted jobs, nudge
//! events for workers whose heartbeat has gone stale on a claimed
//! job.
//!
//! Source of truth, stated first: job state only. `tick` takes
//! no bus message counter, reads no message list, and counts no
//! messages. Statuses that never ring: anything but open (wake)
//! and claimed (nudge). Done, cancelled, blocked, and
//! failed-final jobs are silent, as are malformed records and
//! jobs addressed to agents this machine does not know.

use serde_json::{Map, Value};
use std::collections::{BTreeMap, HashSet};

pub const DEFAULT_INTERVAL_SECONDS: u64 = 10;
pub const DEFAULT_HEARTBEAT_STALE_SECONDS: i64 = 300;

fn text(value: &Value) -> Option<String> {
    match value {
        Value::String(s) => {
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

fn num(value: &Value) -> Option<i64> {
    match value {
        Value::Number(n) => n.as_i64(),
        _ => None,
    }
}

/// Who a job is addressed to, from addressed_to, then to.
/// Mirrors `relay_watchman.addressed_to` (and intel/wake.py's
/// rule): missing or empty fields mean unaddressed, never a
/// guess.
pub fn addressed_to(job: &Map<String, Value>) -> Option<String> {
    for field in ["addressed_to", "to"] {
        if let Some(nick) = job.get(field).and_then(text) {
            return Some(nick);
        }
    }
    None
}

/// Agents input to {nick: record}. Accepts a dict or a list.
/// Unregistered agents (registered False) are dropped; records
/// without a nick are dropped. Input is never mutated: a fresh
/// map is returned.
pub fn normalize_agents(agents: &Value) -> BTreeMap<String, Map<String, Value>> {
    let mut out = BTreeMap::new();
    let items: Vec<(Value, Value)> = match agents {
        Value::Object(map) => map
            .iter()
            .map(|(k, v)| (Value::String(k.clone()), v.clone()))
            .collect(),
        Value::Array(list) => list
            .iter()
            .filter_map(|rec| {
                rec.get("nick")
                    .map(|nick| (nick.clone(), rec.clone()))
            })
            .collect(),
        _ => Vec::new(),
    };
    for (nick_value, rec_value) in items {
        let nick = match text(&nick_value) {
            Some(n) => n,
            None => continue,
        };
        let mut record = match rec_value.as_object().cloned() {
            Some(o) => o,
            None => continue,
        };
        record.insert("nick".to_string(), Value::String(nick.clone()));
        if record.get("registered") == Some(&Value::Bool(false)) {
            continue;
        }
        out.insert(nick, record);
    }
    out
}

/// True when an agent has no heartbeat or a stale one.
pub fn is_sleeping(agent: &Map<String, Value>, now: i64, stale_seconds: i64) -> bool {
    match agent.get("heartbeat_at").and_then(num) {
        None => true,
        Some(hb) => now - hb > stale_seconds,
    }
}

fn wake_key(job_id: &str) -> String {
    format!("wake:{job_id}")
}

fn nudge_key(job_id: &str, heartbeat: i64) -> String {
    format!("nudge:{job_id}:{heartbeat}")
}

/// One watch cycle. Returns (events, new_rung_keys).
/// Pure: no I/O, no counter input, no mutation of jobs, agents,
/// or the ledger.
pub fn tick(
    jobs: &[Value],
    agents: &BTreeMap<String, Map<String, Value>>,
    ledger: &HashSet<String>,
    now: i64,
    heartbeat_stale_seconds: i64,
) -> (Vec<Value>, Vec<String>) {
    let mut events = Vec::new();
    let mut new_keys = Vec::new();
    for job in jobs {
        let record = match job.as_object() {
            Some(o) => o,
            None => continue,
        };
        let job_id = match record.get("id").and_then(text) {
            Some(id) => id,
            None => continue,
        };
        let status = record.get("status").and_then(text);
        match status.as_deref() {
            Some("open") => {
                let nick = match addressed_to(record) {
                    Some(n) => n,
                    None => continue,
                };
                let agent = match agents.get(&nick) {
                    Some(a) => a,
                    None => continue,
                };
                if !is_sleeping(agent, now, heartbeat_stale_seconds) {
                    continue;
                }
                let key = wake_key(&job_id);
                if ledger.contains(&key) {
                    continue;
                }
                let mut event = Map::new();
                event.insert("kind".to_string(), Value::String("wake".to_string()));
                event.insert("job_id".to_string(), Value::String(job_id.clone()));
                event.insert("agent".to_string(), Value::String(nick));
                event.insert(
                    "title".to_string(),
                    record
                        .get("title")
                        .and_then(text)
                        .map(Value::String)
                        .unwrap_or(Value::Null),
                );
                event.insert("ts".to_string(), Value::Number(now.into()));
                events.push(Value::Object(event));
                new_keys.push(key);
            }
            Some("claimed") => {
                let claimer = match record.get("claim").and_then(text) {
                    Some(c) => c,
                    None => continue,
                };
                let agent = match agents.get(&claimer) {
                    Some(a) => a,
                    None => continue,
                };
                let heartbeat = match agent.get("heartbeat_at").and_then(num) {
                    Some(h) => h,
                    None => continue,
                };
                let age = now - heartbeat;
                if age <= heartbeat_stale_seconds {
                    continue;
                }
                let key = nudge_key(&job_id, heartbeat);
                if ledger.contains(&key) {
                    continue;
                }
                let mut event = Map::new();
                event.insert("kind".to_string(), Value::String("nudge".to_string()));
                event.insert("job_id".to_string(), Value::String(job_id.clone()));
                event.insert("agent".to_string(), Value::String(claimer));
                event.insert(
                    "heartbeat_age_seconds".to_string(),
                    Value::Number(age.into()),
                );
                event.insert(
                    "title".to_string(),
                    record
                        .get("title")
                        .and_then(text)
                        .map(Value::String)
                        .unwrap_or(Value::Null),
                );
                event.insert("ts".to_string(), Value::Number(now.into()));
                events.push(Value::Object(event));
                new_keys.push(key);
            }
            _ => continue,
        }
    }
    (events, new_keys)
}

/// One --once cycle from files. Returns the events.
/// Missing file reads as an empty snapshot with a stderr note,
/// never a crash. Malformed JSON is an error (exit 2 under
/// --once, skipped with a note per cycle under --loop).
pub fn run_once(
    jobs_path: &str,
    agents_path: &str,
    state_path: Option<&str>,
    now: i64,
    stale_seconds: i64,
) -> Result<Vec<Value>, String> {
    let jobs = load_json_file(jobs_path, "jobs")?.unwrap_or(Value::Array(Vec::new()));
    let agents = load_json_file(agents_path, "agents")?.unwrap_or(Value::Object(Map::new()));
    let jobs_list = jobs.as_array().cloned().unwrap_or_default();
    let local = normalize_agents(&agents);
    let mut ledger = HashSet::new();
    if let Some(state) = state_path {
        if std::path::Path::new(state).exists() {
            let stored = load_json_file(state, "state")?;
            if let Some(Value::Object(map)) = stored {
                if let Some(Value::Array(rung)) = map.get("rung") {
                    for key in rung {
                        if let Some(k) = key.as_str() {
                            ledger.insert(k.to_string());
                        }
                    }
                }
            }
        }
    }
    let (events, new_keys) = tick(&jobs_list, &local, &ledger, now, stale_seconds);
    if let Some(state) = state_path {
        if !new_keys.is_empty() {
            let mut merged: Vec<String> = ledger.into_iter().chain(new_keys).collect();
            merged.sort();
            merged.dedup();
            let text = serde_json::json!({"rung": merged}).to_string();
            let tmp = format!("{state}.tmp");
            std::fs::write(&tmp, text).map_err(|e| format!("watchman: cannot write state file: {e}"))?;
            std::fs::rename(&tmp, state).map_err(|e| format!("watchman: cannot write state file: {e}"))?;
        }
    }
    Ok(events)
}

fn load_json_file(path: &str, what: &str) -> Result<Option<Value>, String> {
    if !std::path::Path::new(path).exists() {
        eprintln!("watchman: {what} file missing, reading as empty: {path}");
        return Ok(None);
    }
    let text = std::fs::read_to_string(path)
        .map_err(|e| format!("watchman: cannot read {what} file {path}: {e}"))?;
    serde_json::from_str(&text)
        .map(Some)
        .map_err(|e| format!("watchman: cannot read {what} file {path}: {e}"))
}

/// CLI argument shape for relay_watchman.
pub struct WatchmanArgs {
    pub jobs_file: String,
    pub agents_file: String,
    pub state_file: Option<String>,
    pub interval: u64,
    pub heartbeat_stale_seconds: i64,
    pub once: bool,
    pub max_cycles: u64,
    pub now: i64,
}

impl WatchmanArgs {
    fn usage_error(msg: &str) -> Result<Self, String> {
        Err(format!("watchman: {msg}"))
    }

    /// Parse argv (without the program name). `--once` or `--loop`
    /// is required; bad input returns an error (exit 2).
    pub fn parse(argv: &[String]) -> Result<Self, String> {
        let mut args = WatchmanArgs {
            jobs_file: String::new(),
            agents_file: String::new(),
            state_file: None,
            interval: DEFAULT_INTERVAL_SECONDS,
            heartbeat_stale_seconds: DEFAULT_HEARTBEAT_STALE_SECONDS,
            once: false,
            max_cycles: 0,
            now: 0,
        };
        let mut mode: Option<bool> = None;
        let mut it = argv.iter().peekable();
        while let Some(arg) = it.next() {
            match arg.as_str() {
                "--jobs-file" => {
                    args.jobs_file = it.next().ok_or_else(|| "watchman: --jobs-file needs a value".to_string())?.clone();
                }
                "--agents-file" => {
                    args.agents_file = it.next().ok_or_else(|| "watchman: --agents-file needs a value".to_string())?.clone();
                }
                "--state-file" => {
                    args.state_file = Some(it.next().ok_or_else(|| "watchman: --state-file needs a value".to_string())?.clone());
                }
                "--interval" => {
                    args.interval = it
                        .next()
                        .ok_or_else(|| "watchman: --interval needs a value".to_string())?
                        .parse::<i64>()
                        .map_err(|_| "watchman: --interval must be positive".to_string())
                        .and_then(|v| {
                            if v > 0 {
                                Ok(v as u64)
                            } else {
                                Err("watchman: --interval must be positive".to_string())
                            }
                        })?;
                }
                "--heartbeat-stale-seconds" => {
                    args.heartbeat_stale_seconds = it
                        .next()
                        .ok_or_else(|| "watchman: --heartbeat-stale-seconds needs a value".to_string())?
                        .parse::<i64>()
                        .map_err(|_| "watchman: --heartbeat-stale-seconds must be non-negative".to_string())?;
                    if args.heartbeat_stale_seconds < 0 {
                        return Self::usage_error("--heartbeat-stale-seconds must be non-negative");
                    }
                }
                "--once" => mode = Some(true),
                "--loop" => mode = Some(false),
                "--max-cycles" => {
                    args.max_cycles = it
                        .next()
                        .ok_or_else(|| "watchman: --max-cycles needs a value".to_string())?
                        .parse::<u64>()
                        .map_err(|_| "watchman: --max-cycles must be a number".to_string())?;
                }
                "--now" => {
                    args.now = it
                        .next()
                        .ok_or_else(|| "watchman: --now needs a value".to_string())?
                        .parse::<i64>()
                        .map_err(|_| "watchman: --now must be a number".to_string())?;
                }
                other => return Self::usage_error(&format!("unknown argument {other}")),
            }
        }
        match mode {
            None => return Self::usage_error("one of --once or --loop is required"),
            Some(once) => args.once = once,
        }
        if args.jobs_file.is_empty() || args.agents_file.is_empty() {
            return Self::usage_error("--jobs-file and --agents-file are required");
        }
        if args.interval == 0 || args.heartbeat_stale_seconds < 0 {
            return Self::usage_error("--interval must be positive and --heartbeat-stale-seconds non-negative");
        }
        Ok(args)
    }
}

fn system_now() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0)
}

/// CLI entry: `--once` prints one JSON event per line and updates
/// the state file; `--loop` repeats. Exit codes: 0 ok, 2 bad
/// input or usage.
pub fn cli(argv: &[String], stdout: &mut dyn FnMut(String)) -> i32 {
    let args = match WatchmanArgs::parse(argv) {
        Ok(a) => a,
        Err(e) => {
            eprintln!("{e}");
            return 2;
        }
    };
    let now = || {
        if args.now != 0 {
            args.now
        } else {
            system_now()
        }
    };
    if args.once {
        match run_once(
            &args.jobs_file,
            &args.agents_file,
            args.state_file.as_deref(),
            now(),
            args.heartbeat_stale_seconds,
        ) {
            Ok(events) => {
                for event in &events {
                    stdout(serde_json::to_string(event).unwrap_or_default());
                }
                0
            }
            Err(e) => {
                eprintln!("{e}");
                2
            }
        }
    } else {
        let mut cycles = 0u64;
        loop {
            match run_once(
                &args.jobs_file,
                &args.agents_file,
                args.state_file.as_deref(),
                now(),
                args.heartbeat_stale_seconds,
            ) {
                Ok(events) => {
                    for event in &events {
                        stdout(serde_json::to_string(event).unwrap_or_default());
                    }
                }
                Err(e) => eprintln!("{e}"),
            }
            cycles += 1;
            if args.max_cycles > 0 && cycles >= args.max_cycles {
                return 0;
            }
            std::thread::sleep(std::time::Duration::from_secs(args.interval));
        }
    }
}
