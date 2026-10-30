//! OS-122 follow-up: the service-loop caller for watchman_tick().
//! (`os/intel/watchman_loop.py`)
//!
//! Judgment rules, stated plainly because each one guards a
//! silent-failure class:
//! - A successful run folds through watchman_tick(): a tick
//!   proves the watchman ran, a wake event proves the bell, a
//!   quiet tick keeps last_bell None and reads UNKNOWN.
//! - A failed run folds NOTHING fresh. Instead the machine's
//!   last real record, when one exists, is carried forward
//!   unchanged into the judge, so its bell ages honestly. A
//!   carried record drops restart_ok. A failed run for a machine
//!   with no prior record is unjudged, recorded only in
//!   diagnostics.
//! - Malformed stdout lines are contained per machine.
//! - Inputs are never mutated: runs, priors, and journal come
//!   back unchanged, and carried records are copies.

use serde_json::{Map, Value};
use std::collections::BTreeMap;

use crate::watchman_bridge;
use crate::watchman_watch;

/// Stdout text to (events, malformed_count).
/// One JSON object per non-blank line. A line that is not a JSON
/// object is malformed: counted, skipped, never breaking the good
/// lines. Non-string input yields no events and counts as one
/// malformed line.
pub fn parse_event_lines(text: &Value) -> (Vec<Value>, usize) {
    let text = match text.as_str() {
        Some(t) => t,
        None => return (Vec::new(), 1),
    };
    let mut events = Vec::new();
    let mut malformed = 0usize;
    for line in text.lines() {
        if line.trim().is_empty() {
            continue;
        }
        match serde_json::from_str::<Value>(line) {
            Ok(Value::Object(_)) => events.push(serde_json::from_str(line).unwrap()),
            _ => malformed += 1,
        }
    }
    (events, malformed)
}

/// Diagnostics for one service-loop cycle.
#[derive(Debug, Clone, Default)]
pub struct Diagnostics {
    pub run_failures: Vec<String>,
    pub malformed_lines: BTreeMap<String, usize>,
}

impl Diagnostics {
    fn to_json(&self) -> Value {
        let mut map = Map::new();
        map.insert(
            "run_failures".to_string(),
            Value::Array(self.run_failures.iter().map(|s| Value::String(s.clone())).collect()),
        );
        if !self.malformed_lines.is_empty() {
            let mut malformed = Map::new();
            for (k, v) in &self.malformed_lines {
                malformed.insert(k.clone(), Value::Number((*v as u64).into()));
            }
            map.insert("malformed_lines".to_string(), Value::Object(malformed));
        }
        Value::Object(map)
    }
}

/// One service-loop cycle over every machine's watchman run.
/// Returns (records, new_journal, diagnostics).
pub fn loop_cycle(
    runs: &Value,
    now: f64,
    priors: Option<&Value>,
    journal: Option<&[Value]>,
    restart_ok: Option<&Value>,
) -> (BTreeMap<String, Value>, Vec<Value>, Diagnostics) {
    let runs_map = runs.as_object();
    let priors_map = priors.and_then(|v| v.as_object());
    let journal_list: Vec<Value> = journal.unwrap_or(&[]).to_vec();
    let restart_map = restart_ok.and_then(|v| v.as_object());

    let mut ok_events: BTreeMap<String, Vec<Value>> = BTreeMap::new();
    let mut ok_priors: BTreeMap<String, Value> = BTreeMap::new();
    let mut carried: BTreeMap<String, Value> = BTreeMap::new();
    let mut diagnostics = Diagnostics::default();

    let ordered: Vec<String> = match runs_map {
        Some(map) => {
            let mut v: Vec<String> = map.keys().cloned().collect();
            v.sort();
            v
        }
        None => Vec::new(),
    };
    for name in ordered {
        let run = &runs_map.unwrap()[&name];
        let (ok, stdout) = pair_ok_stdout(run);
        if !ok {
            diagnostics.run_failures.push(name.clone());
            if let Some(prior) = priors_map.and_then(|m| m.get(&name)) {
                if let Some(obj) = prior.as_object() {
                    let mut record = obj.clone();
                    record.remove("restart_ok");
                    carried.insert(name.clone(), Value::Object(record));
                }
            }
            continue;
        }
        let (events, malformed) = parse_event_lines(stdout.unwrap_or(&Value::Null));
        if malformed > 0 {
            diagnostics.malformed_lines.insert(name.clone(), malformed);
        }
        ok_events.insert(name.clone(), events);
        if let Some(prior) = priors_map.and_then(|m| m.get(&name)) {
            if prior.is_object() {
                ok_priors.insert(name.clone(), prior.clone());
            }
        }
    }

    let ok_events_value = Value::Object(
        ok_events
            .into_iter()
            .map(|(k, v)| (k, Value::Array(v)))
            .collect(),
    );
    let ok_priors_value = Value::Object(
        ok_priors
            .into_iter()
            .map(|(k, v)| (k, v))
            .collect(),
    );
    let mut restart_filtered = Map::new();
    if let Some(rm) = restart_map {
        for (k, v) in rm {
            if ok_events_value.get(k).is_some() {
                restart_filtered.insert(k.clone(), v.clone());
            }
        }
    }
    // Only machines with successful runs pass restart outcomes in;
    // carried machines must never re-spend an old success.
    let (mut records, mut journal_new) = watchman_bridge::watchman_tick(
        &ok_events_value,
        now,
        Some(&ok_priors_value),
        Some(&journal_list),
        Some(&Value::Object(restart_filtered)),
    );
    if !carried.is_empty() {
        let snapshot = watchman_bridge::machines_snapshot(&Value::Object(
            carried
                .iter()
                .map(|(k, v)| (k.clone(), v.clone()))
                .collect(),
        ));
        let mut combined = journal_list.clone();
        combined.extend(journal_new.clone());
        let carried_new = watchman_watch::watchman_watch_tick(&snapshot, &combined, now);
        journal_new.extend(carried_new);
    }
    for (name, record) in carried {
        records.insert(name, record);
    }
    (records, journal_new, diagnostics)
}

fn pair_ok_stdout(run: &Value) -> (bool, Option<&Value>) {
    let pair = match run.as_array() {
        Some(items) if items.len() >= 2 => items,
        _ => return (false, None),
    };
    match &pair[0] {
        Value::Bool(true) => (true, Some(&pair[1])),
        Value::Bool(false) => (false, None),
        _ => (false, None),
    }
}

impl Diagnostics {
    /// Diagnostics as the plain dict callers log.
    pub fn as_json(&self) -> Value {
        self.to_json()
    }
}
