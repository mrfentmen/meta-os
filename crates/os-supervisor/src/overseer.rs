//! The MOS overseer (port of `os/mos/overseer.py`).
//!
//! Dispatches work, verifies results, requeues failures. One
//! overseer per crew. It:
//!
//! - posts jobs (via jobs) and DMs capable workers (via send `--dm`),
//! - runs [`tick`] periodically: sweeps expired leases, prunes stale
//!   capability registrations, and verifies done-but-unverified jobs,
//! - verifies a done job's machine-readable acceptance criteria
//!   against the worker's branch before the job counts as truly done,
//! - requeues jobs whose acceptance fails, with the failure report as
//!   note.
//!
//! All state stays in Redis; the bus carries announcements only.
//!
//! SEAMS (see the trait docs): `jobs`, `send`,
//! `mos.acceptance`, `mos.capabilities` and `mos.gitops` are not in
//! this batch, so this module does not import them — and in
//! particular does NOT import the `os-jobs`, `os-identity` or
//! `os-workspace` crates, whose APIs are being written in parallel.
//! [`OverseerBackend`] is the single seam carrying all five: job
//! store, capability registry, DM sender, acceptance verifier,
//! worktree operations, announcer, and clock. The dispatch / verify
//! / tick logic in this file operates only through that seam, so it
//! stays independent of the sibling modules' settled APIs.
//!
//! Live-behavior boundary: announcements are best-effort and never
//! fail a state change (Python's `_say` swallows backend errors);
//! the seam's `announce` is therefore infallible by contract, and
//! git worktree operations are real only when the backend performs
//! them — this file never shells out to git itself.

use std::collections::HashMap;

/// Default claim lease in seconds, mirroring Python's
/// `LEASE_DEFAULT = 1800` (and jobs' lease default).
pub const LEASE_DEFAULT: i64 = 1800;

/// One acceptance check result, mirroring `mos.acceptance`'s
/// `{check, ok, detail}` dicts.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CheckResult {
    /// Check name, e.g. `"contains: foo"`.
    pub check: String,
    /// Whether the check passed.
    pub ok: bool,
    /// Human detail.
    pub detail: String,
}

/// One capability record, reduced to the field dispatch reads.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct CapabilityRecord {
    /// DM dead-drop secret, empty when none registered.
    pub dm: String,
}

/// SEAM (see module docs): the jobs / send / acceptance /
/// capabilities / gitops backend behind the overseer. Every method
/// corresponds to one Python call site; the overseer logic in this
/// file never touches Redis, the bus, or git directly.
pub trait OverseerBackend {
    /// Post a job with the given fields; returns the new job id
    /// (Python parses the `JOB <id>` line from `jobs.main` output —
    /// see [`parse_job_id`]; a backend may return the id directly).
    #[allow(clippy::too_many_arguments)]
    fn post_job(
        &mut self,
        title: &str,
        spec: &str,
        accept: &str,
        room: &str,
        lease: i64,
        branch: &str,
        base: &str,
    ) -> Result<String, String>;
    /// Nicks capable of all `requirements` (Python:
    /// `capabilities.find_for(reqs)`).
    fn find_for(&self, requirements: &[String]) -> Vec<String>;
    /// Capability record for a nick, if registered.
    fn capability(&self, nick: &str) -> Option<CapabilityRecord>;
    /// Send a DM; returns `(ok, detail)` where detail is the sender's
    /// stdout stripped, or its stderr stripped when stdout is empty
    /// (Python: `buf.getvalue().strip() or err.getvalue().strip()`).
    fn send_dm(&mut self, secret: &str, text: &str) -> (bool, String);
    /// Best-effort announcement; never fails the state change.
    fn announce(&mut self, room: &str, text: &str);
    /// Sweep expired leases; returns requeued job ids (Python parses
    /// `REQUEUED <jid>` lines from `jobs.main(["sweep"])` output —
    /// see [`parse_requeued_lines`]).
    fn sweep_requeued(&mut self) -> Vec<String>;
    /// Prune stale capability registrations; returns pruned nicks.
    /// Errors are recorded in the tick report, not raised.
    fn prune_stale(&mut self) -> Result<Vec<String>, String>;
    /// All job ids, in index order.
    fn job_ids(&self) -> Vec<String>;
    /// One job's hash, if it exists.
    fn job_get(&self, jid: &str) -> Option<HashMap<String, String>>;
    /// Set hash fields on a job.
    fn set_fields(&mut self, jid: &str, fields: &[(&str, String)]);
    /// Delete hash fields from a job.
    fn delete_fields(&mut self, jid: &str, fields: &[&str]);
    /// Delete the job's claim key (best-effort in Python: errors pass).
    fn delete_claim_key(&mut self, jid: &str);
    /// Verify acceptance text against a workdir; returns
    /// `(ok, results)` (Python: `acceptance.verify`).
    fn verify_acceptance(&self, accept: &str, workdir: &str) -> (bool, Vec<CheckResult>);
    /// Add a git worktree for a branch at a path (Python:
    /// `gitops.worktree_add`).
    fn worktree_add(&mut self, repo: &str, branch: &str, path: &str) -> Result<(), String>;
    /// Remove a git worktree (Python: `gitops.worktree_remove`).
    fn worktree_remove(&mut self, repo: &str, path: &str) -> Result<(), String>;
    /// Current Unix time in seconds (Python: `int(time.time())`).
    fn now_secs(&self) -> i64;
}

/// Parse a new job id from `jobs.main` post output, mirroring
/// Python's `_post_job`: the first line starting with `"JOB "`
/// supplies the id as its second word; anything else fails.
pub fn parse_job_id(output: &str) -> Result<String, String> {
    for line in output.lines() {
        if let Some(rest) = line.strip_prefix("JOB ") {
            if let Some(id) = rest.split_whitespace().next() {
                return Ok(id.to_string());
            }
        }
    }
    Err(format!("could not parse job id from: {output:?}"))
}

/// Parse `REQUEUED <jid>` lines from `jobs.main(["sweep"])` output,
/// mirroring the sweep parsing in Python's `tick()` (and
/// `reconcile.sweep_leases`).
pub fn parse_requeued_lines(output: &str) -> Vec<String> {
    output
        .lines()
        .filter_map(|line| {
            line.strip_prefix("REQUEUED ")
                .and_then(|rest| rest.split_whitespace().next())
                .map(str::to_string)
        })
        .collect()
}

/// Format acceptance results as a report, mirroring
/// `mos.acceptance.format_report`: one `"[PASS|FAIL] check --
/// detail"` line per result, joined with newlines.
pub fn format_report(results: &[CheckResult]) -> String {
    results
        .iter()
        .map(|r| {
            format!(
                "[{}] {} -- {}",
                if r.ok { "PASS" } else { "FAIL" },
                r.check,
                r.detail
            )
        })
        .collect::<Vec<_>>()
        .join("\n")
}

/// Truncate to the LAST `n` characters, mirroring Python's
/// `report[-2000:]` slicing in `_set_verified` and in the
/// acceptance-failure reopen. (Note the oddity, ported as-is: it is
/// a tail slice, not a head slice.)
pub fn truncate_tail(text: &str, n: usize) -> String {
    let chars: Vec<char> = text.chars().collect();
    if chars.len() <= n {
        text.to_string()
    } else {
        chars[chars.len() - n..].iter().collect()
    }
}

/// Normalize dispatch requirements, mirroring Python's
/// `[r.strip().lower() for r in requirements if r and r.strip()]`.
pub fn normalize_requirements(requirements: &[String]) -> Vec<String> {
    requirements
        .iter()
        .filter(|r| !r.trim().is_empty())
        .map(|r| r.trim().to_lowercase())
        .collect()
}

/// One DM result from dispatch: `(nick, dm_ok, detail)`.
pub type DmResult = (String, bool, String);

/// Post a job and DM every capable worker.
///
/// Returns `(jid, dm_results)`. Fails when the spec is empty
/// (Python: `ValueError("spec must not be empty")`) or when the
/// post fails. A worker with no DM secret registered yields
/// `(nick, false, "no DM secret registered")` and no DM is sent.
/// The DM text is `"JOB:<jid> <title>"` plus `" req=a,b"` when
/// requirements are present. Announces
/// `"DISPATCH:<jid> -> <n> worker(s)"` afterwards, best-effort.
#[allow(clippy::too_many_arguments)]
pub fn dispatch(
    backend: &mut dyn OverseerBackend,
    title: &str,
    spec: &str,
    accept: &str,
    requirements: &[String],
    room: &str,
    lease: i64,
    branch: &str,
    base: &str,
) -> Result<(String, Vec<DmResult>), String> {
    if spec.trim().is_empty() {
        return Err("spec must not be empty".to_string());
    }
    let reqs = normalize_requirements(requirements);
    let jid = backend.post_job(title, spec, accept, room, lease, branch, base)?;
    let mut dm_results = Vec::new();
    for nick in backend.find_for(&reqs) {
        let secret = backend.capability(&nick).map(|rec| rec.dm).unwrap_or_default();
        if secret.is_empty() {
            dm_results.push((nick, false, "no DM secret registered".to_string()));
            continue;
        }
        let mut text = format!("JOB:{jid} {title}");
        if !reqs.is_empty() {
            text += &format!(" req={}", reqs.join(","));
        }
        let (ok, detail) = backend.send_dm(&secret, &text);
        dm_results.push((nick, ok, detail));
    }
    backend.announce(room, &format!("DISPATCH:{jid} -> {} worker(s)", dm_results.len()));
    Ok((jid, dm_results))
}

/// Mark a job verified (or not), mirroring Python's `_set_verified`:
/// `verified` `"1"`/`"0"`, `verified_at` now, `verify_report` the
/// report's last 2000 characters.
pub fn set_verified(
    backend: &mut dyn OverseerBackend,
    jid: &str,
    ok: bool,
    report: &str,
) {
    let verified_at = backend.now_secs().to_string();
    backend.set_fields(
        jid,
        &[
            ("verified", if ok { "1".to_string() } else { "0".to_string() }),
            ("verified_at", verified_at),
            ("verify_report", truncate_tail(report, 2000)),
        ],
    );
}

/// Verify a done job's acceptance criteria.
///
/// Checks out the worker's branch (via git worktree) when repo,
/// branch and workdir base are all available; otherwise verifies
/// against `repo` directly (or `"."` when no repo is given). On
/// success marks verified=1 and announces `VERIFIED:<jid>`. On
/// failure requeues the job to open with the failure report as its
/// note, deletes the claim fields, deletes the claim key
/// (best-effort), and announces `REQUEUE:<jid> acceptance failed`.
///
/// Returns `(ok, report_text)`, or an error when the worktree
/// cannot be added (Python raises, and `tick` records it per job).
/// A missing job returns `(false, "no such job: <jid>")`; a job
/// whose status is not done returns `(false, "job <jid> is
/// <status>, not done")`; an already-verified job returns
/// `(true, "already verified")` without re-verifying.
pub fn verify_done(
    backend: &mut dyn OverseerBackend,
    jid: &str,
    repo: Option<&str>,
    workdir_base: Option<&str>,
) -> Result<(bool, String), String> {
    let h = match backend.job_get(jid) {
        Some(h) => h,
        None => return Ok((false, format!("no such job: {jid}"))),
    };
    let status = h.get("status").map(String::as_str).unwrap_or("None");
    if status != "done" {
        return Ok((false, format!("job {jid} is {status}, not done")));
    }
    if h.get("verified").map(String::as_str) == Some("1") {
        return Ok((true, "already verified".to_string()));
    }
    let room = h.get("room").cloned().unwrap_or_default();
    let accept = h.get("accept").cloned().unwrap_or_default();
    let branch = h.get("branch").cloned().unwrap_or_default();

    let mut workdir = repo.unwrap_or(".").to_string();
    let mut wt_path: Option<String> = None;
    if let (Some(repo), Some(base)) = (repo, workdir_base) {
        if !branch.is_empty() {
            let path = format!("{base}/verify-{jid}");
            wt_path = Some(path.clone());
            if let Err(e) = backend.worktree_add(repo, &branch, &path) {
                // Python's finally still attempts cleanup on failure.
                let _ = backend.worktree_remove(repo, &path);
                return Err(e);
            }
            workdir = path;
        }
    }
    let (ok, results) = backend.verify_acceptance(&accept, &workdir);
    let report = format_report(&results);
    if let (Some(path), Some(repo)) = (wt_path, repo) {
        if let Err(e) = backend.worktree_remove(repo, &path) {
            eprintln!("WARNING: worktree cleanup failed ({e})");
        }
    }

    if ok {
        set_verified(backend, jid, true, &report);
        backend.announce(&room, &format!("VERIFIED:{jid}"));
        return Ok((true, report));
    }
    // Acceptance failed: reopen for another worker, keep the evidence.
    backend.set_fields(
        jid,
        &[
            ("status", "open".to_string()),
            ("note", truncate_tail(&format!("acceptance failed:\n{report}"), 2000)),
        ],
    );
    backend.delete_fields(
        jid,
        &[
            "claim",
            "claim_host",
            "claimed_at",
            "lease_until",
            "result_commit",
            "verified",
            "verified_at",
            "verify_report",
        ],
    );
    backend.delete_claim_key(jid);
    backend.announce(&room, &format!("REQUEUE:{jid} acceptance failed"));
    Ok((false, report))
}

/// Job ids with status done and no verified=1 stamp, mirroring
/// Python's `_done_unverified` (a backend read failure yields no
/// ids here, as the Python `except` returns `[]`).
pub fn done_unverified(backend: &dyn OverseerBackend) -> Vec<String> {
    backend
        .job_ids()
        .into_iter()
        .filter(|jid| {
            backend.job_get(jid).is_some_and(|h| {
                h.get("status").map(String::as_str) == Some("done")
                    && h.get("verified").map(String::as_str) != Some("1")
            })
        })
        .collect()
}

/// One overseer pass report, mirroring Python's `tick()` dict.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct TickReport {
    /// Job ids whose expired leases were swept.
    pub swept: Vec<String>,
    /// Nicks whose stale registrations were pruned.
    pub pruned: Vec<String>,
    /// Job ids verified this pass.
    pub verified: Vec<String>,
    /// Job ids whose acceptance failed this pass.
    pub failed: Vec<String>,
    /// Per-job errors, `"prune_stale: ..."` / `"verify <jid>: ..."`.
    pub errors: Vec<String>,
}

/// One overseer pass: sweep expired leases, prune stale capability
/// registrations, verify done-but-unverified jobs. Prune and
/// per-job verify errors are recorded in the report, not raised.
pub fn tick(
    backend: &mut dyn OverseerBackend,
    repo: Option<&str>,
    workdir_base: Option<&str>,
) -> TickReport {
    let mut report = TickReport::default();
    report.swept = backend.sweep_requeued();
    match backend.prune_stale() {
        Ok(nicks) => report.pruned = nicks,
        Err(e) => report.errors.push(format!("prune_stale: {e}")),
    }
    for jid in done_unverified(backend) {
        match verify_done(backend, &jid, repo, workdir_base) {
            Ok((true, _)) => report.verified.push(jid),
            Ok((false, _)) => report.failed.push(jid),
            Err(e) => report.errors.push(format!("verify {jid}: {e}")),
        }
    }
    report
}

#[cfg(test)]
mod tests {
    use super::*;

    struct FakeBackend {
        jobs: HashMap<String, HashMap<String, String>>,
        order: Vec<String>,
        caps: HashMap<String, CapabilityRecord>,
        capable: Vec<String>,
        dm_log: Vec<(String, String)>,
        dm_ok: bool,
        announcements: Vec<(String, String)>,
        swept: Vec<String>,
        prune: Result<Vec<String>, String>,
        accept_ok: bool,
        worktree_fail: bool,
        claim_keys_deleted: Vec<String>,
        now: i64,
    }

    impl FakeBackend {
        fn new() -> Self {
            Self {
                jobs: HashMap::new(),
                order: Vec::new(),
                caps: HashMap::new(),
                capable: Vec::new(),
                dm_log: Vec::new(),
                dm_ok: true,
                announcements: Vec::new(),
                swept: Vec::new(),
                prune: Ok(vec![]),
                accept_ok: true,
                worktree_fail: false,
                claim_keys_deleted: Vec::new(),
                now: 10000,
            }
        }
        fn add_job(&mut self, jid: &str, pairs: &[(&str, &str)]) {
            self.jobs.insert(
                jid.to_string(),
                pairs.iter().map(|(k, v)| (k.to_string(), v.to_string())).collect(),
            );
            self.order.push(jid.to_string());
        }
    }

    impl OverseerBackend for FakeBackend {
        fn post_job(&mut self, _t: &str, _s: &str, _a: &str, _r: &str, _l: i64, _b: &str, _base: &str) -> Result<String, String> {
            Ok("job-1".to_string())
        }
        fn find_for(&self, _reqs: &[String]) -> Vec<String> {
            self.capable.clone()
        }
        fn capability(&self, nick: &str) -> Option<CapabilityRecord> {
            self.caps.get(nick).cloned()
        }
        fn send_dm(&mut self, secret: &str, text: &str) -> (bool, String) {
            self.dm_log.push((secret.to_string(), text.to_string()));
            (self.dm_ok, "sent".to_string())
        }
        fn announce(&mut self, room: &str, text: &str) {
            self.announcements.push((room.to_string(), text.to_string()));
        }
        fn sweep_requeued(&mut self) -> Vec<String> {
            self.swept.clone()
        }
        fn prune_stale(&mut self) -> Result<Vec<String>, String> {
            self.prune.clone()
        }
        fn job_ids(&self) -> Vec<String> {
            self.order.clone()
        }
        fn job_get(&self, jid: &str) -> Option<HashMap<String, String>> {
            self.jobs.get(jid).cloned()
        }
        fn set_fields(&mut self, jid: &str, fields: &[(&str, String)]) {
            if let Some(h) = self.jobs.get_mut(jid) {
                for (k, v) in fields {
                    h.insert(k.to_string(), v.clone());
                }
            }
        }
        fn delete_fields(&mut self, jid: &str, fields: &[&str]) {
            if let Some(h) = self.jobs.get_mut(jid) {
                for f in fields {
                    h.remove(*f);
                }
            }
        }
        fn delete_claim_key(&mut self, jid: &str) {
            self.claim_keys_deleted.push(jid.to_string());
        }
        fn verify_acceptance(&self, _accept: &str, _workdir: &str) -> (bool, Vec<CheckResult>) {
            (
                self.accept_ok,
                vec![CheckResult { check: "contains: done".to_string(), ok: self.accept_ok, detail: "found".to_string() }],
            )
        }
        fn worktree_add(&mut self, _r: &str, _b: &str, _p: &str) -> Result<(), String> {
            if self.worktree_fail {
                Err("git failed".to_string())
            } else {
                Ok(())
            }
        }
        fn worktree_remove(&mut self, _r: &str, _p: &str) -> Result<(), String> {
            Ok(())
        }
        fn now_secs(&self) -> i64 {
            self.now
        }
    }

    #[test]
    fn dispatch_posts_and_dms_capable_workers_from_module_behavior() {
        let mut backend = FakeBackend::new();
        backend.capable = vec!["ana".to_string(), "bob".to_string()];
        backend.caps.insert("ana".to_string(), CapabilityRecord { dm: "secret-ana".to_string() });
        let (jid, results) = dispatch(
            &mut backend,
            "Do thing",
            "Goal: do thing.",
            "",
            &[" Python ".to_string()],
            "build",
            LEASE_DEFAULT,
            "",
            "",
        )
        .unwrap();
        assert_eq!(jid, "job-1");
        assert_eq!(results.len(), 2);
        assert_eq!(results[0], ("ana".to_string(), true, "sent".to_string()));
        assert_eq!(results[1], ("bob".to_string(), false, "no DM secret registered".to_string()));
        assert_eq!(backend.dm_log.len(), 1);
        assert_eq!(backend.dm_log[0].1, "JOB:job-1 Do thing req=python");
        assert!(backend.announcements.iter().any(|(_, t)| t == "DISPATCH:job-1 -> 2 worker(s)"));
    }

    #[test]
    fn dispatch_empty_spec_fails_and_no_dm_sent() {
        let mut backend = FakeBackend::new();
        backend.capable = vec!["ana".to_string()];
        let err = dispatch(&mut backend, "T", "   ", "", &[], "", LEASE_DEFAULT, "", "").unwrap_err();
        assert_eq!(err, "spec must not be empty");
        assert!(backend.dm_log.is_empty());
    }

    #[test]
    fn verify_done_success_marks_verified_and_announces() {
        let mut backend = FakeBackend::new();
        backend.add_job("j1", &[("status", "done"), ("room", "build"), ("accept", "contains: done")]);
        let (ok, report) = verify_done(&mut backend, "j1", None, None).unwrap();
        assert!(ok);
        assert!(report.contains("[PASS]"));
        let h = backend.job_get("j1").unwrap();
        assert_eq!(h.get("verified").map(String::as_str), Some("1"));
        assert_eq!(h.get("verified_at").map(String::as_str), Some("10000"));
        assert!(backend.announcements.iter().any(|(_, t)| t == "VERIFIED:j1"));
    }

    #[test]
    fn verify_done_failure_requeues_with_report_and_clears_claim() {
        let mut backend = FakeBackend::new();
        backend.accept_ok = false;
        backend.add_job(
            "j2",
            &[
                ("status", "done"),
                ("room", "build"),
                ("claim", "ana"),
                ("claimed_at", "9000"),
                ("verified", "0"),
            ],
        );
        let (ok, _report) = verify_done(&mut backend, "j2", None, None).unwrap();
        assert!(!ok);
        let h = backend.job_get("j2").unwrap();
        assert_eq!(h.get("status").map(String::as_str), Some("open"));
        assert!(h.get("note").unwrap().starts_with("acceptance failed:\n"));
        assert!(!h.contains_key("claim"));
        assert!(!h.contains_key("claimed_at"));
        assert_eq!(backend.claim_keys_deleted, vec!["j2"]);
        assert!(backend.announcements.iter().any(|(_, t)| t == "REQUEUE:j2 acceptance failed"));
    }

    #[test]
    fn verify_done_guards_missing_not_done_already_verified() {
        let mut backend = FakeBackend::new();
        assert_eq!(
            verify_done(&mut backend, "nope", None, None).unwrap(),
            (false, "no such job: nope".to_string())
        );
        backend.add_job("j3", &[("status", "open")]);
        assert_eq!(
            verify_done(&mut backend, "j3", None, None).unwrap(),
            (false, "job j3 is open, not done".to_string())
        );
        backend.add_job("j4", &[("status", "done"), ("verified", "1")]);
        assert_eq!(
            verify_done(&mut backend, "j4", None, None).unwrap(),
            (true, "already verified".to_string())
        );
    }

    #[test]
    fn verify_done_worktree_failure_is_error_and_tick_records_it() {
        let mut backend = FakeBackend::new();
        backend.worktree_fail = true;
        backend.add_job(
            "j5",
            &[("status", "done"), ("branch", "feat"), ("room", "build")],
        );
        assert!(verify_done(&mut backend, "j5", Some("/repo"), Some("/tmp/wt")).is_err());
        let mut backend = FakeBackend::new();
        backend.worktree_fail = true;
        backend.swept = vec!["swept-1".to_string()];
        backend.prune = Err("prune boom".to_string());
        backend.add_job("j5", &[("status", "done"), ("branch", "feat"), ("room", "build")]);
        let report = tick(&mut backend, Some("/repo"), Some("/tmp/wt"));
        assert_eq!(report.swept, vec!["swept-1"]);
        assert!(report.errors.iter().any(|e| e.starts_with("prune_stale: ")));
        assert!(report.errors.iter().any(|e| e.starts_with("verify j5: ")));
        assert!(report.verified.is_empty() && report.failed.is_empty());
    }

    #[test]
    fn tick_verifies_done_jobs_and_reports_failed() {
        let mut backend = FakeBackend::new();
        backend.accept_ok = false;
        backend.add_job("a", &[("status", "done")]);
        backend.add_job("b", &[("status", "done"), ("verified", "1")]);
        backend.add_job("c", &[("status", "open")]);
        let report = tick(&mut backend, None, None);
        assert_eq!(report.failed, vec!["a"]);
        assert!(report.verified.is_empty());
        assert!(report.errors.is_empty());
    }

    #[test]
    fn parse_helpers_mirror_python() {
        assert_eq!(parse_job_id("noise\nJOB abc123\n"), Ok("abc123".to_string()));
        assert!(parse_job_id("no job here").is_err());
        assert_eq!(
            parse_requeued_lines("REQUEUED j1\nnoise\nREQUEUED j2\n"),
            vec!["j1", "j2"]
        );
        assert_eq!(truncate_tail("abcdef", 4), "cdef");
        assert_eq!(truncate_tail("abc", 10), "abc");
        assert_eq!(
            normalize_requirements(&[" Python ".to_string(), "  ".to_string(), "DOCS".to_string()]),
            vec!["python", "docs"]
        );
        assert_eq!(LEASE_DEFAULT, 1800);
    }
}
