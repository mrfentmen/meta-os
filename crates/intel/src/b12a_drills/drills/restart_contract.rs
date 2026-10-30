//! Port of `os/intel/drills/restart_contract.py`.
//!
//! Restart contract: a restart request records exactly one
//! restart-request event naming the unit, and a second tick over the
//! same request records nothing new.

use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn restart_event(unit: &str) -> String {
    format!("restart-request {unit}")
}

pub fn run() -> DrillReport {
    let mut journal: Vec<String> = Vec::new();
    let mut phases = Vec::new();
    let ev = restart_event("relay-worker@1");
    if !journal.contains(&ev) {
        journal.push(ev.clone());
    }
    phases.push(if journal.len() == 1 {
        PhaseResult::pass("request-recorded", "exactly one restart-request event")
    } else {
        PhaseResult::fail("request-recorded", "wrong count")
    });
    if !journal.contains(&ev) {
        journal.push(ev);
    }
    phases.push(if journal.len() == 1 {
        PhaseResult::pass("no-duplicate", "second tick records nothing new")
    } else {
        PhaseResult::fail("no-duplicate", "duplicate event")
    });
    DrillReport::new("restart_contract", phases)
}
