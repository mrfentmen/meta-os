//! CB2-308/309/310 — a job's steps.
//!
//! A job that runs nothing reports success while doing nothing, so it is
//! refused at construction. Step order survives a serialise round-trip, and a
//! cancel says what actually happened instead of claiming every cancel worked.
use os_jobs::job::{CancelOutcome, Job, JobError, JobState, Step};

fn step(name: &str, command: &[&str]) -> Step {
    Step::new(name, command).expect("valid step")
}

fn three_step_job() -> Job {
    Job::new(
        "job-7",
        "Build the wall",
        vec![
            step("site", &["sh", "-c", "echo site"]),
            step("raise", &["sh", "-c", "echo raise"]),
            step("cap", &["sh", "-c", "echo cap"]),
        ],
    )
    .expect("three steps is a job")
}

#[test]
fn job_no_steps_refused() {
    assert_eq!(
        Job::new("job-1", "Nothing", vec![]).unwrap_err(),
        JobError::NoSteps,
        "a job with no steps is refused, not run as a no-op",
    );

    // The other construction refusals are named too.
    assert_eq!(
        Step::new("  ", &["sh"]).unwrap_err(),
        JobError::BlankStepName,
    );
    assert_eq!(
        Step::new("build", &[]).unwrap_err(),
        JobError::EmptyStepCommand("build".to_string()),
    );
    assert!(matches!(Job::new("", "Title", vec![step("s", &["sh"])]), Err(JobError::BadLine(_))));
    assert!(matches!(Job::new("id", "  ", vec![step("s", &["sh"])]), Err(JobError::BadLine(_))));
}

#[test]
fn job_step_order_roundtrip() {
    let job = three_step_job();
    let text = job.to_text();
    let reloaded = Job::from_text(&text).expect("the text parses back");

    assert_eq!(reloaded, job, "a round trip is lossless");
    assert_eq!(
        reloaded.steps().iter().map(|s| s.name.clone()).collect::<Vec<_>>(),
        vec!["site", "raise", "cap"],
        "step order is preserved, not sorted",
    );
    assert_eq!(
        reloaded.steps()[1].command,
        vec!["sh".to_string(), "-c".to_string(), "echo raise".to_string()],
        "a step keeps its command words",
    );

    // The state survives too, including a state that is not Pending.
    let mut started = three_step_job();
    started.start();
    let again = Job::from_text(&started.to_text()).expect("parses");
    assert_eq!(again.state(), JobState::Running);

    // A damaged record is refused by name, never half-read. A record with a
    // header but no steps is the empty job; a truncated one is a bad line.
    assert!(matches!(
        Job::from_text("job j\ntitle t\nstate pending\n"),
        Err(JobError::NoSteps),
    ));
    assert!(matches!(Job::from_text("job j\nstep a :: sh\n"), Err(JobError::BadLine(_))));
    assert!(matches!(Job::from_text("nonsense\n"), Err(JobError::BadLine(_))));
    assert!(matches!(
        Job::from_text("job j\ntitle t\nstate nowhere\nstep a :: sh\n"),
        Err(JobError::UnknownState(_)),
    ));
}

#[test]
fn cancel_finished() {
    // A finished job is not cancelled: the outcome says so and the state stays.
    let mut job = three_step_job();
    assert!(job.start());
    assert!(job.finish());
    assert_eq!(job.state(), JobState::Finished);
    assert_eq!(job.cancel(), CancelOutcome::AlreadyFinished);
    assert_eq!(job.state(), JobState::Finished, "history is not rewritten");

    // A second cancel is its own no-op.
    assert_eq!(job.cancel(), CancelOutcome::AlreadyFinished);

    // A live job cancels for real, and then says it was already cancelled.
    let mut live = three_step_job();
    live.start();
    assert_eq!(live.cancel(), CancelOutcome::Cancelled);
    assert_eq!(live.state(), JobState::Cancelled);
    assert_eq!(live.cancel(), CancelOutcome::AlreadyCancelled);

    // A cancelled job cannot finish, and a finished job cannot be started.
    assert!(!live.finish(), "a cancelled job never reports done");
    assert_eq!(live.state(), JobState::Cancelled);
    assert!(!job.start(), "a finished job does not run again");
}

#[test]
fn cancel_from_pending_is_a_real_cancel() {
    let mut job = three_step_job();
    assert_eq!(job.cancel(), CancelOutcome::Cancelled);
    assert_eq!(job.state(), JobState::Cancelled);
}
