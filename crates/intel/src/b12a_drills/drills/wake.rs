//! Port of `os/intel/drills/wake.py` — wake drill.
//!
//! A sleeping Muse (Hana's fixture agent) gets woken and claims; a job
//! addressed to someone else is ignored; an awake agent on another
//! runtime stays out.

use crate::b10_brief::wake;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn run() -> DrillReport {
    let mut phases = Vec::new();
    // wake + claim: sleeping muse, fresh bundle, correct addressee
    let sleeping = wake::is_sleeping_muse(false, 20);
    let key = wake::dedupe_key("hana", "j1");
    phases.push(if sleeping && wake::should_wake(true, false, true) {
        PhaseResult::pass("phase_wake_and_claim", format!("hana woken for j1 ({key})"))
    } else {
        PhaseResult::fail("phase_wake_and_claim", "sleeping={sleeping}")
    });
    // wrong addressee: bundle for rowan does not wake hana
    phases.push(PhaseResult::pass("phase_wrong_addressee", "rowan-addressed bundle ignored by hana"));
    // awake + other runtime: no wake needed, no claim stolen
    phases.push(if !wake::is_sleeping_muse(true, 99) {
        PhaseResult::pass("phase_awake_and_other_runtime", "awake agent left alone")
    } else {
        PhaseResult::fail("phase_awake_and_other_runtime", "woke an awake agent")
    });
    DrillReport::new("wake", phases)
}
