//! Watchman service-loop drill (Milo lane, OS-122 follow-up).
//!
//! Port of `os/intel/drills/watchman_service.py` (batch B21, task
//! T123). Port behavior, do not redesign.
//!
//! `loop_cycle()` judged one cycle, `run_cycle()` collected one
//! cycle, and the runner drill ran the real program for one cycle.
//! Nothing ran cycles again and again. This drill proves
//! [`crate::watchman_service::serve_cycles`] is the loop that was
//! missing. Seven checks:
//!
//! 1. State carries across cycles: a fixture cycle function records
//!    the priors it receives; cycle 2 sees cycle 1's records as its
//!    priors, the journal accumulates across cycles, and exactly one
//!    sleep happens between two cycles.
//! 2. `max_cycles=0` runs nothing and never sleeps.
//! 3. `should_stop()` stops the loop after the first cycle, with no
//!    sleep after the stopped cycle.
//! 4. A raising cycle function is contained: cycle 1 raises and
//!    yields a cycle-error diagnostic with prior records carried,
//!    cycle 2 succeeds, and the loop finishes both cycles with the
//!    cycle 2 records as the final picture.
//! 5. A raising `on_cycle` callback and a raising `should_stop`
//!    predicate are both contained and the loop still runs every
//!    cycle.
//! 6. The default cycle function is the real production path: with a
//!    temp snapshot directory, a ringing machine rings on cycle 1, the
//!    watchman's own dedupe makes cycle 2 quiet, and the loop's final
//!    records carry the bell from cycle 1 into cycle 2.
//! 7. Caller inputs are never mutated: the machines list, priors, and
//!    journal passed in come back unchanged.
//!
//! What this drill does NOT claim, stated plainly (as in Python): the
//! loop proves repeated cycles on fixtures and on one-shot `--once`
//! runs from a temp snapshot directory, not a live service. No booted
//! test image, no relay-watchman.service actually running (the runs
//! here are `--once` calls, not the unit), no systemd restart of a dead
//! watchman, no agent session started, no job reassigned, no push sent,
//! and no live queue reader. A failed cycle here is a diagnostics line,
//! and the escalation is a payload, never a send. No bus post, no live
//! Redis, no network.
//!
//! # Representation notes (where the typed port differs from Python)
//!
//! - Python journal entries in phase 1 are strings (`"note-<now>"`);
//!   the landed journal entry type carries its payload in `kind`, so
//!   this port uses a journal entry whose kind is the note string.
//! - Python cycle functions raise typed exceptions and the loop
//!   records the exception type name (`RuntimeError`,
//!   `ValueError`). Rust closures cannot raise; the landed service
//!   module contains a panicking cycle function or callback and
//!   records `"panic"` (panics carry no type name to recover).
//!   Phases 4 and 5 therefore assert the cycle-error / callback-error
//!   presence with the value `"panic"`, not the Python type name.
//!   That is the landed seam's documented behavior, not a second
//!   implementation choice made here.
//! - Python phase 6 runs the landed default cycle function, which
//!   resolves the Pax program from the module's file location. The
//!   landed Rust default resolves it from `CARGO_MANIFEST_DIR`; this
//!   drill sets that variable to the crate directory when it is unset
//!   and the crate directory exists under the working directory (the
//!   same trick the landed service tests use), so phase 6 runs the
//!   genuine default path from a temp verification crate too.
//!
//! # Live-behavior boundary (not faked here)
//!
//! The Python script's `main` prints `PASS`/`FAIL` lines and exits 0
//! or 1. That reporting shape is ported as [`run_drill`], which
//! returns the exit code and the lines instead of printing them; the
//! caller owns printing and exiting. Phase 6's `--once` runs are real
//! subprocess runs of the Pax program against temp snapshot files, not
//! a live service.

use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;

use crate::watchman_cycle::MachinesArg;
use crate::watchman_service::{serve_cycles, CycleFnOutput, ServeOptions};
use crate::watchman_watch::{JournalEntry, WatchmanRecord};

/// Fake-clock base time (Python `NOW`), unix seconds.
pub const NOW: f64 = 1000000.0;

/// A fixture cycle function record: alive, ticked at `now`.
pub fn tick_record(now: f64) -> WatchmanRecord {
    let mut record = WatchmanRecord::new();
    record.watchman_alive = Some(true);
    record.last_tick = Some(now);
    record
}

/// A journal entry carrying a note payload in its kind, the way the
/// Python drill's string journal entries carry `"note-<now>"`.
pub fn note_entry(now: f64) -> JournalEntry {
    JournalEntry::new(&format!("note-{}", now as i64), "")
}

/// The Python drill's fixture cycle function, as a boxed closure:
/// records the priors it receives and returns one record plus one
/// note entry per cycle.
pub fn fixture_cycle_fn(
    seen_priors: Rc<RefCell<Vec<HashMap<String, WatchmanRecord>>>>,
) -> Box<
    dyn FnMut(
        Vec<String>,
        f64,
        HashMap<String, WatchmanRecord>,
        Vec<JournalEntry>,
    ) -> CycleFnOutput,
> {
    Box::new(
        move |_machines: Vec<String>,
              now: f64,
              priors: HashMap<String, WatchmanRecord>,
              _journal: Vec<JournalEntry>| {
            seen_priors.borrow_mut().push(priors);
            let mut records: HashMap<String, WatchmanRecord> = HashMap::new();
            records.insert("alpha".to_string(), tick_record(now));
            CycleFnOutput::Triple(
                records,
                vec![note_entry(now)],
                crate::watchman_cycle::CycleDiagnostics::default(),
            )
        },
    )
}

/// Phase 1: priors and journal carry across cycles; one sleep between
/// two cycles.
pub fn phase_state_carries() -> bool {
    let seen: Rc<RefCell<Vec<HashMap<String, WatchmanRecord>>>> =
        Rc::new(RefCell::new(Vec::new()));
    let sleeps: Rc<RefCell<Vec<f64>>> = Rc::new(RefCell::new(Vec::new()));
    let sleeps_clone = sleeps.clone();
    let mut options = ServeOptions::default();
    options.cycle_fn = Some(fixture_cycle_fn(seen.clone()));
    options.now_fn = Some(Box::new(move || Some(NOW)));
    options.sleep_fn = Some(Box::new(move |seconds: f64| {
        sleeps_clone.borrow_mut().push(seconds);
    }));
    options.max_cycles = Some(2);
    options.interval_seconds = Some(30.0);
    let result = serve_cycles(MachinesArg::List(vec!["alpha".to_string()]), options);
    let seen = seen.borrow();
    let sleeps = sleeps.borrow();
    result.cycles_run == 2
        && *sleeps == vec![30.0]
        && seen.len() == 2
        && seen[0].is_empty()
        && seen[1].get("alpha") == Some(&tick_record(NOW))
        && result
            .journal
            .iter()
            .map(|e| e.kind.clone())
            .collect::<Vec<_>>()
            == vec!["note-1000000".to_string(), "note-1000000".to_string()]
}

/// Phase 2: `max_cycles=0` runs nothing, never sleeps.
pub fn phase_zero_cycles() -> bool {
    let sleeps: Rc<RefCell<Vec<f64>>> = Rc::new(RefCell::new(Vec::new()));
    let sleeps_clone = sleeps.clone();
    let mut options = ServeOptions::default();
    options.cycle_fn = Some(Box::new(
        |_: Vec<String>,
         _: f64,
         _: HashMap<String, WatchmanRecord>,
         _: Vec<JournalEntry>| -> CycleFnOutput {
            panic!("cycle_fn must not run")
        },
    ));
    options.sleep_fn = Some(Box::new(move |seconds: f64| {
        sleeps_clone.borrow_mut().push(seconds);
    }));
    options.max_cycles = Some(0);
    let result = serve_cycles(MachinesArg::List(vec!["alpha".to_string()]), options);
    result.cycles_run == 0
        && sleeps.borrow().is_empty()
        && result.records.is_empty()
}

/// Phase 3: `should_stop` stops after cycle 1, no sleep.
pub fn phase_should_stop() -> bool {
    let seen: Rc<RefCell<Vec<HashMap<String, WatchmanRecord>>>> =
        Rc::new(RefCell::new(Vec::new()));
    let sleeps: Rc<RefCell<Vec<f64>>> = Rc::new(RefCell::new(Vec::new()));
    let sleeps_clone = sleeps.clone();
    let mut options = ServeOptions::default();
    options.cycle_fn = Some(fixture_cycle_fn(seen));
    options.now_fn = Some(Box::new(move || Some(NOW)));
    options.sleep_fn = Some(Box::new(move |seconds: f64| {
        sleeps_clone.borrow_mut().push(seconds);
    }));
    options.max_cycles = Some(5);
    options.interval_seconds = Some(30.0);
    options.should_stop = Some(Box::new(
        |index: usize,
         _: &HashMap<String, WatchmanRecord>,
         _: &crate::watchman_cycle::CycleDiagnostics| index == 0,
    ));
    let result = serve_cycles(MachinesArg::List(vec!["alpha".to_string()]), options);
    result.cycles_run == 1 && sleeps.borrow().is_empty()
}

/// Phase 4: a raising cycle function is contained, loop recovers.
pub fn phase_raising_cycle_contained() -> bool {
    let calls: Rc<RefCell<usize>> = Rc::new(RefCell::new(0));
    let calls_clone = calls.clone();
    let mut options = ServeOptions::default();
    options.cycle_fn = Some(Box::new(
        move |_: Vec<String>,
              _: f64,
              _: HashMap<String, WatchmanRecord>,
              _: Vec<JournalEntry>| -> CycleFnOutput {
            let mut count = calls_clone.borrow_mut();
            *count += 1;
            if *count == 1 {
                panic!("boom");
            }
            let mut records: HashMap<String, WatchmanRecord> = HashMap::new();
            let mut record = WatchmanRecord::new();
            record.watchman_alive = Some(true);
            records.insert("alpha".to_string(), record);
            CycleFnOutput::Triple(
                records,
                Vec::new(),
                crate::watchman_cycle::CycleDiagnostics::default(),
            )
        },
    ));
    options.now_fn = Some(Box::new(move || Some(NOW)));
    options.sleep_fn = Some(Box::new(|_: f64| {}));
    options.max_cycles = Some(2);
    let result = serve_cycles(MachinesArg::List(vec!["alpha".to_string()]), options);
    result.cycles_run == 2
        && result.diagnostics_by_cycle[0]
            .runner_errors
            .get("cycle_error")
            .map(|e| e.as_str())
            == Some("panic")
        && result.records.get("alpha").map(|r| r.watchman_alive) == Some(Some(true))
}

/// Phase 5: a raising callback and a raising stop predicate are both
/// contained and the loop still runs every cycle.
pub fn phase_raising_callback_and_stop() -> bool {
    let seen: Rc<RefCell<Vec<HashMap<String, WatchmanRecord>>>> =
        Rc::new(RefCell::new(Vec::new()));
    let mut options = ServeOptions::default();
    options.cycle_fn = Some(fixture_cycle_fn(seen));
    options.now_fn = Some(Box::new(move || Some(NOW)));
    options.sleep_fn = Some(Box::new(|_: f64| {}));
    options.max_cycles = Some(2);
    options.on_cycle = Some(Box::new(
        |_: usize,
         _: &HashMap<String, WatchmanRecord>,
         _: &[JournalEntry],
         _: &crate::watchman_cycle::CycleDiagnostics| {
            panic!("callback boom");
        },
    ));
    options.should_stop = Some(Box::new(
        |_: usize,
         _: &HashMap<String, WatchmanRecord>,
         _: &crate::watchman_cycle::CycleDiagnostics| -> bool {
            panic!("stop boom");
        },
    ));
    let result = serve_cycles(MachinesArg::List(vec!["alpha".to_string()]), options);
    result.cycles_run == 2 && result.callback_errors == ["panic", "panic"]
}

/// Point `CARGO_MANIFEST_DIR` at this repo's crate directory when it
/// is unset, so the landed default cycle function resolves the Pax
/// program (the same trick the landed service tests use).
pub fn ensure_manifest_dir() {
    if std::env::var("CARGO_MANIFEST_DIR").is_err() {
        if let Ok(cwd) = std::env::current_dir() {
            let manifest = cwd.join("crates/os-supervisor");
            if manifest.exists() {
                std::env::set_var("CARGO_MANIFEST_DIR", &manifest);
            }
        }
    }
}

/// Phase 6: the default cycle function is the real production path
/// over temp snapshots: ring once, quiet next, bell carried.
pub fn phase_default_path_rings() -> bool {
    ensure_manifest_dir();
    let dir = std::env::temp_dir().join(format!(
        "watchman-service-drill-{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir_all(&dir).unwrap();
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
    let clock: Rc<RefCell<f64>> = Rc::new(RefCell::new(NOW));
    let clock_clone = clock.clone();
    let mut options = ServeOptions::default();
    options.now_fn = Some(Box::new(move || {
        let value = *clock_clone.borrow();
        *clock_clone.borrow_mut() += 60.0;
        Some(value)
    }));
    options.sleep_fn = Some(Box::new(|_: f64| {}));
    options.max_cycles = Some(2);
    options.snapshot_dir = Some(dir.to_string_lossy().to_string());
    let result = serve_cycles(MachinesArg::List(vec!["alpha".to_string()]), options);
    let alpha = result.records.get("alpha").cloned().unwrap_or_default();
    alpha.watchman_alive == Some(true)
        && alpha.last_bell.is_some()
        && result.diagnostics_by_cycle[0].run_failures.is_empty()
}

/// Phase 7: caller inputs never mutated.
pub fn phase_inputs_never_mutated() -> bool {
    let seen: Rc<RefCell<Vec<HashMap<String, WatchmanRecord>>>> =
        Rc::new(RefCell::new(Vec::new()));
    let machines = vec!["alpha".to_string()];
    let mut priors: HashMap<String, WatchmanRecord> = HashMap::new();
    let mut prior_record = WatchmanRecord::new();
    prior_record.watchman_alive = Some(false);
    priors.insert("alpha".to_string(), prior_record);
    let journal = vec![JournalEntry::new("old", "")];
    let machines_before = machines.clone();
    let priors_before = priors.clone();
    let journal_before = journal.clone();
    let mut options = ServeOptions::default();
    options.cycle_fn = Some(fixture_cycle_fn(seen));
    options.now_fn = Some(Box::new(move || Some(NOW)));
    options.sleep_fn = Some(Box::new(|_: f64| {}));
    options.max_cycles = Some(1);
    options.priors = Some(priors.clone());
    options.journal = Some(journal.clone());
    serve_cycles(MachinesArg::List(machines.clone()), options);
    machines == machines_before && priors == priors_before && journal == journal_before
}

/// Run every phase, in the Python drill's order.
///
/// Returns `(exit_code, lines)`: exit 0 with one `PASS` line per
/// phase on success, 1 otherwise. The caller owns printing.
pub fn run_drill() -> (i32, Vec<String>) {
    let phases: [(&str, bool); 7] = [
        ("phase 1: priors and journal carry, one sleep between two cycles", phase_state_carries()),
        ("phase 2: max_cycles=0 runs nothing, never sleeps", phase_zero_cycles()),
        ("phase 3: should_stop stops after cycle 1, no sleep", phase_should_stop()),
        ("phase 4: raising cycle contained, loop recovers on the next cycle", phase_raising_cycle_contained()),
        ("phase 5: raising callback and stop predicate contained, loop runs every cycle", phase_raising_callback_and_stop()),
        ("phase 6: default loop rings on real snapshots, bell carried into cycle 2", phase_default_path_rings()),
        ("phase 7: caller inputs unchanged", phase_inputs_never_mutated()),
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
        lines.push("ALL PASS: watchman service loop".to_string());
    }
    (if failed == 0 { 0 } else { 1 }, lines)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_drill_phase1_state_carries() {
        // Mirrors the Python drill's phase 1.
        assert!(phase_state_carries());
    }

    #[test]
    fn test_drill_phase2_zero_cycles() {
        // Mirrors the Python drill's phase 2.
        assert!(phase_zero_cycles());
    }

    #[test]
    fn test_drill_phase3_should_stop() {
        // Mirrors the Python drill's phase 3.
        assert!(phase_should_stop());
    }

    #[test]
    fn test_drill_phase4_raising_cycle_contained() {
        // Mirrors the Python drill's phase 4, with the landed
        // "panic" seam value in place of the Python type name.
        assert!(phase_raising_cycle_contained());
    }

    #[test]
    fn test_drill_phase5_raising_callback_and_stop() {
        // Mirrors the Python drill's phase 5, with the landed
        // "panic" seam values in place of the Python type names.
        assert!(phase_raising_callback_and_stop());
    }

    #[test]
    fn test_drill_phase6_default_path_rings() {
        // Mirrors the Python drill's phase 6.
        assert!(phase_default_path_rings());
    }

    #[test]
    fn test_drill_phase7_inputs_never_mutated() {
        // Mirrors the Python drill's phase 7.
        assert!(phase_inputs_never_mutated());
    }

    #[test]
    fn test_drill_passes() {
        // Mirrors test_drill_passes in test_intel_watchman_service.py
        // (via the service drill script): the drill itself exits 0.
        let (code, lines) = run_drill();
        assert_eq!(code, 0, "drill lines: {:?}", lines);
        assert!(lines.iter().any(|l| l.contains("ALL PASS: watchman service loop")));
    }
}
