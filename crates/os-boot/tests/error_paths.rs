//! B002 — every refusal and failure branch in `os-boot`, proven as the code says.
//!
//! These are integration tests against the public API only: no test-only `pub` was added, and
//! no production behaviour was changed to make them pass. Git tests build real temporary
//! repositories, because the git module's whole point is that it shells out for real.

use os_boot::cli::{
    cmd_dispatch, cmd_merge, cmd_review, cmd_tick, cmd_verify, expand_text, run_cli,
    AgentRecord, Backends, CapabilitiesBackend, CliOutcome, GitError, GitopsBackend,
    OverseerBackend, ReconcileBackend, ReviewSummary, TickReport, WorkerBackend,
};
use os_boot::git::GitCliBackend;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::process::Command;

// ---------------------------------------------------------------- fakes

struct FakeCaps {
    fail: bool,
}
impl CapabilitiesBackend for FakeCaps {
    fn register(
        &mut self,
        _nick: &str,
        _caps: &[String],
        _roles: &str,
        _max_jobs: i64,
        _dm: &str,
    ) -> Result<(), String> {
        if self.fail {
            Err("store down".to_string())
        } else {
            Ok(())
        }
    }
    fn agents(&self) -> HashMap<String, AgentRecord> {
        HashMap::new()
    }
}

struct FakeOverseer {
    tick: TickReport,
    verify: (bool, String),
}
impl OverseerBackend for FakeOverseer {
    fn dispatch(
        &mut self,
        _title: &str,
        _spec: &str,
        _accept: &str,
        _req: &[String],
        _room: &str,
        _lease: i64,
        _branch: &str,
        _base: &str,
    ) -> (String, Vec<(String, bool, String)>) {
        ("1".to_string(), vec![])
    }
    fn tick(&self, _repo: Option<&str>, _wd: Option<&str>) -> TickReport {
        self.tick.clone()
    }
    fn verify_done(&self, _jid: &str, _repo: Option<&str>, _wd: Option<&str>) -> (bool, String) {
        self.verify.clone()
    }
}

struct FakeWorker;
impl WorkerBackend for FakeWorker {
    fn register(&mut self) {}
    fn heartbeat(&mut self) {}
    fn poll_dms(&mut self) -> Vec<(String, String, Vec<String>)> {
        vec![]
    }
    fn matches(&self, _reqs: &[String]) -> bool {
        true
    }
    fn claim(&mut self, _jid: &str) -> (bool, String) {
        (true, String::new())
    }
    fn job_spec(&self, _jid: &str) -> String {
        String::new()
    }
}

struct FakeReconcile;
impl ReconcileBackend for FakeReconcile {
    fn main(&self, _args: &[String]) -> i32 {
        0
    }
}

struct FakeGit {
    review: Result<ReviewSummary, GitError>,
    merge: Result<String, GitError>,
}
impl GitopsBackend for FakeGit {
    fn review_branch(&self, _r: &str, _b: &str, _base: &str) -> Result<ReviewSummary, GitError> {
        self.review.clone()
    }
    fn approve_merge(&self, _r: &str, _b: &str, _base: &str) -> Result<String, GitError> {
        self.merge.clone()
    }
}

struct Fixture {
    caps: FakeCaps,
    ov: FakeOverseer,
    worker: FakeWorker,
    rec: FakeReconcile,
    git: FakeGit,
}

fn fixture() -> Fixture {
    Fixture {
        caps: FakeCaps { fail: false },
        ov: FakeOverseer {
            tick: TickReport::default(),
            verify: (true, String::new()),
        },
        worker: FakeWorker,
        rec: FakeReconcile,
        git: FakeGit {
            review: Err(GitError("x".into())),
            merge: Err(GitError("x".into())),
        },
    }
}

fn call(fx: &mut Fixture, argv: &[&str]) -> CliOutcome {
    let owned: Vec<String> = argv.iter().map(|s| s.to_string()).collect();
    let mut b = Backends {
        caps: &mut fx.caps,
        overseer: &mut fx.ov,
        worker: &mut fx.worker,
        reconcile: &fx.rec,
        gitops: &fx.git,
    };
    run_cli(&owned, &mut b)
}

// ---------------------------------------------------------------- git fixtures

fn git(dir: &Path, args: &[&str]) -> bool {
    Command::new("git")
        .arg("-C")
        .arg(dir)
        .args(args)
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

fn make_repo(tag: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("os-boot-b002-{}-{tag}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    assert!(git(&dir, &["init", "-b", "main"]), "git init failed");
    assert!(git(&dir, &["config", "user.email", "t@t.t"]));
    assert!(git(&dir, &["config", "user.name", "t"]));
    std::fs::write(dir.join("a.txt"), "v1\n").unwrap();
    assert!(git(&dir, &["add", "."]));
    assert!(git(&dir, &["commit", "-m", "base"]));
    assert!(git(&dir, &["checkout", "-b", "worker/thing"]));
    std::fs::write(dir.join("b.txt"), "new\n").unwrap();
    assert!(git(&dir, &["add", "."]));
    assert!(git(&dir, &["commit", "-m", "worker commit"]));
    assert!(git(&dir, &["checkout", "main"]));
    dir
}

fn repo_str(p: &Path) -> String {
    p.display().to_string()
}

// ---------------------------------------------------------------- git refusals

#[test]
fn review_refuses_a_plain_directory() {
    let dir = std::env::temp_dir().join(format!("os-boot-b002-plain-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    let out = cmd_review(&repo_str(&dir), "worker/thing", "main", &GitCliBackend);
    assert_eq!(out.code, 2);
    assert!(out.err.contains("not a git repo"), "{}", out.err);
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn review_refuses_base_against_itself_before_touching_git_refs() {
    let dir = make_repo("review-self");
    let out = cmd_review(&repo_str(&dir), "main", "main", &GitCliBackend);
    assert_eq!(out.code, 2);
    assert!(
        out.err.contains("refusing to review base against itself"),
        "{}",
        out.err
    );
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn review_refuses_an_unknown_branch() {
    let dir = make_repo("review-unknown");
    let out = cmd_review(&repo_str(&dir), "nope", "main", &GitCliBackend);
    assert_eq!(out.code, 2);
    assert!(out.err.contains("unknown branch: nope"), "{}", out.err);
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn merge_refuses_base_into_itself() {
    let dir = make_repo("merge-self");
    let out = cmd_merge(&repo_str(&dir), "main", "main", &GitCliBackend);
    assert_eq!(out.code, 2);
    assert!(
        out.err.contains("refusing to merge base into itself"),
        "{}",
        out.err
    );
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn merge_refuses_a_dirty_working_tree() {
    let dir = make_repo("merge-dirty");
    std::fs::write(dir.join("untracked.txt"), "x").unwrap();
    let out = cmd_merge(&repo_str(&dir), "worker/thing", "main", &GitCliBackend);
    assert_eq!(out.code, 2);
    assert!(
        out.err.contains("working tree dirty — refusing to merge"),
        "{}",
        out.err
    );
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn merge_refuses_an_unknown_branch_on_a_clean_tree() {
    let dir = make_repo("merge-unknown");
    let out = cmd_merge(&repo_str(&dir), "nope", "main", &GitCliBackend);
    assert_eq!(out.code, 2);
    assert!(out.err.contains("unknown branch: nope"), "{}", out.err);
    let _ = std::fs::remove_dir_all(&dir);
}

// ---------------------------------------------------------------- input refusals

#[test]
fn expand_text_refuses_a_missing_at_file() {
    let err = expand_text("@/nonexistent-os-boot-b002-file").unwrap_err();
    assert!(err.starts_with("cannot read /nonexistent-os-boot-b002-file"), "{err}");
}

#[test]
fn register_reports_a_backend_failure_as_exit_one() {
    let mut fx = fixture();
    fx.caps.fail = true;
    let out = call(&mut fx, &["register", "--caps", "python", "--dm", "s"]);
    assert_eq!(out.code, 1);
    assert_eq!(out.out, "");
    assert!(out.err.contains("ERROR: store down"), "{}", out.err);
}

#[test]
fn dispatch_refuses_an_unreadable_spec_file_as_exit_one() {
    let mut fx = fixture();
    let out = cmd_dispatch(
        "T",
        "@/nonexistent-os-boot-b002-spec",
        "",
        "",
        "",
        1800,
        "",
        "",
        &mut fx.ov,
    );
    assert_eq!(out.code, 1, "a missing @file is not a usage error");
    assert!(out.err.starts_with("ERROR: cannot read"), "{}", out.err);
}

#[test]
fn tick_prints_errors_on_stderr_and_exits_two() {
    let fx = FakeOverseer {
        tick: TickReport {
            swept: vec!["3".into()],
            failed: vec!["4".into()],
            errors: vec!["boom".into()],
            ..Default::default()
        },
        verify: (true, String::new()),
    };
    let out = cmd_tick(None, None, &fx);
    assert_eq!(out.code, 2);
    assert_eq!(out.out, "SWEPT 3\nACCEPTANCE_FAILED 4\n");
    assert_eq!(out.err, "ERROR boom\n");
}

#[test]
fn verify_failure_exits_one_and_says_not_verified() {
    let fx = FakeOverseer {
        tick: TickReport::default(),
        verify: (false, "[FAIL] file-exists: a".to_string()),
    };
    let out = cmd_verify("1", None, None, &fx);
    assert_eq!(out.code, 1);
    assert_eq!(out.out, "[FAIL] file-exists: a\nNOT_VERIFIED\n");
}

#[test]
fn usage_refusals_are_exit_two() {
    let mut fx = fixture();
    assert_eq!(call(&mut fx, &[]).code, 2, "empty argv");
    assert_eq!(call(&mut fx, &["bogus"]).code, 2, "unknown command");
    assert_eq!(
        call(&mut fx, &["register", "--dm", "x"]).code,
        2,
        "register without --caps"
    );
    assert_eq!(
        call(&mut fx, &["dispatch", "--title", "T"]).code,
        2,
        "dispatch without --spec"
    );
    assert_eq!(
        call(
            &mut fx,
            &["dispatch", "--title", "T", "--spec", "s", "--lease", "abc"]
        )
        .code,
        2,
        "non-integer lease"
    );
}

#[test]
fn worker_loop_mode_is_refused_with_the_agent_driven_line() {
    let mut fx = fixture();
    let out = call(&mut fx, &["worker"]);
    assert_eq!(out.code, 2);
    assert!(
        out.err.contains("worker loop: agent-driven; use --once per cycle"),
        "{}",
        out.err
    );
}
