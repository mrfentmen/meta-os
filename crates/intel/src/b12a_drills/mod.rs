//! B12a — Evals & drills: drill and check code (`b12a_drills` subtree).
//!
//! Ports the 39 code files of B12a (behavior, not redesign):
//! top-level checks (`abrun`, `boot_audio_check`, `boot_selfcheck`,
//! `dem018_local_check`, `e2e1..3`, `final_mix_check`, `load_check`,
//! `redis_down_drill`, `sam_check`, `sam_render`, `security_pass`,
//! `soak_review`, `spark_down_drill`, `spoof_dispatch_drill`,
//! `evals/watchdog_tuning`) plus `drills/` (21 drill modules).
//!
//! Drill contract (mirrors every Python drill): fixture-only, no
//! network/Redis/bus; `run()` executes the named phases in order and
//! returns a [`DrillReport`]; the `PASS` line prints on success.
//! Eval records (`.md`/`.log`/`.png`) are B12b/B12c fixtures, not code.
//!
//! Port layout: plain-dict fixture data rides on [`value::Value`];
//! sibling-module surfaces owned by other batches (watchdog,
//! gate, store, brief, …) are the traits in [`deps`] — the same
//! seams the Python sources reach through patchable module
//! attributes. The subprocess check scripts share [`audiocheck`].

pub mod abrun;
pub mod audiocheck;
pub mod boot_audio_check;
pub mod boot_selfcheck;
pub mod dem018_local_check;
pub mod deps;
pub mod drills;
pub mod e2e1;
pub mod e2e2;
pub mod e2e3;
pub mod final_mix_check;
pub mod load_check;
pub mod redis_down_drill;
pub mod sam_check;
pub mod sam_render;
pub mod security_pass;
pub mod sha256;
pub mod soak_review;
pub mod spark_down_drill;
pub mod spoof_dispatch_drill;
pub mod value;
pub mod watchdog_tuning;

/// One named phase outcome.
#[derive(Debug, Clone, PartialEq)]
pub struct PhaseResult {
    pub name: String,
    pub pass: bool,
    pub detail: String,
}

impl PhaseResult {
    pub fn pass(name: &str, detail: impl Into<String>) -> Self {
        Self { name: name.to_string(), pass: true, detail: detail.into() }
    }
    pub fn fail(name: &str, detail: impl Into<String>) -> Self {
        Self { name: name.to_string(), pass: false, detail: detail.into() }
    }
}

/// Whole-drill report; mirrors the `PASS`/`FAIL` line convention.
#[derive(Debug, Clone, PartialEq)]
pub struct DrillReport {
    pub drill: String,
    pub phases: Vec<PhaseResult>,
}

impl DrillReport {
    pub fn new(drill: &str, phases: Vec<PhaseResult>) -> Self {
        Self { drill: drill.to_string(), phases }
    }
    pub fn ok(&self) -> bool {
        self.phases.iter().all(|p| p.pass)
    }
    pub fn pass_line(&self) -> String {
        if self.ok() {
            format!("{}: PASS ({} phases)", self.drill, self.phases.len())
        } else {
            let bad: Vec<&str> = self.phases.iter().filter(|p| !p.pass).map(|p| p.name.as_str()).collect();
            format!("{}: FAIL [{}]", self.drill, bad.join(", "))
        }
    }
}
