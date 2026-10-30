//! Port of `os/intel/drills/trust_negative.py` — OS-114
//! trust negative drill (Milo), at room level.
//!
//! An untrusted machine joins the fixture room and posts a
//! job; the same job is re-posted under a spoofed crew
//! nick. Both attempts are refused by the trusted machine's
//! overseer, logged, and surfaced, and no work is
//! exchanged: zero claims of the hostile jobs by any
//! trusted agent across the test window, and the drill
//! leaves the fixture room clean. A signed variant of the
//! spoof is refused too (decision-level guard). Signatures
//! are real HMAC-SHA256 v2 signatures via the `JobsSign`
//! seat over fixture-only secrets derived from labels.
//! The no-push phase reads the trust module's source and
//! structurally scans this drill's own source — the caller
//! supplies both texts (in the source both are file reads;
//! the AST scan ports as a scan of use-statement roots and
//! file-open path literals, the structural facts the AST
//! walk extracts).

use super::DrillOutcome;
use super::trust_enforcement::{base_job, sign};
use crate::b12a_drills::deps::{JobsSign, Trust};
use crate::b12a_drills::sha256::sha256_hex;
use crate::b12a_drills::value::Value;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub const NOW: i64 = 100000;
pub const ROOM: &str = "fixture-room";
pub const TRUSTED_MACHINE: &str = "machine-trusted";
pub const OUTSIDER_MACHINE: &str = "machine-outsider";
pub const TRUSTED_AGENTS: [&str; 3] = ["milo", "pax", "rowan"];

pub fn trusted_secret() -> String {
    sha256_hex(b"os-114-fixture-crew-a")
}
pub fn outsider_secret() -> String {
    sha256_hex(b"os-114-fixture-outsider")
}

pub fn trust_config() -> Value {
    Value::obj(vec![
        ("trusted_kids", Value::List(vec![Value::s("crew-a")])),
        ("allowed_badges", Value::List(vec![Value::s("agent")])),
    ])
}

pub fn keyring() -> Vec<(String, String)> {
    vec![("crew-a".to_string(), trusted_secret())]
}

/// base_job with this drill's machine default.
fn job(job_id: &str, overrides: Vec<(&str, Value)>) -> Value {
    let mut record = base_job(job_id, vec![]);
    // base_job in trust_enforcement carries machine-a and
    // room fixture-room; this drill's base carries the
    // trusted machine — set before overrides, as the
    // source's own base_job does.
    record.set("machine", Value::s(TRUSTED_MACHINE));
    for (key, value) in overrides {
        record.set(key, value);
    }
    record
}

pub fn control_job(signer: &dyn JobsSign) -> Value {
    let mut j = job("C1", vec![("sig_kid", Value::s("crew-a"))]);
    let sig = sign(signer, &j, &trusted_secret());
    j.set("sig", Value::s(&sig));
    j.set("sig_v", Value::s("2"));
    j
}

pub fn hostile_post(signer: &dyn JobsSign) -> Value {
    let mut j = job(
        "H1",
        vec![
            ("sig_kid", Value::s("crew-x")),
            ("machine", Value::s(OUTSIDER_MACHINE)),
            ("created_by", Value::s("outsider")),
        ],
    );
    let sig = sign(signer, &j, &outsider_secret());
    j.set("sig", Value::s(&sig));
    j.set("sig_v", Value::s("2"));
    j
}

pub fn spoofed_repost() -> Value {
    job(
        "H2",
        vec![
            ("sig_kid", Value::s("crew-a")),
            ("machine", Value::s(OUTSIDER_MACHINE)),
            ("created_by", Value::s("milo")),
        ],
    )
}

pub fn signed_spoof(signer: &dyn JobsSign) -> Value {
    let mut j = job(
        "H3",
        vec![
            ("sig_kid", Value::s("crew-x")),
            ("machine", Value::s(OUTSIDER_MACHINE)),
            ("created_by", Value::s("milo")),
        ],
    );
    let sig = sign(signer, &j, &outsider_secret());
    j.set("sig", Value::s(&sig));
    j.set("sig_v", Value::s("2"));
    j
}

fn decide(trust: &dyn Trust, job: &Value) -> Value {
    let result = trust.verify_signature(job, &keyring(), NOW);
    trust.claim_decision(job, &trust_config(), &result)
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

fn phase_room_setup(trust: &dyn Trust, signer: &dyn JobsSign) -> Result<String, String> {
    let job = control_job(signer);
    let decision = decide(trust, &job);
    if decision.get("claimable") != Value::Bool(true) {
        return Err(format!(
            "room-setup: FAIL: control job not claimable: {}",
            decision.py_repr()
        ));
    }
    let room = Value::obj(vec![
        (
            "machines",
            Value::List(vec![
                Value::s(TRUSTED_MACHINE),
                Value::s(OUTSIDER_MACHINE),
            ]),
        ),
        (
            "agents",
            Value::List(TRUSTED_AGENTS.iter().map(|a| Value::s(a)).collect()),
        ),
    ]);
    if !room
        .get("machines")
        .as_list()
        .map(|m| m.iter().any(|x| x.as_str() == Some(OUTSIDER_MACHINE)))
        .unwrap_or(false)
    {
        return Err("room-setup: FAIL: outsider machine not in room".to_string());
    }
    Ok("room-setup: outsider machine joined the room, trusted control job claimable: PASS".to_string())
}

fn phase_hostile_post(trust: &dyn Trust, signer: &dyn JobsSign) -> Result<String, String> {
    let job = hostile_post(signer);
    let decision = decide(trust, &job);
    if decision.get("claimable") == Value::Bool(true)
        || decision.get("reason").as_str() != Some("untrusted signer")
    {
        return Err(format!("hostile-post: FAIL: {}", decision.py_repr()));
    }
    let note = trust.refusal_note(&job, &decision);
    if note.as_deref().map(|n| !n.contains("untrusted signer")).unwrap_or(true) {
        return Err(format!(
            "hostile-post: FAIL: refusal note wrong: {}",
            note.unwrap_or_else(|| "None".to_string())
        ));
    }
    Ok("hostile-post: outsider job refused, reason untrusted signer: PASS".to_string())
}

fn phase_spoofed_repost(trust: &dyn Trust) -> Result<String, String> {
    let job = spoofed_repost();
    let decision = decide(trust, &job);
    if decision.get("claimable") == Value::Bool(true)
        || decision.get("reason").as_str() != Some("signature absent")
    {
        return Err(format!("spoofed-repost: FAIL: {}", decision.py_repr()));
    }
    let note = trust.refusal_note(&job, &decision);
    if note.as_deref().map(|n| !n.contains("signature absent")).unwrap_or(true) {
        return Err(format!(
            "spoofed-repost: FAIL: refusal note wrong: {}",
            note.unwrap_or_else(|| "None".to_string())
        ));
    }
    Ok("spoofed-repost: spoofed-nick re-post refused, reason signature absent, nick never authority: PASS".to_string())
}

fn phase_signed_spoof_guard(trust: &dyn Trust, signer: &dyn JobsSign) -> Result<String, String> {
    let job = signed_spoof(signer);
    let decision = decide(trust, &job);
    if decision.get("claimable") == Value::Bool(true)
        || decision.get("reason").as_str() != Some("untrusted signer")
    {
        return Err(format!("signed-spoof: FAIL: {}", decision.py_repr()));
    }
    Ok("signed-spoof: spoofed nick with an outsider signature refused too, reason untrusted signer: PASS".to_string())
}

fn phase_test_window(trust: &dyn Trust, signer: &dyn JobsSign) -> Result<String, String> {
    let snapshot = Value::obj(vec![
        (
            "jobs",
            Value::List(vec![
                control_job(signer),
                hostile_post(signer),
                spoofed_repost(),
            ]),
        ),
        ("trust", trust_config()),
    ]);
    let before = snapshot.clone();
    let mut journal: Vec<Value> = Vec::new();
    let hostile_ids = ["H1", "H2"];
    let mut claims: Vec<(String, String)> = Vec::new();
    for tick in 1..=3 {
        let records = trust.trust_tick(&snapshot, &journal, NOW, &keyring());
        journal.extend(records.iter().cloned());
        for agent in TRUSTED_AGENTS {
            if let Some(jobs) = snapshot.get("jobs").as_list() {
                for job in jobs {
                    if hostile_ids.contains(&job.get("id").as_str().unwrap_or("")) {
                        let decision = decide(trust, job);
                        if decision.get("claimable") == Value::Bool(true) {
                            claims.push((job.get("id").py_str(), agent.to_string()));
                        }
                    }
                }
            }
        }
        if tick == 1 && records.len() != 2 {
            return Err(format!(
                "test-window: FAIL: tick 1 journaled {} records, expected 2",
                records.len()
            ));
        }
        if tick > 1 && !records.is_empty() {
            return Err(format!(
                "test-window: FAIL: tick {} journaled {} new records",
                tick,
                records.len()
            ));
        }
    }
    if !claims.is_empty() {
        return Err(format!(
            "test-window: FAIL: hostile jobs claimed: {:?}",
            claims
        ));
    }
    let mut reasons: Vec<String> = journal.iter().map(|r| r.get("reason").py_str()).collect();
    reasons.sort();
    if reasons
        != vec![
            "signature absent".to_string(),
            "untrusted signer".to_string(),
        ]
    {
        return Err(format!(
            "test-window: FAIL: journal reasons wrong: {:?}",
            reasons
        ));
    }
    if snapshot != before {
        return Err("test-window: FAIL: ticks mutated inputs".to_string());
    }
    Ok("test-window: 3 ticks x 3 trusted agents, zero claims of hostile jobs, exactly 2 refusal records, later ticks silent: PASS".to_string())
}

fn phase_surfaced(trust: &dyn Trust, signer: &dyn JobsSign) -> Result<String, String> {
    let snapshot = Value::obj(vec![
        (
            "jobs",
            Value::List(vec![
                control_job(signer),
                hostile_post(signer),
                spoofed_repost(),
            ]),
        ),
        ("trust", trust_config()),
    ]);
    let records = trust.trust_tick(&snapshot, &[], NOW, &keyring());
    let lines = trust.trust_brief_lines(&records);
    let events = trust.trust_events(&records);
    if lines.len() != 2 || events.len() != 2 {
        return Err(format!(
            "surfaced: FAIL: brief/events counts wrong: {:?} {}",
            lines,
            Value::List(events).py_repr()
        ));
    }
    if events
        .iter()
        .any(|e| e.get("machine").as_str() != Some(OUTSIDER_MACHINE))
    {
        return Err(format!(
            "surfaced: FAIL: events name the wrong machine: {}",
            Value::List(events).py_repr()
        ));
    }
    let joined = format!("{}{}", lines[0], lines[1]);
    if !joined.contains("untrusted signer") || !joined.contains("signature absent") {
        return Err(format!(
            "surfaced: FAIL: brief lines miss a reason: {:?}",
            lines
        ));
    }
    Ok("surfaced: both refusals on the brief and the federation feed, naming the outsider machine: PASS".to_string())
}

fn phase_room_clean(trust: &dyn Trust, signer: &dyn JobsSign) -> Result<String, String> {
    // The source's end-state ledgers are empty by
    // construction (nothing in the drill ever records work
    // for a hostile job); the check is kept verbatim.
    let claims: Vec<String> = Vec::new();
    let progress: Vec<String> = Vec::new();
    let artifacts: Vec<String> = Vec::new();
    for job_id in ["H1", "H2", "H3"] {
        if claims.iter().any(|x| x == job_id)
            || progress.iter().any(|x| x == job_id)
            || artifacts.iter().any(|x| x == job_id)
        {
            return Err(format!(
                "room-clean: FAIL: work exchanged for {}",
                job_id
            ));
        }
    }
    let decision = decide(trust, &control_job(signer));
    if decision.get("claimable") != Value::Bool(true) {
        return Err("room-clean: FAIL: control job lost claimability".to_string());
    }
    Ok("room-clean: no claim, progress note, or artifact for any hostile job; control job still claimable: PASS".to_string())
}

/// The structural scan standing in for the source's AST
/// walk: use-statement roots in {requests, socket, redis,
/// upstash}, and file-open calls whose literal path names a
/// token or .config path.
pub fn drill_source_is_clean(source: &str) -> Option<String> {
    for line in source.lines() {
        let trimmed = line.trim_start();
        if let Some(rest) = trimmed.strip_prefix("use ") {
            let root = rest
                .split(|c| c == ':' || c == ';' || c == ' ')
                .next()
                .unwrap_or("");
            if ["requests", "socket", "redis", "upstash"].contains(&root) {
                return Some(root.to_string());
            }
        }
        if trimmed.contains("File::open(") || trimmed.contains("fs::read(") {
            if trimmed.contains("token") || trimmed.contains(".config") {
                return Some("credential path".to_string());
            }
        }
    }
    None
}

fn phase_no_push_no_live(trust_source: &str, drill_source: &str) -> Result<String, String> {
    if trust_source.contains("import push")
        || trust_source.contains("bus_push")
        || trust_source.contains("push.py")
    {
        return Err("no-push: FAIL: trust module carries a push path".to_string());
    }
    if let Some(what) = drill_source_is_clean(drill_source) {
        return Err(format!(
            "no-push: FAIL: drill imports live transport or opens a credential path: {}",
            what
        ));
    }
    Ok("no-push: refusal is journal only, no push path, no live bus, no keyring file read: PASS".to_string())
}

/// The drill's main(): all eight phases, then the summary.
pub fn run(
    trust: &dyn Trust,
    signer: &dyn JobsSign,
    trust_source: &str,
    drill_source: &str,
) -> DrillOutcome {
    let mut phases: Vec<PhaseResult> = Vec::new();
    let mut lines: Vec<String> = Vec::new();
    let mut ok = true;
    ok &= phase("room-setup", phase_room_setup(trust, signer), &mut phases, &mut lines);
    ok &= phase("hostile-post", phase_hostile_post(trust, signer), &mut phases, &mut lines);
    ok &= phase("spoofed-repost", phase_spoofed_repost(trust), &mut phases, &mut lines);
    ok &= phase("signed-spoof", phase_signed_spoof_guard(trust, signer), &mut phases, &mut lines);
    ok &= phase("test-window", phase_test_window(trust, signer), &mut phases, &mut lines);
    ok &= phase("surfaced", phase_surfaced(trust, signer), &mut phases, &mut lines);
    ok &= phase("room-clean", phase_room_clean(trust, signer), &mut phases, &mut lines);
    ok &= phase(
        "no-push",
        phase_no_push_no_live(trust_source, drill_source),
        &mut phases,
        &mut lines,
    );
    lines.push(format!(
        "trust_negative: {}",
        if ok { "ALL PHASES PASS" } else { "FAILED" }
    ));
    DrillOutcome {
        report: DrillReport::new("trust_negative", phases),
        lines,
    }
}
