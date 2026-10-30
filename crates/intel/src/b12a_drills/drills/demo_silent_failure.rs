//! Port of `os/intel/drills/demo_silent_failure.py` — demo
//! silent-failure staging (Milo lane, DEM-011).
//!
//! DEMO.md Shot 7: the staged worker posts one progress
//! note — then nothing. This script stages exactly that
//! moment on fixtures and builds the cue card the operator
//! reads from. It reuses the WDG-020 kill_worker harness
//! (the `fixtures` module here) so the demo scenario and the
//! drill scenario cannot drift apart. It does NOT measure
//! the catch under the demo thresholds profile (DEM-012);
//! its timings are fake-clock seconds, and the cue card says
//! so in plain text.
//!
//! Like the source, `run_drill` fails by assertion: Err
//! carries the assertion message.

use crate::b12a_drills::deps::{Thresholds, Watchdog};
use crate::b12a_drills::fixtures::FakeWorker;
use crate::b12a_drills::value::Value;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub const JOB_ID: &str = "7";
pub const NICK: &str = "milo";
pub const T0: i64 = 100000;
pub const PROGRESS_AT_OFFSET: i64 = 60;
pub const CUE_OFFSET: i64 = 120;

/// A finished run: the alert, the cue card, the phase log.
pub struct SilentFailureOutcome {
    pub alert: Value,
    pub cue: Value,
    pub log: Vec<String>,
    pub phases: Vec<PhaseResult>,
}

fn assert(cond: bool, msg: String) -> Result<(), String> {
    if cond {
        Ok(())
    } else {
        Err(msg)
    }
}

/// Run every phase; Err is the first failed assertion.
pub fn run_drill(
    watchdog: &dyn Watchdog,
    thresholds: &Thresholds,
) -> Result<SilentFailureOutcome, String> {
    let mut log: Vec<String> = Vec::new();
    let mut phases: Vec<PhaseResult> = Vec::new();
    let mut snapshot = Value::obj(vec![
        ("messages", Value::List(vec![])),
        ("jobs", Value::List(vec![])),
        ("presence", Value::List(vec![])),
        (
            "caps",
            Value::obj(vec![(
                NICK,
                Value::obj(vec![("caps", Value::s("build"))]),
            )]),
        ),
    ]);
    let mut worker = FakeWorker::new(NICK);

    // Phase 1 — the setup the audience sees: claim + one note.
    worker.claim(&mut snapshot, JOB_ID, T0, thresholds);
    worker.progress(&mut snapshot, T0 + PROGRESS_AT_OFFSET, "working on it");
    worker.heartbeat(&mut snapshot, T0 + PROGRESS_AT_OFFSET);
    let progress_messages: Vec<Value> = snapshot
        .get("messages")
        .as_list()
        .map(|items| {
            items
                .iter()
                .filter(|m| m.get("nick").as_str() == Some(NICK))
                .cloned()
                .collect()
        })
        .unwrap_or_default();
    assert(
        progress_messages.len() == 1,
        format!(
            "staged worker must post exactly one progress note, got {}",
            progress_messages.len()
        ),
    )?;
    let got = watchdog.tick(&snapshot, Some(T0 + PROGRESS_AT_OFFSET));
    assert(
        got.is_empty(),
        format!(
            "healthy staged worker must yield zero alerts, {}",
            Value::List(got).py_repr()
        ),
    )?;
    log.push(
        "phase 1: worker claims job, posts exactly one progress note, zero alerts while healthy"
            .to_string(),
    );
    phases.push(PhaseResult::pass("phase 1", ""));

    // Phase 2 — THE CUE: the worker goes silent.
    let cue_at = T0 + CUE_OFFSET;
    worker.kill(&mut snapshot);
    assert(
        !snapshot
            .get("presence")
            .as_list()
            .map(|p| p.iter().any(|n| n.as_str() == Some(NICK)))
            .unwrap_or(false),
        "killed worker still present".to_string(),
    )?;
    let mut cue = Value::obj(vec![
        ("shot", Value::Int(7)),
        ("nick", Value::s(NICK)),
        ("job", Value::s(JOB_ID)),
        ("claim_at", Value::Int(T0)),
        ("progress_at", Value::Int(T0 + PROGRESS_AT_OFFSET)),
        ("cue_at", Value::Int(cue_at)),
        ("claim_to_cue_seconds", Value::Int(CUE_OFFSET)),
        ("progress_notes", Value::Int(progress_messages.len() as i64)),
        (
            "cue_line",
            Value::s(
                "On cue, the staged worker posts one progress note, then nothing. No error. No message.",
            ),
        ),
    ]);
    log.push(format!(
        "phase 2: CUE at T0+{}s — worker silent, presence dropped, one progress note on record",
        CUE_OFFSET
    ));
    phases.push(PhaseResult::pass("phase 2", ""));

    // Phase 3 — silence is not yet a stall.
    let quiet_at = cue_at + thresholds.stall_minutes * 60 - 60;
    let before_messages = snapshot.get("messages");
    let job_now = snapshot
        .get("jobs")
        .as_list()
        .and_then(|items| items.first().cloned())
        .unwrap_or(Value::Null);
    let before_progress = job_now.get("last_progress");
    let got = watchdog.tick(&snapshot, Some(quiet_at));
    assert(
        got.is_empty(),
        format!(
            "tick inside the stall window must yield zero alerts, got {}",
            Value::List(got).py_repr()
        ),
    )?;
    assert(
        snapshot.get("messages") == before_messages,
        "messages changed after the cue".to_string(),
    )?;
    let job_now = snapshot
        .get("jobs")
        .as_list()
        .and_then(|items| items.first().cloned())
        .unwrap_or(Value::Null);
    assert(
        job_now.get("last_progress") == before_progress,
        "last_progress changed after the cue".to_string(),
    )?;
    log.push(
        "phase 3: tick inside the stall window yields zero alerts; no worker activity appears after the cue"
            .to_string(),
    );
    phases.push(PhaseResult::pass("phase 3", ""));

    // Phase 4 — past the threshold, the watchdog says it.
    let stall_at = T0 + PROGRESS_AT_OFFSET + thresholds.stall_minutes * 60 + 1;
    let got = watchdog.tick(&snapshot, Some(stall_at));
    assert(
        got.len() == 1,
        format!(
            "past-threshold tick must yield exactly one alert, got {}",
            got.len()
        ),
    )?;
    let alert = got[0].clone();
    for (field, want) in [("kind", "presence-stall"), ("nick", NICK), ("job", JOB_ID)] {
        assert(
            alert.get(field).as_str() == Some(want),
            format!("alert {}", alert.py_repr()),
        )?;
    }
    let expected_age = stall_at - (T0 + PROGRESS_AT_OFFSET);
    assert(
        alert.get("last_progress_age_seconds").as_int() == Some(expected_age),
        format!("alert {}", alert.py_repr()),
    )?;
    let lines = watchdog.announcements_for(&got);
    assert(
        lines.len() == 1 && lines[0].starts_with("ALERT:"),
        format!("lines {:?}", lines),
    )?;
    cue.set("stall_at", Value::Int(stall_at));
    cue.set("last_progress_age_seconds", Value::Int(expected_age));
    cue.set("alert_kind", alert.get("kind"));
    log.push(format!(
        "phase 4: presence-stall alert names {}/{}, last progress {}s ago; announcement line held, not posted",
        NICK, JOB_ID, expected_age
    ));
    phases.push(PhaseResult::pass("phase 4", ""));

    Ok(SilentFailureOutcome {
        alert,
        cue,
        log,
        phases,
    })
}

/// The source main()'s printed lines, success or failure.
pub fn main_lines(result: &Result<SilentFailureOutcome, String>) -> Vec<String> {
    match result {
        Ok(outcome) => {
            let cue = &outcome.cue;
            let mut lines: Vec<String> = outcome
                .log
                .iter()
                .map(|line| format!("demo_silent_failure drill: {}", line))
                .collect();
            lines.push(format!(
                "demo_silent_failure drill: CUE CARD — shot {}: {} (claim to cue: {}s fake-clock; progress notes: {}; stall alert {} at last-progress age {}s under production thresholds — demo-profile timing is DEM-012/DEM-013, not measured here)",
                cue.get("shot").py_str(),
                cue.get("cue_line").py_str(),
                cue.get("claim_to_cue_seconds").py_str(),
                cue.get("progress_notes").py_str(),
                cue.get("alert_kind").py_str(),
                cue.get("last_progress_age_seconds").py_str()
            ));
            lines.push("demo_silent_failure drill: PASS".to_string());
            lines
        }
        Err(exc) => vec![format!("demo_silent_failure drill: FAIL: {}", exc)],
    }
}

/// The phase report for a finished run.
pub fn report(result: &Result<SilentFailureOutcome, String>) -> DrillReport {
    match result {
        Ok(outcome) => DrillReport::new("demo_silent_failure", outcome.phases.clone()),
        Err(exc) => DrillReport::new(
            "demo_silent_failure",
            vec![PhaseResult::fail("run_drill", exc.clone())],
        ),
    }
}
