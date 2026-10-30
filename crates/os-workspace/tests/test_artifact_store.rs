//! Parity tests for the OS-083 artifact store behavior
//! (`os/mos/artifact_store.py`).
//!
//! No test file is assigned to B19 in the batch map (parity is
//! behavior-for-behavior against the source); these tests pin the
//! documented rules: versioned deposits, byte-identical no-op
//! redeposits, escaping validation, git-backed version reads and
//! history, non-mutating `attach`, and the CLI shapes. The
//! OS-083 suite (`os/tests/test_os083_artifact_store.py`) is
//! Buffy's B31 territory and exercises the same behaviors
//! through the same rules.

use os_workspace::artifact_store::*;
use serde_json::json;
use std::path::PathBuf;

fn tmp_root(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "os-workspace-{name}-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .subsec_nanos()
    ));
    std::fs::create_dir_all(&dir).unwrap();
    dir.join("store")
}

fn fixed_git_env() {
    // Deterministic commits for history assertions.
    std::env::set_var("GIT_AUTHOR_NAME", "t");
    std::env::set_var("GIT_AUTHOR_EMAIL", "t@t.t");
    std::env::set_var("GIT_COMMITTER_NAME", "t");
    std::env::set_var("GIT_COMMITTER_EMAIL", "t@t.t");
}

#[test]
fn deposit_and_read_round_trip() {
    fixed_git_env();
    let root = tmp_root("roundtrip");
    let rec = deposit(&root, "7", "report.md", b"hello", "milo", 1000).unwrap();
    assert_eq!(rec.version, 1);
    assert!(rec.new_commit);
    assert_eq!(rec.author, "milo");
    assert_eq!(rec.reference, "artifact:7/report.md@v1");
    assert_eq!(rec.path, "jobs/7/report.md");
    assert_eq!(rec.sha256.len(), 64);
    assert_eq!(read(&root, "7", "report.md", None).unwrap(), b"hello");
}

#[test]
fn versions_increment_and_versioned_read() {
    fixed_git_env();
    let root = tmp_root("versions");
    deposit(&root, "7", "r.md", b"v1", "", 1).unwrap();
    let rec = deposit(&root, "7", "r.md", b"v2", "", 2).unwrap();
    assert_eq!(rec.version, 2);
    assert_eq!(read(&root, "7", "r.md", None).unwrap(), b"v2");
    assert_eq!(read(&root, "7", "r.md", Some(1)).unwrap(), b"v1");
    assert_eq!(read(&root, "7", "r.md", Some(2)).unwrap(), b"v2");
    let hist = history(&root, "7", "r.md").unwrap();
    assert_eq!(hist.len(), 2);
    assert_eq!(hist[0].0, 1);
    assert_eq!(hist[1].0, 2);
    assert!(hist[0].1.len() == 40 && hist[1].1.len() == 40);
}

#[test]
fn identical_redeposit_is_a_noop() {
    fixed_git_env();
    let root = tmp_root("noop");
    let first = deposit(&root, "7", "r.md", b"same", "milo", 1).unwrap();
    let again = deposit(&root, "7", "r.md", b"same", "milo", 2).unwrap();
    assert_eq!(again.version, 1);
    assert!(!again.new_commit);
    assert_eq!(again.sha256, first.sha256);
    // No new commit: one version only.
    assert_eq!(history(&root, "7", "r.md").unwrap().len(), 1);
}

#[test]
fn names_and_job_ids_validated() {
    fixed_git_env();
    let root = tmp_root("validate");
    for bad_name in ["/abs", "a//b", "a/./b", "a/../b", "a\\b", ""] {
        assert!(deposit(&root, "7", bad_name, b"x", "", 1).is_err(), "{bad_name:?}");
    }
    for bad_job in ["a/b", ".", "..", "", "a\\b"] {
        assert!(deposit(&root, bad_job, "r.md", b"x", "", 1).is_err(), "{bad_job:?}");
    }
}

#[test]
fn missing_artifact_and_bad_version_raise() {
    fixed_git_env();
    let root = tmp_root("missing");
    deposit(&root, "7", "r.md", b"v1", "", 1).unwrap();
    assert!(read(&root, "7", "nope.md", None).is_err());
    assert!(read(&root, "7", "r.md", Some(2)).is_err());
    assert!(read(&root, "7", "r.md", Some(0)).is_err());
    assert!(read(&root, "unknown", "r.md", None).is_err());
}

#[test]
fn list_sorted_and_empty_job_reads_empty() {
    fixed_git_env();
    let root = tmp_root("list");
    deposit(&root, "7", "b.md", b"b", "", 1).unwrap();
    deposit(&root, "7", "a.md", b"a", "", 2).unwrap();
    let items = list_artifacts(&root, "7").unwrap();
    assert_eq!(items.iter().map(|i| i.name.clone()).collect::<Vec<_>>(), vec!["a.md", "b.md"]);
    // Reading a job with no manifest returns an empty list, not an error.
    assert!(list_artifacts(&root, "empty-job").unwrap().is_empty());
}

#[test]
fn attach_returns_copy_with_paths_never_mutates() {
    fixed_git_env();
    let root = tmp_root("attach");
    deposit(&root, "7", "r.md", b"data", "milo", 1).unwrap();
    let record = json!({"id": "7", "title": "T", "artifacts": [{"path": "old"}]});
    let before = record.clone();
    let out = attach(&root, "7", &record).unwrap();
    // Input untouched.
    assert_eq!(record, before);
    let arts = out["artifacts"].as_array().unwrap();
    assert_eq!(arts.len(), 2);
    assert_eq!(arts[0]["path"], json!("old"));
    assert_eq!(arts[1]["reference"], json!("artifact:7/r.md@v1"));
    assert_eq!(arts[1]["path"], json!("jobs/7/r.md"));
    assert_eq!(arts[1]["version"], json!(1));
    assert!(arts[1]["sha256"].as_str().unwrap().len() == 64);
}

#[test]
fn cli_deposit_list_read_show() {
    fixed_git_env();
    let root = tmp_root("cli");
    let root_s = root.to_string_lossy().into_owned();
    let src = std::env::temp_dir().join("os-workspace-cli-src.txt");
    std::fs::write(&src, b"payload").unwrap();
    let (code, out, err) = cli(&[
        "deposit".to_string(),
        root_s.clone(),
        "7".to_string(),
        "r.md".to_string(),
        src.to_string_lossy().into_owned(),
        "--author".to_string(),
        "milo".to_string(),
    ]);
    assert_eq!(code, 0, "{err}");
    let rec: serde_json::Value = serde_json::from_slice(&out).unwrap();
    assert_eq!(rec["version"], json!(1));
    let (code, out, err) = cli(&["list".to_string(), root_s.clone(), "7".to_string()]);
    assert_eq!(code, 0, "{err}");
    assert!(String::from_utf8_lossy(&out).contains("artifact:7/r.md@v1"));
    let (code, out, err) = cli(&[
        "read".to_string(),
        root_s.clone(),
        "7".to_string(),
        "r.md".to_string(),
    ]);
    assert_eq!(code, 0, "{err}");
    assert_eq!(out, b"payload");
    let (code, out, err) =
        cli(&["show".to_string(), root_s, "7".to_string(), "r.md".to_string()]);
    assert_eq!(code, 0, "{err}");
    assert!(String::from_utf8_lossy(&out).starts_with("v1 "));
    std::fs::remove_file(&src).ok();
}

#[test]
fn cli_refusals_exit_2() {
    let root = tmp_root("cli-err");
    let root_s = root.to_string_lossy().into_owned();
    let (code, _, err) = cli(&[
        "read".to_string(),
        root_s,
        "7".to_string(),
        "../escape.md".to_string(),
    ]);
    assert_eq!(code, 2);
    assert!(err.contains("ARTIFACT_STORE_ERROR"), "{err}");
    let (code, _, err) = cli(&[]);
    assert_eq!(code, 2);
    assert!(err.contains("usage"), "{err}");
}
