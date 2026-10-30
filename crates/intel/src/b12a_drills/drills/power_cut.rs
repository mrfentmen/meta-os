//! Port of `os/intel/drills/power_cut.py` — power-cut
//! drill (Milo lane, OS-040).
//!
//! Hard-kill the VM mid-job three times; on reboot leases
//! expire, jobs requeue, and the boot brief reports the
//! interruption. The cut is modeled the way OS-034 models
//! systemd: the worker vanishes with no graceful shutdown
//! and no lease release. What is proven is the watchdog +
//! sweep + brief half: one presence-stall alert past lease
//! expiry, the jobs.py requeue rule (the WDG-020 sweep in
//! `fixtures`, imported not re-implemented) reopening the
//! job, the OS-127 recovery line reporting "1 recovered",
//! and a second worker claiming the requeued job healthy. A
//! control run proves the sweep respects the lease. Zero
//! manual fixes: no step edits a job record by hand — in
//! this port the baton_step deposit is applied to the
//! snapshot's job record, which is the same record the
//! source's in-place dict edit touches.

use super::DrillOutcome;
use crate::b12a_drills::deps::{BriefSurface, Thresholds, Watchdog};
use crate::b12a_drills::fixtures::{sweep_expired_leases, FakeWorker};
use crate::b12a_drills::value::Value;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub const T0: i64 = 100000;
pub const RUNS: [(&str, &str); 3] = [("pax", "7"), ("rowan", "8"), ("hana", "9")];

fn check(
    phases: &mut Vec<PhaseResult>,
    log: &mut Vec<String>,
    name: &str,
    condition: bool,
    fail_detail: &str,
) -> bool {
    if condition {
        phases.push(PhaseResult::pass(name, ""));
        log.push(format!("PASS: {}", name));
    } else {
        phases.push(PhaseResult::fail(name, fail_detail.to_string()));
        log.push(format!("FAIL: {} — {}", name, fail_detail));
    }
    condition
}

fn job_in(snapshot: &Value, job_id: &str) -> Value {
    snapshot
        .get("jobs")
        .as_list()
        .and_then(|items| items.iter().find(|j| j.get("id").as_str() == Some(job_id)).cloned())
        .unwrap_or(Value::Null)
}

fn set_job_field(snapshot: &mut Value, job_id: &str, field: &str, value: Value) {
    if let Value::List(mut items) = snapshot.get("jobs") {
        for job in items.iter_mut() {
            if job.get("id").as_str() == Some(job_id) {
                job.set(field, value.clone());
            }
        }
        snapshot.set("jobs", Value::List(std::mem::take(&mut items)));
    }
}

/// One cut/reboot/recover cycle's report.
#[derive(Debug, Clone)]
pub struct RunReport {
    pub nick: String,
    pub job: String,
    pub alert: Value,
    pub requeued: Vec<String>,
    pub recovery_line: String,
}

/// The full drill result: outcome, per-run reports, control.
pub struct PowerCutOutcome {
    pub outcome: DrillOutcome,
    pub runs: Vec<RunReport>,
    pub control_ok: bool,
}

fn one_run(
    watchdog: &dyn Watchdog,
    brief: &dyn BriefSurface,
    thresholds: &Thresholds,
    nick: &str,
    job_id: &str,
) -> (bool, Vec<PhaseResult>, Vec<String>, RunReport) {
    let mut phases: Vec<PhaseResult> = Vec::new();
    let mut log: Vec<String> = Vec::new();
    let phases = &mut phases;
    let log = &mut log;
    let mut ok = true;
    let mut snapshot = Value::obj(vec![
        ("messages", Value::List(vec![])),
        ("jobs", Value::List(vec![])),
        ("presence", Value::List(vec![])),
        (
            "caps",
            Value::obj(vec![(
                nick,
                Value::obj(vec![("caps", Value::s("build"))]),
            )]),
        ),
    ]);
    let mut worker = FakeWorker::new(nick);

    // Phase 1 — healthy worker: claim, deposit progress + baton.
    worker.claim(&mut snapshot, job_id, T0, thresholds);
    worker.progress(&mut snapshot, T0 + 120, "halfway through the job");
    set_job_field(
        &mut snapshot,
        job_id,
        "baton_step",
        Value::s("step 2: second half remains"),
    );
    worker.heartbeat(&mut snapshot, T0 + 300);
    ok &= check(
        phases,
        log,
        "healthy worker ticks zero alerts",
        watchdog.tick(&snapshot, Some(T0 + 300)).is_empty(),
        "",
    );

    // Phase 2 — the power cut: no shutdown, no lease release.
    worker.kill(&mut snapshot);
    let job = job_in(&snapshot, job_id);
    ok &= check(
        phases,
        log,
        "cut leaves the job claimed, lease unreleased",
        job.get("status").as_str() == Some("claimed")
            && job.get("claim").as_str() == Some(nick)
            && job.get("lease_until").as_int().unwrap_or(0) > T0 + 300,
        &format!("got {}", job.py_repr()),
    );

    // Phase 3 — reboot past lease expiry: stall alert fires.
    let reboot_at = T0 + 300 + thresholds.lease_default_seconds + 61;
    let got = watchdog.tick(&snapshot, Some(reboot_at));
    let alert = got.first().cloned().unwrap_or(Value::obj(vec![]));
    let kinds: Vec<String> = got.iter().map(|a| a.get("kind").py_str()).collect();
    ok &= check(
        phases,
        log,
        "reboot tick yields exactly one presence-stall",
        kinds == vec!["presence-stall".to_string()],
        &format!("got {}", Value::List(got.clone()).py_repr()),
    );
    ok &= check(
        phases,
        log,
        "stall alert names nick, job, and age",
        alert.get("nick").as_str() == Some(nick)
            && alert.get("job").as_str() == Some(job_id)
            && alert.get("last_progress_age_seconds").as_int().unwrap_or(0)
                > thresholds.stall_minutes * 60,
        &format!("got {}", alert.py_repr()),
    );

    // Phase 4 — lease sweep: the job requeues, nothing else moves.
    let requeued = sweep_expired_leases(&mut snapshot, reboot_at);
    ok &= check(
        phases,
        log,
        "sweep requeues exactly this job",
        requeued == vec![job_id.to_string()],
        &format!("got {:?}", requeued),
    );
    let job = job_in(&snapshot, job_id);
    ok &= check(
        phases,
        log,
        "requeued job is open with claim cleared",
        job.get("status").as_str() == Some("open")
            && !job.contains_key("claim")
            && !job.contains_key("lease_until"),
        &format!("got {}", job.py_repr()),
    );

    // Phase 5 — boot brief reports the interruption, reconciled.
    let job = job_in(&snapshot, job_id);
    let recovery = Value::obj(vec![
        (
            "recovered",
            Value::List(vec![Value::obj(vec![
                ("id", Value::s(job_id)),
                (
                    "title",
                    if job.contains_key("title") {
                        job.get("title")
                    } else {
                        Value::s("demo job")
                    },
                ),
                ("baton_step", job.get("baton_step")),
            ])]),
        ),
        ("sweep_count", Value::Int(requeued.len() as i64)),
    ]);
    let line = brief.recovery_line(&recovery);
    ok &= check(
        phases,
        log,
        "boot brief recovery line reports 1 recovered",
        line.starts_with("In-flight jobs recovered at this boot: 1 recovered")
            && line.contains(job_id)
            && line.contains("step 2")
            && !line.contains("recovery incomplete"),
        &format!("got {}", line),
    );

    // Phase 6 — the stall alert auto-resolves; job is claimable.
    ok &= check(
        phases,
        log,
        "re-tick after requeue yields zero stall alerts",
        watchdog.tick(&snapshot, Some(reboot_at + 60)).is_empty(),
        "",
    );
    let mut second = FakeWorker::new("second-worker");
    second.claim(&mut snapshot, job_id, reboot_at + 120, thresholds);
    second.heartbeat(&mut snapshot, reboot_at + 120);
    ok &= check(
        phases,
        log,
        "second worker claims the requeued job healthy",
        watchdog.tick(&snapshot, Some(reboot_at + 120)).is_empty(),
        "",
    );

    (
        ok,
        std::mem::take(phases),
        std::mem::take(log),
        RunReport {
            nick: nick.to_string(),
            job: job_id.to_string(),
            alert,
            requeued,
            recovery_line: line,
        },
    )
}

fn control_run(
    watchdog: &dyn Watchdog,
    thresholds: &Thresholds,
) -> (bool, Vec<PhaseResult>, Vec<String>) {
    let mut phases: Vec<PhaseResult> = Vec::new();
    let mut log: Vec<String> = Vec::new();
    let phases = &mut phases;
    let log = &mut log;
    let mut ok = true;
    let (nick, job_id) = ("pax", "7");
    let mut snapshot = Value::obj(vec![
        ("messages", Value::List(vec![])),
        ("jobs", Value::List(vec![])),
        ("presence", Value::List(vec![])),
        (
            "caps",
            Value::obj(vec![(
                nick,
                Value::obj(vec![("caps", Value::s("build"))]),
            )]),
        ),
    ]);
    let mut worker = FakeWorker::new(nick);
    worker.claim(&mut snapshot, job_id, T0, thresholds);
    worker.progress(&mut snapshot, T0 + 120, "halfway through the job");
    worker.kill(&mut snapshot);
    let early = T0 + 300 + thresholds.stall_minutes * 60 + 61;
    let kinds: Vec<String> = watchdog
        .tick(&snapshot, Some(early))
        .iter()
        .map(|a| a.get("kind").py_str())
        .collect();
    ok &= check(
        phases,
        log,
        "early reboot still fires the stall alert",
        kinds == vec!["presence-stall".to_string()],
        "",
    );
    let requeued = sweep_expired_leases(&mut snapshot, early);
    let job = job_in(&snapshot, job_id);
    ok &= check(
        phases,
        log,
        "early sweep requeues nothing, lease unexpired",
        requeued.is_empty() && job.get("status").as_str() == Some("claimed"),
        &format!("got {}", job.py_repr()),
    );
    (ok, std::mem::take(phases), std::mem::take(log))
}

/// `run_drill()` — all three power cuts plus the control.
pub fn run_drill(
    watchdog: &dyn Watchdog,
    brief: &dyn BriefSurface,
    thresholds: &Thresholds,
) -> PowerCutOutcome {
    let mut phases: Vec<PhaseResult> = Vec::new();
    let mut log: Vec<String> = Vec::new();
    let mut ok = true;
    let mut reports: Vec<RunReport> = Vec::new();
    for (nick, job_id) in RUNS {
        let (run_ok, run_phases, run_log, report) =
            one_run(watchdog, brief, thresholds, nick, job_id);
        ok &= run_ok;
        log.push(format!("--- power cut: {}/job {} ---", nick, job_id));
        log.extend(run_log);
        phases.extend(run_phases);
        reports.push(report);
    }
    let (control_ok, ctl_phases, ctl_log) = control_run(watchdog, thresholds);
    ok &= control_ok;
    log.push("--- control: reboot before lease expiry ---".to_string());
    log.extend(ctl_log);
    phases.extend(ctl_phases);
    let mut lines = log;
    lines.push(format!("RESULT: {}", if ok { "PASS" } else { "FAIL" }));
    PowerCutOutcome {
        outcome: DrillOutcome {
            report: DrillReport::new("power_cut", phases),
            lines,
        },
        runs: reports,
        control_ok,
    }
}
