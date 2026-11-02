//! Test-gap close for `os-workspace`: public gitops and CLI paths that the
//! in-file tests touch least. The JSON parser's missing cases live inside
//! `src/lib.rs` (the parser is private); these are the public ones.

use os_workspace::{
    approve_merge, attach, branch_exists, clean_tree, current_branch, deposit, is_repo,
    run_cli, worktree_add, worktree_remove, JsonValue,
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
            "os-workspace-gap-{}-{}-{}",
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

fn git_out(dir: &Path, args: &[&str]) -> String {
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
    String::from_utf8_lossy(&out.stdout).into_owned()
}

fn git(dir: &Path, args: &[&str]) {
    let _ = git_out(dir, args);
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

#[test]
fn current_branch_is_empty_on_a_detached_head() {
    let d = make_repo("detached");
    git(d.path(), &["checkout", "-q", "--detach"]);
    assert_eq!(current_branch(d.path()).unwrap(), "");
}

#[test]
fn branch_exists_is_false_for_a_commit_sha() {
    let d = make_repo("sha-branch");
    let sha = git_out(d.path(), &["rev-parse", "HEAD"]);
    assert!(!branch_exists(d.path(), sha.trim()));
    assert!(branch_exists(d.path(), "main"));
}

#[test]
fn is_repo_accepts_a_subdirectory() {
    let d = make_repo("subdir");
    let sub = d.path().join("sub");
    fs::create_dir_all(&sub).unwrap();
    assert!(is_repo(&sub));
}

#[test]
fn clean_tree_counts_an_untracked_file_as_dirty() {
    let d = make_repo("untracked");
    assert!(clean_tree(d.path()).unwrap());
    fs::write(d.path().join("new.txt"), "x").unwrap();
    assert!(
        !clean_tree(d.path()).unwrap(),
        "an untracked file makes the tree dirty, as git status says"
    );
}

#[test]
fn approve_merge_refuses_an_unknown_base() {
    let d = make_repo("merge-base");
    git(d.path(), &["checkout", "-q", "-b", "feature"]);
    fs::write(d.path().join("b.txt"), "new\n").unwrap();
    git(d.path(), &["add", "-A"]);
    git(d.path(), &["commit", "-q", "-m", "feature work"]);
    let err = approve_merge(d.path(), "feature", "ghost").unwrap_err();
    assert_eq!(err.0, "unknown branch: ghost");
}

#[test]
fn worktree_add_detaches_and_remove_cleans_up() {
    let d = make_repo("worktree");
    let wt = d.path().join("wt");
    worktree_add(d.path(), "main", &wt).unwrap();
    assert!(wt.join("a.txt").is_file());
    assert_eq!(current_branch(&wt).unwrap(), "", "the worktree is detached");
    worktree_remove(d.path(), &wt).unwrap();
    assert!(!wt.exists());
}

#[test]
fn run_cli_identical_deposit_reports_no_new_commit() {
    let d = TmpDir::new("cli-identical");
    let src = d.path().join("in.txt");
    fs::write(&src, b"same").unwrap();
    let root = d.path().to_string_lossy().into_owned();
    let src_s = src.to_string_lossy().into_owned();
    let (code, out, _) = cli(&["deposit", &root, "j", "f.txt", &src_s]);
    assert_eq!(code, 0);
    assert!(out.contains("\"new_commit\": true"), "{}", out);
    let (code, out, _) = cli(&["deposit", &root, "j", "f.txt", &src_s]);
    assert_eq!(code, 0);
    assert!(out.contains("\"new_commit\": false"), "{}", out);
}

#[test]
fn run_cli_show_lists_oldest_first() {
    let d = TmpDir::new("cli-show");
    deposit(d.path(), "j", "f.txt", b"one", "").unwrap();
    deposit(d.path(), "j", "f.txt", b"two", "").unwrap();
    let root = d.path().to_string_lossy().into_owned();
    let (code, out, _) = cli(&["show", &root, "j", "f.txt"]);
    assert_eq!(code, 0);
    let lines: Vec<&str> = out.lines().collect();
    assert_eq!(lines.len(), 2);
    assert!(lines[0].starts_with("v1 "), "{}", out);
    assert!(lines[1].starts_with("v2 "), "{}", out);
}

#[test]
fn attach_preserves_top_level_fields_and_does_not_mutate_input() {
    let d = TmpDir::new("attach-copy");
    deposit(d.path(), "j", "f.txt", b"x", "").unwrap();
    let input = JsonValue::obj(vec![
        ("title", JsonValue::Str("Live job".to_string())),
        ("artifacts", JsonValue::Array(vec![])),
    ]);
    let out = attach(d.path(), "j", &input).unwrap();
    assert_eq!(out.get("title").and_then(|v| v.as_str()), Some("Live job"));
    assert_eq!(
        input
            .get("artifacts")
            .and_then(|a| a.as_array())
            .map(|a| a.len()),
        Some(0),
        "the input record must not be mutated"
    );
    assert_eq!(
        out.get("artifacts")
            .and_then(|a| a.as_array())
            .map(|a| a.len()),
        Some(1)
    );
}
