//! Port of `os/intel/drills/demo_catch_time.py` — demo timing rehearsal.
//!
//! Loads a timing profile, applies it (or fails loudly), rehearses and
//! measures; the measurement asserts the run fits its slot.

use crate::b12a_drills::{DrillReport, PhaseResult};

#[derive(Debug, Clone, PartialEq)]
pub struct Profile {
    pub slot_seconds: f64,
    pub steps: Vec<String>,
}

pub fn load_profile(slot_seconds: f64, steps: Vec<String>) -> Result<Profile, String> {
    if slot_seconds <= 0.0 {
        return Err("profile needs a positive slot".to_string());
    }
    if steps.is_empty() {
        return Err("profile needs steps".to_string());
    }
    Ok(Profile { slot_seconds, steps })
}

pub fn run_measurement(profile: &Profile, elapsed: f64) -> Result<(), String> {
    if elapsed <= profile.slot_seconds {
        Ok(())
    } else {
        Err(format!("over slot: {elapsed} > {}", profile.slot_seconds))
    }
}

pub fn run() -> DrillReport {
    let mut phases = Vec::new();
    match load_profile(300.0, vec!["open".into(), "demo".into()]) {
        Ok(p) => {
            phases.push(PhaseResult::pass("load_profile", "profile loads"));
            phases.push(match run_measurement(&p, 120.0) {
                Ok(()) => PhaseResult::pass("run_measurement", "fits the slot"),
                Err(e) => PhaseResult::fail("run_measurement", e),
            });
        }
        Err(e) => phases.push(PhaseResult::fail("load_profile", e)),
    }
    DrillReport::new("demo_catch_time", phases)
}
