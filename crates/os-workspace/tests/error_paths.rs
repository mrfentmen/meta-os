//! Error paths for `os-workspace`: the refusal branches the source actually
//! has, held to their exact messages. Where the Rust port and Python differ,
//! the difference is recorded in `os-build/records/os-workspace-gaps.md`;
//! nothing here invents a refusal the code does not make.

use os_workspace::{
    approve_merge, attach, branch_exists, clean_tree, current_branch, deposit, is_repo,
    list_artifacts, read_artifact, reject_branch, review_branch, run_cli, validate_job_id,
    validate_name, worktree_add, worktree_remove, ArtifactStoreError, GitError, JsonValue,
};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicUsize, Ordering};

static COUNTER: AtomicUsize = AtomicUsize::new(0);

struct TmpDir(PathBuf);

impl TmpDir {
    fn new(tag: &str) -> TmpDir {
        let n = COUNTER.fetch_add(1, Ordering::SeqCst);
        let p = std::env::temp_dir().join(format!(
            "os-workspace-err-{}-{}-{}",
            std::process::id(),
            tag,
            n
        ));
        let _ = fs::remove_dir_all(&p);
        fs::create_dir_all(&p).expect("create temp dir");
        TmpDir(p)
    }

    fn path(&self) -> &Path {
        &self.0
    }
}

impl Drop for TmpDir {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn a_err<T>(r: Result<T, ArtifactStoreError>) -> String {
    match r {
        Ok(_) => panic!("expected ArtifactStoreError"),
        Err(e) => e.0,
    }
}

fn g_err<T>(r: Result<T, GitError>) -> String {
    match r {
        Ok(_) => panic!("expected GitError"),
        Err(e) => e.0,
    }
}

fn git(dir: &Path, args: &[&str]) {
    let out = Command::new("git")
        .arg("-C")
        .arg(dir)
        .args(args)
        .output()
        .expect("run git");
    assert!(
        out.status.success(),
        "git {:?} failed: {}",
        args,
        String::from_utf8_lossy(&out.stderr)
    );
}

fn make_repo(tag: &str) -> TmpDir {
    let d = TmpDir::new(tag);
    git(d.path(), &["init", "-q", "-b", "main"]);
    git(d.path(), &["config", "user.name", "t"]);
    git(d.path(), &["config", "user.email", "t@t"]);
    fs::write(d.path().join("a.txt"), "one\n").unwrap();
    git(d.path(), &["add", "-A"]);
    git(d.path(), &["commit", "-q", "-m", "initial"]);
    d
}

fn cli(args: &[&str]) -> (i32, String, String) {
    let owned: Vec<String> = args.iter().map(|s| s.to_string()).collect();
    let mut out: Vec<u8> = Vec::new();
    let mut err: Vec<u8> = Vec::new();
    let code = run_cli(&owned, &mut out, &mut err);
    (
        code,
        String::from_utf8_lossy(&out).into_owned(),
        String::from_utf8_lossy(&err).into_owned(),
    )
}

// -- validation -----------------------------------------------------------

#[test]
fn job_id_refusals_are_the_documented_messages() {
    assert_eq!(
        a_err(validate_job_id("")),
        "job id must be a non-empty string"
    );
    assert_eq!(
        a_err(validate_job_id(".")),
        "job id must be a single path segment"
    );
    assert_eq!(
        a_err(validate_job_id("..")),
        "job id must be a single path segment"
    );
    assert_eq!(
        a_err(validate_job_id("a/b")),
        "job id must be a single path segment"
    );
    assert_eq!(
        a_err(validate_job_id("a\\b")),
        "job id must be a single path segment"
    );
    assert_eq!(
        a_err(validate_job_id("a\0b")),
        "job id must be a single path segment"
    );
    assert_eq!(
        a_err(validate_job_id("a b")),
        "job id holds characters outside [A-Za-z0-9._-]"
    );
    assert_eq!(
        a_err(validate_job_id("a:b")),
        "job id holds characters outside [A-Za-z0-9._-]"
    );
}

#[test]
fn name_refusals_are_the_documented_messages() {
    assert_eq!(
        a_err(validate_name("")),
        "artifact name must be a non-empty string"
    );
    assert_eq!(
        a_err(validate_name("/abs.txt")),
        "artifact name must be a relative POSIX path"
    );
    assert_eq!(
        a_err(validate_name("a\\b")),
        "artifact name must be a relative POSIX path"
    );
    assert_eq!(
        a_err(validate_name("a\0b")),
        "artifact name must be a relative POSIX path"
    );
    assert_eq!(
        a_err(validate_name("a//b")),
        "artifact name must not contain empty, . or .. segments"
    );
    assert_eq!(
        a_err(validate_name("a/./b")),
        "artifact name must not contain empty, . or .. segments"
    );
    assert_eq!(
        a_err(validate_name("a/../b")),
        "artifact name must not contain empty, . or .. segments"
    );
}

#[test]
fn deposit_validates_before_it_creates_the_store() {
    let d = TmpDir::new("deposit-refusal");
    assert_eq!(
        a_err(deposit(d.path(), "a/b", "f.txt", b"x", "")),
        "job id must be a single path segment"
    );
    assert_eq!(
        a_err(deposit(d.path(), "j", "/f.txt", b"x", "")),
        "artifact name must be a relative POSIX path"
    );
    assert!(
        !d.path().join(".git").exists(),
        "a refused deposit must not create the store repo"
    );
}

#[test]
fn read_refusals_are_exact() {
    let d = TmpDir::new("read-refusal");
    deposit(d.path(), "j", "f.txt", b"one", "").unwrap();
    assert_eq!(
        a_err(read_artifact(d.path(), "j", "ghost.txt", None)),
        "no artifact 'ghost.txt' for job 'j'"
    );
    assert_eq!(
        a_err(read_artifact(d.path(), "j", "f.txt", Some(0))),
        "version must be a positive integer"
    );
    assert_eq!(
        a_err(read_artifact(d.path(), "j", "f.txt", Some(9))),
        "artifact 'f.txt' for job 'j' has 1 versions, no v9"
    );
}

#[test]
fn attach_refuses_a_non_object_record() {
    let d = TmpDir::new("attach-refusal");
    assert_eq!(
        a_err(attach(d.path(), "j", &JsonValue::Null)),
        "job record must be a dict"
    );
    assert_eq!(
        a_err(attach(d.path(), "j", &JsonValue::Array(vec![]))),
        "job record must be a dict"
    );
}

#[test]
fn manifest_corruption_and_shape_are_refused() {
    let d = TmpDir::new("manifest-bad");
    let dir = d.path().join("jobs/j");
    fs::create_dir_all(&dir).unwrap();
    fs::write(dir.join("manifest.json"), "{not json").unwrap();
    assert!(
        a_err(list_artifacts(d.path(), "j")).starts_with("manifest unreadable:"),
        "a broken manifest must name itself unreadable"
    );
    fs::write(
        dir.join("manifest.json"),
        "{\"job_id\":\"j\",\"artifacts\":[]}",
    )
    .unwrap();
    assert_eq!(
        a_err(list_artifacts(d.path(), "j")),
        "manifest has an unexpected shape"
    );
    fs::write(dir.join("manifest.json"), "[]").unwrap();
    assert_eq!(
        a_err(list_artifacts(d.path(), "j")),
        "manifest has an unexpected shape"
    );
}

// -- CLI ------------------------------------------------------------------

#[test]
fn cli_usage_refusals_exit_two() {
    let cases: Vec<Vec<&str>> = vec![
        vec![],
        vec!["bogus", "/tmp", "j"],
        vec!["deposit", "/tmp", "j", "f.txt"],
        vec!["list", "/tmp"],
        vec!["list", "/tmp", "j", "extra"],
        vec!["show", "/tmp", "j"],
    ];
    for args in cases {
        let (code, _, err) = cli(&args);
        assert_eq!(code, 2, "{:?}", args);
        assert!(
            err.contains("usage: artifact_store deposit|list|read|show ROOT JOB [ARGS]"),
            "{:?} -> {}",
            args,
            err
        );
    }
}

#[test]
fn cli_missing_source_and_artifact_are_artifact_store_errors() {
    let d = TmpDir::new("cli-errors");
    deposit(d.path(), "j", "f.txt", b"x", "").unwrap();
    let root = d.path().to_string_lossy().into_owned();
    let (code, _, err) = cli(&["deposit", &root, "j", "g.txt", "/no/such/source"]);
    assert_eq!(code, 2);
    assert!(err.starts_with("ARTIFACT_STORE_ERROR: "), "{}", err);
    let (code, _, err) = cli(&["read", &root, "j", "ghost.txt"]);
    assert_eq!(code, 2);
    assert!(err.contains("no artifact 'ghost.txt'"), "{}", err);
}

#[test]
fn cli_missing_flag_values_are_usage_errors() {
    let (code, _, err) = cli(&["deposit", "/tmp", "j", "f.txt", "/tmp/x", "--author"]);
    assert_eq!(code, 2);
    assert!(err.contains("usage:"), "{}", err);
    let (code, _, err) = cli(&["read", "/tmp", "j", "f.txt", "--version"]);
    assert_eq!(code, 2);
    assert!(err.contains("usage:"), "{}", err);
}

#[test]
fn cli_non_integer_version_is_refused() {
    let d = TmpDir::new("cli-nan");
    deposit(d.path(), "j", "f.txt", b"x", "").unwrap();
    let root = d.path().to_string_lossy().into_owned();
    let (code, _, err) = cli(&["read", &root, "j", "f.txt", "--version", "nope"]);
    assert_eq!(code, 2);
    assert!(
        err.contains("invalid literal for int() with base 10: 'nope'"),
        "{}",
        err
    );
}

#[test]
fn store_root_that_is_a_file_fails_as_an_artifact_error() {
    let d = TmpDir::new("root-file");
    let root = d.path().join("not-a-dir");
    fs::write(&root, "x").unwrap();
    let e = a_err(deposit(&root, "j", "f.txt", b"x", ""));
    assert!(!e.is_empty(), "an uncreatable root must surface an error");
}

#[test]
fn cli_negative_version_is_refused() {
    let d = TmpDir::new("cli-neg");
    deposit(d.path(), "j", "f.txt", b"x", "").unwrap();
    let root = d.path().to_string_lossy().into_owned();
    let (code, _, err) = cli(&["read", &root, "j", "f.txt", "--version", "-1"]);
    assert_eq!(code, 2);
    assert!(
        err.contains("version must be a positive integer"),
        "{}",
        err
    );
}

// -- gitops ---------------------------------------------------------------

#[test]
fn review_refusals_are_exact() {
    let plain = TmpDir::new("review-plain");
    let e = g_err(review_branch(plain.path(), "x", "main"));
    assert!(e.starts_with("not a git repo: "), "{}", e);

    let d = make_repo("review-guards");
    assert_eq!(
        g_err(review_branch(d.path(), "main", "main")),
        "refusing to review base against itself"
    );
    assert_eq!(
        g_err(review_branch(d.path(), "ghost", "main")),
        "unknown branch: ghost"
    );
    assert_eq!(
        g_err(review_branch(d.path(), "main", "ghost")),
        "unknown branch: ghost"
    );
}

#[test]
fn merge_refusals_are_exact() {
    let d = make_repo("merge-guards");
    assert_eq!(
        g_err(approve_merge(d.path(), "main", "main")),
        "refusing to merge base into itself"
    );
    assert_eq!(
        g_err(approve_merge(d.path(), "ghost", "main")),
        "unknown branch: ghost"
    );
    fs::write(d.path().join("a.txt"), "dirty\n").unwrap();
    assert_eq!(
        g_err(approve_merge(d.path(), "main", "x")),
        "working tree dirty — refusing to merge"
    );

    let plain = TmpDir::new("merge-plain");
    let e = g_err(approve_merge(plain.path(), "feature", "main"));
    assert!(e.contains("git status --porcelain failed:"), "{}", e);
}

#[test]
fn non_repo_gitops_helpers_error_or_are_false() {
    let plain = TmpDir::new("gitops-plain");
    assert!(current_branch(plain.path()).is_err());
    assert!(clean_tree(plain.path()).is_err());
    assert!(!is_repo(plain.path()));
    assert!(!branch_exists(plain.path(), "main"));
}

#[test]
fn reject_branch_needs_a_reason() {
    assert_eq!(g_err(reject_branch("feat", "")), "rejection needs a reason");
    assert_eq!(
        g_err(reject_branch("feat", "   ")),
        "rejection needs a reason"
    );
}

#[test]
fn worktree_refusals_are_exact() {
    let d = make_repo("wt-guards");
    let existing = d.path().join("already");
    fs::create_dir_all(&existing).unwrap();
    assert_eq!(
        g_err(worktree_add(d.path(), "main", &existing)),
        format!("worktree path already exists: {}", existing.display())
    );
    let missing = d.path().join("wt");
    assert_eq!(
        g_err(worktree_add(d.path(), "ghost", &missing)),
        "unknown branch: ghost"
    );
    assert!(
        worktree_remove(d.path(), &missing).is_err(),
        "removing a worktree that does not exist must fail, not silently pass"
    );
}
