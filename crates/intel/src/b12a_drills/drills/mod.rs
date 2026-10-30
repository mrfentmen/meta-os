//! Port of `os/intel/drills/__init__.py` — watchdog drill
//! harnesses (Milo lane, WDG-020/021/022).
//!
//! Each drill runs unattended on fixtures: no network, no
//! Redis, no bus posts. The watchdog itself is pure snapshot
//! evaluation, so a drill stages a snapshot the way a real
//! worker would stage it, runs a tick, and asserts the
//! outcome.

pub const PACKAGE: &str = "drills";

/// One drill run: the phase report plus the exact lines the
/// drill's main() prints (each source's print format differs;
/// the lines are the drill's own, built alongside the phases).
#[derive(Debug, Clone, PartialEq)]
pub struct DrillOutcome {
    pub report: crate::b12a_drills::DrillReport,
    pub lines: Vec<String>,
}

pub mod ab_run;
pub mod attempt_gate;
pub mod baton_pass;
pub mod boot_selfcheck;
pub mod boot_status;
pub mod capability_refusal;
pub mod collision;
pub mod dead_dep;
pub mod demo_catch_time;
pub mod demo_silent_failure;
pub mod demo_thresholds_dropin;
pub mod journal_watch;
pub mod power_cut;
pub mod restart_contract;
pub mod self_repair_ladder;
pub mod soak_review;
pub mod timer_sweep;
pub mod tournament;
pub mod trust_enforcement;
pub mod trust_negative;
pub mod wake;
