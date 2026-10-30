//! Env-override behavior for thresholds (WDG-018).
//!
//! Isolated in its own test binary because env vars are
//! process-global: this process sets real WATCHDOG_* vars and no
//! other test process observes them. Mirrors the Python suite's
//! subprocess isolation (each Python env test runs in a fresh
//! interpreter), so no cross-test interference is possible.

use os_supervisor::thresholds;
use serde_json::json;

fn stall_snapshot() -> serde_json::Value {
    json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 9340}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    })
}

fn tick(snapshot: &serde_json::Value, now: i64) -> Vec<serde_json::Value> {
    os_supervisor::watchdog::tick(
        snapshot,
        Some(now),
        now,
        None,
        os_supervisor::watchdog::TickCallbacks {
            emit: None,
            polish: None,
            announce: None,
            beat: None,
        },
    )
}

#[test]
fn env_override_changes_presence_stall_behavior() {
    assert_eq!(tick(&stall_snapshot(), 10000).len(), 1);
    std::env::set_var("WATCHDOG_STALL_MINUTES", "1000000");
    assert!(tick(&stall_snapshot(), 10000).is_empty());
    std::env::remove_var("WATCHDOG_STALL_MINUTES");
    assert_eq!(tick(&stall_snapshot(), 10000).len(), 1);
    assert_eq!(thresholds::stall_minutes(), 10);
}

#[test]
fn env_override_changes_silent_room_behavior() {
    let snap = || {
        json!({"jobs": [{"id": "7", "title": "d", "status": "claimed", "claim": "pax",
                         "claimed_at": 99990, "last_progress_at": 99990}],
               "messages": [{"nick": "a", "text": "old", "ts": 9000}],
               "presence": ["pax"], "caps": {"pax": {"caps": "build"}}})
    };
    assert_eq!(tick(&snap(), 100000).len(), 1);
    std::env::set_var("WATCHDOG_SILENT_ROOM_MINUTES", "1000000");
    assert!(tick(&snap(), 100000).is_empty());
    std::env::remove_var("WATCHDOG_SILENT_ROOM_MINUTES");
    assert_eq!(thresholds::silent_room_minutes(), 60);
}

#[test]
fn env_override_changes_tick_cap_behavior() {
    let messages: Vec<serde_json::Value> = (0..1500).map(|_| json!("plain")).collect();
    let snap = || {
        json!({"jobs": [], "messages": messages.clone()})
    };
    let capped = os_supervisor::watchdog::cap_tick_snapshot(&snap(), Some(100), None);
    // Explicit cap of 100 keeps the newest 100.
    assert_eq!(capped["messages"].as_array().unwrap().len(), 100);
    std::env::set_var("WATCHDOG_TICK_MAX_MESSAGES", "10");
    let capped = os_supervisor::watchdog::cap_tick_snapshot(&snap(), None, None);
    assert_eq!(capped["messages"].as_array().unwrap().len(), 10);
    assert_eq!(thresholds::tick_max_messages(), 10);
    std::env::remove_var("WATCHDOG_TICK_MAX_MESSAGES");
    assert_eq!(thresholds::tick_max_messages(), 1000);
}

#[test]
fn bad_env_values_fall_back_to_defaults() {
    std::env::set_var("WATCHDOG_STALL_MINUTES", "");
    assert_eq!(thresholds::stall_minutes(), 10);
    std::env::set_var("WATCHDOG_STALL_MINUTES", "junk");
    assert_eq!(thresholds::stall_minutes(), 10);
    std::env::set_var("WATCHDOG_STALL_MINUTES", "-5");
    // Below-minimum falls back rather than inventing a threshold.
    assert_eq!(thresholds::stall_minutes(), 10);
    std::env::remove_var("WATCHDOG_STALL_MINUTES");
}
