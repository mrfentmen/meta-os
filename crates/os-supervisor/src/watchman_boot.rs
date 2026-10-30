//! Watchman state after reboot (OS-129).
//!
//! Port of `os/intel/watchman_boot.py`. The watchman itself survives
//! the machine dying. At boot it rebuilds its picture purely from queue
//! claims and leases: it never reads a stored message counter, so no
//! stale counter gap and no missed ring across the reboot boundary, and
//! a deliberately corrupted stored counter value changes nothing in its
//! behaviour. Its first post-boot cycle rings for every job that arrived
//! while the machine was down, and for every claimed job whose lease
//! died during the downtime (the lease sweep requeues those), and it
//! rings for each such job exactly once. Its first post-boot cycle also
//! reconciles with the lease sweep: the recovered count it reports
//! matches the sweep record.
//!
//! This module is the verification half of OS-129. It does not ring any
//! bell itself and it moves no claim: it computes, from fixture queue
//! state, the ring set a correct watchman must produce, and checks that
//! set against the sweep record. The mechanical half (the resident
//! watchman program that actually rings) is Pax OS-118.
//!
//! Rules, all pure functions of queue state:
//! - Downtime window: `(down_since, boot_at]`. A job posted in that
//!   window arrived while the machine was down, so the first post-boot
//!   cycle must ring for it. A job posted at or before `down_since` was
//!   already visible before the machine died, so it does not ring.
//! - Lease death: a claimed job whose `lease_expires_at` falls in the
//!   window died during the downtime; the sweep requeues it, so the
//!   first post-boot cycle must ring for it. A claimed job whose lease
//!   is still alive at boot does not ring.
//! - Done jobs never ring. Malformed records (no id, no usable
//!   timestamps) never ring and never crash.
//! - Dedupe: a job id rings at most once per boot cycle, however many
//!   times it appears in the input, and a job id already in the rung
//!   ledger (rung by an earlier post-boot cycle) never rings again.
//! - No counter anywhere: no function here takes a counter argument,
//!   and no function reads one. In Rust this is structural: the job
//!   type has no counter field at all, so a corrupted stored counter
//!   cannot even be represented, let alone consulted. The verification
//!   note still recomputes the ring set as the Python counter proof
//!   does, and reports the comparison.
//! - Reconciliation: the lease-expired ring ids must equal the sweep
//!   record's requeued ids. When they match, the verification note
//!   reports recovered counts that agree; when they differ, the note
//!   names the mismatched ids and reports `reconciled` false, never a
//!   fudged count.
//!
//! Inputs are never mutated: every function copies what it returns, and
//! the rung ledger passed in is left alone; the caller owns the ledger
//! update. No push path, no announcement path, no network: a
//! verification note can never contact Dale.
//!
//! This module is standalone: it imports no other module in the chain.

use std::collections::HashSet;

/// Reason for an open job posted during the downtime window.
pub const ARRIVED_DURING_DOWNTIME: &str = "arrived_during_downtime";
/// Reason for a claimed job whose lease died during the downtime window.
pub const LEASE_EXPIRED_DURING_DOWNTIME: &str = "lease_expired_during_downtime";

/// One job record, as read by the boot verification.
///
/// Every field is optional because a Python record may omit it; a
/// missing id or a missing usable timestamp means the job never rings.
/// There is deliberately no counter field here (see the module docs).
#[derive(Clone, Debug, Default, PartialEq)]
pub struct BootJob {
    /// Job id, if a usable non-empty string.
    pub id: Option<String>,
    /// Job status (`"open"`, `"claimed"`, `"done"`, ...), if any.
    pub status: Option<String>,
    /// Posting timestamp, if usable.
    pub posted_at: Option<f64>,
    /// Lease expiry timestamp, if usable.
    pub lease_expires_at: Option<f64>,
}

impl BootJob {
    /// A job with the given id and status, and no timestamps.
    pub fn new(id: &str, status: &str) -> Self {
        BootJob {
            id: if id.trim().is_empty() {
                None
            } else {
                Some(id.trim().to_string())
            },
            status: Some(status.to_string()),
            ..Default::default()
        }
    }
}

/// One ring in the first post-boot cycle's ring set.
#[derive(Clone, Debug, PartialEq)]
pub struct Ring {
    /// Job id.
    pub job_id: String,
    /// One of [`ARRIVED_DURING_DOWNTIME`] or
    /// [`LEASE_EXPIRED_DURING_DOWNTIME`].
    pub reason: String,
    /// Posting timestamp (the job's own value, possibly `None` for a
    /// lease-expired ring).
    pub posted_at: Option<f64>,
    /// Lease expiry timestamp (the job's own value, possibly `None` for
    /// an arrival ring).
    pub lease_expires_at: Option<f64>,
}

/// Job ids where rings and the sweep record disagree.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct SweepMismatch {
    /// Lease-expired rings the sweep did not requeue, sorted.
    pub missing: Vec<String>,
    /// Sweep requeues with no matching ring, sorted.
    pub extra: Vec<String>,
}

/// The OS-129 verification note for one boot cycle.
#[derive(Clone, Debug, PartialEq)]
pub struct BootNote {
    /// The ring set, in input order.
    pub rings: Vec<Ring>,
    /// Count of arrival rings.
    pub arrived_count: usize,
    /// Count of lease-expired rings.
    pub lease_expired_count: usize,
    /// Total rings.
    pub total_rings: usize,
    /// Sweep requeued ids, sorted and deduplicated.
    pub sweep_requeued: Vec<String>,
    /// True when the lease-expired rings exactly equal the sweep record.
    pub reconciled: bool,
    /// Mismatch ids (empty when reconciled).
    pub mismatch: SweepMismatch,
    /// True when recomputing the ring set with corrupted counter values
    /// injected yields the identical ring set (always true here: the
    /// job type has no counter field to corrupt).
    pub counter_ignored: bool,
}

/// The usable job id, or `None` for a missing/blank id.
///
/// Mirrors Python's `_job_id`: a string id is stripped, and a blank id
/// after stripping reads as no id.
fn job_id(job: &BootJob) -> Option<String> {
    match &job.id {
        Some(id) if !id.trim().is_empty() => Some(id.trim().to_string()),
        _ => None,
    }
}

/// The ring set for the first post-boot cycle.
///
/// `jobs` is the job records in input order. `down_since` is the moment
/// the machine went down, `boot_at` the moment it came back.
/// `rung_ledger` is the job ids already rung by earlier post-boot
/// cycles (`None` means nothing rung). Returns ring dicts in input
/// order. Inputs are never mutated.
pub fn post_boot_rings(
    jobs: &[BootJob],
    down_since: f64,
    boot_at: f64,
    rung_ledger: Option<&[String]>,
) -> Vec<Ring> {
    let rung: HashSet<&str> = rung_ledger
        .unwrap_or(&[])
        .iter()
        .map(|id| id.as_str())
        .collect();
    let mut rings = Vec::new();
    let mut seen: HashSet<String> = HashSet::new();
    for job in jobs {
        let id = match job_id(job) {
            Some(id) => id,
            None => continue,
        };
        if seen.contains(&id) || rung.contains(id.as_str()) {
            continue;
        }
        let reason = match job.status.as_deref() {
            Some("open") => match job.posted_at {
                Some(posted_at) if down_since < posted_at && posted_at <= boot_at => {
                    Some(ARRIVED_DURING_DOWNTIME)
                }
                _ => None,
            },
            Some("claimed") => match job.lease_expires_at {
                Some(lease_expires_at)
                    if down_since < lease_expires_at && lease_expires_at <= boot_at =>
                {
                    Some(LEASE_EXPIRED_DURING_DOWNTIME)
                }
                _ => None,
            },
            _ => None,
        };
        let reason = match reason {
            Some(reason) => reason,
            None => continue,
        };
        seen.insert(id.clone());
        rings.push(Ring {
            job_id: id,
            reason: reason.to_string(),
            posted_at: job.posted_at,
            lease_expires_at: job.lease_expires_at,
        });
    }
    rings
}

/// Job ids where rings and the sweep record disagree.
///
/// `sweep_requeued` is the job ids the lease sweep says it requeued.
/// Returns missing (lease-expired rings the sweep did not requeue) and
/// extra (sweep requeues with no matching ring), both sorted.
pub fn sweep_mismatch(rings: &[Ring], sweep_requeued: &[String]) -> SweepMismatch {
    let mut ring_leases: Vec<String> = rings
        .iter()
        .filter(|r| r.reason == LEASE_EXPIRED_DURING_DOWNTIME)
        .map(|r| r.job_id.clone())
        .collect();
    ring_leases.sort();
    let mut swept: Vec<String> = {
        let mut set: HashSet<String> = HashSet::new();
        for id in sweep_requeued {
            set.insert(id.clone());
        }
        let mut list: Vec<String> = set.into_iter().collect();
        list.sort();
        list
    };
    let _ = &mut swept;
    let missing: Vec<String> = ring_leases
        .iter()
        .filter(|id| !swept.contains(id))
        .cloned()
        .collect();
    let extra: Vec<String> = swept
        .iter()
        .filter(|id| !ring_leases.contains(id))
        .cloned()
        .collect();
    SweepMismatch { missing, extra }
}

/// The OS-129 verification note for one boot cycle.
///
/// The note carries no push and no announcement field. The counter proof
/// recomputes the ring set over copies of the jobs (in Python with
/// corrupted counter keys injected; in Rust there is no counter field
/// to inject, so the copies are identical by construction) and reports
/// whether the recomputed ring set matches.
pub fn verify_boot_cycle(
    jobs: &[BootJob],
    down_since: f64,
    boot_at: f64,
    sweep_requeued: &[String],
    rung_ledger: Option<&[String]>,
) -> BootNote {
    let rings = post_boot_rings(jobs, down_since, boot_at, rung_ledger);
    let mismatch = sweep_mismatch(&rings, sweep_requeued);
    let reconciled = mismatch.missing.is_empty() && mismatch.extra.is_empty();
    // Counter proof: recompute over copies of the jobs. Python injects
    // corrupted counter keys into the copies; this type has no counter
    // field, so the copies are the jobs themselves, and the ring set
    // must be identical because no function here ever consults a
    // counter.
    let poisoned: Vec<BootJob> = jobs.to_vec();
    let reproof = post_boot_rings(&poisoned, down_since, boot_at, rung_ledger);
    let counter_ignored: Vec<&str> = reproof.iter().map(|r| r.job_id.as_str()).collect();
    let ring_ids: Vec<&str> = rings.iter().map(|r| r.job_id.as_str()).collect();
    let counter_ignored = counter_ignored == ring_ids;
    let arrived_count = rings
        .iter()
        .filter(|r| r.reason == ARRIVED_DURING_DOWNTIME)
        .count();
    let lease_expired_count = rings
        .iter()
        .filter(|r| r.reason == LEASE_EXPIRED_DURING_DOWNTIME)
        .count();
    let mut swept_sorted: Vec<String> = {
        let mut set: HashSet<String> = HashSet::new();
        for id in sweep_requeued {
            set.insert(id.clone());
        }
        let mut list: Vec<String> = set.into_iter().collect();
        list.sort();
        list
    };
    let _ = &mut swept_sorted;
    BootNote {
        total_rings: rings.len(),
        rings,
        arrived_count,
        lease_expired_count,
        sweep_requeued: swept_sorted,
        reconciled,
        mismatch,
        counter_ignored,
    }
}

/// Format a string list the way Python formats a list of strings
/// (`['a', 'b']`), for brief lines.
fn fmt_py_list(items: &[String]) -> String {
    let inner: Vec<String> = items.iter().map(|item| format!("'{}'", item)).collect();
    format!("[{}]", inner.join(", "))
}

/// Brief lines for a verification note.
pub fn boot_brief_lines(note: &BootNote) -> Vec<String> {
    let mut lines = vec![format!(
        "watchman boot: {} ring(s) ({} arrived during downtime, {} lease-expired)",
        note.total_rings, note.arrived_count, note.lease_expired_count
    )];
    for ring in &note.rings {
        lines.push(format!("ring {}: {}", ring.job_id, ring.reason));
    }
    if note.reconciled {
        lines.push(format!(
            "boot sweep reconciled: {} requeued, counts agree",
            note.sweep_requeued.len()
        ));
    } else {
        lines.push(format!(
            "boot sweep MISMATCH: missing {}, extra {}",
            fmt_py_list(&note.mismatch.missing),
            fmt_py_list(&note.mismatch.extra)
        ));
    }
    lines.push(format!(
        "stored counter ignored: {}",
        if note.counter_ignored { "yes" } else { "NO" }
    ));
    lines
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    const T0: f64 = 100000.0;
    const T1: f64 = 100600.0;

    fn base_jobs() -> Vec<BootJob> {
        vec![
            BootJob {
                id: Some("arrive-1".to_string()),
                status: Some("open".to_string()),
                posted_at: Some(T0 + 100.0),
                ..Default::default()
            },
            BootJob {
                id: Some("arrive-2".to_string()),
                status: Some("open".to_string()),
                posted_at: Some(T0 + 500.0),
                ..Default::default()
            },
            BootJob {
                id: Some("before".to_string()),
                status: Some("open".to_string()),
                posted_at: Some(T0 - 50.0),
                ..Default::default()
            },
            BootJob {
                id: Some("after".to_string()),
                status: Some("open".to_string()),
                posted_at: Some(T1 + 10.0),
                ..Default::default()
            },
            BootJob {
                id: Some("lease-dead".to_string()),
                status: Some("claimed".to_string()),
                lease_expires_at: Some(T0 + 300.0),
                ..Default::default()
            },
            BootJob {
                id: Some("lease-live".to_string()),
                status: Some("claimed".to_string()),
                lease_expires_at: Some(T1 + 900.0),
                ..Default::default()
            },
            BootJob {
                id: Some("done-job".to_string()),
                status: Some("done".to_string()),
                lease_expires_at: Some(T0 + 200.0),
                ..Default::default()
            },
        ]
    }

    fn ids(rings: &[Ring]) -> Vec<&str> {
        rings.iter().map(|r| r.job_id.as_str()).collect()
    }

    #[test]
    fn test_arrivals_ring_and_only_arrivals_ring() {
        // Mirrors test_arrivals_ring_and_only_arrivals_ring.
        let rings = post_boot_rings(&base_jobs(), T0, T1, None);
        assert_eq!(ids(&rings), ["arrive-1", "arrive-2", "lease-dead"]);
        let reasons: HashMap<&str, &str> = rings
            .iter()
            .map(|r| (r.job_id.as_str(), r.reason.as_str()))
            .collect();
        assert_eq!(reasons["arrive-1"], ARRIVED_DURING_DOWNTIME);
        assert_eq!(reasons["arrive-2"], ARRIVED_DURING_DOWNTIME);
        assert_eq!(
            reasons["lease-dead"],
            LEASE_EXPIRED_DURING_DOWNTIME
        );
    }

    #[test]
    fn test_pre_window_post_boot_live_lease_and_done_do_not_ring() {
        // Mirrors test_pre_window_post_boot_live_lease_and_done_do_not_ring.
        let rings = post_boot_rings(&base_jobs(), T0, T1, None);
        let ring_ids = ids(&rings);
        for missing in ["before", "after", "lease-live", "done-job"] {
            assert!(!ring_ids.contains(&missing));
        }
    }

    #[test]
    fn test_malformed_records_never_ring_and_never_crash() {
        // Mirrors test_malformed_records_never_ring_and_never_crash. A
        // Python non-dict record or a None record cannot be built for
        // &[BootJob]; jobs with no id or no usable time cover their
        // judgement (never ring, never crash).
        let mut jobs = base_jobs();
        jobs.push(BootJob {
            id: None,
            status: Some("open".to_string()),
            posted_at: Some(T0 + 10.0),
            ..Default::default()
        });
        jobs.push(BootJob {
            id: Some("no-time".to_string()),
            status: Some("open".to_string()),
            ..Default::default()
        });
        let rings = post_boot_rings(&jobs, T0, T1, None);
        assert_eq!(ids(&rings), ["arrive-1", "arrive-2", "lease-dead"]);
        assert!(!ids(&rings).contains(&"no-time"));
    }

    #[test]
    fn test_duplicate_input_rings_once() {
        // Mirrors test_duplicate_input_rings_once.
        let mut jobs = base_jobs();
        jobs.push(BootJob {
            id: Some("arrive-1".to_string()),
            status: Some("open".to_string()),
            posted_at: Some(T0 + 100.0),
            ..Default::default()
        });
        let rings = post_boot_rings(&jobs, T0, T1, None);
        assert_eq!(ids(&rings).iter().filter(|id| **id == "arrive-1").count(), 1);
    }

    #[test]
    fn test_second_cycle_with_ledger_rings_nothing_new() {
        // Mirrors test_second_cycle_with_ledger_rings_nothing_new.
        let first = post_boot_rings(&base_jobs(), T0, T1, None);
        let first_ids: Vec<String> =
            first.iter().map(|r| r.job_id.clone()).collect();
        let second = post_boot_rings(&base_jobs(), T0, T1, Some(&first_ids));
        assert!(second.is_empty());
    }

    #[test]
    fn test_corrupted_counter_changes_nothing() {
        // Mirrors test_corrupted_counter_changes_nothing. Poisoned jobs
        // in Python carry junk counter keys; this type has no counter
        // field, so the poisoned set is the clean set, and the note's
        // counter_ignored flag is the structural proof.
        let clean = post_boot_rings(&base_jobs(), T0, T1, None);
        let poisoned = post_boot_rings(&base_jobs(), T0, T1, None);
        assert_eq!(ids(&poisoned), ids(&clean));
        let note = verify_boot_cycle(
            &base_jobs(),
            T0,
            T1,
            &["lease-dead".to_string()],
            None,
        );
        assert!(note.counter_ignored);
    }

    #[test]
    fn test_sweep_reconciliation_agrees() {
        // Mirrors test_sweep_reconciliation_agrees.
        let note = verify_boot_cycle(
            &base_jobs(),
            T0,
            T1,
            &["lease-dead".to_string()],
            None,
        );
        assert!(note.reconciled);
        assert_eq!(note.total_rings, 3);
        assert_eq!(note.arrived_count, 2);
        assert_eq!(note.lease_expired_count, 1);
    }

    #[test]
    fn test_sweep_mismatch_named_never_fudged() {
        // Mirrors test_sweep_mismatch_named_never_fudged.
        let note = verify_boot_cycle(
            &base_jobs(),
            T0,
            T1,
            &["job-stranger".to_string()],
            None,
        );
        assert!(!note.reconciled);
        assert_eq!(note.mismatch.missing, ["lease-dead"]);
        assert_eq!(note.mismatch.extra, ["job-stranger"]);
    }

    #[test]
    fn test_inputs_never_mutated() {
        // Mirrors test_inputs_never_mutated.
        let jobs = base_jobs();
        let original = jobs.clone();
        let ledger = vec!["arrive-1".to_string()];
        post_boot_rings(&jobs, T0, T1, Some(&ledger));
        verify_boot_cycle(&jobs, T0, T1, &["lease-dead".to_string()], None);
        assert_eq!(jobs, original);
        assert_eq!(ledger, ["arrive-1"]);
    }

    #[test]
    fn test_note_carries_no_push_or_announcement() {
        // Mirrors test_note_carries_no_push_or_announcement. The note
        // type has no push or announcement field by construction; the
        // brief lines name a ring and the reconciliation.
        let note = verify_boot_cycle(
            &base_jobs(),
            T0,
            T1,
            &["lease-dead".to_string()],
            None,
        );
        let lines = boot_brief_lines(&note);
        assert!(lines.iter().any(|line| line.contains("arrive-1")));
        assert!(lines.iter().any(|line| line.contains("reconciled")));
        assert!(lines.iter().any(|line| line.contains("stored counter ignored: yes")));
    }

    #[test]
    fn test_window_boundaries() {
        // Boundary behavior from the module docs: (down_since, boot_at]
        // is half-open on the left, closed on the right.
        let jobs = vec![
            BootJob {
                id: Some("at-down".to_string()),
                status: Some("open".to_string()),
                posted_at: Some(T0),
                ..Default::default()
            },
            BootJob {
                id: Some("at-boot".to_string()),
                status: Some("open".to_string()),
                posted_at: Some(T1),
                ..Default::default()
            },
            BootJob {
                id: Some("lease-at-boot".to_string()),
                status: Some("claimed".to_string()),
                lease_expires_at: Some(T1),
                ..Default::default()
            },
        ];
        let rings = post_boot_rings(&jobs, T0, T1, None);
        assert_eq!(ids(&rings), ["at-boot", "lease-at-boot"]);
    }

    #[test]
    fn test_mismatch_brief_lines_name_ids() {
        // Companion to test_sweep_mismatch_named_never_fudged: the
        // mismatch brief line names the ids in Python list form.
        let note = verify_boot_cycle(
            &base_jobs(),
            T0,
            T1,
            &["job-stranger".to_string()],
            None,
        );
        let lines = boot_brief_lines(&note);
        assert!(lines.iter().any(|line| line.contains(
            "boot sweep MISMATCH: missing ['lease-dead'], extra ['job-stranger']"
        )));
    }
}
