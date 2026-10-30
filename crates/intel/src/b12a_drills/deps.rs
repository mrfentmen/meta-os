//! `deps` — the external surfaces the B12a modules call, as traits.
//!
//! The Python drills/checks import sibling modules owned by other
//! batches: `intel.watchdog` + `intel.thresholds` (B21, crate
//! `os-supervisor`), `intel.gate` / `intel.store` / `intel.capability`
//! / `intel.integration` / `intel.ladder` (B09, `b09_core`),
//! `intel.baton` / `intel.brief` / `intel.dispatch` / `intel.push` /
//! `intel.wake` (B10, `b10_brief`), the Spark client (B11), and
//! `intel.trust` / `intel.timer_sweep` (B14). Those modules are not
//! in this branch yet, so — exactly like the Python sources, which
//! reach them through patchable module attributes (the e2e loops
//! run on `unittest.mock` seams) — the ports here take the surface
//! as a trait object with the Python call shapes preserved. When
//! the owning batches land, wiring is one adapter per trait.
//!
//! Nothing in this file implements a sibling module's behavior.

use super::value::Value;

/// `intel/thresholds.py` (B21) — the constants the fixtures read.
/// Values are the locked defaults; `from_env` mirrors the source's
/// `_env_int` rule (strip, parse, below-minimum falls back silently).
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Thresholds {
    pub stall_minutes: i64,
    pub progress_stall_minutes: i64,
    pub lease_risk_window_minutes: i64,
    pub lease_risk_quiet_minutes: i64,
    pub alert_dedupe_cooldown_minutes: i64,
    pub silent_room_minutes: i64,
    pub watchdog_beat_ttl_seconds: i64,
    pub tick_page_size: i64,
    pub tick_max_messages: i64,
    pub watchman_stale_minutes: i64,
    pub timer_sweep_interval_seconds: i64,
    pub lease_default_seconds: i64,
}

fn env_int(name: &str, default: i64, minimum: i64) -> i64 {
    let raw = match std::env::var(name) {
        Ok(v) => v,
        Err(_) => return default,
    };
    parse_env_int(&raw, default, minimum)
}

fn parse_env_int(raw: &str, default: i64, minimum: i64) -> i64 {
    let raw = raw.trim();
    if raw.is_empty() {
        return default;
    }
    match raw.parse::<i64>() {
        Ok(value) if value >= minimum => value,
        _ => default,
    }
}

fn env_int_map(vars: &[(String, String)], name: &str, default: i64, minimum: i64) -> i64 {
    match vars.iter().find(|(n, _)| n == name) {
        Some((_, v)) => parse_env_int(v, default, minimum),
        None => default,
    }
}

impl Thresholds {
    pub fn locked() -> Self {
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
            watchman_stale_minutes: 5,
            timer_sweep_interval_seconds: 300,
            lease_default_seconds: 1800,
        }
    }

    /// Thresholds resolved from an explicit env map — the
    /// demo_thresholds_dropin step-2 seat (the source resolves
    /// the real thresholds import in a subprocess with exactly
    /// these vars). Same names, defaults, and minimums as
    /// `from_env`.
    pub fn from_env_map(vars: &[(String, String)]) -> Self {
        Thresholds {
            stall_minutes: env_int_map(vars, "WATCHDOG_STALL_MINUTES", 10, 0),
            progress_stall_minutes: env_int_map(
                vars,
                "WATCHDOG_PROGRESS_STALL_MINUTES",
                10,
                0,
            ),
            lease_risk_window_minutes: env_int_map(
                vars,
                "WATCHDOG_LEASE_RISK_WINDOW_MINUTES",
                5,
                0,
            ),
            lease_risk_quiet_minutes: env_int_map(
                vars,
                "WATCHDOG_LEASE_RISK_QUIET_MINUTES",
                2,
                0,
            ),
            alert_dedupe_cooldown_minutes: env_int_map(
                vars,
                "WATCHDOG_ALERT_DEDUPE_COOLDOWN_MINUTES",
                30,
                0,
            ),
            silent_room_minutes: env_int_map(vars, "WATCHDOG_SILENT_ROOM_MINUTES", 60, 0),
            watchdog_beat_ttl_seconds: env_int_map(
                vars,
                "WATCHDOG_BEAT_TTL_SECONDS",
                300,
                1,
            ),
            tick_page_size: env_int_map(vars, "WATCHDOG_TICK_PAGE_SIZE", 1000, 1),
            tick_max_messages: env_int_map(vars, "WATCHDOG_TICK_MAX_MESSAGES", 1000, 1),
            watchman_stale_minutes: env_int_map(
                vars,
                "WATCHDOG_WATCHMAN_STALE_MINUTES",
                5,
                0,
            ),
            timer_sweep_interval_seconds: env_int_map(
                vars,
                "WATCHDOG_TIMER_SWEEP_INTERVAL_SECONDS",
                300,
                1,
            ),
            lease_default_seconds: 1800,
        }
    }

    pub fn from_env() -> Self {
        Thresholds {
            stall_minutes: env_int("WATCHDOG_STALL_MINUTES", 10, 0),
            progress_stall_minutes: env_int("WATCHDOG_PROGRESS_STALL_MINUTES", 10, 0),
            lease_risk_window_minutes: env_int("WATCHDOG_LEASE_RISK_WINDOW_MINUTES", 5, 0),
            lease_risk_quiet_minutes: env_int("WATCHDOG_LEASE_RISK_QUIET_MINUTES", 2, 0),
            alert_dedupe_cooldown_minutes: env_int(
                "WATCHDOG_ALERT_DEDUPE_COOLDOWN_MINUTES",
                30,
                0,
            ),
            silent_room_minutes: env_int("WATCHDOG_SILENT_ROOM_MINUTES", 60, 0),
            watchdog_beat_ttl_seconds: env_int("WATCHDOG_BEAT_TTL_SECONDS", 300, 1),
            tick_page_size: env_int("WATCHDOG_TICK_PAGE_SIZE", 1000, 1),
            tick_max_messages: env_int("WATCHDOG_TICK_MAX_MESSAGES", 1000, 1),
            watchman_stale_minutes: env_int("WATCHDOG_WATCHMAN_STALE_MINUTES", 5, 0),
            timer_sweep_interval_seconds: env_int(
                "WATCHDOG_TIMER_SWEEP_INTERVAL_SECONDS",
                300,
                1,
            ),
            lease_default_seconds: 1800,
        }
    }
}

/// One entry of `intel.watchdog.DETECTORS` (B21). The boot
/// self-check drill removes one entry and swaps one for a raiser,
/// so the list is data here, not a fixed call.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Detector {
    Named(&'static str),
    /// Stands in for a detector callable that raises: `tick`
    /// swallows a raising detector (one broken detector must not
    /// blind the rest), so it contributes no alerts.
    Raising(&'static str),
}

impl Detector {
    pub fn name(&self) -> &'static str {
        match self {
            Detector::Named(n) => n,
            Detector::Raising(n) => n,
        }
    }
}

/// The DETECTORS list of `intel/watchdog.py`, in order.
pub fn default_detectors() -> Vec<Detector> {
    vec![
        Detector::Named("detect_presence_stall"),
        Detector::Named("detect_progress_stall"),
        Detector::Named("detect_lease_risk"),
        Detector::Named("detect_dead_dep"),
        Detector::Named("detect_missing_dep"),
        Detector::Named("detect_file_collision"),
        Detector::Named("detect_attempt_exhaustion"),
        Detector::Named("detect_silent_room"),
        Detector::Named("detect_rejected_dispatch"),
        Detector::Named("detect_budget_warning"),
    ]
}

/// `intel.watchdog` (B21) — the tick surface the drills call.
pub trait Watchdog {
    /// `watchdog.tick(snapshot, now)` over the default DETECTORS.
    fn tick(&self, snapshot: &Value, now: Option<i64>) -> Vec<Value>;
    /// `watchdog.tick` over an explicit detector list (the boot
    /// self-check drill edits the list to break a detector).
    fn tick_with(
        &self,
        snapshot: &Value,
        now: Option<i64>,
        detectors: &[Detector],
    ) -> Vec<Value>;
    /// `watchdog.announcements_for(alerts)`.
    fn announcements_for(&self, alerts: &[Value]) -> Vec<String>;
    /// `watchdog.resolve_alerts_for_job(jobs, job_id, now)` —
    /// flip this job's open alert records to resolved when the
    /// underlying job state cleared; returns the resolved ids.
    /// The jobs surface is the e2e seam (in the source the jobs
    /// module itself rides in this seat).
    fn resolve_alerts_for_job(
        &self,
        jobs: &dyn super::e2e1::Integration,
        job_id: &str,
        now: Option<i64>,
    ) -> Vec<String>;
    /// `watchdog.tick(snapshot, now, polish_client=client)` —
    /// the Spark polish pass over template explanations
    /// (INT-008 stage 5 ticks with and without it).
    fn tick_with_polish(
        &self,
        snapshot: &Value,
        now: Option<i64>,
        polish: &dyn SparkClient,
    ) -> Vec<Value>;
    /// `watchdog.tick(snapshot, now, emit=callback)` — every
    /// alert also rides the emit callback (INT-010 stage 4).
    fn tick_emit(
        &self,
        snapshot: &Value,
        now: Option<i64>,
        emit: &mut dyn FnMut(&Value),
    ) -> Vec<Value>;
    /// `watchdog.format_announcement(alert)` — the WDG-015
    /// announcement line for one alert, when it has one.
    fn format_announcement(&self, alert: &Value) -> Option<String>;
    /// `watchdog.journal_watch_tick(journal_text, now, emit)` —
    /// one journal-watch loop iteration over journalctl JSON
    /// lines (OS-037); SYSTEM alerts for relay-unit failures.
    fn journal_watch_tick(
        &self,
        journal_text: &str,
        now: Option<i64>,
        emit: Option<&mut dyn FnMut(&Value)>,
    ) -> Vec<Value>;
    /// `watchdog.restart_event_note(nick, job_id, now,
    /// downtime_seconds=None)` — the worker-restart event note
    /// (OS-034): an info record, never an announcement.
    fn restart_event_note(
        &self,
        nick: &str,
        job_id: &str,
        now: i64,
        downtime_seconds: Option<i64>,
    ) -> Value;
    /// `watchdog.detect_progress_stall(snapshot, now)` — the
    /// WDG-003 detector on its own.
    fn detect_progress_stall(&self, snapshot: &Value, now: Option<i64>) -> Vec<Value>;
    /// `watchdog.detect_presence_stall(snapshot, now)` — the
    /// WDG-002 detector on its own.
    fn detect_presence_stall(&self, snapshot: &Value, now: Option<i64>) -> Vec<Value>;
}

/// The `intel.timer_sweep` surface (B14): the timer fallback
/// sweep's decision layer — computes the claim set a correct
/// sweep must produce; wakes nobody itself.
pub trait TimerSweep {
    /// `timer_sweep.sweep_cycle(jobs, now, watchman_alive,
    /// sweep_interval_seconds=..., last_sweep_at=...,
    /// sweep_ledger=..., local_agents=...)` -> the cycle note.
    /// `watchman_alive` None is the unknown state: hold.
    fn sweep_cycle(
        &self,
        jobs: &Value,
        now: i64,
        watchman_alive: Option<bool>,
        sweep_interval_seconds: i64,
        last_sweep_at: Option<i64>,
        sweep_ledger: &[String],
        local_agents: &[String],
    ) -> Value;
    /// `timer_sweep.sweep_brief_lines(note)`.
    fn sweep_brief_lines(&self, note: &Value) -> Vec<String>;
}

/// The `jobs._sign_job_v2` surface (B16): HMAC-SHA256 v2 job
/// signing. Secrets travel as hex of the raw digest bytes.
pub trait JobsSign {
    /// `jobs._sign_job_v2(secret, job_id, sig_kid, fields,
    /// spec)` — fields in the signed order (title, accept,
    /// branch, base, room, created_at, expires_at, nonce).
    fn sign_job_v2(
        &self,
        secret_hex: &str,
        job_id: &str,
        sig_kid: &str,
        fields: &Value,
        spec: &str,
    ) -> String;
}

/// The `intel.trust` surface (B14): signature verification,
/// claim decisions, and the refusal journal tick.
pub trait Trust {
    /// `trust.verify_signature(job, keyring, now)` -> "OK" /
    /// "BAD" / "EXPIRED" / "UNSIGNED" / ... (the module's
    /// result vocabulary).
    fn verify_signature(
        &self,
        job: &Value,
        keyring: &[(String, String)],
        now: i64,
    ) -> String;
    /// `trust.claim_decision(job, trust_config, verify_result)`.
    fn claim_decision(&self, job: &Value, trust: &Value, verify_result: &str) -> Value;
    /// `trust.trust_tick(snapshot, journal, now, keyring=...)`
    /// — one refusal record per newly refused job.
    fn trust_tick(
        &self,
        snapshot: &Value,
        journal: &[Value],
        now: i64,
        keyring: &[(String, String)],
    ) -> Vec<Value>;
    /// `trust.refusal_note(job, decision)` — None when the
    /// decision is not a refusal.
    fn refusal_note(&self, job: &Value, decision: &Value) -> Option<String>;
    /// `trust.trust_brief_lines(records)`.
    fn trust_brief_lines(&self, records: &[Value]) -> Vec<String>;
    /// `trust.trust_events(records)` — the federation events.
    fn trust_events(&self, records: &[Value]) -> Vec<Value>;
}

/// The `intel.wake` surface (B10): judges fixture job and
/// agent records and composes the wake bundle; never starts
/// a real session.
pub trait Wake {
    /// `wake.wake_tick(jobs, agents, journal, now)` — one
    /// wake record per newly woken (job, agent) pair.
    /// Malformed entries yield nothing and never crash.
    fn wake_tick(
        &self,
        jobs: &Value,
        agents: &Value,
        journal: &[Value],
        now: i64,
    ) -> Vec<Value>;
    /// `wake.brief_lines(records)`.
    fn brief_lines(&self, records: &[Value]) -> Vec<String>;
}

/// The `intel.ladder` surface (B09): the self-repair ladder —
/// selects the rung from snapshot facts and journals the
/// decision; it never performs the rung and never mutates
/// the snapshot.
pub trait Ladder {
    /// `ladder.ladder_tick(snapshot, alerts, journal, now)` —
    /// new ladder-action records for stalls not already
    /// journaled.
    fn ladder_tick(
        &self,
        snapshot: &Value,
        alerts: &[Value],
        journal: &[Value],
        now: Option<i64>,
    ) -> Vec<Value>;
    /// `ladder.ladder_brief_lines(records)` — the brief lines.
    fn ladder_brief_lines(&self, records: &[Value]) -> Vec<String>;
}

/// `intel.spark_client` (B11) — the Spark client surface the
/// INT-008 drill exercises over a dead endpoint.
pub trait SparkClient {
    /// `SparkClient.complete(prompt, lane_feature=...)`;
    /// Err carries the SparkError message.
    fn complete(&self, prompt: &str, lane_feature: &str) -> Result<String, String>;
    /// `client.spent_usd` — the spend ledger total.
    fn spent_usd(&self) -> f64;
}

/// `intel.brief` (B10) — the compose/generate surface the
/// INT-008 drill calls directly (the e2e loops reach the same
/// module through the Integration seam).
pub trait BriefSurface {
    /// `brief.compose_brief(snapshot, kind, client, now)`.
    fn compose_brief(
        &self,
        snapshot: &Value,
        kind: &str,
        client: &dyn SparkClient,
        now: Option<i64>,
    ) -> String;
    /// `brief.compose_spark_brief(snapshot, kind, client)`.
    fn compose_spark_brief(
        &self,
        snapshot: &Value,
        kind: &str,
        client: &dyn SparkClient,
    ) -> String;
    /// `brief.brief_failure_line(reason)` — the canned line.
    fn brief_failure_line(&self, reason: &str) -> String;
    /// `brief.generate_brief(snapshot, room, kind, now,
    /// dry_run, client)` -> (text, record).
    fn generate_brief(
        &self,
        snapshot: &Value,
        room: &str,
        kind: &str,
        now: Option<i64>,
        dry_run: bool,
        client: &dyn SparkClient,
    ) -> (String, Value);
    /// `brief.recovery_line(recovery)` — the OS-127 boot-brief
    /// recovery line the power-cut drill reconciles through.
    fn recovery_line(&self, recovery: &Value) -> String;
}

/// `intel.dispatch` (B10) — the plan-from-Spark surface.
pub trait DispatchSurface {
    /// `dispatch.plan_from_spark(goal, complete)` -> (result,
    /// stderr): the source prints the endpoint-down warning to
    /// stderr inside the call; the seam returns it.
    fn plan_from_spark(
        &self,
        goal: &str,
        complete: &dyn Fn(&str) -> Result<String, String>,
    ) -> (Value, String);
}

/// `intel.store` (B09) — the WDG-010 record builder the
/// INT-010 drill validates a detector dict through.
pub trait AlertRecords {
    /// `store.build_alert_record(alert, room=..., now=...)` —
    /// Err carries the ValueError message when the alert does
    /// not validate into a WDG-010 record.
    fn build_alert_record(
        &self,
        alert: &Value,
        room: &str,
        now: Option<i64>,
    ) -> Result<Value, String>;
}

/// `intel.store` (B09) — the boot status line builder the
/// OS-041 drill exercises.
pub trait BootStatus {
    /// `store.build_boot_status(units, workers, alerts, ts=...)`.
    fn build_boot_status(
        &self,
        units: &Value,
        workers: &Value,
        alerts: &Value,
        ts: i64,
    ) -> Value;
    /// `store.boot_status_is_stale(record, now=...)`.
    fn boot_status_is_stale(&self, record: &Value, now: i64) -> bool;
}

/// `intel.capability` (B09) — the grant checker the OS-081
/// drill exercises.
pub trait Capability {
    /// `capability.check_action(grant, action, subject,
    /// identity)` — grant is None when no grant is on file.
    fn check_action(
        &self,
        grant: Option<&Value>,
        action: &str,
        subject: Option<&str>,
        identity: Option<&str>,
    ) -> Option<Value>;
    /// `capability.refusal_alert(decision, now=...)`.
    fn refusal_alert(&self, decision: &Value, now: i64) -> Value;
    /// `capability.refusal_note(decision)`.
    fn refusal_note(&self, decision: &Value) -> String;
    /// `capability.capability_tick(attempts, grants, journal, now)`.
    fn capability_tick(
        &self,
        attempts: &Value,
        grants: &Value,
        journal: &[Value],
        now: i64,
    ) -> Vec<Value>;
    /// `capability.brief_lines(records)`.
    fn brief_lines(&self, records: &[Value]) -> Vec<String>;
}

/// `intel.gate` (B09) — the attempt-budget judgment the
/// OS-096 drill exercises. The gate builds records; it never
/// sends anything (the drill's sent ledger proves it).
pub trait Gate {
    /// `gate.gate_tick(snapshot, journal, now)` -> new records.
    /// The journal is read, never mutated; the caller extends
    /// its own journal with the returned records.
    fn gate_tick(&self, snapshot: &Value, journal: &[Value], now: i64) -> Vec<Value>;
    /// `gate.gate_brief_lines(records)`.
    fn gate_brief_lines(&self, records: &[Value]) -> Vec<String>;
}

/// `intel.push` (B10) — the payload validator the gate drill
/// checks every escalation against.
pub trait Push {
    /// `push.validate_push(payload)`.
    fn validate_push(&self, payload: &Value) -> bool;
}

/// `intel.baton` (B10) — the continuation composer the
/// OS-125 drill exercises. It composes and journals; it never
/// moves a claim and carries no push path.
pub trait Baton {
    /// `baton.compose_baton(job)` — None for a non-record or
    /// an id-less record.
    fn compose_baton(&self, job: &Value) -> Option<Value>;
    /// `baton.baton_pass_tick(snapshot, job_id, next, journal, now)`.
    fn baton_pass_tick(
        &self,
        snapshot: &Value,
        job_id: &str,
        next: &str,
        journal: &[Value],
        now: i64,
    ) -> Vec<Value>;
    /// `baton.baton_brief_lines(records)`.
    fn baton_brief_lines(&self, records: &[Value]) -> Vec<String>;
}
