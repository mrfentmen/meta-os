//! OS-122 follow-up: the runner adapter for the watchman service loop.
//! (`os/intel/watchman_cycle.py`)
//!
//! `watchman_loop.loop_cycle` judges one cycle, but it takes runs
//! that are already collected. `run_cycle` closes that gap: it
//! takes a caller-supplied runner and a machine list, and turns
//! whatever comes back into the runs `loop_cycle` expects:
//! - A runner that raises for a machine yields a failed run for
//!   that machine, never a crash. The exception type is recorded
//!   in diagnostics["runner_errors"].
//! - A runner that returns something other than an (ok, stdout)
//!   pair yields a failed run too, recorded as "bad-return". A
//!   truthy non-True first element is not accepted as success:
//!   only True means the run happened.
//! - A runner that is not callable at all fails every machine the
//!   same way. An empty machine list yields empty records and
//!   journal and diagnostics with empty lists; no runner_errors
//!   key appears when nothing went wrong.

use serde_json::Value;
use std::collections::BTreeMap;

use crate::watchman_loop::Diagnostics;

/// A caller-supplied runner: machine name to its raw return, or
/// an `Err(kind)` when the runner raises for that machine
/// (`kind` is the exception type name). `None` means the runner
/// is not callable at all.
pub type Runner<'a> = Option<&'a dyn Fn(&str) -> Result<Value, String>>;

/// Normalize the machine list: a string is one machine, an array
/// of strings is the list, anything else is empty.
pub fn machine_list(machines: &Value) -> Vec<String> {
    match machines {
        Value::String(s) => vec![s.clone()],
        Value::Array(items) => items
            .iter()
            .filter_map(|v| v.as_str().map(|s| s.to_string()))
            .collect(),
        _ => Vec::new(),
    }
}

/// Classify one raw runner return into a ((ok, stdout), error)
/// pair for the loop. Only boolean first elements count: truthy
/// is not True, short pairs fail, and anything else is a
/// bad return.
fn pair_or_failure(result: Value) -> ((bool, Value), Option<String>) {
    let items = match result.as_array() {
        Some(items) if items.len() >= 2 => items,
        _ => return ((false, Value::String(String::new())), Some("bad-return".to_string())),
    };
    match &items[0] {
        Value::Bool(true) => ((true, items[1].clone()), None),
        Value::Bool(false) => ((false, Value::String(String::new())), None),
        _ => ((false, Value::String(String::new())), Some("bad-return".to_string())),
    }
}

/// One service-loop cycle driven by a caller-supplied runner.
/// Returns (records, new_journal, diagnostics, runner_errors).
/// Diagnostics gains "runner_errors" only when a runner call
/// raised, was not callable, or returned a bad pair.
#[allow(clippy::too_many_arguments)]
pub fn run_cycle(
    runner: Runner<'_>,
    machines: &Value,
    now: f64,
    priors: Option<&Value>,
    journal: Option<&[Value]>,
    restart_ok: Option<&Value>,
) -> (
    BTreeMap<String, Value>,
    Vec<Value>,
    Diagnostics,
    BTreeMap<String, String>,
) {
    let machine_list = machine_list(machines);
    let mut runs = BTreeMap::new();
    let mut runner_errors = BTreeMap::new();
    match runner {
        None => {
            for name in &machine_list {
                runs.insert(
                    name.clone(),
                    Value::Array(vec![Value::Bool(false), Value::String(String::new())]),
                );
                runner_errors.insert(name.clone(), "not-callable".to_string());
            }
        }
        Some(call) => {
            for name in &machine_list {
                match call(name) {
                    Err(kind) => {
                        runs.insert(
                            name.clone(),
                            Value::Array(vec![Value::Bool(false), Value::String(String::new())]),
                        );
                        runner_errors.insert(name.clone(), kind);
                    }
                    Ok(raw) => {
                        let ((ok, stdout), error) = pair_or_failure(raw);
                        runs.insert(
                            name.clone(),
                            Value::Array(vec![
                                Value::Bool(ok),
                                if ok {
                                    stdout
                                } else {
                                    Value::String(String::new())
                                },
                            ]),
                        );
                        if let Some(e) = error {
                            runner_errors.insert(name.clone(), e);
                        }
                    }
                }
            }
        }
    }
    let runs_value = Value::Object(
        runs.into_iter()
            .map(|(k, v)| (k, v))
            .collect(),
    );
    let (records, new_journal, diagnostics) =
        crate::watchman_loop::loop_cycle(&runs_value, now, priors, journal, restart_ok);
    (records, new_journal, diagnostics, runner_errors)
}
