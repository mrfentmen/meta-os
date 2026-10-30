//! Port of `os/intel/drills/attempt_gate.py` — attempt
//! budgets + escalation gate drill (Milo lane, OS-096).
//!
//! A deliberately impossible job burns exactly its budget,
//! parks, and escalates exactly once — no loop, no duplicate
//! pushes; a crew-fixable blocker resolves with zero
//! escalation; a money blocker parks at once quoting the
//! note verbatim. The gate (B09 `Gate` trait) builds records
//! and never sends: the drill's sent ledger stays empty
//! because the gate has no send path at all. Payload
//! validation is the B10 `Push` trait.

use super::DrillOutcome;
use crate::b12a_drills::deps::{Gate, Push};
use crate::b12a_drills::value::Value;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub const T0: i64 = 100000;

/// The drill's `job()` record builder.
pub fn job(
    job_id: &str,
    attempts: Option<Value>,
    maximum: Option<Value>,
    blocker_kind: Option<&str>,
    note: Option<&str>,
    status: &str,
) -> Value {
    let mut pairs = vec![
        ("id", Value::s(job_id)),
        ("title", Value::s(&format!("job {}", job_id))),
        ("status", Value::s(status)),
    ];
    if let Some(a) = attempts {
        pairs.push(("attempts", a));
    }
    if let Some(m) = maximum {
        pairs.push(("max_attempts", m));
    }
    if let Some(b) = blocker_kind {
        pairs.push(("blocker_kind", Value::s(b)));
    }
    if let Some(n) = note {
        pairs.push(("note", Value::s(n)));
    }
    Value::obj(pairs)
}

fn snap(jobs: Vec<Value>) -> Value {
    Value::obj(vec![("jobs", Value::List(jobs))])
}

struct Ctx<'a> {
    phases: Vec<PhaseResult>,
    lines: Vec<String>,
    gate: &'a dyn Gate,
    push: &'a dyn Push,
}

impl<'a> Ctx<'a> {
    fn pass(&mut self, name: &str, line: String) {
        self.phases.push(PhaseResult::pass(name, line.clone()));
        self.lines.push(line);
    }
    fn fail(&mut self, name: &str, line: String) {
        self.phases.push(PhaseResult::fail(name, line.clone()));
        self.lines.push(line);
    }
}

/// Run all phases against the gate/push surfaces.
pub fn run(gate: &dyn Gate, push: &dyn Push) -> DrillOutcome {
    let mut ctx = Ctx {
        phases: Vec::new(),
        lines: Vec::new(),
        gate,
        push,
    };

    // impossible
    {
        let name = "impossible";
        let mut journal: Vec<Value> = Vec::new();
        let mut failure: Option<String> = None;
        let records = gate.gate_tick(&snap(vec![job("7", Some(Value::Int(0)), Some(Value::Int(2)), None, None, "claimed")]), &journal, T0);
        if !records.is_empty() {
            failure = Some("gate acted with budget remaining".to_string());
        }
        if failure.is_none() {
            let records = gate.gate_tick(&snap(vec![job("7", Some(Value::Int(1)), Some(Value::Int(2)), None, None, "claimed")]), &journal, T0 + 60);
            if !records.is_empty() {
                failure = Some("gate acted at 1/2 attempts".to_string());
            }
        }
        if failure.is_none() {
            let full = snap(vec![job("7", Some(Value::Int(2)), Some(Value::Int(2)), None, None, "claimed")]);
            let records = gate.gate_tick(&full, &journal, T0 + 120);
            if records.len() != 2 {
                failure = Some(format!(
                    "expected parked + escalation, got {}",
                    records.len()
                ));
            } else {
                let parked = records[0].clone();
                let escalation = records[1].clone();
                if parked.get("kind").as_str() != Some("parked")
                    || escalation.get("kind").as_str() != Some("escalation")
                {
                    failure = Some("wrong record kinds".to_string());
                } else if !parked.get("reason").py_str().contains("2/2") {
                    failure = Some("park reason does not name the budget".to_string());
                } else {
                    let payload = escalation.get("push");
                    if !push.validate_push(&payload) {
                        failure = Some("escalation payload does not validate".to_string());
                    } else if payload.get("type").as_str() != Some("blocked")
                        || payload.get("job_id").as_str() != Some("7")
                    {
                        failure = Some("payload is not the blocked push for 7".to_string());
                    } else {
                        journal.extend(records);
                        let again = gate.gate_tick(&full, &journal, T0 + 180);
                        if !again.is_empty() {
                            failure = Some(format!(
                                "second tick journaled {} new records",
                                again.len()
                            ));
                        }
                    }
                }
            }
        }
        match failure {
            None => ctx.pass(
                name,
                "impossible: PASS: job 7 burned 2/2, parked, one escalation, second tick silent"
                    .to_string(),
            ),
            Some(msg) => ctx.fail(name, format!("impossible: FAIL: {}", msg)),
        }
    }

    // crew-fixable
    {
        let name = "crew-fixable";
        let journal: Vec<Value> = Vec::new();
        let snapshot = snap(vec![job(
            "8",
            Some(Value::Int(0)),
            Some(Value::Int(3)),
            Some("dependency"),
            Some("waits on job 7"),
            "claimed",
        )]);
        let mut failure = false;
        for tick in 0..3 {
            let records = gate.gate_tick(&snapshot, &journal, T0 + tick * 60);
            if !records.is_empty() {
                failure = true;
                break;
            }
        }
        if failure {
            ctx.fail(
                name,
                "crew-fixable: FAIL: gate acted on a dependency blocker".to_string(),
            );
        } else {
            ctx.pass(
                name,
                "crew-fixable: PASS: dependency blocker, 0/3, zero parks and zero escalations across 3 ticks"
                    .to_string(),
            );
        }
    }

    // dale-call
    {
        let name = "dale-call";
        let note = "needs $40/mo API key approval";
        let mut journal: Vec<Value> = Vec::new();
        let snapshot = snap(vec![job(
            "9",
            Some(Value::Int(1)),
            Some(Value::Int(5)),
            Some("money"),
            Some(note),
            "claimed",
        )]);
        let records = gate.gate_tick(&snapshot, &journal, T0);
        let mut failure: Option<String> = None;
        if records.len() != 2 {
            failure = Some(format!(
                "expected parked + escalation, got {}",
                records.len()
            ));
        } else {
            let parked = records[0].clone();
            let escalation = records[1].clone();
            if parked.get("question").as_str() != Some(note) {
                failure = Some("park question is not the note verbatim".to_string());
            } else {
                let payload = escalation.get("push");
                if !push.validate_push(&payload) {
                    failure = Some("escalation payload does not validate".to_string());
                } else if payload.get("question").as_str() != Some(note) {
                    failure = Some("payload question is not the note verbatim".to_string());
                } else {
                    journal.extend(records);
                    let again = gate.gate_tick(&snapshot, &journal, T0 + 60);
                    if !again.is_empty() {
                        failure = Some(format!(
                            "second tick journaled {} new records",
                            again.len()
                        ));
                    }
                }
            }
        }
        match failure {
            None => ctx.pass(
                name,
                "dale-call: PASS: money blocker parked at 1/5 with the note quoted verbatim, one escalation, second tick silent"
                    .to_string(),
            ),
            Some(msg) => ctx.fail(name, format!("dale-call: FAIL: {}", msg)),
        }
    }

    // malformed
    {
        let name = "malformed";
        let snapshot = snap(vec![
            job("10", Some(Value::s("two")), Some(Value::Int(3)), None, None, "claimed"),
            job("11", Some(Value::Int(1)), None, None, None, "claimed"),
            job("12", Some(Value::Int(1)), Some(Value::Int(0)), None, None, "claimed"),
            job("13", Some(Value::Int(-1)), Some(Value::Int(3)), None, None, "claimed"),
            Value::obj(vec![
                ("title", Value::s("no id at all")),
                ("attempts", Value::Int(9)),
                ("max_attempts", Value::Int(3)),
            ]),
            Value::s("not a record"),
        ]);
        let records = gate.gate_tick(&snapshot, &[], T0);
        if records.is_empty() {
            ctx.pass(
                name,
                "malformed: PASS: non-numeric, missing, zero, negative, and id-less jobs yield nothing and no crash"
                    .to_string(),
            );
        } else {
            ctx.fail(
                name,
                format!(
                    "malformed: FAIL: gate acted on malformed jobs: {}",
                    Value::List(records).py_repr()
                ),
            );
        }
    }

    // no-extra-contact
    {
        let name = "no-extra-contact";
        let sent: Vec<Value> = Vec::new();
        let journal: Vec<Value> = Vec::new();
        let snapshot = snap(vec![
            job("7", Some(Value::Int(2)), Some(Value::Int(2)), None, None, "claimed"),
            job(
                "9",
                Some(Value::Int(1)),
                Some(Value::Int(5)),
                Some("money"),
                Some("needs $40/mo API key approval"),
                "claimed",
            ),
        ]);
        let records = gate.gate_tick(&snapshot, &journal, T0);
        let escalations: Vec<Value> = records
            .iter()
            .filter(|r| r.get("kind").as_str() == Some("escalation"))
            .cloned()
            .collect();
        let mut failure: Option<String> = None;
        if escalations.len() != 2 {
            failure = Some(format!(
                "expected 2 escalations, got {}",
                escalations.len()
            ));
        } else if escalations
            .iter()
            .any(|r| !push.validate_push(&r.get("push")))
        {
            failure = Some("an escalation payload is invalid".to_string());
        } else if !sent.is_empty() {
            failure = Some("the sent ledger is not empty".to_string());
        }
        match failure {
            None => ctx.pass(
                name,
                "no-extra-contact: PASS: exactly 2 escalations, both payloads valid, sent ledger empty (gate builds, never sends)"
                    .to_string(),
            ),
            Some(msg) => ctx.fail(name, format!("no-extra-contact: FAIL: {}", msg)),
        }
    }

    // immutable
    {
        let name = "immutable";
        let snapshot = snap(vec![job("7", Some(Value::Int(2)), Some(Value::Int(2)), None, None, "claimed")]);
        let journal = vec![Value::obj(vec![
            ("kind", Value::s("parked")),
            ("job", Value::s("9")),
            ("dedupe_key", Value::s("park:9")),
        ])];
        let snap_before = snapshot.clone();
        let journal_before = journal.clone();
        let _ = gate.gate_tick(&snapshot, &journal, T0);
        if snapshot != snap_before || journal != journal_before {
            ctx.fail(
                name,
                "immutable: FAIL: gate_tick mutated its inputs".to_string(),
            );
        } else {
            ctx.pass(
                name,
                "immutable: PASS: snapshot and journal unchanged by the tick".to_string(),
            );
        }
    }

    // brief
    {
        let name = "brief";
        let records = gate.gate_tick(
            &snap(vec![job("7", Some(Value::Int(2)), Some(Value::Int(2)), None, None, "claimed")]),
            &[],
            T0,
        );
        let lines = gate.gate_brief_lines(&records);
        let mut failure: Option<String> = None;
        if lines.len() != 2 {
            failure = Some(format!("expected 2 lines, got {}", lines.len()));
        } else if !lines[0].contains("Parked job 7") {
            failure = Some("parked line does not name job 7".to_string());
        } else if !lines[1].contains("Escalated job 7") {
            failure = Some("escalation line does not name job 7".to_string());
        }
        match failure {
            None => ctx.pass(
                name,
                "brief: PASS: parked and escalation lines name job 7".to_string(),
            ),
            Some(msg) => ctx.fail(name, format!("brief: FAIL: {}", msg)),
        }
    }

    DrillOutcome {
        report: DrillReport::new("attempt_gate", ctx.phases),
        lines: ctx.lines,
    }
}
