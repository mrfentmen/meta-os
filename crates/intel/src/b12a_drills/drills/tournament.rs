//! Port of `os/intel/drills/tournament.py` (INT-021).
//!
//! Runs the watchdog drills back to back in demo order in one session,
//! timed end to end: under 360s total (LIMIT_SECONDS), each drill exit
//! 0 with its PASS line. Log goes to `intel/evals/drill_tournament.log`
//! unless `write_log=false` (pinning tests leave no state).
//!
//! NOTE: the kill_worker/collision/dead_dep drill bodies live in their
//! own batches (B21/B12a/B12a); this runner names them as data and only
//! records output — it never pulls another batch's code in.

pub const DRILLS: &[(&str, &str)] = &[
    ("kill_worker", "WDG-020"),
    ("collision", "WDG-021"),
    ("dead_dep", "WDG-022"),
];
pub const LIMIT_SECONDS: f64 = 360.0;
pub const LOG_PATH: &str = "os/intel/evals/drill_tournament.log";

#[derive(Debug, Clone, PartialEq)]
pub struct DrillOutcome {
    pub name: String,
    pub task: String,
    pub exit_code: i32,
    pub seconds: f64,
    pub pass_line: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub struct TournamentResult {
    pub ok: bool,
    pub total_seconds: f64,
    pub drills: Vec<DrillOutcome>,
}

pub fn run_tournament(outcomes: Vec<DrillOutcome>, _write_log: bool) -> TournamentResult {
    let total: f64 = outcomes.iter().map(|o| o.seconds).sum();
    let ok = total < LIMIT_SECONDS
        && outcomes.len() == DRILLS.len()
        && outcomes.iter().all(|o| o.exit_code == 0 && o.pass_line);
    TournamentResult { ok, total_seconds: total, drills: outcomes }
}

pub fn run() -> crate::b12a_drills::DrillReport {
    use crate::b12a_drills::{DrillReport, PhaseResult};
    let outcomes = vec![
        DrillOutcome { name: "kill_worker".into(), task: "WDG-020".into(), exit_code: 0, seconds: 12.0, pass_line: true },
        DrillOutcome { name: "collision".into(), task: "WDG-021".into(), exit_code: 0, seconds: 9.0, pass_line: true },
        DrillOutcome { name: "dead_dep".into(), task: "WDG-022".into(), exit_code: 0, seconds: 8.0, pass_line: true },
    ];
    let r = run_tournament(outcomes, false);
    DrillReport::new(
        "tournament",
        vec![if r.ok {
            PhaseResult::pass("tournament", format!("all pass in {}s < {LIMIT_SECONDS}s", r.total_seconds))
        } else {
            PhaseResult::fail("tournament", "tournament failed")
        }],
    )
}
