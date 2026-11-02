//! Test-gap close (B083): the least-covered sections — the supporting
//! SHA/JSON helpers and the small record transforms — get the cases the
//! existing module leaves to the drivers.

use os_worker::{
    apply_heartbeat, compute_artifacts, empty_state, hmac_sha256_hex, json_escape, parse_json,
    sha256_hex, tick_stalls, BridgeJob, JobSpec, Snapshot, SnapshotJob, StallThresholds,
    StubDriver, UplinkState,
};
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};

static NEXT: AtomicU64 = AtomicU64::new(0);

fn workdir(tag: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "os-worker-gap-{tag}-{}-{}",
        std::process::id(),
        NEXT.fetch_add(1, Ordering::SeqCst)
    ));
    std::fs::create_dir_all(&dir).expect("create temp workdir");
    dir
}

fn spec() -> JobSpec {
    JobSpec::new(
        "7",
        "title",
        "do the work",
        vec!["out.txt".to_string()],
        "",
        Some("sig"),
    )
}

fn claimed_job(now: i64) -> SnapshotJob {
    SnapshotJob {
        id: "7".to_string(),
        title: "demo job".to_string(),
        status: "claimed".to_string(),
        claim: Some("pax".to_string()),
        claimed_at: Some(now),
        last_progress: Some(now),
        ..SnapshotJob::default()
    }
}

#[test]
fn sha256_matches_the_fips_vectors() {
    assert_eq!(
        sha256_hex(b""),
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    );
    assert_eq!(
        sha256_hex(b"abc"),
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    );
}

#[test]
fn hmac_sha256_matches_rfc_4231_case_one() {
    let key = [0x0bu8; 20];
    assert_eq!(
        hmac_sha256_hex(&key, b"Hi There"),
        "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"
    );
}

#[test]
fn json_escape_covers_quotes_backslashes_and_controls() {
    let escaped = json_escape("a\"b\\c\nd\re\tf");
    assert!(escaped.starts_with('"') && escaped.ends_with('"'));
    assert!(escaped.contains("\\\""));
    assert!(escaped.contains("\\\\"));
    assert!(escaped.contains("\\n"));
    assert!(escaped.contains("\\r"));
    assert!(escaped.contains("\\t"));

    // Round trip through the real parser: the escaped text is valid JSON.
    let value = parse_json(&escaped).expect("escaped string parses");
    assert_eq!(value.as_str(), Some("a\"b\\c\nd\re\tf"));
}

#[test]
fn parse_json_reads_nested_values_and_preserves_number_spelling() {
    let value = parse_json(r#"{"a":[1,"x",null,true],"b":{"c":2},"n":-3}"#).expect("json");
    assert_eq!(value.get("a").and_then(|v| v.as_str_list()), None);
    assert_eq!(
        value.get("b").and_then(|v| v.get("c")).and_then(|v| v.as_i64()),
        Some(2)
    );
    assert_eq!(value.get("n").and_then(|v| v.as_i64()), Some(-3));
    assert_eq!(value.get("missing"), None);
}

#[test]
fn apply_heartbeat_truncates_toward_zero_like_python_int() {
    let job = BridgeJob {
        id: "7".to_string(),
        title: "demo".to_string(),
        status: "claimed".to_string(),
        claim: "pax".to_string(),
        last_progress_at: Some(1),
    };
    assert_eq!(apply_heartbeat(&job, 10.9).last_progress_at, Some(10));
    assert_eq!(apply_heartbeat(&job, -10.9).last_progress_at, Some(-10));
    // The caller's job is never mutated.
    assert_eq!(job.last_progress_at, Some(1));
}

#[test]
fn a_snapshot_never_yields_both_stall_kinds_for_one_job() {
    let now = 100_000;
    let thresholds = StallThresholds::defaults();
    let present = Snapshot {
        caps: vec!["pax".to_string()],
        presence: vec!["pax".to_string()],
        jobs: vec![claimed_job(now - 3600)],
    };
    let absent = Snapshot {
        presence: Vec::new(),
        ..present.clone()
    };

    let present_alerts = tick_stalls(&present, now, thresholds);
    assert_eq!(present_alerts.len(), 1);
    assert_eq!(present_alerts[0].kind, "progress-stall");

    let absent_alerts = tick_stalls(&absent, now, thresholds);
    assert_eq!(absent_alerts.len(), 1);
    assert_eq!(absent_alerts[0].kind, "presence-stall");
}

#[test]
fn empty_state_is_the_default_state() {
    assert_eq!(empty_state(), UplinkState::default());
    assert!(empty_state().seen_ids.is_empty());
    assert!(empty_state().pending.is_empty());
    assert_eq!(empty_state().failures, 0);
}

#[test]
fn stopped_run_wins_over_the_exit_code_in_the_artifacts_status() {
    let dir = workdir("stopped");
    let mut driver = StubDriver::new(&dir, None).expect("driver");
    let command = ["sh".to_string(), "-c".to_string(), "sleep 5".to_string()];
    driver.start(&spec(), &command).expect("start");
    let stopped = driver.stop().expect("stop");
    assert_eq!(stopped.status, "stopped");
    let artifacts = driver.wait(None).expect("wait");
    assert_eq!(artifacts.status, "stopped");
    assert_eq!(artifacts.exit_code, Some(-15));
}

#[test]
fn artifacts_split_owned_from_unowned_changes_and_ignore_the_log() {
    let dir = workdir("unowned");
    let mut driver = StubDriver::new(&dir, None).expect("driver");
    let command = [
        "sh".to_string(),
        "-c".to_string(),
        "printf x > other.txt".to_string(),
    ];
    driver.start(&spec(), &command).expect("start");
    let artifacts = driver.wait(None).expect("wait");
    assert_eq!(artifacts.status, "done");
    assert_eq!(artifacts.changed_files, vec!["other.txt".to_string()]);
    assert_eq!(artifacts.unowned_files, vec!["other.txt".to_string()]);
    assert!(artifacts.acceptance_ok, "empty accept text verifies true");

    // The log the driver wrote is excluded by name, not counted as work.
    let before = std::collections::HashMap::new();
    let direct = compute_artifacts(&spec(), &dir, &before, false, Some(0));
    assert!(direct.changed_files.contains(&"other.txt".to_string()));
    assert!(!direct.changed_files.iter().any(|f| f == "driver.log"));
}
