//! B20 drills, ported as in-process phase runners.
//!
//! - `intel/drills/budget_forecast.py` (OS-091, 5 phases)
//! - `intel/drills/budget_gate.py` (OS-085, 4 phases)
//! - `intel/drills/cgroup_limits.py` (OS-035 file/verify/gate
//!   phases; enforcement needs a live cgroup host and stays
//!   environment-gated, exactly like the Python drill's
//!   ENVIRONMENT-BLOCKED verdict)
//!
//! Each drill's `run_*` returns the phase log; tests assert the
//! same PASS conditions the Python `test_drill_passes` cases pin
//! by running the scripts as subprocesses.

use serde_json::{json, Value};

use crate::brief_budget::memory_budget_lines;
use crate::budgets::{claim_allowed, hold_entry, BUDGET_WARN_PERCENT};
use crate::forecast::{forecast_entry, forecast_lines, preempt_decision, preempt_record};
#[cfg(test)]
use crate::budgets::at_warning;
#[cfg(test)]
use crate::forecast::{confidence_for, project_end_of_day};
use crate::watch_budget::detect_budget_warning;

// --- budget_forecast drill (OS-091, 5 phases) ---

/// Run the forecast drill phases; returns the phase log.
/// Raises (Err) on any failed phase, like the Python drill's
/// `sys.exit(1)` on the first failed `_check`.
pub fn run_budget_forecast() -> Result<Vec<String>, String> {
    let mut log = Vec::new();
    let lane = json!({"lane": "spark", "spent": 80, "cap": 100});
    let state = crate::budgets::budget_state(&lane);
    if state != "warning" {
        return Err(format!("warning lane state, got {state}"));
    }
    // Phase 1: forecast.
    let entry = forecast_entry("spark", 80.0, 100.0, 8.0, 24.0)
        .ok_or_else(|| "no forecast for 80/100/8h".to_string())?;
    if entry.projected != 240.0 {
        return Err(format!("forecast projects {}, want 240", entry.projected));
    }
    if !entry.over_cap {
        return Err("forecast must flag the breach".to_string());
    }
    if entry.confidence != "medium" {
        return Err(format!("confidence {}, want medium", entry.confidence));
    }
    if !entry.basis.contains("8 hours of ledger") {
        return Err(format!("basis names the 8 hours, got {}", entry.basis));
    }
    log.push("phase 1: forecast 240, breach, medium, 8-hour basis".to_string());
    // Phase 2: preempt the low-priority running job, progress kept.
    let low_job = json!({"id": "job-low", "priority": "low", "status": "running", "progress": "step 3 of 5 done"});
    if preempt_decision(&low_job, state) != Some("pause") {
        return Err("low-priority running job must pause".to_string());
    }
    let record = preempt_record("job-low", "spark", "paused", "lane at warning, low priority");
    if record["job"] != json!("job-low") || record["lane"] != json!("spark") || record["action"] != json!("paused") {
        return Err("pause journal record must name job, lane, action".to_string());
    }
    log.push("phase 2: low-priority running job pauses, progress kept".to_string());
    // Phase 3: high-priority work is never preempted.
    let high_job = json!({"id": "job-high", "priority": "high", "status": "running", "progress": "step 1 of 2 done"});
    if preempt_decision(&high_job, state).is_some() {
        return Err("high-priority job must be untouched".to_string());
    }
    log.push("phase 3: high-priority job untouched".to_string());
    // Phase 4: budget frees, the paused job resumes cleanly.
    let freed = crate::budgets::budget_state(&json!({"lane": "spark", "spent": 10, "cap": 100}));
    if freed != "ok" {
        return Err(format!("freed lane state, got {freed}"));
    }
    let paused = json!({"id": "job-low", "priority": "low", "status": "paused", "progress": "step 3 of 5 done"});
    if preempt_decision(&paused, freed) != Some("resume") {
        return Err("paused job must resume when budget frees".to_string());
    }
    log.push("phase 4: freed budget resumes the paused job, progress kept".to_string());
    // Phase 5: brief lines.
    let lines = forecast_lines(&json!([{"lane": "spark", "spent": 80, "cap": 100, "elapsed_hours": 8}]));
    if lines.len() != 1 {
        return Err(format!("one forecast brief line, got {lines:?}"));
    }
    let line = &lines[0];
    for needle in [
        "Budget forecast for lane spark: 80 spent of 100 cap, projected 240 by end of day",
        "8 hours of ledger",
        "medium confidence",
        "breach expected before end of day",
    ] {
        if !line.contains(needle) {
            return Err(format!("brief line misses {needle:?}: {line}"));
        }
    }
    if line.trim_start().starts_with('-') || line.trim_start().starts_with('*') {
        return Err(format!("brief line must not be a bullet: {line}"));
    }
    log.push("phase 5: forecast brief line names figures, basis, verdict".to_string());
    Ok(log)
}

// --- budget_gate drill (OS-085, 4 phases) ---

struct FakeQueue {
    jobs: std::collections::BTreeMap<String, String>,
    holds: Vec<String>,
}

impl FakeQueue {
    fn new() -> Self {
        FakeQueue {
            jobs: std::collections::BTreeMap::new(),
            holds: Vec::new(),
        }
    }

    fn post(&mut self, job_id: &str) {
        self.jobs.insert(job_id.to_string(), "open".to_string());
    }

    /// Mirrors jobs.py claim semantics: a granted claim marks the
    /// job claimed; a refused claim leaves the job open and records
    /// the hold. The gate is budgets.claim_allowed — never
    /// re-implemented here.
    fn claim(&mut self, job_id: &str, spent: i64, cap: i64) -> bool {
        if !claim_allowed(spent, cap) {
            self.holds.push(job_id.to_string());
            return false;
        }
        self.jobs.insert(job_id.to_string(), "claimed".to_string());
        true
    }
}

fn snapshot(spent: i64, cap: i64) -> Value {
    json!({"jobs": [], "messages": [], "presence": [], "caps": {},
           "budgets": [{"lane": "spark", "spent": spent, "cap": cap}]})
}

/// Run the budget-gate drill phases; returns the phase log.
pub fn run_budget_gate() -> Result<Vec<String>, String> {
    let mut log = Vec::new();
    let mut queue = FakeQueue::new();
    queue.post("1");
    // Phase 1: under the warning threshold — quiet, claims flow.
    if !detect_budget_warning(&snapshot(70, 100), 100_000, BUDGET_WARN_PERCENT).is_empty() {
        return Err("70 of 100 must yield no budget warning".to_string());
    }
    if !queue.claim("1", 70, 100) {
        return Err("claim under cap must be granted".to_string());
    }
    if queue.jobs["1"] != "claimed" {
        return Err("claimed job must read claimed".to_string());
    }
    log.push("phase 1 — 70/100: no warning, claim granted".to_string());
    // Phase 2: at the warning threshold — exactly one warning, and
    // claims still flow.
    let warnings = detect_budget_warning(&snapshot(80, 100), 100_000, BUDGET_WARN_PERCENT);
    if warnings.len() != 1 {
        return Err(format!("80 of 100 must yield exactly one warning, got {}", warnings.len()));
    }
    let alert = &warnings[0];
    if alert.severity != "warning" || alert.lane != "spark" || alert.spent != 80 || alert.cap != 100 {
        return Err("warning must name spark, 80 of 100".to_string());
    }
    if !alert.explanation.contains("spark") || !alert.explanation.contains("80") {
        return Err("warning explanation must name lane and figure".to_string());
    }
    if alert.dedupe_key != "budget-warning:spark" {
        return Err("dedupe key must be budget-warning:spark".to_string());
    }
    queue.post("2");
    if !queue.claim("2", 80, 100) {
        return Err("claim at warning threshold must still be granted".to_string());
    }
    log.push("phase 2 — 80/100: one budget-warning alert (spark, 80 of 100), claim still granted".to_string());
    // Phase 3: at cap — no warning, the claim is held, the job
    // stays open, and the brief's budget line says so.
    if !detect_budget_warning(&snapshot(100, 100), 100_000, BUDGET_WARN_PERCENT).is_empty() {
        return Err("100 of 100 must yield no warning — the hold replaces it".to_string());
    }
    queue.post("3");
    if queue.claim("3", 100, 100) {
        return Err("claim at cap must be held".to_string());
    }
    if queue.jobs["3"] != "open" {
        return Err("a held claim leaves the job open".to_string());
    }
    if queue.holds != vec!["3".to_string()] {
        return Err("hold must be recorded".to_string());
    }
    let lines = memory_budget_lines(&json!({"budgets": [hold_entry("spark", 100, 100)]}));
    let held: Vec<&String> = lines.iter().filter(|l| l.contains("spark")).collect();
    if held.len() != 1 || !held[0].contains("new claims held") {
        return Err(format!("brief line must name the hold, got {lines:?}"));
    }
    log.push(format!("phase 3 — 100/100: no warning, claim held, job stays open, brief line reads: {}", held[0]));
    // Phase 4: unbudgeted and malformed entries never warn, never
    // hold, never crash.
    let malformed = json!({"budgets": [{"lane": "unbudgeted"}]});
    if !detect_budget_warning(&malformed, 100_000, BUDGET_WARN_PERCENT).is_empty() {
        return Err("a lane with no cap must not warn".to_string());
    }
    // Unbudgeted lanes always allow claims (the typed API's
    // zero-cap rule agrees: no usable cap is never at cap).
    assert!(claim_allowed(0, 0));
    log.push("phase 4 — unbudgeted and malformed entries: no warning, no hold, no crash".to_string());
    Ok(log)
}

// --- cgroup-limits drill (OS-035, file/verify/gate phases) ---

pub const CGROUP_EXPECTED: &[(&str, &str)] = &[("CPUQuota", "100%"), ("MemoryMax", "1G")];
pub const RELAY_WORKERS_SLICE: &str = "os/services/relay-workers.slice";

/// Parse the `[Slice]` section of a systemd slice file.
/// Mirrors the drill's `parse_slice`.
pub fn parse_slice(text: &str) -> std::collections::BTreeMap<String, String> {
    let mut values = std::collections::BTreeMap::new();
    let mut section = String::new();
    for line in text.lines() {
        let line = line.trim();
        if line.starts_with('[') && line.ends_with(']') {
            section = line[1..line.len() - 1].to_string();
            continue;
        }
        if section == "Slice" {
            if let Some(eq) = line.find('=') {
                values.insert(line[..eq].trim().to_string(), line[eq + 1..].trim().to_string());
            }
        }
    }
    values
}

/// The drill's file phase: the slice parses and carries exactly
/// the spec values.
pub fn cgroup_file_phase(slice_text: &str) -> Result<Vec<String>, String> {
    let values = parse_slice(slice_text);
    let mut log = Vec::new();
    for (key, want) in CGROUP_EXPECTED {
        let got = values.get(*key).cloned().unwrap_or_default();
        log.push(format!("file: {key}={got} (expected {want})"));
        if got != *want {
            return Err(format!("file: FAIL: {key} mismatch"));
        }
    }
    log.push("file: PASS".to_string());
    Ok(log)
}

/// The drill's gate phase: the host cgroup hierarchy must expose
/// the cpu and memory controllers, or live enforcement cannot
/// run. Returns `Ok(true)` when the gate passes, `Ok(false)`
/// with the ENVIRONMENT-BLOCKED verdict when it does not.
pub fn cgroup_gate_phase(controllers_text: Result<String, String>) -> Result<bool, String> {
    let text = match controllers_text {
        Ok(t) => t,
        Err(e) => {
            return Err(format!("gate: cannot read cgroup.controllers: {e}\ngate: ENVIRONMENT-BLOCKED"));
        }
    };
    let controllers: Vec<&str> = text.split_whitespace().collect();
    let missing: Vec<&&str> = ["cpu", "memory"]
        .iter()
        .filter(|c| !controllers.contains(c))
        .collect();
    if !missing.is_empty() {
        return Err(format!(
            "gate: missing controllers: {missing:?}\ngate: ENVIRONMENT-BLOCKED: live enforcement cannot run on this host"
        ));
    }
    Ok(true)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn forecast_drill_passes() {
        let log = run_budget_forecast().expect("forecast drill must pass");
        assert_eq!(log.len(), 5);
    }

    #[test]
    fn gate_drill_passes() {
        let log = run_budget_gate().expect("gate drill must pass");
        assert_eq!(log.len(), 4);
        assert!(log[0].contains("PASS phase 1") || log[0].contains("phase 1"));
        assert!(log[1].contains("phase 2"));
        assert!(log[2].contains("phase 3"));
        assert!(log[3].contains("phase 4"));
    }

    #[test]
    fn cgroup_file_phase_pins_slice_values() {
        let text = "[Slice]\nCPUQuota=100%\nMemoryMax=1G\n";
        let log = cgroup_file_phase(text).unwrap();
        assert!(log.last().unwrap().contains("PASS"));
        assert!(cgroup_file_phase("[Slice]\nCPUQuota=50%\n").is_err());
    }

    #[test]
    fn cgroup_gate_blocks_without_controllers() {
        // Empty controller set (this dev VM's shape): enforcement
        // is ENVIRONMENT-BLOCKED, the honest verdict, not a pass.
        assert!(cgroup_gate_phase(Ok(String::new())).is_err());
        assert!(cgroup_gate_phase(Ok("cpu memory".to_string())).unwrap());
    }

    #[test]
    fn preempt_math_spot_checks() {
        assert_eq!(project_end_of_day(80.0, 8.0, 24.0), Some(240.0));
        assert_eq!(confidence_for(8.0), "medium");
        assert!(at_warning(80, 100, 80));
    }
}
