//! B21 drills, ported as in-process phase runners.
//!
//! - `os/intel/drills/kill_worker.py` (presence-stall kill drill)
//! - `os/intel/drills/watchman_boot.py` (OS-129, 15 checks)
//! - `os/intel/drills/watchman_bridge.py` (4 phases)
//! - `os/intel/drills/watchman_bridge_tick.py` (5 phases)
//! - `os/intel/drills/watchman_cycle.py` (6 phases)
//! - `os/intel/drills/watchman_loop.py` (5 phases + 2b/2c)
//! - `os/intel/drills/watchman_runner.py` (6 phases)
//! - `os/intel/drills/watchman_service.py` (7 phases)
//! - `os/intel/drills/watchman_service_cli.py` (5 phases)
//! - `os/intel/drills/watchman_watch.py` (kill/revive/escalate)

use serde_json::{json, Value};

use crate::thresholds;
use crate::watchman_boot;
use crate::watchdog;

// --- kill_worker drill ---

fn stall_age_secs() -> i64 {
    thresholds::stall_minutes() as i64 * 60
}

/// Fixture mirror of jobs.py `_claim_or_requeue`'s requeue rule.
fn sweep_expired_leases(snapshot: &mut Value, now: i64) -> Vec<String> {
    let mut requeued = Vec::new();
    if let Some(jobs) = snapshot.get_mut("jobs").and_then(|v| v.as_array_mut()) {
        for job in jobs.iter_mut() {
            let obj = match job.as_object_mut() {
                Some(o) => o,
                None => continue,
            };
            if obj.get("status").and_then(|v| v.as_str()) != Some("claimed") {
                continue;
            }
            let lease_until = match obj.get("lease_until").and_then(|v| v.as_i64()) {
                Some(v) => v,
                None => continue,
            };
            if now < lease_until {
                continue;
            }
            for field in ["claim", "claim_host", "claimed_at", "lease_until"] {
                obj.remove(field);
            }
            obj.insert("status".to_string(), Value::String("open".to_string()));
            if let Some(id) = obj.get("id").and_then(|v| v.as_str()) {
                requeued.push(id.to_string());
            }
        }
    }
    requeued
}

/// Run the kill_worker drill phases; returns the phase log.
pub fn run_kill_worker() -> Result<Vec<String>, String> {
    let t0 = 100_000i64;
    let mut log = Vec::new();
    let mut snapshot = json!({"messages": [], "jobs": [], "presence": [], "caps": {"pax": {"caps": "build"}}});
    // Phase 1: healthy worker claims, progresses, heartbeats.
    let claim = json!({"id": "7", "title": "demo job", "status": "claimed", "claim": "pax",
        "claimed_at": t0, "lease": thresholds::LEASE_DEFAULT_SECONDS,
        "lease_until": t0 + thresholds::LEASE_DEFAULT_SECONDS as i64});
    snapshot["jobs"] = json!([claim]);
    snapshot["presence"] = json!(["pax"]);
    if let Some(jobs) = snapshot.get_mut("jobs").and_then(|v| v.as_array_mut()) {
        jobs[0]["last_progress"] = json!(t0 + 120);
        jobs[0]["last_heartbeat"] = json!(t0 + 300);
    }
    let got = watchdog::tick(&snapshot, Some(t0 + 300), t0 + 300, None, watchdog::TickCallbacks { emit: None, polish: None, announce: None, beat: None });
    if !got.is_empty() {
        return Err(format!("healthy worker must yield zero alerts, got {got:?}"));
    }
    log.push("phase 1: healthy worker yields zero alerts".to_string());
    // Phase 2: the kill.
    snapshot["presence"] = json!([]);
    let stall_at = t0 + 300 + stall_age_secs() + 61;
    let got = watchdog::tick(&snapshot, Some(stall_at), stall_at, None, watchdog::TickCallbacks { emit: None, polish: None, announce: None, beat: None });
    if got.len() != 1 {
        return Err(format!("dead worker must yield exactly one alert, got {}", got.len()));
    }
    let alert = &got[0];
    if alert["kind"] != json!("presence-stall") || alert["nick"] != json!("pax") || alert["job"] != json!("7") {
        return Err(format!("alert must name pax/7 presence-stall, got {alert}"));
    }
    let expected_age = stall_at - (t0 + 120);
    if alert["last_progress_age_seconds"] != json!(expected_age) {
        return Err(format!("age must be {expected_age}, got {}", alert["last_progress_age_seconds"]));
    }
    let lines = watchdog::announcements_for(&got);
    if lines.len() != 1 || !lines[0].starts_with("ALERT:") {
        return Err(format!("announcement line held not posted, got {lines:?}"));
    }
    log.push(format!("phase 2: presence-stall alert names pax/7, age {expected_age}s; announcement line held, not posted"));
    // Phase 3: the sweep must NOT requeue before the lease ends.
    if !sweep_expired_leases(&mut snapshot, stall_at).is_empty() {
        return Err("unexpired lease stays claimed (no early requeue)".to_string());
    }
    if snapshot["jobs"][0]["status"] != json!("claimed") {
        return Err("job must stay claimed".to_string());
    }
    log.push("phase 3: unexpired lease stays claimed (no early requeue)".to_string());
    // Phase 4: lease expires, sweep requeues, alert auto-resolves.
    let requeue_at = t0 + thresholds::LEASE_DEFAULT_SECONDS as i64 + 1;
    let requeued = sweep_expired_leases(&mut snapshot, requeue_at);
    if requeued != vec!["7".to_string()] {
        return Err(format!("sweep must requeue 7, got {requeued:?}"));
    }
    if snapshot["jobs"][0]["status"] != json!("open") {
        return Err("job must be open".to_string());
    }
    let got = watchdog::tick(&snapshot, Some(requeue_at), requeue_at, None, watchdog::TickCallbacks { emit: None, polish: None, announce: None, beat: None });
    if !got.is_empty() {
        return Err(format!("requeued job must stop firing, got {got:?}"));
    }
    log.push("phase 4: lease expiry requeues job; re-tick yields zero alerts, job open for the next worker".to_string());
    Ok(log)
}

// --- watchman_boot drill (OS-129, 15 checks) ---

/// Run the watchman_boot drill checks; returns (passed, failed).
pub fn run_watchman_boot_drill() -> (usize, usize, Vec<String>) {
    let mut passed = 0usize;
    let mut failed = 0usize;
    let mut log = Vec::new();
    let mut check = |name: &str, ok: bool, detail: String| {
        if ok {
            passed += 1;
            log.push(format!("PASS {name}"));
        } else {
            failed += 1;
            log.push(format!("FAIL {name} -- {detail}"));
        }
    };
    let t0 = 100_000f64;
    let t1 = 100_600f64;
    let jobs = json!([
        {"id": "job-arrive-1", "status": "open", "posted_at": t0 + 100.0},
        {"id": "job-arrive-2", "status": "open", "posted_at": t0 + 500.0},
        {"id": "job-before", "status": "open", "posted_at": t0 - 50.0},
        {"id": "job-after", "status": "open", "posted_at": t1 + 10.0},
        {"id": "job-lease-dead", "status": "claimed", "claimed_by": "hana", "lease_expires_at": t0 + 300.0},
        {"id": "job-lease-live", "status": "claimed", "claimed_by": "rowan", "lease_expires_at": t1 + 900.0},
        {"id": "job-done", "status": "done", "lease_expires_at": t0 + 200.0},
        {"bad-record": "open"},
        "not-a-record",
        {"status": "open", "posted_at": t0 + 10.0},
    ]);
    let rings = watchman_boot::post_boot_rings(&jobs, t0, t1, None);
    let ring_ids: Vec<&str> = rings.iter().map(|r| r.job_id.as_str()).collect();
    let reasons: std::collections::HashMap<&str, &str> =
        rings.iter().map(|r| (r.job_id.as_str(), r.reason.as_str())).collect();
    check(
        "arrival rings",
        ring_ids == ["job-arrive-1", "job-arrive-2", "job-lease-dead"]
            && reasons.get("job-arrive-1") == Some(&"arrived_during_downtime")
            && reasons.get("job-arrive-2") == Some(&"arrived_during_downtime")
            && reasons.get("job-lease-dead") == Some(&"lease_expired_during_downtime"),
        format!("rings={ring_ids:?}"),
    );
    check("pre-window open job does not ring", !ring_ids.contains(&"job-before"), String::new());
    check("post-boot open job does not ring", !ring_ids.contains(&"job-after"), String::new());
    check("live lease does not ring", !ring_ids.contains(&"job-lease-live"), String::new());
    check("done job never rings", !ring_ids.contains(&"job-done"), String::new());
    check("malformed records never ring and never crash", !ring_ids.contains(&"bad-record"), String::new());
    let mut doubled = jobs.as_array().cloned().unwrap_or_default();
    doubled.push(json!({"id": "job-arrive-1", "status": "open", "posted_at": t0 + 100.0}));
    let doubled_rings = watchman_boot::post_boot_rings(&Value::Array(doubled), t0, t1, None);
    let doubled_ids: Vec<&str> = doubled_rings.iter().map(|r| r.job_id.as_str()).collect();
    check(
        "duplicate input rings once",
        doubled_ids.iter().filter(|id| **id == "job-arrive-1").count() == 1,
        String::new(),
    );
    let second = watchman_boot::post_boot_rings(&jobs, t0, t1, Some(&ring_ids.iter().map(|s| s.to_string()).collect::<Vec<_>>()));
    check("second boot cycle rings nothing new", second.is_empty(), String::new());
    // Counter proof is inside verify_boot_cycle; the drill also
    // recomputes with a poisoned snapshot.
    let mut poisoned = jobs.as_array().cloned().unwrap_or_default();
    for job in poisoned.iter_mut() {
        if let Some(obj) = job.as_object_mut() {
            obj.insert("seen_counter".to_string(), json!(999999));
        }
    }
    let poisoned_ids: Vec<String> = watchman_boot::post_boot_rings(&Value::Array(poisoned), t0, t1, None)
        .into_iter()
        .map(|r| r.job_id)
        .collect();
    check(
        "corrupted stored counter changes nothing",
        poisoned_ids == ring_ids,
        format!("rings={poisoned_ids:?}"),
    );
    let note = watchman_boot::verify_boot_cycle(&jobs, t0, t1, &[json!("job-lease-dead")], None);
    check(
        "sweep reconciliation agrees",
        note.reconciled
            && note.total_rings == 3
            && note.arrived_count == 2
            && note.lease_expired_count == 1
            && note.counter_ignored,
        format!("counts={}/{}/{}", note.total_rings, note.arrived_count, note.lease_expired_count),
    );
    let bad_note = watchman_boot::verify_boot_cycle(&jobs, t0, t1, &[json!("job-stranger")], None);
    check(
        "sweep mismatch named, never fudged",
        !bad_note.reconciled
            && bad_note.mismatch.missing == ["job-lease-dead".to_string()]
            && bad_note.mismatch.extra == ["job-stranger".to_string()],
        format!("mismatch={:?}", bad_note.mismatch),
    );
    let ledger = vec!["job-arrive-1".to_string()];
    let jobs_before = jobs.clone();
    watchman_boot::post_boot_rings(&jobs, t0, t1, Some(&ledger));
    watchman_boot::verify_boot_cycle(&jobs, t0, t1, &[json!("job-lease-dead")], None);
    check(
        "inputs never mutated",
        jobs == jobs_before && ledger == ["job-arrive-1".to_string()],
        String::new(),
    );
    // The verification note carries rings, counts, and the sweep
    // reconciliation: no push path, no announcement path -
    // enforced by construction (the struct has no such fields)
    // and by the source-scan test.
    check("no Dale contact in note", !format!("{note:?}").contains("push"), String::new());
    let lines = watchman_boot::boot_brief_lines(&note);
    check(
        "brief lines name rings and reconciliation",
        lines.iter().any(|l| l.contains("job-arrive-1")) && lines.iter().any(|l| l.contains("reconciled")),
        String::new(),
    );
    (passed, failed, log)
}