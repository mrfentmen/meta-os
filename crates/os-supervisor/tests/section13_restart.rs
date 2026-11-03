//! CB2-316/317/318 — the restart policy's three rules.
//!
//! The policy is arithmetic on a counter, so these tests assert exact numbers
//! with no sleeping and no clock.
use os_supervisor::restart::{
    RestartPolicy, WorkerHealth, WorkerState, BACKOFF_SEQUENCE_SECS, DEFAULT_MAX_FAILURES,
};

#[test]
fn supervisor_three_strikes() {
    let policy = RestartPolicy::default();
    assert_eq!(policy.max_failures(), 3, "three strikes is the documented default");
    let mut worker = WorkerHealth::new();

    // Two failures: still restartable, with a delay each time.
    assert_eq!(worker.record_failure(&policy), 1);
    assert_eq!(worker.state(), WorkerState::Restarting);
    assert!(worker.should_restart());

    assert_eq!(worker.record_failure(&policy), 2);
    assert_eq!(worker.failures(), 2);
    assert!(worker.should_restart(), "two strikes is not three");

    // The third failure marks it failed and restarts it never again.
    assert_eq!(worker.record_failure(&policy), 0, "no delay for a restart that will not happen");
    assert_eq!(worker.state(), WorkerState::Failed);
    assert!(!worker.should_restart());
    assert_eq!(worker.failures(), 3);
    assert_eq!(
        DEFAULT_MAX_FAILURES, 3,
        "the constant and the default policy agree",
    );
}

#[test]
fn supervisor_three_strikes_is_sticky() {
    let policy = RestartPolicy::default();
    let mut worker = WorkerHealth::new();
    for _ in 0..3 {
        worker.record_failure(&policy);
    }
    // A fourth failure changes nothing: the count does not climb past the
    // limit and the state does not drift back to restartable.
    assert_eq!(worker.record_failure(&policy), 0);
    assert_eq!(worker.failures(), 3);
    assert_eq!(worker.state(), WorkerState::Failed);
    assert!(!worker.should_restart());
}

#[test]
fn supervisor_three_strikes_respects_an_explicit_limit() {
    let policy = RestartPolicy::new(1).expect("a limit of one is allowed");
    let mut worker = WorkerHealth::new();
    assert_eq!(worker.record_failure(&policy), 0, "the first failure is the limit");
    assert_eq!(worker.state(), WorkerState::Failed);
    assert_eq!(
        RestartPolicy::new(0).unwrap_err().0,
        "restart policy: max_failures must be at least 1",
        "a policy that restarts nothing is refused by name",
    );
}

#[test]
fn supervisor_backoff_sequence() {
    let policy = RestartPolicy::default();
    assert_eq!(BACKOFF_SEQUENCE_SECS, &[1, 2, 4, 8, 16, 32, 60]);
    assert_eq!(policy.backoff_secs(0), 0, "nothing has failed yet");

    // One-based attempts walk the table in order.
    let walked: Vec<u64> = (1..=BACKOFF_SEQUENCE_SECS.len() as u32)
        .map(|attempt| policy.backoff_secs(attempt))
        .collect();
    assert_eq!(walked, BACKOFF_SEQUENCE_SECS.to_vec());

    // Past the table it holds at the ceiling; it never grows without bound.
    assert_eq!(policy.backoff_secs(8), 60);
    assert_eq!(policy.backoff_secs(100), 60);
}

#[test]
fn supervisor_backoff_matches_the_failures_it_follows() {
    let policy = RestartPolicy::new(10).expect("ten strikes");
    let mut worker = WorkerHealth::new();
    let delays: Vec<u64> = (0..5).map(|_| worker.record_failure(&policy)).collect();
    assert_eq!(delays, vec![1, 2, 4, 8, 16], "each failure waits the next delay");
    assert_eq!(worker.state(), WorkerState::Restarting);
}

#[test]
fn supervisor_recovery_resets() {
    let policy = RestartPolicy::default();
    let mut worker = WorkerHealth::new();
    worker.record_failure(&policy);
    worker.record_failure(&policy);
    assert_eq!(worker.failures(), 2);

    worker.record_recovery();
    assert_eq!(worker.failures(), 0, "a healthy run clears the history");
    assert_eq!(worker.state(), WorkerState::Running);
    assert!(worker.should_restart());

    // The first failure after recovery starts the sequence again, not where
    // the worker left off.
    assert_eq!(worker.record_failure(&policy), 1);
    assert_eq!(worker.failures(), 1);
}

#[test]
fn supervisor_recovery_revives_a_failed_worker() {
    let policy = RestartPolicy::default();
    let mut worker = WorkerHealth::new();
    for _ in 0..3 {
        worker.record_failure(&policy);
    }
    assert_eq!(worker.state(), WorkerState::Failed);
    // Only a recorded recovery clears it: an operator-observed run is the one
    // thing that may bring a failed worker back.
    worker.record_recovery();
    assert_eq!(worker.state(), WorkerState::Running);
    assert!(worker.should_restart());
}
