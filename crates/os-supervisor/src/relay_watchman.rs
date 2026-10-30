//! Relay watchman (OS-118): the resident bell for one Meta OS machine.
//!
//! Port of `os/os/watchman/relay_watchman.py` (batch B21, tasks T131/T119).
//! Port behavior, do not redesign.
//!
//! The watchman watches job records and agent heartbeats and rings the
//! bell: it emits wake events for sleeping agents with newly posted jobs,
//! and nudge events for workers whose heartbeat has gone stale on a
//! claimed job. That is the whole job of this program.
//!
//! Source of truth, stated first because the failure mode matters: job
//! state only. [`tick`] reads job records (id, status, addressee, claim,
//! lease) and agent heartbeat records. It takes no bus message counter,
//! reads no message list, and counts no messages, so replaying bus
//! messages, skipping them, or corrupting a stored counter changes
//! nothing: a job that exists and is unclaimed is a fact, not a count.
//!
//! What this module is not:
//!
//! - It makes no model calls and holds no session of its own. Waking
//!   means emitting the wake event naming job + agent; starting the
//!   agent's session with the job as its brief is the OS-119 wake
//!   adapter's work, not this module's.
//! - It posts nothing to the bus and moves no claim. A wake event is a
//!   record, not an announcement.
//! - It does not restart processes and does not reassign jobs. Those
//!   mechanical rungs belong to systemd under the OS-034 contract
//!   (restart) and to the overseer via the OS-125 baton pass (reassign).
//! - It does not invent addressees. A job rings only when its
//!   `addressed_to` (or legacy `to`) field names a local agent nick.
//!   An unaddressed open job is not this machine's to wake.
//!
//! Statuses that never ring: anything but `open` (wake) and `claimed`
//! (nudge). Done, cancelled, blocked, and failed-final jobs are silent,
//! as are malformed records (no id) and jobs addressed to agents this
//! machine does not know. (Python defines a `_SILENT_STATUSES` list, but
//! the decision itself is the `else` branch: every status other than
//! `open`/`claimed` is silent, including unknown statuses.)
//!
//! # Live-behavior boundary (not faked here)
//!
//! The Python program is a CLI: it reads jobs/agents JSON files, prints
//! one JSON event per line, updates a state file holding the rung
//! ledger, and loops with sleeps. This module ports the pure decision
//! core of that CLI ([`tick`], [`normalize_agents`], [`addressed_to`],
//! [`is_sleeping`], and the `--once` / `--loop` decision layer in
//! [`run_once`] / [`loop_cycle`] / [`validate_args`]). Real file
//! reading, JSON parsing, stdout printing, sleeping, and process exit
//! codes live in the CLI shell the parent wires at assembly; they are
//! modelled here as inputs ([`InputLoad`], [`StateLoad`]) and outputs
//! ([`OnceSuccess`], [`OnceError`]) so the decisions are testable
//! without pretending to touch a filesystem. No live relay is watched
//! and no live effect is performed by this module.
//!
//! # Self-containment seam
//!
//! This file is self-contained per the batch work-split: it uses only
//! `std` plus items defined here. It imports nothing from sibling
//! modules. In particular it does not depend on any `relay_common`
//! code (excluded from this batch); the watchman reads plain job and
//! agent records, never bus/relay internals.

use std::collections::{BTreeMap, HashSet};

/// Default seconds between loop cycles (Python `--interval` default).
pub const DEFAULT_INTERVAL_SECONDS: i64 = 10;

/// Default heartbeat age, in seconds, that counts as stale
/// (Python `--heartbeat-stale-seconds` default).
pub const DEFAULT_HEARTBEAT_STALE_SECONDS: f64 = 300.0;

/// Event kind string for a wake event.
pub const WAKE: &str = "wake";

/// Event kind string for a nudge event.
pub const NUDGE: &str = "nudge";

/// CLI exit code: ok.
pub const EXIT_OK: i32 = 0;

/// CLI exit code: bad input or usage (Python `main` returns 2).
pub const EXIT_BAD_INPUT: i32 = 2;

/// The kind of a watchman event.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EventKind {
    /// A sleeping local agent has a newly posted open job.
    Wake,
    /// A local claimer's heartbeat has gone stale on a claimed job.
    Nudge,
}

impl EventKind {
    /// The event kind as the string the Python program emits.
    pub fn as_str(self) -> &'static str {
        match self {
            EventKind::Wake => WAKE,
            EventKind::Nudge => NUDGE,
        }
    }
}

/// One watchman event, mirroring the Python event dict.
///
/// Wake events carry no `heartbeat_age_seconds`; nudge events do, so
/// that field is `None` for wake events and `Some(age)` for nudges.
/// `title` is `None` when the job carries no (non-blank) title: a
/// title is never invented.
#[derive(Clone, Debug, PartialEq)]
pub struct Event {
    /// Wake or nudge.
    pub kind: EventKind,
    /// The job id that rang.
    pub job_id: String,
    /// The local agent nick that rang.
    pub agent: String,
    /// The job title, if the job carried one.
    pub title: Option<String>,
    /// The watch cycle time (unix seconds) the event was raised at.
    pub ts: f64,
    /// For nudges only: `now - heartbeat_at` in seconds.
    pub heartbeat_age_seconds: Option<f64>,
}

/// A job record, holding exactly the fields [`tick`] reads.
///
/// Fields are `Option` because the Python program tolerates missing
/// fields: a missing/blank id means the record is malformed and never
/// rings; a missing/blank status means a silent (non-open, non-claimed)
/// record. Stray fields carried on a Python job dict (for example a
/// `bus_message_count`) have no counterpart here: [`tick`] never reads
/// them, so varying them changes nothing, exactly as in Python.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Job {
    /// Job id (required to ring; blank/missing means malformed).
    pub id: Option<String>,
    /// Job status, e.g. `"open"` or `"claimed"`.
    pub status: Option<String>,
    /// Primary addressee field.
    pub addressed_to: Option<String>,
    /// Legacy addressee field, used only when `addressed_to` is absent.
    pub to: Option<String>,
    /// Claimer nick, read only for `claimed` jobs (nudge path).
    pub claim: Option<String>,
    /// Job title, carried into the event record only.
    pub title: Option<String>,
}

/// One agent heartbeat record as supplied by the caller, before
/// normalization.
///
/// `registered` is `None` when the caller does not say: Python treats
/// a missing `registered` field as registered (`True` default), and
/// only an explicit `False` drops the agent.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct AgentInput {
    /// Agent nick; for list-form input this is the record's nick field.
    /// For map-form input the map key wins (see [`normalize_agents`]).
    pub nick: Option<String>,
    /// Last heartbeat, unix seconds; `None` means never seen.
    pub heartbeat_at: Option<f64>,
    /// `Some(false)` means unregistered and not local; anything else
    /// means registered.
    pub registered: Option<bool>,
}

/// A normalized local agent record (output of [`normalize_agents`]).
///
/// After normalization every agent is registered: unregistered nicks
/// are dropped, never kept with a flag.
#[derive(Clone, Debug, PartialEq)]
pub struct Agent {
    /// Agent nick (stripped, non-blank).
    pub nick: String,
    /// Last heartbeat, unix seconds; `None` means never seen.
    pub heartbeat_at: Option<f64>,
    /// Always `true` after normalization.
    pub registered: bool,
}

/// Agents input in either shape the Python program accepts: a mapping
/// nick -> record, or a list of records each carrying a nick field.
///
/// Non-record entries and records without a nick cannot be expressed
/// in the list form's typed records; in Python they are dropped by
/// [`normalize_agents`], and here they simply cannot be constructed.
#[derive(Clone, Debug, PartialEq)]
pub enum AgentsInput {
    /// Mapping form: each pair is (map key nick, record). The map key
    /// wins over any nick carried inside the record, mirroring Python
    /// (`record["nick"] = nick` after reading the key).
    Map(Vec<(String, AgentInput)>),
    /// List form: each record's own nick field is used.
    List(Vec<AgentInput>),
}

/// A stripped string, or `None` for anything blank/missing.
///
/// Mirrors Python `_text`: strips surrounding whitespace, and an
/// empty-after-strip string means absent, never a guess.
pub fn text(value: Option<&str>) -> Option<String> {
    let trimmed = value?.trim();
    if trimmed.is_empty() {
        None
    } else {
        Some(trimmed.to_string())
    }
}

/// Who a job is addressed to, from `addressed_to`, then `to`.
///
/// Mirrors `intel/wake.py`'s rule so the watchman and the wake adapter
/// agree on addressing. Missing or empty fields mean unaddressed,
/// never a guess. A non-record job cannot be expressed in this typed
/// API (Python returns `None` for it); a [`Job`] with both fields
/// blank behaves the same way.
pub fn addressed_to(job: &Job) -> Option<String> {
    text(job.addressed_to.as_deref())
        .or_else(|| text(job.to.as_deref()))
}

/// Agents input -> map nick -> record.
///
/// Accepts a dict or a list. Unregistered agents (`registered` false)
/// are dropped: they are not this machine's to wake. Records without
/// a (non-blank) nick are dropped. The input is never mutated (it is
/// borrowed, and the output is a fresh map).
pub fn normalize_agents(agents: &AgentsInput) -> BTreeMap<String, Agent> {
    let mut out = BTreeMap::new();
    match agents {
        AgentsInput::Map(items) => {
            for (key, rec) in items {
                // Map key wins over the record's own nick.
                let nick = match text(Some(key.as_str())) {
                    Some(nick) => nick,
                    None => continue,
                };
                if rec.registered == Some(false) {
                    continue;
                }
                out.insert(
                    nick.clone(),
                    Agent {
                        nick,
                        heartbeat_at: rec.heartbeat_at,
                        registered: true,
                    },
                );
            }
        }
        AgentsInput::List(items) => {
            for rec in items {
                let nick = match text(rec.nick.as_deref()) {
                    Some(nick) => nick,
                    None => continue,
                };
                if rec.registered == Some(false) {
                    continue;
                }
                out.insert(
                    nick.clone(),
                    Agent {
                        nick,
                        heartbeat_at: rec.heartbeat_at,
                        registered: true,
                    },
                );
            }
        }
    }
    out
}

/// True when an agent has no heartbeat or a stale one.
///
/// A never-seen agent (`heartbeat_at` `None`) is sleeping. Otherwise
/// sleeping means strictly older than `stale_seconds`: an age exactly
/// equal to the threshold is not stale.
pub fn is_sleeping(agent: &Agent, now: f64, stale_seconds: f64) -> bool {
    match agent.heartbeat_at {
        None => true,
        Some(heartbeat) => (now - heartbeat) > stale_seconds,
    }
}

/// Wake dedup key for a job id: `"wake:<id>"`.
pub fn wake_key(job_id: &str) -> String {
    format!("wake:{job_id}")
}

/// Nudge dedup key for a job id and the heartbeat value that went
/// stale: `"nudge:<id>:<heartbeat>"`.
///
/// Approximation note: Python formats the heartbeat with `%s`, so an
/// integer heartbeat `999000` and a float heartbeat `999000.0` give
/// different keys (`"999000"` vs `"999000.0"`). This typed API carries
/// heartbeats as `f64`, and Rust formats integer-valued floats without
/// a fractional part, matching the Python integer form. Heartbeat
/// timestamps in practice are integer unix seconds, so the keys agree
/// on real inputs.
pub fn nudge_key(job_id: &str, heartbeat: f64) -> String {
    format!("nudge:{job_id}:{heartbeat}")
}

/// One watch cycle. Returns `(events, new_rung_keys)`.
///
/// Pure: no I/O, no counter input, no mutation of jobs, agents, or the
/// ledger (all borrowed; new keys are returned for the caller to
/// merge). A second tick over the same state with the merged ledger
/// yields no repeat events.
///
/// Wake rule: an `open` job addressed to a local sleeping agent rings
/// once per job id. Nudge rule: a `claimed` job whose local claimer
/// has a heartbeat older than `heartbeat_stale_seconds` rings once
/// per (job id, stale heartbeat value): the same stale heartbeat never
/// re-nudges, but a worker that comes back and stalls again on the
/// same job (a new heartbeat value) earns a fresh nudge. A claimer
/// with no heartbeat at all is never nudged into existence.
pub fn tick(
    jobs: &[Job],
    agents: &AgentsInput,
    rung_ledger: &HashSet<String>,
    now: f64,
    heartbeat_stale_seconds: f64,
) -> (Vec<Event>, Vec<String>) {
    let local = normalize_agents(agents);
    let mut events = Vec::new();
    let mut new_keys = Vec::new();
    for job in jobs {
        let job_id = match text(job.id.as_deref()) {
            Some(id) => id,
            None => continue,
        };
        let status = text(job.status.as_deref());
        match status.as_deref() {
            Some("open") => {
                let nick = match addressed_to(job) {
                    Some(nick) => nick,
                    None => continue,
                };
                let agent = match local.get(&nick) {
                    Some(agent) => agent,
                    None => continue,
                };
                if !is_sleeping(agent, now, heartbeat_stale_seconds) {
                    continue;
                }
                let key = wake_key(&job_id);
                if rung_ledger.contains(&key) {
                    continue;
                }
                events.push(Event {
                    kind: EventKind::Wake,
                    job_id,
                    agent: nick,
                    title: text(job.title.as_deref()),
                    ts: now,
                    heartbeat_age_seconds: None,
                });
                new_keys.push(key);
            }
            Some("claimed") => {
                let claimer = match text(job.claim.as_deref()) {
                    Some(claimer) => claimer,
                    None => continue,
                };
                let agent = match local.get(&claimer) {
                    Some(agent) => agent,
                    None => continue,
                };
                let heartbeat = match agent.heartbeat_at {
                    Some(heartbeat) => heartbeat,
                    // Never seen: never nudged into existence.
                    None => continue,
                };
                let age = now - heartbeat;
                if age <= heartbeat_stale_seconds {
                    continue;
                }
                let key = nudge_key(&job_id, heartbeat);
                if rung_ledger.contains(&key) {
                    continue;
                }
                events.push(Event {
                    kind: EventKind::Nudge,
                    job_id,
                    agent: claimer,
                    title: text(job.title.as_deref()),
                    ts: now,
                    heartbeat_age_seconds: Some(age),
                });
                new_keys.push(key);
            }
            // Silent statuses and unknown statuses never ring.
            _ => continue,
        }
    }
    (events, new_keys)
}

/// How one input file loaded, modelling the Python `_load_json_file`
/// outcomes without doing I/O: a missing file reads as an empty
/// snapshot (with a stderr note in the real CLI, not modelled here);
/// a present file carries its parsed value; a malformed file is an
/// error naming the file.
#[derive(Clone, Debug, PartialEq)]
pub enum InputLoad<T> {
    /// File missing: read as empty.
    Missing,
    /// File present and parsed.
    Present(T),
    /// File present but malformed/unreadable; the message names the file.
    Malformed(String),
}

/// A parsed state file, modelling the Python `_run_once` ledger read:
/// a missing state file means an empty ledger; a present state
/// document contributes its `"rung"` list only when it is a dict
/// carrying a list there, and only the string entries of that list
/// (non-string entries are filtered out, mirroring the Python
/// comprehension). A non-dict document or a non-list `"rung"` means
/// an empty ledger.
#[derive(Clone, Debug, Default, PartialEq)]
pub enum StateLoad {
    /// State file missing: empty ledger.
    #[default]
    Missing,
    /// State document present: `rung` is `Some(list)` only for a dict
    /// document with a list under `"rung"`; each entry is `Some(text)`
    /// for string entries and `None` for non-string entries.
    Present {
        rung: Option<Vec<Option<String>>>,
    },
}

impl StateLoad {
    /// The ledger set this state document contributes.
    pub fn ledger(&self) -> HashSet<String> {
        let mut ledger = HashSet::new();
        if let StateLoad::Present { rung: Some(entries) } = self {
            for entry in entries {
                if let Some(key) = entry {
                    ledger.insert(key.clone());
                }
            }
        }
        ledger
    }
}

/// Successful `--once` outcome: the events to print, and the rung
/// ledger to write back to the state file, if any.
///
/// The state file is written only when new keys fired (Python:
/// `if state_path and new_keys`). `state_to_write` is `None` when
/// nothing fired, meaning the caller must leave the state file alone
/// (in particular a missing state file is not created by a silent run).
#[derive(Clone, Debug, PartialEq)]
pub struct OnceSuccess {
    /// Events for this cycle, in job order.
    pub events: Vec<Event>,
    /// Merged ledger, sorted, to write to the state file — or `None`
    /// when no new keys fired.
    pub state_to_write: Option<Vec<String>>,
}

/// `--once` failure: malformed input. The message names the file.
/// Under `--once` this exits 2 with no event printed; under `--loop`
/// the cycle is skipped (see [`loop_cycle`]).
#[derive(Clone, Debug, PartialEq)]
pub struct OnceError(pub String);

/// The merged rung ledger: old keys plus new keys, sorted.
///
/// Mirrors Python `sorted(ledger | set(new_keys))` for the state file.
pub fn merge_ledger(ledger: &HashSet<String>, new_keys: &[String]) -> Vec<String> {
    let mut merged: Vec<String> = ledger.iter().cloned().collect();
    merged.extend(new_keys.iter().cloned());
    merged.sort();
    merged.dedup();
    merged
}

/// One `--once` cycle from already-loaded inputs.
///
/// Missing jobs/agents files read as empty snapshots; a malformed
/// jobs or agents file is an error (exit 2, no events). The state
/// file contributes its ledger; the returned `state_to_write` is
/// `Some` only when new keys fired.
pub fn run_once(
    jobs: InputLoad<Vec<Job>>,
    agents: InputLoad<AgentsInput>,
    state: StateLoad,
    now: f64,
    heartbeat_stale_seconds: f64,
) -> Result<OnceSuccess, OnceError> {
    let jobs = match jobs {
        InputLoad::Missing => Vec::new(),
        InputLoad::Present(jobs) => jobs,
        InputLoad::Malformed(message) => return Err(OnceError(message)),
    };
    let agents = match agents {
        InputLoad::Missing => AgentsInput::Map(Vec::new()),
        InputLoad::Present(agents) => agents,
        InputLoad::Malformed(message) => return Err(OnceError(message)),
    };
    let ledger = state.ledger();
    let (events, new_keys) = tick(
        &jobs,
        &agents,
        &ledger,
        now,
        heartbeat_stale_seconds,
    );
    let state_to_write = if new_keys.is_empty() {
        None
    } else {
        Some(merge_ledger(&ledger, &new_keys))
    };
    Ok(OnceSuccess {
        events,
        state_to_write,
    })
}

/// Map a `--once` result to its process exit code: 0 ok, 2 bad input.
pub fn once_exit_code(result: &Result<OnceSuccess, OnceError>) -> i32 {
    match result {
        Ok(_) => EXIT_OK,
        Err(_) => EXIT_BAD_INPUT,
    }
}

/// One `--loop` cycle from already-loaded inputs.
///
/// Identical to [`run_once`] except a malformed input file is skipped
/// for that cycle (with a stderr note in the real CLI): the cycle
/// yields no events instead of failing. The state write rule is the
/// same: a merged ledger is returned only when new keys fired.
pub fn loop_cycle(
    jobs: InputLoad<Vec<Job>>,
    agents: InputLoad<AgentsInput>,
    state: StateLoad,
    now: f64,
    heartbeat_stale_seconds: f64,
) -> Vec<Event> {
    match run_once(jobs, agents, state, now, heartbeat_stale_seconds) {
        Ok(success) => success.events,
        Err(_) => Vec::new(),
    }
}

/// Validate the CLI timing arguments, mirroring Python `main`'s usage
/// check: `--interval` must be positive and
/// `--heartbeat-stale-seconds` non-negative, else exit 2.
pub fn validate_args(interval_seconds: i64, heartbeat_stale_seconds: f64) -> Result<(), OnceError> {
    if interval_seconds <= 0 || heartbeat_stale_seconds < 0.0 {
        return Err(OnceError(
            "watchman: --interval must be positive and \
             --heartbeat-stale-seconds non-negative"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    const NOW: f64 = 1_000_000.0;
    const STALE: f64 = 300.0;

    fn job(job_id: &str, status: &str) -> Job {
        Job {
            id: Some(job_id.to_string()),
            status: Some(status.to_string()),
            ..Job::default()
        }
    }

    fn addressed(job_id: &str, nick: &str) -> Job {
        Job {
            addressed_to: Some(nick.to_string()),
            ..job(job_id, "open")
        }
    }

    fn map_agents(pairs: Vec<(&str, Option<f64>, Option<bool>)>) -> AgentsInput {
        AgentsInput::Map(
            pairs
                .into_iter()
                .map(|(nick, heartbeat_at, registered)| {
                    (
                        nick.to_string(),
                        AgentInput {
                            nick: None,
                            heartbeat_at,
                            registered,
                        },
                    )
                })
                .collect(),
        )
    }

    fn empty_ledger() -> HashSet<String> {
        HashSet::new()
    }

    // --- WakeTest (mirrors test_os_watchman.py WakeTest) ---

    #[test]
    fn test_open_job_wakes_sleeping_local_agent() {
        let jobs = vec![Job {
            title: Some("Write the brief".to_string()),
            ..addressed("7", "hana")
        }];
        let agents = map_agents(vec![("hana", None, None)]);
        let (events, keys) = tick(&jobs, &agents, &empty_ledger(), NOW, STALE);
        assert_eq!(events.len(), 1);
        assert_eq!(events[0].kind, EventKind::Wake);
        assert_eq!(events[0].job_id, "7");
        assert_eq!(events[0].agent, "hana");
        assert_eq!(events[0].title.as_deref(), Some("Write the brief"));
        assert_eq!(events[0].heartbeat_age_seconds, None);
        assert_eq!(keys, vec!["wake:7".to_string()]);
    }

    #[test]
    fn test_wake_via_legacy_to_field() {
        let jobs = vec![Job {
            to: Some("milo".to_string()),
            ..job("8", "open")
        }];
        let agents = map_agents(vec![("milo", None, None)]);
        let (events, _) = tick(&jobs, &agents, &empty_ledger(), NOW, STALE);
        assert_eq!(events.len(), 1);
        assert_eq!(events[0].agent, "milo");
    }

    #[test]
    fn test_no_wake_for_other_agent_awake_or_unaddressed() {
        let jobs = vec![
            addressed("1", "ghost"),
            addressed("2", "hana"),
            job("3", "open"),
        ];
        let agents = map_agents(vec![("hana", Some(NOW), None)]);
        let (events, _) = tick(&jobs, &agents, &empty_ledger(), NOW, STALE);
        assert!(events.is_empty());
    }

    #[test]
    fn test_no_wake_for_done_or_malformed_or_unknown() {
        // "not-a-record" (a non-dict jobs entry) has no typed
        // counterpart here: a jobs entry is always a Job record, so
        // the malformed cases expressible are a record with no id
        // and a record addressed to an unknown agent.
        let jobs = vec![
            Job {
                addressed_to: Some("hana".to_string()),
                ..job("1", "done")
            },
            Job {
                addressed_to: Some("hana".to_string()),
                ..job("2", "cancelled")
            },
            Job {
                addressed_to: Some("hana".to_string()),
                status: Some("open".to_string()),
                id: None,
                ..Job::default()
            },
            addressed("3", "ghost"),
        ];
        let agents = map_agents(vec![("hana", None, None)]);
        let (events, _) = tick(&jobs, &agents, &empty_ledger(), NOW, STALE);
        assert!(events.is_empty());
    }

    #[test]
    fn test_unregistered_agent_is_not_local() {
        let jobs = vec![addressed("9", "buffy")];
        let agents = map_agents(vec![("buffy", None, Some(false))]);
        let (events, _) = tick(&jobs, &agents, &empty_ledger(), NOW, STALE);
        assert!(events.is_empty());
    }

    // --- NudgeTest (mirrors test_os_watchman.py NudgeTest) ---

    #[test]
    fn test_stale_heartbeat_nudges_on_same_cycle() {
        let jobs = vec![Job {
            claim: Some("milo".to_string()),
            title: Some("Run the drill".to_string()),
            ..job("4", "claimed")
        }];
        let agents = map_agents(vec![("milo", Some(NOW - 1000.0), None)]);
        let (events, keys) = tick(&jobs, &agents, &empty_ledger(), NOW, STALE);
        assert_eq!(events.len(), 1);
        assert_eq!(events[0].kind, EventKind::Nudge);
        assert_eq!(events[0].job_id, "4");
        assert_eq!(events[0].agent, "milo");
        assert_eq!(events[0].heartbeat_age_seconds, Some(1000.0));
        assert_eq!(keys, vec![format!("nudge:4:{}", NOW - 1000.0)]);
    }

    #[test]
    fn test_fresh_or_missing_heartbeat_never_nudges() {
        let jobs = vec![
            Job {
                claim: Some("milo".to_string()),
                ..job("5", "claimed")
            },
            Job {
                claim: Some("hana".to_string()),
                ..job("6", "claimed")
            },
        ];
        let agents = map_agents(vec![
            ("milo", Some(NOW - 10.0), None),
            ("hana", None, None),
        ]);
        let (events, _) = tick(&jobs, &agents, &empty_ledger(), NOW, STALE);
        assert!(events.is_empty());
    }

    #[test]
    fn test_claim_by_nonlocal_agent_never_nudges() {
        let jobs = vec![Job {
            claim: Some("rowan".to_string()),
            ..job("5", "claimed")
        }];
        let agents = map_agents(vec![("milo", Some(NOW - 1000.0), None)]);
        let (events, _) = tick(&jobs, &agents, &empty_ledger(), NOW, STALE);
        assert!(events.is_empty());
    }

    // --- CounterAndDedupeTest (mirrors test_os_watchman.py) ---

    #[test]
    fn test_counter_field_variation_changes_nothing() {
        // Python varies stray fields (bus_message_count, seen) carried
        // on the job dict. This typed API has no stray-field slot, so
        // the mirror varies fields tick() does not read on each path
        // (a claim on the wake path, an addressee on the nudge path)
        // and asserts identical events. That tick takes no counter
        // argument at all is a compile-time fact of its signature:
        // (jobs, agents, rung_ledger, now, heartbeat_stale_seconds).
        let base = vec![addressed("7", "hana")];
        let agents = map_agents(vec![("hana", None, None)]);
        let (first, _) = tick(&base, &agents, &empty_ledger(), NOW, STALE);
        let drifted = vec![Job {
            claim: Some("someone".to_string()),
            ..addressed("7", "hana")
        }];
        let (second, _) = tick(&drifted, &agents, &empty_ledger(), NOW, STALE);
        assert_eq!(first, second);
        assert_eq!(first.len(), 1);
    }

    #[test]
    fn test_second_tick_with_merged_ledger_is_silent() {
        let jobs = vec![
            addressed("7", "hana"),
            Job {
                claim: Some("milo".to_string()),
                ..job("4", "claimed")
            },
        ];
        let agents = map_agents(vec![
            ("hana", None, None),
            ("milo", Some(NOW - 1000.0), None),
        ]);
        let (events, keys) = tick(&jobs, &agents, &empty_ledger(), NOW, STALE);
        assert_eq!(events.len(), 2);
        let merged: HashSet<String> = keys.into_iter().collect();
        let (again, _) = tick(&jobs, &agents, &merged, NOW, STALE);
        assert!(again.is_empty());
    }

    #[test]
    fn test_nudge_refires_only_when_heartbeat_refreshes() {
        let jobs = vec![Job {
            claim: Some("milo".to_string()),
            ..job("4", "claimed")
        }];
        let old = map_agents(vec![("milo", Some(NOW - 1000.0), None)]);
        let (_, keys) = tick(&jobs, &old, &empty_ledger(), NOW, STALE);
        let merged: HashSet<String> = keys.into_iter().collect();
        // Same stale heartbeat value: still deduped, silent.
        let (again, _) = tick(&jobs, &old, &merged, NOW, STALE);
        assert!(again.is_empty());
        // Worker came back and stalled again: new heartbeat value,
        // hence a new nudge key, hence a fresh nudge.
        let fresh = map_agents(vec![("milo", Some(NOW - 900.0), None)]);
        let (events, _) = tick(&jobs, &fresh, &merged, NOW, STALE);
        assert_eq!(events.len(), 1);
        assert_eq!(events[0].kind, EventKind::Nudge);
    }

    #[test]
    fn test_inputs_never_mutated() {
        let jobs = vec![addressed("7", "hana")];
        let agents = map_agents(vec![("hana", None, None)]);
        let ledger = empty_ledger();
        let snapshot_jobs = jobs.clone();
        let snapshot_agents = agents.clone();
        tick(&jobs, &agents, &ledger, NOW, STALE);
        assert_eq!(jobs, snapshot_jobs);
        assert_eq!(agents, snapshot_agents);
        assert!(ledger.is_empty());
    }

    // --- Boundary / normalization cases pinned by the source ---

    #[test]
    fn test_addressed_to_prefers_addressed_to_and_trims() {
        let job_rec = Job {
            addressed_to: Some("  hana  ".to_string()),
            to: Some("milo".to_string()),
            ..job("1", "open")
        };
        assert_eq!(addressed_to(&job_rec).as_deref(), Some("hana"));
        let blank = Job {
            addressed_to: Some("   ".to_string()),
            to: Some("milo".to_string()),
            ..job("2", "open")
        };
        assert_eq!(addressed_to(&blank).as_deref(), Some("milo"));
        let neither = job("3", "open");
        assert_eq!(addressed_to(&neither), None);
    }

    #[test]
    fn test_stale_boundary_is_strict() {
        // Age exactly equal to the threshold is NOT stale on either
        // path: is_sleeping is a strict (now - heartbeat) > stale, so
        // the wake does not fire, and the nudge's age <= stale skip
        // also suppresses the nudge.
        let wake_jobs = vec![addressed("7", "hana")];
        let wake_agents = map_agents(vec![("hana", Some(NOW - STALE), None)]);
        let (events, _) = tick(&wake_jobs, &wake_agents, &empty_ledger(), NOW, STALE);
        assert!(events.is_empty(), "age == stale is not sleeping, so no wake");
        let nudge_jobs = vec![Job {
            claim: Some("milo".to_string()),
            ..job("4", "claimed")
        }];
        let nudge_agents = map_agents(vec![("milo", Some(NOW - STALE), None)]);
        let (events, _) = tick(&nudge_jobs, &nudge_agents, &empty_ledger(), NOW, STALE);
        assert!(events.is_empty(), "age == stale must not nudge");
    }

    #[test]
    fn test_normalize_agents_list_form_and_map_key_wins() {
        let list = AgentsInput::List(vec![
            AgentInput {
                nick: Some("hana".to_string()),
                heartbeat_at: None,
                registered: None,
            },
            AgentInput {
                nick: None,
                heartbeat_at: None,
                registered: None,
            },
        ]);
        let normalized = normalize_agents(&list);
        assert_eq!(normalized.len(), 1);
        assert!(normalized.contains_key("hana"));
        // Map key wins over the record's own nick.
        let map = AgentsInput::Map(vec![(
            "hana".to_string(),
            AgentInput {
                nick: Some("someone-else".to_string()),
                heartbeat_at: None,
                registered: None,
            },
        )]);
        let normalized = normalize_agents(&map);
        assert_eq!(normalized.len(), 1);
        assert!(normalized.contains_key("hana"));
        assert_eq!(normalized["hana"].nick, "hana");
    }

    #[test]
    fn test_silent_and_unknown_statuses_never_ring() {
        for status in ["done", "cancelled", "blocked", "failed-final", "failed", "bogus"] {
            let jobs = vec![addressed("1", "hana")];
            let mut jobs = jobs;
            jobs[0].status = Some(status.to_string());
            let agents = map_agents(vec![("hana", None, None)]);
            let (events, _) = tick(&jobs, &agents, &empty_ledger(), NOW, STALE);
            assert!(events.is_empty(), "status {status} must be silent");
        }
    }

    // --- CliTest decisions (mirrors test_os_watchman.py CliTest) ---
    //
    // The Python CLI tests run the program as a subprocess over temp
    // JSON files. This module ports the decisions those runs pin
    // (events, state-file contents, exit codes) through run_once over
    // already-loaded inputs; actual file I/O and JSON parsing live in
    // the CLI shell at assembly (see the module docs).

    #[test]
    fn test_once_prints_event_and_second_run_is_silent() {
        let jobs = InputLoad::Present(vec![Job {
            title: Some("Write it".to_string()),
            ..addressed("7", "hana")
        }]);
        let agents = InputLoad::Present(map_agents(vec![("hana", None, None)]));
        let first = run_once(jobs.clone(), agents.clone(), StateLoad::Missing, NOW, STALE)
            .expect("first run must succeed");
        assert_eq!(once_exit_code(&Ok(first.clone())), EXIT_OK);
        assert_eq!(first.events.len(), 1);
        assert_eq!(first.events[0].kind, EventKind::Wake);
        assert_eq!(first.events[0].job_id, "7");
        assert_eq!(
            first.state_to_write,
            Some(vec!["wake:7".to_string()]),
            "state file must carry the merged rung ledger"
        );
        // Second run over the merged ledger is silent and writes nothing.
        let state = StateLoad::Present {
            rung: Some(vec![Some("wake:7".to_string())]),
        };
        let second = run_once(jobs, agents, state, NOW, STALE).expect("second run ok");
        assert!(second.events.is_empty());
        assert_eq!(second.state_to_write, None);
    }

    #[test]
    fn test_once_reusing_state_file_is_silent() {
        let jobs = InputLoad::Present(vec![addressed("7", "hana")]);
        let agents = InputLoad::Present(map_agents(vec![("hana", None, None)]));
        let first = run_once(
            jobs.clone(),
            agents.clone(),
            StateLoad::Missing,
            NOW,
            STALE,
        )
        .expect("first run ok");
        assert_eq!(first.events.len(), 1);
        let second = run_once(
            jobs,
            agents,
            StateLoad::Present {
                rung: Some(vec![Some("wake:7".to_string())]),
            },
            NOW,
            STALE,
        )
        .expect("second run ok");
        assert_eq!(once_exit_code(&Ok(second.clone())), EXIT_OK);
        assert!(second.events.is_empty());
        assert_eq!(second.state_to_write, None);
    }

    #[test]
    fn test_once_malformed_input_exits_2_with_no_event() {
        let result = run_once(
            InputLoad::Malformed("watchman: cannot read jobs file".to_string()),
            InputLoad::Present(map_agents(vec![])),
            StateLoad::Missing,
            NOW,
            STALE,
        );
        assert!(result.is_err());
        assert_eq!(once_exit_code(&result), EXIT_BAD_INPUT);
        // No events exist on the error path by construction: the
        // caller prints events only from Ok.
    }

    #[test]
    fn test_once_missing_files_read_as_empty() {
        let result = run_once(
            InputLoad::Missing,
            InputLoad::Missing,
            StateLoad::Missing,
            NOW,
            STALE,
        )
        .expect("missing files must not fail");
        assert_eq!(once_exit_code(&Ok(result.clone())), EXIT_OK);
        assert!(result.events.is_empty());
        assert_eq!(result.state_to_write, None);
    }

    #[test]
    fn test_loop_cycle_skips_malformed_input() {
        let events = loop_cycle(
            InputLoad::Malformed("watchman: cannot read jobs file".to_string()),
            InputLoad::Present(map_agents(vec![])),
            StateLoad::Missing,
            NOW,
            STALE,
        );
        assert!(events.is_empty(), "loop skips a malformed cycle");
    }

    #[test]
    fn test_state_rung_non_string_entries_filtered() {
        // Non-dict state and non-list rung both mean an empty ledger,
        // so the wake still fires; non-string rung entries are dropped.
        let jobs = InputLoad::Present(vec![addressed("7", "hana")]);
        let agents = InputLoad::Present(map_agents(vec![("hana", None, None)]));
        let state = StateLoad::Present {
            rung: Some(vec![None, Some("wake:9".to_string())]),
        };
        let result = run_once(jobs, agents, state, NOW, STALE).expect("ok");
        assert_eq!(result.events.len(), 1);
        assert_eq!(
            result.state_to_write,
            Some(vec!["wake:7".to_string(), "wake:9".to_string()]),
            "merged ledger is sorted with non-string entries dropped"
        );
        let no_rung = run_once(
            InputLoad::Present(vec![addressed("7", "hana")]),
            InputLoad::Present(map_agents(vec![("hana", None, None)])),
            StateLoad::Present { rung: None },
            NOW,
            STALE,
        )
        .expect("ok");
        assert_eq!(no_rung.events.len(), 1);
    }

    #[test]
    fn test_validate_args_rejects_bad_timing() {
        assert!(validate_args(10, 300.0).is_ok());
        assert!(validate_args(0, 300.0).is_err());
        assert!(validate_args(-5, 300.0).is_err());
        assert!(validate_args(10, -1.0).is_err());
        assert!(validate_args(10, 0.0).is_ok(), "zero staleness is allowed");
    }
}
