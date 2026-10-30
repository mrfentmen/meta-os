//! Kill-a-worker drill (WDG-020): a fake worker dies mid-job and the
//! watchdog plus the lease sweep must behave.
//!
//! Port of `os/intel/drills/kill_worker.py` (batch B21, task T120).
//! Port behavior, do not redesign.
//!
//! Scenario, as the demo will run it live: a fake worker claims a job,
//! posts one progress note, keeps heartbeating — then dies mid-job.
//! The watchdog must raise exactly one presence-stall alert naming the
//! nick, the job, and the last-progress age, and once the job's lease
//! expires the sweep must requeue the job so the stall alert stops
//! firing and another worker can claim it.
//!
//! The drill runs unattended on fixtures: no network, no Redis, no bus
//! posts. The sweep half mirrors the rule `jobs.py` already ships
//! (`_claim_or_requeue`: a claimed job whose lease has expired reopens
//! — status back to open, claim fields cleared). The watchdog itself
//! never touches job state (v1 alerts only), so the drill applies the
//! sweep rule to the fixture snapshot and then re-ticks to prove the
//! alert auto-resolves; it does not claim the watchdog performed the
//! requeue.
//!
//! Timeline uses a fake clock (base time [`T0`]) so the drill is
//! deterministic: thresholds come from the constants below, never
//! hardcoded inline in the phase logic.
//!
//! # Seams (self-containment: this file uses only `std` plus items
//! defined here, per the batch work-split)
//!
//! - **Thresholds.** Python reads `intel/thresholds.py` (a sibling
//!   module in this batch, owned by another worker). The values the
//!   drill needs are defined locally here — [`STALL_MINUTES`],
//!   [`PROGRESS_STALL_MINUTES`], and [`LEASE_DEFAULT_SECONDS`] — with
//!   the same documented defaults (10 minutes, 10 minutes, 1800
//!   seconds). At assembly the parent should replace these with the
//!   shared thresholds module so a retune retunes the drill; until
//!   then a threshold change here must be mirrored there, and vice
//!   versa. Note the Python comment: `LEASE_DEFAULT_SECONDS` is owned
//!   by `jobs.py`, not by thresholds, and is deliberately not
//!   env-overridable there.
//! - **Watchdog tick.** Python calls `intel/watchdog.tick` and
//!   `intel/watchdog.announcements_for` (a sibling module in this
//!   batch). They are seamed here as the [`WatchdogTick`] trait, so
//!   the parent can wire the real watchdog at assembly without
//!   touching this file's drill logic. [`LocalWatchdog`] is the
//!   standalone stand-in used by [`run_drill`]: it mirrors exactly
//!   the two detectors the drill's fixture can trip (WDG-002
//!   presence-stall and WDG-003 progress-stall, including the
//!   last-activity field order over the fields this fixture carries)
//!   and the announcements rule that only critical alerts yield a
//!   line. It is a seam mirror, not the watchdog itself: the full
//!   detector set, explanation text, and alert ids live in the
//!   watchdog module.
//! - **Sweep rule.** [`sweep_expired_leases`] is the drill's own
//!   fixture mirror of `jobs.py` `_claim_or_requeue`, ported in full
//!   (see its docs for the field-clearing oddity it preserves).
//!
//! # Live-behavior boundary (not faked here)
//!
//! The Python script's `main` prints `PASS`/`FAIL` lines and exits 0
//! or 1. That reporting shape is ported as [`run_drill_stdout`],
//! which returns the exit code and the lines instead of printing
//! them; the caller owns printing and exiting. No process is killed
//! by this module: [`FakeWorker::kill`] only models a death (presence
//! stops, heartbeats stop) inside the fixture snapshot. A real worker
//! death, a live watchdog tick, and a live lease sweep are outside
//! this module.

/// The demo job id (Python `JOB_ID`).
pub const JOB_ID: &str = "7";

/// The demo worker nick (Python `NICK`).
pub const NICK: &str = "pax";

/// Fake-clock base time (Python `T0`), unix seconds.
pub const T0: i64 = 100_000;

/// Stall window in minutes.
///
/// SEAM: owned by `intel/thresholds.py` (`STALL_MINUTES`, default 10,
/// env-overridable there). Local copy so this file stays
/// self-contained; the parent replaces it with the shared value at
/// assembly.
pub const STALL_MINUTES: i64 = 10;

/// Progress-stall window in minutes.
///
/// SEAM: owned by `intel/thresholds.py`
/// (`PROGRESS_STALL_MINUTES`, default 10). Needed by the local
/// watchdog stand-in for the healthy-worker phase (a present worker
/// with unmoving work). Same replacement note as [`STALL_MINUTES`].
pub const PROGRESS_STALL_MINUTES: i64 = 10;

/// Default job lease in seconds.
///
/// SEAM: owned by `jobs.py` (`LEASE_DEFAULT = 1800` there), referenced
/// from `intel/thresholds.py` as `LEASE_DEFAULT_SECONDS` but
/// deliberately not env-overridable there. Local copy for
/// self-containment; same replacement note as [`STALL_MINUTES`].
pub const LEASE_DEFAULT_SECONDS: i64 = 1800;

/// A fixture message posted by a worker (Python snapshot `messages`
/// entry). Only the fields the drill reads are carried.
#[derive(Clone, Debug, PartialEq)]
pub struct Message {
    /// Posting worker nick.
    pub nick: String,
    /// Message text.
    pub text: String,
}

/// A fixture job record (Python snapshot `jobs` entry).
///
/// Timestamps are unix seconds. `lease_until` is `None` when the job
/// carries no (numeric) lease deadline: the sweep skips such jobs,
/// mirroring Python's `isinstance(lease_until, (int, float))` guard.
/// `last_progress` is the drill's progress timestamp; `claimed_at`
/// is the fallback last-activity timestamp (see [`LocalWatchdog`]).
#[derive(Clone, Debug, PartialEq)]
pub struct Job {
    /// Job id.
    pub id: String,
    /// Job title.
    pub title: String,
    /// Job status: `"claimed"` or `"open"` in this drill.
    pub status: String,
    /// Claimer nick, cleared by the sweep on requeue.
    pub claim: Option<String>,
    /// Claim host, cleared by the sweep on requeue (never set by the
    /// fixture worker, but the sweep deletes it when present).
    pub claim_host: Option<String>,
    /// Time the job was claimed, cleared by the sweep on requeue.
    pub claimed_at: Option<i64>,
    /// Lease length in seconds (kept by the sweep: Python's
    /// `_requeue_fields` deletes `claim`, `claim_host`, `claimed_at`,
    /// and `lease_until`, but NOT `lease` — that oddity is ported).
    pub lease: Option<i64>,
    /// Lease deadline, cleared by the sweep on requeue.
    pub lease_until: Option<i64>,
    /// Last heartbeat time on this job (set by [`FakeWorker::heartbeat`]).
    pub last_heartbeat: Option<i64>,
    /// Last progress time on this job (set by [`FakeWorker::progress`]).
    pub last_progress: Option<i64>,
}

/// A fixture snapshot: the board the watchdog ticks over.
///
/// `caps` is the caps registry: the list of registered nicks (Python
/// snapshot `caps` dict keys). `presence` is the current presence
/// list. Jobs, presence, and caps pass through the drill unchanged
/// except where a worker action or the sweep edits them.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Snapshot {
    /// Posted messages, in order.
    pub messages: Vec<Message>,
    /// Jobs on the board, in order.
    pub jobs: Vec<Job>,
    /// Nicks currently present.
    pub presence: Vec<String>,
    /// Registered nicks (caps registry keys).
    pub caps: Vec<String>,
}

/// A watchdog alert, holding the fields the drill asserts on.
///
/// The full Python alert dict also carries severity, title,
/// explanation, suggested fix, dedupe key, and creation time; those
/// live in the watchdog module. The drill asserts kind, nick, job,
/// and last-progress age, so those are what this seam type carries.
#[derive(Clone, Debug, PartialEq)]
pub struct Alert {
    /// Alert kind, e.g. `"presence-stall"`.
    pub kind: String,
    /// Stalled worker nick.
    pub nick: String,
    /// Stalled job id.
    pub job: String,
    /// Seconds since the job's last activity.
    pub last_progress_age_seconds: i64,
}

/// The watchdog tick, seamed as a trait so the parent can wire the
/// real `intel/watchdog.tick` at assembly.
///
/// The drill only needs: ticking a snapshot at a time yields the
/// alerts firing then (an empty vec when nothing fires). The trait
/// takes the snapshot by reference and never mutates it — the
/// Python watchdog likewise never touches job state.
pub trait WatchdogTick {
    /// Tick the snapshot at `now` (unix seconds); return firing alerts.
    fn tick(&self, snapshot: &Snapshot, now: i64) -> Vec<Alert>;
}

/// Standalone stand-in for the watchdog tick, used by [`run_drill`]
/// so the drill runs without the sibling watchdog module.
///
/// Mirrors the two detectors the drill's fixture can trip:
/// - WDG-002 presence-stall: a nick in caps, absent from presence,
///   holding a claimed job whose last activity is older than
///   [`STALL_MINUTES`].
/// - WDG-003 progress-stall: the same, but the nick IS present (a
///   worker that lives while its work does not move).
///
/// Last activity prefers `last_progress`, else `claimed_at` — the
/// order of Python `_last_activity` over the fields this fixture
/// carries (the full order also checks `progress_at`, `note_ts`,
/// and `last_progress_at`, which the fixture never sets). A job with
/// no timestamp at all yields no alert: the detector never invents
/// an age. A nick not in caps is a walk-on worker and is skipped by
/// both detectors. One alert per (nick, job) pair; a snapshot never
/// yields both kinds for the same job, by construction.
pub struct LocalWatchdog;

impl LocalWatchdog {
    /// Last known activity timestamp for a claimed job, or `None`.
    fn last_activity(job: &Job) -> Option<i64> {
        job.last_progress.or(job.claimed_at)
    }
}

impl WatchdogTick for LocalWatchdog {
    fn tick(&self, snapshot: &Snapshot, now: i64) -> Vec<Alert> {
        let mut alerts = Vec::new();
        for job in &snapshot.jobs {
            if job.status != "claimed" {
                continue;
            }
            let nick = match &job.claim {
                Some(nick) => nick,
                None => continue,
            };
            if !snapshot.caps.iter().any(|cap| cap == nick) {
                continue;
            }
            let last = match Self::last_activity(job) {
                Some(last) => last,
                None => continue,
            };
            let age = now - last;
            let present = snapshot.presence.iter().any(|p| p == nick);
            if !present && age > STALL_MINUTES * 60 {
                alerts.push(Alert {
                    kind: "presence-stall".to_string(),
                    nick: nick.clone(),
                    job: job.id.clone(),
                    last_progress_age_seconds: age,
                });
            } else if present && age > PROGRESS_STALL_MINUTES * 60 {
                alerts.push(Alert {
                    kind: "progress-stall".to_string(),
                    nick: nick.clone(),
                    job: job.id.clone(),
                    last_progress_age_seconds: age,
                });
            }
        }
        alerts
    }
}

/// The announcement lines for an alert list.
///
/// SEAM mirror of `intel/watchdog.announcements_for` (WDG-015):
/// every critical alert yields exactly one line, in list order;
/// warnings and info records yield nothing. The drill's alerts are
/// critical, so each yields one line starting with `"ALERT:"`.
/// The full line format (alert id, explanation text) lives in the
/// watchdog module; the drill asserts only the count and the
/// `"ALERT:"` prefix, so this seam line carries kind, nick, and job
/// after the prefix. Lines are held, never posted: this module posts
/// nothing itself.
pub fn announcements_for(alerts: &[Alert]) -> Vec<String> {
    alerts
        .iter()
        .filter(|alert| alert.kind == "presence-stall" || alert.kind == "progress-stall")
        .map(|alert| {
            format!(
                "ALERT: {}: worker {} on job {} stalled",
                alert.kind, alert.nick, alert.job
            )
        })
        .collect()
}

/// A fixture worker: claims, heartbeats, posts progress, dies.
///
/// It edits the snapshot in place, the way the real worker's actions
/// would change the live snapshot the next tick reads. Killing it
/// means exactly one thing: presence stops and heartbeats stop. It
/// never deletes its own job — a dead worker's job is the sweep's
/// problem, not its own.
#[derive(Clone, Debug, PartialEq)]
pub struct FakeWorker {
    /// Worker nick.
    pub nick: String,
    /// Whether the worker is alive. Set to `false` by [`FakeWorker::kill`].
    pub alive: bool,
}

impl FakeWorker {
    /// Create a live fixture worker.
    pub fn new(nick: &str) -> Self {
        FakeWorker {
            nick: nick.to_string(),
            alive: true,
        }
    }

    /// Claim a job into the snapshot and heartbeat immediately.
    ///
    /// The new job carries the demo title, status `"claimed"`, the
    /// worker as claim, `claimed_at = now`, the default lease, and
    /// `lease_until = now + lease`. Returns a copy of the new job.
    pub fn claim(&self, snapshot: &mut Snapshot, job_id: &str, now: i64) -> Job {
        let job = Job {
            id: job_id.to_string(),
            title: "demo job".to_string(),
            status: "claimed".to_string(),
            claim: Some(self.nick.clone()),
            claim_host: None,
            claimed_at: Some(now),
            lease: Some(LEASE_DEFAULT_SECONDS),
            lease_until: Some(now + LEASE_DEFAULT_SECONDS),
            last_heartbeat: None,
            last_progress: None,
        };
        snapshot.jobs.push(job);
        self.heartbeat(snapshot, now);
        snapshot.jobs.last().expect("just pushed").clone()
    }

    /// Heartbeat: join presence (if absent) and stamp
    /// `last_heartbeat` on every job this worker claims.
    ///
    /// Ported oddity: this does not check `alive`, exactly like
    /// Python — a dead worker heartbeats again only if the caller
    /// keeps calling it, which the drill never does after the kill.
    pub fn heartbeat(&self, snapshot: &mut Snapshot, now: i64) {
        if !snapshot.presence.iter().any(|p| p == &self.nick) {
            snapshot.presence.push(self.nick.clone());
        }
        for job in snapshot.jobs.iter_mut() {
            if job.claim.as_deref() == Some(self.nick.as_str()) {
                job.last_heartbeat = Some(now);
            }
        }
    }

    /// Post one progress note: stamp `last_progress` on every job
    /// this worker claims, and append the message to the snapshot.
    pub fn progress(&self, snapshot: &mut Snapshot, now: i64, text: &str) {
        for job in snapshot.jobs.iter_mut() {
            if job.claim.as_deref() == Some(self.nick.as_str()) {
                job.last_progress = Some(now);
            }
        }
        snapshot.messages.push(Message {
            nick: self.nick.clone(),
            text: text.to_string(),
        });
    }

    /// Stop heartbeats and drop out of presence, mid-job.
    ///
    /// Idempotent: killing an already-dead or already-absent worker
    /// is a no-op beyond setting `alive = false`. The job is left
    /// untouched — claimed, with its claim fields intact — for the
    /// sweep.
    pub fn kill(&mut self, snapshot: &mut Snapshot) {
        self.alive = false;
        snapshot.presence.retain(|p| p != &self.nick);
    }
}

/// Fixture mirror of `jobs.py` `_claim_or_requeue`'s requeue rule.
///
/// A claimed job whose `lease_until` has passed reopens: status back
/// to `"open"`, claim fields cleared (`claim`, `claim_host`,
/// `claimed_at`, `lease_until` — exactly the fields `jobs.py`
/// `_requeue_fields` deletes). A claimed job whose lease still holds
/// is left untouched, as is any non-claimed job and any claimed job
/// with no (numeric) lease deadline. The boundary is strict in the
/// lease's favour only before expiry: `now < lease_until` keeps the
/// job claimed, so `now == lease_until` requeues. Returns the
/// requeued job ids, in board order.
///
/// Note what is NOT cleared: `lease` itself survives (see [`Job`]),
/// and `last_heartbeat` / `last_progress` are untouched — the
/// requeued job keeps its history for the next worker.
pub fn sweep_expired_leases(snapshot: &mut Snapshot, now: i64) -> Vec<String> {
    let mut requeued = Vec::new();
    for job in snapshot.jobs.iter_mut() {
        if job.status != "claimed" {
            continue;
        }
        let lease_until = match job.lease_until {
            Some(lease_until) => lease_until,
            None => continue,
        };
        if now < lease_until {
            continue;
        }
        job.claim = None;
        job.claim_host = None;
        job.claimed_at = None;
        job.lease_until = None;
        job.status = "open".to_string();
        requeued.push(job.id.clone());
    }
    requeued
}

/// The drill report: the phase-2 alert, the phase-4 requeued ids, and
/// the phase log, so callers can assert on the drill's outcome
/// without parsing stdout (mirroring Python `run_drill`'s return).
#[derive(Clone, Debug, PartialEq)]
pub struct Report {
    /// The exactly-one phase-2 presence-stall alert.
    pub alert: Alert,
    /// Job ids requeued in phase 4.
    pub requeued: Vec<String>,
    /// One log line per phase, in order.
    pub log: Vec<String>,
}

/// Run every phase against a watchdog implementation; fail with a
/// message on any failed assertion.
///
/// Mirrors Python `run_drill`, which raises `AssertionError` on any
/// failure; here a failure is `Err(message)`. All ages are computed
/// from the threshold constants, not fixed numbers.
///
/// - Phase 1: healthy worker (claim, one progress note, beats) yields
///   zero alerts.
/// - Phase 2: the kill (heartbeats stop, presence goes dark) yields
///   exactly one presence-stall alert naming nick, job, and
///   last-progress age, with one held (not posted) announcement line.
/// - Phase 3: the sweep must NOT requeue before the lease ends.
/// - Phase 4: lease expiry requeues the job, and a re-tick yields
///   zero alerts — the alert auto-resolves and the job is open for
///   the next worker.
pub fn run_drill_with<W: WatchdogTick>(watchdog: &W) -> Result<Report, String> {
    let mut log = Vec::new();
    let mut snapshot = Snapshot {
        messages: Vec::new(),
        jobs: Vec::new(),
        presence: Vec::new(),
        caps: vec![NICK.to_string()],
    };
    let mut worker = FakeWorker::new(NICK);

    // Phase 1 — healthy worker: claim, one progress note, beats.
    let job = worker.claim(&mut snapshot, JOB_ID, T0);
    worker.progress(&mut snapshot, T0 + 120, "working on it");
    worker.heartbeat(&mut snapshot, T0 + 300);
    let got = watchdog.tick(&snapshot, T0 + 300);
    if !got.is_empty() {
        return Err(format!("healthy worker must yield zero alerts, got {got:?}"));
    }
    log.push("phase 1: healthy worker yields zero alerts".to_string());

    // Phase 2 — the kill: heartbeats stop, presence goes dark.
    worker.kill(&mut snapshot);
    if snapshot.presence.contains(&NICK.to_string()) {
        return Err("killed worker must leave presence".to_string());
    }
    let stall_at = T0 + 300 + STALL_MINUTES * 60 + 61;
    let got = watchdog.tick(&snapshot, stall_at);
    if got.len() != 1 {
        return Err(format!(
            "dead worker must yield exactly one alert, got {}: {got:?}",
            got.len()
        ));
    }
    let alert = got[0].clone();
    if alert.kind != "presence-stall" {
        return Err(format!("alert kind must be presence-stall, got {alert:?}"));
    }
    if alert.nick != NICK {
        return Err(format!("alert nick must be {NICK}, got {alert:?}"));
    }
    if alert.job != JOB_ID {
        return Err(format!("alert job must be {JOB_ID}, got {alert:?}"));
    }
    let expected_age = stall_at - (T0 + 120);
    if alert.last_progress_age_seconds != expected_age {
        return Err(format!(
            "alert last_progress_age_seconds must be {expected_age}, got {alert:?}"
        ));
    }
    let lines = announcements_for(&got);
    if lines.len() != 1 || !lines[0].starts_with("ALERT:") {
        return Err(format!(
            "exactly one announcement line starting with ALERT: expected, got {lines:?}"
        ));
    }
    log.push(format!(
        "phase 2: presence-stall alert names {NICK}/{JOB_ID}, age {expected_age}s; \
         announcement line held, not posted"
    ));

    // Phase 3 — the sweep must NOT requeue before the lease ends.
    if !sweep_expired_leases(&mut snapshot, stall_at).is_empty() {
        return Err("unexpired lease must not requeue".to_string());
    }
    let job_after_phase3 = snapshot
        .jobs
        .iter()
        .find(|j| j.id == JOB_ID)
        .ok_or("job missing after phase 3")?;
    if job_after_phase3.status != "claimed" {
        return Err("unexpired lease must stay claimed".to_string());
    }
    let _ = job;
    log.push("phase 3: unexpired lease stays claimed (no early requeue)".to_string());

    // Phase 4 — lease expires, sweep requeues, alert auto-resolves.
    let requeue_at = T0 + LEASE_DEFAULT_SECONDS + 1;
    let requeued = sweep_expired_leases(&mut snapshot, requeue_at);
    if requeued != vec![JOB_ID.to_string()] {
        return Err(format!("requeue must yield [{JOB_ID}], got {requeued:?}"));
    }
    let job_after = snapshot
        .jobs
        .iter()
        .find(|j| j.id == JOB_ID)
        .ok_or("job missing after phase 4")?;
    if job_after.status != "open" {
        return Err("requeued job must be open".to_string());
    }
    if job_after.claim.is_some() || job_after.lease_until.is_some() {
        return Err("requeued job must have claim and lease_until cleared".to_string());
    }
    let got = watchdog.tick(&snapshot, requeue_at);
    if !got.is_empty() {
        return Err(format!("requeued job must stop firing, got {got:?}"));
    }
    log.push(
        "phase 4: lease expiry requeues job; re-tick yields zero alerts, job open for the next worker"
            .to_string(),
    );

    Ok(Report {
        alert,
        requeued,
        log,
    })
}

/// Run every phase against the standalone watchdog stand-in.
///
/// See [`run_drill_with`] for the phase contract. At assembly the
/// parent may call [`run_drill_with`] with the real watchdog instead.
pub fn run_drill() -> Result<Report, String> {
    run_drill_with(&LocalWatchdog)
}

/// Mirror of the Python script's `main` reporting shape, without
/// printing: returns the process exit code and the stdout lines.
///
/// Success: exit 0, one line per phase plus a `PASS` line. Failure:
/// exit 1, a single `FAIL` line carrying the message. The caller owns
/// printing the lines and exiting with the code.
pub fn run_drill_stdout() -> (i32, Vec<String>) {
    match run_drill() {
        Ok(report) => {
            let mut lines: Vec<String> = report
                .log
                .iter()
                .map(|line| format!("kill_worker drill: {line}"))
                .collect();
            lines.push("kill_worker drill: PASS".to_string());
            (0, lines)
        }
        Err(message) => (1, vec![format!("kill_worker drill: FAIL: {message}")]),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn healthy_snapshot() -> (Snapshot, FakeWorker) {
        let mut snapshot = Snapshot {
            messages: Vec::new(),
            jobs: Vec::new(),
            presence: Vec::new(),
            caps: vec![NICK.to_string()],
        };
        let worker = FakeWorker::new(NICK);
        worker.claim(&mut snapshot, JOB_ID, T0);
        worker.progress(&mut snapshot, T0 + 120, "working on it");
        worker.heartbeat(&mut snapshot, T0 + 300);
        (snapshot, worker)
    }

    fn claimed_job(lease_until: Option<i64>) -> Job {
        Job {
            id: JOB_ID.to_string(),
            title: "demo job".to_string(),
            status: "claimed".to_string(),
            claim: Some(NICK.to_string()),
            claim_host: Some("host-a".to_string()),
            claimed_at: Some(T0),
            lease: Some(LEASE_DEFAULT_SECONDS),
            lease_until,
            last_heartbeat: Some(T0 + 300),
            last_progress: Some(T0 + 120),
        }
    }

    // --- The drill itself (mirrors kill_worker.py run_drill phases) ---

    #[test]
    fn test_run_drill_passes_all_phases() {
        let report = run_drill().expect("drill must pass");
        assert_eq!(report.alert.kind, "presence-stall");
        assert_eq!(report.alert.nick, NICK);
        assert_eq!(report.alert.job, JOB_ID);
        let stall_at = T0 + 300 + STALL_MINUTES * 60 + 61;
        assert_eq!(
            report.alert.last_progress_age_seconds,
            stall_at - (T0 + 120)
        );
        assert_eq!(report.requeued, vec![JOB_ID.to_string()]);
        assert_eq!(report.log.len(), 4);
        assert!(report.log[0].starts_with("phase 1"));
        assert!(report.log[1].starts_with("phase 2"));
        assert!(report.log[2].starts_with("phase 3"));
        assert!(report.log[3].starts_with("phase 4"));
    }

    #[test]
    fn test_run_drill_stdout_reports_pass_and_exit_0() {
        let (code, lines) = run_drill_stdout();
        assert_eq!(code, 0);
        assert_eq!(lines.len(), 5);
        assert_eq!(lines[4], "kill_worker drill: PASS");
        assert!(lines[0].starts_with("kill_worker drill: phase 1"));
    }

    #[test]
    fn test_phase1_healthy_worker_yields_zero_alerts() {
        let (snapshot, _) = healthy_snapshot();
        let got = LocalWatchdog.tick(&snapshot, T0 + 300);
        assert!(got.is_empty(), "healthy worker must yield zero alerts");
    }

    #[test]
    fn test_phase2_kill_yields_exactly_one_presence_stall() {
        let (mut snapshot, mut worker) = healthy_snapshot();
        worker.kill(&mut snapshot);
        assert!(!snapshot.presence.contains(&NICK.to_string()));
        assert!(!worker.alive);
        let stall_at = T0 + 300 + STALL_MINUTES * 60 + 61;
        let got = LocalWatchdog.tick(&snapshot, stall_at);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "presence-stall");
        assert_eq!(got[0].nick, NICK);
        assert_eq!(got[0].job, JOB_ID);
        assert_eq!(got[0].last_progress_age_seconds, stall_at - (T0 + 120));
        let lines = announcements_for(&got);
        assert_eq!(lines.len(), 1);
        assert!(lines[0].starts_with("ALERT:"));
    }

    #[test]
    fn test_phase3_unexpired_lease_stays_claimed() {
        let (mut snapshot, mut worker) = healthy_snapshot();
        worker.kill(&mut snapshot);
        let stall_at = T0 + 300 + STALL_MINUTES * 60 + 61;
        assert!(sweep_expired_leases(&mut snapshot, stall_at).is_empty());
        assert_eq!(snapshot.jobs[0].status, "claimed");
        assert_eq!(snapshot.jobs[0].claim.as_deref(), Some(NICK));
    }

    #[test]
    fn test_phase4_lease_expiry_requeues_and_alert_resolves() {
        let (mut snapshot, mut worker) = healthy_snapshot();
        worker.kill(&mut snapshot);
        let requeue_at = T0 + LEASE_DEFAULT_SECONDS + 1;
        let requeued = sweep_expired_leases(&mut snapshot, requeue_at);
        assert_eq!(requeued, vec![JOB_ID.to_string()]);
        assert_eq!(snapshot.jobs[0].status, "open");
        assert!(snapshot.jobs[0].claim.is_none());
        assert!(snapshot.jobs[0].lease_until.is_none());
        let got = LocalWatchdog.tick(&snapshot, requeue_at);
        assert!(got.is_empty(), "requeued job must stop firing");
    }

    // --- FakeWorker edge cases (from kill_worker.py's own behavior) ---

    #[test]
    fn test_claim_sets_lease_fields_and_presence() {
        let mut snapshot = Snapshot::default();
        let worker = FakeWorker::new(NICK);
        let job = worker.claim(&mut snapshot, JOB_ID, T0);
        assert_eq!(job.status, "claimed");
        assert_eq!(job.claim.as_deref(), Some(NICK));
        assert_eq!(job.claimed_at, Some(T0));
        assert_eq!(job.lease, Some(LEASE_DEFAULT_SECONDS));
        assert_eq!(job.lease_until, Some(T0 + LEASE_DEFAULT_SECONDS));
        assert_eq!(job.last_heartbeat, Some(T0));
        assert!(snapshot.presence.contains(&NICK.to_string()));
        assert_eq!(snapshot.jobs.len(), 1);
    }

    #[test]
    fn test_heartbeat_is_idempotent_on_presence_and_scoped_to_own_jobs() {
        let mut snapshot = Snapshot::default();
        let worker = FakeWorker::new(NICK);
        worker.claim(&mut snapshot, JOB_ID, T0);
        // Another worker's job must not get this worker's heartbeat.
        snapshot.jobs.push(Job {
            id: "8".to_string(),
            title: "other job".to_string(),
            status: "claimed".to_string(),
            claim: Some("hana".to_string()),
            claim_host: None,
            claimed_at: Some(T0),
            lease: None,
            lease_until: None,
            last_heartbeat: None,
            last_progress: None,
        });
        worker.heartbeat(&mut snapshot, T0 + 50);
        assert_eq!(
            snapshot.presence.iter().filter(|p| p.as_str() == NICK).count(),
            1,
            "presence must hold the nick exactly once"
        );
        assert_eq!(snapshot.jobs[1].last_heartbeat, None);
    }

    #[test]
    fn test_progress_stamps_only_own_jobs_and_posts_message() {
        let mut snapshot = Snapshot::default();
        let worker = FakeWorker::new(NICK);
        worker.claim(&mut snapshot, JOB_ID, T0);
        snapshot.jobs.push(Job {
            id: "8".to_string(),
            title: "other job".to_string(),
            status: "claimed".to_string(),
            claim: Some("hana".to_string()),
            claim_host: None,
            claimed_at: Some(T0),
            lease: None,
            lease_until: None,
            last_heartbeat: None,
            last_progress: None,
        });
        worker.progress(&mut snapshot, T0 + 120, "working on it");
        assert_eq!(snapshot.jobs[0].last_progress, Some(T0 + 120));
        assert_eq!(snapshot.jobs[1].last_progress, None);
        assert_eq!(snapshot.messages.len(), 1);
        assert_eq!(snapshot.messages[0].nick, NICK);
        assert_eq!(snapshot.messages[0].text, "working on it");
    }

    #[test]
    fn test_kill_is_idempotent_and_leaves_job_untouched() {
        let (mut snapshot, mut worker) = healthy_snapshot();
        worker.kill(&mut snapshot);
        let after_first = snapshot.clone();
        worker.kill(&mut snapshot);
        assert_eq!(snapshot, after_first, "second kill must change nothing");
        assert_eq!(snapshot.jobs[0].status, "claimed");
        assert_eq!(snapshot.jobs[0].claim.as_deref(), Some(NICK));
        assert!(snapshot.jobs[0].lease_until.is_some());
    }

    #[test]
    fn test_kill_when_absent_is_a_noop() {
        let mut snapshot = Snapshot::default();
        let mut worker = FakeWorker::new(NICK);
        worker.kill(&mut snapshot);
        assert!(!worker.alive);
        assert!(snapshot.presence.is_empty());
    }

    // --- Sweep edge cases (from jobs.py _claim_or_requeue via the drill) ---

    #[test]
    fn test_sweep_boundary_now_equals_lease_until_requeues() {
        let mut snapshot = Snapshot {
            jobs: vec![claimed_job(Some(T0 + LEASE_DEFAULT_SECONDS))],
            caps: vec![NICK.to_string()],
            ..Snapshot::default()
        };
        // One second before expiry: untouched.
        assert!(sweep_expired_leases(&mut snapshot, T0 + LEASE_DEFAULT_SECONDS - 1)
            .is_empty());
        assert_eq!(snapshot.jobs[0].status, "claimed");
        // Exactly at expiry: requeues (Python keeps only now < lease_until).
        let requeued = sweep_expired_leases(&mut snapshot, T0 + LEASE_DEFAULT_SECONDS);
        assert_eq!(requeued, vec![JOB_ID.to_string()]);
        assert_eq!(snapshot.jobs[0].status, "open");
    }

    #[test]
    fn test_sweep_clears_exactly_the_requeue_fields() {
        let mut snapshot = Snapshot {
            jobs: vec![claimed_job(Some(T0 + 10))],
            ..Snapshot::default()
        };
        let requeued = sweep_expired_leases(&mut snapshot, T0 + 11);
        assert_eq!(requeued, vec![JOB_ID.to_string()]);
        let job = &snapshot.jobs[0];
        assert!(job.claim.is_none());
        assert!(job.claim_host.is_none());
        assert!(job.claimed_at.is_none());
        assert!(job.lease_until.is_none());
        // Ported oddity: lease itself survives, as do heartbeat/progress.
        assert_eq!(job.lease, Some(LEASE_DEFAULT_SECONDS));
        assert_eq!(job.last_heartbeat, Some(T0 + 300));
        assert_eq!(job.last_progress, Some(T0 + 120));
    }

    #[test]
    fn test_sweep_skips_open_jobs_and_jobs_without_lease() {
        let mut snapshot = Snapshot {
            jobs: vec![
                Job {
                    status: "open".to_string(),
                    ..claimed_job(Some(T0 + 10))
                },
                Job {
                    id: "9".to_string(),
                    ..claimed_job(None)
                },
            ],
            ..Snapshot::default()
        };
        assert!(sweep_expired_leases(&mut snapshot, T0 + 100).is_empty());
        assert_eq!(snapshot.jobs[0].status, "open");
        assert_eq!(snapshot.jobs[1].status, "claimed");
        assert_eq!(snapshot.jobs[1].claim.as_deref(), Some(NICK));
    }

    #[test]
    fn test_sweep_requeues_in_board_order() {
        let mut snapshot = Snapshot {
            jobs: vec![
                claimed_job(Some(T0 + 10)),
                Job {
                    id: "8".to_string(),
                    ..claimed_job(Some(T0 + 20))
                },
            ],
            ..Snapshot::default()
        };
        let requeued = sweep_expired_leases(&mut snapshot, T0 + 100);
        assert_eq!(requeued, vec![JOB_ID.to_string(), "8".to_string()]);
    }

    // --- LocalWatchdog seam cases (WDG-002/WDG-003 as the drill needs them) ---

    #[test]
    fn test_present_worker_with_stale_progress_gets_progress_stall_not_presence() {
        let (snapshot, _) = healthy_snapshot();
        // Present, but progress unmoving past the progress window.
        let got = LocalWatchdog.tick(&snapshot, T0 + 120 + PROGRESS_STALL_MINUTES * 60 + 1);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "progress-stall");
    }

    #[test]
    fn test_no_alert_without_any_timestamp() {
        let mut snapshot = Snapshot {
            jobs: vec![Job {
                claimed_at: None,
                last_progress: None,
                ..claimed_job(Some(T0 + LEASE_DEFAULT_SECONDS))
            }],
            presence: Vec::new(),
            caps: vec![NICK.to_string()],
            ..Snapshot::default()
        };
        // Absent from presence, but no timestamp: never invent an age.
        assert!(LocalWatchdog.tick(&snapshot, T0 + 100_000).is_empty());
        snapshot.presence.push(NICK.to_string());
        assert!(LocalWatchdog.tick(&snapshot, T0 + 100_000).is_empty());
    }

    #[test]
    fn test_walk_on_claimer_not_in_caps_is_skipped() {
        let (mut snapshot, _) = healthy_snapshot();
        snapshot.caps.clear();
        let got = LocalWatchdog.tick(&snapshot, T0 + 100_000);
        assert!(got.is_empty(), "a nick not in caps is tracked, not alerted");
    }

    #[test]
    fn test_stall_boundary_is_strict() {
        let (mut snapshot, mut worker) = healthy_snapshot();
        worker.kill(&mut snapshot);
        // Age exactly STALL_MINUTES * 60: not a stall.
        let at_boundary = T0 + 120 + STALL_MINUTES * 60;
        assert!(LocalWatchdog.tick(&snapshot, at_boundary).is_empty());
        // One second past: stalls.
        let got = LocalWatchdog.tick(&snapshot, at_boundary + 1);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].kind, "presence-stall");
    }

    #[test]
    fn test_announcements_only_for_critical_alerts() {
        let alerts = vec![
            Alert {
                kind: "presence-stall".to_string(),
                nick: NICK.to_string(),
                job: JOB_ID.to_string(),
                last_progress_age_seconds: 841,
            },
            Alert {
                kind: "worker-restart".to_string(),
                nick: NICK.to_string(),
                job: JOB_ID.to_string(),
                last_progress_age_seconds: 0,
            },
        ];
        let lines = announcements_for(&alerts);
        assert_eq!(lines.len(), 1);
        assert!(lines[0].starts_with("ALERT:"));
    }

    #[test]
    fn test_drill_accepts_an_injected_watchdog() {
        // The seam: run_drill_with works with any WatchdogTick, so the
        // parent can wire the real watchdog without touching drill logic.
        struct Silent;
        impl WatchdogTick for Silent {
            fn tick(&self, _snapshot: &Snapshot, _now: i64) -> Vec<Alert> {
                Vec::new()
            }
        }
        let result = run_drill_with(&Silent);
        assert!(
            result.is_err(),
            "a silent watchdog must fail phase 2, proving the drill really ticks it"
        );
    }
}
