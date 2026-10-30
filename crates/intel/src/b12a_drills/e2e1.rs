//! Port of `os/intel/e2e1.py` — INT-002 end-to-end test 1.
//!
//! Goal -> dispatch dry-run -> approve -> post -> worker claims
//! -> done -> brief reports it, as one scripted run. The loop
//! runs on the in-memory fake surface in the INT-001 namespace,
//! never the live bus: in Python that surface is assembled with
//! `unittest.mock.patch` over jobs / relay_common / intel.store
//! / intel.ingest; here it is the [`Integration`] trait — the
//! same seam, typed. The stage assertions, fixture plan, and
//! transcript format are the source's own.
//!
//! This file also hosts the shared e2e machinery: e2e2, e2e3,
//! and load_check drive the same trait and stage runner.

use super::value::{parse_json, to_json, Value};

/// `integration.INT_ROOM`.
pub const INT_ROOM: &str = "build-int";
/// `integration.INT_JOBNS`.
pub const INT_JOBNS: &str = "muse-bus:int-job";
/// `integration.INT_CAPNS`.
pub const INT_CAPNS: &str = "muse-bus:int-cap";

/// `brief.BRIEF_BUDGETS` (B10).
pub fn brief_budget(kind: &str) -> Option<i64> {
    match kind {
        "morning" => Some(220),
        "onjoin" => Some(150),
        "ondemand" => Some(300),
        _ => None,
    }
}

/// The patched-together surface the e2e loops run against:
/// `intel.integration` + `intel.dispatch` + `intel.ingest` +
/// `intel.brief` + `intel.store` alert seats + the jobs CLI +
/// `mos.capabilities` + the fake clock. Implementations are the
/// harness's (fake surface in tests, the real ports at gate 1).
#[allow(clippy::too_many_arguments)]
pub trait Integration {
    /// `integration.apply_env()` — returns the applied mapping.
    fn apply_env(&self) -> Value;
    /// `dispatch.dry_run_plan(plan_json)` — rendered detail.
    fn dry_run_plan(&self, plan_json: &str) -> String;
    /// `dispatch.validated_plan(plan_json)` -> (plan, order, clamps).
    fn validated_plan(&self, plan_json: &str) -> (Value, Vec<String>, Vec<Value>);
    /// `dispatch.request_approval(plan, approve=...)`.
    fn request_approval(&self, plan: &Value, approve: bool) -> bool;
    /// `dispatch.post_plan(plan, order, room=...)` -> (record, stderr).
    fn post_plan(&self, plan: &Value, order: &[String], room: &str) -> (Value, String);
    /// `dispatch.show_dispatch(dispatch_id)`.
    fn show_dispatch(&self, dispatch_id: &str) -> Value;
    /// A jobs.py CLI main run (`_run_cli`): (code, stdout, stderr).
    fn jobs_cli(&self, argv: &[String]) -> (i32, String, String);
    /// `mos.capabilities.register(nick, caps)`.
    fn register_caps(&self, nick: &str, caps: &[&str]) -> bool;
    /// Set the acting nick (relay_common.NICK + jobs.NICK).
    fn set_nick(&self, nick: &str);
    /// `rc.presence_beat()` for the acting nick.
    fn presence_beat(&self);
    /// `ingest.snapshot(room)`.
    fn snapshot(&self, room: &str) -> Value;
    /// `brief.cap_snapshot_window(snapshot)` (BRF-023 cap).
    fn cap_snapshot_window(&self, snapshot: &Value) -> Value;
    /// `brief.compose_template_brief(snapshot, boot=...)`.
    fn compose_template_brief(&self, snapshot: &Value, boot: bool) -> String;
    /// `brief.build_previous_session(record, jobs)`.
    fn build_previous_session(&self, record: &Value, jobs: &[Value]) -> Option<Value>;
    /// `brief.previous_session_digest(prev)`.
    fn previous_session_digest(&self, prev: &Value) -> Option<String>;
    /// `brief.generate_brief(snapshot, room, kind=..., nick=..., now=...)`
    /// -> (text, stored record).
    fn generate_brief(
        &self,
        snapshot: &Value,
        room: &str,
        kind: &str,
        nick: Option<&str>,
        now: Option<i64>,
    ) -> (String, Value);
    /// `brief.detect_new_nicks(snapshot)`.
    fn detect_new_nicks(&self, snapshot: &Value) -> Vec<String>;
    /// `brief.offer_onjoin_brief(snapshot, room, now=...)` -> offers.
    fn offer_onjoin_brief(&self, snapshot: &Value, room: &str, now: Option<i64>) -> Vec<Value>;
    /// `brief.list_briefs(room)`.
    fn list_briefs(&self, room: &str) -> Vec<Value>;
    /// `brief.get_brief(room, ts)` — stored briefs read back by ts.
    fn get_brief(&self, room: &str, ts: i64) -> Option<Value>;
    /// `store.write_alert(alert, room=...)` -> the stored WDG-010 record.
    fn write_alert(&self, alert: &Value, room: &str) -> Value;
    /// `store.get_alert(alert_id)`; None when absent.
    fn read_alert(&self, alert_id: &str) -> Option<Value>;
    /// The harness clock (`time.time` under the fake, or wall).
    fn now(&self) -> i64;
    /// Advance the fake clock (e2e2/e2e3 time travel).
    fn advance(&self, seconds: i64);
    /// Seed a room's message list directly (load_check stage 2).
    fn seed_room(&self, room: &str, messages: Vec<Value>);
    /// The room's raw stored messages (load_check verify).
    fn room_messages(&self, room: &str) -> Vec<Value>;
}

/// `_job_list_json`: run `list --json`, parse the job list.
pub fn job_list_json(deps: &dyn Integration) -> Result<Vec<Value>, String> {
    let (code, out, _err) = deps.jobs_cli(&["list".into(), "--json".into()]);
    if code != 0 {
        return Err(format!("jobs list failed with exit {}", code));
    }
    match parse_json(&out) {
        Some(Value::List(items)) => Ok(items),
        _ => Err("jobs list output is not a JSON list".to_string()),
    }
}

/// One stage outcome, in run order.
#[derive(Debug, Clone, PartialEq)]
pub struct Stage {
    pub name: String,
    pub ok: bool,
    pub detail: String,
}

/// The stage runner: a stage failure is a loop failure,
/// reported, not traced (`f"{type(exc).__name__}: {exc}"` in the
/// source; assertion failures read "AssertionError: <msg>").
pub fn stage(stages: &mut Vec<Stage>, name: &str, f: impl FnOnce() -> Result<String, String>) {
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

/// A finished loop: stages, verdict, transcript, and the
/// source's success extras (dispatch/job ids when present).
#[derive(Debug, Clone)]
pub struct LoopResult {
    pub ok: bool,
    pub stages: Vec<Stage>,
    pub transcript: String,
    pub extras: Value,
}

pub fn transcript(
    header: &[String],
    stages: &[Stage],
    tag: &str,
    ok: bool,
) -> String {
    let mut lines: Vec<String> = header.to_vec();
    lines.push(String::new());
    for s in stages {
        lines.push(format!(
            "[{}] {}: {}",
            if s.ok { "PASS" } else { "FAIL" },
            s.name,
            s.detail
        ));
    }
    lines.push(String::new());
    lines.push(format!(
        "{}: {}",
        tag,
        if ok { "PASS (all stages)" } else { "FAIL" }
    ));
    lines.join("\n") + "\n"
}

pub const GOAL: &str = "Probe the snapshot path, then report the result in the brief.";

/// The hand-authored plan fixture, byte-identical to the
/// source's `json.dumps` output (default separators).
pub fn plan_json() -> String {
    let job = |key: &str, title: &str, spec: &str, files: Vec<Value>, deps: Vec<Value>, accept: Vec<Value>| {
        Value::obj(vec![
            ("key", Value::s(key)),
            ("title", Value::s(title)),
            ("spec", Value::s(spec)),
            ("files", Value::List(files)),
            ("deps", Value::List(deps)),
            ("max_attempts", Value::Int(3)),
            ("accept", Value::List(accept)),
        ])
    };
    to_json(&Value::obj(vec![
        (
            "summary",
            Value::s("Probe the snapshot path, then report it in the brief."),
        ),
        (
            "jobs",
            Value::List(vec![
                job(
                    "probe",
                    "Write the e2e probe note",
                    "Goal: prove the loop. Context: INT-002 fixture. Files: intel/e2e1_probe.txt. Steps: write the note. Out of scope: any other file.",
                    vec![Value::s("intel/e2e1_probe.txt")],
                    vec![],
                    vec![Value::s("file-exists: intel/e2e1_probe.txt")],
                ),
                job(
                    "report",
                    "Record the probe result in the e2e log",
                    "Goal: close the loop. Context: INT-002 fixture. Files: intel/evals/e2e1.log. Steps: append the probe result. Out of scope: any other file.",
                    vec![Value::s("intel/evals/e2e1.log")],
                    vec![Value::s("probe")],
                    vec![Value::s("contains: intel/evals/e2e1.log :: probe")],
                ),
            ]),
        ),
    ]))
}

const STAGE_NAMES: [&str; 6] = [
    "dry-run",
    "approve",
    "post",
    "worker probe",
    "worker report",
    "brief",
];

/// `run_loop(write_log)` — the INT-002 loop. The transcript
/// write of the source (intel/evals/e2e1.log) is the caller's:
/// the transcript rides in the result, like the returned dict.
pub fn run_loop(deps: &dyn Integration) -> LoopResult {
    deps.apply_env();
    let plan_json = plan_json();
    let mut stages: Vec<Stage> = Vec::new();
    let mut plan_holder: Option<(Value, Vec<String>)> = None;
    let mut record_holder: Option<(Value, std::collections::BTreeMap<String, String>)> = None;

    stage(&mut stages, STAGE_NAMES[0], || {
        let before = job_list_json(deps)?;
        if !before.is_empty() {
            return Err(format!("job list not empty before: {}", Value::List(before).py_repr()));
        }
        let detail = deps.dry_run_plan(&plan_json);
        for needle in [
            "Write the e2e probe note",
            "Record the probe result in the e2e log",
            "jobs in posting order: probe -> report",
        ] {
            if !detail.contains(needle) {
                return Err(format!("dry-run detail missing {:?}", needle));
            }
        }
        let after = job_list_json(deps)?;
        if !after.is_empty() {
            return Err(format!("dry-run posted jobs: {}", Value::List(after).py_repr()));
        }
        Ok("rendered probe -> report in posting order; job list empty before and after"
            .to_string())
    });

    stage(&mut stages, STAGE_NAMES[1], || {
        let (plan, order, clamps) = deps.validated_plan(&plan_json);
        if order != vec!["probe".to_string(), "report".to_string()] {
            return Err(format!("order {:?}", order));
        }
        if !clamps.is_empty() {
            return Err(format!(
                "unexpected clamps {}",
                Value::List(clamps).py_repr()
            ));
        }
        if !deps.request_approval(&plan, true) {
            return Err("approval with approve=True must pass".to_string());
        }
        if deps.request_approval(&plan, false) {
            return Err("approval without a human must deny".to_string());
        }
        plan_holder = Some((plan, order));
        Ok("validated plan, order probe -> report, no clamps".to_string())
    });

    stage(&mut stages, STAGE_NAMES[2], || {
        let (plan, order) = plan_holder
            .clone()
            .ok_or_else(|| "approve stage did not hold a plan".to_string())?;
        deps.set_nick("pax");
        let (record, stderr) = deps.post_plan(&plan, &order, INT_ROOM);
        if !stderr.contains("posting unsigned") {
            return Err("unsigned post must warn loudly on stderr".to_string());
        }
        if record.get("signed") != Value::Bool(false) {
            return Err("record must read signed=False".to_string());
        }
        let jobs = record.get("jobs");
        let job_items = jobs.as_list().cloned().unwrap_or_default();
        let keys: Vec<String> = job_items
            .iter()
            .map(|j| j.get("key").py_str())
            .collect();
        if keys != vec!["probe".to_string(), "report".to_string()] {
            return Err(format!("posted keys {:?}", keys));
        }
        let mut ids = std::collections::BTreeMap::new();
        for j in &job_items {
            ids.insert(j.get("key").py_str(), j.get("id").py_str());
        }
        if ids["report"] == ids["probe"] {
            return Err("report and probe ids must differ".to_string());
        }
        let listed = job_list_json(deps)?;
        let by_id = |id: &str| listed.iter().find(|j| j.get("id").py_str() == id).cloned();
        let probe = by_id(&ids["probe"]).ok_or("probe job not listed")?;
        let report = by_id(&ids["report"]).ok_or("report job not listed")?;
        if probe.get("status").as_str() != Some("open") {
            return Err("probe job must read open".to_string());
        }
        if report.get("status").as_str() != Some("open") {
            return Err("report job must read open".to_string());
        }
        if report.get("deps").py_str() != ids["probe"] {
            return Err("report must carry the real probe id as its dep".to_string());
        }
        let detail = format!(
            "dispatch {}: probe -> {}, report -> {}, signed=False with the unsigned warning",
            record.get("id").py_str(),
            ids["probe"],
            ids["report"]
        );
        record_holder = Some((record, ids));
        Ok(detail)
    });

    let do_worker = |deps: &dyn Integration,
                     record_holder: &Option<(Value, std::collections::BTreeMap<String, String>)>,
                     key: &str,
                     note: &str,
                     expected: Vec<(&str, &str)>|
     -> Result<String, String> {
        let (record, ids) = record_holder
            .clone()
            .ok_or_else(|| "post stage did not hold a record".to_string())?;
        deps.set_nick("worker-a");
        let job_id = ids[key].clone();
        let (code, _out, err) = deps.jobs_cli(&["claim".into(), job_id.clone()]);
        if code != 0 {
            return Err(format!("claim {} failed: {}", key, err));
        }
        let (code, _out, err) = deps.jobs_cli(&[
            "progress".into(),
            job_id.clone(),
            "--note".into(),
            note.into(),
        ]);
        if code != 0 {
            return Err(format!("progress {} failed: {}", key, err));
        }
        let (code, _out, err) = deps.jobs_cli(&[
            "done".into(),
            job_id.clone(),
            "--commit".into(),
            "e2e1-no-real-commit".into(),
            "--note".into(),
            note.into(),
        ]);
        if code != 0 {
            return Err(format!("done {} failed: {}", key, err));
        }
        let report = deps.show_dispatch(&record.get("id").py_str());
        let mut by_key: Vec<(String, Value)> = Vec::new();
        if let Some(jobs) = report.get("jobs").as_list() {
            for job in jobs {
                by_key.push((job.get("key").py_str(), job.get("status")));
            }
        }
        let expected_map: Vec<(String, Value)> = expected
            .iter()
            .map(|(k, v)| (k.to_string(), Value::s(v)))
            .collect();
        if by_key != expected_map {
            return Err(format!(
                "show after {} done reads {}, expected {}",
                key,
                Value::Map(by_key).py_str(),
                Value::Map(expected_map).py_str()
            ));
        }
        Ok(format!(
            "{} claimed, progressed, done as worker-a; show reads {}",
            key,
            Value::Map(by_key).py_str()
        ))
    };

    stage(&mut stages, STAGE_NAMES[3], || {
        do_worker(
            deps,
            &record_holder,
            "probe",
            "probe note written",
            vec![("probe", "done"), ("report", "open")],
        )
    });
    stage(&mut stages, STAGE_NAMES[4], || {
        do_worker(
            deps,
            &record_holder,
            "report",
            "probe result recorded",
            vec![("probe", "done"), ("report", "done")],
        )
    });

    stage(&mut stages, STAGE_NAMES[5], || {
        let (_record, ids) = record_holder
            .clone()
            .ok_or_else(|| "post stage did not hold a record".to_string())?;
        let snapshot = deps.snapshot(INT_ROOM);
        // INT-024: the BRF-023 window cap runs before composing
        // (the source calls it twice; the second call is the
        // route-BRF-023 comment's duplicate — ported as-is).
        let snapshot = deps.cap_snapshot_window(&snapshot);
        let snapshot = deps.cap_snapshot_window(&snapshot);
        if !snapshot.get("source_window").is_dict() {
            return Err("e2e brief stage must carry a BRF-023 window record".to_string());
        }
        let snap_jobs = snapshot.get("jobs");
        let job_items = snap_jobs.as_list().cloned().unwrap_or_default();
        let by_id = |id: &str| job_items.iter().find(|j| j.get("id").py_str() == id).cloned();
        let probe = by_id(&ids["probe"]).ok_or("probe missing from snapshot")?;
        let report = by_id(&ids["report"]).ok_or("report missing from snapshot")?;
        if probe.get("status").as_str() != Some("done") {
            return Err("probe must read done in the snapshot".to_string());
        }
        if report.get("status").as_str() != Some("done") {
            return Err("report must read done in the snapshot".to_string());
        }
        let plain = deps.compose_template_brief(&snapshot, false);
        let in_flight = plain
            .split("In flight")
            .nth(1)
            .and_then(|rest| rest.split("Owners").next())
            .ok_or_else(|| "brief has no In flight section".to_string())?;
        if !in_flight.contains("Nothing reported in this window") {
            return Err("no job may read in flight once both are done".to_string());
        }
        let prev = deps
            .build_previous_session(
                &Value::obj(vec![("generated_at", Value::Int(deps.now()))]),
                &job_items,
            )
            .ok_or_else(|| "previous session must build".to_string())?;
        let digest = deps
            .previous_session_digest(&prev)
            .ok_or_else(|| "previous session digest must exist".to_string())?;
        for needle in [
            "2 jobs completed",
            "Write the e2e probe note",
            "Record the probe result in the e2e log",
        ] {
            if !digest.contains(needle) {
                return Err(format!("digest missing {:?}: {}", needle, digest));
            }
        }
        let mut boot_snapshot = snapshot.clone();
        boot_snapshot.set("previous_session", prev);
        let boot = deps.compose_template_brief(&boot_snapshot, true);
        if !boot.contains(&digest) {
            return Err("boot brief must carry the digest".to_string());
        }
        Ok(format!(
            "snapshot carries both jobs done; boot brief reports: {}",
            digest
        ))
    });

    let ok = stages.len() == STAGE_NAMES.len() && stages.iter().all(|s| s.ok);
    let mut extras = Value::obj(vec![]);
    if ok {
        if let Some((record, ids)) = &record_holder {
            extras.set("dispatch_id", record.get("id"));
            extras.set(
                "job_ids",
                Value::Map(
                    ids.iter()
                        .map(|(k, v)| (k.clone(), Value::s(v)))
                        .collect(),
                ),
            );
        }
    }
    let header = vec![
        "INT-002 end-to-end test 1".to_string(),
        format!("goal: {}", GOAL),
        "plan: hand-authored fixture (no live Spark call; see module docstring)".to_string(),
        format!(
            "queue: in-memory fake surface, namespace {}, room {}",
            INT_JOBNS, INT_ROOM
        ),
    ];
    let text = transcript(&header, &stages, "INT-002", ok);
    LoopResult {
        ok,
        stages,
        transcript: text,
        extras,
    }
}
