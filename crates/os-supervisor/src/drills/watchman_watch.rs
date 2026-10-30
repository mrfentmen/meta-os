//! Watchman-watch drill (Milo lane, OS-122).
//!
//! Port of `os/intel/drills/watchman_watch.py` (batch B21, task
//! T124). Port behavior, do not redesign.
//!
//! Acceptance: kill the watchman on the fixture machine and the
//! watchdog flags crew-dark within one detector cycle, the restart
//! revives it, and no Dale push fires; kill it beyond the restart's
//! power and exactly one blocked-push fires naming the machine; the
//! board's group for that machine reads watchman-dead while it lasts.
//!
//! What fixtures can prove, and what they cannot, stated plainly (as
//! in Python): [`crate::watchman_watch`] judges fixture watchman
//! records; it never touches a process, rings a bell, or sends a push.
//! The drill's simulated owner applies each restart, so the restart
//! half is simulated, not a systemd restart on a live machine. The
//! resident watchman program that actually rings is Pax OS-118, and a
//! live kill on a booted test image is not claimed here, because no
//! test image runs in this repo.
//!
//! Phases, all on fixtures with a fake clock (base time [`T0`]):
//!
//! - kill-and-revive: watchman on machine milo-box is killed (alive
//!   flag false). One tick yields a crew-dark record and a restart
//!   record, and no escalation and no push payload anywhere. The
//!   simulated owner applies the restart (alive flag true, fresh
//!   bell). The next tick yields a recovered record, and still no
//!   escalation. The board reads watchman-dead while dark and
//!   watchman alive after.
//! - kill-beyond-repair: watchman on machine rowan-box is killed with
//!   `restart_ok` false. One tick yields crew-dark, a failed restart
//!   record, and exactly one escalation whose push payload validates
//!   and names the machine. Two further unchanged ticks yield zero new
//!   records: no loop, no duplicate push. The drill's sent ledger
//!   stays empty throughout, because nothing here sends.
//! - revive-then-die-again: after a recovery, the same machine dies
//!   again with `restart_ok` false. The new episode yields a fresh
//!   crew-dark record and a fresh escalation: dedupe is per episode,
//!   so a second death is never silenced by the first one's records.
//! - alive-and-unknown: a live machine and an unknown machine (no
//!   flag, no bell) yield no records at all, and the board lines say
//!   alive and unknown, never dead. Malformed machine entries (a
//!   non-record, a missing machines mapping) yield no records and no
//!   crash.
//! - stale-bell: a watchman whose flag says alive but whose bell is
//!   older than the stale window reads dead and earns a crew-dark
//!   record; a fresh bell reads alive. The stale window is overridable
//!   per call, and the default equals the thresholds value.
//! - no-dale-and-immutable: journal records carry no announcement
//!   field, the tick leaves the snapshot and the journal unchanged,
//!   and the sent ledger stays empty.
//!
//! What this drill does NOT claim: a live watchman actually killed and
//! restarted, a real systemd restart on a booted test image, the
//! watchman's mechanical ringing (Pax OS-118), or a phone actually
//! ringing (the Web Push worker wiring is Hana OS-097). The escalation
//! here is a built payload, never a sent push.
//!
//! # Representation notes (where the typed port differs from Python)
//!
//! - Python phase kill-beyond-repair validates the escalation push
//!   with `intel/push.py`'s validator. That module is outside this
//!   batch, so this port validates through the landed watch module's
//!   push seam ([`DefaultPushBuilder`]), which reproduces the
//!   `intel/push.py` blocked-push builder and validator for exactly
//!   the parked record the judge builds.
//! - A Python malformed machine entry (a non-dict record) is a `None`
//!   entry in [`WatchmanSnapshot`]; a missing or malformed machines
//!   mapping is an empty snapshot. Both judge unknown and yield no
//!   records, exactly as Python judges them.
//! - The Python no-Dale phase scans the watch module's source for
//!   socket, urllib, requests, bus, and redis imports. The landed
//!   module's tests already record that such a scan has no Rust
//!   equivalent for a std-only module with no network dependency; this
//!   drill asserts the behavioral half instead: no record carries an
//!   announcement field (the entry type has none by construction, and
//!   its debug form contains no `announce` text), no record is sent
//!   (the sent ledger stays empty), and the tick leaves its inputs
//!   unchanged.
//! - The stale window default comes from the landed thresholds module
//!   ([`crate::thresholds::WATCHMAN_STALE_MINUTES_DEFAULT`]), the same
//!   value the Python drill reads from `intel.thresholds`.
//!
//! # Live-behavior boundary (not faked here)
//!
//! The Python script's `main` prints `PASS`/`FAIL` lines and exits 0
//! or 1. That reporting shape is ported as [`run_drill`], which
//! returns the exit code and the lines instead of printing them; the
//! caller owns printing and exiting. The sent ledger in this module is
//! a plain empty vector: it models the Python drill's `SENT` list,
//! which nothing ever appends to, because nothing here sends.

use crate::thresholds::WATCHMAN_STALE_MINUTES_DEFAULT;
use crate::watchman_watch::{
    board_lines, current_states, machine_state, watchman_brief_lines,
    watchman_watch_tick, BlockedPushBuilder, DefaultPushBuilder,
    JournalEntry, WatchmanRecord, WatchmanSnapshot, ALIVE, DEAD,
};

/// Fake-clock base time (Python `T0`), unix seconds.
pub const T0: f64 = 100000.0;

/// A dead-machine record with the given restart outcome, as the
/// Python drill's `dead_machine` helper builds it.
pub fn dead_machine(restart_ok: bool) -> WatchmanRecord {
    WatchmanRecord {
        watchman_alive: Some(false),
        last_bell: Some(T0 - 600.0),
        last_wake: Some(T0 - 600.0),
        restart_ok: Some(restart_ok),
        ..Default::default()
    }
}

/// A one-machine snapshot.
pub fn snapshot_with(machine: &str, record: Option<WatchmanRecord>) -> WatchmanSnapshot {
    let mut snapshot = WatchmanSnapshot::new();
    snapshot.machines.insert(machine.to_string(), record);
    snapshot
}

/// Journal kinds, in order.
pub fn kinds(journal: &[JournalEntry]) -> Vec<String> {
    journal.iter().map(|e| e.kind.clone()).collect()
}

/// Phase kill-and-revive: one tick flags crew-dark plus restart, the
/// simulated owner revives the machine, the next tick recovers it,
/// and no push fires anywhere.
pub fn phase_kill_and_revive() -> bool {
    let snap = snapshot_with("milo-box", Some(dead_machine(true)));
    let journal: Vec<JournalEntry> = Vec::new();
    let new = watchman_watch_tick(&snap, &journal, T0);
    if kinds(&new) != ["crew-dark", "watchman-restart"] {
        return false;
    }
    if new.iter().any(|r| r.push.is_some()) {
        return false;
    }
    if board_lines(&current_states(&snap, T0))
        != ["Machine milo-box: watchman dead (crew-dark)."]
    {
        return false;
    }
    let journal: Vec<JournalEntry> =
        journal.iter().cloned().chain(new.iter().cloned()).collect();
    let revived = WatchmanRecord {
        watchman_alive: Some(true),
        last_bell: Some(T0),
        last_wake: Some(T0),
        restart_ok: Some(true),
        ..Default::default()
    };
    let snap = snapshot_with("milo-box", Some(revived));
    let new = watchman_watch_tick(&snap, &journal, T0 + 60.0);
    if kinds(&new) != ["watchman-recovered"] {
        return false;
    }
    if new.iter().any(|r| r.push.is_some()) {
        return false;
    }
    if board_lines(&current_states(&snap, T0 + 60.0))
        != ["Machine milo-box: watchman alive."]
    {
        return false;
    }
    let mut full = journal.clone();
    full.extend(new.iter().cloned());
    let lines = watchman_brief_lines(&full);
    lines
        .iter()
        .any(|line| line.contains("Crew-dark on machine milo-box"))
}

/// Phase kill-beyond-repair: one tick yields crew-dark, failed
/// restart, and exactly one valid escalation naming the machine;
/// re-ticks stay silent; the sent ledger stays empty.
pub fn phase_kill_beyond_repair() -> bool {
    let snap = snapshot_with("rowan-box", Some(dead_machine(false)));
    let journal: Vec<JournalEntry> = Vec::new();
    let new = watchman_watch_tick(&snap, &journal, T0);
    if kinds(&new) != ["crew-dark", "watchman-restart", "escalation"] {
        return false;
    }
    let escalation = &new[2];
    let builder = DefaultPushBuilder;
    let push = match &escalation.push {
        Some(push) => push,
        None => return false,
    };
    if !builder.validate_push(push) {
        return false;
    }
    if !escalation
        .question
        .as_deref()
        .unwrap_or("")
        .contains("rowan-box")
    {
        return false;
    }
    // The sent ledger: nothing here sends, so it stays empty.
    let sent: Vec<JournalEntry> = Vec::new();
    if !sent.is_empty() {
        return false;
    }
    let mut journal: Vec<JournalEntry> =
        journal.iter().cloned().chain(new.iter().cloned()).collect();
    for tick in [T0 + 60.0, T0 + 120.0] {
        let new = watchman_watch_tick(&snap, &journal, tick);
        if !new.is_empty() {
            return false;
        }
        journal.extend(new);
    }
    journal.iter().filter(|r| r.kind == "escalation").count() == 1
}

/// Phase revive-then-die-again: a second death after a recovery
/// re-alerts with a fresh crew-dark and a fresh escalation.
pub fn phase_revive_then_die_again() -> bool {
    let snap = snapshot_with("milo-box", Some(dead_machine(true)));
    let mut journal = watchman_watch_tick(&snap, &[], T0);
    let revived = WatchmanRecord {
        watchman_alive: Some(true),
        last_bell: Some(T0),
        last_wake: Some(T0),
        restart_ok: Some(false),
        ..Default::default()
    };
    let snap = snapshot_with("milo-box", Some(revived));
    journal.extend(watchman_watch_tick(&snap, &journal, T0 + 60.0));
    let dead_again = WatchmanRecord {
        watchman_alive: Some(false),
        last_bell: Some(T0 + 60.0),
        last_wake: Some(T0 + 60.0),
        restart_ok: Some(false),
        ..Default::default()
    };
    let snap = snapshot_with("milo-box", Some(dead_again));
    let new = watchman_watch_tick(&snap, &journal, T0 + 120.0);
    if kinds(&new) != ["crew-dark", "watchman-restart", "escalation"] {
        return false;
    }
    let mut full = journal.clone();
    full.extend(new.iter().cloned());
    full.iter().filter(|r| r.kind == "crew-dark").count() == 2
}

/// Phase alive-and-unknown: live and unknown machines yield nothing;
/// the board lines say alive and unknown, never dead; malformed
/// entries yield nothing and never crash.
pub fn phase_alive_and_unknown() -> bool {
    let mut snapshot = WatchmanSnapshot::new();
    snapshot.machines.insert(
        "live-box".to_string(),
        Some(WatchmanRecord {
            watchman_alive: Some(true),
            last_bell: Some(T0),
            last_wake: Some(T0),
            restart_ok: Some(true),
            ..Default::default()
        }),
    );
    snapshot.machines.insert(
        "quiet-box".to_string(),
        Some(WatchmanRecord {
            last_bell: None,
            last_wake: None,
            ..Default::default()
        }),
    );
    // A non-record machine entry is a None entry here.
    snapshot.machines.insert("broken-box".to_string(), None);
    let new = watchman_watch_tick(&snapshot, &[], T0);
    if !new.is_empty() {
        return false;
    }
    if board_lines(&current_states(&snapshot, T0))
        != [
            "Machine broken-box: watchman state unknown.",
            "Machine live-box: watchman alive.",
            "Machine quiet-box: watchman state unknown.",
        ]
    {
        return false;
    }
    // A missing machines mapping is an empty snapshot here, and a
    // malformed mapping reads the same way: no records, no crash.
    watchman_watch_tick(&WatchmanSnapshot::new(), &[], T0).is_empty()
}

/// Phase stale-bell: a bell 301 seconds old reads dead at a 5-minute
/// window, a bell 60 seconds old reads alive, and the default window
/// equals the thresholds value.
pub fn phase_stale_bell() -> bool {
    let stale = WatchmanRecord {
        watchman_alive: Some(true),
        last_bell: Some(T0 - 301.0),
        last_wake: Some(T0 - 301.0),
        restart_ok: Some(false),
        ..Default::default()
    };
    if machine_state(Some(&stale), T0, Some(5.0)) != DEAD {
        return false;
    }
    let fresh = WatchmanRecord {
        watchman_alive: Some(true),
        last_bell: Some(T0 - 60.0),
        last_wake: Some(T0 - 60.0),
        restart_ok: Some(true),
        ..Default::default()
    };
    if machine_state(Some(&fresh), T0, Some(5.0)) != ALIVE {
        return false;
    }
    if machine_state(Some(&fresh), T0, None) != ALIVE {
        return false;
    }
    if WATCHMAN_STALE_MINUTES_DEFAULT != 5 {
        return false;
    }
    let snap = snapshot_with("stale-box", Some(stale));
    kinds(&watchman_watch_tick(&snap, &[], T0))
        == ["crew-dark", "watchman-restart", "escalation"]
}

/// Phase no-dale-and-immutable: the tick leaves its inputs unchanged,
/// no record carries an announcement field, and the sent ledger stays
/// empty.
pub fn phase_no_dale_and_immutable() -> bool {
    let snap = snapshot_with("rowan-box", Some(dead_machine(false)));
    let journal: Vec<JournalEntry> = Vec::new();
    let snap_before = snap.clone();
    let journal_before = journal.clone();
    let new = watchman_watch_tick(&snap, &journal, T0);
    if snap != snap_before || journal != journal_before {
        return false;
    }
    // The entry type has no announcement field by construction; its
    // debug form therefore carries no `announce` text.
    if format!("{:?}", new).contains("announce") {
        return false;
    }
    let sent: Vec<JournalEntry> = Vec::new();
    sent.is_empty()
}

/// Run every phase, in the Python drill's order.
///
/// Returns `(exit_code, lines)`: exit 0 with one `PASS` line per
/// phase on success, 1 otherwise. The caller owns printing.
pub fn run_drill() -> (i32, Vec<String>) {
    let phases: [(&str, bool); 6] = [
        ("kill-and-revive", phase_kill_and_revive()),
        ("kill-beyond-repair", phase_kill_beyond_repair()),
        ("revive-then-die-again", phase_revive_then_die_again()),
        ("alive-and-unknown", phase_alive_and_unknown()),
        ("stale-bell", phase_stale_bell()),
        ("no-dale-and-immutable", phase_no_dale_and_immutable()),
    ];
    let mut lines = Vec::new();
    let mut passed = 0;
    for (name, ok) in phases {
        if ok {
            lines.push(format!("{}: PASS", name));
            passed += 1;
        } else {
            lines.push(format!("{}: FAIL", name));
        }
    }
    lines.push(format!("{}/{} phases PASS", passed, 6));
    (if passed == 6 { 0 } else { 1 }, lines)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_drill_phase_kill_and_revive() {
        // Mirrors the Python drill's kill-and-revive phase.
        assert!(phase_kill_and_revive());
    }

    #[test]
    fn test_drill_phase_kill_beyond_repair() {
        // Mirrors the Python drill's kill-beyond-repair phase.
        assert!(phase_kill_beyond_repair());
    }

    #[test]
    fn test_drill_phase_revive_then_die_again() {
        // Mirrors the Python drill's revive-then-die-again phase.
        assert!(phase_revive_then_die_again());
    }

    #[test]
    fn test_drill_phase_alive_and_unknown() {
        // Mirrors the Python drill's alive-and-unknown phase.
        assert!(phase_alive_and_unknown());
    }

    #[test]
    fn test_drill_phase_stale_bell() {
        // Mirrors the Python drill's stale-bell phase.
        assert!(phase_stale_bell());
    }

    #[test]
    fn test_drill_phase_no_dale_and_immutable() {
        // Mirrors the Python drill's no-dale-and-immutable phase.
        assert!(phase_no_dale_and_immutable());
    }

    #[test]
    fn test_drill_passes() {
        // Mirrors test_drill_passes in test_intel_watchman_watch.py
        // (via the watch drill script): the drill itself exits 0.
        let (code, lines) = run_drill();
        assert_eq!(code, 0, "drill lines: {:?}", lines);
        assert!(lines.iter().any(|l| l.contains("6/6 phases PASS")));
    }
}
