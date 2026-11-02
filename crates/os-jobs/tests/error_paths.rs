//! B026 — every refusal and failure branch in `os-jobs`, exercised through
//! the public API. The crate's own `mod tests` covers the happy paths and
//! some refusals; this file covers the store-failure branches that the
//! in-crate `FakeStore` cannot produce, using a fault-injecting `JobStore`.
//!
//! No behaviour is invented: each assertion names the message or exit code
//! the code returns (`crates/os-jobs/src/lib.rs`, commands at lines
//! 1343-2275).

use os_jobs::{
    environment_lines, job_key, parse_keyring, read_keyring_file, spec_key, CmdOutcome, EnvRecord,
    FakeClock, FakeStore, JobQueue, JobStore, PostArgs, SetMode, StoreError, Verdict,
};
use std::cell::Cell;
use std::rc::Rc;

const START: u64 = 1_700_000_000;
const NS: &str = "muse-bus:tjob";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Fault {
    None,
    Incr,
    Hset,
    Set,
    Zadd,
    Zrange,
    Get,
    Hgetall,
}

/// Wraps the crate's own `FakeStore`. `fault` fails one operation; the
/// `hset_fail_after` budget fails a later `hset` (needed where the first
/// write must succeed and a subsequent one must fail).
struct FaultStore {
    inner: FakeStore,
    fault: Cell<Fault>,
    hset_fail_after: Cell<Option<usize>>,
}

impl FaultStore {
    fn new(clock: Rc<FakeClock>) -> Self {
        FaultStore {
            inner: FakeStore::new(clock),
            fault: Cell::new(Fault::None),
            hset_fail_after: Cell::new(None),
        }
    }

    fn hit(&self, op: Fault) -> Result<(), StoreError> {
        if self.fault.get() == op {
            Err(StoreError(format!("boom:{:?}", op)))
        } else {
            Ok(())
        }
    }
}

impl JobStore for FaultStore {
    fn incr(&mut self, key: &str) -> Result<u64, StoreError> {
        self.hit(Fault::Incr)?;
        self.inner.incr(key)
    }

    fn hset(&mut self, key: &str, fields: &[(&str, &str)]) -> Result<(), StoreError> {
        if let Some(left) = self.hset_fail_after.get() {
            if left == 0 {
                self.hset_fail_after.set(None);
                return Err(StoreError("boom:Hset".to_string()));
            }
            self.hset_fail_after.set(Some(left - 1));
        }
        self.hit(Fault::Hset)?;
        self.inner.hset(key, fields)
    }

    fn hgetall(&mut self, key: &str) -> Result<Vec<(String, String)>, StoreError> {
        self.hit(Fault::Hgetall)?;
        self.inner.hgetall(key)
    }

    fn hdel(&mut self, key: &str, fields: &[&str]) -> Result<(), StoreError> {
        self.inner.hdel(key, fields)
    }

    fn get(&mut self, key: &str) -> Result<Option<String>, StoreError> {
        self.hit(Fault::Get)?;
        self.inner.get(key)
    }

    fn set(
        &mut self,
        key: &str,
        value: &str,
        mode: Option<SetMode>,
        ex_secs: Option<u64>,
    ) -> Result<bool, StoreError> {
        self.hit(Fault::Set)?;
        self.inner.set(key, value, mode, ex_secs)
    }

    fn del(&mut self, key: &str) -> Result<(), StoreError> {
        self.inner.del(key)
    }

    fn expire(&mut self, key: &str, secs: u64) -> Result<bool, StoreError> {
        self.inner.expire(key, secs)
    }

    fn zadd(&mut self, key: &str, score: i64, member: &str) -> Result<(), StoreError> {
        self.hit(Fault::Zadd)?;
        self.inner.zadd(key, score, member)
    }

    fn zrange(&mut self, key: &str) -> Result<Vec<String>, StoreError> {
        self.hit(Fault::Zrange)?;
        self.inner.zrange(key)
    }
}

fn queue() -> (Rc<FakeClock>, JobQueue<FaultStore>) {
    let clock = Rc::new(FakeClock::new(START));
    let store = FaultStore::new(clock.clone());
    let q = JobQueue::new(store, clock.clone(), NS, "tester", "host-a");
    (clock, q)
}

fn post(q: &mut JobQueue<FaultStore>) -> CmdOutcome {
    let mut args = PostArgs::default();
    args.title = "T".to_string();
    args.spec = "do the work".to_string();
    q.post(args)
}

fn post_with(q: &mut JobQueue<FaultStore>, f: impl Fn(&mut PostArgs)) -> CmdOutcome {
    let mut args = PostArgs::default();
    args.title = "T".to_string();
    args.spec = "do the work".to_string();
    f(&mut args);
    q.post(args)
}

fn secret_file(content: &str) -> std::path::PathBuf {
    let n = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    let path = std::env::temp_dir().join(format!("os-jobs-err-{}-{}", std::process::id(), n));
    std::fs::write(&path, content).expect("write secret file");
    path
}

fn err_has(out: &CmdOutcome, needle: &str) {
    assert!(
        out.err.contains(needle),
        "expected stderr to contain {:?}, got code={} out={:?} err={:?}",
        needle,
        out.code,
        out.out,
        out.err
    );
}

// -- post: validation before any state change ------------------------------

#[test]
fn post_empty_spec_is_refused() {
    let (_c, mut q) = queue();
    let out = post_with(&mut q, |a| a.spec = "   ".to_string());
    assert_eq!(out.code, 2);
    err_has(&out, "ERROR: --spec is empty");
    assert_eq!(q.job_get("1").0, None, "a refused post must write nothing");
}

#[test]
fn post_bad_room_is_refused() {
    let (_c, mut q) = queue();
    let out = post_with(&mut q, |a| a.room = "@@@".to_string());
    assert_eq!(out.code, 2);
    err_has(&out, "invalid room name");
    assert_eq!(q.job_get("1").0, None);
}

#[test]
fn post_short_lease_is_refused() {
    let (_c, mut q) = queue();
    let out = post_with(&mut q, |a| a.lease = 59);
    assert_eq!(out.code, 2);
    err_has(&out, "ERROR: --lease needs at least 60s");
    assert_eq!(q.job_get("1").0, None);
}

#[test]
fn post_malformed_artifact_ref_is_refused() {
    let (_c, mut q) = queue();
    let out = post_with(&mut q, |a| a.artifacts = "artifact:1/x@v0".to_string());
    assert_eq!(out.code, 2);
    err_has(&out, "malformed artifact reference");
    assert_eq!(q.job_get("1").0, None);
}

// -- post: store failures --------------------------------------------------

#[test]
fn post_fails_when_the_sequence_counter_fails() {
    let (_c, mut q) = queue();
    q.store.fault.set(Fault::Incr);
    let out = post(&mut q);
    assert_eq!(out.code, 2);
    err_has(&out, "RELAY_ERROR: post failed (boom:Incr)");
    assert_eq!(q.job_get("1").0, None);
}

#[test]
fn post_fails_when_the_job_hash_write_fails() {
    let (_c, mut q) = queue();
    q.store.fault.set(Fault::Hset);
    let out = post(&mut q);
    assert_eq!(out.code, 2);
    err_has(&out, "RELAY_ERROR: post failed (boom:Hset)");
}

#[test]
fn post_fails_when_the_spec_write_fails() {
    let (_c, mut q) = queue();
    q.store.fault.set(Fault::Set);
    let out = post(&mut q);
    assert_eq!(out.code, 2);
    err_has(&out, "RELAY_ERROR: post failed (boom:Set)");
}

#[test]
fn post_fails_when_the_index_write_fails() {
    let (_c, mut q) = queue();
    q.store.fault.set(Fault::Zadd);
    let out = post(&mut q);
    assert_eq!(out.code, 2);
    err_has(&out, "RELAY_ERROR: post failed (boom:Zadd)");
}

#[test]
fn post_with_a_missing_secret_file_reports_after_the_job_is_written() {
    // Real order: the job hash/spec/index are written first (lib.rs
    // 1409-1460), then the keyring is read (1462). A bad key path
    // therefore leaves an unsigned job behind and exits 2.
    let (_c, mut q) = queue();
    let out = post_with(&mut q, |a| {
        a.secret_file = Some("/nonexistent/os-jobs/secret".to_string())
    });
    assert_eq!(out.code, 2);
    err_has(&out, "ERROR: cannot read secret file");
    assert!(q.job_get("1").0.is_some(), "the job was already written");
}

#[test]
fn post_refuses_an_unknown_kid() {
    let (_c, mut q) = queue();
    let path = secret_file("main:secret\n");
    let out = post_with(&mut q, |a| {
        a.secret_file = Some(path.to_string_lossy().into_owned());
        a.kid = "other".to_string();
    });
    assert_eq!(out.code, 2);
    err_has(&out, "ERROR: unknown kid 'other'");
    let _ = std::fs::remove_file(path);
}

#[test]
fn post_refuses_a_zero_expiry() {
    let (_c, mut q) = queue();
    let path = secret_file("main:secret\n");
    let out = post_with(&mut q, |a| {
        a.secret_file = Some(path.to_string_lossy().into_owned());
        a.expires = Some(0);
    });
    assert_eq!(out.code, 2);
    err_has(&out, "ERROR: --expires needs a positive number of seconds");
    let _ = std::fs::remove_file(path);
}

#[test]
fn post_reports_a_signing_write_failure() {
    let (_c, mut q) = queue();
    let path = secret_file("main:secret\n");
    // The first hset (job fields) succeeds; the second (signature) fails.
    q.store.hset_fail_after.set(Some(1));
    let out = post_with(&mut q, |a| {
        a.secret_file = Some(path.to_string_lossy().into_owned())
    });
    assert_eq!(out.code, 2);
    err_has(&out, "RELAY_ERROR: signing failed");
    let _ = std::fs::remove_file(path);
}

// -- claim: refusals -------------------------------------------------------

#[test]
fn claim_refuses_a_missing_job() {
    let (_c, mut q) = queue();
    let out = q.claim("1", "", 1800, None);
    assert_eq!(out.code, 2);
    err_has(&out, "ERROR: no such job: 1");
}

#[test]
fn claim_refuses_a_short_lease() {
    let (_c, mut q) = queue();
    assert_eq!(post(&mut q).code, 0);
    let out = q.claim("1", "", 10, None);
    assert_eq!(out.code, 2);
    err_has(&out, "ERROR: --lease needs at least 60s");
}

#[test]
fn claim_refuses_a_job_that_is_not_open() {
    let (_c, mut q) = queue();
    assert_eq!(post(&mut q).code, 0);
    assert_eq!(q.claim("1", "", 1800, None).code, 0);
    q.set_nick("other", "host-b");
    let out = q.claim("1", "", 1800, None);
    assert_eq!(out.code, 2);
    err_has(&out, "ERROR: job 1 is claimed (claimed by tester)");
}

#[test]
fn claim_refuses_a_tampered_signature_and_announces_it() {
    let (_c, mut q) = queue();
    let path = secret_file("main:secret\n");
    let out = post_with(&mut q, |a| {
        a.secret_file = Some(path.to_string_lossy().into_owned())
    });
    assert_eq!(out.code, 0, "{:?}", out.err);
    // Overwrite the spec after signing: the v2 payload covers it.
    assert!(q.store_set_raw(&spec_key(NS, "1"), "tampered", None).unwrap());
    let out = q.claim("1", "", 1800, Some(path.to_string_lossy().as_ref()));
    assert_eq!(out.code, 1);
    err_has(&out, "signature BAD");
    assert!(
        q.pushes_to("muse-bus").iter().any(|m| m.contains("REJECTED:1 BAD")),
        "a BAD signature must be announced to the room"
    );
    let _ = std::fs::remove_file(path);
}

#[test]
fn claim_refuses_an_expired_signature() {
    let (clock, mut q) = queue();
    let path = secret_file("main:secret\n");
    let out = post_with(&mut q, |a| {
        a.secret_file = Some(path.to_string_lossy().into_owned());
        a.expires = Some(60);
    });
    assert_eq!(out.code, 0, "{:?}", out.err);
    clock.advance(61);
    let out = q.claim("1", "", 1800, Some(path.to_string_lossy().as_ref()));
    assert_eq!(out.code, 1);
    err_has(&out, "signature EXPIRED");
    let _ = std::fs::remove_file(path);
}

#[test]
fn claim_reports_a_malformed_expiry_as_a_verify_failure() {
    let (_c, mut q) = queue();
    let path = secret_file("main:secret\n");
    assert_eq!(
        post_with(&mut q, |a| a.secret_file = Some(path.to_string_lossy().into_owned())).code,
        0
    );
    q.store_hset_raw(&job_key(NS, "1"), &[("expires_at", "not-a-number")])
        .unwrap();
    let out = q.claim("1", "", 1800, Some(path.to_string_lossy().as_ref()));
    assert_eq!(out.code, 2);
    err_has(&out, "RELAY_ERROR: verify failed (invalid literal for int()");
    let _ = std::fs::remove_file(path);
}

#[test]
fn claim_reports_a_mutex_write_failure() {
    let (_c, mut q) = queue();
    assert_eq!(post(&mut q).code, 0);
    q.store.fault.set(Fault::Set);
    let out = q.claim("1", "", 1800, None);
    assert_eq!(out.code, 2);
    err_has(&out, "RELAY_ERROR: claim failed (boom:Set)");
}

#[test]
fn claim_rolls_back_the_mutex_when_the_claim_record_fails() {
    let (_c, mut q) = queue();
    assert_eq!(post(&mut q).code, 0);
    q.store.hset_fail_after.set(Some(0));
    let out = q.claim("1", "", 1800, None);
    assert_eq!(out.code, 2);
    err_has(&out, "RELAY_ERROR: claim record failed");
    assert_eq!(
        q.store_get_raw("muse-bus:tjob:1:claim"),
        None,
        "the orphaned mutex must be deleted"
    );
    assert_eq!(q.job_get("1").0.unwrap()["status"], "open");
}

// -- heartbeat / progress / done / blocked ---------------------------------

#[test]
fn heartbeat_refuses_a_missing_job() {
    let (_c, mut q) = queue();
    let out = q.heartbeat("9", 0);
    assert_eq!(out.code, 2);
    err_has(&out, "ERROR: no such job: 9");
}

#[test]
fn heartbeat_refuses_a_non_claimer() {
    let (_c, mut q) = queue();
    assert_eq!(post(&mut q).code, 0);
    assert_eq!(q.claim("1", "", 1800, None).code, 0);
    q.set_nick("other", "host-b");
    let out = q.heartbeat("1", 0);
    assert_eq!(out.code, 2);
    err_has(&out, "ERROR: job 1 is claimed by 'tester', not you");
}

#[test]
fn heartbeat_reports_a_lost_lease_on_a_store_failure() {
    let (_c, mut q) = queue();
    assert_eq!(post(&mut q).code, 0);
    assert_eq!(q.claim("1", "", 1800, None).code, 0);
    q.store.fault.set(Fault::Set);
    let out = q.heartbeat("1", 0);
    assert_eq!(out.code, 2);
    err_has(&out, "ERROR: lost the lease on job 1");
}

#[test]
fn progress_refuses_a_non_claimer() {
    let (_c, mut q) = queue();
    assert_eq!(post(&mut q).code, 0);
    assert_eq!(q.claim("1", "", 1800, None).code, 0);
    q.set_nick("other", "host-b");
    let out = q.progress("1", "halfway", "");
    assert_eq!(out.code, 2);
    err_has(&out, "not you");
}

#[test]
fn progress_reports_a_note_write_failure() {
    let (_c, mut q) = queue();
    assert_eq!(post(&mut q).code, 0);
    assert_eq!(q.claim("1", "", 1800, None).code, 0);
    // The lease renewal's hset succeeds; the note hset is the next one.
    q.store.hset_fail_after.set(Some(1));
    let out = q.progress("1", "halfway", "");
    assert_eq!(out.code, 2);
    err_has(&out, "RELAY_ERROR: note save failed");
}

#[test]
fn done_refuses_a_non_claimer() {
    let (_c, mut q) = queue();
    assert_eq!(post(&mut q).code, 0);
    assert_eq!(q.claim("1", "", 1800, None).code, 0);
    q.set_nick("other", "host-b");
    let out = q.done("1", "abc123", "", "");
    assert_eq!(out.code, 2);
    err_has(&out, "not you");
}

#[test]
fn done_reports_a_store_failure() {
    let (_c, mut q) = queue();
    assert_eq!(post(&mut q).code, 0);
    assert_eq!(q.claim("1", "", 1800, None).code, 0);
    q.store.hset_fail_after.set(Some(0));
    let out = q.done("1", "abc123", "finished", "");
    assert_eq!(out.code, 2);
    err_has(&out, "RELAY_ERROR: done failed");
}

#[test]
fn blocked_refuses_a_non_claimer() {
    let (_c, mut q) = queue();
    assert_eq!(post(&mut q).code, 0);
    assert_eq!(q.claim("1", "", 1800, None).code, 0);
    q.set_nick("other", "host-b");
    let out = q.blocked("1", "waiting on a key", "");
    assert_eq!(out.code, 2);
    err_has(&out, "not you");
}

// -- cancel / requeue / sweep ---------------------------------------------

#[test]
fn cancel_reports_a_store_failure() {
    let (_c, mut q) = queue();
    assert_eq!(post(&mut q).code, 0);
    q.store.hset_fail_after.set(Some(0));
    let out = q.cancel("1", "no longer needed");
    assert_eq!(out.code, 2);
    err_has(&out, "RELAY_ERROR: cancel failed");
}

#[test]
fn requeue_refuses_a_job_that_is_not_claimed() {
    let (_c, mut q) = queue();
    assert_eq!(post(&mut q).code, 0);
    let out = q.requeue("1", "");
    assert_eq!(out.code, 2);
    err_has(&out, "ERROR: job 1 is open, not claimed");
}

#[test]
fn requeue_reports_an_attempts_write_failure() {
    let (clock, mut q) = queue();
    assert_eq!(post(&mut q).code, 0);
    assert_eq!(q.claim("1", "", 1800, None).code, 0);
    clock.advance(1801);
    q.store.hset_fail_after.set(Some(0));
    let out = q.requeue("1", "");
    assert_eq!(out.code, 2);
    err_has(&out, "RELAY_ERROR: attempts update failed");
}

#[test]
fn requeue_reports_a_requeue_write_failure() {
    let (clock, mut q) = queue();
    assert_eq!(post(&mut q).code, 0);
    assert_eq!(q.claim("1", "", 1800, None).code, 0);
    clock.advance(1801);
    // The attempts hset succeeds; the requeue_fields hset is next.
    q.store.hset_fail_after.set(Some(1));
    let out = q.requeue("1", "");
    assert_eq!(out.code, 2);
    err_has(&out, "RELAY_ERROR: requeue failed");
}

#[test]
fn sweep_reports_an_index_read_failure() {
    let (_c, mut q) = queue();
    q.store.fault.set(Fault::Zrange);
    let out = q.sweep("");
    assert_eq!(out.code, 2);
    err_has(&out, "RELAY_ERROR: sweep failed (boom:Zrange)");
}

#[test]
fn sweep_warns_when_a_requeue_fails_and_does_not_fail_the_sweep() {
    let (clock, mut q) = queue();
    assert_eq!(post(&mut q).code, 0);
    assert_eq!(q.claim("1", "", 1800, None).code, 0);
    clock.advance(1801);
    q.store.hset_fail_after.set(Some(0));
    let out = q.sweep("");
    assert_eq!(out.code, 0);
    err_has(&out, "WARNING: requeue 1 failed");
    assert_eq!(out.out.trim(), "SWEEP_CLEAN");
}

// -- verify ----------------------------------------------------------------

#[test]
fn verify_refuses_an_unknown_job() {
    let (_c, mut q) = queue();
    let path = secret_file("main:secret\n");
    let out = q.verify("7", &path.to_string_lossy());
    assert_eq!(out.code, 2);
    err_has(&out, "ERROR: no such job: 7");
    let _ = std::fs::remove_file(path);
}

#[test]
fn verify_reports_a_missing_secret_file() {
    let (_c, mut q) = queue();
    let out = q.verify("1", "/nonexistent/os-jobs/secret");
    assert_eq!(out.code, 2);
    err_has(&out, "ERROR: cannot read secret file");
}

#[test]
fn verify_exits_one_on_a_bad_signature() {
    let (_c, mut q) = queue();
    let path = secret_file("main:secret\n");
    assert_eq!(
        post_with(&mut q, |a| a.secret_file = Some(path.to_string_lossy().into_owned())).code,
        0
    );
    q.store_set_raw(&spec_key(NS, "1"), "tampered", None).unwrap();
    let out = q.verify("1", &path.to_string_lossy());
    assert_eq!(out.code, 1);
    assert_eq!(out.out.trim(), "BAD");
    let _ = std::fs::remove_file(path);
}

// -- reads and seams -------------------------------------------------------

#[test]
fn job_get_returns_nothing_for_an_invalid_id() {
    let (_c, mut q) = queue();
    assert_eq!(q.job_get("0").0, None);
    assert_eq!(q.job_get("00").0, None);
    assert_eq!(q.job_get("abc").0, None);
}

#[test]
fn job_get_swallows_a_store_failure() {
    let (_c, mut q) = queue();
    q.store.fault.set(Fault::Hgetall);
    let (h, spec) = q.job_get("1");
    assert_eq!(h, None);
    assert_eq!(spec, "");
}

#[test]
fn nick_claim_returns_none_when_the_store_fails() {
    let (_c, mut q) = queue();
    q.store.fault.set(Fault::Get);
    assert_eq!(q.nick_claim(false), None);
}

// -- keyring and environment refusals -------------------------------------

#[test]
fn keyring_refuses_an_empty_file() {
    let err = parse_keyring("k", "").err().expect("expected a refusal");
    assert!(err.contains("is empty"), "{}", err);
}

#[test]
fn keyring_refuses_a_line_with_two_colons() {
    let err = parse_keyring("k", "kid:secret:extra").err().expect("expected a refusal");
    assert!(err.contains("bad keyring line"), "{}", err);
}

#[test]
fn keyring_refuses_empty_kid_or_secret() {
    assert!(parse_keyring("k", ":secret").err().expect("expected a refusal").contains("bad keyring line"));
    assert!(parse_keyring("k", "kid:").err().expect("expected a refusal").contains("bad keyring line"));
    assert!(parse_keyring("k", "a b:secret").err().expect("expected a refusal").contains("bad keyring line"));
}

#[test]
fn keyring_refuses_multiple_legacy_secrets() {
    let err = parse_keyring("k", "one\ntwo\n").err().expect("expected a refusal");
    assert!(err.contains("multiple secrets need kid:secret lines"), "{}", err);
}

#[test]
fn environment_lines_reports_every_missing_quarter() {
    let lines = environment_lines(&EnvRecord::default());
    assert_eq!(lines[0], "Repo state: not reported in this snapshot");
    assert_eq!(lines[1], "Bus state: not reported in this snapshot");
    assert_eq!(lines[2], "Working now: not reported in this snapshot");
    assert_eq!(lines[3], "Budget: not reported in this snapshot");
}

#[test]
fn environment_lines_reports_nobody_when_the_jobs_list_is_empty() {
    let env = EnvRecord {
        jobs: Some(Vec::new()),
        as_of: None,
        ..EnvRecord::default()
    };
    let lines = environment_lines(&env);
    assert_eq!(
        lines[2],
        "Working now: nobody holds a claimed job in this snapshot (snapshot time not reported)"
    );
}

// -- remaining per-command refusals ---------------------------------------

#[test]
fn claim_does_not_read_the_secret_file_for_an_unsigned_job() {
    let (_c, mut q) = queue();
    assert_eq!(post(&mut q).code, 0);
    // The queued job carries no signature, so the secret file is never
    // consulted: a missing path cannot fail this claim (lib.rs:1699).
    let out = q.claim("1", "", 1800, Some("/nonexistent/os-jobs/secret"));
    assert_eq!(out.code, 0);
}

#[test]
fn a_missing_keyring_file_is_a_read_refusal() {
    let err = read_keyring_file("/nonexistent/os-jobs/secret")
        .err()
        .expect("missing file must refuse");
    assert!(
        err.starts_with("cannot read secret file"),
        "unexpected message: {err}"
    );
}

#[test]
fn progress_refuses_a_missing_job() {
    let (_c, mut q) = queue();
    let out = q.progress("4", "note", "");
    assert_eq!(out.code, 2);
    err_has(&out, "ERROR: no such job: 4");
}

#[test]
fn done_refuses_a_missing_job() {
    let (_c, mut q) = queue();
    let out = q.done("4", "abc", "", "");
    assert_eq!(out.code, 2);
    err_has(&out, "ERROR: no such job: 4");
}

#[test]
fn blocked_refuses_a_missing_job() {
    let (_c, mut q) = queue();
    let out = q.blocked("4", "reason", "");
    assert_eq!(out.code, 2);
    err_has(&out, "ERROR: no such job: 4");
}

#[test]
fn attach_refuses_a_missing_job() {
    let (_c, mut q) = queue();
    let out = q.attach("4", &["artifact:1/a.txt@v1".to_string()]);
    assert_eq!(out.code, 2);
    err_has(&out, "ERROR: no such job: 4");
}

#[test]
fn attach_refuses_a_malformed_ref() {
    let (_c, mut q) = queue();
    assert_eq!(post(&mut q).code, 0);
    let out = q.attach("1", &["artifact:1/a.txt@v0".to_string()]);
    assert_eq!(out.code, 2);
    err_has(&out, "malformed artifact reference");
    assert_eq!(q.job_get("1").0.unwrap().get("artifacts"), None);
}

#[test]
fn attach_reports_a_write_failure() {
    let (_c, mut q) = queue();
    assert_eq!(post(&mut q).code, 0);
    q.store.hset_fail_after.set(Some(0));
    let out = q.attach("1", &["artifact:1/a.txt@v1".to_string()]);
    assert_eq!(out.code, 2);
    err_has(&out, "RELAY_ERROR: attach failed");
}

#[test]
fn requeue_refuses_a_missing_job() {
    let (_c, mut q) = queue();
    let out = q.requeue("4", "");
    assert_eq!(out.code, 2);
    err_has(&out, "ERROR: no such job: 4");
}

// Keep the Verdict import used even if a future edit drops the BAD test.
#[test]
fn verdict_words_are_stable() {
    assert_eq!(Verdict::Ok.as_str(), "OK");
    assert_eq!(Verdict::Bad.as_str(), "BAD");
    assert_eq!(Verdict::Unsigned.as_str(), "UNSIGNED");
    assert_eq!(Verdict::Expired.as_str(), "EXPIRED");
}
