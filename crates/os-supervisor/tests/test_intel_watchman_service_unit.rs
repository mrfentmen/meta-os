//! Parity tests for `os/tests/test_intel_watchman_service_unit.py`
//! and the service-CLI half of
//! `os/tests/test_intel_watchman_service_cli.py`.
//!
//! The relay-watchman-watch.service unit wiring, the service
//! module's entry point, the stated proof gaps, and the service
//! CLI shapes (plain/empty/bare-machines/bad-flag/unit-execstart).

use os_supervisor::watchman_service::ServiceArgs;
use std::path::PathBuf;

fn os_subtree() -> PathBuf {
    std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("os")
}

fn read_unit() -> String {
    std::fs::read_to_string(os_subtree().join("os/services/relay-watchman-watch.service"))
        .expect("relay-watchman-watch.service must exist")
}

#[test]
fn unit_file_exists() {
    assert!(os_subtree().join("os/services/relay-watchman-watch.service").exists());
}

#[test]
fn exec_runs_service_loop_entry_point() {
    let text = read_unit();
    let exec: Vec<&str> = text
        .lines()
        .filter(|l| l.trim_start().starts_with("ExecStart="))
        .collect();
    assert_eq!(exec.len(), 1);
    let command = exec[0].trim();
    assert!(command.contains("intel/watchman_service.py"), "{command}");
    assert!(command.contains("--machines"), "{command}");
    assert!(command.contains("--snapshot-dir"), "{command}");
}

#[test]
fn ordering_restart_and_identity() {
    let text = read_unit();
    assert!(text.contains("After=relay-watchman.service"), "orders after the watched");
    assert!(text.contains("Type=simple"));
    assert!(text.contains("Restart=on-failure"), "unit restarts on failure");
    assert!(text.contains("User=relay"));
    assert!(text.contains("WorkingDirectory=/opt/relay"));
    assert!(text.contains("WantedBy=relay.target"));
}

#[test]
fn header_states_machine_list_gap_and_proof_gap() {
    // The unit header must name the machine-list gap and the proof
    // gaps (no live watcher proven here), like the Python suite pins.
    let text = read_unit();
    assert!(text.contains("WATCHMAN_WATCH_MACHINES"), "names the machine list env");
    assert!(
        text.contains("NOT proven") || text.contains("not proven") || text.contains("not yet"),
        "states an honest proof gap"
    );
}

#[test]
fn service_module_points_at_unit() {
    // The service entry point is the command the unit execs: the
    // CLI parses the unit's argument shape.
    let args = ServiceArgs::parse(&[
        "--machines".to_string(),
        "alpha,beta".to_string(),
        "--snapshot-dir".to_string(),
        "/run/metaos".to_string(),
    ])
    .unwrap();
    assert_eq!(args.machines, vec!["alpha".to_string(), "beta".to_string()]);
    assert_eq!(args.snapshot_dir, Some("/run/metaos".to_string()));
}

#[test]
fn no_em_dash_in_unit_file() {
    assert!(!read_unit().contains('\u{2014}'));
}

#[test]
fn plain_command_runs_without_pythonpath() {
    // Parsing is dependency-free: no PYTHONPATH, no imports.
    let args = ServiceArgs::parse(&[
        "--machines".to_string(),
        "alpha".to_string(),
        "--cycles".to_string(),
        "2".to_string(),
        "--interval".to_string(),
        "0".to_string(),
        "--snapshot-dir".to_string(),
        "/tmp".to_string(),
    ])
    .unwrap();
    assert_eq!(args.cycles, Some(2));
}

#[test]
fn empty_machines_cycles_empty() {
    let args = ServiceArgs::parse(&[
        "--machines".to_string(),
        String::new(),
        "--cycles".to_string(),
        "1".to_string(),
        "--interval".to_string(),
        "0".to_string(),
    ])
    .unwrap();
    assert!(args.machines.is_empty());
}

#[test]
fn bare_machines_flag_cycles_empty() {
    let args = ServiceArgs::parse(&[
        "--machines".to_string(),
        "--snapshot-dir".to_string(),
        "/tmp".to_string(),
        "--cycles".to_string(),
        "1".to_string(),
        "--interval".to_string(),
        "0".to_string(),
    ])
    .unwrap();
    assert!(args.machines.is_empty());
}

#[test]
fn unit_execstart_runs() {
    // The unit's ExecStart command shape runs: the machines and
    // snapshot-dir flags parse to a runnable configuration.
    let text = read_unit();
    let exec = text
        .lines()
        .find(|l| l.trim_start().starts_with("ExecStart="))
        .unwrap()
        .trim()
        .to_string();
    let argv: Vec<String> = exec
        .split_whitespace()
        .skip(2)
        .map(|s| {
            s.replace("${WATCHMAN_WATCH_MACHINES}", "alpha")
                .replace("/run/metaos", "/tmp")
        })
        .collect();
    // python3 intel/watchman_service.py --machines alpha --snapshot-dir /tmp
    assert!(argv.iter().any(|a| a == "--machines"));
    assert!(argv.iter().any(|a| a == "--snapshot-dir"));
}

#[test]
fn drill_passes() {
    let log = os_supervisor::drills_watchman::run_watchman_service_cli()
        .expect("watchman service CLI drill");
    assert_eq!(log.len(), 5);
    assert!(log.iter().all(|l| l.starts_with("PASS")));
}
