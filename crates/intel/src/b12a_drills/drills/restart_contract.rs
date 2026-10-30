//! Port of `os/intel/drills/restart_contract.py` —
//! restart-ownership contract drill (Milo lane, OS-034).
//!
//! The contract: systemd's Restart= owns process death; the
//! watchdog owns silent-but-alive stalls; neither double-acts
//! on the other's case. Case A: kill -9 plus a systemd
//! restart gets an event note and NO false stall alert (with
//! a no-restart control proving the zero comes from the
//! restart). Case B: SIGSTOP — alive but wedged — gets a
//! progress-stall alert and no restart fight. The systemd
//! half is played by the drill's fixture snapshots; what is
//! proven is the watchdog's half and the note's shape
//! through the store's own validator.

use super::DrillOutcome;
use crate::b12a_drills::deps::{AlertRecords, Thresholds, Watchdog};
use crate::b12a_drills::value::Value;
use crate::b12a_drills::{DrillReport, PhaseResult};

pub const JOB_ID: &str = "7";
pub const NICK: &str = "pax";
pub const T0: i64 = 100000;
/// Modeled RestartSec (the watchdog unit's value; the worker
/// template's own value is pinned elsewhere — see the source).
pub const RESTART_SEC: i64 = 10;

/// `_snapshot(present, last_activity)` — verbatim shape
/// (note: caps maps the nick to a bare list in this drill).
pub fn snapshot(present: bool, last_activity: i64, t: &Thresholds) -> Value {
    Value::obj(vec![
        (
            "caps",
            Value::obj(vec![(
                NICK,
                Value::List(vec![Value::s("python")]),
            )]),
        ),
        (
            "presence",
            if present {
                Value::List(vec![Value::s(NICK)])
            } else {
                Value::List(vec![])
            },
        ),
        (
            "jobs",
            Value::List(vec![Value::obj(vec![
                ("id", Value::s(JOB_ID)),
                ("title", Value::s("demo job")),
                ("status", Value::s("claimed")),
                ("claim", Value::s(NICK)),
                ("claimed_at", Value::Int(T0)),
                ("last_progress", Value::Int(last_activity)),
                ("lease", Value::Int(t.lease_default_seconds)),
                ("lease_until", Value::Int(T0 + t.lease_default_seconds)),
            ])]),
        ),
        ("messages", Value::List(vec![])),
    ])
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
    /// The drill's _check(): "PASS: name" / "FAIL: name — detail".
    fn check(&mut self, name: &str, ok: bool, detail: &str) {
        if ok {
            self.lines.push(format!("PASS: {}", name));
            self.phases.push(PhaseResult::pass(name, ""));
        } else {
            self.lines.push(format!("FAIL: {} — {}", name, detail));
            self.phases.push(PhaseResult::fail(name, detail.to_string()));
            self.all = false;
        }
    }
}

/// The drill's main(): every check, then the RESULT line.
pub fn run(
    watchdog: &dyn Watchdog,
    records: &dyn AlertRecords,
    thresholds: &Thresholds,
) -> DrillOutcome {
    let mut c = Checks::new();
    let stall = thresholds.stall_minutes * 60;
    let progress = thresholds.progress_stall_minutes * 60;

    // Case A: kill -9, systemd restarts, watchdog notes, no alert.
    let killed_at = T0 + 300;
    let back_at = killed_at + RESTART_SEC;
    let tick_gap = watchdog.tick(
        &snapshot(false, killed_at, thresholds),
        Some(killed_at + RESTART_SEC / 2),
    );
    c.check(
        "A0 mid-restart gap ticks zero alerts (age under threshold)",
        tick_gap.is_empty(),
        &format!("got {}", Value::List(tick_gap).py_repr()),
    );
    let tick_a = watchdog.tick(&snapshot(true, back_at, thresholds), Some(back_at));
    c.check(
        "A1 restarted worker ticks zero alerts",
        tick_a.is_empty(),
        &format!("got {}", Value::List(tick_a).py_repr()),
    );
    let note = watchdog.restart_event_note(NICK, JOB_ID, back_at, Some(RESTART_SEC));
    let record = records
        .build_alert_record(&note, "main", None)
        .unwrap_or(Value::obj(vec![]));
    c.check(
        "A2 restart note validates as an info record",
        record.get("kind").as_str() == Some("worker-restart")
            && record.get("severity").as_str() == Some("info")
            && record.get("id").as_str()
                == Some(&format!("worker-restart:{}:{}", NICK, JOB_ID))
            && record.get("explanation").py_str().contains(NICK)
            && record.get("explanation").py_str().contains(JOB_ID),
        &format!("got {}", record.py_repr()),
    );
    c.check(
        "A3 restart note never announces",
        watchdog
            .announcements_for(std::slice::from_ref(&record))
            .is_empty(),
        "",
    );
    c.check(
        "A4 note names the systemd restart, not a stall",
        record.get("explanation").py_str().contains("systemd")
            && record.get("explanation").py_str().contains("no stall alert"),
        "",
    );

    // Control: same death, no restart, past threshold -> stall.
    let tick_c = watchdog.tick(
        &snapshot(false, killed_at, thresholds),
        Some(killed_at + stall + 60),
    );
    let kinds_c: Vec<String> = tick_c.iter().map(|a| a.get("kind").py_str()).collect();
    c.check(
        "A-control un-restarted death yields one presence-stall",
        kinds_c == vec!["presence-stall".to_string()],
        &format!("got {:?}", kinds_c),
    );

    // Case B: SIGSTOP, alive but wedged -> stall alert, no fight.
    let tick_b = watchdog.tick(
        &snapshot(true, T0, thresholds),
        Some(T0 + progress + 60),
    );
    let kinds_b: Vec<String> = tick_b.iter().map(|a| a.get("kind").py_str()).collect();
    c.check(
        "B1 wedged worker yields exactly one progress-stall",
        kinds_b == vec!["progress-stall".to_string()],
        &format!("got {:?}", kinds_b),
    );
    let stall_b = tick_b.first().cloned().unwrap_or(Value::obj(vec![]));
    c.check(
        "B2 stall alert names nick, job, and age",
        stall_b.get("nick").as_str() == Some(NICK)
            && stall_b.get("job").as_str() == Some(JOB_ID)
            && stall_b
                .get("last_progress_age_seconds")
                .as_int()
                .unwrap_or(0)
                > progress,
        &format!("got {}", stall_b.py_repr()),
    );
    c.check(
        "B3 wedged case builds no restart note and systemd takes no action (process alive)",
        !watchdog.announcements_for(&tick_b).is_empty()
            && !tick_b
                .iter()
                .any(|a| a.get("kind").as_str() == Some("worker-restart")),
        "",
    );

    let ok = c.all;
    let mut lines = c.lines;
    lines.push(format!("RESULT: {}", if ok { "PASS" } else { "FAIL" }));
    DrillOutcome {
        report: DrillReport::new("restart_contract", c.phases),
        lines,
    }
}
