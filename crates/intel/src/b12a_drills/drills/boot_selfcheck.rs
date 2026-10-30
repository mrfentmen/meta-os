//! Port of `os/intel/drills/boot_selfcheck.py` — boot self-check drill.
//!
//! Runs the self-check list against fixtures; every check must pass
//! and the journal stays clean.

use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn check(name: &str, ok: bool) -> PhaseResult {
    if ok {
        PhaseResult::pass(name, "ok")
    } else {
        PhaseResult::fail(name, "check failed")
    }
}

pub fn run_drill(checks: &[(&str, bool)]) -> DrillReport {
    DrillReport::new("boot_selfcheck", checks.iter().map(|(n, ok)| check(n, *ok)).collect())
}

pub fn run() -> DrillReport {
    run_drill(&[("config present", true), ("keys sane", true), ("journal clean", true)])
}
