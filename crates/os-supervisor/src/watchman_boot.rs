//! Watchman state after reboot (OS-129, Milo).
//! (`os/intel/watchman_boot.py`)
//!
//! The watchman itself survives the machine dying. At boot it
//! rebuilds its picture purely from queue claims and leases:
//! it never reads a stored message counter, so no stale counter
//! gap and no missed ring across the reboot boundary.
//!
//! Rules, all pure functions of queue state:
//! - Downtime window: (down_since, boot_at]. A job posted in that
//!   window arrived while the machine was down. A job posted at
//!   or before down_since was already visible before the machine
//!   died.
//! - Lease death: a claimed job whose lease_expires_at falls in
//!   the window died during the downtime. A claimed job whose
//!   lease is still alive at boot does not ring.
//! - Done jobs never ring. Malformed records never ring and never
//!   crash. Dedupe: a job id rings at most once per boot cycle,
//!   and a job id already in the rung ledger never rings again.
//! - No counter anywhere: no function takes one, no function reads
//!   one. Reconciliation: the lease-expired ring ids must equal
//!   the sweep record's requeued ids.

use serde_json::Value;
use std::collections::HashSet;

fn num(value: &Value) -> Option<f64> {
    match value {
        Value::Number(n) => n.as_f64(),
        _ => None,
    }
}

fn job_id(job: &Value) -> Option<String> {
    let id = job.get("id")?.as_str()?;
    let trimmed = id.trim();
    if trimmed.is_empty() {
        None
    } else {
        Some(trimmed.to_string())
    }
}

/// One ring: job id, reason, posted_at, lease_expires_at.
#[derive(Debug, Clone)]
pub struct Ring {
    pub job_id: String,
    pub reason: String,
    pub posted_at: Option<f64>,
    pub lease_expires_at: Option<f64>,
}

/// The ring set for the first post-boot cycle, in input order.
pub fn post_boot_rings(
    jobs: &Value,
    down_since: f64,
    boot_at: f64,
    rung_ledger: Option<&[String]>,
) -> Vec<Ring> {
    let rung: HashSet<&str> = rung_ledger
        .unwrap_or(&[])
        .iter()
        .map(|s| s.as_str())
        .collect();
    let mut rings = Vec::new();
    let mut seen = HashSet::new();
    let items = match jobs.as_array() {
        Some(items) => items,
        None => return rings,
    };
    for job in items {
        let id = match job_id(job) {
            Some(id) => id,
            None => continue,
        };
        if seen.contains(id.as_str()) || rung.contains(id.as_str()) {
            continue;
        }
        let status = job.get("status").and_then(|v| v.as_str());
        let posted_at = job.get("posted_at").and_then(num);
        let lease_expires_at = job.get("lease_expires_at").and_then(num);
        let reason = match status {
            Some("open") => match posted_at {
                Some(p) if down_since < p && p <= boot_at => Some("arrived_during_downtime"),
                _ => None,
            },
            Some("claimed") => match lease_expires_at {
                Some(l) if down_since < l && l <= boot_at => Some("lease_expired_during_downtime"),
                _ => None,
            },
            _ => None,
        };
        if let Some(reason) = reason {
            seen.insert(id.clone());
            rings.push(Ring {
                job_id: id,
                reason: reason.to_string(),
                posted_at,
                lease_expires_at,
            });
        }
    }
    rings
}

/// Job ids where rings and the sweep record disagree.
#[derive(Debug, Clone)]
pub struct SweepMismatch {
    pub missing: Vec<String>,
    pub extra: Vec<String>,
}

pub fn sweep_mismatch(rings: &[Ring], sweep_requeued: &[Value]) -> SweepMismatch {
    let mut ring_leases: Vec<String> = rings
        .iter()
        .filter(|r| r.reason == "lease_expired_during_downtime")
        .map(|r| r.job_id.clone())
        .collect();
    ring_leases.sort();
    let mut swept: Vec<String> = sweep_requeued
        .iter()
        .filter_map(|v| v.as_str().map(|s| s.to_string()))
        .collect();
    swept.sort();
    swept.dedup();
    let swept_set: HashSet<&str> = swept.iter().map(|s| s.as_str()).collect();
    let ring_set: HashSet<&str> = ring_leases.iter().map(|s| s.as_str()).collect();
    let mut missing: Vec<String> = ring_leases
        .iter()
        .filter(|j| !swept_set.contains(j.as_str()))
        .cloned()
        .collect();
    let mut extra: Vec<String> = swept
        .into_iter()
        .filter(|j| !ring_set.contains(j.as_str()))
        .collect();
    missing.sort();
    extra.sort();
    SweepMismatch { missing, extra }
}

/// The OS-129 verification note for one boot cycle.
#[derive(Debug, Clone)]
pub struct BootNote {
    pub rings: Vec<Ring>,
    pub arrived_count: usize,
    pub lease_expired_count: usize,
    pub total_rings: usize,
    pub sweep_requeued: Vec<String>,
    pub reconciled: bool,
    pub mismatch: SweepMismatch,
    pub counter_ignored: bool,
}

pub fn verify_boot_cycle(
    jobs: &Value,
    down_since: f64,
    boot_at: f64,
    sweep_requeued: &[Value],
    rung_ledger: Option<&[String]>,
) -> BootNote {
    let rings = post_boot_rings(jobs, down_since, boot_at, rung_ledger);
    let mismatch = sweep_mismatch(&rings, sweep_requeued);
    let reconciled = mismatch.missing.is_empty() && mismatch.extra.is_empty();
    // Counter proof: inject a corrupted stored counter into a
    // copy of every record and recompute. The ring set must be
    // identical, because no function here ever consults a counter.
    let poisoned = match jobs.as_array() {
        Some(items) => Value::Array(
            items
                .iter()
                .map(|job| match job.as_object() {
                    Some(obj) => {
                        let mut copy = obj.clone();
                        copy.insert("seen_counter".to_string(), Value::Number(999999.into()));
                        copy.insert("message_counter".to_string(), Value::Number((-42).into()));
                        Value::Object(copy)
                    }
                    None => job.clone(),
                })
                .collect(),
        ),
        None => jobs.clone(),
    };
    let reproof = post_boot_rings(&poisoned, down_since, boot_at, rung_ledger);
    let counter_ignored = reproof.iter().map(|r| &r.job_id).collect::<Vec<_>>()
        == rings.iter().map(|r| &r.job_id).collect::<Vec<_>>();
    let arrived_count = rings.iter().filter(|r| r.reason == "arrived_during_downtime").count();
    let lease_expired_count = rings
        .iter()
        .filter(|r| r.reason == "lease_expired_during_downtime")
        .count();
    let mut swept: Vec<String> = sweep_requeued
        .iter()
        .filter_map(|v| v.as_str().map(|s| s.to_string()))
        .collect();
    swept.sort();
    swept.dedup();
    BootNote {
        total_rings: rings.len(),
        arrived_count,
        lease_expired_count,
        rings,
        sweep_requeued: swept,
        reconciled,
        mismatch,
        counter_ignored,
    }
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
            "boot sweep MISMATCH: missing {:?}, extra {:?}",
            note.mismatch.missing, note.mismatch.extra
        ));
    }
    lines.push(format!(
        "stored counter ignored: {}",
        if note.counter_ignored { "yes" } else { "NO" }
    ));
    lines
}
