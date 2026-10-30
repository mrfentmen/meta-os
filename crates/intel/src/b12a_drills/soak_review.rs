//! Port of `os/intel/soak_review.py` — soak journal review.
//!
//! `review_journal` splits failures from coverage; `soak_brief_lines`
//! renders the brief section. A soak with failures is never green.

use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn is_failure(line: &str) -> bool {
    line.contains("FAIL")
}

pub fn is_cover(line: &str) -> bool {
    line.contains("cover:")
}

pub fn review_journal(lines: &[String]) -> (Vec<String>, Vec<String>) {
    (lines.iter().filter(|l| is_failure(l)).cloned().collect(),
     lines.iter().filter(|l| is_cover(l)).cloned().collect())
}

pub fn soak_brief_lines(failures: &[String], cover: &[String]) -> Vec<String> {
    vec![
        format!("soak: {} failures, {} covered", failures.len(), cover.len()),
    ]
}

pub fn run() -> DrillReport {
    let lines = vec!["cover: a".to_string(), "ok".to_string()];
    let (f, c) = review_journal(&lines);
    DrillReport::new(
        "soak_review",
        vec![if f.is_empty() && !c.is_empty() {
            PhaseResult::pass("review", "no failures, coverage present")
        } else {
            PhaseResult::fail("review", format!("failures: {f:?}"))
        }],
    )
}
