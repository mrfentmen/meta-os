//! Safe Git integration for MOS (`os/mos/gitops.py`): review,
//! approve/merge, reject.
//!
//! Workers never push to main. They commit on their own branch;
//! the overseer reviews the diff and merges. Every mutating
//! operation has guards: refuse to merge main into itself, refuse
//! on a dirty tree, refuse unknown branches. Nothing here
//! force-pushes, ever.

use std::time::Duration;

use crate::git::{self, GitError};

const TIMEOUT: Duration = Duration::from_secs(120);

fn git(repo: &str, args: &[&str]) -> Result<String, GitError> {
    git::run_repo(repo, args, TIMEOUT)
}

/// True when `path` is inside a git work tree.
pub fn is_repo(path: &str) -> bool {
    git(path, &["rev-parse", "--git-dir"]).is_ok()
}

pub fn current_branch(repo: &str) -> Result<String, GitError> {
    Ok(git(repo, &["branch", "--show-current"])?
        .trim()
        .to_string())
}

pub fn clean_tree(repo: &str) -> Result<bool, GitError> {
    Ok(git(repo, &["status", "--porcelain"])?.trim().is_empty())
}

pub fn branch_exists(repo: &str, branch: &str) -> bool {
    git(repo, &["rev-parse", "--verify", &format!("refs/heads/{branch}")]).is_ok()
}

/// Review summary for `branch` vs `base`.
#[derive(Debug)]
pub struct Review {
    pub branch: String,
    pub base: String,
    pub files: Vec<String>,
    pub stat: String,
    pub commits: Vec<String>,
    pub commit_count: usize,
}

/// Return a review summary dict for branch vs base.
pub fn review_branch(repo: &str, branch: &str, base: &str) -> Result<Review, GitError> {
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
    let files_out = git(repo, &["diff", "--name-only", &format!("{base}...{branch}")])?;
    let files: Vec<String> = files_out
        .split_whitespace()
        .map(|s| s.to_string())
        .collect();
    let commits_out = git(repo, &["log", "--format=%h %s", &format!("{base}..{branch}")])?;
    let commits: Vec<String> = commits_out.lines().map(|s| s.to_string()).collect();
    let commit_count = commits.len();
    Ok(Review {
        branch: branch.to_string(),
        base: base.to_string(),
        files,
        stat: stat.trim().to_string(),
        commits,
        commit_count,
    })
}

/// Merge branch into base. Returns the merge commit hash.
///
/// Guards: branch != base, both exist, tree clean, base checked
/// out. Uses --no-ff so worker work is always visible as a merge.
pub fn approve_merge(repo: &str, branch: &str, base: &str) -> Result<String, GitError> {
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

/// Record a rejection. Does not delete anything — the branch stays
/// for the worker to fix. Returns a human-readable summary.
pub fn reject_branch(branch: &str, reason: &str) -> Result<String, String> {
    if reason.trim().is_empty() {
        return Err("rejection needs a reason".to_string());
    }
    Ok(format!("REJECTED {branch}: {}", reason.trim()))
}

/// Check out branch into a detached worktree at path. Returns path.
pub fn worktree_add(repo: &str, branch: &str, path: &str) -> Result<String, GitError> {
    if std::path::Path::new(path).exists() {
        return Err(GitError(format!("worktree path already exists: {path}")));
    }
    if !branch_exists(repo, branch) {
        return Err(GitError(format!("unknown branch: {branch}")));
    }
    git(repo, &["worktree", "add", "--detach", path, branch])?;
    Ok(path.to_string())
}

pub fn worktree_remove(repo: &str, path: &str) -> Result<(), GitError> {
    git(repo, &["worktree", "remove", "--force", path])?;
    Ok(())
}
