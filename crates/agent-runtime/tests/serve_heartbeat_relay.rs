//! B04 carry-through: `serve_once`, the lease heartbeat, the relay
//! NOTIFY hook, and real ISO-8601 timestamps — the Python behaviors
//! (`server/queue/trio_agent.py`) the crate previously only recorded
//! as gaps G1–G4.
//!
//! Names mirror `tests/queue-python/test_queue.py` where the case
//! exists there (`..._parity` suffix); the heartbeat/interval cases
//! mirror the Python expressions directly.
use agent_runtime::{
    format_iso_millis, heartbeat_interval_secs, heartbeat_loop_every, now_iso,
    relay_notify, relay_notify_to, relay_post, Agent, Generator,
    ServeReport,
};
use base64::engine::general_purpose::STANDARD as B64;
use base64::Engine as _;
use queue_store::{InMemoryStore, JobStore, StoreBackend};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::io::{BufRead, BufReader, Read, Write};
use std::net::TcpListener;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Mutex,
};
use std::time::Duration;

struct Scripted {
    replies: Vec<Result<(Value, String, u64), String>>,
    calls: Vec<Option<String>>,
}

impl Generator for Scripted {
    fn generate(
        &mut self,
        _p: &str,
        _img: &[u8],
        _ts: &str,
        correction: Option<&str>,
    ) -> Result<(Value, String, u64), String> {
        self.calls.push(correction.map(|s| s.to_string()));
        let i = self.calls.len() - 1;
        self.replies[i].clone()
    }
}

fn canned() -> Value {
    json!({
        "product": "ignis",
        "timestamp": "2026-10-30T06:00:00.000Z",
        "observations": [{
            "category": "steam or fog",
            "description": "dense white vapor",
            "evidence": "center of frame",
            "confidence": null
        }],
        "assessment": {
            "category": "steam or fog",
            "summary": "white vapor visible",
            "uncertainty": ["cannot distinguish steam from fog"],
            "requires_human_review": true
        },
        "processing": { "model": "muse-spark-1.3", "latency_ms": null }
    })
}

fn envelope(jid: &str, raw: &[u8]) -> Value {
    json!({
        "id": jid, "kind": "trio-assessment", "version": 1,
        "product": "ignis", "timestamp": "2026-10-30T06:00:00.000Z",
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
    Agent { nick: "test-agent".into(), lease: 60, jobs, gen: Scripted { replies, calls: vec![] } }
}

// -- serve_once (Python `serve_once` report dict) ------------------------

#[test]
fn serve_once_done_failed_skipped_lost_parity() {
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    jobs.submit(&envelope("j-ok", b"\xff\xd8"));
    jobs.submit(&envelope("j-bad", b"\xff\xd8"));
    // A job whose result already exists is skipped, never re-billed.
    jobs.submit(&envelope("j-skip", b"\xff\xd8"));
    jobs.put_result(&json!({
        "job_id": "j-skip", "status": "ok", "assessment": canned(),
        "error": null, "model": "m", "latency_ms": 1,
        "completed_at": now_iso(),
    }));
    // A job claimed by someone else is not polled at all (the index
    // only lists opens): the race-lost path is pinned separately in
    // `error_paths::claim_race_lost_writes_nothing`.
    jobs.submit(&envelope("j-race", b"\xff\xd8"));
    assert!(jobs.claim("j-race", "other-agent", 60));

    // Poll order follows the store index (key order here): j-bad is
    // served first and fails validation twice, j-ok then succeeds,
    // j-skip is skipped, j-race is never visited.
    let mut a = agent(
        jobs,
        vec![
            Ok((json!({"not": "a contract"}), "m".into(), 1)),
            Ok((json!({"still": "bad"}), "m".into(), 1)),
            Ok((canned(), "muse-spark-1.3".into(), 7)),
        ],
    );
    let report: ServeReport = a.serve_once();
    assert_eq!(report.done, vec!["j-ok".to_string()]);
    assert_eq!(report.failed, vec!["j-bad".to_string()]);
    assert_eq!(report.skipped, vec!["j-skip".to_string()]);
    assert!(report.lost.is_empty());
    assert_eq!(a.gen.calls.len(), 3);
}

#[test]
fn serve_once_rerun_skips_without_rebilling_parity() {
    // Mirrors `test_submit_serve_result_and_idempotent_skip`: reopen
    // the job by hand; the agent must skip, never re-bill.
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    jobs.submit(&envelope("j-re", b"\xff\xd8"));
    let mut a = agent(jobs, vec![Ok((canned(), "muse-spark-1.3".into(), 123))]);
    let r1 = a.serve_once();
    assert_eq!(r1.done, vec!["j-re".to_string()]);
    let r = a.jobs.get_result("j-re").unwrap();
    assert_eq!(r["status"], "ok");
    assert_eq!(r["latency_ms"], 123);
    assert!(r["error"].is_null());
    // Hand-reopen: status back to open, result still present.
    a.jobs
        .backend
        .hset("t:j-re", &std::collections::HashMap::from([("status".to_string(), "open".to_string())]));
    let r2 = a.serve_once();
    assert_eq!(r2.skipped, vec!["j-re".to_string()]);
    assert_eq!(a.gen.calls.len(), 1, "still exactly one generation");
}

#[test]
fn completed_at_is_iso8601_in_both_envelopes() {
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    jobs.submit(&envelope("j-ts-ok", b"\xff\xd8"));
    jobs.submit(&envelope("j-ts-bad", b"\xff\xd8"));
    // Poll order is key order: j-ts-bad is served first (invalid
    // twice), then j-ts-ok (valid once).
    let mut a = agent(
        jobs,
        vec![
            Ok((json!({"not": "a contract"}), "m".into(), 1)),
            Ok((json!({"still": "bad"}), "m".into(), 1)),
            Ok((canned(), "m".into(), 1)),
        ],
    );
    let report = a.serve_once();
    assert_eq!(report.done, vec!["j-ts-ok".to_string()]);
    assert_eq!(report.failed, vec!["j-ts-bad".to_string()]);
    for jid in ["j-ts-ok", "j-ts-bad"] {
        let ts = a.jobs.get_result(jid).unwrap()["completed_at"]
            .as_str()
            .unwrap()
            .to_string();
        assert_eq!(ts.len(), 24, "{jid}: {ts}");
        assert!(ts.ends_with('Z') && ts.contains('T'), "{jid}: {ts}");
    }
}

// -- heartbeat interval rule ---------------------------------------------

#[test]
fn heartbeat_interval_matches_the_python_rule() {
    // max(5.0, min(60.0, lease / 3)): lease 300 -> 60, 60 -> 20,
    // small leases floor at 5.
    assert_eq!(heartbeat_interval_secs(300), 60.0);
    assert_eq!(heartbeat_interval_secs(60), 20.0);
    assert_eq!(heartbeat_interval_secs(15), 5.0);
    assert_eq!(heartbeat_interval_secs(9), 5.0);
    assert_eq!(heartbeat_interval_secs(0), 5.0);
    assert_eq!(heartbeat_interval_secs(9_999_999), 60.0);
}

#[test]
fn heartbeat_loop_renews_then_stops() {
    // Lease 1s with a 50ms renewal tick: without renewal the claim
    // would lapse ~1s after claiming; with the loop it must still be
    // ours after 1.6s. Then stop: the scoped thread joins at once.
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    jobs.submit(&envelope("j-hb", b"\xff\xd8"));
    assert!(jobs.claim("j-hb", "me", 1));
    let cell = Mutex::new(&mut jobs);
    let stop = AtomicBool::new(false);
    std::thread::scope(|s| {
        s.spawn(|| {
            heartbeat_loop_every(&cell, &stop, "j-hb", "me", 1, 0.05);
        });
        std::thread::sleep(Duration::from_millis(1600));
        // Renewed throughout: a rival still cannot take the claim.
        assert!(!cell.lock().unwrap().claim("j-hb", "rival", 60));
        stop.store(true, Ordering::SeqCst);
    });
    assert!(!cell.lock().unwrap().claim("j-hb", "rival", 60));
}

#[test]
fn heartbeat_loop_exits_when_the_lease_is_gone() {
    let mut jobs = JobStore::new(InMemoryStore::default(), "t");
    jobs.submit(&envelope("j-gone", b"\xff\xd8"));
    assert!(jobs.claim("j-gone", "me", 60));
    jobs.release_claim("j-gone");
    let cell = Mutex::new(&mut jobs);
    let stop = AtomicBool::new(false);
    // No claim to renew: the first interval tick exits the loop.
    heartbeat_loop_every(&cell, &stop, "j-gone", "me", 60, 0.05);
}

// -- ISO-8601 timestamps --------------------------------------------------

#[test]
fn format_iso_millis_vectors() {
    for (ms, want) in [
        (0u128, "1970-01-01T00:00:00.000Z"),
        (1, "1970-01-01T00:00:00.001Z"),
        (999, "1970-01-01T00:00:00.999Z"),
        (1000, "1970-01-01T00:00:01.000Z"),
        (1_761_717_600_000, "2025-10-29T06:00:00.000Z"),
        (1_709_251_200_000, "2024-03-01T00:00:00.000Z"),
        (1_709_164_800_000, "2024-02-29T00:00:00.000Z"),
        (1_735_689_600_123, "2025-01-01T00:00:00.123Z"),
    ] {
        assert_eq!(format_iso_millis(ms), want, "ms={ms}");
    }
}

// -- relay hook -----------------------------------------------------------

/// Start a loopback HTTP recorder: returns the base URL and a handle
/// collecting (path, body) pairs. Accepts until the listener closes.
fn start_recorder() -> (String, std::sync::mpsc::Receiver<(String, Value)>) {
    let listener = TcpListener::bind("127.0.0.1:0").expect("loopback bind");
    let base = format!("http://127.0.0.1:{}", listener.local_addr().unwrap().port());
    let (tx, rx) = std::sync::mpsc::channel();
    std::thread::spawn(move || {
        listener.set_nonblocking(false).ok();
        for stream in listener.incoming().take(16) {
            let Ok(mut stream) = stream else { break };
            stream.set_read_timeout(Some(Duration::from_secs(2))).ok();
            let mut reader = BufReader::new(stream.try_clone().unwrap());
            let mut request_line = String::new();
            if reader.read_line(&mut request_line).is_err() {
                break;
            }
            let path = request_line.split_whitespace().nth(1).unwrap_or("").to_string();
            let mut len = 0usize;
            loop {
                let mut line = String::new();
                if reader.read_line(&mut line).is_err() || line.trim().is_empty() {
                    break;
                }
                if let Some(v) = line.strip_prefix("Content-Length:") {
                    len = v.trim().parse().unwrap_or(0);
                }
            }
            let mut body = vec![0u8; len];
            if reader.read_exact(&mut body).is_err() {
                break;
            }
            let value: Value = serde_json::from_slice(&body).unwrap_or(Value::Null);
            if tx.send((path, value)).is_err() {
                break;
            }
            let _ = stream.write_all(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}");
        }
    });
    (base, rx)
}

#[test]
fn relay_post_delivers_notify_shape_parity() {
    let (base, rx) = start_recorder();
    let payload = json!({"severity": "info", "topic": "trio-result", "text": "hello"});
    relay_post(&base, &payload).expect("loopback post works");
    let (path, body) = rx.recv_timeout(Duration::from_secs(5)).expect("recorded");
    assert_eq!(path, "/rooms/main/notify");
    assert_eq!(body, payload);
}

#[test]
fn relay_post_refuses_non_http_and_dead_hosts() {
    assert!(relay_post("https://127.0.0.1:1", &json!({})).is_err());
    assert!(relay_post("http://127.0.0.1:1", &json!({})).is_err());
    assert!(relay_post("", &json!({})).is_err());
}

#[test]
fn ok_result_posts_info_notify_parity() {
    // Mirrors `test_ok_result_posts_info_notify`: severity info naming
    // the job id, product, and category.
    let (base, rx) = start_recorder();
    relay_notify_to(
        &base,
        &json!({
            "job_id": "j1", "status": "ok",
            "assessment": {"assessment": {"category": "steam or fog"}},
            "error": null, "model": "muse-spark-1.3", "latency_ms": 7,
        }),
        Some("ignis"),
    );
    let (path, body) = rx.recv_timeout(Duration::from_secs(5)).expect("recorded");
    assert_eq!(path, "/rooms/main/notify");
    assert_eq!(body["topic"], "trio-result");
    assert_eq!(body["severity"], "info");
    let text = body["text"].as_str().unwrap();
    assert!(text.contains("j1"), "{text}");
    assert!(text.contains("ignis"), "{text}");
    assert!(text.contains("steam or fog"), "{text}");
}

#[test]
fn failed_result_posts_warning_notify_parity() {
    // Mirrors `test_failed_result_posts_warning_notify`.
    let (base, rx) = start_recorder();
    relay_notify_to(
        &base,
        &json!({"job_id": "j9", "status": "failed", "error": "frame mismatch"}),
        Some("ignis"),
    );
    let (path, body) = rx.recv_timeout(Duration::from_secs(5)).expect("recorded");
    assert_eq!(path, "/rooms/main/notify");
    assert_eq!(body["severity"], "warning");
    let text = body["text"].as_str().unwrap();
    assert!(text.contains("j9"), "{text}");
    assert!(text.contains("failed:"), "{text}");
}

#[test]
fn dead_relay_never_fails_the_job_parity() {
    // Mirrors `test_dead_relay_never_fails_the_job`: connection
    // refused is swallowed, the call is a no-op.
    relay_notify_to(
        "http://127.0.0.1:1",
        &json!({"job_id": "j1", "status": "ok"}),
        Some("ignis"),
    );
    relay_notify(
        &json!({"job_id": "j1", "status": "ok"}),
        Some("ignis"),
    );
}
