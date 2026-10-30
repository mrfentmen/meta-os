//! Port of `os/intel/drills/baton_pass.py` — baton pass
//! drill (Milo lane, OS-125).
//!
//! A worker is killed mid-job; the watchman passes the baton
//! and the job completes with no repeated work — the record
//! shows the deposited progress, zero duplicated file
//! changes, and a continuation prompt that names what
//! remains instead of restating the whole job. In-window the
//! continuation is proven same-program only; the
//! cross-program pass is the named stretch line, not claimed
//! here (see the source docstring). The baton module (B10
//! `Baton` trait) composes the continuation from the job
//! record; it never moves a claim. The no-dale phase reads
//! the baton module's source (passed in by the harness) for
//! a push path, the Rust mapping of the source's text check.

use super::DrillOutcome;
use crate::b12a_drills::deps::Baton;
use crate::b12a_drills::value::Value;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub const T0: i64 = 100000;
pub const WORKER: &str = "pax";
pub const NEXT: &str = "hana";

/// The killed job fixture, verbatim.
pub fn killed_job() -> Value {
    Value::obj(vec![
        ("id", Value::s("7")),
        ("title", Value::s("Wire the watchdog status line")),
        ("goal", Value::s("Show one live health line on the boot screen")),
        ("claim", Value::s(WORKER)),
        ("status", Value::s("claimed")),
        ("claimed_at", Value::Int(T0)),
        ("last_progress_at", Value::Int(T0 + 300)),
        (
            "progress_notes",
            Value::List(vec![
                Value::s("wrote a.txt"),
                Value::s("tests pass for a.txt"),
            ]),
        ),
        ("note", Value::s("tests pass for a.txt")),
        (
            "files",
            Value::List(vec![
                Value::s("a.txt"),
                Value::s("b.txt"),
                Value::s("c.txt"),
            ]),
        ),
        ("completed_files", Value::List(vec![Value::s("a.txt")])),
        (
            "steps",
            Value::List(vec![
                Value::s("write a.txt"),
                Value::s("write b.txt"),
                Value::s("write c.txt"),
            ]),
        ),
        ("completed_steps", Value::List(vec![Value::s("write a.txt")])),
        (
            "acceptance_checks",
            Value::List(vec![Value::s("b.txt renders"), Value::s("c.txt renders")]),
        ),
    ])
}

fn snap(jobs: Vec<Value>) -> Value {
    Value::obj(vec![("jobs", Value::List(jobs))])
}

fn str_list(value: &Value) -> Vec<String> {
    value
        .as_list()
        .map(|items| items.iter().map(|v| v.py_str()).collect())
        .unwrap_or_default()
}

struct Ctx {
    phases: Vec<PhaseResult>,
    lines: Vec<String>,
}

impl Ctx {
    fn pass(&mut self, name: &str, line: String) {
        self.phases.push(PhaseResult::pass(name, line.clone()));
        self.lines.push(line);
    }
    fn fail(&mut self, name: &str, line: String) {
        self.phases.push(PhaseResult::fail(name, line.clone()));
        self.lines.push(line);
    }
}

/// Run all phases. `baton_source` is the baton port's own
/// source text for the no-dale phase.
pub fn run(baton: &dyn Baton, baton_source: &str) -> DrillOutcome {
    let mut ctx = Ctx {
        phases: Vec::new(),
        lines: Vec::new(),
    };

    // full-pass
    {
        let name = "full-pass";
        let job = killed_job();
        let snapshot = snap(vec![job.clone()]);
        let mut failure: Option<String> = None;
        let composed = baton.compose_baton(&job);
        match composed {
            None => failure = Some("no baton composed".to_string()),
            Some(composed) => {
                if composed.get("goal") != job.get("goal") {
                    failure = Some(format!(
                        "baton goal {:?} is not the job goal",
                        composed.get("goal").py_repr()
                    ));
                } else if composed.get("progress_notes") != job.get("progress_notes") {
                    failure = Some(format!(
                        "baton progress {:?} drops deposited notes",
                        composed.get("progress_notes").py_repr()
                    ));
                } else if str_list(&composed.get("remaining_files"))
                    != vec!["b.txt".to_string(), "c.txt".to_string()]
                {
                    failure = Some(format!(
                        "remaining files {:?}, expected [b.txt, c.txt]",
                        composed.get("remaining_files").py_repr()
                    ));
                } else if str_list(&composed.get("remaining_steps"))
                    != vec!["write b.txt".to_string(), "write c.txt".to_string()]
                {
                    failure = Some(format!(
                        "remaining steps {:?}",
                        composed.get("remaining_steps").py_repr()
                    ));
                } else {
                    let prompt = composed.get("prompt").py_str();
                    for needle in [
                        "Show one live health line",
                        "tests pass for a.txt",
                        "write b.txt",
                        "b.txt renders",
                    ] {
                        if !prompt.contains(needle) {
                            failure = Some(format!("prompt misses {:?}", needle));
                            break;
                        }
                    }
                    if failure.is_none() {
                        let still = prompt
                            .split("Files still to touch:")
                            .nth(1)
                            .and_then(|rest| rest.split("What remains:").next())
                            .unwrap_or("");
                        if still.contains("a.txt") {
                            failure = Some(
                                "prompt lists completed a.txt as still to touch".to_string(),
                            );
                        }
                    }
                    if failure.is_none() {
                        let records =
                            baton.baton_pass_tick(&snapshot, "7", NEXT, &[], T0 + 600);
                        if records.len() != 1
                            || records[0].get("kind").as_str() != Some("baton-pass")
                        {
                            failure = Some(format!(
                                "pass tick yielded {}",
                                Value::List(records).py_repr()
                            ));
                        } else if records[0].get("to_worker").as_str() != Some(NEXT) {
                            failure = Some(format!(
                                "pass names {:?}, expected {}",
                                records[0].get("to_worker").py_repr(),
                                NEXT
                            ));
                        } else {
                            let written: Vec<String> =
                                str_list(&composed.get("remaining_files"));
                            let already: Vec<String> =
                                str_list(&composed.get("completed_files"));
                            let overlap: Vec<String> = written
                                .iter()
                                .filter(|f| already.contains(f))
                                .cloned()
                                .collect();
                            if !overlap.is_empty() {
                                failure = Some(format!(
                                    "next worker repeats {:?}",
                                    overlap
                                ));
                            } else {
                                let mut finished: Vec<String> =
                                    written.iter().chain(already.iter()).cloned().collect();
                                finished.sort();
                                finished.dedup();
                                if finished
                                    != vec![
                                        "a.txt".to_string(),
                                        "b.txt".to_string(),
                                        "c.txt".to_string(),
                                    ]
                                {
                                    failure = Some(format!("finished files {:?}", finished));
                                }
                            }
                        }
                    }
                }
            }
        }
        match failure {
            None => ctx.pass(
                name,
                format!(
                    "full-pass: killed worker {} mid-job 7, baton names goal, progress, remaining files b/c, remaining steps, checks; next worker {} writes only b/c, zero duplicated file changes: PASS",
                    WORKER, NEXT
                ),
            ),
            Some(msg) => ctx.fail(name, format!("full-pass: FAIL: {}", msg)),
        }
    }

    // no-progress
    {
        let name = "no-progress";
        let job = Value::obj(vec![
            ("id", Value::s("8")),
            ("title", Value::s("Unstarted job")),
            ("claim", Value::s(WORKER)),
            (
                "files",
                Value::List(vec![Value::s("x.txt"), Value::s("y.txt")]),
            ),
            ("accept", Value::s("x renders\ny renders")),
        ]);
        let mut failure: Option<String> = None;
        match baton.compose_baton(&job) {
            None => failure = Some("no baton for a job with no deposited progress".to_string()),
            Some(composed) => {
                if !composed
                    .get("progress_notes")
                    .as_list()
                    .map(|l| l.is_empty())
                    .unwrap_or(false)
                {
                    failure = Some(format!(
                        "baton invents progress {}",
                        composed.get("progress_notes").py_repr()
                    ));
                } else if !composed
                    .get("completed_files")
                    .as_list()
                    .map(|l| l.is_empty())
                    .unwrap_or(false)
                {
                    failure = Some("baton invents completed files".to_string());
                } else if str_list(&composed.get("remaining_files"))
                    != vec!["x.txt".to_string(), "y.txt".to_string()]
                {
                    failure = Some(format!(
                        "remaining {:?}",
                        composed.get("remaining_files").py_repr()
                    ));
                } else if !composed
                    .get("prompt")
                    .py_str()
                    .contains("no progress notes deposited")
                {
                    failure = Some("prompt does not say no progress was deposited".to_string());
                } else if str_list(&composed.get("acceptance_checks"))
                    != vec!["x renders".to_string(), "y renders".to_string()]
                {
                    failure = Some(format!(
                        "accept string parses to {:?}",
                        composed.get("acceptance_checks").py_repr()
                    ));
                }
            }
        }
        match failure {
            None => ctx.pass(
                name,
                "no-progress: job with nothing deposited yields an honest prompt, every file still to touch: PASS"
                    .to_string(),
            ),
            Some(msg) => ctx.fail(name, format!("no-progress: FAIL: {}", msg)),
        }
    }

    // malformed
    {
        let name = "malformed";
        let mut failure: Option<String> = None;
        if baton.compose_baton(&Value::s("not a record")).is_some() {
            failure = Some("non-record yields a baton".to_string());
        } else if baton
            .compose_baton(&Value::obj(vec![("title", Value::s("no id"))]))
            .is_some()
        {
            failure = Some("id-less record yields a baton".to_string());
        } else if !baton
            .baton_pass_tick(&snap(vec![]), "99", NEXT, &[], T0)
            .is_empty()
        {
            failure = Some("missing job yields a pass record".to_string());
        } else if !baton
            .baton_pass_tick(&snap(vec![]), "", NEXT, &[], T0)
            .is_empty()
        {
            failure = Some("empty job id yields a pass record".to_string());
        } else {
            let string_job = Value::obj(vec![
                ("id", Value::s("9")),
                ("title", Value::s("String forms")),
                ("files", Value::s("a.txt, b.txt, a.txt")),
                ("completed_files", Value::s("a.txt")),
                ("accept", Value::s("a renders\nb renders\n")),
            ]);
            match baton.compose_baton(&string_job) {
                Some(composed) if str_list(&composed.get("files")) == vec!["a.txt".to_string(), "b.txt".to_string()] => {
                    if str_list(&composed.get("remaining_files")) != vec!["b.txt".to_string()] {
                        failure = Some(format!(
                            "remaining from string forms {:?}",
                            composed.get("remaining_files").py_repr()
                        ));
                    }
                }
                other => {
                    failure = Some(format!(
                        "comma files parse to {:?}",
                        other.map(|c| c.get("files").py_repr())
                    ));
                }
            }
            if failure.is_none() {
                let spec_job = Value::obj(vec![
                    ("id", Value::s("10")),
                    ("title", Value::s("Spec goal")),
                    (
                        "spec",
                        Value::s("Goal: Ship the status line\nContext: boot"),
                    ),
                    ("files", Value::List(vec![])),
                ]);
                match baton.compose_baton(&spec_job) {
                    Some(composed) if composed.get("goal").as_str() == Some("Ship the status line") => {}
                    other => {
                        failure = Some(format!(
                            "spec goal reads {:?}",
                            other.map(|c| c.get("goal").py_repr())
                        ));
                    }
                }
            }
        }
        match failure {
            None => ctx.pass(
                name,
                "malformed: non-records, id-less records, and missing jobs yield nothing; string and spec forms parse: PASS"
                    .to_string(),
            ),
            Some(msg) => ctx.fail(name, format!("malformed: FAIL: {}", msg)),
        }
    }

    // idempotent-and-immutable
    {
        let name = "idempotent-and-immutable";
        let job = killed_job();
        let before = job.clone();
        let snapshot = snap(vec![job.clone()]);
        let first = baton.baton_pass_tick(&snapshot, "7", NEXT, &[], T0 + 600);
        let second = baton.baton_pass_tick(&snapshot, "7", NEXT, &first, T0 + 700);
        let mut failure: Option<String> = None;
        if first.len() != 1 || !second.is_empty() {
            failure = Some(format!(
                "idempotent: first tick {} records, second tick {} records, expected 1 then 0",
                first.len(),
                second.len()
            ));
        } else if job != before {
            failure = Some("immutable: composing mutated the job record".to_string());
        } else {
            let lines = baton.baton_brief_lines(&first);
            let line_ok = lines.len() == 1
                && lines[0].contains('7')
                && lines[0].contains(WORKER)
                && lines[0].contains(NEXT)
                && lines[0].contains("2 file(s)");
            if !line_ok {
                failure = Some(format!("idempotent: brief line {:?}", lines));
            }
        }
        match failure {
            None => ctx.pass(
                name,
                "idempotent: second pass journals nothing, job record unchanged, brief line names job/workers/count: PASS"
                    .to_string(),
            ),
            Some(msg) => {
                if let Some(rest) = msg.strip_prefix("idempotent: ") {
                    ctx.fail(name, format!("idempotent: FAIL: {}", rest))
                } else if let Some(rest) = msg.strip_prefix("immutable: ") {
                    ctx.fail(name, format!("immutable: FAIL: {}", rest))
                } else {
                    ctx.fail(name, format!("idempotent: FAIL: {}", msg))
                }
            }
        }
    }

    // no-dale
    {
        let name = "no-dale";
        let job = killed_job();
        let snapshot = snap(vec![job]);
        let records = baton.baton_pass_tick(&snapshot, "7", NEXT, &[], T0 + 600);
        let mut failure: Option<String> = None;
        if records.len() != 1 {
            failure = Some(format!(
                "pass tick yielded {}",
                Value::List(records).py_repr()
            ));
        } else {
            let record = records[0].clone();
            if record.contains_key("push") || record.contains_key("announcement") {
                failure = Some("pass record carries a push or announcement field".to_string());
            } else if baton_source.contains("intel/push")
                || baton_source.contains("import push")
                || baton_source.contains("::push")
            {
                // The source greps baton.py for a push import;
                // "::push" is the Rust path form of the same
                // reach.
                failure = Some("baton module imports a push path".to_string());
            }
        }
        match failure {
            None => ctx.pass(
                name,
                "no-dale: pass record is journal only, baton module has no push path, Dale contacted at no rung: PASS"
                    .to_string(),
            ),
            Some(msg) => ctx.fail(name, format!("no-dale: FAIL: {}", msg)),
        }
    }

    if ctx.phases.iter().all(|p| p.pass) {
        ctx.lines.push("baton_pass: ALL PHASES PASS".to_string());
    } else {
        ctx.lines.push("baton_pass: FAILED".to_string());
    }
    DrillOutcome {
        report: DrillReport::new("baton_pass", ctx.phases),
        lines: ctx.lines,
    }
}
