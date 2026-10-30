//! Port of `os/intel/drills/collision.py` — collision
//! drill (Milo lane, WDG-021).
//!
//! Two fake workers claim jobs whose files fields overlap on
//! one path; neither has finished, neither is stalled — yet
//! the watchdog must raise exactly one critical
//! file-collision alert naming both jobs and the shared
//! path, keep raising it while both work, and stop when one
//! job finishes. The alert line is held, never posted; the
//! drill asserts the held announcement line exists.
//!
//! Like the source, `run_drill` fails by assertion: Err
//! carries the assertion message, and `main_lines` renders
//! the source's "collision drill: ..." output either way.

use crate::b12a_drills::deps::Watchdog;
use crate::b12a_drills::value::Value;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub const FIRST_ID: &str = "1";
pub const SECOND_ID: &str = "2";
pub const FIRST_NICK: &str = "pax";
pub const SECOND_NICK: &str = "rowan";
pub const SHARED_PATH: &str = "intel/store.py";
pub const NOW: i64 = 10000;

/// The drill's FakeWorker: claims a job, stays present and
/// fresh (fresh claims with present nicks in the caps
/// registry mean no stall detector can fire, so any alert
/// here is a collision alert or a test bug).
pub struct FakeWorker {
    pub nick: String,
}

impl FakeWorker {
    pub fn new(nick: &str) -> Self {
        FakeWorker {
            nick: nick.to_string(),
        }
    }

    pub fn claim(&self, snapshot: &mut Value, job_id: &str, files: &str) -> Value {
        let job = Value::obj(vec![
            ("id", Value::s(job_id)),
            ("title", Value::s(&format!("job {}", job_id))),
            ("status", Value::s("claimed")),
            ("claim", Value::s(&self.nick)),
            ("claimed_at", Value::Int(NOW - 10)),
            ("files", Value::s(files)),
        ]);
        match snapshot.get("jobs") {
            Value::List(mut items) => {
                items.push(job.clone());
                snapshot.set("jobs", Value::List(items));
            }
            _ => snapshot.set("jobs", Value::List(vec![job.clone()])),
        }
        let mut presence: Vec<Value> = snapshot
            .get("presence")
            .as_list()
            .cloned()
            .unwrap_or_default();
        if !presence.iter().any(|n| n.as_str() == Some(&self.nick)) {
            presence.push(Value::s(&self.nick));
        }
        snapshot.set("presence", Value::List(presence));
        let mut caps = snapshot.get("caps");
        if !caps.is_dict() {
            caps = Value::obj(vec![]);
        }
        caps.set(
            &self.nick,
            Value::obj(vec![("caps", Value::s("build"))]),
        );
        snapshot.set("caps", caps);
        job
    }

    pub fn progress(&self, snapshot: &mut Value, text: &str) {
        let message = Value::obj(vec![
            ("nick", Value::s(&self.nick)),
            ("text", Value::s(text)),
        ]);
        match snapshot.get("messages") {
            Value::List(mut items) => {
                items.push(message);
                snapshot.set("messages", Value::List(items));
            }
            _ => snapshot.set("messages", Value::List(vec![message])),
        }
    }
}

/// A finished run: the phase log and the collision alert.
pub struct CollisionOutcome {
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
pub fn run_drill(watchdog: &dyn Watchdog) -> Result<CollisionOutcome, String> {
    let mut log: Vec<String> = Vec::new();
    let mut phases: Vec<PhaseResult> = Vec::new();
    let mut snapshot = Value::obj(vec![
        ("messages", Value::List(vec![])),
        ("jobs", Value::List(vec![])),
        ("presence", Value::List(vec![])),
        ("caps", Value::obj(vec![])),
    ]);
    let first = FakeWorker::new(FIRST_NICK);
    let second = FakeWorker::new(SECOND_NICK);

    // Phase 1 — disjoint claims: no collision, nothing to warn.
    first.claim(&mut snapshot, FIRST_ID, "intel/watchdog.py");
    second.claim(&mut snapshot, SECOND_ID, "intel/brief.py");
    let got = watchdog.tick(&snapshot, Some(NOW));
    assert(
        got.is_empty(),
        format!(
            "disjoint claims must yield zero alerts, got {}",
            Value::List(got).py_repr()
        ),
    )?;
    log.push("phase 1: disjoint claims yield zero alerts".to_string());
    phases.push(PhaseResult::pass("phase 1", ""));

    // Phase 2 — the overlap.
    set_job_field(&mut snapshot, SECOND_ID, "files", &format!("{}, intel/brief.py", SHARED_PATH));
    set_job_field(&mut snapshot, FIRST_ID, "files", &format!("intel/watchdog.py, {}", SHARED_PATH));
    let got = watchdog.tick(&snapshot, Some(NOW));
    assert(
        got.len() == 1,
        format!(
            "overlapping claims must yield exactly one alert, got {}: {}",
            got.len(),
            Value::List(got.clone()).py_repr()
        ),
    )?;
    let alert = got[0].clone();
    for (field, want) in [
        ("kind", "file-collision"),
        ("severity", "critical"),
        ("job", FIRST_ID),
        ("other_job", SECOND_ID),
        ("shared_path", SHARED_PATH),
    ] {
        assert(
            alert.get(field).as_str() == Some(want),
            format!("alert {}", alert.py_repr()),
        )?;
    }
    let explanation = alert.get("explanation").py_str();
    for needle in [FIRST_ID, SECOND_ID, SHARED_PATH] {
        assert(
            explanation.contains(needle),
            format!("alert {}", alert.py_repr()),
        )?;
    }
    assert(
        alert.get("dedupe_key").as_str()
            == Some(&format!(
                "file-collision:{}:{}:{}",
                FIRST_ID, SECOND_ID, SHARED_PATH
            )),
        format!("alert {}", alert.py_repr()),
    )?;
    let lines = watchdog.announcements_for(&got);
    assert(
        lines.len() == 1 && lines[0].starts_with("ALERT:"),
        format!("lines {:?}", lines),
    )?;
    log.push(format!(
        "phase 2: critical collision alert names jobs {}/{} on {}; announcement line held, not posted",
        FIRST_ID, SECOND_ID, SHARED_PATH
    ));
    phases.push(PhaseResult::pass("phase 2", ""));

    // Phase 3 — still colliding: the same alert keeps firing.
    first.progress(&mut snapshot, "working on it");
    second.progress(&mut snapshot, "working on it");
    let got = watchdog.tick(&snapshot, Some(NOW + 60));
    assert(
        got.len() == 1,
        format!(
            "live overlap must keep firing, got {}",
            Value::List(got.clone()).py_repr()
        ),
    )?;
    assert(
        got[0].get("dedupe_key") == alert.get("dedupe_key"),
        format!("got {}", Value::List(got).py_repr()),
    )?;
    log.push(
        "phase 3: while both jobs stay claimed, the same collision alert keeps firing (same dedupe key)"
            .to_string(),
    );
    phases.push(PhaseResult::pass("phase 3", ""));

    // Phase 4 — one job finishes: the alert stops firing.
    set_job_field(&mut snapshot, FIRST_ID, "status", "done");
    let got = watchdog.tick(&snapshot, Some(NOW + 120));
    assert(
        got.is_empty(),
        format!(
            "finished overlap must stop firing, got {}",
            Value::List(got).py_repr()
        ),
    )?;
    log.push(
        "phase 4: after one job finishes (no branch), the collision alert stops firing"
            .to_string(),
    );
    phases.push(PhaseResult::pass("phase 4", ""));

    Ok(CollisionOutcome {
        alert,
        log,
        phases,
    })
}

fn set_job_field(snapshot: &mut Value, job_id: &str, field: &str, value: &str) {
    if let Value::List(mut items) = snapshot.get("jobs") {
        for job in items.iter_mut() {
            if job.get("id").as_str() == Some(job_id) {
                job.set(field, Value::s(value));
            }
        }
        snapshot.set("jobs", Value::List(std::mem::take(&mut items)));
    }
}

/// The source main()'s printed lines, success or failure.
pub fn main_lines(result: &Result<CollisionOutcome, String>) -> Vec<String> {
    match result {
        Ok(outcome) => {
            let mut lines: Vec<String> = outcome
                .log
                .iter()
                .map(|line| format!("collision drill: {}", line))
                .collect();
            lines.push("collision drill: PASS".to_string());
            lines
        }
        Err(exc) => vec![format!("collision drill: FAIL: {}", exc)],
    }
}

/// The phase report for a finished run.
pub fn report(result: &Result<CollisionOutcome, String>) -> DrillReport {
    match result {
        Ok(outcome) => DrillReport::new("collision", outcome.phases.clone()),
        Err(exc) => DrillReport::new(
            "collision",
            vec![PhaseResult::fail("run_drill", exc.clone())],
        ),
    }
}
