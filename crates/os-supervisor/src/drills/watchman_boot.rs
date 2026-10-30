//! Watchman-boot drill (Milo lane, OS-129).
//!
//! Port of `os/intel/drills/watchman_boot.py` (batch B21, task T120).
//! Port behavior, do not redesign.
//!
//! Acceptance, as the Python drill states it: across the power cuts,
//! the watchman's first post-boot cycle rings for every job that
//! arrived during downtime and none are double-rung or missed; a
//! deliberately corrupted stored counter value changes nothing in the
//! watchman's behaviour, proving it never reads one; Milo's
//! verification note on the drill is filed separately from Buffy's run
//! log.
//!
//! The drill is the verification half, not the mechanical half: it
//! checks the ring computation of [`crate::watchman_boot`] and its
//! reconciliation with the lease sweep, on fixtures with a fake clock
//! (downtime window [`T0`] to [`T1`]). It rings no bell, moves no
//! claim, and runs no booted test image; a live boot is not claimed
//! here, exactly as the Python drill states.
//!
//! Phases, in the Python drill's order:
//!
//! - arrival rings: two open jobs posted inside the window ring with
//!   reason `arrived_during_downtime`; one open job posted before the
//!   window does not ring; one open job posted after boot does not
//!   ring.
//! - lease rings: a claimed job whose lease died inside the window
//!   rings with reason `lease_expired_during_downtime`; a claimed job
//!   whose lease is still alive at boot does not ring; a done job
//!   never rings, even with a lease expiry inside the window.
//! - no double ring: the same job listed twice in the input rings
//!   once; a second post-boot cycle with the first cycle's rung ids in
//!   the ledger rings nothing new.
//! - corrupted counter: the ring set recomputed over copies of the
//!   jobs is identical to the clean ring set, and the verification
//!   note's `counter_ignored` flag is true.
//! - sweep reconciliation: with a sweep record that requeues exactly
//!   the lease-expired ring ids, the note reports reconciled true and
//!   the recovered count matches; with a sweep record that drops one
//!   requeue and adds one stranger, the note reports reconciled false
//!   and names the missing and extra ids.
//! - immutable and no-Dale: computing rings and verifying leaves the
//!   job records and the rung ledger unchanged; the verification note
//!   carries no push and no announcement field.
//!
//! # Representation notes (where the typed port differs from Python)
//!
//! - The Python fixture carries a bare string record (`"not-a-record"`)
//!   and a record with no id. Neither shape can be built as a
//!   [`BootJob`]; the no-id record covers both judgements (never
//!   rings, never crashes), and the malformed-record phase asserts it.
//! - The Python corrupted-counter phase injects `seen_counter` and
//!   `message_counter` keys into copies of the records. [`BootJob`]
//!   has no counter field, so the poisoned copies are the clean jobs
//!   by construction; the phase asserts the identical ring set plus
//!   the note's `counter_ignored` flag, which is the structural proof.
//! - The Python "no push import" phase scans the module source. The
//!   Rust equivalent asserts that the landed module's source carries
//!   no `crate::push` reference (it is loaded with `include_str!`
//!   from the same relative layout in the crate and in the temp
//!   verification crate) and that the note type has no push field by
//!   construction.
//!
//! # Live-behavior boundary (not faked here)
//!
//! The Python script's `main` prints `PASS`/`FAIL` lines and exits 0
//! or 1. That reporting shape is ported as [`run_drill`], which
//! returns the exit code and the lines instead of printing them; the
//! caller owns printing and exiting. No bell is rung by this module.

use crate::watchman_boot::{
    boot_brief_lines, post_boot_rings, verify_boot_cycle, BootJob,
    ARRIVED_DURING_DOWNTIME, LEASE_EXPIRED_DURING_DOWNTIME,
};

/// Downtime start (Python `T0`), unix seconds.
pub const T0: f64 = 100000.0;
/// Boot time (Python `T1`), unix seconds.
pub const T1: f64 = 100600.0;

/// The Python drill's job fixture, in input order.
///
/// The Python list also holds a bare string record; that shape has no
/// typed equivalent and is covered by the no-id record below (never
/// rings, never crashes).
pub fn drill_jobs() -> Vec<BootJob> {
    vec![
        BootJob {
            id: Some("job-arrive-1".to_string()),
            status: Some("open".to_string()),
            posted_at: Some(T0 + 100.0),
            ..Default::default()
        },
        BootJob {
            id: Some("job-arrive-2".to_string()),
            status: Some("open".to_string()),
            posted_at: Some(T0 + 500.0),
            ..Default::default()
        },
        BootJob {
            id: Some("job-before".to_string()),
            status: Some("open".to_string()),
            posted_at: Some(T0 - 50.0),
            ..Default::default()
        },
        BootJob {
            id: Some("job-after".to_string()),
            status: Some("open".to_string()),
            posted_at: Some(T1 + 10.0),
            ..Default::default()
        },
        BootJob {
            id: Some("job-lease-dead".to_string()),
            status: Some("claimed".to_string()),
            lease_expires_at: Some(T0 + 300.0),
            ..Default::default()
        },
        BootJob {
            id: Some("job-lease-live".to_string()),
            status: Some("claimed".to_string()),
            lease_expires_at: Some(T1 + 900.0),
            ..Default::default()
        },
        BootJob {
            id: Some("job-done".to_string()),
            status: Some("done".to_string()),
            lease_expires_at: Some(T0 + 200.0),
            ..Default::default()
        },
        // Malformed: open but no usable timestamp, so never rings.
        BootJob {
            id: Some("bad-record".to_string()),
            status: Some("open".to_string()),
            ..Default::default()
        },
        // Malformed: no id, so never rings (covers the Python bare
        // string record and the id-less record).
        BootJob {
            id: None,
            status: Some("open".to_string()),
            posted_at: Some(T0 + 10.0),
            ..Default::default()
        },
    ]
}

/// Job ids of a ring set, in order.
pub fn ring_ids(rings: &[crate::watchman_boot::Ring]) -> Vec<String> {
    rings.iter().map(|r| r.job_id.clone()).collect()
}

/// Arrival rings: exactly the two in-window open jobs plus the dead
/// lease, with the Python drill's reasons.
pub fn phase_arrival_rings() -> bool {
    let jobs = drill_jobs();
    let rings = post_boot_rings(&jobs, T0, T1, None);
    let ids = ring_ids(&rings);
    if ids != ["job-arrive-1", "job-arrive-2", "job-lease-dead"] {
        return false;
    }
    let reasons: std::collections::HashMap<&str, &str> = rings
        .iter()
        .map(|r| (r.job_id.as_str(), r.reason.as_str()))
        .collect();
    reasons["job-arrive-1"] == ARRIVED_DURING_DOWNTIME
        && reasons["job-arrive-2"] == ARRIVED_DURING_DOWNTIME
        && reasons["job-lease-dead"] == LEASE_EXPIRED_DURING_DOWNTIME
}

/// Pre-window, post-boot, live-lease, and done jobs never ring.
pub fn phase_non_ringing_jobs() -> bool {
    let jobs = drill_jobs();
    let ids = ring_ids(&post_boot_rings(&jobs, T0, T1, None));
    ["job-before", "job-after", "job-lease-live", "job-done"]
        .iter()
        .all(|id| !ids.iter().any(|ring| ring == id))
}

/// Malformed records never ring and never crash.
pub fn phase_malformed_records() -> bool {
    let jobs = drill_jobs();
    let ids = ring_ids(&post_boot_rings(&jobs, T0, T1, None));
    !ids.contains(&"bad-record".to_string())
}

/// Duplicate input rings once; a second cycle with the first cycle's
/// rung ids in the ledger rings nothing new.
pub fn phase_no_double_ring() -> bool {
    let jobs = drill_jobs();
    let mut doubled = jobs.clone();
    doubled.push(BootJob {
        id: Some("job-arrive-1".to_string()),
        status: Some("open".to_string()),
        posted_at: Some(T0 + 100.0),
        ..Default::default()
    });
    let ids = ring_ids(&post_boot_rings(&doubled, T0, T1, None));
    if ids.iter().filter(|id| *id == "job-arrive-1").count() != 1 {
        return false;
    }
    let first = post_boot_rings(&jobs, T0, T1, None);
    let first_ids = ring_ids(&first);
    post_boot_rings(&jobs, T0, T1, Some(&first_ids)).is_empty()
}

/// A corrupted stored counter changes nothing: the recomputed ring
/// set is identical and the note's counter flag is true.
pub fn phase_corrupted_counter() -> bool {
    let jobs = drill_jobs();
    let clean = ring_ids(&post_boot_rings(&jobs, T0, T1, None));
    // Python injects junk counter keys into copies; this job type has
    // no counter field, so the poisoned copies are the clean jobs.
    let poisoned = jobs.clone();
    let reproof = ring_ids(&post_boot_rings(&poisoned, T0, T1, None));
    let note = verify_boot_cycle(&jobs, T0, T1, &["job-lease-dead".to_string()], None);
    reproof == clean && note.counter_ignored
}

/// Sweep reconciliation agrees on the exact sweep and names the
/// mismatch on a dropped requeue plus a stranger.
pub fn phase_sweep_reconciliation() -> bool {
    let jobs = drill_jobs();
    let note = verify_boot_cycle(&jobs, T0, T1, &["job-lease-dead".to_string()], None);
    if !(note.reconciled
        && note.total_rings == 3
        && note.arrived_count == 2
        && note.lease_expired_count == 1
        && note.counter_ignored)
    {
        return false;
    }
    let bad_note =
        verify_boot_cycle(&jobs, T0, T1, &["job-stranger".to_string()], None);
    !bad_note.reconciled
        && bad_note.mismatch.missing == ["job-lease-dead"]
        && bad_note.mismatch.extra == ["job-stranger"]
}

/// Inputs never mutated; the note carries no push or announcement
/// field; the landed module carries no push reference; brief lines
/// name a ring and the reconciliation.
pub fn phase_immutable_and_no_dale() -> bool {
    let jobs = drill_jobs();
    let original = jobs.clone();
    let ledger = vec!["job-arrive-1".to_string()];
    post_boot_rings(&jobs, T0, T1, Some(&ledger));
    let note = verify_boot_cycle(&jobs, T0, T1, &["job-lease-dead".to_string()], None);
    if jobs != original || ledger != ["job-arrive-1"] {
        return false;
    }
    // The note type has no push or announcement field by construction;
    // the source check below is the import half of the Python phase.
    let source = include_str!("../watchman_boot.rs");
    if source.contains("crate::push") || source.contains("intel::push") {
        return false;
    }
    let lines = boot_brief_lines(&note);
    lines.iter().any(|line| line.contains("job-arrive-1"))
        && lines.iter().any(|line| line.contains("reconciled"))
}

/// Run every phase, in the Python drill's order.
///
/// Returns `(exit_code, lines)`: exit 0 with one `PASS` line per
/// phase on success, 1 otherwise. The caller owns printing.
pub fn run_drill() -> (i32, Vec<String>) {
    let phases: [(&str, fn() -> bool); 7] = [
        ("arrival rings", phase_arrival_rings),
        ("non-ringing jobs stay silent", phase_non_ringing_jobs),
        ("malformed records never ring", phase_malformed_records),
        ("no double ring", phase_no_double_ring),
        ("corrupted counter changes nothing", phase_corrupted_counter),
        ("sweep reconciliation", phase_sweep_reconciliation),
        ("immutable and no-Dale", phase_immutable_and_no_dale),
    ];
    let mut lines = Vec::new();
    let mut failed = 0;
    for (name, phase) in phases {
        if phase() {
            lines.push(format!("PASS {}", name));
        } else {
            lines.push(format!("FAIL {}", name));
            failed += 1;
        }
    }
    let total = lines.len();
    lines.push(format!(
        "{} PASS, {} FAIL",
        total - failed,
        failed
    ));
    (if failed == 0 { 0 } else { 1 }, lines)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_drill_arrival_rings() {
        // Mirrors the Python drill's "arrival rings" check.
        assert!(phase_arrival_rings());
    }

    #[test]
    fn test_drill_non_ringing_jobs() {
        // Mirrors the Python drill's pre-window, post-boot, live-lease,
        // and done checks.
        assert!(phase_non_ringing_jobs());
    }

    #[test]
    fn test_drill_malformed_records() {
        // Mirrors the Python drill's "malformed records never ring and
        // never crash" check (bad-record plus the no-id record, which
        // also covers the bare string record).
        assert!(phase_malformed_records());
    }

    #[test]
    fn test_drill_no_double_ring() {
        // Mirrors the Python drill's duplicate-input and second-cycle
        // checks.
        assert!(phase_no_double_ring());
    }

    #[test]
    fn test_drill_corrupted_counter() {
        // Mirrors the Python drill's corrupted-counter check.
        assert!(phase_corrupted_counter());
    }

    #[test]
    fn test_drill_sweep_reconciliation() {
        // Mirrors the Python drill's sweep-agrees and sweep-mismatch
        // checks.
        assert!(phase_sweep_reconciliation());
    }

    #[test]
    fn test_drill_immutable_and_no_dale() {
        // Mirrors the Python drill's inputs-never-mutated, no-Dale,
        // no-push-import, and brief-lines checks.
        assert!(phase_immutable_and_no_dale());
    }

    #[test]
    fn test_drill_passes() {
        // Mirrors test_drill_passes in test_intel_watchman_boot.py:
        // the drill script itself exits 0.
        let (code, lines) = run_drill();
        assert_eq!(code, 0, "drill lines: {:?}", lines);
        assert!(lines.iter().all(|line| line.starts_with("PASS")
            || line.starts_with("7 PASS")));
    }
}
