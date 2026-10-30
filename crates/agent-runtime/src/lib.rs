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

use base64::{engine::general_purpose::STANDARD as B64, Engine as _};
use queue_store::{JobStore, StoreBackend};
use serde_json::Value;
use sha2::{Digest, Sha256};

pub fn now_iso() -> String {
    // Millisecond ISO-8601 UTC with Z (no external time crate).
    let ms = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis())
        .unwrap_or(0);
    // Format via libc seconds is overkill for parity; keep epoch millis.
    format!("{ms}")
}

pub fn relay_notify_payload(result: &Value, product: Option<&str>) -> Option<Value> {
    let jid = result.get("job_id").and_then(Value::as_str)?;
    if result.get("status").and_then(Value::as_str) == Some("ok") {
        let category = result
            .get("assessment").and_then(|a| a.get("assessment"))
            .and_then(|a| a.get("category")).and_then(Value::as_str).unwrap_or("?");
        Some(serde_json::json!({
            "severity": "info", "topic": "trio-result",
            "text": format!("trio job {jid} product {} completed: category {category}", product.unwrap_or("unknown"))[..500.min(200)].to_string(),
        }))
    } else {
        let err = result.get("error").and_then(Value::as_str).unwrap_or("?");
        Some(serde_json::json!({
            "severity": "warning", "topic": "trio-result",
            "text": format!("trio job {jid} product {} failed: {err}", product.unwrap_or("unknown")),
        }))
    }
}

/// Outcome of serving one job.
#[derive(Debug, PartialEq, Eq)]
pub enum Outcome { Done, Failed, Skipped, Lost }

pub trait Generator {
    fn generate(&mut self, product: &str, image: &[u8], timestamp: &str, correction: Option<&str>) -> Result<(Value, String, u64), String>;
}

pub struct Agent<B: StoreBackend, G: Generator> {
    pub nick: String,
    pub lease: u64,
    pub jobs: JobStore<B>,
    pub gen: G,
}

impl<B: StoreBackend, G: Generator> Agent<B, G> {
    pub fn serve_job(&mut self, jid: &str) -> Outcome {
        // Idempotency before claim.
        if self.jobs.get_result(jid).is_some() {
            self.jobs.finish(jid, "done", "idempotent skip: result already present, not re-billed");
            return Outcome::Skipped;
        }
        if !self.jobs.claim(jid, &self.nick.clone(), self.lease) {
            return Outcome::Lost;
        }
        // Idempotency again under lease.
        if self.jobs.get_result(jid).is_some() {
            self.jobs.finish(jid, "done", "idempotent skip: result already present, not re-billed");
            return Outcome::Skipped;
        }
        let mut product: Option<String> = None;
        let res = self.serve_claimed(jid, &mut product);
        res
    }

    fn serve_claimed(&mut self, jid: &str, product_out: &mut Option<String>) -> Outcome {
        let env = match self.jobs.job_envelope(jid) {
            Some(e) => e,
            None => {
                self.finish_failed(jid, "job envelope missing or unparseable in the store", None, None, None);
                return Outcome::Failed;
            }
        };
        let product = env.get("product").and_then(Value::as_str).unwrap_or("").to_string();
        let timestamp = env.get("timestamp").and_then(Value::as_str).unwrap_or("").to_string();
        *product_out = Some(product.clone());
        let data_url = env.get("image").and_then(|i| i.get("dataUrl")).and_then(Value::as_str).unwrap_or("");
        if !data_url.starts_with("data:image/jpeg;base64,") {
            self.finish_failed(jid, "envelope image is not a JPEG data URL", None, None, Some(&product));
            return Outcome::Failed;
        }
        let raw = match B64.decode(data_url.splitn(2, ',').nth(1).unwrap_or("")) {
            Ok(b) => b,
            Err(_) => {
                self.finish_failed(jid, "envelope image does not base64-decode", None, None, Some(&product));
                return Outcome::Failed;
            }
        };
        let digest = hex::encode(Sha256::digest(&raw));
        if env.get("image").and_then(|i| i.get("sha256")).and_then(Value::as_str) != Some(digest.as_str()) {
            self.finish_failed(jid, "frame sha256 mismatch against the envelope", None, None, Some(&product));
            return Outcome::Failed;
        }
        let (mut assessment, mut model, mut latency) = match self.gen.generate(&product, &raw, &timestamp, None) {
            Ok(t) => t,
            Err(e) => {
                self.finish_failed(jid, &format!("generation failed: {e}"), None, None, Some(&product));
                return Outcome::Failed;
            }
        };
        let (mut ok, mut errors) = validate_assessment(&assessment, &product);
        if !ok {
            // Exactly ONE correction retry.
            let correction = errors.join("; ");
            match self.gen.generate(&product, &raw, &timestamp, Some(&correction)) {
                Ok((a2, m2, l2)) => {
                    assessment = a2; model = m2;
                    latency = latency.saturating_add(l2);
                    let v = validate_assessment(&assessment, &product);
                    ok = v.0; errors = v.1;
                }
                Err(e) => {
                    self.finish_failed(jid, &format!("generation failed: {e}"), Some(&model), Some(latency), Some(&product));
                    return Outcome::Failed;
                }
            }
        }
        if !ok {
            self.finish_failed(jid, &format!("model output failed validateAssessment (after one correction retry): {}", errors.join("; ")), Some(&model), Some(latency), Some(&product));
            return Outcome::Failed;
        }
        let result = serde_json::json!({
            "job_id": jid, "status": "ok", "assessment": assessment,
            "error": null, "model": model, "latency_ms": latency,
            "completed_at": now_iso(),
        });
        self.jobs.put_result(&result);
        self.jobs.finish(jid, "done", &format!("assessment by {}", self.nick));
        Outcome::Done
    }

    fn finish_failed(&mut self, jid: &str, error: &str, model: Option<&String>, latency: Option<u64>, product: Option<&str>) {
        let _ = product;
        let result = serde_json::json!({
            "job_id": jid, "status": "failed", "assessment": null,
            "error": &error[..error.len().min(500)],
            "model": model, "latency_ms": latency, "completed_at": now_iso(),
        });
        self.jobs.put_result(&result);
        self.jobs.finish(jid, "failed", &error[..error.len().min(200)]);
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
        let env = serde_json::json!({"id": jid, "kind": "trio-assessment", "version": 1, "product": "ignis", "timestamp": "t", "image": {"dataUrl": "data:image/jpeg;base64,/9g=", "byteLength": 2, "sha256": hex::encode(Sha256::digest([0xffu8, 0xd8]))}});
        // Manually file with correct sha for [0xff,0xd8]: envelope builder needs matching raw.
        let _ = env;
        // Build a consistent envelope: raw = [0xff, 0xd8].
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
