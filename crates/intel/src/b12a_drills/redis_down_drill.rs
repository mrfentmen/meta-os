//! Port of `os/intel/redis_down_drill.py` — INT-009: Redis
//! outage for all intel commands, scripted drill.
//!
//! The drill runs the real intel CLI against a genuinely dead
//! endpoint (http://127.0.0.1:9, a closed localhost port) and
//! proves every Redis-dependent command fails loudly with
//! RELAY_ERROR and exit 2 — never a traceback — while the
//! store-free commands (dry-run brief, dry-run dispatch) still
//! succeed, the watch stub reports its pre-existing
//! UNIMPLEMENTED, and the watchdog engine still ticks pure
//! while its store write raises. The CLI subprocesses and the
//! in-process relay surface ride the [`DownSurface`] seam (in
//! the source: subprocess + relay_common pointed at the dead
//! URL); stage assertions and details are the source's own.
//! The token file holds a dummy string, never a credential,
//! and is removed when the drill finishes.

use super::deps::Watchdog;
use super::e2e1::Stage;
use super::value::Value;

pub const DOWN_URL: &str = "http://127.0.0.1:9";
pub const NOW: i64 = 10000;
pub const PLAN_PATH: &str = "hackathon/demo_goal_plan.json";

const STAGE_NAMES: [&str; 14] = [
    "precondition",
    "snapshot",
    "brief-store",
    "brief-dry-run",
    "brief-list",
    "brief-show",
    "dispatch-show",
    "dispatch-undo",
    "dispatch-posting",
    "dispatch-dry-run",
    "alerts-show",
    "alerts-query",
    "watch",
    "watchdog-engine",
];

/// The dead-endpoint surface: the shipped CLI as a subprocess
/// and the in-process relay/store calls, all pointed at
/// DOWN_URL by construction of the harness implementation.
pub trait DownSurface {
    /// Run the real intel.py CLI with the drill env:
    /// (exit code, stdout, stderr).
    fn cli(&self, argv: &[String], env: &[(String, String)]) -> (i32, String, String);
    /// `relay_common.api_get(path)` against the dead endpoint;
    /// Err carries the RuntimeError message.
    fn api_get(&self, path: &str) -> Result<Value, String>;
    /// `intel.store.write_alert(alert, room, now)` against the
    /// dead endpoint; Err carries the RuntimeError message.
    fn write_alert(&self, alert: &Value, room: &str, now: i64) -> Result<Value, String>;
}

/// The stage-14 fixture, `SNAPSHOT` verbatim.
pub fn snapshot_fixture() -> Value {
    let job = |pairs: Vec<(&str, Value)>| Value::obj(pairs);
    Value::obj(vec![
        (
            "messages",
            Value::List(vec![
                Value::obj(vec![
                    ("nick", Value::s("pax")),
                    ("text", Value::s("shipping the drill")),
                ]),
                Value::obj(vec![
                    ("nick", Value::s("hana")),
                    ("text", Value::s("brief lane stands by")),
                ]),
            ]),
        ),
        (
            "jobs",
            Value::List(vec![
                job(vec![
                    ("id", Value::s("7")),
                    ("status", Value::s("claimed")),
                    ("claim", Value::s("pax")),
                    ("title", Value::s("Write the drill note")),
                    ("claimed_at", Value::Int(9000)),
                    ("last_progress", Value::Int(9340)),
                ]),
                job(vec![
                    ("id", Value::s("8")),
                    ("status", Value::s("blocked")),
                    ("title", Value::s("Vendor API key")),
                    ("note", Value::s("waiting on vendor")),
                ]),
            ]),
        ),
        ("presence", Value::List(vec![Value::s("pax")])),
        (
            "caps",
            Value::obj(vec![("pax", Value::obj(vec![]))]),
        ),
    ])
}

/// The drill result: {ok, stages, lines}.
#[derive(Debug, Clone)]
pub struct DrillResult {
    pub ok: bool,
    pub stages: Vec<Stage>,
    pub lines: Vec<String>,
}

fn stage(stages: &mut Vec<Stage>, name: &str, f: impl FnOnce() -> Result<String, String>) {
    match f() {
        Ok(detail) => stages.push(Stage {
            name: name.to_string(),
            ok: true,
            detail,
        }),
        Err(msg) => stages.push(Stage {
            name: name.to_string(),
            ok: false,
            detail: format!("AssertionError: {}", msg),
        }),
    }
}

/// `_expect_loud_failure`: exit 2, RELAY_ERROR, no Traceback,
/// empty stdout (and optionally a required stderr phrase).
fn expect_loud_failure(
    surface: &dyn DownSurface,
    argv: &[&str],
    env: &[(String, String)],
    must_name: Option<&str>,
) -> Result<String, String> {
    let argv_owned: Vec<String> = argv.iter().map(|s| s.to_string()).collect();
    let (code, out, err) = surface.cli(&argv_owned, env);
    if code != 2 {
        return Err(format!(
            "{:?} exited {}, not 2: {:?} {:?}",
            argv, code, out, err
        ));
    }
    if !err.contains("RELAY_ERROR") {
        return Err(format!("{:?} stderr lacks RELAY_ERROR: {:?}", argv, err));
    }
    if err.contains("Traceback") {
        return Err(format!("{:?} printed a traceback: {:?}", argv, err));
    }
    if !out.is_empty() {
        return Err(format!("{:?} printed stdout on failure: {:?}", argv, out));
    }
    if let Some(phrase) = must_name {
        if !err.contains(phrase) {
            return Err(format!(
                "{:?} stderr lacks {:?}: {:?}",
                argv, phrase, err
            ));
        }
    }
    Ok("exit 2, RELAY_ERROR, no traceback, empty stdout".to_string())
}

/// `run_drill(write_log)` — the INT-009 drill. The transcript
/// write (intel/evals/redis_down.log) is the caller's; the
/// lines ride in the result, as in the source's return dict.
pub fn run_drill(surface: &dyn DownSurface, watchdog: &dyn Watchdog) -> DrillResult {
    let mut stages: Vec<Stage> = Vec::new();
    // Token file: a dummy string in a fresh temp dir, removed
    // when the drill finishes (best effort, like the source).
    let token_dir = std::env::temp_dir().join(format!(
        "redis-down-drill-{}",
        std::process::id()
    ));
    let _ = std::fs::create_dir_all(&token_dir);
    let token_file = token_dir.join("token");
    let _ = std::fs::write(&token_file, "drill-dummy-token-not-a-secret");
    let env: Vec<(String, String)> = vec![
        ("MUSE_RELAY_URL".to_string(), DOWN_URL.to_string()),
        (
            "MUSE_RELAY_TOKEN_FILE".to_string(),
            token_file.to_string_lossy().to_string(),
        ),
    ];
    let now_s = NOW.to_string();

    stage(&mut stages, STAGE_NAMES[0], || {
        match surface.api_get("lrange/muse-bus/0/0") {
            Err(exc) => {
                if !exc.contains("request failed after 4 attempts") {
                    return Err(format!("unexpected error: {}", exc));
                }
                if !exc.contains("curl rc=7") {
                    return Err(format!("not a connection-refused failure: {}", exc));
                }
                Ok(format!(
                    "RuntimeError: {} (real curl failure, dead port)",
                    exc
                ))
            }
            Ok(_) => Err("dead endpoint answered, drill is void".to_string()),
        }
    });
    stage(&mut stages, STAGE_NAMES[1], || {
        expect_loud_failure(surface, &["snapshot", "--room", "drill-room"], &env, None)
    });
    stage(&mut stages, STAGE_NAMES[2], || {
        expect_loud_failure(
            surface,
            &["brief", "--morning", "--room", "drill-room"],
            &env,
            None,
        )
    });
    stage(&mut stages, STAGE_NAMES[3], || {
        let argv: Vec<String> = [
            "brief", "--morning", "--room", "drill-room", "--now", &now_s, "--dry-run",
        ]
        .iter()
        .map(|s| s.to_string())
        .collect();
        let (code, out, err) = surface.cli(&argv, &env);
        if code != 0 {
            return Err(format!("dry-run brief exited {}: {:?} {:?}", code, out, err));
        }
        if !out.starts_with("TEMPLATE") {
            return Err(format!(
                "dry-run brief first line is not TEMPLATE: {:?}",
                out.chars().take(80).collect::<String>()
            ));
        }
        if err.contains("Traceback") {
            return Err(format!("dry-run brief traced: {:?}", err));
        }
        Ok("exit 0, TEMPLATE brief, store-free by dry run".to_string())
    });
    stage(&mut stages, STAGE_NAMES[4], || {
        expect_loud_failure(
            surface,
            &["brief", "--list", "--room", "drill-room"],
            &env,
            None,
        )
    });
    stage(&mut stages, STAGE_NAMES[5], || {
        expect_loud_failure(
            surface,
            &["brief", "--show", "--room", "drill-room", "--ts", &now_s],
            &env,
            None,
        )
    });
    stage(&mut stages, STAGE_NAMES[6], || {
        expect_loud_failure(surface, &["dispatch", "--show", "drill-missing"], &env, None)
    });
    stage(&mut stages, STAGE_NAMES[7], || {
        expect_loud_failure(surface, &["dispatch", "--undo", "drill-missing"], &env, None)
    });
    stage(&mut stages, STAGE_NAMES[8], || {
        expect_loud_failure(
            surface,
            &[
                "dispatch",
                "--goal",
                "drill goal",
                "--plan",
                PLAN_PATH,
                "--approve",
            ],
            &env,
            Some("no dispatch record stored"),
        )
    });
    stage(&mut stages, STAGE_NAMES[9], || {
        let argv: Vec<String> = [
            "dispatch", "--goal", "drill goal", "--dry-run", "--plan", PLAN_PATH,
        ]
        .iter()
        .map(|s| s.to_string())
        .collect();
        let (code, out, err) = surface.cli(&argv, &env);
        if code != 0 {
            return Err(format!("dry-run exited {}: {:?} {:?}", code, out, err));
        }
        if !out.contains("jobs in posting order") {
            return Err(format!(
                "dry-run did not render the plan: {:?}",
                out.chars().take(200).collect::<String>()
            ));
        }
        if err.contains("Traceback") {
            return Err(format!("dry-run traced: {:?}", err));
        }
        Ok("exit 0, plan renders, pure validation, no store touch".to_string())
    });
    stage(&mut stages, STAGE_NAMES[10], || {
        expect_loud_failure(
            surface,
            &["alerts", "--show", "--id", "drill-missing"],
            &env,
            None,
        )
    });
    stage(&mut stages, STAGE_NAMES[11], || {
        expect_loud_failure(
            surface,
            &["alerts", "--show", "--room", "drill-room", "--since", &now_s],
            &env,
            None,
        )
    });
    stage(&mut stages, STAGE_NAMES[12], || {
        let (code, out, err) = surface.cli(&["watch".to_string()], &env);
        if code != 2 {
            return Err(format!("watch exited {}, not 2", code));
        }
        if !(err.contains("RELAY_ERROR") && err.contains("UNIMPLEMENTED")) {
            return Err(format!("watch did not report the stub: {:?}", err));
        }
        if !out.is_empty() {
            return Err(format!("watch printed stdout: {:?}", out));
        }
        Ok("exit 2, RELAY_ERROR UNIMPLEMENTED: pre-existing stub, not a Redis failure"
            .to_string())
    });
    stage(&mut stages, STAGE_NAMES[13], || {
        let found = watchdog.tick(&snapshot_fixture(), Some(NOW));
        let kinds: Vec<String> = found.iter().map(|a| a.get("kind").py_str()).collect();
        if !kinds.iter().any(|k| k == "progress-stall") {
            return Err(format!("no progress-stall alert, kinds are {:?}", kinds));
        }
        match surface.write_alert(&found[0], "drill-room", NOW) {
            Err(exc) => {
                if !exc.contains("attempts") {
                    return Err(format!("unexpected error: {}", exc));
                }
                Ok(format!(
                    "tick pure: {} alert(s) incl. progress-stall with no store; write_alert raises RuntimeError, caught, not silent",
                    found.len()
                ))
            }
            Ok(_) => Err("dead store accepted the alert write".to_string()),
        }
    });

    let _ = std::fs::remove_file(&token_file);
    let _ = std::fs::remove_dir(&token_dir);

    let ok = stages.iter().all(|s| s.ok);
    let mut lines: Vec<String> = stages
        .iter()
        .map(|s| {
            format!(
                "{} {}: {}",
                if s.ok { "PASS" } else { "FAIL" },
                s.name,
                s.detail
            )
        })
        .collect();
    lines.push(format!(
        "drill {}: {}/{} stages",
        if ok { "PASSED" } else { "FAILED" },
        stages.iter().filter(|s| s.ok).count(),
        stages.len()
    ));
    DrillResult { ok, stages, lines }
}
