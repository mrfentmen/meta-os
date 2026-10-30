//! Bridge from the real watchman to the watchman watchdog (OS-122
//! follow-up to Pax OS-118).
//!
//! Port of `os/intel/watchman_bridge.py`. Pax OS-118 landed the real
//! watchman (`os/watchman/relay_watchman.py`): a pure tick over job and
//! agent-heartbeat records that emits wake and nudge events. What it does
//! not publish is a per-machine watchman record in the shape
//! [`crate::watchman_watch`] judges: `{watchman_alive, last_bell,
//! last_wake}`. This bridge closes that gap from Milo's side only.
//!
//! One mapping rule, nothing else:
//! - A tick the caller actually ran proves the watchman is alive at that
//!   tick's time, so [`fold_tick`] marks `watchman_alive` true with
//!   `last_tick` = now. Aliveness comes from the tick executing, never
//!   from the watchman's rung state file.
//! - A bell is a wake event, nothing else. `last_bell` and `last_wake`
//!   advance only to the latest wake event's `ts` in the tick; a tick
//!   with no wake event keeps the prior bell, and a watchman that has
//!   ticked but never rung carries `last_bell` None. Under the watch
//!   module's own rule that record reads unknown on the board, not alive.
//! - An aged record needs no special case: the watch module judges it
//!   dead once `last_bell` is older than the stale window. The bridge
//!   invents no bell, no wake, and no restart outcome; `restart_ok`
//!   stays a fixture fact the caller supplies.
//!
//! No bus posts, no live Redis, no network, no model calls. The bridge
//! reads only the tick events the caller hands it.
//!
//! Representation notes:
//! - A Python event is a dict; a non-dict event cannot be built in this
//!   typed API. The loop module's event-line parser drops such lines
//!   before they reach [`fold_tick`], which is exactly Python's
//!   skip-and-count behavior for malformed lines. A Python event list
//!   that is not a list folds as an empty list; in Rust that shape is an
//!   empty slice.
//! - A machine missing from the events mapping is not judged at all:
//!   silence in the input is not a dead watchman.

use std::collections::HashMap;

use crate::watchman_watch::{
    JournalEntry, WatchmanRecord, WatchmanSnapshot, watchman_watch_tick,
};

/// Event kind that counts as a bell.
pub const WAKE_KIND: &str = "wake";

/// One relay-watchman tick event, as handed to the bridge.
///
/// `kind` is `None` when the event carries no usable kind, and `ts` is
/// `None` when it carries no usable (non-NaN) numeric timestamp; both
/// read exactly as Python reads a missing or unusable field.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct WatchEvent {
    /// Event kind, if any.
    pub kind: Option<String>,
    /// Event timestamp, if numeric and not NaN.
    pub ts: Option<f64>,
}

impl WatchEvent {
    /// An event with the given kind and timestamp.
    pub fn new(kind: &str, ts: Option<f64>) -> Self {
        WatchEvent {
            kind: Some(kind.to_string()),
            ts: ts.filter(|v| !v.is_nan()),
        }
    }
}

/// The prior record's `last_bell`, or `None` when unusable.
fn prior_bell(prior: Option<&WatchmanRecord>) -> Option<f64> {
    match prior {
        Some(record) => record.last_bell.filter(|v| !v.is_nan()),
        None => None,
    }
}

/// One relay-watchman tick's events -> a watchman-watch record.
///
/// `events` is the tick output's event list. `now` is the tick's time.
/// `prior` is the previous record for the same machine, or `None`.
/// The return is a fresh record; inputs are never mutated.
pub fn fold_tick(
    events: &[WatchEvent],
    now: f64,
    prior: Option<&WatchmanRecord>,
) -> WatchmanRecord {
    let mut bell = prior_bell(prior);
    for event in events {
        if event.kind.as_deref() != Some(WAKE_KIND) {
            continue;
        }
        let ts = match event.ts {
            Some(ts) if !ts.is_nan() => ts,
            _ => continue,
        };
        if bell.is_none() || ts > bell.unwrap() {
            bell = Some(ts);
        }
    }
    WatchmanRecord {
        watchman_alive: Some(true),
        last_tick: if now.is_nan() { None } else { Some(now) },
        last_bell: bell,
        last_wake: bell,
        ..Default::default()
    }
}

/// `{machine: record}` -> the snapshot the watch module consumes.
///
/// Records that are `None` (a shape that is not a watchman record) are
/// skipped, never judged.
pub fn machines_snapshot(
    records: &HashMap<String, Option<WatchmanRecord>>,
) -> WatchmanSnapshot {
    let mut snapshot = WatchmanSnapshot::new();
    for (name, record) in records {
        if let Some(record) = record {
            snapshot
                .machines
                .insert(name.clone(), Some(record.clone()));
        }
    }
    snapshot
}

/// `{machine: record}` with all-valid records -> a snapshot.
pub fn snapshot_from_records(
    records: &HashMap<String, WatchmanRecord>,
) -> WatchmanSnapshot {
    let mut snapshot = WatchmanSnapshot::new();
    for (name, record) in records {
        snapshot
            .machines
            .insert(name.clone(), Some(record.clone()));
    }
    snapshot
}

/// One service-loop call over every machine's watchman events.
///
/// `events_by_machine` is `{machine: events}` where events is a
/// relay-watchman tick's event list. `priors` is `{machine: prior
/// record}` for bell carry-over; a machine absent from priors starts
/// fresh. `journal` is the caller's journal list for episode dedupe; it
/// is never mutated, and only the new records are returned. `restart_ok`
/// is an optional `{machine: bool}` of caller-supplied restart outcomes:
/// a machine with no restart fact supplied carries no `restart_ok` key,
/// so the judge reads a dark machine's restart as failed and escalates
/// once, fail closed, rather than assuming a restart the caller never
/// ran.
///
/// Returns `(records, new_journal)`: records for every machine named in
/// `events_by_machine`; new_journal is what the watch tick judges from
/// those records. Inputs are never mutated. A machine missing from the
/// mapping entirely is absent from records and unjudged.
pub fn watchman_tick(
    events_by_machine: &HashMap<String, Vec<WatchEvent>>,
    now: f64,
    priors: &HashMap<String, WatchmanRecord>,
    journal: &[JournalEntry],
    restart_ok: &HashMap<String, bool>,
) -> (HashMap<String, WatchmanRecord>, Vec<JournalEntry>) {
    let mut names: Vec<&String> = events_by_machine.keys().collect();
    names.sort();
    let mut records: HashMap<String, WatchmanRecord> = HashMap::new();
    for name in names {
        let events = &events_by_machine[name];
        let mut record = fold_tick(events, now, priors.get(name));
        if let Some(outcome) = restart_ok.get(name) {
            record.restart_ok = Some(*outcome);
        }
        records.insert(name.clone(), record);
    }
    let snapshot = snapshot_from_records(&records);
    let new_journal = watchman_watch_tick(&snapshot, journal, now);
    (records, new_journal)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::watchman_watch::{current_states, ALIVE, UNKNOWN};

    const NOW: f64 = 1_000_000.0;
    const STALE: f64 = 5.0 * 60.0;

    fn wake(at: f64) -> WatchEvent {
        WatchEvent::new("wake", Some(at))
    }

    fn kinds(journal: &[JournalEntry]) -> Vec<&str> {
        journal.iter().map(|r| r.kind.as_str()).collect()
    }

    #[test]
    fn test_wake_advances_bell() {
        // Mirrors test_intel_watchman_bridge FoldTest.test_wake_advances_bell.
        // The Python test generates the wake event via the real
        // relay_watchman tick(); relay_watchman is another batch's module,
        // so a literal wake event is used here instead.
        let record = fold_tick(&[wake(NOW)], NOW, None);
        assert_eq!(record.watchman_alive, Some(true));
        assert_eq!(record.last_bell, Some(NOW));
        assert_eq!(record.last_wake, Some(NOW));
        assert_eq!(record.last_tick, Some(NOW));
    }

    #[test]
    fn test_nudge_is_not_a_bell() {
        // Mirrors test_nudge_is_not_a_bell.
        let record = fold_tick(&[WatchEvent::new("nudge", Some(NOW))], NOW, None);
        assert_eq!(record.last_bell, None);
    }

    #[test]
    fn test_prior_bell_kept_without_new_wake() {
        // Mirrors test_prior_bell_kept_without_new_wake.
        let prior = WatchmanRecord {
            watchman_alive: Some(true),
            last_bell: Some(NOW - 60.0),
            ..Default::default()
        };
        let record = fold_tick(&[], NOW, Some(&prior));
        assert_eq!(record.last_bell, Some(NOW - 60.0));
    }

    #[test]
    fn test_malformed_events_and_prior_ignored() {
        // Mirrors test_malformed_events_and_prior_ignored. A non-dict
        // event cannot be built in this typed API; the wake event
        // without a timestamp (the dict half of the Python case) and a
        // missing prior (the non-dict prior half) cover its judgement:
        // no bell is invented, and the record still reads alive.
        let record = fold_tick(&[WatchEvent::new("wake", None)], NOW, None);
        assert_eq!(record.last_bell, None);
        assert_eq!(record.watchman_alive, Some(true));
    }

    #[test]
    fn test_snapshot_skips_non_dict_records() {
        // Mirrors test_snapshot_skips_non_dict_records.
        let mut records: HashMap<String, Option<WatchmanRecord>> = HashMap::new();
        records.insert(
            "m1".to_string(),
            Some(WatchmanRecord {
                watchman_alive: Some(true),
                ..Default::default()
            }),
        );
        records.insert("m2".to_string(), None);
        let snapshot = machines_snapshot(&records);
        assert_eq!(snapshot.machines.keys().collect::<Vec<_>>(), vec!["m1"]);
    }

    #[test]
    fn test_bridge_record_reads_alive_then_dark() {
        // Mirrors test_bridge_record_reads_alive_then_dark.
        let record = fold_tick(&[wake(NOW)], NOW, None);
        let mut records: HashMap<String, WatchmanRecord> = HashMap::new();
        records.insert("m1".to_string(), record);
        let snapshot = snapshot_from_records(&records);
        assert_eq!(current_states(&snapshot, NOW)[0].state, ALIVE);
        assert_eq!(watchman_watch_tick(&snapshot, &[], NOW), Vec::<JournalEntry>::new());
        let mut aged = records["m1"].clone();
        aged.restart_ok = Some(true);
        let mut aged_records: HashMap<String, WatchmanRecord> = HashMap::new();
        aged_records.insert("m1".to_string(), aged);
        let late = NOW + STALE + 60.0;
        let dark = watchman_watch_tick(&snapshot_from_records(&aged_records), &[], late);
        assert_eq!(kinds(&dark), ["crew-dark", "watchman-restart"]);
    }

    #[test]
    fn test_ring_alive_quiet_unknown_no_journal() {
        // Mirrors test_intel_watchman_bridge_tick:
        // test_ring_alive_quiet_unknown_no_journal.
        let mut events: HashMap<String, Vec<WatchEvent>> = HashMap::new();
        events.insert("m1".to_string(), vec![wake(NOW)]);
        events.insert("m2".to_string(), vec![]);
        let (records, journal) = watchman_tick(
            &events,
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        let states: HashMap<String, String> = current_states(&snapshot_from_records(&records), NOW)
            .into_iter()
            .map(|s| (s.machine, s.state))
            .collect();
        assert_eq!(records["m1"].last_bell, Some(NOW));
        assert_eq!(records["m2"].last_bell, None);
        assert_eq!(states["m1"], "alive");
        assert_eq!(states["m2"], "unknown");
        assert!(journal.is_empty());
    }

    #[test]
    fn test_silence_journals_dark_and_restart_only_for_dark() {
        // Mirrors test_silence_journals_dark_and_restart_only_for_dark.
        let mut events: HashMap<String, Vec<WatchEvent>> = HashMap::new();
        events.insert("m1".to_string(), vec![wake(NOW)]);
        events.insert("m2".to_string(), vec![]);
        let (records, _) = watchman_tick(
            &events,
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        let late = NOW + STALE + 60.0;
        let mut events2: HashMap<String, Vec<WatchEvent>> = HashMap::new();
        events2.insert("m1".to_string(), vec![]);
        events2.insert("m2".to_string(), vec![]);
        let mut restart_ok: HashMap<String, bool> = HashMap::new();
        restart_ok.insert("m1".to_string(), true);
        let (_, dark) = watchman_tick(&events2, late, &records, &[], &restart_ok);
        assert_eq!(kinds(&dark), ["crew-dark", "watchman-restart"]);
        assert!(dark.iter().all(|e| e.machine == "m1"));
        assert_eq!(dark[1].restart_ok, Some(true));
    }

    #[test]
    fn test_no_restart_fact_escalates_once() {
        // Mirrors test_no_restart_fact_escalates_once.
        let mut events: HashMap<String, Vec<WatchEvent>> = HashMap::new();
        events.insert("m1".to_string(), vec![wake(NOW)]);
        let (records, _) = watchman_tick(
            &events,
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        let late = NOW + STALE + 60.0;
        let mut events2: HashMap<String, Vec<WatchEvent>> = HashMap::new();
        events2.insert("m1".to_string(), vec![]);
        let (_, dark) = watchman_tick(&events2, late, &records, &[], &HashMap::new());
        assert_eq!(
            kinds(&dark),
            ["crew-dark", "watchman-restart", "escalation"]
        );
    }

    #[test]
    fn test_recovery_then_second_episode_realerts() {
        // Mirrors test_recovery_then_second_episode_realerts.
        let mut events: HashMap<String, Vec<WatchEvent>> = HashMap::new();
        events.insert("m1".to_string(), vec![wake(NOW)]);
        let (records, _) = watchman_tick(
            &events,
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        let late = NOW + STALE + 60.0;
        let mut events2: HashMap<String, Vec<WatchEvent>> = HashMap::new();
        events2.insert("m1".to_string(), vec![]);
        let mut restart_ok: HashMap<String, bool> = HashMap::new();
        restart_ok.insert("m1".to_string(), true);
        let (dark_records, dark) =
            watchman_tick(&events2, late, &records, &[], &restart_ok);
        let mut journal = dark;
        let mut events3: HashMap<String, Vec<WatchEvent>> = HashMap::new();
        events3.insert("m1".to_string(), vec![wake(late + 60.0)]);
        let (recovered_records, recovered) = watchman_tick(
            &events3,
            late + 60.0,
            &dark_records,
            &journal,
            &HashMap::new(),
        );
        assert_eq!(kinds(&recovered), ["watchman-recovered"]);
        journal.extend(recovered);
        let later = late + 2.0 * STALE + 120.0;
        let mut events4: HashMap<String, Vec<WatchEvent>> = HashMap::new();
        events4.insert("m1".to_string(), vec![]);
        let mut restart_ok2: HashMap<String, bool> = HashMap::new();
        restart_ok2.insert("m1".to_string(), false);
        let (dark2_records, dark2) = watchman_tick(
            &events4,
            later,
            &recovered_records,
            &journal,
            &restart_ok2,
        );
        assert_eq!(
            kinds(&dark2),
            ["crew-dark", "watchman-restart", "escalation"]
        );
        journal.extend(dark2);
        let mut events5: HashMap<String, Vec<WatchEvent>> = HashMap::new();
        events5.insert("m1".to_string(), vec![]);
        let (_, again) = watchman_tick(
            &events5,
            later + 60.0,
            &dark2_records,
            &journal,
            &HashMap::new(),
        );
        assert!(again.is_empty());
    }

    #[test]
    fn test_malformed_input_contained_per_machine() {
        // Mirrors test_malformed_input_contained_per_machine. A
        // non-dict events mapping is an empty mapping here, and a
        // non-list events value is an empty event list; both judge as
        // Python judges them (empty records / unknown states).
        let (records, journal) = watchman_tick(
            &HashMap::new(),
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        assert!(records.is_empty());
        assert!(journal.is_empty());
        let mut events: HashMap<String, Vec<WatchEvent>> = HashMap::new();
        events.insert("m1".to_string(), vec![]);
        events.insert("m2".to_string(), vec![]);
        let (records, journal) = watchman_tick(
            &events,
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        let states: HashMap<String, String> =
            current_states(&snapshot_from_records(&records), NOW)
                .into_iter()
                .map(|s| (s.machine, s.state))
                .collect();
        assert_eq!(states["m1"], "unknown");
        assert_eq!(states["m2"], "unknown");
        assert!(journal.is_empty());
    }

    #[test]
    fn test_absent_machine_unjudged() {
        // Mirrors test_absent_machine_unjudged.
        let mut events: HashMap<String, Vec<WatchEvent>> = HashMap::new();
        events.insert("m2".to_string(), vec![]);
        let (records, journal) = watchman_tick(
            &events,
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        assert_eq!(records.keys().collect::<Vec<_>>(), vec!["m2"]);
        assert!(journal.is_empty());
    }

    #[test]
    fn test_inputs_never_mutated() {
        // Mirrors test_inputs_never_mutated.
        let mut events: HashMap<String, Vec<WatchEvent>> = HashMap::new();
        events.insert("m1".to_string(), vec![wake(NOW)]);
        let mut priors: HashMap<String, WatchmanRecord> = HashMap::new();
        priors.insert(
            "m1".to_string(),
            WatchmanRecord {
                watchman_alive: Some(true),
                last_bell: Some(NOW - 60.0),
                ..Default::default()
            },
        );
        let journal = vec![JournalEntry::new("crew-dark", "m1")];
        let events_before = events.clone();
        let priors_before = priors.clone();
        let journal_before = journal.clone();
        watchman_tick(&events, NOW, &priors, &journal, &HashMap::new());
        assert_eq!(events, events_before);
        assert_eq!(priors, priors_before);
        assert_eq!(journal, journal_before);
    }

    #[test]
    fn test_unknown_constant_matches_watch() {
        // Guard: the bridge's unknown reading is the watch module's
        // unknown, not a second spelling.
        assert_eq!(UNKNOWN, "unknown");
        let _ = ALIVE;
    }
}
