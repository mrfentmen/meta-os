//! Crate `agent-runtime` — Meta OS Rust rebuild (B04).
//!
//! Batch B04 — Agent runtime (trio agent). Owner: Rowan.
//! Source: `server/queue/trio_agent.py`. Port behavior, do not redesign.
//!
//! Rules ported: poll index for open jobs; idempotency first (result
//! present => finish done, skip generation — never re-bill); atomic
//! claim (SET NX + lease, heartbeat while generating); frame SHA-256
//! verified against envelope; exactly ONE bounded self-correction retry
//! carrying validation errors; result envelope written once to
//! `trio:{jid}:result`; optional relay NOTIFY hook (fire-and-forget).
//!
//! Port status (B04 work, 2026-11-03): the result and validation core is
//! carried, and so are the lease heartbeat (a scoped renewal thread using
//! [`heartbeat_interval_secs`], stopped on every exit path), the
//! `serve_once` poll loop ([`ServeReport`]), the relay POST
//! ([`relay_notify`], env-gated with swallowed errors, 2s timeout), and
//! real ISO-8601 timestamps ([`now_iso`]).
//! See `os-build/records/agent-runtime-gaps.md` for the original gap list.

pub mod registry;

use base64::{engine::general_purpose::STANDARD as B64, Engine as _};
use queue_store::{JobStore, StoreBackend};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::io::{Read, Write};
use std::net::{TcpStream, ToSocketAddrs};
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Mutex,
};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

/// Relay POST timeout, matching the Python transport's `timeout=2`.
const RELAY_TIMEOUT: Duration = Duration::from_secs(2);

/// Heartbeat slice: the renewal thread wakes this often to check the
/// stop flag, so `join` after `stop` never blocks longer than this.
const HEARTBEAT_POLL: Duration = Duration::from_millis(50);

/// Lease-renewal interval in seconds, exactly the Python rule
/// (`trio_agent.py`: `max(5.0, min(60.0, self.lease / 3))`): a third
/// of the lease, clamped to [5, 60].
pub fn heartbeat_interval_secs(lease: u64) -> f64 {
    (lease as f64 / 3.0).clamp(5.0, 60.0)
}

/// Current UTC time as ISO-8601 with milliseconds and `Z`, the shape
/// the Python original emits (`datetime.now(timezone.utc).isoformat(
/// timespec="milliseconds")` with `+00:00` replaced by `Z`):
/// `YYYY-MM-DDTHH:MM:SS.mmmZ`, always 24 characters. Std only: the
/// calendar math is the days-to-civil inversion, no date dependency.
pub fn now_iso() -> String {
    let ms = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis())
        .unwrap_or(0);
    format_iso_millis(ms)
}

/// Format Unix epoch milliseconds as `YYYY-MM-DDTHH:MM:SS.mmmZ`.
/// Pre-epoch input saturates to the epoch. Pure and unit-tested.
pub fn format_iso_millis(ms_total: u128) -> String {
    let secs = (ms_total / 1000) as i64;
    let millis = (ms_total % 1000) as u32;
    let days = secs.div_euclid(86_400);
    let secs_of_day = secs.rem_euclid(86_400);
    let (year, month, day) = civil_from_days(days);
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}.{:03}Z",
        year,
        month,
        day,
        secs_of_day / 3600,
        (secs_of_day % 3600) / 60,
        secs_of_day % 60,
        millis
    )
}

/// Days since 1970-01-01 to (year, month, day): Howard Hinnant's
/// civil_from_days inversion, valid for the whole Unix range.
fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = (if mp < 10 { mp + 3 } else { mp - 9 }) as u32;
    (if m <= 2 { y + 1 } else { y }, m, d)
}

pub fn relay_notify_payload(result: &Value, product: Option<&str>) -> Option<Value> {
    let jid = result.get("job_id").and_then(Value::as_str)?;
    if result.get("status").and_then(Value::as_str) == Some("ok") {
        let category = result
            .get("assessment").and_then(|a| a.get("assessment"))
            .and_then(|a| a.get("category")).and_then(Value::as_str).unwrap_or("?");
        let text = format!("trio job {jid} product {} completed: category {category}", product.unwrap_or("unknown"));
        Some(serde_json::json!({
            "severity": "info", "topic": "trio-result",
            "text": text.chars().take(500).collect::<String>(),
        }))
    } else {
        let err = result.get("error").and_then(Value::as_str).unwrap_or("?");
        let text = format!("trio job {jid} product {} failed: {err}", product.unwrap_or("unknown"));
        Some(serde_json::json!({
            "severity": "warning", "topic": "trio-result",
            "text": text.chars().take(500).collect::<String>(),
        }))
    }
}

/// POST a relay payload to `{base}/rooms/main/notify` over plain HTTP
/// with a 2s connect/read/write timeout, mirroring the Python hook's
/// `urllib.request.urlopen(req, timeout=2)`. Only `http://` bases are
/// supported (the relay URL is local configuration); anything else, a
/// DNS/connect failure, or a short write is an `Err` the caller
/// swallows — a relay problem must never fail or delay a job.
pub fn relay_post(base: &str, payload: &Value) -> Result<(), String> {
    let rest = base
        .strip_prefix("http://")
        .ok_or_else(|| "relay base is not plain http://".to_string())?;
    let (host_port, prefix) = match rest.find('/') {
        Some(i) => (&rest[..i], rest[i..].trim_end_matches('/').to_string()),
        None => (rest, String::new()),
    };
    if host_port.is_empty() {
        return Err("relay base has no host".to_string());
    }
    let host = host_port.split(':').next().unwrap_or(host_port);
    let mut addrs = format!("{host_port}")
        .to_socket_addrs()
        .map_err(|e| format!("relay resolve failed: {e}"))?;
    let addr = addrs.next().ok_or_else(|| "relay host resolves to nothing".to_string())?;
    let mut stream = TcpStream::connect_timeout(&addr, RELAY_TIMEOUT)
        .map_err(|e| format!("relay connect failed: {e}"))?;
    stream.set_read_timeout(Some(RELAY_TIMEOUT)).ok();
    stream.set_write_timeout(Some(RELAY_TIMEOUT)).ok();
    let body = serde_json::to_string(payload).map_err(|e| e.to_string())?;
    let req = format!(
        "POST {prefix}/rooms/main/notify HTTP/1.1\r\nHost: {host}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
        body.len()
    );
    stream
        .write_all(req.as_bytes())
        .map_err(|e| format!("relay write failed: {e}"))?;
    let mut buf = [0u8; 512];
    let _ = stream.read(&mut buf);
    Ok(())
}

/// Best-effort NOTIFY after a job result is written, exactly the Python
/// `_relay_notify` hook: env `TRIO_RELAY_URL` unset or empty means no
/// hook (the agent behaves as before); every failure is swallowed.
/// Reads the environment on every call, like the original.
pub fn relay_notify(result: &Value, product: Option<&str>) {
    let base = std::env::var("TRIO_RELAY_URL").unwrap_or_default();
    let base = base.trim().trim_end_matches('/').to_string();
    if base.is_empty() {
        return;
    }
    relay_notify_to(&base, result, product);
}

/// The env-independent half of [`relay_notify`]: build the payload and
/// POST it, swallowing every failure. Testable without touching the
/// process environment.
pub fn relay_notify_to(base: &str, result: &Value, product: Option<&str>) {
    let Some(payload) = relay_notify_payload(result, product) else {
        return;
    };
    let _ = relay_post(base, &payload);
}

/// Outcome of serving one job.
#[derive(Debug, PartialEq, Eq)]
pub enum Outcome { Done, Failed, Skipped, Lost }

/// One poll/serve cycle report, mirroring the Python `serve_once`
/// report dict's keys: done, failed, skipped, lost.
#[derive(Debug, Default, PartialEq, Eq)]
pub struct ServeReport {
    /// Job ids finished with an assessment.
    pub done: Vec<String>,
    /// Job ids finished as failed.
    pub failed: Vec<String>,
    /// Job ids skipped: result already present, never re-billed.
    pub skipped: Vec<String>,
    /// Job ids lost: claim race lost (or vanished mid-serve).
    pub lost: Vec<String>,
}

pub trait Generator {
    fn generate(&mut self, product: &str, image: &[u8], timestamp: &str, correction: Option<&str>) -> Result<(Value, String, u64), String>;
}

pub struct Agent<B: StoreBackend, G: Generator> {
    pub nick: String,
    pub lease: u64,
    pub jobs: JobStore<B>,
    pub gen: G,
}

impl<B: StoreBackend + Send, G: Generator> Agent<B, G> {
    /// Poll the namespace index for open jobs and serve each one,
    /// returning the report (`done`, `failed`, `skipped`, `lost`) the
    /// Python `serve_once` returns. The infinite `--poll-interval` loop
    /// stays with the binary; this is the single pass.
    pub fn serve_once(&mut self) -> ServeReport {
        let mut report = ServeReport::default();
        for jid in self.jobs.open_job_ids() {
            match self.serve_job(&jid) {
                Outcome::Done => report.done.push(jid),
                Outcome::Failed => report.failed.push(jid),
                Outcome::Skipped => report.skipped.push(jid),
                Outcome::Lost => report.lost.push(jid),
            }
        }
        report
    }

    pub fn serve_job(&mut self, jid: &str) -> Outcome {
        // Idempotency before any claim or call: an existing result
        // means this deterministic job was already answered.
        if self.jobs.get_result(jid).is_some() {
            self.jobs.finish(jid, "done", "idempotent skip: result already present, not re-billed");
            return Outcome::Skipped;
        }
        if !self.jobs.claim(jid, &self.nick.clone(), self.lease) {
            return Outcome::Lost;
        }
        // Lease heartbeat while generating: a scoped thread renews the
        // claim every `heartbeat_interval_secs(lease)` seconds and stops
        // on the flag set on every exit path below (Python: a daemon
        // `threading.Thread` joined with timeout=2). The store is
        // shared through a mutex of the mutable borrow so renewal runs
        // concurrently with generation without redesigning the
        // `&mut self` serve API; renewal stops silently when the claim
        // is gone, exactly like the Python thread's early return.
        let stop = AtomicBool::new(false);
        let nick = self.nick.clone();
        let lease = self.lease;
        let jid_owned = jid.to_string();
        let cell = Mutex::new(&mut self.jobs);
        std::thread::scope(|s| {
            s.spawn(|| {
                heartbeat_loop(&cell, &stop, &jid_owned, &nick, lease);
            });
            let mut product: Option<String> = None;
            let outcome =
                Self::serve_claimed_body(&cell, &mut self.gen, &self.nick, &jid_owned, &mut product);
            stop.store(true, Ordering::SeqCst);
            outcome
        })
    }

    fn serve_claimed_body(
        jobs: &Mutex<&mut JobStore<B>>,
        gen: &mut G,
        nick: &str,
        jid: &str,
        product_out: &mut Option<String>,
    ) -> Outcome {
        // Idempotency again after the claim (the queue is the source of
        // truth: re-check under lease before any generation call).
        // The guard drops before the branch: `finish` below locks again.
        let already = jobs.lock().unwrap().get_result(jid);
        if already.is_some() {
            jobs.lock().unwrap().finish(jid, "done", "idempotent skip: result already present, not re-billed");
            return Outcome::Skipped;
        }
        // Drop the guard before branching: `finish_failed` locks the
        // same mutex, and a guard held across the `match` would
        // deadlock the missing-envelope arm on this thread.
        let env = jobs.lock().unwrap().job_envelope(jid);
        let env = match env {
            Some(e) => e,
            None => {
                Self::finish_failed(jobs, jid, "job envelope missing or unparseable in the store", None, None, None);
                return Outcome::Failed;
            }
        };
        let product = env.get("product").and_then(Value::as_str).unwrap_or("").to_string();
        let timestamp = env.get("timestamp").and_then(Value::as_str).unwrap_or("").to_string();
        *product_out = Some(product.clone());
        let data_url = env.get("image").and_then(|i| i.get("dataUrl")).and_then(Value::as_str).unwrap_or("");
        if !data_url.starts_with("data:image/jpeg;base64,") {
            Self::finish_failed(jobs, jid, "envelope image is not a JPEG data URL", None, None, Some(&product));
            return Outcome::Failed;
        }
        let raw = match B64.decode(data_url.splitn(2, ',').nth(1).unwrap_or("")) {
            Ok(b) => b,
            Err(_) => {
                Self::finish_failed(jobs, jid, "envelope image does not base64-decode", None, None, Some(&product));
                return Outcome::Failed;
            }
        };
        let digest = hex::encode(Sha256::digest(&raw));
        if env.get("image").and_then(|i| i.get("sha256")).and_then(Value::as_str) != Some(digest.as_str()) {
            Self::finish_failed(jobs, jid, "frame sha256 mismatch against the envelope", None, None, Some(&product));
            return Outcome::Failed;
        }
        let (mut assessment, mut model, mut latency) = match gen.generate(&product, &raw, &timestamp, None) {
            Ok(t) => t,
            Err(e) => {
                Self::finish_failed(jobs, jid, &format!("generation failed: {e}"), None, None, Some(&product));
                return Outcome::Failed;
            }
        };
        let (mut ok, mut errors) = validate_assessment(&assessment, &product);
        if !ok {
            // Bounded self-correction: exactly ONE retry, carrying the
            // first five validation errors as the correction (Python:
            // `"; ".join(errors[:5])`). A second counted call, never
            // a third.
            let correction: String = errors.iter().take(5).cloned().collect::<Vec<_>>().join("; ");
            match gen.generate(&product, &raw, &timestamp, Some(&correction)) {
                Ok((a2, m2, l2)) => {
                    assessment = a2; model = m2;
                    latency = latency.saturating_add(l2);
                    let v = validate_assessment(&assessment, &product);
                    ok = v.0; errors = v.1;
                }
                Err(e) => {
                    Self::finish_failed(jobs, jid, &format!("generation failed: {e}"), Some(&model), Some(latency), Some(&product));
                    return Outcome::Failed;
                }
            }
        }
        if !ok {
            let detail: String = errors.iter().take(5).cloned().collect::<Vec<_>>().join("; ");
            Self::finish_failed(jobs, jid, &format!("model output failed validateAssessment (after one correction retry): {detail}"), Some(&model), Some(latency), Some(&product));
            return Outcome::Failed;
        }
        let result = serde_json::json!({
            "job_id": jid, "status": "ok", "assessment": assessment,
            "error": null, "model": model, "latency_ms": latency,
            "completed_at": now_iso(),
        });
        jobs.lock().unwrap().put_result(&result);
        relay_notify(&result, Some(&product));
        jobs.lock().unwrap().finish(jid, "done", &format!("assessment by {nick}"));
        Outcome::Done
    }

    fn finish_failed(jobs: &Mutex<&mut JobStore<B>>, jid: &str, error: &str, model: Option<&String>, latency: Option<u64>, product: Option<&str>) {
        // Char-safe caps: `&error[..500]` panics on a multi-byte boundary,
        // and the Python original caps by characters (`trio_agent.py:204-213`).
        let capped: String = error.chars().take(500).collect();
        let note: String = error.chars().take(200).collect();
        let result = serde_json::json!({
            "job_id": jid, "status": "failed", "assessment": null,
            "error": capped, "model": model, "latency_ms": latency,
            "completed_at": now_iso(),
        });
        jobs.lock().unwrap().put_result(&result);
        relay_notify(&result, product);
        jobs.lock().unwrap().finish(jid, "failed", &note);
    }
}

/// Renew the claim every `interval_secs` until `stop` is set or renewal
/// fails (lease lost: the thread exits, like the Python thread's early
/// return). Sleeps in [`HEARTBEAT_POLL`] slices so a set flag stops the
/// thread promptly; [`heartbeat_loop`] uses the Python interval rule.
pub fn heartbeat_loop<B: StoreBackend>(
    jobs: &Mutex<&mut JobStore<B>>,
    stop: &AtomicBool,
    jid: &str,
    nick: &str,
    lease: u64,
) {
    heartbeat_loop_every(jobs, stop, jid, nick, lease, heartbeat_interval_secs(lease));
}

/// [`heartbeat_loop`] with an explicit interval: the test seam (the
/// production interval's 5s floor would make renewal unobservable in a
/// fast test).
pub fn heartbeat_loop_every<B: StoreBackend>(
    jobs: &Mutex<&mut JobStore<B>>,
    stop: &AtomicBool,
    jid: &str,
    nick: &str,
    lease: u64,
    interval_secs: f64,
) {
    let mut waited = 0.0;
    let step = HEARTBEAT_POLL.as_secs_f64();
    loop {
        std::thread::sleep(HEARTBEAT_POLL);
        if stop.load(Ordering::SeqCst) {
            return;
        }
        waited += step;
        if waited + 1e-9 >= interval_secs {
            waited = 0.0;
            if !jobs.lock().unwrap().renew_claim(jid, nick, lease) {
                return;
            }
        }
    }
}

/// Full v2 contract validation — port of `validateAssessment` in
/// `js/schema.js` (same shapes, same error strings, same strictness:
/// real calendar dates, present-but-nullable numbers, non-empty
/// category/description/product/model, string evidence/summary,
/// string-array uncertainty, boolean requires_human_review).
/// Extra fields tolerated; nothing fabricated.
pub fn validate_assessment(value: &Value, expected_product: &str) -> (bool, Vec<String>) {
    let mut errors: Vec<String> = vec![];
    let obj = match value.as_object() {
        Some(o) => o,
        None => return (false, vec!["response is not a JSON object".to_string()]),
    };

    if expected_product.is_empty() {
        errors.push("expected product: missing or invalid (validator requires the requested product)".to_string());
    } else {
        match obj.get("product").and_then(Value::as_str) {
            Some(p) if !p.trim().is_empty() => {
                if p != expected_product {
                    errors.push(format!("product: expected \"{expected_product}\", got \"{p}\""));
                }
            }
            _ => errors.push("product: missing or not a non-empty string".to_string()),
        }
    }

    match obj.get("timestamp").and_then(Value::as_str) {
        Some(t) if !t.is_empty() => {
            if !is_valid_iso8601(t) {
                errors.push("timestamp: not a parseable ISO-8601 date".to_string());
            }
        }
        _ => errors.push("timestamp: missing or not a string".to_string()),
    }

    match obj.get("observations") {
        Some(Value::Array(items)) => {
            for (i, obs) in items.iter().enumerate() {
                let prefix = format!("observations[{i}]");
                let o = match obs.as_object() {
                    Some(o) => o,
                    None => {
                        errors.push(format!("{prefix}: not an object"));
                        continue;
                    }
                };
                match o.get("category").and_then(Value::as_str) {
                    Some(c) if !c.trim().is_empty() => {}
                    _ => errors.push(format!("{prefix}.category: missing or not a non-empty string")),
                }
                match o.get("description").and_then(Value::as_str) {
                    Some(d) if !d.trim().is_empty() => {}
                    _ => errors.push(format!("{prefix}.description: missing or not a non-empty string")),
                }
                if !matches!(o.get("evidence"), Some(Value::String(_))) {
                    errors.push(format!("{prefix}.evidence: missing or not a string"));
                }
                check_nullable_number(o, "confidence", &format!("{prefix}.confidence"), &mut errors, Some(0.0), Some(1.0));
                // A region is optional, but when present every coordinate must
                // be a number inside the 0..=1000 frame the record contract
                // uses. A box outside that frame is a mis-scaled box, not a
                // different observation, so it is refused rather than clipped.
                if let Some(region) = o.get("region") {
                    match region.as_object() {
                        _ if region.is_null() => {}
                        None => errors.push(format!("{prefix}.region: must be an object or null")),
                        Some(r) => {
                            for (key, value) in r {
                                match value.as_f64() {
                                    Some(n) if (0.0..=1000.0).contains(&n) => {}
                                    Some(_) => errors.push(format!(
                                        "{prefix}.region.{key}: outside 0..1000"
                                    )),
                                    None => errors.push(format!(
                                        "{prefix}.region.{key}: must be a number"
                                    )),
                                }
                            }
                        }
                    }
                }
            }
        }
        _ => errors.push("observations: missing or not an array".to_string()),
    }

    match obj.get("assessment") {
        Some(Value::Object(a)) => {
            match a.get("category").and_then(Value::as_str) {
                Some(c) if !c.trim().is_empty() => {}
                _ => errors.push("assessment.category: missing or not a non-empty string".to_string()),
            }
            if !matches!(a.get("summary"), Some(Value::String(_))) {
                errors.push("assessment.summary: missing or not a string".to_string());
            }
            match a.get("uncertainty") {
                Some(Value::Array(items)) => {
                    for (i, item) in items.iter().enumerate() {
                        if !matches!(item, Value::String(_)) {
                            errors.push(format!("assessment.uncertainty[{i}]: not a string"));
                        }
                    }
                }
                _ => errors.push("assessment.uncertainty: missing or not an array".to_string()),
            }
            if !matches!(a.get("requires_human_review"), Some(Value::Bool(_))) {
                errors.push("assessment.requires_human_review: missing or not a boolean".to_string());
            }
        }
        _ => errors.push("assessment: missing or not an object".to_string()),
    }

    match obj.get("processing") {
        Some(Value::Object(p)) => {
            match p.get("model").and_then(Value::as_str) {
                Some(m) if !m.trim().is_empty() => {}
                _ => errors.push("processing.model: missing or not a non-empty string".to_string()),
            }
            check_nullable_number(p, "latency_ms", "processing.latency_ms", &mut errors, Some(0.0), None);
        }
        _ => errors.push("processing: missing or not an object".to_string()),
    }

    if errors.is_empty() {
        (true, vec![])
    } else {
        (false, errors)
    }
}

fn check_nullable_number(
    obj: &serde_json::Map<String, Value>,
    key: &str,
    field: &str,
    errors: &mut Vec<String>,
    min: Option<f64>,
    max: Option<f64>,
) {
    let v = match obj.get(key) {
        None => {
            errors.push(format!("{field}: missing (must be present, null when unreported)"));
            return;
        }
        Some(Value::Null) => return,
        Some(Value::Number(n)) => n.as_f64().unwrap(),
        Some(_) => {
            errors.push(format!("{field}: must be null or a number"));
            return;
        }
    };
    if !v.is_finite() {
        errors.push(format!("{field}: must be null or a number"));
        return;
    }
    if let Some(lo) = min {
        if v < lo {
            errors.push(format!("{field}: must not be below {lo}"));
            return;
        }
    }
    if let Some(hi) = max {
        if v > hi {
            errors.push(format!("{field}: out of range {lo}..{hi}", lo = min.unwrap_or(0.0)));
        }
    }
}

/// Strict ISO-8601 with T separator, timezone, and real calendar dates.
/// Mirrors `isValidIso8601` in js/schema.js: `YYYY-MM-DDTHH:MM`,
/// optional `:SS[.frac]`, then `Z` or a numeric offset. Rejects
/// free-form dates and impossible calendar dates.
fn is_valid_iso8601(s: &str) -> bool {
    let (date, time) = match s.split_once('T') {
        Some(t) => t,
        None => return false,
    };
    if date.len() != 10 || date.as_bytes()[4] != b'-' || date.as_bytes()[7] != b'-' {
        return false;
    }
    let num = |a: &str| a.parse::<i32>().ok();
    let (y, mo, da) = match (num(&date[0..4]), num(&date[5..7]), num(&date[8..10])) {
        (Some(y), Some(mo), Some(da)) => (y, mo as u32, da as u32),
        _ => return false,
    };
    if !(1..=12).contains(&mo) || da < 1 || da > days_in_month(y, mo) {
        return false;
    }
    if time.len() < 5 || time.as_bytes()[2] != b':' {
        return false;
    }
    let (h, mi) = match (num(&time[0..2]), num(&time[3..5])) {
        (Some(h), Some(mi)) => (h, mi),
        _ => return false,
    };
    if h > 23 || mi > 59 {
        return false;
    }
    let mut rest = &time[5..];
    if rest.starts_with(':') {
        if rest.len() < 3 {
            return false;
        }
        match rest[1..3].parse::<i32>() {
            Ok(se) if se <= 59 => {}
            _ => return false,
        }
        rest = &rest[3..];
        if rest.starts_with('.') {
            let frac: String = rest[1..].chars().take_while(|c| c.is_ascii_digit()).collect();
            if frac.is_empty() {
                return false;
            }
            rest = &rest[1 + frac.len()..];
        }
    }
    if rest == "Z" {
        return true;
    }
    let b = rest.as_bytes();
    if b.len() < 3 || (b[0] != b'+' && b[0] != b'-') {
        return false;
    }
    let digits: String = rest[1..].chars().filter(|c| *c != ':').collect();
    if digits.len() != 4 || !digits.bytes().all(|c| c.is_ascii_digit()) {
        return false;
    }
    let (oh, om) = (digits[0..2].parse::<i32>().unwrap(), digits[2..4].parse::<i32>().unwrap());
    oh <= 23 && om <= 59
}

fn days_in_month(y: i32, mo: u32) -> u32 {
    match mo {
        2 => {
            let leap = y % 4 == 0 && (y % 100 != 0 || y % 400 == 0);
            if leap { 29 } else { 28 }
        }
        4 | 6 | 9 | 11 => 30,
        _ => 31,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use queue_store::InMemoryStore;

    struct Scripted(Vec<(Value, String, u64)>, Vec<Option<String>>);
    impl Generator for Scripted {
        fn generate(&mut self, _p: &str, _img: &[u8], _ts: &str, correction: Option<&str>) -> Result<(Value, String, u64), String> {
            self.1.push(correction.map(|s| s.to_string()));
            let i = self.1.len() - 1;
            Ok(self.0[i].clone())
        }
    }

    fn canned() -> Value {
        serde_json::json!({
            "product": "ignis", "timestamp": "2026-10-30T06:00:00.000Z",
            "observations": [{"category": "steam or fog", "description": "d", "evidence": "c", "confidence": null}],
            "assessment": {"category": "steam or fog", "summary": "s", "uncertainty": [], "requires_human_review": true},
            "processing": {"model": "muse-spark-1.3", "latency_ms": null}
        })
    }

    fn submit_job(jobs: &mut JobStore<InMemoryStore>, jid: &str) {
        let raw = vec![0xffu8, 0xd8];
        let env = serde_json::json!({"id": jid, "kind": "trio-assessment", "version": 1, "product": "ignis", "timestamp": "t",
            "image": {"dataUrl": format!("data:image/jpeg;base64,{}", B64.encode(&raw)), "byteLength": raw.len(), "sha256": hex::encode(Sha256::digest(&raw))}});
        let _ = jobs.submit(&env);
    }

    #[test]
    fn valid_first_output_is_exactly_one_call() {
        let mut jobs = JobStore::new(InMemoryStore::default(), "t");
        submit_job(&mut jobs, "trio-a");
        let mut a = Agent { nick: "n".into(), lease: 60, jobs, gen: Scripted(vec![(canned(), "m".into(), 5)], vec![]) };
        assert_eq!(a.serve_job("trio-a"), Outcome::Done);
        assert_eq!(a.gen.1.len(), 1);
    }

    #[test]
    fn invalid_then_valid_retries_once() {
        let mut jobs = JobStore::new(InMemoryStore::default(), "t");
        submit_job(&mut jobs, "trio-b");
        let mut a = Agent { nick: "n".into(), lease: 60, jobs,
            gen: Scripted(vec![(serde_json::json!({"not":"c"}), "m".into(), 10), (canned(), "muse-spark-1.3".into(), 20)], vec![]) };
        assert_eq!(a.serve_job("trio-b"), Outcome::Done);
        assert_eq!(a.gen.1.len(), 2);
    }

    #[test]
    fn full_contract_vectors() {
        // Valid canned assessment passes with its envelope product.
        assert!(validate_assessment(&canned(), "ignis").0);
        // Product mismatch.
        let (_, e) = validate_assessment(&canned(), "vigiles");
        assert!(e.iter().any(|x| x.contains("expected \"vigiles\"")), "{e:?}");
        // Missing keys named, not silently passed.
        let (_, e) = validate_assessment(&serde_json::json!({}), "ignis");
        assert!(e.iter().any(|x| x.contains("product: missing")), "{e:?}");
        assert!(e.iter().any(|x| x.contains("observations: missing")), "{e:?}");
        // Bad timestamp (impossible date).
        let mut bad = canned();
        bad["timestamp"] = serde_json::json!("2026-02-30T06:00:00Z");
        let (_, e) = validate_assessment(&bad, "ignis");
        assert!(e.iter().any(|x| x.contains("not a parseable ISO-8601")), "{e:?}");
        // Confidence out of range.
        let mut bad = canned();
        bad["observations"][0]["confidence"] = serde_json::json!(2);
        let (_, e) = validate_assessment(&bad, "ignis");
        assert!(e.iter().any(|x| x.contains("confidence")), "{e:?}");
        // Missing latency_ms key (null is fine, absence is not).
        let mut bad = canned();
        bad["processing"].as_object_mut().unwrap().remove("latency_ms");
        let (_, e) = validate_assessment(&bad, "ignis");
        assert!(e.iter().any(|x| x.contains("latency_ms: missing")), "{e:?}");
        // Uncertainty item must be a string.
        let mut bad = canned();
        bad["assessment"]["uncertainty"] = serde_json::json!([3]);
        let (_, e) = validate_assessment(&bad, "ignis");
        assert!(e.iter().any(|x| x.contains("uncertainty[0]")), "{e:?}");
        // requires_human_review must be boolean.
        let mut bad = canned();
        bad["assessment"]["requires_human_review"] = serde_json::json!("yes");
        let (_, e) = validate_assessment(&bad, "ignis");
        assert!(e.iter().any(|x| x.contains("requires_human_review")), "{e:?}");
    }
}
