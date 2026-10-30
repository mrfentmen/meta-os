//! Port of `os/intel/drills/soak_review.py` (drill).
//!
//! Reviews a soak journal: no failures and no coverage gaps pass;
//! anything else names the offending lines.

use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn is_failure(line: &str) -> bool {
    line.contains("FAIL")
}

pub fn is_cover(line: &str) -> bool {
    line.contains("cover:")
}

pub fn check(journal: &[String]) -> Result<(), String> {
    let bad: Vec<&String> = journal.iter().filter(|l| is_failure(l)).collect();
    if !bad.is_empty() {
        return Err(format!("failures: {}", bad.len()));
    }
    if !journal.iter().any(|l| is_cover(l)) {
        return Err("no coverage lines".to_string());
    }
    Ok(())
}

pub fn clean_journal() -> Vec<String> {
    vec!["cover: a".into(), "ok a".into(), "cover: b".into(), "ok b".into()]
}

pub fn run() -> DrillReport {
    DrillReport::new(
        "soak_review",
        vec![match check(&clean_journal()) {
            Ok(()) => PhaseResult::pass("check", "clean journal passes"),
            Err(e) => PhaseResult::fail("check", e),
        }],
    )
}
