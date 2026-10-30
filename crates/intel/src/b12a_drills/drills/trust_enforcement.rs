//! Port of `os/intel/drills/trust_enforcement.py` —
//! OS-112 trust enforcement drill (Milo).
//!
//! A fixture room with a trusted crew job, an unsigned job,
//! an untrusted-kid job, a transplanted-signature job, an
//! expired job, a legacy v1 job, and a job posted under a
//! spoofed crew nick. Signatures are real HMAC-SHA256 v2
//! signatures computed with jobs._sign_job_v2 (the
//! `JobsSign` seat, B16) over fixture-only secrets derived
//! from labels via this workspace's own SHA-256 — never
//! real crew keys, and no keyring file is read or written.
//! The trust judgments ride the `Trust` trait (B14). The
//! no-push phase reads the trust module's source text,
//! supplied by the caller (the source drill reads
//! intel/trust.py from disk).

use super::DrillOutcome;
use crate::b12a_drills::deps::{JobsSign, Trust};
use crate::b12a_drills::sha256::sha256_hex;
use crate::b12a_drills::value::Value;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub const NOW: i64 = 100000;

/// Fixture-only secrets, derived from labels (hex of the
/// raw SHA-256 digest bytes).
pub fn trusted_secret() -> String {
    sha256_hex(b"os-112-fixture-crew-a")
}
pub fn untrusted_secret() -> String {
    sha256_hex(b"os-112-fixture-outsider")
}

pub fn trust_config() -> Value {
    Value::obj(vec![
        (
            "trusted_kids",
            Value::List(vec![Value::s("crew-a")]),
        ),
        ("allowed_badges", Value::List(vec![Value::s("agent")])),
    ])
}

pub fn keyring() -> Vec<(String, String)> {
    vec![("crew-a".to_string(), trusted_secret())]
}

/// The drill's `base_job()` — overrides applied last.
pub fn base_job(job_id: &str, overrides: Vec<(&str, Value)>) -> Value {
    let mut record = Value::obj(vec![
        ("id", Value::s(job_id)),
        ("title", Value::s(&format!("Fixture job {}", job_id))),
        ("status", Value::s("open")),
        ("spec", Value::s("Do the fixture thing.")),
        ("accept", Value::s("Fixture output exists.")),
        ("branch", Value::s("")),
        ("base", Value::s("")),
        ("room", Value::s("fixture-room")),
        ("created_at", Value::s("90000")),
        ("expires_at", Value::s("")),
        ("nonce", Value::s(&format!("nonce-{}", job_id))),
        ("machine", Value::s("machine-a")),
        ("created_by", Value::s("pax")),
        ("badge_claims", Value::List(vec![Value::s("agent")])),
    ]);
    for (key, value) in overrides {
        record.set(key, value);
    }
    record
}

/// The drill's `sign()` — the v2 signature over the signed
/// field set, in the signed order.
pub fn sign(signer: &dyn JobsSign, job: &Value, secret_hex: &str) -> String {
    let fields = Value::obj(
        [
            "title",
            "accept",
            "branch",
            "base",
            "room",
            "created_at",
            "expires_at",
            "nonce",
        ]
        .iter()
        .map(|key| (*key, job.get(key)))
        .collect::<Vec<(&str, Value)>>(),
    );
    signer.sign_job_v2(
        secret_hex,
        &job.get("id").py_str(),
        &job.get("sig_kid").py_str(),
        &fields,
        &job.get("spec").py_str(),
    )
}

pub fn trusted_job(signer: &dyn JobsSign) -> Value {
    let mut job = base_job(
        "1",
        vec![
            ("sig_kid", Value::s("crew-a")),
            (
                "badge_claims",
                Value::List(vec![Value::s("agent"), Value::s("driver")]),
            ),
        ],
    );
    let sig = sign(signer, &job, &trusted_secret());
    job.set("sig", Value::s(&sig));
    job.set("sig_v", Value::s("2"));
    job
}

fn phase(name: &str, result: Result<String, String>, phases: &mut Vec<PhaseResult>, lines: &mut Vec<String>) -> bool {
    match result {
        Ok(pass_line) => {
            phases.push(PhaseResult::pass(name, ""));
            lines.push(pass_line);
            true
        }
        Err(fail_line) => {
            phases.push(PhaseResult::fail(name, fail_line.clone()));
            lines.push(fail_line);
            false
        }
    }
}

fn decide(trust: &dyn Trust, job: &Value) -> (String, Value) {
    let result = trust.verify_signature(job, &keyring(), NOW);
    let decision = trust.claim_decision(job, &trust_config(), &result);
    (result, decision)
}

fn phase_trusted(trust: &dyn Trust, signer: &dyn JobsSign) -> Result<String, String> {
    let job = trusted_job(signer);
    let (result, decision) = decide(trust, &job);
    if result != "OK" || decision.get("claimable") != Value::Bool(true) {
        return Err(format!(
            "trusted: FAIL: trusted v2 job not claimable: {} {}",
            result,
            decision.py_repr()
        ));
    }
    if decision.get("allowed_badges") != Value::List(vec![Value::s("agent")])
        || decision.get("dropped_badges") != Value::List(vec![Value::s("driver")])
    {
        return Err(format!(
            "trusted: FAIL: badge clamp wrong: {}",
            decision.py_repr()
        ));
    }
    Ok("trusted: trusted v2 job claimable, driver badge dropped and named: PASS".to_string())
}

fn phase_unsigned(trust: &dyn Trust) -> Result<String, String> {
    let job = base_job("2", vec![("sig_kid", Value::s("crew-a"))]);
    let decision = trust.claim_decision(&job, &trust_config(), "UNSIGNED");
    if decision.get("claimable") == Value::Bool(true)
        || decision.get("reason").as_str() != Some("signature absent")
    {
        return Err(format!("unsigned: FAIL: {}", decision.py_repr()));
    }
    Ok("unsigned: refused, reason signature absent: PASS".to_string())
}

fn phase_untrusted(trust: &dyn Trust, signer: &dyn JobsSign) -> Result<String, String> {
    let mut job = base_job("3", vec![("sig_kid", Value::s("crew-x"))]);
    let sig = sign(signer, &job, &untrusted_secret());
    job.set("sig", Value::s(&sig));
    job.set("sig_v", Value::s("2"));
    let (result, decision) = decide(trust, &job);
    if decision.get("claimable") == Value::Bool(true)
        || decision.get("reason").as_str() != Some("untrusted signer")
    {
        return Err(format!(
            "untrusted: FAIL: {} {}",
            result,
            decision.py_repr()
        ));
    }
    Ok("untrusted: correctly signed by an untrusted kid refused, reason untrusted signer: PASS".to_string())
}

fn phase_transplant(trust: &dyn Trust, signer: &dyn JobsSign) -> Result<String, String> {
    let mut donor = base_job("9", vec![("sig_kid", Value::s("crew-a"))]);
    let donor_sig = sign(signer, &donor, &trusted_secret());
    donor.set("sig", Value::s(&donor_sig));
    let mut job = base_job("10", vec![("sig_kid", Value::s("crew-a"))]);
    job.set("sig", donor.get("sig"));
    job.set("sig_v", Value::s("2"));
    let (result, decision) = decide(trust, &job);
    if result != "BAD"
        || decision.get("claimable") == Value::Bool(true)
        || decision.get("reason").as_str() != Some("signature bad")
    {
        return Err(format!(
            "transplant: FAIL: {} {}",
            result,
            decision.py_repr()
        ));
    }
    Ok("transplant: signature lifted from job 9 refused on job 10, reason signature bad: PASS".to_string())
}

fn phase_expired(trust: &dyn Trust, signer: &dyn JobsSign) -> Result<String, String> {
    let mut job = base_job(
        "4",
        vec![
            ("sig_kid", Value::s("crew-a")),
            ("expires_at", Value::s("99999")),
        ],
    );
    let sig = sign(signer, &job, &trusted_secret());
    job.set("sig", Value::s(&sig));
    job.set("sig_v", Value::s("2"));
    let (result, decision) = decide(trust, &job);
    if result != "EXPIRED"
        || decision.get("claimable") == Value::Bool(true)
        || decision.get("reason").as_str() != Some("signature expired")
    {
        return Err(format!(
            "expired: FAIL: {} {}",
            result,
            decision.py_repr()
        ));
    }
    Ok("expired: refused, reason signature expired: PASS".to_string())
}

fn phase_legacy(trust: &dyn Trust) -> Result<String, String> {
    let job = base_job(
        "5",
        vec![
            ("sig_kid", Value::s("crew-a")),
            ("sig", Value::s("deadbeef")),
            ("sig_v", Value::s("1")),
        ],
    );
    let decision = trust.claim_decision(&job, &trust_config(), "OK");
    if decision.get("claimable") == Value::Bool(true)
        || decision.get("reason").as_str() != Some("legacy v1 signature, v2 required")
    {
        return Err(format!("legacy: FAIL: {}", decision.py_repr()));
    }
    Ok("legacy: v1 job refused, reason legacy v1 signature, v2 required: PASS".to_string())
}

fn phase_spoofed_nick(trust: &dyn Trust, signer: &dyn JobsSign) -> Result<String, String> {
    let mut job = base_job(
        "6",
        vec![
            ("sig_kid", Value::s("crew-x")),
            ("created_by", Value::s("milo")),
        ],
    );
    let sig = sign(signer, &job, &untrusted_secret());
    job.set("sig", Value::s(&sig));
    job.set("sig_v", Value::s("2"));
    let (result, decision) = decide(trust, &job);
    if decision.get("claimable") == Value::Bool(true)
        || decision.get("reason").as_str() != Some("untrusted signer")
    {
        return Err(format!(
            "spoofed-nick: FAIL: {} {}",
            result,
            decision.py_repr()
        ));
    }
    Ok("spoofed-nick: familiar nick, untrusted signature refused: PASS".to_string())
}

fn phase_tick(trust: &dyn Trust, signer: &dyn JobsSign) -> Result<String, String> {
    let mut jobs_list = vec![
        trusted_job(signer),
        base_job("2", vec![("sig_kid", Value::s("crew-a"))]),
        base_job("3", vec![("sig_kid", Value::s("crew-x"))]),
    ];
    let sig3 = sign(signer, &jobs_list[2], &untrusted_secret());
    jobs_list[2].set("sig", Value::s(&sig3));
    jobs_list[2].set("sig_v", Value::s("2"));
    let snapshot = Value::obj(vec![
        ("jobs", Value::List(jobs_list.clone())),
        ("trust", trust_config()),
    ]);
    let before = snapshot.clone();
    let records = trust.trust_tick(&snapshot, &[], NOW, &keyring());
    if records.len() != 2 {
        return Err(format!(
            "tick: FAIL: expected 2 refusal records, got {}",
            records.len()
        ));
    }
    let mut reasons: Vec<String> = records.iter().map(|r| r.get("reason").py_str()).collect();
    reasons.sort();
    if reasons
        != vec![
            "signature absent".to_string(),
            "untrusted signer".to_string(),
        ]
    {
        return Err(format!("tick: FAIL: reasons wrong: {:?}", reasons));
    }
    let second = trust.trust_tick(&snapshot, &records, NOW, &keyring());
    if !second.is_empty() {
        return Err(format!(
            "tick: FAIL: second tick journaled {}",
            second.len()
        ));
    }
    if snapshot != before {
        return Err("tick: FAIL: tick mutated its inputs".to_string());
    }
    let real = trust.claim_decision(&jobs_list[1], &trust_config(), "UNSIGNED");
    let note = trust.refusal_note(&jobs_list[1], &real);
    if note.as_deref().map(|n| !n.contains("signature absent")).unwrap_or(true) {
        return Err(format!(
            "tick: FAIL: refusal note wrong: {}",
            note.as_ref().map(|n| n.clone()).unwrap_or_else(|| "None".to_string())
        ));
    }
    let lines = trust.trust_brief_lines(&records);
    let events = trust.trust_events(&records);
    if lines.len() != 2
        || events.len() != 2
        || events[0].get("kind").as_str() != Some("refusal")
    {
        return Err(format!(
            "tick: FAIL: brief/events wrong: {:?} {}",
            lines,
            Value::List(events).py_repr()
        ));
    }
    Ok("tick: 2 refusal records, trusted job silent, second tick silent, inputs immutable, brief and federation events render: PASS".to_string())
}

fn phase_no_push(trust_source: &str) -> Result<String, String> {
    if trust_source.contains("import push")
        || trust_source.contains("bus_push")
        || trust_source.contains("push.py")
    {
        return Err("no-push: FAIL: trust module carries a push path".to_string());
    }
    Ok("no-push: refusal is journal only, no push path, Dale contacted at no step: PASS".to_string())
}

/// The drill's main(): all nine phases, then the summary.
/// `trust_source` is the B14 trust module's source text
/// (the no-push phase's read of intel/trust.py).
pub fn run(trust: &dyn Trust, signer: &dyn JobsSign, trust_source: &str) -> DrillOutcome {
    let mut phases: Vec<PhaseResult> = Vec::new();
    let mut lines: Vec<String> = Vec::new();
    let mut ok = true;
    ok &= phase("trusted", phase_trusted(trust, signer), &mut phases, &mut lines);
    ok &= phase("unsigned", phase_unsigned(trust), &mut phases, &mut lines);
    ok &= phase("untrusted", phase_untrusted(trust, signer), &mut phases, &mut lines);
    ok &= phase("transplant", phase_transplant(trust, signer), &mut phases, &mut lines);
    ok &= phase("expired", phase_expired(trust, signer), &mut phases, &mut lines);
    ok &= phase("legacy", phase_legacy(trust), &mut phases, &mut lines);
    ok &= phase("spoofed-nick", phase_spoofed_nick(trust, signer), &mut phases, &mut lines);
    ok &= phase("tick", phase_tick(trust, signer), &mut phases, &mut lines);
    ok &= phase("no-push", phase_no_push(trust_source), &mut phases, &mut lines);
    lines.push(format!(
        "trust_enforcement: {}",
        if ok { "ALL PHASES PASS" } else { "FAILED" }
    ));
    DrillOutcome {
        report: DrillReport::new("trust_enforcement", phases),
        lines,
    }
}
