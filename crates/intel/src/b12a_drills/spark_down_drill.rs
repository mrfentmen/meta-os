//! Port of `os/intel/spark_down_drill.py` — INT-008: Spark
//! endpoint down for all features, scripted drill.
//!
//! Every Spark call fails because the endpoint is genuinely
//! dead (http://127.0.0.1:9, a closed localhost port — the
//! shipped client over the shipped HTTP transport), and the
//! drill proves nothing crashes and every fallback engages:
//! template brief, canned BRF-026 spark_down line, template
//! record model, FALLBACK dispatch plan after exactly one
//! endpoint call, identical watchdog explanations with the
//! down polish client, and a CLI template brief. The client,
//! brief, dispatch, watchdog, and CLI surfaces ride the
//! deps/e2e traits (B11/B10/B21 own the real ones); the
//! api_key in the source is a drill placeholder, never a
//! real credential.

use super::deps::{BriefSurface, DispatchSurface, SparkClient, Watchdog};
use super::redis_down_drill::DrillResult;
use super::value::Value;

pub const DOWN_ENDPOINT: &str = "http://127.0.0.1:9/spark-down-drill";
pub const GOAL: &str = "Probe the snapshot path, then report the result.";
pub const NOW: i64 = 10000;

const STAGE_NAMES: [&str; 6] = [
    "precondition",
    "brief",
    "brief-record",
    "dispatch",
    "watchdog",
    "cli",
];

/// The fixture snapshot, verbatim from the source.
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

/// The CLI seat for stage 6: `intel.py brief --morning` over a
/// snapshot file (dry run, fake store surface) returns
/// (exit code, stdout); a SystemExit in the source is an
/// assertion failure there, a nonzero code here.
pub trait SparkDownCli {
    fn brief_morning_dry_run(&self, snapshot: &Value, room: &str, now: i64) -> (i32, String);
}

fn stage(
    stages: &mut Vec<super::e2e1::Stage>,
    name: &str,
    f: impl FnOnce() -> Result<String, String>,
) {
    match f() {
        Ok(detail) => stages.push(super::e2e1::Stage {
            name: name.to_string(),
            ok: true,
            detail,
        }),
        Err(msg) => stages.push(super::e2e1::Stage {
            name: name.to_string(),
            ok: false,
            detail: format!("AssertionError: {}", msg),
        }),
    }
}

/// `run_drill(write_log)` — the INT-008 drill. One `client`
/// plays the source's per-stage `_down_client()` (a fresh
/// client per stage there; the seam object is stateless about
/// the endpoint and the ledger reads $0 because the endpoint
/// is dead).
pub fn run_drill(
    client: &dyn SparkClient,
    brief: &dyn BriefSurface,
    dispatch: &dyn DispatchSurface,
    watchdog: &dyn Watchdog,
    cli: &dyn SparkDownCli,
) -> DrillResult {
    let mut stages: Vec<super::e2e1::Stage> = Vec::new();
    let snapshot = snapshot_fixture();

    stage(&mut stages, STAGE_NAMES[0], || {
        match client.complete("hello", "drill-probe") {
            Err(exc) => {
                if !exc.contains("unreachable") {
                    return Err(format!("unexpected error: {}", exc));
                }
                Ok(format!("SparkError: {} (0 real calls completed)", exc))
            }
            Ok(_) => Err("dead endpoint answered, drill is void".to_string()),
        }
    });

    stage(&mut stages, STAGE_NAMES[1], || {
        let text = brief.compose_brief(&snapshot, "morning", client, Some(NOW));
        if !text.starts_with("TEMPLATE") {
            return Err(format!(
                "brief first line is not TEMPLATE: {:?}",
                text.chars().take(80).collect::<String>()
            ));
        }
        let words = text.split_whitespace().count();
        if words > 220 {
            return Err(format!("morning brief {} words, over 220", words));
        }
        if !text.contains("Vendor API key") {
            return Err("blocked job missing from brief".to_string());
        }
        let spark_only = brief.compose_spark_brief(&snapshot, "morning", client);
        let canned = brief.brief_failure_line("spark_down");
        if spark_only != canned {
            return Err(format!(
                "spark-only path did not return the canned line: {:?}",
                spark_only
            ));
        }
        Ok(format!(
            "template brief {} words, blocked job named, spark-only path returns the canned line verbatim",
            words
        ))
    });

    stage(&mut stages, STAGE_NAMES[2], || {
        let (text, record) = brief.generate_brief(
            &snapshot,
            "drill-room",
            "morning",
            Some(NOW),
            true,
            client,
        );
        if !text.starts_with("TEMPLATE") {
            return Err(format!(
                "record text first line is not TEMPLATE: {:?}",
                text.chars().take(80).collect::<String>()
            ));
        }
        if record.get("model").as_str() != Some("template") {
            return Err(format!(
                "record model is {:?}, not template",
                record.get("model").py_repr()
            ));
        }
        Ok("dry-run record model is template for template text".to_string())
    });

    stage(&mut stages, STAGE_NAMES[3], || {
        let calls: std::cell::RefCell<Vec<String>> = std::cell::RefCell::new(Vec::new());
        let down_complete = |goal: &str| -> Result<String, String> {
            calls.borrow_mut().push(goal.to_string());
            client.complete(
                &format!("Write a dispatch plan for this goal: {}", goal),
                "dispatch",
            )
        };
        let (result, stderr) = dispatch.plan_from_spark(GOAL, &down_complete);
        let call_count = calls.borrow().len();
        if call_count != 1 {
            return Err(format!("endpoint called {} times", call_count));
        }
        if result.get("fallback") != Value::Bool(true) {
            return Err("no fallback on endpoint down".to_string());
        }
        let order: Vec<String> = result
            .get("order")
            .as_list()
            .map(|items| items.iter().map(|v| v.py_str()).collect())
            .unwrap_or_default();
        if order != vec!["fallback-job".to_string()] {
            return Err(format!("order is {:?}", order));
        }
        let plan = result.get("plan");
        let jobs = plan.get("jobs");
        let job_items = jobs.as_list().cloned().unwrap_or_default();
        if job_items.len() != 1 {
            return Err("fallback plan is not one job".to_string());
        }
        let job = job_items[0].clone();
        if !plan.get("summary").py_str().contains("FALLBACK") {
            return Err("summary not marked".to_string());
        }
        if !job.get("title").py_str().contains("FALLBACK") {
            return Err("title not marked".to_string());
        }
        if !job.get("spec").py_str().contains("FALLBACK") {
            return Err("spec not marked".to_string());
        }
        if !job.get("spec").py_str().contains(GOAL) {
            return Err("raw goal missing from spec".to_string());
        }
        if !result.get("warning").py_str().contains("endpoint is down") {
            return Err(format!(
                "warning does not name the outage: {:?}",
                result.get("warning").py_repr()
            ));
        }
        if !stderr.contains("endpoint is down") {
            return Err("endpoint-down warning missing from stderr".to_string());
        }
        if client.spent_usd() != 0.0 {
            return Err("dead endpoint recorded spend".to_string());
        }
        Ok("FALLBACK plan, one job, raw goal in spec, endpoint called once, nothing posted, $0 spent".to_string())
    });

    stage(&mut stages, STAGE_NAMES[4], || {
        let plain = watchdog.tick(&snapshot, Some(NOW));
        let polished = watchdog.tick_with_polish(&snapshot, Some(NOW), client);
        if plain.is_empty() {
            return Err("no alert fired on the stall snapshot".to_string());
        }
        let kinds: Vec<String> = plain.iter().map(|a| a.get("kind").py_str()).collect();
        if !kinds.iter().any(|k| k == "progress-stall") {
            return Err(format!("no progress-stall alert, kinds are {:?}", kinds));
        }
        if polished.len() != plain.len() {
            return Err(format!(
                "polish changed alert count: {} vs {}",
                polished.len(),
                plain.len()
            ));
        }
        for (before, after) in plain.iter().zip(polished.iter()) {
            if before.get("explanation") != after.get("explanation") {
                return Err("down polish changed a template explanation".to_string());
            }
        }
        Ok(format!(
            "{} alert(s) incl. progress-stall, template explanations identical with down polish",
            plain.len()
        ))
    });

    stage(&mut stages, STAGE_NAMES[5], || {
        let (code, out) = cli.brief_morning_dry_run(&snapshot, "drill-room", NOW);
        if code != 0 {
            return Err(format!("CLI exited {}", code));
        }
        if !out.starts_with("TEMPLATE") {
            return Err(format!(
                "CLI brief first line is not TEMPLATE: {:?}",
                out.chars().take(80).collect::<String>()
            ));
        }
        Ok("CLI brief --morning exits 0 with a template brief".to_string())
    });

    let ok = stages.iter().all(|s| s.ok);
    let mut lines: Vec<String> = vec![
        "INT-008 Spark-down drill: endpoint is down for all features".to_string(),
        format!(
            "Endpoint: {} (closed localhost port, real HTTP transport)",
            DOWN_ENDPOINT
        ),
        format!(
            "Snapshot: 2 messages, 2 jobs (1 stalled claimed, 1 blocked), clock {}",
            NOW
        ),
    ];
    for s in &stages {
        lines.push(format!(
            "[{}] {}: {}",
            if s.ok { "PASS" } else { "FAIL" },
            s.name,
            s.detail
        ));
    }
    lines.push(format!(
        "RESULT: {}",
        if ok {
            "PASS, every fallback engaged, nothing crashed"
        } else {
            "FAIL"
        }
    ));
    DrillResult { ok, stages, lines }
}
