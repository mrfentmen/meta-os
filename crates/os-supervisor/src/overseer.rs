//! The MOS overseer: dispatches work, verifies results, requeues failures.
//! (`os/mos/overseer.py`)
//!
//! One overseer per crew. It posts jobs and DMs capable workers,
//! runs `tick()` periodically (sweep expired leases, prune stale
//! capability registrations, verify done-but-unverified jobs),
//! verifies a done job's acceptance criteria, and requeues jobs
//! whose acceptance fails with the failure report as note.
//!
//! The live transport (Redis, bus, DM sends, git worktrees, the
//! acceptance runner) is injected: `dispatch` takes a DM sender,
//! `verify_done` takes an acceptance verifier over an
//! already-resolved workdir (worktree orchestration itself is
//! B19 gitops, acceptance checks are B31). All state lives in
//! the passed-in [`Backend`][crate::backend::Backend]; the bus
//! carries announcements only.

use crate::backend::{Backend, JobRecord};

pub const LEASE_DEFAULT: u64 = 1800;

/// Post a job and DM every capable worker.
/// Returns (jid, dm_results) where dm_results is
/// [(nick, dm_ok, detail)].
pub fn dispatch(
    backend: &mut Backend,
    title: &str,
    spec: &str,
    accept: &str,
    requirements: &[String],
    room: &str,
    branch: &str,
    base: &str,
    dm_send: &mut dyn FnMut(&str, &str, &str) -> Result<String, String>,
) -> Result<(String, Vec<(String, bool, String)>), String> {
    if spec.trim().is_empty() {
        return Err("spec must not be empty".to_string());
    }
    let reqs: Vec<String> = requirements
        .iter()
        .map(|r| r.trim().to_lowercase())
        .filter(|r| !r.is_empty())
        .collect();
    let _ = base;
    let jid = backend.post_job(title, spec, accept, branch, room, &reqs.join(","));
    let mut dm_results = Vec::new();
    for nick in backend.find_for(&reqs) {
        let secret = backend
            .caps
            .get(&nick)
            .map(|r| r.dm_secret.clone())
            .unwrap_or_default();
        if secret.is_empty() {
            dm_results.push((nick, false, "no DM secret registered".to_string()));
            continue;
        }
        let mut text = format!("JOB:{jid} {title}");
        if !reqs.is_empty() {
            text.push_str(&format!(" req={}", reqs.join(",")));
        }
        match dm_send(&nick, &secret, &text) {
            Ok(detail) => dm_results.push((nick, true, detail)),
            Err(detail) => dm_results.push((nick, false, detail)),
        }
    }
    backend.announce(room, &format!("DISPATCH:{jid} -> {} worker(s)", dm_results.len()));
    Ok((jid, dm_results))
}

fn set_verified(job: &mut JobRecord, ok: bool, report: &str, now: u64) {
    job.verified = ok;
    let _ = now;
    job.note = report.chars().rev().take(2000).collect::<Vec<_>>().into_iter().rev().collect();
}

/// Verify a done job's acceptance criteria against `workdir`.
/// On success marks verified. On failure requeues the job to
/// open with the failure report as its note.
/// Returns (ok, report_text).
pub fn verify_done(
    backend: &mut Backend,
    jid: &str,
    workdir: &str,
    verifier: &dyn Fn(&str, &str) -> (bool, String),
) -> (bool, String) {
    let job = match backend.jobs.get(jid).cloned() {
        Some(j) => j,
        None => return (false, format!("no such job: {jid}")),
    };
    if job.status != "done" {
        return (false, format!("job {jid} is {}, not done", job.status));
    }
    if job.verified {
        return (true, "already verified".to_string());
    }
    let (ok, report) = verifier(&job.accept, workdir);
    if ok {
        if let Some(stored) = backend.jobs.get_mut(jid) {
            set_verified(stored, true, &report, backend.now);
        }
        backend.announce(&job.room.clone(), &format!("VERIFIED:{jid}"));
        return (true, report);
    }
    if let Some(stored) = backend.jobs.get_mut(jid) {
        stored.status = "open".to_string();
        stored.note = format!("acceptance failed:\n{report}");
        if stored.note.len() > 2000 {
            stored.note = stored.note[stored.note.len() - 2000..].to_string();
        }
        stored.claim.clear();
        stored.result_commit.clear();
        stored.verified = false;
    }
    backend.announce(&job.room.clone(), &format!("REQUEUE:{jid} acceptance failed"));
    (false, report)
}

/// Job ids with status done and no verified stamp.
pub fn done_unverified(backend: &Backend) -> Vec<String> {
    backend
        .index
        .iter()
        .filter(|jid| {
            backend
                .jobs
                .get(*jid)
                .map(|j| j.status == "done" && !j.verified)
                .unwrap_or(false)
        })
        .cloned()
        .collect()
}

/// One overseer pass. Returns a report dict.
#[derive(Debug, Default)]
pub struct TickReport {
    pub swept: Vec<String>,
    pub pruned: Vec<String>,
    pub verified: Vec<String>,
    pub failed: Vec<String>,
    pub errors: Vec<String>,
}

/// Sweeping requeues lease-expired claims; the lease rule itself
/// lives in the queue (B16). Here the sweep is modeled as: jobs
/// the caller marks swept are reported; callers pass them in.
pub fn tick(
    backend: &mut Backend,
    swept: Vec<String>,
    verifier: &dyn Fn(&str, &str) -> (bool, String),
    workdir: &str,
) -> TickReport {
    let mut report = TickReport::default();
    report.swept = swept;
    report.pruned = backend.prune_stale();
    for jid in done_unverified(backend) {
        let (ok, _) = verify_done(backend, &jid, workdir, verifier);
        if ok {
            report.verified.push(jid);
        } else {
            report.failed.push(jid);
        }
    }
    report
}
