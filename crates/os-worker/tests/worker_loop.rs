//! B22 claim-path start: worker poll → capability match → atomic
//! claim → lease heartbeat → done/blocked reporting (`os/mos/worker.py`
//! `run_once`/`run_loop` through the [`WorkerBackend`] seam).
use os_worker::{
    Announcement, HandlerError, RunReport, Worker, WorkerBackend,
};
use std::collections::{BTreeSet, HashMap};

struct FakeBackend {
    dms: Vec<Announcement>,
    specs: HashMap<String, String>,
    registers: usize,
    heartbeats: usize,
    claimed: Vec<String>,
    claim_ok: HashMap<String, bool>,
    done: Vec<String>,
    finish_ok: bool,
    blocked: Vec<(String, String)>,
}

impl FakeBackend {
    fn new() -> FakeBackend {
        FakeBackend {
            dms: Vec::new(),
            specs: HashMap::new(),
            registers: 0,
            heartbeats: 0,
            claimed: Vec::new(),
            claim_ok: HashMap::new(),
            done: Vec::new(),
            finish_ok: true,
            blocked: Vec::new(),
        }
    }
}

impl WorkerBackend for FakeBackend {
    fn register(&mut self, _w: &Worker) {
        self.registers += 1;
    }
    fn heartbeat(&mut self, _w: &Worker) -> Vec<String> {
        self.heartbeats += 1;
        self.claimed.clone()
    }
    fn poll_dms(&mut self, _w: &Worker) -> Vec<Announcement> {
        self.dms.clone()
    }
    fn claim(&mut self, _w: &Worker, jid: &str) -> (bool, String) {
        let ok = self.claim_ok.get(jid).copied().unwrap_or(true);
        if ok {
            self.claimed.push(jid.to_string());
            (true, format!("CLAIMED {jid}"))
        } else {
            (false, "claim refused: already claimed".to_string())
        }
    }
    fn finish(&mut self, _w: &Worker, jid: &str, _c: &str, _n: &str) -> bool {
        if self.finish_ok {
            self.done.push(jid.to_string());
            true
        } else {
            false
        }
    }
    fn block(&mut self, _w: &Worker, jid: &str, reason: &str) -> bool {
        self.blocked.push((jid.to_string(), reason.to_string()));
        true
    }
    fn job_spec(&mut self, _w: &Worker, jid: &str) -> String {
        self.specs.get(jid).cloned().unwrap_or_default()
    }
}

fn worker() -> Worker {
    Worker::new("w1", "s3cret", &["python", "Testing"], "", "/tmp", 1800, 1)
}

fn ann(jid: &str, title: &str, reqs: &[&str]) -> Announcement {
    Announcement {
        jid: jid.to_string(),
        title: title.to_string(),
        reqs: reqs.iter().map(|s| s.to_string()).collect(),
    }
}

fn ok_handler(
    _jid: &str,
    _title: &str,
    _spec: &str,
    _workdir: &str,
) -> Result<(String, String), HandlerError> {
    Ok(("deadbee".to_string(), "did it".to_string()))
}

#[test]
fn poll_claim_done_reporting_chain() {
    // The full chain: poll finds the DM, caps cover the reqs, the
    // atomic claim succeeds, the handler runs, done is reported.
    let mut backend = FakeBackend::new();
    backend.dms = vec![ann("7", "Write it", &["python"])];
    let report: RunReport = worker().run_once(&mut backend, ok_handler);
    assert_eq!(report.claimed, vec!["7".to_string()]);
    assert_eq!(report.done, vec!["7".to_string()]);
    assert!(report.blocked.is_empty() && report.skipped.is_empty() && report.errors.is_empty());
    assert_eq!(backend.registers, 1, "run_once registers first");
    assert_eq!(backend.heartbeats, 1, "run_once heartbeats the lease");
}

#[test]
fn capability_mismatch_skips_before_any_claim() {
    // `req=rust` is not covered by caps: skipped, and the claim path
    // is never entered.
    let mut backend = FakeBackend::new();
    backend.dms = vec![ann("8", "Write it", &["rust"])];
    let report = worker().run_once(&mut backend, |_, _, _, _| {
        panic!("handler must not run for unmet requirements")
    });
    assert_eq!(report.skipped, vec!["8".to_string()]);
    assert!(backend.claimed.is_empty(), "no claim attempted");
    assert!(report.done.is_empty() && report.claimed.is_empty());
}

#[test]
fn lost_claim_race_is_an_error_not_a_crash() {
    // The atomic claim fails (a rival holds the job): the cycle
    // records `claim <jid>: <detail>` and moves on.
    let mut backend = FakeBackend::new();
    backend.dms = vec![ann("9", "Write it", &["python"])];
    backend.claim_ok.insert("9".to_string(), false);
    let report = worker().run_once(&mut backend, ok_handler);
    assert!(report.claimed.is_empty());
    assert_eq!(report.errors.len(), 1);
    assert!(report.errors[0].starts_with("claim 9: "), "{}", report.errors[0]);
    assert!(report.errors[0].contains("already claimed"), "{}", report.errors[0]);
}

#[test]
fn blocked_and_crash_handlers_report_blocked() {
    let mut backend = FakeBackend::new();
    backend.dms = vec![
        ann("10", "Clean block", &[]),
        ann("11", "Crash", &[]),
    ];
    let report = worker().run_once(&mut backend, |jid, _, _, _| {
        if jid == "10" {
            Err(HandlerError::Blocked("needs a human".to_string()))
        } else {
            Err(HandlerError::Crashed("boom".to_string()))
        }
    });
    assert_eq!(report.blocked, vec!["10".to_string(), "11".to_string()]);
    assert_eq!(backend.blocked[0], ("10".to_string(), "needs a human".to_string()));
    assert!(backend.blocked[1].0 == "11");
    assert!(backend.blocked[1].1.starts_with("handler crashed: "), "{}", backend.blocked[1].1);
    assert!(backend.blocked[1].1.contains("boom"), "{}", backend.blocked[1].1);
}

#[test]
fn blocked_reason_is_capped_at_500_chars() {
    let mut backend = FakeBackend::new();
    backend.dms = vec![ann("12", "Long block", &[])];
    let report = worker().run_once(&mut backend, |_, _, _, _| {
        Err(HandlerError::Blocked("r".repeat(600)))
    });
    assert_eq!(report.blocked, vec!["12".to_string()]);
    assert_eq!(backend.blocked[0].1.chars().count(), 500);
}

#[test]
fn no_dm_secret_polls_nothing() {
    // Python short-circuits `poll_dms` when the secret is empty; the
    // Rust loop mirrors it so no backend read happens.
    let mut backend = FakeBackend::new();
    backend.dms = vec![ann("13", "Should not appear", &[])];
    let w = Worker::new("w1", "", &["python"], "", "/tmp", 1800, 1);
    let report = w.run_once(&mut backend, |_, _, _, _| {
        panic!("no announcements without a DM secret")
    });
    assert_eq!(report, RunReport::default());
    assert_eq!(backend.registers, 1);
}

#[test]
fn run_loop_bounds_cycles_and_heartbeats_each_one() {
    // `run_loop` with `Some(n)` runs exactly n poll/claim cycles and
    // heartbeats each one; interval 0 keeps the test fast.
    let mut backend = FakeBackend::new();
    backend.dms = vec![ann("20", "Steady work", &["python"])];
    worker().run_loop(&mut backend, ok_handler, 0, Some(3));
    assert_eq!(backend.registers, 3);
    assert_eq!(backend.heartbeats, 3, "lease heartbeat runs every cycle");
    assert_eq!(backend.done, vec!["20".to_string(); 3]);
}

#[test]
fn run_loop_zero_cycles_does_nothing() {
    let mut backend = FakeBackend::new();
    worker().run_loop(&mut backend, ok_handler, 0, Some(0));
    assert_eq!(backend.registers, 0);
    assert_eq!(backend.heartbeats, 0);
}

#[test]
fn caps_normalize_like_python() {
    // `{c.strip().lower()}` with empties dropped.
    let w = Worker::new("w", "s", &["  Python ", "", "TESTING", "  "], "", "/tmp", 60, 1);
    let want: BTreeSet<String> =
        ["python".to_string(), "testing".to_string()].into_iter().collect();
    assert_eq!(w.caps, want);
    assert!(w.matches(&BTreeSet::new()), "empty reqs always match");
    assert!(!w.matches(&["rust".to_string()].into_iter().collect()));
}
