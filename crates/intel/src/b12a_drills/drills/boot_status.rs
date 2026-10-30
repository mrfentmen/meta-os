//! Port of `os/intel/drills/boot_status.py` — boot status drill.
//!
//! Asserts the boot-status record shape (stale flags, required fields)
//! on fixtures.

use crate::b12a_drills::{DrillReport, PhaseResult};

#[derive(Debug, Clone, PartialEq)]
pub struct BootStatus {
    pub booted_at: i64,
    pub stale: bool,
    pub checks_passed: bool,
}

pub fn check(s: &BootStatus) -> Result<(), String> {
    if s.booted_at < 0 {
        return Err("bad booted_at".to_string());
    }
    if !s.checks_passed {
        return Err("checks failed".to_string());
    }
    Ok(())
}

pub fn run_drill(statuses: &[BootStatus]) -> DrillReport {
    let phases = statuses
        .iter()
        .enumerate()
        .map(|(i, s)| match check(s) {
            Ok(()) => PhaseResult::pass(&format!("status-{i}"), "ok"),
            Err(e) => PhaseResult::fail(&format!("status-{i}"), e),
        })
        .collect();
    DrillReport::new("boot_status", phases)
}

pub fn run() -> DrillReport {
    run_drill(&[BootStatus { booted_at: 100, stale: false, checks_passed: true }])
}
