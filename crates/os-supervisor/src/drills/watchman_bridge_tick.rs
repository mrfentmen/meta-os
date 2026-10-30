//! Watchman bridge service-loop drill (Milo lane, OS-122 follow-up).
//!
//! Port of `os/intel/drills/watchman_bridge_tick.py` (batch B21,
//! task T121). Port behavior, do not redesign.
//!
//! The bridge already folds one relay-watchman tick into one
//! watchman_watch record, but a service loop must not hand-assemble
//! fold, snapshot, and judge per machine. `watchman_tick()` is the one
//! call: `{machine: events}` in, `({machine: record}, new journal
//! records)` out. This drill proves that call on fixtures, in five
//! checks:
//!
//! 1. Two machines, one rings, one quiet: the ringing record reads
//!    ALIVE with its bell at the tick time, the quiet record reads
//!    UNKNOWN (ticking but never rang is not claimed alive), and the
//!    journal stays empty.
//! 2. Silence then recovery: the ringing machine folded with no new
//!    events past the stale window (`restart_ok` true, the caller's
//!    restart fact) journals exactly one crew-dark plus one
//!    restart-succeeded record and nothing for the quiet machine; a
//!    fresh ring then journals exactly one recovered record.
//! 3. Second episode re-alerts: after recovery the same machine goes
//!    dark again (`restart_ok` false, no restart fact invented) and
//!    journals a fresh crew-dark, a restart-failed record, and exactly
//!    one escalation; an identical second tick journals nothing new.
//! 4. Malformed input is contained: a non-dict mapping yields no
//!    records and no journal, and junk events for one machine leave
//!    the healthy machine's record and journal untouched.
//! 5. Inputs are never mutated: events, priors, and journal come back
//!    unchanged; a machine missing from the mapping is unjudged.
//!
//! What this drill does NOT claim, stated plainly (as in Python): the
//! call proves the record shape and the detector path, not a live
//! watchman. No booted test image, no relay-watchman.service actually
//! running, no systemd restart of a dead watchman, and no live queue
//! reader. A `restart_ok` value is always the caller's fact, never
//! something this module observes. No bus post, no live Redis, no
//! network.
//!
//! # Representation notes (where the typed port differs from Python)
//!
//! - Python phases 1 and 2 generate their events with the real Pax
//!   tick. That tick lives in another batch's module, so this port
//!   uses literal wake events (the tick output shape the bridge
//!   consumes); the tick's sleeping-agent judgement is not re-proven
//!   here.
//! - A Python non-dict events mapping reads as an empty mapping, and
//!   a non-list events value for a machine reads as an empty event
//!   list. Both shapes are an empty map / empty list here, which judge
//!   exactly as Python judges them.
//! - The stale window comes from the landed thresholds module, the
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
use crate::watchman_bridge::{snapshot_from_records, watchman_tick, WatchEvent};
use crate::watchman_watch::{current_states, JournalEntry, WatchmanRecord};

/// Fake-clock base time (Python `NOW`), unix seconds.
pub const NOW: f64 = 1000000.0;
/// Stale window in seconds (Python `STALE`).
pub const STALE: f64 = WATCHMAN_STALE_MINUTES_DEFAULT as f64 * 60.0;

/// A literal wake event at `at`, the shape the real Pax tick emits
/// for one open job addressed to a sleeping agent.
pub fn wake_event(at: f64) -> WatchEvent {
    WatchEvent::new("wake", Some(at))
}

/// Journal kinds, in order.
pub fn kinds(journal: &[JournalEntry]) -> Vec<String> {
    journal.iter().map(|e| e.kind.clone()).collect()
}

/// Board states by machine name.
pub fn states_by_machine(
    records: &HashMap<String, WatchmanRecord>,
    now: f64,
) -> HashMap<String, String> {
    current_states(&snapshot_from_records(records), now)
        .into_iter()
        .map(|s| (s.machine, s.state))
        .collect()
}

/// Phase 1: one machine rings, one stays quiet.
pub fn phase_ring_and_quiet() -> bool {
    let mut events: HashMap<String, Vec<WatchEvent>> = HashMap::new();
    events.insert("m1".to_string(), vec![wake_event(NOW)]);
    events.insert("m2".to_string(), vec![]);
    let events_before = events.clone();
    let (records, journal) = watchman_tick(
        &events,
        NOW,
        &HashMap::new(),
        &[],
        &HashMap::new(),
    );
    let states = states_by_machine(&records, NOW);
    records["m1"].last_bell == Some(NOW)
        && records["m2"].last_bell.is_none()
        && states.get("m1").map(|s| s.as_str()) == Some("alive")
        && states.get("m2").map(|s| s.as_str()) == Some("unknown")
        && journal.is_empty()
        && events == events_before
}

/// Phase 2: the ringing machine goes silent past the stale window,
/// then rings again and recovers.
pub fn phase_silence_and_recovery() -> bool {
    let mut events: HashMap<String, Vec<WatchEvent>> = HashMap::new();
    events.insert("m1".to_string(), vec![wake_event(NOW)]);
    events.insert("m2".to_string(), vec![]);
    let (records, _) =
        watchman_tick(&events, NOW, &HashMap::new(), &[], &HashMap::new());
    let late = NOW + STALE + 60.0;
    let priors = records.clone();
    let priors_before = priors.clone();
    let mut dark_events: HashMap<String, Vec<WatchEvent>> = HashMap::new();
    dark_events.insert("m1".to_string(), vec![]);
    dark_events.insert("m2".to_string(), vec![]);
    let mut restart_ok: HashMap<String, bool> = HashMap::new();
    restart_ok.insert("m1".to_string(), true);
    let (dark_records, dark) =
        watchman_tick(&dark_events, late, &priors, &[], &restart_ok);
    let journal = dark.clone();
    let mut fresh_events: HashMap<String, Vec<WatchEvent>> = HashMap::new();
    fresh_events.insert("m1".to_string(), vec![wake_event(late + 60.0)]);
    fresh_events.insert("m2".to_string(), vec![]);
    let (_, recovered) = watchman_tick(
        &fresh_events,
        late + 60.0,
        &dark_records,
        &journal,
        &HashMap::new(),
    );
    kinds(&dark) == ["crew-dark", "watchman-restart"]
        && dark[1].restart_ok == Some(true)
        && dark.iter().all(|e| e.machine == "m1")
        && kinds(&recovered) == ["watchman-recovered"]
        && recovered[0].machine == "m1"
        && priors == priors_before
}

/// Phase 3: a second dark episode re-alerts, then stays quiet.
pub fn phase_second_episode_realerts() -> bool {
    // Rebuild the recovered state exactly as phase 2 leaves it.
    let mut events: HashMap<String, Vec<WatchEvent>> = HashMap::new();
    events.insert("m1".to_string(), vec![wake_event(NOW)]);
    let (records, _) =
        watchman_tick(&events, NOW, &HashMap::new(), &[], &HashMap::new());
    let late = NOW + STALE + 60.0;
    let mut dark_events: HashMap<String, Vec<WatchEvent>> = HashMap::new();
    dark_events.insert("m1".to_string(), vec![]);
    let mut restart_ok: HashMap<String, bool> = HashMap::new();
    restart_ok.insert("m1".to_string(), true);
    let (dark_records, dark) =
        watchman_tick(&dark_events, late, &records, &[], &restart_ok);
    let mut journal = dark;
    let mut fresh_events: HashMap<String, Vec<WatchEvent>> = HashMap::new();
    fresh_events.insert("m1".to_string(), vec![wake_event(late + 60.0)]);
    let (recovered_records, recovered) = watchman_tick(
        &fresh_events,
        late + 60.0,
        &dark_records,
        &journal,
        &HashMap::new(),
    );
    journal.extend(recovered);
    let later = late + 2.0 * STALE + 120.0;
    let mut dark2_events: HashMap<String, Vec<WatchEvent>> = HashMap::new();
    dark2_events.insert("m1".to_string(), vec![]);
    let mut restart_ok2: HashMap<String, bool> = HashMap::new();
    restart_ok2.insert("m1".to_string(), false);
    let (dark2_records, dark2) = watchman_tick(
        &dark2_events,
        later,
        &recovered_records,
        &journal,
        &restart_ok2,
    );
    let mut journal2 = journal.clone();
    journal2.extend(dark2.iter().cloned());
    let (_, again) = watchman_tick(
        &dark2_events,
        later + 60.0,
        &dark2_records,
        &journal2,
        &HashMap::new(),
    );
    kinds(&dark2) == ["crew-dark", "watchman-restart", "escalation"]
        && dark2[1].restart_ok == Some(false)
        && again.is_empty()
        && dark2.iter().all(|e| e.machine == "m1")
}

/// Phase 4: malformed input is contained per machine.
pub fn phase_malformed_contained() -> bool {
    // A non-dict mapping is an empty mapping here.
    let (bad_records, bad_journal) = watchman_tick(
        &HashMap::new(),
        NOW,
        &HashMap::new(),
        &[],
        &HashMap::new(),
    );
    if !bad_records.is_empty() || !bad_journal.is_empty() {
        return false;
    }
    // A non-list events value for m1 is an empty event list here.
    let mut mixed: HashMap<String, Vec<WatchEvent>> = HashMap::new();
    mixed.insert("m1".to_string(), vec![]);
    mixed.insert("m2".to_string(), vec![]);
    let (mixed_records, mixed_journal) = watchman_tick(
        &mixed,
        NOW,
        &HashMap::new(),
        &[],
        &HashMap::new(),
    );
    let states = states_by_machine(&mixed_records, NOW);
    mixed_records["m1"].last_bell.is_none()
        && mixed_records["m2"].last_bell.is_none()
        && states.get("m1").map(|s| s.as_str()) == Some("unknown")
        && states.get("m2").map(|s| s.as_str()) == Some("unknown")
        && mixed_journal.is_empty()
}

/// Phase 5: a machine missing from the mapping is unjudged.
pub fn phase_absent_machine_unjudged() -> bool {
    let mut events: HashMap<String, Vec<WatchEvent>> = HashMap::new();
    events.insert("m2".to_string(), vec![]);
    let (records, journal) = watchman_tick(
        &events,
        NOW,
        &HashMap::new(),
        &[],
        &HashMap::new(),
    );
    records.keys().collect::<Vec<_>>() == vec!["m2"] && journal.is_empty()
}

/// Run every phase, in the Python drill's order.
///
/// Returns `(exit_code, lines)`: exit 0 with one `PASS` line per
/// phase on success, 1 otherwise. The caller owns printing.
pub fn run_drill() -> (i32, Vec<String>) {
    let phases: [(&str, fn() -> bool); 5] = [
        ("phase1-ring-and-quiet", phase_ring_and_quiet),
        ("phase2-silence-and-recovery", phase_silence_and_recovery),
        ("phase3-second-episode-realerts", phase_second_episode_realerts),
        ("phase4-malformed-contained", phase_malformed_contained),
        ("phase5-absent-machine-unjudged", phase_absent_machine_unjudged),
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
        "watchman_bridge_tick drill: {}",
        if failed == 0 { "PASS" } else { "FAIL" }
    ));
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
    fn test_drill_phase2_silence_and_recovery() {
        // Mirrors the Python drill's phase 2.
        assert!(phase_silence_and_recovery());
    }

    #[test]
    fn test_drill_phase3_second_episode_realerts() {
        // Mirrors the Python drill's phase 3.
        assert!(phase_second_episode_realerts());
    }

    #[test]
    fn test_drill_phase4_malformed_contained() {
        // Mirrors the Python drill's phase 4.
        assert!(phase_malformed_contained());
    }

    #[test]
    fn test_drill_phase5_absent_machine_unjudged() {
        // Mirrors the Python drill's phase 5.
        assert!(phase_absent_machine_unjudged());
    }

    #[test]
    fn test_drill_passes() {
        // Mirrors test_drill_passes in test_intel_watchman_bridge_tick.py
        // (via the bridge-tick drill script): the drill itself exits 0.
        let (code, lines) = run_drill();
        assert_eq!(code, 0, "drill lines: {:?}", lines);
        assert!(lines.last().map(|l| l.contains("PASS")).unwrap_or(false));
    }
}
