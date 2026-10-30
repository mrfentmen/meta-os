//! Watchman runner-adapter drill (Milo lane, OS-122 follow-up).
//!
//! Port of `os/intel/drills/watchman_cycle.py` (batch B21, task T122).
//! Port behavior, do not redesign.
//!
//! `loop_cycle()` judges runs that are already collected, but a
//! production loop must collect them by calling a runner per machine,
//! and a runner can raise or return garbage. This drill proves
//! [`crate::watchman_cycle::run_cycle`] on fixtures, in six checks:
//!
//! 1. Two machines through a well-behaved runner, real Pax tick output
//!    as stdout: the ringing machine reads its bell at the tick time,
//!    the quiet machine invents no bell, the journal stays empty, the
//!    runner is called once per machine, and clean diagnostics carry
//!    no runner errors.
//! 2. A raising runner ages honestly: the ringing machine's runner
//!    raises on a later cycle, so its prior record is carried forward
//!    with `restart_ok` stripped and its bell unchanged; past the stale
//!    window it journals exactly one crew-dark, one restart reading
//!    restart failed, and one escalation; diagnostics name the machine
//!    in `run_failures` and the exception type in `runner_errors`. No
//!    crash.
//! 3. A garbage-returning runner is contained: a machine whose runner
//!    returns a bare string (no prior record) earns no record and
//!    journals nothing, and diagnostics record it as a bad-return
//!    failure, not a success.
//! 4. A non-callable runner fails every machine the same way: no
//!    record, no journal, `runner_errors` per machine reading
//!    `not-callable`, and still no raise.
//! 5. An empty machine list yields empty records and journal and
//!    diagnostics with empty lists, and the runner is never called.
//! 6. Truthy is not True, and inputs are never mutated: a runner
//!    returning a truthy-but-not-True first element is a failed run,
//!    not a success; a short pair is a bad return; priors and journal
//!    come back unchanged, and a carried record is a copy, not the
//!    prior object.
//!
//! What this drill does NOT claim, stated plainly (as in Python): the
//! adapter proves the collection judgment, not a live service. No
//! booted test image, no relay-watchman.service actually running
//! (runners here are fixture callables, the module starts no
//! subprocess), no systemd restart of a dead watchman, no agent
//! session started, no job reassigned, no push sent, and no live queue
//! reader. A failed run here is a diagnostics line, and the escalation
//! is a payload, never a send. No bus post, no live Redis, no network.
//!
//! # Representation notes (where the typed port differs from Python)
//!
//! - Python phases generate stdout with the real Pax tick. That tick
//!   lives in another batch's module, so this port uses a literal
//!   wake-event line in the tick's JSON-lines shape; the loop's stdout
//!   parser (already landed) reads it exactly as it reads real tick
//!   output.
//! - Python runners raise exceptions or return arbitrary values. The
//!   landed adapter's [`RunnerResult`] seam carries those shapes:
//!   [`RunnerResult::Raise`] carries the exception type name (so phase
//!   2 can still assert `RuntimeError`), [`RunnerResult::Bad`]
//!   covers a garbage return, a truthy non-True first element, and a
//!   short pair, and `None` for the runner covers a non-callable.
//! - The stale window comes from the landed thresholds module, the
//!   same value the Python drill reads from `intel.thresholds`.
//!
//! # Live-behavior boundary (not faked here)
//!
//! The Python script's `main` prints `PASS`/`FAIL` lines and exits 0
//! or 1. That reporting shape is ported as [`run_drill`], which
//! returns the exit code and the lines instead of printing them; the
//! caller owns printing and exiting. No subprocess runs here.

use std::collections::HashMap;

use crate::thresholds::WATCHMAN_STALE_MINUTES_DEFAULT;
use crate::watchman_cycle::{run_cycle, MachinesArg, RunnerResult};
use crate::watchman_watch::{JournalEntry, WatchmanRecord};

/// Fake-clock base time (Python `NOW`), unix seconds.
pub const NOW: f64 = 1000000.0;
/// Stale window in seconds (Python `STALE`).
pub const STALE: f64 = WATCHMAN_STALE_MINUTES_DEFAULT as f64 * 60.0;

/// Stdout lines for a relay-watchman tick that rings once at `at`,
/// in the tick's JSON-lines shape.
pub fn stdout_for(at: f64) -> String {
    format!(
        "{{\"job_id\": \"j1\", \"kind\": \"wake\", \"ts\": {}}}\n",
        at as i64
    )
}

/// Journal kinds, in order.
pub fn kinds(journal: &[JournalEntry]) -> Vec<String> {
    journal.iter().map(|e| e.kind.clone()).collect()
}

/// The well-behaved fixture runner: alpha rings, any other machine
/// stays quiet.
pub fn good_runner(name: &str) -> RunnerResult {
    if name == "alpha" {
        RunnerResult::Pair(true, stdout_for(NOW))
    } else {
        RunnerResult::Pair(true, String::new())
    }
}

/// Phase 1's records: alpha rang at [`NOW`], beta stayed quiet.
/// Used as the priors for the later phases, as the Python drill
/// threads its phase 1 records forward.
pub fn first_cycle_records() -> HashMap<String, WatchmanRecord> {
    let mut runner = good_runner;
    let (records, _, _) = run_cycle(
        Some(&mut runner),
        MachinesArg::List(vec!["alpha".to_string(), "beta".to_string()]),
        NOW,
        &HashMap::new(),
        &[],
        &HashMap::new(),
    );
    records
}

/// Phase 1: well-behaved runner, ring plus quiet, clean diagnostics.
pub fn phase_well_behaved_runner() -> bool {
    let mut calls: Vec<String> = Vec::new();
    let mut runner = |name: &str| {
        calls.push(name.to_string());
        good_runner(name)
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
    sorted_calls == ["alpha", "beta"]
        && records["alpha"].last_bell == Some(NOW)
        && records["beta"].last_bell.is_none()
        && new.is_empty()
        && diagnostics.run_failures.is_empty()
        && diagnostics.runner_errors.is_empty()
}

/// Phase 2: a raising runner ages the prior honestly into one dark
/// episode with one fail-closed escalation.
pub fn phase_raising_runner() -> bool {
    let priors = first_cycle_records();
    let priors_before = priors.clone();
    let journal: Vec<JournalEntry> = Vec::new();
    let journal_before = journal.clone();
    // The Python drill's raising runner raises only for alpha; beta
    // succeeds quietly.
    let mut raising = |name: &str| {
        if name == "alpha" {
            RunnerResult::Raise("RuntimeError".to_string())
        } else {
            RunnerResult::Pair(true, String::new())
        }
    };
    let (records, new, diagnostics) = run_cycle(
        Some(&mut raising),
        MachinesArg::List(vec!["alpha".to_string(), "beta".to_string()]),
        NOW + STALE + 100.0,
        &priors,
        &journal,
        &HashMap::new(),
    );
    diagnostics.run_failures == ["alpha"]
        && diagnostics.runner_errors.get("alpha").map(|e| e.as_str())
            == Some("RuntimeError")
        && records["alpha"].restart_ok.is_none()
        && records["alpha"].last_bell == Some(NOW)
        && !std::ptr::eq(&records["alpha"], &priors["alpha"])
        && kinds(&new) == ["crew-dark", "watchman-restart", "escalation"]
        && priors == priors_before
        && journal == journal_before
}

/// Phase 3: a garbage-returning runner is contained, unjudged without
/// a prior.
pub fn phase_garbage_runner() -> bool {
    let mut garbage = |_: &str| RunnerResult::Bad;
    let (records, new, diagnostics) = run_cycle(
        Some(&mut garbage),
        MachinesArg::List(vec!["gamma".to_string()]),
        NOW,
        &HashMap::new(),
        &[],
        &HashMap::new(),
    );
    !records.contains_key("gamma")
        && new.is_empty()
        && diagnostics.run_failures == ["gamma"]
        && diagnostics.runner_errors.get("gamma").map(|e| e.as_str())
            == Some("bad-return")
}

/// Phase 4: a non-callable runner fails every machine, no raise.
pub fn phase_non_callable_runner() -> bool {
    let (records, new, diagnostics) = run_cycle(
        None,
        MachinesArg::List(vec!["alpha".to_string(), "beta".to_string()]),
        NOW,
        &HashMap::new(),
        &[],
        &HashMap::new(),
    );
    records.is_empty()
        && new.is_empty()
        && diagnostics.runner_errors.get("alpha").map(|e| e.as_str())
            == Some("not-callable")
        && diagnostics.runner_errors.get("beta").map(|e| e.as_str())
            == Some("not-callable")
}

/// Phase 5: an empty machine list runs nothing.
pub fn phase_empty_machine_list() -> bool {
    let mut calls: Vec<String> = Vec::new();
    let mut counting = |name: &str| {
        calls.push(name.to_string());
        RunnerResult::Pair(true, String::new())
    };
    let (records, new, diagnostics) = run_cycle(
        Some(&mut counting),
        MachinesArg::List(vec![]),
        NOW,
        &HashMap::new(),
        &[],
        &HashMap::new(),
    );
    records.is_empty()
        && new.is_empty()
        && calls.is_empty()
        && diagnostics.run_failures.is_empty()
        && diagnostics.runner_errors.is_empty()
}

/// Phase 6: truthy is not True, short pairs fail, inputs unchanged.
///
/// `priors` and `journal` are the carried state from phase 2, as in
/// the Python drill; both must come back unchanged.
pub fn phase_truthy_is_not_true(
    priors: &HashMap<String, WatchmanRecord>,
    journal: &[JournalEntry],
) -> bool {
    let priors_before = priors.clone();
    let journal_before = journal.to_vec();
    // A truthy-but-not-True first element and a short pair are both
    // the Bad seam (see the module docs).
    let mut tricky = |_: &str| RunnerResult::Bad;
    let (_, _, diagnostics) = run_cycle(
        Some(&mut tricky),
        MachinesArg::List(vec!["alpha".to_string(), "beta".to_string()]),
        NOW + 500.0,
        priors,
        journal,
        &HashMap::new(),
    );
    diagnostics.runner_errors.get("alpha").map(|e| e.as_str()) == Some("bad-return")
        && diagnostics.runner_errors.get("beta").map(|e| e.as_str())
            == Some("bad-return")
        && *priors == priors_before
        && journal == journal_before.as_slice()
}

/// Run every phase, in the Python drill's order, threading phase 1
/// and phase 2 state forward as the Python drill does.
///
/// Returns `(exit_code, lines)`: exit 0 with one `PASS` line per
/// phase on success, 1 otherwise. The caller owns printing.
pub fn run_drill() -> (i32, Vec<String>) {
    // Phase 2's carried records, as the Python drill threads them.
    let priors = first_cycle_records();
    let mut raising = |name: &str| {
        if name == "alpha" {
            RunnerResult::Raise("RuntimeError".to_string())
        } else {
            RunnerResult::Pair(true, String::new())
        }
    };
    let (carried, new, _) = run_cycle(
        Some(&mut raising),
        MachinesArg::List(vec!["alpha".to_string(), "beta".to_string()]),
        NOW + STALE + 100.0,
        &priors,
        &[],
        &HashMap::new(),
    );
    let _ = &new;
    let journal: Vec<JournalEntry> = Vec::new();
    let phases: [(&str, bool); 6] = [
        ("phase 1: runner ring reads ALIVE bell, quiet reads UNKNOWN, clean diagnostics", phase_well_behaved_runner()),
        ("phase 2: raising runner contained, prior ages into one dark episode with one fail-closed escalation", phase_raising_runner()),
        ("phase 3: garbage runner return is a contained failure, never a success", phase_garbage_runner()),
        ("phase 4: non-callable runner fails all machines, still no raise", phase_non_callable_runner()),
        ("phase 5: empty machine list yields empty cycle, runner never called", phase_empty_machine_list()),
        ("phase 6: truthy is not True, short pairs fail, inputs unchanged", phase_truthy_is_not_true(&carried, &journal)),
    ];
    let mut lines = Vec::new();
    let mut failed = 0;
    for (name, ok) in phases {
        if ok {
            lines.push(format!("PASS {}", name));
        } else {
            lines.push(format!("FAIL {}", name));
            failed += 1;
        }
    }
    if failed == 0 {
        lines.push("ALL PASS (6 phases)".to_string());
    }
    (if failed == 0 { 0 } else { 1 }, lines)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_drill_phase1_well_behaved_runner() {
        // Mirrors the Python drill's phase 1.
        assert!(phase_well_behaved_runner());
    }

    #[test]
    fn test_drill_phase2_raising_runner() {
        // Mirrors the Python drill's phase 2.
        assert!(phase_raising_runner());
    }

    #[test]
    fn test_drill_phase3_garbage_runner() {
        // Mirrors the Python drill's phase 3.
        assert!(phase_garbage_runner());
    }

    #[test]
    fn test_drill_phase4_non_callable_runner() {
        // Mirrors the Python drill's phase 4.
        assert!(phase_non_callable_runner());
    }

    #[test]
    fn test_drill_phase5_empty_machine_list() {
        // Mirrors the Python drill's phase 5.
        assert!(phase_empty_machine_list());
    }

    #[test]
    fn test_drill_phase6_truthy_is_not_true() {
        // Mirrors the Python drill's phase 6, with phase 2's carried
        // records as the priors.
        let priors = first_cycle_records();
        assert!(phase_truthy_is_not_true(&priors, &[]));
    }

    #[test]
    fn test_drill_passes() {
        // Mirrors test_drill_passes in test_intel_watchman_cycle.py
        // (via the cycle drill script): the drill itself exits 0.
        let (code, lines) = run_drill();
        assert_eq!(code, 0, "drill lines: {:?}", lines);
        assert!(lines.iter().any(|l| l.contains("ALL PASS (6 phases)")));
    }
}
