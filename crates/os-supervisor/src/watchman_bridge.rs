//! OS-122 follow-up to Pax OS-118: the bridge from the real
//! watchman to the watchman judge.
//! (`os/intel/watchman_bridge.py`)
//!
//! One mapping rule, nothing else:
//! - A tick the caller actually ran proves the watchman is alive
//!   at that tick's time, so fold marks watchman_alive True with
//!   last_tick = now. Aliveness comes from the tick executing,
//!   never from the rung state file.
//! - A bell is a wake event, nothing else. last_bell and
//!   last_wake advance only to the latest wake event's ts in the
//!   tick; a tick with no wake event keeps the prior bell, and a
//!   watchman that has ticked but never rung carries last_bell
//!   None. Under watchman_watch's own rule that record reads
//!   UNKNOWN on the board, not ALIVE.
//! - The service-loop entry point is watchman_tick(): one call
//!   folds every machine's relay_watchman events into
//!   watchman_watch records and judges them. A machine missing
//!   from the events mapping is not judged at all. A machine that
//!   stops reporting must be folded explicitly with an empty
//!   event list and its prior record.

use serde_json::{Map, Value};
use std::collections::BTreeMap;

use crate::watchman_watch;

pub const WAKE_KIND: &str = "wake";

fn num(value: &Value) -> Option<f64> {
    match value {
        Value::Bool(_) => None,
        Value::Number(n) => {
            let v = n.as_f64()?;
            if v != v {
                None
            } else {
                Some(v)
            }
        }
        _ => None,
    }
}

fn prior_bell(prior: Option<&Value>) -> Option<f64> {
    prior?.as_object()?.get("last_bell").and_then(num)
}

fn num_value(v: f64) -> Value {
    serde_json::Number::from_f64(v)
        .map(Value::Number)
        .unwrap_or(Value::Null)
}

/// One relay_watchman tick's events to a watchman_watch record.
/// Inputs are never mutated; the return is a fresh dict.
pub fn fold_tick(events: &Value, now: f64, prior: Option<&Value>) -> Value {
    let items: &[Value] = events.as_array().map(|v| v.as_slice()).unwrap_or(&[]);
    let mut bell = prior_bell(prior);
    for event in items {
        let obj = match event.as_object() {
            Some(o) => o,
            None => continue,
        };
        if obj.get("kind").and_then(|v| v.as_str()) != Some(WAKE_KIND) {
            continue;
        }
        let ts = match obj.get("ts").and_then(num) {
            Some(t) => t,
            None => continue,
        };
        if bell.map(|b| ts > b).unwrap_or(true) {
            bell = Some(ts);
        }
    }
    let mut record = Map::new();
    record.insert("watchman_alive".to_string(), Value::Bool(true));
    record.insert("last_tick".to_string(), num_value(now));
    record.insert(
        "last_bell".to_string(),
        bell.map(num_value).unwrap_or(Value::Null),
    );
    record.insert(
        "last_wake".to_string(),
        bell.map(num_value).unwrap_or(Value::Null),
    );
    Value::Object(record)
}

/// One service-loop call over every machine's watchman events.
/// Returns (records, new_journal). Inputs are never mutated.
pub fn watchman_tick(
    events_by_machine: &Value,
    now: f64,
    priors: Option<&Value>,
    journal: Option<&[Value]>,
    restart_ok: Option<&Value>,
) -> (BTreeMap<String, Value>, Vec<Value>) {
    let events_map = events_by_machine.as_object();
    let priors_map = priors.and_then(|v| v.as_object());
    let restart_map = restart_ok.and_then(|v| v.as_object());
    let mut records = BTreeMap::new();
    let names: Vec<String> = match events_map {
        Some(map) => {
            let mut names: Vec<String> = map.keys().cloned().collect();
            names.sort();
            names
        }
        None => Vec::new(),
    };
    for name in names {
        let events = &events_map.unwrap()[&name];
        let prior = priors_map.and_then(|m| m.get(&name));
        let mut record = fold_tick(events, now, prior)
            .as_object()
            .cloned()
            .unwrap_or_default();
        if let Some(outcome) = restart_map
            .and_then(|m| m.get(&name))
            .and_then(|v| v.as_bool())
        {
            record.insert("restart_ok".to_string(), Value::Bool(outcome));
        }
        records.insert(name, Value::Object(record));
    }
    let snapshot = machines_snapshot(&Value::Object(
        records
            .iter()
            .map(|(k, v)| (k.clone(), v.clone()))
            .collect(),
    ));
    let journal_list: Vec<Value> = journal.unwrap_or(&[]).to_vec();
    let new_journal = watchman_watch::watchman_watch_tick(&snapshot, &journal_list, now);
    (records, new_journal)
}

/// {machine: record} to the snapshot watchman_watch consumes.
/// Non-dict records are skipped, never judged.
pub fn machines_snapshot(records: &Value) -> Value {
    let mut machines = Map::new();
    if let Some(obj) = records.as_object() {
        for (name, record) in obj {
            if record.is_object() {
                machines.insert(name.clone(), record.clone());
            }
        }
    }
    let mut snapshot = Map::new();
    snapshot.insert("machines".to_string(), Value::Object(machines));
    Value::Object(snapshot)
}
