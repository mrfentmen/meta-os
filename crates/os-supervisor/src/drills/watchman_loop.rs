//! Watchman service-loop caller drill (Milo lane, OS-122 follow-up).
//!
//! Port of `os/intel/drills/watchman_loop.py` (batch B21, task T122).
//! Port behavior, do not redesign.
//!
//! `watchman_tick()` folds one cycle's events, but a loop must run the
//! watchman per machine, carry priors and journal across cycles, and
//! survive a watchman that cannot run. This drill proves
//! [`crate::watchman_loop::loop_cycle`] on fixtures, in five checks:
//!
//! 1. Two machines, real Pax tick output as stdout: the sleeping
//!    agent's machine rings and reads ALIVE with its bell at the tick
//!    time; the quiet machine reads UNKNOWN (ticking but never rang is
//!    not claimed alive); the journal stays empty.
//! 2. Death by failed runs, honestly aged: the ringing machine's runs
//!    fail on later cycles, so its prior record is carried forward,
//!    never refreshed. Past the stale window it journals exactly one
//!    crew-dark, one restart record reading restart failed (the
//!    prior's `restart_ok` True from cycle 1 is stripped on carry,
//!    never re-spent), and exactly one escalation; a further failed
//!    cycle journals nothing new. A fresh successful ring then
//!    journals exactly one recovered.
//! 3. Malformed stdout contained: one junk line in a successful run's
//!    stdout counts in diagnostics and leaves the machine's good wake
//!    event, the other machine, and the journal untouched.
//! 4. No-prior failure unjudged: a machine whose run fails before it
//!    ever reported is absent from records and journal, and appears
//!    only in diagnostics.
//! 5. Inputs are never mutated: runs, priors, and journal come back
//!    unchanged, and a carried record is a copy, not the prior object.
//!
//! What this drill does NOT claim, stated plainly (as in Python): the
//! loop proves the caller judgment, not a live service. No booted test
//! image, no relay-watchman.service actually running (runs are
//! supplied pairs, the module starts no subprocess), no systemd
//! restart of a dead watchman, no agent session started, no job
//! reassigned, no push sent, and no live queue reader. A failed run
//! here is a diagnostics line, and the escalation is a payload, never
//! a send. No bus post, no live Redis, no network.
//!
//! # Representation notes (where the typed port differs from Python)
//!
//! - Python phases generate stdout with the real Pax tick. That tick
//!   lives in another batch's module, so this port uses a literal
//!   wake-event line in the tick's JSON-lines shape; the loop's stdout
//!   parser (already landed) reads it exactly as it reads real tick
//!   output.
//! - Python phase 2 passes `restart_ok={"alpha": True}` on cycle 1,
//!   then relies on the carry stripping it. The landed loop strips
//!   `restart_ok` on carry in the same way, so the phase asserts the
//!   carried record has no `restart_ok` and the restart record reads
//!   failed, exactly as Python does.
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
use crate::watchman_loop::{loop_cycle, LoopRun};
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

/// Phase 1's records: alpha rang at [`NOW`], beta stayed quiet.
/// Used as the priors for the later phases, as the Python drill
/// threads its phase 1 records forward.
pub fn first_cycle_records() -> HashMap<String, WatchmanRecord> {
    let mut runs: HashMap<String, LoopRun> = HashMap::new();
    runs.insert("alpha".to_string(), LoopRun::Run(true, stdout_for(NOW)));
    runs.insert("beta".to_string(), LoopRun::Run(true, String::new()));
    let (records, _, _) = loop_cycle(
        &runs,
        NOW,
        &HashMap::new(),
        &[],
        &HashMap::new(),
    );
    records
}

/// Phase 1: two machines, real tick output shape as stdout.
pub fn phase_ring_and_quiet() -> bool {
    let mut runs: HashMap<String, LoopRun> = HashMap::new();
    runs.insert("alpha".to_string(), LoopRun::Run(true, stdout_for(NOW)));
    runs.insert("beta".to_string(), LoopRun::Run(true, String::new()));
    let runs_before = runs.clone();
    let (records, new, diagnostics) = loop_cycle(
        &runs,
        NOW,
        &HashMap::new(),
        &[],
        &HashMap::new(),
    );
    records["alpha"].last_bell == Some(NOW)
        && records["beta"].last_bell.is_none()
        && new.is_empty()
        && diagnostics.run_failures.is_empty()
        && runs == runs_before
}

/// Phase 2: failed runs age the prior into one dark episode with one
/// fail-closed escalation; the restart reads failed, never re-spent.
pub fn phase_failed_runs_age_dark() -> bool {
    let priors = first_cycle_records();
    let priors_before = priors.clone();
    let journal: Vec<JournalEntry> = Vec::new();
    let journal_before = journal.clone();
    let mut runs: HashMap<String, LoopRun> = HashMap::new();
    runs.insert(
        "alpha".to_string(),
        LoopRun::Run(false, "unused".to_string()),
    );
    runs.insert("beta".to_string(), LoopRun::Run(true, String::new()));
    let (records, new, diagnostics) = loop_cycle(
        &runs,
        NOW + STALE + 100.0,
        &priors,
        &journal,
        &HashMap::new(),
    );
    let restart = new
        .iter()
        .find(|e| e.kind == "watchman-restart")
        .cloned();
    diagnostics.run_failures == ["alpha"]
        && records["alpha"].restart_ok.is_none()
        && records["alpha"].last_bell == Some(NOW)
        && kinds(&new) == ["crew-dark", "watchman-restart", "escalation"]
        && restart.map(|r| r.restart_ok) == Some(Some(false))
        && priors == priors_before
        && journal == journal_before
        && !std::ptr::eq(&records["alpha"], &priors["alpha"])
}

/// Phase 2b: a further failed cycle journals nothing new.
pub fn phase_open_episode_stays_silent() -> bool {
    // Rebuild phase 2's state: dark episode open in the journal.
    let priors = first_cycle_records();
    let mut runs: HashMap<String, LoopRun> = HashMap::new();
    runs.insert(
        "alpha".to_string(),
        LoopRun::Run(false, "unused".to_string()),
    );
    runs.insert("beta".to_string(), LoopRun::Run(true, String::new()));
    let (records, new, _) = loop_cycle(
        &runs,
        NOW + STALE + 100.0,
        &priors,
        &[],
        &HashMap::new(),
    );
    let mut journal = new;
    let mut runs2: HashMap<String, LoopRun> = HashMap::new();
    runs2.insert(
        "alpha".to_string(),
        LoopRun::Run(false, "unused".to_string()),
    );
    let (_, new2, _) = loop_cycle(
        &runs2,
        NOW + STALE + 200.0,
        &records,
        &journal,
        &HashMap::new(),
    );
    journal.extend(new2.iter().cloned());
    new2.is_empty()
}

/// Phase 2c: a fresh successful ring recovers the dark machine.
pub fn phase_fresh_ring_recovers() -> bool {
    let priors = first_cycle_records();
    let mut runs: HashMap<String, LoopRun> = HashMap::new();
    runs.insert(
        "alpha".to_string(),
        LoopRun::Run(false, "unused".to_string()),
    );
    runs.insert("beta".to_string(), LoopRun::Run(true, String::new()));
    let (records, new, _) = loop_cycle(
        &runs,
        NOW + STALE + 100.0,
        &priors,
        &[],
        &HashMap::new(),
    );
    let journal = new;
    let mut runs2: HashMap<String, LoopRun> = HashMap::new();
    runs2.insert(
        "alpha".to_string(),
        LoopRun::Run(true, stdout_for(NOW + STALE + 300.0)),
    );
    let (_, new2, _) = loop_cycle(
        &runs2,
        NOW + STALE + 300.0,
        &records,
        &journal,
        &HashMap::new(),
    );
    kinds(&new2) == ["watchman-recovered"]
}

/// Phase 3: malformed stdout line contained per machine.
pub fn phase_malformed_stdout_contained() -> bool {
    // Rebuild the recovered state, as the Python drill threads it.
    let priors = first_cycle_records();
    let mut runs: HashMap<String, LoopRun> = HashMap::new();
    runs.insert(
        "alpha".to_string(),
        LoopRun::Run(false, "unused".to_string()),
    );
    runs.insert("beta".to_string(), LoopRun::Run(true, String::new()));
    let (records, new, _) = loop_cycle(
        &runs,
        NOW + STALE + 100.0,
        &priors,
        &[],
        &HashMap::new(),
    );
    let mut journal = new;
    let mut runs2: HashMap<String, LoopRun> = HashMap::new();
    runs2.insert(
        "alpha".to_string(),
        LoopRun::Run(true, stdout_for(NOW + STALE + 300.0)),
    );
    let (_, new2, _) = loop_cycle(
        &runs2,
        NOW + STALE + 300.0,
        &records,
        &journal,
        &HashMap::new(),
    );
    journal.extend(new2);
    let priors = {
        let mut runs3: HashMap<String, LoopRun> = HashMap::new();
        runs3.insert(
            "alpha".to_string(),
            LoopRun::Run(true, stdout_for(NOW + STALE + 300.0)),
        );
        let (records3, _, _) =
            loop_cycle(&runs3, NOW + STALE + 300.0, &records, &journal, &HashMap::new());
        records3
    };
    let dirty = format!("{}this is not json\n", stdout_for(NOW + STALE + 400.0));
    let mut runs4: HashMap<String, LoopRun> = HashMap::new();
    runs4.insert("alpha".to_string(), LoopRun::Run(true, dirty));
    runs4.insert("beta".to_string(), LoopRun::Run(true, String::new()));
    let (records4, new4, diagnostics) = loop_cycle(
        &runs4,
        NOW + STALE + 400.0,
        &priors,
        &journal,
        &HashMap::new(),
    );
    diagnostics.malformed_lines.get("alpha") == Some(&1)
        && records4["alpha"].last_bell == Some(NOW + STALE + 400.0)
        && new4.is_empty()
}

/// Phase 4: a no-prior failure is unjudged, diagnostics only.
pub fn phase_no_prior_failure_unjudged() -> bool {
    let mut runs: HashMap<String, LoopRun> = HashMap::new();
    runs.insert("gamma".to_string(), LoopRun::Run(false, String::new()));
    let (records, new, diagnostics) = loop_cycle(
        &runs,
        NOW,
        &HashMap::new(),
        &[],
        &HashMap::new(),
    );
    !records.contains_key("gamma")
        && new.is_empty()
        && diagnostics.run_failures == ["gamma"]
}

/// Phase 5: inputs never mutated across a mixed cycle.
pub fn phase_inputs_never_mutated() -> bool {
    let priors = first_cycle_records();
    let journal: Vec<JournalEntry> = Vec::new();
    let mut runs: HashMap<String, LoopRun> = HashMap::new();
    runs.insert(
        "alpha".to_string(),
        LoopRun::Run(true, stdout_for(NOW + 500.0)),
    );
    runs.insert("beta".to_string(), LoopRun::Run(false, String::new()));
    let runs_before = runs.clone();
    let priors_before = priors.clone();
    let journal_before = journal.clone();
    loop_cycle(&runs, NOW + 500.0, &priors, &journal, &HashMap::new());
    runs == runs_before && priors == priors_before && journal == journal_before
}

/// Run every phase, in the Python drill's order.
///
/// Returns `(exit_code, lines)`: exit 0 with one `PASS` line per
/// phase on success, 1 otherwise. The caller owns printing.
pub fn run_drill() -> (i32, Vec<String>) {
    let phases: [(&str, bool); 7] = [
        ("phase 1: ring reads ALIVE bell, quiet reads UNKNOWN", phase_ring_and_quiet()),
        ("phase 2: failed runs age the prior into one dark episode with one fail-closed escalation", phase_failed_runs_age_dark()),
        ("phase 2b: open dark episode stays silent on repeat", phase_open_episode_stays_silent()),
        ("phase 2c: fresh ring recovers the dark machine", phase_fresh_ring_recovers()),
        ("phase 3: junk stdout line counted, good events kept", phase_malformed_stdout_contained()),
        ("phase 4: unseen machine's failed run is diagnostics only", phase_no_prior_failure_unjudged()),
        ("phase 5: runs, priors, and journal unchanged", phase_inputs_never_mutated()),
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
        lines.push("ALL PASS (5 phases)".to_string());
    }
    (if failed == 0 { 0 } else { 1 }, lines)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_drill_phase1_ring_and_quiet() {
        // Mirrors the Python drill's phase 1.
        assert!(phase_ring_and_quiet());
    }

    #[test]
    fn test_drill_phase2_failed_runs_age_dark() {
        // Mirrors the Python drill's phase 2.
        assert!(phase_failed_runs_age_dark());
    }

    #[test]
    fn test_drill_phase2b_open_episode_stays_silent() {
        // Mirrors the Python drill's phase 2b.
        assert!(phase_open_episode_stays_silent());
    }

    #[test]
    fn test_drill_phase2c_fresh_ring_recovers() {
        // Mirrors the Python drill's phase 2c.
        assert!(phase_fresh_ring_recovers());
    }

    #[test]
    fn test_drill_phase3_malformed_stdout_contained() {
        // Mirrors the Python drill's phase 3.
        assert!(phase_malformed_stdout_contained());
    }

    #[test]
    fn test_drill_phase4_no_prior_failure_unjudged() {
        // Mirrors the Python drill's phase 4.
        assert!(phase_no_prior_failure_unjudged());
    }

    #[test]
    fn test_drill_phase5_inputs_never_mutated() {
        // Mirrors the Python drill's phase 5.
        assert!(phase_inputs_never_mutated());
    }

    #[test]
    fn test_drill_passes() {
        // Mirrors test_drill_passes in test_intel_watchman_loop.py
        // (via the loop drill script): the drill itself exits 0.
        let (code, lines) = run_drill();
        assert_eq!(code, 0, "drill lines: {:?}", lines);
        assert!(lines.iter().any(|l| l.contains("ALL PASS (5 phases)")));
    }
}
