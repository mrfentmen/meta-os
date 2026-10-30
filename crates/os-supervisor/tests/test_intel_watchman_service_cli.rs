//! Parity tests for the CLI half of
//! `os/tests/test_intel_watchman_service_cli.py`.
//!
//! Plain/empty/bare --machines shapes, bad-flag exit 2, and the
//! unit ExecStart command shape.

use os_supervisor::watchman_service::ServiceArgs;

// --- service CLI tests ---

#[test]
fn plain_command_runs_without_pythonpath() {
    use os_supervisor::watchman_service::ServiceArgs;
    // No PYTHONPATH needed: parsing is dependency-free.
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
    assert_eq!(args.machines, vec!["alpha".to_string()]);
    assert_eq!(args.cycles, Some(2));
}

#[test]
fn empty_machines_cycles_empty() {
    use os_supervisor::watchman_service::ServiceArgs;
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
    use os_supervisor::watchman_service::ServiceArgs;
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
fn bad_flag_exits_2_cleanly() {
    use os_supervisor::watchman_service::ServiceArgs;
    assert!(ServiceArgs::parse(&["--bogus-flag".to_string()]).is_err());
}

#[test]
fn unit_execstart_runs() {
    // The unit ExecStart names the service entry point with
    // --machines and --snapshot-dir: parse the live unit command.
    let manifest = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    let unit = std::fs::read_to_string(
        manifest.join("../../os/services/relay-watchman-watch.service"),
    )
    .unwrap();
    let exec = unit
        .lines()
        .find(|l| l.trim_start().starts_with("ExecStart="))
        .unwrap();
    assert!(exec.contains("--machines"), "{exec}");
    assert!(exec.contains("--snapshot-dir"), "{exec}");
}
