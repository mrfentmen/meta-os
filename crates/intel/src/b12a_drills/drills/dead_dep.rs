//! Port of `os/intel/drills/dead_dep.py` — dead-dep drill
//! (Milo lane, WDG-022).
//!
//! Job A is posted, job B is posted depending on A, then A
//! gets blocked with a reason: the watchdog must raise
//! exactly one critical dead-dep alert naming both jobs and
//! A's blocking reason verbatim — keep raising it while A
//! stays blocked, and stop once A is unblocked. The
//! dead-dep detector has no age gate by design, so the drill
//! ages the clock between phases to show persistence, not to
//! cross a threshold. The alert line is held, never posted.
//!
//! Like the source, `run_drill` fails by assertion: Err
//! carries the assertion message, and `main_lines` renders
//! the source's "dead-dep drill: ..." output either way.

use crate::b12a_drills::deps::Watchdog;
use crate::b12a_drills::value::Value;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub const DEP_ID: &str = "1";
pub const JOB_ID: &str = "2";
pub const REASON: &str = "needs Pax sign-off on the key shape";
pub const NOW: i64 = 10000;

/// `_post` — append a job, deps when given.
fn post(snapshot: &mut Value, job_id: &str, deps: Option<&str>) -> Value {
    let mut pairs = vec![
        ("id", Value::s(job_id)),
        ("title", Value::s(&format!("job {}", job_id))),
        ("status", Value::s("open")),
    ];
    if let Some(deps) = deps {
        pairs.push(("deps", Value::s(deps)));
    }
    let job = Value::obj(pairs);
    match snapshot.get("jobs") {
        Value::List(mut items) => {
            items.push(job.clone());
            snapshot.set("jobs", Value::List(items));
        }
        _ => snapshot.set("jobs", Value::List(vec![job.clone()])),
    }
    job
}

fn mutate_job(
    snapshot: &mut Value,
    job_id: &str,
    f: impl Fn(&mut Value),
) -> Result<Value, String> {
    if let Value::List(mut items) = snapshot.get("jobs") {
        for job in items.iter_mut() {
            if job.get("id").as_str() == Some(job_id) {
                f(job);
                let out = job.clone();
                snapshot.set("jobs", Value::List(std::mem::take(&mut items)));
                return Ok(out);
            }
        }
        snapshot.set("jobs", Value::List(items));
    }
    Err(format!("no job {} to block", job_id))
}

/// `_block` — status blocked, note = the reason.
fn block(snapshot: &mut Value, job_id: &str, reason: &str) -> Result<Value, String> {
    mutate_job(snapshot, job_id, |job| {
        job.set("status", Value::s("blocked"));
        job.set("note", Value::s(reason));
    })
}

/// `_unblock` — status open, note removed.
fn unblock(snapshot: &mut Value, job_id: &str) -> Result<Value, String> {
    mutate_job(snapshot, job_id, |job| {
        job.set("status", Value::s("open"));
        job.remove("note");
    })
    .map_err(|_| format!("no job {} to unblock", job_id))
}

/// A finished run: the phase log and the dead-dep alert.
pub struct DeadDepOutcome {
    pub alert: Value,
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
pub fn run_drill(watchdog: &dyn Watchdog) -> Result<DeadDepOutcome, String> {
    let mut log: Vec<String> = Vec::new();
    let mut phases: Vec<PhaseResult> = Vec::new();
    let mut snapshot = Value::obj(vec![
        ("messages", Value::List(vec![])),
        ("jobs", Value::List(vec![])),
        ("presence", Value::List(vec![])),
        ("caps", Value::obj(vec![])),
    ]);

    // Phase 1 — A and B posted, A live: nothing to warn about.
    post(&mut snapshot, DEP_ID, None);
    post(&mut snapshot, JOB_ID, Some(DEP_ID));
    let got = watchdog.tick(&snapshot, Some(NOW));
    assert(
        got.is_empty(),
        format!(
            "live dep must yield zero alerts, got {}",
            Value::List(got).py_repr()
        ),
    )?;
    log.push("phase 1: posted A and B(deps A) with A live yield zero alerts".to_string());
    phases.push(PhaseResult::pass("phase 1", ""));

    // Phase 2 — A blocked with a reason: the alert fires,
    // naming B, A, and the reason verbatim.
    block(&mut snapshot, DEP_ID, REASON)?;
    let got = watchdog.tick(&snapshot, Some(NOW + 60));
    assert(
        got.len() == 1,
        format!(
            "blocked dep must yield exactly one alert, got {}: {}",
            got.len(),
            Value::List(got.clone()).py_repr()
        ),
    )?;
    let alert = got[0].clone();
    for (field, want) in [
        ("kind", "dead-dep"),
        ("severity", "critical"),
        ("job", JOB_ID),
        ("dep", DEP_ID),
        ("blocking_reason", REASON),
    ] {
        assert(
            alert.get(field).as_str() == Some(want),
            format!("alert {}", alert.py_repr()),
        )?;
    }
    let explanation = alert.get("explanation").py_str();
    for needle in [REASON, JOB_ID, DEP_ID] {
        assert(
            explanation.contains(needle),
            format!("alert {}", alert.py_repr()),
        )?;
    }
    assert(
        alert.get("dedupe_key").as_str() == Some(&format!("dead-dep:{}:{}", JOB_ID, DEP_ID)),
        format!("alert {}", alert.py_repr()),
    )?;
    let lines = watchdog.announcements_for(&got);
    assert(
        lines.len() == 1 && lines[0].starts_with("ALERT:"),
        format!("lines {:?}", lines),
    )?;
    log.push(format!(
        "phase 2: critical dead-dep alert names job {} blocked on dep {} for reason '{}' verbatim; announcement line held, not posted",
        JOB_ID, DEP_ID, REASON
    ));
    phases.push(PhaseResult::pass("phase 2", ""));

    // Phase 3 — A still blocked, clock aged: same alert.
    let got = watchdog.tick(&snapshot, Some(NOW + 3600));
    assert(
        got.len() == 1,
        format!(
            "still-blocked dep must keep firing, got {}",
            Value::List(got.clone()).py_repr()
        ),
    )?;
    assert(
        got[0].get("dedupe_key") == alert.get("dedupe_key"),
        format!("got {}", Value::List(got).py_repr()),
    )?;
    log.push(
        "phase 3: while A stays blocked, the same dead-dep alert keeps firing (same dedupe key)"
            .to_string(),
    );
    phases.push(PhaseResult::pass("phase 3", ""));

    // Phase 4 — A unblocked: the alert stops firing.
    unblock(&mut snapshot, DEP_ID)?;
    let got = watchdog.tick(&snapshot, Some(NOW + 3660));
    assert(
        got.is_empty(),
        format!(
            "unblocked dep must stop firing, got {}",
            Value::List(got).py_repr()
        ),
    )?;
    log.push("phase 4: after A is unblocked, the dead-dep alert stops firing".to_string());
    phases.push(PhaseResult::pass("phase 4", ""));

    Ok(DeadDepOutcome {
        alert,
        log,
        phases,
    })
}

/// The source main()'s printed lines, success or failure.
pub fn main_lines(result: &Result<DeadDepOutcome, String>) -> Vec<String> {
    match result {
        Ok(outcome) => {
            let mut lines: Vec<String> = outcome
                .log
                .iter()
                .map(|line| format!("dead-dep drill: {}", line))
                .collect();
            lines.push("dead-dep drill: PASS".to_string());
            lines
        }
        Err(exc) => vec![format!("dead-dep drill: FAIL: {}", exc)],
    }
}

/// The phase report for a finished run.
pub fn report(result: &Result<DeadDepOutcome, String>) -> DrillReport {
    match result {
        Ok(outcome) => DrillReport::new("dead_dep", outcome.phases.clone()),
        Err(exc) => DrillReport::new(
            "dead_dep",
            vec![PhaseResult::fail("run_drill", exc.clone())],
        ),
    }
}
