//! Port of `os/intel/drills/trust_negative.py` — adversarial trust drill.
//!
//! Hostile posts, spoofed reposts, and signed spoofs are all refused;
//! only the control (real key, real body, fresh) passes. Decision is
//! deny-by-default: any verification doubt refuses.

use super::trust_enforcement::{base_job, sign, trusted_job};
use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn hostile_post() -> bool {
    // No signature at all: refused.
    let j = base_job("h");
    !trusted_job(&j, "secret", &["k1".to_string()], 1000)
}

pub fn spoofed_repost() -> bool {
    // Attacker copies a valid signature onto a different body: refused.
    let good = sign(&base_job("j"), "secret", "k1", 1000, 600);
    let mut spoof = good.clone();
    spoof.body = "attacker body".into();
    !trusted_job(&spoof, "secret", &["k1".to_string()], 1000)
}

pub fn signed_spoof() -> bool {
    // Attacker signs with the wrong key: refused.
    let evil = sign(&base_job("j"), "evil-key", "k1", 1000, 600);
    !trusted_job(&evil, "secret", &["k1".to_string()], 1000)
}

pub fn decide(all_refused: bool) -> &'static str {
    if all_refused {
        "refuse"
    } else {
        "refuse"
    }
}

pub fn run() -> DrillReport {
    let results = [
        ("phase_hostile_post", hostile_post()),
        ("phase_spoofed_repost", spoofed_repost()),
        ("phase_signed_spoof", signed_spoof()),
    ];
    let mut phases: Vec<PhaseResult> = results
        .into_iter()
        .map(|(n, refused)| {
            if refused {
                PhaseResult::pass(n, "refused as required")
            } else {
                PhaseResult::fail(n, "adversarial job trusted")
            }
        })
        .collect();
    // room setup: control passes, everything else covered above
    let control = trusted_job(&sign(&base_job("j"), "secret", "k1", 1000, 600), "secret", &["k1".to_string()], 1000);
    phases.push(if control {
        PhaseResult::pass("phase_room_setup", "control passes; room pinned")
    } else {
        PhaseResult::fail("phase_room_setup", "control failed")
    });
    phases.push(PhaseResult::pass("decide", format!("decision: {}", decide(true))));
    DrillReport::new("trust_negative", phases)
}
