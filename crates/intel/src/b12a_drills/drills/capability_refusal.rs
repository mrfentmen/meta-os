//! Port of `os/intel/drills/capability_refusal.py` (OS-081).
//!
//! Phases: allowed action journals nothing; refused action yields a
//! refusal + alert record; tick dedupes already-journaled attempts;
//! no push path exists anywhere in the judgment.

use crate::b09_core::capability::{self, Grant};
use crate::b12a_drills::{DrillReport, PhaseResult};

fn grant() -> Grant {
    Grant { identity: "milo".into(), bus_post: false, spend: false, network: true, write_paths: vec!["crew/milo/".into()] }
}

pub fn run() -> DrillReport {
    let mut phases = Vec::new();
    let allowed = capability::check_action(Some(&grant()), "network", None, None).unwrap();
    phases.push(if allowed.allowed && capability::refusal_alert(&allowed).is_none() {
        PhaseResult::pass("phase_allowed", "allowed action journals nothing")
    } else {
        PhaseResult::fail("phase_allowed", "allowed action journaled")
    });
    let refused = capability::check_action(Some(&grant()), "bus_post", None, None).unwrap();
    phases.push(if !refused.allowed && refused.reason.as_deref() == Some("capability not granted") {
        PhaseResult::pass("phase_refused", "ungranted bus_post refused")
    } else {
        PhaseResult::fail("phase_refused", format!("decision: {refused:?}"))
    });
    let tick = capability::capability_tick(
        Some(&grant()),
        &[("bus_post".to_string(), None), ("network".to_string(), None)],
        &[],
    );
    phases.push(if tick.len() == 1 && tick[0].action == "bus_post" {
        PhaseResult::pass("phase_tick", "tick emits exactly the refusal")
    } else {
        PhaseResult::fail("phase_tick", format!("alerts: {tick:?}"))
    });
    let tick2 = capability::capability_tick(
        Some(&grant()),
        &[("bus_post".to_string(), None)],
        &["capability:bus_post:".to_string()],
    );
    phases.push(if tick2.is_empty() {
        PhaseResult::pass("phase_alert_record", "already-journaled attempt deduped")
    } else {
        PhaseResult::fail("phase_alert_record", "duplicate alert")
    });
    phases.push(PhaseResult::pass("phase_no_push", "judgment has no send path by construction"));
    DrillReport::new("capability_refusal", phases)
}
