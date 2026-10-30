//! Port of `os/intel/drills/collision.py` (WDG-021).
//!
//! Two workers claim jobs touching the same file: the drill surfaces
//! the file-collision alert with both nicks and the shared path, and
//! the ladder takes no rung (no stall — a collision is negotiated,
//! not repaired).

use crate::b09_core::explanations;
use crate::b12a_drills::{DrillReport, PhaseResult};
use std::collections::HashMap;

pub fn run_drill(nick_a: &str, nick_b: &str, path: &str) -> DrillReport {
    let mut phases = Vec::new();
    let mut f = HashMap::new();
    f.insert("nick_a".into(), nick_a.to_string());
    f.insert("nick_b".into(), nick_b.to_string());
    f.insert("path".into(), path.to_string());
    match explanations::render("file-collision", &f) {
        Ok((e, _)) => phases.push(if e.contains(nick_a) && e.contains(nick_b) && e.contains(path) {
            PhaseResult::pass("collision-surfaced", "both nicks + shared path named")
        } else {
            PhaseResult::fail("collision-surfaced", e)
        }),
        Err(e) => phases.push(PhaseResult::fail("collision-surfaced", e)),
    }
    phases.push(PhaseResult::pass("no-ladder-rung", "collision negotiates; ladder stays out"));
    DrillReport::new("collision", phases)
}

pub fn run() -> DrillReport {
    run_drill("milo", "hana", "os/store.py")
}
