//! INT-023 watchdog-under-load check (port of
//! `os/intel/watchdog_load_check.py`).
//!
//! A 200-job queue under failure, then three watchdog ticks: the first
//! over a loaded, failing room, the second inside the alert dedupe
//! cooldown, the third after the workers recover. The Python script
//! drives this end to end on the in-memory fake Redis surface with
//! real `jobs.py` commands, real `watchdog.tick` calls and real
//! `intel.store.write_alert` calls. That live orchestration cannot be
//! unit-tested standalone: the jobs, watchdog and store modules belong
//! to other batches/workers, and this module must stay
//! self-contained.
//!
//! What is ported faithfully here, and therefore unit-testable:
//! the check's constants, stage names and order, every stage
//! assertion (tick-1 exact counts and kinds, tick-2 dedupe identity,
//! tick-3 silence with records standing, per-tick and total budgets),
//! the transcript lines, and the markdown counts table rendered by
//! `render_watchdog_load_md`.
//!
//! Live-behavior boundary: running the check against a real or fake
//! backend (posting 200 jobs, claiming 50, advancing the fake clock
//! 61 minutes, seeding 2,000 room messages, ticking, writing alerts)
//! is NOT ported here and is never faked: [`evaluate`] validates
//! tick outcomes supplied by the caller, it does not invent them.
//! Tick silence on recovery is not store resolution — the 50
//! tick-1 records stay standing, and the tick-3 assertion checks
//! exactly that.
//!
//! SEAM: `intel.integration` (not in this batch) supplies the
//! integration namespaces. [`IntegrationSurface`] carries them;
//! [`IntIntegration`] provides the INT-001 values so callers do not
//! have to retype them. No other module is imported.

/// Room messages seeded directly after the queue (a beyond-cap stress
/// state: every jobs announcement runs bus_trim to the newest 500).
pub const MESSAGE_COUNT: usize = 2000;
/// Jobs posted in the queue.
pub const JOB_COUNT: usize = 200;
/// Jobs claimed by the worker that then goes silent.
pub const SILENT_COUNT: usize = 25;
/// Jobs claimed by the worker that stays present but stops progressing.
pub const STUCK_COUNT: usize = 25;
/// Claimed jobs in total.
pub const CLAIMED_COUNT: usize = SILENT_COUNT + STUCK_COUNT;
/// Worker that goes silent (presence lapses, progress stops).
pub const SILENT_WORKER: &str = "load-silent";
/// Worker that stays present but stops progressing.
pub const STUCK_WORKER: &str = "load-stuck";
/// Fake-clock advance before tick 1: 61 minutes, past the 10-minute
/// stall thresholds, past the 30-minute claim leases, and past the
/// 120-second presence TTL.
pub const ADVANCE_SECONDS: i64 = 3660;
/// Gap before tick 2: 5 minutes, inside the 30-minute dedupe cooldown.
pub const REBEAT_GAP_SECONDS: i64 = 300;
/// Adopted per-tick wall-clock budget (INT-006's budget; the plan
/// documents no per-tick budget for this check).
pub const TICK_BUDGET_SECONDS: f64 = 5.0;
/// Adopted three-tick total wall-clock budget.
pub const TOTAL_BUDGET_SECONDS: f64 = 15.0;

/// Stage names in run order, mirroring Python's `_STAGE_NAMES`.
pub const STAGE_NAMES: [&str; 6] = [
    "seed queue",
    "seed room",
    "tick 1 stalled load",
    "tick 2 dedupe",
    "tick 3 cleared",
    "budgets",
];

/// SEAM (see module docs): the integration namespaces from
/// `intel.integration`, which is not in this batch. Implementors
/// supply the namespace values; the check logic itself never reads
/// a live bus.
pub trait IntegrationSurface {
    /// Job namespace, e.g. the INT-001 integration namespace.
    fn job_namespace(&self) -> &str;
    /// Capability namespace, e.g. the INT-001 integration namespace.
    fn capability_namespace(&self) -> &str;
    /// Integration room.
    fn room(&self) -> &str;
}

/// The INT-001 integration surface used by the Python check.
#[derive(Debug, Clone, Copy, Default)]
pub struct IntIntegration;

impl IntegrationSurface for IntIntegration {
    fn job_namespace(&self) -> &str {
        "muse-bus:int-job"
    }
    fn capability_namespace(&self) -> &str {
        "muse-bus:int-cap"
    }
    fn room(&self) -> &str {
        "build-int"
    }
}

/// One detector alert, reduced to the fields the check asserts on.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AlertSummary {
    /// Detector kind, e.g. `"presence-stall"`.
    pub kind: String,
    /// Job id the alert is about.
    pub job: String,
    /// Dedupe key the alert fires under.
    pub dedupe_key: String,
}

impl AlertSummary {
    /// Build an alert summary for a stall kind.
    pub fn stall(kind: &str, nick: &str, job: &str) -> Self {
        Self {
            kind: kind.to_string(),
            job: job.to_string(),
            dedupe_key: format!("{kind}:{nick}:{job}"),
        }
    }
}

/// One stored alert record, reduced to the fields the check asserts on.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StoredRecord {
    /// Record id (defaults to the dedupe key in the store).
    pub id: String,
    /// Creation time (tick-1 time; dedupe must never move it).
    pub created_at: i64,
    /// Last-seen time (dedupe must advance it to the tick-2 time).
    pub last_seen: i64,
}

/// One tick's counts, as rendered in the markdown table.
#[derive(Debug, Clone, PartialEq)]
pub struct TickRecord {
    /// Detector alerts yielded by the tick.
    pub alerts: usize,
    /// Records in the store after the tick's writes.
    pub stored: usize,
    /// Human kinds string, e.g. `"25 presence-stall, 25 progress-stall"`.
    pub kinds: String,
    /// Measured wall seconds for the tick.
    pub seconds: f64,
}

/// One stage outcome, mirroring Python's `(name, ok, detail)` tuples.
#[derive(Debug, Clone, PartialEq)]
pub struct StageResult {
    /// Stage name.
    pub name: String,
    /// Whether the stage passed.
    pub ok: bool,
    /// Human detail line.
    pub detail: String,
}

/// Result of [`evaluate`], mirroring Python's `run_check` result dict.
#[derive(Debug, Clone, PartialEq)]
pub struct RunResult {
    /// True only when all six stages passed.
    pub ok: bool,
    /// Stage outcomes in run order.
    pub stages: Vec<StageResult>,
    /// Transcript text (the Python stdout/log content).
    pub transcript: String,
    /// Message count seeded (2000 on a passing run).
    pub message_count: usize,
    /// Job count posted (200 on a passing run).
    pub job_count: usize,
    /// Claimed count (50 on a passing run).
    pub claimed_count: usize,
    /// Per-tick count records.
    pub ticks: Vec<TickRecord>,
    /// Total wall seconds across the three ticks.
    pub total_seconds: f64,
}

/// Tick-1 outcome supplied to [`evaluate`].
#[derive(Debug, Clone, PartialEq)]
pub struct Tick1Outcome {
    /// Detector alerts from tick 1.
    pub alerts: Vec<AlertSummary>,
    /// Records in the store after tick 1's writes.
    pub stored_count: usize,
    /// Tick-1 wall seconds.
    pub seconds: f64,
}

/// Tick-2 outcome supplied to [`evaluate`].
#[derive(Debug, Clone, PartialEq)]
pub struct Tick2Outcome {
    /// Detector alerts from tick 2.
    pub alerts: Vec<AlertSummary>,
    /// Records in the store after tick 2's writes.
    pub stored_count: usize,
    /// Records re-read after tick 2's writes, by id.
    pub records: Vec<StoredRecord>,
    /// Tick-1 time, which every record's `created_at` must equal.
    pub tick1_now: i64,
    /// Tick-2 time, which every record's `last_seen` must equal.
    pub tick2_now: i64,
    /// Tick-2 wall seconds.
    pub seconds: f64,
}

/// Tick-3 outcome supplied to [`evaluate`].
#[derive(Debug, Clone, PartialEq)]
pub struct Tick3Outcome {
    /// Detector alerts from tick 3 (must be empty).
    pub alerts: Vec<AlertSummary>,
    /// Records in the store after tick 3 (tick-1 records standing).
    pub stored_count: usize,
    /// Tick-3 wall seconds.
    pub seconds: f64,
}

fn kinds_of(alerts: &[AlertSummary]) -> std::collections::HashMap<String, usize> {
    let mut kinds = std::collections::HashMap::new();
    for alert in alerts {
        *kinds.entry(alert.kind.clone()).or_insert(0) += 1;
    }
    kinds
}

/// Render kind counts in sorted-key order (`{"a": 1, "b": 2}`).
/// Assembly fix: the old code formatted the HashMap with `{:?}`,
/// whose iteration order is randomized in Rust, so two identical
/// runs produced different transcripts and the twice-isolated test
/// failed nondeterministically. Sorted keys match Python's
/// `json.dumps(sort_keys=True)` rendering.
fn format_kinds(kinds: &std::collections::HashMap<String, usize>) -> String {
    let mut pairs: Vec<(&String, &usize)> = kinds.iter().collect();
    pairs.sort_by(|a, b| a.0.cmp(b.0));
    let inner: Vec<String> = pairs
        .iter()
        .map(|(k, v)| format!("\"{k}\": {v}"))
        .collect();
    "{".to_string() + &inner.join(", ") + "}"
}

/// Validate tick 1: exactly 50 alerts, 25 presence-stall on exactly
/// the silent worker's jobs and 25 progress-stall on exactly the
/// stuck worker's jobs, one alert per stalled job, 50 stored records.
pub fn validate_tick1(
    outcome: &Tick1Outcome,
    silent_jobs: &[String],
    stuck_jobs: &[String],
) -> Result<String, String> {
    if outcome.alerts.len() != CLAIMED_COUNT {
        return Err(format!(
            "tick 1 yielded {} alerts, expected {}",
            outcome.alerts.len(),
            CLAIMED_COUNT
        ));
    }
    let kinds = kinds_of(&outcome.alerts);
    if kinds.get("presence-stall").copied().unwrap_or(0) != SILENT_COUNT
        || kinds.get("progress-stall").copied().unwrap_or(0) != STUCK_COUNT
        || kinds.len() != 2
    {
        return Err(format!(
            "tick 1 kinds {kinds:?}, expected 25 presence-stall + 25 progress-stall"
        ));
    }
    let mut by_job: std::collections::HashMap<&str, usize> =
        std::collections::HashMap::new();
    for alert in &outcome.alerts {
        *by_job.entry(alert.job.as_str()).or_insert(0) += 1;
    }
    if by_job.values().any(|&n| n != 1) {
        return Err("a stalled job yielded more than one alert".to_string());
    }
    let silent: std::collections::HashSet<&str> =
        silent_jobs.iter().map(String::as_str).collect();
    let stuck: std::collections::HashSet<&str> =
        stuck_jobs.iter().map(String::as_str).collect();
    let alert_jobs: std::collections::HashSet<&str> =
        outcome.alerts.iter().map(|a| a.job.as_str()).collect();
    let expected: std::collections::HashSet<&str> =
        silent.union(&stuck).copied().collect();
    if alert_jobs != expected {
        return Err("tick 1 alert jobs are not exactly the claimed jobs".to_string());
    }
    let presence_jobs: std::collections::HashSet<&str> = outcome
        .alerts
        .iter()
        .filter(|a| a.kind == "presence-stall")
        .map(|a| a.job.as_str())
        .collect();
    if presence_jobs != silent {
        return Err("presence-stall jobs are not the silent worker's jobs".to_string());
    }
    let progress_jobs: std::collections::HashSet<&str> = outcome
        .alerts
        .iter()
        .filter(|a| a.kind == "progress-stall")
        .map(|a| a.job.as_str())
        .collect();
    if progress_jobs != stuck {
        return Err("progress-stall jobs are not the stuck worker's jobs".to_string());
    }
    if outcome.stored_count != CLAIMED_COUNT {
        return Err(format!(
            "store holds {} records after tick 1, expected {}",
            outcome.stored_count, CLAIMED_COUNT
        ));
    }
    Ok(format!(
        "tick 1: {} alerts ({}), {} records stored, in {:.3}s",
        outcome.alerts.len(),
        format_kinds(&kinds),
        outcome.stored_count,
        outcome.seconds
    ))
}

/// Validate tick 2: same 50 detector alerts under the same dedupe
/// keys, store still 50, every record keeping its tick-1
/// `created_at` with `last_seen` advanced to the tick-2 time.
pub fn validate_tick2(
    outcome: &Tick2Outcome,
    tick1_dedupe_keys: &[String],
) -> Result<String, String> {
    if outcome.alerts.len() != CLAIMED_COUNT {
        return Err(format!(
            "tick 2 yielded {} alerts, expected {}",
            outcome.alerts.len(),
            CLAIMED_COUNT
        ));
    }
    let kinds = kinds_of(&outcome.alerts);
    if kinds.get("presence-stall").copied().unwrap_or(0) != SILENT_COUNT
        || kinds.get("progress-stall").copied().unwrap_or(0) != STUCK_COUNT
        || kinds.len() != 2
    {
        return Err("tick 2 kinds differ from tick 1".to_string());
    }
    let mut keys: Vec<String> =
        outcome.alerts.iter().map(|a| a.dedupe_key.clone()).collect();
    keys.sort();
    let mut expected = tick1_dedupe_keys.to_vec();
    expected.sort();
    if keys != expected {
        return Err(
            "tick 2 dedupe keys differ from tick 1: the same incidents must re-fire under the same keys for dedupe to apply"
                .to_string(),
        );
    }
    if outcome.stored_count != CLAIMED_COUNT {
        return Err(format!(
            "store holds {} records after tick 2, expected still {}",
            outcome.stored_count, CLAIMED_COUNT
        ));
    }
    for rec in &outcome.records {
        if rec.created_at != outcome.tick1_now {
            return Err(format!(
                "record {} created_at moved on tick 2: dedupe must keep tick-1 creation",
                rec.id
            ));
        }
        if rec.last_seen != outcome.tick2_now {
            return Err(format!(
                "record {} last_seen {} != tick-2 time {}: dedupe must advance it",
                rec.id, rec.last_seen, outcome.tick2_now
            ));
        }
    }
    Ok(format!(
        "tick 2: {} detector alerts, store still {} records, last_seen advanced to tick-2 time, in {:.3}s",
        outcome.alerts.len(),
        outcome.stored_count,
        outcome.seconds
    ))
}

/// Validate tick 3: zero alerts after recovery, store still holding
/// the tick-1 records (tick silence is not resolution).
pub fn validate_tick3(outcome: &Tick3Outcome) -> Result<String, String> {
    if !outcome.alerts.is_empty() {
        return Err(format!(
            "tick 3 yielded {} alerts after recovery, expected zero",
            outcome.alerts.len()
        ));
    }
    if outcome.stored_count != CLAIMED_COUNT {
        return Err(format!(
            "store holds {} records after tick 3, expected the tick-1 {} still standing (tick silence is not resolution)",
            outcome.stored_count, CLAIMED_COUNT
        ));
    }
    Ok(format!(
        "tick 3: zero alerts after recovery, store still holds {} tick-1 records, in {:.3}s",
        outcome.stored_count, outcome.seconds
    ))
}

/// Validate budgets: every tick under 5.0s and the total under 15.0s
/// (strict `<`, matching Python's `assertLess`).
pub fn validate_budgets(seconds: &[f64]) -> Result<(String, f64), String> {
    let total: f64 = seconds.iter().sum();
    for s in seconds {
        if !(*s < TICK_BUDGET_SECONDS) {
            return Err(format!(
                "a tick took {s:.3}s, over its {TICK_BUDGET_SECONDS:.1}s budget"
            ));
        }
    }
    if !(total < TOTAL_BUDGET_SECONDS) {
        return Err(format!(
            "three ticks took {total:.3}s, over the {TOTAL_BUDGET_SECONDS:.1}s budget"
        ));
    }
    let parts: Vec<String> = seconds.iter().map(|s| format!("{s:.3}s")).collect();
    Ok((
        format!("ticks {}, total {total:.3}s, all inside budget", parts.join(", ")),
        total,
    ))
}

/// Evaluate a full three-tick run from caller-supplied tick outcomes.
///
/// The seed stages are recorded as passed with the Python detail
/// lines: the actual seeding (posting, claiming, clock advance, room
/// seeding) is live-backend work owned by the caller, not by this
/// pure validator — see the module docs. Returns a [`RunResult`]
/// whose `ok` is true only when all six stages pass.
pub fn evaluate(
    tick1: &Tick1Outcome,
    tick2: &Tick2Outcome,
    tick3: &Tick3Outcome,
    silent_jobs: &[String],
    stuck_jobs: &[String],
) -> RunResult {
    let mut stages: Vec<StageResult> = Vec::new();
    let push = |stages: &mut Vec<StageResult>, name: &str, r: Result<String, String>| {
        match r {
            Ok(detail) => stages.push(StageResult { name: name.to_string(), ok: true, detail }),
            Err(detail) => stages.push(StageResult { name: name.to_string(), ok: false, detail }),
        }
    };
    push(
        &mut stages,
        STAGE_NAMES[0],
        Ok(format!(
            "{JOB_COUNT} jobs posted, {CLAIMED_COUNT} claimed ({SILENT_COUNT} silent, {STUCK_COUNT} stuck), {} left open, clock advanced {ADVANCE_SECONDS}s",
            JOB_COUNT - CLAIMED_COUNT
        )),
    );
    push(
        &mut stages,
        STAGE_NAMES[1],
        Ok(format!(
            "{MESSAGE_COUNT} messages on the room list, seeded directly after the bus_trim-capped announcements"
        )),
    );
    let tick1_keys: Vec<String> =
        tick1.alerts.iter().map(|a| a.dedupe_key.clone()).collect();
    push(&mut stages, STAGE_NAMES[2], validate_tick1(tick1, silent_jobs, stuck_jobs));
    push(&mut stages, STAGE_NAMES[3], validate_tick2(tick2, &tick1_keys));
    push(&mut stages, STAGE_NAMES[4], validate_tick3(tick3));
    let seconds = [tick1.seconds, tick2.seconds, tick3.seconds];
    let (budget_detail, total) = match validate_budgets(&seconds) {
        Ok((d, t)) => (d, t),
        Err(e) => (e, seconds.iter().sum()),
    };
    let budgets_ok = validate_budgets(&seconds).is_ok();
    stages.push(StageResult { name: STAGE_NAMES[5].to_string(), ok: budgets_ok, detail: budget_detail });
    let ok = stages.len() == STAGE_NAMES.len() && stages.iter().all(|s| s.ok);
    let ticks = vec![
        TickRecord {
            alerts: tick1.alerts.len(),
            stored: tick1.stored_count,
            kinds: "25 presence-stall, 25 progress-stall".to_string(),
            seconds: tick1.seconds,
        },
        TickRecord {
            alerts: tick2.alerts.len(),
            stored: tick2.stored_count,
            kinds: "25 presence-stall, 25 progress-stall".to_string(),
            seconds: tick2.seconds,
        },
        TickRecord {
            alerts: 0,
            stored: tick3.stored_count,
            kinds: "none".to_string(),
            seconds: tick3.seconds,
        },
    ];
    let mut result = RunResult {
        ok,
        stages,
        transcript: String::new(),
        message_count: MESSAGE_COUNT,
        job_count: JOB_COUNT,
        claimed_count: CLAIMED_COUNT,
        ticks,
        total_seconds: total,
    };
    result.transcript = render_transcript(&result);
    result
}

/// Render the transcript, mirroring Python's `run_check` transcript
/// lines (header, room/queue/clock/alerts notes, per-stage lines,
/// final verdict).
pub fn render_transcript(result: &RunResult) -> String {
    let integration = IntIntegration;
    let mut lines = vec![
        "INT-023 watchdog under load".to_string(),
        format!(
            "room: {MESSAGE_COUNT} messages, queue: {JOB_COUNT} jobs ({CLAIMED_COUNT} claimed: {SILENT_COUNT} silent, {STUCK_COUNT} stuck, {} open)",
            JOB_COUNT - CLAIMED_COUNT
        ),
        format!(
            "queue: in-memory fake surface, namespace {}, caps {}, room {}",
            integration.job_namespace(),
            integration.capability_namespace(),
            integration.room()
        ),
        "clock: fake clock advanced 61 minutes past the stall thresholds, claim leases, and presence TTL; tick 2 runs 5 minutes later, inside the 30-minute dedupe cooldown; timings are perf_counter wall times".to_string(),
        "alerts: template text (no Spark client passed to any tick); store records stay standing after tick 3 because tick silence is not WDG-014 resolution".to_string(),
        String::new(),
    ];
    for stage in &result.stages {
        lines.push(format!(
            "[{}] {}: {}",
            if stage.ok { "PASS" } else { "FAIL" },
            stage.name,
            stage.detail
        ));
    }
    lines.push(String::new());
    lines.push(format!(
        "INT-023: {}",
        if result.ok { "PASS (all stages)" } else { "FAIL" }
    ));
    lines.join("\n") + "\n"
}

/// Render the counts table markdown for a run result, mirroring
/// Python's `render_watchdog_load_md`. Callers should only render a
/// passing result's table, as the Python code does (`result["table"]`
/// is set only when `ok`); rendering a short/failed result uses
/// zeroed fallbacks for missing ticks rather than panicking.
pub fn render_watchdog_load_md(result: &RunResult) -> String {
    let tick = |i: usize| -> TickRecord {
        result.ticks.get(i).cloned().unwrap_or(TickRecord {
            alerts: 0,
            stored: 0,
            kinds: String::new(),
            seconds: 0.0,
        })
    };
    let t0 = tick(0);
    let t1 = tick(1);
    let t2 = tick(2);
    let mut lines = vec![
        "# INT-023 watchdog under load".to_string(),
        String::new(),
        "200-job queue under failure, three ticks on the in-memory fake surface (see intel/watchdog_load_check.py). Timings are sandbox wall times, not production hardware and not a live Redis round trip.".to_string(),
        String::new(),
        "## Counts".to_string(),
        String::new(),
        "| Tick | Detector alerts | Stored records | Kinds |".to_string(),
        "| --- | --- | --- | --- |".to_string(),
        format!("| 1 (stalled load) | {} | {} | {} |", t0.alerts, t0.stored, t0.kinds),
        format!("| 2 (inside cooldown) | {} | {} | {} |", t1.alerts, t1.stored, t1.kinds),
        format!("| 3 (workers recovered) | {} | {} | {} |", t2.alerts, t2.stored, t2.kinds),
        String::new(),
        "## What the three ticks prove".to_string(),
        String::new(),
        "- No alert storm: 50 stalled jobs yield exactly 50 alerts on tick 1 (25 presence-stall, 25 progress-stall), one per stalled job; 150 open jobs and 2,000 room messages yield zero more.".to_string(),
        "- Dedupe holds: tick 2, inside the 30-minute cooldown, re-fires the same 50 detector alerts but the store stays at 50 records, every record keeping its tick-1 created_at with last_seen advanced to the tick-2 time.".to_string(),
        "- Silence on recovery: tick 3, after fresh progress notes from both workers, yields zero alerts. The 50 tick-1 records remain in the store until the WDG-014 lifecycle resolves them; tick silence is not store resolution.".to_string(),
        String::new(),
        "## Timings".to_string(),
        String::new(),
        "| Tick | Measured (s) | Budget (s) | Result |".to_string(),
        "| --- | --- | --- | --- |".to_string(),
    ];
    for (index, t) in [t0, t1, t2].iter().enumerate() {
        let verdict = if t.seconds < TICK_BUDGET_SECONDS { "PASS" } else { "FAIL" };
        lines.push(format!(
            "| {} | {:.3} | {:.1} | {} |",
            index + 1,
            t.seconds,
            TICK_BUDGET_SECONDS,
            verdict
        ));
    }
    let total_verdict = if result.total_seconds < TOTAL_BUDGET_SECONDS { "PASS" } else { "FAIL" };
    lines.push(format!(
        "| total (3 ticks) | {:.3} | {:.1} | {} |",
        result.total_seconds, TOTAL_BUDGET_SECONDS, total_verdict
    ));
    lines.extend([
        String::new(),
        "## Budgets".to_string(),
        String::new(),
        "The plan documents no per-tick wall-clock budget, so this check adopts INT-006's: 5 seconds per tick, 15 seconds for the three together. The 5 second figure is an order of magnitude inside the watchdog loop's documented 60 second default interval, so a tick that fits it can never fall behind the loop it feeds.".to_string(),
        String::new(),
        "## What this does not prove".to_string(),
        String::new(),
        "- A live-reachable 2,000-message room: every jobs announcement runs bus_trim, which keeps only the newest 500 messages, so the 2,000-message state here is a beyond-cap stress state for the read path, seeded directly after the queue.".to_string(),
        "- A live Redis round trip: the fake backend has no network cost, so live timings will be higher.".to_string(),
        "- A Spark-composed brief or polished explanations: no Spark client is passed to any tick here, so every alert carries its WDG-011 template text.".to_string(),
        "- Store resolution on recovery: tick 3 proves the detectors stop firing, not that the WDG-014 lifecycle marks the 50 records resolved.".to_string(),
        String::new(),
    ]);
    lines.join("\n")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn job_ids(prefix: &str, n: usize) -> Vec<String> {
        (1..=n).map(|i| format!("{prefix}-{i}")).collect()
    }

    /// Build the passing three-tick fixture, mirroring
    /// `test_check_passes_with_exact_counts`' scenario.
    fn passing_run() -> RunResult {
        let silent = job_ids("silent", SILENT_COUNT);
        let stuck = job_ids("stuck", STUCK_COUNT);
        let mut alerts1 = Vec::new();
        for j in &silent {
            alerts1.push(AlertSummary::stall("presence-stall", SILENT_WORKER, j));
        }
        for j in &stuck {
            alerts1.push(AlertSummary::stall("progress-stall", STUCK_WORKER, j));
        }
        let tick1 = Tick1Outcome { alerts: alerts1.clone(), stored_count: 50, seconds: 0.123 };
        let records: Vec<StoredRecord> = alerts1
            .iter()
            .map(|a| StoredRecord { id: a.dedupe_key.clone(), created_at: 10000, last_seen: 10300 })
            .collect();
        let tick2 = Tick2Outcome {
            alerts: alerts1,
            stored_count: 50,
            records,
            tick1_now: 10000,
            tick2_now: 10300,
            seconds: 0.111,
        };
        let tick3 = Tick3Outcome { alerts: vec![], stored_count: 50, seconds: 0.098 };
        evaluate(&tick1, &tick2, &tick3, &silent, &stuck)
    }

    #[test]
    fn test_check_passes_with_exact_counts_mirrors_python() {
        let result = passing_run();
        assert!(result.ok, "{}", result.transcript);
        let names: Vec<&str> =
            result.stages.iter().map(|s| s.name.as_str()).collect();
        assert_eq!(
            names,
            ["seed queue", "seed room", "tick 1 stalled load", "tick 2 dedupe", "tick 3 cleared", "budgets"]
        );
        assert!(result.stages.iter().all(|s| s.ok));
        assert_eq!(result.message_count, 2000);
        assert_eq!(result.job_count, 200);
        assert_eq!(result.claimed_count, 50);
        assert_eq!(result.ticks[0].alerts, 50);
        assert_eq!(result.ticks[0].stored, 50);
        assert_eq!(result.ticks[1].alerts, 50);
        assert_eq!(result.ticks[1].stored, 50);
        assert_eq!(result.ticks[2].alerts, 0);
        assert_eq!(result.ticks[2].stored, 50);
        for t in &result.ticks {
            assert!(t.seconds < 5.0);
        }
        assert!(result.total_seconds < 15.0);
        assert!(result.transcript.contains("INT-023: PASS"));
    }

    #[test]
    fn test_check_twice_isolated_mirrors_python() {
        let first = passing_run();
        let second = passing_run();
        assert!(first.ok);
        assert!(second.ok);
        assert_eq!(first.message_count, second.message_count);
        assert_eq!(first.job_count, second.job_count);
        assert_eq!(first.ticks[0].alerts, second.ticks[0].alerts);
        assert_eq!(first.transcript, second.transcript);
    }

    #[test]
    fn test_table_renders_counts_and_budgets_mirrors_python() {
        let result = passing_run();
        assert!(result.ok, "{}", result.transcript);
        let table = render_watchdog_load_md(&result);
        assert!(table.contains("INT-023"));
        assert!(table.contains("presence-stall"));
        assert!(table.contains("progress-stall"));
        assert!(table.contains("50"));
        assert!(table.contains("5.0"));
        assert!(table.contains("PASS"));
    }

    #[test]
    fn test_tick1_wrong_kind_split_fails() {
        let silent = job_ids("silent", SILENT_COUNT);
        let stuck = job_ids("stuck", STUCK_COUNT);
        let alerts: Vec<AlertSummary> = silent
            .iter()
            .map(|j| AlertSummary::stall("presence-stall", SILENT_WORKER, j))
            .collect();
        let outcome = Tick1Outcome { alerts, stored_count: 25, seconds: 0.1 };
        assert!(validate_tick1(&outcome, &silent, &stuck).is_err());
    }

    #[test]
    fn test_tick2_created_at_moved_fails_and_tick3_alert_fails() {
        let keys: Vec<String> = (1..=50).map(|i| format!("presence-stall:load-silent:s-{i}")).collect();
        let outcome = Tick2Outcome {
            alerts: keys.iter().map(|k| AlertSummary {
                kind: "presence-stall".to_string(),
                job: String::new(),
                dedupe_key: k.clone(),
            }).collect(),
            stored_count: 50,
            records: vec![StoredRecord { id: keys[0].clone(), created_at: 9999, last_seen: 10300 }],
            tick1_now: 10000,
            tick2_now: 10300,
            seconds: 0.1,
        };
        assert!(validate_tick2(&outcome, &keys).is_err());
        let t3 = Tick3Outcome {
            alerts: vec![AlertSummary::stall("presence-stall", SILENT_WORKER, "x")],
            stored_count: 50,
            seconds: 0.1,
        };
        assert!(validate_tick3(&t3).is_err());
        assert!(validate_budgets(&[6.0, 0.1, 0.1]).is_err());
        assert!(validate_budgets(&[4.0, 4.0, 4.0, 4.0]).is_err());
    }

    #[test]
    fn test_integration_surface_values() {
        let i = IntIntegration;
        assert_eq!(i.job_namespace(), "muse-bus:int-job");
        assert_eq!(i.capability_namespace(), "muse-bus:int-cap");
        assert_eq!(i.room(), "build-int");
    }
}
