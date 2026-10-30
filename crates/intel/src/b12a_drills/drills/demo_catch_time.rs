//! Port of `os/intel/drills/demo_catch_time.py` — demo
//! catch-time measurement (Milo lane, DEM-012).
//!
//! DEMO.md Shot 8: from the Shot 7 silence cue to the red
//! STALL alert on the dashboard must be under 90 seconds, in
//! demo configuration — the DEM-013 profile
//! (intel/metaos-demo.env) loaded, not production thresholds.
//! Each rehearsal replays the DEM-011 staging exactly (milo
//! claims demo job 7, posts one progress note at T0+60, goes
//! silent at the T0+120 cue), then ticks every 5 s from the
//! cue until the first alert or the budget is spent. The
//! three rehearsals differ only in tick-grid phase (+0/+2/+4
//! s), so the measurement must hold for every phase.
//!
//! The source applies the profile at import time and asserts
//! the loaded stall window equals the profile's before
//! ticking; here `check_profile` runs those asserts up front
//! over the parsed profile, and the rehearsals take the demo
//! thresholds explicitly — the measurement can never silently
//! run on production thresholds.

use crate::b12a_drills::deps::{Thresholds, Watchdog};
use crate::b12a_drills::fixtures::FakeWorker;
use crate::b12a_drills::value::Value;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub const CATCH_BUDGET_SECONDS: i64 = 90;
pub const TICK_INTERVAL_SECONDS: i64 = 5;
pub const TICK_PHASES_SECONDS: [i64; 3] = [0, 2, 4];
pub const JOB_ID: &str = "7";
pub const NICK: &str = "milo";
pub const T0: i64 = 100000;
pub const PROGRESS_AT_OFFSET: i64 = 60;
pub const CUE_OFFSET: i64 = 120;

/// `load_profile(path)` — parse the demo .env text into
/// {name: value}, comments and blank lines out.
pub fn load_profile(text: &str) -> Value {
    let mut pairs: Vec<(String, Value)> = Vec::new();
    for raw in text.lines() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let (name, value) = match line.split_once('=') {
            Some((n, v)) => (n.trim().to_string(), v.trim().to_string()),
            None => (line.to_string(), String::new()),
        };
        if let Some(slot) = pairs.iter_mut().find(|(k, _)| *k == name) {
            slot.1 = Value::s(&value);
        } else {
            pairs.push((name, Value::s(&value)));
        }
    }
    Value::Map(pairs)
}

/// The profile's WATCHDOG_* entries, as the environment
/// overlay the source applies before thresholds load.
pub fn profile_env(profile: &Value) -> Vec<(String, String)> {
    match profile.as_map() {
        Some(pairs) => pairs
            .iter()
            .filter(|(name, _)| name.starts_with("WATCHDOG_"))
            .map(|(name, value)| (name.clone(), value.py_str()))
            .collect(),
        None => Vec::new(),
    }
}

/// `_apply_profile_or_fail` + the import-time assert: the
/// profile must state DEMO_TICK_INTERVAL_SECONDS equal to
/// the measured interval, and the loaded (demo) thresholds'
/// stall window must equal the profile's
/// WATCHDOG_STALL_MINUTES. Err is the assertion message.
pub fn check_profile(profile: &Value, thresholds: &Thresholds) -> Result<(), String> {
    let tick_interval = profile.get("DEMO_TICK_INTERVAL_SECONDS");
    if tick_interval.is_null() {
        return Err("demo profile must state DEMO_TICK_INTERVAL_SECONDS".to_string());
    }
    let stated: i64 = tick_interval.py_str().parse().unwrap_or(i64::MIN);
    if stated != TICK_INTERVAL_SECONDS {
        return Err(format!(
            "measurement ticks every {}s but the profile says {}s — run the loop at the measured interval or re-measure",
            TICK_INTERVAL_SECONDS,
            tick_interval.py_str()
        ));
    }
    let profile_stall: i64 = profile
        .get("WATCHDOG_STALL_MINUTES")
        .py_str()
        .parse()
        .unwrap_or(i64::MIN);
    if thresholds.stall_minutes != profile_stall {
        return Err(format!(
            "loaded stall window {} does not match demo profile {} — refusing to measure on the wrong thresholds",
            thresholds.stall_minutes,
            profile.get("WATCHDOG_STALL_MINUTES").py_str()
        ));
    }
    Ok(())
}

/// One rehearsal's report (the source's report dict).
#[derive(Debug, Clone)]
pub struct Rehearsal {
    pub phase_seconds: i64,
    pub catch_seconds: i64,
    pub last_progress_age_seconds: i64,
    pub ticks_to_catch: i64,
    pub alert: Value,
}

/// `run_rehearsal(phase_seconds)` — one catch measurement at
/// the given tick-grid phase. Err is the assertion message.
pub fn run_rehearsal(
    watchdog: &dyn Watchdog,
    thresholds: &Thresholds,
    phase_seconds: i64,
) -> Result<Rehearsal, String> {
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
    worker.claim(&mut snapshot, JOB_ID, T0, thresholds);
    worker.progress(&mut snapshot, T0 + PROGRESS_AT_OFFSET, "working on it");
    worker.heartbeat(&mut snapshot, T0 + PROGRESS_AT_OFFSET);
    let got = watchdog.tick(&snapshot, Some(T0 + PROGRESS_AT_OFFSET));
    if !got.is_empty() {
        return Err("healthy staged worker must yield zero alerts".to_string());
    }
    let cue_at = T0 + CUE_OFFSET;
    worker.kill(&mut snapshot);
    if snapshot
        .get("presence")
        .as_list()
        .map(|p| p.iter().any(|n| n.as_str() == Some(NICK)))
        .unwrap_or(false)
    {
        return Err("killed worker still present".to_string());
    }
    let mut tick_at = cue_at + phase_seconds;
    let mut alert: Option<Value> = None;
    let mut ticks: i64 = 0;
    while tick_at < cue_at + CATCH_BUDGET_SECONDS {
        ticks += 1;
        let got = watchdog.tick(&snapshot, Some(tick_at));
        if !got.is_empty() {
            if got.len() != 1 {
                return Err(format!(
                    "catch tick must yield exactly one alert, got {}",
                    Value::List(got).py_repr()
                ));
            }
            alert = Some(got[0].clone());
            break;
        }
        tick_at += TICK_INTERVAL_SECONDS;
    }
    let alert = alert.ok_or_else(|| {
        format!(
            "no alert within {}s of the cue (phase {}s) — catch budget missed",
            CATCH_BUDGET_SECONDS, phase_seconds
        )
    })?;
    for (field, want) in [("kind", "presence-stall"), ("nick", NICK), ("job", JOB_ID)] {
        if alert.get(field).as_str() != Some(want) {
            return Err(format!("alert {}", alert.py_repr()));
        }
    }
    let lines = watchdog.announcements_for(std::slice::from_ref(&alert));
    if lines.len() != 1 || !lines[0].starts_with("ALERT:") {
        return Err(format!("lines {:?}", lines));
    }
    Ok(Rehearsal {
        phase_seconds,
        catch_seconds: tick_at - cue_at,
        last_progress_age_seconds: alert
            .get("last_progress_age_seconds")
            .as_int()
            .unwrap_or(0),
        ticks_to_catch: ticks,
        alert,
    })
}

/// `run_measurement()` — all three rehearsals.
pub fn run_measurement(
    watchdog: &dyn Watchdog,
    thresholds: &Thresholds,
) -> Result<Vec<Rehearsal>, String> {
    TICK_PHASES_SECONDS
        .iter()
        .map(|phase| run_rehearsal(watchdog, thresholds, *phase))
        .collect()
}

/// The source main()'s printed lines, success or failure.
pub fn main_lines(result: &Result<Vec<Rehearsal>, String>) -> Vec<String> {
    match result {
        Ok(reports) => {
            let mut lines: Vec<String> = reports
                .iter()
                .map(|r| {
                    format!(
                        "demo_catch_time measurement: rehearsal (tick phase +{}s): catch {}s after cue, alert presence-stall milo/7, last progress {}s ago, {} ticks",
                        r.phase_seconds,
                        r.catch_seconds,
                        r.last_progress_age_seconds,
                        r.ticks_to_catch
                    )
                })
                .collect();
            let catches = reports
                .iter()
                .map(|r| format!("{}s", r.catch_seconds))
                .collect::<Vec<_>>()
                .join(", ");
            lines.push(format!(
                "demo_catch_time measurement: PASS — 3/3 rehearsals under {}s (catches: {})",
                CATCH_BUDGET_SECONDS, catches
            ));
            lines
        }
        Err(exc) => vec![format!("demo_catch_time measurement: FAIL: {}", exc)],
    }
}

/// The phase report for a finished measurement.
pub fn report(result: &Result<Vec<Rehearsal>, String>) -> DrillReport {
    match result {
        Ok(reports) => DrillReport::new(
            "demo_catch_time",
            reports
                .iter()
                .map(|r| {
                    PhaseResult::pass(
                        &format!("rehearsal +{}s", r.phase_seconds),
                        format!("catch {}s", r.catch_seconds),
                    )
                })
                .collect(),
        ),
        Err(exc) => DrillReport::new(
            "demo_catch_time",
            vec![PhaseResult::fail("run_measurement", exc.clone())],
        ),
    }
}
