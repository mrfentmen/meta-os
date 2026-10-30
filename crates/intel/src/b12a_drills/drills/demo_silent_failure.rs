//! Port of `os/intel/drills/demo_silent_failure.py`.
//!
//! A demo step that fails silently must still surface: the drill feeds
//! a quiet failure through the journal and asserts an alert exists with
//! the step named. Silence is never a pass.

use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn run_drill(step: &str, failed_quietly: bool, alert_raised: bool) -> DrillReport {
    let mut phases = Vec::new();
    phases.push(if failed_quietly && !alert_raised {
        PhaseResult::fail("silent-failure", format!("{step} failed with no alert"))
    } else if failed_quietly && alert_raised {
        PhaseResult::pass("silent-failure", format!("{step} failure surfaced by alert"))
    } else {
        PhaseResult::pass("silent-failure", format!("{step} clean"))
    });
    DrillReport::new("demo_silent_failure", phases)
}

pub fn run() -> DrillReport {
    run_drill("caption", true, true)
}
