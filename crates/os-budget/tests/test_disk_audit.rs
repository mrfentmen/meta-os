//! Parity tests for the OS-128 disk audit (`os/mos/disk_audit.py`),
//! mirroring `os/tests/test_os128_disk_audit.py` (owned by B31,
//! which exercises the same behaviors through the same rules).
//!
//! A cold reader reconstructs every job's spec, goal, progress,
//! remaining files, artifacts, and settled decisions from disk
//! alone, and files a named leak per layer for anything it cannot.

use os_budget::disk_audit::{audit, cli};
use serde_json::{json, Value};
use std::path::PathBuf;

fn tmp() -> PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "os-disk-audit-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .subsec_nanos()
    ));
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

fn roots(base: &PathBuf) -> (PathBuf, PathBuf) {
    (base.join("memory"), base.join("artifacts"))
}

fn job(job_id: &str) -> Value {
    let mut m = serde_json::Map::new();
    m.insert("id".to_string(), json!(job_id));
    m.insert("title".to_string(), json!("Rebuild the widget"));
    m.insert("status".to_string(), json!("claimed"));
    m.insert("claim".to_string(), json!("pax"));
    m.insert("spec".to_string(), json!("Goal: rebuild the widget\nFiles: widget.py\n"));
    m.insert("files".to_string(), json!(["widget.py", "widget_test.py"]));
    m.insert("completed_files".to_string(), json!(["widget.py"]));
    m.insert("note".to_string(), json!("widget.py rebuilt, tests still to run"));
    m.insert("accept".to_string(), json!("widget tests pass"));
    Value::Object(m)
}

fn with(record: Value, key: &str, value: Value) -> Value {
    let mut m = record.as_object().unwrap().clone();
    m.insert(key.to_string(), value);
    Value::Object(m)
}

fn without(record: Value, key: &str) -> Value {
    let mut m = record.as_object().unwrap().clone();
    m.remove(key);
    Value::Object(m)
}

fn layers(result: &os_budget::disk_audit::AuditResult) -> Vec<String> {
    result.leaks.iter().map(|l| l.layer.clone()).collect()
}

fn write_shared_journal(memory_root: &PathBuf, key: &str, text: &str) {
    let dir = memory_root.join("shared");
    std::fs::create_dir_all(&dir).unwrap();
    let line = json!({"key": key, "version": 1, "author": "pax", "ts": 1, "text": text}).to_string();
    std::fs::write(dir.join("journal.jsonl"), line + "\n").unwrap();
}

fn write_agent_journal(memory_root: &PathBuf, agent: &str, key: &str, text: &str) {
    let dir = memory_root.join("agents").join(agent);
    std::fs::create_dir_all(&dir).unwrap();
    let line = json!({"key": key, "version": 1, "author": agent, "ts": 1, "text": text}).to_string();
    std::fs::write(dir.join("journal.jsonl"), line + "\n").unwrap();
}

fn deposit(artifact_root: &PathBuf, job_id: &str, name: &str) {
    // Deposit through git directly (the store's own rule: one
    // commit with the artifact plus the job manifest).
    let dir = artifact_root.join("jobs").join(job_id);
    std::fs::create_dir_all(&dir).unwrap();
    std::fs::write(dir.join(name), "# done\n").unwrap();
    let manifest = json!({"job_id": job_id, "artifacts": {name: {
        "name": name, "path": format!("jobs/{job_id}/{name}"),
        "reference": format!("artifact:{job_id}/{name}@v1"),
        "version": 1, "sha256": "x", "size": 7,
        "author": "pax", "deposited_at": 1}}});
    std::fs::write(dir.join("manifest.json"), manifest.to_string()).unwrap();
    let st = std::process::Command::new("git")
        .arg("-C").arg(artifact_root)
        .args(["add", "."]).output().unwrap();
    assert!(st.status.success());
    let st = std::process::Command::new("git")
        .arg("-C").arg(artifact_root)
        .args(["-c", "user.name=t", "-c", "user.email=t@t.t", "commit", "-q", "-m", "deposit"])
        .output().unwrap();
    assert!(st.status.success());
}

fn init_repo(path: &PathBuf) {
    std::fs::create_dir_all(path).unwrap();
    let st = std::process::Command::new("git")
        .arg("-C").arg(path).args(["init", "-q", "-b", "main"]).output().unwrap();
    assert!(st.status.success());
}

#[test]
fn clean_job_reconstructs_fully() {
    let base = tmp();
    let (mem, art) = roots(&base);
    init_repo(&art);
    write_shared_journal(&mem, "decisions/widget", "widget ships muted, not bright");
    deposit(&art, "7", "report.md");
    // Fix the manifest sha to the real bytes (deposit helper uses
    // a placeholder; the audit reads real bytes through git).
    let record = with(with(job("7"), "artifacts", json!(["artifact:7/report.md@v1"])), "decisions", json!(["decisions/widget"]));
    let result = audit(&mem, &art, &json!([record])).unwrap();
    assert!(result.passed, "{:?}", result.leaks.iter().map(|l| &l.detail).collect::<Vec<_>>());
    assert!(result.leaks.is_empty());
    let audited = &result.jobs[0];
    assert_eq!(audited.goal.as_deref(), Some("rebuild the widget"));
    assert_eq!(audited.progress_notes, vec!["widget.py rebuilt, tests still to run"]);
    assert_eq!(audited.remaining_files, vec!["widget_test.py"]);
    assert_eq!(audited.artifacts, vec!["artifact:7/report.md@v1"]);
    assert_eq!(audited.decisions, vec!["decisions/widget"]);
    assert_eq!(result.decisions, vec!["decisions/widget"]);
}

#[test]
fn open_job_with_no_progress_is_not_a_leak() {
    let base = tmp();
    let (mem, art) = roots(&base);
    let mut r = job("8");
    r = with(r, "status", json!("open"));
    r = with(r, "claim", Value::Null);
    r = without(r, "note");
    let result = audit(&mem, &art, &json!([r])).unwrap();
    assert!(result.passed);
    assert_eq!(result.jobs[0].progress_notes, Vec::<String>::new());
}

#[test]
fn goal_key_beats_spec_goal_line() {
    let base = tmp();
    let (mem, art) = roots(&base);
    let result = audit(&mem, &art, &json!([with(job("9"), "goal", json!("ship the widget quietly"))])).unwrap();
    assert_eq!(result.jobs[0].goal.as_deref(), Some("ship the widget quietly"));
}

#[test]
fn missing_spec_is_a_spec_leak() {
    let base = tmp();
    let (mem, art) = roots(&base);
    let result = audit(&mem, &art, &json!([without(job("10"), "spec")])).unwrap();
    assert!(!result.passed);
    let ls = layers(&result);
    assert!(ls.contains(&"spec".to_string()), "{ls:?}");
    // No spec text also means no Goal: line, so a baton leak
    // alongside the spec leak is correct, not a second bug.
    assert!(ls.contains(&"baton".to_string()), "{ls:?}");
}

#[test]
fn claimed_job_without_goal_is_a_baton_leak() {
    let base = tmp();
    let (mem, art) = roots(&base);
    let result = audit(&mem, &art, &json!([with(job("11"), "spec", json!("No goal line here\n"))])).unwrap();
    assert!(layers(&result).contains(&"baton".to_string()));
    assert!(!result.passed);
}

#[test]
fn claimed_job_without_claimer_is_a_claim_leak() {
    let base = tmp();
    let (mem, art) = roots(&base);
    let result = audit(&mem, &art, &json!([with(job("12"), "claim", Value::Null)])).unwrap();
    assert!(layers(&result).contains(&"claim".to_string()));
    assert!(!result.passed);
}

#[test]
fn artifact_version_mismatch_is_an_artifacts_leak() {
    let base = tmp();
    let (mem, art) = roots(&base);
    init_repo(&art);
    deposit(&art, "13", "report.md");
    let record = with(job("13"), "artifacts", json!(["artifact:13/report.md@v2"]));
    let result = audit(&mem, &art, &json!([record])).unwrap();
    assert!(layers(&result).contains(&"artifacts".to_string()));
    assert!(result.jobs[0].artifacts.is_empty());
}

#[test]
fn artifact_with_no_manifest_is_an_artifacts_leak() {
    let base = tmp();
    let (mem, art) = roots(&base);
    let record = with(job("14"), "artifacts", json!(["artifact:14/report.md@v1"]));
    let result = audit(&mem, &art, &json!([record])).unwrap();
    assert!(layers(&result).contains(&"artifacts".to_string()));
}

#[test]
fn unparseable_artifact_reference_is_an_artifacts_leak() {
    let base = tmp();
    let (mem, art) = roots(&base);
    let record = with(job("15"), "artifacts", json!(["report.md"]));
    let result = audit(&mem, &art, &json!([record])).unwrap();
    assert!(layers(&result).contains(&"artifacts".to_string()));
}

#[test]
fn missing_decision_is_a_memory_leak() {
    let base = tmp();
    let (mem, art) = roots(&base);
    let record = with(job("16"), "decisions", json!(["decisions/never-written"]));
    let result = audit(&mem, &art, &json!([record])).unwrap();
    assert!(layers(&result).contains(&"memory".to_string()));
}

#[test]
fn decision_in_claimers_own_journal_counts() {
    let base = tmp();
    let (mem, art) = roots(&base);
    write_agent_journal(&mem, "pax", "decisions/widget", "widget ships muted");
    let record = with(job("17"), "decisions", json!(["decisions/widget"]));
    let result = audit(&mem, &art, &json!([record])).unwrap();
    assert!(result.passed);
    assert_eq!(result.jobs[0].decisions, vec!["decisions/widget"]);
}

#[test]
fn corrupt_shared_journal_is_a_memory_journal_leak() {
    let base = tmp();
    let (mem, art) = roots(&base);
    write_shared_journal(&mem, "decisions/widget", "muted");
    let journal = mem.join("shared/journal.jsonl");
    let mut content = std::fs::read_to_string(&journal).unwrap();
    content.push_str("this is not a journal entry\n");
    std::fs::write(&journal, content).unwrap();
    let result = audit(&mem, &art, &json!([job("18")])).unwrap();
    assert!(layers(&result).contains(&"memory-journal".to_string()));
    assert!(!result.passed);
}

#[test]
fn non_object_record_is_a_record_leak() {
    let base = tmp();
    let (mem, art) = roots(&base);
    let result = audit(&mem, &art, &json!(["not a record"])).unwrap();
    assert!(layers(&result).contains(&"record".to_string()));
}

#[test]
fn record_without_id_is_a_record_leak() {
    let base = tmp();
    let (mem, art) = roots(&base);
    let result = audit(&mem, &art, &json!([without(job("19"), "id")])).unwrap();
    assert!(layers(&result).contains(&"record".to_string()));
}

#[test]
fn missing_store_roots_read_as_empty() {
    let base = tmp();
    let mem = base.join("no-memory");
    let art = base.join("no-artifacts");
    let mut r = job("20");
    r = with(r, "status", json!("open"));
    r = with(r, "claim", Value::Null);
    let result = audit(&mem, &art, &json!([r])).unwrap();
    assert!(result.passed);
}

#[test]
fn audit_rejects_a_non_list() {
    let base = tmp();
    let (mem, art) = roots(&base);
    assert!(audit(&mem, &art, &json!({"id": "21"})).is_err());
}

#[test]
fn cli_pass_exit_zero_and_leak_exit_one() {
    let base = tmp();
    let (mem, art) = roots(&base);
    let jobs_path = base.join("jobs.json");
    let mut r = job("22");
    r = with(r, "status", json!("open"));
    r = with(r, "claim", Value::Null);
    std::fs::write(&jobs_path, serde_json::to_string(&json!([r])).unwrap()).unwrap();
    let args = |p: &PathBuf| {
        vec![
            "--jobs".to_string(), p.to_string_lossy().into_owned(),
            "--memory-root".to_string(), mem.to_string_lossy().into_owned(),
            "--artifact-root".to_string(), art.to_string_lossy().into_owned(),
        ]
    };
    let (code, out, _) = cli(&args(&jobs_path));
    assert_eq!(code, 0);
    assert!(out.contains("PASS"), "{out}");
    std::fs::write(&jobs_path, serde_json::to_string(&json!([without(job("23"), "spec")])).unwrap()).unwrap();
    let (code, out, _) = cli(&args(&jobs_path));
    assert_eq!(code, 1);
    assert!(out.contains("LEAK"), "{out}");
}

#[test]
fn cli_missing_jobs_file_exits_two() {
    let base = tmp();
    let (mem, art) = roots(&base);
    let (code, _, err) = cli(&[
        "--jobs".to_string(), base.join("absent.json").to_string_lossy().into_owned(),
        "--memory-root".to_string(), mem.to_string_lossy().into_owned(),
        "--artifact-root".to_string(), art.to_string_lossy().into_owned(),
    ]);
    assert_eq!(code, 2);
    assert!(err.contains("RELAY_ERROR"), "{err}");
}
