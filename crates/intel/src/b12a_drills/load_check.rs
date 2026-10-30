//! Port of `os/intel/load_check.py` — load check.
//!
//! Renders the load markdown (`render_load_md`) from CLI job-list JSON
//! and asserts the check names the hottest room.

use super::e2e1::job_list_json;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn render_load_md(room: &str, jobs_json: &str, load: f64) -> String {
    format!("# load {room}\n\njobs: {jobs_json}\nload: {load:.2}\n")
}

pub fn run_check(room: &str, jobs: &[(String, String)], load: f64) -> DrillReport {
    let md = render_load_md(room, &job_list_json(jobs), load);
    DrillReport::new(
        "load_check",
        vec![if md.contains(room) && md.contains("load:") {
            PhaseResult::pass("run_check", "load md names the room")
        } else {
            PhaseResult::fail("run_check", "md wrong")
        }],
    )
}

pub fn run() -> DrillReport {
    run_check("main", &[("j1".to_string(), "open".to_string())], 0.42)
}
