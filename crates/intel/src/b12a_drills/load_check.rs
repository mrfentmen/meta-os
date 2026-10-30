//! Port of `os/intel/load_check.py` — INT-006 load check.
//!
//! A 2,000-message room and a 200-job queue on the in-memory
//! fake surface, with snapshot, template-brief build, and
//! watchdog tick each timed against a stated budget. The room
//! is seeded directly (past the bus_trim 500 cap) after the
//! queue — a beyond-cap stress state for the read path, not a
//! live-reachable room; the source's "What this does not
//! prove" section rides in `render_load_md` verbatim. Timings
//! are wall times (the source's perf_counter; here Instant).

use super::deps::Watchdog;
use super::e2e1::{
    brief_budget, job_list_json, stage, Integration, LoopResult, Stage, INT_CAPNS, INT_JOBNS,
    INT_ROOM,
};
use super::value::Value;

pub const MESSAGE_COUNT: i64 = 2000;
pub const JOB_COUNT: i64 = 200;
pub const CLAIMED_COUNT: i64 = 10;
pub const WORKER: &str = "load-worker";
pub const SNAPSHOT_BUDGET_SECONDS: f64 = 5.0;
pub const BRIEF_BUDGET_SECONDS: f64 = 5.0;
pub const TICK_BUDGET_SECONDS: f64 = 5.0;
pub const TOTAL_BUDGET_SECONDS: f64 = 15.0;

const STAGE_NAMES: [&str; 6] = [
    "seed queue",
    "seed room",
    "snapshot",
    "brief",
    "tick",
    "budgets",
];

/// `render_load_md(result)` — the timings-table markdown for a
/// finished run_check result.
pub fn render_load_md(result: &Value) -> String {
    let timings = result.get("timings");
    let budgets = result.get("budgets");
    let measured = |map: &Value, name: &str| map.get(name).as_number().unwrap_or(0.0);
    let mut lines: Vec<String> = vec![
        "# INT-006 load check".to_string(),
        String::new(),
        "2,000-message room + 200-job queue, timed on the in-memory fake surface (see intel/load_check.py). Timings are sandbox wall times, not production hardware and not a live Redis round trip.".to_string(),
        String::new(),
        "## Timings".to_string(),
        String::new(),
        "| Operation | Measured (s) | Budget (s) | Result |".to_string(),
        "| --- | --- | --- | --- |".to_string(),
    ];
    for name in ["snapshot", "brief", "tick"] {
        let m = measured(&timings, name);
        let b = measured(&budgets, name);
        lines.push(format!(
            "| {} | {:.3} | {:.1} | {} |",
            name,
            m,
            b,
            if m < b { "PASS" } else { "FAIL" }
        ));
    }
    let total_m = measured(&timings, "total");
    let total_b = measured(&budgets, "total");
    lines.push(format!(
        "| total (3 ops) | {:.3} | {:.1} | {} |",
        total_m,
        total_b,
        if total_m < total_b { "PASS" } else { "FAIL" }
    ));
    let message_count = result.get("message_count").as_int().unwrap_or(0);
    let job_count = result.get("job_count").as_int().unwrap_or(0);
    let claimed_count = result.get("claimed_count").as_int().unwrap_or(0);
    lines.extend([
        String::new(),
        "## Counts".to_string(),
        String::new(),
        format!("- Room messages in snapshot: {}", message_count),
        format!(
            "- Jobs in snapshot: {} ({} claimed with fresh progress, {} open)",
            job_count,
            claimed_count,
            job_count - claimed_count
        ),
        format!(
            "- Morning brief words: {} (FND-034 morning budget {})",
            result.get("brief_words").py_str(),
            result.get("brief_word_budget").py_str()
        ),
        format!(
            "- Watchdog tick alerts: {} (healthy load room, zero expected)",
            result.get("alert_count").py_str()
        ),
        String::new(),
        "## Budgets".to_string(),
        String::new(),
        "The plan documents no per-operation wall-clock budget for snapshot, brief, or tick, so this check adopts one and records it here: 5 seconds per operation, 15 seconds for the three together. The 5 second figure is an order of magnitude inside the watchdog loop's documented 60 second default interval, so a tick that fits it can never fall behind the loop it feeds. The brief word budget is the plan's own: FND-034 caps a morning brief at 220 words.".to_string(),
        String::new(),
        "## What this does not prove".to_string(),
        String::new(),
        "- A live-reachable 2,000-message room: every jobs announcement runs bus_trim, which keeps only the newest 500 messages, so the 2,000-message state here is a beyond-cap stress state for the read path, seeded directly after the queue.".to_string(),
        "- A live Redis round trip: the fake backend has no network cost, so live timings will be higher.".to_string(),
        "- A Spark-composed brief: the brief here is a template brief, because GOV-001 leaves live Spark transport blocked.".to_string(),
        "- Alert behavior under load: the tick yields zero alerts here by design (every claimed job is healthy). Alert counts under a loaded, failing room are Milo's INT-023, not this check.".to_string(),
        String::new(),
    ]);
    lines.join("\n")
}

/// `run_check(write_files)` — the INT-006 load check. The
/// transcript and table ride in the result (the source also
/// writes intel/evals/load.log + load.md; that write is the
/// caller's, as in the e2e ports).
pub fn run_check(deps: &dyn Integration, watchdog: &dyn Watchdog) -> LoopResult {
    deps.apply_env();
    let mut stages: Vec<Stage> = Vec::new();
    let mut posted: Vec<String> = Vec::new();
    let mut snapshot_holder: Option<Value> = None;
    let mut timings: Vec<(String, f64)> = Vec::new();
    let mut brief_words: i64 = 0;
    let mut brief_text = String::new();

    let timing = |map: &Vec<(String, f64)>, name: &str| -> f64 {
        map.iter()
            .find(|(k, _)| k == name)
            .map(|(_, v)| *v)
            .unwrap_or(0.0)
    };

    stage(&mut stages, STAGE_NAMES[0], || {
        deps.set_nick("pax");
        let before = job_list_json(deps)?;
        if !before.is_empty() {
            return Err(format!(
                "job list not empty before: {}",
                Value::List(before).py_repr()
            ));
        }
        let mut ids: Vec<String> = Vec::new();
        for number in 1..=JOB_COUNT {
            let spec = format!(
                "Goal: finish load job {}. Context: INT-006 fixture. Files: intel/load_{}.txt. Steps: write the note. Out of scope: any other file.",
                number, number
            );
            let argv: Vec<String> = vec![
                "post".into(),
                "--title".into(),
                format!("Load job {}", number),
                "--spec".into(),
                spec,
                "--files".into(),
                format!("intel/load_{}.txt", number),
                "--max-attempts".into(),
                "3".into(),
                "--room".into(),
                INT_ROOM.into(),
            ];
            let (code, out, err) = deps.jobs_cli(&argv);
            if code != 0 {
                return Err(format!("post {} failed: {}", number, err));
            }
            if !out.starts_with("JOB ") {
                return Err(format!("unexpected post out: {}", out));
            }
            ids.push(
                out.split_whitespace()
                    .nth(1)
                    .ok_or("post output carries no job id")?
                    .to_string(),
            );
        }
        let listed = job_list_json(deps)?;
        if listed.len() as i64 != JOB_COUNT {
            return Err(format!(
                "job list holds {} jobs, expected {}",
                listed.len(),
                JOB_COUNT
            ));
        }
        if !deps.register_caps(WORKER, &["python"]) {
            return Err("worker registration must read True".to_string());
        }
        deps.set_nick(WORKER);
        deps.presence_beat();
        for job_id in ids.iter().take(CLAIMED_COUNT as usize) {
            let (code, _out, err) = deps.jobs_cli(&["claim".into(), job_id.clone()]);
            if code != 0 {
                return Err(format!("claim {} failed: {}", job_id, err));
            }
            let (code, _out, err) = deps.jobs_cli(&[
                "progress".into(),
                job_id.clone(),
                "--note".into(),
                "load progress note".into(),
            ]);
            if code != 0 {
                return Err(format!("progress {} failed: {}", job_id, err));
            }
        }
        let listed = job_list_json(deps)?;
        let claimed = ids
            .iter()
            .take(CLAIMED_COUNT as usize)
            .filter(|id| {
                listed
                    .iter()
                    .find(|j| &j.get("id").py_str() == *id)
                    .map(|j| j.get("status").as_str() == Some("claimed"))
                    .unwrap_or(false)
            })
            .count() as i64;
        if claimed != CLAIMED_COUNT {
            return Err(format!(
                "claimed {} jobs, expected {}",
                claimed, CLAIMED_COUNT
            ));
        }
        posted = ids;
        Ok(format!(
            "{} jobs posted, {} claimed and progressed, {} left open",
            JOB_COUNT,
            CLAIMED_COUNT,
            JOB_COUNT - CLAIMED_COUNT
        ))
    });

    stage(&mut stages, STAGE_NAMES[1], || {
        // Seeded after the queue, and directly: every jobs
        // announcement ran bus_trim (newest 500), so clearing
        // the list and pushing exactly 2,000 plain messages is
        // the only way to hold the task's 2,000-message state.
        let messages: Vec<Value> = (0..MESSAGE_COUNT)
            .map(|index| {
                Value::s(&format!(
                    "load-{}: load note {}, routine chatter, nothing to act on",
                    index % 8,
                    index
                ))
            })
            .collect();
        deps.seed_room(INT_ROOM, messages);
        let listed = deps.room_messages(INT_ROOM);
        if listed.len() as i64 != MESSAGE_COUNT {
            return Err(format!(
                "room list holds {} messages, expected {}",
                listed.len(),
                MESSAGE_COUNT
            ));
        }
        Ok(format!(
            "{} messages on the room list, seeded directly after the bus_trim-capped announcements",
            MESSAGE_COUNT
        ))
    });

    stage(&mut stages, STAGE_NAMES[2], || {
        let start = std::time::Instant::now();
        let snapshot = deps.snapshot(INT_ROOM);
        let elapsed = start.elapsed().as_secs_f64();
        let messages = snapshot.get("messages").as_list().map(|m| m.len()).unwrap_or(0);
        if messages as i64 != MESSAGE_COUNT {
            return Err(format!(
                "snapshot holds {} messages, expected {}",
                messages, MESSAGE_COUNT
            ));
        }
        let jobs = snapshot.get("jobs").as_list().map(|j| j.len()).unwrap_or(0);
        if jobs as i64 != JOB_COUNT {
            return Err(format!(
                "snapshot holds {} jobs, expected {}",
                jobs, JOB_COUNT
            ));
        }
        snapshot_holder = Some(snapshot);
        timings.push(("snapshot".to_string(), elapsed));
        Ok(format!(
            "snapshot read {} messages and {} jobs in {:.3}s",
            MESSAGE_COUNT, JOB_COUNT, elapsed
        ))
    });

    stage(&mut stages, STAGE_NAMES[3], || {
        let snapshot = snapshot_holder
            .clone()
            .ok_or("snapshot stage did not hold a snapshot")?;
        let start = std::time::Instant::now();
        let (text, stored) =
            deps.generate_brief(&snapshot, INT_ROOM, "morning", None, Some(deps.now()));
        let elapsed = start.elapsed().as_secs_f64();
        if !text.starts_with("TEMPLATE") {
            return Err("morning brief here must be a template brief".to_string());
        }
        let words = text.split_whitespace().count() as i64;
        let budget = brief_budget("morning").unwrap_or(220);
        if words > budget {
            return Err(format!("morning brief over budget: {} words", words));
        }
        if stored.get("kind").as_str() != Some("morning") {
            return Err(format!("stored {}", stored.py_repr()));
        }
        timings.push(("brief".to_string(), elapsed));
        brief_words = words;
        brief_text = text;
        Ok(format!(
            "morning brief ({} words, budget {}) in {:.3}s, built from the BRF-023 capped 500-message window",
            words, budget, elapsed
        ))
    });

    stage(&mut stages, STAGE_NAMES[4], || {
        let snapshot = snapshot_holder
            .clone()
            .ok_or("snapshot stage did not hold a snapshot")?;
        let start = std::time::Instant::now();
        let got = watchdog.tick(&snapshot, Some(deps.now()));
        let elapsed = start.elapsed().as_secs_f64();
        if !got.is_empty() {
            return Err(format!(
                "healthy load room must yield zero alerts, got {}: {}",
                got.len(),
                Value::List(got).py_repr()
            ));
        }
        timings.push(("tick".to_string(), elapsed));
        Ok(format!("tick yielded zero alerts in {:.3}s", elapsed))
    });

    stage(&mut stages, STAGE_NAMES[5], || {
        let total = timing(&timings, "snapshot") + timing(&timings, "brief") + timing(&timings, "tick");
        let budgets: [(&str, f64); 4] = [
            ("snapshot", SNAPSHOT_BUDGET_SECONDS),
            ("brief", BRIEF_BUDGET_SECONDS),
            ("tick", TICK_BUDGET_SECONDS),
            ("total", TOTAL_BUDGET_SECONDS),
        ];
        for (name, budget) in budgets {
            let value = if name == "total" {
                total
            } else {
                timing(&timings, name)
            };
            if !(value < budget) {
                return Err(format!(
                    "{} took {:.3}s, over its {:.1}s budget",
                    name, value, budget
                ));
            }
        }
        timings.push(("total".to_string(), total));
        Ok(format!(
            "snapshot {:.3}s, brief {:.3}s, tick {:.3}s, total {:.3}s, all inside budget",
            timing(&timings, "snapshot"),
            timing(&timings, "brief"),
            timing(&timings, "tick"),
            total
        ))
    });

    let _ = &posted;
    let ok = stages.len() == STAGE_NAMES.len() && stages.iter().all(|s| s.ok);
    let mut extras = Value::obj(vec![]);
    if ok {
        extras.set("message_count", Value::Int(MESSAGE_COUNT));
        extras.set("job_count", Value::Int(JOB_COUNT));
        extras.set("claimed_count", Value::Int(CLAIMED_COUNT));
        extras.set("brief_words", Value::Int(brief_words));
        extras.set(
            "brief_word_budget",
            Value::Int(brief_budget("morning").unwrap_or(220)),
        );
        extras.set("alert_count", Value::Int(0));
        extras.set(
            "timings",
            Value::Map(
                timings
                    .iter()
                    .map(|(k, v)| (k.clone(), Value::Float(*v)))
                    .collect(),
            ),
        );
        extras.set(
            "budgets",
            Value::obj(vec![
                ("snapshot", Value::Float(SNAPSHOT_BUDGET_SECONDS)),
                ("brief", Value::Float(BRIEF_BUDGET_SECONDS)),
                ("tick", Value::Float(TICK_BUDGET_SECONDS)),
                ("total", Value::Float(TOTAL_BUDGET_SECONDS)),
            ]),
        );
        extras.set("brief_text", Value::s(&brief_text));
        let table = render_load_md(&extras);
        extras.set("table", Value::s(&table));
    }
    let mut lines: Vec<String> = vec![
        "INT-006 load check".to_string(),
        format!(
            "room: {} messages, queue: {} jobs ({} claimed, {} open)",
            MESSAGE_COUNT,
            JOB_COUNT,
            CLAIMED_COUNT,
            JOB_COUNT - CLAIMED_COUNT
        ),
        format!(
            "queue: in-memory fake surface, namespace {}, caps {}, room {}",
            INT_JOBNS, INT_CAPNS, INT_ROOM
        ),
        "clock: fake clock never advanced, so every claimed job stays healthy and the tick must yield zero alerts; timings are perf_counter wall times".to_string(),
        "brief: template path (no live Spark call; GOV-001 leaves live transport blocked), built from the BRF-023 capped 500-message window".to_string(),
        String::new(),
    ];
    for s in &stages {
        lines.push(format!(
            "[{}] {}: {}",
            if s.ok { "PASS" } else { "FAIL" },
            s.name,
            s.detail
        ));
    }
    lines.push(String::new());
    lines.push(format!(
        "INT-006: {}",
        if ok { "PASS (all stages)" } else { "FAIL" }
    ));
    LoopResult {
        ok,
        stages,
        transcript: lines.join("\n") + "\n",
        extras,
    }
}
