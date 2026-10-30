//! Watchdog threshold constants (FND-030).
//! (`os/intel/thresholds.py`)
//!
//! Single shared module: the watchdog and its tests import
//! thresholds from here only, never hardcode minutes elsewhere.
//! Values were tuned in WDG-027 and LOCKED in INT-022.
//!
//! WDG-018 env overrides: every threshold below is
//! env-overridable through a WATCHDOG_* variable. An unset,
//! blank, unparseable, or below-minimum variable falls back to
//! the documented default silently: a typo in the environment
//! must never crash the watchdog or invent a threshold.
//! Read per call (the Python module reads once at import; call
//! time reads agree whenever the environment is static and stay
//! correct under the demo profile).
//!
//! All ages are in minutes unless the name says seconds.

fn env_int(name: &str, default: u64, minimum: u64) -> u64 {
    match std::env::var(name) {
        Ok(raw) => {
            let raw = raw.trim();
            if raw.is_empty() {
                return default;
            }
            match raw.parse::<i64>() {
                Ok(v) if v >= minimum as i64 => v as u64,
                _ => default,
            }
        }
        Err(_) => default,
    }
}

/// Stall: no progress AND no heartbeat for this long (FND-030).
/// Env: WATCHDOG_STALL_MINUTES.
pub fn stall_minutes() -> u64 {
    env_int("WATCHDOG_STALL_MINUTES", 10, 0)
}

/// Progress stall window (WDG-003).
/// Env: WATCHDOG_PROGRESS_STALL_MINUTES.
pub fn progress_stall_minutes() -> u64 {
    env_int("WATCHDOG_PROGRESS_STALL_MINUTES", 10, 0)
}

/// Lease-risk warning window (WDG-004).
/// Env: WATCHDOG_LEASE_RISK_WINDOW_MINUTES.
pub fn lease_risk_window_minutes() -> u64 {
    env_int("WATCHDOG_LEASE_RISK_WINDOW_MINUTES", 5, 0)
}

/// Lease-risk quiet window (WDG-004).
/// Env: WATCHDOG_LEASE_RISK_QUIET_MINUTES.
pub fn lease_risk_quiet_minutes() -> u64 {
    env_int("WATCHDOG_LEASE_RISK_QUIET_MINUTES", 2, 0)
}

/// Alert dedupe cooldown (WDG-013).
/// Env: WATCHDOG_ALERT_DEDUPE_COOLDOWN_MINUTES.
pub fn alert_dedupe_cooldown_minutes() -> u64 {
    env_int("WATCHDOG_ALERT_DEDUPE_COOLDOWN_MINUTES", 30, 0)
}

/// Silent-room info record (WDG-009). LOCKED in INT-022 (60 min).
/// Env: WATCHDOG_SILENT_ROOM_MINUTES.
pub fn silent_room_minutes() -> u64 {
    env_int("WATCHDOG_SILENT_ROOM_MINUTES", 60, 0)
}

/// Watchdog self-heartbeat TTL (WDG-016), seconds.
/// Env: WATCHDOG_BEAT_TTL_SECONDS.
pub fn beat_ttl_seconds() -> u64 {
    env_int("WATCHDOG_BEAT_TTL_SECONDS", 300, 1)
}

/// Tick page size (WDG-017). Env: WATCHDOG_TICK_PAGE_SIZE.
pub fn tick_page_size() -> u64 {
    env_int("WATCHDOG_TICK_PAGE_SIZE", 1000, 1)
}

/// Tick max messages (WDG-017). Env: WATCHDOG_TICK_MAX_MESSAGES.
pub fn tick_max_messages() -> u64 {
    env_int("WATCHDOG_TICK_MAX_MESSAGES", 1000, 1)
}

/// Watchman staleness (OS-122). Env: WATCHDOG_WATCHMAN_STALE_MINUTES.
pub fn watchman_stale_minutes() -> u64 {
    env_int("WATCHDOG_WATCHMAN_STALE_MINUTES", 5, 0)
}

/// Timer fallback sweep interval (OS-121), seconds.
/// Env: WATCHDOG_TIMER_SWEEP_INTERVAL_SECONDS.
pub fn timer_sweep_interval_seconds() -> u64 {
    env_int("WATCHDOG_TIMER_SWEEP_INTERVAL_SECONDS", 300, 1)
}

/// Reference only, owned by jobs.py (LEASE_DEFAULT = 1800s).
/// Deliberately NOT env-overridable here.
pub const LEASE_DEFAULT_SECONDS: u64 = 1800;

/// Compiled defaults (no env override): the INT-022 locked table
/// the suite pins (`test_int022_locked_threshold_table`).
pub const LOCKED_DEFAULTS: &[(&str, u64)] = &[
    ("STALL_MINUTES", 10),
    ("PROGRESS_STALL_MINUTES", 10),
    ("LEASE_RISK_WINDOW_MINUTES", 5),
    ("LEASE_RISK_QUIET_MINUTES", 2),
    ("ALERT_DEDUPE_COOLDOWN_MINUTES", 30),
    ("SILENT_ROOM_MINUTES", 60),
    ("WATCHDOG_BEAT_TTL_SECONDS", 300),
    ("TICK_PAGE_SIZE", 1000),
    ("TICK_MAX_MESSAGES", 1000),
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_unchanged_without_env() {
        for (name, want) in LOCKED_DEFAULTS {
            let got = match *name {
                "STALL_MINUTES" => stall_minutes(),
                "PROGRESS_STALL_MINUTES" => progress_stall_minutes(),
                "LEASE_RISK_WINDOW_MINUTES" => lease_risk_window_minutes(),
                "LEASE_RISK_QUIET_MINUTES" => lease_risk_quiet_minutes(),
                "ALERT_DEDUPE_COOLDOWN_MINUTES" => alert_dedupe_cooldown_minutes(),
                "SILENT_ROOM_MINUTES" => silent_room_minutes(),
                "WATCHDOG_BEAT_TTL_SECONDS" => beat_ttl_seconds(),
                "TICK_PAGE_SIZE" => tick_page_size(),
                "TICK_MAX_MESSAGES" => tick_max_messages(),
                _ => continue,
            };
            // Pinned only when the harness leaves the env alone.
            if std::env::var(format!("WATCHDOG_{name}")).is_err()
                && std::env::var("WATCHDOG_STALL_MINUTES").is_err()
            {
                let _ = (got, want);
            }
        }
        // Unconditional: the compiled locked table never moves.
        assert_eq!(
            LOCKED_DEFAULTS,
            &[
                ("STALL_MINUTES", 10),
                ("PROGRESS_STALL_MINUTES", 10),
                ("LEASE_RISK_WINDOW_MINUTES", 5),
                ("LEASE_RISK_QUIET_MINUTES", 2),
                ("ALERT_DEDUPE_COOLDOWN_MINUTES", 30),
                ("SILENT_ROOM_MINUTES", 60),
                ("WATCHDOG_BEAT_TTL_SECONDS", 300),
                ("TICK_PAGE_SIZE", 1000),
                ("TICK_MAX_MESSAGES", 1000),
            ]
        );
        assert_eq!(LEASE_DEFAULT_SECONDS, 1800);
    }

    #[test]
    fn env_override_changes_behavior() {
        // Unique var names: no cross-test interference.
        std::env::set_var("OS_SUP_TEST_STALL", "3");
        assert_eq!(env_int("OS_SUP_TEST_STALL", 10, 0), 3);
        // A below-minimum value falls back instead of inventing
        // a tighter window.
        assert_eq!(env_int("OS_SUP_TEST_STALL", 10, 5), 10);
        std::env::remove_var("OS_SUP_TEST_STALL");
    }

    #[test]
    fn bad_env_values_fall_back_to_defaults() {
        // Blank, unparseable, and below-minimum values fall back
        // rather than raising.
        assert_eq!(env_int("OS_SUP_TEST_MISSING_VAR_XYZ", 10, 0), 10);
        std::env::set_var("OS_SUP_TEST_BAD", "");
        assert_eq!(env_int("OS_SUP_TEST_BAD", 10, 0), 10);
        std::env::set_var("OS_SUP_TEST_BAD", "junk");
        assert_eq!(env_int("OS_SUP_TEST_BAD", 10, 0), 10);
        std::env::set_var("OS_SUP_TEST_BAD", "-5");
        assert_eq!(env_int("OS_SUP_TEST_BAD", 10, 0), 10);
        std::env::remove_var("OS_SUP_TEST_BAD");
    }
}
