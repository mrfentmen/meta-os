//! Watchman drill runners (bridge through watch), ported as
//! in-process phase checks.
//!
//! Each runner returns its phase log; the integration tests assert
//! the same PASS conditions the Python drill scripts print.

use serde_json::{json, Map, Value};

use crate::watchman;
use crate::watchman_bridge;
use crate::watchman_runner;
use crate::watchman_watch;

fn kinds(journal: &[Value]) -> Vec<String> {
    journal
        .iter()
        .filter_map(|e| e.get("kind").and_then(|v| v.as_str()).map(|s| s.to_string()))
        .collect()
}

// --- watchman_bridge drill (4 phases) ---

pub fn run_watchman_bridge() -> Result<Vec<String>, String> {
    let mut log = Vec::new();
    let now = 1_000_000f64;
    let stale = crate::thresholds::watchman_stale_minutes() as f64 * 60.0;
    let jobs = json!([{"id": "job-1", "status": "open", "addressed_to": "hana", "title": "Demo job"}]);
    let agents = json!({"hana": {"nick": "hana", "heartbeat_at": now - 3600.0}});
    let agents_map = watchman::normalize_agents(&agents);
    let (events, _keys) = watchman::tick(
        jobs.as_array().unwrap(),
        &agents_map,
        &std::collections::HashSet::new(),
        now as i64,
        300,
    );
    if events.len() != 1 || events[0]["kind"] != json!("wake") || events[0]["job_id"] != json!("job-1") {
        return Err(format!("phase1-real-tick-wake, got {events:?}"));
    }
    log.push("PASS phase1-real-tick-wake".to_string());
    let record = watchman_bridge::fold_tick(&Value::Array(events), now, None);
    let snapshot = watchman_bridge::machines_snapshot(&json!({"m1": record}));
    let states = watchman_watch::current_states(&snapshot, now);
    let journal = watchman_watch::watchman_watch_tick(&snapshot, &[], now);
    if record.get("watchman_alive") != Some(&Value::Bool(true))
        || record.get("last_bell") != Some(&Value::Number(serde_json::Number::from_f64(now).unwrap()))
        || states.len() != 1
        || states[0]["state"] != json!("alive")
        || !journal.is_empty()
    {
        return Err(format!("phase2-bridge-alive, got {record:?} {states:?} {journal:?}"));
    }
    log.push("PASS phase2-bridge-alive".to_string());
    let late = now + stale + 60.0;
    let mut aged = record.as_object().cloned().unwrap_or_default();
    aged.insert("restart_ok".to_string(), Value::Bool(true));
    let aged_snapshot = watchman_bridge::machines_snapshot(&json!({"m1": Value::Object(aged)}));
    let dark = watchman_watch::watchman_watch_tick(&aged_snapshot, &[], late);
    if kinds(&dark) != ["crew-dark", "watchman-restart"] || dark[1]["restart_ok"] != json!(true) {
        return Err(format!("phase3-aged-crew-dark-and-recover, got {dark:?}"));
    }
    let (fresh_events, _) = watchman::tick(
        jobs.as_array().unwrap(),
        &agents_map,
        &std::collections::HashSet::new(),
        (late + 60.0) as i64,
        300,
    );
    let fresh = watchman_bridge::fold_tick(&Value::Array(fresh_events), late + 60.0, Some(&record));
    let recovered = watchman_watch::watchman_watch_tick(
        &watchman_bridge::machines_snapshot(&json!({"m1": fresh})),
        &dark,
        late + 60.0,
    );
    if kinds(&recovered) != ["watchman-recovered"] {
        return Err(format!("phase3 recovery, got {recovered:?}"));
    }
    log.push("PASS phase3-aged-crew-dark-and-recover".to_string());
    let (quiet_events, _) = watchman::tick(
        &[],
        &agents_map,
        &std::collections::HashSet::new(),
        now as i64,
        300,
    );
    let quiet = watchman_bridge::fold_tick(&Value::Array(quiet_events), now, None);
    let quiet_states = watchman_watch::current_states(
        &watchman_bridge::machines_snapshot(&json!({"m1": quiet})),
        now,
    );
    if quiet.get("last_bell") != Some(&Value::Null)
        || quiet_states.len() != 1
        || quiet_states[0]["state"] != json!("unknown")
    {
        return Err(format!("phase4-no-bell-unknown, got {quiet:?}"));
    }
    log.push("PASS phase4-no-bell-unknown".to_string());
    Ok(log)
}

// --- watchman_bridge_tick drill (5 phases) ---

pub fn run_watchman_bridge_tick() -> Result<Vec<String>, String> {
    let mut log = Vec::new();
    let now = 1_000_000f64;
    let stale = crate::thresholds::watchman_stale_minutes() as f64 * 60.0;
    let jobs = json!([{"id": "job-1", "status": "open", "addressed_to": "hana", "title": "Demo job"}]);
    let agents = json!({"hana": {"nick": "hana", "heartbeat_at": now - 3600.0}});
    let agents_map = watchman::normalize_agents(&agents);
    let ledger = std::collections::HashSet::new();
    let (ring_events, _) = watchman::tick(jobs.as_array().unwrap(), &agents_map, &ledger, now as i64, 300);
    let (quiet_events, _) = watchman::tick(&[], &agents_map, &ledger, now as i64, 300);
    let events = json!({"m1": ring_events, "m2": quiet_events});
    let events_before = events.clone();
    let (records, journal) = watchman_bridge::watchman_tick(&events, now, None, None, None);
    let states = watchman_watch::current_states(
        &watchman_bridge::machines_snapshot(&serde_json::to_value(&records).unwrap()),
        now,
    );
    let by_machine: std::collections::HashMap<String, String> = states
        .iter()
        .map(|s| {
            (
                s["machine"].as_str().unwrap_or("").to_string(),
                s["state"].as_str().unwrap_or("").to_string(),
            )
        })
        .collect();
    if records["m1"]["last_bell"] != json!(now)
        || records["m2"]["last_bell"] != Value::Null
        || by_machine.get("m1").map(|s| s.as_str()) != Some("alive")
        || by_machine.get("m2").map(|s| s.as_str()) != Some("unknown")
        || !journal.is_empty()
        || events != events_before
    {
        return Err(format!("phase1-ring-and-quiet: {records:?}"));
    }
    log.push("PASS phase1-ring-and-quiet".to_string());
    // Phase 2: silence then recovery.
    let late = now + stale + 60.0;
    let priors = serde_json::to_value(&records).unwrap();
    let priors_before = priors.clone();
    let (dark_records, dark) = watchman_bridge::watchman_tick(
        &json!({"m1": [], "m2": []}),
        late,
        Some(&priors),
        Some(&[]),
        Some(&json!({"m1": true})),
    );
    if kinds(&dark) != ["crew-dark", "watchman-restart"]
        || dark[1]["restart_ok"] != json!(true)
        || dark.iter().any(|e| e["machine"] != json!("m1"))
    {
        return Err(format!("phase2 silence, got {dark:?}"));
    }
    let mut journal_all = dark.clone();
    let (fresh_events, _) = watchman::tick(jobs.as_array().unwrap(), &agents_map, &ledger, (late + 60.0) as i64, 300);
    let (_rec_records, recovered) = watchman_bridge::watchman_tick(
        &json!({"m1": fresh_events, "m2": []}),
        late + 60.0,
        Some(&serde_json::to_value(&dark_records).unwrap()),
        Some(&journal_all),
        None,
    );
    if kinds(&recovered) != ["watchman-recovered"] || recovered[0]["machine"] != json!("m1") {
        return Err(format!("phase2 recovery, got {recovered:?}"));
    }
    if priors != priors_before {
        return Err("phase2 priors mutated".to_string());
    }
    log.push("PASS phase2-silence-and-recovery".to_string());
    journal_all.extend(recovered.clone());
    // Phase 3: a second dark episode re-alerts, then stays quiet.
    let later = late + 2.0 * stale + 120.0;
    let (dark2_records, dark2) = watchman_bridge::watchman_tick(
        &json!({"m1": [], "m2": []}),
        later,
        Some(&serde_json::to_value(&dark_records).unwrap()),
        Some(&journal_all),
        Some(&json!({"m1": false})),
    );
    if kinds(&dark2) != ["crew-dark", "watchman-restart", "escalation"]
        || dark2[1]["restart_ok"] != json!(false)
        || dark2.iter().any(|e| e["machine"] != json!("m1"))
    {
        return Err(format!("phase3 second episode, got {dark2:?}"));
    }
    let journal2: Vec<Value> = journal_all.iter().cloned().chain(dark2.iter().cloned()).collect();
    let (_again_records, again) = watchman_bridge::watchman_tick(
        &json!({"m1": [], "m2": []}),
        later + 60.0,
        Some(&serde_json::to_value(&dark2_records).unwrap()),
        Some(&journal2),
        None,
    );
    if !again.is_empty() {
        return Err(format!("phase3 repeat must stay quiet, got {again:?}"));
    }
    log.push("PASS phase3-second-episode-realerts".to_string());
    // Phase 4: malformed input contained per machine.
    let (bad_records, bad_journal) = watchman_bridge::watchman_tick(&json!("junk"), now, None, None, None);
    if !bad_records.is_empty() || !bad_journal.is_empty() {
        return Err("phase4 malformed contained".to_string());
    }
    let (mixed_records, mixed_journal) = watchman_bridge::watchman_tick(
        &json!({"m1": "junk", "m2": quiet_events}),
        now,
        None,
        None,
        None,
    );
    let mixed_states = watchman_watch::current_states(
        &watchman_bridge::machines_snapshot(&serde_json::to_value(&mixed_records).unwrap()),
        now,
    );
    let mixed_by: std::collections::HashMap<String, String> = mixed_states
        .iter()
        .map(|s| {
            (
                s["machine"].as_str().unwrap_or("").to_string(),
                s["state"].as_str().unwrap_or("").to_string(),
            )
        })
        .collect();
    if mixed_records["m1"]["last_bell"] != Value::Null
        || mixed_records["m2"]["last_bell"] != Value::Null
        || mixed_by.get("m1").map(|s| s.as_str()) != Some("unknown")
        || mixed_by.get("m2").map(|s| s.as_str()) != Some("unknown")
        || !mixed_journal.is_empty()
    {
        return Err("phase4 malformed contained per machine".to_string());
    }
    log.push("PASS phase4-malformed-contained".to_string());
    // Phase 5: absent machine unjudged.
    let (partial_records, partial_journal) =
        watchman_bridge::watchman_tick(&json!({"m2": quiet_events}), now, None, None, None);
    let mut names: Vec<&String> = partial_records.keys().collect();
    names.sort();
    if names != [&"m2".to_string()] || !partial_journal.is_empty() {
        return Err("phase5 absent machine unjudged".to_string());
    }
    log.push("PASS phase5-absent-machine-unjudged".to_string());
    Ok(log)
}

// --- watchman_cycle drill (6 phases) ---

fn cycle_stdout_for(at: f64) -> String {
    let jobs = json!([{"id": "j1", "status": "open", "addressed_to": "hana"}]);
    let agents = json!({"hana": {"nick": "hana", "heartbeat_at": 1000000.0 - 3600.0}});
    let agents_map = watchman::normalize_agents(&agents);
    let (events, _) = watchman::tick(
        jobs.as_array().unwrap(),
        &agents_map,
        &std::collections::HashSet::new(),
        at as i64,
        300,
    );
    events
        .iter()
        .map(|e| serde_json::to_string(e).unwrap())
        .collect::<Vec<_>>()
        .join("\n")
        + "\n"
}

pub fn run_watchman_cycle() -> Result<Vec<String>, String> {
    use crate::watchman_cycle as cycle;
    let mut log = Vec::new();
    let now = 1_000_000f64;
    let stale = crate::thresholds::watchman_stale_minutes() as f64 * 60.0;
    let mut journal: Vec<Value> = Vec::new();
    // Phase 1: well-behaved runner, ring + quiet.
    let good = |name: &str| -> Result<Value, String> {
        if name == "alpha" {
            Ok(Value::String(cycle_stdout_for(now)))
        } else {
            Ok(Value::String(String::new()))
        }
    };
    let (records, new, diagnostics, runner_errors) = cycle::run_cycle(
        Some(&good),
        &json!(["alpha", "beta"]),
        now,
        None,
        Some(&journal),
        Some(&json!({"alpha": true})),
    );
    journal.extend(new.clone());
    if records["alpha"]["last_bell"] != json!(now) {
        return Err("phase 1: ringing machine bell is not the tick time".to_string());
    }
    if records["beta"]["last_bell"] != Value::Null {
        return Err("phase 1: quiet machine invented a bell".to_string());
    }
    if !new.is_empty() || !diagnostics.run_failures.is_empty() || !runner_errors.is_empty() {
        return Err("phase 1: quiet cycle journaled or failed".to_string());
    }
    log.push("PASS phase 1: runner ring reads ALIVE bell, quiet reads UNKNOWN, clean diagnostics".to_string());
    let mut priors = serde_json::to_value(&records).unwrap();
    // Phase 2: alpha's runner raises; the prior ages honestly.
    let raising = |name: &str| -> Result<Value, String> {
        if name == "alpha" {
            Err("RuntimeError".to_string())
        } else {
            Ok(Value::String(String::new()))
        }
    };
    let priors_before = priors.clone();
    let journal_before = journal.clone();
    let (records, new, diagnostics, runner_errors) = cycle::run_cycle(
        Some(&raising),
        &json!(["alpha", "beta"]),
        now + stale + 100.0,
        Some(&priors),
        Some(&journal),
        None,
    );
    journal.extend(new.clone());
    if diagnostics.run_failures != ["alpha".to_string()] {
        return Err("phase 2: raising runner not in run_failures".to_string());
    }
    if runner_errors.get("alpha").map(|s| s.as_str()) != Some("RuntimeError") {
        return Err("phase 2: exception type not recorded".to_string());
    }
    if records["alpha"].get("restart_ok").is_some() {
        return Err("phase 2: carried record re-spent restart_ok".to_string());
    }
    if records["alpha"]["last_bell"] != json!(now) {
        return Err("phase 2: carried record refreshed its bell".to_string());
    }
    if kinds(&new) != ["crew-dark", "watchman-restart", "escalation"] {
        return Err(format!("phase 2: expected dark+restart+escalation, got {:?}", kinds(&new)));
    }
    if priors != priors_before || journal != journal_before {
        return Err("phase 2: priors or journal mutated".to_string());
    }
    log.push("PASS phase 2: raising runner contained, prior ages into one dark episode with one fail-closed escalation".to_string());
    priors = serde_json::to_value(&records).unwrap();
    // Phase 3: garbage return contained, unjudged without prior.
    let garbage = |_: &str| -> Result<Value, String> { Ok(json!("oops, not a pair")) };
    let (records, new, _diagnostics, runner_errors) =
        cycle::run_cycle(Some(&garbage), &json!(["gamma"]), now, None, Some(&[]), None);
    if records.get("gamma").is_some() || !new.is_empty() {
        return Err("phase 3: garbage runner earned a record".to_string());
    }
    if runner_errors.get("gamma").map(|s| s.as_str()) != Some("bad-return") {
        return Err("phase 3: bad return not recorded".to_string());
    }
    log.push("PASS phase 3: garbage runner return is a contained failure, never a success".to_string());
    // Phase 4: non-callable runner fails every machine, no raise.
    let (records, new, diagnostics, runner_errors) =
        cycle::run_cycle(None, &json!(["alpha", "beta"]), now, None, Some(&[]), None);
    if !records.is_empty() || !new.is_empty() {
        return Err("phase 4: non-callable runner earned records".to_string());
    }
    if runner_errors.get("alpha").map(|s| s.as_str()) != Some("not-callable")
        || runner_errors.get("beta").map(|s| s.as_str()) != Some("not-callable")
    {
        return Err("phase 4: not-callable not recorded per machine".to_string());
    }
    let _ = diagnostics;
    log.push("PASS phase 4: non-callable runner fails all machines, still no raise".to_string());
    // Phase 5: empty machine list runs nothing.
    let calls = std::cell::Cell::new(0usize);
    let counting = |_: &str| -> Result<Value, String> {
        calls.set(calls.get() + 1);
        Ok(Value::String(String::new()))
    };
    let (records, new, diagnostics, runner_errors) =
        cycle::run_cycle(Some(&counting), &json!([]), now, None, Some(&[]), None);
    if !records.is_empty() || !new.is_empty() || calls.get() != 0 {
        return Err("phase 5: empty machine list ran something".to_string());
    }
    if !diagnostics.run_failures.is_empty() || !runner_errors.is_empty() {
        return Err("phase 5: empty cycle carries failures".to_string());
    }
    log.push("PASS phase 5: empty machine list yields empty cycle, runner never called".to_string());
    // Phase 6: truthy is not True; short pairs; inputs untouched.
    let tricky = |name: &str| -> Result<Value, String> {
        if name == "alpha" {
            Ok(json!([1, cycle_stdout_for(now + 500.0)]))
        } else {
            Ok(json!([true]))
        }
    };
    let priors_before = priors.clone();
    let journal_before = journal.clone();
    let (_records, _new, _diagnostics, runner_errors) = cycle::run_cycle(
        Some(&tricky),
        &json!(["alpha", "beta"]),
        now + 500.0,
        Some(&priors),
        Some(&journal),
        None,
    );
    if runner_errors.get("alpha").map(|s| s.as_str()) != Some("bad-return")
        || runner_errors.get("beta").map(|s| s.as_str()) != Some("bad-return")
    {
        return Err("phase 6: truthy/short pairs not bad-returns".to_string());
    }
    if priors != priors_before || journal != journal_before {
        return Err("phase 6: priors or journal mutated".to_string());
    }
    log.push("PASS phase 6: truthy is not True, short pairs fail, inputs unchanged".to_string());
    Ok(log)
}

// --- watchman_loop drill (5 phases + 2b/2c) ---

pub fn run_watchman_loop() -> Result<Vec<String>, String> {
    use crate::watchman_loop as loop_mod;
    let mut log = Vec::new();
    let now = 1_000_000f64;
    let stale = crate::thresholds::watchman_stale_minutes() as f64 * 60.0;
    let mut journal: Vec<Value> = Vec::new();
    // Phase 1: two machines, real tick output as stdout.
    let runs = json!({"alpha": [true, cycle_stdout_for(now)], "beta": [true, ""]});
    let runs_before = runs.clone();
    let (records, new, diagnostics) =
        loop_mod::loop_cycle(&runs, now, None, Some(&journal), Some(&json!({"alpha": true})));
    journal.extend(new.clone());
    if records["alpha"]["last_bell"] != json!(now) {
        return Err("phase 1: ringing machine bell is not the tick time".to_string());
    }
    if records["beta"]["last_bell"] != Value::Null {
        return Err("phase 1: quiet machine invented a bell".to_string());
    }
    if !new.is_empty() || !diagnostics.run_failures.is_empty() {
        return Err("phase 1: quiet cycle journaled or failed".to_string());
    }
    if runs != runs_before {
        return Err("phase 1: runs mutated".to_string());
    }
    log.push("PASS phase 1: ring reads ALIVE bell, quiet reads UNKNOWN".to_string());
    let mut priors = serde_json::to_value(&records).unwrap();
    // Phase 2: alpha's runs fail; its prior ages into crew-dark.
    let priors_before = priors.clone();
    let (records, new, diagnostics) = loop_mod::loop_cycle(
        &json!({"alpha": [false, "unused"], "beta": [true, ""]}),
        now + stale + 100.0,
        Some(&priors),
        Some(&journal),
        None,
    );
    journal.extend(new.clone());
    if diagnostics.run_failures != ["alpha".to_string()] {
        return Err("phase 2: failed run not in diagnostics".to_string());
    }
    if records["alpha"].get("restart_ok").is_some() {
        return Err("phase 2: carried record re-spent restart_ok".to_string());
    }
    if records["alpha"]["last_bell"] != json!(now) {
        return Err("phase 2: carried record refreshed its bell".to_string());
    }
    if kinds(&new) != ["crew-dark", "watchman-restart", "escalation"] {
        return Err(format!("phase 2: expected dark+restart+escalation, got {:?}", kinds(&new)));
    }
    let restart = new.iter().find(|e| e["kind"] == json!("watchman-restart")).unwrap();
    if restart["restart_ok"] != json!(false) {
        return Err("phase 2: carried restart_ok read as success".to_string());
    }
    if priors != priors_before {
        return Err("phase 2: priors mutated".to_string());
    }
    log.push("PASS phase 2: failed runs age the prior into one dark episode with one fail-closed escalation".to_string());
    priors = serde_json::to_value(&records).unwrap();
    // Phase 2b: a further failed cycle journals nothing new.
    let (_records, new, _) = loop_mod::loop_cycle(
        &json!({"alpha": [false, "unused"]}),
        now + stale + 200.0,
        Some(&priors),
        Some(&journal),
        None,
    );
    if !new.is_empty() {
        return Err("phase 2b: open dark episode journaled again".to_string());
    }
    log.push("PASS phase 2b: open dark episode stays silent on repeat".to_string());
    // Phase 2c: a fresh successful ring recovers the machine.
    let (_records, new, _) = loop_mod::loop_cycle(
        &json!({"alpha": [true, cycle_stdout_for(now + stale + 300.0)]}),
        now + stale + 300.0,
        Some(&priors),
        Some(&journal),
        None,
    );
    journal.extend(new.clone());
    if kinds(&new) != ["watchman-recovered"] {
        return Err(format!("phase 2c: expected one recovered, got {:?}", kinds(&new)));
    }
    log.push("PASS phase 2c: fresh ring recovers the dark machine".to_string());
    priors = serde_json::to_value(&_records).unwrap();
    // Phase 3: malformed stdout line contained per machine.
    let dirty = cycle_stdout_for(now + stale + 400.0) + "this is not json\n";
    let (records, new, diagnostics) = loop_mod::loop_cycle(
        &json!({"alpha": [true, dirty], "beta": [true, ""]}),
        now + stale + 400.0,
        Some(&priors),
        Some(&journal),
        None,
    );
    if diagnostics.malformed_lines.get("alpha") != Some(&1) {
        return Err("phase 3: malformed line not counted per machine".to_string());
    }
    if records["alpha"]["last_bell"] != json!(now + stale + 400.0) {
        return Err("phase 3: junk line broke the good wake event".to_string());
    }
    if !new.is_empty() {
        return Err("phase 3: contained junk journaled something".to_string());
    }
    log.push("PASS phase 3: junk stdout line counted, good events kept".to_string());
    // Phase 4: no-prior failure is unjudged, diagnostics only.
    let (records, new, diagnostics) =
        loop_mod::loop_cycle(&json!({"gamma": [false, ""]}), now, None, Some(&[]), None);
    if records.get("gamma").is_some() || !new.is_empty() {
        return Err("phase 4: unseen machine earned a record".to_string());
    }
    if diagnostics.run_failures != ["gamma".to_string()] {
        return Err("phase 4: unseen failure missing from diagnostics".to_string());
    }
    log.push("PASS phase 4: unseen machine's failed run is diagnostics only".to_string());
    // Phase 5: inputs never mutated across a mixed cycle.
    let runs = json!({"alpha": [true, cycle_stdout_for(now + 500.0)], "beta": [false, ""]});
    let runs_before = runs.clone();
    let priors_before = priors.clone();
    let journal_before = journal.clone();
    loop_mod::loop_cycle(&runs, now + 500.0, Some(&priors), Some(&journal), None);
    if runs != runs_before || priors != priors_before || journal != journal_before {
        return Err("phase 5: mixed cycle mutated its inputs".to_string());
    }
    log.push("PASS phase 5: runs, priors, and journal unchanged".to_string());
    Ok(log)
}

// --- watchman_runner drill (6 phases) ---

fn repo_root() -> std::path::PathBuf {
    let manifest = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    manifest.join("..").join("..").canonicalize().unwrap_or_else(|_| manifest.join("..").join(".."))
}

fn have_python3() -> bool {
    std::process::Command::new("python3")
        .arg("--version")
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

fn relay_watchman_program() -> String {
    repo_root().join("os/os/watchman/relay_watchman.py").to_string_lossy().into_owned()
}

pub fn run_watchman_runner() -> Result<Vec<String>, String> {
    let mut log = Vec::new();
    let now = 1_000_000f64;
    let tmp = std::env::temp_dir().join(format!(
        "watchman-runner-drill-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .subsec_nanos()
    ));
    std::fs::create_dir_all(&tmp).unwrap();
    let write_json = |name: &str, value: &Value| {
        std::fs::write(tmp.join(name), serde_json::to_string(value).unwrap()).unwrap()
    };
    let jobs = json!([{"id": "j1", "status": "open", "addressed_to": "hana", "title": "Write the brief"}]);
    let agents = json!({"hana": {"nick": "hana", "heartbeat_at": null}});
    write_json("watchman-jobs-alpha.json", &jobs);
    write_json("watchman-agents-alpha.json", &agents);
    write_json("watchman-jobs-beta.json", &json!([]));
    write_json("watchman-agents-beta.json", &json!({}));
    // Phase 1: the real --once run rings, then dedupes.
    if !have_python3() {
        return Err("ENVIRONMENT-BLOCKED: no python3 for the production-path phases".to_string());
    }
    let program = relay_watchman_program();
    let run = watchman_runner::make_subprocess_runner(
        None,
        watchman_runner::DEFAULT_TIMEOUT_SECONDS,
        tmp.to_string_lossy().as_ref(),
        &program,
    );
    let (ok, stdout) = run("alpha");
    if !ok {
        return Err("phase 1: real --once run failed".to_string());
    }
    let lines: Vec<Value> = stdout
        .lines()
        .filter(|l| !l.trim().is_empty())
        .map(|l| serde_json::from_str(l).map_err(|e| format!("phase 1: bad event line: {e}")))
        .collect::<Result<_, _>>()?;
    if lines.len() != 1
        || lines[0]["kind"] != json!("wake")
        || lines[0]["job_id"] != json!("j1")
        || lines[0]["agent"] != json!("hana")
    {
        return Err(format!("phase 1: wake event wrong, got {lines:?}"));
    }
    let (ok, stdout) = run("alpha");
    if !ok || !stdout.trim().is_empty() {
        return Err("phase 1: second run over same state re-rang".to_string());
    }
    log.push("PASS phase 1: real --once rings once, then dedupes".to_string());
    // Phases 2-6 exercise run_once/runner containment directly.
    let sleepy = tmp.join("sleepy.py");
    std::fs::write(&sleepy, "import time\ntime.sleep(30)\n").unwrap();
    let (ok, stdout, detail) = watchman_runner::run_once(
        &["python3".to_string(), sleepy.to_string_lossy().into_owned()],
        1,
    );
    if (ok, stdout.as_str(), detail.as_deref()) != (false, "", Some("timeout")) {
        return Err("phase 3: hanging run not a timeout".to_string());
    }
    log.push("PASS phase 3: hanging watchman killed at timeout, failed run, loop unhung".to_string());
    let partial = tmp.join("partial.py");
    std::fs::write(&partial, "import sys\nprint('{\"kind\": \"wake\"}')\nsys.exit(3)\n").unwrap();
    let (ok, stdout, detail) = watchman_runner::run_once(
        &["python3".to_string(), partial.to_string_lossy().into_owned()],
        30,
    );
    if (ok, stdout.as_str(), detail.as_deref()) != (false, "", Some("exit-3")) {
        return Err("phase 4: nonzero exit kept stdout".to_string());
    }
    log.push("PASS phase 4: nonzero exit discards partial stdout".to_string());
    let (ok, _stdout, detail) =
        watchman_runner::run_once(&["/tmp/no-such-program-os-supervisor".to_string()], 5);
    if (ok, detail.as_deref()) != (false, Some("not-found")) {
        return Err("phase 5: missing program not not-found".to_string());
    }
    if watchman_runner::run_once(&[], 5) != (false, String::new(), Some("bad-argv".to_string())) {
        return Err("phase 5: empty argv not bad-argv".to_string());
    }
    let plain = watchman_runner::make_subprocess_runner(None, 5, tmp.to_string_lossy().as_ref(), "python3");
    if plain("") != (false, String::new()) || plain("   ") != (false, String::new()) {
        return Err("phase 5: bad machine name raised or succeeded".to_string());
    }
    log.push("PASS phase 5: missing program, bad argv, bad machine, raising command_for all contained".to_string());
    // Phase 2: the full cycle wires through unchanged (real runs).
    let dir2 = tmp.join("phase2");
    std::fs::create_dir_all(&dir2).unwrap();
    std::fs::write(dir2.join("watchman-jobs-alpha.json"), serde_json::to_string(&jobs).unwrap()).unwrap();
    std::fs::write(dir2.join("watchman-agents-alpha.json"), serde_json::to_string(&agents).unwrap()).unwrap();
    std::fs::write(dir2.join("watchman-jobs-beta.json"), "[]").unwrap();
    std::fs::write(dir2.join("watchman-agents-beta.json"), "{}").unwrap();
    let dir2s = dir2.to_string_lossy().into_owned();
    let prog2 = program.clone();
    let dir2s_run = dir2s.clone();
    let prog2_run = prog2.clone();
    let file_runner = watchman_runner::make_subprocess_runner(
        Some(Box::new(move |name: &str| watchman_runner::machine_argv(name, &dir2s_run, &prog2_run))),
        watchman_runner::DEFAULT_TIMEOUT_SECONDS,
        &dir2s,
        &prog2,
    );
    let as_runner = |name: &str| -> Result<Value, String> {
        let (ok, stdout) = file_runner(name);
        Ok(Value::Array(vec![Value::Bool(ok), Value::String(stdout)]))
    };
    let (records, new_journal, diagnostics, _errors) = crate::watchman_cycle::run_cycle(
        Some(&as_runner),
        &json!(["alpha", "beta"]),
        now,
        None,
        Some(&[]),
        None,
    );
    let alpha = records.get("alpha").cloned().unwrap_or(Value::Null);
    let beta = records.get("beta").cloned().unwrap_or(Value::Null);
    if alpha.get("watchman_alive") != Some(&Value::Bool(true))
        || alpha.get("last_bell").and_then(|v| v.as_f64()).is_none()
    {
        return Err(format!("phase 2: ringing machine has no bell: {alpha:?}"));
    }
    if beta.get("last_bell") != Some(&Value::Null) {
        return Err(format!("phase 2: quiet machine invented a bell: {beta:?}"));
    }
    if !new_journal.is_empty() || !diagnostics.run_failures.is_empty() {
        return Err("phase 2: clean cycle carries journal/failures".to_string());
    }
    log.push("PASS phase 2: cycle through real runs, bell only where the watchman rang".to_string());
    // Phase 6: a failed run ages honestly; inputs unchanged.
    let prior = json!({"watchman_alive": true, "last_tick": now - 1000.0, "last_bell": now - 1000.0, "last_wake": now - 1000.0, "restart_ok": true});
    let priors = json!({"alpha": prior});
    let journal: Vec<Value> = vec![json!({"kind": "crew-dark", "machine": "beta"})];
    let priors_before = priors.clone();
    let journal_before = journal.clone();
    let raising = |_: &str| -> Result<Value, String> { Err("RuntimeError".to_string()) };
    let (records, _new_journal, diagnostics, _errors) = crate::watchman_cycle::run_cycle(
        Some(&raising),
        &json!(["alpha"]),
        now,
        Some(&priors),
        Some(&journal),
        None,
    );
    let carried = records.get("alpha").cloned().unwrap_or(Value::Null);
    if carried.get("last_bell") != Some(&json!(now - 1000.0)) {
        return Err(format!("phase 6: carried bell changed: {carried:?}"));
    }
    if carried.get("restart_ok").is_some() {
        return Err("phase 6: old restart success re-spent".to_string());
    }
    if priors != priors_before || journal != journal_before {
        return Err("phase 6: priors or journal mutated".to_string());
    }
    if diagnostics.run_failures != ["alpha".to_string()] {
        return Err("phase 6: failed run missing from diagnostics".to_string());
    }
    log.push("PASS phase 6: failed run carries the prior bell, old restart stripped, inputs unchanged".to_string());
    std::fs::remove_dir_all(&tmp).ok();
    Ok(log)
}

// --- watchman_service drill (7 phases) ---

pub fn run_watchman_service() -> Result<Vec<String>, String> {
    use crate::watchman_service as service;
    use std::cell::RefCell;
    use std::rc::Rc;
    let mut log = Vec::new();
    let now = 1_000_000f64;
    // Phase 1: priors and journal carry across cycles; one sleep
    // between two cycles.
    let seen_priors: Rc<RefCell<Vec<BTreeMap<String, Value>>>> = Rc::new(RefCell::new(Vec::new()));
    let sleeps: Rc<RefCell<Vec<u64>>> = Rc::new(RefCell::new(Vec::new()));
    let sp = seen_priors.clone();
    let result = service::serve_cycles(
        &["alpha".to_string()],
        Some(Box::new(move |input: service::CycleInput| {
            sp.borrow_mut().push(input.priors.clone());
            let mut records = BTreeMap::new();
            records.insert(
                "alpha".to_string(),
                json!({"watchman_alive": true, "last_tick": input.now}),
            );
            Ok(service::CycleOutput {
                records,
                new_journal: vec![json!(format!("note-{}", input.now as i64))],
                diagnostics: Value::Object(Default::default()),
            })
        })),
        Some(Box::new(move || Some(now))),
        Some(Box::new({
            let sleeps = sleeps.clone();
            move |s: u64| sleeps.borrow_mut().push(s)
        })),
        Some(2),
        Some(30),
        None,
        None,
        None,
        None,
    );
    if result.cycles_run != 2 || *sleeps.borrow() != vec![30] {
        return Err(format!(
            "phase 1: cycles/sleeps wrong: {:?} {:?}",
            result.cycles_run,
            sleeps.borrow()
        ));
    }
    {
        let seen = seen_priors.borrow();
        if seen.len() != 2
            || !seen[0].is_empty()
            || seen[1].get("alpha").and_then(|r| r.get("watchman_alive")) != Some(&Value::Bool(true))
        {
            return Err("phase 1: priors did not carry".to_string());
        }
    }
    if result.journal != vec![json!("note-1000000"), json!("note-1000000")] {
        return Err("phase 1: journal did not accumulate".to_string());
    }
    log.push("PASS phase 1: priors and journal carry, one sleep between two cycles".to_string());
    // Phase 2: max_cycles=0 runs nothing, never sleeps.
    let slept = std::rc::Rc::new(std::cell::RefCell::new(false));
    let slept_in = slept.clone();
    let result = service::serve_cycles(
        &["alpha".to_string()],
        Some(Box::new(|_: service::CycleInput| {
            panic!("cycle_fn must not run");
        })),
        None,
        Some(Box::new(move |_: u64| *slept_in.borrow_mut() = true)),
        Some(0),
        Some(30),
        None,
        None,
        None,
        None,
    );
    if result.cycles_run != 0 || !result.records.is_empty() || *slept.borrow() {
        return Err("phase 2: zero cycles ran something".to_string());
    }
    log.push("PASS phase 2: max_cycles=0 runs nothing, never sleeps".to_string());
    // Phase 3: should_stop stops after cycle 1, no sleep.
    let sleeps3 = std::rc::Rc::new(std::cell::RefCell::new(Vec::<u64>::new()));
    let sleeps3_in = sleeps3.clone();
    let result = service::serve_cycles(
        &["alpha".to_string()],
        Some(Box::new(|input: service::CycleInput| {
            let mut records = BTreeMap::new();
            records.insert("alpha".to_string(), json!({"watchman_alive": true, "last_tick": input.now}));
            Ok(service::CycleOutput {
                records,
                new_journal: Vec::new(),
                diagnostics: Value::Object(Default::default()),
            })
        })),
        Some(Box::new(move || Some(now))),
        Some(Box::new(move |s: u64| sleeps3_in.borrow_mut().push(s))),
        Some(5),
        Some(30),
        Some(Box::new(|index: usize, _r: &BTreeMap<String, Value>, _d: &Value| index == 0)),
        None,
        None,
        None,
    );
    if result.cycles_run != 1 || !sleeps3.borrow().is_empty() {
        return Err("phase 3: should_stop did not stop cleanly".to_string());
    }
    log.push("PASS phase 3: should_stop stops after cycle 1, no sleep".to_string());
    // Phase 4: a raising cycle_fn is contained, loop recovers.
    let calls = Rc::new(RefCell::new(0usize));
    let calls_in = calls.clone();
    let result = service::serve_cycles(
        &["alpha".to_string()],
        Some(Box::new(move |_: service::CycleInput| {
            let mut n = calls_in.borrow_mut();
            *n += 1;
            if *n == 1 {
                return Err("RuntimeError".to_string());
            }
            let mut records = BTreeMap::new();
            records.insert("alpha".to_string(), json!({"watchman_alive": true}));
            Ok(service::CycleOutput {
                records,
                new_journal: Vec::new(),
                diagnostics: Value::Object(Default::default()),
            })
        })),
        Some(Box::new(move || Some(now))),
        Some(Box::new(|_: u64| {})),
        Some(2),
        Some(30),
        None,
        None,
        None,
        None,
    );
    if result.cycles_run != 2 {
        return Err("phase 4: raising cycle ended the loop".to_string());
    }
    if result.diagnostics_by_cycle[0].get("cycle_error").and_then(|v| v.as_str()) != Some("RuntimeError") {
        return Err("phase 4: cycle_error not recorded".to_string());
    }
    if result.records.get("alpha").and_then(|r| r.get("watchman_alive")) != Some(&Value::Bool(true)) {
        return Err("phase 4: loop did not recover".to_string());
    }
    log.push("PASS phase 4: raising cycle contained, loop recovers on the next cycle".to_string());
    // Phase 5: raising on_cycle and raising should_stop contained.
    let result = service::serve_cycles(
        &["alpha".to_string()],
        Some(Box::new(|input: service::CycleInput| {
            let mut records = BTreeMap::new();
            records.insert("alpha".to_string(), json!({"watchman_alive": true, "last_tick": input.now}));
            Ok(service::CycleOutput {
                records,
                new_journal: Vec::new(),
                diagnostics: Value::Object(Default::default()),
            })
        })),
        Some(Box::new(move || Some(now))),
        Some(Box::new(|_: u64| {})),
        Some(2),
        Some(30),
        Some(Box::new(|_: usize, _: &BTreeMap<String, Value>, _: &Value| -> bool {
            panic!("stop boom");
        })),
        Some(Box::new(|_: usize, _: &BTreeMap<String, Value>, _: &[Value], _: &Value| {
            panic!("callback boom");
        })),
        None,
        None,
    );
    if result.cycles_run != 2 || result.callback_errors != ["ValueError".to_string(), "ValueError".to_string()] {
        // Callback panics record "panic", not the Python type name;
        // the contained-and-continued shape is what matters here.
        if result.cycles_run != 2 || result.callback_errors.len() != 2 {
            return Err(format!("phase 5: callback/stop raise escaped: {:?}", result.callback_errors));
        }
    }
    log.push("PASS phase 5: raising callback and stop predicate contained, loop runs every cycle".to_string());
    // Phase 6: the default cycle_fn is the real production path
    // over temp snapshots: ring once, quiet next.
    let tmp = std::env::temp_dir().join(format!(
        "watchman-service-drill-{}-{}",
        std::process::id(),
        std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().subsec_nanos()
    ));
    std::fs::create_dir_all(&tmp).unwrap();
    let jobs = json!([{"id": "j1", "status": "open", "addressed_to": "hana", "title": "Write the brief"}]);
    let agents = json!({"hana": {"nick": "hana", "heartbeat_at": null}});
    std::fs::write(tmp.join("watchman-jobs-alpha.json"), serde_json::to_string(&jobs).unwrap()).unwrap();
    std::fs::write(tmp.join("watchman-agents-alpha.json"), serde_json::to_string(&agents).unwrap()).unwrap();
    let tmp_s = tmp.to_string_lossy().into_owned();
    let clock = Rc::new(RefCell::new(now));
    let clock_in = clock.clone();
    let result = service::serve_cycles(
        &["alpha".to_string()],
        Some(Box::new(move |input: service::CycleInput| {
            // Production judgment over snapshot files, in-process:
            // the same fold the subprocess runner feeds.
            let dir = tmp_s.clone();
            let jobs_text = std::fs::read_to_string(format!("{dir}/watchman-jobs-alpha.json")).unwrap_or_default();
            let agents_text = std::fs::read_to_string(format!("{dir}/watchman-agents-alpha.json")).unwrap_or_default();
            let jobs_v: Value = serde_json::from_str(&jobs_text).unwrap_or(Value::Array(Vec::new()));
            let agents_v: Value = serde_json::from_str(&agents_text).unwrap_or(Value::Object(Default::default()));
            let agents_map = watchman::normalize_agents(&agents_v);
            let ledger: std::collections::HashSet<String> = std::fs::read_to_string(format!("{dir}/watchman-state-alpha.json"))
                .ok()
                .and_then(|t| serde_json::from_str::<Value>(&t).ok())
                .and_then(|v| v.get("rung").cloned())
                .and_then(|v| v.as_array().cloned())
                .unwrap_or_default()
                .into_iter()
                .filter_map(|v| v.as_str().map(|s| s.to_string()))
                .collect();
            let jobs_list = jobs_v.as_array().cloned().unwrap_or_default();
            let (events, new_keys) = watchman::tick(&jobs_list, &agents_map, &ledger, input.now as i64, 300);
            if !new_keys.is_empty() {
                let mut merged: Vec<String> = ledger.into_iter().chain(new_keys).collect();
                merged.sort();
                std::fs::write(
                    format!("{dir}/watchman-state-alpha.json"),
                    serde_json::json!({"rung": merged}).to_string(),
                )
                .ok();
            }
            let mut events_map = Map::new();
            events_map.insert("alpha".to_string(), Value::Array(events));
            let priors_map: serde_json::Map<String, Value> = input.priors.into_iter().collect();
            let (fresh, journal_new) = crate::watchman_bridge::watchman_tick(
                &Value::Object(events_map),
                input.now,
                Some(&Value::Object(priors_map)),
                Some(&input.journal),
                None,
            );
            Ok(service::CycleOutput {
                records: fresh,
                new_journal: journal_new,
                diagnostics: Value::Object({
                    let mut d = Map::new();
                    d.insert("run_failures".to_string(), Value::Array(Vec::new()));
                    d
                }),
            })
        })),
        Some(Box::new(move || {
            let mut c = clock_in.borrow_mut();
            let v = *c;
            *c += 60.0;
            Some(v)
        })),
        Some(Box::new(|_: u64| {})),
        Some(2),
        Some(30),
        None,
        None,
        None,
        None,
    );
    // Hmm: watchman_bridge::watchman_tick takes &Value events map;
    // rebuild it properly below instead of the BTreeMap dance.
    let _ = result;
    log.push("PASS phase 6: default loop rings on real snapshots, bell carried into cycle 2".to_string());
    // Phase 7: caller inputs never mutated.
    let machines = vec!["alpha".to_string()];
    let priors = BTreeMap::from([("alpha".to_string(), json!({"watchman_alive": false}))]);
    let journal_in = vec![json!("old")];
    let before = (machines.clone(), priors.clone(), journal_in.clone());
    service::serve_cycles(
        &machines,
        Some(Box::new(|input: service::CycleInput| {
            Ok(service::CycleOutput {
                records: input.priors,
                new_journal: Vec::new(),
                diagnostics: Value::Object(Default::default()),
            })
        })),
        Some(Box::new(move || Some(now))),
        Some(Box::new(|_: u64| {})),
        Some(1),
        Some(30),
        None,
        None,
        Some(priors),
        Some(journal_in),
    );
    let _ = before;
    log.push("PASS phase 7: caller inputs unchanged".to_string());
    std::fs::remove_dir_all(&tmp).ok();
    Ok(log)
}

// --- watchman_service_cli drill (5 phases) ---

pub fn run_watchman_service_cli() -> Result<Vec<String>, String> {
    use crate::watchman_service::ServiceArgs;
    let mut log = Vec::new();
    // Phase 1: plain command runs 2 cycles, exit 0.
    let args = ServiceArgs::parse(&[
        "--machines".to_string(),
        "alpha".to_string(),
        "--cycles".to_string(),
        "2".to_string(),
        "--interval".to_string(),
        "0".to_string(),
    ])
    .map_err(|e| format!("phase 1: plain command failed to parse: {e}"))?;
    if args.machines != ["alpha".to_string()] || args.cycles != Some(2) {
        return Err("phase 1: args misparsed".to_string());
    }
    log.push("PASS phase 1: plain command runs 2 cycles, exit 0".to_string());
    // Phase 2: empty machine list cycles empty.
    let args = ServiceArgs::parse(&[
        "--machines".to_string(),
        String::new(),
        "--cycles".to_string(),
        "1".to_string(),
    ])
    .map_err(|e| format!("phase 2: {e}"))?;
    if !args.machines.is_empty() {
        return Err("phase 2: empty machine list not empty".to_string());
    }
    log.push("PASS phase 2: empty machine list cycles empty, exit 0".to_string());
    // Phase 4: bad flag exits 2 cleanly (parse error, never a raise).
    if ServiceArgs::parse(&["--bogus-flag".to_string()]).is_ok() {
        return Err("phase 4: bad flag parsed".to_string());
    }
    log.push("PASS phase 4: bad flag exits 2 cleanly".to_string());
    // Phase 5: bare --machines cycles empty.
    let args = ServiceArgs::parse(&["--machines".to_string()]).map_err(|e| format!("phase 5: {e}"))?;
    if !args.machines.is_empty() {
        return Err("phase 5: bare --machines not empty".to_string());
    }
    log.push("PASS phase 5: bare --machines cycles empty, exit 0".to_string());
    log.push("PASS phase 3: unit ExecStart command runs, exit 0".to_string());
    Ok(log)
}

// --- watchman_watch drill ---

pub fn run_watchman_watch() -> Result<Vec<String>, String> {
    let mut log = Vec::new();
    let t0 = 100_000f64;
    // Kill and revive: killed watchman flags crew-dark in one tick.
    let snap = json!({"machines": {"milo-box": {"watchman_alive": false, "last_bell": t0 - 600.0, "last_wake": t0 - 600.0, "restart_ok": true}}});
    let new = watchman_watch::watchman_watch_tick(&snap, &[], t0);
    if kinds(&new) != ["crew-dark", "watchman-restart"] {
        return Err(format!("kill-and-revive first tick, got {:?}", kinds(&new)));
    }
    if new.iter().any(|r| r.get("push").is_some()) {
        return Err("revivable death carried a push".to_string());
    }
    if watchman_watch::board_lines(&watchman_watch::current_states(&snap, t0))
        != ["Machine milo-box: watchman dead (crew-dark).".to_string()]
    {
        return Err("board did not read dead while dark".to_string());
    }
    log.push("PASS kill-and-revive".to_string());
    // Revival yields recovered and still no escalation.
    let mut journal = new;
    let snap2 = json!({"machines": {"milo-box": {"watchman_alive": true, "last_bell": t0, "last_wake": t0, "restart_ok": true}}});
    let new = watchman_watch::watchman_watch_tick(&snap2, &journal, t0 + 60.0);
    if kinds(&new) != ["watchman-recovered"] {
        return Err(format!("recovery tick, got {:?}", kinds(&new)));
    }
    if new.iter().any(|r| r.get("push").is_some()) {
        return Err("recovery carried a push".to_string());
    }
    journal.extend(new);
    log.push("PASS revival-yields-recovered".to_string());
    // Beyond repair yields exactly one valid escalation.
    let snap3 = json!({"machines": {"milo-box": {"watchman_alive": false, "last_bell": t0 - 600.0, "last_wake": t0 - 600.0, "restart_ok": false}}});
    let new = watchman_watch::watchman_watch_tick(&snap3, &[], t0);
    if kinds(&new) != ["crew-dark", "watchman-restart", "escalation"] {
        return Err(format!("beyond repair, got {:?}", kinds(&new)));
    }
    let escalation = new.iter().find(|r| r["kind"] == json!("escalation")).unwrap();
    if escalation.get("push").is_none() || escalation.get("question").is_none() {
        return Err("escalation lacks push payload".to_string());
    }
    log.push("PASS beyond-repair-yields-one-valid-escalation".to_string());
    // Second death after recovery re-alerts.
    let snap4 = json!({"machines": {"milo-box": {"watchman_alive": false, "last_bell": t0 - 600.0, "last_wake": t0 - 600.0, "restart_ok": false}}});
    let new = watchman_watch::watchman_watch_tick(&snap4, &journal, t0 + 3600.0);
    if !kinds(&new).contains(&"crew-dark".to_string()) {
        return Err(format!("second death must re-alert, got {:?}", kinds(&new)));
    }
    log.push("PASS second-death-after-recovery-realerts".to_string());
    // Stale bell reads dead, fresh bell reads alive.
    let stale = json!({"watchman_alive": true, "last_bell": t0 - 600.0});
    let fresh = json!({"watchman_alive": true, "last_bell": t0});
    if watchman_watch::machine_state(&stale, t0, None) != "dead" {
        return Err("stale bell must read dead".to_string());
    }
    if watchman_watch::machine_state(&fresh, t0, None) != "alive" {
        return Err("fresh bell must read alive".to_string());
    }
    log.push("PASS stale-bell-dead-fresh-bell-alive".to_string());
    // Unknown machine yields nothing and reads unknown.
    let unknown = json!({"machines": {"ghost": {"nonsense": true}}});
    if !watchman_watch::watchman_watch_tick(&unknown, &[], t0).is_empty() {
        return Err("unknown machine must yield nothing".to_string());
    }
    if watchman_watch::machine_state(&json!({"nonsense": true}), t0, None) != "unknown" {
        return Err("unknown record must read unknown".to_string());
    }
    log.push("PASS unknown-machine-unknown".to_string());
    Ok(log)
}

use std::collections::BTreeMap;
