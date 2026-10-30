//! Crate `queue-core` — Meta OS Rust rebuild (B01).
//!
//! Batch B01 — Queue core (queue service). Owner: Rowan.
//! Source files this batch ports:
//! - `server/queue/.gitignore` (carried: local db + guardrail state are gitignored)
//! - `server/queue/README.md` (carried as doc reference)
//! - `server/queue/queue_service.py` (ported below)
//!
//! Port behavior, do not redesign. Frozen contracts:
//! - Job kind `trio-assessment`, version 1.
//! - Job id deterministic: `trio-<sha256(product + "\0" + timestamp + "\0" + frame bytes)[:32]>`
//! - Queue semantics: claim = SET NX lease with heartbeat; result written once.

use std::collections::HashSet;

use base64::{engine::general_purpose::STANDARD as B64, Engine as _};
use serde_json::Value;
use sha2::{Digest, Sha256};

/// Product ids from `js/products.js` — the source of truth.
/// Mirrors `trio_repo.product_ids()` without spawning node.
pub fn product_ids() -> HashSet<String> {
    ["vigiles".to_string(), "ignis".to_string(), "medicus".to_string()]
        .into_iter()
        .collect()
}

/// Deterministic job id: `trio-<sha256(product\0timestamp\0frame)[:32]>`.
/// Mirrors `buildQueueJob` in `server/queue.mjs` and `python_job_id` in tests.
pub fn deterministic_job_id(product: &str, timestamp: &str, frame: &[u8]) -> String {
    let mut h = Sha256::new();
    h.update(product.as_bytes());
    h.update([0u8]);
    h.update(timestamp.as_bytes());
    h.update([0u8]);
    h.update(frame);
    let digest = hex::encode(h.finalize());
    format!("trio-{}", &digest[..32])
}

/// Validate a trio-assessment v1 envelope.
/// Returns `None` when fileable, or an error string (mirrors
/// `queue_service.validate_envelope` returning an error string).
pub fn validate_envelope(env: &Value, products: &HashSet<String>) -> Option<String> {
    if !env.is_object() {
        return Some("envelope is not a JSON object".to_string());
    }
    if env.get("version").and_then(Value::as_u64) != Some(1)
        || env.get("kind").and_then(Value::as_str) != Some("trio-assessment")
    {
        return Some("not a trio-assessment v1 envelope".to_string());
    }
    match env.get("id").and_then(Value::as_str) {
        Some(s) if !s.is_empty() => {}
        _ => return Some("envelope has no job id".to_string()),
    }
    let product = env.get("product").and_then(Value::as_str).unwrap_or("");
    if !products.contains(product) {
        return Some(format!("unknown product {product:?}"));
    }
    match env.get("timestamp").and_then(Value::as_str) {
        Some(s) if !s.is_empty() => {}
        _ => return Some("envelope has no timestamp".to_string()),
    }
    let image = match env.get("image") {
        Some(v) if v.is_object() => v,
        _ => return Some("envelope has no image object".to_string()),
    };
    let data_url = image.get("dataUrl").and_then(Value::as_str).unwrap_or("");
    if !data_url.starts_with("data:image/jpeg;base64,") {
        return Some("image.dataUrl is not a JPEG data URL".to_string());
    }
    let b64part = data_url.splitn(2, ',').nth(1).unwrap_or("");
    // Python uses validate=True; reject whitespace-tolerant junk by
    // decoding strictly (no whitespace allowed in our path).
    let raw = match B64.decode(b64part.trim_end()) {
        Ok(b) => b,
        Err(_) => return Some("image.dataUrl does not base64-decode".to_string()),
    };
    if image.get("byteLength").and_then(Value::as_u64) != Some(raw.len() as u64) {
        return Some("image.byteLength does not match the decoded frame".to_string());
    }
    let hex_digest = hex::encode(Sha256::digest(&raw));
    if image.get("sha256").and_then(Value::as_str) != Some(hex_digest.as_str()) {
        return Some("image.sha256 does not match the decoded frame".to_string());
    }
    None
}

/// Health payload shape for `GET /health`.
pub fn health_payload(
    store_name: &str,
    store_fallback: bool,
    namespace: &str,
    result_prefix: &str,
) -> Value {
    serde_json::json!({
        "ok": true,
        "service": "trio-queue",
        "store": store_name,
        "store_fallback": store_fallback,
        "namespace": namespace,
        "result_prefix": result_prefix,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use sha2::{Digest, Sha256};

    fn frame() -> Vec<u8> {
        (0..=255u8).cycle().take(1024).collect()
    }

    fn node_like_envelope(frame: &[u8]) -> Value {
        let product = "ignis";
        let timestamp = "2026-10-30T06:00:00.000Z";
        let id = deterministic_job_id(product, timestamp, frame);
        serde_json::json!({
            "version": 1,
            "kind": "trio-assessment",
            "id": id,
            "product": product,
            "timestamp": timestamp,
            "image": {
                "mediaType": "image/jpeg",
                "byteLength": frame.len(),
                "sha256": hex::encode(Sha256::digest(frame)),
                "dataUrl": format!("data:image/jpeg;base64,{}", B64.encode(frame)),
            }
        })
    }

    #[test]
    fn test_node_built_envelope_verifies() {
        let f = frame();
        let env = node_like_envelope(&f);
        assert_eq!(validate_envelope(&env, &product_ids()), None);
        let expect = deterministic_job_id("ignis", "2026-10-30T06:00:00.000Z", &f);
        assert_eq!(env["id"].as_str().unwrap(), expect);
    }

    #[test]
    fn test_tampered_byte_length_refused() {
        let f = frame();
        let mut env = node_like_envelope(&f);
        let n = env["image"]["byteLength"].as_u64().unwrap() + 1;
        env["image"]["byteLength"] = serde_json::json!(n);
        let err = validate_envelope(&env, &product_ids()).unwrap();
        assert!(err.contains("byteLength"), "{err}");
    }

    #[test]
    fn test_tampered_sha256_refused() {
        let f = frame();
        let mut env = node_like_envelope(&f);
        env["image"]["sha256"] = serde_json::json!("0".repeat(64));
        let err = validate_envelope(&env, &product_ids()).unwrap();
        assert!(err.contains("sha256"), "{err}");
    }

    #[test]
    fn test_unknown_product_refused() {
        let f = frame();
        let mut env = node_like_envelope(&f);
        env["product"] = serde_json::json!("nope");
        let err = validate_envelope(&env, &product_ids()).unwrap();
        assert!(err.contains("unknown product"), "{err}");
    }

    #[test]
    fn test_wrong_kind_refused() {
        let f = frame();
        let mut env = node_like_envelope(&f);
        env["kind"] = serde_json::json!("something-else");
        assert!(validate_envelope(&env, &product_ids()).is_some());
    }

    #[test]
    fn test_health_names_fallback_store_honestly() {
        let h = health_payload("local-sqlite-FALLBACK", true, "trio-test-http", "trio");
        assert_eq!(h["ok"], true);
        assert_eq!(h["store"], "local-sqlite-FALLBACK");
        assert_eq!(h["store_fallback"], true);
    }
}
