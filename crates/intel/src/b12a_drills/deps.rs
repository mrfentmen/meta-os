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
    let raw = raw.trim();
    if raw.is_empty() {
        return default;
    }
    match raw.parse::<i64>() {
        Ok(value) if value >= minimum => value,
        _ => default,
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
}
