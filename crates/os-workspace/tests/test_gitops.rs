//! Parity tests for the MOS gitops behavior (`os/mos/gitops.py`).
//!
//! No test file is assigned to B19 in the batch map (parity is
//! behavior-for-behavior against the source); these tests mirror
//! `os/tests/test_mos_gitops.py` (owned by B23, which exercises
//! the same behavior through the mos CLI): review summaries,
//! merge guards, rejections, worktrees, and unknown-branch errors.
//! Nothing here force-pushes, ever.

use os_workspace::gitops::*;
use std::path::PathBuf;
use std::process::Command;

fn tmp_repo(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "os-gitops-{name}-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .subsec_nanos()
    ));
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

fn git(repo: &PathBuf, args: &[&str]) {
    let st = Command::new("git")
        .arg("-C")
        .arg(repo)
        .args(args)
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .status()
        .expect("git must exist");
    assert!(st.success(), "git {args:?} failed");
}

fn make_repo(path: &PathBuf) -> String {
    git(path, &["init", "-b", "main"]);
    git(path, &["config", "user.email", "t@t.t"]);
    git(path, &["config", "user.name", "t"]);
    std::fs::write(path.join("a.txt"), "v1\n").unwrap();
    git(path, &["add", "."]);
    git(path, &["commit", "-m", "base"]);
    git(path, &["checkout", "-b", "worker/thing"]);
    std::fs::write(path.join("b.txt"), "new\n").unwrap();
    git(path, &["add", "."]);
    git(path, &["commit", "-m", "worker commit"]);
    git(path, &["checkout", "main"]);
    path.to_string_lossy().into_owned()
}

#[test]
fn gitops_review_branch() {
    let repo = make_repo(&tmp_repo("review"));
    let r = review_branch(&repo, "worker/thing", "main").unwrap();
    assert_eq!(r.branch, "worker/thing");
    assert_eq!(r.commit_count, 1);
    assert!(r.files.contains(&"b.txt".to_string()), "{:?}", r.files);
    assert!(!r.stat.is_empty());
}

#[test]
fn gitops_review_rejects_self() {
    let repo = make_repo(&tmp_repo("self"));
    assert!(review_branch(&repo, "main", "main").is_err());
}

#[test]
fn gitops_review_unknown_branch() {
    let repo = make_repo(&tmp_repo("unknown"));
    assert!(review_branch(&repo, "nope", "main").is_err());
}

#[test]
fn gitops_approve_merge() {
    let repo = make_repo(&tmp_repo("merge"));
    let h = approve_merge(&repo, "worker/thing", "main").unwrap();
    assert_eq!(h.len(), 40);
    assert!(h.chars().all(|c| c.is_ascii_hexdigit()));
    assert!(PathBuf::from(&repo).join("b.txt").exists());
}

#[test]
fn gitops_merge_refuses_dirty_tree() {
    let repo = tmp_repo("dirty");
    let repo_s = make_repo(&repo);
    std::fs::write(repo.join("dirty.txt"), "x").unwrap();
    assert!(approve_merge(&repo_s, "worker/thing", "main").is_err());
}

#[test]
fn gitops_merge_refuses_self() {
    let repo = make_repo(&tmp_repo("mergeself"));
    assert!(approve_merge(&repo, "main", "main").is_err());
}

#[test]
fn gitops_reject_branch() {
    assert_eq!(
        reject_branch("worker/thing", "tests fail").unwrap(),
        "REJECTED worker/thing: tests fail"
    );
    assert!(reject_branch("worker/thing", "  ").is_err());
}

#[test]
fn gitops_worktree_add_remove() {
    let repo = tmp_repo("wt");
    let repo_s = make_repo(&repo);
    let wt = repo.join("wt-checkout").to_string_lossy().into_owned();
    worktree_add(&repo_s, "worker/thing", &wt).unwrap();
    assert!(PathBuf::from(&wt).join("b.txt").exists());
    worktree_remove(&repo_s, &wt).unwrap();
    assert!(!PathBuf::from(&wt).exists());
}

#[test]
fn gitops_not_a_repo() {
    let dir = tmp_repo("notrepo");
    assert!(review_branch(&dir.to_string_lossy(), "worker/thing", "main").is_err());
}

#[test]
fn gitops_helpers_read_repo_state() {
    let repo = make_repo(&tmp_repo("helpers"));
    assert!(is_repo(&repo));
    assert!(!is_repo(&tmp_repo("helpers-empty").to_string_lossy()));
    assert_eq!(current_branch(&repo).unwrap(), "main");
    assert!(clean_tree(&repo).unwrap());
    assert!(branch_exists(&repo, "worker/thing"));
    assert!(!branch_exists(&repo, "nope"));
}
