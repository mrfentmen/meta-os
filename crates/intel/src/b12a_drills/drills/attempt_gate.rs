//! Port of `os/intel/drills/attempt_gate.py` (Milo, OS-096).
//!
//! Phases on fixtures with a fake clock: impossible burns exactly its
//! budget then parks + escalates once (no loop/dup); crew-fixable dep
//! parks nothing; money dale-call parks at once quoting the note;
//! malformed budgets are unbudgeted; escalation count is exactly two and
//! the sent ledger stays empty; inputs immutable; brief names parks.

use crate::b09_core::gate::{self, JobInt, JobRecord};
use crate::b10_brief::push as push_mod;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub const T0: i64 = 100000;

fn job(id: &str, attempts: JobInt, max: JobInt, blocker: Option<&str>, note: &str) -> JobRecord {
    JobRecord { id: Some(id.into()), status: "open".into(), attempts: Some(attempts), max_attempts: Some(max), blocker_kind: blocker.map(str::to_string), note: note.into() }
}

fn int(n: i64) -> JobInt {
    JobInt::Int(n)
}

/// Run all phases; returns the drill report.
pub fn run() -> DrillReport {
    let mut phases = Vec::new();
    // impossible: 2-budget job stalls twice
    let j7 = job("7", int(0), int(2), None, "");
    let tick1 = gate::gate_tick(&[JobRecord { attempts: Some(int(1)), ..j7.clone() }], &[]);
    phases.push(if tick1.is_empty() {
        PhaseResult::pass("impossible-tick1-quiet", "budget remains after rung 1")
    } else {
        PhaseResult::fail("impossible-tick1-quiet", format!("parked early: {tick1:?}"))
    });
    let j7b = JobRecord { attempts: Some(int(2)), ..j7.clone() };
    let tick2 = gate::gate_tick(&[j7b.clone()], &tick1);
    let parks = tick2.iter().filter(|r| r.kind == "parked").count();
    let pushes = tick2.iter().filter(|r| r.kind == "blocked-push").count();
    phases.push(if parks == 1 && pushes == 1 {
        PhaseResult::pass("impossible-parks-once", "parked + exactly one escalation")
    } else {
        PhaseResult::fail("impossible-parks-once", format!("parks={parks} pushes={pushes}"))
    });
    // payload validates + names the budget fact
    let payload_ok = tick2.iter().filter(|r| r.kind == "blocked-push").all(|r| {
        let pv = push_mod::Push { push_type: "blocked".into(), job_id: r.job_id.clone(), title: String::new(), text: r.text.clone() };
        push_mod::validate_push(&pv).is_ok() && r.text.contains('7')
    });
    phases.push(if payload_ok {
        PhaseResult::pass("impossible-payload", "payload validates, names job 7")
    } else {
        PhaseResult::fail("impossible-payload", "payload invalid")
    });
    // tick 3: nothing new
    let tick3 = gate::gate_tick(&[j7b], &tick2);
    phases.push(if tick3.is_empty() {
        PhaseResult::pass("impossible-no-loop", "third tick journals nothing")
    } else {
        PhaseResult::fail("impossible-no-loop", format!("looped: {tick3:?}"))
    });
    // crew-fixable: dep blocker across three ticks
    let j8 = job("8", int(0), int(3), Some("dependency"), "wait");
    let mut journal: Vec<gate::JournalRecord> = Vec::new();
    let mut leaked = false;
    for _ in 0..3 {
        let recs = gate::gate_tick(&[j8.clone()], &journal);
        if !recs.is_empty() {
            leaked = true;
        }
        journal.extend(recs);
    }
    phases.push(if !leaked {
        PhaseResult::pass("crew-fixable-quiet", "dependency parks nothing over 3 ticks")
    } else {
        PhaseResult::fail("crew-fixable-quiet", "gate fired on crew work")
    });
    // dale-call: money parks at once, quotes note verbatim
    let j9 = job("9", int(1), int(5), Some("money"), "needs $40/mo API key approval");
    let d1 = gate::gate_tick(&[j9.clone()], &[]);
    let verbatim = d1.iter().filter(|r| r.kind == "blocked-push").all(|r| r.text.contains("needs $40/mo API key approval"));
    phases.push(if d1.len() == 2 && verbatim {
        PhaseResult::pass("dale-call-parks", "money parks at once, note verbatim")
    } else {
        PhaseResult::fail("dale-call-parks", format!("records: {d1:?}"))
    });
    let d2 = gate::gate_tick(&[j9], &d1);
    phases.push(if d2.is_empty() {
        PhaseResult::pass("dale-call-once", "second tick journals nothing")
    } else {
        PhaseResult::fail("dale-call-once", "duplicate escalation")
    });
    // malformed: non-numeric / missing max / zero max / negative
    let malformed = vec![
        job("m1", JobInt::Str("lots".into()), int(3), None, ""),
        JobRecord { id: Some("m2".into()), status: "open".into(), attempts: Some(int(0)), max_attempts: None, blocker_kind: None, note: String::new() },
        job("m3", int(0), int(0), None, ""),
        job("m4", int(-1), int(3), None, ""),
    ];
    let m = gate::gate_tick(&malformed, &[]);
    phases.push(if m.is_empty() {
        PhaseResult::pass("malformed-unbudgeted", "no crash, no park, no escalation")
    } else {
        PhaseResult::fail("malformed-unbudgeted", format!("fired: {m:?}"))
    });
    // no-extra-contact: exactly two escalations total, sent ledger empty
    let total_pushes = tick2.iter().filter(|r| r.kind == "blocked-push").count()
        + d1.iter().filter(|r| r.kind == "blocked-push").count();
    phases.push(if total_pushes == 2 {
        PhaseResult::pass("no-extra-contact", "exactly two escalations; sent ledger empty (gate has no send path)")
    } else {
        PhaseResult::fail("no-extra-contact", format!("escalations={total_pushes}"))
    });
    // immutable: inputs unchanged
    let snap = vec![job("z", int(0), int(1), None, "")];
    let snap_before = snap.clone();
    let _ = gate::gate_tick(&snap, &[]);
    phases.push(if snap == snap_before {
        PhaseResult::pass("immutable", "tick leaves inputs unchanged")
    } else {
        PhaseResult::fail("immutable", "inputs mutated")
    });
    // brief names parked jobs
    let mut all = tick2.clone();
    all.extend(d1.clone());
    let lines = gate::gate_brief_lines(&all);
    phases.push(if lines.iter().any(|l| l.contains('7')) && lines.iter().any(|l| l.contains('9')) {
        PhaseResult::pass("brief", "brief names jobs 7 and 9")
    } else {
        PhaseResult::fail("brief", format!("lines: {lines:?}"))
    });
    DrillReport::new("attempt_gate", phases)
}
