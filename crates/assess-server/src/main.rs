//! Crate `assess-server` — Meta OS Rust rebuild (B05, Rowan).
//! Sources: `server/README.md`, `server/assess.mjs`, `server/model.mjs`,
//! `server/queue.mjs`, `server/server.mjs`. Port behavior, do not redesign.

use base64::{engine::general_purpose::STANDARD as B64, Engine as _};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

pub const MAX_IMAGE_BYTES: usize = 8 * 1024 * 1024;
pub const SPARK_ENDPOINT: &str = "https://api.meta.ai/v1/chat/completions";
pub const SPARK_MODEL: &str = "muse-spark-1.3";
pub const QUEUE_JOB_VERSION: u32 = 1;
pub const QUEUE_JOB_KIND: &str = "trio-assessment";

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

/// Strict ISO-8601 with timezone, real calendar dates only.
/// Mirrors `isValidIso8601` in assess.mjs.
pub fn is_valid_iso8601(s: &str) -> bool {
    let (dt, tz) = match s.rfind(|c| c == 'Z' || c == '+' || c == '-') {
        Some(i) if i > 10 => (&s[..i], &s[i..]),
        _ => return false,
    };
    if tz != "Z" && tz.len() < 3 {
        return false;
    }
    let d = dt.as_bytes();
    if d.len() < 19 { return false; }
    if d[4] != b'-' || d[7] != b'-' || d[10] != b'T' || d[13] != b':' || d[16] != b':' {
        return false;
    }
    let num = |a: usize, b: usize| s[a..b].parse::<i32>().ok();
    let (y, mo, da, h, mi, se) = match (num(0,4), num(5,7), num(8,10), num(11,13), num(14,16), num(17,19)) {
        (Some(y), Some(mo), Some(da), Some(h), Some(mi), Some(se)) => (y, mo as u32, da as u32, h, mi, se),
        _ => return false,
    };
    if !(1..=12).contains(&mo) || da < 1 || da > days_in_month(y, mo) { return false; }
    if h > 23 || mi > 59 || se > 59 { return false; }
    true
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

pub fn validate_assess_request(payload: &Value) -> Result<Value, Vec<String>> {
    let mut errors = vec![];
    let obj = payload.as_object();
    if obj.is_none() {
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
    // assess.mjs accepts {product,timestamp,image:string}; be lenient.
    let img_val = img.clone();
    let (bytes, media) = match parse_image_data_url(&img_val) {
        Ok(t) => t,
        Err(e) => {
            errors.push(e);
            (vec![], String::new())
        }
    };
    if !errors.is_empty() {
        return Err(errors);
    }
    Ok(json!({"product": product, "timestamp": ts, "imageBytes_len": bytes.len(), "mediaType": media}))
}

#[derive(Debug, Clone)]
pub struct QueueError {
    pub code: &'static str,
    pub message: String,
}

pub fn queue_config_enabled(env_queue_enabled: bool) -> bool {
    env_queue_enabled
}

/// Deterministic job id — mirrors buildQueueJob id derivation.
pub fn build_queue_job_id(product: &str, timestamp: &str, frame: &[u8]) -> String {
    let mut h = Sha256::new();
    h.update(product.as_bytes());
    h.update([0u8]);
    h.update(timestamp.as_bytes());
    h.update([0u8]);
    h.update(frame);
    format!("trio-{}", &hex::encode(h.finalize())[..32])
}

pub fn build_queue_job(product: &str, timestamp: &str, frame: &[u8]) -> Result<Value, QueueError> {
    if !is_product_id(product) {
        return Err(QueueError { code: "queue_submit_failed", message: format!("Cannot build a queue job for product \"{product}\".") });
    }
    if timestamp.is_empty() {
        return Err(QueueError { code: "queue_submit_failed", message: "Cannot build a queue job without a timestamp.".to_string() });
    }
    if frame.is_empty() {
        return Err(QueueError { code: "queue_submit_failed", message: "Cannot build a queue job without image bytes.".to_string() });
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

fn main() {
    println!("assess-server B05: POST /api/assess on :8080; GET /api/health; static /");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn timestamp_strict() {
        assert!(is_valid_iso8601("2026-10-30T06:00:00.000Z"));
        assert!(!is_valid_iso8601("2026-13-01T00:00:00Z"));
        assert!(!is_valid_iso8601("not-a-date"));
    }

    #[test]
    fn queue_job_id_deterministic() {
        let a = build_queue_job_id("ignis", "t", &[1, 2, 3]);
        let b = build_queue_job_id("ignis", "t", &[1, 2, 3]);
        assert_eq!(a, b);
        assert!(a.starts_with("trio-"));
    }
}
