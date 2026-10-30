//! Crate `assess-server` — Meta OS Rust rebuild (B05, Rowan).
//!
//! Sources: `server/README.md`, `server/assess.mjs`, `server/model.mjs`,
//! `server/queue.mjs`, `server/server.mjs`. Port behavior, do not redesign.
//!
//! Real HTTP service (std `TcpListener`, thread per connection — mirrors
//! plain `node:http` in server.mjs, no framework): POST /api/assess,
//! GET /api/health, static frontend from the launch directory.
//! Assessment order (QUEUE-TRANSPORT-3): queue first when
//! `TRIO_QUEUE_ENABLED=1` (bounded 30x1s poll, fallback to direct Spark
//! on any queue failure, logged never faked); invalid queue/model
//! answers are 502, never silent fallbacks. No assessment is ever
//! invented here: every error path returns an HTTP status + error shape.

use base64::{engine::general_purpose::STANDARD as B64, Engine as _};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::io::{BufRead, BufReader, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::time::Duration;

pub const MAX_IMAGE_BYTES: usize = 8 * 1024 * 1024;
pub const MAX_BODY_BYTES: usize = 12 * 1024 * 1024;
pub const QUEUE_JOB_VERSION: u32 = 1;
pub const QUEUE_JOB_KIND: &str = "trio-assessment";
pub const QUEUE_RESULT_VERSION: u32 = 1;
pub const QUEUE_RESULT_KIND: &str = "trio-assessment-result";
pub const QUEUE_POLL_INTERVAL_MS: u64 = 1000;
pub const QUEUE_POLL_MAX_ATTEMPTS: u32 = 30;

pub use guardrail::{SPARK_ENDPOINT, SPARK_MODEL};

pub fn is_product_id(v: &str) -> bool {
    matches!(v, "vigiles" | "ignis" | "medicus")
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

/// Strict ISO-8601 (mirrors assess.mjs + js/schema.js): T separator,
/// optional seconds/fraction, timezone required, real calendar dates.
pub fn is_valid_iso8601(s: &str) -> bool {
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

pub fn parse_image_data_url(image: &Value) -> Result<(Vec<u8>, String), String> {
    let s = image.as_str().ok_or("image: missing or not a string (expected a JPEG data URL)")?;
    let prefix = "data:image/jpeg;base64,";
    if !s.starts_with(prefix) {
        return Err("image: must be a data:image/jpeg;base64 URL, as both clients send".to_string());
    }
    let bytes = B64.decode(&s[prefix.len()..]).map_err(|_| "image: data URL does not base64-decode".to_string())?;
    if bytes.is_empty() {
        return Err("image: data URL decodes to zero bytes".to_string());
    }
    if bytes.len() > MAX_IMAGE_BYTES {
        return Err(format!("image: {} bytes exceeds the {MAX_IMAGE_BYTES}-byte cap", bytes.len()));
    }
    if bytes.len() < 3 || bytes[0] != 0xff || bytes[1] != 0xd8 || bytes[2] != 0xff {
        return Err("image: decoded bytes do not start with the JPEG magic bytes".to_string());
    }
    Ok((bytes, "image/jpeg".to_string()))
}

pub struct ValidInput {
    pub product: String,
    pub timestamp: String,
    pub image_bytes: Vec<u8>,
    pub media_type: String,
}

pub fn validate_assess_request(payload: &Value) -> Result<ValidInput, Vec<String>> {
    let mut errors = vec![];
    if !payload.is_object() {
        return Err(vec!["request body is not a JSON object".to_string()]);
    }
    let product = payload.get("product").and_then(Value::as_str).unwrap_or("");
    if !is_product_id(product) {
        errors.push("product: must be one of \"vigiles\", \"ignis\", \"medicus\"".to_string());
    }
    let ts = payload.get("timestamp").and_then(Value::as_str).unwrap_or("");
    if !is_valid_iso8601(ts) {
        errors.push("timestamp: must be a valid ISO-8601 timestamp with timezone".to_string());
    }
    let img = payload.get("image").unwrap_or(&Value::Null);
    let (bytes, media) = match parse_image_data_url(&img.clone()) {
        Ok(t) => t,
        Err(e) => {
            errors.push(e);
            (vec![], String::new())
        }
    };
    if !errors.is_empty() {
        return Err(errors);
    }
    Ok(ValidInput { product: product.to_string(), timestamp: ts.to_string(), image_bytes: bytes, media_type: media })
}

// ---------------------------------------------------------------------------
// Queue transport (server/queue.mjs)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct QueueError {
    pub code: &'static str,
    pub message: String,
}
impl QueueError {
    fn new(code: &'static str, message: impl Into<String>) -> Self {
        Self { code, message: message.into() }
    }
}

#[derive(Debug, Clone)]
pub struct QueueConfig {
    pub enabled: bool,
    pub url: String,
}

pub fn queue_config_enabled(env_queue_enabled: bool, url: &str) -> QueueConfig {
    QueueConfig { enabled: env_queue_enabled, url: url.to_string() }
}

/// Deterministic job id — the single implementation lives in
/// `queue_core` (owning crate); this is a thin alias, not a copy.
pub fn build_queue_job_id(product: &str, timestamp: &str, frame: &[u8]) -> String {
    queue_core::deterministic_job_id(product, timestamp, frame)
}

pub fn build_queue_job(product: &str, timestamp: &str, frame: &[u8]) -> Result<Value, QueueError> {
    if !is_product_id(product) {
        return Err(QueueError::new("queue_submit_failed", format!("Cannot build a queue job for product \"{product}\".")));
    }
    if timestamp.is_empty() {
        return Err(QueueError::new("queue_submit_failed", "Cannot build a queue job without a timestamp."));
    }
    if frame.is_empty() {
        return Err(QueueError::new("queue_submit_failed", "Cannot build a queue job without image bytes."));
    }
    let digest = hex::encode(Sha256::digest(frame));
    let id = build_queue_job_id(product, timestamp, frame);
    Ok(json!({
        "version": QUEUE_JOB_VERSION, "kind": QUEUE_JOB_KIND, "id": id,
        "product": product, "timestamp": timestamp,
        "image": {"mediaType": "image/jpeg", "byteLength": frame.len(), "sha256": digest,
                  "dataUrl": format!("data:image/jpeg;base64,{}", B64.encode(frame))},
    }))
}

fn queue_service_base(url: &str) -> String {
    url.trim_end_matches('/').to_string()
}

fn ureq_agent() -> ureq::Agent {
    ureq::AgentBuilder::new().timeout(Duration::from_secs(30)).build()
}

/// Production POST transport: TRIO_QUEUE_URL is the service base URL.
pub fn http_queue_post(base: &str, job: &Value) -> Result<String, QueueError> {
    let url = format!("{}/jobs", queue_service_base(base));
    let resp = ureq_agent().post(&url).set("Content-Type", "application/json").send_json(job.clone()).map_err(|e| match e {
        ureq::Error::Status(code, _) => QueueError::new("queue_submit_failed", format!("Queue submit failed with HTTP {code}.")),
        e => QueueError::new("queue_submit_failed", format!("Queue submit failed: {e}.")),
    })?;
    let data: Value = resp.into_json().map_err(|_| QueueError::new("queue_submit_failed", "Queue submit response was not JSON."))?;
    let job_id = data.get("jobId").or_else(|| data.get("id")).or_else(|| data.get("job_id")).and_then(Value::as_str).unwrap_or("");
    if job_id.is_empty() {
        return Err(QueueError::new("queue_submit_failed", "Queue submit returned no job id."));
    }
    Ok(job_id.to_string())
}

/// Production GET transport. A missing result (404) is "pending".
pub fn http_queue_get(base: &str, job_id: &str) -> Result<Value, QueueError> {
    let url = format!("{}/jobs/{}/result", queue_service_base(base), job_id);
    match ureq_agent().get(&url).call() {
        Ok(resp) => resp.into_json().map_err(|_| QueueError::new("queue_fetch_failed", "Queue result response was not JSON.")),
        Err(ureq::Error::Status(404, _)) => Ok(json!({"job_id": job_id, "status": "pending", "assessment": null, "error": null})),
        Err(ureq::Error::Status(code, _)) => Err(QueueError::new("queue_fetch_failed", format!("Queue result fetch failed with HTTP {code}."))),
        Err(e) => Err(QueueError::new("queue_fetch_failed", format!("Queue result fetch failed: {e}."))),
    }
}

fn is_plain_object(v: &Value) -> bool {
    v.is_object()
}

/// Normalized result: pending | done{assessment} | failed{error?}.
#[derive(Debug, Clone, PartialEq)]
pub enum QueueResult {
    Pending { job_id: String },
    Done { job_id: String, assessment: Value },
    Failed { job_id: String, error: Option<String> },
}

fn fail(detail: &str) -> QueueError {
    QueueError::new("queue_fetch_failed", format!("Queue result envelope malformed: {detail}"))
}

/// Accepts the Pax-agreed shape and the step-2 proposed shape.
pub fn parse_queue_result_envelope(result: &Value, job_id: &str) -> Result<QueueResult, QueueError> {
    if !is_plain_object(result) {
        return Err(fail("result is not an object"));
    }
    if let Some(j) = result.get("job_id").and_then(Value::as_str) {
        if j != job_id {
            return Err(fail("job_id does not match the requested job"));
        }
    }
    if let Some(j) = result.get("jobId").and_then(Value::as_str) {
        if j != job_id {
            return Err(fail("jobId does not match the requested job"));
        }
    }
    // Proposed step-2 shape: version/kind present means exact.
    if result.get("version").is_some() || result.get("kind").is_some() {
        if result.get("version").and_then(Value::as_u64) != Some(QUEUE_RESULT_VERSION as u64) {
            return Err(fail(&format!("version is not {QUEUE_RESULT_VERSION}")));
        }
        if result.get("kind").and_then(Value::as_str) != Some(QUEUE_RESULT_KIND) {
            return Err(fail(&format!("kind is not \"{QUEUE_RESULT_KIND}\"")));
        }
        if result.get("jobId").and_then(Value::as_str) != Some(job_id) {
            return Err(fail("jobId does not match the requested job"));
        }
        return match result.get("status").and_then(Value::as_str) {
            Some("pending") => Ok(QueueResult::Pending { job_id: job_id.into() }),
            Some("done") => match result.get("assessment") {
                Some(a) if is_plain_object(a) => Ok(QueueResult::Done { job_id: job_id.into(), assessment: a.clone() }),
                _ => Err(fail("done result carries no assessment object")),
            },
            Some("failed") => match result.get("error") {
                None => Ok(QueueResult::Failed { job_id: job_id.into(), error: None }),
                Some(Value::String(e)) => Ok(QueueResult::Failed { job_id: job_id.into(), error: Some(e.clone()) }),
                Some(_) => Err(fail("failed result carries a non-string error")),
            },
            other => Err(fail(&format!("unknown status \"{}\"", other.unwrap_or("?")))),
        };
    }
    // Pax-agreed shape.
    if result.get("job_id").and_then(Value::as_str) != Some(job_id) {
        return Err(fail("job_id does not match the requested job"));
    }
    match result.get("status").and_then(Value::as_str) {
        Some("pending") => {
            if !matches!(result.get("assessment"), None | Some(Value::Null)) {
                return Err(fail("pending result carries an assessment"));
            }
            Ok(QueueResult::Pending { job_id: job_id.into() })
        }
        Some("ok") => {
            let assessment = match result.get("assessment") {
                Some(a) if is_plain_object(a) => a.clone(),
                _ => return Err(fail("ok result carries no assessment object")),
            };
            if !matches!(result.get("error"), None | Some(Value::Null)) {
                return Err(fail("ok result carries an error"));
            }
            Ok(QueueResult::Done { job_id: job_id.into(), assessment })
        }
        Some("failed") => {
            match result.get("error") {
                None | Some(Value::Null) => {}
                Some(Value::String(_)) => {}
                Some(_) => return Err(fail("failed result carries a non-string error")),
            }
            if !matches!(result.get("assessment"), None | Some(Value::Null)) {
                return Err(fail("failed result carries an assessment"));
            }
            Ok(QueueResult::Failed { job_id: job_id.into(), error: result.get("error").and_then(Value::as_str).map(str::to_string) })
        }
        other => Err(fail(&format!("unknown status \"{}\"", other.unwrap_or("?")))),
    }
}

pub fn submit_queue_job(job: &Value, cfg: &QueueConfig, post: &dyn Fn(&str, &Value) -> Result<String, QueueError>) -> Result<String, QueueError> {
    if !cfg.enabled {
        return Err(QueueError::new("queue_disabled", "The OS queue path is disabled: TRIO_QUEUE_ENABLED is not 1. The direct Spark path remains the fallback."));
    }
    if cfg.url.is_empty() {
        return Err(QueueError::new("queue_not_configured", "No queue URL is configured on the server. Set TRIO_QUEUE_URL in the server environment."));
    }
    if !job.is_object()
        || job.get("version").and_then(Value::as_u64) != Some(QUEUE_JOB_VERSION as u64)
        || job.get("kind").and_then(Value::as_str) != Some(QUEUE_JOB_KIND)
        || job.get("id").and_then(Value::as_str).map(|s| s.is_empty()).unwrap_or(true)
    {
        return Err(QueueError::new("queue_submit_failed", "Refused to submit a malformed queue job."));
    }
    post(&cfg.url, job).map_err(|e| match e {
        QueueError { .. } => e,
    })
}

pub fn fetch_queue_result(job_id: &str, cfg: &QueueConfig, get: &dyn Fn(&str, &str) -> Result<Value, QueueError>) -> Result<QueueResult, QueueError> {
    if !cfg.enabled {
        return Err(QueueError::new("queue_disabled", "The OS queue path is disabled: TRIO_QUEUE_ENABLED is not 1. The direct Spark path remains the fallback."));
    }
    if cfg.url.is_empty() {
        return Err(QueueError::new("queue_not_configured", "No queue URL is configured on the server. Set TRIO_QUEUE_URL in the server environment."));
    }
    if job_id.is_empty() {
        return Err(QueueError::new("queue_fetch_failed", "Cannot fetch a queue result without a job id."));
    }
    let raw = get(&cfg.url, job_id)?;
    parse_queue_result_envelope(&raw, job_id)
}

pub fn poll_queue_result(
    job_id: &str,
    cfg: &QueueConfig,
    get: &dyn Fn(&str, &str) -> Result<Value, QueueError>,
    max_attempts: u32,
    interval_ms: u64,
    sleep_ms: &dyn Fn(u64),
) -> Result<QueueResult, QueueError> {
    for attempt in 1..=max_attempts.max(1) {
        let result = fetch_queue_result(job_id, cfg, get)?;
        match result {
            QueueResult::Pending { .. } => {
                if attempt == max_attempts.max(1) {
                    break;
                }
                sleep_ms(interval_ms);
            }
            done => return Ok(done),
        }
    }
    Err(QueueError::new("queue_fetch_failed", format!("Queue result poll timed out after {max_attempts} attempts: job {job_id} still pending. The direct Spark path remains the fallback.")))
}

// ---------------------------------------------------------------------------
// Model adapter (server/model.mjs)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct ModelError {
    pub code: &'static str,
    pub message: String,
}
impl ModelError {
    fn new(code: &'static str, message: impl Into<String>) -> Self {
        Self { code, message: message.into() }
    }
}

pub struct ModelConfig {
    pub key_present: bool,
    pub live_enabled: bool,
}

pub fn model_status(key_present: bool, live_enabled: bool) -> Value {
    json!({"configured": key_present, "live_enabled": live_enabled})
}

pub fn build_spark_prompt(product: &str, timestamp: &str) -> Result<String, ModelError> {
    let p = queue_store::product_profile(product)
        .ok_or_else(|| ModelError::new("model_call_failed", format!("No prompt profile for product \"{product}\".")))?;
    Ok(guardrail::build_prompt(product, p.display_name, p.department, p.categories, p.limitations, timestamp, None))
}

/// Live Spark transport (SPARK-TRANSPORT-1): endpoint/model from the
/// verified smoke call; key only in the Authorization header.
/// Every call passes through the $75 guardrail counter first.
pub fn assess_with_model(input: &ValidInput, key: Option<&str>, live_enabled: bool, endpoint: Option<&str>, guardrail_state: &str) -> Result<Value, ModelError> {
    if !live_enabled {
        return Err(ModelError::new("held", "Live model calls are held: Spark stays off until the build is complete and Del green-lights the test phase."));
    }
    let key = key.filter(|k| !k.is_empty()).ok_or_else(|| {
        ModelError::new("not_configured", "No model API key is configured on the server. Set SPARK_API_KEY in the server environment.")
    })?;
    if let Err(stop) = guardrail::check(&guardrail::load_state(guardrail_state)) {
        return Err(ModelError::new("model_call_failed", stop.0));
    }
    let prompt = build_spark_prompt(&input.product, &input.timestamp)?;
    let image_url = format!("data:image/jpeg;base64,{}", B64.encode(&input.image_bytes));
    let body = json!({
        "model": guardrail::SPARK_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }],
    });
    let url = endpoint.unwrap_or(guardrail::SPARK_ENDPOINT);
    let started = std::time::Instant::now();
    let resp = ureq::AgentBuilder::new()
        .timeout(Duration::from_secs(60))
        .build()
        .post(url)
        .set("Content-Type", "application/json")
        .set("Authorization", &format!("Bearer {key}"))
        .send_json(body)
        .map_err(|e| match e {
            ureq::Error::Status(code, _) => ModelError::new("model_call_failed", format!("Spark request failed with HTTP {code}.")),
            e => ModelError::new("model_call_failed", format!("Spark request failed: {e}.")),
        })?;
    let data: Value = resp.into_json().map_err(|_| ModelError::new("model_call_failed", "Spark response was not JSON."))?;
    let latency_ms = started.elapsed().as_millis().min(u128::from(u64::MAX)) as u64;
    {
        let usage = data.get("usage");
        let in_tok = usage.and_then(|u| u.get("prompt_tokens").or_else(|| u.get("input_tokens"))).and_then(Value::as_u64).unwrap_or(0);
        let out_tok = usage.and_then(|u| u.get("completion_tokens").or_else(|| u.get("output_tokens"))).and_then(Value::as_u64).unwrap_or(0);
        let model = data.get("model").and_then(Value::as_str).unwrap_or(guardrail::SPARK_MODEL);
        guardrail::record(guardrail_state, &format!("assess:{}", input.product), model, in_tok, out_tok, latency_ms);
    }
    let content = data.pointer("/choices/0/message/content");
    let text = match content {
        Some(Value::String(s)) => s.clone(),
        Some(Value::Array(parts)) => parts
            .iter()
            .filter_map(|p| {
                if p.get("type").and_then(Value::as_str) == Some("text") {
                    p.get("text").and_then(Value::as_str).map(str::to_string)
                } else {
                    None
                }
            })
            .collect::<String>(),
        _ => String::new(),
    };
    if text.trim().is_empty() {
        return Err(ModelError::new("model_call_failed", "Spark response carried no message content."));
    }
    let unwrapped = guardrail::unwrap_model_text(&text);
    serde_json::from_str::<Value>(&unwrapped)
        .map_err(|_| ModelError::new("model_call_failed", "Spark response content was not JSON."))
        .and_then(|v| {
            if v.is_object() {
                Ok(v)
            } else {
                Err(ModelError::new("model_call_failed", "Spark response content was not JSON."))
            }
        })
}

// ---------------------------------------------------------------------------
// POST /api/assess orchestration (server/assess.mjs)
// ---------------------------------------------------------------------------

pub struct Env {
    pub trio_queue_enabled: bool,
    pub trio_queue_url: String,
    pub spark_api_key: Option<String>,
    pub assess_live_model: bool,
    /// Guardrail state file (mirrors spark_guardrail_state.json beside
    /// spark_gen.py; deployment-local, never committed).
    pub guardrail_state_path: String,
}
impl Env {
    pub fn from_process() -> Self {
        let v = |k: &str| std::env::var(k).unwrap_or_default();
        Self {
            trio_queue_enabled: v("TRIO_QUEUE_ENABLED") == "1",
            trio_queue_url: v("TRIO_QUEUE_URL"),
            spark_api_key: std::env::var("SPARK_API_KEY").ok().filter(|s| !s.is_empty()),
            assess_live_model: v("ASSESS_LIVE_MODEL") == "1",
            guardrail_state_path: match v("SPARK_GUARDRAIL_STATE").as_str() {
                "" => "spark_guardrail_state.json".to_string(),
                s => s.to_string(),
            },
        }
    }
}

pub struct Deps {
    pub assess_model: fn(&ValidInput, &Env) -> Result<Value, ModelError>,
    pub queue_post: fn(&str, &Value) -> Result<String, QueueError>,
    pub queue_get: fn(&str, &str) -> Result<Value, QueueError>,
    pub poll_interval_ms: u64,
    pub max_attempts: u32,
    pub sleep_ms: fn(u64),
    pub log: fn(&str),
}

fn default_sleep_ms(ms: u64) {
    std::thread::sleep(Duration::from_millis(ms));
}
fn default_log(line: &str) {
    eprintln!("{line}");
}

fn real_assess_model(input: &ValidInput, env: &Env) -> Result<Value, ModelError> {
    assess_with_model(input, env.spark_api_key.as_deref(), env.assess_live_model, None, &env.guardrail_state_path)
}

pub fn default_deps() -> Deps {
    Deps {
        assess_model: real_assess_model,
        queue_post: http_queue_post,
        queue_get: http_queue_get,
        poll_interval_ms: QUEUE_POLL_INTERVAL_MS,
        max_attempts: QUEUE_POLL_MAX_ATTEMPTS,
        sleep_ms: default_sleep_ms,
        log: default_log,
    }
}

/// Validate a model/queue answer against the frozen v2 contract.
/// The single implementation lives in `agent-runtime` (owning crate);
/// an invalid answer is a 502, never a silent fallback.
fn contract_check(output: &Value, product: &str) -> Result<Value, Value> {
    match agent_runtime::validate_assessment(output, product) {
        (true, _) => Ok(output.clone()),
        (false, errors) => Err(json!({"error": format!("Model response failed contract validation: {}", errors.join("; "))})),
    }
}

/// Returns (status, body) ready to serialize.
pub fn handle_assess(payload: &Value, env: &Env, deps: &Deps) -> (u16, Value) {
    let input = match validate_assess_request(payload) {
        Ok(v) => v,
        Err(errors) => return (400, json!({"error": errors.join("; ")})),
    };

    let mut output: Option<Value> = None;
    let mut from_queue = false;
    if env.trio_queue_enabled {
        let cfg = QueueConfig { enabled: true, url: env.trio_queue_url.clone() };
        match build_queue_job(&input.product, &input.timestamp, &input.image_bytes) {
            Ok(job) => match submit_queue_job(&job, &cfg, &|u, j| (deps.queue_post)(u, j)) {
                Ok(sub) => match poll_queue_result(&sub, &cfg, &|u, j| (deps.queue_get)(u, j), deps.max_attempts, deps.poll_interval_ms, &|ms| (deps.sleep_ms)(ms)) {
                    Ok(QueueResult::Done { assessment, .. }) => {
                        output = Some(assessment);
                        from_queue = true;
                    }
                    Ok(QueueResult::Failed { error, .. }) => {
                        (deps.log)(&format!("queue fallback: queue result failed for job {}{}; falling back to the direct Spark path", sub, error.map(|e| format!(": {e}")).unwrap_or_default()));
                    }
                    Ok(QueueResult::Pending { .. }) => {
                        (deps.log)(&format!("queue fallback: queue result pending for job {sub}; falling back to the direct Spark path"));
                    }
                    Err(err) => {
                        (deps.log)(&format!("queue fallback: {}; falling back to the direct Spark path", err.message));
                    }
                },
                Err(err) => {
                    (deps.log)(&format!("queue fallback: {}; falling back to the direct Spark path", err.message));
                }
            },
            Err(err) => {
                (deps.log)(&format!("queue fallback: {}; falling back to the direct Spark path", err.message));
            }
        }
    }

    if !from_queue {
        match (deps.assess_model)(&input, env) {
            Ok(v) => output = Some(v),
            Err(err) => {
                let status = if err.code == "model_call_failed" { 502 } else { 503 };
                return (status, json!({"error": err.message}));
            }
        }
    }

    let output = output.unwrap();
    match contract_check(&output, &input.product) {
        Ok(v) => (200, v),
        Err(body) => (502, body),
    }
}

// ---------------------------------------------------------------------------
// HTTP service (server/server.mjs)
// ---------------------------------------------------------------------------

fn send_json(stream: &mut TcpStream, status: u16, body: &Value) {
    let text = serde_json::to_string(body).unwrap();
    let reason = match status {
        200 => "OK",
        201 => "Created",
        204 => "No Content",
        400 => "Bad Request",
        404 => "Not Found",
        405 => "Method Not Allowed",
        413 => "Payload Too Large",
        500 => "Internal Server Error",
        502 => "Bad Gateway",
        503 => "Service Unavailable",
        _ => "OK",
    };
    let head = format!(
        "HTTP/1.1 {status} {reason}\r\nContent-Type: application/json; charset=utf-8\r\nContent-Length: {}\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n",
        text.len()
    );
    let _ = stream.write_all(head.as_bytes());
    let _ = stream.write_all(text.as_bytes());
}

fn content_type_for(ext: &str) -> Option<&'static str> {
    match ext {
        "html" => Some("text/html; charset=utf-8"),
        "css" => Some("text/css; charset=utf-8"),
        "js" | "mjs" => Some("text/javascript; charset=utf-8"),
        "json" => Some("application/json; charset=utf-8"),
        _ => None,
    }
}

fn serve_static(stream: &mut TcpStream, url_path: &str, doc_root: &Path) {
    let rel = if url_path == "/" { "index.html".to_string() } else { url_path.trim_start_matches('/').to_string() };
    let ext = rel.rsplit('.').next().unwrap_or("");
    let Some(content_type) = content_type_for(ext) else {
        send_json(stream, 404, &json!({"error": format!("not found: {url_path}")}));
        return;
    };
    // Traversal guard: resolve and require containment (mirrors server.mjs).
    let mut file_path = doc_root.to_path_buf();
    for part in rel.split('/') {
        if part.is_empty() || part == "." {
            continue;
        }
        if part == ".." {
            send_json(stream, 404, &json!({"error": format!("not found: {url_path}")}));
            return;
        }
        file_path.push(part);
    }
    match std::fs::read(&file_path) {
        Ok(data) => {
            let head = format!("HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {}\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n", data.len());
            let _ = stream.write_all(head.as_bytes());
            let _ = stream.write_all(&data);
        }
        Err(_) => send_json(stream, 404, &json!({"error": format!("not found: {url_path}")})),
    }
}

pub struct ServerDeps {
    pub env: Env,
    pub deps: Deps,
    pub doc_root: PathBuf,
}

fn handle_connection(stream: TcpStream, srv: &ServerDeps) {
    let mut stream = stream;
    let mut reader = BufReader::new(stream.try_clone().unwrap());
    let mut head = Vec::new();
    loop {
        let mut line = String::new();
        match reader.read_line(&mut line) {
            Ok(0) => return,
            Ok(_) => {}
            Err(_) => return,
        }
        head.extend_from_slice(line.as_bytes());
        if head.ends_with(b"\r\n\r\n") || head.len() > 65536 {
            break;
        }
    }
    let head_text = String::from_utf8_lossy(&head);
    let mut lines = head_text.lines();
    let request_line = lines.next().unwrap_or("");
    let mut parts = request_line.split_whitespace();
    let method = parts.next().unwrap_or("");
    let path = parts.next().unwrap_or("/");
    if method == "OPTIONS" {
        let resp = "HTTP/1.1 204 No Content\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET, POST, OPTIONS\r\nAccess-Control-Allow-Headers: Content-Type\r\nConnection: close\r\n\r\n";
        let _ = stream.write_all(resp.as_bytes());
        return;
    }
    // Content-Length bounded body.
    let mut content_length: usize = 0;
    for line in head_text.lines().skip(1) {
        if line.is_empty() {
            break;
        }
        if let Some(v) = line.strip_prefix("Content-Length:").or_else(|| line.strip_prefix("content-length:")) {
            content_length = v.trim().parse().unwrap_or(0);
        }
    }
    if content_length > MAX_BODY_BYTES {
        send_json(&mut stream, 413, &json!({"error": format!("request body exceeds {MAX_BODY_BYTES} bytes")}));
        return;
    }
    let mut body = vec![0u8; content_length];
    if content_length > 0 {
        if reader.read_exact(&mut body).is_err() {
            send_json(&mut stream, 400, &json!({"error": "request body is not valid JSON"}));
            return;
        }
    }
    if path == "/api/assess" {
        if method != "POST" {
            send_json(&mut stream, 405, &json!({"error": "method not allowed: use POST"}));
            return;
        }
        let payload: Value = match serde_json::from_slice(&body) {
            Ok(v) => v,
            Err(_) => {
                send_json(&mut stream, 400, &json!({"error": "request body is not valid JSON"}));
                return;
            }
        };
        let (status, resp_body) = handle_assess(&payload, &srv.env, &srv.deps);
        send_json(&mut stream, status, &resp_body);
        return;
    }
    if path == "/api/health" {
        if method != "GET" {
            send_json(&mut stream, 405, &json!({"error": "method not allowed: use GET"}));
            return;
        }
        let key_present = srv.env.spark_api_key.is_some();
        send_json(&mut stream, 200, &json!({
            "ok": true, "service": "meta-trio-assess",
            "products": ["vigiles", "ignis", "medicus"],
            "model": model_status(key_present, srv.env.assess_live_model),
        }));
        return;
    }
    if path.starts_with("/api/") {
        send_json(&mut stream, 404, &json!({"error": format!("unknown route: {path}")}));
        return;
    }
    if method != "GET" {
        send_json(&mut stream, 405, &json!({"error": "method not allowed"}));
        return;
    }
    serve_static(&mut stream, path, &srv.doc_root);
}

fn main() {
    let port: u16 = std::env::var("PORT").ok().and_then(|p| p.parse().ok()).unwrap_or(8080);
    let doc_root = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    let env = Env::from_process();
    let status = model_status(env.spark_api_key.is_some(), env.assess_live_model);
    let listener = TcpListener::bind(("127.0.0.1", port)).expect("assess-server: bind failed");
    println!("meta-trio-assess listening on http://localhost:{port}");
    println!("POST /api/assess  GET /api/health  static web app on /");
    println!("model: key {}configured, live calls {} (Spark rule)",
        if status["configured"] == json!(true) { "" } else { "NOT " },
        if status["live_enabled"] == json!(true) { "ENABLED (test phase)" } else { "held" });
    let deps = Box::new(ServerDeps { env, deps: default_deps(), doc_root });
    let deps: &'static ServerDeps = Box::leak(deps);
    for stream in listener.incoming() {
        match stream {
            Ok(s) => {
                std::thread::spawn(move || handle_connection(s, deps));
            }
            Err(e) => eprintln!("assess-server: accept failed: {e}"),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_env() -> Env {
        Env { trio_queue_enabled: false, trio_queue_url: String::new(), spark_api_key: None, assess_live_model: false, guardrail_state_path: std::env::temp_dir().join(format!("test-guardrail-{}.json", std::process::id())).to_string_lossy().into_owned() }
    }

    fn canned_output(product: &str, ts: &str) -> Value {
        json!({
            "product": product, "timestamp": ts,
            "observations": [{"category": "steam or fog", "description": "d", "evidence": "c", "confidence": null}],
            "assessment": {"category": "steam or fog", "summary": "s", "uncertainty": [], "requires_human_review": true},
            "processing": {"model": "muse-spark-1.3", "latency_ms": null},
        })
    }

    fn stub_ok(_input: &ValidInput, _env: &Env) -> Result<Value, ModelError> {
        Ok(canned_output("ignis", "2026-10-30T06:00:00.000Z"))
    }

    fn stub_held(_input: &ValidInput, _env: &Env) -> Result<Value, ModelError> {
        Err(ModelError::new("held", "Live model calls are held: Spark stays off until the build is complete and Del green-lights the test phase."))
    }

    fn stub_garbage(_input: &ValidInput, _env: &Env) -> Result<Value, ModelError> {
        Ok(json!({"not": "a contract"}))
    }

    fn deps_with(stub: fn(&ValidInput, &Env) -> Result<Value, ModelError>) -> Deps {
        Deps {
            assess_model: stub,
            queue_post: |_, _| Err(QueueError::new("queue_submit_failed", "no transport in test")),
            queue_get: |_, _| Err(QueueError::new("queue_fetch_failed", "no transport in test")),
            poll_interval_ms: 0,
            max_attempts: 1,
            sleep_ms: |_| {},
            log: |_| {},
        }
    }

    fn assess_payload() -> Value {
        let frame = vec![0xffu8, 0xd8, 0xff, 0xe0, 0x00];
        json!({
            "product": "ignis",
            "timestamp": "2026-10-30T06:00:00.000Z",
            "image": format!("data:image/jpeg;base64,{}", B64.encode(&frame)),
        })
    }

    #[test]
    fn timestamp_strict() {
        assert!(is_valid_iso8601("2026-10-30T06:00:00.000Z"));
        assert!(is_valid_iso8601("2026-10-30T06:00:00+02:00"));
        assert!(is_valid_iso8601("2026-10-30T06:00Z"));
        assert!(!is_valid_iso8601("2026-13-01T00:00:00Z"));
        assert!(!is_valid_iso8601("2026-02-30T00:00:00Z"));
        assert!(!is_valid_iso8601("not-a-date"));
        assert!(!is_valid_iso8601("2026-10-30 06:00:00"));
    }

    #[test]
    fn queue_job_id_deterministic() {
        let a = build_queue_job_id("ignis", "t", &[1, 2, 3]);
        let b = build_queue_job_id("ignis", "t", &[1, 2, 3]);
        assert_eq!(a, b);
        assert!(a.starts_with("trio-"));
    }

    #[test]
    fn direct_model_ok_returns_200() {
        let (status, body) = handle_assess(&assess_payload(), &test_env(), &deps_with(stub_ok));
        assert_eq!(status, 200);
        assert_eq!(body["assessment"]["category"], "steam or fog");
    }

    #[test]
    fn direct_model_held_returns_503() {
        let (status, body) = handle_assess(&assess_payload(), &test_env(), &deps_with(stub_held));
        assert_eq!(status, 503);
        assert!(body["error"].as_str().unwrap().contains("held"));
    }

    #[test]
    fn invalid_model_answer_is_502_never_silent_fallback() {
        let (status, body) = handle_assess(&assess_payload(), &test_env(), &deps_with(stub_garbage));
        assert_eq!(status, 502);
        assert!(body["error"].as_str().unwrap().contains("contract"));
    }

    #[test]
    fn bad_request_is_400() {
        let (status, _) = handle_assess(&json!({"product": "nope"}), &test_env(), &deps_with(stub_ok));
        assert_eq!(status, 400);
    }

    #[test]
    fn queue_disabled_never_touched() {
        let env = Env { trio_queue_enabled: false, ..test_env() };
        let (status, _) = handle_assess(&assess_payload(), &env, &deps_with(stub_ok));
        assert_eq!(status, 200);
    }

    #[test]
    fn poll_timeout_is_typed_queue_error() {
        let cfg = QueueConfig { enabled: true, url: "http://127.0.0.1:9".into() };
        let pending = |_: &str, _: &str| Ok(json!({"job_id": "trio-x", "status": "pending"}));
        let err = poll_queue_result("trio-x", &cfg, &pending, 2, 0, &|_| {}).unwrap_err();
        assert_eq!(err.code, "queue_fetch_failed");
        assert!(err.message.contains("timed out"));
    }

    #[test]
    fn result_shapes_normalize() {
        let jid = "trio-x";
        let done = parse_queue_result_envelope(&json!({"job_id": jid, "status": "ok", "assessment": {"a": 1}, "error": null}), jid).unwrap();
        assert!(matches!(done, QueueResult::Done { .. }));
        let pend = parse_queue_result_envelope(&json!({"jobId": jid, "status": "pending", "version": 1, "kind": "trio-assessment-result"}), jid).unwrap();
        assert!(matches!(pend, QueueResult::Pending { .. }));
        let failed = parse_queue_result_envelope(&json!({"job_id": jid, "status": "failed", "error": "boom"}), jid).unwrap();
        assert!(matches!(failed, QueueResult::Failed { .. }));
    }

    #[test]
    fn queue_first_invalid_answer_is_502() {        let env = Env { trio_queue_enabled: true, trio_queue_url: "http://q".into(), ..test_env() };
        let deps = Deps {
            assess_model: stub_garbage,
            queue_post: |_, _| Ok("trio-x".into()),
            queue_get: |_, _| Ok(json!({"job_id": "trio-x", "status": "pending"})),
            poll_interval_ms: 0,
            max_attempts: 1,
            sleep_ms: |_| {},
            log: |_| {},
        };
        // Pending poll exhausts the bound (max_attempts=1) -> falls back
        // to direct; direct garbage -> 502, never a silent fallback.
        let (status, _) = handle_assess(&assess_payload(), &env, &deps);
        assert_eq!(status, 502);
    }

    #[test]
    fn guardrail_stop_refuses_before_send() {
        let dir = std::env::temp_dir().join(format!("grd-{}", std::process::id()));
        let _ = std::fs::create_dir_all(&dir);
        let path = dir.join("state.json").to_string_lossy().into_owned();
        std::fs::write(&path, r#"{"calls":999,"est_cost_usd":75.0,"log":[]}"#).unwrap();
        let input = ValidInput { product: "ignis".into(), timestamp: "2026-10-30T06:00:00.000Z".into(), image_bytes: vec![0xff, 0xd8], media_type: "image/jpeg".into() };
        let err = assess_with_model(&input, Some("dummy"), true, Some("http://127.0.0.1:9/"), &path).unwrap_err();
        assert_eq!(err.code, "model_call_failed");
        assert!(err.message.contains("GUARDRAIL STOP"), "{err:?}");
    }
}
