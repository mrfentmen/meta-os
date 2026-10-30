//! Watchman subprocess-runner drill (Milo lane, OS-122 follow-up).
//!
//! Port of `os/intel/drills/watchman_runner.py` (batch B21, task
//! T123). Port behavior, do not redesign.
//!
//! `run_cycle()` judged runs that were already collected, and the
//! cycle drill proved the collection judgment on fixture callables.
//! This drill proves the missing half: [`crate::watchman_runner`]
//! actually runs the real Pax OS-118 program,
//! `os/os/watchman/relay_watchman.py --once`, once per machine, and
//! folds the results through `run_cycle()` unchanged. Six checks:
//!
//! 1. The real `--once` run rings: snapshot files for one machine
//!    carry an open job addressed to a sleeping local agent, and the
//!    runner returns a success pair with exactly one wake event naming
//!    the job and the agent. A second run over the same state file
//!    prints nothing: the watchman's own rung dedupe holds, and the run
//!    still counts as success.
//! 2. The full cycle wires through: `run_cycle_with_subprocess` over a
//!    ringing machine and a quiet machine (empty snapshots) yields a
//!    fresh record for the ringer with a bell and no invented bell for
//!    the quiet machine, an empty journal, and clean diagnostics with
//!    no run failures.
//! 3. A hanging watchman is a failed run, not a hung loop: a fake
//!    program that sleeps is killed at the timeout and `run_once()`
//!    reports `timeout`, and the runner pair is `(false, "")`.
//! 4. A nonzero exit discards its stdout: a fake program that prints a
//!    line and exits 3 yields detail `exit-3` and an empty stdout, so
//!    partial lines never reach the loop as if they were events.
//! 5. A missing program and bad inputs are contained: a nonexistent
//!    executable yields `not-found`, an empty argv yields `bad-argv`,
//!    a non-string machine and a raising `command_for` both yield
//!    `(false, "")` from the runner, and nothing raises.
//! 6. A failed run ages honestly through the cycle: a machine whose
//!    runner now fails, with a prior record carrying a bell, comes back
//!    as a carried record with the bell unchanged, and the priors and
//!    journal the caller passed in come back unchanged.
//!
//! What this drill does NOT claim, stated plainly (as in Python): the
//! runner proves the local collection half, not a live service. No
//! booted test image, no relay-watchman.service actually running (the
//! runs here are one-shot `--once` calls from a temp snapshot
//! directory, not the unit), no systemd restart of a dead watchman, no
//! agent session started, no job reassigned, no push sent, and no live
//! queue reader (the snapshots here are hand-written fixtures). A
//! failed run here is a diagnostics line, and the escalation is a
//! payload, never a send. No bus post, no live Redis, no network.
//!
//! # Representation notes (where the typed port differs from Python)
//!
//! - The Pax program is located by [`relay_program`]: the
//!   `WATCHMAN_TEST_PROGRAM` environment variable when set (the same
//!   seam the landed runner tests use), else the repo-relative path
//!   `os/os/watchman/relay_watchman.py` from the working directory.
//!   The drill passes it explicitly to the runner instead of relying
//!   on the landed default-program resolution, so the drill runs the
//!   same way from a temp verification crate as from cargo.
//! - Python phase 1 asserts the wake event's `job_id` and `agent`
//!   fields. The landed loop event type carries only `kind` and `ts`,
//!   so this port asserts kind and timestamp through the landed
//!   stdout parser and job id and agent on the raw output line text
//!   (the relay prints one JSON object per line, sorted keys).
//! - Python `run_once` returns a detail string; the landed Rust
//!   `run_once` returns `Option<String>` (`None` on success). Phase
//!   assertions use the `Some(...)` form.
//! - A Python non-string machine (`None`, `7`) and a non-string argv
//!   part have no typed equivalent. Empty and whitespace-only machine
//!   names and an empty argv part cover their judgement (a contained
//!   failure, never a raise).
//! - Python's raising `command_for` is a panicking closure here; the
//!   landed runner contains panics with `catch_unwind`, so the pair is
//!   still `(false, "")`.
//!
//! # Live-behavior boundary (not faked here)
//!
//! The Python script's `main` prints `PASS`/`FAIL` lines and exits 0
//! or 1. That reporting shape is ported as [`run_drill`], which
//! returns the exit code and the lines instead of printing them; the
//! caller owns printing and exiting. The `--once` runs in phases 1
//! and 2 are real subprocess runs of the Pax program against temp
//! snapshot files, not a live service; phases 3 to 5 run fake
//! programs, also as real subprocesses.

use std::collections::HashMap;
use std::time::Instant;

use crate::watchman_cycle::MachinesArg;
use crate::watchman_loop::parse_event_lines;
use crate::watchman_runner::{
    make_subprocess_runner, run_cycle_with_subprocess, run_once,
    DEFAULT_TIMEOUT_SECONDS,
};
use crate::watchman_watch::{JournalEntry, WatchmanRecord};

/// Fake-clock base time (Python `NOW`), unix seconds.
pub const NOW: f64 = 1000000.0;

/// The repo's relay-watchman program, located as described in the
/// module docs: `WATCHMAN_TEST_PROGRAM` when set, else the landed
/// `watchman_runner::default_program()` (CARGO_MANIFEST_DIR under
/// cargo, repo-relative otherwise). Assembly fix: the old
/// bare-relative fallback assumed a repo-root working directory, but
/// cargo runs test binaries from the crate directory.
pub fn relay_program() -> String {
    if let Ok(path) = std::env::var("WATCHMAN_TEST_PROGRAM") {
        return path;
    }
    crate::watchman_runner::default_program()
}

/// A fresh temp directory for one drill run.
pub fn tmp_dir(prefix: &str) -> std::path::PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "{}{}",
        prefix,
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

/// Write one snapshot file pair for a machine.
pub fn write_snapshots(dir: &std::path::Path, machine: &str, jobs: &str, agents: &str) {
    std::fs::write(
        dir.join(format!("watchman-jobs-{}.json", machine)),
        jobs,
    )
    .unwrap();
    std::fs::write(
        dir.join(format!("watchman-agents-{}.json", machine)),
        agents,
    )
    .unwrap();
}

/// The drill's shared context: temp snapshot directory plus the Pax
/// program path. Phases run in order against one context, as the
/// Python drill runs its phases against one temp directory.
pub struct DrillCtx {
    /// Temp snapshot directory.
    pub dir: std::path::PathBuf,
    /// Pax relay-watchman program path.
    pub program: String,
}

impl DrillCtx {
    /// A fresh context with the Python drill's alpha/beta fixtures
    /// already written.
    pub fn new() -> Self {
        let dir = tmp_dir("watchman-runner-drill-");
        let jobs = r#"[{"id": "j1", "status": "open", "addressed_to": "hana", "title": "Write the brief"}]"#;
        let agents = r#"{"hana": {"nick": "hana", "heartbeat_at": null}}"#;
        write_snapshots(&dir, "alpha", jobs, agents);
        write_snapshots(&dir, "beta", "[]", "{}");
        DrillCtx {
            dir,
            program: relay_program(),
        }
    }

    /// The snapshot directory as a string, for runner calls.
    pub fn dir_str(&self) -> String {
        self.dir.to_string_lossy().to_string()
    }

    /// A subprocess runner over this context's snapshots and program.
    pub fn runner(&self) -> Box<dyn FnMut(&str) -> (bool, String)> {
        make_subprocess_runner(
            None,
            DEFAULT_TIMEOUT_SECONDS,
            &self.dir_str(),
            Some(&self.program),
        )
    }
}

/// Phase 1: the real `--once` run rings once, then dedupes.
pub fn phase_real_once_rings(ctx: &DrillCtx) -> bool {
    let mut run = ctx.runner();
    let (ok, stdout) = run("alpha");
    if !ok {
        return false;
    }
    let (events, malformed) = parse_event_lines(Some(&stdout));
    if events.len() != 1
        || events[0].kind.as_deref() != Some("wake")
        || malformed != 0
        || !stdout.contains("\"job_id\": \"j1\"")
        || !stdout.contains("\"agent\": \"hana\"")
    {
        return false;
    }
    let (ok, stdout) = run("alpha");
    ok && stdout.trim().is_empty()
}

/// Phase 2: the full cycle wires through unchanged.
pub fn phase_full_cycle(ctx: &DrillCtx) -> bool {
    // Reset the alpha snapshots and drop the state file, as the
    // Python drill does, so the cycle rings fresh.
    let jobs = r#"[{"id": "j1", "status": "open", "addressed_to": "hana", "title": "Write the brief"}]"#;
    let agents = r#"{"hana": {"nick": "hana", "heartbeat_at": null}}"#;
    write_snapshots(&ctx.dir, "alpha", jobs, agents);
    let state = ctx.dir.join("watchman-state-alpha.json");
    if state.exists() {
        std::fs::remove_file(&state).unwrap();
    }
    let (records, new_journal, diagnostics) = run_cycle_with_subprocess(
        MachinesArg::List(vec!["alpha".to_string(), "beta".to_string()]),
        NOW,
        &HashMap::new(),
        &[],
        &HashMap::new(),
        None,
        DEFAULT_TIMEOUT_SECONDS,
        &ctx.dir_str(),
        Some(&ctx.program),
    );
    let alpha = records.get("alpha").cloned().unwrap_or_default();
    let beta = records.get("beta").cloned().unwrap_or_default();
    alpha.watchman_alive == Some(true)
        && alpha.last_bell.is_some()
        && beta.last_bell.is_none()
        && new_journal.is_empty()
        && diagnostics.run_failures.is_empty()
}

/// Phase 3: a hanging watchman is killed at the timeout.
pub fn phase_hanging_timeout(ctx: &DrillCtx) -> bool {
    let sleepy = ctx.dir.join("sleepy.py");
    std::fs::write(&sleepy, "import time\ntime.sleep(30)\n").unwrap();
    let sleepy_str = sleepy.to_string_lossy().to_string();
    let (ok, stdout, detail) = run_once(
        &["python3".to_string(), sleepy_str.clone()],
        1.0,
    );
    if (ok, stdout.as_str(), detail.as_deref()) != (false, "", Some("timeout")) {
        return false;
    }
    let started = Instant::now();
    let mut runner = make_subprocess_runner(
        Some(Box::new(move |_: &str| {
            Some(vec!["python3".to_string(), sleepy_str.clone()])
        })),
        1.0,
        &ctx.dir_str(),
        None,
    );
    let pair = runner("alpha");
    pair == (false, String::new()) && started.elapsed().as_secs() < 20
}

/// Phase 4: a nonzero exit discards partial stdout.
pub fn phase_nonzero_discards(ctx: &DrillCtx) -> bool {
    let partial = ctx.dir.join("partial.py");
    std::fs::write(
        &partial,
        "import sys\nprint('{\"kind\": \"wake\"}')\nsys.exit(3)\n",
    )
    .unwrap();
    let (ok, stdout, detail) = run_once(
        &["python3".to_string(), partial.to_string_lossy().to_string()],
        DEFAULT_TIMEOUT_SECONDS,
    );
    (ok, stdout.as_str(), detail.as_deref()) == (false, "", Some("exit-3"))
}

/// Phase 5: missing program, bad argv, bad machine, and a raising
/// `command_for` are all contained, nothing raises.
pub fn phase_bad_inputs_contained(ctx: &DrillCtx) -> bool {
    let missing = ctx.dir.join("no-such-program").to_string_lossy().to_string();
    let (ok, _, detail) = run_once(&[missing], DEFAULT_TIMEOUT_SECONDS);
    if (ok, detail.as_deref()) != (false, Some("not-found")) {
        return false;
    }
    if run_once(&[], DEFAULT_TIMEOUT_SECONDS)
        != (false, String::new(), Some("bad-argv".to_string()))
    {
        return false;
    }
    if run_once(
        &["python3".to_string(), String::new()],
        DEFAULT_TIMEOUT_SECONDS,
    ) != (false, String::new(), Some("bad-argv".to_string()))
    {
        return false;
    }
    let mut plain = ctx.runner();
    if plain("") != (false, String::new()) || plain("   ") != (false, String::new()) {
        return false;
    }
    let mut raising = make_subprocess_runner(
        Some(Box::new(|_: &str| -> Option<Vec<String>> {
            panic!("boom")
        })),
        DEFAULT_TIMEOUT_SECONDS,
        &ctx.dir_str(),
        None,
    );
    raising("alpha") == (false, String::new())
}

/// Phase 6: a failed run ages honestly; inputs unchanged.
pub fn phase_failed_run_ages(ctx: &DrillCtx) -> bool {
    let mut prior = WatchmanRecord::default();
    prior.watchman_alive = Some(true);
    prior.last_tick = Some(NOW - 1000.0);
    prior.last_bell = Some(NOW - 1000.0);
    prior.last_wake = Some(NOW - 1000.0);
    prior.restart_ok = Some(true);
    let mut priors: HashMap<String, WatchmanRecord> = HashMap::new();
    priors.insert("alpha".to_string(), prior);
    let journal = vec![JournalEntry::new("crew-dark", "beta")];
    let priors_before = priors.clone();
    let journal_before = journal.clone();
    let (records, _, diagnostics) = run_cycle_with_subprocess(
        MachinesArg::List(vec!["alpha".to_string()]),
        NOW,
        &priors,
        &journal,
        &HashMap::new(),
        Some(Box::new(|_: &str| -> Option<Vec<String>> {
            panic!("boom")
        })),
        DEFAULT_TIMEOUT_SECONDS,
        &ctx.dir_str(),
        None,
    );
    let carried = records.get("alpha").cloned().unwrap_or_default();
    carried.last_bell == Some(NOW - 1000.0)
        && carried.restart_ok.is_none()
        && priors == priors_before
        && journal == journal_before
        && diagnostics.run_failures.contains(&"alpha".to_string())
}

/// Run every phase, in the Python drill's order, against one shared
/// context.
///
/// Returns `(exit_code, lines)`: exit 0 with one `PASS` line per
/// phase on success, 1 otherwise. The caller owns printing.
pub fn run_drill() -> (i32, Vec<String>) {
    let ctx = DrillCtx::new();
    let phases: [(&str, bool); 6] = [
        ("phase 1: real --once rings once, then dedupes", phase_real_once_rings(&ctx)),
        ("phase 2: cycle through real runs, bell only where the watchman rang", phase_full_cycle(&ctx)),
        ("phase 3: hanging watchman killed at timeout, failed run, loop unhung", phase_hanging_timeout(&ctx)),
        ("phase 4: nonzero exit discards partial stdout", phase_nonzero_discards(&ctx)),
        ("phase 5: missing program, bad argv, bad machine, raising command_for all contained", phase_bad_inputs_contained(&ctx)),
        ("phase 6: failed run carries the prior bell, old restart stripped, inputs unchanged", phase_failed_run_ages(&ctx)),
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
    fn test_drill_phase1_real_once_rings() {
        // Mirrors the Python drill's phase 1.
        let ctx = DrillCtx::new();
        assert!(phase_real_once_rings(&ctx));
    }

    #[test]
    fn test_drill_phase2_full_cycle() {
        // Mirrors the Python drill's phase 2.
        let ctx = DrillCtx::new();
        assert!(phase_full_cycle(&ctx));
    }

    #[test]
    fn test_drill_phase3_hanging_timeout() {
        // Mirrors the Python drill's phase 3.
        let ctx = DrillCtx::new();
        assert!(phase_hanging_timeout(&ctx));
    }

    #[test]
    fn test_drill_phase4_nonzero_discards() {
        // Mirrors the Python drill's phase 4.
        let ctx = DrillCtx::new();
        assert!(phase_nonzero_discards(&ctx));
    }

    #[test]
    fn test_drill_phase5_bad_inputs_contained() {
        // Mirrors the Python drill's phase 5.
        let ctx = DrillCtx::new();
        assert!(phase_bad_inputs_contained(&ctx));
    }

    #[test]
    fn test_drill_phase6_failed_run_ages() {
        // Mirrors the Python drill's phase 6.
        let ctx = DrillCtx::new();
        assert!(phase_failed_run_ages(&ctx));
    }

    #[test]
    fn test_drill_passes() {
        // Mirrors test_drill_passes in test_intel_watchman_runner.py
        // (via the runner drill script): the drill itself exits 0.
        let (code, lines) = run_drill();
        assert_eq!(code, 0, "drill lines: {:?}", lines);
        assert!(lines.iter().any(|l| l.contains("ALL PASS (6 phases)")));
    }
}
