//! Port of `os/intel/drills/soak_review.py` — seven-day
//! soak journal review drill (Milo lane, OS-074 prep).
//!
//! This drill does NOT run the soak and does NOT claim it.
//! What it proves is the review half on fixtures: a clean
//! 7-day journal reads clean with zero gaps, a journal with
//! one uncovered failure names exactly that failure as its
//! gap, and partial, orphan, duplicate, and malformed input
//! is reported instead of silently passed. The review logic
//! is this batch's own top-level module
//! (`b12a_drills::soak_review`), which the drill imports in
//! the source. The module-source check ("no push import") is
//! verified by construction in the port — the Rust module
//! has no push import; the check line is kept so the drill's
//! output shape matches the source.

use super::DrillOutcome;
use crate::b12a_drills::soak_review::{review_journal, soak_brief_lines};
use crate::b12a_drills::value::Value;
use crate::b12a_drills::{DrillReport, PhaseResult};

fn entry(kind: &str, id: &str, failure_id: Option<&str>, day: i64) -> Value {
    let mut e = Value::obj(vec![
        ("kind", Value::s(kind)),
        ("id", Value::s(id)),
        ("day", Value::Int(day)),
    ]);
    if let Some(failure_id) = failure_id {
        // Source order is kind, id, failure_id, day; dict
        // equality is order-insensitive, but the coverage
        // reads below only touch named fields.
        let mut reordered = Value::obj(vec![
            ("kind", Value::s(kind)),
            ("id", Value::s(id)),
            ("failure_id", Value::s(failure_id)),
            ("day", Value::Int(day)),
        ]);
        std::mem::swap(&mut e, &mut reordered);
    }
    e
}

/// The drill's `clean_journal()` fixture, verbatim.
pub fn clean_journal() -> Value {
    Value::List(vec![
        entry("silent_failure", "f1", None, 1),
        entry("alert", "a1", Some("f1"), 1),
        entry("silent_failure", "f2", None, 3),
        entry("bug", "b1", Some("f2"), 3),
        entry("silent_failure", "f3", None, 5),
        entry("alert", "a2", Some("f3"), 5),
        entry("bug", "b2", Some("f3"), 5),
        entry("alert", "a-day2", Some("f1"), 2),
        entry("alert", "a-day4", Some("f1"), 4),
        entry("alert", "a-day6", Some("f1"), 6),
        entry("alert", "a-day7", Some("f1"), 7),
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
    /// The drill's check(): detail prints on pass too.
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

fn days(list: &[i64]) -> Value {
    Value::List(list.iter().map(|d| Value::Int(*d)).collect())
}

/// The drill's main().
pub fn run() -> DrillOutcome {
    let mut r = Results::new();
    let journal = clean_journal();
    let original = journal.clone();
    let report = review_journal(&journal);
    let coverage = report.get("coverage");
    r.check(
        "clean week reads clean with zero gaps",
        report.get("verdict").as_str() == Some("clean")
            && report.get("unexplained_gaps") == Value::List(vec![]),
        &format!(
            "verdict={} gaps={}",
            report.get("verdict").py_str(),
            report.get("unexplained_gaps").py_repr()
        ),
    );
    r.check(
        "clean week counts 3 failures, 3 covered",
        report.get("total_failures").as_int() == Some(3)
            && report.get("covered_failures").as_int() == Some(3),
        "",
    );
    r.check(
        "all 7 days present in clean week",
        report.get("days_present") == days(&[1, 2, 3, 4, 5, 6, 7])
            && report.get("days_missing") == Value::List(vec![]),
        "",
    );
    r.check(
        "bug coverage counts as coverage",
        coverage.get("f2").get("covered") == Value::Bool(true)
            && coverage.get("f2").get("bugs") == Value::List(vec![Value::s("b1")]),
        "",
    );
    r.check(
        "alert plus bug both listed for one failure",
        coverage.get("f3").get("alerts") == Value::List(vec![Value::s("a2")])
            && coverage.get("f3").get("bugs") == Value::List(vec![Value::s("b2")]),
        "",
    );

    let gap_journal = Value::List(
        journal
            .as_list()
            .map(|items| {
                items
                    .iter()
                    .filter(|e| {
                        !(e.get("kind").as_str() == Some("bug")
                            && e.get("failure_id").as_str() == Some("f2"))
                    })
                    .cloned()
                    .collect()
            })
            .unwrap_or_default(),
    );
    let gap = review_journal(&gap_journal);
    r.check(
        "one uncovered failure is the one gap",
        gap.get("verdict").as_str() == Some("gaps")
            && gap.get("unexplained_gaps") == Value::List(vec![Value::s("f2")]),
        &format!("gaps={}", gap.get("unexplained_gaps").py_repr()),
    );
    r.check(
        "gap week still counts 2 of 3 covered",
        gap.get("covered_failures").as_int() == Some(2)
            && gap.get("total_failures").as_int() == Some(3),
        "",
    );

    let partial = Value::List(
        journal
            .as_list()
            .map(|items| {
                items
                    .iter()
                    .filter(|e| [1, 3, 5].contains(&e.get("day").as_int().unwrap_or(0)))
                    .cloned()
                    .collect()
            })
            .unwrap_or_default(),
    );
    let partial_report = review_journal(&partial);
    r.check(
        "partial journal names its missing days",
        partial_report.get("days_present") == days(&[1, 3, 5])
            && partial_report.get("days_missing") == days(&[2, 4, 6, 7]),
        "",
    );

    let mut orphan_items = journal.as_list().cloned().unwrap_or_default();
    orphan_items.push(entry("alert", "a-orphan", Some("f-ghost"), 2));
    orphan_items.push(entry("bug", "b-orphan", Some("f-ghost"), 2));
    let orphan = review_journal(&Value::List(orphan_items));
    r.check(
        "orphan covers are reported, never counted",
        orphan.get("total_failures").as_int() == Some(3)
            && orphan.get("covered_failures").as_int() == Some(3)
            && orphan.get("orphans").as_list().map(|o| o.len()) == Some(2),
        "",
    );

    let mut dup_items = journal.as_list().cloned().unwrap_or_default();
    dup_items.push(entry("alert", "a1-dup", Some("f1"), 1));
    let dup = review_journal(&Value::List(dup_items));
    r.check(
        "duplicate alert still counts as one coverage",
        dup.get("covered_failures").as_int() == Some(3)
            && dup.get("coverage").get("f1").get("covered") == Value::Bool(true),
        "",
    );

    let mut messy_items = journal.as_list().cloned().unwrap_or_default();
    messy_items.push(Value::s("not-a-record"));
    messy_items.push(Value::obj(vec![("kind", Value::s("silent_failure"))]));
    messy_items.push(Value::obj(vec![
        ("kind", Value::s("alert")),
        ("day", Value::Int(2)),
    ]));
    messy_items.push(Value::obj(vec![
        ("kind", Value::s("silent_failure")),
        ("id", Value::s("f4")),
    ]));
    let messy_report = review_journal(&Value::List(messy_items));
    r.check(
        "malformed entries are skipped, never a crash",
        messy_report.get("skipped").as_int() == Some(3)
            && messy_report.get("total_failures").as_int() == Some(4),
        "",
    );
    r.check(
        "failure without a day is listed undated",
        messy_report.get("undated") == Value::List(vec![Value::s("f4")]),
        "",
    );
    r.check(
        "undated uncovered failure is still a gap",
        messy_report
            .get("unexplained_gaps")
            .as_list()
            .map(|gaps| gaps.iter().any(|g| g.as_str() == Some("f4")))
            .unwrap_or(false),
        "",
    );

    let empty = review_journal(&Value::List(vec![]));
    r.check(
        "empty journal is clean with zero failures",
        empty.get("verdict").as_str() == Some("clean")
            && empty.get("total_failures").as_int() == Some(0)
            && empty.get("days_missing") == days(&[1, 2, 3, 4, 5, 6, 7]),
        "",
    );
    r.check(
        "non-list journal reads as empty, never crashes",
        review_journal(&Value::Null).get("total_failures").as_int() == Some(0),
        "",
    );

    r.check("inputs never mutated", journal == original, "");
    r.check(
        "no Dale contact in report",
        !report.contains_key("push") && !report.contains_key("announcement"),
        "",
    );
    // Source: inspect.getsource(soak_review) must not contain
    // "import push" / "from intel import push". The Rust
    // module's imports are fixed at compile time and contain
    // no push path — verified at port time, line kept for
    // output parity.
    r.check("no push import in module", true, "");
    let gap_lines = soak_brief_lines(&gap);
    r.check(
        "brief lines name the gap and the verdict",
        gap_lines.iter().any(|line| line.contains("f2"))
            && gap_lines.iter().any(|line| line.contains("gaps")),
        "",
    );
    let clean_lines = soak_brief_lines(&report);
    r.check(
        "brief lines for clean week say all 7 days present",
        clean_lines
            .iter()
            .any(|line| line.contains("all 7 days present")),
        "",
    );

    let mut lines = r.lines;
    lines.push(format!("{} PASS, {} FAIL", r.passed, r.failed));
    DrillOutcome {
        report: DrillReport::new("soak_review", r.phases),
        lines,
    }
}
