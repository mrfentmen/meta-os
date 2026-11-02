//! B203 — test-gap close.
//!
//! `crates/stack` has one module. Its best-covered area is configuration
//! resolution and service shape; the gaps were `from_env` (never called
//! by a test), namespace propagation into `plan`, the readiness
//! constants as constructs rather than literals, and the summary lines
//! under custom bases. These tests close those gaps.

use stack::{
    plan, summary_lines, Readiness, StackConfig, Transport, AGENT_SETTLE_SECS,
    WAIT_HTTP_INTERVAL_MS, WAIT_HTTP_MAX_ATTEMPTS, WAIT_HTTP_TIMEOUT_SECS,
};
use std::env;

/// Saves the named variables and restores them on drop, so the one test
/// that touches the process environment cannot leak into another run.
struct EnvGuard(Vec<(&'static str, Option<String>)>);

impl EnvGuard {
    fn new(keys: &[&'static str]) -> Self {
        EnvGuard(keys.iter().map(|k| (*k, env::var(*k).ok())).collect())
    }
}

impl Drop for EnvGuard {
    fn drop(&mut self) {
        for (key, value) in &self.0 {
            match value {
                Some(v) => env::set_var(*key, v),
                None => env::remove_var(*key),
            }
        }
    }
}

#[test]
fn from_env_reads_live_values_and_empty_falls_back() {
    let _guard = EnvGuard::new(&[
        "RELAY_PORT",
        "QUEUE_PORT",
        "PORT",
        "SPARK_API_KEY",
        "TRIO_JOB_NS",
    ]);

    env::set_var("RELAY_PORT", "9100");
    env::set_var("QUEUE_PORT", "9101");
    env::set_var("PORT", "9102");
    env::set_var("SPARK_API_KEY", "sk-gap");
    env::set_var("TRIO_JOB_NS", "gap-ns");

    let c = StackConfig::from_env();
    assert_eq!(c.relay_port, "9100");
    assert_eq!(c.queue_port, "9101");
    assert_eq!(c.app_port, "9102");
    assert_eq!(c.transport, Transport::ProductionDirect);
    assert_eq!(c.job_ns.as_deref(), Some("gap-ns"));

    // `${VAR:-default}`: an exported empty value falls back.
    env::set_var("RELAY_PORT", "");
    assert_eq!(StackConfig::from_env().relay_port, "8787");
}

#[test]
fn summary_lines_carry_custom_bases() {
    let c = StackConfig::from_entries(&[
        ("RELAY_PORT", "9000"),
        ("QUEUE_PORT", "9001"),
        ("PORT", "9002"),
    ]);
    let lines = summary_lines(&c);
    assert_eq!(lines.len(), 4);
    assert!(lines[0].contains("http://127.0.0.1:9000/"));
    assert!(lines[1].contains("http://127.0.0.1:9001/health"));
    assert!(lines[2].contains("http://127.0.0.1:9000/rooms/main"));
    assert!(lines[3].contains("http://127.0.0.1:9002/"));
    assert!(lines[3].contains("http://127.0.0.1:9002/api/assess"));
}

#[test]
fn plan_without_job_namespace_has_no_namespace_env() {
    for service in plan(&StackConfig::from_entries(&[])) {
        assert!(
            service.env.iter().all(|(key, _)| key != "TRIO_JOB_NS"),
            "{} invented TRIO_JOB_NS",
            service.name
        );
    }
}

#[test]
fn plan_with_empty_job_namespace_is_inherited() {
    let services = plan(&StackConfig::from_entries(&[("TRIO_JOB_NS", "")]));
    assert!(services[1]
        .env
        .iter()
        .any(|(key, value)| key == "TRIO_JOB_NS" && value.is_empty()));
    assert!(services[2]
        .env
        .iter()
        .any(|(key, value)| key == "TRIO_JOB_NS" && value.is_empty()));
    assert!(services[0]
        .env
        .iter()
        .all(|(key, _)| key != "TRIO_JOB_NS"));
    assert!(services[3]
        .env
        .iter()
        .all(|(key, _)| key != "TRIO_JOB_NS"));
}

#[test]
fn readiness_constants_are_the_script_values() {
    assert_eq!(WAIT_HTTP_MAX_ATTEMPTS, 50);
    assert_eq!(WAIT_HTTP_INTERVAL_MS, 200);
    assert_eq!(WAIT_HTTP_TIMEOUT_SECS, 2);
    assert_eq!(AGENT_SETTLE_SECS, 1);

    let services = plan(&StackConfig::from_entries(&[]));
    match &services[0].readiness {
        Readiness::HttpHealth {
            max_attempts,
            interval_ms,
            timeout_secs,
            ..
        } => {
            assert_eq!(*max_attempts, WAIT_HTTP_MAX_ATTEMPTS);
            assert_eq!(*interval_ms, WAIT_HTTP_INTERVAL_MS);
            assert_eq!(*timeout_secs, WAIT_HTTP_TIMEOUT_SECS);
        }
        other => panic!("relay readiness is not HTTP health: {:?}", other),
    }
}

#[test]
fn dev_helper_warning_is_only_for_dev_helper() {
    assert!(!Transport::ProductionDirect.dev_helper_warning());
    assert!(Transport::DevHelper.dev_helper_warning());
}

#[test]
fn plan_order_and_cwd_match_the_script() {
    let services = plan(&StackConfig::from_entries(&[]));
    let names: Vec<&str> = services.iter().map(|s| s.name).collect();
    assert_eq!(
        names,
        vec![
            "Meta Nuntius relay",
            "queue service",
            "resident agent",
            "Trio app server",
        ]
    );
    let cwds: Vec<&str> = services.iter().map(|s| s.cwd).collect();
    assert_eq!(cwds, vec![".", "server/queue", "server/queue", "."]);
}

#[test]
fn the_resident_agent_never_gets_an_http_gate() {
    let services = plan(&StackConfig::from_entries(&[]));
    assert_eq!(&services[2].readiness, &Readiness::ProcessAlive);
    assert!(matches!(
        &services[0].readiness,
        Readiness::HttpHealth { .. }
    ));
    assert!(matches!(
        &services[1].readiness,
        Readiness::HttpHealth { .. }
    ));
    assert!(matches!(
        &services[3].readiness,
        Readiness::HttpHealth { .. }
    ));
}
