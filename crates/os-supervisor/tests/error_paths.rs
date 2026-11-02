//! Error-path tests for `os-supervisor` (B014).
//!
//! Each test pins one refusal branch to the behaviour its code and docs
//! state. Nothing is asserted that the module does not do: where the
//! code returns a typed `Err` or exit code, that is what is checked.

use std::collections::HashMap;

use os_supervisor::overseer::parse_job_id;
use os_supervisor::reconcile::{
    blocked_from, exit_code, reconcile, render_summary, JobHash, ReconcileBackend,
    ReconcileReport,
};
use os_supervisor::relay_watchman::{
    once_exit_code, run_once, validate_args, InputLoad, StateLoad,
};
use os_supervisor::thresholds::parse_env_int;
use os_supervisor::watchdog::{env_int_range, paginate, parse_json, render_explanation};
use os_supervisor::watchman_service::parse_service_args;

struct FakeBackend {
    redis: bool,
    sweep: Result<Vec<String>, String>,
    prune: Result<Vec<String>, String>,
    hashes: Vec<(String, JobHash)>,
}

impl ReconcileBackend for FakeBackend {
    fn redis_ok(&self) -> bool {
        self.redis
    }
    fn sweep_leases(&mut self) -> Result<Vec<String>, String> {
        self.sweep.clone()
    }
    fn prune_stale(&mut self) -> Result<Vec<String>, String> {
        self.prune.clone()
    }
    fn job_hashes(&self) -> Vec<(String, JobHash)> {
        self.hashes.clone()
    }
}

fn hash(pairs: &[(&str, &str)]) -> JobHash {
    pairs
        .iter()
        .map(|(k, v)| (k.to_string(), v.to_string()))
        .collect()
}

#[test]
fn paginate_refuses_a_zero_page_size() {
    let err = paginate(&[1, 2, 3], 0).expect_err("zero page size must be refused");
    assert_eq!(err, "page_size must be a positive int");
}

#[test]
fn paginate_refuses_a_negative_page_size() {
    let err = paginate(&[1, 2, 3], -7).expect_err("negative page size must be refused");
    assert_eq!(err, "page_size must be a positive int");
}

#[test]
fn parse_json_refuses_a_truncated_document() {
    assert!(parse_json("{").is_err());
    assert!(parse_json("not json at all").is_err());
}

#[test]
fn parse_json_refuses_trailing_characters() {
    let err = parse_json("{} trailing").expect_err("trailing text must be refused");
    assert_eq!(err, "trailing characters after JSON document");
}

#[test]
#[should_panic]
fn unknown_explanation_template_panics() {
    let _ = render_explanation("no-such-template", &[]);
}

#[test]
fn reconcile_stops_when_the_backend_is_unreachable() {
    let mut backend = FakeBackend {
        redis: false,
        sweep: Ok(vec!["7".to_string()]),
        prune: Ok(vec!["nick".to_string()]),
        hashes: vec![("8".to_string(), hash(&[("status", "blocked")]))],
    };
    let report = reconcile(&mut backend);
    assert!(!report.redis);
    assert!(report.requeued.is_empty());
    assert!(report.pruned.is_empty());
    assert!(report.unverified.is_empty());
    assert!(report.blocked.is_empty());
    assert_eq!(exit_code(&report), 2);
    assert!(render_summary(&report).contains("redis: UNREACHABLE"));
}

#[test]
fn reconcile_tolerates_sweep_and_prune_failures_and_still_reads_jobs() {
    let mut backend = FakeBackend {
        redis: true,
        sweep: Err("sweep broke".to_string()),
        prune: Err("prune broke".to_string()),
        hashes: vec![
            ("8".to_string(), hash(&[("status", "done")])),
            (
                "9".to_string(),
                hash(&[("status", "blocked"), ("note", "waiting")]),
            ),
        ],
    };
    let report = reconcile(&mut backend);
    assert!(report.redis);
    assert!(report.requeued.is_empty());
    assert!(report.pruned.is_empty());
    assert_eq!(report.unverified, vec!["8".to_string()]);
    assert_eq!(
        report.blocked,
        vec![("9".to_string(), "waiting".to_string())]
    );
    let summary = render_summary(&report);
    assert!(summary.contains("UNVERIFIED 8"));
    assert!(summary.contains("BLOCKED 9: waiting"));
    assert_eq!(exit_code(&report), 0);
}

#[test]
fn parse_job_id_refuses_output_with_no_job_line() {
    let err = parse_job_id("posted nothing\n").expect_err("no JOB line must fail");
    assert!(err.starts_with("could not parse job id from:"));
}

#[test]
fn parse_job_id_takes_the_first_job_line() {
    assert_eq!(
        parse_job_id("noise\nJOB 42 extra\nJOB 43\n").expect("first line wins"),
        "42"
    );
}

#[test]
fn service_args_refuse_an_unknown_flag() {
    let err = parse_service_args(&["--wat".to_string()]).expect_err("unknown flag must fail");
    assert_eq!(err, "unknown argument: --wat");
}

#[test]
fn service_args_refuse_a_missing_cycles_value() {
    let err = parse_service_args(&["--cycles".to_string()]).expect_err("missing value must fail");
    assert_eq!(err, "missing --cycles value");
}

#[test]
fn relay_args_refuse_a_non_positive_interval() {
    let err = validate_args(0, 0.0).expect_err("zero interval must be refused");
    assert_eq!(
        err.0,
        "watchman: --interval must be positive and --heartbeat-stale-seconds non-negative"
    );
}

#[test]
fn relay_args_refuse_a_negative_stale_window() {
    assert!(validate_args(10, -1.0).is_err());
}

#[test]
fn relay_once_exits_2_on_a_malformed_input_file() {
    let result = run_once(
        InputLoad::<Vec<os_supervisor::relay_watchman::Job>>::Malformed(
            "jobs.json: bad shape".to_string(),
        ),
        InputLoad::Missing,
        StateLoad::Missing,
        0.0,
        300.0,
    );
    assert!(result.is_err());
    assert_eq!(result.unwrap_err().0, "jobs.json: bad shape");
    assert_eq!(
        once_exit_code(&run_once(
            InputLoad::Malformed("x".to_string()),
            InputLoad::Missing,
            StateLoad::Missing,
            0.0,
            300.0,
        )),
        2
    );
}

#[test]
fn env_values_below_the_minimum_fall_back() {
    assert_eq!(parse_env_int(Some("-1"), 10, 0), 10);
    assert_eq!(parse_env_int(Some("0"), 300, 1), 300);
}

#[test]
fn env_int_range_refuses_outside_both_bounds() {
    assert_eq!(env_int_range(Some("0"), 80, 1, 100), 80);
    assert_eq!(env_int_range(Some("101"), 80, 1, 100), 80);
    assert_eq!(env_int_range(Some("1"), 80, 1, 100), 1);
    assert_eq!(env_int_range(Some("100"), 80, 1, 100), 100);
}

#[test]
fn blocked_reasons_are_cut_at_200_characters() {
    let long = "x".repeat(250);
    let hashes = vec![(
        "9".to_string(),
        hash(&[("status", "blocked"), ("note", long.as_str())]),
    )];
    let blocked = blocked_from(&hashes);
    assert_eq!(blocked.len(), 1);
    assert_eq!(blocked[0].1.chars().count(), 200);
}

#[test]
fn a_clean_report_is_not_default_when_redis_answers() {
    let mut backend = FakeBackend {
        redis: true,
        sweep: Ok(Vec::new()),
        prune: Ok(Vec::new()),
        hashes: Vec::new(),
    };
    let report = reconcile(&mut backend);
    assert_eq!(
        report,
        ReconcileReport {
            redis: true,
            ..ReconcileReport::default()
        }
    );
    assert!(report.is_clean());
    assert!(render_summary(&report).contains("RECONCILE_CLEAN"));
}

#[test]
fn an_empty_hash_map_never_produces_a_blocked_reason() {
    let mut empty = HashMap::new();
    empty.insert("status".to_string(), "blocked".to_string());
    let blocked = blocked_from(&[("1".to_string(), empty)]);
    assert_eq!(blocked, vec![("1".to_string(), String::new())]);
}
