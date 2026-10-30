//! Port of `os/intel/trust.py` — OS-112 signed-job trust gate.
//!
//! Before a local agent may claim a job, the overseer verifies the
//! HMAC-SHA256 v2 signature against the local trust list. Check order:
//! 1. no id / non-dict -> no decision, no record. 2. only open jobs
//! judged (claimed/done past the gate; refused stays refused via
//! dedupe). 3. no signature -> "signature absent". 4. non-v2 ->
//! "legacy v1 signature, v2 required" (v1 transplantable). 5. kid
//! outside trust list -> "untrusted signer" (checked before crypto).
//! 6. bad recompute / past expiry -> "signature bad" / "signature
//! expired" (v2 binds job id + kid + timestamps + nonce). Badges clamp
//! to `allowed_badges`, every drop named; missing policy passes through
//! with `badge_policy="unset"` (OS-115 owed). Dedupe
//! `trust-refusal:<job>` keeps one record across ticks. Judgment only:
//! never moves claims/writes/posts; a nick is never authority.

use std::collections::HashMap;

#[derive(Debug, Clone, PartialEq)]
pub struct JobInput {
    pub id: Option<String>,
    pub status: String,
    pub kid: Option<String>,
    pub sig_version: Option<u32>,
    pub signature: Option<String>,
    pub body: String,
    pub nonce: Option<String>,
    pub issued_at: Option<i64>,
    pub expires_at: Option<i64>,
    pub badge_claims: Vec<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct TrustList {
    pub trusted_kids: Vec<String>,
    pub allowed_badges: Option<Vec<String>>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Decision {
    pub claimable: bool,
    pub reason: Option<String>,
    pub kept_badges: Vec<String>,
    pub dropped_badges: Vec<String>,
    pub badge_policy: String, // "set" | "unset"
}

/// Toy HMAC-SHA256 stand-in: same verify-before-trust order as the
/// Python (`hmac.compare_digest`); gate-2 re-verifies with real HMAC.
/// Noted, not redesigned: must match Python before PORTED.
pub fn recompute_sig(key: &str, job_id: &str, kid: &str, body: &str, nonce: &str, issued_at: i64) -> String {
    let mut h: u64 = 0xcbf29ce484222325;
    for b in key
        .as_bytes()
        .iter()
        .chain(job_id.as_bytes())
        .chain(kid.as_bytes())
        .chain(body.as_bytes())
        .chain(nonce.as_bytes())
        .chain(issued_at.to_string().as_bytes())
    {
        h ^= *b as u64;
        h = h.wrapping_mul(0x100000001b3);
    }
    format!("v2:{h:016x}")
}

/// Cryptography half: recompute check + expiry. `None` = verifies.
pub fn verify_signature(job: &JobInput, keyring: &HashMap<String, String>, now: i64) -> Option<String> {
    let kid = job.kid.clone()?;
    let key = keyring.get(&kid)?;
    let want = recompute_sig(
        key,
        job.id.as_deref().unwrap_or(""),
        &kid,
        &job.body,
        job.nonce.as_deref().unwrap_or(""),
        job.issued_at.unwrap_or(0),
    );
    if Some(&want) != job.signature.as_ref() {
        return Some("signature bad".to_string());
    }
    if job.expires_at.is_some_and(|e| e <= now) {
        return Some("signature expired".to_string());
    }
    None
}

/// Full claim decision. `None` = no decision (absent subject / not open).
pub fn claim_decision(
    job: &JobInput,
    trust: &TrustList,
    keyring: &HashMap<String, String>,
    now: i64,
) -> Option<Decision> {
    let id = job.id.clone().filter(|s| !s.is_empty())?;
    let _ = id;
    if job.status != "open" {
        return None;
    }
    let refuse = |reason: &str, kept: Vec<String>, dropped: Vec<String>, policy: &str| {
        Some(Decision {
            claimable: false,
            reason: Some(reason.to_string()),
            kept_badges: kept,
            dropped_badges: dropped,
            badge_policy: policy.to_string(),
        })
    };
    // badges clamp (computed for every refusal record too)
    let (kept, dropped, policy) = match &trust.allowed_badges {
        Some(allowed) => {
            let kept: Vec<String> = job.badge_claims.iter().filter(|b| allowed.contains(b)).cloned().collect();
            let dropped: Vec<String> = job.badge_claims.iter().filter(|b| !allowed.contains(b)).cloned().collect();
            (kept, dropped, "set".to_string())
        }
        None => (job.badge_claims.clone(), Vec::new(), "unset".to_string()),
    };
    if job.signature.is_none() {
        return refuse("signature absent", kept, dropped, &policy);
    }
    if job.sig_version != Some(2) {
        return refuse("legacy v1 signature, v2 required", kept, dropped, &policy);
    }
    let kid = job.kid.clone().unwrap_or_default();
    if !trust.trusted_kids.contains(&kid) {
        return refuse("untrusted signer", kept, dropped, &policy);
    }
    if let Some(problem) = verify_signature(job, keyring, now) {
        return refuse(&problem, kept, dropped, &policy);
    }
    Some(Decision { claimable: true, reason: None, kept_badges: kept, dropped_badges: dropped, badge_policy: policy })
}

/// One tick: refusal records for open jobs lacking a `trust-refusal:<id>`
/// entry already in the journal.
pub fn trust_tick(
    jobs: &[JobInput],
    trust: &TrustList,
    keyring: &HashMap<String, String>,
    journal_dedupe_keys: &[String],
    now: i64,
) -> Vec<TrustRecord> {
    let mut out = Vec::new();
    for job in jobs {
        let Some(d) = claim_decision(job, trust, keyring, now) else { continue };
        if d.claimable {
            continue;
        }
        let id = job.id.clone().unwrap_or_default();
        let key = format!("trust-refusal:{id}");
        if journal_dedupe_keys.contains(&key) || out.iter().any(|r: &TrustRecord| r.dedupe_key == key) {
            continue;
        }
        out.push(TrustRecord {
            dedupe_key: key,
            job_id: id,
            reason: d.reason.clone().unwrap_or_default(),
            dropped_badges: d.dropped_badges.clone(),
        });
    }
    out
}

#[derive(Debug, Clone, PartialEq)]
pub struct TrustRecord {
    pub dedupe_key: String,
    pub job_id: String,
    pub reason: String,
    pub dropped_badges: Vec<String>,
}

pub fn refusal_note(job_id: &str, d: &Decision) -> Option<String> {
    if d.claimable {
        return None;
    }
    Some(format!("Job {job_id} refused at claim: {}.", d.reason.clone().unwrap_or_default()))
}

pub fn trust_brief_lines(records: &[TrustRecord]) -> Vec<String> {
    records.iter().map(|r| format!("Trust refusal {}: {}", r.job_id, r.reason)).collect()
}

#[derive(Debug, Clone, PartialEq)]
pub struct TrustEvent {
    pub kind: String,
    pub job_id: String,
    pub detail: String,
}

/// Hana OS-117 federation trust-event shape.
pub fn trust_events(records: &[TrustRecord], machine: &str) -> Vec<TrustEvent> {
    records
        .iter()
        .map(|r| TrustEvent {
            kind: "refusal".to_string(),
            job_id: format!("{machine}:{}", r.job_id),
            detail: r.reason.clone(),
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn open_job() -> JobInput {
        JobInput {
            id: Some("j".into()),
            status: "open".into(),
            kid: Some("crew-a".into()),
            sig_version: Some(2),
            signature: None,
            body: "work".into(),
            nonce: Some("n".into()),
            issued_at: Some(100),
            expires_at: Some(9999),
            badge_claims: vec!["agent".into(), "weird".into()],
        }
    }
    fn trust() -> TrustList {
        TrustList { trusted_kids: vec!["crew-a".into()], allowed_badges: Some(vec!["agent".into()]) }
    }
    fn keyring() -> HashMap<String, String> {
        HashMap::from([("crew-a".into(), "s3cret".into())])
    }
    fn signed() -> JobInput {
        let mut j = open_job();
        j.signature = Some(recompute_sig("s3cret", "j", "crew-a", "work", "n", 100));
        j
    }

    #[test]
    fn check_order_absent_before_crypto() {
        let mut j = signed();
        j.signature = None;
        let d = claim_decision(&j, &trust(), &keyring(), 200).unwrap();
        assert_eq!(d.reason.as_deref(), Some("signature absent"));
    }
    #[test]
    fn legacy_v1_refused() {
        let mut j = signed();
        j.sig_version = Some(1);
        let d = claim_decision(&j, &trust(), &keyring(), 200).unwrap();
        assert!(d.reason.as_deref().unwrap().contains("v1"));
    }
    #[test]
    fn untrusted_kid_before_crypto() {
        let mut j = signed();
        j.kid = Some("stranger".into());
        let t = TrustList { trusted_kids: vec!["crew-a".into()], allowed_badges: Some(vec!["agent".into()]) };
        let d = claim_decision(&j, &t, &HashMap::from([("stranger".into(), "k".into())]), 200).unwrap();
        assert_eq!(d.reason.as_deref(), Some("untrusted signer"));
    }
    #[test]
    fn trusted_passes_with_clamped_badges() {
        let d = claim_decision(&signed(), &trust(), &keyring(), 200).unwrap();
        assert!(d.claimable);
        assert_eq!(d.kept_badges, vec!["agent".to_string()]);
        assert_eq!(d.dropped_badges, vec!["weird".to_string()]);
    }
    #[test]
    fn unset_policy_passes_through() {
        let t = TrustList { trusted_kids: vec!["crew-a".into()], allowed_badges: None };
        let d = claim_decision(&signed(), &t, &keyring(), 200).unwrap();
        assert!(d.claimable && d.badge_policy == "unset");
    }
    #[test]
    fn nick_is_never_authority() {
        // familiar nick + untrusted signature == stranger
        let mut j = signed();
        j.kid = Some("milo".into());
        let t = TrustList { trusted_kids: vec!["crew-a".into()], allowed_badges: Some(vec!["agent".into()]) };
        assert!(!claim_decision(&j, &t, &keyring(), 200).unwrap().claimable);
    }
}
