//! Port of `os/intel/abrun.py` — A/B run comparison.
//!
//! Attributes stalls to arms, drops malformed runs, and renders
//! measurement records for the comparison table.

use crate::b12a_drills::{DrillReport, PhaseResult};

#[derive(Debug, Clone, PartialEq)]
pub struct Run {
    pub arm: String,
    pub stall_minutes: Option<f64>,
}

pub fn attribute_stall(run: &Run) -> Option<&str> {
    run.stall_minutes.and(Some(run.arm.as_str())).filter(|_| run.stall_minutes.is_some_and(|m| m >= 0.0))
}

pub fn measurement_records(runs: &[Run]) -> Vec<String> {
    runs
        .iter()
        .filter_map(|r| attribute_stall(r).map(|a| format!("{}: {:?}", a, r.stall_minutes)))
        .collect()
}

pub fn run_comparison(a: &[Run], b: &[Run]) -> (Vec<String>, Vec<String>) {
    (measurement_records(a), measurement_records(b))
}

pub fn run() -> DrillReport {
    let a = vec![Run { arm: "control".into(), stall_minutes: Some(2.0) }];
    let b = vec![Run { arm: "variant".into(), stall_minutes: None }];
    let (ra, rb) = run_comparison(&a, &b);
    DrillReport::new(
        "abrun",
        vec![if ra.len() == 1 && rb.is_empty() {
            PhaseResult::pass("clean-run", "malformed variant run dropped")
        } else {
            PhaseResult::fail("clean-run", "records wrong")
        }],
    )
}
