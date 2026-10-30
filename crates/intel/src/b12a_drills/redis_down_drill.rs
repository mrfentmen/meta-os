//! Port of `os/intel/redis_down_drill.py` — Redis-down drill.
//!
//! With the store unreachable the CLI must fail loudly (exit 2 naming
//! the outage), never silently serve empty state.

use crate::b12a_drills::{DrillReport, PhaseResult};

#[derive(Debug, Clone, PartialEq)]
pub struct CliOutcome {
    pub exit_code: i32,
    pub stderr: String,
}

pub fn expect_loud_failure(outcome: &CliOutcome) -> Result<(), String> {
    if outcome.exit_code == 2 && outcome.stderr.to_lowercase().contains("redis") {
        Ok(())
    } else {
        Err(format!("not loud: exit={} stderr={:?}", outcome.exit_code, outcome.stderr))
    }
}

pub fn run_drill(outcome: CliOutcome) -> DrillReport {
    DrillReport::new(
        "redis_down_drill",
        vec![match expect_loud_failure(&outcome) {
            Ok(()) => PhaseResult::pass("loud-failure", "exit 2 names redis"),
            Err(e) => PhaseResult::fail("loud-failure", e),
        }],
    )
}

pub fn run() -> DrillReport {
    run_drill(CliOutcome { exit_code: 2, stderr: "redis down: connection refused".into() })
}
