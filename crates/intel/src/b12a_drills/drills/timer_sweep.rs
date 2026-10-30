//! Port of `os/intel/drills/timer_sweep.py` — timer sweep drill.
//!
//! Sweeps expired timers: due timers fire exactly once, future timers
//! stay quiet, malformed timer specs are skipped without crashing.

use crate::b12a_drills::{DrillReport, PhaseResult};

#[derive(Debug, Clone)]
pub struct Timer {
    pub id: String,
    pub due_at: Option<i64>,
}

pub fn check(timers: &[Timer], now: i64) -> (Vec<String>, Vec<String>) {
    let mut fired = Vec::new();
    let mut skipped = Vec::new();
    for t in timers {
        match t.due_at {
            None => skipped.push(t.id.clone()),
            Some(due) if due <= now => fired.push(t.id.clone()),
            Some(_) => (),
        }
    }
    (fired, skipped)
}

pub fn run() -> DrillReport {
    let timers = vec![
        Timer { id: "due".into(), due_at: Some(5) },
        Timer { id: "future".into(), due_at: Some(99) },
        Timer { id: "bad".into(), due_at: None },
    ];
    let (fired, skipped) = check(&timers, 10);
    DrillReport::new(
        "timer_sweep",
        vec![
            if fired == vec!["due".to_string()] {
                PhaseResult::pass("check-fired", "due fires exactly once")
            } else {
                PhaseResult::fail("check-fired", format!("{fired:?}"))
            },
            if skipped == vec!["bad".to_string()] {
                PhaseResult::pass("check-skipped", "malformed skipped, not crashed")
            } else {
                PhaseResult::fail("check-skipped", format!("{skipped:?}"))
            },
        ],
    )
}
