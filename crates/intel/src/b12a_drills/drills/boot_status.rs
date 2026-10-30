//! Port of `os/intel/drills/boot_status.py` — boot status
//! line drill (Milo lane, OS-041).
//!
//! One line of live health (units up, workers alive, last
//! alert) for Rowan's boot checklist: green on a healthy
//! fixture, round-trips through a store sink, drops and
//! names the unit when one is killed, names the latest open
//! alert (resolved ones ignored), and goes stale 30 s after
//! the record's ts. The line is a verdict on the fixture
//! inputs, not on a boot (see the source docstring). The
//! builder/staleness surface is intel.store (B09 `BootStatus`
//! trait); the sink here is an in-memory map, as in the
//! source.

use super::DrillOutcome;
use crate::b12a_drills::deps::BootStatus;
use crate::b12a_drills::value::Value;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub const T0: i64 = 100000;

pub fn units() -> Value {
    let unit = |name: &str| {
        Value::obj(vec![
            ("unit", Value::s(name)),
            ("state", Value::s("active")),
        ])
    };
    Value::List(vec![
        unit("relay-bus"),
        unit("relay-jobs"),
        unit("relay-watchdog"),
    ])
}

pub fn workers() -> Value {
    Value::List(vec![Value::s("milo"), Value::s("rowan")])
}

/// The drill result: outcome plus the green record (the
/// source's report dict carries "record").
pub struct BootStatusOutcome {
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

/// Run every phase against the store surface.
pub fn run_drill(store: &dyn BootStatus) -> BootStatusOutcome {
    let mut phases: Vec<PhaseResult> = Vec::new();
    let mut lines: Vec<String> = Vec::new();
    let units = units();
    let workers = workers();
    let no_alerts = Value::List(vec![]);

    let record = store.build_boot_status(&units, &workers, &no_alerts, T0);
    check(
        &mut phases,
        &mut lines,
        "green line on healthy fixture",
        record.get("line").as_str()
            == Some("Boot: 3/3 units up, 2 workers alive — no open alerts"),
        &record.py_repr(),
    );
    check(
        &mut phases,
        &mut lines,
        "green record fields",
        record.get("units_up").as_int() == Some(3)
            && record.get("units_total").as_int() == Some(3)
            && record.get("workers_count").as_int() == Some(2)
            && record.get("last_alert").is_null(),
        &record.py_repr(),
    );

    // Store sink round-trip (put returns the bootstatus key).
    let mut sink: Vec<((String, i64), Value)> = Vec::new();
    sink.push((("main".to_string(), T0), record.clone()));
    let _key = format!("muse-bus:intel:wd:bootstatus:main:{}", T0);
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

    let killed = Value::List(
        units
            .as_list()
            .cloned()
            .unwrap_or_default()
            .into_iter()
            .map(|mut u| {
                if u.get("unit").as_str() == Some("relay-jobs") {
                    u.set("state", Value::s("failed"));
                }
                u
            })
            .collect(),
    );
    let after_kill = store.build_boot_status(&killed, &workers, &no_alerts, T0 + 5);
    check(
        &mut phases,
        &mut lines,
        "killed unit drops the line and names it",
        after_kill.get("line").as_str()
            == Some(
                "Boot: 2/3 units up, 2 workers alive — down: relay-jobs — no open alerts",
            ),
        &after_kill.py_repr(),
    );

    let alert = |id: &str, severity: &str, created: i64, resolved: Option<i64>| {
        Value::obj(vec![
            ("id", Value::s(id)),
            ("severity", Value::s(severity)),
            ("created_at", Value::Int(created)),
            (
                "resolved_at",
                match resolved {
                    Some(ts) => Value::Int(ts),
                    None => Value::Null,
                },
            ),
        ])
    };
    let alerts = Value::List(vec![
        alert("a-old", "warning", T0 - 100, None),
        alert("a-new", "critical", T0 - 10, None),
        alert("a-done", "critical", T0 - 1, Some(T0)),
    ]);
    let with_alert = store.build_boot_status(&units, &workers, &alerts, T0);
    check(
        &mut phases,
        &mut lines,
        "latest open alert named, resolved ignored",
        with_alert.get("last_alert").get("id").as_str() == Some("a-new")
            && with_alert
                .get("line")
                .py_str()
                .contains("last alert: a-new (critical)"),
        &with_alert.py_repr(),
    );

    check(
        &mut phases,
        &mut lines,
        "pre-kill record fresh at exactly 30s",
        !store.boot_status_is_stale(&record, T0 + 30),
        "",
    );
    check(
        &mut phases,
        &mut lines,
        "pre-kill record stale at 31s",
        store.boot_status_is_stale(&record, T0 + 31),
        "",
    );
    check(
        &mut phases,
        &mut lines,
        "post-kill record fresh at +5s",
        !store.boot_status_is_stale(&after_kill, T0 + 10),
        "",
    );

    let ok = phases.iter().all(|p| p.pass);
    lines.push(format!("RESULT: {}", if ok { "PASS" } else { "FAIL" }));
    BootStatusOutcome {
        outcome: DrillOutcome {
            report: DrillReport::new("boot_status", phases),
            lines,
        },
        record,
    }
}
