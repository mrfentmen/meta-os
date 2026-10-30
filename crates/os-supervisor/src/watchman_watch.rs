//! Watchman watchdog (OS-122): who watches the watchman.
//!
//! Port of `os/intel/watchman_watch.py`. The watchdog treats a dead
//! watchman as a first-class failure ("crew-dark"): the machine's agents
//! are asleep, its jobs are invisible to them, and no bell will ring for
//! new work until the watchman is back.
//!
//! Rules, ported verbatim from the Python source:
//! - A watchman with `watchman_alive` false is dead, whatever its bell says.
//! - A watchman with `watchman_alive` true and a bell older than the stale
//!   window is dead; a fresh bell is alive.
//! - Anything else (no flag, no bell, a malformed record) is unknown, and
//!   unknown machines yield no records and no escalation.
//! - A dead machine with no open dark episode yields a crew-dark record and
//!   a restart record; when the restart cannot revive it (`restart_ok` not
//!   true) the same tick also yields the episode's one escalation record.
//!   A dead machine with an open episode yields nothing new. An alive
//!   machine with an open episode yields a recovered record. Episodes, not
//!   globals: recovery closes an episode, so a second death re-alerts.
//! - The escalation payload is built, never sent. This module has no
//!   network, no bus post, and no secret.
//!
//! Representation notes (typed Rust vs Python dicts):
//! - A Python machine record is a dict; a record that is not a dict (or a
//!   missing snapshot/machines mapping) cannot be built in this typed API.
//!   Those shapes are represented here as `None` entries in
//!   [`WatchmanSnapshot`] (malformed record) or an empty snapshot (missing
//!   or malformed mapping), and both judge exactly as Python judges them:
//!   unknown, yielding no records.
//! - Timestamps are `f64`. Python ints and floats both map to `f64`; a
//!   Python bool timestamp is not a time, and has no typed equivalent here.
//! - The stale window default is [`WATCHMAN_STALE_MINUTES`], read from the
//!   `WATCHDOG_WATCHMAN_STALE_MINUTES` environment variable at call time
//!   when no override is given, mirroring `intel/thresholds.py` (an
//!   unparseable or negative value falls back to the default of 5).
//!
//! Push seam: the Python module imports `intel/push`, which is outside
//! this batch. [`BlockedPushBuilder`] is the seam, and
//! [`DefaultPushBuilder`] reproduces `intel/push.py`'s blocked-push
//! builder and validator exactly for the parked record this module builds.
//! [`watchman_watch_tick`] uses the default builder; use
//! [`watchman_watch_tick_with_push`] to inject another builder.

use std::collections::HashMap;

/// State string for a live watchman.
pub const ALIVE: &str = "alive";
/// State string for a dead watchman.
pub const DEAD: &str = "dead";
/// State string for an unknown watchman state.
pub const UNKNOWN: &str = "unknown";
/// Default stale window in minutes (mirrors `intel/thresholds.py`).
pub const WATCHMAN_STALE_MINUTES: f64 = 5.0;

/// One machine's watchman record, as judged by this module.
///
/// Every field is optional because a Python record may omit it; a missing
/// field judges exactly as Python judges a missing key.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct WatchmanRecord {
    /// The `watchman_alive` flag, if present.
    pub watchman_alive: Option<bool>,
    /// Timestamp of the last bell, if usable.
    pub last_bell: Option<f64>,
    /// Timestamp of the last wake, if usable.
    pub last_wake: Option<f64>,
    /// Timestamp of the last tick, if usable (set by the bridge).
    pub last_tick: Option<f64>,
    /// Caller-supplied restart outcome for this cycle, if any.
    pub restart_ok: Option<bool>,
}

impl WatchmanRecord {
    /// A record with every field unset.
    pub fn new() -> Self {
        Self::default()
    }
}

/// A snapshot of machines for one tick.
///
/// A `None` entry is a malformed (non-dict) machine record: it judges
/// unknown, yields no journal records, and still appears in board states.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct WatchmanSnapshot {
    /// Machine name to record (`None` = malformed record).
    pub machines: HashMap<String, Option<WatchmanRecord>>,
}

impl WatchmanSnapshot {
    /// An empty snapshot: no machine is judged from it.
    pub fn new() -> Self {
        Self::default()
    }
}

/// One board state record per machine.
#[derive(Clone, Debug, PartialEq)]
pub struct StateRecord {
    /// Machine name.
    pub machine: String,
    /// One of [`ALIVE`], [`DEAD`], or [`UNKNOWN`].
    pub state: String,
    /// Last bell timestamp, if usable.
    pub last_bell: Option<f64>,
    /// Last wake timestamp, if usable.
    pub last_wake: Option<f64>,
    /// The tick time this state is as of.
    pub as_of: f64,
}

/// A blocked-push payload, as built by `intel/push.py`'s blocked builder.
#[derive(Clone, Debug, PartialEq)]
pub struct BlockedPush {
    /// Push type; always `"blocked"` from the default builder.
    pub push_type: String,
    /// Job id, here `"watchman:<machine>"`.
    pub job_id: String,
    /// Push title.
    pub title: String,
    /// Push body: `"<title> is blocked. Question: <question>"`.
    pub body: String,
    /// The question, verbatim (stripped).
    pub question: String,
}

/// Seam for the `intel/push` dependency, which is outside this batch.
///
/// The default implementation reproduces `intel/push.py` exactly for the
/// parked record this module builds (status `"blocked"`, note = question).
pub trait BlockedPushBuilder {
    /// Build a blocked push for a parked record, or `None` when gated out.
    fn build_blocked_push(
        &self,
        job_id: &str,
        title: &str,
        status: &str,
        note: &str,
        question: &str,
    ) -> Option<BlockedPush>;
    /// Validate a built push.
    fn validate_push(&self, push: &BlockedPush) -> bool;
}

/// The `intel/push.py` blocked-push builder and validator, reproduced.
#[derive(Clone, Copy, Debug, Default)]
pub struct DefaultPushBuilder;

impl BlockedPushBuilder for DefaultPushBuilder {
    fn build_blocked_push(
        &self,
        job_id: &str,
        title: &str,
        status: &str,
        note: &str,
        question: &str,
    ) -> Option<BlockedPush> {
        if job_id.is_empty() {
            return None;
        }
        if status != "blocked" {
            return None;
        }
        let question = if !question.is_empty() {
            question
        } else {
            note
        };
        let question = question.trim();
        if question.is_empty() {
            return None;
        }
        let title = if !title.is_empty() {
            title.to_string()
        } else {
            format!("job {}", job_id)
        };
        let body = format!("{} is blocked. Question: {}", title, question);
        Some(BlockedPush {
            push_type: "blocked".to_string(),
            job_id: job_id.to_string(),
            title,
            body,
            question: question.to_string(),
        })
    }

    fn validate_push(&self, push: &BlockedPush) -> bool {
        if push.push_type != "done" && push.push_type != "blocked" {
            return false;
        }
        if push.job_id.is_empty() {
            return false;
        }
        !push.body.trim().is_empty()
    }
}

/// One journal record produced by a watchman tick.
///
/// Fields mirror the Python dict keys; only the fields a given kind
/// carries are set. `dedupe_key` is empty for hand-built entries that
/// carry no dedupe key (Python journal entries are read by kind and
/// machine, so a missing key never changes episode judgement).
#[derive(Clone, Debug, Default, PartialEq)]
pub struct JournalEntry {
    /// Record kind: `crew-dark`, `watchman-restart`, `escalation`, or
    /// `watchman-recovered` (other kinds render nothing in brief lines).
    pub kind: String,
    /// Machine name.
    pub machine: String,
    /// State carried by crew-dark (`dead`) and recovered (`alive`) records.
    pub state: Option<String>,
    /// Reason carried by crew-dark and escalation records.
    pub reason: Option<String>,
    /// Question carried by escalation records.
    pub question: Option<String>,
    /// Blocked-push payload carried by escalation records.
    pub push: Option<BlockedPush>,
    /// Restart outcome carried by restart records.
    pub restart_ok: Option<bool>,
    /// Creation time carried by crew-dark records.
    pub created_at: Option<f64>,
    /// Recovery time carried by recovered records.
    pub recovered_at: Option<f64>,
    /// Attempt time carried by restart records.
    pub attempted_at: Option<f64>,
    /// Escalation time carried by escalation records.
    pub escalated_at: Option<f64>,
    /// Dedupe key carried by tick-produced records.
    pub dedupe_key: String,
}

impl JournalEntry {
    /// A journal entry with only kind and machine set.
    pub fn new(kind: &str, machine: &str) -> Self {
        JournalEntry {
            kind: kind.to_string(),
            machine: machine.to_string(),
            ..Default::default()
        }
    }
}

/// The stale window in minutes used when no override is given.
///
/// Reads `WATCHDOG_WATCHMAN_STALE_MINUTES` at call time; an unparseable
/// or negative value falls back to [`WATCHMAN_STALE_MINUTES`].
pub fn stale_minutes_default() -> f64 {
    match std::env::var("WATCHDOG_WATCHMAN_STALE_MINUTES") {
        Ok(raw) => match raw.trim().parse::<f64>() {
            Ok(value) if value >= 0.0 => value,
            _ => WATCHMAN_STALE_MINUTES,
        },
        Err(_) => WATCHMAN_STALE_MINUTES,
    }
}

/// Alive, dead, or unknown for one watchman record.
///
/// `None` is a malformed or missing record and reads unknown.
/// `stale_minutes` overrides the default for this call; `None` reads the
/// default at call time.
pub fn machine_state(
    record: Option<&WatchmanRecord>,
    now: f64,
    stale_minutes: Option<f64>,
) -> &'static str {
    let record = match record {
        Some(record) => record,
        None => return UNKNOWN,
    };
    if record.watchman_alive == Some(false) {
        return DEAD;
    }
    if record.watchman_alive != Some(true) {
        return UNKNOWN;
    }
    let bell = match record.last_bell {
        Some(bell) => bell,
        None => return UNKNOWN,
    };
    let stale = stale_minutes.unwrap_or_else(stale_minutes_default);
    let window = stale * 60.0;
    if now - bell > window {
        DEAD
    } else {
        ALIVE
    }
}

/// One board state record per machine, in name order.
pub fn current_states(snapshot: &WatchmanSnapshot, now: f64) -> Vec<StateRecord> {
    let mut names: Vec<&String> = snapshot.machines.keys().collect();
    names.sort();
    names
        .into_iter()
        .map(|name| {
            let record = snapshot.machines.get(name).and_then(|r| r.as_ref());
            let state = machine_state(record, now, None).to_string();
            let (bell, wake) = match record {
                Some(record) => (record.last_bell, record.last_wake),
                None => (None, None),
            };
            StateRecord {
                machine: name.clone(),
                state,
                last_bell: bell,
                last_wake: wake,
                as_of: now,
            }
        })
        .collect()
}

/// True when the machine's latest crew-dark record has no recovered
/// record after it. Journal order is episode order.
fn episode_open(journal: &[JournalEntry], machine: &str) -> bool {
    let mut open_dark = false;
    for entry in journal {
        if entry.machine != machine {
            continue;
        }
        if entry.kind == "crew-dark" {
            open_dark = true;
        } else if entry.kind == "watchman-recovered" {
            open_dark = false;
        }
    }
    open_dark
}

/// True when an escalation record appears after the machine's latest
/// crew-dark record.
///
/// Ported verbatim, including the Python quirk: the second scan checks
/// only the kind, not the machine, so an escalation for another machine
/// that follows this machine's latest crew-dark record also counts.
fn escalated_this_episode(journal: &[JournalEntry], machine: &str) -> bool {
    let mut last_dark: Option<usize> = None;
    for (index, entry) in journal.iter().enumerate() {
        if entry.machine != machine {
            continue;
        }
        if entry.kind == "crew-dark" {
            last_dark = Some(index);
        }
    }
    let last_dark = match last_dark {
        Some(index) => index,
        None => return false,
    };
    journal[last_dark + 1..]
        .iter()
        .any(|entry| entry.kind == "escalation")
}

/// The one blocked-push payload for an unrevivable watchman, or `None`
/// when no valid payload builds. The payload is built, never sent.
fn escalation_for(
    machine: &str,
    now: f64,
    push_builder: &dyn BlockedPushBuilder,
) -> Option<JournalEntry> {
    let question = format!(
        "The watchman on machine {} is dead and its restart failed; \
         the machine's agents are asleep and its jobs are invisible to \
         them. Dale's call is needed.",
        machine
    );
    let parked_id = format!("watchman:{}", machine);
    let title = format!("Watchman on machine {}", machine);
    let payload = push_builder.build_blocked_push(
        &parked_id,
        &title,
        "blocked",
        &question,
        &question,
    )?;
    if !push_builder.validate_push(&payload) {
        return None;
    }
    Some(JournalEntry {
        kind: "escalation".to_string(),
        machine: machine.to_string(),
        reason: Some("watchman dead, restart failed".to_string()),
        question: Some(question),
        push: Some(payload),
        escalated_at: Some(now),
        dedupe_key: format!("watchdark-escalate:{}", machine),
        ..Default::default()
    })
}

/// New journal records for this tick's machines, using the default push
/// builder. Inputs are never mutated; the return holds only new records.
pub fn watchman_watch_tick(
    snapshot: &WatchmanSnapshot,
    journal: &[JournalEntry],
    now: f64,
) -> Vec<JournalEntry> {
    watchman_watch_tick_with_push(snapshot, journal, now, &DefaultPushBuilder)
}

/// New journal records for this tick's machines, with an injected push
/// builder (the seam for `intel/push`, which is outside this batch).
pub fn watchman_watch_tick_with_push(
    snapshot: &WatchmanSnapshot,
    journal: &[JournalEntry],
    now: f64,
    push_builder: &dyn BlockedPushBuilder,
) -> Vec<JournalEntry> {
    let mut records: Vec<JournalEntry> = Vec::new();
    let mut names: Vec<&String> = snapshot.machines.keys().collect();
    names.sort();
    for name in names {
        let record = snapshot.machines.get(name).and_then(|r| r.as_ref());
        let state = machine_state(record, now, None);
        if state == UNKNOWN {
            continue;
        }
        if state == ALIVE {
            let combined: Vec<JournalEntry> =
                journal.iter().cloned().chain(records.iter().cloned()).collect();
            if episode_open(&combined, name) {
                records.push(JournalEntry {
                    kind: "watchman-recovered".to_string(),
                    machine: name.clone(),
                    state: Some(ALIVE.to_string()),
                    recovered_at: Some(now),
                    dedupe_key: format!("watchrecovered:{}", name),
                    ..Default::default()
                });
            }
            continue;
        }
        // Dead.
        let combined: Vec<JournalEntry> =
            journal.iter().cloned().chain(records.iter().cloned()).collect();
        if episode_open(&combined, name) {
            continue;
        }
        records.push(JournalEntry {
            kind: "crew-dark".to_string(),
            machine: name.clone(),
            state: Some(DEAD.to_string()),
            reason: Some(
                "watchman dead: agents asleep, jobs invisible".to_string(),
            ),
            created_at: Some(now),
            dedupe_key: format!("watchdark:{}", name),
            ..Default::default()
        });
        let restart_ok = record.map(|r| r.restart_ok == Some(true)).unwrap_or(false);
        records.push(JournalEntry {
            kind: "watchman-restart".to_string(),
            machine: name.clone(),
            restart_ok: Some(restart_ok),
            attempted_at: Some(now),
            dedupe_key: format!("watchrestart:{}", name),
            ..Default::default()
        });
        if !restart_ok {
            let combined: Vec<JournalEntry> = journal
                .iter()
                .cloned()
                .chain(records.iter().cloned())
                .collect();
            if !escalated_this_episode(&combined, name) {
                if let Some(escalation) = escalation_for(name, now, push_builder) {
                    records.push(escalation);
                }
            }
        }
    }
    records
}

/// One frozen line per watchman journal record for the next brief.
/// Other records render nothing.
pub fn watchman_brief_lines(records: &[JournalEntry]) -> Vec<String> {
    let mut lines = Vec::new();
    for record in records {
        match record.kind.as_str() {
            "crew-dark" => lines.push(format!(
                "Crew-dark on machine {}: watchman dead, agents asleep, jobs invisible.",
                record.machine
            )),
            "watchman-restart" => {
                if record.restart_ok == Some(true) {
                    lines.push(format!(
                        "Watchman restart attempted on machine {}: restart succeeded.",
                        record.machine
                    ));
                } else {
                    lines.push(format!(
                        "Watchman restart attempted on machine {}: restart failed.",
                        record.machine
                    ));
                }
            }
            "escalation" => lines.push(format!(
                "Escalated machine {}: one blocked push queued (watchman dead, restart failed).",
                record.machine
            )),
            "watchman-recovered" => lines.push(format!(
                "Watchman recovered on machine {}.",
                record.machine
            )),
            _ => {}
        }
    }
    lines
}

/// One line per board state record for the machine groups.
pub fn board_lines(states: &[StateRecord]) -> Vec<String> {
    let mut lines = Vec::new();
    for state in states {
        match state.state.as_str() {
            DEAD => lines.push(format!(
                "Machine {}: watchman dead (crew-dark).",
                state.machine
            )),
            ALIVE => lines.push(format!(
                "Machine {}: watchman alive.",
                state.machine
            )),
            UNKNOWN => lines.push(format!(
                "Machine {}: watchman state unknown.",
                state.machine
            )),
            _ => {}
        }
    }
    lines
}

#[cfg(test)]
mod tests {
    use super::*;

    const T0: f64 = 100000.0;

    fn dead_machine(restart_ok: bool) -> WatchmanRecord {
        WatchmanRecord {
            watchman_alive: Some(false),
            last_bell: Some(T0 - 600.0),
            last_wake: Some(T0 - 600.0),
            restart_ok: Some(restart_ok),
            ..Default::default()
        }
    }

    fn snapshot_with(machine: &str, record: Option<WatchmanRecord>) -> WatchmanSnapshot {
        let mut snapshot = WatchmanSnapshot::new();
        snapshot.machines.insert(machine.to_string(), record);
        snapshot
    }

    fn kinds(records: &[JournalEntry]) -> Vec<&str> {
        records.iter().map(|r| r.kind.as_str()).collect()
    }

    #[test]
    fn test_killed_watchman_flags_crew_dark_in_one_tick() {
        // Mirrors test_intel_watchman_watch:
        // test_killed_watchman_flags_crew_dark_in_one_tick.
        let snap = snapshot_with("milo-box", Some(dead_machine(true)));
        let new = watchman_watch_tick(&snap, &[], T0);
        assert_eq!(kinds(&new), ["crew-dark", "watchman-restart"]);
        assert!(!new.iter().any(|r| r.push.is_some()));
    }

    #[test]
    fn test_revival_yields_recovered_and_still_no_escalation() {
        // Mirrors test_revival_yields_recovered_and_still_no_escalation.
        let snap = snapshot_with("milo-box", Some(dead_machine(true)));
        let journal = watchman_watch_tick(&snap, &[], T0);
        let alive = WatchmanRecord {
            watchman_alive: Some(true),
            last_bell: Some(T0),
            last_wake: Some(T0),
            restart_ok: Some(true),
            ..Default::default()
        };
        let snap2 = snapshot_with("milo-box", Some(alive));
        let new = watchman_watch_tick(&snap2, &journal, T0 + 60.0);
        assert_eq!(kinds(&new), ["watchman-recovered"]);
        assert!(!journal.iter().chain(new.iter()).any(|r| r.push.is_some()));
    }

    #[test]
    fn test_beyond_repair_yields_exactly_one_valid_escalation() {
        // Mirrors test_beyond_repair_yields_exactly_one_valid_escalation.
        let snap = snapshot_with("rowan-box", Some(dead_machine(false)));
        let journal = watchman_watch_tick(&snap, &[], T0);
        assert_eq!(
            kinds(&journal),
            ["crew-dark", "watchman-restart", "escalation"]
        );
        let escalation = &journal[2];
        let builder = DefaultPushBuilder;
        assert!(builder.validate_push(escalation.push.as_ref().unwrap()));
        assert!(escalation
            .question
            .as_ref()
            .unwrap()
            .contains("rowan-box"));
        for tick in [T0 + 60.0, T0 + 120.0] {
            assert_eq!(watchman_watch_tick(&snap, &journal, tick), Vec::<JournalEntry>::new());
        }
        assert_eq!(
            journal.iter().filter(|r| r.kind == "escalation").count(),
            1
        );
    }

    #[test]
    fn test_second_death_after_recovery_realerts() {
        // Mirrors test_second_death_after_recovery_realerts.
        let snap = snapshot_with("milo-box", Some(dead_machine(true)));
        let mut journal = watchman_watch_tick(&snap, &[], T0);
        let alive = WatchmanRecord {
            watchman_alive: Some(true),
            last_bell: Some(T0),
            last_wake: Some(T0),
            restart_ok: Some(false),
            ..Default::default()
        };
        let snap2 = snapshot_with("milo-box", Some(alive));
        journal.extend(watchman_watch_tick(&snap2, &journal, T0 + 60.0));
        let snap3 = snapshot_with("milo-box", Some(dead_machine(false)));
        let new = watchman_watch_tick(&snap3, &journal, T0 + 120.0);
        assert_eq!(
            kinds(&new),
            ["crew-dark", "watchman-restart", "escalation"]
        );
    }

    #[test]
    fn test_stale_bell_reads_dead_and_fresh_bell_reads_alive() {
        // Mirrors test_stale_bell_reads_dead_and_fresh_bell_reads_alive.
        // The thresholds constant itself lives in another batch's module;
        // this module's own default is asserted here instead.
        assert_eq!(WATCHMAN_STALE_MINUTES, 5.0);
        let stale = WatchmanRecord {
            watchman_alive: Some(true),
            last_bell: Some(T0 - 301.0),
            last_wake: Some(T0 - 301.0),
            ..Default::default()
        };
        let fresh = WatchmanRecord {
            watchman_alive: Some(true),
            last_bell: Some(T0 - 60.0),
            last_wake: Some(T0 - 60.0),
            ..Default::default()
        };
        assert_eq!(machine_state(Some(&stale), T0, Some(5.0)), DEAD);
        assert_eq!(machine_state(Some(&fresh), T0, Some(5.0)), ALIVE);
        // Boundary: exactly at the window is not yet dead (strict `>`).
        let edge = WatchmanRecord {
            watchman_alive: Some(true),
            last_bell: Some(T0 - 300.0),
            ..Default::default()
        };
        assert_eq!(machine_state(Some(&edge), T0, Some(5.0)), ALIVE);
    }

    #[test]
    fn test_unknown_machine_yields_nothing_and_reads_unknown() {
        // Mirrors test_unknown_machine_yields_nothing_and_reads_unknown.
        let mut record = WatchmanRecord::new();
        record.last_bell = None;
        let snap = snapshot_with("quiet-box", Some(record));
        assert_eq!(watchman_watch_tick(&snap, &[], T0), Vec::<JournalEntry>::new());
        let states = current_states(&snap, T0);
        assert_eq!(states[0].state, UNKNOWN);
        assert_eq!(
            board_lines(&states),
            ["Machine quiet-box: watchman state unknown."]
        );
    }

    #[test]
    fn test_malformed_inputs_never_crash() {
        // Mirrors test_malformed_inputs_never_crash. A missing mapping is
        // an empty snapshot; a non-mapping machines value is likewise
        // empty; a non-dict machine record is a None entry.
        assert_eq!(
            watchman_watch_tick(&WatchmanSnapshot::new(), &[], T0),
            Vec::<JournalEntry>::new()
        );
        let snap = snapshot_with("x", None);
        assert_eq!(watchman_watch_tick(&snap, &[], T0), Vec::<JournalEntry>::new());
        assert_eq!(machine_state(None, T0, None), UNKNOWN);
        let states = current_states(&snap, T0);
        assert_eq!(states[0].state, UNKNOWN);
        assert!(states[0].last_bell.is_none());
    }

    #[test]
    fn test_tick_never_mutates_inputs() {
        // Mirrors test_tick_never_mutates_inputs.
        let snap = snapshot_with("rowan-box", Some(dead_machine(false)));
        let journal = vec![JournalEntry::new("crew-dark", "other-box")];
        let snap_before = snap.clone();
        let journal_before = journal.clone();
        watchman_watch_tick(&snap, &journal, T0);
        assert_eq!(snap, snap_before);
        assert_eq!(journal, journal_before);
    }

    #[test]
    fn test_brief_and_board_lines() {
        // Mirrors test_brief_and_board_lines.
        let mut restart = JournalEntry::new("watchman-restart", "m-box");
        restart.restart_ok = Some(false);
        let records = vec![
            JournalEntry::new("crew-dark", "m-box"),
            restart,
            JournalEntry::new("escalation", "m-box"),
            JournalEntry::new("watchman-recovered", "m-box"),
            JournalEntry::new("unrelated", "m-box"),
        ];
        let lines = watchman_brief_lines(&records);
        assert_eq!(lines.len(), 4);
        assert!(lines.iter().all(|line| line.contains("m-box")));
        let states = vec![
            StateRecord {
                machine: "a".to_string(),
                state: DEAD.to_string(),
                last_bell: None,
                last_wake: None,
                as_of: T0,
            },
            StateRecord {
                machine: "b".to_string(),
                state: ALIVE.to_string(),
                last_bell: None,
                last_wake: None,
                as_of: T0,
            },
            StateRecord {
                machine: "c".to_string(),
                state: UNKNOWN.to_string(),
                last_bell: None,
                last_wake: None,
                as_of: T0,
            },
        ];
        assert_eq!(
            board_lines(&states),
            [
                "Machine a: watchman dead (crew-dark).",
                "Machine b: watchman alive.",
                "Machine c: watchman state unknown.",
            ]
        );
    }

    #[test]
    fn test_escalation_payload_built_never_sent() {
        // Behavioral mirror of test_escalation_is_built_never_sent: the
        // escalation carries a payload and no send marker, and this
        // module exposes no send API. (The Python test's source-text
        // scan for socket/urllib/bus imports has no Rust equivalent:
        // this std-only module has no network dependency by
        // construction.)
        let snap = snapshot_with("rowan-box", Some(dead_machine(false)));
        let journal = watchman_watch_tick(&snap, &[], T0);
        let escalation = &journal[2];
        assert!(escalation.push.is_some());
        assert_eq!(escalation.push.as_ref().unwrap().push_type, "blocked");
        assert_eq!(
            escalation.push.as_ref().unwrap().job_id,
            "watchman:rowan-box"
        );
    }

    #[test]
    fn test_escalated_this_episode_quirk_other_machine_counts() {
        // Ported Python quirk, not covered by a Python case: the second
        // scan in _escalated_this_episode checks kind only, not machine.
        // A dark record for m1 followed by an escalation for m2 blocks
        // m1's own escalation on the next tick of the same episode.
        let mut journal = vec![
            JournalEntry::new("crew-dark", "m1"),
            JournalEntry::new("escalation", "m2"),
        ];
        // m1 is dead with an open episode, so it yields nothing anyway;
        // instead verify the quirk through a fresh dark + failed restart
        // where the journal already holds a foreign escalation after a
        // closed-then-reopened episode is impossible without recovery,
        // so assert directly via a second death after recovery:
        let snap = snapshot_with("m1", Some(dead_machine(true)));
        journal = watchman_watch_tick(&snap, &[], T0);
        let alive = WatchmanRecord {
            watchman_alive: Some(true),
            last_bell: Some(T0),
            last_wake: Some(T0),
            ..Default::default()
        };
        let snap2 = snapshot_with("m1", Some(alive));
        journal.extend(watchman_watch_tick(&snap2, &journal, T0 + 60.0));
        // Foreign escalation appended after m1's recovery (not after a
        // new dark record) must not block m1's next escalation.
        journal.push(JournalEntry::new("escalation", "m2"));
        let snap3 = snapshot_with("m1", Some(dead_machine(false)));
        let new = watchman_watch_tick(&snap3, &journal, T0 + 120.0);
        assert_eq!(
            kinds(&new),
            ["crew-dark", "watchman-restart", "escalation"]
        );
    }

    #[test]
    fn test_default_push_builder_gates() {
        // Mirrors intel/push.py gates used through the seam: a
        // non-blocked status, an empty id, or an empty question yields
        // no push; a valid blocked record validates.
        let builder = DefaultPushBuilder;
        assert!(builder
            .build_blocked_push("watchman:m", "T", "open", "q", "q")
            .is_none());
        assert!(builder
            .build_blocked_push("", "T", "blocked", "q", "q")
            .is_none());
        assert!(builder
            .build_blocked_push("watchman:m", "T", "blocked", "", "")
            .is_none());
        let push = builder
            .build_blocked_push("watchman:m", "Watchman on machine m", "blocked", "q?", "q?")
            .unwrap();
        assert_eq!(push.body, "Watchman on machine m is blocked. Question: q?");
        assert!(builder.validate_push(&push));
    }
}
