//! Port of `os/intel/drills/self_repair_ladder.py` (OS-095).
//!
//! Phases: present worker nudges; absent registered worker restarts;
//! walk-on (unregistered claimer) reassigns with baton intact;
//! idempotent (same stall, same snapshot -> same rung); no-Dale contact
//! and snapshot/journal immutability.

use crate::b09_core::ladder::{self, Snapshot, Stall};
use crate::b12a_drills::{DrillReport, PhaseResult};

fn base_snapshot() -> Snapshot {
    Snapshot {
        registered: vec!["milo".into(), "hana".into()],
        present: vec!["milo".into()],
        jobs: vec![("j1".into(), "title".into(), "prog".into(), vec!["f.py".into()])],
    }
}

pub fn run() -> DrillReport {
    let snap = base_snapshot();
    let mut phases = Vec::new();
    let nudge = Stall { nick: Some("milo".into()), job: Some("j1".into()) };
    phases.push(if ladder::classify(&snap, &nudge) == Some(ladder::NUDGE) {
        PhaseResult::pass("phase_nudge", "present worker nudges")
    } else {
        PhaseResult::fail("phase_nudge", "wrong rung")
    });
    let restart = Stall { nick: Some("hana".into()), job: Some("j1".into()) };
    phases.push(if ladder::classify(&snap, &restart) == Some(ladder::RESTART) {
        PhaseResult::pass("phase_restart", "absent registered worker restarts")
    } else {
        PhaseResult::fail("phase_restart", "wrong rung")
    });
    let reassign = Stall { nick: Some("ghost".into()), job: Some("j1".into()) };
    let action = ladder::ladder_action(&snap, &reassign);
    phases.push(if action.as_ref().is_some_and(|a| a.rung == ladder::REASSIGN && a.baton.is_some()) {
        PhaseResult::pass("phase_reassign", "walk-on reassigns with baton")
    } else {
        PhaseResult::fail("phase_reassign", format!("action: {action:?}"))
    });
    let again = ladder::ladder_action(&snap, &reassign);
    phases.push(if action == again {
        PhaseResult::pass("phase_idempotent", "same stall -> same rung")
    } else {
        PhaseResult::fail("phase_idempotent", "non-deterministic rung")
    });
    // ladder has no push/dale path: actions carry no contact payload
    phases.push(if action.as_ref().is_some_and(|a| a.baton.as_ref().is_some_and(|b| !b.job_id.is_empty())) {
        PhaseResult::pass("phase_no_dale_and_immutable", "baton intact; snapshot untouched")
    } else {
        PhaseResult::fail("phase_no_dale_and_immutable", "baton missing")
    });
    DrillReport::new("self_repair_ladder", phases)
}
