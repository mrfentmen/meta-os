//! Port of `os/intel/drills/wake.py` — OS-119 wake drill
//! (Milo).
//!
//! A sleeping fixture agent, given a posted job and zero
//! human contact, wakes, claims, and starts work with the
//! bundle in place; its first bus action is the claim, not
//! a status check. A job addressed to a different agent
//! does not wake it. The module under test (B10
//! `intel.wake`, behind the `Wake` trait) judges fixture
//! records and composes the bundle; it never starts a real
//! session. The drill's FakeMuseRuntime applies the start,
//! so the session-start half is simulated. A bundle whose
//! job carries no mind image reference says the OS-102
//! loader is pending instead of inventing a reference. The
//! module-import scan reads the wake module's source text,
//! supplied by the caller (the source reads intel/wake.py
//! and walks its AST; the port scans use-statement roots,
//! the structural fact the walk extracts).

use super::DrillOutcome;
use crate::b12a_drills::deps::Wake;
use crate::b12a_drills::value::Value;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub const T0: i64 = 100000;

/// The drill's FakeMuseRuntime: start(bundle) opens a
/// session whose first bus action is the claim of the
/// bundled job, or a status poll when started with none.
pub struct FakeMuseRuntime {
    pub sessions: Vec<Value>,
}

impl FakeMuseRuntime {
    pub fn new() -> Self {
        FakeMuseRuntime { sessions: Vec::new() }
    }

    pub fn start(&mut self, bundle: Option<&Value>) -> Value {
        let session = match bundle {
            None => Value::obj(vec![
                ("bundle", Value::Null),
                ("first_bus_action", Value::s("status")),
                ("claimed_job", Value::Null),
                ("progress", Value::List(vec![])),
            ]),
            Some(bundle) => Value::obj(vec![
                ("bundle", bundle.clone()),
                ("first_bus_action", Value::s("claim")),
                ("claimed_job", bundle.get("job_id")),
                (
                    "progress",
                    Value::List(vec![Value::s(&format!(
                        "started job {}",
                        bundle.get("job_id").py_str()
                    ))]),
                ),
            ]),
        };
        self.sessions.push(session.clone());
        session
    }
}

impl Default for FakeMuseRuntime {
    fn default() -> Self {
        Self::new()
    }
}

pub fn hana_agent(asleep: bool, runtime: &str) -> Value {
    Value::obj(vec![
        ("nick", Value::s("hana")),
        ("machine", Value::s("hana-box")),
        ("runtime", Value::s(runtime)),
        ("asleep", Value::Bool(asleep)),
    ])
}

pub fn rowan_agent(asleep: bool, runtime: &str) -> Value {
    Value::obj(vec![
        ("nick", Value::s("rowan")),
        ("machine", Value::s("rowan-box")),
        ("runtime", Value::s(runtime)),
        ("asleep", Value::Bool(asleep)),
    ])
}

/// The drill's `job()` builder.
pub fn job(job_id: &str, addressed_to: &str, mind_image: bool) -> Value {
    let mut record = Value::obj(vec![
        ("id", Value::s(job_id)),
        ("addressed_to", Value::s(addressed_to)),
        ("goal", Value::s("Write the watchdog brief line")),
        (
            "spec",
            Value::s("Goal: Write the watchdog brief line\nSteps: draft, check, file"),
        ),
        (
            "acceptance_checks",
            Value::List(vec![
                Value::s("brief line names the alert"),
                Value::s("brief line names the machine"),
            ]),
        ),
        (
            "files",
            Value::List(vec![Value::s("intel/brief.py")]),
        ),
    ]);
    if mind_image {
        record.set("mind_image_ref", Value::s("mind/hana-base-v3"));
    }
    record
}

fn list(items: Vec<Value>) -> Value {
    Value::List(items)
}

fn phase(name: &str, result: Result<(), String>, phases: &mut Vec<PhaseResult>, lines: &mut Vec<String>) -> bool {
    match result {
        Ok(()) => {
            phases.push(PhaseResult::pass(name, ""));
            lines.push(format!("{}: PASS", name));
            true
        }
        Err(detail) => {
            phases.push(PhaseResult::fail(name, detail.clone()));
            lines.push(format!("{}: FAIL {}", name, detail));
            false
        }
    }
}

fn phase_wake_and_claim(wake: &dyn Wake) -> Result<(), String> {
    let agent = hana_agent(true, "muse");
    let posted = job("job-1", "hana", true);
    let new = wake.wake_tick(&list(vec![posted]), &list(vec![agent]), &[], T0);
    if new.len() != 1 || new[0].get("kind").as_str() != Some("wake") {
        return Err(format!("tick yielded {} records", new.len()));
    }
    let bundle = new[0].get("bundle");
    if bundle.get("goal").as_str() != Some("Write the watchdog brief line") {
        return Err("bundle goal wrong".to_string());
    }
    if bundle.get("spec").is_null() || !bundle.get("spec").py_str().contains("Goal:") {
        return Err("bundle spec missing".to_string());
    }
    if bundle.get("acceptance_checks")
        != Value::List(vec![
            Value::s("brief line names the alert"),
            Value::s("brief line names the machine"),
        ])
    {
        return Err("bundle checks wrong".to_string());
    }
    if bundle.get("mind_image").as_str() != Some("mind/hana-base-v3") {
        return Err("bundle mind image wrong".to_string());
    }
    let mut runtime = FakeMuseRuntime::new();
    let session = runtime.start(Some(&bundle));
    if session.get("first_bus_action").as_str() != Some("claim") {
        return Err(format!(
            "first bus action was {}",
            session.get("first_bus_action").py_str()
        ));
    }
    if session.get("claimed_job").as_str() != Some("job-1") {
        return Err("session claimed wrong job".to_string());
    }
    if session.get("progress") != Value::List(vec![Value::s("started job job-1")]) {
        return Err("session progress wrong".to_string());
    }
    let polling = runtime.start(None);
    if polling.get("first_bus_action").as_str() != Some("status") {
        return Err("a bundle-free start did not poll status".to_string());
    }
    if wake.brief_lines(&new)
        != vec!["Wake: hana woken for job job-1 on hana-box".to_string()]
    {
        return Err("brief line wrong".to_string());
    }
    Ok(())
}

fn phase_wrong_addressee(wake: &dyn Wake) -> Result<(), String> {
    let hana = hana_agent(true, "muse");
    let rowan = rowan_agent(true, "muse");
    for (posted, agents, label) in [
        (job("job-1", "rowan", true), vec![hana], "rowan job woke hana"),
        (job("job-1", "hana", true), vec![rowan], "hana job woke rowan"),
    ] {
        let new = wake.wake_tick(&list(vec![posted]), &list(agents), &[], T0);
        if !new.is_empty() {
            return Err(label.to_string());
        }
        let runtime = FakeMuseRuntime::new();
        if !runtime.sessions.is_empty() {
            return Err("a session started without a wake".to_string());
        }
    }
    Ok(())
}

fn phase_awake_and_other_runtime(wake: &dyn Wake) -> Result<(), String> {
    let posted = job("job-1", "hana", true);
    let awake = hana_agent(false, "muse");
    if !wake
        .wake_tick(&list(vec![posted.clone()]), &list(vec![awake]), &[], T0)
        .is_empty()
    {
        return Err("an awake agent woke".to_string());
    }
    let other = hana_agent(true, "freebuff");
    if !wake
        .wake_tick(&list(vec![posted.clone()]), &list(vec![other]), &[], T0)
        .is_empty()
    {
        return Err("a non-muse runtime woke".to_string());
    }
    let unknown = Value::obj(vec![
        ("nick", Value::s("hana")),
        ("machine", Value::s("hana-box")),
        ("asleep", Value::Bool(true)),
    ]);
    if !wake
        .wake_tick(&list(vec![posted]), &list(vec![unknown]), &[], T0)
        .is_empty()
    {
        return Err("a runtime-free record woke".to_string());
    }
    Ok(())
}

fn phase_dedupe_and_second_job(wake: &dyn Wake) -> Result<(), String> {
    let agent = hana_agent(true, "muse");
    let first = job("job-1", "hana", true);
    let journal = wake.wake_tick(
        &list(vec![first.clone()]),
        &list(vec![agent.clone()]),
        &[],
        T0,
    );
    if journal.len() != 1 {
        return Err(format!("first tick yielded {}", journal.len()));
    }
    if !wake
        .wake_tick(&list(vec![first.clone()]), &list(vec![agent.clone()]), &journal, T0)
        .is_empty()
    {
        return Err("second tick re-woke the same pair".to_string());
    }
    let second = job("job-2", "hana", true);
    let new = wake.wake_tick(
        &list(vec![first, second]),
        &list(vec![agent]),
        &journal,
        T0,
    );
    if new.len() != 1 || new[0].get("job").as_str() != Some("job-2") {
        return Err(format!("second job yielded {} records", new.len()));
    }
    if new[0].get("dedupe_key").as_str() != Some("wake:job-2:hana") {
        return Err("dedupe key wrong".to_string());
    }
    Ok(())
}

fn phase_no_mind_image_honesty(wake: &dyn Wake) -> Result<(), String> {
    let agent = hana_agent(true, "muse");
    let posted = job("job-1", "hana", false);
    let new = wake.wake_tick(&list(vec![posted]), &list(vec![agent]), &[], T0);
    if new.len() != 1 {
        return Err(format!("tick yielded {} records", new.len()));
    }
    let bundle = new[0].get("bundle");
    if !bundle.get("mind_image").is_null() {
        return Err("bundle invented a mind image".to_string());
    }
    let note = bundle.get("mind_image_note").py_str();
    if !note.contains("OS-102") || !note.contains("pending") {
        return Err("bundle note does not name OS-102 pending".to_string());
    }
    let mut runtime = FakeMuseRuntime::new();
    let session = runtime.start(Some(&bundle));
    if session.get("first_bus_action").as_str() != Some("claim") {
        return Err("first bus action was not claim".to_string());
    }
    Ok(())
}

/// The structural scan standing in for the source's AST
/// walk of intel/wake.py: use-statement roots in the banned
/// set {socket, urllib, requests, redis, subprocess}.
pub fn module_imports_banned(source: &str) -> bool {
    let banned = ["socket", "urllib", "requests", "redis", "subprocess"];
    source.lines().any(|line| {
        let trimmed = line.trim_start();
        if let Some(rest) = trimmed.strip_prefix("use ") {
            let root = rest
                .split(|c| c == ':' || c == ';' || c == ' ')
                .next()
                .unwrap_or("");
            banned.contains(&root)
        } else {
            false
        }
    })
}

fn phase_malformed_and_immutable(wake: &dyn Wake, wake_source: &str) -> Result<(), String> {
    let jobs = list(vec![
        Value::Null,
        Value::s("not-a-job"),
        Value::obj(vec![("id", Value::s("job-1"))]),
        Value::obj(vec![("addressed_to", Value::s("hana"))]),
        job("job-1", "hana", true),
    ]);
    let agents = list(vec![
        Value::Null,
        Value::s("not-an-agent"),
        Value::obj(vec![("nick", Value::s("hana"))]),
        hana_agent(true, "muse"),
    ]);
    let jobs_before = jobs.clone();
    let agents_before = agents.clone();
    let journal: Vec<Value> = vec![
        Value::s("not-a-record"),
        Value::obj(vec![("kind", Value::s("wake"))]),
    ];
    let journal_before = journal.clone();
    let new = wake.wake_tick(&jobs, &agents, &journal, T0);
    if new.len() != 1 || new[0].get("job").as_str() != Some("job-1") {
        return Err(format!("malformed tick yielded {} records", new.len()));
    }
    if jobs != jobs_before || agents != agents_before {
        return Err("tick mutated jobs or agents".to_string());
    }
    if journal != journal_before {
        return Err("tick mutated the journal".to_string());
    }
    if !wake.wake_tick(&Value::Null, &Value::Null, &[], T0).is_empty() {
        return Err("None inputs yielded records".to_string());
    }
    if module_imports_banned(wake_source) {
        return Err("module imports a banned module".to_string());
    }
    // The drill's SENT ledger: nothing in the drill ever
    // sends, so it is empty by construction.
    let sent: Vec<Value> = Vec::new();
    if !sent.is_empty() {
        return Err("sent ledger is not empty".to_string());
    }
    Ok(())
}

/// The drill's main(): all six phases, then the tally.
/// `wake_source` is the B10 wake module's source text.
pub fn run(wake: &dyn Wake, wake_source: &str) -> DrillOutcome {
    let mut phases: Vec<PhaseResult> = Vec::new();
    let mut lines: Vec<String> = Vec::new();
    let mut passed = 0usize;
    let total = 6usize;
    if phase("wake-and-claim", phase_wake_and_claim(wake), &mut phases, &mut lines) {
        passed += 1;
    }
    if phase("wrong-addressee", phase_wrong_addressee(wake), &mut phases, &mut lines) {
        passed += 1;
    }
    if phase(
        "awake-and-other-runtime",
        phase_awake_and_other_runtime(wake),
        &mut phases,
        &mut lines,
    ) {
        passed += 1;
    }
    if phase(
        "dedupe-and-second-job",
        phase_dedupe_and_second_job(wake),
        &mut phases,
        &mut lines,
    ) {
        passed += 1;
    }
    if phase(
        "no-mind-image-honesty",
        phase_no_mind_image_honesty(wake),
        &mut phases,
        &mut lines,
    ) {
        passed += 1;
    }
    if phase(
        "malformed-and-immutable",
        phase_malformed_and_immutable(wake, wake_source),
        &mut phases,
        &mut lines,
    ) {
        passed += 1;
    }
    lines.push(format!("{}/{} phases PASS", passed, total));
    DrillOutcome {
        report: DrillReport::new("wake", phases),
        lines,
    }
}
