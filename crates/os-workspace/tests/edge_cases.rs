//! Edge cases for `os-workspace`: empty input, maximum input, duplicate
//! input, and out-of-order input. Each test is named for the case it pins.

use os_workspace::{
    attach, deposit, history, read_artifact, JsonValue,
};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};

static COUNTER: AtomicUsize = AtomicUsize::new(0);

struct TmpDir(PathBuf);

impl TmpDir {
    fn new(tag: &str) -> TmpDir {
        let n = COUNTER.fetch_add(1, Ordering::SeqCst);
        let p = std::env::temp_dir().join(format!(
            "os-workspace-edge-{}-{}-{}",
            std::process::id(),
            tag,
            n
        ));
        let _ = fs::remove_dir_all(&p);
        fs::create_dir_all(&p).expect("create temp dir");
        TmpDir(p)
    }

    fn path(&self) -> &Path {
        &self.0
    }
}

impl Drop for TmpDir {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

// -- empty input ----------------------------------------------------------

#[test]
fn empty_input_deposits_a_zero_byte_artifact() {
    let d = TmpDir::new("empty-bytes");
    let out = deposit(d.path(), "j", "empty.bin", b"", "").unwrap();
    assert_eq!(out.record.version, 1);
    assert_eq!(out.record.size, 0);
    assert_eq!(
        out.record.sha256,
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    );
    assert_eq!(
        read_artifact(d.path(), "j", "empty.bin", None).unwrap(),
        Vec::<u8>::new()
    );
}

#[test]
fn empty_record_attaches_an_empty_artifact_list() {
    let d = TmpDir::new("empty-record");
    let out = attach(d.path(), "j", &JsonValue::obj(vec![])).unwrap();
    assert_eq!(
        out.get("artifacts")
            .and_then(|a| a.as_array())
            .map(|a| a.len()),
        Some(0)
    );
}

// -- maximum input --------------------------------------------------------

#[test]
fn maximum_input_one_mebibyte_round_trips() {
    let d = TmpDir::new("max-bytes");
    let blob: Vec<u8> = (0..1_048_576).map(|i| (i % 251) as u8).collect();
    deposit(d.path(), "j", "big.bin", &blob, "").unwrap();
    assert_eq!(
        read_artifact(d.path(), "j", "big.bin", None).unwrap(),
        blob,
        "latest read must return every byte"
    );
    assert_eq!(
        read_artifact(d.path(), "j", "big.bin", Some(1)).unwrap(),
        blob,
        "versioned read must return every byte"
    );
}

#[test]
fn maximum_name_depth_and_long_job_id_round_trip() {
    let d = TmpDir::new("max-name");
    let name = format!("{}leaf.txt", "a/".repeat(20));
    let job_id = "a".repeat(180);
    deposit(d.path(), &job_id, &name, b"deep", "").unwrap();
    assert_eq!(
        read_artifact(d.path(), &job_id, &name, None).unwrap(),
        b"deep"
    );
}

// -- duplicate input ------------------------------------------------------

#[test]
fn duplicate_identical_deposit_is_one_version() {
    let d = TmpDir::new("dupe-deposit");
    let first = deposit(d.path(), "j", "f.txt", b"same", "").unwrap();
    let second = deposit(d.path(), "j", "f.txt", b"same", "other").unwrap();
    assert_eq!(second.record.version, 1);
    assert!(!second.new_commit);
    assert_eq!(second.record.author, first.record.author);
    assert_eq!(history(d.path(), "j", "f.txt").unwrap().len(), 1);
}

#[test]
fn duplicate_attach_entries_are_appended_not_deduped() {
    let d = TmpDir::new("dupe-attach");
    deposit(d.path(), "j", "f.txt", b"x", "").unwrap();
    let existing = JsonValue::Array(vec![JsonValue::obj(vec![(
        "path",
        JsonValue::Str("jobs/j/f.txt".to_string()),
    )])]);
    let record = JsonValue::obj(vec![("artifacts", existing)]);
    let out = attach(d.path(), "j", &record).unwrap();
    let arts = out.get("artifacts").and_then(|a| a.as_array()).unwrap();
    assert_eq!(
        arts.len(),
        2,
        "attach preserves the caller's entries and appends the store's"
    );
}

// -- out-of-order input ---------------------------------------------------

#[test]
fn out_of_order_version_reads_return_the_right_bytes() {
    let d = TmpDir::new("versions");
    deposit(d.path(), "j", "f.txt", b"one", "").unwrap();
    deposit(d.path(), "j", "f.txt", b"two", "").unwrap();
    deposit(d.path(), "j", "f.txt", b"three", "").unwrap();
    assert_eq!(
        read_artifact(d.path(), "j", "f.txt", Some(3)).unwrap(),
        b"three"
    );
    assert_eq!(
        read_artifact(d.path(), "j", "f.txt", Some(1)).unwrap(),
        b"one"
    );
    assert_eq!(
        read_artifact(d.path(), "j", "f.txt", Some(2)).unwrap(),
        b"two"
    );
    let h = history(d.path(), "j", "f.txt").unwrap();
    assert_eq!(
        h.iter().map(|e| e.version).collect::<Vec<_>>(),
        vec![1, 2, 3],
        "history is oldest first even when versions were read out of order"
    );
}

#[test]
fn out_of_order_attach_keeps_existing_order_then_appends_store_order() {
    let d = TmpDir::new("attach-order");
    deposit(d.path(), "j", "b.txt", b"b", "").unwrap();
    deposit(d.path(), "j", "a.txt", b"a", "").unwrap();
    let existing = JsonValue::Array(vec![
        JsonValue::obj(vec![("path", JsonValue::Str("old-2".to_string()))]),
        JsonValue::obj(vec![("path", JsonValue::Str("old-1".to_string()))]),
    ]);
    let record = JsonValue::obj(vec![("artifacts", existing)]);
    let out = attach(d.path(), "j", &record).unwrap();
    let paths: Vec<&str> = out
        .get("artifacts")
        .and_then(|a| a.as_array())
        .unwrap()
        .iter()
        .map(|e| e.get("path").and_then(|p| p.as_str()).unwrap())
        .collect();
    assert_eq!(
        paths,
        vec!["old-2", "old-1", "jobs/j/a.txt", "jobs/j/b.txt"]
    );
}

#[test]
fn non_array_artifacts_field_is_treated_as_absent() {
    let d = TmpDir::new("attach-non-array");
    deposit(d.path(), "j", "f.txt", b"x", "").unwrap();
    let record = JsonValue::obj(vec![(
        "artifacts",
        JsonValue::Str("not a list".to_string()),
    )]);
    let out = attach(d.path(), "j", &record).unwrap();
    let arts = out.get("artifacts").and_then(|a| a.as_array()).unwrap();
    assert_eq!(arts.len(), 1);
}
