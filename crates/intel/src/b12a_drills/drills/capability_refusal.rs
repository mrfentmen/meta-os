//! Port of `os/intel/drills/capability_refusal.py` —
//! OS-081 drill.
//!
//! A fixture crew process attempts actions inside and
//! outside its grant: every outside-grant attempt is refused
//! with the exact missing capability its case earns, the
//! explanation and the refusal note name the identity, the
//! action, and the missing capability, inside-grant attempts
//! are allowed and journal nothing, a tick journals one
//! refusal record per refused attempt (dedupe on the second
//! tick), inputs are never mutated, and the module carries
//! no push path. The alert record shape is proven through
//! intel.store.build_alert_record on the B09 surface. Grants
//! are plain dicts in the OS-080 shape, supplied by the
//! caller — no capability file is read or written.

use super::DrillOutcome;
use crate::b12a_drills::deps::{AlertRecords, Capability};
use crate::b12a_drills::value::Value;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub const NOW: i64 = 100000;

/// The GRANTS fixture, verbatim.
pub fn grants() -> Value {
    Value::obj(vec![
        (
            "milo",
            Value::obj(vec![
                ("identity", Value::s("milo")),
                ("bus_post", Value::Bool(false)),
                ("spend", Value::Bool(false)),
                ("network", Value::Bool(true)),
                (
                    "write_paths",
                    Value::List(vec![Value::s("crew/milo/")]),
                ),
            ]),
        ),
        (
            "pax",
            Value::obj(vec![
                ("identity", Value::s("pax")),
                ("bus_post", Value::Bool(true)),
                ("spend", Value::Bool(true)),
                ("network", Value::Bool(true)),
                (
                    "write_paths",
                    Value::List(vec![Value::s("crew/pax/"), Value::s("plan/")]),
                ),
            ]),
        ),
    ])
}

struct Checks {
    lines: Vec<String>,
    all: bool,
}

impl Checks {
    fn new() -> Self {
        Checks {
            lines: Vec::new(),
            all: true,
        }
    }
    /// The drill's check(): prints name + PASS, or FAIL: detail.
    fn check(&mut self, name: &str, condition: bool, detail: &str) {
        if condition {
            self.lines.push(format!("{}: PASS", name));
        } else {
            self.lines.push(format!("{}: FAIL: {}", name, detail));
            self.all = false;
        }
    }
}

/// Run all phases. `capability_source` is the capability
/// port's own source text for the no-push phase (the source
/// reads intel/capability.py; the banned substrings are the
/// source's own list).
pub fn run(
    capability: &dyn Capability,
    records: &dyn AlertRecords,
    capability_source: &str,
) -> DrillOutcome {
    let grants = grants();
    let mut phases: Vec<PhaseResult> = Vec::new();
    let mut lines: Vec<String> = Vec::new();

    // allowed
    {
        let mut c = Checks::new();
        let decision = capability.check_action(
            Some(&grants.get("pax")),
            "bus_post",
            None,
            None,
        );
        c.check(
            "allowed-bus-post",
            decision.as_ref().map(|d| d.get("allowed").truthy()).unwrap_or(false),
            &decision.map(|d| d.py_repr()).unwrap_or_else(|| "None".to_string()),
        );
        let decision = capability.check_action(
            Some(&grants.get("milo")),
            "network",
            None,
            None,
        );
        c.check(
            "allowed-network",
            decision.as_ref().map(|d| d.get("allowed").truthy()).unwrap_or(false),
            &decision.map(|d| d.py_repr()).unwrap_or_else(|| "None".to_string()),
        );
        let decision = capability.check_action(
            Some(&grants.get("pax")),
            "write_file",
            Some("plan/lanes/PAX.md"),
            None,
        );
        c.check(
            "allowed-write-inside",
            decision.as_ref().map(|d| d.get("allowed").truthy()).unwrap_or(false),
            &decision.map(|d| d.py_repr()).unwrap_or_else(|| "None".to_string()),
        );
        phases.push(if c.all {
            PhaseResult::pass("allowed", "")
        } else {
            PhaseResult::fail("allowed", "")
        });
        lines.extend(c.lines);
    }

    // refused
    {
        let mut c = Checks::new();
        let cases: [(&str, &str, Option<&str>, &str, &str); 7] = [
            ("milo", "bus_post", None, "bus_post", "capability not granted"),
            ("milo", "spend", None, "spend", "capability not granted"),
            (
                "pax",
                "write_file",
                Some("crew/milo/notes.md"),
                "write:crew/milo/notes.md",
                "write path outside grant",
            ),
            (
                "milo",
                "write_file",
                Some("crew/milo/../pax/x.md"),
                "write:crew/pax/x.md",
                "write path outside grant",
            ),
            ("milo", "write_file", None, "write_file", "no file path given"),
            ("ghost", "bus_post", None, "bus_post", "no capability grant on file"),
            ("milo", "teleport", None, "teleport", "unknown action"),
        ];
        for (identity, action, subject, missing, reason) in cases {
            let grant = if grants.contains_key(identity) {
                Some(grants.get(identity))
            } else {
                None
            };
            let decision = capability.check_action(
                grant.as_ref(),
                action,
                subject,
                Some(identity),
            );
            let refused = match &decision {
                Some(d) => !d.get("allowed").truthy(),
                None => false,
            };
            if !refused {
                c.check(
                    &format!("refused-{}-{}", identity, action),
                    false,
                    &decision.map(|d| d.py_repr()).unwrap_or_else(|| "None".to_string()),
                );
                continue;
            }
            let decision = decision.unwrap();
            let good = decision.get("missing_capability").as_str() == Some(missing)
                && decision.get("reason").as_str() == Some(reason);
            c.check(
                &format!("refused-{}-{}", identity, action),
                good,
                &decision.py_repr(),
            );
            let alert = capability.refusal_alert(&decision, NOW);
            let text = format!(
                "{} {}",
                alert.get("explanation").py_str(),
                alert.get("suggested_fix").py_str()
            );
            let named = text.contains(identity)
                && text.contains(action)
                && text.contains(missing);
            c.check(
                &format!("explanation-names-{}-{}", identity, action),
                named,
                &text,
            );
            let note = capability.refusal_note(&decision);
            let noted = note.contains(identity)
                && note.contains(action)
                && note.contains(missing);
            c.check(
                &format!("note-names-{}-{}", identity, action),
                noted,
                &note,
            );
            if alert.get("kind").as_str() != Some("capability-refusal")
                || alert.get("severity").as_str() != Some("warning")
            {
                c.check(
                    &format!("alert-shape-{}-{}", identity, action),
                    false,
                    &alert.py_repr(),
                );
            }
        }
        phases.push(if c.all {
            PhaseResult::pass("refused", "")
        } else {
            PhaseResult::fail("refused", "")
        });
        lines.extend(c.lines);
    }

    // tick
    {
        let mut c = Checks::new();
        let attempt = |pairs: Vec<(&str, Value)>| Value::obj(pairs);
        let attempts = Value::List(vec![
            attempt(vec![
                ("identity", Value::s("milo")),
                ("action", Value::s("bus_post")),
                ("subject", Value::Null),
            ]),
            attempt(vec![
                ("identity", Value::s("milo")),
                ("action", Value::s("spend")),
                ("subject", Value::Null),
            ]),
            attempt(vec![
                ("identity", Value::s("pax")),
                ("action", Value::s("bus_post")),
                ("subject", Value::Null),
            ]),
            attempt(vec![
                ("identity", Value::s("milo")),
                ("action", Value::s("write_file")),
                ("subject", Value::s("crew/milo/notes.md")),
            ]),
            attempt(vec![
                ("identity", Value::s("milo")),
                ("action", Value::s("bus_post")),
                ("subject", Value::Null),
            ]),
            Value::s("not-a-dict"),
            attempt(vec![
                ("identity", Value::s("milo")),
                ("action", Value::s("")),
                ("subject", Value::Null),
            ]),
        ]);
        let attempts_before = attempts.clone();
        let grants_before = grants.clone();
        let mut journal: Vec<Value> = Vec::new();
        let first = capability.capability_tick(&attempts, &grants, &journal, NOW);
        journal.extend(first.clone());
        let second = capability.capability_tick(&attempts, &grants, &journal, NOW + 60);
        c.check("tick-count", first.len() == 2, &Value::List(first.clone()).py_repr());
        c.check(
            "tick-second-silent",
            second.is_empty(),
            &Value::List(second).py_repr(),
        );
        c.check(
            "tick-inputs-immutable",
            attempts == attempts_before && grants == grants_before,
            "inputs mutated",
        );
        let brief = capability.brief_lines(&first);
        c.check(
            "brief-lines",
            brief.len() == 2
                && brief[0].contains("milo")
                && brief[0].contains("bus_post"),
            &format!("{:?}", brief),
        );
        phases.push(if c.all {
            PhaseResult::pass("tick", "")
        } else {
            PhaseResult::fail("tick", "")
        });
        lines.extend(c.lines);
    }

    // alert-record
    {
        let mut c = Checks::new();
        let decision = capability
            .check_action(Some(&grants.get("milo")), "bus_post", None, None)
            .unwrap_or(Value::Null);
        let alert = capability.refusal_alert(&decision, NOW);
        // The source lets a ValueError from build_alert_record
        // escape the phase (a crash, exit 1); the port records
        // the four record checks as failed with the error as
        // detail instead — same verdict, no traceback.
        let record = match records.build_alert_record(&alert, "fixture-room", Some(NOW)) {
            Ok(record) => record,
            Err(exc) => {
                for name in [
                    "record-kind",
                    "record-status-open",
                    "record-id-is-dedupe",
                    "record-explanation-names",
                ] {
                    c.check(name, false, &exc);
                }
                phases.push(PhaseResult::fail("alert-record", ""));
                lines.extend(c.lines);
                return finish(phases, lines);
            }
        };
        c.check(
            "record-kind",
            record.get("kind").as_str() == Some("capability-refusal"),
            &record.py_repr(),
        );
        c.check(
            "record-status-open",
            record.get("status").as_str() == Some("open"),
            &record.py_repr(),
        );
        c.check(
            "record-id-is-dedupe",
            record.get("id") == alert.get("dedupe_key"),
            &record.py_repr(),
        );
        c.check(
            "record-explanation-names",
            record.get("explanation").py_str().contains("milo")
                && record.get("explanation").py_str().contains("bus_post"),
            &record.py_repr(),
        );
        phases.push(if c.all {
            PhaseResult::pass("alert-record", "")
        } else {
            PhaseResult::fail("alert-record", "")
        });
        lines.extend(c.lines);
    }

    // no-push
    {
        let mut c = Checks::new();
        let banned = ["push.py", "bus_post(", "announce(", "post_to_bus", "redis", "socket"];
        let found: Vec<&str> = banned
            .iter()
            .copied()
            .filter(|word| capability_source.contains(word))
            .collect();
        c.check("no-push-path", found.is_empty(), &format!("{:?}", found));
        phases.push(if c.all {
            PhaseResult::pass("no-push", "")
        } else {
            PhaseResult::fail("no-push", "")
        });
        lines.extend(c.lines);
    }

    let passed = phases.iter().filter(|p| p.pass).count();
    lines.push(format!(
        "capability_refusal: {}/{} phases PASS",
        passed,
        phases.len()
    ));
    finish(phases, lines)
}

fn finish(phases: Vec<PhaseResult>, lines: Vec<String>) -> DrillOutcome {
    DrillOutcome {
        report: DrillReport::new("capability_refusal", phases),
        lines,
    }
}
