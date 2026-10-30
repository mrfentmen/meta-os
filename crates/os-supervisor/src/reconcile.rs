//! Restart/failover recovery for MOS. Idempotent.
//! (`os/mos/reconcile.py`)
//!
//! Does three things: requeues jobs whose claim lease expired (via
//! the sweep), drops capability registrations whose heartbeat
//! went stale, and reports anything needing a human:
//! done-but-unverified jobs and blocked jobs. Returns a report
//! dict and prints a human-readable summary.

use crate::backend::Backend;

/// True when the relay backend answers. The liveness probe is
/// injected so the pure report logic stays testable without a bus.
pub fn redis_ok(probe: &dyn Fn() -> bool) -> bool {
    probe()
}

/// Ids of jobs done but not yet acceptance-verified.
pub fn done_unverified(backend: &Backend) -> Vec<String> {
    crate::overseer::done_unverified(backend)
}

/// Ids of currently blocked jobs, with their reasons.
pub fn blocked_jobs(backend: &Backend) -> Vec<(String, String)> {
    backend
        .index
        .iter()
        .filter_map(|jid| {
            backend.jobs.get(jid).and_then(|j| {
                if j.status == "blocked" {
                    Some((jid.clone(), j.note.chars().take(200).collect()))
                } else {
                    None
                }
            })
        })
        .collect()
}

/// Full recovery report.
#[derive(Debug, Default)]
pub struct ReconcileReport {
    pub redis: bool,
    pub requeued: Vec<String>,
    pub pruned: Vec<String>,
    pub unverified: Vec<String>,
    pub blocked: Vec<(String, String)>,
}

/// Run full recovery. `swept` carries the ids the lease sweep
/// requeued (the sweep itself is the queue's, B16).
pub fn reconcile(backend: &mut Backend, redis: bool, swept: Vec<String>) -> ReconcileReport {
    let mut report = ReconcileReport {
        redis,
        ..Default::default()
    };
    if !report.redis {
        return report;
    }
    report.requeued = swept;
    report.pruned = backend.prune_stale();
    report.unverified = done_unverified(backend);
    report.blocked = blocked_jobs(backend);
    report
}

/// Human-readable summary lines for a report; returns the exit
/// code (0 when the backend answers, 2 when unreachable).
/// Mirrors `reconcile.main`.
pub fn main_report(report: &ReconcileReport) -> (Vec<String>, i32) {
    let mut lines = vec![format!(
        "redis: {}",
        if report.redis { "OK" } else { "UNREACHABLE" }
    )];
    for jid in &report.requeued {
        lines.push(format!("REQUEUED {jid}"));
    }
    for nick in &report.pruned {
        lines.push(format!("PRUNED {nick}"));
    }
    for jid in &report.unverified {
        lines.push(format!("UNVERIFIED {jid}"));
    }
    for (jid, reason) in &report.blocked {
        lines.push(format!("BLOCKED {jid}: {reason}"));
    }
    if report.requeued.is_empty()
        && report.pruned.is_empty()
        && report.unverified.is_empty()
        && report.blocked.is_empty()
    {
        lines.push("RECONCILE_CLEAN".to_string());
    }
    (lines, if report.redis { 0 } else { 2 })
}
