//! B194 — error paths.
//!
//! `crates/stack` has no refusal branch: no `Result`, no panic, no
//! validation. That is the documented behaviour (`src/lib.rs:13-17`,
//! `110-121`), so the "error paths" here are the values a validating
//! crate would reject. Each test proves the crate carries the value
//! through instead of inventing a refusal it does not have.

use stack::{plan, summary_lines, StackConfig, Transport};

#[test]
fn empty_port_value_is_not_an_error_it_falls_back() {
    let c = StackConfig::from_entries(&[("RELAY_PORT", ""), ("QUEUE_PORT", ""), ("PORT", "")]);
    assert_eq!(c.relay_port, "8787");
    assert_eq!(c.queue_port, "8935");
    assert_eq!(c.app_port, "8080");
}

#[test]
fn whitespace_port_is_kept_verbatim() {
    let c = StackConfig::from_entries(&[("RELAY_PORT", "   ")]);
    assert_eq!(c.relay_base(), "http://127.0.0.1:   ");
}

#[test]
fn negative_port_is_kept_verbatim() {
    let c = StackConfig::from_entries(&[("QUEUE_PORT", "-1")]);
    assert_eq!(c.queue_base(), "http://127.0.0.1:-1");
}

#[test]
fn unknown_keys_are_ignored_not_refused() {
    let c = StackConfig::from_entries(&[("RELAY_PORT_", "9000"), ("QUEUE_PORT ", "9001")]);
    assert_eq!(c.relay_port, "8787");
    assert_eq!(c.queue_port, "8935");
}

#[test]
fn keys_are_case_sensitive_and_a_wrong_case_is_unset() {
    let c = StackConfig::from_entries(&[("relay_port", "9000"), ("Port", "9002")]);
    assert_eq!(c.relay_port, "8787");
    assert_eq!(c.app_port, "8080");
}

#[test]
fn duplicate_keys_take_the_first_match() {
    let c = StackConfig::from_entries(&[("RELAY_PORT", "9000"), ("RELAY_PORT", "9001")]);
    assert_eq!(c.relay_port, "9000");
}

#[test]
fn missing_spark_key_selects_dev_helper_not_an_error() {
    let c = StackConfig::from_entries(&[]);
    assert_eq!(c.transport, Transport::DevHelper);
    assert!(c.transport.dev_helper_warning());
}

#[test]
fn empty_spark_key_selects_dev_helper_not_an_error() {
    let c = StackConfig::from_entries(&[("SPARK_API_KEY", "")]);
    assert_eq!(c.transport, Transport::DevHelper);
}

#[test]
fn any_non_empty_spark_key_is_production_without_validation() {
    // No shape check: a single space still selects production.
    let c = StackConfig::from_entries(&[("SPARK_API_KEY", " ")]);
    assert_eq!(c.transport, Transport::ProductionDirect);
    assert!(!c.transport.dev_helper_warning());
}

#[test]
fn plan_survives_an_unusable_port() {
    let c = StackConfig::from_entries(&[("RELAY_PORT", "abc"), ("QUEUE_PORT", "nope"), ("PORT", "-2")]);
    let services = plan(&c);
    assert_eq!(services.len(), 4);
    assert!(format!("{:?}", services[0].readiness).contains(":abc/health"));
    assert!(format!("{:?}", services[3].readiness).contains(":-2/api/health"));
}

#[test]
fn summary_survives_an_unusable_port() {
    let c = StackConfig::from_entries(&[("RELAY_PORT", "abc")]);
    let lines = summary_lines(&c);
    assert_eq!(lines.len(), 4);
    assert!(lines[0].contains("http://127.0.0.1:abc/"));
    assert!(lines[2].contains("http://127.0.0.1:abc/rooms/main"));
}
