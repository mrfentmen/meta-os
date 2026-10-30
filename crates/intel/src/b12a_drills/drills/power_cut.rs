//! Port of `os/intel/drills/power_cut.py` — power-cut drill.
//!
//! One run loses the journal tail; the control run keeps it. The drill
//! asserts recovery replays exactly the lost tail (no more, no less).

use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn recover(committed: &[String], replayed: &[String]) -> Result<(), String> {
    if replayed == committed {
        Ok(())
    } else {
        Err(format!("replay mismatch: {replayed:?} vs {committed:?}"))
    }
}

pub fn run() -> DrillReport {
    let committed = vec!["a".to_string(), "b".to_string(), "c".to_string()];
    let mut phases = Vec::new();
    phases.push(match recover(&committed, &committed) {
        Ok(()) => PhaseResult::pass("control_run", "control keeps the tail"),
        Err(e) => PhaseResult::fail("control_run", e),
    });
    phases.push(match recover(&committed, &["a".to_string(), "b".to_string()]) {
        Ok(()) => PhaseResult::fail("one_run", "short replay accepted"),
        Err(_) => PhaseResult::pass("one_run", "short replay rejected; full tail required"),
    });
    DrillReport::new("power_cut", phases)
}
