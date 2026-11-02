//! Test-gap close for `os-supervisor` (B023).
//!
//! `thresholds.rs` carries the fewest tests in the crate (3). This file
//! brings it to the coverage level of the best-covered module by
//! exercising the fallback rule, the range rule, and the shared
//! severity/announcement tables through the public API.

use std::collections::HashMap;

use os_supervisor::thresholds::{
    parse_env_int, Thresholds, LEASE_DEFAULT_SECONDS, STALL_MINUTES_DEFAULT,
    WATCHMAN_STALE_MINUTES_DEFAULT,
};
use os_supervisor::watchdog::{
    announcements_for, at_warning, env_int_range, format_announcement, severity_by_kind, Alert,
    Thresholds as WatchdogThresholds, DETECTORS,
};

#[test]
fn locked_defaults_are_the_documented_numbers() {
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
    assert_eq!(STALL_MINUTES_DEFAULT, 10);
    assert_eq!(WATCHMAN_STALE_MINUTES_DEFAULT, 5);
    // The lease belongs to jobs and must not be env-overridable here.
    assert_eq!(LEASE_DEFAULT_SECONDS, 1800);
}

#[test]
fn whitespace_is_stripped_before_parsing() {
    assert_eq!(parse_env_int(Some(" 42 "), 10, 0), 42);
    assert_eq!(parse_env_int(Some("\t7\n"), 10, 0), 7);
}

#[test]
fn a_number_too_large_for_i64_falls_back() {
    assert_eq!(parse_env_int(Some("9223372036854775808"), 10, 0), 10);
}

#[test]
fn a_float_is_not_an_int_and_falls_back() {
    assert_eq!(parse_env_int(Some("10.0"), 10, 0), 10);
}

#[test]
fn watchdog_thresholds_read_overrides_and_keep_defaults_for_the_rest() {
    let mut env: HashMap<&str, &str> = HashMap::new();
    env.insert("WATCHDOG_STALL_MINUTES", "5");
    env.insert("WATCHDOG_TICK_PAGE_SIZE", "7");
    env.insert("WATCHDOG_BUDGET_WARN_PERCENT", "90");
    let t = WatchdogThresholds::from_env_with(|name| env.get(name).map(|v| v.to_string()));
    assert_eq!(t.stall_minutes, 5);
    assert_eq!(t.tick_page_size, 7);
    assert_eq!(t.budget_warn_percent, 90);
    // Untouched keys keep the locked defaults.
    assert_eq!(t.progress_stall_minutes, 10);
    assert_eq!(t.tick_max_messages, 1000);
}

#[test]
fn bad_env_values_never_invent_a_threshold() {
    let mut env: HashMap<&str, &str> = HashMap::new();
    env.insert("WATCHDOG_STALL_MINUTES", "soon");
    env.insert("WATCHDOG_TICK_PAGE_SIZE", "0");
    env.insert("WATCHDOG_BUDGET_WARN_PERCENT", "101");
    env.insert("WATCHDOG_BEAT_TTL_SECONDS", "-5");
    let t = WatchdogThresholds::from_env_with(|name| env.get(name).map(|v| v.to_string()));
    assert_eq!(t.stall_minutes, 10);
    assert_eq!(t.tick_page_size, 1000);
    assert_eq!(t.budget_warn_percent, 80);
    assert_eq!(t.watchdog_beat_ttl_seconds, 300);
}

#[test]
fn the_budget_warning_band_is_warning_at_the_edge_but_never_at_the_cap() {
    assert!(!at_warning(79, 100, 80));
    assert!(at_warning(80, 100, 80));
    assert!(at_warning(99, 100, 80));
    assert!(!at_warning(100, 100, 80));
    // Unusable figures never warn.
    assert!(!at_warning(10, 0, 80));
    assert!(!at_warning(-1, 100, 80));
}

#[test]
fn every_detector_kind_has_one_canonical_severity() {
    for kind in [
        "presence-stall",
        "progress-stall",
        "lease-risk",
        "dead-dep",
        "missing-dep",
        "file-collision",
        "attempt-warning",
        "attempt-exhaustion",
        "silent-room",
        "rejected-dispatch",
        "budget-warning",
    ] {
        assert!(
            severity_by_kind(kind).is_some(),
            "no severity for {kind}"
        );
    }
    assert_eq!(severity_by_kind("silent-room"), Some("info"));
    assert_eq!(severity_by_kind("lease-risk"), Some("warning"));
    assert_eq!(severity_by_kind("presence-stall"), Some("critical"));
    assert_eq!(severity_by_kind("not-a-kind"), None);
}

#[test]
fn the_detector_registry_has_the_ten_registered_detectors() {
    assert_eq!(DETECTORS.len(), 10);
}

#[test]
fn only_critical_alerts_announce_and_the_id_prefers_the_explicit_one() {
    let critical = Alert {
        kind: "presence-stall".to_string(),
        severity: "critical".to_string(),
        dedupe_key: "presence-stall:pax:7".to_string(),
        explanation: "explained".to_string(),
        ..Alert::default()
    };
    assert_eq!(
        format_announcement(&critical).as_deref(),
        Some("ALERT:presence-stall:pax:7 presence-stall: explained")
    );

    let explicit = Alert {
        id: Some("alert-1".to_string()),
        ..critical.clone()
    };
    assert_eq!(
        format_announcement(&explicit).as_deref(),
        Some("ALERT:alert-1 presence-stall: explained")
    );

    let warning = Alert {
        severity: "warning".to_string(),
        ..critical.clone()
    };
    assert_eq!(format_announcement(&warning), None);

    let no_id = Alert {
        dedupe_key: String::new(),
        ..critical.clone()
    };
    assert_eq!(format_announcement(&no_id), None);

    assert_eq!(announcements_for(&[critical, warning]).len(), 1);
}

#[test]
fn announcement_newlines_are_flattened_to_one_line() {
    let alert = Alert {
        kind: "budget-warning".to_string(),
        severity: "critical".to_string(),
        dedupe_key: "k".to_string(),
        explanation: "line one\nline two\r\nline three".to_string(),
        ..Alert::default()
    };
    let line = format_announcement(&alert).expect("critical announces");
    assert!(!line.contains('\n'));
    assert!(line.contains("line one line two line three"));
}

#[test]
fn env_int_range_stays_inside_the_budget_band() {
    assert_eq!(env_int_range(Some("80"), 80, 1, 100), 80);
    assert_eq!(env_int_range(Some("1"), 80, 1, 100), 1);
    assert_eq!(env_int_range(Some("100"), 80, 1, 100), 100);
    assert_eq!(env_int_range(Some("0"), 80, 1, 100), 80);
}
