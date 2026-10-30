//! OS-122 follow-up: the repeating production loop for the watchman.
//! (`os/intel/watchman_service.py`)
//!
//! How it runs: serve_cycles() takes a machine list and repeats
//! one cycle per interval. The records of one cycle become the
//! priors of the next, and each cycle's new journal entries
//! accumulate into the loop's journal, so episode dedupe holds
//! across cycles.
//!
//! What never kills the loop: a cycle_fn that raises, an on_cycle
//! callback that raises, a should_stop predicate that raises, a
//! sleep_fn that raises, and a now_fn that raises are all
//! contained; the next cycle still runs. A cycle whose cycle_fn
//! raises contributes diagnostics {"cycle_error": <type>} and
//! carries the prior records forward.

use serde_json::{Map, Value};
use std::collections::BTreeMap;

pub const DEFAULT_INTERVAL_SECONDS: u64 = 60;

/// One cycle's inputs: (machines, now, priors, journal).
#[derive(Debug, Clone)]
pub struct CycleInput {
    pub machines: Vec<String>,
    pub now: f64,
    pub priors: BTreeMap<String, Value>,
    pub journal: Vec<Value>,
}

/// One cycle's outputs: (records, new_journal, diagnostics).
#[derive(Debug, Clone)]
pub struct CycleOutput {
    pub records: BTreeMap<String, Value>,
    pub new_journal: Vec<Value>,
    pub diagnostics: Value,
}

/// Loop result: cycles run, final records, accumulated journal,
/// per-cycle diagnostics, and callback error type names.
#[derive(Debug)]
pub struct ServeResult {
    pub cycles_run: usize,
    pub records: BTreeMap<String, Value>,
    pub journal: Vec<Value>,
    pub diagnostics_by_cycle: Vec<Value>,
    pub callback_errors: Vec<String>,
}

fn bad_diagnostics(kind: &str) -> Value {
    let mut map = Map::new();
    map.insert("cycle_error".to_string(), Value::String(kind.to_string()));
    Value::Object(map)
}

/// Run watchman cycles until max_cycles or should_stop().
/// `cycle_fn` maps CycleInput to CycleOutput or an error type
/// name; `now_fn` supplies the clock (None models a raising
/// clock); `sleep_fn` sleeps between cycles only. All callbacks
/// are contained: nothing a callback raises escapes the loop.
#[allow(clippy::too_many_arguments)]
pub fn serve_cycles(
    machines: &[String],
    mut cycle_fn: Option<Box<dyn FnMut(CycleInput) -> Result<CycleOutput, String>>>,
    mut now_fn: Option<Box<dyn FnMut() -> Option<f64>>>,
    mut sleep_fn: Option<Box<dyn FnMut(u64)>>,
    max_cycles: Option<usize>,
    interval_seconds: Option<i64>,
    mut should_stop: Option<Box<dyn FnMut(usize, &BTreeMap<String, Value>, &Value) -> bool>>,
    mut on_cycle: Option<Box<dyn FnMut(usize, &BTreeMap<String, Value>, &[Value], &Value)>>,
    priors: Option<BTreeMap<String, Value>>,
    journal: Option<Vec<Value>>,
) -> ServeResult {
    let interval = match interval_seconds {
        None => DEFAULT_INTERVAL_SECONDS,
        Some(v) if v < 0 => 0,
        Some(v) => v as u64,
    };
    if let Some(0) = max_cycles {
        return ServeResult {
            cycles_run: 0,
            records: BTreeMap::new(),
            journal: journal.unwrap_or_default(),
            diagnostics_by_cycle: Vec::new(),
            callback_errors: Vec::new(),
        };
    }
    let mut current_priors = priors.unwrap_or_default();
    let mut accumulated = journal.unwrap_or_default();
    let mut diagnostics_by_cycle = Vec::new();
    let mut callback_errors = Vec::new();
    let mut cycles_run = 0usize;
    loop {
        let now = match now_fn.as_mut().map(|f| f()) {
            Some(Some(t)) => Some(t),
            _ => None,
        };
        // A raising clock yields a cycle_error cycle with the
        // prior records carried, and the loop continues.
        let (records, new_journal, diagnostics) = match now {
            None => {
                let diagnostics = bad_diagnostics("clock");
                (current_priors.clone(), Vec::new(), diagnostics)
            }
            Some(t) => {
                let input = CycleInput {
                    machines: machines.to_vec(),
                    now: t,
                    priors: current_priors.clone(),
                    journal: accumulated.clone(),
                };
                match cycle_fn.as_mut().map(|f| f(input)) {
                    Some(Ok(out)) => (out.records, out.new_journal, out.diagnostics),
                    Some(Err(kind)) => {
                        (current_priors.clone(), Vec::new(), bad_diagnostics(&kind))
                    }
                    None => {
                        // No cycle_fn: a quiet empty cycle.
                        (
                            current_priors.clone(),
                            Vec::new(),
                            Value::Object(Map::new()),
                        )
                    }
                }
            }
        };
        diagnostics_by_cycle.push(diagnostics.clone());
        accumulated.extend(new_journal.clone());
        current_priors = records.clone();
        cycles_run += 1;
        if let Some(cb) = on_cycle.as_mut() {
            // now_fn values are f64; on_cycle sees copies.
            let outcome = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                cb(cycles_run - 1, &records, &new_journal, &diagnostics);
            }));
            if outcome.is_err() {
                // A panicking callback is contained like a raising
                // one; record the panic, keep watching.
                callback_errors.push("panic".to_string());
            }
        }
        // should_stop raising counts as False: a stop check that
        // crashes must not stop the watcher.
        let stop = should_stop
            .as_mut()
            .map(|f| {
                std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                    f(cycles_run - 1, &records, &diagnostics)
                }))
                .unwrap_or(false)
            })
            .unwrap_or(false);
        if stop {
            break;
        }
        if let Some(max) = max_cycles {
            if cycles_run >= max {
                break;
            }
        }
        if let Some(sleep) = sleep_fn.as_mut() {
            let outcome = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                sleep(interval);
            }));
            let _ = outcome;
        }
        // Unbounded loops without should_stop cannot be tested;
        // production passes should_stop or a finite max_cycles.
        if max_cycles.is_none() && should_stop.is_none() {
            break;
        }
    }
    ServeResult {
        cycles_run,
        records: current_priors,
        journal: accumulated,
        diagnostics_by_cycle,
        callback_errors,
    }
}

/// CLI argument shape for the watchman service loop.
pub struct ServiceArgs {
    pub machines: Vec<String>,
    pub cycles: Option<usize>,
    pub interval: f64,
    pub snapshot_dir: Option<String>,
}

impl ServiceArgs {
    /// Parse argv. A bare --machines (no value) reads as an empty
    /// list: the unit's ExecStart passes ${WATCHMAN_WATCH_MACHINES},
    /// and with no env file systemd expands that to nothing,
    /// leaving --machines directly before --snapshot-dir.
    pub fn parse(argv: &[String]) -> Result<Self, String> {
        let mut machines: Vec<String> = Vec::new();
        let mut cycles: Option<usize> = None;
        let mut interval = DEFAULT_INTERVAL_SECONDS as f64;
        let mut snapshot_dir: Option<String> = None;
        let mut it = argv.iter().peekable();
        while let Some(arg) = it.next() {
            match arg.as_str() {
                "--machines" => {
                    if let Some(next) = it.peek() {
                        if !next.starts_with("--") {
                            let value = it.next().unwrap();
                            machines = value
                                .split(',')
                                .map(|s| s.trim().to_string())
                                .filter(|s| !s.is_empty())
                                .collect();
                        }
                    }
                }
                "--cycles" => {
                    cycles = Some(
                        it.next()
                            .ok_or_else(|| "watchman-service: --cycles needs a value".to_string())?
                            .parse::<usize>()
                            .map_err(|_| "watchman-service: --cycles must be a number".to_string())?,
                    );
                }
                "--interval" => {
                    interval = it
                        .next()
                        .ok_or_else(|| "watchman-service: --interval needs a value".to_string())?
                        .parse::<f64>()
                        .map_err(|_| "watchman-service: --interval must be a number".to_string())?;
                }
                "--snapshot-dir" => {
                    snapshot_dir = Some(
                        it.next()
                            .ok_or_else(|| "watchman-service: --snapshot-dir needs a value".to_string())?
                            .clone(),
                    );
                }
                other if other.starts_with("--") => {
                    return Err(format!("watchman-service: unknown argument {other}"));
                }
                other => {
                    return Err(format!("watchman-service: unexpected argument {other}"));
                }
            }
        }
        Ok(ServiceArgs {
            machines,
            cycles,
            interval,
            snapshot_dir,
        })
    }
}
