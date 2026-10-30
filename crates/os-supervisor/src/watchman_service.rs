//! Repeating production loop for the watchman (OS-122 follow-up).
//!
//! Port of `os/intel/watchman_service.py`. The loop module judges one
//! cycle, the cycle module collects one cycle from a caller-supplied
//! runner, and the runner module supplies the real subprocess runner.
//! What still did not exist was the loop itself: something that runs
//! those cycles again and again, carries the board picture and the
//! journal forward from cycle to cycle, and keeps watching when one
//! cycle goes wrong. A loop that dies on a bad cycle watches nothing,
//! which is the silent failure the watchdog exists to catch. This
//! module is that loop.
//!
//! How it runs ([`serve_cycles`] takes a machine list and repeats one
//! cycle per interval):
//! - Each cycle calls `cycle_fn(machines, now, priors, journal)` and
//!   gets back `(records, new_journal, diagnostics)`. By default
//!   `cycle_fn` is [`default_cycle_fn`] (real relay-watchman `--once`
//!   runs against the snapshot directory), so the production loop runs
//!   the real Pax OS-118 program once per machine per cycle with no
//!   judgment changed.
//! - The records of one cycle become the priors of the next, and each
//!   cycle's new journal entries accumulate into the loop's journal, so
//!   episode dedupe in the judge holds across cycles: a machine that
//!   recovers and dies again re-alerts, while a machine that stays dark
//!   does not re-escalate every cycle.
//! - `now_fn` supplies the clock (default: the real clock as an int).
//!   A fake clock in tests makes cycle timing exact, and the production
//!   loop never reads the wall clock twice for one cycle.
//! - `sleep_fn` sleeps between cycles only, never after the last cycle.
//!   `max_cycles` bounds a run; `None` means run until `should_stop()`
//!   says stop. `should_stop(index, records, diagnostics)` is checked
//!   after each cycle.
//!
//! What never kills the loop, ported verbatim:
//! - A `cycle_fn` that raises yields that cycle's diagnostics
//!   `{"cycle_error": <exception type>}` and the prior records carried
//!   forward unchanged, never a crash. The next cycle still runs.
//! - An `on_cycle` callback that raises is contained the same way: its
//!   exception type is collected in the result's `callback_errors` and
//!   the loop continues.
//! - A `should_stop` predicate that raises is treated as false: a stop
//!   check that crashes must not stop the watcher. A `sleep_fn` that
//!   raises is ignored: a missed sleep delays the next cycle, it never
//!   ends watching.
//! - A `now_fn` that raises yields a `cycle_error` cycle with the prior
//!   records carried, and the loop continues.
//!
//! What this module does not claim: it posts nothing to the bus, moves
//! no claim, restarts no process (systemd under OS-034), reassigns no
//! job, and sends no push. It reads no live queue and starts no agent
//! session.
//!
//! Systemd-unit boundary (live-service boundary, stated plainly): the
//! loop runs as a systemd unit,
//! `os/services/relay-watchman-watch.service`, and the unit's command is
//! the entry point ported here as [`service_main`]. A booted service is
//! still not proven here: there is no test image in this repo, the unit
//! is not yet wired into relay.target wants or any image enablement
//! list, and a systemd restart of the unit is still owed on the test
//! image. The unit's directives are therefore ported as data, not as a
//! live effect: see [`UNIT_DIRECTIVES`], [`unit_directive`], and the
//! machine-list gap note in [`UNIT_MACHINE_LIST_GAP`]. The unit file
//! itself is a systemd artifact, not Rust code, and is not generated
//! here; the constants below are its contract, checked by the tests in
//! this file the way the Python unit tests check the unit file text.
//!
//! Representation notes:
//! - Python exceptions have type names; Rust closures cannot raise, so
//!   a panicking callback, stop predicate, clock, or cycle function is
//!   contained via `catch_unwind` and recorded as `"panic"`, except for
//!   the clock, which Python records as `"clock"` (a clock failure has
//!   no exception type in Python either: the code sets `now = None` and
//!   the cycle error is the literal `"clock"`). A fixture cycle function
//!   can return [`CycleFnOutput::Bad`] to mirror a Python cycle function
//!   returning a non-triple, which Python records as
//!   `"bad-cycle-return"`.
//! - Python's `serve_cycles` journal items are untyped; here the journal
//!   is `Vec<JournalEntry>`, the judge's journal type. Fixture cycle
//!   functions in the tests below return journal entries whose kind
//!   carries the Python test's string payload (for example `"n1000000"`).
//! - Python's `main()` catches `KeyboardInterrupt` and returns 0. Rust
//!   has no equivalent in a std-only library port: a Ctrl-C terminates
//!   the process with the default signal disposition. A parent binary
//!   that needs the 0-on-interrupt behavior must install its own signal
//!   handling; [`service_main`] documents this boundary and does not
//!   fake it.

use std::collections::HashMap;
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use crate::watchman_cycle::{CycleDiagnostics, MachinesArg};
use crate::watchman_runner::run_cycle_with_subprocess;
use crate::watchman_watch::{JournalEntry, WatchmanRecord};

/// Default interval between cycles in seconds.
pub const DEFAULT_INTERVAL_SECONDS: f64 = 60.0;

/// The systemd unit's directives, as data (see the module docs: the unit
/// file itself is a systemd artifact, and a booted service is not proven
/// here).
pub const UNIT_DIRECTIVES: &[(&str, &str)] = &[
    ("ExecStart", "/usr/bin/python3 /opt/relay/intel/watchman_service.py --machines ${WATCHMAN_WATCH_MACHINES} --snapshot-dir /run/metaos"),
    ("After", "relay-watchman.service"),
    ("Restart", "on-failure"),
    ("User", "relay"),
    ("WorkingDirectory", "/opt/relay"),
    ("WantedBy", "relay.target"),
    ("EnvironmentFile", "-/etc/metaos/watchman-watch.env"),
];

/// The unit header's machine-list gap, stated plainly: no machine-naming
/// convention exists in the repo yet, so with no env file the loop
/// cycles with zero machines, which judges nothing and is a
/// configuration gap, not a passing watch. The unit is a verified unit
/// file, not a live watcher.
pub const UNIT_MACHINE_LIST_GAP: &str =
    "no machine-naming convention exists yet; with no env file the loop \
     cycles with zero machines, which is a configuration gap, not a \
     passing watch; service active at boot is NOT proven here, and the \
     unit is not a live watcher until image integration wires it in";

/// Look up one unit directive by name, or `None` when absent.
pub fn unit_directive(name: &str) -> Option<&'static str> {
    UNIT_DIRECTIVES
        .iter()
        .find(|(key, _)| *key == name)
        .map(|(_, value)| *value)
}

/// What a cycle function returns: either a usable triple, or a bad
/// return (a Python cycle function returning a non-triple).
#[derive(Clone, Debug, PartialEq)]
pub enum CycleFnOutput {
    /// `(records, new_journal, diagnostics)`.
    Triple(
        HashMap<String, WatchmanRecord>,
        Vec<JournalEntry>,
        CycleDiagnostics,
    ),
    /// A return value that is not a usable triple.
    Bad,
}

/// Options for [`serve_cycles`]. Every field mirrors a Python keyword
/// argument; `None` selects the production default described in the
/// module docs.
#[derive(Default)]
pub struct ServeOptions {
    /// Cycle function; `None` runs the real subprocess runner.
    pub cycle_fn: Option<
        Box<
            dyn FnMut(
                Vec<String>,
                f64,
                HashMap<String, WatchmanRecord>,
                Vec<JournalEntry>,
            ) -> CycleFnOutput,
        >,
    >,
    /// Clock; `None` reads the real clock as an int. `None` returned
    /// from the clock (or a panic) yields a `"clock"` cycle error.
    pub now_fn: Option<Box<dyn FnMut() -> Option<f64>>>,
    /// Sleep between cycles; `None` sleeps for real.
    pub sleep_fn: Option<Box<dyn FnMut(f64)>>,
    /// Cycle bound; `None` runs until `should_stop` says stop. A value
    /// <= 0 runs nothing (and returns empty records, not the priors).
    pub max_cycles: Option<i64>,
    /// Seconds between cycles; `None` is the default interval.
    pub interval_seconds: Option<f64>,
    /// Stop predicate, checked after each cycle; `None` never stops.
    pub should_stop: Option<
        Box<
            dyn FnMut(
                usize,
                &HashMap<String, WatchmanRecord>,
                &CycleDiagnostics,
            ) -> bool,
        >,
    >,
    /// Per-cycle reporting callback.
    pub on_cycle: Option<
        Box<
            dyn FnMut(
                usize,
                &HashMap<String, WatchmanRecord>,
                &[JournalEntry],
                &CycleDiagnostics,
            ),
        >,
    >,
    /// Starting priors.
    pub priors: Option<HashMap<String, WatchmanRecord>>,
    /// Starting journal.
    pub journal: Option<Vec<JournalEntry>>,
    /// Snapshot directory for the default cycle function.
    pub snapshot_dir: Option<String>,
    /// Subprocess timeout for the default cycle function.
    pub timeout_seconds: Option<f64>,
}

/// The result of [`serve_cycles`].
#[derive(Clone, Debug, PartialEq)]
pub struct ServiceResult {
    /// Cycles actually run.
    pub cycles_run: usize,
    /// Final records (the last cycle's records).
    pub records: HashMap<String, WatchmanRecord>,
    /// Accumulated journal (starting journal plus every cycle's new
    /// entries).
    pub journal: Vec<JournalEntry>,
    /// Diagnostics per cycle, in order.
    pub diagnostics_by_cycle: Vec<CycleDiagnostics>,
    /// Exception type names from `on_cycle` callbacks, in order.
    pub callback_errors: Vec<String>,
}

/// One production cycle through the real subprocess runner.
pub fn default_cycle_fn(
    machines: Vec<String>,
    now: f64,
    priors: HashMap<String, WatchmanRecord>,
    journal: Vec<JournalEntry>,
    snapshot_dir: Option<&str>,
    timeout_seconds: Option<f64>,
) -> CycleFnOutput {
    let (records, new_journal, diagnostics) = run_cycle_with_subprocess(
        MachinesArg::List(machines),
        now,
        &priors,
        &journal,
        &HashMap::new(),
        None,
        timeout_seconds.unwrap_or(crate::watchman_runner::DEFAULT_TIMEOUT_SECONDS),
        snapshot_dir.unwrap_or(crate::watchman_runner::DEFAULT_SNAPSHOT_DIR),
        None,
    );
    CycleFnOutput::Triple(records, new_journal, diagnostics)
}

/// Interval normalization: an unusable value reads as the default, NaN
/// reads as the default, and a negative value reads as 0 (no delay).
fn interval_seconds(value: Option<f64>) -> f64 {
    match value {
        None => DEFAULT_INTERVAL_SECONDS,
        Some(seconds) => {
            if seconds.is_nan() {
                DEFAULT_INTERVAL_SECONDS
            } else if seconds < 0.0 {
                0.0
            } else {
                seconds
            }
        }
    }
}

/// Run watchman cycles until `max_cycles` or `should_stop()`.
///
/// `machines` is the iterable of machine names run every cycle.
/// Returns the cycles run, the final records, the accumulated journal,
/// per-cycle diagnostics, and callback errors. A cycle whose cycle
/// function raises (panics) contributes diagnostics with a
/// `"cycle_error"` entry and carries the prior records forward.
pub fn serve_cycles(machines: MachinesArg, mut options: ServeOptions) -> ServiceResult {
    let machine_list = machines.machine_list();
    let interval = interval_seconds(options.interval_seconds);
    if let Some(max_cycles) = options.max_cycles {
        if max_cycles <= 0 {
            return ServiceResult {
                cycles_run: 0,
                records: HashMap::new(),
                journal: options.journal.unwrap_or_default(),
                diagnostics_by_cycle: Vec::new(),
                callback_errors: Vec::new(),
            };
        }
    }

    let snapshot_dir = options.snapshot_dir.clone();
    let timeout_seconds = options.timeout_seconds;
    let mut cycle_fn = match options.cycle_fn.take() {
        Some(f) => f,
        None => Box::new(
            move |machines_arg: Vec<String>,
                  now: f64,
                  priors_arg: HashMap<String, WatchmanRecord>,
                  journal_arg: Vec<JournalEntry>| {
                default_cycle_fn(
                    machines_arg,
                    now,
                    priors_arg,
                    journal_arg,
                    snapshot_dir.as_deref(),
                    timeout_seconds,
                )
            },
        )
            as Box<
                dyn FnMut(
                    Vec<String>,
                    f64,
                    HashMap<String, WatchmanRecord>,
                    Vec<JournalEntry>,
                ) -> CycleFnOutput,
            >,
    };
    let mut now_fn = match options.now_fn.take() {
        Some(f) => f,
        None => Box::new(|| {
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .ok()
                .map(|d| d.as_secs() as f64)
        }) as Box<dyn FnMut() -> Option<f64>>,
    };
    let mut sleep_fn = match options.sleep_fn.take() {
        Some(f) => f,
        None => Box::new(|seconds: f64| {
            if seconds > 0.0 {
                thread_sleep(seconds);
            }
        }) as Box<dyn FnMut(f64)>,
    };

    let mut current_priors: HashMap<String, WatchmanRecord> =
        options.priors.clone().unwrap_or_default();
    let mut accumulated: Vec<JournalEntry> = options.journal.clone().unwrap_or_default();
    let mut diagnostics_by_cycle: Vec<CycleDiagnostics> = Vec::new();
    let mut callback_errors: Vec<String> = Vec::new();
    let mut cycles_run: usize = 0;

    loop {
        let now = match catch_unwind(AssertUnwindSafe(|| now_fn())) {
            Ok(value) => value,
            Err(_) => None,
        };
        let (records, new_journal, diagnostics) = if now.is_none() {
            (
                current_priors.clone(),
                Vec::new(),
                CycleDiagnostics {
                    run_failures: Vec::new(),
                    malformed_lines: HashMap::new(),
                    runner_errors: HashMap::new(),
                },
            )
        } else {
            let now = now.unwrap();
            let raw = catch_unwind(AssertUnwindSafe(|| {
                cycle_fn(
                    machine_list.clone(),
                    now,
                    current_priors.clone(),
                    accumulated.clone(),
                )
            }));
            match raw {
                Ok(CycleFnOutput::Triple(records, new_journal, diagnostics)) => {
                    (records, new_journal, diagnostics)
                }
                Ok(CycleFnOutput::Bad) => (
                    current_priors.clone(),
                    Vec::new(),
                    cycle_error_diagnostics("bad-cycle-return"),
                ),
                Err(_) => (
                    current_priors.clone(),
                    Vec::new(),
                    cycle_error_diagnostics("panic"),
                ),
            }
        };
        // A cycle_error cycle is represented by a diagnostics value whose
        // runner_errors map carries the error under the "cycle_error"
        // key; see cycle_error_diagnostics. For the clock case the
        // diagnostics above must carry "clock" the same way.
        let diagnostics = if now.is_none() {
            cycle_error_diagnostics("clock")
        } else {
            diagnostics
        };
        diagnostics_by_cycle.push(diagnostics.clone());
        accumulated.extend(new_journal.iter().cloned());
        current_priors = records.clone();
        cycles_run += 1;
        if let Some(on_cycle) = options.on_cycle.as_mut() {
            let result = catch_unwind(AssertUnwindSafe(|| {
                on_cycle(
                    cycles_run - 1,
                    &records,
                    &new_journal,
                    &diagnostics,
                )
            }));
            if result.is_err() {
                callback_errors.push("panic".to_string());
            }
        }
        let mut stop = false;
        if let Some(should_stop) = options.should_stop.as_mut() {
            let result = catch_unwind(AssertUnwindSafe(|| {
                should_stop(cycles_run - 1, &records, &diagnostics)
            }));
            stop = result.unwrap_or(false);
        }
        if stop {
            break;
        }
        if let Some(max_cycles) = options.max_cycles {
            if cycles_run as i64 >= max_cycles {
                break;
            }
        }
        let _ = catch_unwind(AssertUnwindSafe(|| sleep_fn(interval)));
    }

    ServiceResult {
        cycles_run,
        records: current_priors,
        journal: accumulated,
        diagnostics_by_cycle,
        callback_errors,
    }
}

/// A diagnostics value carrying one cycle error, recorded in the
/// `runner_errors` map under the `"cycle_error"` key so the error type
/// survives the typed diagnostics shape (Python uses a one-key dict
/// `{"cycle_error": <type>}` for these cycles).
fn cycle_error_diagnostics(error: &str) -> CycleDiagnostics {
    let mut diagnostics = CycleDiagnostics::default();
    diagnostics
        .runner_errors
        .insert("cycle_error".to_string(), error.to_string());
    diagnostics
}

fn thread_sleep(seconds: f64) {
    std::thread::sleep(Duration::from_secs_f64(seconds));
}

/// Parsed command-line arguments for [`service_main`].
#[derive(Clone, Debug, PartialEq)]
pub struct CliArgs {
    /// Machine names from `--machines` (comma-separated, trimmed).
    pub machines: Vec<String>,
    /// Cycle count from `--cycles`, if given.
    pub cycles: Option<i64>,
    /// Interval from `--interval` (default 60).
    pub interval: f64,
    /// Snapshot directory from `--snapshot-dir`, if given.
    pub snapshot_dir: Option<String>,
}

/// Parse the service-loop command line.
///
/// Mirrors the Python argparse shape, including the bare `--machines`
/// case: a `--machines` flag directly before another flag (or at the
/// end) reads as an empty list, because the unit's ExecStart passes an
/// unset `${WATCHMAN_WATCH_MACHINES}` that systemd expands to nothing.
/// Returns an error string on a malformed command line (Python argparse
/// exits 2 there; [`service_main`] returns 2).
pub fn parse_service_args(args: &[String]) -> Result<CliArgs, String> {
    let mut machines_raw = String::new();
    let mut cycles: Option<i64> = None;
    let mut interval = DEFAULT_INTERVAL_SECONDS;
    let mut snapshot_dir: Option<String> = None;
    let mut index = 0;
    while index < args.len() {
        let arg = &args[index];
        let (flag, inline_value) = match arg.split_once('=') {
            Some((flag, value)) if flag.starts_with("--") => {
                (flag.to_string(), Some(value.to_string()))
            }
            _ => (arg.clone(), None),
        };
        match flag.as_str() {
            "--machines" => {
                if let Some(value) = inline_value {
                    machines_raw = value;
                } else if index + 1 < args.len() && !args[index + 1].starts_with("--") {
                    machines_raw = args[index + 1].clone();
                    index += 1;
                } else {
                    machines_raw = String::new();
                }
            }
            "--cycles" => {
                let value = match inline_value {
                    Some(value) => value,
                    None => {
                        index += 1;
                        args.get(index).cloned().ok_or("missing --cycles value")?
                    }
                };
                cycles = Some(
                    value
                        .parse::<i64>()
                        .map_err(|_| "invalid --cycles value".to_string())?,
                );
            }
            "--interval" => {
                let value = match inline_value {
                    Some(value) => value,
                    None => {
                        index += 1;
                        args.get(index).cloned().ok_or("missing --interval value")?
                    }
                };
                interval = value
                    .parse::<f64>()
                    .map_err(|_| "invalid --interval value".to_string())?;
            }
            "--snapshot-dir" => {
                let value = match inline_value {
                    Some(value) => value,
                    None => {
                        index += 1;
                        args.get(index)
                            .cloned()
                            .ok_or("missing --snapshot-dir value")?
                    }
                };
                snapshot_dir = Some(value);
            }
            other => return Err(format!("unknown argument: {}", other)),
        }
        index += 1;
    }
    let machines: Vec<String> = machines_raw
        .split(',')
        .map(|name| name.trim().to_string())
        .filter(|name| !name.is_empty())
        .collect();
    Ok(CliArgs {
        machines,
        cycles,
        interval,
        snapshot_dir,
    })
}

/// Command entry point: the command relay-watchman-watch.service execs.
///
/// `python3 intel/watchman_service.py --machines alpha,beta [--cycles
/// N] [--interval SECONDS] [--snapshot-dir DIR]` in Python; here the
/// same arguments as a slice (without the program name). Returns 0 on a
/// completed loop, 2 on a malformed command line. Prints one `cycle N`
/// line per cycle and a final stopped line, as the Python entry point
/// does. See the module docs for the Ctrl-C boundary: this function
/// does not catch interrupts.
pub fn service_main(argv: &[String]) -> i32 {
    let args = match parse_service_args(argv) {
        Ok(args) => args,
        Err(err) => {
            eprintln!("error: {}", err);
            return 2;
        }
    };
    let mut options = ServeOptions::default();
    options.max_cycles = args.cycles;
    options.interval_seconds = Some(args.interval);
    options.snapshot_dir = args.snapshot_dir.clone();
    options.on_cycle = Some(Box::new(
        |index: usize,
         records: &HashMap<String, WatchmanRecord>,
         new_journal: &[JournalEntry],
         diagnostics: &CycleDiagnostics| {
            println!(
                "cycle {}: {} machines, {} new journal, {:?}",
                index,
                records.len(),
                new_journal.len(),
                diagnostics
            );
        },
    ));
    let result = serve_cycles(MachinesArg::List(args.machines), options);
    println!("service loop stopped after {} cycles", result.cycles_run);
    0
}

#[cfg(test)]
mod tests {
    use super::*;

    const NOW: f64 = 1_000_000.0;

    fn cycle_with(records: HashMap<String, WatchmanRecord>, entry: &str) -> CycleFnOutput {
        let mut journal_entry = JournalEntry::new(entry, "");
        journal_entry.machine = String::new();
        CycleFnOutput::Triple(records, vec![journal_entry], CycleDiagnostics::default())
    }

    fn journal_entry(kind: &str) -> JournalEntry {
        JournalEntry::new(kind, "")
    }

    fn serve_with(
        cycle_fn: Box<
            dyn FnMut(
                Vec<String>,
                f64,
                HashMap<String, WatchmanRecord>,
                Vec<JournalEntry>,
            ) -> CycleFnOutput,
        >,
        max_cycles: Option<i64>,
        now_value: f64,
    ) -> ServiceResult {
        let mut options = ServeOptions::default();
        options.cycle_fn = Some(cycle_fn);
        options.now_fn = Some(Box::new(move || Some(now_value)));
        options.sleep_fn = Some(Box::new(|_: f64| {}));
        options.max_cycles = max_cycles;
        serve_cycles(MachinesArg::List(vec!["alpha".to_string()]), options)
    }

    #[test]
    fn test_priors_and_journal_carry_across_cycles() {
        // Mirrors ServiceLoopTest.test_priors_and_journal_carry_across_cycles.
        // Python journal entries are strings ("n<now>"); here the entry
        // kind carries that payload.
        let seen: std::rc::Rc<std::cell::RefCell<Vec<(HashMap<String, WatchmanRecord>, Vec<JournalEntry>)>>> =
            std::rc::Rc::new(std::cell::RefCell::new(Vec::new()));
        let seen_clone = seen.clone();
        let cycle_fn = Box::new(
            move |_machines: Vec<String>,
                  now: f64,
                  priors: HashMap<String, WatchmanRecord>,
                  journal: Vec<JournalEntry>| {
                seen_clone
                    .borrow_mut()
                    .push((priors.clone(), journal.clone()));
                let mut records: HashMap<String, WatchmanRecord> = HashMap::new();
                let mut record = WatchmanRecord::new();
                record.last_tick = Some(now);
                records.insert("alpha".to_string(), record);
                CycleFnOutput::Triple(
                    records,
                    vec![journal_entry(&format!("n{}", now as i64))],
                    CycleDiagnostics::default(),
                )
            },
        );
        let result = serve_with(cycle_fn, Some(2), NOW);
        assert_eq!(result.cycles_run, 2);
        let seen = seen.borrow();
        assert!(seen[0].0.is_empty());
        assert!(seen[0].1.is_empty());
        assert_eq!(seen[1].0["alpha"].last_tick, Some(NOW));
        assert_eq!(seen[1].1.len(), 1);
        assert_eq!(seen[1].1[0].kind, "n1000000");
        assert_eq!(result.journal.len(), 2);
        assert!(result.journal.iter().all(|e| e.kind == "n1000000"));
    }

    #[test]
    fn test_sleep_only_between_cycles() {
        // Mirrors test_sleep_only_between_cycles.
        let sleeps: std::rc::Rc<std::cell::RefCell<Vec<f64>>> =
            std::rc::Rc::new(std::cell::RefCell::new(Vec::new()));
        let sleeps_clone = sleeps.clone();
        let mut options = ServeOptions::default();
        options.cycle_fn = Some(Box::new(
            move |_, _, _, _| cycle_with(HashMap::new(), "x"),
        ));
        options.now_fn = Some(Box::new(|| Some(NOW)));
        options.sleep_fn = Some(Box::new(move |seconds: f64| {
            sleeps_clone.borrow_mut().push(seconds);
        }));
        options.max_cycles = Some(3);
        options.interval_seconds = Some(45.0);
        let result = serve_cycles(
            MachinesArg::List(vec!["alpha".to_string()]),
            options,
        );
        assert_eq!(result.cycles_run, 3);
        assert_eq!(*sleeps.borrow(), vec![45.0, 45.0]);
    }

    #[test]
    fn test_zero_cycles_runs_nothing() {
        // Mirrors test_zero_cycles_runs_nothing.
        let mut options = ServeOptions::default();
        options.cycle_fn = Some(Box::new(|_, _, _, _| {
            panic!("must not run");
        }));
        options.sleep_fn = Some(Box::new(|_: f64| {}));
        options.max_cycles = Some(0);
        let result = serve_cycles(
            MachinesArg::List(vec!["alpha".to_string()]),
            options,
        );
        assert_eq!(result.cycles_run, 0);
        assert!(result.records.is_empty());
    }

    #[test]
    fn test_should_stop_stops_without_sleep() {
        // Mirrors test_should_stop_stops_without_sleep.
        let sleeps: std::rc::Rc<std::cell::RefCell<Vec<f64>>> =
            std::rc::Rc::new(std::cell::RefCell::new(Vec::new()));
        let sleeps_clone = sleeps.clone();
        let mut options = ServeOptions::default();
        options.cycle_fn = Some(Box::new(
            move |_, _, _, _| cycle_with(HashMap::new(), "x"),
        ));
        options.now_fn = Some(Box::new(|| Some(NOW)));
        options.sleep_fn = Some(Box::new(move |seconds: f64| {
            sleeps_clone.borrow_mut().push(seconds);
        }));
        options.max_cycles = Some(5);
        options.should_stop = Some(Box::new(
            |index: usize, _, _| index == 0,
        ));
        let result = serve_cycles(
            MachinesArg::List(vec!["alpha".to_string()]),
            options,
        );
        assert_eq!(result.cycles_run, 1);
        assert!(sleeps.borrow().is_empty());
    }

    #[test]
    fn test_raising_cycle_contained_and_loop_recovers() {
        // Mirrors test_raising_cycle_contained_and_loop_recovers.
        // The Python cycle raises RuntimeError; here the closure
        // panics, and the cycle error is recorded as "panic" (see the
        // module docs: Rust panics carry no exception type name).
        let calls: std::rc::Rc<std::cell::RefCell<usize>> =
            std::rc::Rc::new(std::cell::RefCell::new(0));
        let calls_clone = calls.clone();
        let cycle_fn = Box::new(
            move |_, _, _, _| {
                *calls_clone.borrow_mut() += 1;
                if *calls_clone.borrow() == 1 {
                    panic!("boom");
                }
                let mut records: HashMap<String, WatchmanRecord> = HashMap::new();
                records.insert(
                    "alpha".to_string(),
                    WatchmanRecord {
                        watchman_alive: Some(true),
                        ..Default::default()
                    },
                );
                CycleFnOutput::Triple(records, Vec::new(), CycleDiagnostics::default())
            },
        );
        let result = serve_with(cycle_fn, Some(2), NOW);
        assert_eq!(result.cycles_run, 2);
        assert_eq!(
            result.diagnostics_by_cycle[0].runner_errors["cycle_error"],
            "panic"
        );
        assert_eq!(
            result.records["alpha"].watchman_alive,
            Some(true)
        );
    }

    #[test]
    fn test_raising_callback_and_stop_contained() {
        // Mirrors test_raising_callback_and_stop_contained. Python
        // records "ValueError" and "KeyError"; Rust panics record
        // "panic" for both (see the module docs).
        let mut options = ServeOptions::default();
        options.cycle_fn = Some(Box::new(
            move |_, _, _, _| cycle_with(HashMap::new(), "x"),
        ));
        options.now_fn = Some(Box::new(|| Some(NOW)));
        options.sleep_fn = Some(Box::new(|_: f64| {}));
        options.max_cycles = Some(2);
        options.on_cycle = Some(Box::new(|_, _, _, _| {
            panic!("callback boom");
        }));
        options.should_stop = Some(Box::new(|_, _, _| {
            panic!("stop boom");
        }));
        let result = serve_cycles(
            MachinesArg::List(vec!["alpha".to_string()]),
            options,
        );
        assert_eq!(result.cycles_run, 2);
        assert_eq!(result.callback_errors, ["panic", "panic"]);
    }

    #[test]
    fn test_raising_clock_contained() {
        // Mirrors test_raising_clock_contained. A Python clock that
        // raises yields the literal "clock" cycle error; here a clock
        // returning None (or panicking) yields the same.
        let mut options = ServeOptions::default();
        options.cycle_fn = Some(Box::new(|_, _, _, _| {
            let mut records: HashMap<String, WatchmanRecord> = HashMap::new();
            records.insert("alpha".to_string(), WatchmanRecord::new());
            cycle_with(records, "x")
        }));
        options.now_fn = Some(Box::new(|| None));
        options.sleep_fn = Some(Box::new(|_: f64| {}));
        options.max_cycles = Some(1);
        let result = serve_cycles(
            MachinesArg::List(vec!["alpha".to_string()]),
            options,
        );
        assert_eq!(result.cycles_run, 1);
        assert_eq!(
            result.diagnostics_by_cycle[0].runner_errors["cycle_error"],
            "clock"
        );
    }

    #[test]
    fn test_bad_cycle_return_contained() {
        // Mirrors test_bad_cycle_return_contained.
        let cycle_fn = Box::new(|_, _, _, _| CycleFnOutput::Bad);
        let result = serve_with(cycle_fn, Some(1), NOW);
        assert_eq!(result.cycles_run, 1);
        assert_eq!(
            result.diagnostics_by_cycle[0].runner_errors["cycle_error"],
            "bad-cycle-return"
        );
    }

    #[test]
    fn test_negative_interval_means_no_sleep_delay() {
        // Mirrors test_negative_interval_means_no_sleep_delay.
        let sleeps: std::rc::Rc<std::cell::RefCell<Vec<f64>>> =
            std::rc::Rc::new(std::cell::RefCell::new(Vec::new()));
        let sleeps_clone = sleeps.clone();
        let mut options = ServeOptions::default();
        options.cycle_fn = Some(Box::new(
            move |_, _, _, _| cycle_with(HashMap::new(), "x"),
        ));
        options.now_fn = Some(Box::new(|| Some(NOW)));
        options.sleep_fn = Some(Box::new(move |seconds: f64| {
            sleeps_clone.borrow_mut().push(seconds);
        }));
        options.max_cycles = Some(2);
        options.interval_seconds = Some(-5.0);
        serve_cycles(
            MachinesArg::List(vec!["alpha".to_string()]),
            options,
        );
        assert_eq!(*sleeps.borrow(), vec![0.0]);
    }

    #[test]
    fn test_inputs_never_mutated() {
        // Mirrors test_inputs_never_mutated.
        let machines = MachinesArg::List(vec!["alpha".to_string()]);
        let mut priors: HashMap<String, WatchmanRecord> = HashMap::new();
        priors.insert(
            "alpha".to_string(),
            WatchmanRecord {
                watchman_alive: Some(false),
                ..Default::default()
            },
        );
        let journal = vec![journal_entry("old")];
        let priors_before = priors.clone();
        let journal_before = journal.clone();
        let mut options = ServeOptions::default();
        options.cycle_fn = Some(Box::new(
            move |_, _, _, _| cycle_with(HashMap::new(), "x"),
        ));
        options.now_fn = Some(Box::new(|| Some(NOW)));
        options.sleep_fn = Some(Box::new(|_: f64| {}));
        options.max_cycles = Some(1);
        options.priors = Some(priors.clone());
        options.journal = Some(journal.clone());
        serve_cycles(machines, options);
        assert_eq!(priors, priors_before);
        assert_eq!(journal, journal_before);
    }

    #[test]
    fn test_default_path_rings_on_real_snapshots() {
        // Mirrors test_default_path_rings_on_real_snapshots, using the
        // default cycle function against temp snapshots. The default
        // program is resolved from CARGO_MANIFEST_DIR; when the test
        // binary runs outside cargo, point it at this repo's crate dir.
        if std::env::var("CARGO_MANIFEST_DIR").is_err() {
            if let Ok(cwd) = std::env::current_dir() {
                let manifest = cwd.join("crates/os-supervisor");
                if manifest.exists() {
                    std::env::set_var("CARGO_MANIFEST_DIR", &manifest);
                }
            }
        }
        let dir = std::env::temp_dir().join(format!(
            "watchman-service-test-{}",
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&dir).unwrap();
        let dir_str = dir.to_string_lossy().to_string();
        std::fs::write(
            dir.join("watchman-jobs-alpha.json"),
            r#"[{"id": "j1", "status": "open", "addressed_to": "hana", "title": "Write the brief"}]"#,
        )
        .unwrap();
        std::fs::write(
            dir.join("watchman-agents-alpha.json"),
            r#"{"hana": {"nick": "hana", "heartbeat_at": null}}"#,
        )
        .unwrap();
        let clock: std::rc::Rc<std::cell::RefCell<f64>> =
            std::rc::Rc::new(std::cell::RefCell::new(NOW));
        let clock_clone = clock.clone();
        let mut options = ServeOptions::default();
        options.now_fn = Some(Box::new(move || {
            let value = *clock_clone.borrow();
            *clock_clone.borrow_mut() += 60.0;
            Some(value)
        }));
        options.sleep_fn = Some(Box::new(|_: f64| {}));
        options.max_cycles = Some(2);
        options.snapshot_dir = Some(dir_str);
        let result = serve_cycles(
            MachinesArg::List(vec!["alpha".to_string()]),
            options,
        );
        let alpha = result.records.get("alpha").cloned().unwrap_or_default();
        assert_eq!(alpha.watchman_alive, Some(true));
        assert!(alpha.last_bell.is_some());
        assert!(result.diagnostics_by_cycle[0].run_failures.is_empty());
    }

    #[test]
    fn test_unit_directives_match_unit_contract() {
        // Mirrors test_intel_watchman_service_unit:
        // test_exec_runs_service_loop_entry_point and
        // test_ordering_restart_and_identity, against the ported unit
        // directives (the unit file itself is a systemd artifact; see
        // the module docs).
        let exec = unit_directive("ExecStart").unwrap();
        assert!(exec.contains("/opt/relay/intel/watchman_service.py"));
        assert!(exec.contains("--snapshot-dir /run/metaos"));
        assert!(exec.contains("--machines ${WATCHMAN_WATCH_MACHINES}"));
        assert!(unit_directive("After").unwrap().contains("relay-watchman.service"));
        assert_eq!(unit_directive("Restart").unwrap(), "on-failure");
        assert_eq!(unit_directive("User").unwrap(), "relay");
        assert_eq!(unit_directive("WorkingDirectory").unwrap(), "/opt/relay");
        assert_eq!(unit_directive("WantedBy").unwrap(), "relay.target");
        assert_eq!(
            unit_directive("EnvironmentFile").unwrap(),
            "-/etc/metaos/watchman-watch.env"
        );
        // Mirrors test_header_states_machine_list_gap_and_proof_gap.
        assert!(UNIT_MACHINE_LIST_GAP.contains("no machine-naming convention exists"));
        assert!(UNIT_MACHINE_LIST_GAP.contains("NOT proven here"));
        assert!(UNIT_MACHINE_LIST_GAP.contains("not a live watcher"));
    }

    #[test]
    fn test_cli_parsing_bare_and_empty_machines() {
        // Mirrors the CLI tests' argument shapes (bare --machines and
        // empty --machines) at the parser level; the Python tests run
        // the script as a subprocess, which has no Rust equivalent in a
        // library crate.
        let args: Vec<String> = vec![
            "--machines".to_string(),
            "--snapshot-dir".to_string(),
            "/tmp/snap".to_string(),
            "--cycles".to_string(),
            "1".to_string(),
            "--interval".to_string(),
            "0".to_string(),
        ];
        let parsed = parse_service_args(&args).unwrap();
        assert!(parsed.machines.is_empty());
        assert_eq!(parsed.cycles, Some(1));
        assert_eq!(parsed.interval, 0.0);
        let args: Vec<String> = vec![
            "--machines".to_string(),
            "alpha, beta".to_string(),
            "--cycles".to_string(),
            "2".to_string(),
        ];
        let parsed = parse_service_args(&args).unwrap();
        assert_eq!(parsed.machines, ["alpha", "beta"]);
        assert_eq!(parsed.cycles, Some(2));
        let args: Vec<String> = vec![
            "--machines".to_string(),
            String::new(),
            "--cycles".to_string(),
            "1".to_string(),
        ];
        let parsed = parse_service_args(&args).unwrap();
        assert!(parsed.machines.is_empty());
        assert!(parse_service_args(&["--cycles".to_string(), "nope".to_string()]).is_err());
        assert!(parse_service_args(&["--unknown".to_string()]).is_err());
    }

    #[test]
    fn test_service_main_runs_one_cycle_on_real_snapshots() {
        // End-to-end mirror of the CLI test's plain-command case, at
        // the library entry point: one cycle over real snapshots
        // returns 0. Output lines go to stdout, as in Python.
        if std::env::var("CARGO_MANIFEST_DIR").is_err() {
            if let Ok(cwd) = std::env::current_dir() {
                let manifest = cwd.join("crates/os-supervisor");
                if manifest.exists() {
                    std::env::set_var("CARGO_MANIFEST_DIR", &manifest);
                }
            }
        }
        let dir = std::env::temp_dir().join(format!(
            "watchman-service-cli-test-{}",
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&dir).unwrap();
        let dir_str = dir.to_string_lossy().to_string();
        std::fs::write(
            dir.join("watchman-jobs-alpha.json"),
            r#"[{"id": "j1", "status": "open", "addressed_to": "hana", "title": "Write the brief"}]"#,
        )
        .unwrap();
        std::fs::write(
            dir.join("watchman-agents-alpha.json"),
            r#"{"hana": {"nick": "hana", "heartbeat_at": null}}"#,
        )
        .unwrap();
        let code = service_main(&[
            "--machines".to_string(),
            "alpha".to_string(),
            "--cycles".to_string(),
            "1".to_string(),
            "--interval".to_string(),
            "0".to_string(),
            "--snapshot-dir".to_string(),
            dir_str,
        ]);
        assert_eq!(code, 0);
    }
}
