//! Port of `os/intel/drills/boot_selfcheck.py` — boot
//! self-check drill (Milo lane, OS-036).
//!
//! At relay-ready the watchdog runs each detector once
//! against the seeded fixture and writes a green self-check
//! record; breaking a detector fails the boot test. The
//! record is a verdict on the detectors, not on the boot —
//! what this proves and does not prove is the source
//! docstring's. The store sink here is an in-memory map
//! standing in for intel.store.put_selfcheck/get_selfcheck:
//! the drill proves the record shape survives a round-trip;
//! the suite pins the real store keys against the fake.

use super::DrillOutcome;
use crate::b12a_drills::boot_selfcheck as root_check;
use crate::b12a_drills::deps::{default_detectors, Detector, Thresholds, Watchdog};
use crate::b12a_drills::value::Value;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub const T0: i64 = 100000;

/// The drill result: outcome plus the green record itself
/// (the source's report dict carries "record").
pub struct BootSelfcheckOutcome {
    pub outcome: DrillOutcome,
    pub record: Value,
}

fn check(
    phases: &mut Vec<PhaseResult>,
    lines: &mut Vec<String>,
    name: &str,
    condition: bool,
    fail_detail: &str,
) {
    if condition {
        phases.push(PhaseResult::pass(name, ""));
        lines.push(format!("PASS: {}", name));
    } else {
        phases.push(PhaseResult::fail(name, fail_detail.to_string()));
        lines.push(format!("FAIL: {} — {}", name, fail_detail));
    }
}

/// Run every phase against the B21 watchdog surface.
pub fn run_drill<W: Watchdog>(watchdog: &W) -> BootSelfcheckOutcome {
    let mut phases: Vec<PhaseResult> = Vec::new();
    let mut lines: Vec<String> = Vec::new();
    let thresholds = Thresholds::locked();
    let snapshot = root_check::seeded_fixture(T0, &thresholds);

    let record = root_check::run_self_check(watchdog, &snapshot, Some(T0), "main", None);
    check(
        &mut phases,
        &mut lines,
        "green record on seeded fixture",
        record.get("status").as_str() == Some("green"),
        &record.py_repr(),
    );
    check(
        &mut phases,
        &mut lines,
        "10 alerts from 9 detectors",
        record.get("alert_count").as_int() == Some(10)
            && record.get("expected_count").as_int() == Some(10),
        &record.py_repr(),
    );
    let detectors = record.get("detectors");
    let all_ok = detectors
        .as_list()
        .map(|items| items.iter().all(|d| d.get("ok") == Value::Bool(true)))
        .unwrap_or(false);
    check(
        &mut phases,
        &mut lines,
        "every detector entry ok",
        all_ok,
        &detectors.py_repr(),
    );

    // The store sink: put returns the self-check key, get
    // reads the record back unchanged.
    let mut sink: Vec<((String, i64), Value)> = Vec::new();
    let put = |sink: &mut Vec<((String, i64), Value)>, room: &str, ts: i64, rec: &Value| -> String {
        sink.push(((room.to_string(), ts), rec.clone()));
        format!("muse-bus:intel:wd:selfcheck:{}:{}", room, ts)
    };
    let _key = put(&mut sink, "main", T0, &record);
    let round_tripped = sink
        .iter()
        .find(|((room, ts), _)| room == "main" && *ts == T0)
        .map(|(_, rec)| rec.clone());
    check(
        &mut phases,
        &mut lines,
        "record round-trips through store sink",
        round_tripped.as_ref() == Some(&record),
        "",
    );

    let again = root_check::run_self_check(watchdog, &snapshot, Some(T0), "main", None);
    check(
        &mut phases,
        &mut lines,
        "second boot test still green",
        again.get("status").as_str() == Some("green") && again == record,
        "fixture mutated or verdict unstable",
    );

    // Broken: detect_dead_dep removed from the list.
    let broken_detectors: Vec<Detector> = default_detectors()
        .into_iter()
        .filter(|d| *d != Detector::Named("detect_dead_dep"))
        .collect();
    let broken = root_check::run_self_check_with(
        watchdog,
        &snapshot,
        Some(T0),
        "main",
        None,
        Some(&broken_detectors),
    );
    let failing_kinds: Vec<String> = broken
        .get("detectors")
        .as_list()
        .map(|items| {
            items
                .iter()
                .filter(|d| d.get("ok") != Value::Bool(true))
                .map(|d| d.get("kind").py_str())
                .collect()
        })
        .unwrap_or_default();
    check(
        &mut phases,
        &mut lines,
        "removed detector fails the boot test",
        broken.get("status").as_str() == Some("red")
            && failing_kinds == vec!["dead-dep".to_string()],
        &broken.get("detectors").py_repr(),
    );

    // Crash: detect_lease_risk replaced by a raising detector.
    let crash_detectors: Vec<Detector> = default_detectors()
        .into_iter()
        .map(|d| {
            if d == Detector::Named("detect_lease_risk") {
                Detector::Raising("detect_lease_risk")
            } else {
                d
            }
        })
        .collect();
    let crashed = root_check::run_self_check_with(
        watchdog,
        &snapshot,
        Some(T0),
        "main",
        None,
        Some(&crash_detectors),
    );
    let failing_kinds: Vec<String> = crashed
        .get("detectors")
        .as_list()
        .map(|items| {
            items
                .iter()
                .filter(|d| d.get("ok") != Value::Bool(true))
                .map(|d| d.get("kind").py_str())
                .collect()
        })
        .unwrap_or_default();
    check(
        &mut phases,
        &mut lines,
        "crashing detector fails the boot test",
        crashed.get("status").as_str() == Some("red")
            && failing_kinds == vec!["lease-risk".to_string()]
            && crashed.get("alert_count").as_int() == Some(9),
        &crashed.get("detectors").py_repr(),
    );

    let ok = phases.iter().all(|p| p.pass);
    lines.push(format!("RESULT: {}", if ok { "PASS" } else { "FAIL" }));
    BootSelfcheckOutcome {
        outcome: DrillOutcome {
            report: DrillReport::new("boot_selfcheck", phases),
            lines,
        },
        record,
    }
}
