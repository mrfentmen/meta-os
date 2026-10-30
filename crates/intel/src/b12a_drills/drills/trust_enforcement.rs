//! Port of `os/intel/drills/trust_enforcement.py`.
//!
//! Phases on HMAC-signed job records: trusted (fresh signature) passes;
//! unsigned refused; untrusted-key refused; transplanted signature
//! (valid sig, wrong job) refused; expired refused.

use crate::b12a_drills::{DrillReport, PhaseResult};

#[derive(Debug, Clone, PartialEq)]
pub struct SignedJob {
    pub id: String,
    pub body: String,
    pub sig: Option<String>,
    pub key_id: Option<String>,
    pub expires_at: Option<i64>,
}

fn toy_sign(key: &str, body: &str) -> String {
    // Toy HMAC stand-in with the same verify-before-trust order as the
    // Python (hmac.compare_digest); the Mac gate re-verifies with the
    // real keyring. Noted, not redesigned.
    let mut h: u64 = 0xcbf29ce484222325;
    for b in key.as_bytes().iter().chain(body.as_bytes()) {
        h ^= *b as u64;
        h = h.wrapping_mul(0x100000001b3);
    }
    format!("{h:016x}")
}

pub fn base_job(id: &str) -> SignedJob {
    SignedJob { id: id.into(), body: "do work".into(), sig: None, key_id: None, expires_at: None }
}

pub fn sign(job: &SignedJob, key: &str, key_id: &str, now: i64, ttl: i64) -> SignedJob {
    let mut j = job.clone();
    j.sig = Some(toy_sign(key, &job.body));
    j.key_id = Some(key_id.into());
    j.expires_at = Some(now + ttl);
    j
}

pub fn trusted_job(job: &SignedJob, key: &str, trusted_keys: &[String], now: i64) -> bool {
    let Some(sig) = &job.sig else { return false };
    let Some(kid) = &job.key_id else { return false };
    if !trusted_keys.contains(kid) {
        return false;
    }
    if job.expires_at.is_some_and(|e| e <= now) {
        return false;
    }
    &toy_sign(key, &job.body) == sig
}

pub fn run() -> DrillReport {
    let now = 1000;
    let trusted = vec!["k1".to_string()];
    let base = base_job("j");
    let good = sign(&base, "secret", "k1", now, 600);
    let mut transplant = good.clone();
    transplant.id = "other".into();
    transplant.body = "changed".into();
    let mut expired = good.clone();
    expired.expires_at = Some(now - 1);
    let cases = [
        ("phase_trusted", trusted_job(&good, "secret", &trusted, now), true),
        ("phase_unsigned", trusted_job(&base, "secret", &trusted, now), false),
        ("phase_untrusted", trusted_job(&good, "secret", &["zz".to_string()], now), false),
        ("phase_transplant", trusted_job(&transplant, "secret", &trusted, now), false),
        ("phase_expired", trusted_job(&expired, "secret", &trusted, now), false),
    ];
    DrillReport::new(
        "trust_enforcement",
        cases
            .into_iter()
            .map(|(n, got, want)| {
                if got == want {
                    PhaseResult::pass(n, "as expected")
                } else {
                    PhaseResult::fail(n, format!("got {got}, want {want}"))
                }
            })
            .collect(),
    )
}
