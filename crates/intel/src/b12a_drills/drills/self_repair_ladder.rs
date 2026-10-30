//! Port of `os/intel/drills/self_repair_ladder.py` —
//! self-repair ladder drill (Milo lane, OS-095).
//!
//! Three staged stalls (unresponsive worker, dead worker,
//! job held by the wrong worker) are each resolved by the
//! correct rung with zero Dale contact; every ladder action
//! appears in the journal and the next brief. The ladder
//! module (B09) is the watchdog's judgment: it selects the
//! rung from snapshot facts and journals the decision; it
//! never performs the rung. Each phase pairs the ladder
//! record with a simulated owner applying the rung, exactly
//! as OS-034 pairs its alerts with a simulated restart. The
//! drill does NOT claim a live nudge, restart, or reassign.

use super::DrillOutcome;
use crate::b12a_drills::deps::{Ladder, Thresholds, Watchdog};
use crate::b12a_drills::value::Value;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub const T0: i64 = 100000;
pub const WORKER: &str = "pax";
pub const SIBLING: &str = "hana";
pub const WALK_ON: &str = "ghost";

/// `base_snapshot(presence, jobs)` — caps carry the two
/// registered workers.
pub fn base_snapshot(presence: &[&str], jobs: Vec<Value>) -> Value {
    Value::obj(vec![
        (
            "caps",
            Value::obj(vec![
                (WORKER, Value::obj(vec![("caps", Value::s("python"))])),
                (SIBLING, Value::obj(vec![("caps", Value::s("python"))])),
            ]),
        ),
        (
            "presence",
            Value::List(presence.iter().map(|n| Value::s(n)).collect()),
        ),
        ("jobs", Value::List(jobs)),
        ("messages", Value::List(vec![])),
    ])
}

/// The drill's `job()` builder (note: `last_progress_at`).
pub fn job(job_id: &str, claimer: &str, last_progress: i64, files: Option<Vec<&str>>) -> Value {
    let mut record = Value::obj(vec![
        ("id", Value::s(job_id)),
        ("title", Value::s(&format!("job {}", job_id))),
        ("status", Value::s("claimed")),
        ("claim", Value::s(claimer)),
        ("claimed_at", Value::Int(T0)),
        ("last_progress_at", Value::Int(last_progress)),
    ]);
    if let Some(files) = files {
        record.set(
            "files",
            Value::List(files.iter().map(|f| Value::s(f)).collect()),
        );
    }
    record
}

fn phase(
    name: &str,
    result: Result<String, String>,
    phases: &mut Vec<PhaseResult>,
    lines: &mut Vec<String>,
) -> bool {
    match result {
        Ok(pass_line) => {
            phases.push(PhaseResult::pass(name, ""));
            lines.push(pass_line);
            true
        }
        Err(fail_line) => {
            phases.push(PhaseResult::fail(name, fail_line.clone()));
            lines.push(fail_line);
            false
        }
    }
}

fn phase_nudge(
    watchdog: &dyn Watchdog,
    ladder: &dyn Ladder,
    t: &Thresholds,
) -> Result<String, String> {
    let now = T0 + t.progress_stall_minutes * 60 + 60;
    let snap = base_snapshot(&[WORKER, SIBLING], vec![job("7", WORKER, T0, None)]);
    let alerts = watchdog.detect_progress_stall(&snap, Some(now));
    if alerts.len() != 1 {
        return Err(format!(
            "nudge: FAIL: expected 1 progress-stall alert, got {}",
            alerts.len()
        ));
    }
    let records = ladder.ladder_tick(&snap, &alerts, &[], Some(now));
    if records.len() != 1 || records[0].get("rung").as_str() != Some("nudge") {
        return Err(format!(
            "nudge: FAIL: expected 1 nudge record, got {}",
            Value::List(records).py_repr()
        ));
    }
    let record = &records[0];
    if record.get("worker").as_str() != Some(WORKER) || record.get("job").as_str() != Some("7") {
        return Err(format!(
            "nudge: FAIL: record names {}/{}, expected {}/7",
            record.get("worker").py_str(),
            record.get("job").py_str(),
            WORKER
        ));
    }
    let lines = ladder.ladder_brief_lines(&records);
    if lines.len() != 1
        || !lines[0].contains("nudge")
        || !lines[0].contains('7')
        || !lines[0].contains(WORKER)
    {
        return Err(format!(
            "nudge: FAIL: brief line {:?} names no rung/job/worker",
            lines
        ));
    }
    Ok(format!(
        "nudge: present worker {}, stale job 7 -> rung nudge, journal + brief line agree: PASS",
        WORKER
    ))
}

fn phase_restart(
    watchdog: &dyn Watchdog,
    ladder: &dyn Ladder,
    t: &Thresholds,
) -> Result<String, String> {
    let now = T0 + t.stall_minutes * 60 + 60;
    let snap = base_snapshot(&[SIBLING], vec![job("7", WORKER, T0, None)]);
    let alerts = watchdog.detect_presence_stall(&snap, Some(now));
    if alerts.len() != 1 {
        return Err(format!(
            "restart: FAIL: expected 1 presence-stall alert, got {}",
            alerts.len()
        ));
    }
    let before = snap.clone();
    let records = ladder.ladder_tick(&snap, &alerts, &[], Some(now));
    if records.len() != 1 || records[0].get("rung").as_str() != Some("restart") {
        return Err(format!(
            "restart: FAIL: expected 1 restart record, got {}",
            Value::List(records).py_repr()
        ));
    }
    if snap != before {
        return Err("restart: FAIL: ladder tick mutated the snapshot".to_string());
    }
    let claim = snap
        .get("jobs")
        .as_list()
        .and_then(|items| items.first().map(|j| j.get("claim")))
        .unwrap_or(Value::Null);
    if claim.as_str() != Some(WORKER) {
        return Err(format!(
            "restart: FAIL: ladder moved the claim; the claim stays with {} until systemd/overseer act",
            WORKER
        ));
    }
    let note = watchdog.restart_event_note(WORKER, "7", now, None);
    if note.get("kind").as_str() != Some("worker-restart")
        || note.get("severity").as_str() != Some("info")
    {
        return Err(format!(
            "restart: FAIL: simulated systemd note is not an info worker-restart record: {}",
            note.py_repr()
        ));
    }
    Ok(format!(
        "restart: absent worker {}, job 7 stays claimed, rung restart journaled, systemd note is info: PASS",
        WORKER
    ))
}

fn phase_reassign(ladder: &dyn Ladder) -> Result<String, String> {
    let now = T0 + 600;
    let files = vec!["a.txt", "b.txt"];
    let snap = base_snapshot(
        &[WORKER, SIBLING],
        vec![job("9", WALK_ON, T0 + 100, Some(files.clone()))],
    );
    let stall = Value::obj(vec![
        ("kind", Value::s("presence-stall")),
        ("nick", Value::s(WALK_ON)),
        ("job", Value::s("9")),
    ]);
    let records = ladder.ladder_tick(&snap, std::slice::from_ref(&stall), &[], Some(now));
    if records.len() != 1 || records[0].get("rung").as_str() != Some("reassign") {
        return Err(format!(
            "reassign: FAIL: expected 1 reassign record, got {}",
            Value::List(records).py_repr()
        ));
    }
    let baton = records[0].get("baton");
    let files_value = Value::List(files.iter().map(|f| Value::s(f)).collect());
    if baton.is_null()
        || baton.get("last_progress_at").as_int() != Some(T0 + 100)
        || baton.get("files") != files_value
    {
        return Err(format!(
            "reassign: FAIL: baton {} does not carry the deposited progress and files exactly",
            baton.py_repr()
        ));
    }
    let moved = job(
        "9",
        SIBLING,
        baton.get("last_progress_at").as_int().unwrap_or(0),
        Some(files.clone()),
    );
    if moved.get("last_progress_at").as_int() != Some(T0 + 100)
        || moved.get("files") != files_value
    {
        return Err(
            "reassign: FAIL: simulated overseer move changed progress or files; the baton pass must not repeat work"
                .to_string(),
        );
    }
    Ok(format!(
        "reassign: walk-on {} holding job 9 -> rung reassign, baton carries progress + files exactly, claim moves to {} with no repeated work: PASS",
        WALK_ON, SIBLING
    ))
}

fn phase_idempotent(
    watchdog: &dyn Watchdog,
    ladder: &dyn Ladder,
    t: &Thresholds,
) -> Result<String, String> {
    let now = T0 + t.stall_minutes * 60 + 60;
    let snap = base_snapshot(&[SIBLING], vec![job("7", WORKER, T0, None)]);
    let alerts = watchdog.detect_presence_stall(&snap, Some(now));
    let first = ladder.ladder_tick(&snap, &alerts, &[], Some(now));
    let second = ladder.ladder_tick(&snap, &alerts, &first, Some(now));
    if first.len() != 1 || !second.is_empty() {
        return Err(format!(
            "idempotent: FAIL: first tick {} records, second tick {} records, expected 1 then 0",
            first.len(),
            second.len()
        ));
    }
    Ok("idempotent: second tick over the same stall journals nothing new: PASS".to_string())
}

fn phase_no_dale_and_immutable(
    watchdog: &dyn Watchdog,
    ladder: &dyn Ladder,
    t: &Thresholds,
) -> Result<String, String> {
    let now = T0 + t.progress_stall_minutes * 60 + 60;
    let snap = base_snapshot(&[WORKER, SIBLING], vec![job("7", WORKER, T0, None)]);
    let alerts = watchdog.detect_progress_stall(&snap, Some(now));
    let before = snap.clone();
    let records = ladder.ladder_tick(&snap, &alerts, &[], Some(now));
    let push_ledger: Vec<Value> = Vec::new();
    if snap != before {
        return Err("no-dale: FAIL: ladder tick mutated the snapshot".to_string());
    }
    for record in &records {
        if record.get("kind").as_str() != Some("ladder-action") {
            return Err(format!(
                "no-dale: FAIL: journal record kind {} is not ladder-action",
                record.get("kind").py_repr()
            ));
        }
        if record.contains_key("push") || record.contains_key("announcement") {
            return Err(format!(
                "no-dale: FAIL: journal record carries a push or announcement field: {}",
                record.py_repr()
            ));
        }
    }
    if !push_ledger.is_empty() {
        return Err("no-dale: FAIL: push ledger is not empty".to_string());
    }
    Ok("no-dale: journal holds only ladder-action records, push ledger empty, snapshot unchanged: PASS".to_string())
}

/// The drill's main(): all five phases, then the summary.
pub fn run(
    watchdog: &dyn Watchdog,
    ladder: &dyn Ladder,
    thresholds: &Thresholds,
) -> DrillOutcome {
    let mut phases: Vec<PhaseResult> = Vec::new();
    let mut lines: Vec<String> = Vec::new();
    let mut ok = true;
    ok &= phase(
        "nudge",
        phase_nudge(watchdog, ladder, thresholds),
        &mut phases,
        &mut lines,
    );
    ok &= phase(
        "restart",
        phase_restart(watchdog, ladder, thresholds),
        &mut phases,
        &mut lines,
    );
    ok &= phase("reassign", phase_reassign(ladder), &mut phases, &mut lines);
    ok &= phase(
        "idempotent",
        phase_idempotent(watchdog, ladder, thresholds),
        &mut phases,
        &mut lines,
    );
    ok &= phase(
        "no-dale",
        phase_no_dale_and_immutable(watchdog, ladder, thresholds),
        &mut phases,
        &mut lines,
    );
    lines.push(format!(
        "self_repair_ladder: {}",
        if ok { "ALL PHASES PASS" } else { "FAILED" }
    ));
    DrillOutcome {
        report: DrillReport::new("self_repair_ladder", phases),
        lines,
    }
}
