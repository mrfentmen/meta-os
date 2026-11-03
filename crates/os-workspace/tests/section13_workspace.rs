//! CB2-321..323: the artifact store's path and listing edges.
//!
//! These pin behaviour the crate already promises in its docs: a name or job
//! id cannot climb out of the store with `..`, a written entry reads back
//! byte-identical at latest and at its version, and an empty store lists zero
//! entries rather than failing.

use os_workspace::{deposit, list_artifacts, read_artifact};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};

static COUNTER: AtomicUsize = AtomicUsize::new(0);

struct TmpDir(PathBuf);

impl TmpDir {
    fn new(tag: &str) -> TmpDir {
        let n = COUNTER.fetch_add(1, Ordering::SeqCst);
        let p = std::env::temp_dir().join(format!(
            "os-workspace-section13-{}-{}-{}",
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

#[test]
fn workspace_path_traversal_refused() {
    let d = TmpDir::new("traversal");

    let err = deposit(d.path(), "job-1", "../escape.txt", b"x", "").unwrap_err();
    assert!(
        err.0.contains(".."),
        "the refusal must name the bad segment, got: {}",
        err.0
    );

    let err = deposit(d.path(), "job-1", "/etc/passwd", b"x", "").unwrap_err();
    assert_eq!(err.0, "artifact name must be a relative POSIX path");

    // A job id is one path segment too: `..` is not a job.
    let err = deposit(d.path(), "..", "f.txt", b"x", "").unwrap_err();
    assert_eq!(err.0, "job id must be a single path segment");

    // Refused before the store was created: nothing was written anywhere.
    assert!(
        !d.path().join("jobs").exists(),
        "a refused deposit must not create a job directory"
    );
}

#[test]
fn workspace_entry_roundtrip() {
    let d = TmpDir::new("roundtrip");
    let payload = b"line one\nline two\n";

    let out = deposit(
        d.path(),
        "job-1",
        "notes/report.txt",
        payload,
        "bond",
    )
    .unwrap();
    assert_eq!(out.record.size, payload.len());
    assert_eq!(out.record.version, 1);
    assert_eq!(out.record.author, "bond");
    assert_eq!(out.record.path, "jobs/job-1/notes/report.txt");
    assert!(out.new_commit);

    assert_eq!(
        read_artifact(d.path(), "job-1", "notes/report.txt", None).unwrap(),
        payload,
        "latest read must be byte-identical"
    );
    assert_eq!(
        read_artifact(d.path(), "job-1", "notes/report.txt", Some(1)).unwrap(),
        payload,
        "the versioned read must be byte-identical too"
    );

    let listed = list_artifacts(d.path(), "job-1").unwrap();
    assert_eq!(listed.len(), 1);
    assert_eq!(listed[0].name, "notes/report.txt");
    assert_eq!(listed[0].sha256, out.record.sha256);
    assert_eq!(listed[0].size, payload.len());
}

#[test]
fn workspace_list_empty() {
    let d = TmpDir::new("list-empty");

    let listed = list_artifacts(d.path(), "no-such-job").unwrap();
    assert_eq!(listed.len(), 0, "an empty store lists zero entries");

    // A job that exists but holds no artifacts is empty too, not an error.
    fs::create_dir_all(d.path().join("jobs").join("job-empty")).unwrap();
    let listed = list_artifacts(d.path(), "job-empty").unwrap();
    assert_eq!(listed.len(), 0);
}
