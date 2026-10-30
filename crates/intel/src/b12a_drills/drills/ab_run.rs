//! Port of `os/intel/drills/ab_run.py` — OS-106 drill.
//!
//! One A/B result for the demo's one comparison (bare launch
//! vs mind image): the same jobs, both versions, times and
//! acceptance outcomes recorded; at least one observed stall
//! correctly attributed as an image defect, with the journal
//! evidence named. The drill runs the comparison in the
//! OS-105 shape on fixtures — it never runs a live agent and
//! no booted test image is claimed (see the source
//! docstring). The logic under test is `intel/abrun` (the
//! sibling module in this subtree); the banned-import check
//! reads that module's source text, passed in by the harness
//! (the Rust analog of the source's ast walk: the abrun port
//! must carry no process/network/http/redis path).

use super::DrillOutcome;
use crate::b12a_drills::abrun;
use crate::b12a_drills::value::Value;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn bare_image() -> Value {
    Value::obj(vec![
        ("name", Value::s("bare")),
        ("version", Value::s("bare")),
        ("skills", Value::List(vec![])),
        ("instructions", Value::List(vec![])),
        ("brief", Value::s("thin")),
    ])
}

pub fn mind_image() -> Value {
    Value::obj(vec![
        ("name", Value::s("mind")),
        ("version", Value::s("mind-v1")),
        (
            "skills",
            Value::List(vec![Value::s("git-review"), Value::s("brief-read")]),
        ),
        (
            "instructions",
            Value::List(vec![Value::s("verify acceptance before closing")]),
        ),
        ("brief", Value::s("full")),
    ])
}

pub fn jobs() -> Vec<String> {
    ["job-a", "job-b", "job-c", "job-d"]
        .iter()
        .map(|s| s.to_string())
        .collect()
}

/// JOBS as the Value list `run_comparison` takes.
pub fn jobs_value() -> Value {
    Value::List(jobs().iter().map(|j| Value::s(j)).collect())
}

fn stall(pairs: Vec<(&str, Value)>) -> Value {
    Value::obj(pairs)
}

fn run_row(job: &str, seconds: i64, outcome: &str, stalls: Vec<Value>) -> Value {
    Value::obj(vec![
        ("job", Value::s(job)),
        ("seconds", Value::Int(seconds)),
        ("outcome", Value::s(outcome)),
        ("stalls", Value::List(stalls)),
    ])
}

/// The RUNS fixture, verbatim.
pub fn runs() -> Value {
    let worker_died = |job: &str| {
        stall(vec![
            ("job", Value::s(job)),
            ("reason", Value::s("worker died")),
            (
                "journal",
                Value::List(vec![Value::s("worker process died mid-job")]),
            ),
            ("worker_cause", Value::s("worker died")),
        ])
    };
    Value::obj(vec![
        (
            "bare",
            Value::obj(vec![
                (
                    "job-a",
                    run_row(
                        "job-a",
                        420,
                        "fail",
                        vec![stall(vec![
                            ("job", Value::s("job-a")),
                            ("reason", Value::s("stalled waiting for a skill")),
                            (
                                "journal",
                                Value::List(vec![Value::s(
                                    "worker stalled: needs skill git-review to review the patch",
                                )]),
                            ),
                            ("missing_skill", Value::s("git-review")),
                        ])],
                    ),
                ),
                (
                    "job-b",
                    run_row(
                        "job-b",
                        300,
                        "fail",
                        vec![stall(vec![
                            ("job", Value::s("job-b")),
                            ("reason", Value::s("stalled for context")),
                            (
                                "journal",
                                Value::List(vec![Value::s(
                                    "worker stalled: no repo context in the brief",
                                )]),
                            ),
                            ("thin_brief", Value::Bool(true)),
                        ])],
                    ),
                ),
                (
                    "job-c",
                    run_row("job-c", 200, "fail", vec![worker_died("job-c")]),
                ),
                ("job-d", run_row("job-d", 180, "pass", vec![])),
            ]),
        ),
        (
            "mind-v1",
            Value::obj(vec![
                ("job-a", run_row("job-a", 120, "pass", vec![])),
                ("job-b", run_row("job-b", 90, "pass", vec![])),
                (
                    "job-c",
                    run_row("job-c", 200, "fail", vec![worker_died("job-c")]),
                ),
                ("job-d", run_row("job-d", 60, "pass", vec![])),
            ]),
        ),
    ])
}

/// The IMAGES fixture: version -> image.
pub fn images() -> Value {
    Value::obj(vec![
        ("bare", bare_image()),
        ("mind-v1", mind_image()),
    ])
}

fn check(phases: &mut Vec<PhaseResult>, name: &str, ok: bool, detail: &str) {
    if ok {
        phases.push(PhaseResult::pass(name, ""));
    } else {
        phases.push(PhaseResult::fail(name, detail.to_string()));
    }
}

fn defects_for(result: &Value, job: &str, version: &str) -> Vec<Value> {
    result
        .get("defects")
        .as_list()
        .map(|items| {
            items
                .iter()
                .filter(|d| {
                    d.get("job").as_str() == Some(job)
                        && d.get("version").as_str() == Some(version)
                })
                .cloned()
                .collect()
        })
        .unwrap_or_default()
}

/// Run all phases. `abrun_source` is the abrun port's own
/// source text for the banned-import phase (the harness
/// passes include_str! of the sibling module).
pub fn run(abrun_source: &str) -> DrillOutcome {
    let mut phases: Vec<PhaseResult> = Vec::new();
    let job_list = jobs();
    let runs_fixture = runs();
    let images_fixture = images();

    // comparison-table
    {
        let result = abrun::run_comparison(&jobs_value(), &runs_fixture, &images_fixture);
        let mut failure: Option<String> = None;
        let result_jobs: Vec<String> = result
            .get("jobs")
            .as_list()
            .map(|items| items.iter().map(|v| v.py_str()).collect())
            .unwrap_or_default();
        if result_jobs != job_list {
            failure = Some("job list changed".to_string());
        }
        let versions: Vec<String> = result
            .get("versions")
            .as_list()
            .map(|items| items.iter().map(|v| v.py_str()).collect())
            .unwrap_or_default();
        if failure.is_none() && versions != vec!["bare".to_string(), "mind-v1".to_string()] {
            failure = Some("version list changed".to_string());
        }
        if failure.is_none() {
            if let Some(rows) = result.get("table").as_list() {
                for row in rows {
                    for version in ["bare", "mind-v1"] {
                        let entry = row.get("versions").get(version);
                        if entry.get("seconds").is_null()
                            || entry.get("outcome").as_str() == Some("missing")
                        {
                            failure = Some(format!(
                                "row {} {} unrecorded",
                                row.get("job").py_str(),
                                version
                            ));
                            break;
                        }
                    }
                    if failure.is_some() {
                        break;
                    }
                }
            }
        }
        let totals = result.get("totals");
        if failure.is_none() && totals.get("bare").get("seconds").as_int() != Some(1100) {
            failure = Some("bare total not 1100".to_string());
        }
        if failure.is_none() && totals.get("mind-v1").get("seconds").as_int() != Some(470) {
            failure = Some("mind total not 470".to_string());
        }
        if failure.is_none()
            && !(totals.get("mind-v1").get("passed").as_int() == Some(3)
                && totals.get("bare").get("passed").as_int() == Some(1))
        {
            failure = Some("pass counts wrong".to_string());
        }
        if failure.is_none() && abrun::measurement_records(&result).len() != 8 {
            failure = Some("not 8 measurements".to_string());
        }
        check(
            &mut phases,
            "comparison-table",
            failure.is_none(),
            failure.as_deref().unwrap_or(""),
        );
    }

    // missing-skill
    {
        let result = abrun::run_comparison(&jobs_value(), &runs_fixture, &images_fixture);
        let defects = defects_for(&result, "job-a", "bare");
        let mut failure: Option<String> = None;
        if defects.len() != 1 {
            failure = Some("job-a defect count wrong".to_string());
        } else {
            let defect = defects[0].clone();
            if defect.get("kind").as_str() != Some("missing-skill") {
                failure = Some("kind not missing-skill".to_string());
            } else if !defect
                .get("evidence")
                .as_list()
                .map(|lines| lines.iter().any(|l| l.py_str().contains("git-review")))
                .unwrap_or(false)
            {
                failure = Some("evidence lacks the skill".to_string());
            }
        }
        if failure.is_none()
            && result
                .get("defects")
                .as_list()
                .map(|items| {
                    items.iter().any(|d| {
                        d.get("job").as_str() == Some("job-a")
                            && d.get("version").as_str() == Some("mind-v1")
                    })
                })
                .unwrap_or(false)
        {
            failure = Some("mind-v1 blamed too".to_string());
        }
        check(
            &mut phases,
            "missing-skill",
            failure.is_none(),
            failure.as_deref().unwrap_or(""),
        );
    }

    // thin-brief
    {
        let result = abrun::run_comparison(&jobs_value(), &runs_fixture, &images_fixture);
        let defects = defects_for(&result, "job-b", "bare");
        let mut failure: Option<String> = None;
        if defects.len() != 1 || defects[0].get("kind").as_str() != Some("thin-brief") {
            failure = Some("job-b defect not thin-brief".to_string());
        } else if !defects[0]
            .get("evidence")
            .as_list()
            .map(|lines| lines.iter().any(|l| l.py_str().contains("repo context")))
            .unwrap_or(false)
        {
            failure = Some("evidence lacks the context line".to_string());
        }
        check(
            &mut phases,
            "thin-brief",
            failure.is_none(),
            failure.as_deref().unwrap_or(""),
        );
    }

    // bad-instruction
    {
        let bad_image = Value::obj(vec![
            ("name", Value::s("mind")),
            ("version", Value::s("mind-v0")),
            ("skills", Value::List(vec![Value::s("git-review")])),
            (
                "instructions",
                Value::List(vec![Value::s("skip acceptance checks")]),
            ),
            ("brief", Value::s("full")),
        ]);
        let stall_fixture = stall(vec![
            ("job", Value::s("job-x")),
            ("reason", Value::s("acceptance skipped")),
            (
                "journal",
                Value::List(vec![Value::s(
                    "worker followed instruction skip acceptance checks and closed early",
                )]),
            ),
            ("bad_instruction", Value::s("skip acceptance checks")),
        ]);
        let (kind, detail, evidence) = abrun::attribute_stall(&stall_fixture, &bad_image);
        let mut failure: Option<String> = None;
        if kind != "image-defect" || detail.as_deref() != Some("bad-instruction") {
            failure = Some("carried fault not a defect".to_string());
        } else if !evidence
            .iter()
            .any(|l| l.py_str().contains("skip acceptance checks"))
        {
            failure = Some("evidence lacks instruction".to_string());
        }
        if failure.is_none() {
            let mut stranger = stall_fixture.clone();
            stranger.set("bad_instruction", Value::s("never in this image"));
            let (kind2, _, _) = abrun::attribute_stall(&stranger, &bad_image);
            if kind2 == "image-defect" {
                failure = Some("uncarried fault blamed".to_string());
            }
        }
        check(
            &mut phases,
            "bad-instruction",
            failure.is_none(),
            failure.as_deref().unwrap_or(""),
        );
    }

    // worker-failure
    {
        let result = abrun::run_comparison(&jobs_value(), &runs_fixture, &images_fixture);
        let mut failure: Option<String> = None;
        if result
            .get("defects")
            .as_list()
            .map(|items| items.iter().any(|d| d.get("job").as_str() == Some("job-c")))
            .unwrap_or(false)
        {
            failure = Some("job-c blamed on an image".to_string());
        }
        if failure.is_none() {
            for version in ["bare", "mind-v1"] {
                let stall_fixture = runs_fixture
                    .get(version)
                    .get("job-c")
                    .get("stalls")
                    .as_list()
                    .and_then(|items| items.first().cloned())
                    .unwrap_or(Value::Null);
                let (kind, detail, _) =
                    abrun::attribute_stall(&stall_fixture, &images_fixture.get(version));
                if (kind.as_str(), detail.as_str()) != ("worker-failure", "worker died") {
                    failure = Some(format!("job-c {} not worker-failure", version));
                    break;
                }
            }
        }
        if failure.is_none() {
            let carried = stall(vec![
                ("job", Value::s("job-y")),
                ("reason", Value::s("stalled")),
                (
                    "journal",
                    Value::List(vec![Value::s("worker stalled: needs skill git-review")]),
                ),
                ("missing_skill", Value::s("git-review")),
            ]);
            let (kind, _, _) = abrun::attribute_stall(&carried, &mind_image());
            if kind == "image-defect" {
                failure = Some("carried skill blamed".to_string());
            }
        }
        check(
            &mut phases,
            "worker-failure",
            failure.is_none(),
            failure.as_deref().unwrap_or(""),
        );
    }

    // malformed-and-immutable
    {
        let jobs_before = job_list.clone();
        let runs_before = runs_fixture.clone();
        let mut failure: Option<String> = None;
        let empty = abrun::run_comparison(&Value::List(vec![]), &Value::Null, &Value::Null);
        if !(empty.get("jobs").as_list().map(|j| j.is_empty()).unwrap_or(false)
            && empty.get("defects").as_list().map(|d| d.is_empty()).unwrap_or(false))
        {
            failure = Some("malformed input invented a result".to_string());
        }
        if failure.is_none() {
            let result = abrun::run_comparison(&jobs_value(), &runs_fixture, &images_fixture);
            let note = abrun::revision_note(&result.get("defects"));
            let changes: Vec<String> = note
                .get("next_version_changes")
                .as_list()
                .map(|items| items.iter().map(|v| v.py_str()).collect())
                .unwrap_or_default();
            if !changes.iter().any(|c| c.contains("git-review")) {
                failure = Some("note lacks the skill add".to_string());
            } else if !changes.iter().any(|c| c.contains("brief")) {
                failure = Some("note lacks the brief change".to_string());
            } else {
                let note_text = note.get("note").py_str();
                if note_text.contains("auto") && !note_text.contains("nothing auto-applies") {
                    failure = Some("note claims applying".to_string());
                }
            }
        }
        if failure.is_none() && (job_list != jobs_before || runs_fixture != runs_before) {
            failure = Some("inputs mutated".to_string());
        }
        if failure.is_none() {
            // The source's ast walk over abrun.py, mapped to
            // the port: banned roots are socket/network
            // (std::net), urllib/requests (an HTTP client),
            // redis, and subprocess (std::process).
            let banned = [
                "std::net",
                "std::process",
                "reqwest",
                "ureq",
                "redis",
                "TcpStream",
                "UdpSocket",
            ];
            if banned.iter().any(|b| abrun_source.contains(b)) {
                failure = Some("module imports a banned module".to_string());
            }
        }
        check(
            &mut phases,
            "malformed-and-immutable",
            failure.is_none(),
            failure.as_deref().unwrap_or(""),
        );
    }

    let mut lines: Vec<String> = phases
        .iter()
        .map(|p| {
            if p.pass {
                format!("{}: PASS", p.name)
            } else {
                format!("{}: FAIL ({})", p.name, p.detail)
            }
        })
        .collect();
    let passed = phases.iter().filter(|p| p.pass).count();
    lines.push(format!("{}/{} phases PASS", passed, phases.len()));
    DrillOutcome {
        report: DrillReport::new("ab_run", phases),
        lines,
    }
}
