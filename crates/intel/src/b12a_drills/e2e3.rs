//! Port of `os/intel/e2e3.py` — INT-004 end-to-end test 3.
//!
//! A fresh nick joins a room where a drill is already running,
//! and the on-join brief it is offered names the drill's
//! blocked item and the drill's active alert, as one scripted
//! run. The offer path is the BRF-029 path: presence beat,
//! detect_new_nicks, offer record with no brief attached, and
//! only then generate_brief(kind="onjoin"). Two gaps the loop
//! names instead of hiding (from the source docstring): the
//! brief's Blocked section names id and title but not the
//! reason verbatim (real snapshot rows carry no note field),
//! and the stored alert record is attached to the brief
//! snapshot by the caller, as the dashboard and CLI do.

use super::deps::{Thresholds, Watchdog};
use super::e2e1::{
    brief_budget, job_list_json, stage, Integration, LoopResult, Stage, INT_CAPNS, INT_JOBNS,
    INT_ROOM,
};
use super::value::Value;

pub const BLOCKED_TITLE: &str = "Ship the e2e3 release note";
pub const BLOCKED_SPEC: &str = "Goal: ship the INT-004 release note. Context: INT-004 fixture. Files: intel/e2e3_release.txt. Steps: write the note. Out of scope: any other file.";
pub const BLOCKED_FILES: &str = "intel/e2e3_release.txt";
pub const BLOCKED_REASON: &str = "waiting on the outside review, no reply yet";
pub const STALL_TITLE: &str = "Fix the e2e3 stall note";
pub const STALL_SPEC: &str = "Goal: close the INT-004 loop. Context: INT-004 fixture. Files: intel/e2e3_note.txt. Steps: write the note. Out of scope: any other file.";
pub const STALL_FILES: &str = "intel/e2e3_note.txt";
pub const MAX_ATTEMPTS: i64 = 3;
pub const WORKER_A: &str = "worker-a";
pub const WORKER_B: &str = "worker-b";
pub const STALL_PROGRESS: &str = "halfway through the stall note";
pub const FRESH_NICK: &str = "newbie";

const STAGE_NAMES: [&str; 6] = [
    "drill setup",
    "blocked item",
    "stall and alert",
    "fresh nick joins",
    "on-join brief",
    "no auto-post",
];

const SECTION_HEADINGS: [&str; 5] = [
    "Decisions",
    "In flight",
    "Owners",
    "Blocked and why",
    "Watch items",
];

/// `_section_lines(text, heading)` — the non-empty lines of one
/// brief section, between its heading and the next heading.
pub fn section_lines(text: &str, heading: &str) -> Vec<String> {
    let lines: Vec<&str> = text.lines().collect();
    let start = match lines.iter().position(|l| *l == heading) {
        Some(i) => i + 1,
        None => return Vec::new(),
    };
    let mut end = lines.len();
    for (index, line) in lines.iter().enumerate().skip(start) {
        if SECTION_HEADINGS.contains(line) {
            end = index;
            break;
        }
    }
    lines[start..end]
        .iter()
        .filter(|l| !l.trim().is_empty())
        .map(|l| l.to_string())
        .collect()
}

/// `run_loop(write_log)` — the INT-004 loop.
pub fn run_loop(
    deps: &dyn Integration,
    watchdog: &dyn Watchdog,
    thresholds: &Thresholds,
) -> LoopResult {
    deps.apply_env();
    let mut stages: Vec<Stage> = Vec::new();
    let mut blocked_id = String::new();
    let mut stall_id = String::new();
    let mut last_progress_at: i64 = 0;
    let mut alert_holder: Option<(Value, Value)> = None;
    let mut messages_before_brief: usize = 0;
    let mut brief_text = String::new();
    let t = thresholds;

    let post = |deps: &dyn Integration, title: &str, spec: &str, files: &str| -> Result<String, String> {
        let argv: Vec<String> = [
            "post",
            "--title",
            title,
            "--spec",
            spec,
            "--files",
            files,
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
        out.split_whitespace()
            .nth(1)
            .map(|s| s.to_string())
            .ok_or_else(|| "post output carries no job id".to_string())
    };

    stage(&mut stages, STAGE_NAMES[0], || {
        deps.set_nick("pax");
        let before = job_list_json(deps)?;
        if !before.is_empty() {
            return Err(format!(
                "job list not empty before: {}",
                Value::List(before).py_repr()
            ));
        }
        blocked_id = post(deps, BLOCKED_TITLE, BLOCKED_SPEC, BLOCKED_FILES)?;
        stall_id = post(deps, STALL_TITLE, STALL_SPEC, STALL_FILES)?;
        let listed = job_list_json(deps)?;
        if listed.len() != 2 {
            return Err(format!(
                "job list after posts: {}",
                Value::List(listed).py_repr()
            ));
        }
        for id in [&blocked_id, &stall_id] {
            let row = listed
                .iter()
                .find(|j| &j.get("id").py_str() == id)
                .ok_or("posted job missing from list")?;
            if row.get("status").as_str() != Some("open") {
                return Err(format!("row {}", row.py_repr()));
            }
        }
        Ok(format!(
            "jobs {} (release note) and {} (stall note) posted, both open",
            blocked_id, stall_id
        ))
    });

    stage(&mut stages, STAGE_NAMES[1], || {
        if !deps.register_caps(WORKER_B, &["python"]) {
            return Err("worker-b registration must read True".to_string());
        }
        deps.set_nick(WORKER_B);
        let (code, _out, err) = deps.jobs_cli(&["claim".into(), blocked_id.clone()]);
        if code != 0 {
            return Err(format!("worker-b claim failed: {}", err));
        }
        let (code, out, err) = deps.jobs_cli(&[
            "blocked".into(),
            blocked_id.clone(),
            "--reason".into(),
            BLOCKED_REASON.into(),
        ]);
        if code != 0 {
            return Err(format!("worker-b blocked failed: {}", err));
        }
        if !out.starts_with("BLOCKED ") {
            return Err(format!("unexpected blocked out: {}", out));
        }
        let listed = job_list_json(deps)?;
        let row = listed
            .iter()
            .find(|j| j.get("id").py_str() == blocked_id)
            .ok_or("blocked job missing from list")?
            .clone();
        if row.get("status").as_str() != Some("blocked") {
            return Err(format!("job after blocked: {}", row.py_repr()));
        }
        if row.get("claim") != Value::Null {
            return Err(format!("claim not released: {}", row.py_repr()));
        }
        let snapshot = deps.snapshot(INT_ROOM);
        let srow = snapshot
            .get("jobs")
            .as_list()
            .and_then(|items| items.iter().find(|j| j.get("id").py_str() == blocked_id).cloned())
            .ok_or("blocked job missing from snapshot")?;
        if srow.get("status").as_str() != Some("blocked") {
            return Err("snapshot must carry the job blocked".to_string());
        }
        let needle = format!("BLOCKED:{} {}", blocked_id, BLOCKED_REASON);
        let announced = snapshot
            .get("messages")
            .as_list()
            .map(|msgs| msgs.iter().any(|m| m.py_str().contains(&needle)))
            .unwrap_or(false);
        if !announced {
            return Err("BLOCKED announcement missing from room messages".to_string());
        }
        Ok(format!(
            "job {} blocked by {}, claim released, BLOCKED announcement on the room list",
            blocked_id, WORKER_B
        ))
    });

    stage(&mut stages, STAGE_NAMES[2], || {
        if !deps.register_caps(WORKER_A, &["python"]) {
            return Err("worker-a registration must read True".to_string());
        }
        deps.set_nick(WORKER_A);
        deps.presence_beat();
        let (code, _out, err) = deps.jobs_cli(&["claim".into(), stall_id.clone()]);
        if code != 0 {
            return Err(format!("worker-a claim failed: {}", err));
        }
        let (code, _out, err) = deps.jobs_cli(&[
            "progress".into(),
            stall_id.clone(),
            "--note".into(),
            STALL_PROGRESS.into(),
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
            .and_then(|items| items.iter().find(|j| j.get("id").py_str() == stall_id).cloned())
            .ok_or("stall job missing from snapshot")?;
        if row.get("status").as_str() != Some("claimed") {
            return Err("stall job must read claimed".to_string());
        }
        if row.get("claim").as_str() != Some(WORKER_A) {
            return Err("stall job claim must read worker-a".to_string());
        }
        last_progress_at = row.get("last_progress_at").as_int().unwrap_or(0);
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
        let still = snapshot
            .get("presence")
            .as_list()
            .map(|p| p.iter().any(|n| n.as_str() == Some(WORKER_A)))
            .unwrap_or(false);
        if still {
            return Err("dead worker must be gone from presence".to_string());
        }
        let row = snapshot
            .get("jobs")
            .as_list()
            .and_then(|items| items.iter().find(|j| j.get("id").py_str() == stall_id).cloned())
            .ok_or("stall job missing from snapshot")?;
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
        if alert.get("kind").as_str() != Some("presence-stall") {
            return Err(format!("alert {}", alert.py_repr()));
        }
        if alert.get("nick").as_str() != Some(WORKER_A) {
            return Err(format!("alert {}", alert.py_repr()));
        }
        if alert.get("job").py_str() != stall_id {
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
            stall_id,
            record.get("id").py_str(),
            expected_age
        );
        alert_holder = Some((alert, record));
        Ok(detail)
    });

    stage(&mut stages, STAGE_NAMES[3], || {
        deps.set_nick(FRESH_NICK);
        deps.presence_beat();
        let snapshot = deps.snapshot(INT_ROOM);
        let presence: Vec<String> = snapshot
            .get("presence")
            .as_list()
            .map(|items| items.iter().map(|n| n.py_str()).collect())
            .unwrap_or_default();
        if presence != vec![FRESH_NICK.to_string()] {
            return Err(format!(
                "presence must hold only the fresh nick, got {:?}",
                presence
            ));
        }
        let new_nicks = deps.detect_new_nicks(&snapshot);
        if new_nicks != vec![FRESH_NICK.to_string()] {
            return Err(format!(
                "fresh nick must be the only new nick, got {:?}",
                new_nicks
            ));
        }
        let offers = deps.offer_onjoin_brief(&snapshot, INT_ROOM, Some(deps.now()));
        if offers.len() != 1 {
            return Err(format!(
                "offers must be exactly one: {}",
                Value::List(offers).py_repr()
            ));
        }
        let offer = offers[0].clone();
        if offer.get("nick").as_str() != Some(FRESH_NICK) {
            return Err(format!("offer {}", offer.py_repr()));
        }
        if offer.get("kind").as_str() != Some("onjoin") {
            return Err(format!("offer {}", offer.py_repr()));
        }
        if offer.get("status").as_str() != Some("offered") {
            return Err(format!("offer {}", offer.py_repr()));
        }
        if offer.get("brief_generated") != Value::Bool(false) {
            return Err(format!("offer {}", offer.py_repr()));
        }
        if offer.get("brief_id") != Value::Null {
            return Err(format!("offer {}", offer.py_repr()));
        }
        if !deps.list_briefs(INT_ROOM).is_empty() {
            return Err("no brief may exist before the offer is invoked".to_string());
        }
        messages_before_brief = snapshot
            .get("messages")
            .as_list()
            .map(|m| m.len())
            .unwrap_or(0);
        Ok(format!(
            "{} joined, offered an onjoin brief, none generated yet",
            FRESH_NICK
        ))
    });

    stage(&mut stages, STAGE_NAMES[4], || {
        let (_alert, record) = alert_holder
            .clone()
            .ok_or("alert stage did not hold a record")?;
        let mut snapshot = deps.snapshot(INT_ROOM);
        snapshot.set("alerts", Value::List(vec![record.clone()]));
        let (text, stored) =
            deps.generate_brief(&snapshot, INT_ROOM, "onjoin", None, Some(deps.now()));
        if !text.starts_with("TEMPLATE") {
            return Err("onjoin brief here must be a template brief".to_string());
        }
        let words = text.split_whitespace().count() as i64;
        let budget = brief_budget("onjoin").unwrap_or(150);
        if words > budget {
            return Err(format!("onjoin brief over budget: {} words", words));
        }
        let blocked_lines = section_lines(&text, "Blocked and why");
        let names_blocked = blocked_lines
            .iter()
            .any(|line| line.contains(&blocked_id) && line.contains(BLOCKED_TITLE));
        if !names_blocked {
            return Err(format!(
                "Blocked section must name job {} {:?}, got: {:?}",
                blocked_id, BLOCKED_TITLE, blocked_lines
            ));
        }
        let watch_lines = section_lines(&text, "Watch items");
        let explanation_first = record
            .get("explanation")
            .py_str()
            .lines()
            .next()
            .unwrap_or("")
            .trim()
            .to_string();
        let record_id = record.get("id").py_str();
        let names_alert = watch_lines
            .iter()
            .any(|line| line.contains(&record_id) && line.contains(&explanation_first));
        if !names_alert {
            return Err(format!(
                "Watch items must name alert {} with its explanation, got: {:?}",
                record_id, watch_lines
            ));
        }
        if stored.get("kind").as_str() != Some("onjoin") {
            return Err(format!("stored {}", stored.py_repr()));
        }
        let entries = deps.list_briefs(INT_ROOM);
        if entries.len() != 1 {
            return Err(format!(
                "brief index must hold one: {}",
                Value::List(entries).py_repr()
            ));
        }
        if entries[0].get("kind").as_str() != Some("onjoin") {
            return Err(format!("entries {}", Value::List(entries).py_repr()));
        }
        let fetched = deps
            .get_brief(INT_ROOM, entries[0].get("ts").as_int().unwrap_or(0))
            .ok_or("stored brief must read back")?;
        if fetched.get("kind").as_str() != Some("onjoin") {
            return Err(format!("fetched {}", fetched.py_repr()));
        }
        if fetched.get("text").py_str() != text {
            return Err("stored brief text must match the generated text".to_string());
        }
        brief_text = text.clone();
        Ok(format!(
            "onjoin brief ({} words) names blocked job {} and alert {}, stored and retrievable",
            words, blocked_id, record_id
        ))
    });

    stage(&mut stages, STAGE_NAMES[5], || {
        let snapshot = deps.snapshot(INT_ROOM);
        let count = snapshot
            .get("messages")
            .as_list()
            .map(|m| m.len())
            .unwrap_or(0);
        if count != messages_before_brief {
            return Err("brief step must not add room messages".to_string());
        }
        let any_alert = snapshot
            .get("messages")
            .as_list()
            .map(|msgs| msgs.iter().any(|m| m.py_str().contains("ALERT:")))
            .unwrap_or(false);
        if any_alert {
            return Err("room messages must hold no ALERT line".to_string());
        }
        Ok("room message list unchanged across the brief step, no ALERT line posted".to_string())
    });

    let ok = stages.len() == STAGE_NAMES.len() && stages.iter().all(|s| s.ok);
    let mut extras = Value::obj(vec![]);
    if ok {
        extras.set("blocked_job_id", Value::s(&blocked_id));
        extras.set("stall_job_id", Value::s(&stall_id));
        if let Some((alert, record)) = &alert_holder {
            extras.set("alert", alert.clone());
            extras.set("alert_record_id", record.get("id"));
        }
        extras.set("brief_text", Value::s(&brief_text));
    }
    let mut lines: Vec<String> = vec![
        "INT-004 end-to-end test 3".to_string(),
        format!("blocked job: {} (files: {})", BLOCKED_TITLE, BLOCKED_FILES),
        format!("stall job: {} (files: {})", STALL_TITLE, STALL_FILES),
        format!(
            "queue: in-memory fake surface, namespace {}, caps {}, room {}",
            INT_JOBNS, INT_CAPNS, INT_ROOM
        ),
        format!(
            "clock: fake clock advanced, never wall-waited; presence TTL 120s, stall window {} minutes",
            t.stall_minutes
        ),
        format!(
            "brief: template path (no live Spark call; GOV-001 leaves live transport blocked); fresh nick {}",
            FRESH_NICK
        ),
        String::new(),
    ];
    for s in &stages {
        lines.push(format!(
            "[{}] {}: {}",
            if s.ok { "PASS" } else { "FAIL" },
            s.name,
            s.detail
        ));
    }
    lines.push(String::new());
    lines.push("On-join brief text:".to_string());
    if !brief_text.is_empty() {
        lines.push(brief_text.trim_end().to_string());
    }
    lines.push(String::new());
    lines.push(format!(
        "INT-004: {}",
        if ok { "PASS (all stages)" } else { "FAIL" }
    ));
    LoopResult {
        ok,
        stages,
        transcript: lines.join("\n") + "\n",
        extras,
    }
}
