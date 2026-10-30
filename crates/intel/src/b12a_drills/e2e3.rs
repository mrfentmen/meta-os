//! Port of `os/intel/e2e3.py` — e2e loop, scenario three (done flow).

use super::e2e1::{job_list_json, section_lines};
use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn run_loop() -> DrillReport {
    let jobs = vec![("j1".to_string(), "done".to_string())];
    let j = job_list_json(&jobs);
    let lines = section_lines("e2e3-done", &j);
    DrillReport::new(
        "e2e3",
        vec![if lines[1].contains("done") {
            PhaseResult::pass("run_loop", "done flow renders")
        } else {
            PhaseResult::fail("run_loop", "done missing")
        }],
    )
}

pub fn run() -> DrillReport {
    run_loop()
}
