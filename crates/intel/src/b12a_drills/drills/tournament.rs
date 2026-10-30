//! Port of `os/intel/drills/tournament.py` — drill
//! tournament (Milo lane, INT-021).
//!
//! Runs the three watchdog drills back to back in one
//! session, in demo order, timed end to end: kill_worker
//! (WDG-020), collision (WDG-021), dead_dep (WDG-022). Each
//! drill must exit 0 and print a line ending in ": PASS";
//! total wall time under 360 seconds. The subprocess seat
//! is the `DrillRunner` trait (the drills themselves are
//! the ported modules; how the seat invokes them — in
//! process or as binaries — is the caller's wiring). The
//! log write to intel/evals/drill_tournament.log is part
//! of the port, rooted at the caller's repo root.

use std::path::Path;
use std::time::Instant;

use crate::b12a_drills::value::Value;

pub const DRILLS: [(&str, &str); 3] = [
    ("kill_worker", "WDG-020"),
    ("collision", "WDG-021"),
    ("dead_dep", "WDG-022"),
];
pub const LIMIT_SECONDS: f64 = 360.0;

/// One drill subprocess: (exit_code, stdout, stderr).
pub trait DrillRunner {
    fn run_drill(&self, name: &str) -> (i32, String, String);
}

/// `run_tournament(write_log)` — the result dict as a Value:
/// {ok, total_seconds, drills: [{name, task, exit_code,
/// seconds, pass_line, output}], transcript}.
pub fn run_tournament(runner: &dyn DrillRunner, write_log: bool, root: &Path) -> Value {
    let mut lines: Vec<String> = vec![
        "INT-021 drill tournament: kill_worker, collision, dead_dep, back to back in one session"
            .to_string(),
    ];
    let mut drills: Vec<Value> = Vec::new();
    let started = Instant::now();
    let mut ok = true;
    for (name, task) in DRILLS {
        let drill_started = Instant::now();
        let (exit_code, stdout, stderr) = runner.run_drill(name);
        let seconds = drill_started.elapsed().as_secs_f64();
        let out = stdout.trim().to_string();
        // The LAST line whose strip ends with ": PASS".
        let pass_line: Option<String> = out
            .lines()
            .map(|line| line.trim().to_string())
            .filter(|line| line.ends_with(": PASS"))
            .last();
        let drill_ok = exit_code == 0 && pass_line.is_some();
        if !drill_ok {
            ok = false;
        }
        drills.push(Value::obj(vec![
            ("name", Value::s(name)),
            ("task", Value::s(task)),
            ("exit_code", Value::Int(exit_code as i64)),
            ("seconds", Value::Float(seconds)),
            (
                "pass_line",
                pass_line.clone().map(Value::s).unwrap_or(Value::Null),
            ),
            ("output", Value::s(&out)),
        ]));
        if drill_ok {
            lines.push(format!(
                "PASS: {} ({}) -- exit 0, {}, {:.2}s",
                name,
                task,
                pass_line.unwrap_or_default(),
                seconds
            ));
        } else {
            lines.push(format!(
                "FAIL: {} ({}) -- exit {}, {:.2}s\n{}\n{}",
                name, task, exit_code, seconds, out, stderr
            ));
        }
    }
    let total = started.elapsed().as_secs_f64();
    if total >= LIMIT_SECONDS {
        ok = false;
        lines.push(format!(
            "FAIL: total {:.2}s >= {:.0}s limit",
            total, LIMIT_SECONDS
        ));
    }
    if ok {
        lines.push(format!(
            "INT-021: PASS -- 3/3 drills passed, total {:.2}s (limit {:.0}s)",
            total, LIMIT_SECONDS
        ));
    } else {
        lines.push(format!(
            "INT-021: FAIL -- total {:.2}s (limit {:.0}s)",
            total, LIMIT_SECONDS
        ));
    }
    let mut transcript = lines.join("\n");
    transcript.push('\n');
    if write_log {
        let log_path = root.join("intel/evals/drill_tournament.log");
        if let Some(dir) = log_path.parent() {
            let _ = std::fs::create_dir_all(dir);
        }
        let mut content = transcript.clone();
        for drill in &drills {
            content.push_str(&format!(
                "\n--- {} ({}), {:.2}s ---\n{}\n",
                drill.get("name").py_str(),
                drill.get("task").py_str(),
                drill.get("seconds").as_number().unwrap_or(0.0),
                drill.get("output").py_str()
            ));
        }
        let _ = std::fs::write(&log_path, content);
    }
    Value::obj(vec![
        ("ok", Value::Bool(ok)),
        ("total_seconds", Value::Float(total)),
        ("drills", Value::List(drills)),
        ("transcript", Value::s(&transcript)),
    ])
}
