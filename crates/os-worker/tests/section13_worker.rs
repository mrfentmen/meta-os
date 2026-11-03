//! CB2-319/320 — a worker's payload contract and its result order.
//!
//! A job's payload is its `spec` text: a job with an empty spec has nothing to
//! do, so the contract refuses it before any process spawns rather than
//! running an empty step. Results are returned in submission order, so a caller
//! can line them up with the checks it sent.
use std::fs;
use std::path::PathBuf;

use os_worker::{
    run_accept_checks, validate_spec, AcceptCheck, DriverError, JobSpec,
};

fn files(list: &[&str]) -> Vec<String> {
    list.iter().map(|s| s.to_string()).collect()
}

#[test]
fn worker_empty_payload() {
    // Empty spec text is the empty payload: refused by name, before spawn.
    let spec = JobSpec::new("job-1", "A job", "", files(&["out.txt"]), "", Some("sig"));
    match validate_spec(&spec) {
        Err(DriverError::BadSpec(message)) => assert_eq!(
            message,
            "job spec field 'spec' must be a non empty string",
            "an empty payload is named by its field",
        ),
        other => panic!("an empty payload must be refused, got {other:?}"),
    }

    // Whitespace is the same as empty: it is not a payload either.
    let blank = JobSpec::new("job-1", "A job", "   ", files(&["out.txt"]), "", Some("sig"));
    assert!(matches!(validate_spec(&blank), Err(DriverError::BadSpec(_))));

    // The same contract covers the rest of the payload: no id, no title, no
    // files, and no signature are each refused by their own name.
    let no_id = JobSpec::new("", "A job", "do it", files(&["out.txt"]), "", Some("sig"));
    assert!(matches!(validate_spec(&no_id), Err(DriverError::BadSpec(ref m)) if m.contains("'id'")));

    let no_files = JobSpec::new("job-1", "A job", "do it", vec![], "", Some("sig"));
    assert!(matches!(validate_spec(&no_files), Err(DriverError::BadSpec(ref m)) if m.contains("'files'")));

    let unsigned = JobSpec::new("job-1", "A job", "do it", files(&["out.txt"]), "", None);
    assert!(matches!(validate_spec(&unsigned), Err(DriverError::Unsigned(_))));

    // A complete spec still validates, so the refusals above are not a blanket.
    let good = JobSpec::new("job-1", "A job", "do it", files(&["out.txt"]), "", Some("sig"));
    assert!(validate_spec(&good).is_ok());
}

#[test]
fn worker_result_order() {
    let dir: PathBuf = std::env::temp_dir().join(format!("os-worker-order-{}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).expect("temp dir");
    fs::write(dir.join("a.txt"), "first").expect("write a");
    fs::write(dir.join("c.txt"), "third").expect("write c");

    // Submitted a (present), b (missing), c (present).
    let checks: Vec<AcceptCheck> = ["a.txt", "b.txt", "c.txt"]
        .iter()
        .map(|name| AcceptCheck {
            kind: "file-exists".to_string(),
            arg: (*name).to_string(),
        })
        .collect();

    let results = run_accept_checks(&checks, &dir);
    assert_eq!(results.len(), 3, "one result per check");
    assert_eq!(
        results.iter().map(|r| r.check.clone()).collect::<Vec<_>>(),
        vec![
            "file-exists: a.txt".to_string(),
            "file-exists: b.txt".to_string(),
            "file-exists: c.txt".to_string(),
        ],
        "results come back in submission order, not sorted or grouped",
    );
    assert_eq!(
        results.iter().map(|r| r.ok).collect::<Vec<_>>(),
        vec![true, false, true],
        "each result belongs to the check at its index",
    );

    // Reversing the submission reverses the results: the order follows the
    // input, so a caller can zip them.
    let mut reversed = checks.clone();
    reversed.reverse();
    let reversed_results = run_accept_checks(&reversed, &dir);
    assert_eq!(
        reversed_results.iter().map(|r| r.ok).collect::<Vec<_>>(),
        vec![true, false, true],
    );
    assert_eq!(reversed_results[0].check, "file-exists: c.txt");
    assert_eq!(reversed_results[2].check, "file-exists: a.txt");

    let _ = fs::remove_dir_all(&dir);
}
