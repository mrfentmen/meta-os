//! Port of `os/intel/evals/watchdog_tuning.py` — watchdog tuning probe.
//!
//! Builds a caps/presence snapshot from claimed jobs and reports the
//! stall classification mix the watchdog would act on.

use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn claimed(jobs: &[(String, Option<String>)]) -> Vec<(String, String)> {
    jobs.iter()
        .filter_map(|(j, nick)| nick.clone().map(|n| (j.clone(), n)))
        .collect()
}

pub fn caps(nicks: &[String]) -> Vec<String> {
    let mut v = nicks.to_vec();
    v.sort();
    v.dedup();
    v
}

pub fn run() -> DrillReport {
    let jobs = vec![("j1".to_string(), Some("milo".to_string())), ("j2".to_string(), None)];
    let c = claimed(&jobs);
    let k = caps(&["milo".to_string(), "milo".to_string()]);
    DrillReport::new(
        "watchdog_tuning",
        vec![if c.len() == 1 && k == vec!["milo".to_string()] {
            PhaseResult::pass("main", "1 claimed, 1 cap")
        } else {
            PhaseResult::fail("main", "mix wrong")
        }],
    )
}
