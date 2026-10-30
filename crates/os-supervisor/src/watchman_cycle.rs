//! Runner adapter for the watchman service loop (OS-122 follow-up).
//!
//! Port of `os/intel/watchman_cycle.py`. [`crate::watchman_loop`]'s
//! `loop_cycle()` judges one cycle, but it takes runs that are already
//! collected: `{machine: run}`. Nothing in the repo collected them. A
//! production loop that called a runner itself would have one failure
//! mode `loop_cycle()` never sees: the runner can raise, or return
//! something that is not a `(ok, stdout)` pair at all. Left uncontained,
//! either one crashes the loop, and a crashed loop watches nothing.
//!
//! [`run_cycle`] closes that gap. It takes a caller-supplied runner and a
//! machine list, calls the runner once per machine, and turns whatever
//! comes back into the runs `loop_cycle()` expects:
//!
//! - A runner that raises for a machine yields a failed run for that
//!   machine, never a crash. The exception type is recorded in
//!   diagnostics `runner_errors` and the machine folds through
//!   `loop_cycle()` exactly like any other failed run.
//! - A runner that returns something other than a `(ok, stdout)` pair
//!   (not a tuple/list of length >= 2, or a first element that is not
//!   exactly true/false) yields a failed run too, recorded as
//!   `"bad-return"`. A truthy non-true first element is not accepted as
//!   success: only true means the run happened.
//! - A runner that is not callable at all fails every machine the same
//!   way, recorded per machine, instead of raising on the first call.
//! - An empty machine list yields empty records and journal and
//!   diagnostics with empty lists; no runner error appears when nothing
//!   went wrong with a runner, so a clean cycle's diagnostics keep
//!   `loop_cycle()`'s exact shape (here: an empty `runner_errors` map
//!   means the key is absent).
//!
//! What this module does not claim: it starts no subprocess itself, sends
//! no push, restarts nothing, and reassigns nothing; escalation payloads
//! built by the judge stay payloads, never sends. Inputs are never
//! mutated.
//!
//! Representation notes:
//! - Python runners are callables that may raise arbitrary exception
//!   types or return arbitrary values. Rust closures cannot raise, so
//!   [`RunnerResult::Raise`] is the seam that represents a raising
//!   runner: it carries the exception type name (for example
//!   `"RuntimeError"`), and [`run_cycle`] records it exactly as Python
//!   records `type(exc).__name__`. A closure that actually panics is
//!   also contained (via `catch_unwind`) and recorded as `"panic"`;
//!   Rust panics carry no exception type name to recover.
//! - A Python runner returning a list pair `[true, stdout]` and one
//!   returning a tuple pair `(true, stdout)` are the same shape here:
//!   both are [`RunnerResult::Pair`]. A truthy non-true first element
//!   (for example `1`) and a short pair are both [`RunnerResult::Bad`].

use std::collections::HashMap;
use std::panic::{catch_unwind, AssertUnwindSafe};

use crate::watchman_loop::{loop_cycle, Diagnostics, LoopRun};
use crate::watchman_watch::{JournalEntry, WatchmanRecord};

/// The machine list for one cycle.
///
/// Mirrors Python's duck-typed `machines` argument: `None` is an empty
/// cycle, a single string is one machine, and a list is the list. A
/// non-iterable Python value also reads as an empty cycle; that shape
/// has no typed equivalent and is represented by [`MachinesArg::Empty`].
#[derive(Clone, Debug, Default, PartialEq)]
pub enum MachinesArg {
    /// No machines (Python `None` or a non-iterable value).
    #[default]
    Empty,
    /// One machine (a Python string argument).
    Single(String),
    /// A list of machines.
    List(Vec<String>),
}

impl MachinesArg {
    /// The machine list, in the caller's order.
    pub fn machine_list(&self) -> Vec<String> {
        match self {
            MachinesArg::Empty => Vec::new(),
            MachinesArg::Single(name) => vec![name.clone()],
            MachinesArg::List(names) => names.clone(),
        }
    }
}

/// What a caller-supplied runner returns for one machine.
#[derive(Clone, Debug, PartialEq)]
pub enum RunnerResult {
    /// A usable `(ok, stdout)` pair (tuple or list in Python).
    Pair(bool, String),
    /// A return value that is not a usable pair.
    Bad,
    /// A raising runner, carrying the exception type name (the seam for
    /// Python's `raise`; see the module docs).
    Raise(String),
}

/// Per-cycle diagnostics from [`run_cycle`]: the loop's diagnostics plus
/// a `runner_errors` map when any runner call raised, was not callable,
/// or returned a bad pair. An empty map means the key is absent.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct CycleDiagnostics {
    /// Machines whose runs failed, in machine-name order.
    pub run_failures: Vec<String>,
    /// Malformed stdout line counts, present only for machines that had
    /// malformed lines.
    pub malformed_lines: HashMap<String, usize>,
    /// Runner error reasons by machine, present only for machines whose
    /// runner call failed.
    pub runner_errors: HashMap<String, String>,
}

impl From<Diagnostics> for CycleDiagnostics {
    fn from(diagnostics: Diagnostics) -> Self {
        CycleDiagnostics {
            run_failures: diagnostics.run_failures,
            malformed_lines: diagnostics.malformed_lines,
            runner_errors: HashMap::new(),
        }
    }
}

/// Call the runner once per machine -> `(runs, runner_errors)`.
///
/// `runner` is `None` when the caller supplied no callable at all: every
/// machine fails the same way, recorded per machine as `"not-callable"`.
fn collect_runs(
    runner: Option<&mut dyn FnMut(&str) -> RunnerResult>,
    machines: &[String],
) -> (HashMap<String, LoopRun>, HashMap<String, String>) {
    let mut runs: HashMap<String, LoopRun> = HashMap::new();
    let mut runner_errors: HashMap<String, String> = HashMap::new();
    let runner = match runner {
        Some(runner) => runner,
        None => {
            for name in machines {
                runs.insert(name.clone(), LoopRun::Run(false, String::new()));
                runner_errors.insert(name.clone(), "not-callable".to_string());
            }
            return (runs, runner_errors);
        }
    };
    for name in machines {
        let result = catch_unwind(AssertUnwindSafe(|| runner(name)));
        let result = match result {
            Ok(result) => result,
            Err(_) => RunnerResult::Raise("panic".to_string()),
        };
        match result {
            RunnerResult::Pair(true, stdout) => {
                runs.insert(name.clone(), LoopRun::Run(true, stdout));
            }
            RunnerResult::Pair(false, _) => {
                runs.insert(name.clone(), LoopRun::Run(false, String::new()));
            }
            RunnerResult::Bad => {
                runs.insert(name.clone(), LoopRun::Run(false, String::new()));
                runner_errors.insert(name.clone(), "bad-return".to_string());
            }
            RunnerResult::Raise(reason) => {
                runs.insert(name.clone(), LoopRun::Run(false, String::new()));
                runner_errors.insert(name.clone(), reason);
            }
        }
    }
    (runs, runner_errors)
}

/// One service-loop cycle driven by a caller-supplied runner.
///
/// `runner` is a callable taking a machine name and returning a
/// [`RunnerResult`], or `None` for a non-callable runner. `machines` is
/// the machine list for this cycle. `now`, `priors`, `journal`, and
/// `restart_ok` pass straight through to `loop_cycle()`.
///
/// Returns `(records, new_journal, diagnostics)`: records is the board's
/// latest picture, new_journal holds only this cycle's new records,
/// diagnostics is `loop_cycle()`'s diagnostics plus a `runner_errors`
/// map when any runner call raised, was not callable, or returned a bad
/// pair.
pub fn run_cycle(
    runner: Option<&mut dyn FnMut(&str) -> RunnerResult>,
    machines: MachinesArg,
    now: f64,
    priors: &HashMap<String, WatchmanRecord>,
    journal: &[JournalEntry],
    restart_ok: &HashMap<String, bool>,
) -> (
    HashMap<String, WatchmanRecord>,
    Vec<JournalEntry>,
    CycleDiagnostics,
) {
    let machine_list = machines.machine_list();
    let (runs, runner_errors) = collect_runs(runner, &machine_list);
    let (records, new_journal, diagnostics) =
        loop_cycle(&runs, now, priors, journal, restart_ok);
    let mut diagnostics = CycleDiagnostics::from(diagnostics);
    diagnostics.runner_errors = runner_errors;
    (records, new_journal, diagnostics)
}

#[cfg(test)]
mod tests {
    use super::*;

    const NOW: f64 = 1_000_000.0;
    const STALE: f64 = 5.0 * 60.0;

    /// Stdout lines for a relay-watchman tick that rings once at `at`.
    /// The Python tests generate these via the real relay-watchman
    /// tick(); a literal wake-event line is used here instead.
    fn stdout_for(at: f64) -> String {
        format!(
            "{{\"job_id\": \"j1\", \"kind\": \"wake\", \"ts\": {}}}\n",
            at as i64
        )
    }

    fn ring_runner(name: &str) -> RunnerResult {
        if name == "alpha" {
            RunnerResult::Pair(true, stdout_for(NOW))
        } else {
            RunnerResult::Pair(true, String::new())
        }
    }

    fn kinds(journal: &[JournalEntry]) -> Vec<&str> {
        journal.iter().map(|r| r.kind.as_str()).collect()
    }

    #[test]
    fn test_ring_and_quiet_clean_diagnostics() {
        // Mirrors TestRunCycleSuccess.test_ring_and_quiet_clean_diagnostics.
        let mut calls: Vec<String> = Vec::new();
        let mut runner = |name: &str| {
            calls.push(name.to_string());
            ring_runner(name)
        };
        let (records, new, diagnostics) = run_cycle(
            Some(&mut runner),
            MachinesArg::List(vec!["alpha".to_string(), "beta".to_string()]),
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        let mut sorted_calls = calls.clone();
        sorted_calls.sort();
        assert_eq!(sorted_calls, ["alpha", "beta"]);
        assert_eq!(records["alpha"].last_bell, Some(NOW));
        assert_eq!(records["beta"].last_bell, None);
        assert!(new.is_empty());
        assert!(diagnostics.run_failures.is_empty());
        assert!(diagnostics.runner_errors.is_empty());
    }

    #[test]
    fn test_list_pair_accepted_as_success() {
        // Mirrors test_list_pair_accepted_as_success. A Python list pair
        // and a tuple pair are the same RunnerResult::Pair here.
        let mut runner =
            |_: &str| RunnerResult::Pair(true, stdout_for(NOW));
        let (records, _, _) = run_cycle(
            Some(&mut runner),
            MachinesArg::List(vec!["alpha".to_string()]),
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        assert_eq!(records["alpha"].last_bell, Some(NOW));
    }

    #[test]
    fn test_false_pair_is_failed_not_runner_error() {
        // Mirrors test_false_pair_is_failed_not_runner_error.
        let mut runner = |_: &str| RunnerResult::Pair(false, "unused".to_string());
        let (_, _, diagnostics) = run_cycle(
            Some(&mut runner),
            MachinesArg::List(vec!["alpha".to_string()]),
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        assert_eq!(diagnostics.run_failures, ["alpha"]);
        assert!(diagnostics.runner_errors.is_empty());
    }

    #[test]
    fn test_string_machines_is_one_machine() {
        // Mirrors test_string_machines_is_one_machine.
        let mut runner = |_: &str| RunnerResult::Pair(true, String::new());
        let (records, _, _) = run_cycle(
            Some(&mut runner),
            MachinesArg::Single("alpha".to_string()),
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        assert!(records.contains_key("alpha"));
    }

    #[test]
    fn test_none_machines_is_empty_cycle() {
        // Mirrors test_none_machines_is_empty_cycle.
        let mut runner = |_: &str| RunnerResult::Pair(true, String::new());
        let (records, new, diagnostics) = run_cycle(
            Some(&mut runner),
            MachinesArg::Empty,
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        assert!(records.is_empty());
        assert!(new.is_empty());
        assert!(diagnostics.run_failures.is_empty());
    }

    #[test]
    fn test_raising_runner_carries_prior_and_names_error() {
        // Mirrors test_raising_runner_carries_prior_and_names_error.
        // The Python runner raises RuntimeError; here the Raise seam
        // carries that type name.
        let mut first = ring_runner;
        let (records, _, _) = run_cycle(
            Some(&mut first),
            MachinesArg::List(vec!["alpha".to_string()]),
            NOW,
            &HashMap::new(),
            &[],
            &{
                let mut restart_ok: HashMap<String, bool> = HashMap::new();
                restart_ok.insert("alpha".to_string(), true);
                restart_ok
            },
        );
        let priors = records;
        let mut raising =
            |_: &str| RunnerResult::Raise("RuntimeError".to_string());
        let (carried, new, diagnostics) = run_cycle(
            Some(&mut raising),
            MachinesArg::List(vec!["alpha".to_string()]),
            NOW + STALE + 100.0,
            &priors,
            &[],
            &HashMap::new(),
        );
        assert_eq!(diagnostics.run_failures, ["alpha"]);
        assert_eq!(diagnostics.runner_errors["alpha"], "RuntimeError");
        assert_eq!(carried["alpha"].restart_ok, None);
        assert_eq!(carried["alpha"].last_bell, Some(NOW));
        assert!(!std::ptr::eq(
            &carried["alpha"] as *const WatchmanRecord,
            &priors["alpha"] as *const WatchmanRecord
        ));
        assert_eq!(
            kinds(&new),
            ["crew-dark", "watchman-restart", "escalation"]
        );
    }

    #[test]
    fn test_panicking_runner_is_contained_as_panic() {
        // Rust-only companion to the raising-runner case: a closure that
        // actually panics is contained and recorded as "panic" (Rust
        // panics carry no exception type name to recover).
        let mut runner = |_: &str| -> RunnerResult { panic!("binary missing") };
        let (records, new, diagnostics) = run_cycle(
            Some(&mut runner),
            MachinesArg::List(vec!["alpha".to_string()]),
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        assert!(records.is_empty());
        assert!(new.is_empty());
        assert_eq!(diagnostics.runner_errors["alpha"], "panic");
    }

    #[test]
    fn test_garbage_string_is_bad_return_unjudged() {
        // Mirrors test_garbage_string_is_bad_return_unjudged. A Python
        // runner returning the string "oops" is RunnerResult::Bad here.
        let mut runner = |_: &str| RunnerResult::Bad;
        let (records, new, diagnostics) = run_cycle(
            Some(&mut runner),
            MachinesArg::List(vec!["gamma".to_string()]),
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        assert!(!records.contains_key("gamma"));
        assert!(new.is_empty());
        assert_eq!(diagnostics.runner_errors["gamma"], "bad-return");
    }

    #[test]
    fn test_short_pair_is_bad_return() {
        // Mirrors test_short_pair_is_bad_return.
        let mut runner = |_: &str| RunnerResult::Bad;
        let (_, _, diagnostics) = run_cycle(
            Some(&mut runner),
            MachinesArg::List(vec!["alpha".to_string()]),
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        assert_eq!(diagnostics.runner_errors["alpha"], "bad-return");
    }

    #[test]
    fn test_truthy_one_is_not_true() {
        // Mirrors test_truthy_one_is_not_true. A Python first element
        // of 1 (truthy, not True) is RunnerResult::Bad here.
        let mut runner = |_: &str| RunnerResult::Bad;
        let (records, _, diagnostics) = run_cycle(
            Some(&mut runner),
            MachinesArg::List(vec!["alpha".to_string()]),
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        assert!(!records.contains_key("alpha"));
        assert_eq!(diagnostics.runner_errors["alpha"], "bad-return");
    }

    #[test]
    fn test_non_callable_fails_every_machine() {
        // Mirrors test_non_callable_fails_every_machine.
        let (records, new, diagnostics) = run_cycle(
            None,
            MachinesArg::List(vec!["alpha".to_string(), "beta".to_string()]),
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        assert!(records.is_empty());
        assert!(new.is_empty());
        assert_eq!(diagnostics.runner_errors["alpha"], "not-callable");
        assert_eq!(diagnostics.runner_errors["beta"], "not-callable");
    }

    #[test]
    fn test_empty_machines_never_calls_runner() {
        // Mirrors test_empty_machines_never_calls_runner.
        let mut calls: Vec<String> = Vec::new();
        let mut runner = |name: &str| {
            calls.push(name.to_string());
            RunnerResult::Pair(true, String::new())
        };
        let (records, new, diagnostics) = run_cycle(
            Some(&mut runner),
            MachinesArg::List(vec![]),
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        assert!(calls.is_empty());
        assert!(records.is_empty());
        assert!(new.is_empty());
        assert!(diagnostics.runner_errors.is_empty());
    }

    #[test]
    fn test_priors_and_journal_unchanged() {
        // Mirrors TestRunCycleImmutability.test_priors_and_journal_unchanged.
        let mut first = ring_runner;
        let (records, _, _) = run_cycle(
            Some(&mut first),
            MachinesArg::List(vec!["alpha".to_string()]),
            NOW,
            &HashMap::new(),
            &[],
            &{
                let mut restart_ok: HashMap<String, bool> = HashMap::new();
                restart_ok.insert("alpha".to_string(), true);
                restart_ok
            },
        );
        let priors_before = records.clone();
        let journal = vec![JournalEntry::new("crew-dark", "alpha")];
        let journal_before = journal.clone();
        let mut raising =
            |_: &str| RunnerResult::Raise("ValueError".to_string());
        run_cycle(
            Some(&mut raising),
            MachinesArg::List(vec!["alpha".to_string()]),
            NOW + 10.0,
            &records,
            &journal,
            &HashMap::new(),
        );
        assert_eq!(records, priors_before);
        assert_eq!(journal, journal_before);
    }
}
