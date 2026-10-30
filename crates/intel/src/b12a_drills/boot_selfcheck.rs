//! Port of `os/intel/boot_selfcheck.py` — watchdog boot
//! self-check (OS-036).
//!
//! run_self_check ticks the snapshot through `intel.watchdog`
//! (B21 — the `Watchdog` trait in `deps`) once and compares the
//! alerts found, per kind, against EXPECTED, the counts the
//! seeded fixture is built to produce. The record is green only
//! when every kind matches exactly; extra kinds are reported
//! as unexpected entries and also turn the record red.
//! seeded_fixture builds the OS-026-shaped fixture to spec:
//! ages derive from thresholds, never hardcoded, except the
//! stale lease, which is stale by construction.

use super::deps::{Thresholds, Watchdog};
use super::value::Value;

/// Expected alert counts per kind on the seeded fixture.
pub fn expected() -> Value {
    Value::obj(vec![
        ("presence-stall", Value::Int(1)),
        ("progress-stall", Value::Int(1)),
        ("lease-risk", Value::Int(1)),
        ("dead-dep", Value::Int(1)),
        ("missing-dep", Value::Int(1)),
        ("file-collision", Value::Int(1)),
        ("attempt-warning", Value::Int(1)),
        ("attempt-exhaustion", Value::Int(1)),
        ("silent-room", Value::Int(1)),
        ("rejected-dispatch", Value::Int(1)),
    ])
}

/// `seeded_fixture(now)` — the OS-026-shaped fixture.
pub fn seeded_fixture(now: i64, thresholds: &Thresholds) -> Value {
    let stall_ago = now - (thresholds.stall_minutes + 10) * 60;
    let job = |pairs: Vec<(&str, Value)>| Value::obj(pairs);
    Value::obj(vec![
        ("room", Value::s("main")),
        (
            "messages",
            Value::List(vec![
                Value::obj(vec![
                    ("nick", Value::s("pax")),
                    ("text", Value::s("working on it")),
                    (
                        "ts",
                        Value::Int(now - (thresholds.silent_room_minutes + 10) * 60),
                    ),
                ]),
                Value::s("REJECTED:42 BAD signed_by=pax rejected_by=rowan"),
            ]),
        ),
        (
            "jobs",
            Value::List(vec![
                job(vec![
                    ("id", Value::s("1")),
                    ("title", Value::s("stale lease job")),
                    ("status", Value::s("claimed")),
                    ("claim", Value::s("gone")),
                    ("last_progress", Value::Int(stall_ago)),
                    ("lease_until", Value::Int(now - 60)),
                ]),
                job(vec![
                    ("id", Value::s("2")),
                    ("title", Value::s("stuck job")),
                    ("status", Value::s("claimed")),
                    ("claim", Value::s("stuck")),
                    ("last_progress", Value::Int(stall_ago)),
                ]),
                job(vec![
                    ("id", Value::s("3")),
                    ("title", Value::s("expiring job")),
                    ("status", Value::s("claimed")),
                    ("claim", Value::s("leasey")),
                    ("last_progress", Value::Int(now - 60)),
                    ("last_heartbeat", Value::Int(now - 3 * 60)),
                    ("lease_until", Value::Int(now + 3 * 60)),
                    ("lease", Value::Int(thresholds.lease_default_seconds)),
                ]),
                job(vec![
                    ("id", Value::s("4")),
                    ("title", Value::s("collision job A")),
                    ("status", Value::s("claimed")),
                    ("claim", Value::s("colla")),
                    ("last_progress", Value::Int(now - 60)),
                    ("last_heartbeat", Value::Int(now - 60)),
                    ("lease_until", Value::Int(now + 3600)),
                    ("files", Value::s("intel/store.py")),
                ]),
                job(vec![
                    ("id", Value::s("5")),
                    ("title", Value::s("collision job B")),
                    ("status", Value::s("claimed")),
                    ("claim", Value::s("collb")),
                    ("last_progress", Value::Int(now - 60)),
                    ("last_heartbeat", Value::Int(now - 60)),
                    ("lease_until", Value::Int(now + 3600)),
                    ("files", Value::s("intel/store.py")),
                ]),
                job(vec![
                    ("id", Value::s("20")),
                    ("title", Value::s("blocked dep")),
                    ("status", Value::s("blocked")),
                    ("note", Value::s("waiting on review")),
                ]),
                job(vec![
                    ("id", Value::s("21")),
                    ("title", Value::s("waits on blocked dep")),
                    ("status", Value::s("open")),
                    ("deps", Value::s("20")),
                ]),
                job(vec![
                    ("id", Value::s("22")),
                    ("title", Value::s("waits on missing dep")),
                    ("status", Value::s("open")),
                    ("deps", Value::s("999")),
                ]),
                job(vec![
                    ("id", Value::s("23")),
                    ("title", Value::s("one attempt left")),
                    ("status", Value::s("open")),
                    ("attempts", Value::Int(2)),
                    ("max_attempts", Value::Int(3)),
                ]),
                job(vec![
                    ("id", Value::s("24")),
                    ("title", Value::s("budget spent")),
                    ("status", Value::s("open")),
                    ("attempts", Value::Int(3)),
                    ("max_attempts", Value::Int(3)),
                ]),
                job(vec![
                    ("id", Value::s("30")),
                    ("title", Value::s("finished job")),
                    ("status", Value::s("done")),
                ]),
            ]),
        ),
        (
            "presence",
            Value::List(vec![
                Value::s("stuck"),
                Value::s("leasey"),
                Value::s("colla"),
                Value::s("collb"),
            ]),
        ),
        (
            "caps",
            Value::obj(vec![
                ("gone", Value::obj(vec![("caps", Value::s("build"))])),
                ("stuck", Value::obj(vec![("caps", Value::s("build"))])),
                ("leasey", Value::obj(vec![("caps", Value::s("build"))])),
                ("colla", Value::obj(vec![("caps", Value::s("build"))])),
                ("collb", Value::obj(vec![("caps", Value::s("build"))])),
            ]),
        ),
    ])
}

/// `run_self_check(snapshot, now, room, expected)` — tick once,
/// compare per-kind counts, return the record. The watchdog is
/// the B21 surface in `deps`; a detector that raises is
/// swallowed by tick, so it shows up as found 0 against its
/// expected count — red, named, honest.
pub fn run_self_check<W: Watchdog>(
    watchdog: &W,
    snapshot: &Value,
    now: Option<i64>,
    room: &str,
    expected: Option<&Value>,
) -> Value {
    run_self_check_with(watchdog, snapshot, now, room, expected, None)
}

/// The same check over an explicit detector list — the boot
/// self-check drill edits the list (one detector removed, one
/// replaced by a raising callable) to prove the fail modes.
pub fn run_self_check_with<W: Watchdog>(
    watchdog: &W,
    snapshot: &Value,
    now: Option<i64>,
    room: &str,
    expected: Option<&Value>,
    detectors: Option<&[super::deps::Detector]>,
) -> Value {
    let expected = match expected {
        Some(e) => e.clone(),
        None => expected(),
    };
    let alerts = match detectors {
        Some(list) => watchdog.tick_with(snapshot, now, list),
        None => watchdog.tick(snapshot, now),
    };
    let mut found: Vec<(String, i64)> = Vec::new();
    for alert in &alerts {
        if alert.is_dict() {
            if let Some(kind) = alert.get("kind").as_str() {
                if let Some(slot) = found.iter_mut().find(|(k, _)| k == kind) {
                    slot.1 += 1;
                } else {
                    found.push((kind.to_string(), 1));
                }
            }
        }
    }
    let mut kinds: Vec<String> = Vec::new();
    if let Some(pairs) = expected.as_map() {
        for (k, _) in pairs {
            if !kinds.contains(k) {
                kinds.push(k.clone());
            }
        }
    }
    for (k, _) in &found {
        if !kinds.contains(k) {
            kinds.push(k.clone());
        }
    }
    kinds.sort();
    let mut detectors = Vec::new();
    let mut ok = true;
    for kind in &kinds {
        let want = expected.get(kind).as_int().unwrap_or(0);
        let got = found
            .iter()
            .find(|(k, _)| k == kind)
            .map(|(_, c)| *c)
            .unwrap_or(0);
        let entry_ok = want == got;
        if !entry_ok {
            ok = false;
        }
        detectors.push(Value::obj(vec![
            ("kind", Value::s(kind)),
            ("expected", Value::Int(want)),
            ("found", Value::Int(got)),
            ("ok", Value::Bool(entry_ok)),
        ]));
    }
    let expected_count: i64 = match expected.as_map() {
        Some(pairs) => pairs
            .iter()
            .map(|(_, v)| v.as_int().unwrap_or(0))
            .sum(),
        None => 0,
    };
    Value::obj(vec![
        ("status", Value::s(if ok { "green" } else { "red" })),
        ("room", Value::s(room)),
        (
            "ts",
            match now {
                Some(n) => Value::Int(n),
                None => Value::Null,
            },
        ),
        ("detectors", Value::List(detectors)),
        ("alert_count", Value::Int(alerts.len() as i64)),
        ("expected_count", Value::Int(expected_count)),
    ])
}
