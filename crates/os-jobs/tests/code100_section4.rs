//! CB-032: a job id reused after completion is a new job, not a
//! resurrection. `post` takes the next sequence id, so the completed
//! job keeps its record and the new work gets a different id.

use os_jobs::{index_key, FakeClock, FakeStore, JobQueue, JobStore, PostArgs};
use std::rc::Rc;

const NS: &str = "muse-bus:code100";

fn post_once(q: &mut JobQueue<FakeStore>) {
    let mut args = PostArgs::default();
    args.title = "reuse probe".to_string();
    args.spec = "do the work".to_string();
    assert_eq!(q.post(args).code, 0);
}

#[test]
fn posting_after_completion_uses_a_new_id_and_keeps_the_old_record() {
    let clock = Rc::new(FakeClock::new(1_700_000_000));
    let store = FakeStore::new(clock.clone());
    let mut q = JobQueue::new(store, clock, NS, "tester", "host-a");

    post_once(&mut q);
    let first = q.store.zrange(&index_key(NS)).unwrap()[0].clone();
    assert_eq!(q.claim(&first, "", 1800, None).code, 0);
    assert_eq!(q.done(&first, "abc123", "finished", "").code, 0);

    post_once(&mut q);
    let ids = q.store.zrange(&index_key(NS)).unwrap();
    assert_eq!(ids.len(), 2, "the completed job is still indexed");
    let second = ids
        .iter()
        .find(|id| **id != first)
        .expect("a different id for the new job")
        .clone();
    assert_ne!(first, second);
    assert_eq!(q.show(&first).code, 0, "the old job still resolves");
}
