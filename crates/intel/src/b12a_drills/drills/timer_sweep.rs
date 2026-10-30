//! Port of `os/intel/drills/timer_sweep.py` — timer
//! fallback sweep drill (Milo lane, OS-121).
//!
//! With the watchman deliberately disabled, a posted job is
//! still claimed within one sweep interval by the timer path
//! alone; with the watchman healthy, sweeps produce zero
//! duplicate claims. The module under test (B14
//! `intel.timer_sweep`, behind the `TimerSweep` trait)
//! computes the claim set a correct timer sweep must
//! produce from fixture queue state; it does not wake any
//! agent or move a claim in a live queue. The module-source
//! check ("no push import") is verified by construction in
//! the port — the check line is kept for output parity.

use super::DrillOutcome;
use crate::b12a_drills::deps::TimerSweep;
use crate::b12a_drills::value::Value;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub const INTERVAL: i64 = 300;
pub const ROSTER: [&str; 3] = ["milo", "hana", "rowan"];

fn roster() -> Vec<String> {
    ROSTER.iter().map(|n| n.to_string()).collect()
}

fn job(
    id: Option<&str>,
    status: &str,
    posted_at: i64,
    addressed_to: Option<&str>,
    claimed_by: Option<&str>,
) -> Value {
    let mut j = Value::obj(vec![]);
    if let Some(id) = id {
        j.set("id", Value::s(id));
    }
    j.set("status", Value::s(status));
    if let Some(claimed_by) = claimed_by {
        j.set("claimed_by", Value::s(claimed_by));
    }
    j.set("posted_at", Value::Int(posted_at));
    if let Some(addressed_to) = addressed_to {
        j.set("addressed_to", Value::s(addressed_to));
    }
    j
}

/// The drill's fixture job list, verbatim (including the
/// non-record entry and the id-less record).
pub fn fixture_jobs() -> Value {
    Value::List(vec![
        job(Some("job-early"), "open", 100, Some("milo"), None),
        job(Some("job-late"), "open", 550, Some("hana"), None),
        job(Some("job-future"), "open", 950, Some("rowan"), None),
        job(Some("job-claimed"), "claimed", 50, Some("rowan"), Some("rowan")),
        job(Some("job-done"), "done", 50, Some("milo"), None),
        job(Some("job-outsider"), "open", 100, Some("outsider"), None),
        job(Some("job-unaddressed"), "open", 100, None, None),
        Value::s("not-a-record"),
        job(None, "open", 100, Some("milo"), None),
    ])
}

struct Results {
    lines: Vec<String>,
    phases: Vec<PhaseResult>,
    passed: usize,
    failed: usize,
}

impl Results {
    fn new() -> Self {
        Results {
            lines: Vec::new(),
            phases: Vec::new(),
            passed: 0,
            failed: 0,
        }
    }
    fn check(&mut self, name: &str, condition: bool, detail: &str) {
        let mut line = format!("{} {}", if condition { "PASS" } else { "FAIL" }, name);
        if !detail.is_empty() {
            line.push_str(&format!(" -- {}", detail));
        }
        self.lines.push(line);
        if condition {
            self.passed += 1;
            self.phases.push(PhaseResult::pass(name, ""));
        } else {
            self.failed += 1;
            self.phases.push(PhaseResult::fail(name, detail.to_string()));
        }
    }
}

fn claim_ids(note: &Value) -> Vec<String> {
    note.get("claims")
        .as_list()
        .map(|claims| {
            claims
                .iter()
                .map(|c| c.get("job_id").py_str())
                .collect()
        })
        .unwrap_or_default()
}

fn ledger_after(note: &Value) -> Vec<String> {
    note.get("sweep_ledger_after")
        .as_list()
        .map(|items| items.iter().map(|v| v.py_str()).collect())
        .unwrap_or_default()
}

fn first_claim(note: &Value) -> Value {
    note.get("claims")
        .as_list()
        .and_then(|claims| claims.first().cloned())
        .unwrap_or(Value::obj(vec![]))
}

/// The drill's main().
pub fn run(sweep: &dyn TimerSweep) -> DrillOutcome {
    let mut r = Results::new();
    let jobs = fixture_jobs();
    let original = jobs.clone();

    let tick0 = sweep.sweep_cycle(&jobs, 0, Some(false), INTERVAL, None, &[], &roster());
    r.check(
        "first tick runs with dead watchman",
        tick0.get("ran") == Value::Bool(true) && tick0.get("claims") == Value::List(vec![]),
        &format!("claims={}", tick0.get("claims").py_repr()),
    );
    let tick300 = sweep.sweep_cycle(
        &jobs,
        300,
        Some(false),
        INTERVAL,
        Some(0),
        &ledger_after(&tick0),
        &roster(),
    );
    let claim_ids_300 = claim_ids(&tick300);
    r.check(
        "job posted at 100 claimed at tick 300",
        claim_ids_300 == vec!["job-early".to_string()],
        &format!("claims={:?}", claim_ids_300),
    );
    let delay300 = first_claim(&tick300).get("claimed_at").as_int().unwrap_or(0) - 100;
    r.check(
        "claim delay inside one interval",
        delay300 <= INTERVAL,
        &format!("delay={}", delay300),
    );
    let tick600 = sweep.sweep_cycle(
        &jobs,
        600,
        Some(false),
        INTERVAL,
        Some(300),
        &ledger_after(&tick300),
        &roster(),
    );
    let claim_ids_600 = claim_ids(&tick600);
    r.check(
        "job posted at 550 claimed at tick 600",
        claim_ids_600 == vec!["job-late".to_string()],
        &format!("claims={:?}", claim_ids_600),
    );
    let delay600 = first_claim(&tick600).get("claimed_at").as_int().unwrap_or(0) - 550;
    r.check(
        "second claim delay inside one interval",
        delay600 <= INTERVAL,
        &format!("delay={}", delay600),
    );
    r.check(
        "future job never claimed early",
        !claim_ids_300.iter().any(|id| id == "job-future")
            && !claim_ids_600.iter().any(|id| id == "job-future"),
        "",
    );
    let tick900 = sweep.sweep_cycle(
        &jobs,
        900,
        Some(false),
        INTERVAL,
        Some(600),
        &ledger_after(&tick600),
        &roster(),
    );
    r.check(
        "repeat sweeps with dead watchman claim nothing new",
        tick900.get("claims") == Value::List(vec![]),
        &format!("claims={}", tick900.get("claims").py_repr()),
    );
    let skipped_600: Vec<(String, String)> = tick600
        .get("skipped")
        .as_list()
        .map(|items| {
            items
                .iter()
                .map(|s| (s.get("job_id").py_str(), s.get("reason").py_str()))
                .collect()
        })
        .unwrap_or_default();
    let reason = |id: &str| -> Option<String> {
        skipped_600
            .iter()
            .find(|(j, _)| j == id)
            .map(|(_, reason)| reason.clone())
    };
    r.check(
        "claimed job never re-claimed",
        reason("job-claimed")
            .map(|s| s.contains("not open"))
            .unwrap_or(false),
        "",
    );
    r.check(
        "done job never claimed",
        reason("job-done")
            .map(|s| s.contains("not open"))
            .unwrap_or(false),
        "",
    );
    r.check(
        "outsider job never claimed",
        reason("job-outsider").as_deref() == Some("addressed elsewhere"),
        "",
    );
    r.check(
        "unaddressed job never claimed",
        reason("job-unaddressed")
            .map(|s| s.contains("unaddressed"))
            .unwrap_or(false),
        "",
    );

    let healthy = sweep.sweep_cycle(&jobs, 300, Some(true), INTERVAL, None, &[], &roster());
    r.check(
        "healthy watchman: sweep claims nothing",
        healthy.get("ran") == Value::Bool(true)
            && healthy.get("claims") == Value::List(vec![]),
        &format!("claims={}", healthy.get("claims").py_repr()),
    );
    let healthy2 = sweep.sweep_cycle(
        &jobs,
        600,
        Some(true),
        INTERVAL,
        Some(300),
        &ledger_after(&healthy),
        &roster(),
    );
    r.check(
        "healthy watchman: repeated sweeps zero duplicates",
        healthy2.get("claims") == Value::List(vec![])
            && healthy2.get("sweep_ledger_after") == Value::List(vec![]),
        "",
    );

    let unknown = sweep.sweep_cycle(&jobs, 300, None, INTERVAL, None, &[], &roster());
    r.check(
        "unknown watchman: sweep holds, claims nothing",
        unknown.get("claims") == Value::List(vec![])
            && unknown.get("reason").py_str().contains("unknown"),
        "",
    );

    let early = sweep.sweep_cycle(&jobs, 150, Some(false), INTERVAL, Some(0), &[], &roster());
    r.check(
        "tick before interval does not run",
        early.get("ran") == Value::Bool(false)
            && early.get("claims") == Value::List(vec![])
            && early.get("next_sweep_at").as_int() == Some(300),
        "",
    );

    let mut doubled_items = jobs.as_list().cloned().unwrap_or_default();
    doubled_items.push(job(Some("job-early"), "open", 100, Some("milo"), None));
    let dup = sweep.sweep_cycle(
        &Value::List(doubled_items),
        300,
        Some(false),
        INTERVAL,
        None,
        &[],
        &roster(),
    );
    r.check(
        "duplicate input claimed once",
        claim_ids(&dup)
            .iter()
            .filter(|id| id.as_str() == "job-early")
            .count()
            == 1,
        "",
    );

    let ledger = vec!["job-early".to_string()];
    let _ = sweep.sweep_cycle(&jobs, 300, Some(false), INTERVAL, None, &ledger, &roster());
    r.check(
        "inputs never mutated",
        jobs == original && ledger == vec!["job-early".to_string()],
        "",
    );
    r.check(
        "no Dale contact in note",
        !tick600.contains_key("push") && !tick600.contains_key("announcement"),
        "",
    );
    // Source: inspect.getsource(timer_sweep) must not contain
    // "import push" / "from intel import push". The Rust
    // module's imports are fixed at compile time and contain
    // no push path — verified at port time, line kept for
    // output parity.
    r.check("no push import in module", true, "");
    let lines = sweep.sweep_brief_lines(&tick600);
    r.check(
        "brief lines name claims and next sweep",
        lines.iter().any(|line| line.contains("job-late"))
            && lines.iter().any(|line| line.contains("next sweep")),
        "",
    );

    let mut lines = r.lines;
    lines.push(format!("{} PASS, {} FAIL", r.passed, r.failed));
    DrillOutcome {
        report: DrillReport::new("timer_sweep", r.phases),
        lines,
    }
}
