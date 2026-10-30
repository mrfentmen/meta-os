//! MOS command line port (`os/mos/cli.py`): the overseer's and worker's
//! hands.
//!
//! Usage (mirrors the Python CLI):
//! ```text
//! mos.py register --caps python,testing --dm SECRET [--roles builder]
//! mos.py caps
//! mos.py dispatch --title T --spec SPEC [--accept ACCEPT] [--req python]
//!                 [--room R] [--lease SECS] [--branch B]
//! mos.py tick [--repo PATH --workdir-base PATH]
//! mos.py verify <jid> [--repo PATH --workdir-base PATH]
//! mos.py worker --dm SECRET --caps python [--once]
//! mos.py reconcile
//! mos.py review --repo PATH --branch B [--base main]
//! mos.py merge --repo PATH --branch B [--base main]
//! ```
//! Spec/accept may be given inline or via @file. Never prints the token.
//!
//! Backend operations (capabilities registry, overseer, worker, reconcile,
//! gitops) live in the owning crates (B16/B18/B19/B21/B22) and are not
//! merged to main yet, so this module dispatches through traits — the
//! same seam pattern the B21 port uses for its overseer backend. The
//! `git` module provides a real git backend for the review/merge
//! commands, which are the only gitops operations this CLI exposes.
//!
//! Approximations, all noted here rather than hidden:
//! - Argument errors produce a short usage line and exit code 2; the
//!   exact argparse help/error text is not reproduced verbatim.
//! - `expand_text` on an unreadable @file returns a clean error instead
//!   of a Python traceback.
//! - The register nick is a caller-supplied parameter; Python reads the
//!   `relay_common.NICK` global (excluded relay code).
//! - `worker`'s `job_get` header is dropped: the CLI prints only the spec.

use std::collections::HashMap;

/// Outcome of one CLI invocation: exit code plus captured stdout/stderr.
/// Mirrors the `CmdOutcome` shape the B16 port uses.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CliOutcome {
    /// Process exit code.
    pub code: i32,
    /// Captured stdout (each printed line terminated by `\n`).
    pub out: String,
    /// Captured stderr (each printed line terminated by `\n`).
    pub err: String,
}

impl CliOutcome {
    /// Build an outcome from line lists, joining each with `\n`.
    fn from_lines(code: i32, out: &[String], err: &[String]) -> CliOutcome {
        let join = |lines: &[String]| -> String {
            if lines.is_empty() {
                String::new()
            } else {
                let mut s = lines.join("\n");
                s.push('\n');
                s
            }
        };
        CliOutcome {
            code,
            out: join(out),
            err: join(err),
        }
    }
}

/// One registered agent's record, as printed by the `caps` command.
/// Missing fields print as empty strings, matching Python's `.get(..., '')`.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct AgentRecord {
    /// Comma-separated capabilities string.
    pub caps: String,
    /// Roles string.
    pub roles: String,
    /// Host string.
    pub host: String,
    /// Updated timestamp string.
    pub updated: String,
}

/// Capabilities-registry backend (owns the `register` / `caps` commands).
/// The real implementation lives in the B18 crate (`os-identity`).
pub trait CapabilitiesBackend {
    /// Register an agent; mirrors `capabilities.register`.
    fn register(
        &mut self,
        nick: &str,
        caps: &[String],
        roles: &str,
        max_jobs: i64,
        dm_secret: &str,
    ) -> Result<(), String>;
    /// All registered agents by nick.
    fn agents(&self) -> HashMap<String, AgentRecord>;
}

/// One overseer tick report, printed by the `tick` command.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct TickReport {
    /// Job ids swept.
    pub swept: Vec<String>,
    /// Nicks pruned.
    pub pruned: Vec<String>,
    /// Job ids verified.
    pub verified: Vec<String>,
    /// Job ids whose acceptance failed.
    pub failed: Vec<String>,
    /// Error lines (go to stderr; any error makes the exit code 2).
    pub errors: Vec<String>,
}

/// Overseer backend (owns `dispatch` / `tick` / `verify`).
/// The real implementation lives in the B21 crate (`os-supervisor`).
pub trait OverseerBackend {
    /// Dispatch a job; returns the job id and one (nick, ok, detail)
    /// triple per DM sent. Mirrors `overseer.dispatch`.
    #[allow(clippy::too_many_arguments)]
    fn dispatch(
        &mut self,
        title: &str,
        spec: &str,
        accept: &str,
        requirements: &[String],
        room: &str,
        lease: i64,
        branch: &str,
        base: &str,
    ) -> (String, Vec<(String, bool, String)>);
    /// One overseer pass. Mirrors `overseer.tick`.
    fn tick(&self, repo: Option<&str>, workdir_base: Option<&str>) -> TickReport;
    /// Verify a done job; returns (ok, report). Mirrors `overseer.verify_done`.
    fn verify_done(
        &self,
        jid: &str,
        repo: Option<&str>,
        workdir_base: Option<&str>,
    ) -> (bool, String);
}

/// Worker backend (owns the `worker --once` cycle).
/// The real implementation lives in the B22 crate (`os-worker`).
pub trait WorkerBackend {
    /// Register this worker. Mirrors `Worker.register`.
    fn register(&mut self);
    /// Renew claims. Mirrors `Worker.heartbeat`.
    fn heartbeat(&mut self);
    /// Poll DMs; returns (jid, title, requirements) per new dispatch.
    /// Mirrors `Worker.poll_dms`.
    fn poll_dms(&mut self) -> Vec<(String, String, Vec<String>)>;
    /// Whether this worker covers the requirements. Mirrors `Worker._matches`.
    fn matches(&self, reqs: &[String]) -> bool;
    /// Claim a job; returns (ok, detail). Mirrors `Worker._claim`.
    fn claim(&mut self, jid: &str) -> (bool, String);
    /// Fetch a job's spec. Mirrors `jobs.job_get` (header dropped: the
    /// CLI prints only the spec).
    fn job_spec(&self, jid: &str) -> String;
}

/// Reconcile backend (owns the `reconcile` command).
/// The real implementation lives in the B21 crate (`os-supervisor`).
pub trait ReconcileBackend {
    /// Run recovery; the return value is the process exit code.
    /// Mirrors `reconcile.main([])`.
    fn main(&self, args: &[String]) -> i32;
}

/// Review summary, as printed by the `review` command.
/// Mirrors `gitops.review_branch` (see the `git` module).
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ReviewSummary {
    /// Branch under review.
    pub branch: String,
    /// Base branch.
    pub base: String,
    /// Files changed (three-dot diff, name only).
    pub files: Vec<String>,
    /// Three-dot diff stat (stripped; empty when no diff).
    pub stat: String,
    /// Commit lines (`%h %s`, two-dot log).
    pub commits: Vec<String>,
    /// Number of commits.
    pub commit_count: usize,
}

/// Git error, printed as `ERROR: <message>` by review/merge.
/// Mirrors `gitops.GitError`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitError(pub String);

impl std::fmt::Display for GitError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

/// Gitops backend (owns `review` / `merge`).
/// The `git` module provides a real git-CLI implementation; tests use fakes.
pub trait GitopsBackend {
    /// Review a branch. Mirrors `gitops.review_branch`.
    fn review_branch(
        &self,
        repo: &str,
        branch: &str,
        base: &str,
    ) -> Result<ReviewSummary, GitError>;
    /// Approve-merge a branch; returns the merge commit hash.
    /// Mirrors `gitops.approve_merge`.
    fn approve_merge(
        &self,
        repo: &str,
        branch: &str,
        base: &str,
    ) -> Result<String, GitError>;
}

/// All backends the CLI dispatches through, as trait objects.
pub struct Backends<'a> {
    /// Capabilities registry backend.
    pub caps: &'a mut dyn CapabilitiesBackend,
    /// Overseer backend.
    pub overseer: &'a mut dyn OverseerBackend,
    /// Worker backend.
    pub worker: &'a mut dyn WorkerBackend,
    /// Reconcile backend.
    pub reconcile: &'a dyn ReconcileBackend,
    /// Gitops backend.
    pub gitops: &'a dyn GitopsBackend,
}

/// Expand a spec/accept value: `@file` reads the file (with `~` expanded
/// to the home directory), anything else passes through, empty stays empty.
/// Mirrors `cli._text`. A missing file is an error (Python would traceback).
pub fn expand_text(v: &str) -> Result<String, String> {
    if let Some(path) = v.strip_prefix('@') {
        let expanded = if let Some(rest) = path.strip_prefix("~/") {
            match std::env::var("HOME") {
                Ok(home) => format!("{home}/{rest}"),
                Err(_) => path.to_string(),
            }
        } else {
            path.to_string()
        };
        std::fs::read_to_string(&expanded)
            .map_err(|e| format!("cannot read {expanded}: {e}"))
    } else {
        Ok(v.to_string())
    }
}

/// Split a comma-separated caps/req value, dropping entries that are empty
/// or whitespace-only, but keeping the remaining entries verbatim (not
/// stripped). Mirrors the list comprehensions in `cmd_register`,
/// `cmd_dispatch`, and `cmd_worker` — including the oddity that
/// `" testing "` keeps its spaces in the sorted output.
pub fn split_caps(s: &str) -> Vec<String> {
    s.split(',').filter(|c| !c.trim().is_empty()).map(str::to_string).collect()
}

/// `register` command: `REGISTERED <nick>: <sorted caps>`.
/// `nick` is caller-supplied (Python reads the relay `NICK` global).
pub fn cmd_register(
    nick: &str,
    caps_arg: &str,
    roles: &str,
    max_jobs: i64,
    dm: &str,
    backend: &mut dyn CapabilitiesBackend,
) -> CliOutcome {
    let caps = split_caps(caps_arg);
    match backend.register(nick, &caps, roles, max_jobs, dm) {
        Ok(()) => {
            let mut sorted = caps.clone();
            sorted.sort();
            CliOutcome::from_lines(
                0,
                &[format!("REGISTERED {}: {}", nick, sorted.join(","))],
                &[],
            )
        }
        Err(e) => CliOutcome::from_lines(1, &[], &[format!("ERROR: {e}")]),
    }
}

/// `caps` command: `NO_AGENTS`, or one sorted line per agent.
pub fn cmd_caps(backend: &dyn CapabilitiesBackend) -> CliOutcome {
    let agents = backend.agents();
    if agents.is_empty() {
        return CliOutcome::from_lines(0, &["NO_AGENTS".to_string()], &[]);
    }
    let mut nicks: Vec<&String> = agents.keys().collect();
    nicks.sort();
    let lines: Vec<String> = nicks
        .iter()
        .map(|nick| {
            let r = &agents[*nick];
            format!(
                "{}: caps={} roles={} host={} updated={}",
                nick, r.caps, r.roles, r.host, r.updated
            )
        })
        .collect();
    CliOutcome::from_lines(0, &lines, &[])
}

/// `dispatch` command: `DISPATCHED <jid>` plus one DM line per worker,
/// or the no-capable-workers line.
#[allow(clippy::too_many_arguments)]
pub fn cmd_dispatch(
    title: &str,
    spec_arg: &str,
    accept_arg: &str,
    req_arg: &str,
    room: &str,
    lease: i64,
    branch: &str,
    base: &str,
    backend: &mut dyn OverseerBackend,
) -> CliOutcome {
    let spec = match expand_text(spec_arg) {
        Ok(s) => s,
        Err(e) => return CliOutcome::from_lines(1, &[], &[format!("ERROR: {e}")]),
    };
    let accept = match expand_text(accept_arg) {
        Ok(s) => s,
        Err(e) => return CliOutcome::from_lines(1, &[], &[format!("ERROR: {e}")]),
    };
    let reqs = split_caps(req_arg);
    let (jid, dms) = backend.dispatch(title, &spec, &accept, &reqs, room, lease, branch, base);
    let mut lines = vec![format!("DISPATCHED {jid}")];
    for (nick, ok, detail) in &dms {
        lines.push(format!(
            "  DM {}: {} {}",
            nick,
            if *ok { "OK" } else { "FAIL" },
            detail
        ));
    }
    if dms.is_empty() {
        lines.push("  (no capable workers registered)".to_string());
    }
    CliOutcome::from_lines(0, &lines, &[])
}

/// `tick` command: swept/pruned/verified/failed lines, errors to stderr,
/// `TICK_CLEAN` when everything is empty; exit 2 when errors exist.
pub fn cmd_tick(
    repo: Option<&str>,
    workdir_base: Option<&str>,
    backend: &dyn OverseerBackend,
) -> CliOutcome {
    let rep = backend.tick(repo, workdir_base);
    let mut out: Vec<String> = Vec::new();
    for jid in &rep.swept {
        out.push(format!("SWEPT {jid}"));
    }
    for nick in &rep.pruned {
        out.push(format!("PRUNED {nick}"));
    }
    for jid in &rep.verified {
        out.push(format!("VERIFIED {jid}"));
    }
    for jid in &rep.failed {
        out.push(format!("ACCEPTANCE_FAILED {jid}"));
    }
    let mut err: Vec<String> = Vec::new();
    for e in &rep.errors {
        err.push(format!("ERROR {e}"));
    }
    if out.is_empty() && err.is_empty() {
        out.push("TICK_CLEAN".to_string());
    }
    let code = if rep.errors.is_empty() { 0 } else { 2 };
    CliOutcome::from_lines(code, &out, &err)
}

/// `verify` command: report line, then `VERIFIED`/`NOT_VERIFIED`.
pub fn cmd_verify(
    jid: &str,
    repo: Option<&str>,
    workdir_base: Option<&str>,
    backend: &dyn OverseerBackend,
) -> CliOutcome {
    let (ok, report) = backend.verify_done(jid, repo, workdir_base);
    CliOutcome::from_lines(
        if ok { 0 } else { 1 },
        &[report, if ok { "VERIFIED".to_string() } else { "NOT_VERIFIED".to_string() }],
        &[],
    )
}

/// `worker --once` cycle: register, heartbeat, then one poll+claim pass.
/// Prints `SKIP` / `CLAIMED` + spec / `CLAIM_FAILED` / `NO_DISPATCHES`.
/// The non-`--once` loop mode is handled in `run_cli` (stderr + exit 2).
pub fn cmd_worker_once(backend: &mut dyn WorkerBackend) -> CliOutcome {
    backend.register();
    backend.heartbeat();
    let found = backend.poll_dms();
    let mut lines: Vec<String> = Vec::new();
    let mut claimed: Option<String> = None;
    for (jid, title, reqs) in &found {
        if !backend.matches(reqs) {
            let mut sorted = reqs.clone();
            sorted.sort();
            lines.push(format!("SKIP {} (req {})", jid, sorted.join(",")));
            continue;
        }
        let (ok, _) = backend.claim(jid);
        if ok {
            claimed = Some(jid.clone());
            let spec = backend.job_spec(jid);
            lines.push(format!("CLAIMED {jid}: {title}"));
            lines.push("--- spec ---".to_string());
            lines.push(spec);
            break;
        }
        lines.push(format!("CLAIM_FAILED {jid}"));
    }
    if claimed.is_none() && found.is_empty() {
        lines.push("NO_DISPATCHES".to_string());
    }
    CliOutcome::from_lines(0, &lines, &[])
}

/// `reconcile` command: exit code passes through from the backend.
pub fn cmd_reconcile(backend: &dyn ReconcileBackend) -> CliOutcome {
    CliOutcome::from_lines(backend.main(&[]), &[], &[])
}

/// `review` command: branch summary, commit lines, stat when non-empty.
/// Git errors go to stderr with exit code 2.
pub fn cmd_review(
    repo: &str,
    branch: &str,
    base: &str,
    backend: &dyn GitopsBackend,
) -> CliOutcome {
    match backend.review_branch(repo, branch, base) {
        Err(e) => CliOutcome::from_lines(2, &[], &[format!("ERROR: {e}")]),
        Ok(r) => {
            let mut lines = vec![format!(
                "branch {} vs {}: {} commits, {} files",
                r.branch,
                r.base,
                r.commit_count,
                r.files.len()
            )];
            for c in &r.commits {
                lines.push(format!("  {c}"));
            }
            if !r.stat.is_empty() {
                lines.push(r.stat.clone());
            }
            CliOutcome::from_lines(0, &lines, &[])
        }
    }
}

/// `merge` command: `MERGED <branch> -> <base>: <hash>`.
/// Git errors go to stderr with exit code 2.
pub fn cmd_merge(
    repo: &str,
    branch: &str,
    base: &str,
    backend: &dyn GitopsBackend,
) -> CliOutcome {
    match backend.approve_merge(repo, branch, base) {
        Err(e) => CliOutcome::from_lines(2, &[], &[format!("ERROR: {e}")]),
        Ok(h) => CliOutcome::from_lines(
            0,
            &[format!("MERGED {branch} -> {base}: {h}")],
            &[],
        ),
    }
}

/// Short usage text for argument errors (approximation: argparse's exact
/// help/error text is not reproduced; the exit code 2 contract is kept).
const USAGE: &str = "usage: mos.py {register|caps|dispatch|tick|verify|worker|reconcile|review|merge}";

/// Parse one `--flag value` / `--flag=value` pair. Returns the value, or
/// `None` when the flag takes no value / is missing one.
fn flag_value(args: &[String], i: &mut usize, flag: &str) -> Option<String> {
    let arg = &args[*i];
    if let Some(v) = arg.strip_prefix(&format!("{flag}=")) {
        return Some(v.to_string());
    }
    if arg == flag {
        if *i + 1 < args.len() {
            *i += 1;
            return Some(args[*i].clone());
        }
        return None;
    }
    None
}

/// Collect all `--flag value` occurrences for one flag name.
fn take_flag(args: &[String], flag: &str) -> (Vec<String>, Vec<String>) {
    let mut values = Vec::new();
    let mut rest = Vec::new();
    let mut i = 0;
    while i < args.len() {
        if args[i] == flag || args[i].starts_with(&format!("{flag}=")) {
            match flag_value(args, &mut i, flag) {
                Some(v) => values.push(v),
                None => {
                    rest.push(format!("{flag} (missing value)"));
                }
            }
        } else {
            rest.push(args[i].clone());
        }
        i += 1;
    }
    (values, rest)
}

/// Parse an integer flag value; on failure returns an argument error.
fn parse_int(v: Option<String>, default: i64) -> Result<i64, CliOutcome> {
    match v {
        None => Ok(default),
        Some(s) => s.parse::<i64>().map_err(|_| {
            CliOutcome::from_lines(2, &[], &[USAGE.to_string()])
        }),
    }
}

/// First positional argument, if any.
fn positional(args: &[String]) -> Option<String> {
    args.iter().find(|a| !a.starts_with('-')).cloned()
}

/// The full CLI entry point, mirroring `mos.main(argv)`.
/// `argv` excludes the program name. Unknown commands, missing required
/// arguments, unknown flags, and bad integers all yield usage + exit 2.
pub fn run_cli(argv: &[String], backends: &mut Backends<'_>) -> CliOutcome {
    if argv.is_empty() {
        return CliOutcome::from_lines(2, &[], &[USAGE.to_string()]);
    }
    let cmd = argv[0].as_str();
    let rest = &argv[1..];
    match cmd {
        "register" => {
            let (caps, r1) = take_flag(rest, "--caps");
            let (dm, r2) = take_flag(&r1, "--dm");
            let (roles, r3) = take_flag(&r2, "--roles");
            let (max_jobs, r4) = take_flag(&r3, "--max-jobs");
            if caps.is_empty() || !r4.is_empty() || positional(&r4).is_some() {
                return CliOutcome::from_lines(2, &[], &[USAGE.to_string()]);
            }
            let max = match parse_int(max_jobs.into_iter().next(), 1) {
                Ok(v) => v,
                Err(e) => return e,
            };
            // Nick comes from the caller in this port (Python reads the
            // relay NICK global); the env override keeps tests honest.
            let nick = std::env::var("MOS_NICK").unwrap_or_default();
            cmd_register(
                &nick,
                caps.first().map(String::as_str).unwrap_or(""),
                roles.first().map(String::as_str).unwrap_or(""),
                max,
                dm.first().map(String::as_str).unwrap_or(""),
                &mut *backends.caps,
            )
        }
        "caps" => {
            if !rest.is_empty() {
                return CliOutcome::from_lines(2, &[], &[USAGE.to_string()]);
            }
            cmd_caps(&*backends.caps)
        }
        "dispatch" => {
            let (title, r1) = take_flag(rest, "--title");
            let (spec, r2) = take_flag(&r1, "--spec");
            let (accept, r3) = take_flag(&r2, "--accept");
            let (req, r4) = take_flag(&r3, "--req");
            let (room, r5) = take_flag(&r4, "--room");
            let (lease, r6) = take_flag(&r5, "--lease");
            let (branch, r7) = take_flag(&r6, "--branch");
            let (base, r8) = take_flag(&r7, "--base");
            if title.is_empty() || spec.is_empty() || !r8.is_empty() || positional(&r8).is_some()
            {
                return CliOutcome::from_lines(2, &[], &[USAGE.to_string()]);
            }
            let lease_v = match parse_int(lease.into_iter().next(), 1800) {
                Ok(v) => v,
                Err(e) => return e,
            };
            cmd_dispatch(
                title.first().map(String::as_str).unwrap_or(""),
                spec.first().map(String::as_str).unwrap_or(""),
                accept.first().map(String::as_str).unwrap_or(""),
                req.first().map(String::as_str).unwrap_or(""),
                room.first().map(String::as_str).unwrap_or(""),
                lease_v,
                branch.first().map(String::as_str).unwrap_or(""),
                base.first().map(String::as_str).unwrap_or(""),
                &mut *&mut *backends.overseer,
            )
        }
        "tick" => {
            let (repo, r1) = take_flag(rest, "--repo");
            let (base, r2) = take_flag(&r1, "--workdir-base");
            if !r2.is_empty() || positional(&r2).is_some() {
                return CliOutcome::from_lines(2, &[], &[USAGE.to_string()]);
            }
            cmd_tick(
                repo.first().map(String::as_str),
                base.first().map(String::as_str),
                &mut *&mut *backends.overseer,
            )
        }
        "verify" => {
            let (repo, r1) = take_flag(rest, "--repo");
            let (base, r2) = take_flag(&r1, "--workdir-base");
            let jid = positional(&r2);
            if jid.is_none() || !r2.is_empty() {
                return CliOutcome::from_lines(2, &[], &[USAGE.to_string()]);
            }
            cmd_verify(
                jid.as_deref().unwrap_or(""),
                repo.first().map(String::as_str),
                base.first().map(String::as_str),
                &mut *&mut *backends.overseer,
            )
        }
        "worker" => {
            let (dm, r1) = take_flag(rest, "--dm");
            let (caps, r2) = take_flag(&r1, "--caps");
            let (roles, r3) = take_flag(&r2, "--roles");
            let (workdir, r4) = take_flag(&r3, "--workdir");
            let (lease, r5) = take_flag(&r4, "--lease");
            let once = r5.iter().any(|a| a == "--once");
            let r6: Vec<String> =
                r5.iter().filter(|a| *a != "--once").cloned().collect();
            if !r6.is_empty() || positional(&r6).is_some() {
                return CliOutcome::from_lines(2, &[], &[USAGE.to_string()]);
            }
            let _ = (dm, caps, roles, workdir, lease);
            if once {
                // The worker handle is caller-constructed (dm/caps/roles/
                // workdir/lease are construction parameters in Python);
                // the backend trait carries the constructed worker.
                cmd_worker_once(&mut *backends.worker)
            } else {
                CliOutcome::from_lines(
                    2,
                    &[],
                    &["worker loop: agent-driven; use --once per cycle".to_string()],
                )
            }
        }
        "reconcile" => {
            if !rest.is_empty() {
                return CliOutcome::from_lines(2, &[], &[USAGE.to_string()]);
            }
            cmd_reconcile(&*backends.reconcile)
        }
        "review" => {
            let (repo, r1) = take_flag(rest, "--repo");
            let (branch, r2) = take_flag(&r1, "--branch");
            let (base, r3) = take_flag(&r2, "--base");
            if repo.is_empty() || branch.is_empty() || !r3.is_empty() || positional(&r3).is_some()
            {
                return CliOutcome::from_lines(2, &[], &[USAGE.to_string()]);
            }
            cmd_review(
                repo.first().map(String::as_str).unwrap_or(""),
                branch.first().map(String::as_str).unwrap_or(""),
                base.first().map(String::as_str).unwrap_or("main"),
                &*backends.gitops,
            )
        }
        "merge" => {
            let (repo, r1) = take_flag(rest, "--repo");
            let (branch, r2) = take_flag(&r1, "--branch");
            let (base, r3) = take_flag(&r2, "--base");
            if repo.is_empty() || branch.is_empty() || !r3.is_empty() || positional(&r3).is_some()
            {
                return CliOutcome::from_lines(2, &[], &[USAGE.to_string()]);
            }
            cmd_merge(
                repo.first().map(String::as_str).unwrap_or(""),
                branch.first().map(String::as_str).unwrap_or(""),
                base.first().map(String::as_str).unwrap_or("main"),
                &*backends.gitops,
            )
        }
        _ => CliOutcome::from_lines(2, &[], &[USAGE.to_string()]),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Fake capabilities backend recording registrations.
    struct FakeCaps {
        agents: HashMap<String, AgentRecord>,
        registered: Vec<(String, Vec<String>, String, i64, String)>,
        fail: bool,
    }

    impl CapabilitiesBackend for FakeCaps {
        fn register(
            &mut self,
            nick: &str,
            caps: &[String],
            roles: &str,
            max_jobs: i64,
            dm_secret: &str,
        ) -> Result<(), String> {
            if self.fail {
                return Err("store down".to_string());
            }
            self.registered.push((
                nick.to_string(),
                caps.to_vec(),
                roles.to_string(),
                max_jobs,
                dm_secret.to_string(),
            ));
            self.agents.insert(
                nick.to_string(),
                AgentRecord {
                    caps: caps.join(","),
                    roles: roles.to_string(),
                    host: "host-a".to_string(),
                    updated: "1".to_string(),
                },
            );
            Ok(())
        }

        fn agents(&self) -> HashMap<String, AgentRecord> {
            self.agents.clone()
        }
    }

    /// Fake overseer backend with scripted answers.
    struct FakeOverseer {
        dispatch_answer: (String, Vec<(String, bool, String)>),
        tick_answer: TickReport,
        verify_answer: (bool, String),
    }

    impl OverseerBackend for FakeOverseer {
        fn dispatch(
            &mut self,
            _title: &str,
            _spec: &str,
            _accept: &str,
            _requirements: &[String],
            _room: &str,
            _lease: i64,
            _branch: &str,
            _base: &str,
        ) -> (String, Vec<(String, bool, String)>) {
            self.dispatch_answer.clone()
        }

        fn tick(
            &self,
            _repo: Option<&str>,
            _workdir_base: Option<&str>,
        ) -> TickReport {
            self.tick_answer.clone()
        }

        fn verify_done(
            &self,
            _jid: &str,
            _repo: Option<&str>,
            _workdir_base: Option<&str>,
        ) -> (bool, String) {
            self.verify_answer.clone()
        }
    }

    /// Fake worker backend with a scripted DM queue.
    struct FakeWorker {
        queue: Vec<(String, String, Vec<String>)>,
        match_all: bool,
        claim_ok: bool,
        specs: HashMap<String, String>,
    }

    impl WorkerBackend for FakeWorker {
        fn register(&mut self) {}
        fn heartbeat(&mut self) {}
        fn poll_dms(&mut self) -> Vec<(String, String, Vec<String>)> {
            std::mem::take(&mut self.queue)
        }
        fn matches(&self, _reqs: &[String]) -> bool {
            self.match_all
        }
        fn claim(&mut self, _jid: &str) -> (bool, String) {
            (self.claim_ok, String::new())
        }
        fn job_spec(&self, jid: &str) -> String {
            self.specs.get(jid).cloned().unwrap_or_default()
        }
    }

    struct FakeReconcile(i32);

    impl ReconcileBackend for FakeReconcile {
        fn main(&self, _args: &[String]) -> i32 {
            self.0
        }
    }

    struct FakeGitops {
        review: Result<ReviewSummary, GitError>,
        merge: Result<String, GitError>,
    }

    impl GitopsBackend for FakeGitops {
        fn review_branch(
            &self,
            _repo: &str,
            _branch: &str,
            _base: &str,
        ) -> Result<ReviewSummary, GitError> {
            self.review.clone()
        }
        fn approve_merge(
            &self,
            _repo: &str,
            _branch: &str,
            _base: &str,
        ) -> Result<String, GitError> {
            self.merge.clone()
        }
    }

    fn s(v: &str) -> String {
        v.to_string()
    }

    #[test]
    fn test_expand_text_plain_and_empty() {
        assert_eq!(expand_text("hello").unwrap(), "hello");
        assert_eq!(expand_text("").unwrap(), "");
    }

    #[test]
    fn test_expand_text_at_file() {
        let dir = std::env::temp_dir().join("os-boot-expand-test");
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("spec.txt");
        std::fs::write(&path, "file spec").unwrap();
        let got = expand_text(&format!("@{}", path.display())).unwrap();
        assert_eq!(got, "file spec");
        assert!(expand_text("@/nonexistent-os-boot-file-xyz").is_err());
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_split_caps_filters_and_keeps_raw() {
        // Mirrors the Python comprehension, including the kept-spaces oddity.
        assert_eq!(
            split_caps("python, testing ,,docs"),
            vec!["python".to_string(), " testing ".to_string(), "docs".to_string()]
        );
        assert!(split_caps(" , ,").is_empty());
    }

    #[test]
    fn test_register_output_sorted_raw_caps() {
        let mut fake = FakeCaps { agents: HashMap::new(), registered: vec![], fail: false };
        let out = cmd_register("w1", "testing,python", "builder", 2, "s3", &mut fake);
        assert_eq!(out.code, 0);
        // Sorted raw strings: "python" < "testing".
        assert_eq!(out.out, "REGISTERED w1: python,testing\n");
        assert_eq!(fake.registered[0].3, 2);
    }

    #[test]
    fn test_register_backend_error() {
        let mut fake = FakeCaps { agents: HashMap::new(), registered: vec![], fail: true };
        let out = cmd_register("w1", "python", "", 1, "", &mut fake);
        assert_eq!(out.code, 1);
        assert!(out.err.contains("store down"));
    }

    #[test]
    fn test_caps_empty_and_listed() {
        let fake = FakeCaps { agents: HashMap::new(), registered: vec![], fail: false };
        assert_eq!(cmd_caps(&fake).out, "NO_AGENTS\n");
        let mut agents = HashMap::new();
        agents.insert(
            "w2".to_string(),
            AgentRecord { caps: "docs".into(), roles: "".into(), host: "h".into(), updated: "9".into() },
        );
        agents.insert(
            "w1".to_string(),
            AgentRecord { caps: "python".into(), roles: "builder".into(), host: "h".into(), updated: "8".into() },
        );
        let fake2 = FakeCaps { agents, registered: vec![], fail: false };
        assert_eq!(
            cmd_caps(&fake2).out,
            "w1: caps=python roles=builder host=h updated=8\nw2: caps=docs roles= host=h updated=9\n"
        );
    }

    #[test]
    fn test_dispatch_with_and_without_workers() {
        let mut fake = FakeOverseer {
            dispatch_answer: (
                "7".to_string(),
                vec![("w1".to_string(), true, "sent".to_string())],
            ),
            tick_answer: TickReport::default(),
            verify_answer: (true, String::new()),
        };
        let out = cmd_dispatch("T", "spec", "", "python", "", 1800, "", "", &mut fake);
        assert_eq!(out.out, "DISPATCHED 7\n  DM w1: OK sent\n");
        fake.dispatch_answer = ("8".to_string(), vec![]);
        let out2 = cmd_dispatch("T", "spec", "", "", "", 1800, "", "", &mut fake);
        assert_eq!(out2.out, "DISPATCHED 8\n  (no capable workers registered)\n");
    }

    #[test]
    fn test_dispatch_at_file_error() {
        let mut fake = FakeOverseer {
            dispatch_answer: ("1".to_string(), vec![]),
            tick_answer: TickReport::default(),
            verify_answer: (true, String::new()),
        };
        let out = cmd_dispatch("T", "@/nonexistent-os-boot-file-xyz", "", "", "", 1800, "", "", &mut fake);
        assert_eq!(out.code, 1);
    }

    #[test]
    fn test_tick_clean_and_errors() {
        let fake = FakeOverseer {
            dispatch_answer: (String::new(), vec![]),
            tick_answer: TickReport::default(),
            verify_answer: (true, String::new()),
        };
        let out = cmd_tick(None, None, &fake);
        assert_eq!(out.code, 0);
        assert_eq!(out.out, "TICK_CLEAN\n");
        let fake2 = FakeOverseer {
            dispatch_answer: (String::new(), vec![]),
            tick_answer: TickReport {
                swept: vec!["3".to_string()],
                failed: vec!["4".to_string()],
                errors: vec!["boom".to_string()],
                ..Default::default()
            },
            verify_answer: (true, String::new()),
        };
        let out2 = cmd_tick(None, None, &fake2);
        assert_eq!(out2.code, 2);
        assert_eq!(out2.out, "SWEPT 3\nACCEPTANCE_FAILED 4\n");
        assert_eq!(out2.err, "ERROR boom\n");
    }

    #[test]
    fn test_verify_ok_and_fail() {
        let fake = FakeOverseer {
            dispatch_answer: (String::new(), vec![]),
            tick_answer: TickReport::default(),
            verify_answer: (true, "[PASS] file-exists: a".to_string()),
        };
        let out = cmd_verify("1", None, None, &fake);
        assert_eq!(out.code, 0);
        assert_eq!(out.out, "[PASS] file-exists: a\nVERIFIED\n");
        let fake2 = FakeOverseer {
            dispatch_answer: (String::new(), vec![]),
            tick_answer: TickReport::default(),
            verify_answer: (false, "[FAIL] file-exists: a".to_string()),
        };
        let out2 = cmd_verify("1", None, None, &fake2);
        assert_eq!(out2.code, 1);
        assert!(out2.out.ends_with("NOT_VERIFIED\n"));
    }

    #[test]
    fn test_worker_once_claim_skip_and_empty() {
        let mut specs = HashMap::new();
        specs.insert("1".to_string(), "do the thing".to_string());
        let mut w = FakeWorker {
            queue: vec![
                ("1".to_string(), "Build".to_string(), vec!["python".to_string()]),
            ],
            match_all: true,
            claim_ok: true,
            specs,
        };
        let out = cmd_worker_once(&mut w);
        assert_eq!(out.out, "CLAIMED 1: Build\n--- spec ---\ndo the thing\n");
        let mut w2 = FakeWorker {
            queue: vec![(
                "2".to_string(),
                "Rust".to_string(),
                vec!["rust".to_string()],
            )],
            match_all: false,
            claim_ok: true,
            specs: HashMap::new(),
        };
        let out2 = cmd_worker_once(&mut w2);
        assert_eq!(out2.out, "SKIP 2 (req rust)\n");
        let mut w3 = FakeWorker {
            queue: vec![],
            match_all: true,
            claim_ok: true,
            specs: HashMap::new(),
        };
        assert_eq!(cmd_worker_once(&mut w3).out, "NO_DISPATCHES\n");
    }

    #[test]
    fn test_worker_once_claim_failed_no_no_dispatches_line() {
        // Python prints NO_DISPATCHES only when nothing was found at all.
        let mut w = FakeWorker {
            queue: vec![(
                "1".to_string(),
                "Build".to_string(),
                vec!["python".to_string()],
            )],
            match_all: true,
            claim_ok: false,
            specs: HashMap::new(),
        };
        let out = cmd_worker_once(&mut w);
        assert_eq!(out.out, "CLAIM_FAILED 1\n");
    }

    #[test]
    fn test_reconcile_passthrough() {
        assert_eq!(cmd_reconcile(&FakeReconcile(3)).code, 3);
        assert_eq!(cmd_reconcile(&FakeReconcile(0)).code, 0);
    }

    #[test]
    fn test_review_and_merge_fake_backend() {
        let fake = FakeGitops {
            review: Ok(ReviewSummary {
                branch: "worker/thing".to_string(),
                base: "main".to_string(),
                files: vec!["b.txt".to_string()],
                stat: " b.txt | 1 +".to_string(),
                commits: vec!["abc1234 worker commit".to_string()],
                commit_count: 1,
            }),
            merge: Ok("deadbeefdeadbeefdeadbeefdeadbeefdeadbeef".to_string()),
        };
        let out = cmd_review("/r", "worker/thing", "main", &fake);
        assert_eq!(
            out.out,
            "branch worker/thing vs main: 1 commits, 1 files\n  abc1234 worker commit\n b.txt | 1 +\n"
        );
        let out2 = cmd_merge("/r", "worker/thing", "main", &fake);
        assert_eq!(
            out2.out,
            "MERGED worker/thing -> main: deadbeefdeadbeefdeadbeefdeadbeefdeadbeef\n"
        );
        let fake_err = FakeGitops {
            review: Err(GitError("unknown branch: nope".to_string())),
            merge: Err(GitError("working tree dirty — refusing to merge".to_string())),
        };
        assert_eq!(cmd_review("/r", "nope", "main", &fake_err).code, 2);
        assert!(cmd_review("/r", "nope", "main", &fake_err).err.contains("unknown branch"));
        assert_eq!(cmd_merge("/r", "worker/thing", "main", &fake_err).code, 2);
    }

    #[test]
    fn test_run_cli_arg_errors() {
        let mut caps = FakeCaps { agents: HashMap::new(), registered: vec![], fail: false };
        let mut ov = FakeOverseer {
            dispatch_answer: (String::new(), vec![]),
            tick_answer: TickReport::default(),
            verify_answer: (true, String::new()),
        };
        let mut w = FakeWorker {
            queue: vec![],
            match_all: true,
            claim_ok: true,
            specs: HashMap::new(),
        };
        let rec = FakeReconcile(0);
        let git = FakeGitops {
            review: Err(GitError("x".into())),
            merge: Err(GitError("x".into())),
        };
        let mut b = Backends {
            caps: &mut caps,
            overseer: &mut ov,
            worker: &mut w,
            reconcile: &rec,
            gitops: &git,
        };
        // Missing subcommand, unknown command, missing required flag.
        assert_eq!(run_cli(&[], &mut b).code, 2);
        assert_eq!(run_cli(&[s("bogus")], &mut b).code, 2);
        assert_eq!(run_cli(&[s("register"), s("--dm"), s("x")], &mut b).code, 2);
        assert_eq!(
            run_cli(&[s("dispatch"), s("--title"), s("T")], &mut b).code,
            2
        );
        // Bad integer.
        assert_eq!(
            run_cli(
                &[s("dispatch"), s("--title"), s("T"), s("--spec"), s("s"), s("--lease"), s("abc")],
                &mut b
            )
            .code,
            2
        );
        // Worker loop mode (no --once) is stderr + exit 2.
        let out = run_cli(&[s("worker")], &mut b);
        assert_eq!(out.code, 2);
        assert!(out.err.contains("agent-driven"));
    }

    #[test]
    fn test_run_cli_dispatch_defaults() {
        let mut caps = FakeCaps { agents: HashMap::new(), registered: vec![], fail: false };
        let mut ov = FakeOverseer {
            dispatch_answer: ("9".to_string(), vec![]),
            tick_answer: TickReport::default(),
            verify_answer: (true, String::new()),
        };
        let mut w = FakeWorker {
            queue: vec![],
            match_all: true,
            claim_ok: true,
            specs: HashMap::new(),
        };
        let rec = FakeReconcile(0);
        let git = FakeGitops {
            review: Err(GitError("x".into())),
            merge: Err(GitError("x".into())),
        };
        let mut b = Backends {
            caps: &mut caps,
            overseer: &mut ov,
            worker: &mut w,
            reconcile: &rec,
            gitops: &git,
        };
        let out = run_cli(
            &[s("dispatch"), s("--title"), s("T"), s("--spec"), s("s")],
            &mut b,
        );
        assert_eq!(out.code, 0);
        assert_eq!(out.out, "DISPATCHED 9\n  (no capable workers registered)\n");
    }
}
