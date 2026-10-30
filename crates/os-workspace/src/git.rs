//! Shared local-git runner for the workspace crate.
//!
//! Both `artifact_store` and `gitops` shell out to the `git`
//! binary; this module holds the one runner so timeout, error,
//! and missing-binary behavior agree. Timeouts are enforced by a
//! poll loop (the Python originals pass `timeout=` to
//! `subprocess.run`); a timed-out or missing `git` is a
//! [`GitError`], never a hang and never a panic.

use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

/// Any git failure: missing binary, timeout, or nonzero exit.
#[derive(Debug, Clone)]
pub struct GitError(pub String);

impl std::fmt::Display for GitError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl std::error::Error for GitError {}

/// Run `git -c safe.directory=* -C <root> <args>` with a timeout.
/// Returns stdout on success; every failure becomes a `GitError`.
/// Mirrors `artifact_store._git` (binary-safe callers use
/// [`run_bytes`] instead).
pub fn run(root: &str, args: &[&str], timeout: Duration) -> Result<String, GitError> {
    let out = run_bytes(root, args, None, timeout)?;
    String::from_utf8(out).map_err(|e| GitError(format!("git failed: {e}")))
}

/// Binary-safe variant: optional stdin bytes, raw stdout bytes.
pub fn run_bytes(
    root: &str,
    args: &[&str],
    input: Option<&[u8]>,
    timeout: Duration,
) -> Result<Vec<u8>, GitError> {
    let mut cmd = Command::new("git");
    cmd.arg("-c")
        .arg("safe.directory=*")
        .arg("-C")
        .arg(root)
        .args(args)
        .stdin(if input.is_some() {
            Stdio::piped()
        } else {
            Stdio::null()
        })
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut child = cmd.spawn().map_err(|e| {
        if e.kind() == std::io::ErrorKind::NotFound {
            GitError("git is not available on this machine".to_string())
        } else {
            GitError(format!("git failed: {e}"))
        }
    })?;
    if let Some(data) = input {
        use std::io::Write;
        if let Some(mut stdin) = child.stdin.take() {
            let _ = stdin.write_all(data);
        }
    }
    let start = Instant::now();
    loop {
        match child.try_wait() {
            Err(e) => {
                let _ = child.kill();
                return Err(GitError(format!("git failed: {e}")));
            }
            Ok(Some(status)) => {
                let mut stdout = Vec::new();
                let mut stderr = Vec::new();
                use std::io::Read;
                if let Some(mut out) = child.stdout.take() {
                    let _ = out.read_to_end(&mut stdout);
                }
                if let Some(mut err) = child.stderr.take() {
                    let _ = err.read_to_end(&mut stderr);
                }
                if !status.success() {
                    let detail = String::from_utf8_lossy(&stderr);
                    let tail: String = detail
                        .chars()
                        .rev()
                        .take(500)
                        .collect::<Vec<_>>()
                        .into_iter()
                        .rev()
                        .collect();
                    return Err(GitError(format!(
                        "git {} failed: {}",
                        args.first().unwrap_or(&"?"),
                        tail.trim()
                    )));
                }
                return Ok(stdout);
            }
            Ok(None) => {
                if start.elapsed() >= timeout {
                    let _ = child.kill();
                    let _ = child.wait();
                    return Err(GitError(format!(
                        "git {} timed out",
                        args.join(" ")
                    )));
                }
                std::thread::sleep(Duration::from_millis(10));
            }
        }
    }
}

/// Plain `git -C <repo> <args>` runner for `gitops` (no
/// `safe.directory` override, text stdout). Mirrors
/// `gitops._git`, including its error text shape.
pub fn run_repo(repo: &str, args: &[&str], timeout: Duration) -> Result<String, GitError> {
    let mut cmd = Command::new("git");
    cmd.arg("-C")
        .arg(repo)
        .args(args)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut child = cmd.spawn().map_err(|_| GitError("git not found on PATH".to_string()))?;
    let start = Instant::now();
    loop {
        match child.try_wait() {
            Err(_) => {
                let _ = child.kill();
                return Err(GitError(format!("git {} timed out", args.join(" "))));
            }
            Ok(Some(status)) => {
                let mut stdout = Vec::new();
                let mut stderr = Vec::new();
                use std::io::Read;
                if let Some(mut out) = child.stdout.take() {
                    let _ = out.read_to_end(&mut stdout);
                }
                if let Some(mut err) = child.stderr.take() {
                    let _ = err.read_to_end(&mut stderr);
                }
                if !status.success() {
                    let detail = String::from_utf8_lossy(&stderr);
                    let tail: String = detail
                        .chars()
                        .rev()
                        .take(500)
                        .collect::<Vec<_>>()
                        .into_iter()
                        .rev()
                        .collect();
                    return Err(GitError(format!(
                        "git {} failed: {}",
                        args.join(" "),
                        tail.trim()
                    )));
                }
                return Ok(String::from_utf8_lossy(&stdout).into_owned());
            }
            Ok(None) => {
                if start.elapsed() >= timeout {
                    let _ = child.kill();
                    let _ = child.wait();
                    return Err(GitError(format!("git {} timed out", args.join(" "))));
                }
                std::thread::sleep(Duration::from_millis(10));
            }
        }
    }
}

/// Is `git` on PATH at all?
pub fn have_git() -> bool {
    Command::new("git")
        .arg("--version")
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}
