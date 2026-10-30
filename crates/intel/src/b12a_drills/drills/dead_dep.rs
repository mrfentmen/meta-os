//! Port of `os/intel/drills/dead_dep.py` (WDG-022).
//!
//! A job blocked on a dead dependency: block posts the dep-wait note,
//! unblock clears it, and the drill asserts the journal shows exactly
//! one block + one unblock with the dep named.

use crate::b12a_drills::{DrillReport, PhaseResult};

#[derive(Debug, Default)]
pub struct Journal {
    pub entries: Vec<String>,
}

pub fn block(j: &mut Journal, job: &str, dep: &str) {
    j.entries.push(format!("blocked {job} on {dep}"));
}

pub fn unblock(j: &mut Journal, job: &str, dep: &str) {
    j.entries.push(format!("unblocked {job} from {dep}"));
}

pub fn run_drill(job: &str, dep: &str) -> DrillReport {
    let mut phases = Vec::new();
    let mut j = Journal::default();
    block(&mut j, job, dep);
    unblock(&mut j, job, dep);
    phases.push(if j.entries == vec![format!("blocked {job} on {dep}"), format!("unblocked {job} from {dep}")] {
        PhaseResult::pass("block-unblock", "exactly one block + one unblock, dep named")
    } else {
        PhaseResult::fail("block-unblock", format!("{:?}", j.entries))
    });
    DrillReport::new("dead_dep", phases)
}

pub fn run() -> DrillReport {
    run_drill("j1", "dep-A")
}
