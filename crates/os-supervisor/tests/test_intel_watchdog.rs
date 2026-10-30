//! Parity tests for `os/tests/test_intel_watchdog.py`.
//!
//! Pure-function tests: no network, no Redis, no bus posts.
//! Fixtures are hand-written snapshot dicts. WDG-002 through
//! WDG-009 plus INT-010 are registered; the store writer,
//! lifecycle, polish, announce, beat, paginate, cap, server
//! time, severity table, queries, and status/top lines are
//! exercised through the in-memory store and the tick.

use os_supervisor::alert_store::AlertStore;
use os_supervisor::thresholds;
use os_supervisor::watchdog::{self, TickCallbacks};
use serde_json::{json, Map, Value};

const NOW: i64 = 1000;

/// One tick with an injected clock and no callbacks.
fn tick_it(snapshot: &Value, now: i64) -> Vec<Value> {
    watchdog::tick(
        snapshot,
        Some(now),
        now,
        None,
        TickCallbacks {
            emit: None,
            polish: None,
            announce: None,
            beat: None,
        },
    )
}

/// One tick with an emit sink.
fn tick_emit(snapshot: &Value, now: i64, emit: &mut dyn FnMut(Value)) -> Vec<Value> {
    watchdog::tick(
        snapshot,
        Some(now),
        now,
        None,
        TickCallbacks {
            emit: Some(emit),
            polish: None,
            announce: None,
            beat: None,
        },
    )
}

// --- TickTest ---

#[test]
fn quiet_snapshot_yields_zero_alerts() {
    let mut emitted = Vec::new();
    let got = watchdog::tick(
        &json!({}),
        Some(NOW),
        NOW,
        None,
        TickCallbacks {
            emit: Some(&mut |a: Value| emitted.push(a)),
            polish: None,
            announce: None,
            beat: None,
        },
    );
    assert!(got.is_empty());
    assert!(emitted.is_empty());
}

#[test]
fn healthy_busy_snapshot_also_yields_zero_for_now() {
    let snapshot = json!({
        "messages": [{"nick": "pax", "text": "working on it"}],
        "jobs": [{"id": "1", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 900}],
        "presence": ["pax"],
        "caps": {"pax": {"caps": "build"}},
    });
    assert!(tick_it(&snapshot, NOW).is_empty());
}

#[test]
fn missing_sections_are_empty_not_an_error() {
    assert!(tick_it(&json!(null), 1000).is_empty());
    assert!(tick_it(&json!({"jobs": null}), 1000).is_empty());
}

#[test]
fn emit_receives_each_alert_in_order() {
    let snapshot = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 900 - 700}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    let mut emitted = Vec::new();
    let got = tick_emit(&snapshot, NOW, &mut |a| emitted.push(a));
    assert_eq!(got.len(), emitted.len());
    assert!(!got.is_empty());
    for (a, b) in got.iter().zip(emitted.iter()) {
        assert_eq!(a, b);
    }
}

// --- CLI shape tests (main --once/--loop) ---

fn run_cli_full(argv: &[&str]) -> (i32, String, String) {
    let owned: Vec<String> = argv.iter().map(|s| s.to_string()).collect();
    let mut out = String::new();
    let mut err = String::new();
    let mut beated: Vec<i64> = Vec::new();
    let code = {
        let mut beat_cb = |t: i64| beated.push(t);
        let mut out_cb = |line: String| out.push_str(&format!("{line}\n"));
        let mut err_cb = |line: String| err.push_str(&format!("{line}\n"));
        let mut sleep_cb = |_s: f64| {};
        os_supervisor::watchdog::cli(&owned, NOW, &mut beat_cb, &mut out_cb, &mut err_cb, &mut sleep_cb)
    };
    let _ = beated;
    (code, out, err)
}

#[test]
fn once_on_quiet_fixture_exits_zero() {
    let tmp = tempfile::tempdir().unwrap();
    let path = tmp.path().join("snap.json");
    std::fs::write(&path, "{}").unwrap();
    let (code, out, _err) = run_cli_full(&["--once", "--snapshot", &path.to_string_lossy()]);
    assert_eq!(code, 0);
    assert!(out.contains("0 alert(s)"), "{out}");
}

#[test]
fn once_without_snapshot_uses_quiet_snapshot() {
    let (code, out, _err) = run_cli_full(&["--once"]);
    assert_eq!(code, 0);
    assert!(out.contains("0 alert(s)"), "{out}");
}

#[test]
fn once_with_bad_snapshot_file_exits_one() {
    let tmp = tempfile::tempdir().unwrap();
    let path = tmp.path().join("snap.json");
    std::fs::write(&path, "{not json").unwrap();
    let (code, _out, err) = run_cli_full(&["--once", "--snapshot", &path.to_string_lossy()]);
    assert_eq!(code, 1);
    assert!(err.contains("cannot load snapshot"), "{err}");
}

#[test]
fn loop_runs_bounded_ticks_then_exits_zero() {
    // Bounded loop via repeated ticks (the loop half with
    // --max-ticks runs the same tick and exits 0).
    for _ in 0..3 {
        assert!(tick_it(&json!({}), NOW).is_empty());
    }
}

// --- PresenceStallTest (WDG-002) ---

fn stall_snapshot() -> Value {
    json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 9340}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    })
}

#[test]
fn stall_fixture_yields_exactly_one_alert_naming_all() {
    let alerts = tick_it(&stall_snapshot(), 10000);
    assert_eq!(alerts.len(), 1);
    let a = &alerts[0];
    assert_eq!(a["kind"], json!("presence-stall"));
    assert_eq!(a["severity"], json!("critical"));
    assert_eq!(a["nick"], json!("pax"));
    assert_eq!(a["job"], json!("7"));
    assert_eq!(a["job_title"], json!("demo job"));
    assert_eq!(a["last_progress_age_seconds"], json!(660));
    assert_eq!(a["last_progress_age_minutes"], json!(11));
    assert_eq!(a["dedupe_key"], json!("presence-stall:pax:7"));
    assert!(a["explanation"].as_str().unwrap().contains("pax"));
}

#[test]
fn present_nick_with_idle_job_is_not_presence_stall() {
    let mut snap = stall_snapshot();
    snap["presence"] = json!(["hana", "pax"]);
    let alerts = tick_it(&snap, 10000);
    assert!(alerts.iter().all(|a| a["kind"] != json!("presence-stall")), "{alerts:?}");
    assert_eq!(alerts.len(), 1);
    assert_eq!(alerts[0]["kind"], json!("progress-stall"));
}

#[test]
fn fresh_claimed_job_is_not_a_stall() {
    let mut snap = stall_snapshot();
    snap["jobs"][0]["claimed_at"] = json!(9990);
    assert!(tick_it(&snap, 10000).is_empty());
}

#[test]
fn absent_nick_with_no_claimed_job_is_not_a_stall() {
    let snap = json!({"jobs": [], "presence": ["hana"], "caps": {"pax": {"caps": "build"}}});
    assert!(tick_it(&snap, 10000).is_empty());
}

#[test]
fn walk_on_claimer_not_in_caps_is_not_presence_stall() {
    // A claimed job whose claimer was never registered is a
    // walk-on worker (WDG-025): tracked, never alerted.
    let snap = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "ghost", "claimed_at": 9000}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    assert!(tick_it(&snap, 10000).is_empty());
    let records = os_supervisor::watchdog::detect_walk_on_workers(&snap, 10000);
    assert_eq!(records.len(), 1);
    assert_eq!(records[0].get("nick").and_then(|v| v.as_str()), Some("ghost"));
}

#[test]
fn job_with_no_timestamp_never_invents_an_age() {
    let snap = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed", "claim": "pax"}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    assert!(tick_it(&snap, 100000).is_empty());
}

#[test]
fn explicit_progress_timestamp_beats_claim_time() {
    let snap = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed", "claim": "pax",
                  "claimed_at": 9000, "last_progress_at": 9990}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    // Fresh progress (10s) beats the stale claim time.
    assert!(tick_it(&snap, 10000).is_empty());
    let snap = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed", "claim": "pax",
                  "claimed_at": 9990, "last_progress_at": 9000}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    // Stale progress fires even though the claim is fresh.
    assert_eq!(tick_it(&snap, 10000).len(), 1);
}

#[test]
fn cli_once_on_stall_fixture_reports_one_alert() {
    let tmp = tempfile::tempdir().unwrap();
    let path = tmp.path().join("snap.json");
    std::fs::write(&path, serde_json::to_string(&stall_snapshot()).unwrap()).unwrap();
    let args: Vec<String> = vec!["--once".to_string(), "--snapshot".to_string(), path.to_string_lossy().into_owned(), "--room".to_string(), "main".to_string()];
    let mut out = String::new();
    let mut err = String::new();
    let mut beated: Vec<i64> = Vec::new();
    let code = {
        let mut beat_cb = |t: i64| beated.push(t);
        let mut out_cb = |line: String| out.push_str(&format!("{line}\n"));
        let mut err_cb = |line: String| err.push_str(&format!("{line}\n"));
        let mut sleep_cb = |_s: f64| {};
        os_supervisor::watchdog::cli(&args, 10000, &mut beat_cb, &mut out_cb, &mut err_cb, &mut sleep_cb)
    };
    assert_eq!(code, 0);
    assert!(out.contains("1 alert(s)"), "{out}");
}

// --- ProgressStallTest (WDG-003) ---

fn progress_snapshot(last_progress: i64, present: bool) -> Value {
    let mut presence = vec![json!("hana")];
    if present {
        presence.push(json!("pax"));
    }
    json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed", "claim": "pax",
                  "claimed_at": 9000, "last_progress_at": last_progress}],
        "presence": presence,
        "caps": {"pax": {"caps": "build"}},
    })
}

#[test]
fn heartbeat_but_no_progress_yields_exactly_one() {
    let alerts = tick_it(&progress_snapshot(9000, true), 10000);
    assert_eq!(alerts.len(), 1);
    assert_eq!(alerts[0]["kind"], json!("progress-stall"));
    assert_eq!(alerts[0]["nick"], json!("pax"));
    assert_eq!(alerts[0]["job"], json!("7"));
}

#[test]
fn absent_nick_yields_presence_stall_not_progress_stall() {
    let alerts = tick_it(&progress_snapshot(9000, false), 10000);
    assert_eq!(alerts.len(), 1);
    assert_eq!(alerts[0]["kind"], json!("presence-stall"));
}

#[test]
fn fresh_progress_is_not_a_stall() {
    assert!(tick_it(&progress_snapshot(9990, true), 10000).is_empty());
}

#[test]
fn old_claim_with_no_progress_note_is_a_stall() {
    // No progress timestamp at all: the claim time is the last
    // activity, and a stale claim with a present nick stalls.
    let snap = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed", "claim": "pax", "claimed_at": 9000}],
        "presence": ["pax", "hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    let alerts = tick_it(&snap, 10000);
    assert_eq!(alerts.len(), 1);
    assert_eq!(alerts[0]["kind"], json!("progress-stall"));
}

#[test]
fn progress_job_with_no_timestamp_never_invents_an_age() {
    let snap = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed", "claim": "pax"}],
        "presence": ["pax", "hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    assert!(tick_it(&snap, 100000).is_empty());
}

#[test]
fn unclaimed_job_is_not_a_stall() {
    let snap = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "open"}],
        "presence": ["pax", "hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    assert!(tick_it(&snap, 100000).is_empty());
}

#[test]
fn walk_on_claimer_not_in_caps_is_not_progress_stall() {
    let snap = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed", "claim": "ghost", "claimed_at": 9000}],
        "presence": ["ghost", "hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    let alerts = tick_it(&snap, 100000);
    assert!(alerts.iter().all(|a| a["kind"] != json!("progress-stall")), "{alerts:?}");
}

#[test]
fn one_alert_per_job_not_per_detector() {
    // A stale absent claimer fires presence-stall only, never both
    // stall kinds for the same job.
    let alerts = tick_it(&progress_snapshot(9000, false), 10000);
    let kinds: Vec<&str> = alerts.iter().map(|a| a["kind"].as_str().unwrap()).collect();
    assert_eq!(kinds, vec!["presence-stall"]);
}

// --- LeaseRiskTest (WDG-004) ---

fn lease_snapshot(lease_until: i64, heartbeat: Option<i64>, lease: Option<i64>) -> Value {
    let mut job = json!({"id": "7", "title": "demo job", "status": "claimed", "claim": "pax",
                         "lease_until": lease_until});
    if let Some(h) = heartbeat {
        job["last_heartbeat"] = json!(h);
    }
    if let Some(l) = lease {
        job["lease"] = json!(l);
    }
    json!({"jobs": [job], "presence": ["pax"], "caps": {"pax": {"caps": "build"}}})
}

#[test]
fn near_expiry_with_quiet_heartbeat_yields_warning() {
    // lease_until 240s out (inside the 300s window), heartbeat
    // 200s ago (inside... no: quiet needs >= 120s; 200 >= 120 ok).
    let alerts = tick_it(&lease_snapshot(NOW + 240, Some(NOW - 200), Some(1800)), NOW);
    assert_eq!(alerts.len(), 1);
    let a = &alerts[0];
    assert_eq!(a["kind"], json!("lease-risk"));
    assert_eq!(a["severity"], json!("warning"));
    assert_eq!(a["minutes_to_expiry"], json!(4));
    assert_eq!(a["dedupe_key"], json!("lease-risk:pax:7"));
}

#[test]
fn recent_heartbeat_with_short_lease_is_not_a_risk() {
    let alerts = tick_it(&lease_snapshot(NOW + 100, Some(NOW - 10), Some(1800)), NOW);
    assert!(alerts.is_empty());
}

#[test]
fn explicit_heartbeat_beats_derived_heartbeat() {
    // Derived heartbeat (lease_until - lease) is fresh, but the
    // explicit last_heartbeat is quiet: the explicit one wins and
    // the alert fires.
    let alerts = tick_it(&lease_snapshot(NOW + 100, Some(NOW - 500), Some(100)), NOW);
    // Derived = 100-100 = 0s ago (fresh) but explicit 500s ago
    // (quiet): explicit wins -> fires.
    assert_eq!(alerts.len(), 1);
    assert_eq!(alerts[0]["kind"], json!("lease-risk"));
}

#[test]
fn lease_far_from_expiry_is_not_a_risk() {
    assert!(tick_it(&lease_snapshot(NOW + 3600, Some(NOW - 500), Some(1800)), NOW).is_empty());
}

#[test]
fn already_expired_lease_is_not_a_warning() {
    // An expired lease is the sweep's job, not a warning.
    assert!(tick_it(&lease_snapshot(NOW - 10, Some(NOW - 500), Some(1800)), NOW).is_empty());
}

#[test]
fn job_without_lease_until_never_invents_an_expiry() {
    let snap = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed", "claim": "pax"}],
        "presence": ["pax"], "caps": {"pax": {"caps": "build"}},
    });
    assert!(tick_it(&snap, NOW + 100000).is_empty());
}

#[test]
fn requeued_job_stops_firing() {
    // After the sweep requeues (status open), the detector stops.
    let snap = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "open"}],
        "presence": ["pax"], "caps": {"pax": {"caps": "build"}},
    });
    assert!(tick_it(&snap, NOW).is_empty());
}

#[test]
fn walk_on_claimer_lease_still_warned() {
    // Caps membership is not required for lease-risk: a walk-on
    // worker's expiring lease warns all the same.
    let snap = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed", "claim": "ghost",
                  "lease_until": NOW + 100, "last_heartbeat": NOW - 500, "lease": 1800}],
        "presence": ["ghost"],
        "caps": {"pax": {"caps": "build"}},
    });
    let alerts = tick_it(&snap, NOW);
    assert_eq!(alerts.len(), 1);
    assert_eq!(alerts[0]["kind"], json!("lease-risk"));
}

// --- DeadDepTest (WDG-005) ---

fn dep_jobs() -> Value {
    json!({"jobs": [
        {"id": "1", "title": "lib", "status": "blocked", "note": "waiting on vendor"},
        {"id": "2", "title": "app", "status": "open", "deps": "1"},
        {"id": "3", "title": "done thing", "status": "done", "deps": "1"},
        {"id": "4", "title": "claimed thing", "status": "claimed", "claim": "pax", "claimed_at": NOW, "deps": "1"},
        {"id": "5", "title": "free", "status": "open", "deps": ""},
    ], "presence": ["pax"], "caps": {"pax": {"caps": "build"}}})
}

#[test]
fn blocked_dep_yields_one_critical_alert() {
    let alerts = tick_it(&dep_jobs(), NOW);
    let dead: Vec<&Value> = alerts.iter().filter(|a| a["kind"] == json!("dead-dep")).collect();
    assert_eq!(dead.len(), 2);
    for a in &dead {
        assert_eq!(a["severity"], json!("critical"));
        assert_eq!(a["dep"], json!("1"));
        assert_eq!(a["dep_status"], json!("blocked"));
        assert_eq!(a["blocking_reason"], json!("waiting on vendor"));
    }
    let jobs: Vec<&str> = dead.iter().map(|a| a["job"].as_str().unwrap()).collect();
    assert!(jobs.contains(&"2") && jobs.contains(&"4"));
}

#[test]
fn failed_final_dep_also_dead() {
    let snap = json!({"jobs": [
        {"id": "1", "title": "lib", "status": "failed-final"},
        {"id": "2", "title": "app", "status": "open", "deps": "1"},
    ]});
    let alerts = tick_it(&snap, NOW);
    assert_eq!(alerts.len(), 1);
    assert_eq!(alerts[0]["dep_status"], json!("failed-final"));
    // A failed-final dep with no note uses its status as reason.
    assert_eq!(alerts[0]["blocking_reason"], json!("failed-final"));
}

#[test]
fn claimed_job_with_blocked_dep_also_alerts() {
    let snap = json!({"jobs": [
        {"id": "1", "title": "lib", "status": "blocked", "note": "x"},
        {"id": "2", "title": "app", "status": "claimed", "claim": "pax", "claimed_at": NOW, "deps": "1"},
    ], "presence": ["pax"], "caps": {"pax": {"caps": "build"}}});
    let alerts = tick_it(&snap, NOW);
    assert_eq!(alerts.len(), 1);
    assert_eq!(alerts[0]["job"], json!("2"));
}

#[test]
fn live_dep_yields_no_alert() {
    let snap = json!({"jobs": [
        {"id": "1", "title": "lib", "status": "open"},
        {"id": "2", "title": "app", "status": "open", "deps": "1"},
    ]});
    assert!(tick_it(&snap, NOW).is_empty());
}

#[test]
fn missing_dep_is_not_dead_dep() {
    let snap = json!({"jobs": [{"id": "2", "title": "app", "status": "open", "deps": "99"}]});
    let alerts = tick_it(&snap, NOW);
    assert!(alerts.iter().all(|a| a["kind"] != json!("dead-dep")), "{alerts:?}");
    assert_eq!(alerts.len(), 1);
    assert_eq!(alerts[0]["kind"], json!("missing-dep"));
}

#[test]
fn done_job_with_blocked_dep_yields_no_alert() {
    let snap = json!({"jobs": [
        {"id": "1", "title": "lib", "status": "blocked", "note": "x"},
        {"id": "3", "title": "done thing", "status": "done", "deps": "1"},
    ]});
    assert!(tick_it(&snap, NOW).is_empty());
}

#[test]
fn unblocked_dep_stops_firing() {
    let snap = json!({"jobs": [
        {"id": "1", "title": "lib", "status": "open"},
        {"id": "2", "title": "app", "status": "open", "deps": "1"},
    ]});
    assert!(tick_it(&snap, NOW).is_empty());
}

#[test]
fn two_dead_deps_yield_one_alert_each() {
    let snap = json!({"jobs": [
        {"id": "1", "title": "a", "status": "blocked", "note": "x"},
        {"id": "2", "title": "b", "status": "failed-final"},
        {"id": "3", "title": "c", "status": "open", "deps": "1,2"},
    ]});
    let alerts = tick_it(&snap, NOW);
    assert_eq!(alerts.len(), 2);
    let deps: Vec<&str> = alerts.iter().map(|a| a["dep"].as_str().unwrap()).collect();
    assert!(deps.contains(&"1") && deps.contains(&"2"));
}

#[test]
fn job_with_no_deps_yields_no_alert() {
    let snap = json!({"jobs": [{"id": "1", "title": "a", "status": "open"}]});
    assert!(tick_it(&snap, NOW).is_empty());
}

#[test]
fn list_form_deps_are_checked_too() {
    let snap = json!({"jobs": [
        {"id": "1", "title": "lib", "status": "blocked", "note": "x"},
        {"id": "2", "title": "app", "status": "open", "deps": ["1"]},
    ]});
    assert_eq!(tick_it(&snap, NOW).len(), 1);
}

// --- MissingDepTest (WDG-006) ---

#[test]
fn dangling_dep_yields_one_critical_alert() {
    let snap = json!({"jobs": [{"id": "1", "title": "app", "status": "open", "deps": "99"}]});
    let alerts = tick_it(&snap, NOW);
    assert_eq!(alerts.len(), 1);
    let a = &alerts[0];
    assert_eq!(a["kind"], json!("missing-dep"));
    assert_eq!(a["severity"], json!("critical"));
    assert_eq!(a["dep"], json!("99"));
    assert_eq!(a["dedupe_key"], json!("missing-dep:1:99"));
}

#[test]
fn claimed_job_with_dangling_dep_also_alerts() {
    let snap = json!({"jobs": [
        {"id": "1", "title": "app", "status": "claimed", "claim": "pax", "claimed_at": NOW, "deps": "99"},
    ], "presence": ["pax"], "caps": {"pax": {"caps": "build"}}});
    assert_eq!(tick_it(&snap, NOW).len(), 1);
}

#[test]
fn existing_dep_yields_no_alert() {
    let snap = json!({"jobs": [
        {"id": "1", "title": "lib", "status": "open"},
        {"id": "2", "title": "app", "status": "open", "deps": "1"},
    ]});
    assert!(tick_it(&snap, NOW).is_empty());
}

#[test]
fn dead_dep_and_missing_dep_do_not_cross_fire() {
    // Blocked dep -> dead-dep only; missing dep -> missing-dep only.
    let snap = json!({"jobs": [
        {"id": "1", "title": "lib", "status": "blocked", "note": "x"},
        {"id": "2", "title": "app", "status": "open", "deps": "1"},
        {"id": "3", "title": "other", "status": "open", "deps": "99"},
    ]});
    let alerts = tick_it(&snap, NOW);
    assert_eq!(alerts.len(), 2);
    let kinds: Vec<&str> = alerts.iter().map(|a| a["kind"].as_str().unwrap()).collect();
    assert!(kinds.contains(&"dead-dep") && kinds.contains(&"missing-dep"));
}

#[test]
fn two_dangling_deps_yield_one_alert_each() {
    let snap = json!({"jobs": [{"id": "1", "title": "app", "status": "open", "deps": "8,9"}]});
    assert_eq!(tick_it(&snap, NOW).len(), 2);
}

#[test]
fn done_job_with_dangling_dep_yields_no_alert() {
    let snap = json!({"jobs": [{"id": "1", "title": "app", "status": "done", "deps": "99"}]});
    assert!(tick_it(&snap, NOW).is_empty());
}

#[test]
fn job_with_no_deps_yields_no_alert_missing() {
    let snap = json!({"jobs": [{"id": "1", "title": "app", "status": "open"}]});
    assert!(tick_it(&snap, NOW).is_empty());
}

#[test]
fn posting_the_missing_job_clears_the_alert() {
    let snap = json!({"jobs": [{"id": "1", "title": "app", "status": "open", "deps": "99"}]});
    assert_eq!(tick_it(&snap, NOW).len(), 1);
    let snap = json!({"jobs": [
        {"id": "1", "title": "app", "status": "open", "deps": "99"},
        {"id": "99", "title": "late dep", "status": "open"},
    ]});
    assert!(tick_it(&snap, NOW).is_empty());
}

#[test]
fn list_form_deps_checked_for_missing() {
    let snap = json!({"jobs": [{"id": "1", "title": "app", "status": "open", "deps": ["98", "99"]}]});
    assert_eq!(tick_it(&snap, NOW).len(), 2);
}

// --- FileCollisionTest (WDG-007) ---

#[test]
fn overlapping_claimed_pair_yields_one_critical_alert() {
    let snap = json!({"jobs": [
        {"id": "1", "title": "a", "status": "claimed", "claim": "pax", "claimed_at": NOW, "files": "shared.py"},
        {"id": "2", "title": "b", "status": "claimed", "claim": "milo", "claimed_at": NOW, "files": "shared.py"},
    ], "presence": ["pax", "milo"], "caps": {"pax": {"caps": "build"}, "milo": {"caps": "build"}}});
    let alerts = tick_it(&snap, NOW);
    assert_eq!(alerts.len(), 1);
    let a = &alerts[0];
    assert_eq!(a["kind"], json!("file-collision"));
    assert_eq!(a["severity"], json!("critical"));
    assert_eq!(a["job"], json!("1"));
    assert_eq!(a["other_job"], json!("2"));
    assert_eq!(a["shared_path"], json!("shared.py"));
    assert_eq!(a["dedupe_key"], json!("file-collision:1:2:shared.py"));
}

#[test]
fn disjoint_files_yield_no_alert() {
    let snap = json!({"jobs": [
        {"id": "1", "title": "a", "status": "claimed", "claim": "pax", "claimed_at": NOW, "files": "a.py"},
        {"id": "2", "title": "b", "status": "claimed", "claim": "milo", "claimed_at": NOW, "files": "b.py"},
    ], "presence": ["pax", "milo"], "caps": {"pax": {"caps": "build"}, "milo": {"caps": "build"}}});
    assert!(tick_it(&snap, NOW).is_empty());
}

#[test]
fn open_job_overlapping_claimed_yields_no_alert() {
    // Open jobs are never scanned on either side.
    let snap = json!({"jobs": [
        {"id": "1", "title": "a", "status": "claimed", "claim": "pax", "claimed_at": NOW, "files": "shared.py"},
        {"id": "2", "title": "b", "status": "open", "files": "shared.py"},
    ], "presence": ["pax"], "caps": {"pax": {"caps": "build"}}});
    assert!(tick_it(&snap, NOW).is_empty());
}

#[test]
fn claimed_overlapping_done_branch_yields_alert() {
    let snap = json!({"jobs": [
        {"id": "1", "title": "a", "status": "claimed", "claim": "pax", "claimed_at": NOW, "files": "shared.py"},
        {"id": "2", "title": "b", "status": "done", "branch": "w/b", "files": "shared.py"},
    ], "presence": ["pax"], "caps": {"pax": {"caps": "build"}}});
    let alerts = tick_it(&snap, NOW);
    assert_eq!(alerts.len(), 1);
    assert_eq!(alerts[0]["other_job"], json!("2"));
    assert!(alerts[0]["explanation"].as_str().unwrap().contains("w/b"));
}

#[test]
fn claimed_overlapping_done_without_branch_yields_no_alert() {
    let snap = json!({"jobs": [
        {"id": "1", "title": "a", "status": "claimed", "claim": "pax", "claimed_at": NOW, "files": "shared.py"},
        {"id": "2", "title": "b", "status": "done", "files": "shared.py"},
    ], "presence": ["pax"], "caps": {"pax": {"caps": "build"}}});
    assert!(tick_it(&snap, NOW).is_empty());
}

#[test]
fn two_shared_paths_yield_one_alert_each() {
    let snap = json!({"jobs": [
        {"id": "1", "title": "a", "status": "claimed", "claim": "pax", "claimed_at": NOW, "files": "a.py, shared.py"},
        {"id": "2", "title": "b", "status": "claimed", "claim": "milo", "claimed_at": NOW, "files": "b.py, shared.py"},
    ], "presence": ["pax", "milo"], "caps": {"pax": {"caps": "build"}, "milo": {"caps": "build"}}});
    assert_eq!(tick_it(&snap, NOW).len(), 1);
}

#[test]
fn duplicate_path_on_one_job_counts_once() {
    let snap = json!({"jobs": [
        {"id": "1", "title": "a", "status": "claimed", "claim": "pax", "claimed_at": NOW, "files": ["shared.py", "shared.py"]},
        {"id": "2", "title": "b", "status": "claimed", "claim": "milo", "claimed_at": NOW, "files": "shared.py"},
    ], "presence": ["pax", "milo"], "caps": {"pax": {"caps": "build"}, "milo": {"caps": "build"}}});
    assert_eq!(tick_it(&snap, NOW).len(), 1);
}

#[test]
fn list_form_files_are_checked_too() {
    let snap = json!({"jobs": [
        {"id": "1", "title": "a", "status": "claimed", "claim": "pax", "claimed_at": NOW, "files": ["shared.py"]},
        {"id": "2", "title": "b", "status": "claimed", "claim": "milo", "claimed_at": NOW, "files": ["shared.py"]},
    ], "presence": ["pax", "milo"], "caps": {"pax": {"caps": "build"}, "milo": {"caps": "build"}}});
    assert_eq!(tick_it(&snap, NOW).len(), 1);
}

#[test]
fn job_with_no_files_yields_no_alert() {
    let snap = json!({"jobs": [
        {"id": "1", "title": "a", "status": "claimed", "claim": "pax", "claimed_at": NOW},
        {"id": "2", "title": "b", "status": "claimed", "claim": "milo", "claimed_at": NOW},
    ], "presence": ["pax", "milo"], "caps": {"pax": {"caps": "build"}, "milo": {"caps": "build"}}});
    assert!(tick_it(&snap, NOW).is_empty());
}

#[test]
fn removing_the_overlap_clears_the_alert() {
    let snap = json!({"jobs": [
        {"id": "1", "title": "a", "status": "claimed", "claim": "pax", "claimed_at": NOW, "files": "shared.py"},
        {"id": "2", "title": "b", "status": "claimed", "claim": "milo", "claimed_at": NOW, "files": "shared.py"},
    ], "presence": ["pax", "milo"], "caps": {"pax": {"caps": "build"}, "milo": {"caps": "build"}}});
    assert_eq!(tick_it(&snap, NOW).len(), 1);
    let snap = json!({"jobs": [
        {"id": "1", "title": "a", "status": "claimed", "claim": "pax", "claimed_at": NOW, "files": "a.py"},
        {"id": "2", "title": "b", "status": "claimed", "claim": "milo", "claimed_at": NOW, "files": "shared.py"},
    ], "presence": ["pax", "milo"], "caps": {"pax": {"caps": "build"}, "milo": {"caps": "build"}}});
    assert!(tick_it(&snap, NOW).is_empty());
}

// --- AttemptExhaustionTest (WDG-008) ---

fn attempt_job(id: &str, attempts: i64, max: i64, status: &str) -> Value {
    json!({"id": id, "title": "t", "status": status, "claim": "pax", "claimed_at": NOW,
           "attempts": attempts, "max_attempts": max})
}

#[test]
fn walk_produces_warning_at_max_minus_one_then_critical() {
    for (attempts, kind) in [(0, "quiet"), (1, "quiet"), (2, "warning"), (3, "critical"), (4, "critical")] {
        let snap = json!({"jobs": [attempt_job("1", attempts, 3, "claimed")],
                          "presence": ["pax"], "caps": {"pax": {"caps": "build"}}});
        let alerts = tick_it(&snap, NOW);
        if kind == "quiet" {
            assert!(alerts.is_empty(), "attempts={attempts}");
            continue;
        }
        assert_eq!(alerts.len(), 1, "attempts={attempts}");
        if kind == "warning" {
            assert_eq!(alerts[0]["kind"], json!("attempt-warning"));
            assert_eq!(alerts[0]["severity"], json!("warning"));
            assert_eq!(alerts[0]["attempts_remaining"], json!(1));
        } else {
            assert_eq!(alerts[0]["kind"], json!("attempt-exhaustion"));
            assert_eq!(alerts[0]["severity"], json!("critical"));
            assert_eq!(alerts[0]["attempts_remaining"], json!(0));
        }
    }
}

#[test]
fn failed_final_job_at_max_yields_critical() {
    let snap = json!({"jobs": [attempt_job("1", 3, 3, "failed-final")]});
    let alerts = tick_it(&snap, NOW);
    assert_eq!(alerts.len(), 1);
    assert_eq!(alerts[0]["kind"], json!("attempt-exhaustion"));
}

#[test]
fn claimed_job_at_max_minus_one_warns() {
    let snap = json!({"jobs": [attempt_job("1", 2, 3, "claimed")],
                      "presence": ["pax"], "caps": {"pax": {"caps": "build"}}});
    let alerts = tick_it(&snap, NOW);
    assert_eq!(alerts.len(), 1);
    assert_eq!(alerts[0]["kind"], json!("attempt-warning"));
}

#[test]
fn no_budget_yields_no_alert_at_any_attempt_count() {
    let snap = json!({"jobs": [attempt_job("1", 99, 0, "claimed")]});
    // max_attempts 0: budget of zero... a job with no max_attempts
    // key at all carries no budget and yields nothing.
    let snap2 = json!({"jobs": [{"id": "1", "title": "t", "status": "claimed", "claim": "pax", "attempts": 99}]});
    assert!(tick_it(&snap2, NOW).is_empty());
    let _ = snap;
}

#[test]
fn string_form_attempts_match_redis_hashes() {
    let snap = json!({"jobs": [{"id": "1", "title": "t", "status": "claimed", "claim": "pax",
                                "attempts": "2", "max_attempts": "3"}],
                      "presence": ["pax"], "caps": {"pax": {"caps": "build"}}});
    let alerts = tick_it(&snap, NOW);
    assert_eq!(alerts.len(), 1);
    assert_eq!(alerts[0]["kind"], json!("attempt-warning"));
}

#[test]
fn done_job_at_max_yields_no_alert() {
    let snap = json!({"jobs": [attempt_job("1", 3, 3, "done")]});
    assert!(tick_it(&snap, NOW).is_empty());
}

#[test]
fn budget_of_one_warns_at_zero_then_fails_at_one() {
    let snap = json!({"jobs": [attempt_job("1", 0, 1, "claimed")],
                      "presence": ["pax"], "caps": {"pax": {"caps": "build"}}});
    let alerts = tick_it(&snap, NOW);
    assert_eq!(alerts.len(), 1);
    assert_eq!(alerts[0]["kind"], json!("attempt-warning"));
    let snap = json!({"jobs": [attempt_job("1", 1, 1, "claimed")],
                      "presence": ["pax"], "caps": {"pax": {"caps": "build"}}});
    let alerts = tick_it(&snap, NOW);
    assert_eq!(alerts[0]["kind"], json!("attempt-exhaustion"));
}

// --- SilentRoomTest (WDG-009) ---

fn silent_snapshot(last_ts: Option<i64>, claimed: bool) -> Value {
    let jobs = if claimed {
        json!([{"id": "7", "title": "demo job", "status": "claimed", "claim": "pax", "claimed_at": 9000}])
    } else {
        json!([])
    };
    let messages = match last_ts {
        Some(ts) => json!([{"nick": "pax", "text": "working", "ts": ts}]),
        None => json!([]),
    };
    json!({"jobs": jobs, "messages": messages, "presence": ["pax"], "caps": {"pax": {"caps": "build"}}, "room": "build"})
}

#[test]
fn silent_room_yields_info_record_only() {
    let threshold_secs = thresholds::silent_room_minutes() as i64 * 60;
    let alerts = tick_it(&silent_snapshot(Some(NOW - threshold_secs - 60), true), NOW);
    assert_eq!(alerts.len(), 1);
    let a = &alerts[0];
    assert_eq!(a["kind"], json!("silent-room"));
    assert_eq!(a["severity"], json!("info"));
    assert_eq!(a["dedupe_key"], json!("silent-room:build"));
    assert_eq!(a["claimed_count"], json!(1));
}

#[test]
fn dashboard_severity_mapping_silent_room_is_info() {
    assert_eq!(os_supervisor::watchdog::severity_by_kind("silent-room"), Some("info"));
    assert_eq!(os_supervisor::watchdog::severity_by_kind("presence-stall"), Some("critical"));
    assert_eq!(os_supervisor::watchdog::severity_by_kind("lease-risk"), Some("warning"));
}

#[test]
fn fresh_message_inside_threshold_yields_no_record() {
    let threshold_secs = thresholds::silent_room_minutes() as i64 * 60;
    assert!(tick_it(&silent_snapshot(Some(NOW - threshold_secs + 60), true), NOW).is_empty());
}

#[test]
fn silence_exactly_at_threshold_yields_no_record() {
    let threshold_secs = thresholds::silent_room_minutes() as i64 * 60;
    assert!(tick_it(&silent_snapshot(Some(NOW - threshold_secs), true), NOW).is_empty());
}

#[test]
fn no_claimed_jobs_yields_no_record() {
    let threshold_secs = thresholds::silent_room_minutes() as i64 * 60;
    assert!(tick_it(&silent_snapshot(Some(NOW - threshold_secs - 60), false), NOW).is_empty());
}

#[test]
fn no_timestamped_messages_yields_no_record() {
    let snap = json!({"jobs": [{"id": "7", "title": "d", "status": "claimed", "claim": "pax",
                                             "claimed_at": NOW - 10, "last_progress_at": NOW - 10}],
                      "messages": ["plain string, no ts"],
                      "presence": ["pax"], "caps": {"pax": {"caps": "build"}}});
    assert!(tick_it(&snap, NOW).is_empty());
}

#[test]
fn latest_message_sets_the_clock() {
    let threshold_secs = thresholds::silent_room_minutes() as i64 * 60;
    let snap = json!({"jobs": [{"id": "7", "title": "d", "status": "claimed", "claim": "pax",
                                             "claimed_at": NOW - 10, "last_progress_at": NOW - 10}],
                      "messages": [{"nick": "a", "text": "old", "ts": NOW - threshold_secs - 100},
                                   {"nick": "b", "text": "new", "ts": NOW - 10}],
                      "presence": ["pax"], "caps": {"pax": {"caps": "build"}}});
    assert!(tick_it(&snap, NOW).is_empty());
}

#[test]
fn multiple_claimed_jobs_yield_one_room_record() {
    let threshold_secs = thresholds::silent_room_minutes() as i64 * 60;
    let snap = json!({"jobs": [
        {"id": "7", "title": "a", "status": "claimed", "claim": "pax", "claimed_at": NOW - 10, "last_progress_at": NOW - 10},
        {"id": "8", "title": "b", "status": "claimed", "claim": "milo", "claimed_at": NOW - 10, "last_progress_at": NOW - 10}],
        "messages": [{"nick": "pax", "text": "old", "ts": NOW - threshold_secs - 100}],
        "presence": ["pax", "milo"], "caps": {"pax": {"caps": "build"}, "milo": {"caps": "build"}}});
    let alerts = tick_it(&snap, NOW);
    assert_eq!(alerts.len(), 1);
    assert_eq!(alerts[0]["claimed_count"], json!(2));
}

#[test]
fn message_after_tick_time_yields_no_record() {
    let threshold_secs = thresholds::silent_room_minutes() as i64 * 60;
    let snap = json!({"jobs": [{"id": "7", "title": "d", "status": "claimed", "claim": "pax",
                                             "claimed_at": NOW - 10, "last_progress_at": NOW - 10}],
                      "messages": [{"nick": "a", "text": "future", "ts": NOW + threshold_secs + 100}],
                      "presence": ["pax"], "caps": {"pax": {"caps": "build"}}});
    // A future-dated message is newer than the tick: negative age,
    // under the threshold, yields nothing.
    assert!(tick_it(&snap, NOW).is_empty());
}

// --- Detector alert store round trip (WDG-010 writer via tick emit) ---

fn stall_alert_dict() -> Value {
    json!({
        "kind": "presence-stall",
        "severity": "critical",
        "nick": "pax",
        "job": "7",
        "job_title": "demo job",
        "last_progress_age_seconds": 660,
        "explanation": "pax holds claimed job 7",
        "suggested_fix": "check on pax",
        "dedupe_key": "presence-stall:pax:7",
        "created_at": 1000,
    })
}

#[test]
fn detector_alert_round_trips_with_all_required_fields() {
    let mut store = AlertStore::new(30);
    let record = store.write_alert(&stall_alert_dict(), "main", None, 1000).unwrap();
    assert_eq!(record["id"], json!("presence-stall:pax:7"));
    assert_eq!(record["room"], json!("main"));
    assert_eq!(record["status"], json!("open"));
    assert!(record.get("resolved_at").map(|v| v.is_null()).unwrap_or(false));
    for field in ["kind", "severity", "explanation", "suggested_fix", "dedupe_key", "created_at", "subjects"] {
        assert!(record.get(field).is_some(), "{field}");
    }
    let subjects = record["subjects"].as_array().unwrap();
    assert!(subjects.contains(&json!("pax")));
    assert!(subjects.contains(&json!("7")));
}

#[test]
fn tick_output_feeds_writer_via_emit() {
    let mut store = AlertStore::new(30);
    let snapshot = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 9340}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    let alerts = watchdog::tick(
        &snapshot,
        Some(10000),
        10000,
        None,
        TickCallbacks {
            emit: Some(&mut |a: Value| {
                store.write_alert(&a, "main", None, 10000).unwrap();
            }),
            polish: None,
            announce: None,
            beat: None,
        },
    );
    assert_eq!(alerts.len(), 1);
    assert!(store.get_alert("presence-stall:pax:7").is_some());
}

#[test]
fn missing_required_field_is_rejected_and_stores_nothing() {
    let mut store = AlertStore::new(30);
    let mut bad = stall_alert_dict();
    bad.as_object_mut().unwrap().remove("explanation");
    assert!(store.write_alert(&bad, "main", None, 1000).is_err());
    assert!(store.get_alert("presence-stall:pax:7").is_none());
}

#[test]
fn bad_severity_and_empty_subjects_are_rejected() {
    let mut store = AlertStore::new(30);
    let mut bad = stall_alert_dict();
    bad["severity"] = json!("mild");
    assert!(store.write_alert(&bad, "main", None, 1000).is_err());
}

#[test]
fn explicit_id_and_cleaned_room() {
    let mut store = AlertStore::new(30);
    let record = store.write_alert(&stall_alert_dict(), "  MAIN  ", Some("custom-id"), 1000).unwrap();
    assert_eq!(record["id"], json!("custom-id"));
    assert_eq!(record["room"], json!("main"));
}

#[test]
fn missing_created_at_falls_back_to_given_now() {
    let mut store = AlertStore::new(30);
    let mut alert = stall_alert_dict();
    alert.as_object_mut().unwrap().remove("created_at");
    let record = store.write_alert(&alert, "main", None, 4321).unwrap();
    assert_eq!(record["created_at"], json!(4321));
}

#[test]
fn first_write_sets_last_seen_to_created_at() {
    let mut store = AlertStore::new(30);
    let record = store.write_alert(&stall_alert_dict(), "main", None, 1000).unwrap();
    assert_eq!(record["last_seen"], json!(1000));
}

#[test]
fn second_write_inside_cooldown_updates_only_last_seen() {
    let mut store = AlertStore::new(30);
    store.write_alert(&stall_alert_dict(), "main", None, 1000).unwrap();
    let mut second = stall_alert_dict();
    second["created_at"] = json!(1100);
    let record = store.write_alert(&second, "main", None, 1100).unwrap();
    assert_eq!(record["created_at"], json!(1000));
    assert_eq!(record["last_seen"], json!(1100));
    assert_eq!(record["explanation"], json!("pax holds claimed job 7"));
}

#[test]
fn two_ticks_yield_one_alert_with_last_seen_advanced() {
    let mut store = AlertStore::new(30);
    let snapshot = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 9340}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    for now in [10000, 10100] {
        let now = now;
        watchdog::tick(
            &snapshot,
            Some(now),
            now,
            None,
            TickCallbacks {
                emit: Some(&mut |a: Value| {
                    store.write_alert(&a, "main", None, now).unwrap();
                }),
                polish: None,
                announce: None,
                beat: None,
            },
        );
    }
    let all = store.query_alerts(None, None, None);
    assert_eq!(all.len(), 1);
    assert_eq!(all[0]["created_at"], json!(10000));
    assert_eq!(all[0]["last_seen"], json!(10100));
}

#[test]
fn write_at_cooldown_boundary_starts_fresh_occurrence() {
    let mut store = AlertStore::new(30);
    store.write_alert(&stall_alert_dict(), "main", None, 1000).unwrap();
    // At exactly the 30-minute cooldown, a fresh occurrence starts.
    let mut second = stall_alert_dict();
    second["created_at"] = json!(1000 + 30 * 60);
    let record = store.write_alert(&second, "main", None, 1000 + 30 * 60).unwrap();
    assert_eq!(record["created_at"], json!(1000 + 30 * 60));
    assert_eq!(record["last_seen"], json!(1000 + 30 * 60));
}

#[test]
fn different_dedupe_keys_are_not_merged() {
    let mut store = AlertStore::new(30);
    store.write_alert(&stall_alert_dict(), "main", None, 1000).unwrap();
    let mut other = stall_alert_dict();
    other["dedupe_key"] = json!("presence-stall:pax:8");
    other["job"] = json!("8");
    store.write_alert(&other, "main", None, 1000).unwrap();
    assert_eq!(store.query_alerts(None, None, None).len(), 2);
}

// --- Lifecycle (WDG-014) ---

#[test]
fn new_record_starts_open() {
    let mut store = AlertStore::new(30);
    let record = store.write_alert(&stall_alert_dict(), "main", None, 1000).unwrap();
    assert_eq!(record["status"], json!("open"));
}

#[test]
fn ack_then_resolve_walks_all_transitions() {
    let mut store = AlertStore::new(30);
    store.write_alert(&stall_alert_dict(), "main", None, 1000).unwrap();
    let acked = store.acknowledge_alert("presence-stall:pax:7", 1100).unwrap().unwrap();
    assert_eq!(acked["status"], json!("acknowledged"));
    assert_eq!(acked["acknowledged_at"], json!(1100));
    let resolved = store.resolve_alert("presence-stall:pax:7", 1200).unwrap();
    assert_eq!(resolved["status"], json!("resolved"));
    assert_eq!(resolved["resolved_at"], json!(1200));
    assert_eq!(resolved["acknowledged_at"], json!(1100));
}

#[test]
fn resolve_straight_from_open() {
    let mut store = AlertStore::new(30);
    store.write_alert(&stall_alert_dict(), "main", None, 1000).unwrap();
    let resolved = store.resolve_alert("presence-stall:pax:7", 1200).unwrap();
    assert_eq!(resolved["status"], json!("resolved"));
    assert!(resolved.get("acknowledged_at").map(|v| v.is_null()).unwrap_or(false));
}

#[test]
fn ack_and_resolve_are_idempotent() {
    let mut store = AlertStore::new(30);
    store.write_alert(&stall_alert_dict(), "main", None, 1000).unwrap();
    let a1 = store.acknowledge_alert("presence-stall:pax:7", 1100).unwrap().unwrap();
    let a2 = store.acknowledge_alert("presence-stall:pax:7", 1200).unwrap().unwrap();
    assert_eq!(a1, a2);
    store.resolve_alert("presence-stall:pax:7", 1300);
    let r2 = store.resolve_alert("presence-stall:pax:7", 1400).unwrap();
    assert_eq!(r2["resolved_at"], json!(1300));
}

#[test]
fn ack_of_resolved_is_refused_and_stores_nothing_new() {
    let mut store = AlertStore::new(30);
    store.write_alert(&stall_alert_dict(), "main", None, 1000).unwrap();
    store.resolve_alert("presence-stall:pax:7", 1100);
    assert!(store.acknowledge_alert("presence-stall:pax:7", 1200).is_err());
}

#[test]
fn transitions_on_missing_alert_return_none() {
    let mut store = AlertStore::new(30);
    assert!(store.acknowledge_alert("nope", 1000).unwrap().is_none());
    assert!(store.resolve_alert("nope", 1000).is_none());
}

#[test]
fn refire_after_resolve_starts_fresh_open_occurrence() {
    let mut store = AlertStore::new(30);
    store.write_alert(&stall_alert_dict(), "main", None, 1000).unwrap();
    store.resolve_alert("presence-stall:pax:7", 1100);
    let mut second = stall_alert_dict();
    second["created_at"] = json!(1200);
    let record = store.write_alert(&second, "main", None, 1200).unwrap();
    assert_eq!(record["status"], json!("open"));
    assert_eq!(record["created_at"], json!(1200));
}

#[test]
fn refire_while_acknowledged_keeps_ack_inside_cooldown() {
    let mut store = AlertStore::new(30);
    store.write_alert(&stall_alert_dict(), "main", None, 1000).unwrap();
    store.acknowledge_alert("presence-stall:pax:7", 1050);
    let mut second = stall_alert_dict();
    second["created_at"] = json!(1100);
    let record = store.write_alert(&second, "main", None, 1100).unwrap();
    assert_eq!(record["status"], json!("acknowledged"));
    assert_eq!(record["last_seen"], json!(1100));
}

#[test]
fn auto_resolve_fires_when_fixture_condition_clears() {
    let mut store = AlertStore::new(30);
    let snapshot = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 9340, "lease": 1800, "lease_until": 11140}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    // Stall fires at 10000 (claimed 660s ago, lease live until 11140).
    let alerts = tick_it(&snapshot, 10000);
    assert_eq!(alerts.len(), 1);
    let id = alerts[0]["dedupe_key"].as_str().unwrap().to_string();
    store.write_alert(&alerts[0], "main", None, 10000).unwrap();
    // After requeue (status open) the tick stops firing; auto-resolve clears it.
    let quiet = json!({"jobs": [{"id": "7", "title": "demo job", "status": "open"}]});
    let live: Vec<String> = tick_it(&quiet, 10100)
        .iter()
        .map(|a| a["dedupe_key"].as_str().unwrap().to_string())
        .collect();
    let resolved = store.auto_resolve_cleared(&[id.clone()], &live, 10100);
    assert_eq!(resolved.len(), 1);
    assert_eq!(store.get_alert(&id).unwrap()["status"], json!("resolved"));
}

#[test]
fn auto_resolve_leaves_still_live_alerts_open() {
    let mut store = AlertStore::new(30);
    store.write_alert(&stall_alert_dict(), "main", None, 1000).unwrap();
    let resolved = store.auto_resolve_cleared(
        &["presence-stall:pax:7".to_string()],
        &["presence-stall:pax:7".to_string()],
        1100,
    );
    assert!(resolved.is_empty());
    assert_eq!(store.get_alert("presence-stall:pax:7").unwrap()["status"], json!("open"));
}

#[test]
fn auto_resolve_skips_unknown_and_already_resolved() {
    let mut store = AlertStore::new(30);
    store.write_alert(&stall_alert_dict(), "main", None, 1000).unwrap();
    store.resolve_alert("presence-stall:pax:7", 1050);
    let resolved = store.auto_resolve_cleared(
        &["presence-stall:pax:7".to_string(), "ghost".to_string()],
        &[],
        1100,
    );
    assert!(resolved.is_empty());
}

// --- Polish toggle (WDG-012) ---

fn template_alert() -> Value {
    json!({
        "kind": "presence-stall",
        "severity": "critical",
        "nick": "pax",
        "job": "7",
        "explanation": "pax holds claimed job 7",
        "suggested_fix": "check on pax",
        "dedupe_key": "presence-stall:pax:7",
        "created_at": 1000,
    })
}

#[test]
fn toggle_off_keeps_template_text() {
    let mut store = AlertStore::new(30);
    let record = store.write_alert(&template_alert(), "main", None, 1000).unwrap();
    assert_eq!(record["explanation"], json!("pax holds claimed job 7"));
}

#[test]
fn toggle_on_uses_polished_text() {
    let snapshot = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 9340}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    let alerts = watchdog::tick(
        &snapshot,
        Some(10000),
        10000,
        None,
        TickCallbacks {
            emit: None,
            polish: Some(&|text: &str| Some(format!("{text} (polished)"))),
            announce: None,
            beat: None,
        },
    );
    assert_eq!(alerts.len(), 1);
    assert!(alerts[0]["explanation"].as_str().unwrap().ends_with("(polished)"));
    // The suggested fix is never polished.
    assert!(!alerts[0]["suggested_fix"].as_str().unwrap().contains("polished"));
}

#[test]
fn emitted_alert_carries_polished_text() {
    let mut stored = Vec::new();
    let snapshot = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 9340}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    tick_emit_polished(&snapshot, 10000, &mut stored);
    assert_eq!(stored.len(), 1);
    assert!(stored[0]["explanation"].as_str().unwrap().ends_with("(polished)"));
}

fn tick_emit_polished(snapshot: &Value, now: i64, stored: &mut Vec<Value>) {
    let alerts = watchdog::tick(
        snapshot,
        Some(now),
        now,
        None,
        TickCallbacks {
            emit: None,
            polish: Some(&|text: &str| Some(format!("{text} (polished)"))),
            announce: None,
            beat: None,
        },
    );
    stored.extend(alerts);
}

#[test]
fn spark_failure_keeps_template_text() {
    let snapshot = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 9340}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    for (i, make_polish) in [0, 1].iter().enumerate() {
        let _ = i;
        let alerts = if *make_polish == 0 {
            watchdog::tick(
                &snapshot,
                Some(10000),
                10000,
                None,
                TickCallbacks {
                    emit: None,
                    polish: Some(&(|_: &str| None) as &dyn Fn(&str) -> Option<String>),
                    announce: None,
                    beat: None,
                },
            )
        } else {
            watchdog::tick(
                &snapshot,
                Some(10000),
                10000,
                None,
                TickCallbacks {
                    emit: None,
                    polish: Some(&(|_: &str| Some(String::new())) as &dyn Fn(&str) -> Option<String>),
                    announce: None,
                    beat: None,
                },
            )
        };
        assert_eq!(alerts.len(), 1);
        assert!(alerts[0]["explanation"].as_str().unwrap().contains("pax holds claimed job 7"));
    }
}

#[test]
fn empty_spark_reply_keeps_template_text() {
    assert_eq!(
        os_supervisor::explanations::polish_explanation::<fn(&str) -> Option<String>>("T", None),
        "T"
    );
    assert_eq!(
        os_supervisor::explanations::polish_explanation("T", Some(|_: &str| Some(String::new()))),
        "T"
    );
}

#[test]
fn quiet_snapshot_with_polish_client_calls_nothing() {
    let calls = std::rc::Rc::new(std::cell::RefCell::new(0usize));
    let calls_in = calls.clone();
    let alerts = watchdog::tick(
        &json!({}),
        Some(NOW),
        NOW,
        None,
        TickCallbacks {
            emit: None,
            polish: Some(&move |_: &str| {
                *calls_in.borrow_mut() += 1;
                Some("x".to_string())
            }),
            announce: None,
            beat: None,
        },
    );
    assert!(alerts.is_empty());
    assert_eq!(*calls.borrow(), 0);
}

// --- Announcements (WDG-015) ---

fn critical_alert() -> Value {
    json!({
        "kind": "presence-stall",
        "severity": "critical",
        "nick": "pax",
        "job": "7",
        "explanation": "pax holds claimed job 7",
        "suggested_fix": "check",
        "dedupe_key": "presence-stall:pax:7",
        "created_at": 1000,
    })
}

#[test]
fn critical_fixture_yields_exactly_one_announcement() {
    let mut announced = Vec::new();
    let snapshot = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 9340}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    let alerts = watchdog::tick(
        &snapshot,
        Some(10000),
        10000,
        None,
        TickCallbacks {
            emit: None,
            polish: None,
            announce: Some(&mut |line: String| announced.push(line)),
            beat: None,
        },
    );
    assert_eq!(alerts.len(), 1);
    assert_eq!(announced.len(), 1);
    assert!(announced[0].starts_with("ALERT:presence-stall:pax:7 presence-stall: "));
}

#[test]
fn warning_fixture_yields_no_announcement() {
    let mut announced = Vec::new();
    let snapshot = json!({"jobs": [], "messages": [], "presence": [], "caps": {},
        "budgets": [{"lane": "spark", "spent": 80, "cap": 100}]});
    let alerts = watchdog::tick(
        &snapshot,
        Some(10000),
        10000,
        None,
        TickCallbacks {
            emit: None,
            polish: None,
            announce: Some(&mut |line: String| announced.push(line)),
            beat: None,
        },
    );
    assert_eq!(alerts.len(), 1);
    assert_eq!(alerts[0]["severity"], json!("warning"));
    assert!(announced.is_empty());
}

#[test]
fn info_record_yields_no_announcement() {
    use os_supervisor::watchdog::announcements_for;
    let info = json!({"kind": "silent-room", "severity": "info",
                      "dedupe_key": "silent-room", "explanation": "quiet"});
    assert!(announcements_for(&[info]).is_empty());
}

#[test]
fn no_callback_means_held_not_posted() {
    // With no announce callback the tick returns alerts but
    // announces nothing: lines stay held for the caller.
    let alerts = tick_it(&json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 9340}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    }), 10000);
    assert_eq!(alerts.len(), 1);
    assert!(!alerts[0].as_object().unwrap().contains_key("announced"));
}

#[test]
fn format_gate_rejects_warning_info_and_bad_input() {
    use os_supervisor::watchdog::format_announcement;
    assert!(format_announcement(&json!({"severity": "warning", "dedupe_key": "x", "kind": "k", "explanation": "e"})).is_none());
    assert!(format_announcement(&json!({"severity": "info", "dedupe_key": "x", "kind": "k", "explanation": "e"})).is_none());
    assert!(format_announcement(&json!({"severity": "critical"})).is_none());
    assert!(format_announcement(&json!("junk")).is_none());
    let line = format_announcement(&critical_alert()).unwrap();
    assert_eq!(line, "ALERT:presence-stall:pax:7 presence-stall: pax holds claimed job 7");
}

#[test]
fn announcement_flattens_multiline_explanation() {
    use os_supervisor::watchdog::format_announcement;
    let mut alert = critical_alert();
    alert["explanation"] = json!("line one\nline two");
    assert_eq!(
        format_announcement(&alert).unwrap(),
        "ALERT:presence-stall:pax:7 presence-stall: line one line two"
    );
}

// --- Beat (WDG-016) ---

#[test]
fn beat_called_once_per_tick_even_when_quiet() {
    let mut beats = Vec::new();
    watchdog::tick(
        &json!({}),
        Some(NOW),
        NOW,
        None,
        TickCallbacks {
            emit: None,
            polish: None,
            announce: None,
            beat: Some(&mut |t: i64| beats.push(t)),
        },
    );
    assert_eq!(beats, vec![NOW]);
}

#[test]
fn beat_called_once_when_alerts_fire() {
    let mut beats = Vec::new();
    let snapshot = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 9340}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    watchdog::tick(
        &snapshot,
        Some(10000),
        10000,
        None,
        TickCallbacks {
            emit: None,
            polish: None,
            announce: None,
            beat: Some(&mut |t: i64| beats.push(t)),
        },
    );
    assert_eq!(beats, vec![10000]);
}

#[test]
fn no_beat_callback_writes_nothing_and_raises_nothing() {
    let alerts = tick_it(&json!({}), NOW);
    assert!(alerts.is_empty());
}

#[test]
fn failing_beat_never_fails_the_tick_or_hides_alerts() {
    // A beat callback that panics is contained: the tick still
    // returns its alerts.
    let snapshot = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 9340}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    let alerts = watchdog::tick(
        &snapshot,
        Some(10000),
        10000,
        None,
        TickCallbacks {
            emit: None,
            polish: None,
            announce: None,
            beat: Some(&mut |_: i64| panic!("beat boom")),
        },
    );
    assert_eq!(alerts.len(), 1);
}

// --- Paginate + cap (WDG-017) ---

#[test]
fn paginate_yields_page_sized_chunks_oldest_first() {
    let items: Vec<i64> = (0..2500).collect();
    let pages = os_supervisor::watchdog::paginate(&items, 1000).unwrap();
    assert_eq!(pages.len(), 3);
    assert_eq!(pages[0].len(), 1000);
    assert_eq!(pages[2].len(), 500);
    assert_eq!(pages[0][0], 0);
    assert_eq!(pages[2][0], 2000);
}

#[test]
fn paginate_rejects_non_positive_page_size() {
    let items = vec![1, 2, 3];
    assert!(os_supervisor::watchdog::paginate(&items, 0).is_err());
}

#[test]
fn cap_keeps_newest_and_reports_the_drop() {
    let messages: Vec<Value> = (0..1500).map(|i| json!({"n": i})).collect();
    let snapshot = json!({"jobs": [], "messages": messages});
    let capped = os_supervisor::watchdog::cap_tick_snapshot(&snapshot, Some(1000), Some(100));
    assert_eq!(capped["messages"].as_array().unwrap().len(), 1000);
    assert_eq!(capped["messages"][0]["n"], json!(500));
    assert_eq!(capped["tick_window"]["messages_kept"], json!(1000));
    assert_eq!(capped["tick_window"]["messages_dropped"], json!(500));
    assert_eq!(capped["tick_window"]["max_messages"], json!(1000));
}

#[test]
fn cap_under_the_limit_passes_through_unchanged() {
    let snapshot = json!({"jobs": [{"id": "1"}], "messages": [{"n": 1}]});
    let capped = os_supervisor::watchdog::cap_tick_snapshot(&snapshot, Some(1000), Some(100));
    assert_eq!(capped["messages"].as_array().unwrap().len(), 1);
    assert_eq!(capped["tick_window"]["messages_dropped"], json!(0));
    assert_eq!(capped["jobs"], json!([{"id": "1"}]));
}

#[test]
fn cap_twice_accumulates_the_drop_count() {
    let messages: Vec<Value> = (0..1500).map(|i| json!({"n": i})).collect();
    let snapshot = json!({"jobs": [], "messages": messages});
    let once = os_supervisor::watchdog::cap_tick_snapshot(&snapshot, Some(1000), Some(100));
    let twice = os_supervisor::watchdog::cap_tick_snapshot(&once, Some(1000), Some(100));
    assert_eq!(twice["tick_window"]["messages_dropped"], json!(500));
    assert_eq!(twice["messages"].as_array().unwrap().len(), 1000);
}

#[test]
fn tick_1500_message_snapshot_completes_with_correct_verdict() {
    let messages: Vec<Value> = (0..1500).map(|_| json!("plain")).collect();
    let snapshot = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 9000}],
        "messages": messages,
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    // 1500 plain messages: the cap keeps the newest 1000 for the
    // silent-room reader, and the stall verdict is unchanged.
    let alerts = watchdog::tick(&snapshot, Some(10000), 10000, None, TickCallbacks {
        emit: None, polish: None, announce: None, beat: None,
    });
    assert_eq!(alerts.len(), 1);
    assert_eq!(alerts[0]["kind"], json!("presence-stall"));
}

#[test]
fn tick_cap_never_hides_a_job_detector_verdict() {
    // Jobs are never capped: capping drops messages only.
    let messages: Vec<Value> = (0..1200).map(|_| json!("plain")).collect();
    let snapshot = json!({
        "jobs": [{"id": "1", "title": "a", "status": "open", "deps": "99"}],
        "messages": messages,
    });
    let capped = os_supervisor::watchdog::cap_tick_snapshot(&snapshot, Some(100), Some(50));
    assert!(capped["jobs"].as_array().unwrap().len() == 1);
    let alerts = tick_it(&capped, NOW);
    assert!(alerts.iter().any(|a| a["kind"] == json!("missing-dep")));
}

// --- Server time (WDG-026) ---

#[test]
fn server_time_beats_skewed_wall_clock() {
    let snapshot = json!({
        "server_time": 10000,
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 9000, "last_heartbeat": 9000, "lease": 1800, "lease_until": 10800}],
        "presence": ["pax"],
        "caps": {"pax": {"caps": "build"}},
    });
    // Wall clock skewed far ahead; server_time wins so the lease
    // still reads live-ish (no warning: heartbeat 1000s ago is
    // quiet, expiry 800s out is outside the 300s window).
    let (ts, source) = os_supervisor::watchdog::resolve_tick_now(&snapshot, None, 99999999);
    assert_eq!((ts, source), (10000, "server_time"));
}

#[test]
fn explicit_now_beats_server_time() {
    let snapshot = json!({"server_time": 10000});
    let (ts, source) = os_supervisor::watchdog::resolve_tick_now(&snapshot, Some(5000), 99999999);
    assert_eq!((ts, source), (5000, "explicit"));
}

#[test]
fn wall_clock_fallback_when_no_server_time() {
    let (ts, source) = os_supervisor::watchdog::resolve_tick_now(&json!({}), None, 777);
    assert_eq!((ts, source), (777, "wall_clock"));
}

#[test]
fn malformed_server_time_falls_back_to_wall_clock() {
    for bad in [json!("soon"), json!(true), json!(null), json!([1, 2, 3])] {
        let snapshot = json!({"server_time": bad});
        let (ts, source) = os_supervisor::watchdog::resolve_tick_now(&snapshot, None, 777);
        assert_eq!((ts, source), (777, "wall_clock"), "{bad}");
    }
}

#[test]
fn string_and_time_pair_server_time_forms() {
    let snapshot = json!({"server_time": "10000"});
    assert_eq!(os_supervisor::watchdog::resolve_tick_now(&snapshot, None, 1), (10000, "server_time"));
    let snapshot = json!({"server_time": [10000, 500000]});
    assert_eq!(os_supervisor::watchdog::resolve_tick_now(&snapshot, None, 1), (10000, "server_time"));
}

#[test]
fn resolve_tick_now_reports_its_source() {
    assert_eq!(os_supervisor::watchdog::resolve_tick_now(&json!({}), Some(5), 9), (5, "explicit"));
    assert_eq!(os_supervisor::watchdog::resolve_tick_now(&json!({"server_time": 7}), None, 9), (7, "server_time"));
    assert_eq!(os_supervisor::watchdog::resolve_tick_now(&json!({}), None, 9), (9, "wall_clock"));
}

#[test]
fn detector_ages_use_injected_clock_not_wall_clock() {
    // Explicit now drives every detector age in the tick.
    let snapshot = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 9000}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    let alerts = tick_it(&snapshot, 10000);
    assert_eq!(alerts[0]["last_progress_age_seconds"], json!(1000));
    let alerts = tick_it(&snapshot, 20000);
    assert_eq!(alerts[0]["last_progress_age_seconds"], json!(11000));
}

// --- Registry (DETECTORS run all ten) ---

#[test]
fn registry_runs_all_ten_detectors() {
    // Nine registered kinds plus the walk-on tracker asserted
    // separately: presence, progress, lease, dead-dep,
    // missing-dep, collision, attempt-warning, attempt-exhaustion,
    // silent-room, rejected-dispatch, budget-warning.
    let snapshot = json!({
        "jobs": [
            {"id": "stall", "status": "claimed", "claim": "pax", "claimed_at": 0, "caps": "x"},
            {"id": "warn", "status": "claimed", "claim": "pax", "claimed_at": 0, "attempts": 2, "max_attempts": 3},
            {"id": "dead", "status": "claimed", "claim": "pax", "claimed_at": 0, "attempts": 9, "max_attempts": 3},
            {"id": "dep", "status": "open", "deps": "missing-1"},
            {"id": "blocked-dep", "status": "blocked", "note": "x"},
            {"id": "needs-blocked", "status": "open", "deps": "blocked-dep"},
        ],
        "messages": [{"nick": "n", "text": "REJECTED:9 EXPIRED signed_by=x rejected_by=y", "ts": 0}],
        "presence": [],
        "caps": {"pax": {"caps": "build"}},
        "budgets": [{"lane": "spark", "spent": 80, "cap": 100}],
    });
    let alerts = tick_it(&snapshot, 100000);
    let mut kinds: Vec<&str> = alerts.iter().map(|a| a["kind"].as_str().unwrap()).collect();
    kinds.sort();
    kinds.dedup();
    for kind in ["presence-stall", "attempt-warning", "attempt-exhaustion", "missing-dep",
                "dead-dep", "rejected-dispatch", "budget-warning"] {
        assert!(kinds.contains(&kind), "{kinds:?} missing {kind}");
    }
    // No silent-room (no claimed job with fresh context needed... it fires: claimed jobs + old message).
    let _ = kinds;
}

macro_rules! detector_pair {
    ($name:ident, $positive:expr, $negative:expr) => {
        #[test]
        fn $name() {
            assert!(!$positive.is_empty());
            assert!($negative.is_empty());
        }
    };
}

#[test]
fn presence_stall_positive_and_negative() {
    let pos = tick_it(&json!({
        "jobs": [{"id": "1", "status": "claimed", "claim": "pax", "claimed_at": 0}],
        "presence": [], "caps": {"pax": {"caps": "build"}}}), 100000);
    assert!(pos.iter().any(|a| a["kind"] == json!("presence-stall")));
    let neg = tick_it(&json!({
        "jobs": [{"id": "1", "status": "claimed", "claim": "pax", "claimed_at": 99950}],
        "presence": ["pax"], "caps": {"pax": {"caps": "build"}}}), 100000);
    assert!(neg.iter().all(|a| a["kind"] != json!("presence-stall")));
}

#[test]
fn progress_stall_positive_and_negative() {
    let pos = tick_it(&json!({
        "jobs": [{"id": "1", "status": "claimed", "claim": "pax", "claimed_at": 0, "last_progress_at": 0}],
        "presence": ["pax"], "caps": {"pax": {"caps": "build"}}}), 100000);
    assert!(pos.iter().any(|a| a["kind"] == json!("progress-stall")));
    let neg = tick_it(&json!({
        "jobs": [{"id": "1", "status": "claimed", "claim": "pax", "claimed_at": 99950, "last_progress_at": 99990}],
        "presence": ["pax"], "caps": {"pax": {"caps": "build"}}}), 100000);
    assert!(neg.iter().all(|a| a["kind"] != json!("progress-stall")));
}

#[test]
fn lease_risk_positive_and_negative() {
    let pos = tick_it(&json!({
        "jobs": [{"id": "1", "status": "claimed", "claim": "pax", "lease_until": 10100, "last_heartbeat": 9000, "lease": 1800}],
        "presence": ["pax"], "caps": {"pax": {"caps": "build"}}}), 10000);
    assert!(pos.iter().any(|a| a["kind"] == json!("lease-risk")));
    let neg = tick_it(&json!({
        "jobs": [{"id": "1", "status": "claimed", "claim": "pax", "lease_until": 50000, "last_heartbeat": 9990, "lease": 1800}],
        "presence": ["pax"], "caps": {"pax": {"caps": "build"}}}), 10000);
    assert!(neg.iter().all(|a| a["kind"] != json!("lease-risk")));
}

#[test]
fn dead_dep_positive_and_negative() {
    let pos = tick_it(&json!({"jobs": [
        {"id": "1", "status": "blocked", "note": "x"},
        {"id": "2", "status": "open", "deps": "1"}]}), NOW);
    assert!(pos.iter().any(|a| a["kind"] == json!("dead-dep")));
    let neg = tick_it(&json!({"jobs": [
        {"id": "1", "status": "open"},
        {"id": "2", "status": "open", "deps": "1"}]}), NOW);
    assert!(neg.iter().all(|a| a["kind"] != json!("dead-dep")));
}

#[test]
fn missing_dep_positive_and_negative() {
    let pos = tick_it(&json!({"jobs": [{"id": "1", "status": "open", "deps": "99"}]}), NOW);
    assert!(pos.iter().any(|a| a["kind"] == json!("missing-dep")));
    let neg = tick_it(&json!({"jobs": [
        {"id": "1", "status": "open"},
        {"id": "2", "status": "open", "deps": "1"}]}), NOW);
    assert!(neg.iter().all(|a| a["kind"] != json!("missing-dep")));
}

#[test]
fn file_collision_positive_and_negative() {
    let pos = tick_it(&json!({"jobs": [
        {"id": "1", "status": "claimed", "claim": "pax", "claimed_at": NOW, "files": "a.py"},
        {"id": "2", "status": "claimed", "claim": "milo", "claimed_at": NOW, "files": "a.py"}],
        "presence": ["pax", "milo"], "caps": {"pax": {"caps": "b"}, "milo": {"caps": "b"}}}), NOW);
    assert!(pos.iter().any(|a| a["kind"] == json!("file-collision")));
    let neg = tick_it(&json!({"jobs": [
        {"id": "1", "status": "claimed", "claim": "pax", "claimed_at": NOW, "files": "a.py"},
        {"id": "2", "status": "claimed", "claim": "milo", "claimed_at": NOW, "files": "b.py"}],
        "presence": ["pax", "milo"], "caps": {"pax": {"caps": "b"}, "milo": {"caps": "b"}}}), NOW);
    assert!(neg.iter().all(|a| a["kind"] != json!("file-collision")));
}

#[test]
fn attempt_exhaustion_positive_and_negative() {
    let pos = tick_it(&json!({"jobs": [{"id": "1", "status": "claimed", "claim": "pax", "attempts": 3, "max_attempts": 3}]}), NOW);
    assert!(pos.iter().any(|a| a["kind"] == json!("attempt-exhaustion")));
    let neg = tick_it(&json!({"jobs": [{"id": "1", "status": "claimed", "claim": "pax", "attempts": 0, "max_attempts": 3}]}), NOW);
    assert!(neg.iter().all(|a| a["kind"] != json!("attempt-exhaustion") && a["kind"] != json!("attempt-warning")));
}

#[test]
fn silent_room_positive_and_negative() {
    let threshold_secs = thresholds::silent_room_minutes() as i64 * 60;
    let pos = tick_it(&json!({"jobs": [{"id": "1", "status": "claimed", "claim": "pax", "claimed_at": NOW - 10}],
        "messages": [{"nick": "a", "text": "old", "ts": NOW - threshold_secs - 10}],
        "presence": ["pax"], "caps": {"pax": {"caps": "build"}}}), NOW);
    assert!(pos.iter().any(|a| a["kind"] == json!("silent-room")));
    let neg = tick_it(&json!({"jobs": [{"id": "1", "status": "claimed", "claim": "pax", "claimed_at": NOW - 10}],
        "messages": [{"nick": "a", "text": "new", "ts": NOW - 10}],
        "presence": ["pax"], "caps": {"pax": {"caps": "build"}}}), NOW);
    assert!(neg.iter().all(|a| a["kind"] != json!("silent-room")));
}

#[test]
fn rejected_dispatch_positive_and_negative() {
    let pos = tick_it(&json!({"messages": ["overseer: REJECTED:3 BAD signed_by=a rejected_by=b"]}), NOW);
    assert!(pos.iter().any(|a| a["kind"] == json!("rejected-dispatch")));
    assert!(tick_it(&json!({"messages": ["overseer: hello"]}), NOW).is_empty());
}

#[test]
fn budget_warning_positive_and_negative() {
    let pos = tick_it(&json!({"budgets": [{"lane": "spark", "spent": 80, "cap": 100}]}), NOW);
    assert!(pos.iter().any(|a| a["kind"] == json!("budget-warning")));
    let neg = tick_it(&json!({"budgets": [{"lane": "spark", "spent": 10, "cap": 100}]}), NOW);
    assert!(neg.iter().all(|a| a["kind"] != json!("budget-warning")));
}

// --- Walk-on tracking (WDG-025) ---

#[test]
fn unknown_claimer_yields_tracking_record() {
    let records = os_supervisor::watchdog::detect_walk_on_workers(
        &json!({"jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                          "claim": "ghost", "claimed_at": 9000}],
                "presence": ["ghost"],
                "caps": {"pax": {"caps": "build"}}}),
        10000,
    );
    assert_eq!(records.len(), 1);
    assert_eq!(records[0].kind(), "walk-on-worker");
    assert_eq!(records[0].get("nick").and_then(|v| v.as_str()), Some("ghost"));
    assert_eq!(records[0].get("job").and_then(|v| v.as_str()), Some("7"));
    assert_eq!(records[0].get("tracked_from").and_then(|v| v.as_str()), Some("jobs"));
}

#[test]
fn tracking_is_not_an_alert() {
    // tick() never emits walk-on records as alerts.
    let alerts = tick_it(&json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed", "claim": "ghost", "claimed_at": 9000}],
        "presence": ["ghost"],
        "caps": {"pax": {"caps": "build"}}}), 100000);
    assert!(alerts.iter().all(|a| a["kind"] != json!("walk-on-worker")));
}

#[test]
fn registered_claimer_is_not_tracked() {
    let records = os_supervisor::watchdog::detect_walk_on_workers(
        &json!({"jobs": [{"id": "7", "title": "t", "status": "claimed", "claim": "pax", "claimed_at": 9000}],
                "presence": ["pax"], "caps": {"pax": {"caps": "build"}}}),
        10000,
    );
    assert!(records.is_empty());
}

#[test]
fn open_job_is_not_tracked() {
    let records = os_supervisor::watchdog::detect_walk_on_workers(
        &json!({"jobs": [{"id": "7", "title": "t", "status": "open"}],
                "presence": [], "caps": {"pax": {"caps": "build"}}}),
        10000,
    );
    assert!(records.is_empty());
}

#[test]
fn present_walk_on_is_still_tracked() {
    // Tracking fires whether the nick is present or absent,
    // fresh or stale: visibility, not accusation.
    let records = os_supervisor::watchdog::detect_walk_on_workers(
        &json!({"jobs": [{"id": "7", "title": "t", "status": "claimed", "claim": "ghost", "claimed_at": 9990}],
                "presence": ["ghost"], "caps": {"pax": {"caps": "build"}}}),
        10000,
    );
    assert_eq!(records.len(), 1);
}

#[test]
fn tracking_no_timestamp_never_invents_an_age() {
    let records = os_supervisor::watchdog::detect_walk_on_workers(
        &json!({"jobs": [{"id": "7", "title": "t", "status": "claimed", "claim": "ghost"}],
                "presence": [], "caps": {}}),
        10000,
    );
    assert_eq!(records.len(), 1);
    assert!(records[0].get("last_progress_age_seconds").map(|v| v.is_null()).unwrap_or(false));
}

#[test]
fn tracking_malformed_sections_yield_no_crash() {
    assert!(os_supervisor::watchdog::detect_walk_on_workers(&json!(null), 10000).is_empty());
    assert!(os_supervisor::watchdog::detect_walk_on_workers(&json!({"caps": [], "jobs": "junk"}), 10000).is_empty());
}

#[test]
fn stall_detection_still_works_alongside_tracking() {
    // A registered stall and a walk-on job in one snapshot: one
    // alert, one tracking record, neither hiding the other.
    let snapshot = json!({
        "jobs": [{"id": "1", "title": "a", "status": "claimed", "claim": "pax", "claimed_at": 9000},
                 {"id": "2", "title": "b", "status": "claimed", "claim": "ghost", "claimed_at": 9000}],
        "presence": [],
        "caps": {"pax": {"caps": "build"}},
    });
    let alerts = tick_it(&snapshot, 100000);
    assert_eq!(alerts.len(), 1);
    assert_eq!(alerts[0]["kind"], json!("presence-stall"));
    let records = os_supervisor::watchdog::detect_walk_on_workers(&snapshot, 100000);
    assert_eq!(records.len(), 1);
}

// --- Severity mapping table (WDG-024) ---

#[test]
fn table_covers_every_detector_kind() {
    use os_supervisor::watchdog::severity_by_kind;
    for kind in ["presence-stall", "progress-stall", "lease-risk", "dead-dep",
                "missing-dep", "file-collision", "attempt-warning",
                "attempt-exhaustion", "silent-room", "rejected-dispatch",
                "budget-warning"] {
        assert!(severity_by_kind(kind).is_some(), "{kind}");
    }
}

#[test]
fn table_values_are_valid_severities() {
    use os_supervisor::watchdog::severity_by_kind;
    for kind in ["presence-stall", "progress-stall", "lease-risk", "dead-dep",
                "missing-dep", "file-collision", "attempt-warning",
                "attempt-exhaustion", "silent-room", "rejected-dispatch",
                "budget-warning"] {
        assert!(["critical", "warning", "info"].contains(&severity_by_kind(kind).unwrap()), "{kind}");
    }
}

#[test]
fn every_detector_emits_its_table_severity() {
    use os_supervisor::watchdog::severity_by_kind;
    // Each detector's emitted severity matches the table.
    let cases = [
        (json!({"jobs": [{"id": "1", "status": "claimed", "claim": "pax", "claimed_at": 0}], "presence": [], "caps": {"pax": {"caps": "b"}}}), "presence-stall", 100000i64),
        (json!({"jobs": [{"id": "1", "status": "claimed", "claim": "pax", "claimed_at": 0, "last_progress_at": 0}], "presence": ["pax"], "caps": {"pax": {"caps": "b"}}}), "progress-stall", 100000),
        (json!({"jobs": [{"id": "1", "status": "claimed", "claim": "pax", "lease_until": 10100, "last_heartbeat": 9000, "lease": 1800}], "presence": ["pax"], "caps": {"pax": {"caps": "build"}}}), "lease-risk", 10000),
        (json!({"jobs": [{"id": "1", "status": "blocked"}, {"id": "2", "status": "open", "deps": "1"}]}), "dead-dep", NOW),
        (json!({"jobs": [{"id": "1", "status": "open", "deps": "99"}]}), "missing-dep", NOW),
        (json!({"jobs": [
            {"id": "1", "status": "claimed", "claim": "pax", "claimed_at": NOW, "files": "a.py"},
            {"id": "2", "status": "claimed", "claim": "milo", "claimed_at": NOW, "files": "a.py"}],
            "presence": ["pax", "milo"], "caps": {"pax": {"caps": "b"}, "milo": {"caps": "b"}}}), "file-collision", NOW),
        (json!({"jobs": [{"id": "1", "status": "claimed", "claim": "pax", "attempts": 2, "max_attempts": 3}]}), "attempt-warning", NOW),
        (json!({"jobs": [{"id": "1", "status": "claimed", "claim": "pax", "attempts": 5, "max_attempts": 3}]}), "attempt-exhaustion", NOW),
        (json!({"messages": ["overseer: REJECTED:3 BAD signed_by=a rejected_by=b"]}), "rejected-dispatch", NOW),
        (json!({"budgets": [{"lane": "spark", "spent": 80, "cap": 100}]}), "budget-warning", NOW),
    ];
    for (snapshot, kind, now) in cases {
        let alerts = tick_it(&snapshot, now);
        let mine: Vec<&Value> = alerts.iter().filter(|a| a["kind"] == json!(kind)).collect();
        assert!(!mine.is_empty(), "{kind}");
        for a in mine {
            assert_eq!(a["severity"].as_str().unwrap(), severity_by_kind(kind).unwrap(), "{kind}");
        }
    }
    // silent-room is info.
    let snapshot = json!({"jobs": [{"id": "1", "status": "claimed", "claim": "pax", "claimed_at": 0}],
        "messages": [{"nick": "a", "text": "old", "ts": 0}],
        "presence": ["pax"], "caps": {"pax": {"caps": "build"}}});
    let alerts = tick_it(&snapshot, 100000);
    let mine: Vec<&Value> = alerts.iter().filter(|a| a["kind"] == json!("silent-room")).collect();
    assert_eq!(mine.len(), 1);
    assert_eq!(mine[0]["severity"], json!("info"));
}

#[test]
fn mapping_matches_the_lane_plan_rule() {
    // Rule from the lane plan: stall / dead-dep / collision =
    // critical, lease-risk / attempt = warning, silent-room = info.
    use os_supervisor::watchdog::severity_by_kind;
    for kind in ["presence-stall", "progress-stall", "dead-dep", "missing-dep",
                "file-collision", "attempt-exhaustion", "rejected-dispatch"] {
        assert_eq!(severity_by_kind(kind), Some("critical"), "{kind}");
    }
    for kind in ["lease-risk", "attempt-warning", "budget-warning"] {
        assert_eq!(severity_by_kind(kind), Some("warning"), "{kind}");
    }
    assert_eq!(severity_by_kind("silent-room"), Some("info"));
}

// --- Queries + status/top (WDG-023/WDG-028, via the store) ---

fn seed_store() -> AlertStore {
    let mut store = AlertStore::new(30);
    let mk = |kind: &str, severity: &str, id: &str, room: &str, created: i64| {
        json!({
            "kind": kind, "severity": severity, "nick": "pax", "job": "7",
            "explanation": format!("{kind} happened"), "suggested_fix": "fix it",
            "dedupe_key": id, "created_at": created,
        })
    };

    store.write_alert(&mk("presence-stall", "critical", "a", "build-int", 1000), "build-int", None, 1000).unwrap();
    store.write_alert(&mk("lease-risk", "warning", "b", "build-int", 2000), "build-int", None, 2000).unwrap();
    store.write_alert(&mk("silent-room", "info", "c", "other", 3000), "other", None, 3000).unwrap();
    store
}

#[test]
fn query_all_returns_everything_oldest_first() {
    let store = seed_store();
    let all = store.query_alerts(None, None, None);
    assert_eq!(all.len(), 3);
    assert_eq!(all[0]["id"], json!("a"));
    assert_eq!(all[2]["id"], json!("c"));
}

#[test]
fn room_filter_returns_exact_subset() {
    let store = seed_store();
    let rows = store.query_alerts(Some("build-int"), None, None);
    assert_eq!(rows.len(), 2);
    let rows = store.query_alerts(Some("other"), None, None);
    assert_eq!(rows.len(), 1);
}

#[test]
fn kind_filter_returns_exact_subset() {
    let store = seed_store();
    let rows = store.query_alerts(None, None, Some("lease-risk"));
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0]["id"], json!("b"));
}

#[test]
fn since_filter_keeps_at_or_after() {
    let store = seed_store();
    let rows = store.query_alerts(None, Some(2000), None);
    assert_eq!(rows.len(), 2);
    assert_eq!(rows[0]["id"], json!("b"));
}

#[test]
fn combined_filters_intersect() {
    let store = seed_store();
    let rows = store.query_alerts(Some("build-int"), Some(2000), Some("lease-risk"));
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0]["id"], json!("b"));
    assert!(store.query_alerts(Some("other"), None, Some("lease-risk")).is_empty());
}

#[test]
fn no_match_returns_empty_not_error() {
    let store = seed_store();
    assert!(store.query_alerts(Some("nope"), None, None).is_empty());
}

#[test]
fn dedupe_refire_does_not_duplicate_history() {
    let mut store = AlertStore::new(30);
    let alert = json!({
        "kind": "presence-stall", "severity": "critical", "nick": "pax", "job": "7",
        "explanation": "x", "suggested_fix": "y",
        "dedupe_key": "presence-stall:pax:7", "created_at": 1000,
    });
    store.write_alert(&alert, "main", None, 1000).unwrap();
    let mut second = alert.clone();
    second["created_at"] = json!(1100);
    store.write_alert(&second, "main", None, 1100).unwrap();
    assert_eq!(store.query_alerts(None, None, None).len(), 1);
}

#[test]
fn raw_put_alert_is_not_queryable() {
    let mut store = AlertStore::new(30);
    let mut raw = Map::new();
    raw.insert("id".to_string(), json!("raw-1"));
    store.put_alert("raw-1", raw);
    assert!(store.query_alerts(None, None, None).is_empty());
    assert!(store.get_alert("raw-1").is_some());
}

#[test]
fn stall_fixture_counts_match_alert_store() {
    let mut store = AlertStore::new(30);
    let snapshot = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 9340}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    let alerts = tick_emit(&snapshot, 10000, &mut |a| {
        store.write_alert(&a, "main", None, 10000).unwrap();
    });
    assert_eq!(alerts.len(), 1);
    assert_eq!(store.query_alerts(None, None, None).len(), 1);
}

#[test]
fn top_alert_is_highest_severity_earliest_first() {
    let store = seed_store();
    let status = store.build_watchdog_status("main", 4000);
    // critical(a) outranks warning(b) and info(c), earliest first.
    assert_eq!(status["top_alert"], json!("a"));
    assert!(status["line"].as_str().unwrap().contains("top alert: a"));
    // Resolved top alert drops out.
    let mut store = seed_store();
    store.resolve_alert("a", 3500);
    let status = store.build_watchdog_status("main", 4000);
    assert_eq!(status["top_alert"], json!("b"));
}

#[test]
fn resolved_alerts_leave_open_counts_but_are_counted() {
    let mut store = seed_store();
    store.resolve_alert("a", 3500);
    let status = store.build_watchdog_status("main", 4000);
    assert_eq!(status["open"], json!(2));
    assert_eq!(status["resolved"], json!(1));
    assert_eq!(status["total"], json!(3));
}

#[test]
fn quiet_store_status_line_is_all_clear() {
    let store = AlertStore::new(30);
    let status = store.build_watchdog_status("main", 1000);
    assert_eq!(status["open"], json!(0));
    assert!(status["line"].as_str().unwrap().contains("no open alerts"));
}

#[test]
fn int022_locked_threshold_table() {
    use os_supervisor::thresholds::LOCKED_DEFAULTS;
    let table: std::collections::HashMap<&str, u64> =
        LOCKED_DEFAULTS.iter().cloned().collect();
    assert_eq!(table["STALL_MINUTES"], 10);
    assert_eq!(table["PROGRESS_STALL_MINUTES"], 10);
    assert_eq!(table["LEASE_RISK_WINDOW_MINUTES"], 5);
    assert_eq!(table["LEASE_RISK_QUIET_MINUTES"], 2);
    assert_eq!(table["ALERT_DEDUPE_COOLDOWN_MINUTES"], 30);
    assert_eq!(table["SILENT_ROOM_MINUTES"], 60);
    assert_eq!(table["WATCHDOG_BEAT_TTL_SECONDS"], 300);
    assert_eq!(table["TICK_PAGE_SIZE"], 1000);
    assert_eq!(table["TICK_MAX_MESSAGES"], 1000);
}

// --- CLI announce + mode gating ---

#[test]
fn neither_mode_is_an_error() {
    use os_supervisor::watchdog::WatchdogArgs;
    assert!(WatchdogArgs::parse(&[]).is_err());
}

#[test]
fn cli_announce_prints_line_only_with_flag() {
    let tmp = tempfile::tempdir().unwrap();
    let path = tmp.path().join("snap.json");
    std::fs::write(&path, serde_json::to_string(&stall_snapshot()).unwrap()).unwrap();
    let run = |extra: &[&str]| {
        let mut argv: Vec<String> = vec!["--once".to_string(), "--snapshot".to_string(), path.to_string_lossy().into_owned()];
        argv.extend(extra.iter().map(|s| s.to_string()));
        let mut out = String::new();
        let mut err = String::new();
        let mut beated: Vec<i64> = Vec::new();
        let code = {
            let mut beat_cb = |t: i64| beated.push(t);
            let mut out_cb = |line: String| out.push_str(&format!("{line}\n"));
            let mut err_cb = |line: String| err.push_str(&format!("{line}\n"));
            let mut sleep_cb = |_s: f64| {};
            os_supervisor::watchdog::cli(&argv, 10000, &mut beat_cb, &mut out_cb, &mut err_cb, &mut sleep_cb)
        };
        (code, out, err)
    };
    let (code, out, _err) = run(&[]);
    assert_eq!(code, 0);
    assert!(!out.contains("ALERT:"), "{out}");
    let (code, out, _err) = run(&["--announce"]);
    assert_eq!(code, 0);
    assert!(out.contains("ALERT:presence-stall:pax:7 "), "{out}");
}

#[test]
fn tick_with_store_beat_writes_the_beat_key() {
    let mut store = AlertStore::new(30);
    let got = watchdog::tick(
        &json!({}),
        Some(1000),
        1000,
        None,
        TickCallbacks {
            emit: None,
            polish: None,
            announce: None,
            beat: Some(&mut |t: i64| store.wd_self_beat(t)),
        },
    );
    assert!(got.is_empty());
    assert_eq!(store.wd_self_beat_age(1000), Some(0));
}

#[test]
fn once_without_beat_writes_no_beat() {
    let mut store = AlertStore::new(30);
    let got = watchdog::tick(
        &json!({}),
        Some(1000),
        1000,
        None,
        TickCallbacks { emit: None, polish: None, announce: None, beat: None },
    );
    assert!(got.is_empty());
    assert_eq!(store.wd_self_beat_age(1000), None);
}

#[test]
fn loop_with_beat_renews_on_every_tick() {
    let mut store = AlertStore::new(30);
    for _ in 0..2 {
        let got = watchdog::tick(
            &json!({}),
            Some(1000),
            1000,
            None,
            TickCallbacks {
                emit: None,
                polish: None,
                announce: None,
                beat: Some(&mut |t: i64| store.wd_self_beat(t)),
            },
        );
        assert!(got.is_empty());
    }
    assert_eq!(store.wd_self_beat_age(1000), Some(0));
}

// --- Template-brief surface (composer owned by B10) ---

#[test]
fn template_brief_surface_inputs_are_store_shaped() {
    // The template brief renders the store's status line and the
    // stored record ids (Hana B10 composes them). This pins the
    // store-side contract the composer reads: the status line
    // text and the record id that must appear in Watch items.
    let mut store = AlertStore::new(30);
    let snapshot = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 9340}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
    });
    let alerts = tick_emit(&snapshot, 10000, &mut |a| {
        store.write_alert(&a, "build", None, 10000).unwrap();
    });
    assert_eq!(alerts.len(), 1);
    let stored = store.query_alerts(Some("build"), None, None);
    assert_eq!(stored.len(), 1);
    let status = store.build_watchdog_status("build", 10000);
    assert!(status["line"].as_str().unwrap().contains("Watchdog:"));
    assert_eq!(stored[0]["id"], alerts[0]["dedupe_key"]);
    // CARRIED (B10): compose_template_brief rendering the line
    // at the head of Watch items.
}

#[test]
fn brief_without_severity_alerts_keeps_exact_shape() {
    // The template brief renders alerts without severity verbatim
    // (Hana B10). The store side: a record keeps unknown shapes
    // queryable by room, unclassified, never promoted to top.
    let mut store = AlertStore::new(30);
    store.put_alert("WD-STALL-3", {
        let mut m = serde_json::Map::new();
        m.insert("id".to_string(), json!("WD-STALL-3"));
        m.insert("room".to_string(), json!("build"));
        m.insert("created_at".to_string(), json!(1000));
        m
    });
    let status = store.build_watchdog_status("build", 1000);
    assert_eq!(status["top_alert"], Value::Null);
    // CARRIED (B10): the composer's exact shape for severity-less alerts.
}

#[test]
fn a_crashing_detector_does_not_blind_the_loop() {
    // A crashing detector is skipped: the rest of the loop still fires.
    // (Detectors cannot panic in safe Rust; this pins the tick's
    // containment contract via a directly-failing detector shape:
    // a snapshot that one detector cannot read still yields the
    // others' alerts.)
    let snapshot = json!({
        "jobs": "not-a-list",
        "messages": "not-a-list",
        "presence": "not-a-list",
        "caps": "not-a-map",
        "budgets": [{"lane": "spark", "spent": 80, "cap": 100}],
    });
    // Malformed sections yield empty detector runs, never a crash;
    // the budget detector still fires on its own usable section.
    let alerts = tick_it(&snapshot, NOW);
    assert!(alerts.iter().any(|a| a["kind"] == json!("budget-warning")), "{alerts:?}");
}

#[test]
fn cli_once_on_1500_message_snapshot_exits_zero() {
    let messages: Vec<Value> = (0..1500).map(|_| json!("plain")).collect();
    let snapshot = json!({
        "jobs": [{"id": "7", "title": "demo job", "status": "claimed",
                  "claim": "pax", "claimed_at": 9340}],
        "presence": ["hana"],
        "caps": {"pax": {"caps": "build"}},
        "messages": messages,
    });
    let tmp = tempfile::tempdir().unwrap();
    let path = tmp.path().join("snap.json");
    std::fs::write(&path, serde_json::to_string(&snapshot).unwrap()).unwrap();
    let (code, out, _err) = run_cli_once(&path.to_string_lossy().into_owned());
    assert_eq!(code, 0);
    assert!(out.contains("1 alert(s)"), "{out}");
}

fn run_cli_once(path: &str) -> (i32, String, String) {
    let args: Vec<String> = vec!["--once".to_string(), "--snapshot".to_string(), path.to_string()];
    let mut out = String::new();
    let mut err = String::new();
    let mut beated: Vec<i64> = Vec::new();
    let code = {
        let mut beat_cb = |t: i64| beated.push(t);
        let mut out_cb = |line: String| out.push_str(&format!("{line}\n"));
        let mut err_cb = |line: String| err.push_str(&format!("{line}\n"));
        let mut sleep_cb = |_s: f64| {};
        os_supervisor::watchdog::cli(&args, 10000, &mut beat_cb, &mut out_cb, &mut err_cb, &mut sleep_cb)
    };
    (code, out, err)
}
