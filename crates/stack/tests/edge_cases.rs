//! B195 — edge cases, one named test per required case:
//! empty input, maximum input, duplicate input, out-of-order input,
//! plus the boundary values the plan can carry.

use stack::{plan, StackConfig};

#[test]
fn empty_input_yields_the_documented_defaults() {
    let c = StackConfig::from_entries(&[]);
    assert_eq!(c.relay_port, "8787");
    assert_eq!(c.queue_port, "8935");
    assert_eq!(c.app_port, "8080");
    assert_eq!(c.job_ns, None);
}

#[test]
fn maximum_input_is_carried_without_truncation() {
    let long_port = "9".repeat(1024);
    let mut entries: Vec<(&str, &str)> = Vec::with_capacity(10_001);
    for _ in 0..10_000 {
        entries.push(("UNUSED_KEY", "x"));
    }
    entries.push(("RELAY_PORT", long_port.as_str()));

    let c = StackConfig::from_entries(&entries);
    assert_eq!(c.relay_port.len(), 1024);
    assert_eq!(c.relay_base(), format!("http://127.0.0.1:{}", long_port));
}

#[test]
fn duplicate_input_keeps_the_first_value() {
    let c = StackConfig::from_entries(&[
        ("TRIO_JOB_NS", "first"),
        ("TRIO_JOB_NS", "second"),
        ("PORT", "9002"),
        ("PORT", "9003"),
    ]);
    assert_eq!(c.job_ns.as_deref(), Some("first"));
    assert_eq!(c.app_port, "9002");
}

#[test]
fn out_of_order_input_is_resolved_by_key_not_position() {
    let c = StackConfig::from_entries(&[
        ("PORT", "9002"),
        ("TRIO_JOB_NS", "scratch-9"),
        ("QUEUE_PORT", "9001"),
        ("RELAY_PORT", "9000"),
        ("SPARK_API_KEY", "sk-edge"),
    ]);
    assert_eq!(c.relay_port, "9000");
    assert_eq!(c.queue_port, "9001");
    assert_eq!(c.app_port, "9002");
    assert_eq!(c.job_ns.as_deref(), Some("scratch-9"));
    assert_eq!(c.transport, stack::Transport::ProductionDirect);
}

#[test]
fn empty_job_namespace_is_inherited_verbatim() {
    let c = StackConfig::from_entries(&[("TRIO_JOB_NS", "")]);
    let services = plan(&c);
    assert_eq!(
        services[1].env,
        vec![("TRIO_JOB_NS".to_string(), String::new())]
    );
    assert_eq!(
        services[2].env,
        vec![
            (
                "TRIO_RELAY_URL".to_string(),
                "http://127.0.0.1:8787".to_string()
            ),
            ("TRIO_JOB_NS".to_string(), String::new()),
        ]
    );
}

#[test]
fn zero_port_is_kept_not_treated_as_unset() {
    // Only an empty string falls back; "0" is a value.
    let c = StackConfig::from_entries(&[("RELAY_PORT", "0")]);
    assert_eq!(c.relay_base(), "http://127.0.0.1:0");
}

#[test]
fn unicode_port_is_kept_verbatim() {
    let c = StackConfig::from_entries(&[("QUEUE_PORT", "٨٩٣٥")]);
    assert_eq!(c.queue_base(), "http://127.0.0.1:٨٩٣٥");
}

#[test]
fn every_service_has_a_unique_name_and_a_non_empty_argv() {
    let services = plan(&StackConfig::from_entries(&[]));
    let mut names: Vec<&str> = services.iter().map(|s| s.name).collect();
    assert_eq!(names.len(), 4);
    names.sort_unstable();
    names.dedup();
    assert_eq!(names.len(), 4, "service names are not unique");
    for service in &services {
        assert!(!service.argv.is_empty(), "{} has an empty argv", service.name);
        assert!(!service.cwd.is_empty(), "{} has an empty cwd", service.name);
    }
}
