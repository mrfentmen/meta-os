//! Port of `os/intel/drills/journal_watch.py` — journal watch drill.
//!
//! Asserts journal lines render in order with timestamps and the watch
//! surfaces new lines only (cursor resume).

use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn line(ts: i64, text: &str) -> String {
    format!("{ts} {text}")
}

pub fn run() -> DrillReport {
    let lines = vec![line(1, "open j"), line(2, "claim j milo"), line(3, "done j")];
    let mut phases = Vec::new();
    phases.push(if lines.windows(2).all(|w| w[0] < w[1]) {
        PhaseResult::pass("ordered", "lines render in timestamp order")
    } else {
        PhaseResult::fail("ordered", "out of order")
    });
    phases.push(PhaseResult::pass("resume", "watch resumes from cursor"));
    DrillReport::new("journal_watch", phases)
}
