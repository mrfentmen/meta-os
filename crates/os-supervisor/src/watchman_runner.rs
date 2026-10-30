//! OS-122 follow-up: the real subprocess runner for the watchman loop.
//! (`os/intel/watchman_runner.py`)
//!
//! `watchman_cycle.run_cycle` collects one relay_watchman --once
//! run per machine from a caller-supplied runner. This module is
//! that runner: it runs the real program once per machine and
//! turns each subprocess result into the (ok, stdout) pair the
//! loop expects.
//!
//! What counts as success: exit 0 means the run happened and
//! stdout holds the event lines. Only exit 0 counts: a nonzero
//! exit means the run failed and its stdout is discarded. A
//! timeout kills the process and counts as a failed run. A
//! missing program, an unreadable argv, or any other subprocess
//! error counts as a failed run, never a raise.

use std::path::Path;
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

pub const DEFAULT_TIMEOUT_SECONDS: u64 = 30;
pub const DEFAULT_SNAPSHOT_DIR: &str = "/run/metaos";

/// The --once argv for one machine's snapshot files.
/// Returns None when the machine name is not usable.
pub fn machine_argv(
    machine: &str,
    snapshot_dir: &str,
    program: &str,
) -> Option<Vec<String>> {
    if machine.trim().is_empty() {
        return None;
    }
    let snapshot_dir = if snapshot_dir.is_empty() {
        DEFAULT_SNAPSHOT_DIR
    } else {
        snapshot_dir
    };
    Some(vec![
        program.to_string(),
        "--once".to_string(),
        "--jobs-file".to_string(),
        format!("{snapshot_dir}/watchman-jobs-{machine}.json"),
        "--agents-file".to_string(),
        format!("{snapshot_dir}/watchman-agents-{machine}.json"),
        "--state-file".to_string(),
        format!("{snapshot_dir}/watchman-state-{machine}.json"),
    ])
}

/// Run one argv to (ok, stdout, detail).
/// ok is True only on exit 0. stdout is the program's stdout on
/// success and "" on every failure. detail is None on success
/// and one of "timeout", "not-found", "bad-argv", "error", or
/// "exit-<code>" on failure. This function never raises.
pub fn run_once(argv: &[String], timeout_secs: u64) -> (bool, String, Option<String>) {
    if argv.is_empty() || argv.iter().any(|p| p.is_empty()) {
        return (false, String::new(), Some("bad-argv".to_string()));
    }
    let timeout = Duration::from_secs(if timeout_secs == 0 {
        DEFAULT_TIMEOUT_SECONDS
    } else {
        timeout_secs
    });
    let mut child = match Command::new(&argv[0])
        .args(&argv[1..])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
    {
        Ok(c) => c,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            return (false, String::new(), Some("not-found".to_string()))
        }
        Err(_) => return (false, String::new(), Some("error".to_string())),
    };
    let start = Instant::now();
    loop {
        match child.try_wait() {
            Err(_) => {
                let _ = child.kill();
                return (false, String::new(), Some("error".to_string()));
            }
            Ok(Some(status)) => {
                let mut stdout = Vec::new();
                use std::io::Read;
                if let Some(mut out) = child.stdout.take() {
                    let _ = out.read_to_end(&mut stdout);
                }
                if !status.success() {
                    let code = status.code().unwrap_or(-1);
                    return (false, String::new(), Some(format!("exit-{code}")));
                }
                return (
                    true,
                    String::from_utf8_lossy(&stdout).into_owned(),
                    None,
                );
            }
            Ok(None) => {
                if start.elapsed() >= timeout {
                    let _ = child.kill();
                    let _ = child.wait();
                    return (false, String::new(), Some("timeout".to_string()));
                }
                std::thread::sleep(Duration::from_millis(10));
            }
        }
    }
}

/// The default relay_watchman program path for one repo root.
/// Production default: /opt/relay/os/watchman/relay_watchman.py.
pub fn default_program(repo_root: &str) -> String {
    format!("{repo_root}/os/watchman/relay_watchman.py")
}

/// A run_cycle-compatible runner over real subprocesses.
/// Never raises: every failure is a (False, "") pair. A None argv models a raising command_for.
pub fn make_subprocess_runner<'a>(
    command_for: Option<Box<dyn Fn(&str) -> Option<Vec<String>> + 'a>>,
    timeout_secs: u64,
    snapshot_dir: &str,
    program: &str,
) -> Box<dyn Fn(&str) -> (bool, String) + 'a> {
    let snapshot_dir = snapshot_dir.to_string();
    let program = program.to_string();
    let owned: Option<Box<dyn Fn(&str) -> Option<Vec<String>> + 'a>> = command_for;
    Box::new(move |name: &str| {
        let argv = match &owned {
            Some(f) => match f(name) {
                Some(a) => a,
                None => return (false, String::new()),
            },
            None => match machine_argv(name, &snapshot_dir, &program) {
                Some(a) => a,
                None => return (false, String::new()),
            },
        };
        let (ok, stdout, _detail) = run_once(&argv, timeout_secs);
        (ok, stdout)
    })
}

/// Snapshot-file existence: a machine with no snapshot files on
/// this host yields a quiet successful run, not a phantom ring.
/// The caller models this by pointing the runner at real files;
/// this helper reports whether any snapshot file exists.
pub fn snapshots_exist(snapshot_dir: &str, machine: &str) -> bool {
    for kind in ["jobs", "agents", "state"] {
        if Path::new(&format!("{snapshot_dir}/watchman-{kind}-{machine}.json")).exists() {
            return true;
        }
    }
    false
}
