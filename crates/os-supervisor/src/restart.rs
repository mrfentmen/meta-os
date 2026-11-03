//! Restart policy for a watched worker.
//!
//! The watchdog observes and reports; this module is the policy it consults
//! before a worker is put back. Three rules, each written down because a
//! policy that lives only in a caller's `if` is a policy nobody can check:
//!
//! 1. **Three strikes.** A worker that fails [`DEFAULT_MAX_FAILURES`] times in
//!    a window is marked [`WorkerState::Failed`] and is not restarted. A
//!    supervisor that keeps restarting a broken worker turns one failure into
//!    a storm.
//! 2. **Documented backoff.** Restart delays come from
//!    [`BACKOFF_SEQUENCE_SECS`], in order, and hold at the last entry instead
//!    of growing without bound.
//! 3. **Recovery resets.** A worker that runs again resets its failure count,
//!    so an old failure never counts against a later, healthy run.
//!
//! No clock is read here: every function is arithmetic on a counter, so the
//! policy is deterministic and testable without sleeping.

/// Failures in the window that mark a worker failed.
pub const DEFAULT_MAX_FAILURES: u32 = 3;

/// Restart delays in seconds, in the order they are used. The last entry is
/// the ceiling: a worker that keeps failing backs off to it and stays there.
pub const BACKOFF_SEQUENCE_SECS: &[u64] = &[1, 2, 4, 8, 16, 32, 60];

/// Where a worker is, as far as the policy is concerned.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WorkerState {
    /// Running, or healthy enough to be put back.
    Running,
    /// Failed at least once and still under the strike limit.
    Restarting,
    /// At the strike limit: not restarted again in this window.
    Failed,
}

/// A refusal to build a policy that could not restart anything.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PolicyError(pub String);

/// How many failures the supervisor tolerates before it stops restarting.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RestartPolicy {
    max_failures: u32,
}

impl Default for RestartPolicy {
    fn default() -> Self {
        Self { max_failures: DEFAULT_MAX_FAILURES }
    }
}

impl RestartPolicy {
    /// A policy with an explicit strike limit. Zero is refused: a supervisor
    /// that restarts nothing is not a policy, it is an outage with a name.
    pub fn new(max_failures: u32) -> Result<Self, PolicyError> {
        if max_failures == 0 {
            return Err(PolicyError("restart policy: max_failures must be at least 1".to_string()));
        }
        Ok(Self { max_failures })
    }

    pub fn max_failures(&self) -> u32 {
        self.max_failures
    }

    /// Delay before the `attempt`-th restart, one-based. Attempt 0 has no
    /// delay because nothing has failed yet; attempts past the table hold at
    /// the ceiling.
    pub fn backoff_secs(&self, attempt: u32) -> u64 {
        if attempt == 0 {
            return 0;
        }
        let last = BACKOFF_SEQUENCE_SECS.len() - 1;
        let index = (attempt as usize - 1).min(last);
        BACKOFF_SEQUENCE_SECS[index]
    }
}

/// One worker's health under a policy.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkerHealth {
    failures: u32,
    state: WorkerState,
}

impl Default for WorkerHealth {
    fn default() -> Self {
        Self { failures: 0, state: WorkerState::Running }
    }
}

impl WorkerHealth {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn failures(&self) -> u32 {
        self.failures
    }

    pub fn state(&self) -> WorkerState {
        self.state
    }

    /// Whether the supervisor may put this worker back. A failed worker is
    /// never restarted; an operator decides what happens to it instead.
    pub fn should_restart(&self) -> bool {
        self.state != WorkerState::Failed
    }

    /// Record one failure. Returns the backoff delay to wait before the next
    /// restart, or 0 when the worker just hit the strike limit and will not be
    /// restarted at all — a delay for a restart that never happens would be a
    /// number with no meaning.
    pub fn record_failure(&mut self, policy: &RestartPolicy) -> u64 {
        if self.state == WorkerState::Failed {
            return 0;
        }
        self.failures += 1;
        if self.failures >= policy.max_failures() {
            self.state = WorkerState::Failed;
            return 0;
        }
        self.state = WorkerState::Restarting;
        policy.backoff_secs(self.failures)
    }

    /// Record that the worker ran again. The count resets, so a worker that
    /// recovers is treated as healthy rather than as a worker with history.
    pub fn record_recovery(&mut self) {
        self.failures = 0;
        self.state = WorkerState::Running;
    }
}
