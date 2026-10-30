//! B11 parity — one test per assigned Python test root.
//! Spark-down cases assert the honest unconfigured path (never fake green).

use intel::b11_spark::{mind_image, mind_loader, skills_loader, spark_agent, spark_client};
use intel::b11_spark::spark_client::{Completion, CompletionRequest, SparkError, StubTransport, Transport, TransportKind};
use std::collections::HashMap;

fn req() -> CompletionRequest {
    CompletionRequest { lane_feature: "l".into(), system: "s".into(), prompt: "p".into(), max_tokens: 8, job_ns: "n".into() }
}

#[test] fn test_intel_spark_agent_unconfigured_errors() {
    assert!(spark_agent::unconfigured_generate().is_err());
}
#[test] fn test_intel_spark_agent_spec_contract() {
    let s = spark_agent::parse_spark_spec("spark-complete", 1, "l", "s", "p", 8, "n").unwrap();
    assert_eq!(spark_agent::result_key_for("n", "j"), "n:j:result");
    assert!(s.result_key_pattern.contains("{jid}"));
}
#[test] fn test_intel_spark_agent_stub_transport_ports_as_is() {
    let stub = StubTransport { reply: Some(Ok(Completion { text: "hi".into(), tokens_in: None, tokens_out: None, usage: "unreported".into() })) };
    let c = spark_client::complete(&stub, &TransportKind::Agent, &req(), 0.0, 75.0).unwrap();
    assert_eq!((c.text.as_str(), c.usage.as_str()), ("hi", "unreported"));
}
#[test] fn test_intel_spark_client_two_transports() {
    assert_eq!(TransportKind::from_env("agent").unwrap(), TransportKind::Agent);
    assert_eq!(TransportKind::from_env("http").unwrap(), TransportKind::Http);
}
#[test] fn test_intel_spark_client_budget_gates_http() {
    let stub = StubTransport::default();
    assert!(matches!(
        spark_client::complete(&stub, &TransportKind::Http, &req(), 75.0, 75.0),
        Err(SparkError::Budget(_))
    ));
}
#[test] fn test_intel_spark_client_result_envelope() {
    let (t, ti, to) = spark_client::result_body_for(r#"{"text":"x","tokens_in":1,"tokens_out":2}"#);
    assert_eq!((t, ti, to), ("x".to_string(), Some(1), Some(2)));
}
#[test] fn test_intel_spark_down_unconfigured_before_send() {
    let stub = StubTransport::default();
    assert!(matches!(
        stub.complete(&req()),
        Err(SparkError::NotConfigured(_))
    ));
}
#[test] fn test_intel_mind_image_bundle_shape() {
    let mut m = HashMap::new();
    m.insert("name".into(), "pax-default".into());
    let b = mind_image::parse_bundle(m, "brief", "constitution", vec![("milo".into(), vec!["dispatch".into()])], &[]).unwrap();
    assert!(mind_image::validate_bundle(&b).is_ok());
    assert!(mind_image::bundle_summary(&b).contains("pax-default"));
}
#[test] fn test_intel_mind_loader_launch_roundtrip() {
    let files = vec![("SKILL.md".into(), b"skill".to_vec())];
    let l = mind_loader::assemble_launch("worker", "root", files.clone(), "milo").unwrap();
    assert!(mind_loader::verify_launch(&l, &files).is_ok());
}
#[test] fn test_intel_skills_loader_names() {
    assert!(skills_loader::resolve_skill("root", "fixture-brief").is_ok());
    assert!(skills_loader::resolve_skill("root", "not a skill").is_err());
}
