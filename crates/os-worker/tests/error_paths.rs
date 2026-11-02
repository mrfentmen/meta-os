//! Every refusal branch in `os-worker`, proven against the public API.
//!
//! Mirrors the contract assertions in the Python originals
//! (`test_os_driver_contract.py`, `test_os_worker_units.py`) without
//! touching private internals. No mocks: the driver tests spawn real
//! `sh` children where a child is needed, and the pure functions get
//! exact inputs.

use os_worker::{
    parse_accept, parse_json, run_driver, validate_spec, verify_accept, wait_child, DriverError,
    JobSpec, MuseDriver, StubDriver,
};
use std::path::PathBuf;
use std::process::Command;
use std::sync::atomic::{AtomicU64, Ordering};

static NEXT: AtomicU64 = AtomicU64::new(0);

fn workdir(tag: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "os-worker-err-{tag}-{}-{}",
        std::process::id(),
        NEXT.fetch_add(1, Ordering::SeqCst)
    ));
    std::fs::create_dir_all(&dir).expect("create temp workdir");
    dir
}

fn signed() -> JobSpec {
    JobSpec::new(
        "7",
        "title",
        "do the work",
        vec!["out.txt".to_string()],
        "file-exists: out.txt",
        Some("sig"),
    )
}

fn expect_err<T>(result: Result<T, DriverError>) -> DriverError {
    match result {
        Ok(_) => panic!("expected a refusal"),
        Err(e) => e,
    }
}

#[test]
fn new_refuses_a_missing_workdir() {
    let missing = std::env::temp_dir().join(format!(
        "os-worker-no-such-dir-{}-{}",
        std::process::id(),
        NEXT.fetch_add(1, Ordering::SeqCst)
    ));
    let _ = std::fs::remove_dir_all(&missing);
    let err = match StubDriver::new(&missing, None) {
        Ok(_) => panic!("missing workdir must be refused"),
        Err(e) => e,
    };
    assert!(err.message().contains("workdir does not exist"));
    assert!(!err.is_unsigned() && !err.is_bad_spec() && !err.is_not_started());
}

#[test]
fn every_operation_before_start_is_not_started() {
    let dir = workdir("before-start");
    let mut driver = StubDriver::new(&dir, None).expect("driver");
    assert!(driver.heartbeat("n").unwrap_err().is_not_started());
    assert!(driver.poll().unwrap_err().is_not_started());
    assert!(driver.stop().unwrap_err().is_not_started());
    assert!(driver.wait(None).unwrap_err().is_not_started());
    assert!(driver.artifacts().unwrap_err().is_not_started());
}

#[test]
fn validate_spec_names_every_missing_field() {
    let mut spec = signed();
    spec.id = "  ".to_string();
    assert!(validate_spec(&spec).unwrap_err().is_bad_spec());

    let mut spec = signed();
    spec.title = String::new();
    assert!(validate_spec(&spec).unwrap_err().is_bad_spec());

    let mut spec = signed();
    spec.spec = String::new();
    assert!(validate_spec(&spec).unwrap_err().is_bad_spec());

    let mut spec = signed();
    spec.files.clear();
    let err = validate_spec(&spec).unwrap_err();
    assert!(err.is_bad_spec());
    assert!(err.message().contains("non empty list"));

    let mut spec = signed();
    spec.files = vec!["ok.txt".to_string(), " ".to_string()];
    assert!(validate_spec(&spec).unwrap_err().is_bad_spec());
}

#[test]
fn validate_spec_refuses_unparseable_accept_lines() {
    let mut spec = signed();
    spec.accept = "not a check".to_string();
    let err = validate_spec(&spec).unwrap_err();
    assert!(err.is_bad_spec());
    assert!(err.message().contains("unparseable accept lines"));
}

#[test]
fn validate_spec_refuses_unsigned_and_blank_signature() {
    let mut spec = signed();
    spec.sig = None;
    assert!(validate_spec(&spec).unwrap_err().is_unsigned());

    let mut spec = signed();
    spec.sig = Some("   ".to_string());
    let err = validate_spec(&spec).unwrap_err();
    assert!(err.is_unsigned());
    assert!(err.message().contains("no signature"));
}

#[test]
fn parse_accept_refuses_every_bad_line_shape() {
    let no_colon = parse_accept("file-exists out.txt").unwrap_err();
    assert!(no_colon.contains("no ':' separator"));

    let unknown = parse_accept("wat: out.txt").unwrap_err();
    assert!(unknown.contains("unknown check"));

    let empty = parse_accept("file-exists:").unwrap_err();
    assert!(empty.contains("empty argument"));

    let contains = parse_accept("contains: out.txt").unwrap_err();
    assert!(contains.contains("path :: substring"));

    assert!(parse_accept("# comment\n\nfile-exists: out.txt").is_ok());
}

#[test]
fn verify_accept_reports_a_parse_failure_as_one_result() {
    let dir = workdir("parse-verify");
    let (ok, results) = verify_accept("nonsense", &dir);
    assert!(!ok);
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].check, "(parse)");
    assert!(!results[0].ok);
}

#[test]
fn start_refuses_an_unsigned_spec_before_spawning() {
    let dir = workdir("unsigned");
    let mut driver = StubDriver::new(&dir, None).expect("driver");
    let mut spec = signed();
    spec.sig = None;
    let err = expect_err(driver.start(&spec, &["true".to_string()]));
    assert!(err.is_unsigned());
    assert!(!driver.has_child());
}

#[test]
fn start_refuses_an_empty_command_without_a_child() {
    let dir = workdir("empty-command");
    let mut driver = StubDriver::new(&dir, None).expect("driver");
    let err = expect_err(driver.start(&signed(), &[]));
    assert!(err.is_bad_spec());
    assert!(err.message().contains("non empty argv"));
    assert!(!driver.has_child());
}

#[test]
fn a_second_start_is_refused_even_after_the_child_exited() {
    let dir = workdir("double-start");
    let mut driver = StubDriver::new(&dir, None).expect("driver");
    let command = ["sh".to_string(), "-c".to_string(), "exit 0".to_string()];
    driver.start(&signed(), &command).expect("first start");
    let _ = driver.wait(None).expect("first wait");
    let err = expect_err(driver.start(&signed(), &command));
    assert!(err.message().contains("already started"));
}

#[test]
fn start_refuses_a_command_that_cannot_spawn() {
    let dir = workdir("no-command");
    let mut driver = StubDriver::new(&dir, None).expect("driver");
    let err = expect_err(driver.start(
        &signed(),
        &["definitely-not-a-binary-xyz".to_string()],
    ));
    assert!(err.message().contains("could not launch"));
    assert!(!driver.has_child());
}

#[test]
fn muse_refuses_a_binary_that_is_not_on_path() {
    let dir = workdir("no-muse");
    let mut driver = MuseDriver::new(&dir, None, Some("/nonexistent/muse-xyz"), &[])
        .expect("driver");
    let err = expect_err(driver.start(&signed()));
    assert!(err.message().contains("muse binary not found"));
    assert!(!driver.has_child());
}

#[test]
fn run_driver_maps_bad_json_and_missing_fields_to_errors() {
    let dir = workdir("run-driver");
    let bad = run_driver("not json", &dir, None, &[]).unwrap_err();
    assert!(bad.starts_with("run_driver: cannot read spec file"));

    let missing = run_driver(r#"{"id":"7","files":["a"]}"#, &dir, None, &[]).unwrap_err();
    assert!(missing.contains("spec field \"title\" must be a string"));

    let no_files = run_driver(r#"{"id":"7"}"#, &dir, None, &[]).unwrap_err();
    assert!(no_files.contains("spec field 'files' must be a list of strings"));

    let wrong_files = run_driver(
        r#"{"id":"7","title":"t","spec":"d","files":"nope"}"#,
        &dir,
        None,
        &[],
    )
    .unwrap_err();
    assert!(wrong_files.contains("spec field 'files' must be a list of strings"));

    let no_binary = run_driver(
        r#"{"id":"7","title":"t","spec":"d","files":["a"],"sig":"s"}"#,
        &dir,
        Some("/nonexistent/muse-xyz"),
        &[],
    )
    .unwrap_err();
    assert!(no_binary.contains("muse binary not found"));

    assert!(parse_json("[").is_err());
    assert!(parse_json("{}").is_ok());
}

#[test]
fn wait_child_times_out_when_asked_to() {
    let mut child = Command::new("sleep").arg("5").spawn().expect("spawn sleep");
    let err = wait_child(&mut child, Some(0.05)).unwrap_err();
    assert!(err.message().contains("timed out"));
    let _ = child.kill();
    let _ = child.wait();
}

#[test]
fn wait_child_reports_a_signal_as_a_negative_code() {
    let mut child = Command::new("sh")
        .arg("-c")
        .arg("kill -TERM $$")
        .spawn()
        .expect("spawn shell");
    let code = wait_child(&mut child, None).expect("wait");
    assert_eq!(code, -15);
}
