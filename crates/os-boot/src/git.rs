//! Real git backend for the `review` / `merge` commands
//! (`os/mos/gitops.py`, narrow slice: only the operations the MOS CLI
//! exposes — `review_branch` and `approve_merge`).
//!
//! Guard-for-guard parity with the Python source: refuse to review or
//! merge a base against itself, refuse unknown branches, refuse a dirty
//! tree on merge, check out the base before merging, merge with
//! `--no-ff` and the message `Merge <branch> (MOS approved)`, return
//! the merge HEAD hash. Nothing here force-pushes, ever.
//!
//! Approximations: the Python helper runs git with a 120s timeout;
//! `std::process` has no timeout, so this backend runs git without one
//! (local commands, fast in practice). `reject_branch` and the
//! worktree helpers are not CLI operations and are not duplicated here;
//! the B19 crate (`os-workspace`) ports the full gitops module.

use crate::cli::{GitError, ReviewSummary};
use std::process::Command;

/// Run `git -C <repo> <args>`, returning stdout on success.
/// Mirrors `gitops._git` minus the timeout: spawn failure becomes
/// "git not found on PATH"; a nonzero exit becomes
/// `git <args> failed: <last 500 chars of stderr>`.
fn git(repo: &str, args: &[&str]) -> Result<String, GitError> {
    let out = Command::new("git")
        .arg("-C")
        .arg(repo)
        .args(args)
        .output()
        .map_err(|_| GitError("git not found on PATH".to_string()))?;
    if !out.status.success() {
        let stderr = String::from_utf8_lossy(&out.stderr);
        let tail: String = stderr.chars().rev().take(500).collect::<String>().chars().rev().collect();
        return Err(GitError(format!(
            "git {} failed: {}",
            args.join(" "),
            tail.trim()
        )));
    }
    Ok(String::from_utf8_lossy(&out.stdout).into_owned())
}

/// Whether `path` is a git repo. Mirrors `gitops.is_repo`.
pub fn is_repo(path: &str) -> bool {
    git(path, &["rev-parse", "--git-dir"]).is_ok()
}

/// Current branch, stripped. Mirrors `gitops.current_branch`.
pub fn current_branch(repo: &str) -> Result<String, GitError> {
    Ok(git(repo, &["branch", "--show-current"])?.trim().to_string())
}

/// Whether the working tree is clean. Mirrors `gitops.clean_tree`.
pub fn clean_tree(repo: &str) -> Result<bool, GitError> {
    Ok(git(repo, &["status", "--porcelain"])?.trim().is_empty())
}

/// Whether a local branch exists. Mirrors `gitops.branch_exists`.
pub fn branch_exists(repo: &str, branch: &str) -> bool {
    git(repo, &["rev-parse", "--verify", &format!("refs/heads/{branch}")]).is_ok()
}

/// Review summary for `branch` vs `base`. Mirrors `gitops.review_branch`.
pub fn review_branch(
    repo: &str,
    branch: &str,
    base: &str,
) -> Result<ReviewSummary, GitError> {
    if !is_repo(repo) {
        return Err(GitError(format!("not a git repo: {repo}")));
    }
    if branch == base {
        return Err(GitError("refusing to review base against itself".to_string()));
    }
    for b in [branch, base] {
        if !branch_exists(repo, b) {
            return Err(GitError(format!("unknown branch: {b}")));
        }
    }
    let stat = git(repo, &["diff", "--stat", &format!("{base}...{branch}")])?;
    let files: Vec<String> = git(repo, &["diff", "--name-only", &format!("{base}...{branch}")])?
        .split_whitespace()
        .map(str::to_string)
        .collect();
    let commits: Vec<String> = git(repo, &["log", "--format=%h %s", &format!("{base}..{branch}")])?
        .lines()
        .map(str::to_string)
        .collect();
    Ok(ReviewSummary {
        branch: branch.to_string(),
        base: base.to_string(),
        files,
        stat: stat.trim().to_string(),
        commit_count: commits.len(),
        commits,
    })
}

/// Merge `branch` into `base` with `--no-ff`; returns the merge HEAD hash.
/// Mirrors `gitops.approve_merge` (guards in the same order).
pub fn approve_merge(
    repo: &str,
    branch: &str,
    base: &str,
) -> Result<String, GitError> {
    if branch == base {
        return Err(GitError("refusing to merge base into itself".to_string()));
    }
    if !clean_tree(repo)? {
        return Err(GitError("working tree dirty — refusing to merge".to_string()));
    }
    for b in [branch, base] {
        if !branch_exists(repo, b) {
            return Err(GitError(format!("unknown branch: {b}")));
        }
    }
    if current_branch(repo)? != base {
        git(repo, &["checkout", base])?;
    }
    git(
        repo,
        &["merge", "--no-ff", branch, "-m", &format!("Merge {branch} (MOS approved)")],
    )?;
    Ok(git(repo, &["rev-parse", "HEAD"])?.trim().to_string())
}

/// Real git backend implementing the CLI's `GitopsBackend` trait.
pub struct GitCliBackend;

impl crate::cli::GitopsBackend for GitCliBackend {
    fn review_branch(
        &self,
        repo: &str,
        branch: &str,
        base: &str,
    ) -> Result<ReviewSummary, GitError> {
        review_branch(repo, branch, base)
    }

    fn approve_merge(
        &self,
        repo: &str,
        branch: &str,
        base: &str,
    ) -> Result<String, GitError> {
        approve_merge(repo, branch, base)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cli::{cmd_merge, cmd_review};

    /// Build a temp git repo: main + `worker/thing` one commit ahead.
    /// Mirrors the `_make_repo` fixture in `test_mos_gitops.py`.
    fn make_repo(tag: &str) -> std::path::PathBuf {
        let dir = std::env::temp_dir().join(format!("os-boot-git-{tag}"));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        let g = |args: &[&str]| {
            let out = Command::new("git")
                .arg("-C")
                .arg(&dir)
                .args(args)
                .output()
                .unwrap();
            assert!(out.status.success(), "git {args:?} failed");
        };
        g(&["init", "-b", "main"]);
        g(&["config", "user.email", "t@t.t"]);
        g(&["config", "user.name", "t"]);
        std::fs::write(dir.join("a.txt"), "v1\n").unwrap();
        g(&["add", "."]);
        g(&["commit", "-m", "base"]);
        g(&["checkout", "-b", "worker/thing"]);
        std::fs::write(dir.join("b.txt"), "new\n").unwrap();
        g(&["add", "."]);
        g(&["commit", "-m", "worker commit"]);
        g(&["checkout", "main"]);
        dir
    }

    fn repo_str(dir: &std::path::Path) -> String {
        dir.display().to_string()
    }

    #[test]
    fn test_gitops_review_branch_via_cli() {
        // Mirrors test_mos_gitops.py::test_review_branch, through cmd_review.
        let dir = make_repo("review");
        let out = cmd_review(&repo_str(&dir), "worker/thing", "main", &GitCliBackend);
        assert_eq!(out.code, 0, "{}", out.err);
        assert!(out.out.contains("branch worker/thing vs main: 1 commits, 1 files"), "{}", out.out);
        assert!(out.out.contains("b.txt"), "{}", out.out);
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_gitops_review_rejects_self_unknown_and_non_repo() {
        // Mirrors test_review_rejects_self, test_review_unknown_branch,
        // and test_not_a_repo.
        let dir = make_repo("review-err");
        let repo = repo_str(&dir);
        assert_eq!(cmd_review(&repo, "main", "main", &GitCliBackend).code, 2);
        assert_eq!(cmd_review(&repo, "nope", "main", &GitCliBackend).code, 2);
        let plain = std::env::temp_dir().join("os-boot-git-plain");
        let _ = std::fs::remove_dir_all(&plain);
        std::fs::create_dir_all(&plain).unwrap();
        let out = cmd_review(&repo_str(&plain), "worker/thing", "main", &GitCliBackend);
        assert_eq!(out.code, 2);
        assert!(out.err.contains("not a git repo"), "{}", out.err);
        let _ = std::fs::remove_dir_all(&dir);
        let _ = std::fs::remove_dir_all(&plain);
    }

    #[test]
    fn test_gitops_approve_merge_via_cli() {
        // Mirrors test_mos_gitops.py::test_approve_merge, through cmd_merge.
        let dir = make_repo("merge");
        let out = cmd_merge(&repo_str(&dir), "worker/thing", "main", &GitCliBackend);
        assert_eq!(out.code, 0, "{}", out.err);
        let hash = out.out.trim().rsplit(' ').next().unwrap_or("");
        assert_eq!(hash.len(), 40, "{}", out.out);
        assert!(hash.chars().all(|c| c.is_ascii_hexdigit()), "{}", out.out);
        assert!(dir.join("b.txt").exists());
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_gitops_merge_refuses_dirty_and_self() {
        // Mirrors test_merge_refuses_dirty_tree and test_merge_refuses_self.
        let dir = make_repo("merge-err");
        std::fs::write(dir.join("dirty.txt"), "x").unwrap();
        let repo = repo_str(&dir);
        let out = cmd_merge(&repo, "worker/thing", "main", &GitCliBackend);
        assert_eq!(out.code, 2);
        assert!(out.err.contains("dirty"), "{}", out.err);
        let _ = std::fs::remove_file(dir.join("dirty.txt"));
        let out2 = cmd_merge(&repo, "main", "main", &GitCliBackend);
        assert_eq!(out2.code, 2);
        assert!(out2.err.contains("itself"), "{}", out2.err);
        let _ = std::fs::remove_dir_all(&dir);
    }
}
