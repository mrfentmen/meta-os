//! Who watches the watchman (OS-122, Milo).
//! (`os/intel/watchman_watch.py`)
//!
//! The watchdog treats a dead watchman as a first-class failure.
//! Crew-dark is the name for it: the machine's agents are asleep,
//! its jobs are invisible to them, and no bell will ring for new
//! work until the watchman is back.
//!
//! What counts as dead is a pure function of the machine's
//! watchman record and the tick time:
//! - watchman_alive False: dead, whatever the bell says.
//! - watchman_alive True with a bell older than the stale window:
//!   dead. A flag that says alive while the bell has gone quiet
//!   is a stale flag, not a live watchman.
//! - watchman_alive True with a fresh bell: alive.
//! - anything else (no flag, no bell, malformed): unknown.
//!
//! Episodes, not globals: a machine that recovers and then dies
//! again earns a fresh crew-dark record. Dedupe is per dark
//! episode. The escalation payload is built, never sent.

use serde_json::{Map, Value};

use crate::push_lite;
use crate::thresholds;

pub const ALIVE: &str = "alive";
pub const DEAD: &str = "dead";
pub const UNKNOWN: &str = "unknown";

fn num(value: &Value) -> Option<f64> {
    match value {
        Value::Number(n) => n.as_f64(),
        _ => None,
    }
}

fn machines(snapshot: &Value) -> Vec<(String, Value)> {
    match snapshot.get("machines").and_then(|v| v.as_object()) {
        Some(map) => map.iter().map(|(k, v)| (k.clone(), v.clone())).collect(),
        None => Vec::new(),
    }
}

/// Alive, dead, or unknown for one watchman record.
/// `stale_minutes` overrides the thresholds default for the call.
pub fn machine_state(record: &Value, now: f64, stale_minutes: Option<f64>) -> &'static str {
    let obj = match record.as_object() {
        Some(o) => o,
        None => return UNKNOWN,
    };
    match obj.get("watchman_alive") {
        Some(Value::Bool(false)) => return DEAD,
        Some(Value::Bool(true)) => {}
        _ => return UNKNOWN,
    }
    let bell = match obj.get("last_bell").and_then(num) {
        Some(b) => b,
        None => return UNKNOWN,
    };
    let stale = stale_minutes.unwrap_or_else(|| thresholds::watchman_stale_minutes() as f64);
    let window = stale * 60.0;
    if now - bell > window {
        DEAD
    } else {
        ALIVE
    }
}

/// One board state record per machine, in name order.
pub fn current_states(snapshot: &Value, now: f64) -> Vec<Value> {
    let mut machines = machines(snapshot);
    machines.sort_by(|a, b| a.0.cmp(&b.0));
    machines
        .into_iter()
        .map(|(name, record)| {
            let state = machine_state(&record, now, None);
            let (bell, wake) = match record.as_object() {
                Some(o) => (
                    o.get("last_bell").and_then(num).map(|v| v.into()),
                    o.get("last_wake").and_then(num).map(|v| v.into()),
                ),
                None => (None, None),
            };
            serde_json::json!({
                "machine": name,
                "state": state,
                "last_bell": bell.unwrap_or(Value::Null),
                "last_wake": wake.unwrap_or(Value::Null),
                "as_of": now,
            })
        })
        .collect()
}

fn episode_open(journal: &[Value], machine: &str) -> bool {
    let mut open_dark = false;
    for entry in journal {
        let obj = match entry.as_object() {
            Some(o) => o,
            None => continue,
        };
        if obj.get("machine").and_then(|v| v.as_str()) != Some(machine) {
            continue;
        }
        match obj.get("kind").and_then(|v| v.as_str()) {
            Some("crew-dark") => open_dark = true,
            Some("watchman-recovered") => open_dark = false,
            _ => {}
        }
    }
    open_dark
}

fn escalated_this_episode(journal: &[Value], machine: &str) -> bool {
    let mut last_dark: Option<usize> = None;
    for (index, entry) in journal.iter().enumerate() {
        let is_dark = match entry.as_object() {
            Some(o) => {
                o.get("machine").and_then(|v| v.as_str()) == Some(machine)
                    && o.get("kind").and_then(|v| v.as_str()) == Some("crew-dark")
            }
            None => false,
        };
        if is_dark {
            last_dark = Some(index);
        }
    }
    match last_dark {
        None => false,
        Some(dark) => journal[dark + 1..].iter().any(|entry| match entry.as_object() {
            Some(o) => o.get("kind").and_then(|v| v.as_str()) == Some("escalation"),
            None => false,
        }),
    }
}

fn escalation_for(machine: &str, now: f64, restart_ok: bool) -> Option<Value> {
    if restart_ok {
        return None;
    }
    let question = format!(
        "The watchman on machine {machine} is dead and its restart failed; the machine's agents are asleep and its jobs are invisible to them. Dale's call is needed."
    );
    let mut parked = Map::new();
    parked.insert("id".to_string(), Value::String(format!("watchman:{machine}")));
    parked.insert(
        "title".to_string(),
        Value::String(format!("Watchman on machine {machine}")),
    );
    parked.insert("status".to_string(), Value::String("blocked".to_string()));
    parked.insert("note".to_string(), Value::String(question.clone()));
    let payload = push_lite::build_blocked_push(&parked, Some(&question))?;
    if !push_lite::validate_push(&payload) {
        return None;
    }
    Some(serde_json::json!({
        "kind": "escalation",
        "machine": machine,
        "reason": "watchman dead, restart failed",
        "question": question,
        "push": payload,
        "escalated_at": now,
        "dedupe_key": format!("watchdark-escalate:{machine}"),
    }))
}

/// New journal records for this tick's machines.
pub fn watchman_watch_tick(snapshot: &Value, journal: &[Value], now: f64) -> Vec<Value> {
    let mut records = Vec::new();
    let mut machines = machines(snapshot);
    machines.sort_by(|a, b| a.0.cmp(&b.0));
    // The judge sees the caller's journal plus this tick's new
    // records, so a second dark in one tick does not double-fire.
    let mut seen: Vec<Value> = journal.to_vec();
    for (name, record) in &machines {
        let state = machine_state(record, now, None);
        if state == UNKNOWN {
            continue;
        }
        if state == ALIVE {
            if episode_open(&seen, name) {
                let entry = serde_json::json!({
                    "kind": "watchman-recovered",
                    "machine": name,
                    "state": ALIVE,
                    "recovered_at": now,
                    "dedupe_key": format!("watchrecovered:{name}"),
                });
                seen.push(entry.clone());
                records.push(entry);
            }
            continue;
        }
        if episode_open(&seen, name) {
            continue;
        }
        let dark = serde_json::json!({
            "kind": "crew-dark",
            "machine": name,
            "state": DEAD,
            "reason": "watchman dead: agents asleep, jobs invisible",
            "created_at": now,
            "dedupe_key": format!("watchdark:{name}"),
        });
        seen.push(dark.clone());
        records.push(dark);
        let restart_ok = record
            .as_object()
            .and_then(|o| o.get("restart_ok"))
            == Some(&Value::Bool(true));
        let restart = serde_json::json!({
            "kind": "watchman-restart",
            "machine": name,
            "restart_ok": restart_ok,
            "attempted_at": now,
            "dedupe_key": format!("watchrestart:{name}"),
        });
        seen.push(restart.clone());
        records.push(restart);
        if !restart_ok && !escalated_this_episode(&seen, name) {
            if let Some(escalation) = escalation_for(name, now, restart_ok) {
                seen.push(escalation.clone());
                records.push(escalation);
            }
        }
    }
    records
}

/// One frozen line per watchman journal record for the next brief.
pub fn watchman_brief_lines(records: &[Value]) -> Vec<String> {
    let mut lines = Vec::new();
    for record in records {
        let obj = match record.as_object() {
            Some(o) => o,
            None => continue,
        };
        let machine = obj.get("machine").and_then(|v| v.as_str()).unwrap_or("");
        match obj.get("kind").and_then(|v| v.as_str()) {
            Some("crew-dark") => lines.push(format!(
                "Crew-dark on machine {machine}: watchman dead, agents asleep, jobs invisible."
            )),
            Some("watchman-restart") => {
                if obj.get("restart_ok") == Some(&Value::Bool(true)) {
                    lines.push(format!(
                        "Watchman restart attempted on machine {machine}: restart succeeded."
                    ));
                } else {
                    lines.push(format!(
                        "Watchman restart attempted on machine {machine}: restart failed."
                    ));
                }
            }
            Some("escalation") => lines.push(format!(
                "Escalated machine {machine}: one blocked push queued (watchman dead, restart failed)."
            )),
            Some("watchman-recovered") => {
                lines.push(format!("Watchman recovered on machine {machine}."))
            }
            _ => {}
        }
    }
    lines
}

/// One line per board state record for the machine groups.
pub fn board_lines(states: &[Value]) -> Vec<String> {
    let mut lines = Vec::new();
    for state in states {
        let obj = match state.as_object() {
            Some(o) => o,
            None => continue,
        };
        let machine = obj.get("machine").and_then(|v| v.as_str()).unwrap_or("");
        match obj.get("state").and_then(|v| v.as_str()) {
            Some(DEAD) => lines.push(format!("Machine {machine}: watchman dead (crew-dark).")),
            Some(ALIVE) => lines.push(format!("Machine {machine}: watchman alive.")),
            Some(UNKNOWN) => lines.push(format!("Machine {machine}: watchman state unknown.")),
            _ => {}
        }
    }
    lines
}
