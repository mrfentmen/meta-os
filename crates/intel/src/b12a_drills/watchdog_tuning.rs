//! Port of `os/intel/evals/watchdog_tuning.py` — WDG-027:
//! watchdog tuning run, tick() over every detector fixture.
//!
//! Standalone harness, deliberately NOT the unit tests: one
//! positive and one (or more) negative snapshot per detector,
//! ticked at now=10000 through the B21 `Watchdog` trait, with
//! false positives / false negatives tabulated. Exit 0 only
//! when every case matches its expected kinds exactly — in
//! particular the quiet fixture must yield zero alerts, which
//! is the WDG-027 pass requirement. Fixtures are the suite's
//! hand-written snapshot shapes (no separate synthetic-history
//! files exist, per the source's own note).

use super::deps::Watchdog;
use super::value::Value;

pub const NOW: i64 = 10000;

fn claimed(job_id: &str, nick: &str, extra: Vec<(&str, Value)>) -> Value {
    let mut pairs = vec![
        ("id", Value::s(job_id)),
        ("title", Value::s(&format!("job {}", job_id))),
        ("status", Value::s("claimed")),
        ("claim", Value::s(nick)),
        ("claimed_at", Value::Int(9990)),
    ];
    pairs.extend(extra);
    Value::obj(pairs)
}

fn caps(nicks: &[&str]) -> Value {
    Value::obj(
        nicks
            .iter()
            .map(|n| (*n, Value::obj(vec![("caps", Value::s("build"))])))
            .collect(),
    )
}

fn job(pairs: Vec<(&str, Value)>) -> Value {
    Value::obj(pairs)
}

/// One tuning case: (fixture name, detector under test,
/// snapshot, expected kinds).
pub struct Case {
    pub name: &'static str,
    pub detector: &'static str,
    pub snapshot: Value,
    pub expected: Vec<&'static str>,
}

fn case(
    name: &'static str,
    detector: &'static str,
    snapshot: Value,
    expected: Vec<&'static str>,
) -> Case {
    Case {
        name,
        detector,
        snapshot,
        expected,
    }
}

/// The CASES table, verbatim from the source.
pub fn cases() -> Vec<Case> {
    vec![
        // Quiet / healthy: zero alerts is the WDG-027 pass requirement.
        case("quiet-empty", "tick", Value::obj(vec![]), vec![]),
        case(
            "healthy-busy",
            "tick",
            Value::obj(vec![
                (
                    "messages",
                    Value::List(vec![Value::obj(vec![
                        ("nick", Value::s("pax")),
                        ("text", Value::s("working on it")),
                    ])]),
                ),
                (
                    "jobs",
                    Value::List(vec![job(vec![
                        ("id", Value::s("1")),
                        ("title", Value::s("demo job")),
                        ("status", Value::s("claimed")),
                        ("claim", Value::s("pax")),
                        ("claimed_at", Value::Int(9900)),
                    ])]),
                ),
                ("presence", Value::List(vec![Value::s("pax")])),
                ("caps", caps(&["pax"])),
            ]),
            vec![],
        ),
        // WDG-002 presence-stall.
        case(
            "presence-stall-positive",
            "WDG-002",
            Value::obj(vec![
                (
                    "jobs",
                    Value::List(vec![job(vec![
                        ("id", Value::s("7")),
                        ("title", Value::s("demo job")),
                        ("status", Value::s("claimed")),
                        ("claim", Value::s("pax")),
                        ("claimed_at", Value::Int(9340)),
                    ])]),
                ),
                ("presence", Value::List(vec![Value::s("hana")])),
                ("caps", caps(&["pax"])),
            ]),
            vec!["presence-stall"],
        ),
        case(
            "presence-stall-negative-present",
            "WDG-002",
            Value::obj(vec![
                (
                    "jobs",
                    Value::List(vec![job(vec![
                        ("id", Value::s("7")),
                        ("title", Value::s("demo job")),
                        ("status", Value::s("claimed")),
                        ("claim", Value::s("pax")),
                        ("claimed_at", Value::Int(9340)),
                    ])]),
                ),
                (
                    "presence",
                    Value::List(vec![Value::s("pax"), Value::s("hana")]),
                ),
                ("caps", caps(&["pax"])),
            ]),
            // present-but-idle is WDG-003, not WDG-002
            vec!["progress-stall"],
        ),
        case(
            "presence-stall-negative-fresh",
            "WDG-002",
            Value::obj(vec![
                (
                    "jobs",
                    Value::List(vec![job(vec![
                        ("id", Value::s("7")),
                        ("title", Value::s("demo job")),
                        ("status", Value::s("claimed")),
                        ("claim", Value::s("pax")),
                        ("claimed_at", Value::Int(9900)),
                    ])]),
                ),
                ("presence", Value::List(vec![Value::s("hana")])),
                ("caps", caps(&["pax"])),
            ]),
            vec![],
        ),
        case(
            "presence-stall-negative-walkon",
            "WDG-002/WDG-025",
            Value::obj(vec![
                (
                    "jobs",
                    Value::List(vec![job(vec![
                        ("id", Value::s("7")),
                        ("title", Value::s("demo job")),
                        ("status", Value::s("claimed")),
                        ("claim", Value::s("pax")),
                        ("claimed_at", Value::Int(9340)),
                    ])]),
                ),
                ("presence", Value::List(vec![Value::s("hana")])),
                (
                    "caps",
                    Value::obj(vec![("hana", Value::obj(vec![]))]),
                ),
            ]),
            vec![],
        ),
        // WDG-003 progress-stall.
        case(
            "progress-stall-positive",
            "WDG-003",
            Value::obj(vec![
                (
                    "jobs",
                    Value::List(vec![job(vec![
                        ("id", Value::s("7")),
                        ("title", Value::s("demo job")),
                        ("status", Value::s("claimed")),
                        ("claim", Value::s("pax")),
                        ("claimed_at", Value::Int(9000)),
                        ("last_progress", Value::Int(9340)),
                    ])]),
                ),
                (
                    "presence",
                    Value::List(vec![Value::s("pax"), Value::s("hana")]),
                ),
                ("caps", caps(&["pax"])),
            ]),
            vec!["progress-stall"],
        ),
        case(
            "progress-stall-negative-fresh",
            "WDG-003",
            Value::obj(vec![
                (
                    "jobs",
                    Value::List(vec![job(vec![
                        ("id", Value::s("7")),
                        ("title", Value::s("demo job")),
                        ("status", Value::s("claimed")),
                        ("claim", Value::s("pax")),
                        ("claimed_at", Value::Int(9000)),
                        ("last_progress", Value::Int(9900)),
                    ])]),
                ),
                (
                    "presence",
                    Value::List(vec![Value::s("pax"), Value::s("hana")]),
                ),
                ("caps", caps(&["pax"])),
            ]),
            vec![],
        ),
        case(
            "progress-stall-negative-absent",
            "WDG-003",
            Value::obj(vec![
                (
                    "jobs",
                    Value::List(vec![job(vec![
                        ("id", Value::s("7")),
                        ("title", Value::s("demo job")),
                        ("status", Value::s("claimed")),
                        ("claim", Value::s("pax")),
                        ("claimed_at", Value::Int(9000)),
                        ("last_progress", Value::Int(9340)),
                    ])]),
                ),
                ("presence", Value::List(vec![Value::s("hana")])),
                ("caps", caps(&["pax"])),
            ]),
            vec!["presence-stall"],
        ),
        // WDG-004 lease-risk.
        case(
            "lease-risk-positive",
            "WDG-004",
            Value::obj(vec![
                (
                    "jobs",
                    Value::List(vec![job(vec![
                        ("id", Value::s("9")),
                        ("title", Value::s("lease job")),
                        ("status", Value::s("claimed")),
                        ("claim", Value::s("pax")),
                        ("claimed_at", Value::Int(9900)),
                        ("lease_until", Value::Int(10240)),
                    ])]),
                ),
                ("presence", Value::List(vec![Value::s("pax")])),
                ("caps", caps(&["pax"])),
            ]),
            vec!["lease-risk"],
        ),
        case(
            "lease-risk-negative-live-heartbeat",
            "WDG-004",
            Value::obj(vec![
                (
                    "jobs",
                    Value::List(vec![job(vec![
                        ("id", Value::s("9")),
                        ("title", Value::s("lease job")),
                        ("status", Value::s("claimed")),
                        ("claim", Value::s("pax")),
                        ("claimed_at", Value::Int(9900)),
                        ("lease_until", Value::Int(10090)),
                        ("lease", Value::Int(120)),
                    ])]),
                ),
                ("presence", Value::List(vec![Value::s("pax")])),
                ("caps", caps(&["pax"])),
            ]),
            vec![],
        ),
        case(
            "lease-risk-negative-far-expiry",
            "WDG-004",
            Value::obj(vec![
                (
                    "jobs",
                    Value::List(vec![job(vec![
                        ("id", Value::s("9")),
                        ("title", Value::s("lease job")),
                        ("status", Value::s("claimed")),
                        ("claim", Value::s("pax")),
                        ("claimed_at", Value::Int(9900)),
                        ("lease_until", Value::Int(11000)),
                    ])]),
                ),
                ("presence", Value::List(vec![Value::s("pax")])),
                ("caps", caps(&["pax"])),
            ]),
            vec![],
        ),
        // WDG-005 dead-dep / WDG-006 missing-dep.
        case(
            "dead-dep-positive",
            "WDG-005",
            Value::obj(vec![(
                "jobs",
                Value::List(vec![
                    job(vec![
                        ("id", Value::s("2")),
                        ("title", Value::s("blocked job")),
                        ("status", Value::s("open")),
                        ("deps", Value::s("1")),
                    ]),
                    job(vec![
                        ("id", Value::s("1")),
                        ("title", Value::s("dep job")),
                        ("status", Value::s("blocked")),
                        ("note", Value::s("waiting on vendor API key")),
                    ]),
                ]),
            )]),
            vec!["dead-dep"],
        ),
        case(
            "dead-dep-negative-live-dep",
            "WDG-005",
            Value::obj(vec![(
                "jobs",
                Value::List(vec![
                    job(vec![
                        ("id", Value::s("2")),
                        ("title", Value::s("blocked job")),
                        ("status", Value::s("open")),
                        ("deps", Value::s("1")),
                    ]),
                    job(vec![
                        ("id", Value::s("1")),
                        ("title", Value::s("dep job")),
                        ("status", Value::s("open")),
                    ]),
                ]),
            )]),
            vec![],
        ),
        case(
            "missing-dep-positive",
            "WDG-006",
            Value::obj(vec![(
                "jobs",
                Value::List(vec![job(vec![
                    ("id", Value::s("2")),
                    ("title", Value::s("blocked job")),
                    ("status", Value::s("open")),
                    ("deps", Value::s("9")),
                ])]),
            )]),
            vec!["missing-dep"],
        ),
        case(
            "missing-dep-negative-existing-dep",
            "WDG-006",
            Value::obj(vec![(
                "jobs",
                Value::List(vec![
                    job(vec![
                        ("id", Value::s("2")),
                        ("title", Value::s("blocked job")),
                        ("status", Value::s("open")),
                        ("deps", Value::s("1")),
                    ]),
                    job(vec![
                        ("id", Value::s("1")),
                        ("title", Value::s("dep job")),
                        ("status", Value::s("open")),
                    ]),
                ]),
            )]),
            vec![],
        ),
        // WDG-007 file-collision.
        case(
            "file-collision-positive",
            "WDG-007",
            Value::obj(vec![
                (
                    "jobs",
                    Value::List(vec![
                        claimed(
                            "1",
                            "pax",
                            vec![("files", Value::s("intel/watchdog.py, intel/store.py"))],
                        ),
                        claimed(
                            "2",
                            "rowan",
                            vec![("files", Value::s("intel/store.py, intel/brief.py"))],
                        ),
                    ]),
                ),
                (
                    "presence",
                    Value::List(vec![Value::s("pax"), Value::s("rowan")]),
                ),
                ("caps", caps(&["pax", "rowan"])),
            ]),
            vec!["file-collision"],
        ),
        case(
            "file-collision-negative-disjoint",
            "WDG-007",
            Value::obj(vec![
                (
                    "jobs",
                    Value::List(vec![
                        claimed("1", "pax", vec![("files", Value::s("intel/watchdog.py"))]),
                        claimed("2", "rowan", vec![("files", Value::s("intel/brief.py"))]),
                    ]),
                ),
                (
                    "presence",
                    Value::List(vec![Value::s("pax"), Value::s("rowan")]),
                ),
                ("caps", caps(&["pax", "rowan"])),
            ]),
            vec![],
        ),
        case(
            "file-collision-negative-done-no-branch",
            "WDG-007",
            Value::obj(vec![
                (
                    "jobs",
                    Value::List(vec![
                        claimed("1", "pax", vec![("files", Value::s("intel/store.py"))]),
                        job(vec![
                            ("id", Value::s("2")),
                            ("title", Value::s("done job")),
                            ("status", Value::s("done")),
                            ("files", Value::s("intel/store.py")),
                        ]),
                    ]),
                ),
                ("presence", Value::List(vec![Value::s("pax")])),
                ("caps", caps(&["pax"])),
            ]),
            vec![],
        ),
        // WDG-008 attempt-exhaustion.
        case(
            "attempt-warning-positive",
            "WDG-008",
            Value::obj(vec![(
                "jobs",
                Value::List(vec![job(vec![
                    ("id", Value::s("7")),
                    ("title", Value::s("flaky job")),
                    ("status", Value::s("open")),
                    ("claim", Value::s("pax")),
                    ("attempts", Value::Int(2)),
                    ("max_attempts", Value::Int(3)),
                ])]),
            )]),
            vec!["attempt-warning"],
        ),
        case(
            "attempt-exhaustion-positive",
            "WDG-008",
            Value::obj(vec![(
                "jobs",
                Value::List(vec![job(vec![
                    ("id", Value::s("7")),
                    ("title", Value::s("flaky job")),
                    ("status", Value::s("open")),
                    ("claim", Value::s("pax")),
                    ("attempts", Value::Int(3)),
                    ("max_attempts", Value::Int(3)),
                ])]),
            )]),
            vec!["attempt-exhaustion"],
        ),
        case(
            "attempt-negative-early",
            "WDG-008",
            Value::obj(vec![(
                "jobs",
                Value::List(vec![job(vec![
                    ("id", Value::s("7")),
                    ("title", Value::s("flaky job")),
                    ("status", Value::s("open")),
                    ("claim", Value::s("pax")),
                    ("attempts", Value::Int(0)),
                    ("max_attempts", Value::Int(3)),
                ])]),
            )]),
            vec![],
        ),
        case(
            "attempt-negative-done",
            "WDG-008",
            Value::obj(vec![(
                "jobs",
                Value::List(vec![job(vec![
                    ("id", Value::s("7")),
                    ("title", Value::s("flaky job")),
                    ("status", Value::s("done")),
                    ("claim", Value::s("pax")),
                    ("attempts", Value::Int(3)),
                    ("max_attempts", Value::Int(3)),
                ])]),
            )]),
            vec![],
        ),
        // WDG-009 silent-room (info only, never an alert severity).
        case(
            "silent-room-positive",
            "WDG-009",
            Value::obj(vec![
                (
                    "jobs",
                    Value::List(vec![job(vec![
                        ("id", Value::s("1")),
                        ("title", Value::s("claimed job")),
                        ("status", Value::s("claimed")),
                        ("claim", Value::s("pax")),
                        ("claimed_at", Value::Int(1000)),
                    ])]),
                ),
                (
                    "messages",
                    Value::List(vec![Value::obj(vec![
                        ("nick", Value::s("pax")),
                        ("text", Value::s("starting")),
                        ("ts", Value::Int(1000)),
                    ])]),
                ),
            ]),
            vec!["silent-room"],
        ),
        case(
            "silent-room-negative-fresh-message",
            "WDG-009",
            Value::obj(vec![
                (
                    "jobs",
                    Value::List(vec![job(vec![
                        ("id", Value::s("1")),
                        ("title", Value::s("claimed job")),
                        ("status", Value::s("claimed")),
                        ("claim", Value::s("pax")),
                        ("claimed_at", Value::Int(1000)),
                    ])]),
                ),
                (
                    "messages",
                    Value::List(vec![Value::obj(vec![
                        ("nick", Value::s("pax")),
                        ("text", Value::s("update")),
                        ("ts", Value::Int(8200)),
                    ])]),
                ),
            ]),
            vec![],
        ),
        case(
            "silent-room-negative-no-claims",
            "WDG-009",
            Value::obj(vec![
                (
                    "jobs",
                    Value::List(vec![job(vec![
                        ("id", Value::s("1")),
                        ("title", Value::s("open job")),
                        ("status", Value::s("open")),
                    ])]),
                ),
                (
                    "messages",
                    Value::List(vec![Value::obj(vec![
                        ("nick", Value::s("pax")),
                        ("text", Value::s("done for now")),
                        ("ts", Value::Int(1000)),
                    ])]),
                ),
            ]),
            vec![],
        ),
    ]
}

fn sorted_set(items: &[String]) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    for item in items {
        if !out.contains(item) {
            out.push(item.clone());
        }
    }
    out.sort();
    out
}

fn list_repr(items: &[String]) -> String {
    Value::List(items.iter().map(|s| Value::s(s)).collect()).py_repr()
}

/// The script's main(): tabulate every case through
/// `watchdog.tick`, print the table, return (exit code, lines).
pub fn execute<W: Watchdog>(watchdog: &W) -> (i32, Vec<String>) {
    let mut lines = vec![format!(
        "{:<38} {:<14} {:<22} {:<22} {}",
        "fixture", "detector", "expected", "got", "verdict"
    )];
    let mut bad = 0usize;
    let all = cases();
    let total = all.len();
    for case in &all {
        let alerts = watchdog.tick(&case.snapshot, Some(NOW));
        let got: Vec<String> = alerts.iter().map(|a| a.get("kind").py_str()).collect();
        let expected: Vec<String> = case.expected.iter().map(|s| s.to_string()).collect();
        let false_pos: Vec<String> = sorted_set(&got)
            .into_iter()
            .filter(|k| !expected.contains(k))
            .collect();
        let false_neg: Vec<String> = sorted_set(&expected)
            .into_iter()
            .filter(|k| !got.contains(k))
            .collect();
        let verdict = if false_pos.is_empty() && false_neg.is_empty() {
            "OK".to_string()
        } else {
            format!(
                "FP={} FN={}",
                list_repr(&false_pos),
                list_repr(&false_neg)
            )
        };
        if verdict != "OK" {
            bad += 1;
        }
        let expected_cell = if expected.is_empty() {
            "-".to_string()
        } else {
            expected.join(",")
        };
        let got_cell = if got.is_empty() {
            "-".to_string()
        } else {
            got.join(",")
        };
        lines.push(format!(
            "{:<38} {:<14} {:<22} {:<22} {}",
            case.name, case.detector, expected_cell, got_cell, verdict
        ));
    }
    lines.push(format!("cases={} mismatches={}", total, bad));
    (if bad > 0 { 1 } else { 0 }, lines)
}
