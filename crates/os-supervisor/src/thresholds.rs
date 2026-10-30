//! Watchdog threshold constants (port of `os/intel/thresholds.py`, FND-030).
//!
//! Single shared module: the watchdog and its tests import thresholds
//! from here only, never hardcode minutes elsewhere. Values come from
//! the lane plan, tuned in WDG-027 and LOCKED in INT-022. A later
//! change needs a failing fixture and a new tuning-table run, not a
//! guess; the demo profile (DEM-013/OS-038) overrides these through
//! the environment only and never edits this file.
//!
//! Every threshold below is env-overridable through a `WATCHDOG_*`
//! variable, read once when [`Thresholds::from_env`] is called. An
//! unset, blank, unparseable, or below-minimum variable falls back to
//! the documented default silently: a typo in the environment must
//! never crash the watchdog or invent a threshold. All ages are in
//! minutes unless the name says seconds.
//!
//! Reference only, owned by jobs (lease default 1800s there): the
//! watchdog reads lease values off the job hash, never redefines
//! them. [`LEASE_DEFAULT_SECONDS`] is deliberately NOT
//! env-overridable here: it is jobs' lease, and two modules
//! overriding the same number would disagree silently.

/// Stall: no progress AND no heartbeat for this long (FND-030 default).
/// Env: `WATCHDOG_STALL_MINUTES`.
pub const STALL_MINUTES_DEFAULT: i64 = 10;
/// Progress stall uses the same window: heartbeat alive, but the job's
/// progress note has not changed for this long (WDG-003).
/// Env: `WATCHDOG_PROGRESS_STALL_MINUTES`.
pub const PROGRESS_STALL_MINUTES_DEFAULT: i64 = 10;
/// Lease-risk warning window (WDG-004).
/// Env: `WATCHDOG_LEASE_RISK_WINDOW_MINUTES`.
pub const LEASE_RISK_WINDOW_MINUTES_DEFAULT: i64 = 5;
/// Lease-risk quiet window (WDG-004).
/// Env: `WATCHDOG_LEASE_RISK_QUIET_MINUTES`.
pub const LEASE_RISK_QUIET_MINUTES_DEFAULT: i64 = 2;
/// Alert dedupe cooldown (WDG-013): same dedupe key inside this window
/// updates last_seen instead of creating a new alert.
/// Env: `WATCHDOG_ALERT_DEDUPE_COOLDOWN_MINUTES`.
pub const ALERT_DEDUPE_COOLDOWN_MINUTES_DEFAULT: i64 = 30;
/// Silent-room info record (WDG-009), LOCKED in INT-022.
/// Env: `WATCHDOG_SILENT_ROOM_MINUTES`.
pub const SILENT_ROOM_MINUTES_DEFAULT: i64 = 60;
/// Watchdog self-heartbeat TTL (WDG-016): five missed 60-second loop
/// ticks. Env: `WATCHDOG_BEAT_TTL_SECONDS`.
pub const WATCHDOG_BEAT_TTL_SECONDS_DEFAULT: i64 = 300;
/// Tick budget guard page size (WDG-017).
/// Env: `WATCHDOG_TICK_PAGE_SIZE`.
pub const TICK_PAGE_SIZE_DEFAULT: i64 = 1000;
/// Tick budget guard message cap (WDG-017).
/// Env: `WATCHDOG_TICK_MAX_MESSAGES`.
pub const TICK_MAX_MESSAGES_DEFAULT: i64 = 1000;
/// Watchman staleness (OS-122): a watchman whose bell is older than
/// this is dead, even if its alive flag still says true.
/// Env: `WATCHDOG_WATCHMAN_STALE_MINUTES`.
pub const WATCHMAN_STALE_MINUTES_DEFAULT: i64 = 5;
/// Timer fallback sweep interval (OS-121).
/// Env: `WATCHDOG_TIMER_SWEEP_INTERVAL_SECONDS`.
pub const TIMER_SWEEP_INTERVAL_SECONDS_DEFAULT: i64 = 300;
/// Reference only, owned by jobs.py (`LEASE_DEFAULT = 1800s` there).
/// Deliberately NOT env-overridable.
pub const LEASE_DEFAULT_SECONDS: i64 = 1800;

/// One env-overridable integer threshold, mirroring Python's
/// `_env_int`: returns the variable's int value when `raw` parses
/// and is at least `minimum`, else `default`.
///
/// Blank and unparseable values fall back rather than raising.
/// Whitespace around the value is stripped first, matching Python's
/// `raw.strip()` before `int(raw)`.
pub fn parse_env_int(raw: Option<&str>, default: i64, minimum: i64) -> i64 {
    let Some(raw) = raw else {
        return default;
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

/// Read one env-overridable integer threshold from the process
/// environment, falling back to `default` exactly as
/// [`parse_env_int`] describes.
pub fn env_int(name: &str, default: i64, minimum: i64) -> i64 {
    parse_env_int(std::env::var(name).ok().as_deref(), default, minimum)
}

/// All watchdog thresholds in one value, mirroring the module-level
/// constants of `os/intel/thresholds.py`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Thresholds {
    /// Stall window in minutes (FND-030).
    pub stall_minutes: i64,
    /// Progress-stall window in minutes (WDG-003).
    pub progress_stall_minutes: i64,
    /// Lease-risk warning window in minutes (WDG-004).
    pub lease_risk_window_minutes: i64,
    /// Lease-risk quiet window in minutes (WDG-004).
    pub lease_risk_quiet_minutes: i64,
    /// Alert dedupe cooldown in minutes (WDG-013).
    pub alert_dedupe_cooldown_minutes: i64,
    /// Silent-room window in minutes (WDG-009).
    pub silent_room_minutes: i64,
    /// Watchdog self-heartbeat TTL in seconds (WDG-016).
    pub watchdog_beat_ttl_seconds: i64,
    /// Tick page size (WDG-017).
    pub tick_page_size: i64,
    /// Tick message cap (WDG-017).
    pub tick_max_messages: i64,
    /// Watchman staleness in minutes (OS-122).
    pub watchman_stale_minutes: i64,
    /// Timer fallback sweep interval in seconds (OS-121).
    pub timer_sweep_interval_seconds: i64,
}

impl Thresholds {
    /// The documented defaults, with no environment applied.
    pub fn defaults() -> Self {
        Self {
            stall_minutes: STALL_MINUTES_DEFAULT,
            progress_stall_minutes: PROGRESS_STALL_MINUTES_DEFAULT,
            lease_risk_window_minutes: LEASE_RISK_WINDOW_MINUTES_DEFAULT,
            lease_risk_quiet_minutes: LEASE_RISK_QUIET_MINUTES_DEFAULT,
            alert_dedupe_cooldown_minutes: ALERT_DEDUPE_COOLDOWN_MINUTES_DEFAULT,
            silent_room_minutes: SILENT_ROOM_MINUTES_DEFAULT,
            watchdog_beat_ttl_seconds: WATCHDOG_BEAT_TTL_SECONDS_DEFAULT,
            tick_page_size: TICK_PAGE_SIZE_DEFAULT,
            tick_max_messages: TICK_MAX_MESSAGES_DEFAULT,
            watchman_stale_minutes: WATCHMAN_STALE_MINUTES_DEFAULT,
            timer_sweep_interval_seconds: TIMER_SWEEP_INTERVAL_SECONDS_DEFAULT,
        }
    }

    /// Read every `WATCHDOG_*` variable once, mirroring the Python
    /// module's import-time reads. Minimums match the Python calls:
    /// 0 for the minute thresholds, 1 for the two second thresholds
    /// that must stay positive (`WATCHDOG_BEAT_TTL_SECONDS`,
    /// `WATCHDOG_TIMER_SWEEP_INTERVAL_SECONDS`) and for the two tick
    /// guards (a non-positive page size or a zero message cap would
    /// break pagination / drop every message).
    pub fn from_env() -> Self {
        Self {
            stall_minutes: env_int("WATCHDOG_STALL_MINUTES", STALL_MINUTES_DEFAULT, 0),
            progress_stall_minutes: env_int(
                "WATCHDOG_PROGRESS_STALL_MINUTES",
                PROGRESS_STALL_MINUTES_DEFAULT,
                0,
            ),
            lease_risk_window_minutes: env_int(
                "WATCHDOG_LEASE_RISK_WINDOW_MINUTES",
                LEASE_RISK_WINDOW_MINUTES_DEFAULT,
                0,
            ),
            lease_risk_quiet_minutes: env_int(
                "WATCHDOG_LEASE_RISK_QUIET_MINUTES",
                LEASE_RISK_QUIET_MINUTES_DEFAULT,
                0,
            ),
            alert_dedupe_cooldown_minutes: env_int(
                "WATCHDOG_ALERT_DEDUPE_COOLDOWN_MINUTES",
                ALERT_DEDUPE_COOLDOWN_MINUTES_DEFAULT,
                0,
            ),
            silent_room_minutes: env_int(
                "WATCHDOG_SILENT_ROOM_MINUTES",
                SILENT_ROOM_MINUTES_DEFAULT,
                0,
            ),
            watchdog_beat_ttl_seconds: env_int(
                "WATCHDOG_BEAT_TTL_SECONDS",
                WATCHDOG_BEAT_TTL_SECONDS_DEFAULT,
                1,
            ),
            tick_page_size: env_int("WATCHDOG_TICK_PAGE_SIZE", TICK_PAGE_SIZE_DEFAULT, 1),
            tick_max_messages: env_int(
                "WATCHDOG_TICK_MAX_MESSAGES",
                TICK_MAX_MESSAGES_DEFAULT,
                1,
            ),
            watchman_stale_minutes: env_int(
                "WATCHDOG_WATCHMAN_STALE_MINUTES",
                WATCHMAN_STALE_MINUTES_DEFAULT,
                0,
            ),
            timer_sweep_interval_seconds: env_int(
                "WATCHDOG_TIMER_SWEEP_INTERVAL_SECONDS",
                TIMER_SWEEP_INTERVAL_SECONDS_DEFAULT,
                1,
            ),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_match_locked_python_values() {
        let t = Thresholds::defaults();
        assert_eq!(t.stall_minutes, 10);
        assert_eq!(t.progress_stall_minutes, 10);
        assert_eq!(t.lease_risk_window_minutes, 5);
        assert_eq!(t.lease_risk_quiet_minutes, 2);
        assert_eq!(t.alert_dedupe_cooldown_minutes, 30);
        assert_eq!(t.silent_room_minutes, 60);
        assert_eq!(t.watchdog_beat_ttl_seconds, 300);
        assert_eq!(t.tick_page_size, 1000);
        assert_eq!(t.tick_max_messages, 1000);
        assert_eq!(t.watchman_stale_minutes, 5);
        assert_eq!(t.timer_sweep_interval_seconds, 300);
        assert_eq!(LEASE_DEFAULT_SECONDS, 1800);
    }

    #[test]
    fn parse_env_int_unset_blank_unparseable_fall_back() {
        assert_eq!(parse_env_int(None, 10, 0), 10);
        assert_eq!(parse_env_int(Some(""), 10, 0), 10);
        assert_eq!(parse_env_int(Some("   "), 10, 0), 10);
        assert_eq!(parse_env_int(Some("ten"), 10, 0), 10);
        assert_eq!(parse_env_int(Some("10.5"), 10, 0), 10);
    }

    #[test]
    fn parse_env_int_below_minimum_falls_back_at_minimum_passes() {
        assert_eq!(parse_env_int(Some("-1"), 10, 0), 10);
        assert_eq!(parse_env_int(Some("0"), 300, 1), 300);
        assert_eq!(parse_env_int(Some("1"), 300, 1), 1);
        assert_eq!(parse_env_int(Some(" 42 "), 10, 0), 42);
        assert_eq!(parse_env_int(Some("0"), 10, 0), 0);
    }
}
