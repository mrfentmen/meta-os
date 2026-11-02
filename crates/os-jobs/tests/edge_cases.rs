//! B027 — the four named edge cases for `os-jobs`: empty input, maximum
//! input, duplicate input, out-of-order input. Each test is named for the
//! case it pins, and each asserts the code's real behaviour rather than a
//! wished-for one.

use os_jobs::{FakeClock, FakeStore, JobQueue, PostArgs};
use std::rc::Rc;

const START: u64 = 1_700_000_000;
const NS: &str = "muse-bus:tjob";

fn queue() -> (Rc<FakeClock>, JobQueue<FakeStore>) {
    let clock = Rc::new(FakeClock::new(START));
    let store = FakeStore::new(clock.clone());
    let q = JobQueue::new(store, clock.clone(), NS, "tester", "host-a");
    (clock, q)
}

fn post(q: &mut JobQueue<FakeStore>, title: &str, spec: &str) -> String {
    let mut args = PostArgs::default();
    args.title = title.to_string();
    args.spec = spec.to_string();
    let out = q.post(args);
    assert_eq!(out.code, 0, "{:?}", out.err);
    out.out.trim().trim_start_matches("JOB ").to_string()
}

#[test]
fn empty_input_omits_empty_fields_and_lists_no_jobs() {
    let (_c, mut q) = queue();
    // An empty title is allowed; empty optional fields are not written at
    // all because JobQueue::hset drops empty values (lib.rs 984-998).
    let jid = post(&mut q, "", "spec");
    let (h, spec) = q.job_get(&jid);
    let h = h.expect("job exists");
    assert_eq!(spec, "spec");
    for field in ["title", "files", "deps", "req", "artifacts", "max_attempts"] {
        assert!(
            !h.contains_key(field),
            "empty {field} must not be stored, got {:?}",
            h.get(field)
        );
    }
    let out = q.list("no-such-status", false);
    assert_eq!(out.code, 0);
    assert_eq!(out.out.trim(), "NO_JOBS");
}

#[test]
fn maximum_input_round_trips_a_64k_spec() {
    let (_c, mut q) = queue();
    let spec = "x".repeat(64 * 1024);
    let jid = post(&mut q, "big", &spec);
    let (h, stored) = q.job_get(&jid);
    assert!(h.is_some());
    assert_eq!(stored.len(), spec.len());
    assert_eq!(stored, spec);
}

#[test]
fn duplicate_input_in_one_attach_is_stored_twice() {
    let (_c, mut q) = queue();
    let jid = post(&mut q, "dupes", "spec");
    let refs = vec![
        "artifact:1/report.txt@v1".to_string(),
        "artifact:1/report.txt@v1".to_string(),
    ];
    let out = q.attach(&jid, &refs);
    assert_eq!(out.code, 0, "{:?}", out.err);
    // Real behaviour (lib.rs 1671-1694 and os/jobs.py:583-593): the
    // dedupe compares against the STORED list only, so a duplicate
    // inside one call is stored twice. Pinned, not endorsed.
    let (h, _) = q.job_get(&jid);
    let artifacts = h.unwrap()["artifacts"].clone();
    assert_eq!(
        artifacts,
        "artifact:1/report.txt@v1,artifact:1/report.txt@v1"
    );
    // Re-attaching the same ref against the stored list is a no-op.
    let again = q.attach(&jid, &["artifact:1/report.txt@v1".to_string()]);
    assert_eq!(again.code, 0);
    assert!(again.out.contains("(already present)"));
}

#[test]
fn out_of_order_input_lists_ids_lexicographically_within_one_second() {
    let (_c, mut q) = queue();
    // Ten posts inside the same clock second all carry the same zset
    // score. FakeStore::zrange sorts (score, member) (lib.rs 303-317),
    // so the index order is lexicographic, not numeric.
    for i in 0..10 {
        post(&mut q, &format!("job {i}"), "s");
    }
    let out = q.list("all", false);
    assert_eq!(out.code, 0);
    let ids: Vec<String> = out
        .out
        .lines()
        .skip(1)
        .filter_map(|line| line.split_whitespace().next().map(str::to_string))
        .collect();
    assert_eq!(
        ids,
        vec!["1", "10", "2", "3", "4", "5", "6", "7", "8", "9"]
    );
}

#[test]
fn duplicate_deps_warn_once_per_listed_dep() {
    let (_c, mut q) = queue();
    let mut args = PostArgs::default();
    args.title = "deps".to_string();
    args.spec = "s".to_string();
    args.deps = "2,2".to_string();
    let out = q.post(args);
    assert_eq!(out.code, 0);
    let warnings = out.err.matches("does not exist").count();
    assert_eq!(warnings, 2, "each listed dep is checked: {:?}", out.err);
}

#[test]
fn zero_attempt_budget_fails_final_on_the_first_requeue() {
    let (clock, mut q) = queue();
    let mut args = PostArgs::default();
    args.title = "budget".to_string();
    args.spec = "s".to_string();
    args.max_attempts = Some(0);
    assert_eq!(q.post(args).code, 0);
    assert_eq!(q.claim("1", "", 1800, None).code, 0);
    clock.advance(1801);
    let out = q.requeue("1", "");
    assert_eq!(out.code, 2);
    assert!(out.err.contains("reached max_attempts (0)"), "{:?}", out.err);
    assert_eq!(q.job_get("1").0.unwrap()["status"], "failed-final");
}
