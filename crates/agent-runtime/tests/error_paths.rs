//! B098 — every refusal and failure branch in `agent-runtime`.
//!
//! Each test drives the real `Agent::serve_job` over an in-memory store
//! and asserts the failed envelope the code writes. Nothing is mocked:
//! the store is the crate's own `InMemoryStore`, and the generator is
//! the crate's `Generator` seam with a scripted reply list.
use agent_runtime::{relay_notify_payload, validate_assessment, Agent, Generator, Outcome};
use base64::engine::general_purpose::STANDARD as B64;
use base64::Engine as _;
use queue_store::{InMemoryStore, JobStore};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

struct Scripted {
    replies: Vec<Result<(Value, String, u64), String>>,
    calls: usize,
}

impl Generator for Scripted {
    fn generate(
        &mut self,
        _product: &str,
        _image: &[u8],
        _timestamp: &str,
        correction: Option<&str>,
    ) -> Result<(Value, String, u64), String> {
        assert!(self.calls < self.replies.len(), "generator called past the script");
        let i = self.calls;
        self.calls += 1;
        if i == 0 {
            assert!(correction.is_none(), "first call must carry no correction");
        } else {
            assert!(correction.is_some(), "retry must carry the validation errors");
        }
        self.replies[i].clone()
    }
}

fn canned() -> Value {
    json!({
        "product": "ignis",
        "timestamp": "2026-10-30T06:00:00.000Z",
        "observations": [{
            "category": "visible smoke",
            "description": "grey plume",
            "evidence": "frame centre",
            "confidence": null
        }],
        "assessment": {
            "category": "visible smoke",
            "summary": "Smoke visible.",
            "uncertainty": [],
            "requires_human_review": true
        },
        "processing": { "model": "muse-spark-1.3", "latency_ms": null }
    })
}

fn envelope(jid: &str, raw: &[u8]) -> Value {
    json!({
        "id": jid,
        "kind": "trio-assessment",
        "version": 1,
        "product": "ignis",
        "timestamp": "2026-10-30T06:00:00.000Z",
        "image": {
            "dataUrl": format!("data:image/jpeg;base64,{}", B64.encode(raw)),
            "byteLength": raw.len(),
            "sha256": hex::encode(Sha256::digest(raw))
        }
    })
}

fn agent(
    jobs: JobStore<InMemoryStore>,
    replies: Vec<Result<(Value, String, u64), String>>,
) -> Agent<InMemoryStore, Scripted> {
    Agent {
        nick: "tester".into(),
        lease: 60,
        jobs,
        gen: Scripted { replies, calls: 0 },
    }
}

#[test]
fn missing_envelope_refuses() {
    let jobs = JobStore::new(InMemoryStore::default(), "t");
    let mut a = agent(jobs, vec![]);
    assert_eq!(a.serve_job("no-such-job"), Outcome::Failed);
    let r = a.jobs.get_result("no-such-job").unwrap();
    assert_eq!(r["status"], "failed");
    assert_eq!(r["assessment"], Value::Null);
    assert!(r["error"]
        .as_str()
        .unwrap()
        .contains("job envelope missing or unparseable"));
    assert_eq!(a.gen.calls, 0, "no generation on a missing envelope");
}

#[test]
fn non_jpeg_data_url_refuses() {
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    let mut env = envelope("j-png", b"\xff\xd8");
    env["image"]["dataUrl"] = json!("data:image/png;base64,AA==");
    jobs.submit(&env);
    let mut a = agent(jobs, vec![]);
    assert_eq!(a.serve_job("j-png"), Outcome::Failed);
    let r = a.jobs.get_result("j-png").unwrap();
    assert!(r["error"].as_str().unwrap().contains("not a JPEG data URL"));
    assert_eq!(a.gen.calls, 0);
}

#[test]
fn bad_base64_refuses() {
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    let mut env = envelope("j-b64", b"\xff\xd8");
    env["image"]["dataUrl"] = json!("data:image/jpeg;base64,!!!!");
    jobs.submit(&env);
    let mut a = agent(jobs, vec![]);
    assert_eq!(a.serve_job("j-b64"), Outcome::Failed);
    assert!(a.jobs.get_result("j-b64").unwrap()["error"]
        .as_str()
        .unwrap()
        .contains("does not base64-decode"));
    assert_eq!(a.gen.calls, 0);
}

#[test]
fn sha256_mismatch_refuses() {
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    let mut env = envelope("j-sha", b"\xff\xd8");
    env["image"]["sha256"] = json!("deadbeef");
    jobs.submit(&env);
    let mut a = agent(jobs, vec![]);
    assert_eq!(a.serve_job("j-sha"), Outcome::Failed);
    assert!(a.jobs.get_result("j-sha").unwrap()["error"]
        .as_str()
        .unwrap()
        .contains("sha256 mismatch"));
    assert_eq!(a.gen.calls, 0);
}

#[test]
fn first_generation_error_refuses() {
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    jobs.submit(&envelope("j-gen", b"\xff\xd8"));
    let mut a = agent(jobs, vec![Err("boom".into())]);
    assert_eq!(a.serve_job("j-gen"), Outcome::Failed);
    let r = a.jobs.get_result("j-gen").unwrap();
    assert!(r["error"].as_str().unwrap().contains("generation failed: boom"));
    assert_eq!(r["model"], Value::Null);
    assert_eq!(r["latency_ms"], Value::Null);
    assert_eq!(a.gen.calls, 1);
}

#[test]
fn retry_generation_error_refuses_with_first_model_and_latency() {
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    jobs.submit(&envelope("j-gen2", b"\xff\xd8"));
    let mut a = agent(
        jobs,
        vec![
            Ok((json!({"not": "valid"}), "m1".into(), 10)),
            Err("retry boom".into()),
        ],
    );
    assert_eq!(a.serve_job("j-gen2"), Outcome::Failed);
    let r = a.jobs.get_result("j-gen2").unwrap();
    assert!(r["error"].as_str().unwrap().contains("generation failed: retry boom"));
    assert_eq!(r["model"], "m1");
    assert_eq!(r["latency_ms"], 10);
    assert_eq!(a.gen.calls, 2);
}

#[test]
fn invalid_after_exactly_one_retry_refuses() {
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    jobs.submit(&envelope("j-bad", b"\xff\xd8"));
    let mut a = agent(
        jobs,
        vec![
            Ok((json!({"not": "valid"}), "m1".into(), 10)),
            Ok((json!({"still": "invalid"}), "m2".into(), 20)),
        ],
    );
    assert_eq!(a.serve_job("j-bad"), Outcome::Failed);
    let r = a.jobs.get_result("j-bad").unwrap();
    assert_eq!(r["status"], "failed");
    assert_eq!(r["assessment"], Value::Null);
    assert!(r["error"]
        .as_str()
        .unwrap()
        .contains("after one correction retry"));
    assert_eq!(r["model"], "m2");
    assert_eq!(r["latency_ms"], 30, "retry latency is summed");
    assert_eq!(a.gen.calls, 2, "never a third call");
}

#[test]
fn claim_race_lost_writes_nothing() {
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    jobs.submit(&envelope("j-race", b"\xff\xd8"));
    assert!(jobs.claim("j-race", "other-agent", 60));
    let mut a = agent(jobs, vec![]);
    assert_eq!(a.serve_job("j-race"), Outcome::Lost);
    assert!(a.jobs.get_result("j-race").is_none());
    assert_eq!(a.gen.calls, 0);
}

#[test]
fn validator_names_an_empty_expected_product() {
    let (ok, errors) = validate_assessment(&canned(), "");
    assert!(!ok);
    assert!(errors.iter().any(|e| e.contains("expected product")));
}

#[test]
fn validator_refuses_a_non_object() {
    let (ok, errors) = validate_assessment(&json!(["not", "an", "object"]), "ignis");
    assert!(!ok);
    assert_eq!(errors, vec!["response is not a JSON object".to_string()]);
}

#[test]
fn relay_failed_payload_is_a_warning_and_names_the_error() {
    let payload = relay_notify_payload(
        &json!({"job_id": "j1", "status": "failed", "error": "frame mismatch"}),
        Some("ignis"),
    )
    .unwrap();
    assert_eq!(payload["severity"], "warning");
    assert_eq!(payload["topic"], "trio-result");
    let text = payload["text"].as_str().unwrap();
    assert!(text.contains("j1"));
    assert!(text.contains("ignis"));
    assert!(text.contains("frame mismatch"));
}

#[test]
fn relay_ok_payload_does_not_panic_and_is_capped() {
    let category = "c".repeat(600);
    let payload = relay_notify_payload(
        &json!({
            "job_id": "j2",
            "status": "ok",
            "assessment": {"assessment": {"category": category}}
        }),
        Some("ignis"),
    )
    .unwrap();
    assert_eq!(payload["severity"], "info");
    assert!(payload["text"].as_str().unwrap().chars().count() <= 500);
}
