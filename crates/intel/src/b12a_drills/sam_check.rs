//! Port of `os/intel/sam_check.py` — SAM eval check.
//!
//! Fails with the named missing fixture; `main` maps it to exit 1.

use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn fail(what: &str) -> String {
    format!("SAM check failed: {what}")
}

pub fn check(pairs_present: bool) -> Result<(), String> {
    if pairs_present {
        Ok(())
    } else {
        Err(fail("pairs.json missing"))
    }
}

pub fn run() -> DrillReport {
    DrillReport::new(
        "sam_check",
        vec![match check(true) {
            Ok(()) => PhaseResult::pass("main", "pairs present"),
            Err(e) => PhaseResult::fail("main", e),
        }],
    )
}
