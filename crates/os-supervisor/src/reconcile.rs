//! Restart/failover recovery for MOS (port of `os/mos/reconcile.py`).
//!
//! Idempotent — safe to run at every overseer/worker startup and on
//! a schedule. Does three things:
//!
//! 1. Requeues jobs whose claim lease expired (via the jobs sweep).
//! 2. Drops capability registrations whose heartbeat went stale.
//! 3. Reports anything needing a human: done-but-unverified jobs and
//!    blocked jobs.
//!
//! Returns a report dict; the human-readable summary is rendered by
//! [`render_summary`], mirroring Python's `main()` output.
//!
//! SEAMS (see the trait docs): `jobs`, `mos.capabilities` and
//! `relay_common` are not in this batch, so this module does not
//! import them. [`ReconcileBackend`] is the seam: it supplies the
//! backend answers (backend reachable, sweep output, stale prune,
//! job hashes) and the pure filtering logic in this file —
//! [`done_unverified_from`], [`blocked_from`] — operates on those
//! hashes exactly as the Python code operates on `jobs._hgetall`
//! results. No live Redis effect is performed or faked here.

use std::collections::HashMap;

/// One job hash, as `jobs._hgetall` returns it: field name to value.
pub type JobHash = HashMap<String, String>;

/// SEAM (see module docs): the jobs / capabilities / relay backend
/// behind reconcile. Implementors supply backend answers; the
/// recovery logic in [`reconcile`] stays backend-independent.
pub trait ReconcileBackend {
    /// True when the relay backend answers (Python: `rc.api_get("ping")`
    /// does not raise).
    fn redis_ok(&self) -> bool;
    /// Requeue lease-expired claims; returns requeued job ids
    /// (Python parses `REQUEUED <jid>` lines from `jobs.main(["sweep"])`
    /// output). Errors are tolerated by [`reconcile`] with a warning.
    fn sweep_leases(&mut self) -> Result<Vec<String>, String>;
    /// Drop stale capability registrations; returns pruned nicks.
    /// Errors are tolerated by [`reconcile`] with a warning.
    fn prune_stale(&mut self) -> Result<Vec<String>, String>;
    /// All job hashes, as `(job id, hash)` pairs, in index order
    /// (Python reads the job index, then `_hgetall` per id; a backend
    /// failure there yields no ids, i.e. an empty list here).
    fn job_hashes(&self) -> Vec<(String, JobHash)>;
}

/// Ids of jobs done but not yet acceptance-verified: status
/// `"done"` and `verified` not equal to `"1"`.
pub fn done_unverified_from(hashes: &[(String, JobHash)]) -> Vec<String> {
    hashes
        .iter()
        .filter(|(_, h)| {
            h.get("status").map(String::as_str) == Some("done")
                && h.get("verified").map(String::as_str) != Some("1")
        })
        .map(|(jid, _)| jid.clone())
        .collect()
}

/// Ids of jobs currently blocked, with their reasons. The reason is
/// the job's `note`, truncated to 200 characters exactly as Python's
/// `h.get("note", "")[:200]` (character count, not bytes).
pub fn blocked_from(hashes: &[(String, JobHash)]) -> Vec<(String, String)> {
    hashes
        .iter()
        .filter(|(_, h)| h.get("status").map(String::as_str) == Some("blocked"))
        .map(|(jid, h)| {
            let note = h.get("note").map(String::as_str).unwrap_or("");
            (jid.clone(), note.chars().take(200).collect())
        })
        .collect()
}

/// Full recovery report, mirroring Python's `reconcile()` dict.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ReconcileReport {
    /// Whether the relay backend answered.
    pub redis: bool,
    /// Job ids whose lease-expired claims were requeued.
    pub requeued: Vec<String>,
    /// Nicks whose stale capability registrations were pruned.
    pub pruned: Vec<String>,
    /// Ids of jobs done but not yet acceptance-verified.
    pub unverified: Vec<String>,
    /// Blocked jobs with their reasons.
    pub blocked: Vec<(String, String)>,
}

impl ReconcileReport {
    /// True when nothing needed doing (no requeued, pruned,
    /// unverified, or blocked entries) — the `RECONCILE_CLEAN` case.
    pub fn is_clean(&self) -> bool {
        self.requeued.is_empty()
            && self.pruned.is_empty()
            && self.unverified.is_empty()
            && self.blocked.is_empty()
    }
}

/// Run full recovery. Returns a report dict.
///
/// If the backend is unreachable, the report is returned immediately
/// with all lists empty (Python returns before sweeping, pruning, or
/// reading jobs). Sweep and prune failures are tolerated with a
/// warning on stderr, exactly as Python prints `WARNING: sweep
/// failed (...)` / `WARNING: prune failed (...)`; the unverified and
/// blocked reads are then still performed.
pub fn reconcile(backend: &mut dyn ReconcileBackend) -> ReconcileReport {
    let mut report = ReconcileReport::default();
    report.redis = backend.redis_ok();
    if !report.redis {
        return report;
    }
    match backend.sweep_leases() {
        Ok(ids) => report.requeued = ids,
        Err(e) => eprintln!("WARNING: sweep failed ({e})"),
    }
    match backend.prune_stale() {
        Ok(nicks) => report.pruned = nicks,
        Err(e) => eprintln!("WARNING: prune failed ({e})"),
    }
    let hashes = backend.job_hashes();
    report.unverified = done_unverified_from(&hashes);
    report.blocked = blocked_from(&hashes);
    report
}

/// Render the human-readable summary, mirroring Python's `main()`
/// output lines in order: redis line, one line per requeued /
/// pruned / unverified / blocked entry, and `RECONCILE_CLEAN` when
/// nothing needed doing.
pub fn render_summary(report: &ReconcileReport) -> String {
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
    if report.is_clean() {
        lines.push("RECONCILE_CLEAN".to_string());
    }
    lines.join("\n")
}

/// Exit code for a report, mirroring Python's `main()`: 0 when the
/// backend answered, 2 when it did not.
pub fn exit_code(report: &ReconcileReport) -> i32 {
    if report.redis {
        0
    } else {
        2
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct FakeBackend {
        redis: bool,
        sweep: Result<Vec<String>, String>,
        prune: Result<Vec<String>, String>,
        hashes: Vec<(String, JobHash)>,
    }

    impl ReconcileBackend for FakeBackend {
        fn redis_ok(&self) -> bool {
            self.redis
        }
        fn sweep_leases(&mut self) -> Result<Vec<String>, String> {
            self.sweep.clone()
        }
        fn prune_stale(&mut self) -> Result<Vec<String>, String> {
            self.prune.clone()
        }
        fn job_hashes(&self) -> Vec<(String, JobHash)> {
            self.hashes.clone()
        }
    }

    fn hash(pairs: &[(&str, &str)]) -> JobHash {
        pairs.iter().map(|(k, v)| (k.to_string(), v.to_string())).collect()
    }

    fn mixed_hashes() -> Vec<(String, JobHash)> {
        vec![
            ("j1".to_string(), hash(&[("status", "done")])),
            ("j2".to_string(), hash(&[("status", "done"), ("verified", "1")])),
            ("j3".to_string(), hash(&[("status", "done"), ("verified", "0")])),
            ("j4".to_string(), hash(&[("status", "blocked"), ("note", "waiting on dep")])),
            ("j5".to_string(), hash(&[("status", "open")])),
            ("j6".to_string(), hash(&[("status", "blocked")])),
        ]
    }

    #[test]
    fn reconcile_full_flow_from_module_behavior() {
        let mut backend = FakeBackend {
            redis: true,
            sweep: Ok(vec!["j9".to_string()]),
            prune: Ok(vec!["stale-nick".to_string()]),
            hashes: mixed_hashes(),
        };
        let report = reconcile(&mut backend);
        assert!(report.redis);
        assert_eq!(report.requeued, vec!["j9"]);
        assert_eq!(report.pruned, vec!["stale-nick"]);
        assert_eq!(report.unverified, vec!["j1", "j3"]);
        assert_eq!(
            report.blocked,
            vec![
                ("j4".to_string(), "waiting on dep".to_string()),
                ("j6".to_string(), String::new()),
            ]
        );
        assert_eq!(exit_code(&report), 0);
        let summary = render_summary(&report);
        assert!(summary.contains("redis: OK"));
        assert!(summary.contains("REQUEUED j9"));
        assert!(summary.contains("PRUNED stale-nick"));
        assert!(summary.contains("UNVERIFIED j1"));
        assert!(summary.contains("BLOCKED j4: waiting on dep"));
        assert!(!summary.contains("RECONCILE_CLEAN"));
    }

    #[test]
    fn reconcile_redis_down_returns_early_empty() {
        let mut backend = FakeBackend {
            redis: false,
            sweep: Ok(vec!["j9".to_string()]),
            prune: Ok(vec!["stale-nick".to_string()]),
            hashes: mixed_hashes(),
        };
        let report = reconcile(&mut backend);
        assert!(!report.redis);
        assert!(report.requeued.is_empty());
        assert!(report.pruned.is_empty());
        assert!(report.unverified.is_empty());
        assert!(report.blocked.is_empty());
        assert_eq!(exit_code(&report), 2);
        assert!(render_summary(&report).contains("redis: UNREACHABLE"));
        assert!(render_summary(&report).contains("RECONCILE_CLEAN"));
    }

    #[test]
    fn reconcile_sweep_and_prune_failures_tolerated() {
        let mut backend = FakeBackend {
            redis: true,
            sweep: Err("boom".to_string()),
            prune: Err("gone".to_string()),
            hashes: mixed_hashes(),
        };
        let report = reconcile(&mut backend);
        assert!(report.redis);
        assert!(report.requeued.is_empty());
        assert!(report.pruned.is_empty());
        assert_eq!(report.unverified, vec!["j1", "j3"]);
        assert_eq!(report.blocked.len(), 2);
    }

    #[test]
    fn blocked_note_truncated_to_200_chars() {
        let long = "x".repeat(500);
        let hashes = vec![("jb".to_string(), hash(&[("status", "blocked"), ("note", &long)]))];
        let blocked = blocked_from(&hashes);
        assert_eq!(blocked[0].1.chars().count(), 200);
    }

    #[test]
    fn reconcile_clean_summary_when_nothing_to_do() {
        let mut backend = FakeBackend {
            redis: true,
            sweep: Ok(vec![]),
            prune: Ok(vec![]),
            hashes: vec![("j2".to_string(), hash(&[("status", "done"), ("verified", "1")]))],
        };
        let report = reconcile(&mut backend);
        assert!(report.is_clean());
        assert_eq!(render_summary(&report), "redis: OK\nRECONCILE_CLEAN");
    }

    #[test]
    fn reconcile_twice_is_idempotent_on_same_backend() {
        let mut backend = FakeBackend {
            redis: true,
            sweep: Ok(vec![]),
            prune: Ok(vec![]),
            hashes: mixed_hashes(),
        };
        let first = reconcile(&mut backend);
        let second = reconcile(&mut backend);
        assert_eq!(first, second);
    }
}
