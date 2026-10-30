//! Port of `os/intel/e2e2.py` — e2e loop, scenario two (claim flow).

use super::e2e1::{job_list_json, section_lines};
use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn run_loop() -> DrillReport {
    let jobs = vec![("j1".to_string(), "claimed".to_string()), ("j2".to_string(), "open".to_string())];
    let j = job_list_json(&jobs);
    let lines = section_lines("e2e2-claim", &j);
    DrillReport::new(
        "e2e2",
        vec![if lines[1].contains("claimed") {
            PhaseResult::pass("run_loop", "claim flow renders")
        } else {
            PhaseResult::fail("run_loop", "claim missing")
        }],
    )
}

pub fn run() -> DrillReport {
    run_loop()
}
