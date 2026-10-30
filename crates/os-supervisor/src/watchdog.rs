//! Watchdog core — silent-failure detectors (WDG workstream).
//!
//! Rust port of `os/intel/watchdog.py` (batch B21, task T129).
//! Port behavior, do not redesign: the Python module is the spec.
//!
//! `tick` evaluates every registered detector over one snapshot and
//! returns the alert records found; an optional emit callback receives
//! each alert. The loop itself never hardcodes a detector: detectors
//! register in [`DETECTORS`]. The watchdog never mutates job state —
//! it alerts; humans (or the mos tick) act.
//!
//! Detectors (WDG-002..WDG-009, INT-010, OS-085, OS-037):
//! presence-stall, progress-stall, lease-risk, dead-dep, missing-dep,
//! file-collision, attempt-exhaustion / attempt-warning, silent-room
//! (info only), rejected-dispatch, budget-warning. Walk-on tracking
//! ([`detect_walk_on_workers`], WDG-025) is a standalone tracking
//! function, deliberately not a detector and not in [`DETECTORS`].
//! Journal failures (OS-037) are a second loop input, also not in
//! [`DETECTORS`]: snapshot ticks never wait on journalctl.
//!
//! Self-containment seams (this file uses only `std` plus items
//! defined here; sibling modules are being written in parallel and
//! their APIs are not settled yet):
//! - Thresholds: [`Thresholds`] embeds the locked defaults from
//!   `os/intel/thresholds.py` plus its env-override parsing
//!   (WDG-018). When the thresholds module lands, this struct can
//!   be replaced by a re-export without changing detector logic.
//! - Explanations: [`render_explanation`] embeds the templates from
//!   `os/intel/explanations.py` verbatim, because alert wording is
//!   part of the watchdog's observable behavior. When the
//!   explanations module lands, replace this function with a call
//!   into it; the template keys and field names are unchanged.
//! - Budgets: [`detect_budget_warning`] embeds the warning-band
//!   rule from `os/intel/budgets.py` (`at_warning`: spent at or
//!   past the warning percent of cap, but below cap). When the
//!   budgets module lands, replace the local check with it.
//! - Spark polish: [`PolishClient`] is the trait seam for
//!   `intel.explanations.polish_explanation`'s client seat.
//! - Store: the alert writer (`intel.store.write_alert`), the
//!   lifecycle/dedupe/query/store-status functions, and the
//!   self-heartbeat writer (`intel.store.wd_self_beat`) live in
//!   another module. `tick`'s `emit` / `beat` callbacks are the
//!   seats those writers plug into; this module never touches a
//!   store or the bus on its own (Dale's posting rule: the
//!   `announce` callback receives frozen-format lines, held, not
//!   posted).
//!
//! Live-behavior boundary (never faked): the CLI's `--beat` flag
//! is accepted, but the beat callback in this standalone module
//! is a no-op sink — the real beat writer is the store module's
//! `wd_self_beat`. Likewise `--loop` sleeps between ticks and
//! `--journal` reads journalctl JSON from a file; neither restarts
//! a unit nor posts anywhere. The watchdog never restarts a unit
//! itself (OS-034: systemd owns process death).

use std::collections::{HashMap, HashSet, VecDeque};
use std::io::Write;
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

// ---------------------------------------------------------------------------
// Thresholds (locked defaults from os/intel/thresholds.py, FND-030/INT-022)
// ---------------------------------------------------------------------------

/// Lease duration in seconds from `jobs.py` (reference only; the
/// watchdog reads lease values off the job, never redefines them).
pub const LEASE_DEFAULT_SECONDS: i64 = 1800;

/// Watchdog thresholds. Defaults are the INT-022 locked table.
/// Construct with [`Thresholds::default`] for production defaults,
/// or override individual fields (the Rust equivalent of reloading
/// the Python thresholds module with `WATCHDOG_*` variables set;
/// see [`Thresholds::from_env_with`]).
#[derive(Clone, Debug)]
pub struct Thresholds {
    /// Minutes of no activity before a presence-stall fires.
    pub stall_minutes: i64,
    /// Minutes of no progress before a progress-stall fires.
    pub progress_stall_minutes: i64,
    /// Minutes to lease expiry inside which a lease-risk warns.
    pub lease_risk_window_minutes: i64,
    /// Minutes of heartbeat quiet required for a lease-risk warning.
    pub lease_risk_quiet_minutes: i64,
    /// Alert dedupe cooldown in minutes (store-side; kept here
    /// because the Python thresholds module owns the constant).
    pub alert_dedupe_cooldown_minutes: i64,
    /// Minutes of room silence before a silent-room record fires.
    pub silent_room_minutes: i64,
    /// Self-heartbeat key TTL in seconds.
    pub watchdog_beat_ttl_seconds: i64,
    /// Page size for the tick message walk (WDG-017).
    pub tick_page_size: i64,
    /// Maximum messages kept in a tick window (WDG-017).
    pub tick_max_messages: usize,
    /// Budget warning threshold percent (OS-085, default 80).
    pub budget_warn_percent: i64,
}

impl Default for Thresholds {
    /// The INT-022 locked defaults.
    fn default() -> Self {
        Thresholds {
            stall_minutes: 10,
            progress_stall_minutes: 10,
            lease_risk_window_minutes: 5,
            lease_risk_quiet_minutes: 2,
            alert_dedupe_cooldown_minutes: 30,
            silent_room_minutes: 60,
            watchdog_beat_ttl_seconds: 300,
            tick_page_size: 1000,
            tick_max_messages: 1000,
            budget_warn_percent: 80,
        }
    }
}

/// One env-overridable integer threshold, mirroring
/// `thresholds._env_int`: blank, unparseable, or below-minimum
/// values fall back to the default silently, never raising.
pub fn env_int(raw: Option<&str>, default: i64, minimum: i64) -> i64 {
    let raw = match raw {
        Some(raw) => raw.trim(),
        None => return default,
    };
    if raw.is_empty() {
        return default;
    }
    match raw.parse::<i64>() {
        Ok(value) if value >= minimum => value,
        _ => default,
    }
}

/// Env integer with both bounds, mirroring `budgets._env_int`
/// (used for the budget warning percent, range 1..=100).
pub fn env_int_range(raw: Option<&str>, default: i64, minimum: i64, maximum: i64) -> i64 {
    let raw = match raw {
        Some(raw) => raw.trim(),
        None => return default,
    };
    if raw.is_empty() {
        return default;
    }
    match raw.parse::<i64>() {
        Ok(value) if value >= minimum && value <= maximum => value,
        _ => default,
    }
}

impl Thresholds {
    /// Read thresholds from the process environment (`WATCHDOG_*`
    /// variables), exactly as the Python module does at import time.
    pub fn from_env() -> Self {
        Self::from_env_with(|name| std::env::var(name).ok())
    }

    /// Read thresholds using a caller-supplied lookup. Production
    /// passes the real environment ([`Thresholds::from_env`]);
    /// tests pass a fixed map, so no test ever mutates the real
    /// environment (Rust tests run in parallel threads).
    pub fn from_env_with<F: Fn(&str) -> Option<String>>(lookup: F) -> Self {
        let get = |name: &str| lookup(name);
        Thresholds {
            stall_minutes: env_int(get("WATCHDOG_STALL_MINUTES").as_deref(), 10, 0),
            progress_stall_minutes: env_int(
                get("WATCHDOG_PROGRESS_STALL_MINUTES").as_deref(),
                10,
                0,
            ),
            lease_risk_window_minutes: env_int(
                get("WATCHDOG_LEASE_RISK_WINDOW_MINUTES").as_deref(),
                5,
                0,
            ),
            lease_risk_quiet_minutes: env_int(
                get("WATCHDOG_LEASE_RISK_QUIET_MINUTES").as_deref(),
                2,
                0,
            ),
            alert_dedupe_cooldown_minutes: env_int(
                get("WATCHDOG_ALERT_DEDUPE_COOLDOWN_MINUTES").as_deref(),
                30,
                0,
            ),
            silent_room_minutes: env_int(
                get("WATCHDOG_SILENT_ROOM_MINUTES").as_deref(),
                60,
                0,
            ),
            watchdog_beat_ttl_seconds: env_int(
                get("WATCHDOG_BEAT_TTL_SECONDS").as_deref(),
                300,
                1,
            ),
            tick_page_size: env_int(get("WATCHDOG_TICK_PAGE_SIZE").as_deref(), 1000, 1),
            tick_max_messages: env_int(
                get("WATCHDOG_TICK_MAX_MESSAGES").as_deref(),
                1000,
                1,
            ) as usize,
            budget_warn_percent: env_int_range(
                get("WATCHDOG_BUDGET_WARN_PERCENT").as_deref(),
                80,
                1,
                100,
            ),
        }
    }
}

// ---------------------------------------------------------------------------
// Loose snapshot values (the Python dict shape, with its tolerance)
// ---------------------------------------------------------------------------

/// A JSON-like value, mirroring a Python snapshot dict's loose
/// typing: numbers may arrive as ints, floats, or numeric strings
/// (Redis hash form), fields may be missing or mistyped, and a
/// mistyped section is treated as empty, never as a crash.
#[derive(Clone, Debug, PartialEq)]
pub enum Value {
    /// Missing / JSON null.
    Null,
    /// A boolean. Python's `bool` is an `int` subclass, so timestamp
    /// fields accept it (as 1/0) while `_as_int` fields reject it —
    /// see [`Value::as_py_int`] vs [`Value::as_strict_int`].
    Bool(bool),
    /// An integer.
    Int(i64),
    /// A float; truncated toward zero where an int is needed.
    Float(f64),
    /// A string.
    Str(String),
    /// A list.
    List(Vec<Value>),
    /// An object, as insertion-ordered key/value pairs.
    Map(Vec<(String, Value)>),
}

impl Value {
    /// Look up a key in a map value; `None` for non-maps and
    /// missing keys.
    pub fn get(&self, key: &str) -> Option<&Value> {
        match self {
            Value::Map(entries) => entries
                .iter()
                .find(|(k, _)| k == key)
                .map(|(_, v)| v),
            _ => None,
        }
    }

    /// The string form of a value, Python `str()` style for the
    /// scalar cases detectors actually meet (ints, floats, bools,
    /// strings); `None` for null, lists, and maps.
    pub fn py_str(&self) -> Option<String> {
        match self {
            Value::Str(s) => Some(s.clone()),
            Value::Int(i) => Some(i.to_string()),
            Value::Float(f) => {
                if f.is_finite() && f.fract() == 0.0 {
                    Some(format!("{:.1}", f))
                } else {
                    Some(format!("{}", f))
                }
            }
            Value::Bool(true) => Some("True".to_string()),
            Value::Bool(false) => Some("False".to_string()),
            _ => None,
        }
    }

    /// Python `isinstance(value, (int, float))` semantics: bools
    /// count (1/0), floats truncate. Used for timestamps and
    /// lease fields, where the Python code does not reject bools.
    pub fn as_py_int(&self) -> Option<i64> {
        match self {
            Value::Bool(true) => Some(1),
            Value::Bool(false) => Some(0),
            Value::Int(i) => Some(*i),
            Value::Float(f) if f.is_finite() => Some(*f as i64),
            _ => None,
        }
    }

    /// Python `_as_int` semantics: bools rejected, ints kept,
    /// floats truncated, non-empty strings parsed as ints, and
    /// anything else yields the caller's default (`None` here).
    pub fn as_strict_int(&self) -> Option<i64> {
        match self {
            Value::Bool(_) => None,
            Value::Int(i) => Some(*i),
            Value::Float(f) if f.is_finite() => Some(*f as i64),
            Value::Str(s) => {
                let trimmed = s.trim();
                if trimmed.is_empty() {
                    None
                } else {
                    trimmed.parse::<i64>().ok()
                }
            }
            _ => None,
        }
    }

    /// A non-empty string, else `None`.
    pub fn as_nonempty_str(&self) -> Option<String> {
        match self {
            Value::Str(s) if !s.is_empty() => Some(s.clone()),
            _ => None,
        }
    }
}

/// One job row in a snapshot, in the shape `intel/ingest.py` rows
/// use (the `jobs.py` list --json shape).
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Job {
    /// Job id as a string (`str(id)` in Python); `None` when the
    /// snapshot carries no id at all.
    pub id: Option<String>,
    /// Claiming nick; `None` when absent or empty.
    pub claim: Option<String>,
    /// Job title; `""` when absent.
    pub title: String,
    /// Job status (`"claimed"`, `"open"`, `"done"`, ...); `""`
    /// when absent.
    pub status: String,
    /// Dependency ids, comma-separated or list form.
    pub deps: Vec<String>,
    /// File paths, comma-separated or list form, deduplicated
    /// in order.
    pub files: Vec<String>,
    /// Last known activity timestamp: the first present field in
    /// `last_progress`, `progress_at`, `note_ts`,
    /// `last_progress_at`, `claimed_at`. `None` when the job
    /// carries no timestamp at all — detectors never invent one.
    pub last_activity: Option<i64>,
    /// Lease expiry timestamp, if any.
    pub lease_until: Option<i64>,
    /// Lease duration in seconds, if any.
    pub lease: Option<i64>,
    /// Last heartbeat timestamp: `heartbeat_at`, else
    /// `last_heartbeat`, if any.
    pub heartbeat: Option<i64>,
    /// The dep's blocking note, when it is a non-empty string.
    pub note: Option<String>,
    /// Branch name on a done job, when non-empty.
    pub branch: Option<String>,
    /// Attempt count; unparseable or missing values yield 0
    /// (Python `_as_int(..., 0)`).
    pub attempts: i64,
    /// Attempt budget; `None` when absent or unparseable — a job
    /// with no budget yields no attempt alert at any count.
    pub max_attempts: Option<i64>,
}

/// One message in a snapshot: either a raw bus string or a
/// brief-shaped dict with `text` and an optional `ts`.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Message {
    /// Body text (`""` for malformed messages).
    pub text: String,
    /// Timestamp in seconds, via `_as_int` semantics, if any.
    pub ts: Option<i64>,
}

/// One OS-079-shaped budget entry from a snapshot.
#[derive(Clone, Debug, Default)]
pub struct BudgetEntry {
    /// Lane name (non-empty; entries without one are dropped).
    pub lane: String,
    /// Spent, when it is a usable integer (ints only, no bools).
    pub spent: Option<i64>,
    /// Cap, when it is a usable integer (ints only, no bools).
    pub cap: Option<i64>,
}

/// The WDG-017 tick-window record carried on a capped snapshot.
#[derive(Clone, Debug, Default)]
pub struct TickWindow {
    /// Maximum messages kept.
    pub max_messages: usize,
    /// Page size used for the walk.
    pub page_size: i64,
    /// Messages kept after the cap.
    pub messages_kept: usize,
    /// Messages dropped, accumulating across repeated caps.
    pub messages_dropped: i64,
}

/// One snapshot for a tick, in the shape `intel/brief.py`
/// documents (`messages`, `jobs`, `presence`, `caps`, `alerts`).
/// Missing sections are empty, never invented; see
/// [`Snapshot::from_value`] for the loose-dict conversion rules.
#[derive(Clone, Debug, Default)]
pub struct Snapshot {
    /// Job rows.
    pub jobs: Vec<Job>,
    /// Nicks currently present.
    pub presence: Vec<String>,
    /// Caps registry keys (values are irrelevant to detectors).
    pub caps: Vec<String>,
    /// Messages, oldest first (ingest order).
    pub messages: Vec<Message>,
    /// Budget entries.
    pub budgets: Vec<BudgetEntry>,
    /// Room name, when it is a non-empty string.
    pub room: Option<String>,
    /// Raw `server_time` field, if present (parsed by
    /// [`resolve_tick_now`]; malformed values fall back to the
    /// wall clock).
    pub server_time: Option<Value>,
    /// Prior tick-window record, if any (drop counts accumulate).
    pub tick_window: Option<TickWindow>,
}

fn parse_deps(value: Option<&Value>) -> Vec<String> {
    match value {
        Some(Value::List(items)) => items
            .iter()
            .filter_map(|d| d.py_str())
            .map(|d| d.trim().to_string())
            .filter(|d| !d.is_empty())
            .collect(),
        Some(Value::Str(s)) => s
            .split(',')
            .map(|d| d.trim().to_string())
            .filter(|d| !d.is_empty())
            .collect(),
        _ => Vec::new(),
    }
}

fn parse_files(value: Option<&Value>) -> Vec<String> {
    let raw = parse_deps(value);
    let mut seen = HashSet::new();
    let mut out = Vec::new();
    for path in raw {
        if seen.insert(path.clone()) {
            out.push(path);
        }
    }
    out
}

fn job_from_value(value: &Value) -> Option<Job> {
    let map = match value {
        Value::Map(_) => value,
        _ => return None,
    };
    let last_activity = ["last_progress", "progress_at", "note_ts", "last_progress_at", "claimed_at"]
        .iter()
        .find_map(|field| map.get(field).and_then(|v| v.as_py_int()));
    let heartbeat = ["heartbeat_at", "last_heartbeat"]
        .iter()
        .find_map(|field| map.get(field).and_then(|v| v.as_py_int()));
    Some(Job {
        id: map.get("id").and_then(|v| match v {
            Value::Null => None,
            other => other.py_str(),
        }),
        claim: map.get("claim").and_then(|v| v.as_nonempty_str()),
        title: map
            .get("title")
            .and_then(|v| match v {
                Value::Str(s) => Some(s.clone()),
                _ => None,
            })
            .unwrap_or_default(),
        status: map
            .get("status")
            .and_then(|v| match v {
                Value::Str(s) => Some(s.clone()),
                _ => None,
            })
            .unwrap_or_default(),
        deps: parse_deps(map.get("deps")),
        files: parse_files(map.get("files")),
        last_activity,
        lease_until: map.get("lease_until").and_then(|v| v.as_py_int()),
        lease: map.get("lease").and_then(|v| v.as_py_int()),
        heartbeat,
        note: map.get("note").and_then(|v| v.as_nonempty_str()),
        branch: map.get("branch").and_then(|v| v.as_nonempty_str()),
        attempts: map
            .get("attempts")
            .and_then(|v| v.as_strict_int())
            .unwrap_or(0),
        max_attempts: map.get("max_attempts").and_then(|v| v.as_strict_int()),
    })
}

fn message_from_value(value: &Value) -> Message {
    match value {
        Value::Str(s) => Message {
            text: s.clone(),
            ts: None,
        },
        Value::Map(_) => Message {
            text: match value.get("text") {
                Some(Value::Str(s)) => s.clone(),
                _ => String::new(),
            },
            ts: value.get("ts").and_then(|v| v.as_strict_int()),
        },
        _ => Message::default(),
    }
}

impl Snapshot {
    /// Convert a loose snapshot value (e.g. parsed JSON) into a
    /// typed snapshot, applying the Python detectors' tolerance:
    /// a non-dict snapshot is empty; a non-dict `caps`, a
    /// non-list `jobs`/`messages`/`budgets` section yields an
    /// empty section, never a crash.
    pub fn from_value(value: &Value) -> Snapshot {
        let map = match value {
            Value::Map(_) => value,
            _ => return Snapshot::default(),
        };
        let jobs = match map.get("jobs") {
            Some(Value::List(items)) => items.iter().filter_map(job_from_value).collect(),
            _ => Vec::new(),
        };
        let presence = match map.get("presence") {
            Some(Value::List(items)) => items
                .iter()
                .filter_map(|v| match v {
                    Value::Str(s) => Some(s.clone()),
                    _ => None,
                })
                .collect(),
            _ => Vec::new(),
        };
        let caps = match map.get("caps") {
            Some(Value::Map(entries)) => entries.iter().map(|(k, _)| k.clone()).collect(),
            _ => Vec::new(),
        };
        let messages = match map.get("messages") {
            Some(Value::List(items)) => items.iter().map(message_from_value).collect(),
            _ => Vec::new(),
        };
        let budgets = match map.get("budgets") {
            Some(Value::List(items)) => items
                .iter()
                .filter_map(|entry| {
                    let lane = entry.get("lane").and_then(|v| v.as_nonempty_str())?;
                    let usable = |v: Option<&Value>| match v {
                        Some(Value::Int(i)) => Some(*i),
                        _ => None,
                    };
                    Some(BudgetEntry {
                        lane,
                        spent: usable(entry.get("spent")),
                        cap: usable(entry.get("cap")),
                    })
                })
                .collect(),
            _ => Vec::new(),
        };
        let room = map.get("room").and_then(|v| v.as_nonempty_str());
        let server_time = map.get("server_time").cloned();
        let tick_window = match map.get("tick_window") {
            Some(Value::Map(_)) => {
                let dropped = map
                    .get("tick_window")
                    .and_then(|w| w.get("messages_dropped"))
                    .and_then(|v| v.as_py_int());
                dropped.map(|d| TickWindow {
                    messages_dropped: d,
                    ..TickWindow::default()
                })
            }
            _ => None,
        };
        Snapshot {
            jobs,
            presence,
            caps,
            messages,
            budgets,
            room,
            server_time,
            tick_window,
        }
    }

    /// Parse a snapshot JSON document into a typed snapshot.
    /// Returns an error string for malformed JSON or a
    /// non-object document (the CLI maps this to exit 1).
    pub fn from_json_text(text: &str) -> Result<Snapshot, String> {
        let value = parse_json(text)?;
        match value {
            Value::Map(_) => Ok(Snapshot::from_value(&value)),
            _ => Err("snapshot file must hold a JSON object".to_string()),
        }
    }
}

// ---------------------------------------------------------------------------
// Alert records
// ---------------------------------------------------------------------------

/// One alert / info record produced by a detector. Fields that a
/// detector kind does not use stay `None` (or empty); this mirrors
/// the Python dicts, where each kind carries only its own fields
/// plus the shared `explanation`, `suggested_fix`, `dedupe_key`,
/// and `created_at`.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Alert {
    /// Alert kind, e.g. `"presence-stall"`.
    pub kind: String,
    /// Severity: `"critical"`, `"warning"`, or `"info"`.
    pub severity: String,
    /// Worker nick, when the record is about a worker.
    pub nick: Option<String>,
    /// Job id, when the record is about a job.
    pub job: Option<String>,
    /// Job title, `""` when absent.
    pub job_title: String,
    /// Dependency id (dead-dep / missing-dep).
    pub dep: Option<String>,
    /// Dependency status (dead-dep).
    pub dep_status: Option<String>,
    /// Blocking reason, verbatim note or dep status (dead-dep).
    pub blocking_reason: Option<String>,
    /// The other job in a file collision.
    pub other_job: Option<String>,
    /// The other job's title in a file collision.
    pub other_title: String,
    /// Shared path in a file collision.
    pub shared_path: Option<String>,
    /// `"done"` for a claimed-vs-done-branch collision.
    pub other_status: Option<String>,
    /// Unmerged branch name (claimed-vs-done-branch collision).
    pub branch: Option<String>,
    /// Lane name (budget-warning).
    pub lane: Option<String>,
    /// Budget spent (budget-warning).
    pub spent: Option<i64>,
    /// Budget cap (budget-warning).
    pub cap: Option<i64>,
    /// Budget remaining, `cap - spent` (budget-warning).
    pub remaining: Option<i64>,
    /// Attempt count (attempt kinds).
    pub attempts: Option<i64>,
    /// Attempt budget (attempt kinds).
    pub max_attempts: Option<i64>,
    /// Attempts remaining (attempt kinds).
    pub attempts_remaining: Option<i64>,
    /// Last-progress age in seconds (stall kinds, silent-room).
    pub last_progress_age_seconds: Option<i64>,
    /// Last-progress age in minutes (stall kinds, silent-room).
    pub last_progress_age_minutes: Option<i64>,
    /// Seconds to lease expiry (lease-risk).
    pub seconds_to_expiry: Option<i64>,
    /// Minutes to lease expiry (lease-risk).
    pub minutes_to_expiry: Option<i64>,
    /// Last-heartbeat age in seconds (lease-risk).
    pub last_heartbeat_age_seconds: Option<i64>,
    /// Claimed job ids (silent-room).
    pub claimed_jobs: Vec<String>,
    /// Claimed job count (silent-room).
    pub claimed_count: Option<usize>,
    /// Last-message age in seconds (silent-room).
    pub last_message_age_seconds: Option<i64>,
    /// Last-message age in minutes (silent-room).
    pub last_message_age_minutes: Option<i64>,
    /// Refusal verdict, `"BAD"` or `"EXPIRED"` (rejected-dispatch).
    pub verdict: Option<String>,
    /// Poster nick from the refusal line, `"?"` when absent.
    pub signed_by: Option<String>,
    /// Refuser nick from the refusal line, `"?"` when absent.
    pub rejected_by: Option<String>,
    /// Subjects (system-failure records).
    pub subjects: Vec<String>,
    /// Unit name (system-failure records).
    pub unit: Option<String>,
    /// `true` for system-failure records; `false` otherwise.
    pub system_alert: bool,
    /// Number of failures grouped into one system alert.
    pub failure_count: Option<usize>,
    /// First failure message, verbatim (system-failure).
    pub journal_message: Option<String>,
    /// Plain-English explanation (template text, or polished
    /// text when a polish client is supplied to a tick).
    pub explanation: String,
    /// Suggested fix (never polished).
    pub suggested_fix: String,
    /// Dedupe key; also the store id when no explicit id exists.
    pub dedupe_key: String,
    /// Tick timestamp the record was created at.
    pub created_at: i64,
    /// Downtime in seconds, when known (worker-restart notes).
    pub downtime_seconds: Option<i64>,
    /// Room, when the record carries one (silent-room).
    pub room: Option<String>,
    /// Explicit id, when the record carries one (announcements
    /// prefer it over the dedupe key).
    pub id: Option<String>,
}

fn base_alert(kind: &str, severity: &str, created_at: i64) -> Alert {
    Alert {
        kind: kind.to_string(),
        severity: severity.to_string(),
        created_at,
        ..Alert::default()
    }
}

// ---------------------------------------------------------------------------
// Explanations (templates from os/intel/explanations.py, verbatim)
// ---------------------------------------------------------------------------

/// Render one explanation template, returning
/// `(explanation, suggested_fix)`. Field values are substituted
/// for `{name}` placeholders. Panics on an unknown template key —
/// exactly as Python `render` raises `ValueError` — and a tick
/// skips a detector that panics, so a bad key can never ship a
/// half-filled explanation.
pub fn render_explanation(template_key: &str, fields: &[(&str, String)]) -> (String, String) {
    let (explanation, suggested_fix) = match template_key {
        "presence-stall" => (
            "{nick} holds claimed job {job} but has been absent from presence for over {stall_minutes} minutes with no progress on it for {age_minutes} minutes.",
            "Check on {nick}; if the worker is gone, the lease sweep will requeue job {job} for another worker.",
        ),
        "progress-stall" => (
            "{nick} is present and holding claimed job {job}, but has made no progress on it for {age_minutes} minutes (over the {window_minutes}-minute window): the worker is alive, the work is stuck.",
            "Check what {nick} is stuck on for job {job}; if the work is blocked, the lease sweep will requeue it for another worker.",
        ),
        "lease-risk" => (
            "Claimed job {job} held by {nick} has its lease expiring in {minutes_to_expiry} minute(s) with no heartbeat in the last {quiet_minutes} minutes: renew it or the lease sweep will requeue the job.",
            "Have {nick} heartbeat job {job} to renew the lease, or let the sweep requeue it for another worker.",
        ),
        "dead-dep" => (
            "Job {job} cannot proceed: its dependency {dep} is {dep_status}.{blocking_note}",
            "Unblock or replace dependency {dep} (currently {dep_status}) so job {job} can proceed, or repost job {job} without that dependency.",
        ),
        "missing-dep" => (
            "Job {job} depends on job {dep}, which does not exist in the job index: the dependency was never posted, was deleted, or was mistyped.",
            "Repost job {job} without dependency {dep}, or post the missing job {dep} first, then re-check job {job}.",
        ),
        "file-collision" => (
            "Jobs {job} and {other_job} both touch {shared_path}: two workers editing the same file will collide at merge time.",
            "Coordinate jobs {job} and {other_job} before either finishes: split {shared_path} between them, or hold one job until the other merges.",
        ),
        "file-collision-done" => (
            "Claimed job {job} touches {shared_path}, which job {other_job} already finished on branch {branch}: the new claim risks redoing or clobbering finished work.",
            "Coordinate jobs {job} and {other_job} before either finishes: split {shared_path} between them, or hold one job until the other merges.",
        ),
        "attempt-warning" => (
            "Job {job} has used {attempts} of {max_attempts} attempts: one attempt left before the job goes failed-final instead of requeueing.",
            "Fix the blocker on job {job} now, or repost it with a larger attempt budget before the last attempt burns.",
        ),
        "attempt-exhaustion" => (
            "Job {job} has used {attempts} of {max_attempts} attempts: its attempt budget is spent and the job is failed-final, not requeued.",
            "Do not requeue job {job} as-is: fix the blocker, then repost it with a fresh attempt budget.",
        ),
        "silent-room" => (
            "The room has claimed jobs ({claimed_ids}) but no messages for {age_minutes} minutes (over the {window_minutes}-minute window): the crew may be stuck, or heads-down in deep work.",
            "No action required: this is informational only. If the crew is stuck, check on the claimed jobs; if they are heads-down, this record needs nothing.",
        ),
        "rejected-dispatch" => (
            "Job {job} was refused: its signature verdict is {verdict} (posted as {signed_by}, refused by {rejected_by}). The job stays open and unclaimed, and the refusal is the evidence, not an accusation against the refuser.",
            "Do not claim job {job} without verifying its signature against the crew keyring. If the poster is legitimate, repost the job with a fresh signature; if it is not, leave the job open and tell the crew who posted it.",
        ),
        "budget-warning" => (
            "The {lane} lane has spent {spent} of its {cap} budget ({remaining} remaining): it is past the {warn_percent}% warning threshold, so the next claims could hit the cap and stop the lane silently.",
            "Slow new {lane} claims, raise the lane cap, or let the lane finish its current work before posting more — at cap, new claims are held and the job stays open.",
        ),
        other => panic!("unknown explanation template: {}", other),
    };
    let fill = |template: &str| -> String {
        let mut out = template.to_string();
        for (name, value) in fields {
            out = out.replace(&format!("{{{}}}", name), value);
        }
        out
    };
    (fill(explanation), fill(suggested_fix))
}

fn s(value: &str) -> String {
    value.to_string()
}

fn n(value: i64) -> String {
    value.to_string()
}

/// The Spark polish client seat (WDG-012), mirroring the
/// duck-typed `client.complete(prompt, system=None,
/// lane_feature="watchdog")` call. Returns the polished text,
/// or `Err` on any client failure (the template then stands).
pub trait PolishClient {
    /// Rewrite `prompt`'s explanation for clarity. The prompt
    /// already forbids inventing facts.
    fn complete(&mut self, prompt: &str, lane_feature: &str) -> Result<String, String>;
}

/// WDG-012: optionally rewrite one explanation via Spark. With
/// no client, a raising client, or an empty/whitespace reply,
/// the template text comes back unchanged — the polish is an
/// optional clarity rewrite, never a replacement the alert
/// depends on.
pub fn polish_explanation(explanation: &str, client: Option<&mut dyn PolishClient>) -> String {
    let client = match client {
        Some(client) => client,
        None => return explanation.to_string(),
    };
    let prompt = format!(
        "Rewrite this alert explanation for clarity, in plain English, in one sentence. Do not add, remove, or change any facts, names, job ids, paths, or numbers: {}",
        explanation
    );
    let result = catch_unwind(AssertUnwindSafe(|| client.complete(&prompt, "watchdog")));
    let text = match result {
        Ok(Ok(text)) => text,
        _ => return explanation.to_string(),
    };
    if text.trim().is_empty() {
        explanation.to_string()
    } else {
        text.trim().to_string()
    }
}

// ---------------------------------------------------------------------------
// Detectors
// ---------------------------------------------------------------------------

/// A detector: `fn(snapshot, now, thresholds) -> alerts`.
pub type DetectorFn = fn(&Snapshot, i64, &Thresholds) -> Vec<Alert>;

/// WDG-002: presence-stall detector. A nick in the caps registry,
/// absent from presence, holding a claimed job with no activity
/// for longer than `stall_minutes`, is stalled. One alert per
/// (nick, job) pair. Walk-on claimers are skipped (tracked by
/// [`detect_walk_on_workers`], not alerted).
pub fn detect_presence_stall(snapshot: &Snapshot, now: i64, thresholds: &Thresholds) -> Vec<Alert> {
    let caps: HashSet<&str> = snapshot.caps.iter().map(|c| c.as_str()).collect();
    let present: HashSet<&str> = snapshot.presence.iter().map(|p| p.as_str()).collect();
    let threshold = thresholds.stall_minutes * 60;
    let mut alerts = Vec::new();
    for job in &snapshot.jobs {
        if job.status != "claimed" {
            continue;
        }
        let nick = match &job.claim {
            Some(nick) => nick,
            None => continue,
        };
        if !caps.contains(nick.as_str()) || present.contains(nick.as_str()) {
            continue;
        }
        let last = match job.last_activity {
            Some(last) => last,
            None => continue,
        };
        let age = now - last;
        if age <= threshold {
            continue;
        }
        let job_id = job.id.clone().unwrap_or_default();
        let (explanation, suggested_fix) = render_explanation(
            "presence-stall",
            &[
                ("nick", s(nick)),
                ("job", s(&job_id)),
                ("stall_minutes", n(thresholds.stall_minutes)),
                ("age_minutes", n(age / 60)),
            ],
        );
        let mut alert = base_alert("presence-stall", "critical", now);
        alert.nick = Some(nick.clone());
        alert.job = Some(job_id.clone());
        alert.job_title = job.title.clone();
        alert.last_progress_age_seconds = Some(age);
        alert.last_progress_age_minutes = Some(age / 60);
        alert.explanation = explanation;
        alert.suggested_fix = suggested_fix;
        alert.dedupe_key = format!("presence-stall:{}:{}", nick, job_id);
        alerts.push(alert);
    }
    alerts
}

/// WDG-003: progress-stall detector. A nick in the caps registry
/// that IS present while holding a claimed job with no activity
/// for longer than `progress_stall_minutes` is stuck, not gone.
/// One alert per (nick, job) pair. Distinct from presence-stall
/// by construction: that fires only when absent, this only when
/// present.
pub fn detect_progress_stall(snapshot: &Snapshot, now: i64, thresholds: &Thresholds) -> Vec<Alert> {
    let caps: HashSet<&str> = snapshot.caps.iter().map(|c| c.as_str()).collect();
    let present: HashSet<&str> = snapshot.presence.iter().map(|p| p.as_str()).collect();
    let threshold = thresholds.progress_stall_minutes * 60;
    let mut alerts = Vec::new();
    for job in &snapshot.jobs {
        if job.status != "claimed" {
            continue;
        }
        let nick = match &job.claim {
            Some(nick) => nick,
            None => continue,
        };
        if !caps.contains(nick.as_str()) || !present.contains(nick.as_str()) {
            continue;
        }
        let last = match job.last_activity {
            Some(last) => last,
            None => continue,
        };
        let age = now - last;
        if age <= threshold {
            continue;
        }
        let job_id = job.id.clone().unwrap_or_default();
        let (explanation, suggested_fix) = render_explanation(
            "progress-stall",
            &[
                ("nick", s(nick)),
                ("job", s(&job_id)),
                ("age_minutes", n(age / 60)),
                ("window_minutes", n(thresholds.progress_stall_minutes)),
            ],
        );
        let mut alert = base_alert("progress-stall", "critical", now);
        alert.nick = Some(nick.clone());
        alert.job = Some(job_id.clone());
        alert.job_title = job.title.clone();
        alert.last_progress_age_seconds = Some(age);
        alert.last_progress_age_minutes = Some(age / 60);
        alert.explanation = explanation;
        alert.suggested_fix = suggested_fix;
        alert.dedupe_key = format!("progress-stall:{}:{}", nick, job_id);
        alerts.push(alert);
    }
    alerts
}

/// A walk-on tracking record (WDG-025): a claimed job whose
/// claimer was never in the caps registry. Not an alert.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct WalkOnRecord {
    /// Always `"walk-on-worker"`.
    pub kind: String,
    /// Claiming nick.
    pub nick: String,
    /// Job id.
    pub job: String,
    /// Job title.
    pub job_title: String,
    /// Last-activity age in seconds, when the job has a timestamp.
    pub last_progress_age_seconds: Option<i64>,
    /// Last-activity age in minutes, when the job has a timestamp.
    pub last_progress_age_minutes: Option<i64>,
    /// Always `"jobs"`.
    pub tracked_from: String,
    /// Tick timestamp.
    pub created_at: i64,
}

/// WDG-025: walk-on worker tracking records. A claimed job whose
/// claimer was never in the caps registry yields one record
/// naming nick, job, and last-activity age, from jobs data alone.
/// Not a detector, not registered in [`DETECTORS`], and `tick`
/// never emits it. A job with no timestamp still yields a
/// record, with `None` ages. Malformed sections yield nothing.
pub fn detect_walk_on_workers(snapshot: &Snapshot, now: i64) -> Vec<WalkOnRecord> {
    let caps: HashSet<&str> = snapshot.caps.iter().map(|c| c.as_str()).collect();
    let mut records = Vec::new();
    for job in &snapshot.jobs {
        if job.status != "claimed" {
            continue;
        }
        let nick = match &job.claim {
            Some(nick) => nick,
            None => continue,
        };
        if caps.contains(nick.as_str()) {
            continue;
        }
        let age = job.last_activity.map(|last| now - last);
        records.push(WalkOnRecord {
            kind: "walk-on-worker".to_string(),
            nick: nick.clone(),
            job: job.id.clone().unwrap_or_default(),
            job_title: job.title.clone(),
            last_progress_age_seconds: age,
            last_progress_age_minutes: age.map(|a| a / 60),
            tracked_from: "jobs".to_string(),
            created_at: now,
        });
    }
    records
}

/// WDG-004: lease-risk detector. A claimed job whose lease
/// expires within `lease_risk_window_minutes` and with no
/// heartbeat in the last `lease_risk_quiet_minutes` minutes gets
/// a warning before expiry. Severity warning, not critical: the
/// job is not lost yet, just about to be. Caps membership is not
/// required: a walk-on worker's expiring lease warns too. An
/// already-expired lease yields nothing (that is the sweep's
/// job), and a job with no `lease_until` yields nothing.
pub fn detect_lease_risk(snapshot: &Snapshot, now: i64, thresholds: &Thresholds) -> Vec<Alert> {
    let window = thresholds.lease_risk_window_minutes * 60;
    let quiet = thresholds.lease_risk_quiet_minutes * 60;
    let mut alerts = Vec::new();
    for job in &snapshot.jobs {
        if job.status != "claimed" {
            continue;
        }
        let lease_until = match job.lease_until {
            Some(until) => until,
            None => continue,
        };
        let seconds_to_expiry = lease_until - now;
        if seconds_to_expiry <= 0 || seconds_to_expiry > window {
            continue;
        }
        let heartbeat = match job.heartbeat {
            Some(heartbeat) => heartbeat,
            None => lease_until - job.lease.unwrap_or(LEASE_DEFAULT_SECONDS),
        };
        if now - heartbeat < quiet {
            continue;
        }
        let nick = job.claim.clone().unwrap_or_default();
        let job_id = job.id.clone().unwrap_or_default();
        let (explanation, suggested_fix) = render_explanation(
            "lease-risk",
            &[
                ("job", s(&job_id)),
                ("nick", s(&nick)),
                ("minutes_to_expiry", n(seconds_to_expiry / 60)),
                ("quiet_minutes", n(thresholds.lease_risk_quiet_minutes)),
            ],
        );
        let mut alert = base_alert("lease-risk", "warning", now);
        alert.nick = Some(nick.clone());
        alert.job = Some(job_id.clone());
        alert.job_title = job.title.clone();
        alert.seconds_to_expiry = Some(seconds_to_expiry);
        alert.minutes_to_expiry = Some(seconds_to_expiry / 60);
        alert.last_heartbeat_age_seconds = Some(now - heartbeat);
        alert.explanation = explanation;
        alert.suggested_fix = suggested_fix;
        alert.dedupe_key = format!("lease-risk:{}:{}", nick, job_id);
        alerts.push(alert);
    }
    alerts
}

/// WDG-005: dead-dependency detector. An open or claimed job
/// whose dependency is blocked or failed-final cannot proceed.
/// One alert per (job, dep) pair, severity critical. The blocking
/// reason is the dep's note verbatim when it carries one, else
/// the dep's status. A dep that does not exist is WDG-006's
/// case, not this detector's.
pub fn detect_dead_dep(snapshot: &Snapshot, now: i64, _thresholds: &Thresholds) -> Vec<Alert> {
    let mut by_id: HashMap<&str, &Job> = HashMap::new();
    for job in &snapshot.jobs {
        if let Some(id) = &job.id {
            by_id.entry(id.as_str()).or_insert(job);
        }
    }
    let mut alerts = Vec::new();
    for job in &snapshot.jobs {
        if job.status != "open" && job.status != "claimed" {
            continue;
        }
        let job_id = job.id.clone().unwrap_or_default();
        for dep_id in &job.deps {
            let dep = match by_id.get(dep_id.as_str()) {
                Some(dep) => dep,
                None => continue,
            };
            if dep.status != "blocked" && dep.status != "failed-final" {
                continue;
            }
            let dep_status = dep.status.clone();
            let reason = match &dep.note {
                Some(note) => note.clone(),
                None => dep_status.clone(),
            };
            let blocking_note = match &dep.note {
                Some(note) => format!(" Blocking reason: {}", note),
                None => String::new(),
            };
            let (explanation, suggested_fix) = render_explanation(
                "dead-dep",
                &[
                    ("job", s(&job_id)),
                    ("dep", s(dep_id)),
                    ("dep_status", s(&dep_status)),
                    ("blocking_note", s(&blocking_note)),
                ],
            );
            let mut alert = base_alert("dead-dep", "critical", now);
            alert.nick = Some(job.claim.clone().unwrap_or_default());
            alert.job = Some(job_id.clone());
            alert.job_title = job.title.clone();
            alert.dep = Some(dep_id.clone());
            alert.dep_status = Some(dep_status);
            alert.blocking_reason = Some(reason);
            alert.explanation = explanation;
            alert.suggested_fix = suggested_fix;
            alert.dedupe_key = format!("dead-dep:{}:{}", job_id, dep_id);
            alerts.push(alert);
        }
    }
    alerts
}

/// WDG-006: missing-dependency detector. An open or claimed job
/// whose dependency id does not exist in the job index at all.
/// One alert per (job, dep) pair, severity critical. The
/// complement of WDG-005, which stays silent on missing deps.
pub fn detect_missing_dep(snapshot: &Snapshot, now: i64, _thresholds: &Thresholds) -> Vec<Alert> {
    let known: HashSet<&str> = snapshot
        .jobs
        .iter()
        .filter_map(|job| job.id.as_deref())
        .collect();
    let mut alerts = Vec::new();
    for job in &snapshot.jobs {
        if job.status != "open" && job.status != "claimed" {
            continue;
        }
        let job_id = job.id.clone().unwrap_or_default();
        for dep_id in &job.deps {
            if known.contains(dep_id.as_str()) {
                continue;
            }
            let (explanation, suggested_fix) = render_explanation(
                "missing-dep",
                &[("job", s(&job_id)), ("dep", s(dep_id))],
            );
            let mut alert = base_alert("missing-dep", "critical", now);
            alert.nick = Some(job.claim.clone().unwrap_or_default());
            alert.job = Some(job_id.clone());
            alert.job_title = job.title.clone();
            alert.dep = Some(dep_id.clone());
            alert.explanation = explanation;
            alert.suggested_fix = suggested_fix;
            alert.dedupe_key = format!("missing-dep:{}:{}", job_id, dep_id);
            alerts.push(alert);
        }
    }
    alerts
}

/// WDG-007: file-collision detector. Two claimed jobs whose
/// files overlap, or a claimed job overlapping a done-but-
/// unmerged branch's files (a done job that still carries a
/// branch name). One alert per (job pair, shared path),
/// severity critical. Open jobs are never scanned on either
/// side; a done job with no branch stays silent.
pub fn detect_file_collision(snapshot: &Snapshot, now: i64, _thresholds: &Thresholds) -> Vec<Alert> {
    let claimed: Vec<&Job> = snapshot
        .jobs
        .iter()
        .filter(|job| job.status == "claimed")
        .collect();
    let done_branches: Vec<&Job> = snapshot
        .jobs
        .iter()
        .filter(|job| job.status == "done" && job.branch.is_some())
        .collect();
    let mut alerts = Vec::new();
    let make_alert = |first: &Job,
                      second: &Job,
                      path: &str,
                      done: bool,
                      now: i64|
     -> Alert {
        let first_id = first.id.clone().unwrap_or_default();
        let second_id = second.id.clone().unwrap_or_default();
        let (explanation, suggested_fix) = if done {
            render_explanation(
                "file-collision-done",
                &[
                    ("job", s(&first_id)),
                    ("other_job", s(&second_id)),
                    ("shared_path", s(path)),
                    ("branch", s(second.branch.as_deref().unwrap_or(""))),
                ],
            )
        } else {
            render_explanation(
                "file-collision",
                &[
                    ("job", s(&first_id)),
                    ("other_job", s(&second_id)),
                    ("shared_path", s(path)),
                ],
            )
        };
        let mut alert = base_alert("file-collision", "critical", now);
        alert.nick = Some(first.claim.clone().unwrap_or_default());
        alert.job = Some(first_id.clone());
        alert.other_job = Some(second_id.clone());
        alert.job_title = first.title.clone();
        alert.other_title = second.title.clone();
        alert.shared_path = Some(path.to_string());
        alert.explanation = explanation;
        alert.suggested_fix = suggested_fix;
        alert.dedupe_key = format!("file-collision:{}:{}:{}", first_id, second_id, path);
        if done {
            alert.other_status = Some("done".to_string());
            alert.branch = second.branch.clone();
        }
        alert
    };
    for (i, first) in claimed.iter().enumerate() {
        if first.files.is_empty() {
            continue;
        }
        // A path listed twice on one job counts once
        // (Python _parse_files deduplicates per job).
        let mut first_seen: HashSet<&str> = HashSet::new();
        let first_files: Vec<&str> = first
            .files
            .iter()
            .map(|f| f.as_str())
            .filter(|f| first_seen.insert(*f))
            .collect();
        for second in &claimed[i + 1..] {
            let second_files: HashSet<&str> =
                second.files.iter().map(|f| f.as_str()).collect();
            for path in &first_files {
                if second_files.contains(*path) {
                    alerts.push(make_alert(first, second, path, false, now));
                }
            }
        }
        for done in &done_branches {
            let done_files: HashSet<&str> = done.files.iter().map(|f| f.as_str()).collect();
            for path in &first_files {
                if done_files.contains(*path) {
                    alerts.push(make_alert(first, done, path, true, now));
                }
            }
        }
    }
    alerts
}

/// WDG-008: attempt-exhaustion detector. One alert per job,
/// never both kinds for the same job in one tick:
/// `attempts == max_attempts - 1` yields a warning heads-up
/// (kind `attempt-warning`); `attempts >= max_attempts` yields
/// a critical alert (kind `attempt-exhaustion`). A job with no
/// budget yields nothing; a done job yields nothing. Open,
/// claimed, blocked, and failed-final jobs are scanned.
pub fn detect_attempt_exhaustion(snapshot: &Snapshot, now: i64, _thresholds: &Thresholds) -> Vec<Alert> {
    let mut alerts = Vec::new();
    for job in &snapshot.jobs {
        if !matches!(
            job.status.as_str(),
            "open" | "claimed" | "blocked" | "failed-final"
        ) {
            continue;
        }
        let max_attempts = match job.max_attempts {
            Some(max) => max,
            None => continue,
        };
        let attempts = job.attempts;
        let job_id = job.id.clone().unwrap_or_default();
        if attempts >= max_attempts {
            let (explanation, suggested_fix) = render_explanation(
                "attempt-exhaustion",
                &[
                    ("job", s(&job_id)),
                    ("attempts", n(attempts)),
                    ("max_attempts", n(max_attempts)),
                ],
            );
            let mut alert = base_alert("attempt-exhaustion", "critical", now);
            alert.nick = Some(job.claim.clone().unwrap_or_default());
            alert.job = Some(job_id.clone());
            alert.job_title = job.title.clone();
            alert.attempts = Some(attempts);
            alert.max_attempts = Some(max_attempts);
            alert.attempts_remaining = Some(0);
            alert.explanation = explanation;
            alert.suggested_fix = suggested_fix;
            alert.dedupe_key = format!("attempt-exhaustion:{}", job_id);
            alerts.push(alert);
        } else if attempts == max_attempts - 1 {
            let (explanation, suggested_fix) = render_explanation(
                "attempt-warning",
                &[
                    ("job", s(&job_id)),
                    ("attempts", n(attempts)),
                    ("max_attempts", n(max_attempts)),
                ],
            );
            let mut alert = base_alert("attempt-warning", "warning", now);
            alert.nick = Some(job.claim.clone().unwrap_or_default());
            alert.job = Some(job_id.clone());
            alert.job_title = job.title.clone();
            alert.attempts = Some(attempts);
            alert.max_attempts = Some(max_attempts);
            alert.attempts_remaining = Some(1);
            alert.explanation = explanation;
            alert.suggested_fix = suggested_fix;
            alert.dedupe_key = format!("attempt-warning:{}", job_id);
            alerts.push(alert);
        }
    }
    alerts
}

/// WDG-009: silent-room detector (informational, never an
/// alert). A room with claimed jobs but zero messages for
/// longer than `silent_room_minutes` yields exactly one
/// room-level record, severity `"info"`. Silence is measured
/// from the latest timestamped message; a snapshot with no
/// timestamped messages, or with no claimed jobs, yields no
/// record. Plain bus strings carry no timestamp and are
/// ignored for the silence clock.
pub fn detect_silent_room(snapshot: &Snapshot, now: i64, thresholds: &Thresholds) -> Vec<Alert> {
    let claimed: Vec<&Job> = snapshot
        .jobs
        .iter()
        .filter(|job| job.status == "claimed")
        .collect();
    if claimed.is_empty() {
        return Vec::new();
    }
    let mut last_ts: Option<i64> = None;
    let pages = paginate(&snapshot.messages, thresholds.tick_page_size)
        .unwrap_or_default();
    for page in pages {
        for message in page {
            if let Some(ts) = message.ts {
                last_ts = Some(match last_ts {
                    Some(prev) if prev >= ts => prev,
                    _ => ts,
                });
            }
        }
    }
    let last_ts = match last_ts {
        Some(ts) => ts,
        None => return Vec::new(),
    };
    let age = now - last_ts;
    if age <= thresholds.silent_room_minutes * 60 {
        return Vec::new();
    }
    let claimed_ids: Vec<String> = claimed
        .iter()
        .map(|job| job.id.clone().unwrap_or_default())
        .collect();
    let dedupe_key = match &snapshot.room {
        Some(room) => format!("silent-room:{}", room),
        None => "silent-room".to_string(),
    };
    let (explanation, suggested_fix) = render_explanation(
        "silent-room",
        &[
            ("claimed_ids", s(&claimed_ids.join(", "))),
            ("age_minutes", n(age / 60)),
            ("window_minutes", n(thresholds.silent_room_minutes)),
        ],
    );
    let mut record = base_alert("silent-room", "info", now);
    record.claimed_jobs = claimed_ids;
    record.claimed_count = Some(record.claimed_jobs.len());
    record.last_message_age_seconds = Some(age);
    record.last_message_age_minutes = Some(age / 60);
    record.explanation = explanation;
    record.suggested_fix = suggested_fix;
    record.dedupe_key = dedupe_key;
    record.room = snapshot.room.clone();
    vec![record]
}

/// INT-010: refused-dispatch detector. A worker's
/// `REJECTED:<job> <BAD|EXPIRED>` line becomes one critical
/// alert per (job, verdict) per tick; the same refusal
/// reappearing in the window does not double-alert. The
/// detector verifies nothing itself — it reports the refusal
/// the worker already computed.
pub fn detect_rejected_dispatch(snapshot: &Snapshot, now: i64, _thresholds: &Thresholds) -> Vec<Alert> {
    let mut seen: HashSet<String> = HashSet::new();
    let mut alerts = Vec::new();
    for message in &snapshot.messages {
        let text = &message.text;
        if text.is_empty() {
            continue;
        }
        for (job_id, verdict, signed_by, rejected_by) in scan_rejected_lines(text) {
            let key = format!("rejected-dispatch:{}:{}", job_id, verdict);
            if !seen.insert(key.clone()) {
                continue;
            }
            let signed = signed_by.unwrap_or_else(|| "?".to_string());
            let rejected = rejected_by.unwrap_or_else(|| "?".to_string());
            let (explanation, suggested_fix) = render_explanation(
                "rejected-dispatch",
                &[
                    ("job", s(&job_id)),
                    ("verdict", s(&verdict)),
                    ("signed_by", s(&signed)),
                    ("rejected_by", s(&rejected)),
                ],
            );
            let mut alert = base_alert("rejected-dispatch", "critical", now);
            alert.job = Some(job_id.clone());
            alert.verdict = Some(verdict);
            alert.signed_by = Some(signed);
            alert.rejected_by = Some(rejected);
            alert.explanation = explanation;
            alert.suggested_fix = suggested_fix;
            alert.dedupe_key = key;
            alerts.push(alert);
        }
    }
    alerts
}

/// Scan one message body for `REJECTED:` lines, mirroring the
/// Python regex `REJECTED:(\d+) (BAD|EXPIRED)\b(?:\s+signed_by=(\S+))?(?:\s+rejected_by=(\S+))?`.
/// Returns `(job_id, verdict, signed_by, rejected_by)` per match,
/// in message order.
fn scan_rejected_lines(text: &str) -> Vec<(String, String, Option<String>, Option<String>)> {
    let bytes = text.as_bytes();
    let mut out = Vec::new();
    let mut pos = 0usize;
    while pos < bytes.len() {
        let rest = &text[pos..];
        let found = match rest.find("REJECTED:") {
            Some(index) => pos + index,
            None => break,
        };
        let mut cursor = found + "REJECTED:".len();
        let digit_start = cursor;
        while cursor < bytes.len() && bytes[cursor].is_ascii_digit() {
            cursor += 1;
        }
        if cursor == digit_start {
            pos = found + 1;
            continue;
        }
        let job_id = text[digit_start..cursor].to_string();
        // Literal space, then BAD or EXPIRED, then a word boundary.
        if cursor >= bytes.len() || bytes[cursor] != b' ' {
            pos = found + 1;
            continue;
        }
        let after_space = cursor + 1;
        let verdict = if text[after_space..].starts_with("BAD") {
            "BAD"
        } else if text[after_space..].starts_with("EXPIRED") {
            "EXPIRED"
        } else {
            pos = found + 1;
            continue;
        };
        let verdict_end = after_space + verdict.len();
        let boundary_ok = match text[verdict_end..].chars().next() {
            None => true,
            Some(ch) => !(ch.is_ascii_alphanumeric() || ch == '_'),
        };
        if !boundary_ok {
            pos = found + 1;
            continue;
        }
        cursor = verdict_end;
        let mut signed_by: Option<String> = None;
        let mut rejected_by: Option<String> = None;
        loop {
            // Tentatively skip whitespace, then try each optional group.
            let mut ws = cursor;
            while ws < bytes.len() && (bytes[ws] as char).is_whitespace() {
                ws += 1;
            }
            if ws == cursor {
                break;
            }
            if signed_by.is_none() && text[ws..].starts_with("signed_by=") {
                let value_start = ws + "signed_by=".len();
                let mut value_end = value_start;
                while value_end < bytes.len() && !(bytes[value_end] as char).is_whitespace() {
                    value_end += 1;
                }
                signed_by = Some(text[value_start..value_end].to_string());
                cursor = value_end;
                continue;
            }
            if rejected_by.is_none() && text[ws..].starts_with("rejected_by=") {
                let value_start = ws + "rejected_by=".len();
                let mut value_end = value_start;
                while value_end < bytes.len() && !(bytes[value_end] as char).is_whitespace() {
                    value_end += 1;
                }
                rejected_by = Some(text[value_start..value_end].to_string());
                cursor = value_end;
                continue;
            }
            break;
        }
        out.push((job_id, verdict.to_string(), signed_by, rejected_by));
        pos = cursor.max(found + 1);
    }
    out
}

/// OS-085: budget-warning detector. A lane that has spent past
/// the warning threshold of its cap (but is below cap) gets a
/// warning alert. A lane at cap yields no warning here (the cap
/// hold is the louder signal). Entries without a usable cap are
/// unbudgeted and yield nothing. One alert per lane per tick;
/// a repeated lane name is collapsed to its first entry.
pub fn detect_budget_warning(snapshot: &Snapshot, now: i64, thresholds: &Thresholds) -> Vec<Alert> {
    let mut seen: HashSet<&str> = HashSet::new();
    let mut alerts = Vec::new();
    for entry in &snapshot.budgets {
        if !seen.insert(entry.lane.as_str()) {
            continue;
        }
        let (spent, cap) = match (entry.spent, entry.cap) {
            (Some(spent), Some(cap)) => (spent, cap),
            _ => continue,
        };
        if !at_warning(spent, cap, thresholds.budget_warn_percent) {
            continue;
        }
        let remaining = cap - spent;
        let (explanation, suggested_fix) = render_explanation(
            "budget-warning",
            &[
                ("lane", s(&entry.lane)),
                ("spent", n(spent)),
                ("cap", n(cap)),
                ("remaining", n(remaining)),
                ("warn_percent", n(thresholds.budget_warn_percent)),
            ],
        );
        let mut alert = base_alert("budget-warning", "warning", now);
        alert.lane = Some(entry.lane.clone());
        alert.spent = Some(spent);
        alert.cap = Some(cap);
        alert.remaining = Some(remaining);
        alert.explanation = explanation;
        alert.suggested_fix = suggested_fix;
        alert.dedupe_key = format!("budget-warning:{}", entry.lane);
        alerts.push(alert);
    }
    alerts
}

/// The OS-085 warning band, mirroring `budgets.at_warning`:
/// spent at or past `warn_percent`% of cap, but below cap.
/// Unusable figures (non-positive cap, negative spent) never warn.
pub fn at_warning(spent: i64, cap: i64, warn_percent: i64) -> bool {
    if cap <= 0 || spent < 0 {
        return false;
    }
    let ratio = spent as f64 / cap as f64;
    ratio >= warn_percent as f64 / 100.0 && spent < cap
}

/// Detector registry (WDG-002..WDG-009, plus INT-010's
/// rejected-dispatch and OS-085's budget-warning). The loop
/// never hardcodes a detector; it runs this list in order.
pub static DETECTORS: &[DetectorFn] = &[
    detect_presence_stall,
    detect_progress_stall,
    detect_lease_risk,
    detect_dead_dep,
    detect_missing_dep,
    detect_file_collision,
    detect_attempt_exhaustion,
    detect_silent_room,
    detect_rejected_dispatch,
    detect_budget_warning,
];

/// WDG-024: the canonical severity mapping, the single source
/// of truth the dashboard and the brief read.
pub const SEVERITY_BY_KIND: &[(&str, &str)] = &[
    ("presence-stall", "critical"),
    ("progress-stall", "critical"),
    ("lease-risk", "warning"),
    ("dead-dep", "critical"),
    ("missing-dep", "critical"),
    ("file-collision", "critical"),
    ("attempt-warning", "warning"),
    ("attempt-exhaustion", "critical"),
    ("silent-room", "info"),
    ("rejected-dispatch", "critical"),
    ("budget-warning", "warning"),
];

/// Look up a kind's canonical severity, or `None` for unknown kinds.
pub fn severity_by_kind(kind: &str) -> Option<&'static str> {
    SEVERITY_BY_KIND
        .iter()
        .find(|(k, _)| *k == kind)
        .map(|(_, severity)| *severity)
}

// ---------------------------------------------------------------------------
// Announcements, pagination, tick window, clock resolution, tick
// ---------------------------------------------------------------------------

/// WDG-015: one frozen-format announcement line for an alert:
/// `"ALERT:<id> <kind>: <explanation>"`, exactly one line
/// (embedded newlines are flattened to spaces). Only severity
/// `"critical"` announces; warnings, info records, unknown
/// severities, non-dicts (here: alerts without an id or dedupe
/// key) yield `None`. The id is the alert's id when present,
/// else its dedupe key.
pub fn format_announcement(alert: &Alert) -> Option<String> {
    if alert.severity != "critical" {
        return None;
    }
    let alert_id = match &alert.id {
        Some(id) if !id.is_empty() => id.clone(),
        _ => {
            if alert.dedupe_key.is_empty() {
                return None;
            }
            alert.dedupe_key.clone()
        }
    };
    let kind = if alert.kind.is_empty() {
        "alert".to_string()
    } else {
        alert.kind.clone()
    };
    let explanation = if alert.explanation.is_empty() {
        kind.clone()
    } else {
        alert.explanation.clone()
    };
    let line = format!("ALERT:{} {}: {}", alert_id, kind, explanation);
    let flattened = line.replace("\r\n", "\n");
    Some(
        flattened
            .split(|c| c == '\n' || c == '\r')
            .collect::<Vec<_>>()
            .join(" "),
    )
}

/// WDG-015: the announcement lines for an alert list. Every
/// critical alert yields exactly one line, in list order;
/// warnings and info records yield nothing.
pub fn announcements_for(alerts: &[Alert]) -> Vec<String> {
    alerts.iter().filter_map(format_announcement).collect()
}

/// WDG-017: yield successive pages of a sequence, oldest first.
/// Same shape as `digest.py`'s LRANGE loop: full pages, then a
/// short final page, order preserved. A non-positive page size
/// is a caller bug and returns an error rather than slurping
/// everything.
pub fn paginate<T: Clone>(items: &[T], page_size: i64) -> Result<Vec<Vec<T>>, String> {
    if page_size <= 0 {
        return Err("page_size must be a positive int".to_string());
    }
    let page_size = page_size as usize;
    let mut pages = Vec::new();
    let mut start = 0usize;
    while start < items.len() {
        let end = (start + page_size).min(items.len());
        pages.push(items[start..end].to_vec());
        start = end;
    }
    Ok(pages)
}

/// WDG-017: cap a snapshot's message window before a tick.
/// Returns a new snapshot whose messages are the newest
/// `max_messages` (default `tick_max_messages`), oldest dropped
/// first. The returned snapshot carries a `tick_window` record
/// `{max_messages, page_size, messages_kept, messages_dropped}`;
/// a second cap accumulates the earlier drop count instead of
/// resetting it. Jobs, presence, caps, and budgets pass through
/// unchanged: capping jobs could hide a stall or a collision.
pub fn cap_tick_snapshot(
    snapshot: &Snapshot,
    max_messages: Option<usize>,
    page_size: Option<i64>,
    thresholds: &Thresholds,
) -> Result<Snapshot, String> {
    let max_messages = max_messages.unwrap_or(thresholds.tick_max_messages);
    let page_size = page_size.unwrap_or(thresholds.tick_page_size);
    let pages = paginate(&snapshot.messages, page_size)?;
    let mut kept: VecDeque<Message> = VecDeque::new();
    for page in pages {
        for message in page {
            if max_messages == 0 {
                // A zero cap keeps nothing (deque maxlen 0).
            } else {
                if kept.len() == max_messages {
                    kept.pop_front();
                }
                kept.push_back(message);
            }
        }
    }
    let total = snapshot.messages.len();
    let mut dropped = total as i64 - kept.len() as i64;
    if let Some(prior) = &snapshot.tick_window {
        dropped += prior.messages_dropped;
    }
    let mut capped = snapshot.clone();
    capped.messages = kept.into_iter().collect();
    capped.tick_window = Some(TickWindow {
        max_messages,
        page_size,
        messages_kept: capped.messages.len(),
        messages_dropped: dropped,
    });
    Ok(capped)
}

/// Parse a Redis server timestamp off a snapshot, or `None`.
/// Accepted shapes, in order: an int/float epoch; a numeric
/// string; a two-element `[seconds, microseconds]` pair (Redis
/// TIME's literal shape — the sub-second part is dropped).
/// Anything else — a non-numeric string, a bool, a
/// wrong-length sequence — yields `None`, never an invented
/// timestamp.
pub fn parse_server_time(value: &Value) -> Option<i64> {
    match value {
        Value::Bool(_) => None,
        Value::Int(i) => Some(*i),
        Value::Float(f) if f.is_finite() => Some(*f as i64),
        Value::Str(s) => {
            let trimmed = s.trim();
            if trimmed.is_empty() {
                return None;
            }
            if let Ok(i) = trimmed.parse::<i64>() {
                return Some(i);
            }
            trimmed.parse::<f64>().ok().and_then(|f| {
                if f.is_finite() {
                    Some(f as i64)
                } else {
                    None
                }
            })
        }
        Value::List(items) if items.len() == 2 => {
            let seconds = parse_server_time(&items[0])?;
            let _microseconds = parse_server_time(&items[1])?;
            Some(seconds)
        }
        _ => None,
    }
}

/// The current wall-clock time in whole seconds.
pub fn wall_clock_now() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0)
}

/// WDG-026: the one "now" a tick computes ages from, with its
/// source: `"explicit"` (caller-passed `now`), `"server_time"`
/// (the snapshot's `server_time` field, when usable), or
/// `"wall_clock"` (local clock fallback). Precedence is fixed:
/// explicit beats server_time beats wall clock. A malformed
/// `server_time` is treated as absent, never as zero.
pub fn resolve_tick_now(snapshot: &Snapshot, now: Option<i64>) -> (i64, &'static str) {
    resolve_tick_now_with_clock(snapshot, now, wall_clock_now())
}

/// [`resolve_tick_now`] with an injected wall-clock value, for
/// tests (the Python suite patches `time.time` the same way).
pub fn resolve_tick_now_with_clock(
    snapshot: &Snapshot,
    now: Option<i64>,
    wall_clock: i64,
) -> (i64, &'static str) {
    if let Some(now) = now {
        return (now, "explicit");
    }
    if let Some(server_time) = &snapshot.server_time {
        if let Some(parsed) = parse_server_time(server_time) {
            return (parsed, "server_time");
        }
    }
    (wall_clock, "wall_clock")
}

/// WDG-001: evaluate one snapshot, return the alerts found.
/// Full-callback form: `emit` is called once per alert, in
/// detector order; `polish_client` (WDG-012) rewrites each
/// alert's explanation for clarity when supplied; `announce`
/// (WDG-015) receives one frozen-format line per critical alert;
/// `beat` (WDG-016) is called once per tick with the tick
/// timestamp, quiet ticks included. Never fails on a bad
/// detector: a panicking detector is skipped, because one
/// broken detector must not blind the rest of the loop. A
/// failing beat never fails a tick (swallowed). `max_messages`
/// (WDG-017) caps the message window before any detector runs;
/// jobs are never capped.
#[allow(clippy::too_many_arguments)]
pub fn tick_full(
    snapshot: &Snapshot,
    now: Option<i64>,
    thresholds: &Thresholds,
    detectors: &[DetectorFn],
    emit: Option<&mut dyn FnMut(&Alert)>,
    polish_client: Option<&mut dyn PolishClient>,
    announce: Option<&mut dyn FnMut(&str)>,
    beat: Option<&mut dyn FnMut(i64)>,
    max_messages: Option<usize>,
) -> Vec<Alert> {
    let (current, _source) = resolve_tick_now(snapshot, now);
    // The tick cap cannot fail here: page size comes from the
    // thresholds (always >= 1) and max_messages is a usize.
    let capped = cap_tick_snapshot(snapshot, max_messages, None, thresholds)
        .unwrap_or_else(|_| snapshot.clone());
    let mut alerts: Vec<Alert> = Vec::new();
    let mut emit = emit;
    let mut announce = announce;
    let mut polish_client = polish_client;
    for detector in detectors {
        let found = catch_unwind(AssertUnwindSafe(|| detector(&capped, current, thresholds)));
        let found = match found {
            Ok(found) => found,
            Err(_) => continue,
        };
        for mut alert in found {
            if let Some(client) = polish_client.as_deref_mut() {
                if !alert.explanation.is_empty() {
                    alert.explanation = polish_explanation(&alert.explanation, Some(client));
                }
            }
            if let Some(emit) = emit.as_deref_mut() {
                emit(&alert);
            }
            if let Some(announce) = announce.as_deref_mut() {
                if let Some(line) = format_announcement(&alert) {
                    announce(&line);
                }
            }
            alerts.push(alert);
        }
    }
    if let Some(beat) = beat {
        let _ = catch_unwind(AssertUnwindSafe(|| beat(current)));
    }
    alerts
}

/// WDG-001: evaluate one snapshot with the registered
/// detectors, default thresholds, and no callbacks. `now`
/// defaults to the resolved tick clock (explicit, else
/// `server_time`, else wall clock).
pub fn tick(snapshot: &Snapshot, now: Option<i64>) -> Vec<Alert> {
    let thresholds = Thresholds::default();
    tick_full(
        snapshot,
        now,
        &thresholds,
        DETECTORS,
        None,
        None,
        None,
        None,
        None,
    )
}

/// WDG-001 with explicit thresholds (the Rust equivalent of
/// reloading the Python thresholds module before a tick).
pub fn tick_with_thresholds(
    snapshot: &Snapshot,
    now: Option<i64>,
    thresholds: &Thresholds,
) -> Vec<Alert> {
    tick_full(
        snapshot,
        now,
        thresholds,
        DETECTORS,
        None,
        None,
        None,
        None,
        None,
    )
}

// ---------------------------------------------------------------------------
// OS-034 restart notes and OS-037 journal watch
// ---------------------------------------------------------------------------

/// OS-034: the watchdog's event note for a systemd-restarted
/// worker. Exactly an INFO record, never a stall alert: systemd
/// owns process death, the watchdog owns silent-but-alive
/// stalls. `downtime_seconds`, when known, rides along as
/// evidence and is named in the explanation; when unknown it
/// is omitted, never guessed. Returns an error when nick or
/// job id is missing (Python raises `ValueError`).
pub fn restart_event_note(
    nick: &str,
    job_id: &str,
    now: i64,
    downtime_seconds: Option<i64>,
) -> Result<Alert, String> {
    if nick.is_empty() || job_id.is_empty() {
        return Err("restart_event_note needs a nick and a job id".to_string());
    }
    let down = match downtime_seconds {
        None => "after a brief absence".to_string(),
        Some(seconds) => format!("after {}s down", seconds),
    };
    let explanation = format!(
        "Worker {} on job {} died and was restarted by systemd {}; no stall alert fired because the worker is back and progressing.",
        nick, job_id, down
    );
    let mut note = base_alert("worker-restart", "info", now);
    note.nick = Some(nick.to_string());
    note.job = Some(job_id.to_string());
    note.explanation = explanation;
    note.suggested_fix = "No action: systemd handled the death. Investigate only if restarts repeat."
        .to_string();
    note.dedupe_key = format!("worker-restart:{}:{}", nick, job_id);
    note.downtime_seconds = downtime_seconds;
    Ok(note)
}

/// Unit-name prefix that counts as a crew (relay) unit.
pub const JOURNAL_RELAY_UNIT_PREFIX: &str = "relay-";

/// Journald priorities at or below err (3) count as failures.
pub const JOURNAL_FAILURE_MAX_PRIORITY: i64 = 3;

/// One normalized journal entry: `(unit, message, priority)`.
#[derive(Clone, Debug, PartialEq)]
pub struct JournalEntry {
    /// Systemd unit name.
    pub unit: String,
    /// MESSAGE field.
    pub message: String,
    /// PRIORITY field, when it parses to an int.
    pub priority: Option<i64>,
}

fn journal_fields_from_value(value: &Value) -> Option<JournalEntry> {
    let unit = ["_SYSTEMD_UNIT", "SYSTEMD_UNIT", "unit"]
        .iter()
        .find_map(|key| value.get(key).and_then(|v| v.as_nonempty_str()))?;
    let message = match value.get("MESSAGE") {
        Some(Value::Null) | None => match value.get("message") {
            Some(v) => v.py_str().unwrap_or_default(),
            None => String::new(),
        },
        Some(v) => v.py_str().unwrap_or_default(),
    };
    let priority_raw = value.get("PRIORITY").or_else(|| value.get("priority"));
    let priority = match priority_raw {
        Some(Value::Bool(_)) => None,
        Some(Value::Int(i)) => Some(*i),
        Some(Value::Str(s)) => {
            let trimmed = s.trim();
            if trimmed.is_empty() {
                None
            } else {
                trimmed.parse::<i64>().ok()
            }
        }
        _ => None,
    };
    Some(JournalEntry {
        unit,
        message,
        priority,
    })
}

/// Normalize one journal entry to its fields. Accepts
/// journalctl -o json dicts (`_SYSTEMD_UNIT`, `MESSAGE`,
/// `PRIORITY`) and the plain-keyed equivalents, plus a JSON
/// string of either shape. Returns `None` for anything unusable
/// — a blank line, unparseable JSON, a non-dict, or an entry
/// with no unit — because an unattributed failure must never be
/// filed under an invented unit name.
pub fn journal_entry_fields(entry: &Value) -> Option<JournalEntry> {
    journal_fields_from_value(entry)
}

/// Normalize one journal entry given as a JSON string.
pub fn journal_entry_fields_from_text(text: &str) -> Option<JournalEntry> {
    let trimmed = text.trim();
    if trimmed.is_empty() {
        return None;
    }
    let value = parse_json(trimmed).ok()?;
    journal_fields_from_value(&value)
}

/// OS-037: is this journal entry a relay unit failure? Only
/// relay units count (unit name starting with `"relay-"`).
/// Within relay units, failure is either a systemd failure
/// message or an err-or-worse priority.
pub fn journal_entry_is_failure(entry: &JournalEntry) -> bool {
    if !entry.unit.starts_with(JOURNAL_RELAY_UNIT_PREFIX) {
        return false;
    }
    if let Some(priority) = entry.priority {
        if priority <= JOURNAL_FAILURE_MAX_PRIORITY {
            return true;
        }
    }
    let lower = entry.message.to_lowercase();
    lower.contains("failed with result")
        || lower.contains("main process exited")
        || lower.contains("failed to start")
        || lower.contains("entered failed state")
}

/// OS-037: is this raw journal entry (value or JSON text) a
/// relay unit failure? Unusable entries yield `false`.
pub fn journal_entry_is_failure_value(entry: &Value) -> bool {
    match journal_fields_from_value(entry) {
        Some(fields) => journal_entry_is_failure(&fields),
        None => false,
    }
}

/// Parse journalctl -o json output into normalized entries.
/// One JSON object per line; blank lines and unparseable lines
/// are skipped, never fatal. Entries with no unit are dropped.
pub fn parse_journal_entries(text: &str) -> Vec<JournalEntry> {
    let mut entries = Vec::new();
    for line in text.lines() {
        if let Some(fields) = journal_entry_fields_from_text(line) {
            entries.push(fields);
        }
    }
    entries
}

/// OS-037: relay unit failures -> one SYSTEM alert per unit.
/// Failures group by unit: a unit that fails, restarts, and
/// fails again in one window is one incident, not a storm —
/// the alert carries `failure_count`. The alert is a SYSTEM
/// record by construction: kind `"system-failure"`, subjects
/// `[unit]`, `system_alert` true, and no nick or job field at
/// all. The explanation quotes the first failure message
/// (truncated at 300 chars; the full text rides in
/// `journal_message`), and the suggested fix names
/// `journalctl -u` and an operator restart — the watchdog
/// never restarts a unit itself.
pub fn detect_journal_failures(entries: &[JournalEntry], now: i64) -> Vec<Alert> {
    let mut by_unit: HashMap<String, (String, usize)> = HashMap::new();
    let mut order: Vec<String> = Vec::new();
    for entry in entries {
        if !journal_entry_is_failure(entry) {
            continue;
        }
        if let Some((_, count)) = by_unit.get_mut(&entry.unit) {
            *count += 1;
        } else {
            by_unit.insert(entry.unit.clone(), (entry.message.clone(), 1));
            order.push(entry.unit.clone());
        }
    }
    let mut alerts = Vec::new();
    for unit in order {
        let (first, count) = by_unit.get(&unit).cloned().unwrap_or_default();
        let char_count = first.chars().count();
        let excerpt = if char_count <= 300 {
            first.clone()
        } else {
            let truncated: String = first.chars().take(297).collect();
            format!("{}...", truncated)
        };
        let explanation = if excerpt.is_empty() {
            format!("System unit {} failed (no message logged).", unit)
        } else {
            format!("System unit {} failed: {}", unit, excerpt)
        };
        let mut alert = base_alert("system-failure", "critical", now);
        alert.subjects = vec![unit.clone()];
        alert.unit = Some(unit.clone());
        alert.system_alert = true;
        alert.failure_count = Some(count);
        alert.journal_message = Some(first);
        alert.explanation = explanation;
        alert.suggested_fix = format!(
            "Check journalctl -u {} for the failure, then restart the unit; the watchdog reports unit failures but never restarts units itself.",
            unit
        );
        alert.dedupe_key = format!("system-failure:{}", unit);
        alerts.push(alert);
    }
    alerts
}

/// OS-037: one journal-watch loop iteration over journalctl
/// -o json text. Emits each alert through `emit` when given;
/// an emit failure for one alert must not hide the next unit's
/// failure, so emit panics are swallowed per alert. Returns the
/// alert list regardless.
pub fn journal_watch_tick_text(
    text: &str,
    now: Option<i64>,
    emit: Option<&mut dyn FnMut(&Alert)>,
) -> Vec<Alert> {
    let current = now.unwrap_or_else(wall_clock_now);
    journal_watch_tick_entries(&parse_journal_entries(text), current, emit)
}

/// OS-037: one journal-watch loop iteration over already
/// normalized entries.
pub fn journal_watch_tick_entries(
    entries: &[JournalEntry],
    now: i64,
    emit: Option<&mut dyn FnMut(&Alert)>,
) -> Vec<Alert> {
    let alerts = detect_journal_failures(entries, now);
    if let Some(emit) = emit {
        for alert in &alerts {
            let _ = catch_unwind(AssertUnwindSafe(|| emit(alert)));
        }
    }
    alerts
}

// ---------------------------------------------------------------------------
// Minimal JSON parser (std-only; the CLI reads snapshot files)
// ---------------------------------------------------------------------------

struct JsonParser {
    chars: Vec<char>,
    pos: usize,
}

impl JsonParser {
    fn new(text: &str) -> Self {
        JsonParser {
            chars: text.chars().collect(),
            pos: 0,
        }
    }

    fn skip_ws(&mut self) {
        while self.pos < self.chars.len() && self.chars[self.pos].is_whitespace() {
            self.pos += 1;
        }
    }

    fn peek(&self) -> Option<char> {
        self.chars.get(self.pos).copied()
    }

    fn parse_value(&mut self) -> Result<Value, String> {
        self.skip_ws();
        match self.peek() {
            Some('{') => self.parse_object(),
            Some('[') => self.parse_array(),
            Some('"') => Ok(Value::Str(self.parse_string()?)),
            Some('t') => self.parse_literal("true", Value::Bool(true)),
            Some('f') => self.parse_literal("false", Value::Bool(false)),
            Some('n') => self.parse_literal("null", Value::Null),
            Some(ch) if ch == '-' || ch.is_ascii_digit() => self.parse_number(),
            Some(ch) => Err(format!("unexpected character in JSON: {}", ch)),
            None => Err("unexpected end of JSON input".to_string()),
        }
    }

    fn parse_literal(&mut self, word: &str, value: Value) -> Result<Value, String> {
        for expected in word.chars() {
            if self.peek() != Some(expected) {
                return Err(format!("invalid JSON literal, expected {}", word));
            }
            self.pos += 1;
        }
        Ok(value)
    }

    fn parse_object(&mut self) -> Result<Value, String> {
        self.pos += 1; // '{'
        let mut entries = Vec::new();
        self.skip_ws();
        if self.peek() == Some('}') {
            self.pos += 1;
            return Ok(Value::Map(entries));
        }
        loop {
            self.skip_ws();
            if self.peek() != Some('"') {
                return Err("expected string key in JSON object".to_string());
            }
            let key = self.parse_string()?;
            self.skip_ws();
            if self.peek() != Some(':') {
                return Err("expected ':' in JSON object".to_string());
            }
            self.pos += 1;
            let value = self.parse_value()?;
            entries.push((key, value));
            self.skip_ws();
            match self.peek() {
                Some(',') => {
                    self.pos += 1;
                }
                Some('}') => {
                    self.pos += 1;
                    break;
                }
                _ => return Err("expected ',' or '}' in JSON object".to_string()),
            }
        }
        Ok(Value::Map(entries))
    }

    fn parse_array(&mut self) -> Result<Value, String> {
        self.pos += 1; // '['
        let mut items = Vec::new();
        self.skip_ws();
        if self.peek() == Some(']') {
            self.pos += 1;
            return Ok(Value::List(items));
        }
        loop {
            let value = self.parse_value()?;
            items.push(value);
            self.skip_ws();
            match self.peek() {
                Some(',') => {
                    self.pos += 1;
                }
                Some(']') => {
                    self.pos += 1;
                    break;
                }
                _ => return Err("expected ',' or ']' in JSON array".to_string()),
            }
        }
        Ok(Value::List(items))
    }

    fn parse_string(&mut self) -> Result<String, String> {
        self.pos += 1; // opening quote
        let mut out = String::new();
        loop {
            let ch = match self.peek() {
                Some(ch) => ch,
                None => return Err("unterminated JSON string".to_string()),
            };
            self.pos += 1;
            match ch {
                '"' => break,
                '\\' => {
                    let escape = match self.peek() {
                        Some(e) => e,
                        None => return Err("unterminated JSON escape".to_string()),
                    };
                    self.pos += 1;
                    match escape {
                        '"' => out.push('"'),
                        '\\' => out.push('\\'),
                        '/' => out.push('/'),
                        'b' => out.push('\u{0008}'),
                        'f' => out.push('\u{000C}'),
                        'n' => out.push('\n'),
                        'r' => out.push('\r'),
                        't' => out.push('\t'),
                        'u' => {
                            let code = self.parse_hex4()?;
                            if (0xD800..0xDC00).contains(&code) {
                                // High surrogate: expect \uXXXX low surrogate.
                                if self.peek() == Some('\\') {
                                    self.pos += 1;
                                    if self.peek() == Some('u') {
                                        self.pos += 1;
                                        let low = self.parse_hex4()?;
                                        let combined = 0x10000
                                            + (((code - 0xD800) as u32) << 10)
                                            + ((low - 0xDC00) as u32);
                                        out.push(
                                            char::from_u32(combined).unwrap_or('\u{FFFD}'),
                                        );
                                    } else {
                                        out.push('\u{FFFD}');
                                    }
                                } else {
                                    out.push('\u{FFFD}');
                                }
                            } else {
                                out.push(char::from_u32(code as u32).unwrap_or('\u{FFFD}'));
                            }
                        }
                        other => return Err(format!("invalid JSON escape: \\{}", other)),
                    }
                }
                other => out.push(other),
            }
        }
        Ok(out)
    }

    fn parse_hex4(&mut self) -> Result<u16, String> {
        let mut code: u16 = 0;
        for _ in 0..4 {
            let ch = match self.peek() {
                Some(ch) => ch,
                None => return Err("truncated \\u escape in JSON string".to_string()),
            };
            let digit = ch.to_digit(16).ok_or("invalid \\u escape in JSON string")?;
            code = code * 16 + digit as u16;
            self.pos += 1;
        }
        Ok(code)
    }

    fn parse_number(&mut self) -> Result<Value, String> {
        let start = self.pos;
        if self.peek() == Some('-') {
            self.pos += 1;
        }
        while matches!(self.peek(), Some(ch) if ch.is_ascii_digit()) {
            self.pos += 1;
        }
        let mut is_float = false;
        if self.peek() == Some('.') {
            is_float = true;
            self.pos += 1;
            while matches!(self.peek(), Some(ch) if ch.is_ascii_digit()) {
                self.pos += 1;
            }
        }
        if matches!(self.peek(), Some('e') | Some('E')) {
            is_float = true;
            self.pos += 1;
            if matches!(self.peek(), Some('+') | Some('-')) {
                self.pos += 1;
            }
            while matches!(self.peek(), Some(ch) if ch.is_ascii_digit()) {
                self.pos += 1;
            }
        }
        let text: String = self.chars[start..self.pos].iter().collect();
        if is_float {
            text.parse::<f64>()
                .map(Value::Float)
                .map_err(|_| format!("invalid JSON number: {}", text))
        } else {
            match text.parse::<i64>() {
                Ok(i) => Ok(Value::Int(i)),
                Err(_) => text
                    .parse::<f64>()
                    .map(Value::Float)
                    .map_err(|_| format!("invalid JSON number: {}", text)),
            }
        }
    }
}

/// Parse a JSON document into a [`Value`]. Used by the CLI for
/// snapshot files and by journal entry parsing.
pub fn parse_json(text: &str) -> Result<Value, String> {
    let mut parser = JsonParser::new(text);
    let value = parser.parse_value()?;
    parser.skip_ws();
    if parser.pos != parser.chars.len() {
        return Err("trailing characters after JSON document".to_string());
    }
    Ok(value)
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

/// Watchdog CLI: `--once` runs one tick, `--loop` repeats it.
///
/// `args` are the arguments *excluding* the program name (as
/// Python's `main(argv)` receives them). Output goes to `out`,
/// diagnostics to `err` (so tests can capture stdout exactly
/// as the Python suite does with `redirect_stdout`).
/// Returns a process exit code: 0 on a clean run, 1 when a
/// snapshot or journal file is unusable, 2 on a usage error
/// (neither `--once` nor `--loop`, unknown flags, bad numbers).
///
/// `--snapshot <file>` supplies the snapshot JSON; without it
/// the tick runs on an empty (quiet) snapshot. `--journal
/// <file>` supplies journalctl -o json lines for one OS-037
/// journal-watch iteration, reported alongside the snapshot
/// tick (stdout only, never a bus post). `--interval` sets the
/// loop pause in seconds; `--max-ticks` bounds a loop run.
/// `--announce` prints each critical alert's WDG-015 line to
/// stdout after the count (a drill view, not a bus post: this
/// CLI never posts anywhere). `--beat` is accepted, but in
/// this standalone module its callback is a no-op sink — the
/// real beat writer is the store module's `wd_self_beat` (see
/// the module docs' live-behavior boundary).
pub fn run_cli(args: &[String], out: &mut dyn Write, err: &mut dyn Write) -> i32 {
    let mut once = false;
    let mut loop_mode = false;
    let mut snapshot_path: Option<String> = None;
    let mut journal_path: Option<String> = None;
    let mut interval: f64 = 60.0;
    let mut max_ticks: Option<i64> = None;
    let mut announce = false;
    let mut beat_flag = false;
    let mut i = 0usize;
    while i < args.len() {
        let arg = args[i].as_str();
        let take_value = |i: &mut usize| -> Option<String> {
            *i += 1;
            args.get(*i).cloned()
        };
        match arg {
            "--once" => once = true,
            "--loop" => loop_mode = true,
            "--announce" => announce = true,
            "--beat" => beat_flag = true,
            "--snapshot" => match take_value(&mut i) {
                Some(v) => snapshot_path = Some(v),
                None => {
                    let _ = writeln!(err, "watchdog: --snapshot needs a value");
                    return 2;
                }
            },
            "--journal" => match take_value(&mut i) {
                Some(v) => journal_path = Some(v),
                None => {
                    let _ = writeln!(err, "watchdog: --journal needs a value");
                    return 2;
                }
            },
            "--interval" => match take_value(&mut i) {
                Some(v) => match v.parse::<f64>() {
                    Ok(parsed) => interval = parsed,
                    Err(_) => {
                        let _ = writeln!(err, "watchdog: bad --interval: {}", v);
                        return 2;
                    }
                },
                None => {
                    let _ = writeln!(err, "watchdog: --interval needs a value");
                    return 2;
                }
            },
            "--max-ticks" => match take_value(&mut i) {
                Some(v) => match v.parse::<i64>() {
                    Ok(parsed) => max_ticks = Some(parsed),
                    Err(_) => {
                        let _ = writeln!(err, "watchdog: bad --max-ticks: {}", v);
                        return 2;
                    }
                },
                None => {
                    let _ = writeln!(err, "watchdog: --max-ticks needs a value");
                    return 2;
                }
            },
            "--room" => {
                // Recorded, not read yet (live reading waits on FND-014).
                if take_value(&mut i).is_none() {
                    let _ = writeln!(err, "watchdog: --room needs a value");
                    return 2;
                }
            }
            other => {
                let _ = writeln!(err, "watchdog: unknown argument: {}", other);
                return 2;
            }
        }
        i += 1;
    }
    if !once && !loop_mode {
        let _ = writeln!(err, "watchdog needs --once or --loop");
        return 2;
    }
    let snapshot = match &snapshot_path {
        Some(path) => {
            let text = match std::fs::read_to_string(path) {
                Ok(text) => text,
                Err(exc) => {
                    let _ = writeln!(err, "watchdog: cannot load snapshot: {}", exc);
                    return 1;
                }
            };
            match Snapshot::from_json_text(&text) {
                Ok(snapshot) => snapshot,
                Err(exc) => {
                    let _ = writeln!(err, "watchdog: cannot load snapshot: {}", exc);
                    return 1;
                }
            }
        }
        None => Snapshot::default(),
    };
    let journal_text = match &journal_path {
        Some(path) => match std::fs::read_to_string(path) {
            Ok(text) => Some(text),
            Err(exc) => {
                let _ = writeln!(err, "watchdog: cannot load journal: {}", exc);
                return 1;
            }
        },
        None => None,
    };
    // Beat seam: a no-op sink here; the store module's
    // wd_self_beat plugs into this seat at assembly. The sink
    // is created fresh per tick so no borrow spans loop
    // iterations.
    let thresholds = Thresholds::default();
    let report = |alerts: &[Alert], out: &mut dyn Write| {
        let _ = writeln!(out, "watchdog: {} alert(s)", alerts.len());
        if announce {
            for line in announcements_for(alerts) {
                let _ = writeln!(out, "{}", line);
            }
        }
    };
    if once {
        let mut beat_sink = |_ts: i64| {};
        let beat: Option<&mut dyn FnMut(i64)> = if beat_flag {
            Some(&mut beat_sink)
        } else {
            None
        };
        let mut alerts = tick_full(
            &snapshot,
            None,
            &thresholds,
            DETECTORS,
            None,
            None,
            None,
            beat,
            None,
        );
        if let Some(text) = &journal_text {
            alerts.extend(journal_watch_tick_text(text, None, None));
        }
        report(&alerts, out);
        return 0;
    }
    let mut count: i64 = 0;
    loop {
        if let Some(max) = max_ticks {
            if count >= max {
                break;
            }
        }
        let mut beat_sink = |_ts: i64| {};
        let beat: Option<&mut dyn FnMut(i64)> = if beat_flag {
            Some(&mut beat_sink)
        } else {
            None
        };
        let alerts = tick_full(
            &snapshot,
            None,
            &thresholds,
            DETECTORS,
            None,
            None,
            None,
            beat,
            None,
        );
        report(&alerts, out);
        count += 1;
        if let Some(max) = max_ticks {
            if count >= max {
                break;
            }
        }
        if interval > 0.0 {
            std::thread::sleep(Duration::from_secs_f64(interval));
        }
    }
    0
}

// ---------------------------------------------------------------------------
// Tests — mirrors of os/tests/test_intel_watchdog.py, class by class.
// Test names reference the Python test they mirror. Classes whose
// subject is another module (intel/store.py writer, dedupe,
// lifecycle, history query, watchdog status line, brief rendering)
// are NOT mirrored here; they are named in the completion report
// as other-batch, except for two tick-half adaptations noted
// inline below (emit seat, dedupe-key stability).
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;
    use std::sync::atomic::{AtomicUsize, Ordering};

    fn th() -> Thresholds {
        Thresholds::default()
    }

    fn tick_at(snapshot: &Snapshot, now: i64) -> Vec<Alert> {
        tick_full(snapshot, Some(now), &th(), DETECTORS, None, None, None, None, None)
    }

    fn mk_job(id: &str, status: &str) -> Job {
        Job {
            id: Some(id.to_string()),
            status: status.to_string(),
            ..Job::default()
        }
    }

    fn claimed(id: &str, nick: &str, last_activity: i64) -> Job {
        Job {
            id: Some(id.to_string()),
            claim: Some(nick.to_string()),
            title: "demo job".to_string(),
            status: "claimed".to_string(),
            last_activity: Some(last_activity),
            ..Job::default()
        }
    }

    fn snap(jobs: Vec<Job>, presence: Vec<&str>, caps: Vec<&str>) -> Snapshot {
        Snapshot {
            jobs,
            presence: presence.iter().map(|s| s.to_string()).collect(),
            caps: caps.iter().map(|s| s.to_string()).collect(),
            ..Snapshot::default()
        }
    }

    fn msg(text: &str, ts: i64) -> Message {
        Message {
            text: text.to_string(),
            ts: Some(ts),
        }
    }

    fn raw_msg(text: &str) -> Message {
        Message {
            text: text.to_string(),
            ts: None,
        }
    }

    fn stall_snapshot() -> Snapshot {
        snap(vec![claimed("7", "pax", 9340)], vec!["hana"], vec!["pax"])
    }

    fn kinds_set(alerts: &[Alert]) -> HashSet<String> {
        alerts.iter().map(|a| a.kind.clone()).collect()
    }

    // ---- TickTest ----

    #[test]
    fn tick_test_quiet_snapshot_yields_zero_alerts() {
        let mut emitted: Vec<Alert> = Vec::new();
        let mut emit = |a: &Alert| emitted.push(a.clone());
        let got = tick_full(
            &Snapshot::default(),
            Some(1000),
            &th(),
            DETECTORS,
            Some(&mut emit as &mut dyn FnMut(&Alert)),
            None,
            None,
            None,
            None,
        );
        assert!(got.is_empty());
        assert!(emitted.is_empty());
    }

    #[test]
    fn tick_test_healthy_busy_snapshot_also_yields_zero_for_now() {
        let snapshot = Snapshot {
            jobs: vec![claimed("1", "pax", 900)],
            presence: vec!["pax".to_string()],
            caps: vec!["pax".to_string()],
            messages: vec![raw_msg("working on it")],
            ..Snapshot::default()
        };
        assert!(tick_at(&snapshot, 1000).is_empty());
    }

    #[test]
    fn tick_test_missing_sections_are_empty_not_an_error() {
        assert!(tick_at(&Snapshot::from_value(&Value::Null), 1000).is_empty());
        let value = Value::Map(vec![("jobs".to_string(), Value::Null)]);
        assert!(tick_at(&Snapshot::from_value(&value), 1000).is_empty());
    }

    fn boom_detector(_snapshot: &Snapshot, _now: i64, _th: &Thresholds) -> Vec<Alert> {
        panic!("detector blew up")
    }

    fn ok_detector(_snapshot: &Snapshot, _now: i64, _th: &Thresholds) -> Vec<Alert> {
        vec![Alert {
            kind: "test".to_string(),
            id: Some("t1".to_string()),
            ..Alert::default()
        }]
    }

    #[test]
    fn tick_test_a_crashing_detector_does_not_blind_the_loop() {
        let got = tick_full(
            &Snapshot::default(),
            Some(1000),
            &th(),
            &[boom_detector, ok_detector],
            None,
            None,
            None,
            None,
            None,
        );
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "test");
        assert_eq!(got[0].id.as_deref(), Some("t1"));
    }

    fn two_detector(_snapshot: &Snapshot, _now: i64, _th: &Thresholds) -> Vec<Alert> {
        vec![
            Alert {
                id: Some("a".to_string()),
                ..Alert::default()
            },
            Alert {
                id: Some("b".to_string()),
                ..Alert::default()
            },
        ]
    }

    #[test]
    fn tick_test_emit_receives_each_alert_in_order() {
        let mut seen: Vec<Alert> = Vec::new();
        let mut emit = |a: &Alert| seen.push(a.clone());
        let got = tick_full(
            &Snapshot::default(),
            Some(1000),
            &th(),
            &[two_detector],
            Some(&mut emit as &mut dyn FnMut(&Alert)),
            None,
            None,
            None,
            None,
        );
        assert_eq!(got.len(), 2);
        assert_eq!(seen, got);
    }

    // ---- CliTest ----

    static TMP_COUNTER: AtomicUsize = AtomicUsize::new(0);

    fn tmp_snapshot_file(name: &str, content: &str) -> std::path::PathBuf {
        let n = TMP_COUNTER.fetch_add(1, Ordering::SeqCst);
        let path = std::env::temp_dir().join(format!(
            "watchdog-test-{}-{}-{}.json",
            std::process::id(),
            name,
            n
        ));
        std::fs::write(&path, content).expect("write temp snapshot");
        path
    }

    fn run_cli_capture(args: &[&str]) -> (i32, String) {
        let owned: Vec<String> = args.iter().map(|s| s.to_string()).collect();
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        let code = run_cli(&owned, &mut out, &mut err);
        (code, String::from_utf8_lossy(&out).into_owned())
    }

    #[test]
    fn cli_test_once_on_quiet_fixture_exits_zero() {
        let path = tmp_snapshot_file("quiet", "{}");
        let (code, out) = run_cli_capture(&["--once", "--snapshot", path.to_str().unwrap()]);
        assert_eq!(code, 0);
        assert!(out.contains("0 alert(s)"), "out: {}", out);
        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn cli_test_once_without_snapshot_uses_quiet_snapshot() {
        let (code, out) = run_cli_capture(&["--once"]);
        assert_eq!(code, 0);
        assert!(out.contains("0 alert(s)"), "out: {}", out);
    }

    #[test]
    fn cli_test_once_with_bad_snapshot_file_exits_one() {
        let (code, _out) = run_cli_capture(&["--once", "--snapshot", "/nonexistent/snapshot.json"]);
        assert_eq!(code, 1);
    }

    #[test]
    fn cli_test_loop_runs_bounded_ticks_then_exits_zero() {
        let path = tmp_snapshot_file("loop", "{}");
        let (code, out) = run_cli_capture(&[
            "--loop",
            "--snapshot",
            path.to_str().unwrap(),
            "--interval",
            "0",
            "--max-ticks",
            "2",
        ]);
        assert_eq!(code, 0);
        assert_eq!(out.matches("0 alert(s)").count(), 2, "out: {}", out);
        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn cli_test_neither_mode_is_an_error() {
        let (code, _out) = run_cli_capture(&[]);
        assert_eq!(code, 2);
    }

    // ---- PresenceStallTest ----

    #[test]
    fn presence_stall_test_stall_fixture_yields_exactly_one_alert_naming_all() {
        let got = tick_at(&stall_snapshot(), 10000);
        assert_eq!(got.len(), 1);
        let alert = &got[0];
        assert_eq!(alert.kind, "presence-stall");
        assert_eq!(alert.nick.as_deref(), Some("pax"));
        assert_eq!(alert.job.as_deref(), Some("7"));
        assert_eq!(alert.last_progress_age_seconds, Some(660));
        assert_eq!(alert.last_progress_age_minutes, Some(11));
    }

    #[test]
    fn presence_stall_test_present_nick_with_idle_job_is_not_presence_stall() {
        let snapshot = snap(vec![claimed("7", "pax", 9340)], vec!["pax", "hana"], vec!["pax"]);
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "progress-stall");
        assert_eq!(got[0].nick.as_deref(), Some("pax"));
        assert_eq!(got[0].job.as_deref(), Some("7"));
    }

    #[test]
    fn presence_stall_test_fresh_claimed_job_is_not_a_stall() {
        let mut snapshot = stall_snapshot();
        snapshot.jobs[0].last_activity = Some(9900);
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn presence_stall_test_absent_nick_with_no_claimed_job_is_not_a_stall() {
        let mut snapshot = stall_snapshot();
        snapshot.jobs[0].status = "open".to_string();
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn presence_stall_test_walk_on_claimer_not_in_caps_is_not_presence_stall() {
        let snapshot = snap(vec![claimed("7", "pax", 9340)], vec!["hana"], vec!["hana"]);
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn presence_stall_test_job_with_no_timestamp_never_invents_an_age() {
        let mut snapshot = stall_snapshot();
        snapshot.jobs[0].last_activity = None;
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn presence_stall_test_explicit_progress_timestamp_beats_claim_time() {
        // last_activity already models the first-present-field
        // rule: a fresh progress timestamp (9950) means no stall
        // even though the claim itself is old.
        let mut snapshot = stall_snapshot();
        snapshot.jobs[0].last_activity = Some(9950);
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn presence_stall_test_cli_once_on_stall_fixture_reports_one_alert() {
        let path = tmp_snapshot_file(
            "stall",
            r#"{"jobs": [{"id": "7", "title": "demo job", "status": "claimed", "claim": "pax", "claimed_at": 9340}], "presence": ["hana"], "caps": {"pax": {"caps": "build"}}}"#,
        );
        let (code, out) = run_cli_capture(&["--once", "--snapshot", path.to_str().unwrap()]);
        assert_eq!(code, 0);
        assert!(out.contains("1 alert(s)"), "out: {}", out);
        let _ = std::fs::remove_file(&path);
    }

    // ---- ProgressStallTest ----

    fn progress_snapshot() -> Snapshot {
        snap(vec![claimed("7", "pax", 9340)], vec!["pax", "hana"], vec!["pax"])
    }

    #[test]
    fn progress_stall_test_heartbeat_but_no_progress_yields_exactly_one() {
        let got = tick_at(&progress_snapshot(), 10000);
        assert_eq!(got.len(), 1);
        let alert = &got[0];
        assert_eq!(alert.kind, "progress-stall");
        assert_ne!(alert.kind, "presence-stall");
        assert_eq!(alert.nick.as_deref(), Some("pax"));
        assert_eq!(alert.job.as_deref(), Some("7"));
        assert_eq!(alert.last_progress_age_seconds, Some(660));
        assert_eq!(alert.last_progress_age_minutes, Some(11));
        assert_eq!(alert.severity, "critical");
        assert_eq!(alert.dedupe_key, "progress-stall:pax:7");
    }

    #[test]
    fn progress_stall_test_absent_nick_yields_presence_stall_not_progress_stall() {
        let snapshot = snap(vec![claimed("7", "pax", 9340)], vec!["hana"], vec!["pax"]);
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "presence-stall");
    }

    #[test]
    fn progress_stall_test_fresh_progress_is_not_a_stall() {
        let mut snapshot = progress_snapshot();
        snapshot.jobs[0].last_activity = Some(9900);
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn progress_stall_test_old_claim_with_no_progress_note_is_a_stall() {
        // Claim time counts as last activity: claimed 11 min ago
        // with no progress note since is stuck work.
        let got = tick_at(&progress_snapshot(), 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "progress-stall");
    }

    #[test]
    fn progress_stall_test_job_with_no_timestamp_never_invents_an_age() {
        let mut snapshot = progress_snapshot();
        snapshot.jobs[0].last_activity = None;
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn progress_stall_test_unclaimed_job_is_not_a_stall() {
        let mut snapshot = progress_snapshot();
        snapshot.jobs[0].status = "open".to_string();
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn progress_stall_test_walk_on_claimer_not_in_caps_is_not_progress_stall() {
        let snapshot = snap(vec![claimed("7", "pax", 9340)], vec!["pax", "hana"], vec!["hana"]);
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn progress_stall_test_one_alert_per_job_not_per_detector() {
        let mut snapshot = progress_snapshot();
        let mut second = claimed("8", "pax", 9300);
        second.title = "second job".to_string();
        snapshot.jobs.push(second);
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 2);
        let jobs: HashSet<&str> = got.iter().filter_map(|a| a.job.as_deref()).collect();
        assert_eq!(jobs, HashSet::from(["7", "8"]));
        assert!(got.iter().all(|a| a.kind == "progress-stall"));
    }

    // ---- LeaseRiskTest ----

    fn lease_snapshot(lease_until: i64, extra: impl FnOnce(&mut Job)) -> Snapshot {
        let mut job = claimed("9", "pax", 9900);
        job.title = "lease job".to_string();
        job.lease_until = Some(lease_until);
        extra(&mut job);
        snap(vec![job], vec!["pax"], vec!["pax"])
    }

    #[test]
    fn lease_risk_test_near_expiry_with_quiet_heartbeat_yields_warning() {
        let got = tick_at(&lease_snapshot(10240, |_| {}), 10000);
        assert_eq!(got.len(), 1);
        let alert = &got[0];
        assert_eq!(alert.kind, "lease-risk");
        assert_eq!(alert.severity, "warning");
        assert_eq!(alert.nick.as_deref(), Some("pax"));
        assert_eq!(alert.job.as_deref(), Some("9"));
        assert_eq!(alert.seconds_to_expiry, Some(240));
        assert_eq!(alert.minutes_to_expiry, Some(4));
        assert_eq!(alert.dedupe_key, "lease-risk:pax:9");
        assert!(alert.explanation.contains('9'));
    }

    #[test]
    fn lease_risk_test_recent_heartbeat_with_short_lease_is_not_a_risk() {
        // Lease expiring in 90s but heartbeat 30s ago (short
        // 120s lease: 10090 - 120 = 9970) is a live worker.
        let snapshot = lease_snapshot(10090, |job| job.lease = Some(120));
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn lease_risk_test_explicit_heartbeat_beats_derived_heartbeat() {
        let snapshot = lease_snapshot(10180, |job| job.heartbeat = Some(9990));
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn lease_risk_test_lease_far_from_expiry_is_not_a_risk() {
        assert!(tick_at(&lease_snapshot(11000, |_| {}), 10000).is_empty());
    }

    #[test]
    fn lease_risk_test_already_expired_lease_is_not_a_warning() {
        assert!(tick_at(&lease_snapshot(9990, |_| {}), 10000).is_empty());
    }

    #[test]
    fn lease_risk_test_job_without_lease_until_never_invents_an_expiry() {
        let mut snapshot = lease_snapshot(10240, |_| {});
        snapshot.jobs[0].lease_until = None;
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn lease_risk_test_requeued_job_stops_firing() {
        let mut snapshot = lease_snapshot(10240, |_| {});
        snapshot.jobs[0].status = "open".to_string();
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn lease_risk_test_walk_on_claimer_lease_still_warned() {
        let mut snapshot = lease_snapshot(10240, |_| {});
        snapshot.caps = vec!["hana".to_string()];
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "lease-risk");
    }

    // ---- DeadDepTest ----

    fn dead_dep_snapshot(dep_status: &str, dep_note: Option<&str>, job_status: &str) -> Snapshot {
        let mut job = mk_job("2", job_status);
        job.title = "blocked job".to_string();
        job.deps = vec!["1".to_string()];
        let mut dep = mk_job("1", dep_status);
        dep.title = "dep job".to_string();
        dep.note = dep_note.map(|s| s.to_string());
        Snapshot {
            jobs: vec![job, dep],
            ..Snapshot::default()
        }
    }

    #[test]
    fn dead_dep_test_blocked_dep_yields_one_critical_alert() {
        let got = tick_at(&dead_dep_snapshot("blocked", Some("waiting on vendor API key"), "open"), 10000);
        assert_eq!(got.len(), 1);
        let alert = &got[0];
        assert_eq!(alert.kind, "dead-dep");
        assert_eq!(alert.severity, "critical");
        assert_eq!(alert.job.as_deref(), Some("2"));
        assert_eq!(alert.dep.as_deref(), Some("1"));
        assert_eq!(alert.dep_status.as_deref(), Some("blocked"));
        assert_eq!(alert.blocking_reason.as_deref(), Some("waiting on vendor API key"));
        assert!(alert.explanation.contains('2'));
        assert!(alert.explanation.contains('1'));
        assert!(alert.explanation.contains("waiting on vendor API key"));
        assert_eq!(alert.dedupe_key, "dead-dep:2:1");
    }

    #[test]
    fn dead_dep_test_failed_final_dep_also_dead() {
        let got = tick_at(&dead_dep_snapshot("failed-final", None, "open"), 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].dep_status.as_deref(), Some("failed-final"));
        assert_eq!(got[0].blocking_reason.as_deref(), Some("failed-final"));
    }

    #[test]
    fn dead_dep_test_claimed_job_with_blocked_dep_also_alerts() {
        let mut snapshot = dead_dep_snapshot("blocked", Some("waiting on vendor API key"), "claimed");
        snapshot.jobs[0].claim = Some("pax".to_string());
        snapshot.jobs[0].last_activity = Some(9990);
        snapshot.presence = vec!["pax".to_string()];
        snapshot.caps = vec!["pax".to_string()];
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "dead-dep");
    }

    #[test]
    fn dead_dep_test_live_dep_yields_no_alert() {
        for status in ["open", "claimed", "done"] {
            let got = tick_at(&dead_dep_snapshot(status, Some("waiting on vendor API key"), "open"), 10000);
            assert!(got.is_empty(), "dep status {} must not alert", status);
        }
    }

    #[test]
    fn dead_dep_test_missing_dep_is_not_dead_dep() {
        let mut snapshot = dead_dep_snapshot("blocked", Some("waiting on vendor API key"), "open");
        snapshot.jobs.truncate(1);
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "missing-dep");
        assert_eq!(got[0].dep.as_deref(), Some("1"));
    }

    #[test]
    fn dead_dep_test_done_job_with_blocked_dep_yields_no_alert() {
        assert!(tick_at(&dead_dep_snapshot("blocked", Some("waiting on vendor API key"), "done"), 10000).is_empty());
    }

    #[test]
    fn dead_dep_test_unblocked_dep_stops_firing() {
        assert!(tick_at(&dead_dep_snapshot("open", Some("waiting on vendor API key"), "open"), 10000).is_empty());
    }

    #[test]
    fn dead_dep_test_two_dead_deps_yield_one_alert_each() {
        let mut snapshot = dead_dep_snapshot("blocked", Some("waiting on vendor API key"), "open");
        snapshot.jobs[0].deps = vec!["1".to_string(), "3".to_string()];
        let mut dep3 = mk_job("3", "blocked");
        dep3.title = "second dep".to_string();
        dep3.note = Some("out of budget".to_string());
        snapshot.jobs.push(dep3);
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 2);
        let deps: HashSet<&str> = got.iter().filter_map(|a| a.dep.as_deref()).collect();
        assert_eq!(deps, HashSet::from(["1", "3"]));
        let keys: HashSet<&str> = got.iter().map(|a| a.dedupe_key.as_str()).collect();
        assert_eq!(keys, HashSet::from(["dead-dep:2:1", "dead-dep:2:3"]));
    }

    #[test]
    fn dead_dep_test_job_with_no_deps_yields_no_alert() {
        let mut snapshot = dead_dep_snapshot("blocked", Some("waiting on vendor API key"), "open");
        snapshot.jobs[0].deps = Vec::new();
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    // ---- MissingDepTest ----

    fn missing_dep_snapshot(deps: Vec<&str>, extra: Vec<Job>, job_status: &str) -> Snapshot {
        let mut job = mk_job("2", job_status);
        job.title = "dangling job".to_string();
        job.deps = deps.iter().map(|s| s.to_string()).collect();
        let mut jobs = vec![job];
        jobs.extend(extra);
        Snapshot {
            jobs,
            ..Snapshot::default()
        }
    }

    #[test]
    fn missing_dep_test_dangling_dep_yields_one_critical_alert() {
        let got = tick_at(&missing_dep_snapshot(vec!["9"], vec![], "open"), 10000);
        assert_eq!(got.len(), 1);
        let alert = &got[0];
        assert_eq!(alert.kind, "missing-dep");
        assert_eq!(alert.severity, "critical");
        assert_eq!(alert.job.as_deref(), Some("2"));
        assert_eq!(alert.dep.as_deref(), Some("9"));
        assert!(alert.explanation.contains('2'));
        assert!(alert.explanation.contains('9'));
        assert_eq!(alert.dedupe_key, "missing-dep:2:9");
    }

    #[test]
    fn missing_dep_test_claimed_job_with_dangling_dep_also_alerts() {
        let mut snapshot = missing_dep_snapshot(vec!["9"], vec![], "claimed");
        snapshot.jobs[0].claim = Some("pax".to_string());
        snapshot.jobs[0].last_activity = Some(9990);
        snapshot.presence = vec!["pax".to_string()];
        snapshot.caps = vec!["pax".to_string()];
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "missing-dep");
    }

    #[test]
    fn missing_dep_test_existing_dep_yields_no_alert() {
        for status in ["open", "claimed", "done", "blocked", "failed-final"] {
            let snapshot = missing_dep_snapshot(vec!["9"], vec![mk_job("9", status)], "open");
            let got = tick_at(&snapshot, 10000);
            assert!(
                got.iter().all(|a| a.kind != "missing-dep"),
                "existing dep status {} must not yield missing-dep",
                status
            );
            if ["open", "claimed", "done"].contains(&status) {
                assert!(got.is_empty(), "live dep status {} must not alert at all", status);
            }
        }
    }

    #[test]
    fn missing_dep_test_dead_dep_and_missing_dep_do_not_cross_fire() {
        let mut blocked = mk_job("1", "blocked");
        blocked.title = "blocked dep".to_string();
        blocked.note = Some("waiting on vendor API key".to_string());
        let snapshot = missing_dep_snapshot(vec!["1", "9"], vec![blocked], "open");
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 2);
        assert_eq!(kinds_set(&got), HashSet::from(["dead-dep".to_string(), "missing-dep".to_string()]));
        let deps: HashSet<&str> = got.iter().filter_map(|a| a.dep.as_deref()).collect();
        assert_eq!(deps, HashSet::from(["1", "9"]));
    }

    #[test]
    fn missing_dep_test_two_dangling_deps_yield_one_alert_each() {
        let snapshot = missing_dep_snapshot(vec!["9", "10"], vec![], "open");
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 2);
        let deps: HashSet<&str> = got.iter().filter_map(|a| a.dep.as_deref()).collect();
        assert_eq!(deps, HashSet::from(["9", "10"]));
        let keys: HashSet<&str> = got.iter().map(|a| a.dedupe_key.as_str()).collect();
        assert_eq!(keys, HashSet::from(["missing-dep:2:9", "missing-dep:2:10"]));
    }

    #[test]
    fn missing_dep_test_done_job_with_dangling_dep_yields_no_alert() {
        assert!(tick_at(&missing_dep_snapshot(vec!["9"], vec![], "done"), 10000).is_empty());
    }

    #[test]
    fn missing_dep_test_list_form_deps_are_checked_too() {
        // List form is parsed by Snapshot::from_value; here the
        // typed form already carries a list, so assert via value.
        let value = Value::Map(vec![(
            "jobs".to_string(),
            Value::List(vec![Value::Map(vec![
                ("id".to_string(), Value::Str("2".to_string())),
                ("status".to_string(), Value::Str("open".to_string())),
                (
                    "deps".to_string(),
                    Value::List(vec![Value::Str("9".to_string())]),
                ),
            ])]),
        )]);
        let snapshot = Snapshot::from_value(&value);
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].dep.as_deref(), Some("9"));
    }

    #[test]
    fn missing_dep_test_job_with_no_deps_yields_no_alert() {
        assert!(tick_at(&missing_dep_snapshot(vec![], vec![], "open"), 10000).is_empty());
    }

    #[test]
    fn missing_dep_test_posting_the_missing_job_clears_the_alert() {
        let mut late = mk_job("9", "open");
        late.title = "late dep".to_string();
        assert!(tick_at(&missing_dep_snapshot(vec!["9"], vec![late], "open"), 10000).is_empty());
    }

    // ---- FileCollisionTest ----

    fn collision_job(id: &str, nick: &str, files: &str) -> Job {
        let mut job = claimed(id, nick, 9990);
        job.title = format!("job {}", id);
        job.files = files
            .split(',')
            .map(|f| f.trim().to_string())
            .filter(|f| !f.is_empty())
            .collect();
        job
    }

    fn collision_snapshot(jobs: Vec<Job>) -> Snapshot {
        let nicks: Vec<String> = jobs
            .iter()
            .filter_map(|j| j.claim.clone())
            .collect();
        Snapshot {
            presence: nicks.clone(),
            caps: nicks,
            jobs,
            ..Snapshot::default()
        }
    }

    #[test]
    fn file_collision_test_overlapping_claimed_pair_yields_one_critical_alert() {
        let snapshot = collision_snapshot(vec![
            collision_job("1", "pax", "intel/watchdog.py, intel/store.py"),
            collision_job("2", "rowan", "intel/store.py, intel/brief.py"),
        ]);
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        let alert = &got[0];
        assert_eq!(alert.kind, "file-collision");
        assert_eq!(alert.severity, "critical");
        assert_eq!(alert.job.as_deref(), Some("1"));
        assert_eq!(alert.other_job.as_deref(), Some("2"));
        assert_eq!(alert.shared_path.as_deref(), Some("intel/store.py"));
        assert!(alert.explanation.contains('1'));
        assert!(alert.explanation.contains('2'));
        assert!(alert.explanation.contains("intel/store.py"));
        assert_eq!(alert.dedupe_key, "file-collision:1:2:intel/store.py");
    }

    #[test]
    fn file_collision_test_disjoint_files_yield_no_alert() {
        let snapshot = collision_snapshot(vec![
            collision_job("1", "pax", "intel/watchdog.py"),
            collision_job("2", "rowan", "intel/brief.py"),
        ]);
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn file_collision_test_open_job_overlapping_claimed_yields_no_alert() {
        let mut open = mk_job("2", "open");
        open.title = "open job".to_string();
        open.files = vec!["intel/store.py".to_string()];
        let snapshot = collision_snapshot(vec![collision_job("1", "pax", "intel/store.py"), open]);
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn file_collision_test_claimed_overlapping_done_branch_yields_alert() {
        let mut done = mk_job("2", "done");
        done.title = "done job".to_string();
        done.branch = Some("worker/rowan/feature".to_string());
        done.files = vec!["intel/store.py".to_string()];
        let snapshot = collision_snapshot(vec![collision_job("1", "pax", "intel/store.py"), done]);
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "file-collision");
        assert_eq!(got[0].other_job.as_deref(), Some("2"));
        assert_eq!(got[0].other_status.as_deref(), Some("done"));
        assert_eq!(got[0].branch.as_deref(), Some("worker/rowan/feature"));
        assert!(got[0].explanation.contains("intel/store.py"));
    }

    #[test]
    fn file_collision_test_claimed_overlapping_done_without_branch_yields_no_alert() {
        let mut done = mk_job("2", "done");
        done.title = "done job".to_string();
        done.files = vec!["intel/store.py".to_string()];
        let snapshot = collision_snapshot(vec![collision_job("1", "pax", "intel/store.py"), done]);
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn file_collision_test_two_shared_paths_yield_one_alert_each() {
        let snapshot = collision_snapshot(vec![
            collision_job("1", "pax", "a.py, b.py"),
            collision_job("2", "rowan", "b.py, a.py"),
        ]);
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 2);
        let paths: HashSet<&str> = got.iter().filter_map(|a| a.shared_path.as_deref()).collect();
        assert_eq!(paths, HashSet::from(["a.py", "b.py"]));
        let keys: HashSet<&str> = got.iter().map(|a| a.dedupe_key.as_str()).collect();
        assert_eq!(keys, HashSet::from(["file-collision:1:2:a.py", "file-collision:1:2:b.py"]));
    }

    #[test]
    fn file_collision_test_duplicate_path_on_one_job_counts_once() {
        let snapshot = collision_snapshot(vec![
            collision_job("1", "pax", "a.py, a.py"),
            collision_job("2", "rowan", "a.py"),
        ]);
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
    }

    #[test]
    fn file_collision_test_list_form_files_are_checked_too() {
        let value = Value::Map(vec![(
            "jobs".to_string(),
            Value::List(vec![
                Value::Map(vec![
                    ("id".to_string(), Value::Str("1".to_string())),
                    ("status".to_string(), Value::Str("claimed".to_string())),
                    ("claim".to_string(), Value::Str("pax".to_string())),
                    ("claimed_at".to_string(), Value::Int(9990)),
                    (
                        "files".to_string(),
                        Value::List(vec![Value::Str("a.py".to_string())]),
                    ),
                ]),
                Value::Map(vec![
                    ("id".to_string(), Value::Str("2".to_string())),
                    ("status".to_string(), Value::Str("claimed".to_string())),
                    ("claim".to_string(), Value::Str("rowan".to_string())),
                    ("claimed_at".to_string(), Value::Int(9990)),
                    (
                        "files".to_string(),
                        Value::List(vec![Value::Str("a.py".to_string()), Value::Str("c.py".to_string())]),
                    ),
                ]),
            ]),
        )]);
        let mut snapshot = Snapshot::from_value(&value);
        snapshot.presence = vec!["pax".to_string(), "rowan".to_string()];
        snapshot.caps = vec!["pax".to_string(), "rowan".to_string()];
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].shared_path.as_deref(), Some("a.py"));
    }

    #[test]
    fn file_collision_test_job_with_no_files_yields_no_alert() {
        let snapshot = collision_snapshot(vec![
            collision_job("1", "pax", ""),
            collision_job("2", "rowan", "a.py"),
        ]);
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn file_collision_test_removing_the_overlap_clears_the_alert() {
        let mut jobs = vec![
            collision_job("1", "pax", "a.py"),
            collision_job("2", "rowan", "a.py"),
        ];
        assert_eq!(tick_at(&collision_snapshot(jobs.clone()), 10000).len(), 1);
        jobs[1].files = vec!["b.py".to_string()];
        assert!(tick_at(&collision_snapshot(jobs), 10000).is_empty());
    }

    // ---- AttemptExhaustionTest ----

    fn attempt_job(attempts: i64, max_attempts: Option<i64>, status: &str) -> Job {
        let mut job = mk_job("7", status);
        job.title = "flaky job".to_string();
        job.claim = Some("pax".to_string());
        job.attempts = attempts;
        job.max_attempts = max_attempts;
        job
    }

    #[test]
    fn attempt_exhaustion_test_walk_produces_warning_at_max_minus_one_then_critical() {
        for attempts in [0, 1] {
            let snapshot = Snapshot {
                jobs: vec![attempt_job(attempts, Some(3), "open")],
                ..Snapshot::default()
            };
            assert!(tick_at(&snapshot, 10000).is_empty(), "attempts={} should be silent", attempts);
        }
        let snapshot = Snapshot {
            jobs: vec![attempt_job(2, Some(3), "open")],
            ..Snapshot::default()
        };
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "attempt-warning");
        assert_eq!(got[0].severity, "warning");
        assert_eq!(got[0].job.as_deref(), Some("7"));
        assert_eq!(got[0].attempts, Some(2));
        assert_eq!(got[0].max_attempts, Some(3));
        assert_eq!(got[0].attempts_remaining, Some(1));
        assert_eq!(got[0].dedupe_key, "attempt-warning:7");
        assert!(got[0].explanation.contains('7'));
        assert!(got[0].explanation.contains("one attempt"));
        let snapshot = Snapshot {
            jobs: vec![attempt_job(3, Some(3), "open")],
            ..Snapshot::default()
        };
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "attempt-exhaustion");
        assert_eq!(got[0].severity, "critical");
        assert_eq!(got[0].job.as_deref(), Some("7"));
        assert_eq!(got[0].attempts_remaining, Some(0));
        assert_eq!(got[0].dedupe_key, "attempt-exhaustion:7");
        assert!(got[0].explanation.contains("failed-final"));
        let snapshot = Snapshot {
            jobs: vec![attempt_job(4, Some(3), "open")],
            ..Snapshot::default()
        };
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "attempt-exhaustion");
    }

    #[test]
    fn attempt_exhaustion_test_failed_final_job_at_max_yields_critical() {
        let snapshot = Snapshot {
            jobs: vec![attempt_job(3, Some(3), "failed-final")],
            ..Snapshot::default()
        };
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "attempt-exhaustion");
    }

    #[test]
    fn attempt_exhaustion_test_claimed_job_at_max_minus_one_warns() {
        let snapshot = Snapshot {
            jobs: vec![attempt_job(2, Some(3), "claimed")],
            ..Snapshot::default()
        };
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "attempt-warning");
    }

    #[test]
    fn attempt_exhaustion_test_no_budget_yields_no_alert_at_any_attempt_count() {
        // No budget: max_attempts None, or unparseable ("" in
        // Python, which from_value maps to None).
        let value = Value::Map(vec![(
            "jobs".to_string(),
            Value::List(vec![Value::Map(vec![
                ("id".to_string(), Value::Str("7".to_string())),
                ("status".to_string(), Value::Str("open".to_string())),
                ("attempts".to_string(), Value::Int(9)),
                ("max_attempts".to_string(), Value::Str("".to_string())),
            ])]),
        )]);
        assert!(tick_at(&Snapshot::from_value(&value), 10000).is_empty());
        for job in [attempt_job(9, None, "open")] {
            let snapshot = Snapshot {
                jobs: vec![job],
                ..Snapshot::default()
            };
            assert!(tick_at(&snapshot, 10000).is_empty());
        }
    }

    #[test]
    fn attempt_exhaustion_test_string_form_attempts_match_redis_hashes() {
        let value = Value::Map(vec![(
            "jobs".to_string(),
            Value::List(vec![Value::Map(vec![
                ("id".to_string(), Value::Str("7".to_string())),
                ("status".to_string(), Value::Str("open".to_string())),
                ("attempts".to_string(), Value::Str("2".to_string())),
                ("max_attempts".to_string(), Value::Str("3".to_string())),
            ])]),
        )]);
        let got = tick_at(&Snapshot::from_value(&value), 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "attempt-warning");
    }

    #[test]
    fn attempt_exhaustion_test_done_job_at_max_yields_no_alert() {
        let snapshot = Snapshot {
            jobs: vec![attempt_job(3, Some(3), "done")],
            ..Snapshot::default()
        };
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn attempt_exhaustion_test_budget_of_one_warns_at_zero_then_fails_at_one() {
        let snapshot = Snapshot {
            jobs: vec![attempt_job(0, Some(1), "open")],
            ..Snapshot::default()
        };
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "attempt-warning");
        let snapshot = Snapshot {
            jobs: vec![attempt_job(1, Some(1), "open")],
            ..Snapshot::default()
        };
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "attempt-exhaustion");
    }

    // ---- SilentRoomTest ----

    fn silent_snapshot(job_ids: Vec<&str>, messages: Vec<Message>) -> Snapshot {
        Snapshot {
            jobs: job_ids
                .iter()
                .map(|id| {
                    let mut job = claimed(id, "pax", 1000);
                    job.title = "claimed job".to_string();
                    job
                })
                .collect(),
            messages,
            ..Snapshot::default()
        }
    }

    #[test]
    fn silent_room_test_silent_room_yields_info_record_only() {
        let snapshot = silent_snapshot(vec!["1"], vec![msg("starting", 1000)]);
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        let record = &got[0];
        assert_eq!(record.kind, "silent-room");
        assert_eq!(record.severity, "info");
        assert_eq!(record.claimed_jobs, vec!["1".to_string()]);
        assert_eq!(record.claimed_count, Some(1));
        assert_eq!(record.last_message_age_seconds, Some(9000));
        assert_eq!(record.dedupe_key, "silent-room");
        assert!(record.explanation.contains('1'));
        assert!(record.explanation.contains("60"));
        assert!(!record.explanation.contains("ALERT"));
    }

    #[test]
    fn silent_room_test_dashboard_severity_mapping_silent_room_is_info() {
        let snapshot = silent_snapshot(vec!["1"], vec![msg("starting", 1000)]);
        let got = tick_at(&snapshot, 10000);
        let severities: HashSet<&str> = got.iter().map(|r| r.severity.as_str()).collect();
        assert_eq!(severities, HashSet::from(["info"]));
        assert!(got.iter().all(|r| r.severity != "critical" && r.severity != "warning"));
    }

    #[test]
    fn silent_room_test_fresh_message_inside_threshold_yields_no_record() {
        let snapshot = silent_snapshot(vec!["1"], vec![msg("update", 8200)]);
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn silent_room_test_silence_exactly_at_threshold_yields_no_record() {
        let snapshot = silent_snapshot(vec!["1"], vec![msg("starting", 6400)]);
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn silent_room_test_no_claimed_jobs_yields_no_record() {
        let snapshot = Snapshot {
            jobs: vec![mk_job("1", "open")],
            messages: vec![msg("done for now", 1000)],
            ..Snapshot::default()
        };
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn silent_room_test_no_timestamped_messages_yields_no_record() {
        for messages in [
            vec![raw_msg("working")],
            vec![],
            vec![raw_msg("pax: working")],
        ] {
            let snapshot = silent_snapshot(vec!["1"], messages.clone());
            assert!(tick_at(&snapshot, 10000).is_empty(), "messages should be silent");
        }
    }

    #[test]
    fn silent_room_test_latest_message_sets_the_clock() {
        let snapshot = silent_snapshot(vec!["1"], vec![msg("old", 1000), msg("new", 9500)]);
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn silent_room_test_multiple_claimed_jobs_yield_one_room_record() {
        let snapshot = silent_snapshot(vec!["1", "2"], vec![msg("starting", 1000)]);
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].claimed_jobs, vec!["1".to_string(), "2".to_string()]);
        assert_eq!(got[0].claimed_count, Some(2));
    }

    #[test]
    fn silent_room_test_message_after_tick_time_yields_no_record() {
        let snapshot = silent_snapshot(vec!["1"], vec![msg("starting", 20000)]);
        assert!(tick_at(&snapshot, 10000).is_empty());
    }

    #[test]
    fn silent_room_test_room_name_scopes_dedupe_key() {
        let mut snapshot = silent_snapshot(vec!["1"], vec![msg("starting", 1000)]);
        snapshot.room = Some("build".to_string());
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].dedupe_key, "silent-room:build");
        assert_eq!(got[0].room.as_deref(), Some("build"));
    }

    // ---- AlertRecordWriterTest / AlertDedupeTest: tick halves only ----
    // The store writer, dedupe, lifecycle, query, and status-line
    // assertions in these Python classes are intel/store.py's
    // subject (other batch) and are NOT mirrored here. What is
    // mirrored is the watchdog half: tick output feeding an emit
    // sink, and dedupe-key stability across ticks.

    #[test]
    fn alert_record_writer_test_tick_output_feeds_emit_sink() {
        let mut written: Vec<Alert> = Vec::new();
        let mut emit = |a: &Alert| written.push(a.clone());
        let got = tick_full(
            &stall_snapshot(),
            Some(10000),
            &th(),
            DETECTORS,
            Some(&mut emit as &mut dyn FnMut(&Alert)),
            None,
            None,
            None,
            None,
        );
        assert_eq!(got.len(), 1);
        assert_eq!(written.len(), 1);
        assert_eq!(written[0].kind, "presence-stall");
        assert_eq!(written, got);
    }

    #[test]
    fn alert_dedupe_test_two_ticks_yield_same_dedupe_key() {
        let first = tick_at(&stall_snapshot(), 10000);
        let second = tick_at(&stall_snapshot(), 10600);
        assert_eq!(first.len(), 1);
        assert_eq!(second.len(), 1);
        assert_eq!(first[0].dedupe_key, second[0].dedupe_key);
        assert_eq!(first[0].dedupe_key, "presence-stall:pax:7");
    }

    // ---- SparkPolishTest ----

    struct FakeClient {
        text: Option<String>,
        error: Option<String>,
        calls: Vec<(String, String)>,
    }

    impl PolishClient for FakeClient {
        fn complete(&mut self, prompt: &str, lane_feature: &str) -> Result<String, String> {
            self.calls.push((prompt.to_string(), lane_feature.to_string()));
            if let Some(error) = &self.error {
                return Err(error.clone());
            }
            Ok(self.text.clone().unwrap_or_default())
        }
    }

    #[test]
    fn spark_polish_test_toggle_off_keeps_template_text() {
        let got = tick_at(&stall_snapshot(), 10000);
        assert_eq!(got.len(), 1);
        assert!(got[0].explanation.starts_with("pax holds claimed job 7"));
    }

    #[test]
    fn spark_polish_test_toggle_on_uses_polished_text() {
        let mut client = FakeClient {
            text: Some("Pax has gone quiet while holding job 7.".to_string()),
            error: None,
            calls: Vec::new(),
        };
        let got = tick_full(
            &stall_snapshot(),
            Some(10000),
            &th(),
            DETECTORS,
            None,
            Some(&mut client as &mut dyn PolishClient),
            None,
            None,
            None,
        );
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].explanation, "Pax has gone quiet while holding job 7.");
        assert!(got[0].suggested_fix.contains("lease sweep"));
        assert_eq!(client.calls.len(), 1);
        assert_eq!(client.calls[0].1, "watchdog");
        assert!(client.calls[0].0.contains("job 7"));
    }

    #[test]
    fn spark_polish_test_emitted_alert_carries_polished_text() {
        let mut client = FakeClient {
            text: Some("Polished explanation.".to_string()),
            error: None,
            calls: Vec::new(),
        };
        let mut seen: Vec<Alert> = Vec::new();
        let mut emit = |a: &Alert| seen.push(a.clone());
        let got = tick_full(
            &stall_snapshot(),
            Some(10000),
            &th(),
            DETECTORS,
            Some(&mut emit as &mut dyn FnMut(&Alert)),
            Some(&mut client as &mut dyn PolishClient),
            None,
            None,
            None,
        );
        assert_eq!(seen, got);
        assert_eq!(seen[0].explanation, "Polished explanation.");
    }

    #[test]
    fn spark_polish_test_spark_failure_keeps_template_text() {
        let mut client = FakeClient {
            text: None,
            error: Some("spark down".to_string()),
            calls: Vec::new(),
        };
        let got = tick_full(
            &stall_snapshot(),
            Some(10000),
            &th(),
            DETECTORS,
            None,
            Some(&mut client as &mut dyn PolishClient),
            None,
            None,
            None,
        );
        assert_eq!(got.len(), 1);
        assert!(got[0].explanation.starts_with("pax holds claimed job 7"));
    }

    #[test]
    fn spark_polish_test_empty_spark_reply_keeps_template_text() {
        for empty in ["", "   "] {
            let mut client = FakeClient {
                text: Some(empty.to_string()),
                error: None,
                calls: Vec::new(),
            };
            let got = tick_full(
                &stall_snapshot(),
                Some(10000),
                &th(),
                DETECTORS,
                None,
                Some(&mut client as &mut dyn PolishClient),
                None,
                None,
                None,
            );
            assert!(got[0].explanation.starts_with("pax holds claimed job 7"));
        }
    }

    #[test]
    fn spark_polish_test_quiet_snapshot_with_polish_client_calls_nothing() {
        let mut client = FakeClient {
            text: Some("never used".to_string()),
            error: None,
            calls: Vec::new(),
        };
        let got = tick_full(
            &Snapshot::default(),
            Some(1000),
            &th(),
            DETECTORS,
            None,
            Some(&mut client as &mut dyn PolishClient),
            None,
            None,
            None,
        );
        assert!(got.is_empty());
        assert!(client.calls.is_empty());
    }

    #[test]
    fn spark_polish_test_polish_helper_toggle_off_and_failure() {
        let template = "pax holds claimed job 7.";
        assert_eq!(polish_explanation(template, None), template);
        let mut failing = FakeClient {
            text: None,
            error: Some("down".to_string()),
            calls: Vec::new(),
        };
        assert_eq!(
            polish_explanation(template, Some(&mut failing as &mut dyn PolishClient)),
            template
        );
        let mut blank = FakeClient {
            text: Some("  ".to_string()),
            error: None,
            calls: Vec::new(),
        };
        assert_eq!(
            polish_explanation(template, Some(&mut blank as &mut dyn PolishClient)),
            template
        );
    }

    // ---- AnnounceTest ----

    fn lease_announce_snapshot() -> Snapshot {
        lease_snapshot(10240, |_| {})
    }

    fn silent_announce_snapshot() -> Snapshot {
        let mut snapshot = silent_snapshot(vec!["7"], vec![msg("old", 1000)]);
        snapshot.jobs[0].last_activity = Some(9900);
        snapshot
    }

    #[test]
    fn announce_test_critical_fixture_yields_exactly_one_announcement() {
        let mut lines: Vec<String> = Vec::new();
        let mut announce = |line: &str| lines.push(line.to_string());
        let got = tick_full(
            &stall_snapshot(),
            Some(10000),
            &th(),
            DETECTORS,
            None,
            None,
            Some(&mut announce as &mut dyn FnMut(&str)),
            None,
            None,
        );
        assert_eq!(got.len(), 1);
        assert_eq!(lines.len(), 1);
        assert!(lines[0].starts_with("ALERT:presence-stall:pax:7 presence-stall: "));
        assert!(lines[0].contains("pax"));
        assert!(!lines[0].contains('\n'));
    }

    #[test]
    fn announce_test_warning_fixture_yields_no_announcement() {
        let mut lines: Vec<String> = Vec::new();
        let mut announce = |line: &str| lines.push(line.to_string());
        let got = tick_full(
            &lease_announce_snapshot(),
            Some(10000),
            &th(),
            DETECTORS,
            None,
            None,
            Some(&mut announce as &mut dyn FnMut(&str)),
            None,
            None,
        );
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].severity, "warning");
        assert!(lines.is_empty());
    }

    #[test]
    fn announce_test_info_record_yields_no_announcement() {
        let mut lines: Vec<String> = Vec::new();
        let mut announce = |line: &str| lines.push(line.to_string());
        let got = tick_full(
            &silent_announce_snapshot(),
            Some(10000),
            &th(),
            DETECTORS,
            None,
            None,
            Some(&mut announce as &mut dyn FnMut(&str)),
            None,
            None,
        );
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].severity, "info");
        assert!(lines.is_empty());
    }

    #[test]
    fn announce_test_no_callback_means_held_not_posted() {
        let got = tick_at(&stall_snapshot(), 10000);
        assert_eq!(got.len(), 1);
        let lines = announcements_for(&got);
        assert_eq!(lines.len(), 1);
        assert_eq!(lines[0], format_announcement(&got[0]).unwrap());
        assert!(lines[0].starts_with("ALERT:presence-stall:pax:7 "));
    }

    #[test]
    fn announce_test_format_gate_rejects_warning_info_and_bad_input() {
        let warning = Alert {
            severity: "warning".to_string(),
            id: Some("w".to_string()),
            kind: "lease-risk".to_string(),
            explanation: "x".to_string(),
            ..Alert::default()
        };
        let info = Alert {
            severity: "info".to_string(),
            id: Some("i".to_string()),
            kind: "silent-room".to_string(),
            explanation: "x".to_string(),
            ..Alert::default()
        };
        let no_id = Alert {
            severity: "critical".to_string(),
            kind: "stall".to_string(),
            explanation: "x".to_string(),
            ..Alert::default()
        };
        assert_eq!(format_announcement(&warning), None);
        assert_eq!(format_announcement(&info), None);
        assert_eq!(format_announcement(&no_id), None);
        assert!(announcements_for(&[warning, info]).is_empty());
        assert!(announcements_for(&[]).is_empty());
    }

    #[test]
    fn announce_test_announcement_flattens_multiline_explanation() {
        let alert = Alert {
            severity: "critical".to_string(),
            id: Some("c1".to_string()),
            kind: "presence-stall".to_string(),
            explanation: "line one\nline two".to_string(),
            ..Alert::default()
        };
        assert_eq!(
            format_announcement(&alert).unwrap(),
            "ALERT:c1 presence-stall: line one line two"
        );
    }

    #[test]
    fn announce_test_cli_announce_prints_line_only_with_flag() {
        let content = r#"{"jobs": [{"id": "7", "title": "demo job", "status": "claimed", "claim": "pax", "claimed_at": 9340}], "presence": ["hana"], "caps": {"pax": {"caps": "build"}}}"#;
        let path = tmp_snapshot_file("announce", content);
        let (code, out) = run_cli_capture(&["--once", "--snapshot", path.to_str().unwrap()]);
        assert_eq!(code, 0);
        assert!(!out.contains("ALERT:"), "out: {}", out);
        let (code, out) = run_cli_capture(&[
            "--once",
            "--snapshot",
            path.to_str().unwrap(),
            "--announce",
        ]);
        assert_eq!(code, 0);
        assert!(out.contains("ALERT:presence-stall:pax:7 "), "out: {}", out);
        let _ = std::fs::remove_file(&path);
    }

    // ---- SelfBeatTest ----

    #[test]
    fn self_beat_test_beat_called_once_per_tick_even_when_quiet() {
        let mut beats: Vec<i64> = Vec::new();
        let mut beat = |ts: i64| beats.push(ts);
        let got = tick_full(
            &Snapshot::default(),
            Some(1000),
            &th(),
            DETECTORS,
            None,
            None,
            None,
            Some(&mut beat as &mut dyn FnMut(i64)),
            None,
        );
        assert!(got.is_empty());
        assert_eq!(beats, vec![1000]);
    }

    #[test]
    fn self_beat_test_beat_called_once_when_alerts_fire() {
        let snapshot = snap(vec![claimed("7", "pax", 100)], vec![], vec!["pax"]);
        let mut beats: Vec<i64> = Vec::new();
        let mut beat = |ts: i64| beats.push(ts);
        let got = tick_full(
            &snapshot,
            Some(10000),
            &th(),
            DETECTORS,
            None,
            None,
            None,
            Some(&mut beat as &mut dyn FnMut(i64)),
            None,
        );
        assert!(!got.is_empty());
        assert_eq!(beats, vec![10000]);
    }

    #[test]
    fn self_beat_test_no_beat_callback_writes_nothing_and_raises_nothing() {
        assert!(tick_at(&Snapshot::default(), 1000).is_empty());
    }

    #[test]
    fn self_beat_test_failing_beat_never_fails_the_tick_or_hides_alerts() {
        let mut boom = |_ts: i64| panic!("store down");
        let snapshot = snap(vec![claimed("7", "pax", 100)], vec![], vec!["pax"]);
        let got = tick_full(
            &snapshot,
            Some(10000),
            &th(),
            DETECTORS,
            None,
            None,
            None,
            Some(&mut boom as &mut dyn FnMut(i64)),
            None,
        );
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "presence-stall");
    }

    // ---- TickBudgetTest ----

    fn busy_snapshot(message_count: usize, last_ts: i64) -> Snapshot {
        let messages: Vec<Message> = (0..message_count)
            .map(|i| Message {
                text: format!("note {}", i),
                ts: Some(last_ts - (message_count as i64 - 1 - i as i64)),
            })
            .collect();
        Snapshot {
            jobs: vec![claimed("1", "pax", 1000)],
            messages,
            ..Snapshot::default()
        }
    }

    #[test]
    fn tick_budget_test_paginate_yields_page_sized_chunks_oldest_first() {
        let items: Vec<i64> = (0..2500).collect();
        let pages = paginate(&items, 1000).unwrap();
        assert_eq!(
            pages.iter().map(|p| p.len()).collect::<Vec<_>>(),
            vec![1000, 1000, 500]
        );
        let flat: Vec<i64> = pages.into_iter().flatten().collect();
        assert_eq!(flat, items);
    }

    #[test]
    fn tick_budget_test_paginate_rejects_non_positive_page_size() {
        for bad in [0, -100] {
            assert!(paginate(&[1, 2, 3], bad).is_err());
        }
    }

    #[test]
    fn tick_budget_test_cap_keeps_newest_and_reports_the_drop() {
        let snapshot = busy_snapshot(1500, 1000);
        let capped = cap_tick_snapshot(&snapshot, None, None, &th()).unwrap();
        let window = capped.tick_window.unwrap();
        assert_eq!(window.messages_kept, 1000);
        assert_eq!(window.messages_dropped, 500);
        assert_eq!(capped.messages[0].text, "note 500");
        assert_eq!(capped.messages.last().unwrap().text, "note 1499");
        assert_eq!(capped.jobs, snapshot.jobs);
    }

    #[test]
    fn tick_budget_test_cap_under_the_limit_passes_through_unchanged() {
        let snapshot = busy_snapshot(50, 1000);
        let capped = cap_tick_snapshot(&snapshot, None, None, &th()).unwrap();
        assert_eq!(capped.tick_window.unwrap().messages_dropped, 0);
        assert_eq!(capped.messages, snapshot.messages);
    }

    #[test]
    fn tick_budget_test_cap_twice_accumulates_the_drop_count() {
        let once = cap_tick_snapshot(&busy_snapshot(1500, 1000), None, None, &th()).unwrap();
        let twice = cap_tick_snapshot(&once, Some(100), None, &th()).unwrap();
        assert_eq!(twice.tick_window.unwrap().messages_dropped, 500 + 900);
        assert_eq!(twice.messages.len(), 100);
    }

    #[test]
    fn tick_budget_test_1500_message_tick_completes_with_correct_verdict() {
        let got = tick_at(&busy_snapshot(1500, 1000), 10000);
        let records: Vec<&Alert> = got.iter().filter(|r| r.kind == "silent-room").collect();
        assert_eq!(records.len(), 1);
        assert_eq!(records[0].last_message_age_seconds, Some(9000));
        let got = tick_at(&busy_snapshot(1500, 8200), 10000);
        assert!(got.iter().all(|r| r.kind != "silent-room"));
    }

    #[test]
    fn tick_budget_test_tick_cap_never_hides_a_job_detector_verdict() {
        let mut snapshot = busy_snapshot(1500, 8200);
        snapshot.jobs = vec![claimed("7", "pax", 100)];
        snapshot.presence = Vec::new();
        snapshot.caps = vec!["pax".to_string()];
        let got = tick_at(&snapshot, 10000);
        let stalls: Vec<&Alert> = got.iter().filter(|r| r.kind == "presence-stall").collect();
        assert_eq!(stalls.len(), 1);
        assert_eq!(stalls[0].job.as_deref(), Some("7"));
    }

    #[test]
    fn tick_budget_test_cli_once_on_1500_message_snapshot_exits_zero() {
        // Build the JSON the Python suite writes via json.dump.
        let mut messages = String::new();
        for i in 0..1500 {
            if i > 0 {
                messages.push(',');
            }
            messages.push_str(&format!(
                "{{\"nick\": \"pax\", \"text\": \"note {}\", \"ts\": {}}}",
                i,
                8200 - (1500 - 1 - i)
            ));
        }
        let content = format!(
            "{{\"jobs\": [{{\"id\": \"1\", \"title\": \"claimed job\", \"status\": \"claimed\", \"claim\": \"pax\", \"claimed_at\": 1000}}], \"messages\": [{}]}}",
            messages
        );
        let path = tmp_snapshot_file("busy", &content);
        let (code, _out) = run_cli_capture(&["--once", "--snapshot", path.to_str().unwrap()]);
        assert_eq!(code, 0);
        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn tick_budget_test_cap_with_zero_max_keeps_nothing() {
        let snapshot = busy_snapshot(50, 1000);
        let capped = cap_tick_snapshot(&snapshot, Some(0), None, &th()).unwrap();
        assert!(capped.messages.is_empty());
        assert_eq!(capped.tick_window.unwrap().messages_dropped, 50);
    }

    // ---- EnvOverrideTest ----
    // Python reloads the thresholds module with WATCHDOG_* set.
    // The Rust equivalent is Thresholds::from_env_with (a fixed
    // lookup, so tests never mutate the shared environment) plus
    // tick_with_thresholds (the reload's behavioral effect).

    fn env_thresholds(pairs: &[(&str, &str)]) -> Thresholds {
        let map: HashMap<String, String> = pairs
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect();
        Thresholds::from_env_with(move |name| map.get(name).cloned())
    }

    #[test]
    fn env_override_test_defaults_unchanged_without_env() {
        let thresholds = Thresholds::default();
        assert_eq!(thresholds.stall_minutes, 10);
        assert_eq!(thresholds.progress_stall_minutes, 10);
        assert_eq!(thresholds.lease_risk_window_minutes, 5);
        assert_eq!(thresholds.lease_risk_quiet_minutes, 2);
        assert_eq!(thresholds.alert_dedupe_cooldown_minutes, 30);
        assert_eq!(thresholds.silent_room_minutes, 60);
        assert_eq!(thresholds.watchdog_beat_ttl_seconds, 300);
        assert_eq!(thresholds.tick_page_size, 1000);
        assert_eq!(thresholds.tick_max_messages, 1000);
    }

    #[test]
    fn env_override_test_env_override_changes_presence_stall_behavior() {
        let snapshot = snap(vec![claimed("9", "pax", 100)], vec![], vec!["pax"]);
        let got = tick_at(&snapshot, 1900);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "presence-stall");
        let mut overridden = th();
        overridden.stall_minutes = 60;
        assert!(tick_with_thresholds(&snapshot, Some(1900), &overridden).is_empty());
        assert_eq!(tick_at(&snapshot, 1900).len(), 1);
        // And the env lookup itself yields 60 for the variable.
        assert_eq!(
            env_thresholds(&[("WATCHDOG_STALL_MINUTES", "60")]).stall_minutes,
            60
        );
    }

    #[test]
    fn env_override_test_env_override_changes_silent_room_behavior() {
        let snapshot = Snapshot {
            jobs: vec![claimed("1", "pax", 1000)],
            messages: vec![msg("note", 1000)],
            ..Snapshot::default()
        };
        let records: Vec<Alert> = tick_at(&snapshot, 5200)
            .into_iter()
            .filter(|r| r.kind == "silent-room")
            .collect();
        assert_eq!(records.len(), 1);
        let mut overridden = th();
        overridden.silent_room_minutes = 120;
        let records: Vec<Alert> = tick_with_thresholds(&snapshot, Some(5200), &overridden)
            .into_iter()
            .filter(|r| r.kind == "silent-room")
            .collect();
        assert!(records.is_empty());
        assert_eq!(
            env_thresholds(&[("WATCHDOG_SILENT_ROOM_MINUTES", "120")]).silent_room_minutes,
            120
        );
    }

    #[test]
    fn env_override_test_env_override_changes_tick_cap_behavior() {
        let snapshot = Snapshot {
            jobs: Vec::new(),
            messages: (0..1500)
                .map(|i| Message {
                    text: format!("note {}", i),
                    ts: Some(i as i64),
                })
                .collect(),
            ..Snapshot::default()
        };
        let thresholds = env_thresholds(&[("WATCHDOG_TICK_MAX_MESSAGES", "100")]);
        let capped = cap_tick_snapshot(&snapshot, None, None, &thresholds).unwrap();
        let window = capped.tick_window.unwrap();
        assert_eq!(window.messages_kept, 100);
        assert_eq!(window.messages_dropped, 1400);
    }

    #[test]
    fn env_override_test_bad_env_values_fall_back_to_defaults() {
        assert_eq!(env_int(Some(""), 10, 0), 10);
        assert_eq!(env_int(Some("banana"), 10, 0), 10);
        assert_eq!(env_int(Some("-5"), 10, 0), 10);
        assert_eq!(env_int(None, 10, 0), 10);
        assert_eq!(env_int(Some("45"), 30, 0), 45);
        assert_eq!(
            env_thresholds(&[("WATCHDOG_TICK_PAGE_SIZE", "0")]).tick_page_size,
            1000
        );
        assert_eq!(
            env_thresholds(&[("WATCHDOG_ALERT_DEDUPE_COOLDOWN_MINUTES", "45")])
                .alert_dedupe_cooldown_minutes,
            45
        );
    }

    // ---- DetectorCoverageTest ----

    fn coverage_positives() -> Vec<(Snapshot, &'static str)> {
        let mut stall = claimed("7", "pax", 9340);
        stall.title = String::new();
        let mut progress = claimed("7", "pax", 9340);
        progress.title = String::new();
        let mut lease = mk_job("7", "claimed");
        lease.claim = Some("pax".to_string());
        lease.lease_until = Some(10200);
        let dead = {
            let mut job = mk_job("1", "open");
            job.deps = vec!["2".to_string()];
            let mut dep = mk_job("2", "blocked");
            dep.note = Some("waiting on vendor".to_string());
            Snapshot {
                jobs: vec![job, dep],
                ..Snapshot::default()
            }
        };
        let missing = {
            let mut job = mk_job("1", "open");
            job.deps = vec!["9".to_string()];
            Snapshot {
                jobs: vec![job],
                ..Snapshot::default()
            }
        };
        let collision = {
            let mut a = mk_job("1", "claimed");
            a.files = vec!["a.py".to_string()];
            let mut b = mk_job("2", "claimed");
            b.files = vec!["a.py".to_string()];
            Snapshot {
                jobs: vec![a, b],
                ..Snapshot::default()
            }
        };
        let attempt = {
            let mut job = mk_job("1", "open");
            job.attempts = 2;
            job.max_attempts = Some(3);
            Snapshot {
                jobs: vec![job],
                ..Snapshot::default()
            }
        };
        let silent = Snapshot {
            jobs: vec![mk_job("1", "claimed")],
            messages: vec![msg("hi", 6000)],
            ..Snapshot::default()
        };
        let rejected = Snapshot {
            jobs: vec![mk_job("1", "open")],
            messages: vec![raw_msg("worker: REJECTED:1 BAD signed_by=overseer rejected_by=worker")],
            ..Snapshot::default()
        };
        let budget = Snapshot {
            budgets: vec![BudgetEntry {
                lane: "spark".to_string(),
                spent: Some(80),
                cap: Some(100),
            }],
            ..Snapshot::default()
        };
        vec![
            (snap(vec![stall], vec!["hana"], vec!["pax"]), "presence-stall"),
            (snap(vec![progress], vec!["pax"], vec!["pax"]), "progress-stall"),
            (Snapshot { jobs: vec![lease], ..Snapshot::default() }, "lease-risk"),
            (dead, "dead-dep"),
            (missing, "missing-dep"),
            (collision, "file-collision"),
            (attempt, "attempt-warning"),
            (silent, "silent-room"),
            (rejected, "rejected-dispatch"),
            (budget, "budget-warning"),
        ]
    }

    #[test]
    fn detector_coverage_test_registry_runs_all_nine_detectors() {
        assert_eq!(DETECTORS.len(), 10);
        let mut seen: HashSet<String> = HashSet::new();
        for (snapshot, _kind) in coverage_positives() {
            for alert in tick_at(&snapshot, 10000) {
                seen.insert(alert.kind);
            }
        }
        for (_snapshot, kind) in coverage_positives() {
            assert!(seen.contains(kind), "registry must run {}", kind);
        }
    }

    #[test]
    fn detector_coverage_test_presence_stall_positive_and_negative() {
        let stalled = snap(vec![claimed("7", "pax", 9340)], vec!["hana"], vec!["pax"]);
        assert_eq!(detect_presence_stall(&stalled, 10000, &th()).len(), 1);
        let present = snap(vec![claimed("7", "pax", 9340)], vec!["pax"], vec!["pax"]);
        assert!(detect_presence_stall(&present, 10000, &th()).is_empty());
    }

    #[test]
    fn detector_coverage_test_progress_stall_positive_and_negative() {
        let stuck = snap(vec![claimed("7", "pax", 9340)], vec!["pax"], vec!["pax"]);
        assert_eq!(detect_progress_stall(&stuck, 10000, &th()).len(), 1);
        let fresh = snap(vec![claimed("7", "pax", 9900)], vec!["pax"], vec!["pax"]);
        assert!(detect_progress_stall(&fresh, 10000, &th()).is_empty());
    }

    #[test]
    fn detector_coverage_test_lease_risk_positive_and_negative() {
        let mut at_risk = mk_job("7", "claimed");
        at_risk.claim = Some("pax".to_string());
        at_risk.lease_until = Some(10200);
        let snapshot = Snapshot {
            jobs: vec![at_risk],
            ..Snapshot::default()
        };
        assert_eq!(detect_lease_risk(&snapshot, 10000, &th()).len(), 1);
        let mut renewed = mk_job("7", "claimed");
        renewed.claim = Some("pax".to_string());
        renewed.lease_until = Some(10200);
        renewed.heartbeat = Some(9950);
        let snapshot = Snapshot {
            jobs: vec![renewed],
            ..Snapshot::default()
        };
        assert!(detect_lease_risk(&snapshot, 10000, &th()).is_empty());
    }

    #[test]
    fn detector_coverage_test_dead_dep_positive_and_negative() {
        let dead = dead_dep_snapshot("blocked", Some("waiting on vendor"), "open");
        let got = detect_dead_dep(&dead, 10000, &th());
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "dead-dep");
        let live = dead_dep_snapshot("open", Some("waiting on vendor"), "open");
        assert!(detect_dead_dep(&live, 10000, &th()).is_empty());
    }

    #[test]
    fn detector_coverage_test_missing_dep_positive_and_negative() {
        let dangling = missing_dep_snapshot(vec!["9"], vec![], "open");
        let got = detect_missing_dep(&dangling, 10000, &th());
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "missing-dep");
        let found = missing_dep_snapshot(vec!["2"], vec![mk_job("2", "open")], "open");
        assert!(detect_missing_dep(&found, 10000, &th()).is_empty());
    }

    #[test]
    fn detector_coverage_test_file_collision_positive_and_negative() {
        let clash = collision_snapshot(vec![
            collision_job("1", "pax", "a.py"),
            collision_job("2", "rowan", "a.py"),
        ]);
        let got = detect_file_collision(&clash, 10000, &th());
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "file-collision");
        let disjoint = collision_snapshot(vec![
            collision_job("1", "pax", "a.py"),
            collision_job("2", "rowan", "b.py"),
        ]);
        assert!(detect_file_collision(&disjoint, 10000, &th()).is_empty());
    }

    #[test]
    fn detector_coverage_test_attempt_exhaustion_positive_and_negative() {
        let warning = Snapshot {
            jobs: vec![attempt_job(2, Some(3), "open")],
            ..Snapshot::default()
        };
        let got = detect_attempt_exhaustion(&warning, 10000, &th());
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "attempt-warning");
        let spent = Snapshot {
            jobs: vec![attempt_job(3, Some(3), "open")],
            ..Snapshot::default()
        };
        let got = detect_attempt_exhaustion(&spent, 10000, &th());
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "attempt-exhaustion");
        let healthy = Snapshot {
            jobs: vec![attempt_job(0, Some(3), "open")],
            ..Snapshot::default()
        };
        assert!(detect_attempt_exhaustion(&healthy, 10000, &th()).is_empty());
    }

    #[test]
    fn detector_coverage_test_silent_room_positive_and_negative() {
        let quiet = Snapshot {
            jobs: vec![mk_job("1", "claimed")],
            messages: vec![msg("hi", 6000)],
            ..Snapshot::default()
        };
        let got = detect_silent_room(&quiet, 10000, &th());
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "silent-room");
        assert_eq!(got[0].severity, "info");
        let noisy = Snapshot {
            jobs: vec![mk_job("1", "claimed")],
            messages: vec![msg("hi", 9900)],
            ..Snapshot::default()
        };
        assert!(detect_silent_room(&noisy, 10000, &th()).is_empty());
    }

    #[test]
    fn detector_coverage_test_rejected_dispatch_positive_and_negative() {
        let refused = Snapshot {
            jobs: vec![mk_job("1", "open")],
            messages: vec![raw_msg("worker: REJECTED:1 BAD signed_by=overseer rejected_by=worker")],
            ..Snapshot::default()
        };
        let got = detect_rejected_dispatch(&refused, 10000, &th());
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "rejected-dispatch");
        assert_eq!(got[0].severity, "critical");
        assert_eq!(got[0].dedupe_key, "rejected-dispatch:1:BAD");
        assert_eq!(got[0].job.as_deref(), Some("1"));
        assert_eq!(got[0].verdict.as_deref(), Some("BAD"));
        let clean = Snapshot {
            jobs: vec![mk_job("1", "open")],
            messages: vec![msg("all quiet", 9000)],
            ..Snapshot::default()
        };
        // Dict-shaped message text is "all quiet" (no ts needed
        // here); use a raw string form for the clean case too.
        let clean = Snapshot {
            messages: vec![raw_msg("all quiet")],
            ..clean
        };
        assert!(detect_rejected_dispatch(&clean, 10000, &th()).is_empty());
        let malformed = Snapshot {
            messages: vec![
                raw_msg("worker: REJECTED:abc BAD"),
                raw_msg("worker: REJECTED:2 OK signed_by=x rejected_by=y"),
                raw_msg("worker: REJECTED"),
            ],
            ..Snapshot::default()
        };
        assert!(detect_rejected_dispatch(&malformed, 10000, &th()).is_empty());
    }

    #[test]
    fn detector_coverage_test_budget_warning_positive_and_negative() {
        let warned = Snapshot {
            budgets: vec![BudgetEntry {
                lane: "spark".to_string(),
                spent: Some(80),
                cap: Some(100),
            }],
            ..Snapshot::default()
        };
        let got = detect_budget_warning(&warned, 10000, &th());
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "budget-warning");
        assert_eq!(got[0].severity, "warning");
        assert_eq!(got[0].lane.as_deref(), Some("spark"));
        assert_eq!(got[0].dedupe_key, "budget-warning:spark");
        let under = Snapshot {
            budgets: vec![BudgetEntry {
                lane: "spark".to_string(),
                spent: Some(70),
                cap: Some(100),
            }],
            ..Snapshot::default()
        };
        assert!(detect_budget_warning(&under, 10000, &th()).is_empty());
        let capped = Snapshot {
            budgets: vec![BudgetEntry {
                lane: "spark".to_string(),
                spent: Some(100),
                cap: Some(100),
            }],
            ..Snapshot::default()
        };
        assert!(detect_budget_warning(&capped, 10000, &th()).is_empty());
    }

    // ---- WalkOnTrackingTest ----

    fn walk_on_snapshot() -> Snapshot {
        Snapshot {
            jobs: vec![claimed("7", "walkon", 9340)],
            presence: vec!["hana".to_string()],
            caps: vec!["hana".to_string()],
            ..Snapshot::default()
        }
    }

    #[test]
    fn walk_on_tracking_test_unknown_claimer_yields_tracking_record() {
        let got = detect_walk_on_workers(&walk_on_snapshot(), 10000);
        assert_eq!(got.len(), 1);
        let record = &got[0];
        assert_eq!(record.kind, "walk-on-worker");
        assert_eq!(record.nick, "walkon");
        assert_eq!(record.job, "7");
        assert_eq!(record.last_progress_age_seconds, Some(660));
        assert_eq!(record.last_progress_age_minutes, Some(11));
        assert_eq!(record.tracked_from, "jobs");
    }

    #[test]
    fn walk_on_tracking_test_tracking_is_not_an_alert() {
        // The record rides the tracking function, never tick:
        // the walk-on fixture still yields zero alerts. The
        // tracking function cannot be registered at all — it
        // has a different signature from DetectorFn, so it is
        // not (and cannot be) a member of DETECTORS.
        assert!(tick_at(&walk_on_snapshot(), 10000).is_empty());
        assert_eq!(DETECTORS.len(), 10);
    }

    #[test]
    fn walk_on_tracking_test_registered_claimer_is_not_tracked() {
        let mut snapshot = walk_on_snapshot();
        snapshot.caps = vec!["walkon".to_string(), "hana".to_string()];
        assert!(detect_walk_on_workers(&snapshot, 10000).is_empty());
    }

    #[test]
    fn walk_on_tracking_test_open_job_is_not_tracked() {
        let mut snapshot = walk_on_snapshot();
        snapshot.jobs[0].status = "open".to_string();
        assert!(detect_walk_on_workers(&snapshot, 10000).is_empty());
    }

    #[test]
    fn walk_on_tracking_test_present_walk_on_is_still_tracked() {
        let mut snapshot = walk_on_snapshot();
        snapshot.presence = vec!["walkon".to_string(), "hana".to_string()];
        let got = detect_walk_on_workers(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].nick, "walkon");
    }

    #[test]
    fn walk_on_tracking_test_no_timestamp_never_invents_an_age() {
        let mut snapshot = walk_on_snapshot();
        snapshot.jobs[0].last_activity = None;
        let got = detect_walk_on_workers(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].last_progress_age_seconds, None);
        assert_eq!(got[0].last_progress_age_minutes, None);
    }

    #[test]
    fn walk_on_tracking_test_malformed_sections_yield_no_crash() {
        let value = Value::Map(vec![
            ("jobs".to_string(), Value::Str("not-a-list".to_string())),
            ("caps".to_string(), Value::Str("not-a-dict".to_string())),
        ]);
        assert!(detect_walk_on_workers(&Snapshot::from_value(&value), 10000).is_empty());
        assert!(detect_walk_on_workers(&Snapshot::from_value(&Value::Null), 10000).is_empty());
    }

    #[test]
    fn walk_on_tracking_test_stall_detection_still_works_alongside_tracking() {
        let mut snapshot = walk_on_snapshot();
        let mut registered = claimed("8", "pax", 9340);
        registered.title = "registered job".to_string();
        snapshot.jobs.push(registered);
        snapshot.caps = vec!["pax".to_string(), "hana".to_string()];
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "presence-stall");
        assert_eq!(got[0].nick.as_deref(), Some("pax"));
        let tracked = detect_walk_on_workers(&snapshot, 10000);
        assert_eq!(tracked.len(), 1);
        assert_eq!(tracked[0].nick, "walkon");
    }

    // ---- SeverityMappingTest ----

    fn severity_positives() -> Vec<(Snapshot, &'static str)> {
        let mut positives = coverage_positives();
        let spent = Snapshot {
            jobs: vec![attempt_job(3, Some(3), "open")],
            ..Snapshot::default()
        };
        positives.push((spent, "attempt-exhaustion"));
        positives
    }

    #[test]
    fn severity_mapping_test_table_covers_every_detector_kind() {
        let mut emitted: HashSet<String> = HashSet::new();
        for (snapshot, _kind) in severity_positives() {
            for alert in tick_at(&snapshot, 10000) {
                emitted.insert(alert.kind);
            }
        }
        let table: HashSet<String> = SEVERITY_BY_KIND
            .iter()
            .map(|(k, _)| k.to_string())
            .collect();
        assert_eq!(table, emitted);
    }

    #[test]
    fn severity_mapping_test_table_values_are_valid_severities() {
        // Python reads istore.ALERT_SEVERITIES here; the valid
        // set is the same three literals, embedded locally.
        for (_kind, severity) in SEVERITY_BY_KIND {
            assert!(["critical", "warning", "info"].contains(severity));
        }
    }

    #[test]
    fn severity_mapping_test_every_detector_emits_its_table_severity() {
        for (snapshot, kind) in severity_positives() {
            let got: Vec<Alert> = tick_at(&snapshot, 10000)
                .into_iter()
                .filter(|a| a.kind == kind)
                .collect();
            assert_eq!(got.len(), 1, "{} fixture", kind);
            assert_eq!(got[0].severity, severity_by_kind(kind).unwrap());
        }
    }

    #[test]
    fn severity_mapping_test_mapping_matches_the_lane_plan_rule() {
        for kind in ["presence-stall", "progress-stall", "dead-dep", "missing-dep", "file-collision"] {
            assert_eq!(severity_by_kind(kind), Some("critical"));
        }
        for kind in ["lease-risk", "attempt-warning", "budget-warning"] {
            assert_eq!(severity_by_kind(kind), Some("warning"));
        }
        assert_eq!(severity_by_kind("silent-room"), Some("info"));
        assert_eq!(severity_by_kind("attempt-exhaustion"), Some("critical"));
    }

    // ---- ClockSkewTest ----

    fn clock_skew_snapshot(server_time: Option<Value>) -> Snapshot {
        let mut snapshot = snap(vec![claimed("7", "pax", 9300)], vec!["hana"], vec!["pax"]);
        snapshot.server_time = server_time;
        snapshot
    }

    #[test]
    fn clock_skew_test_server_time_beats_skewed_wall_clock() {
        // Wall clock says 9500 (age 200s, fresh); the server
        // says 10000 (age 700s, stalled). The alert must come
        // from the server's clock, with the server's timestamp.
        let snapshot = clock_skew_snapshot(Some(Value::Int(10000)));
        let (now, source) = resolve_tick_now_with_clock(&snapshot, None, 9500);
        assert_eq!((now, source), (10000, "server_time"));
        let got = tick_at(&snapshot, 10000);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "presence-stall");
        assert_eq!(got[0].last_progress_age_seconds, Some(700));
        assert_eq!(got[0].created_at, 10000);
    }

    #[test]
    fn clock_skew_test_explicit_now_beats_server_time() {
        let snapshot = clock_skew_snapshot(Some(Value::Int(10000)));
        assert!(tick_at(&snapshot, 9500).is_empty());
    }

    #[test]
    fn clock_skew_test_wall_clock_fallback_when_no_server_time() {
        // No server_time, no explicit now: the wall clock is
        // the tick clock. Use the live wall clock with a job
        // aged ~700s against it, and allow a few seconds of
        // test-run skew.
        let now = wall_clock_now();
        let mut snapshot = snap(vec![claimed("7", "pax", now - 700)], vec!["hana"], vec!["pax"]);
        snapshot.server_time = None;
        let got = tick_full(&snapshot, None, &th(), DETECTORS, None, None, None, None, None);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "presence-stall");
        let age = got[0].last_progress_age_seconds.unwrap();
        assert!((700..=705).contains(&age), "age: {}", age);
        assert!((now..=now + 5).contains(&got[0].created_at));
    }

    #[test]
    fn clock_skew_test_malformed_server_time_falls_back_to_wall_clock() {
        for bad in [Value::Str("not-a-time".to_string()), Value::Bool(true)] {
            let snapshot = clock_skew_snapshot(Some(bad));
            let (now, source) = resolve_tick_now_with_clock(&snapshot, None, 10000);
            assert_eq!((now, source), (10000, "wall_clock"));
        }
    }

    #[test]
    fn clock_skew_test_string_and_time_pair_server_time_forms() {
        for form in [
            Value::Str("10000".to_string()),
            Value::List(vec![Value::Int(10000), Value::Int(500000)]),
        ] {
            let snapshot = clock_skew_snapshot(Some(form));
            let (now, source) = resolve_tick_now_with_clock(&snapshot, None, 9500);
            assert_eq!((now, source), (10000, "server_time"));
            let got = tick_at(&snapshot, 10000);
            assert_eq!(got.len(), 1);
            assert_eq!(got[0].created_at, 10000);
        }
    }

    #[test]
    fn clock_skew_test_resolve_tick_now_reports_its_source() {
        assert_eq!(
            resolve_tick_now_with_clock(&Snapshot::default(), Some(123), 9500),
            (123, "explicit")
        );
        assert_eq!(
            resolve_tick_now_with_clock(&clock_skew_snapshot(Some(Value::Int(10000))), None, 9500),
            (10000, "server_time")
        );
        assert_eq!(
            resolve_tick_now_with_clock(&Snapshot::default(), None, 9500),
            (9500, "wall_clock")
        );
    }

    #[test]
    fn clock_skew_test_detector_ages_use_injected_clock_not_wall_clock() {
        let snapshot = clock_skew_snapshot(None);
        let got = detect_presence_stall(&snapshot, 10000, &th());
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].last_progress_age_seconds, Some(700));
    }

    // ---- LockedThresholdsTest ----

    #[test]
    fn locked_thresholds_test_int022_locked_threshold_table() {
        let thresholds = Thresholds::default();
        assert_eq!(thresholds.stall_minutes, 10);
        assert_eq!(thresholds.progress_stall_minutes, 10);
        assert_eq!(thresholds.lease_risk_window_minutes, 5);
        assert_eq!(thresholds.lease_risk_quiet_minutes, 2);
        assert_eq!(thresholds.alert_dedupe_cooldown_minutes, 30);
        assert_eq!(thresholds.silent_room_minutes, 60);
        assert_eq!(thresholds.watchdog_beat_ttl_seconds, 300);
        assert_eq!(thresholds.tick_page_size, 1000);
        assert_eq!(thresholds.tick_max_messages, 1000);
    }

    // ---- Journal watch & restart notes (from watchdog.py, OS-037/OS-034) ----
    // These functions have no direct tests in
    // test_intel_watchdog.py (their tests live in the watchdog
    // service test file, another worker's scope); the cases
    // below mirror the source's documented behavior.

    fn journal_entry(unit: &str, message: &str, priority: Option<i64>) -> JournalEntry {
        JournalEntry {
            unit: unit.to_string(),
            message: message.to_string(),
            priority,
        }
    }

    #[test]
    fn journal_test_relay_err_priority_is_a_failure() {
        assert!(journal_entry_is_failure(&journal_entry("relay-worker", "started", Some(3))));
        assert!(journal_entry_is_failure(&journal_entry("relay-worker", "started", Some(0))));
    }

    #[test]
    fn journal_test_relay_info_and_non_relay_failures_are_quiet() {
        assert!(!journal_entry_is_failure(&journal_entry("relay-worker", "started ok", Some(6))));
        assert!(!journal_entry_is_failure(&journal_entry("sshd", "failed to start", Some(3))));
        assert!(!journal_entry_is_failure(&journal_entry("relay-worker", "healthy", Some(6))));
    }

    #[test]
    fn journal_test_systemd_failure_phrasing_fires_at_benign_priority() {
        for message in [
            "relay-worker failed with result 'exit-code'",
            "Main process exited, code=exited",
            "Failed to start Relay worker.",
            "Unit entered failed state.",
        ] {
            assert!(
                journal_entry_is_failure(&journal_entry("relay-worker", message, Some(6))),
                "message: {}",
                message
            );
        }
    }

    #[test]
    fn journal_test_parse_skips_blank_bad_and_unitless_lines() {
        let text = "\nnot json\n{\"_SYSTEMD_UNIT\": \"relay-worker\", \"MESSAGE\": \"failed to start\", \"PRIORITY\": \"3\"}\n{\"MESSAGE\": \"orphan failure\"}\n";
        let entries = parse_journal_entries(text);
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].unit, "relay-worker");
        assert_eq!(entries[0].priority, Some(3));
    }

    #[test]
    fn journal_test_failures_group_by_unit_with_count_and_truncation() {
        let long_message = "x".repeat(400);
        let entries = vec![
            journal_entry("relay-worker", "failed to start", Some(3)),
            journal_entry("relay-worker", "second failure", Some(3)),
            journal_entry("relay-other", "main process exited", Some(6)),
        ];
        let alerts = detect_journal_failures(&entries, 10000);
        assert_eq!(alerts.len(), 2);
        let worker = &alerts[0];
        assert_eq!(worker.kind, "system-failure");
        assert_eq!(worker.severity, "critical");
        assert_eq!(worker.subjects, vec!["relay-worker".to_string()]);
        assert_eq!(worker.unit.as_deref(), Some("relay-worker"));
        assert!(worker.system_alert);
        assert_eq!(worker.failure_count, Some(2));
        assert!(worker.nick.is_none());
        assert!(worker.job.is_none());
        assert_eq!(worker.dedupe_key, "system-failure:relay-worker");
        assert!(worker.suggested_fix.contains("journalctl -u relay-worker"));
        assert!(worker.explanation.contains("failed to start"));
        let long_entries = vec![journal_entry("relay-worker", &long_message, Some(3))];
        let long_alerts = detect_journal_failures(&long_entries, 10000);
        let excerpt = long_alerts[0]
            .explanation
            .strip_prefix("System unit relay-worker failed: ")
            .unwrap();
        assert_eq!(excerpt.chars().count(), 300);
        assert!(excerpt.ends_with("..."));
        assert_eq!(long_alerts[0].journal_message.as_deref(), Some(long_message.as_str()));
    }

    #[test]
    fn journal_test_watch_tick_emit_failure_does_not_hide_next_unit() {
        let text = "{\"_SYSTEMD_UNIT\": \"relay-a\", \"MESSAGE\": \"failed to start\", \"PRIORITY\": \"3\"}\n{\"_SYSTEMD_UNIT\": \"relay-b\", \"MESSAGE\": \"failed to start\", \"PRIORITY\": \"3\"}\n";
        let mut boom = |_alert: &Alert| panic!("emit down");
        let alerts = journal_watch_tick_text(
            text,
            Some(10000),
            Some(&mut boom as &mut dyn FnMut(&Alert)),
        );
        assert_eq!(alerts.len(), 2);
    }

    #[test]
    fn journal_test_value_and_text_entry_shapes() {
        let value = Value::Map(vec![
            ("unit".to_string(), Value::Str("relay-worker".to_string())),
            ("message".to_string(), Value::Str("failed to start".to_string())),
            ("priority".to_string(), Value::Str("bad".to_string())),
        ]);
        assert!(journal_entry_is_failure_value(&value));
        assert!(!journal_entry_is_failure_value(&Value::Str("not json".to_string())));
        assert!(journal_entry_fields_from_text("  ").is_none());
    }

    #[test]
    fn restart_note_test_worker_restart_is_info_not_a_stall() {
        let note = restart_event_note("pax", "7", 10000, Some(30)).unwrap();
        assert_eq!(note.kind, "worker-restart");
        assert_eq!(note.severity, "info");
        assert!(note.explanation.contains("after 30s down"));
        assert_eq!(note.dedupe_key, "worker-restart:pax:7");
        assert_eq!(format_announcement(&note), None);
        let brief = restart_event_note("pax", "7", 10000, None).unwrap();
        assert!(brief.explanation.contains("after a brief absence"));
        assert_eq!(brief.downtime_seconds, None);
    }

    #[test]
    fn restart_note_test_missing_nick_or_job_is_an_error() {
        assert!(restart_event_note("", "7", 10000, None).is_err());
        assert!(restart_event_note("pax", "", 10000, None).is_err());
    }

    // ---- JSON parser / snapshot conversion helpers ----

    #[test]
    fn json_test_snapshot_from_json_text_and_non_object_rejected() {
        let snapshot = Snapshot::from_json_text(
            r#"{"jobs": [{"id": 7, "status": "claimed", "claim": "pax", "claimed_at": 9340, "deps": "1, 2", "files": ["a.py", "a.py"]}], "presence": ["hana"], "caps": {"pax": {}}, "server_time": "10000"}"#,
        )
        .unwrap();
        assert_eq!(snapshot.jobs.len(), 1);
        assert_eq!(snapshot.jobs[0].id.as_deref(), Some("7"));
        assert_eq!(snapshot.jobs[0].deps, vec!["1".to_string(), "2".to_string()]);
        assert_eq!(snapshot.jobs[0].files, vec!["a.py".to_string()]);
        assert_eq!(parse_server_time(snapshot.server_time.as_ref().unwrap()), Some(10000));
        assert!(Snapshot::from_json_text("[1, 2]").is_err());
        assert!(Snapshot::from_json_text("{bad json").is_err());
    }

    #[test]
    fn json_test_last_activity_prefers_progress_fields_in_order() {
        let value = Value::Map(vec![(
            "jobs".to_string(),
            Value::List(vec![Value::Map(vec![
                ("id".to_string(), Value::Str("7".to_string())),
                ("status".to_string(), Value::Str("claimed".to_string())),
                ("claimed_at".to_string(), Value::Int(9000)),
                ("last_progress_at".to_string(), Value::Int(9950)),
            ])]),
        )]);
        let snapshot = Snapshot::from_value(&value);
        assert_eq!(snapshot.jobs[0].last_activity, Some(9950));
    }

    #[test]
    #[should_panic(expected = "unknown explanation template")]
    fn render_test_unknown_template_panics_like_python_value_error() {
        render_explanation("no-such-template", &[]);
    }
}
