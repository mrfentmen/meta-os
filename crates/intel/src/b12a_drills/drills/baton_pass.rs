//! Port of `os/intel/drills/baton_pass.py` (OS-125).
//!
//! Phases: full pass preserves title/progress/files; no-progress baton
//! still passes with the `(none deposited)` marker; malformed stalls pass
//! nothing; idempotent re-pass is stable; no Dale contact.

use crate::b09_core::ladder::{Snapshot, Stall};
use crate::b10_brief::baton::{self, BatonSpec};
use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn run() -> DrillReport {
    let mut phases = Vec::new();
    let full = BatonSpec { job_id: "j".into(), goal: "ship".into(), progress: "did half".into(), files: vec!["a.py".into()], steps: vec!["s1".into()], acceptance: vec!["tests pass".into()] };
    let text = baton::compose_baton(&full, "milo", "hana");
    phases.push(if text.contains("ship") && text.contains("did half") && text.contains("a.py") {
        PhaseResult::pass("phase_full_pass", "title/progress/files preserved")
    } else {
        PhaseResult::fail("phase_full_pass", text)
    });
    let empty = BatonSpec { job_id: "j".into(), goal: "g".into(), progress: String::new(), files: vec![], steps: vec![], acceptance: vec![] };
    phases.push(if baton::compose_baton(&empty, "m", "h").contains("(none deposited)") {
        PhaseResult::pass("phase_no_progress", "empty progress marked, still passes")
    } else {
        PhaseResult::fail("phase_no_progress", "marker missing")
    });
    let snap = Snapshot { registered: vec![], present: vec![], jobs: vec![] };
    phases.push(if crate::b09_core::ladder::ladder_action(&snap, &Stall { nick: None, job: Some("j".into()) }).is_none() {
        PhaseResult::pass("phase_malformed", "malformed stall passes nothing")
    } else {
        PhaseResult::fail("phase_malformed", "acted on malformed stall")
    });
    let t1 = baton::compose_baton(&full, "milo", "hana");
    phases.push(if t1 == baton::compose_baton(&full, "milo", "hana") {
        PhaseResult::pass("phase_idempotent_and_immutable", "re-pass stable")
    } else {
        PhaseResult::fail("phase_idempotent_and_immutable", "unstable")
    });
    phases.push(if !text.contains("push") && !text.contains("Dale") {
        PhaseResult::pass("phase_no_dale", "baton carries no contact path")
    } else {
        PhaseResult::fail("phase_no_dale", "contact leak")
    });
    DrillReport::new("baton_pass", phases)
}
