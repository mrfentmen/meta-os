//! Watchman service CLI drill (Milo lane, OS-122 follow-up).
//!
//! Port of `os/intel/drills/watchman_service_cli.py` (batch B21,
//! task T124). Port behavior, do not redesign.
//!
//! The service loop was proven in-process and the unit file was
//! proven as a shape, but the command the unit actually execs had
//! never run as a process: the Python script failed at import time,
//! because Python puts the script's own directory first on `sys.path`,
//! not the repo root. The bootstrap in the service module fixes that;
//! this drill proves the fix, with no `PYTHONPATH` set, so no
//! environment variable is load-bearing. Five checks, all as
//! command-line shapes against the landed CLI parser and loop:
//!
//! 1. The plain command runs: `--machines alpha --cycles 2
//!    --interval 0` against a temp snapshot directory exits 0, prints
//!    one cycle line per cycle, and prints the stopped line naming 2
//!    cycles.
//! 2. The config-gap case runs: `--machines ""` exits 0 and reports 0
//!    machines, judging nothing, instead of crashing or inventing a
//!    machine.
//! 3. The unit's own ExecStart runs: the ExecStart line is read out
//!    of the unit data, `/opt/relay` is swapped for the repo root,
//!    `${WATCHMAN_WATCH_MACHINES}` is replaced with `alpha`,
//!    `/run/metaos` is replaced with the temp snapshot directory, and
//!    `--cycles 1 --interval 0` are appended. That exact command exits
//!    0 with a cycle line.
//! 4. A bad flag is a clean exit 2, not a traceback crash: the CLI
//!    contract fails cleanly.
//! 5. The no-env-file unit shape runs: a bare `--machines` directly
//!    before `--snapshot-dir` (what the unit's ExecStart becomes when
//!    systemd expands an unset `${WATCHMAN_WATCH_MACHINES}` to
//!    nothing) exits 0 and cycles empty, instead of an exit 2, which
//!    under `Restart=on-failure` would restart-loop the unit rather
//!    than report the configuration gap.
//!
//! What this drill does NOT claim, stated plainly (as in Python): it
//! proves the command the unit execs, not a booted service. No systemd
//! unit is started here, no restart is observed, no live watchman runs
//! on a booted test image, and the per-machine snapshot files are
//! still the interface until the live queue reader lands. No bus post,
//! no live Redis, no network.
//!
//! # Representation notes (where the typed port differs from Python)
//!
//! - The Python drill spawns the service script as a subprocess and
//!   reads its stdout. A Rust library drill cannot spawn itself, so
//!   [`run_cli`] ports the entry point's logic exactly (parse with
//!   [`parse_service_args`], serve with an `on_cycle` reporter that
//!   collects the same cycle lines [`service_main`] prints, then the
//!   stopped line) and returns the exit code and the lines instead of
//!   printing them. The printing boundary is the only difference: the
//!   lines asserted here are the lines the binary prints.
//! - The Python drill reads the ExecStart line out of
//!   `os/services/relay-watchman-watch.service`. That unit file is
//!   absent from this repo tree (there is no `os/services/`
//!   directory here), so phase 3 reads the ExecStart value from the
//!   landed unit-directive data ([`unit_directive`]), which is the
//!   port of the unit shape the landed service module pins. The
//!   substitutions are the drill's own, applied to that value.
//! - The ExecStart value names the Python entry point
//!   (`/opt/relay/intel/watchman_service.py`) after the interpreter.
//!   The Rust binary IS the entry point, so
//!   [`unit_execstart_argv`] drops the interpreter and script tokens
//!   and returns the flag argv the parser sees; the flag argv is what
//!   phase 3 runs. That drop is the binary boundary, stated here, not
//!   a skipped check: the parsed machines, snapshot directory, and
//!   cycle line are all asserted.
//! - The default cycle path in phases 1 and 3 resolves the Pax
//!   program the way the landed service module does (from
//!   `CARGO_MANIFEST_DIR`); the drill sets that variable to the crate
//!   directory when unset, the same trick the landed service tests
//!   use, so the phases run from a temp verification crate too.
//!
//! # Live-behavior boundary (not faked here)
//!
//! The Python script's `main` prints `PASS`/`FAIL` lines and exits 0
//! or 1. That reporting shape is ported as [`run_drill`], which
//! returns the exit code and the lines instead of printing them; the
//! caller owns printing and exiting. Phases 1 and 3 run real
//! `--once` subprocesses of the Pax program against temp snapshot
//! files, not a live service.

use crate::watchman_cycle::MachinesArg;
use crate::watchman_service::{
    parse_service_args, serve_cycles, unit_directive, ServeOptions,
};
use crate::watchman_watch::{JournalEntry, WatchmanRecord};

/// The outcome of one CLI run: exit code plus the lines the binary
/// would print.
#[derive(Clone, Debug, PartialEq)]
pub struct CliOutcome {
    /// Exit code: 0 on a completed loop, 2 on a malformed command
    /// line.
    pub exit_code: i32,
    /// Cycle lines plus the final stopped line (or the error line).
    pub lines: Vec<String>,
}

/// Run the service-loop command line, collecting its lines.
///
/// This is [`crate::watchman_service::service_main`] with its prints
/// collected instead of printed: parse, serve with an `on_cycle`
/// reporter in the same line format, then the stopped line. A
/// malformed command line yields exit 2 with an `error:` line and no
/// traceback. `argv` omits the program name, as in the landed parser.
/// The caller must pass a bounded `--cycles` value: an unbounded run
/// loops until stopped, exactly as the binary does.
pub fn run_cli(argv: &[String]) -> CliOutcome {
    let args = match parse_service_args(argv) {
        Ok(args) => args,
        Err(err) => {
            return CliOutcome {
                exit_code: 2,
                lines: vec![format!("error: {}", err)],
            };
        }
    };
    let mut options = ServeOptions::default();
    options.max_cycles = args.cycles;
    options.interval_seconds = Some(args.interval);
    options.snapshot_dir = args.snapshot_dir.clone();
    let lines_cell = std::rc::Rc::new(std::cell::RefCell::new(Vec::new()));
    let lines_clone = lines_cell.clone();
    options.on_cycle = Some(Box::new(
        move |index: usize,
              records: &std::collections::HashMap<String, WatchmanRecord>,
              new_journal: &[JournalEntry],
              diagnostics: &crate::watchman_cycle::CycleDiagnostics| {
            lines_clone.borrow_mut().push(format!(
                "cycle {}: {} machines, {} new journal, {:?}",
                index,
                records.len(),
                new_journal.len(),
                diagnostics
            ));
        },
    ));
    let result = serve_cycles(MachinesArg::List(args.machines), options);
    let mut lines = lines_cell.borrow().clone();
    lines.push(format!(
        "service loop stopped after {} cycles",
        result.cycles_run
    ));
    CliOutcome {
        exit_code: 0,
        lines,
    }
}

/// The unit's ExecStart, after the Python drill's substitutions, as
/// the flag argv the CLI parser sees.
///
/// `repo_root` replaces `/opt/relay`, `machines` replaces
/// `${WATCHMAN_WATCH_MACHINES}`, and `snapshot_dir` replaces
/// `/run/metaos`. The interpreter and script tokens are dropped: the
/// Rust binary is the entry point (see the module docs). Returns
/// `None` when the landed unit data carries no ExecStart.
pub fn unit_execstart_argv(
    repo_root: &str,
    machines: &str,
    snapshot_dir: &str,
) -> Option<Vec<String>> {
    let exec_start = unit_directive("ExecStart")?;
    let command = exec_start
        .replace("/opt/relay", repo_root)
        .replace("${WATCHMAN_WATCH_MACHINES}", machines)
        .replace("/run/metaos", snapshot_dir);
    let tokens: Vec<String> =
        command.split_whitespace().map(|t| t.to_string()).collect();
    // Drop the interpreter and the script path; the rest is the flag
    // argv.
    if tokens.len() < 2 {
        return None;
    }
    Some(tokens[2..].to_vec())
}

/// Point `CARGO_MANIFEST_DIR` at this repo's crate directory when it
/// is unset, so the landed default cycle function resolves the Pax
/// program (the same trick the landed service tests use).
pub fn ensure_manifest_dir() {
    if std::env::var("CARGO_MANIFEST_DIR").is_err() {
        if let Ok(cwd) = std::env::current_dir() {
            let manifest = cwd.join("crates/os-supervisor");
            if manifest.exists() {
                std::env::set_var("CARGO_MANIFEST_DIR", &manifest);
            }
        }
    }
}

/// A fresh temp snapshot directory with the Python drill's alpha
/// fixtures written.
pub fn fixture_dir() -> std::path::PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "watchman-service-cli-{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir_all(&dir).unwrap();
    std::fs::write(
        dir.join("watchman-jobs-alpha.json"),
        r#"[{"id": "j1", "status": "open", "addressed_to": "hana", "title": "Write the brief"}]"#,
    )
    .unwrap();
    std::fs::write(
        dir.join("watchman-agents-alpha.json"),
        r#"{"hana": {"nick": "hana", "heartbeat_at": null}}"#,
    )
    .unwrap();
    dir
}

/// String arguments, as a test would write them on a command line.
pub fn argv(items: &[&str]) -> Vec<String> {
    items.iter().map(|item| item.to_string()).collect()
}

/// Phase 1: the plain command runs 2 cycles, exit 0.
pub fn phase_plain_command(dir: &std::path::Path) -> bool {
    ensure_manifest_dir();
    let outcome = run_cli(&argv(&[
        "--machines",
        "alpha",
        "--cycles",
        "2",
        "--interval",
        "0",
        "--snapshot-dir",
        &dir.to_string_lossy(),
    ]));
    outcome.exit_code == 0
        && outcome
            .lines
            .iter()
            .filter(|line| line.starts_with("cycle "))
            .count()
            == 2
        && outcome
            .lines
            .iter()
            .any(|line| line.contains("service loop stopped after 2 cycles"))
}

/// Phase 2: an empty machine list cycles empty, exit 0.
pub fn phase_empty_machines(dir: &std::path::Path) -> bool {
    let outcome = run_cli(&argv(&[
        "--machines",
        "",
        "--cycles",
        "1",
        "--interval",
        "0",
        "--snapshot-dir",
        &dir.to_string_lossy(),
    ]));
    outcome.exit_code == 0
        && outcome
            .lines
            .iter()
            .any(|line| line.contains("cycle 0: 0 machines"))
}

/// Phase 3: the unit's ExecStart command runs, exit 0.
///
/// The repo root for the substitution is the working directory when
/// it holds the crate tree, else the current directory as a string;
/// the substituted script path is dropped by [`unit_execstart_argv`],
/// so only the flag argv reaches the parser.
pub fn phase_unit_execstart(dir: &std::path::Path) -> bool {
    ensure_manifest_dir();
    let repo_root = match std::env::current_dir() {
        Ok(cwd) => cwd.to_string_lossy().to_string(),
        Err(_) => ".".to_string(),
    };
    let mut flags = match unit_execstart_argv(
        &repo_root,
        "alpha",
        &dir.to_string_lossy(),
    ) {
        Some(flags) => flags,
        None => return false,
    };
    flags.extend(argv(&["--cycles", "1", "--interval", "0"]));
    let parsed = match parse_service_args(&flags) {
        Ok(parsed) => parsed,
        Err(_) => return false,
    };
    if parsed.machines != vec!["alpha".to_string()] {
        return false;
    }
    let outcome = run_cli(&flags);
    outcome.exit_code == 0
        && outcome
            .lines
            .iter()
            .any(|line| line.contains("cycle 0: 1 machines"))
}

/// Phase 4: a bad flag exits 2 cleanly, no traceback.
pub fn phase_bad_flag() -> bool {
    let outcome = run_cli(&argv(&["--bogus-flag"]));
    outcome.exit_code == 2
        && !outcome
            .lines
            .iter()
            .any(|line| line.contains("Traceback"))
}

/// Phase 5: a bare `--machines` cycles empty, exit 0.
pub fn phase_bare_machines(dir: &std::path::Path) -> bool {
    let outcome = run_cli(&argv(&[
        "--machines",
        "--snapshot-dir",
        &dir.to_string_lossy(),
        "--cycles",
        "1",
        "--interval",
        "0",
    ]));
    outcome.exit_code == 0
        && outcome
            .lines
            .iter()
            .any(|line| line.contains("cycle 0: 0 machines"))
}

/// Run every phase, in the Python drill's order, against one shared
/// fixture directory.
///
/// Returns `(exit_code, lines)`: exit 0 with one `PASS` line per
/// phase on success, 1 otherwise. The caller owns printing.
pub fn run_drill() -> (i32, Vec<String>) {
    let dir = fixture_dir();
    let phases: [(&str, bool); 5] = [
        ("phase 1: plain command runs 2 cycles, exit 0", phase_plain_command(&dir)),
        ("phase 2: empty machine list cycles empty, exit 0", phase_empty_machines(&dir)),
        ("phase 3: unit ExecStart command runs, exit 0", phase_unit_execstart(&dir)),
        ("phase 4: bad flag exits 2 cleanly", phase_bad_flag()),
        ("phase 5: bare --machines cycles empty, exit 0", phase_bare_machines(&dir)),
    ];
    let mut lines = Vec::new();
    let mut failed = 0;
    for (name, ok) in phases {
        if ok {
            lines.push(format!("PASS {}", name));
        } else {
            lines.push(format!("FAIL {}", name));
            failed += 1;
        }
    }
    if failed == 0 {
        lines.push("ALL PASS: watchman service CLI".to_string());
    }
    (if failed == 0 { 0 } else { 1 }, lines)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_drill_phase1_plain_command() {
        // Mirrors the Python drill's phase 1 and
        // test_plain_command_runs_without_pythonpath in
        // test_intel_watchman_service_cli.py.
        let dir = fixture_dir();
        assert!(phase_plain_command(&dir));
    }

    #[test]
    fn test_drill_phase2_empty_machines() {
        // Mirrors the Python drill's phase 2 and
        // test_empty_machines_cycles_empty.
        let dir = fixture_dir();
        assert!(phase_empty_machines(&dir));
    }

    #[test]
    fn test_drill_phase3_unit_execstart() {
        // Mirrors the Python drill's phase 3 and
        // test_unit_execstart_runs, against the landed unit-directive
        // data (the unit file itself is absent from this repo tree;
        // see the module docs).
        let dir = fixture_dir();
        assert!(phase_unit_execstart(&dir));
    }

    #[test]
    fn test_drill_phase4_bad_flag() {
        // Mirrors the Python drill's phase 4.
        assert!(phase_bad_flag());
    }

    #[test]
    fn test_drill_phase5_bare_machines() {
        // Mirrors the Python drill's phase 5 and
        // test_bare_machines_flag_cycles_empty.
        let dir = fixture_dir();
        assert!(phase_bare_machines(&dir));
    }

    #[test]
    fn test_drill_passes() {
        // Mirrors test_drill_passes in test_intel_watchman_service_cli.py
        // (via the service-CLI drill script): the drill itself exits 0.
        let (code, lines) = run_drill();
        assert_eq!(code, 0, "drill lines: {:?}", lines);
        assert!(lines.iter().any(|l| l.contains("ALL PASS: watchman service CLI")));
    }
}
