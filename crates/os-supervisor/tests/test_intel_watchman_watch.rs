//! Parity tests for `os/tests/test_intel_watchman_watch.py`.
//!
//! The OS-122 judge: killed watchman flags crew-dark in one
//! tick; revival yields recovered with no escalation; beyond
//! repair yields exactly one valid escalation (built, never
//! sent); second death re-alerts; stale/fresh bells, unknown
//! machines, malformed inputs, brief and board lines, and the
//! drill.

use os_supervisor::watchman_watch as ww;
use serde_json::{json, Value};

const T0: f64 = 100_000.0;

fn snap(record: Value) -> Value {
    json!({"machines": {"milo-box": record}})
}

#[test]
fn killed_watchman_flags_crew_dark_in_one_tick() {
    let new = ww::watchman_watch_tick(
        &snap(json!({"watchman_alive": false, "last_bell": T0 - 600.0, "last_wake": T0 - 600.0, "restart_ok": true})),
        &[],
        T0,
    );
    assert_eq!(
        new.iter().map(|r| r["kind"].clone()).collect::<Vec<_>>(),
        vec![json!("crew-dark"), json!("watchman-restart")]
    );
    assert!(new.iter().all(|r| r.get("push").is_none()));
    // Board reads dead while dark.
    assert_eq!(
        ww::board_lines(&ww::current_states(&snap(json!({"watchman_alive": false, "last_bell": T0 - 600.0, "last_wake": T0 - 600.0, "restart_ok": true})), T0)),
        vec!["Machine milo-box: watchman dead (crew-dark).".to_string()]
    );
}

#[test]
fn revival_yields_recovered_and_still_no_escalation() {
    let dark = ww::watchman_watch_tick(
        &snap(json!({"watchman_alive": false, "last_bell": T0 - 600.0, "last_wake": T0 - 600.0, "restart_ok": true})),
        &[],
        T0,
    );
    let new = ww::watchman_watch_tick(
        &snap(json!({"watchman_alive": true, "last_bell": T0, "last_wake": T0, "restart_ok": true})),
        &dark,
        T0 + 60.0,
    );
    assert_eq!(
        new.iter().map(|r| r["kind"].clone()).collect::<Vec<_>>(),
        vec![json!("watchman-recovered")]
    );
    assert!(new.iter().all(|r| r.get("push").is_none()));
    assert_eq!(
        ww::board_lines(&ww::current_states(
            &snap(json!({"watchman_alive": true, "last_bell": T0, "last_wake": T0, "restart_ok": true})),
            T0 + 60.0
        )),
        vec!["Machine milo-box: watchman alive.".to_string()]
    );
}

#[test]
fn beyond_repair_yields_exactly_one_valid_escalation() {
    let new = ww::watchman_watch_tick(
        &snap(json!({"watchman_alive": false, "last_bell": T0 - 600.0, "last_wake": T0 - 600.0, "restart_ok": false})),
        &[],
        T0,
    );
    assert_eq!(
        new.iter().map(|r| r["kind"].clone()).collect::<Vec<_>>(),
        vec![json!("crew-dark"), json!("watchman-restart"), json!("escalation")]
    );
    let escalation = new.iter().find(|r| r["kind"] == json!("escalation")).unwrap();
    assert!(escalation.get("push").is_some());
    assert!(escalation.get("question").is_some());
    assert!(os_supervisor::push_lite::validate_push(&escalation["push"]));
}

#[test]
fn second_death_after_recovery_realerts() {
    let dark = ww::watchman_watch_tick(
        &snap(json!({"watchman_alive": false, "last_bell": T0 - 600.0, "last_wake": T0 - 600.0, "restart_ok": false})),
        &[],
        T0,
    );
    let mut journal = dark;
    let recovered = ww::watchman_watch_tick(
        &snap(json!({"watchman_alive": true, "last_bell": T0, "last_wake": T0, "restart_ok": true})),
        &journal,
        T0 + 60.0,
    );
    assert!(!recovered.is_empty());
    journal.extend(recovered);
    let new = ww::watchman_watch_tick(
        &snap(json!({"watchman_alive": false, "last_bell": T0, "last_wake": T0, "restart_ok": false})),
        &journal,
        T0 + 3600.0,
    );
    // A new dark episode after recovery re-alerts.
    assert!(new.iter().any(|r| r["kind"] == json!("crew-dark")));
    assert!(new.iter().any(|r| r["kind"] == json!("escalation")));
}

#[test]
fn stale_bell_reads_dead_and_fresh_bell_reads_alive() {
    assert_eq!(
        ww::machine_state(&json!({"watchman_alive": true, "last_bell": T0 - 600.0}), T0, None),
        "dead"
    );
    assert_eq!(
        ww::machine_state(&json!({"watchman_alive": true, "last_bell": T0}), T0, None),
        "alive"
    );
    // Env-window override is honored per call.
    assert_eq!(
        ww::machine_state(&json!({"watchman_alive": true, "last_bell": T0 - 600.0}), T0, Some(60.0)),
        "alive"
    );
}

#[test]
fn unknown_machine_yields_nothing_and_reads_unknown() {
    let snap = json!({"machines": {"ghost": {"nonsense": true}}});
    assert!(ww::watchman_watch_tick(&snap, &[], T0).is_empty());
    assert_eq!(ww::machine_state(&json!({"nonsense": true}), T0, None), "unknown");
    assert_eq!(
        ww::board_lines(&ww::current_states(&snap, T0)),
        vec!["Machine ghost: watchman state unknown.".to_string()]
    );
}

#[test]
fn malformed_inputs_never_crash() {
    assert!(ww::watchman_watch_tick(&Value::Null, &[], T0).is_empty());
    assert!(ww::watchman_watch_tick(&json!({"machines": null}), &[], T0).is_empty());
    assert!(ww::watchman_watch_tick(&json!({"machines": {"m": [1, 2]}}), &[], T0).is_empty());
    assert!(ww::current_states(&Value::Null, T0).is_empty());
    assert!(ww::machine_state(&Value::Null, T0, None) == "unknown");
    assert!(ww::watchman_brief_lines(&Value::Null).is_empty());
    assert!(ww::board_lines(&Value::Null).is_empty());
}

#[test]
fn tick_never_mutates_inputs() {
    let snap = snap(json!({"watchman_alive": false, "last_bell": T0 - 600.0, "restart_ok": false}));
    let before = snap.clone();
    let journal: Vec<Value> = vec![json!({"kind": "crew-dark", "machine": "other"})];
    let journal_before = journal.clone();
    ww::watchman_watch_tick(&snap, &journal, T0);
    assert_eq!(snap, before);
    assert_eq!(journal, journal_before);
}

#[test]
fn brief_and_board_lines() {
    let records = vec![
        json!({"kind": "crew-dark", "machine": "m1"}),
        json!({"kind": "watchman-restart", "machine": "m1", "restart_ok": true}),
        json!({"kind": "watchman-restart", "machine": "m2", "restart_ok": false}),
        json!({"kind": "escalation", "machine": "m2"}),
        json!({"kind": "watchman-recovered", "machine": "m3"}),
        json!({"kind": "other"}),
    ];
    let lines = ww::watchman_brief_lines(&records);
    assert_eq!(lines.len(), 5);
    assert!(lines[0].contains("Crew-dark on machine m1"));
    assert!(lines[1].contains("restart succeeded"));
    assert!(lines[2].contains("restart failed"));
    assert!(lines[3].contains("Escalated machine m2"));
    assert!(lines[4].contains("Watchman recovered on machine m3"));
}

#[test]
fn escalation_is_built_never_sent() {
    // The escalation carries a validated push payload; sending it
    // is the Web Push worker's job, outside this repo.
    let new = ww::watchman_watch_tick(
        &snap(json!({"watchman_alive": false, "last_bell": T0 - 600.0, "restart_ok": false})),
        &[],
        T0,
    );
    let escalation = new.iter().find(|r| r["kind"] == json!("escalation")).unwrap();
    assert!(os_supervisor::push_lite::validate_push(&escalation["push"]));
    assert!(escalation["push"]["job_id"].as_str().unwrap().contains("milo-box"));
}

#[test]
fn drill_passes() {
    let log = os_supervisor::drills_watchman::run_watchman_watch()
        .expect("watchman watch drill");
    assert!(!log.is_empty());
    assert!(log.iter().all(|l| l.starts_with("PASS")));
}

#[test]
fn new_files_carry_no_em_dash() {
    // The Python NEW_FILES for this batch item: the watchman
    // module, its drill, and this test. The blocked-push template
    // in push_lite.rs carries the pinned em dash from
    // explanations.py, like its Python source does.
    let manifest = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    for file in [
        "src/watchman_watch.rs",
        "tests/test_intel_watchman_watch.rs",
    ] {
        let text = std::fs::read_to_string(manifest.join(file)).unwrap();
        assert!(!text.contains('\u{2014}'), "{file}");
    }
}
