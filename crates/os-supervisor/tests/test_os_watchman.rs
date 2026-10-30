//! Parity tests for `os/tests/test_os_watchman.py` (OS-118).
//!
//! The resident bell: wake for newly posted open jobs addressed
//! to sleeping local agents; nudge for stale heartbeats on
//! claimed jobs; no counter anywhere; dedupe with heartbeat
//! refresh; no input mutation; the --once CLI (events as JSON
//! lines, state file, exit 2 on malformed input, missing files
//! read as empty); the unit wiring (relay-watchman.service).

use os_supervisor::watchman;
use serde_json::{json, Value};
use std::collections::HashSet;

const NOW: i64 = 1_000_000;
const STALE: i64 = 300;

fn job(job_id: &str, status: &str, fields: Value) -> Value {
    let mut map = serde_json::Map::new();
    map.insert("id".to_string(), json!(job_id));
    map.insert("status".to_string(), json!(status));
    if let Some(obj) = fields.as_object() {
        for (k, v) in obj {
            map.insert(k.clone(), v.clone());
        }
    }
    Value::Object(map)
}

fn agents() -> std::collections::BTreeMap<String, serde_json::Map<String, Value>> {
    watchman::normalize_agents(&json!({"hana": {"heartbeat_at": null}}))
}

#[test]
fn open_job_wakes_sleeping_local_agent() {
    let jobs = vec![job("7", "open", json!({"addressed_to": "hana", "title": "Write the brief"}))];
    let (events, keys) = watchman::tick(&jobs, &agents(), &HashSet::new(), NOW, STALE);
    assert_eq!(events.len(), 1);
    assert_eq!(events[0]["kind"], json!("wake"));
    assert_eq!(events[0]["job_id"], json!("7"));
    assert_eq!(events[0]["agent"], json!("hana"));
    assert_eq!(keys, vec!["wake:7".to_string()]);
}

#[test]
fn wake_via_legacy_to_field() {
    let agents = watchman::normalize_agents(&json!({"milo": {}}));
    let jobs = vec![job("8", "open", json!({"to": "milo"}))];
    let (events, _) = watchman::tick(&jobs, &agents, &HashSet::new(), NOW, STALE);
    assert_eq!(events.len(), 1);
    assert_eq!(events[0]["agent"], json!("milo"));
}

#[test]
fn no_wake_for_other_agent_awake_or_unaddressed() {
    let agents = watchman::normalize_agents(&json!({"hana": {"heartbeat_at": NOW}}));
    let jobs = vec![
        job("1", "open", json!({"addressed_to": "ghost"})),
        job("2", "open", json!({"addressed_to": "hana"})),
        job("3", "open", json!({})),
    ];
    let (events, _) = watchman::tick(&jobs, &agents, &HashSet::new(), NOW, STALE);
    assert!(events.is_empty());
}

#[test]
fn no_wake_for_done_or_malformed_or_unknown() {
    let jobs = vec![
        job("1", "done", json!({"addressed_to": "hana"})),
        job("2", "cancelled", json!({"addressed_to": "hana"})),
        Value::Object({
            let mut m = serde_json::Map::new();
            m.insert("status".to_string(), json!("open"));
            m.insert("addressed_to".to_string(), json!("hana"));
            m
        }),
        Value::String("not-a-record".to_string()),
        job("3", "open", json!({"addressed_to": "ghost"})),
    ];
    let (events, _) = watchman::tick(&jobs, &agents(), &HashSet::new(), NOW, STALE);
    assert!(events.is_empty());
}

#[test]
fn unregistered_agent_is_not_local() {
    let agents = watchman::normalize_agents(&json!({"buffy": {"heartbeat_at": null, "registered": false}}));
    let jobs = vec![job("9", "open", json!({"addressed_to": "buffy"}))];
    let (events, _) = watchman::tick(&jobs, &agents, &HashSet::new(), NOW, STALE);
    assert!(events.is_empty());
}

#[test]
fn stale_heartbeat_nudges_on_same_cycle() {
    let agents = watchman::normalize_agents(&json!({"milo": {"heartbeat_at": NOW - 1000}}));
    let jobs = vec![job("4", "claimed", json!({"claim": "milo", "title": "Run the drill"}))];
    let (events, keys) = watchman::tick(&jobs, &agents, &HashSet::new(), NOW, STALE);
    assert_eq!(events.len(), 1);
    assert_eq!(events[0]["kind"], json!("nudge"));
    assert_eq!(events[0]["job_id"], json!("4"));
    assert_eq!(events[0]["agent"], json!("milo"));
    assert_eq!(events[0]["heartbeat_age_seconds"], json!(1000));
    assert_eq!(keys, vec![format!("nudge:4:{}", NOW - 1000)]);
}

#[test]
fn fresh_or_missing_heartbeat_never_nudges() {
    let agents = watchman::normalize_agents(
        &json!({"milo": {"heartbeat_at": NOW - 10}, "hana": {"heartbeat_at": null}}),
    );
    let jobs = vec![
        job("5", "claimed", json!({"claim": "milo"})),
        job("6", "claimed", json!({"claim": "hana"})),
    ];
    let (events, _) = watchman::tick(&jobs, &agents, &HashSet::new(), NOW, STALE);
    assert!(events.is_empty());
}

#[test]
fn claim_by_nonlocal_agent_never_nudges() {
    let agents = watchman::normalize_agents(&json!({"milo": {"heartbeat_at": NOW - 1000}}));
    let jobs = vec![job("5", "claimed", json!({"claim": "rowan"}))];
    let (events, _) = watchman::tick(&jobs, &agents, &HashSet::new(), NOW, STALE);
    assert!(events.is_empty());
}

#[test]
fn counter_field_variation_changes_nothing() {
    let base = vec![job("7", "open", json!({"addressed_to": "hana"}))];
    let (first, _) = watchman::tick(&base, &agents(), &HashSet::new(), NOW, STALE);
    let mut drifted = base.clone();
    drifted[0]["bus_message_count"] = json!(999);
    drifted[0]["seen"] = json!(12345);
    let (second, _) = watchman::tick(&drifted, &agents(), &HashSet::new(), NOW, STALE);
    assert_eq!(first, second);
}

#[test]
fn second_tick_with_merged_ledger_is_silent() {
    let jobs = vec![
        job("7", "open", json!({"addressed_to": "hana"})),
        job("4", "claimed", json!({"claim": "milo"})),
    ];
    let agents = watchman::normalize_agents(
        &json!({"hana": {"heartbeat_at": null}, "milo": {"heartbeat_at": NOW - 1000}}),
    );
    let (events, keys) = watchman::tick(&jobs, &agents, &HashSet::new(), NOW, STALE);
    assert_eq!(events.len(), 2);
    let ledger: HashSet<String> = keys.into_iter().collect();
    let (again, _) = watchman::tick(&jobs, &agents, &ledger, NOW, STALE);
    assert!(again.is_empty());
}

#[test]
fn nudge_refires_only_when_heartbeat_refreshes() {
    let jobs = vec![job("4", "claimed", json!({"claim": "milo"}))];
    let old = watchman::normalize_agents(&json!({"milo": {"heartbeat_at": NOW - 1000}}));
    let (_, keys) = watchman::tick(&jobs, &old, &HashSet::new(), NOW, STALE);
    let fresh = watchman::normalize_agents(&json!({"milo": {"heartbeat_at": NOW - 900}}));
    let ledger: HashSet<String> = keys.into_iter().collect();
    let (events, _) = watchman::tick(&jobs, &fresh, &ledger, NOW, STALE);
    assert_eq!(events.len(), 1);
    assert_eq!(events[0]["kind"], json!("nudge"));
}

#[test]
fn inputs_never_mutated() {
    let jobs = vec![job("7", "open", json!({"addressed_to": "hana"}))];
    let agents = agents();
    let ledger = HashSet::new();
    let jobs_before = jobs.clone();
    let agents_before = agents.clone();
    watchman::tick(&jobs, &agents, &ledger, NOW, STALE);
    assert_eq!(jobs, jobs_before);
    assert_eq!(agents, agents_before);
    assert!(ledger.is_empty());
}

fn run_once_files(jobs: &Value, agents: &Value, state: Option<&Value>) -> (tempfile::TempDir, String, String, String) {
    let tmp = tempfile::tempdir().unwrap();
    let jobs_path = tmp.path().join("jobs.json");
    let agents_path = tmp.path().join("agents.json");
    let state_path = tmp.path().join("state.json");
    std::fs::write(&jobs_path, serde_json::to_string(jobs).unwrap()).unwrap();
    std::fs::write(&agents_path, serde_json::to_string(agents).unwrap()).unwrap();
    if let Some(s) = state {
        std::fs::write(&state_path, serde_json::to_string(s).unwrap()).unwrap();
    }
    (
        tmp,
        jobs_path.to_string_lossy().into_owned(),
        agents_path.to_string_lossy().into_owned(),
        state_path.to_string_lossy().into_owned(),
    )
}

#[test]
fn once_prints_event_and_second_run_is_silent() {
    let (_tmp, jobs_path, agents_path, state_path) = run_once_files(
        &json!([{"id": "7", "status": "open", "addressed_to": "hana", "title": "Write it"}]),
        &json!({"hana": {"heartbeat_at": null}}),
        Some(&json!({"rung": []})),
    );
    let mut out = Vec::new();
    let code = watchman::cli(
        &[
            "--once".to_string(),
            "--jobs-file".to_string(),
            jobs_path.clone(),
            "--agents-file".to_string(),
            agents_path.clone(),
            "--state-file".to_string(),
            state_path.clone(),
            "--now".to_string(),
            NOW.to_string(),
        ],
        &mut |line| out.push(line),
    );
    assert_eq!(code, 0);
    assert_eq!(out.len(), 1);
    let event: Value = serde_json::from_str(&out[0]).unwrap();
    assert_eq!(event["kind"], json!("wake"));
    assert_eq!(event["job_id"], json!("7"));
    let state: Value =
        serde_json::from_str(&std::fs::read_to_string(&state_path).unwrap()).unwrap();
    assert_eq!(state["rung"], json!(["wake:7"]));
}

#[test]
fn once_reusing_state_file_is_silent() {
    let (_tmp, jobs_path, agents_path, state_path) = run_once_files(
        &json!([{"id": "7", "status": "open", "addressed_to": "hana"}]),
        &json!({"hana": {"heartbeat_at": null}}),
        Some(&json!({"rung": []})),
    );
    let argv = |jp: &str, ap: &str, sp: &str| {
        vec![
            "--once".to_string(),
            "--jobs-file".to_string(),
            jp.to_string(),
            "--agents-file".to_string(),
            ap.to_string(),
            "--state-file".to_string(),
            sp.to_string(),
            "--now".to_string(),
            NOW.to_string(),
        ]
    };
    let mut out1 = Vec::new();
    let code = watchman::cli(&argv(&jobs_path, &agents_path, &state_path), &mut |l| out1.push(l));
    assert_eq!(code, 0);
    assert_eq!(out1.len(), 1);
    let mut out2 = Vec::new();
    let code = watchman::cli(&argv(&jobs_path, &agents_path, &state_path), &mut |l| out2.push(l));
    assert_eq!(code, 0);
    assert!(out2.is_empty());
}

#[test]
fn once_malformed_input_exits_2_with_no_event() {
    let tmp = tempfile::tempdir().unwrap();
    let jobs_path = tmp.path().join("jobs.json");
    let agents_path = tmp.path().join("agents.json");
    std::fs::write(&jobs_path, "{not json").unwrap();
    std::fs::write(&agents_path, "{}").unwrap();
    let mut out = Vec::new();
    let code = watchman::cli(
        &[
            "--once".to_string(),
            "--jobs-file".to_string(),
            jobs_path.to_string_lossy().into_owned(),
            "--agents-file".to_string(),
            agents_path.to_string_lossy().into_owned(),
            "--now".to_string(),
            NOW.to_string(),
        ],
        &mut |line| out.push(line),
    );
    assert_eq!(code, 2);
    assert!(out.is_empty());
}

#[test]
fn once_missing_files_read_as_empty() {
    let tmp = tempfile::tempdir().unwrap();
    let events = watchman::run_once(
        &tmp.path().join("no-jobs.json").to_string_lossy().into_owned(),
        &tmp.path().join("no-agents.json").to_string_lossy().into_owned(),
        None,
        NOW,
        STALE,
    )
    .unwrap();
    assert!(events.is_empty());
}

fn os_subtree() -> std::path::PathBuf {
    std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("os")
}

#[test]
fn unit_file_shape() {
    let text = std::fs::read_to_string(os_subtree().join("os/services/relay-watchman.service")).unwrap();
    assert!(text.contains("After=relay-jobs.service"));
    assert!(text.contains("PartOf=relay.target"));
    assert!(text.contains("WantedBy=relay.target"));
    assert!(text.contains("ConditionPathExists=/etc/metaos/secrets.env"));
    assert!(text.contains("relay_watchman.py --loop"));
    assert!(text.contains("User=relay"));
    assert!(!text.contains("--dm"));
    assert!(!text.contains("--token"));
    assert!(!text.contains("MUSE_RELAY_TOKEN"));
}

#[test]
fn target_wants_watchman_and_all_routes_enable_it() {
    let target = std::fs::read_to_string(os_subtree().join("os/services/relay.target")).unwrap();
    assert!(target.contains("relay-watchman.service"));
    for path in [
        "os/build-image.sh",
        "os/packer/metaos.pkr.hcl",
        "os/live-build/config/hooks/live/0900-metaos-services.hook.chroot",
    ] {
        let text = std::fs::read_to_string(os_subtree().join(path)).unwrap();
        assert!(text.contains("relay-watchman.service"), "{path}");
    }
}

#[test]
fn readme_carries_os118_section() {
    let readme = std::fs::read_to_string(os_subtree().join("os/README.md")).unwrap();
    assert!(readme.contains("OS-118"));
    assert!(readme.contains("relay_watchman"));
}
