//! Watchman bridge drill (Milo lane, OS-122 follow-up to Pax OS-118).
//!
//! Port of `os/intel/drills/watchman_bridge.py` (batch B21, task T121).
//! Port behavior, do not redesign.
//!
//! OS-118 landed the real watchman program with a pure tick; this
//! drill closes the bridge between that tick and the watchdog's
//! who-watches-the-watchman detector, on fixtures, in four checks:
//!
//! 1. Real tick: one open job addressed to a sleeping agent yields
//!    exactly one wake event.
//! 2. Bridge: folding that tick yields a record with `watchman_alive`
//!    true and `last_bell` equal to the tick time; the watchman_watch
//!    board reads ALIVE and its tick journals nothing new.
//! 3. Silence: the same record aged past the stale window
//!    (`restart_ok` true, the revivable case) yields exactly one
//!    crew-dark record plus one restart-succeeded record and no
//!    escalation; a fresh fold after the dark episode yields a
//!    watchman-recovered record.
//! 4. No-bell honesty: a tick with no wake event yields a record
//!    whose `last_bell` stays None, and the board reads UNKNOWN, not
//!    ALIVE. The rung state file is never read as liveness proof.
//!
//! What this drill does NOT claim, stated plainly (as in Python): the
//! bridge proves the record shape and the detector path, not a live
//! watchman. No booted test image, no relay-watchman.service actually
//! running, no systemd restart of a dead watchman, and no live queue
//! reader. No bus post, no live Redis, no network.
//!
//! # Representation notes (where the typed port differs from Python)
//!
//! - Phase 1 in Python runs the real Pax tick
//!   (`os/watchman/relay_watchman.py`) and asserts the event's kind,
//!   job id, and timestamp. That tick lives in another batch's module
//!   (`relay_watchman`, not one of this drill's landed inputs), so
//!   this port asserts the wake-event shape the bridge consumes (kind
//!   `wake`, timestamp `NOW`) with a literal event; the tick's own
//!   job-addressing and sleeping-agent judgement is the relay
//!   module's, not the bridge's, and is not re-proven here. The
//!   landed bridge tests cover the same fold with literal wakes.
//! - The stale window comes from the landed thresholds module
//!   ([`crate::thresholds::WATCHMAN_STALE_MINUTES_DEFAULT`]), the
//!   same value the Python drill reads from `intel.thresholds`.
//!
//! # Live-behavior boundary (not faked here)
//!
//! The Python script's `main` prints `PASS`/`FAIL` lines and exits 0
//! or 1. That reporting shape is ported as [`run_drill`], which
//! returns the exit code and the lines instead of printing them; the
//! caller owns printing and exiting. No watchman process runs here.

use std::collections::HashMap;

use crate::thresholds::WATCHMAN_STALE_MINUTES_DEFAULT;
use crate::watchman_bridge::{fold_tick, machines_snapshot, WatchEvent};
use crate::watchman_watch::{
    current_states, watchman_watch_tick, WatchmanRecord, WatchmanSnapshot,
};

/// Fake-clock base time (Python `NOW`), unix seconds.
pub const NOW: f64 = 1000000.0;
/// Stale window in seconds (Python `STALE`).
pub const STALE: f64 = WATCHMAN_STALE_MINUTES_DEFAULT as f64 * 60.0;

/// A literal wake event at `at`, the shape the real Pax tick emits
/// for one open job addressed to a sleeping agent.
pub fn wake_event(at: f64) -> WatchEvent {
    WatchEvent::new("wake", Some(at))
}

/// One machine's record as a snapshot the watch module consumes.
pub fn snapshot_of(name: &str, record: WatchmanRecord) -> WatchmanSnapshot {
    let mut records: HashMap<String, Option<WatchmanRecord>> = HashMap::new();
    records.insert(name.to_string(), Some(record));
    machines_snapshot(&records)
}

/// Phase 1: the wake-event shape the real tick yields for a sleeping
/// agent's job: one event, kind `wake`, timestamp `NOW`.
///
/// The tick's job-addressing half (job id, agent, sleeping check) is
/// the relay module's behavior and is not re-proven here; see the
/// module docs.
pub fn phase_real_tick_wake() -> bool {
    let event = wake_event(NOW);
    event.kind.as_deref() == Some("wake") && event.ts == Some(NOW)
}

/// Phase 2: the bridge record reads ALIVE, journals nothing.
pub fn phase_bridge_alive() -> bool {
    let record = fold_tick(&[wake_event(NOW)], NOW, None);
    if record.watchman_alive != Some(true) || record.last_bell != Some(NOW) {
        return false;
    }
    let snapshot = snapshot_of("m1", record);
    let states = current_states(&snapshot, NOW);
    let journal = watchman_watch_tick(&snapshot, &[], NOW);
    states.len() == 1 && states[0].state == "alive" && journal.is_empty()
}

/// Phase 3: aged past the stale window, revivable restart, then a
/// fresh ring recovers the machine.
pub fn phase_aged_dark_and_recover() -> bool {
    let record = fold_tick(&[wake_event(NOW)], NOW, None);
    let mut aged = record.clone();
    aged.restart_ok = Some(true);
    let late = NOW + STALE + 60.0;
    let dark = watchman_watch_tick(&snapshot_of("m1", aged), &[], late);
    let kinds: Vec<&str> = dark.iter().map(|e| e.kind.as_str()).collect();
    if kinds != ["crew-dark", "watchman-restart"] || dark[1].restart_ok != Some(true) {
        return false;
    }
    let fresh = fold_tick(&[wake_event(late + 60.0)], late + 60.0, Some(&record));
    let recovered =
        watchman_watch_tick(&snapshot_of("m1", fresh), &dark, late + 60.0);
    recovered.len() == 1 && recovered[0].kind == "watchman-recovered"
}

/// Phase 4: a tick with no wake event never invents a bell; the board
/// reads UNKNOWN, not ALIVE.
pub fn phase_no_bell_unknown() -> bool {
    let quiet = fold_tick(&[], NOW, None);
    if quiet.last_bell.is_some() {
        return false;
    }
    let states = current_states(&snapshot_of("m1", quiet), NOW);
    states.len() == 1 && states[0].state == "unknown"
}

/// Run every phase, in the Python drill's order.
///
/// Returns `(exit_code, lines)`: exit 0 with one `PASS` line per
/// phase on success, 1 otherwise. The caller owns printing.
pub fn run_drill() -> (i32, Vec<String>) {
    let phases: [(&str, fn() -> bool); 4] = [
        ("phase1-real-tick-wake", phase_real_tick_wake),
        ("phase2-bridge-alive", phase_bridge_alive),
        ("phase3-aged-crew-dark-and-recover", phase_aged_dark_and_recover),
        ("phase4-no-bell-unknown", phase_no_bell_unknown),
    ];
    let mut lines = Vec::new();
    let mut failed = 0;
    for (name, phase) in phases {
        if phase() {
            lines.push(format!("PASS {}", name));
        } else {
            lines.push(format!("FAIL {}", name));
            failed += 1;
        }
    }
    lines.push(format!(
        "watchman_bridge drill: {}",
        if failed == 0 { "PASS" } else { "FAIL" }
    ));
    (if failed == 0 { 0 } else { 1 }, lines)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_drill_phase1_real_tick_wake() {
        // Mirrors the Python drill's phase 1, with the relay-tick half
        // noted in the module docs (literal wake-event shape).
        assert!(phase_real_tick_wake());
    }

    #[test]
    fn test_drill_phase2_bridge_alive() {
        // Mirrors the Python drill's phase 2.
        assert!(phase_bridge_alive());
    }

    #[test]
    fn test_drill_phase3_aged_crew_dark_and_recover() {
        // Mirrors the Python drill's phase 3.
        assert!(phase_aged_dark_and_recover());
    }

    #[test]
    fn test_drill_phase4_no_bell_unknown() {
        // Mirrors the Python drill's phase 4.
        assert!(phase_no_bell_unknown());
    }

    #[test]
    fn test_drill_passes() {
        // Mirrors test_drill_passes in test_intel_watchman_bridge.py
        // (via the bridge drill script): the drill itself exits 0.
        let (code, lines) = run_drill();
        assert_eq!(code, 0, "drill lines: {:?}", lines);
        assert!(lines.last().map(|l| l.contains("PASS")).unwrap_or(false));
    }
}
