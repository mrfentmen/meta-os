//! Port of `os/intel/boot_selfcheck.py` — boot self-check runner.
//!
//! Runs the seeded fixture check list; any failure names its check.

use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn seeded_fixture() -> Vec<(&'static str, bool)> {
    vec![("config", true), ("keys", true), ("journal", true)]
}

pub fn run_self_check(fixture: &[(&str, bool)]) -> DrillReport {
    DrillReport::new(
        "boot_selfcheck",
        fixture
            .iter()
            .map(|(n, ok)| {
                if *ok {
                    PhaseResult::pass(n, "ok")
                } else {
                    PhaseResult::fail(n, "self-check failed")
                }
            })
            .collect(),
    )
}

pub fn run() -> DrillReport {
    run_self_check(&seeded_fixture())
}
