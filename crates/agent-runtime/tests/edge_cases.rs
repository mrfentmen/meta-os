//! B099 — empty, maximum, duplicate and out-of-order inputs for
//! `agent-runtime`, one named test per case.
//!
//! Real store, real serve path; only the generator is scripted through
//! the crate's own `Generator` seam.
use agent_runtime::{validate_assessment, Agent, Generator, Outcome};
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
        _correction: Option<&str>,
    ) -> Result<(Value, String, u64), String> {
        assert!(self.calls < self.replies.len(), "generator called past the script");
        let i = self.calls;
        self.calls += 1;
        self.replies[i].clone()
    }
}

struct Capture {
    sizes: Vec<usize>,
}

impl Generator for Capture {
    fn generate(
        &mut self,
        _product: &str,
        image: &[u8],
        _timestamp: &str,
        _correction: Option<&str>,
    ) -> Result<(Value, String, u64), String> {
        self.sizes.push(image.len());
        Ok((canned(), "m".into(), 1))
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
fn empty_job_id_is_served_and_echoed() {
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    jobs.submit(&envelope("", b"\xff\xd8"));
    let mut a = agent(jobs, vec![Ok((canned(), "m".into(), 1))]);
    assert_eq!(a.serve_job(""), Outcome::Done);
    let r = a.jobs.get_result("").unwrap();
    assert_eq!(r["job_id"], "");
    assert_eq!(r["status"], "ok");
}

#[test]
fn empty_image_bytes_reach_the_generator_as_empty() {
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    jobs.submit(&envelope("j-empty", b""));
    let mut a = Agent {
        nick: "tester".into(),
        lease: 60,
        jobs,
        gen: Capture { sizes: vec![] },
    };
    assert_eq!(a.serve_job("j-empty"), Outcome::Done);
    assert_eq!(a.gen.sizes, vec![0], "the decoded image is zero bytes");
}

#[test]
fn duplicate_serve_skips_before_generating() {
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    jobs.submit(&envelope("j-dup", b"\xff\xd8"));
    let mut a = agent(jobs, vec![Ok((canned(), "m".into(), 1))]);
    assert_eq!(a.serve_job("j-dup"), Outcome::Done);
    assert_eq!(a.serve_job("j-dup"), Outcome::Skipped);
    assert_eq!(a.gen.calls, 1, "the second pass must not re-bill");
}

#[test]
fn out_of_order_serve_loses_the_claim_then_wins_after_release() {
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    jobs.submit(&envelope("j-order", b"\xff\xd8"));
    assert!(jobs.claim("j-order", "other-agent", 60));
    let mut a = agent(jobs, vec![Ok((canned(), "m".into(), 1))]);
    assert_eq!(a.serve_job("j-order"), Outcome::Lost);
    assert!(a.jobs.get_result("j-order").is_none());
    a.jobs.release_claim("j-order");
    assert_eq!(a.serve_job("j-order"), Outcome::Done);
    assert_eq!(a.gen.calls, 1);
}

#[test]
fn duplicate_submit_keeps_the_first_envelope() {
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    let env = envelope("j-submit", b"\xff\xd8");
    let (jid, created) = jobs.submit(&env);
    assert!(created);
    assert_eq!(jid, "j-submit");
    let (jid2, created2) = jobs.submit(&json!({"id": "j-submit", "product": "medicus"}));
    assert_eq!(jid2, "j-submit");
    assert!(!created2, "an already-submitted id is not re-created");
    let mut a = agent(jobs, vec![Ok((canned(), "m".into(), 1))]);
    assert_eq!(a.serve_job("j-submit"), Outcome::Done);
}

#[test]
fn long_ascii_error_is_capped_at_500_in_the_result() {
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    jobs.submit(&envelope("j-long", b"\xff\xd8"));
    let mut a = agent(jobs, vec![Err("e".repeat(600))]);
    assert_eq!(a.serve_job("j-long"), Outcome::Failed);
    let r = a.jobs.get_result("j-long").unwrap();
    assert_eq!(r["error"].as_str().unwrap().chars().count(), 500);
}

#[test]
fn long_ascii_error_is_capped_at_200_in_the_finish_note() {
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    jobs.submit(&envelope("j-note", b"\xff\xd8"));
    let mut a = agent(jobs, vec![Err("e".repeat(600))]);
    assert_eq!(a.serve_job("j-note"), Outcome::Failed);
    let fields = a.jobs.job_fields("j-note");
    assert_eq!(fields["status"], "failed");
    assert_eq!(fields["note"].chars().count(), 200);
}

#[test]
fn empty_observations_array_is_valid() {
    let mut v = canned();
    v["observations"] = json!([]);
    let (ok, errors) = validate_assessment(&v, "ignis");
    assert!(ok, "the code sets no minimum observation count: {errors:?}");
}

#[test]
fn five_hundred_observations_are_accepted() {
    let mut v = canned();
    let obs: Vec<Value> = (0..500)
        .map(|i| {
            json!({
                "category": "visible smoke",
                "description": format!("plume {i}"),
                "evidence": "frame centre",
                "confidence": 0.5
            })
        })
        .collect();
    v["observations"] = Value::Array(obs);
    let (ok, errors) = validate_assessment(&v, "ignis");
    assert!(ok, "no observation-count maximum exists: {errors:?}");
}

#[test]
fn confidence_boundaries_are_inclusive() {
    for (value, expected_ok) in [(json!(0.0), true), (json!(1.0), true), (json!(1.0001), false), (json!(-0.1), false)] {
        let mut v = canned();
        v["observations"][0]["confidence"] = value.clone();
        let (ok, errors) = validate_assessment(&v, "ignis");
        assert_eq!(ok, expected_ok, "confidence {value}: {errors:?}");
    }
}

#[test]
fn utf8_error_is_capped_without_panicking() {
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    jobs.submit(&envelope("j-utf8", b"\xff\xd8"));
    // 600 two-byte characters: a byte slice at 500 would panic.
    let mut a = agent(jobs, vec![Err("é".repeat(600))]);
    assert_eq!(a.serve_job("j-utf8"), Outcome::Failed);
    let r = a.jobs.get_result("j-utf8").unwrap();
    assert_eq!(r["error"].as_str().unwrap().chars().count(), 500);
    let fields = a.jobs.job_fields("j-utf8");
    assert_eq!(fields["note"].chars().count(), 200);
}
