//! Port of `os/intel/e2e2.py` — INT-003 end-to-end test 2.
//!
//! Worker death -> presence-stall alert -> sweep requeue ->
//! next worker completes -> the morning brief names the
//! auto-resolved alert, as one scripted run. The surface is
//! the same [`Integration`] seam as e2e1 (fake transport in the
//! INT-001 namespace), the watchdog is the B21 trait, and time
//! travel rides the harness clock: the fake advances, so bus
//! keys expire by real TTL rules. Assertions, stage names, and
//! the transcript are the source's own.

use super::deps::{Thresholds, Watchdog};
use super::e2e1::{job_list_json, stage, transcript, Integration, LoopResult, Stage, INT_ROOM};
use super::value::Value;

pub const TITLE: &str = "Fix the e2e2 stall note";
pub const SPEC: &str = "Goal: close the INT-003 loop. Context: INT-003 fixture. Files: intel/e2e2_note.txt. Steps: write the note. Out of scope: any other file.";
pub const FILES: &str = "intel/e2e2_note.txt";
pub const MAX_ATTEMPTS: i64 = 3;
pub const WORKER_A: &str = "worker-a";
pub const WORKER_B: &str = "worker-b";
pub const PROGRESS_NOTE: &str = "halfway through the note";
pub const DONE_NOTE: &str = "note written, stall closed";

const STAGE_NAMES: [&str; 7] = [
    "post",
    "worker-a",
    "death and alert",
    "sweep requeue",
    "alert auto-resolves",
    "worker-b",
    "final quiet",
];

/// `run_loop(write_log)` — the INT-003 loop (transcript rides
/// in the result, as in e2e1).
pub fn run_loop(
    deps: &dyn Integration,
    watchdog: &dyn Watchdog,
    thresholds: &Thresholds,
) -> LoopResult {
    deps.apply_env();
    let mut stages: Vec<Stage> = Vec::new();
    let mut job_id = String::new();
    let mut last_progress_at: i64 = 0;
    let mut alert_holder: Option<(Value, Value)> = None; // (alert, record)
    let mut resolved_id = String::new();
    let mut brief_text = String::new();
    let t = thresholds;

    stage(&mut stages, STAGE_NAMES[0], || {
        deps.set_nick("pax");
        let before = job_list_json(deps)?;
        if !before.is_empty() {
            return Err(format!(
                "job list not empty before: {}",
                Value::List(before).py_repr()
            ));
        }
        let argv: Vec<String> = [
            "post",
            "--title",
            TITLE,
            "--spec",
            SPEC,
            "--files",
            FILES,
            "--max-attempts",
            "3",
            "--room",
            INT_ROOM,
        ]
        .iter()
        .map(|s| s.to_string())
        .collect();
        let (code, out, err) = deps.jobs_cli(&argv);
        if code != 0 {
            return Err(format!("post failed: {}", err));
        }
        if !out.starts_with("JOB ") {
            return Err(format!("unexpected post out: {}", out));
        }
        let id = out
            .split_whitespace()
            .nth(1)
            .ok_or("post output carries no job id")?
            .to_string();
        let listed = job_list_json(deps)?;
        if listed.len() != 1 || listed[0].get("id").py_str() != id {
            return Err(format!(
                "job list after post: {}",
                Value::List(listed).py_repr()
            ));
        }
        if listed[0].get("status").as_str() != Some("open") {
            return Err("posted job must read open".to_string());
        }
        job_id = id.clone();
        Ok(format!("job {} posted and listed open", id))
    });

    stage(&mut stages, STAGE_NAMES[1], || {
        if !deps.register_caps(WORKER_A, &["python"]) {
            return Err("worker-a registration must read True".to_string());
        }
        deps.set_nick(WORKER_A);
        deps.presence_beat();
        let (code, _out, err) = deps.jobs_cli(&["claim".into(), job_id.clone()]);
        if code != 0 {
            return Err(format!("worker-a claim failed: {}", err));
        }
        let (code, _out, err) = deps.jobs_cli(&[
            "progress".into(),
            job_id.clone(),
            "--note".into(),
            PROGRESS_NOTE.into(),
        ]);
        if code != 0 {
            return Err(format!("worker-a progress failed: {}", err));
        }
        let snapshot = deps.snapshot(INT_ROOM);
        let present = snapshot
            .get("presence")
            .as_list()
            .map(|p| p.iter().any(|n| n.as_str() == Some(WORKER_A)))
            .unwrap_or(false);
        if !present {
            return Err("worker-a must be present while alive".to_string());
        }
        let row = snapshot
            .get("jobs")
            .as_list()
            .and_then(|items| items.iter().find(|j| j.get("id").py_str() == job_id).cloned())
            .ok_or("job missing from snapshot")?;
        if row.get("status").as_str() != Some("claimed") {
            return Err("job must read claimed".to_string());
        }
        if row.get("claim").as_str() != Some(WORKER_A) {
            return Err("job claim must read worker-a".to_string());
        }
        last_progress_at = row.get("last_progress_at").as_int().unwrap_or(0);
        Ok(format!(
            "{} claimed {} and reported progress at {}",
            WORKER_A, job_id, last_progress_at
        ))
    });

    stage(&mut stages, STAGE_NAMES[2], || {
        let snapshot = deps.snapshot(INT_ROOM);
        let got = watchdog.tick(&snapshot, Some(deps.now()));
        if !got.is_empty() {
            return Err(format!(
                "healthy worker must yield zero alerts, got {}",
                Value::List(got).py_repr()
            ));
        }
        deps.advance(t.stall_minutes * 60 + 61);
        let stall_now = deps.now();
        let snapshot = deps.snapshot(INT_ROOM);
        let still_present = snapshot
            .get("presence")
            .as_list()
            .map(|p| p.iter().any(|n| n.as_str() == Some(WORKER_A)))
            .unwrap_or(false);
        if still_present {
            return Err("dead worker must be gone from presence".to_string());
        }
        let row = snapshot
            .get("jobs")
            .as_list()
            .and_then(|items| items.iter().find(|j| j.get("id").py_str() == job_id).cloned())
            .ok_or("job missing from snapshot")?;
        if row.get("status").as_str() != Some("claimed") {
            return Err("job must still be claimed before any sweep".to_string());
        }
        let got = watchdog.tick(&snapshot, Some(stall_now));
        if got.len() != 1 {
            return Err(format!(
                "dead worker must yield exactly one alert, got {}: {}",
                got.len(),
                Value::List(got.clone()).py_repr()
            ));
        }
        let alert = got[0].clone();
        for (field, want) in [
            ("kind", "presence-stall"),
            ("nick", WORKER_A),
        ] {
            if alert.get(field).as_str() != Some(want) {
                return Err(format!("alert {}", alert.py_repr()));
            }
        }
        if alert.get("job").py_str() != job_id {
            return Err(format!("alert {}", alert.py_repr()));
        }
        let expected_age = stall_now - last_progress_at;
        if alert.get("last_progress_age_seconds").as_int() != Some(expected_age) {
            return Err(format!("alert {}", alert.py_repr()));
        }
        let record = deps.write_alert(&alert, INT_ROOM);
        if record.get("id") != alert.get("dedupe_key") {
            return Err(format!("record {}", record.py_repr()));
        }
        let reread = deps
            .read_alert(&record.get("id").py_str())
            .ok_or("stored alert must read back by id")?;
        if reread.get("id") != record.get("id") {
            return Err("stored alert id mismatch on read-back".to_string());
        }
        if reread.get("status").as_str() != Some("open") {
            return Err(format!("reread {}", reread.py_repr()));
        }
        let lines = watchdog.announcements_for(std::slice::from_ref(&alert));
        if lines.len() != 1 || !lines[0].starts_with("ALERT:") {
            return Err(format!("lines {}", lines.join("\n")));
        }
        let held = snapshot
            .get("messages")
            .as_list()
            .map(|msgs| msgs.iter().all(|m| !m.py_str().contains(&lines[0])))
            .unwrap_or(true);
        if !held {
            return Err("announcement line must be held, never posted".to_string());
        }
        let detail = format!(
            "presence-stall alert for {}/{} stored as {}, age {}s; announcement line held",
            WORKER_A,
            job_id,
            record.get("id").py_str(),
            expected_age
        );
        alert_holder = Some((alert, record));
        Ok(detail)
    });

    stage(&mut stages, STAGE_NAMES[3], || {
        let (_alert, record) = alert_holder
            .clone()
            .ok_or("alert stage did not hold a record")?;
        // The source's clock math: advance(LEASE_DEFAULT -
        // (fake.now() - last_claim_at) + 1); last_claim_at is
        // the progress timestamp the snapshot carried.
        let elapsed = deps.now() - last_progress_at;
        deps.advance(t.lease_default_seconds - elapsed + 1);
        let sweep_now = deps.now();
        let snapshot = deps.snapshot(INT_ROOM);
        let got = watchdog.tick(&snapshot, Some(sweep_now));
        if got.len() != 1 {
            return Err(format!(
                "sweep tick must yield exactly one alert, got {}: {}",
                got.len(),
                Value::List(got.clone()).py_repr()
            ));
        }
        let sweep_alert = got[0].clone();
        if sweep_alert.get("kind").as_str() != Some("presence-stall") {
            return Err(format!("sweep alert {}", sweep_alert.py_repr()));
        }
        if sweep_alert.get("dedupe_key") != record.get("id") {
            return Err(format!("sweep alert {}", sweep_alert.py_repr()));
        }
        let lines = watchdog.announcements_for(std::slice::from_ref(&sweep_alert));
        if lines.len() != 1 || !lines[0].starts_with("ALERT:") {
            return Err(format!("lines {}", lines.join("\n")));
        }
        if !lines[0].contains("job requeued") {
            return Err("sweep announcement must say the job was requeued".to_string());
        }
        let listed = job_list_json(deps)?;
        let row = listed
            .iter()
            .find(|j| j.get("id").py_str() == job_id)
            .ok_or("job missing after sweep")?
            .clone();
        if row.get("status").as_str() != Some("open") {
            return Err(format!("job after sweep: {}", row.py_repr()));
        }
        if row.get("claim") != Value::Null {
            return Err(format!("claim not released: {}", row.py_repr()));
        }
        if row.get("attempts").as_int() != Some(1) {
            return Err(format!("job after sweep: {}", row.py_repr()));
        }
        let record2 = deps.write_alert(&sweep_alert, INT_ROOM);
        if record2.get("id") != record.get("id") {
            return Err("sweep write must land on the same alert record".to_string());
        }
        if record2.get("status").as_str() != Some("open") {
            return Err(format!("record after sweep: {}", record2.py_repr()));
        }
        let detail = format!(
            "lease lapsed at {}s; sweep requeued job {} (attempts 1), alert {} still open",
            sweep_now,
            job_id,
            record.get("id").py_str()
        );
        alert_holder = Some((sweep_alert, record2));
        Ok(detail)
    });

    stage(&mut stages, STAGE_NAMES[4], || {
        let (_alert, record) = alert_holder
            .clone()
            .ok_or("sweep stage did not hold a record")?;
        let snapshot = deps.snapshot(INT_ROOM);
        let got = watchdog.tick(&snapshot, Some(deps.now()));
        if !got.is_empty() {
            return Err(format!(
                "requeued job must yield zero alerts, got {}",
                Value::List(got).py_repr()
            ));
        }
        let resolved = watchdog.resolve_alerts_for_job(deps, &job_id, Some(deps.now()));
        if resolved.len() != 1 || resolved[0] != record.get("id") {
            return Err(format!("resolved {:?}", resolved));
        }
        let reread = deps
            .read_alert(&record.get("id").py_str())
            .ok_or("resolved alert must still read back")?;
        if reread.get("status").as_str() != Some("resolved") {
            return Err(format!("reread {}", reread.py_repr()));
        }
        if reread.get("resolution").as_str()
            != Some("auto-resolved: underlying job state cleared")
        {
            return Err(format!("reread {}", reread.py_repr()));
        }
        if reread.get("resolved_at").is_null() {
            return Err(format!("reread {}", reread.py_repr()));
        }
        resolved_id = record.get("id").py_str();
        Ok(format!(
            "alert {} auto-resolved once the job state cleared",
            resolved_id
        ))
    });

    stage(&mut stages, STAGE_NAMES[5], || {
        if !deps.register_caps(WORKER_B, &["python"]) {
            return Err("worker-b registration must read True".to_string());
        }
        deps.set_nick(WORKER_B);
        deps.presence_beat();
        let (code, _out, err) = deps.jobs_cli(&["claim".into(), job_id.clone()]);
        if code != 0 {
            return Err(format!("worker-b claim failed: {}", err));
        }
        let (code, _out, err) = deps.jobs_cli(&[
            "done".into(),
            job_id.clone(),
            "--commit".into(),
            "e2e2-no-real-commit".into(),
            "--note".into(),
            DONE_NOTE.into(),
        ]);
        if code != 0 {
            return Err(format!("worker-b done failed: {}", err));
        }
        let listed = job_list_json(deps)?;
        let row = listed
            .iter()
            .find(|j| j.get("id").py_str() == job_id)
            .ok_or("job missing after worker-b")?
            .clone();
        if row.get("status").as_str() != Some("done") {
            return Err(format!("job after worker-b: {}", row.py_repr()));
        }
        if row.get("claim").as_str() != Some(WORKER_B) {
            return Err(format!("job after worker-b: {}", row.py_repr()));
        }
        Ok(format!("{} claimed {} and marked it done", WORKER_B, job_id))
    });

    stage(&mut stages, STAGE_NAMES[6], || {
        let snapshot = deps.snapshot(INT_ROOM);
        let got = watchdog.tick(&snapshot, Some(deps.now()));
        if !got.is_empty() {
            return Err(format!(
                "finished loop must be quiet, got {}",
                Value::List(got).py_repr()
            ));
        }
        let record = deps
            .read_alert(&resolved_id)
            .ok_or("resolved alert must read back for the brief")?;
        let mut brief_snapshot = deps.snapshot(INT_ROOM);
        brief_snapshot.set("alerts", Value::List(vec![record]));
        let (text, stored) =
            deps.generate_brief(&brief_snapshot, INT_ROOM, "morning", None, None);
        if text.contains("OPEN FIRES") {
            return Err("brief must not read open fires once resolved".to_string());
        }
        for needle in [
            resolved_id.as_str(),
            "resolved",
            "auto-resolved: underlying job state cleared",
        ] {
            if !text.contains(needle) {
                return Err(format!("brief missing {:?}", needle));
            }
        }
        let budget = super::e2e1::brief_budget("morning").unwrap_or(220);
        let words = text.split_whitespace().count() as i64;
        if words > budget {
            return Err(format!("morning brief over budget: {} words", words));
        }
        if stored.get("kind").as_str() != Some("morning") {
            return Err(format!("stored {}", stored.py_repr()));
        }
        let entries = deps.list_briefs(INT_ROOM);
        if entries.len() != 1 {
            return Err(format!(
                "brief index must hold one: {}",
                Value::List(entries).py_repr()
            ));
        }
        brief_text = text.clone();
        Ok(format!(
            "watchdog quiet; morning brief ({} words) names {} as auto-resolved",
            words, resolved_id
        ))
    });

    let ok = stages.len() == STAGE_NAMES.len() && stages.iter().all(|s| s.ok);
    let mut extras = Value::obj(vec![]);
    if ok {
        extras.set("job_id", Value::s(&job_id));
        if let Some((alert, record)) = &alert_holder {
            extras.set("alert", alert.clone());
            extras.set("alert_record_id", record.get("id"));
        }
        extras.set("brief_text", Value::s(&brief_text));
    }
    let header = vec![
        "INT-003 end-to-end test 2".to_string(),
        format!("job: {} (files: {})", TITLE, FILES),
        format!(
            "queue: in-memory fake surface, namespace {}, room {}",
            super::e2e1::INT_JOBNS,
            INT_ROOM
        ),
        format!(
            "clock: fake clock advanced, never wall-waited; stall window {} minutes, lease {}s",
            t.stall_minutes, t.lease_default_seconds
        ),
        "brief: template path (no live Spark call; GOV-001 leaves live transport blocked)"
            .to_string(),
    ];
    let text = transcript(&header, &stages, "INT-003", ok);
    LoopResult {
        ok,
        stages,
        transcript: text,
        extras,
    }
}
