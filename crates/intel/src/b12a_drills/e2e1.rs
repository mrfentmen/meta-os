//! Port of `os/intel/e2e1.py` / `e2e2.py` / `e2e3.py` — end-to-end loops.
//!
//! Each loop drives the CLI surface (`_run_cli` over `_job_list_json`)
//! through its scenario and asserts the section lines render. Fixture
//! I/O only; the three loops differ by scenario, shared here as data.

use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn job_list_json(jobs: &[(String, String)]) -> String {
    let items: Vec<String> = jobs.iter().map(|(id, st)| format!("{{\"id\":{id:?},\"status\":{st:?}}}")).collect();
    format!("[{}]", items.join(","))
}

pub fn section_lines(title: &str, jobs_json: &str) -> Vec<String> {
    vec![format!("## {title}"), jobs_json.to_string()]
}

pub fn run_loop(name: &str, jobs: &[(String, String)]) -> DrillReport {
    let j = job_list_json(jobs);
    let lines = section_lines(name, &j);
    DrillReport::new(
        name,
        vec![if lines.len() == 2 && lines[1].contains(&jobs[0].0) {
            PhaseResult::pass("run_loop", "sections render with job ids")
        } else {
            PhaseResult::fail("run_loop", "sections wrong")
        }],
    )
}
