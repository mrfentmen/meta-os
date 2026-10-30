//! Port of `os/intel/drills/__init__.py` — drills package marker.

pub const PACKAGE: &str = "drills";

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
