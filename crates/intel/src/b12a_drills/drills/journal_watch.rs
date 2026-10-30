//! Port of `os/intel/drills/journal_watch.py` — journal
//! watch drill (Milo lane, OS-037).
//!
//! Force-failing a unit must produce a SYSTEM alert in the
//! alert store within one watchdog loop. The force-fail is
//! played by fixture journal lines (journalctl -o json
//! shapes) — there is no test image to kill a real relay
//! unit on. One journal_watch_tick over the fixture yields
//! exactly one SYSTEM alert: the unit's two failure lines
//! group into one alert with failure_count 2, the healthy
//! relay unit and the non-relay failure stay silent, the
//! alert validates through the store's own writer shape, and
//! a re-tick re-fires the same dedupe key. Journal watch is
//! not a DETECTORS member — the severity lives in the alert
//! itself (check 9's point).

use super::DrillOutcome;
use crate::b12a_drills::deps::{AlertRecords, Watchdog};
use crate::b12a_drills::value::{to_json, Value};
use crate::b12a_drills::{DrillReport, PhaseResult};

pub const T0: i64 = 100000;
pub const UNIT: &str = "relay-jobs.service";

fn line(unit: &str, message: &str, priority: i64) -> String {
    to_json(&Value::obj(vec![
        ("_SYSTEMD_UNIT", Value::s(unit)),
        ("MESSAGE", Value::s(message)),
        ("PRIORITY", Value::s(&priority.to_string())),
    ]))
}

/// The FIXTURE journal text, verbatim (including the blank
/// line and the not-JSON line that must be skipped, not fatal).
pub fn fixture() -> String {
    let mut text = [
        line(UNIT, "relay-jobs.service: Failed with result 'exit-code'.", 3),
        line(
            UNIT,
            "relay-jobs.service: Main process exited, code=exited, status=1/FAILURE",
            3,
        ),
        line("relay-bus.service", "Started relay-bus.service.", 6),
        line(
            "sshd.service",
            "sshd.service: Failed with result 'exit-code'.",
            3,
        ),
        String::new(),
        "this line is not json and must be skipped, not fatal".to_string(),
    ]
    .join("\n");
    text.push('\n');
    text
}

struct Checks {
    lines: Vec<String>,
    phases: Vec<PhaseResult>,
    all: bool,
}

impl Checks {
    fn new() -> Self {
        Checks {
            lines: Vec::new(),
            phases: Vec::new(),
            all: true,
        }
    }
    /// The drill's _check(): "PASS name" / "FAIL name — detail".
    fn check(&mut self, name: &str, ok: bool, detail: &str) {
        if ok {
            self.lines.push(format!("PASS {}", name));
            self.phases.push(PhaseResult::pass(name, ""));
        } else {
            self.lines.push(format!("FAIL {} — {}", name, detail));
            self.phases.push(PhaseResult::fail(name, detail.to_string()));
            self.all = false;
        }
    }
}

/// The drill's main(): every check, then the RESULT line.
pub fn run(watchdog: &dyn Watchdog, records: &dyn AlertRecords) -> DrillOutcome {
    let mut c = Checks::new();
    let fixture = fixture();
    let mut collected: Vec<Value> = Vec::new();
    let alerts = watchdog.journal_watch_tick(
        &fixture,
        Some(T0),
        Some(&mut |a: &Value| collected.push(a.clone())),
    );
    c.check(
        "1 forced failure yields exactly one SYSTEM alert",
        alerts.len() == 1,
        &format!("got {}: {}", alerts.len(), Value::List(alerts.clone()).py_repr()),
    );
    let alert = alerts.first().cloned().unwrap_or(Value::obj(vec![]));
    c.check(
        "2 alert kind is system-failure, severity critical",
        alert.get("kind").as_str() == Some("system-failure")
            && alert.get("severity").as_str() == Some("critical"),
        &format!("got {}", alert.py_repr()),
    );
    c.check(
        "3 alert is SYSTEM, not a job alert: subjects the unit, no nick, no job",
        alert.get("subjects") == Value::List(vec![Value::s(UNIT)])
            && alert.get("system_alert") == Value::Bool(true)
            && !alert.contains_key("nick")
            && !alert.contains_key("job"),
        &format!("got {}", alert.py_repr()),
    );
    c.check(
        "4 same unit's two failure lines group into one alert with failure_count 2",
        alert.get("failure_count").as_int() == Some(2),
        &format!("got {}", alert.py_repr()),
    );
    c.check(
        "5 explanation quotes the failure and names the unit",
        alert.get("explanation").py_str().contains(UNIT)
            && alert.get("explanation").py_str().contains("Failed with result"),
        &format!("got {:?}", alert.get("explanation").py_repr()),
    );
    c.check(
        "6 suggested fix points at journalctl -u and an operator restart, never a watchdog restart",
        alert
            .get("suggested_fix")
            .py_str()
            .contains(&format!("journalctl -u {}", UNIT))
            && alert
                .get("suggested_fix")
                .py_str()
                .contains("never restarts units itself"),
        &format!("got {:?}", alert.get("suggested_fix").py_repr()),
    );
    c.check(
        "7 emit received the alert (the store-writer seat)",
        collected == alerts,
        &format!("got {}", Value::List(collected.clone()).py_repr()),
    );
    let (built, record, build_detail) = match records.build_alert_record(&alert, "main", None) {
        Ok(record) => (true, record, String::new()),
        Err(exc) => (false, Value::obj(vec![]), exc),
    };
    let record_detail = if build_detail.is_empty() {
        format!("got {}", record.py_repr())
    } else {
        build_detail.clone()
    };
    c.check(
        "8 alert validates as a WDG-010 store record",
        built && record.get("id").as_str() == Some(&format!("system-failure:{}", UNIT)),
        &record_detail,
    );
    c.check(
        "9 system-failure severity is critical in the alert itself (not via the snapshot-detector table: journal watch is not a DETECTORS member, so the WDG-024 table lock in test_intel_watchdog.py must keep covering exactly the snapshot kinds)",
        alert.get("severity").as_str() == Some("critical"),
        &format!("got {:?}", alert.get("severity").py_repr()),
    );
    let again = watchdog.journal_watch_tick(&fixture, Some(T0 + 60), None);
    c.check(
        "10 re-tick re-fires the same dedupe key only",
        again.len() == 1 && again[0].get("dedupe_key") == alert.get("dedupe_key"),
        &format!("got {}", Value::List(again).py_repr()),
    );

    let ok = c.all;
    let mut lines = c.lines;
    lines.push(format!("RESULT: {}", if ok { "PASS" } else { "FAIL" }));
    DrillOutcome {
        report: DrillReport::new("journal_watch", c.phases),
        lines,
    }
}
