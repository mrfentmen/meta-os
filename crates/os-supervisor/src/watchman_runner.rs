//! Real subprocess runner for the watchman loop (OS-122 follow-up).
//!
//! Port of `os/intel/watchman_runner.py`. [`crate::watchman_cycle`]'s
//! `run_cycle()` collects one relay-watchman `--once` run per machine
//! from a caller-supplied runner, but every runner it has ever seen was
//! a fixture callable. This module is the runner that actually runs
//! something: it runs the real Pax OS-118 program,
//! `os/watchman/relay_watchman.py`, once per machine, and turns each
//! subprocess result into the `(ok, stdout)` pair the loop expects.
//!
//! How one machine is run: by default a machine's snapshots live under a
//! snapshot directory (production default `/run/metaos`, the directory
//! the relay-watchman.service unit reads from) as per-machine files:
//!
//! ```text
//! watchman-jobs-<machine>.json
//! watchman-agents-<machine>.json
//! watchman-state-<machine>.json
//! ```
//!
//! The runner builds `[python, relay_watchman.py, --once, --jobs-file
//! ..., --agents-file ..., --state-file ...]` for that machine and runs
//! it. The state file is per machine so the watchman's own rung dedupe
//! (a job rings once) holds across cycles. A caller that keeps snapshots
//! somewhere else supplies its own `command_for(machine)` callable
//! returning an argv list instead; the default is only a convenience.
//!
//! What counts as success, ported verbatim:
//! - Exit 0 means the run happened and stdout holds the event lines.
//!   Only exit 0 counts: a nonzero exit means the run failed and its
//!   stdout is discarded, even when the program printed partial lines
//!   before failing.
//! - A timeout kills the process and counts as a failed run. A watchman
//!   that hangs must not hang the loop with it.
//! - A missing program, an unreadable argv, or any other subprocess
//!   error counts as a failed run, never a raise. The runner itself
//!   never raises for a bad machine name, a bad argv, or a
//!   `command_for` that raises: every failure is a `(false, "")` pair.
//!
//! What this module does not claim: it runs the CLI locally against
//! snapshot files; it does not reach another machine over the network,
//! does not ssh anywhere, and does not invent a transport for machines
//! whose snapshots are not on this host. It posts nothing to the bus,
//! moves no claim, restarts nothing, reassigns nothing, and sends no
//! push. It reads no live queue. Inputs are never mutated, and no secret
//! appears on any command line.
//!
//! Representation notes:
//! - Python's `sys.executable` (the interpreter running the module) has
//!   no Rust equivalent; argv[0] is `"python3"`, the interpreter the
//!   service unit itself execs (`/usr/bin/python3`).
//! - Python's `_PROGRAM` is computed from the module's file location.
//!   [`default_program`] resolves the same repo-relative path from
//!   `CARGO_MANIFEST_DIR` at runtime when that variable is set (the
//!   normal cargo build), and falls back to the repo-relative path
//!   `os/os/watchman/relay_watchman.py` otherwise. Callers that need an
//!   exact program pass it explicitly to [`machine_argv`].
//! - Python's `run_once` returns a detail string `"exit-<code>"` for a
//!   nonzero exit; a process killed by a signal has no exit code in
//!   Rust, and that case reports `"exit-signal"` instead (untested in
//!   Python, where the code would be negative).
//! - A Python argv that is not a list, or holds a non-string part, is
//!   `"bad-argv"`. Those shapes cannot be built for `&[String]`; an
//!   empty argv or an empty part reports the same detail.

use std::collections::HashMap;
use std::io::Read;
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::process::{Command, Stdio};
use std::sync::mpsc;
use std::thread;
use std::time::Duration;

use crate::watchman_cycle::{
    run_cycle, CycleDiagnostics, MachinesArg, RunnerResult,
};
use crate::watchman_watch::{JournalEntry, WatchmanRecord};

/// Default snapshot directory (production default).
pub const DEFAULT_SNAPSHOT_DIR: &str = "/run/metaos";
/// Default subprocess timeout in seconds.
pub const DEFAULT_TIMEOUT_SECONDS: f64 = 30.0;

/// Path of the repo's relay-watchman program, resolved as described in
/// the module docs.
pub fn default_program() -> String {
    if let Ok(manifest) = std::env::var("CARGO_MANIFEST_DIR") {
        return normalize_path(&format!(
            "{}/../../os/os/watchman/relay_watchman.py",
            manifest
        ));
    }
    "os/os/watchman/relay_watchman.py".to_string()
}

/// Lexically normalize a path: resolve `.` and `..` components without
/// touching the filesystem.
fn normalize_path(path: &str) -> String {
    let absolute = path.starts_with('/');
    let mut parts: Vec<&str> = Vec::new();
    for part in path.split('/') {
        match part {
            "" | "." => {}
            ".." => {
                parts.pop();
            }
            other => parts.push(other),
        }
    }
    let joined = parts.join("/");
    if absolute {
        format!("/{}", joined)
    } else {
        joined
    }
}

/// The `--once` argv for one machine's snapshot files.
///
/// Returns `None` when the machine name is not a usable non-empty
/// string, so callers can treat it as a failed run instead of building
/// an argv out of garbage. An empty snapshot directory or an empty
/// program falls back to the default, as Python's `or` does.
pub fn machine_argv(
    machine: &str,
    snapshot_dir: &str,
    program: Option<&str>,
) -> Option<Vec<String>> {
    if machine.trim().is_empty() {
        return None;
    }
    let snapshot_dir = if snapshot_dir.is_empty() {
        DEFAULT_SNAPSHOT_DIR
    } else {
        snapshot_dir
    };
    let program = match program {
        Some(program) if !program.is_empty() => program.to_string(),
        _ => default_program(),
    };
    let base = |kind: &str| {
        format!(
            "{}/watchman-{}-{}.json",
            snapshot_dir.trim_end_matches('/'),
            kind,
            machine
        )
    };
    Some(vec![
        "python3".to_string(),
        program,
        "--once".to_string(),
        "--jobs-file".to_string(),
        base("jobs"),
        "--agents-file".to_string(),
        base("agents"),
        "--state-file".to_string(),
        base("state"),
    ])
}

/// Run one argv -> `(ok, stdout, detail)`.
///
/// `ok` is true only on exit 0. Stdout is the program's stdout on
/// success and `""` on every failure, so a failed run never leaks
/// partial lines downstream. Detail is `None` on success and one of
/// `"timeout"`, `"not-found"`, `"bad-argv"`, `"error"`, or
/// `"exit-<code>"` on failure. This function never raises (panics).
pub fn run_once(argv: &[String], timeout_seconds: f64) -> (bool, String, Option<String>) {
    if argv.is_empty() || argv.iter().any(|part| part.is_empty()) {
        return (false, String::new(), Some("bad-argv".to_string()));
    }
    let timeout = if timeout_seconds.is_finite() && timeout_seconds > 0.0 {
        timeout_seconds
    } else {
        DEFAULT_TIMEOUT_SECONDS
    };
    let mut child = match Command::new(&argv[0])
        .args(&argv[1..])
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
    {
        Ok(child) => child,
        Err(err) => {
            if err.kind() == std::io::ErrorKind::NotFound {
                return (false, String::new(), Some("not-found".to_string()));
            }
            return (false, String::new(), Some("error".to_string()));
        }
    };
    let stdout_pipe = child.stdout.take();
    let (sender, receiver) = mpsc::channel::<String>();
    thread::spawn(move || {
        let mut text = String::new();
        if let Some(mut pipe) = stdout_pipe {
            let _ = pipe.read_to_string(&mut text);
        }
        let _ = sender.send(text);
    });
    let poll = Duration::from_millis(5);
    let mut waited = Duration::from_secs(0);
    let timeout_duration = Duration::from_secs_f64(timeout);
    loop {
        match child.try_wait() {
            Ok(Some(status)) => {
                let stdout = receiver
                    .recv_timeout(Duration::from_secs(2))
                    .unwrap_or_default();
                if status.success() {
                    return (true, stdout, None);
                }
                let detail = match status.code() {
                    Some(code) => format!("exit-{}", code),
                    None => "exit-signal".to_string(),
                };
                return (false, String::new(), Some(detail));
            }
            Ok(None) => {
                if waited >= timeout_duration {
                    let _ = child.kill();
                    let _ = child.wait();
                    return (false, String::new(), Some("timeout".to_string()));
                }
                thread::sleep(poll);
                waited += poll;
            }
            Err(_) => {
                return (false, String::new(), Some("error".to_string()));
            }
        }
    }
}

/// A `run_cycle()`-compatible runner over real subprocesses.
///
/// `command_for` is a callable taking a machine name and returning an
/// argv list, or `None` for no argv; when omitted, [`machine_argv`]
/// over `snapshot_dir` supplies it. The returned runner takes a machine
/// name and returns `(ok, stdout)`, and never raises: a bad machine, a
/// bad argv, a raising `command_for`, a timeout, or a nonzero exit all
/// yield `(false, "")`. The detail `run_once()` reports is the runner's
/// own concern, not the loop's.
pub fn make_subprocess_runner(
    command_for: Option<Box<dyn FnMut(&str) -> Option<Vec<String>>>>,
    timeout_seconds: f64,
    snapshot_dir: &str,
    program: Option<&str>,
) -> Box<dyn FnMut(&str) -> (bool, String)> {
    let snapshot_dir = snapshot_dir.to_string();
    let program = program.map(|p| p.to_string());
    let mut command_for: Box<dyn FnMut(&str) -> Option<Vec<String>>> =
        match command_for {
            Some(f) => f,
            None => {
                let snapshot_dir = snapshot_dir.clone();
                let program = program.clone();
                Box::new(move |machine: &str| {
                    machine_argv(machine, &snapshot_dir, program.as_deref())
                })
            }
        };
    Box::new(move |machine: &str| {
        let argv = match catch_unwind(AssertUnwindSafe(|| command_for(machine))) {
            Ok(argv) => argv,
            Err(_) => return (false, String::new()),
        };
        let argv = match argv {
            Some(argv) => argv,
            None => return (false, String::new()),
        };
        let (ok, stdout, _detail) = run_once(&argv, timeout_seconds);
        (ok, stdout)
    })
}

/// One service-loop cycle driven by real `--once` runs.
///
/// Builds a subprocess runner and passes it straight to `run_cycle()`,
/// so the production loop calls this one function with its machine list
/// and gets back the same `(records, new_journal, diagnostics)` the
/// fixture adapter returns, with no judgment changed.
pub fn run_cycle_with_subprocess(
    machines: MachinesArg,
    now: f64,
    priors: &HashMap<String, WatchmanRecord>,
    journal: &[JournalEntry],
    restart_ok: &HashMap<String, bool>,
    command_for: Option<Box<dyn FnMut(&str) -> Option<Vec<String>>>>,
    timeout_seconds: f64,
    snapshot_dir: &str,
    program: Option<&str>,
) -> (
    HashMap<String, WatchmanRecord>,
    Vec<JournalEntry>,
    CycleDiagnostics,
) {
    let mut runner =
        make_subprocess_runner(command_for, timeout_seconds, snapshot_dir, program);
    let mut adapter = |name: &str| -> RunnerResult {
        let (ok, stdout) = runner(name);
        RunnerResult::Pair(ok, stdout)
    };
    run_cycle(
        Some(&mut adapter),
        machines,
        now,
        priors,
        journal,
        restart_ok,
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    const NOW: f64 = 1_000_000.0;

    fn tmp_dir(prefix: &str) -> std::path::PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "{}{}",
            prefix,
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    fn write_script(dir: &std::path::Path, name: &str, body: &str) -> String {
        let path = dir.join(name);
        let mut file = std::fs::File::create(&path).unwrap();
        file.write_all(body.as_bytes()).unwrap();
        path.to_string_lossy().to_string()
    }

    fn write_json(dir: &std::path::Path, name: &str, value: &str) {
        let path = dir.join(name);
        let mut file = std::fs::File::create(&path).unwrap();
        file.write_all(value.as_bytes()).unwrap();
    }

    /// The repo's relay-watchman program, located via
    /// `WATCHMAN_TEST_PROGRAM` when set, else via `default_program()`
    /// (CARGO_MANIFEST_DIR under cargo, repo-relative otherwise).
    /// Assembly fix: the old bare-relative fallback assumed the test
    /// binary runs from the repo root, but cargo runs it from the
    /// crate directory, so the real-program tests failed under cargo.
    fn relay_program() -> String {
        if let Ok(path) = std::env::var("WATCHMAN_TEST_PROGRAM") {
            return path;
        }
        default_program()
    }

    #[test]
    fn test_default_argv_shape() {
        // Mirrors TestMachineArgv.test_default_argv_shape, except argv[0]
        // is "python3" (see the module docs: sys.executable has no Rust
        // equivalent) and argv[1] is the default program path.
        let argv = machine_argv("alpha", "/run/metaos", None).unwrap();
        assert_eq!(argv[0], "python3");
        assert!(argv[1].ends_with("os/watchman/relay_watchman.py"));
        assert_eq!(argv[2], "--once");
        assert!(argv.contains(&"/run/metaos/watchman-jobs-alpha.json".to_string()));
        assert!(argv.contains(&"/run/metaos/watchman-agents-alpha.json".to_string()));
        assert!(argv.contains(&"/run/metaos/watchman-state-alpha.json".to_string()));
        // With an explicit program the shape is exact, as in Python.
        let argv = machine_argv(
            "alpha",
            "/run/metaos",
            Some("/repo/os/os/watchman/relay_watchman.py"),
        )
        .unwrap();
        assert_eq!(argv[1], "/repo/os/os/watchman/relay_watchman.py");
    }

    #[test]
    fn test_argv_distinct_per_machine() {
        // Mirrors test_argv_distinct_per_machine.
        let alpha = machine_argv("alpha", "/tmp/snap", None).unwrap();
        let beta = machine_argv("beta", "/tmp/snap", None).unwrap();
        assert_ne!(alpha, beta);
        assert!(!beta.join(" ").contains("alpha"));
    }

    #[test]
    fn test_bad_machine_yields_none() {
        // Mirrors test_bad_machine_yields_none. A Python non-string
        // machine (None, 7) has no typed equivalent; empty and
        // whitespace-only names cover the None case's judgement.
        assert_eq!(machine_argv("", "/tmp/snap", None), None);
        assert_eq!(machine_argv("   ", "/tmp/snap", None), None);
    }

    #[test]
    fn test_success_returns_stdout() {
        // Mirrors TestRunOnce.test_success_returns_stdout.
        let dir = tmp_dir("watchman-runner-test-");
        let script = write_script(&dir, "ok.py", "print('hello')\n");
        let (ok, stdout, detail) =
            run_once(&["python3".to_string(), script], DEFAULT_TIMEOUT_SECONDS);
        assert_eq!((ok, stdout.trim(), detail), (true, "hello", None));
    }

    #[test]
    fn test_nonzero_discards_partial_stdout() {
        // Mirrors test_nonzero_discards_partial_stdout.
        let dir = tmp_dir("watchman-runner-test-");
        let script = write_script(
            &dir,
            "partial.py",
            "import sys\nprint('partial')\nsys.exit(3)\n",
        );
        let (ok, stdout, detail) =
            run_once(&["python3".to_string(), script], DEFAULT_TIMEOUT_SECONDS);
        assert_eq!((ok, stdout, detail), (false, "".to_string(), Some("exit-3".to_string())));
    }

    #[test]
    fn test_timeout() {
        // Mirrors test_timeout.
        let dir = tmp_dir("watchman-runner-test-");
        let script =
            write_script(&dir, "sleepy.py", "import time\ntime.sleep(30)\n");
        let (ok, stdout, detail) =
            run_once(&["python3".to_string(), script], 1.0);
        assert_eq!((ok, stdout, detail), (false, "".to_string(), Some("timeout".to_string())));
    }

    #[test]
    fn test_not_found() {
        // Mirrors test_not_found.
        let dir = tmp_dir("watchman-runner-test-");
        let missing = dir.join("no-such-program").to_string_lossy().to_string();
        let (ok, _stdout, detail) = run_once(&[missing], DEFAULT_TIMEOUT_SECONDS);
        assert_eq!((ok, detail), (false, Some("not-found".to_string())));
    }

    #[test]
    fn test_bad_argv() {
        // Mirrors test_bad_argv. A Python None argv or a non-string part
        // cannot be built for &[String]; the empty argv and the empty
        // part below report the same "bad-argv" detail.
        assert_eq!(
            run_once(&[], DEFAULT_TIMEOUT_SECONDS),
            (false, "".to_string(), Some("bad-argv".to_string()))
        );
        assert_eq!(
            run_once(
                &["python3".to_string(), String::new()],
                DEFAULT_TIMEOUT_SECONDS
            ),
            (false, "".to_string(), Some("bad-argv".to_string()))
        );
    }

    #[test]
    fn test_runner_never_raises() {
        // Mirrors TestSubprocessRunner.test_runner_never_raises.
        let dir = tmp_dir("watchman-runner-test-");
        let dir_str = dir.to_string_lossy().to_string();
        let mut plain =
            make_subprocess_runner(None, DEFAULT_TIMEOUT_SECONDS, &dir_str, None);
        assert_eq!(plain(""), (false, String::new()));
        // A Python None machine has no typed equivalent; an empty
        // machine name is the same failed run.
        let mut raising = make_subprocess_runner(
            Some(Box::new(|_: &str| -> Option<Vec<String>> {
                panic!("boom")
            })),
            DEFAULT_TIMEOUT_SECONDS,
            &dir_str,
            None,
        );
        assert_eq!(raising("alpha"), (false, String::new()));
    }

    #[test]
    fn test_real_cycle_rings_and_stays_quiet() {
        // Mirrors test_real_cycle_rings_and_stays_quiet, run against
        // the real relay-watchman program over temp snapshot files.
        let dir = tmp_dir("watchman-runner-test-");
        let program = relay_program();
        assert!(
            std::path::Path::new(&program).exists(),
            "relay-watchman program missing: {}",
            program
        );
        write_json(
            &dir,
            "watchman-jobs-alpha.json",
            r#"[{"id": "j1", "status": "open", "addressed_to": "hana", "title": "Write the brief"}]"#,
        );
        write_json(
            &dir,
            "watchman-agents-alpha.json",
            r#"{"hana": {"nick": "hana", "heartbeat_at": null}}"#,
        );
        write_json(&dir, "watchman-jobs-beta.json", "[]");
        write_json(&dir, "watchman-agents-beta.json", "{}");
        let dir_str = dir.to_string_lossy().to_string();
        let (records, new_journal, diagnostics) = run_cycle_with_subprocess(
            MachinesArg::List(vec!["alpha".to_string(), "beta".to_string()]),
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
            None,
            DEFAULT_TIMEOUT_SECONDS,
            &dir_str,
            Some(&program),
        );
        assert_eq!(records["alpha"].watchman_alive, Some(true));
        assert!(records["alpha"].last_bell.is_some());
        assert_eq!(records["beta"].last_bell, None);
        assert!(new_journal.is_empty());
        assert!(diagnostics.run_failures.is_empty());
    }

    #[test]
    fn test_failed_run_carries_prior_bell_stripped() {
        // Mirrors test_failed_run_carries_prior_bell_stripped.
        let mut prior = WatchmanRecord {
            watchman_alive: Some(true),
            last_tick: Some(NOW - 1000.0),
            last_bell: Some(NOW - 1000.0),
            last_wake: Some(NOW - 1000.0),
            restart_ok: Some(true),
            ..Default::default()
        };
        let mut priors: HashMap<String, WatchmanRecord> = HashMap::new();
        priors.insert("alpha".to_string(), prior.clone());
        let priors_before = priors.clone();
        let journal: Vec<JournalEntry> = Vec::new();
        let dir = tmp_dir("watchman-runner-test-");
        let dir_str = dir.to_string_lossy().to_string();
        let (records, _new, diagnostics) = run_cycle_with_subprocess(
            MachinesArg::List(vec!["alpha".to_string()]),
            NOW,
            &priors,
            &journal,
            &HashMap::new(),
            Some(Box::new(|_: &str| -> Option<Vec<String>> {
                panic!("boom")
            })),
            DEFAULT_TIMEOUT_SECONDS,
            &dir_str,
            None,
        );
        // The runner contains the raising command_for, so the cycle
        // sees a plain failed run, not an exception.
        assert_eq!(records["alpha"].last_bell, Some(NOW - 1000.0));
        assert_eq!(records["alpha"].restart_ok, None);
        assert!(diagnostics.run_failures.contains(&"alpha".to_string()));
        assert_eq!(priors, priors_before);
        assert!(journal.is_empty());
        let _ = &mut prior;
    }

    #[test]
    fn test_missing_snapshots_are_quiet_not_failed() {
        // Mirrors test_missing_snapshots_are_quiet_not_failed.
        let dir = tmp_dir("watchman-runner-test-");
        let program = relay_program();
        let dir_str = dir.to_string_lossy().to_string();
        let (records, _new, diagnostics) = run_cycle_with_subprocess(
            MachinesArg::List(vec!["ghost".to_string()]),
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
            None,
            DEFAULT_TIMEOUT_SECONDS,
            &dir_str,
            Some(&program),
        );
        assert!(diagnostics.run_failures.is_empty());
        assert_eq!(records["ghost"].last_bell, None);
    }
}
