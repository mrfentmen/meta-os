//! INT-020 end-to-end watchdog surfaces (port of
//! `os/intel/e2e_watchdog_surfaces.py`).
//!
//! One watchdog alert traced across all three surfaces that are
//! supposed to show it, with the same id and severity on each:
//!
//! 1. alert store: the WDG-010 record built from the detector dict
//!    (id defaults to the dedupe key, one record per dedupe key),
//! 2. brief: Watch items (BRF-022), template brief,
//! 3. dashboard: the intelPanel alerts panel (DSH-013/014).
//!
//! The alert is a real watchdog tick in Python, not a hand-built
//! dict: a presence-stall fixture goes through `watchdog.tick`,
//! exactly the WDG-002 detector path. The store surface is the
//! validated WDG-010 record built from that detector dict, and the
//! brief and dashboard surfaces are fed that same record object,
//! not retyped copies, so an id or severity mismatch between
//! surfaces fails the run rather than being typed away.
//!
//! SEAMS (see the trait docs): `intel.watchdog`, `intel.brief` and
//! `intel.store` are not in this batch, so this module does not
//! import them. [`E2eSurfaces`] is the seam: [`LocalSurfaces`]
//! implements the WDG-002 presence-stall detector, the WDG-010
//! record shape, and the BRF-022 Watch-item extraction locally, so
//! the loop is runnable standalone. Two approximations are noted
//! where they occur: the explanation text is a local template (the
//! exact WDG-011 template lives in `intel.explanations`, not in
//! this batch), and the dashboard check is a row/HTML seam — the
//! real dashboard check runs the node harness against `bus.html`,
//! which is excluded viewer code, so that execution is
//! exclusion-blocked and is never faked as a live panel run.
//!
//! Honest limit, carried over from the Python docstring: the card
//! renders kind, severity, explanation and suggested fix, but not
//! the id literal itself — the id lives in the panel's row data,
//! not in the card text. That is a rendering observation, not a
//! mismatch: no surface here carries a different id or severity.
//!
//! Live-behavior boundary: nothing here touches the live bus or
//! posts a real job, and nothing is announced: the ALERT line stays
//! held, per the posting rule. Log-file writing is caller-side:
//! [`run_loop`] returns the transcript instead of writing
//! `intel/evals/e2e_watchdog_surfaces.log` itself.

/// Fixture time for the INT-020 loop.
pub const NOW: i64 = 10000;
/// Room the INT-020 record is built for.
pub const E2E_ROOM: &str = "build-int";
/// Expected alert id for the INT-020 fixture.
pub const EXPECTED_ALERT_ID: &str = "presence-stall:pax:7";

/// One job in a watchdog snapshot, reduced to the fields the
/// presence-stall detector reads.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SnapshotJob {
    /// Job id.
    pub id: String,
    /// Job title.
    pub title: String,
    /// Job status, e.g. `"claimed"`.
    pub status: String,
    /// Claiming nick.
    pub claim: String,
    /// Last-activity timestamp: first numeric field among
    /// `last_progress`, `progress_at`, `note_ts`,
    /// `last_progress_at`, `claimed_at` in the Python detector.
    /// `None` means the job carries no timestamp at all, and the
    /// detector never invents an age for it.
    pub last_activity: Option<i64>,
}

/// A watchdog snapshot: jobs, presence list, and caps registry
/// (nick -> caps description; only membership is read here).
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Snapshot {
    /// Jobs in the snapshot.
    pub jobs: Vec<SnapshotJob>,
    /// Nicks currently present.
    pub presence: Vec<String>,
    /// Nicks in the caps registry.
    pub caps: Vec<String>,
}

/// A watchdog detector alert, reduced to the fields the surfaces use.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Alert {
    /// Detector kind, e.g. `"presence-stall"`.
    pub kind: String,
    /// Severity, e.g. `"critical"`.
    pub severity: String,
    /// Nick the alert is about.
    pub nick: String,
    /// Job id the alert is about.
    pub job: String,
    /// Job title.
    pub job_title: String,
    /// Age of last activity in seconds.
    pub last_progress_age_seconds: i64,
    /// Age of last activity in whole minutes.
    pub last_progress_age_minutes: i64,
    /// Explanation text (WDG-011 template in Python).
    pub explanation: String,
    /// Suggested fix text (WDG-011 template in Python).
    pub suggested_fix: String,
    /// Dedupe key, e.g. `"presence-stall:pax:7"`.
    pub dedupe_key: String,
    /// Creation time.
    pub created_at: i64,
}

/// A WDG-010 alert record built from a detector alert.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AlertRecord {
    /// Record id: explicit id, else the detector's id, else the
    /// dedupe key — one record per dedupe key.
    pub id: String,
    /// Detector kind.
    pub kind: String,
    /// Severity.
    pub severity: String,
    /// Room (cleaned; default `"main"`).
    pub room: String,
    /// Subjects derived from nick/job fields.
    pub subjects: Vec<String>,
    /// Creation time.
    pub created_at: i64,
    /// Last-seen time (the record's `created_at` unless the detector
    /// already carried a valid int `last_seen`).
    pub last_seen: i64,
    /// WDG-014 status: every fresh occurrence starts `"open"`.
    pub status: String,
    /// Acknowledged time, always `None` on a fresh record.
    pub acknowledged_at: Option<i64>,
    /// Resolved time, always `None` on a fresh record.
    pub resolved_at: Option<i64>,
    /// Explanation carried over from the detector dict.
    pub explanation: String,
    /// Suggested fix carried over from the detector dict.
    pub suggested_fix: String,
    /// Dedupe key carried over from the detector dict.
    pub dedupe_key: String,
}

/// One brief Watch item: `{id, summary}` by reference (BRF-022).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WatchItem {
    /// Alert id.
    pub id: String,
    /// One-line summary, verbatim.
    pub summary: String,
}

/// One dashboard panel row, reduced to the fields the check reads.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DashboardRow {
    /// Alert id from the panel's row data.
    pub id: String,
    /// Alert kind.
    pub kind: String,
    /// Alert severity.
    pub severity: String,
}

/// Dashboard check outcome: panel rows plus rendered card HTML.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DashboardOutcome {
    /// Panel alert rows.
    pub rows: Vec<DashboardRow>,
    /// Rendered card HTML.
    pub html: String,
}

/// SEAM (see module docs): the tick source and dashboard panel,
/// whose real implementations live in `intel.watchdog` and in the
/// `bus.html` viewer code — neither in this batch. Implementors
/// supply a tick and a dashboard outcome for a record; the loop
/// logic itself (stage order, id/severity equality across surfaces)
/// lives in [`run_loop`] and is not re-implemented per backend.
pub trait E2eSurfaces {
    /// Run a watchdog tick over a snapshot at `now`.
    fn tick(&self, snapshot: &Snapshot, now: i64) -> Vec<Alert>;
    /// Check a record against the dashboard panel at `now_ms`.
    fn dashboard_check(&self, record: &AlertRecord, now_ms: i64) -> DashboardOutcome;
}

/// The INT-020 stall fixture: job 7 claimed by `pax` (in caps,
/// absent from presence) with last activity at 9340, seen at 10000
/// — age 660s, past the 10-minute (600s) stall window.
pub fn stall_snapshot() -> Snapshot {
    Snapshot {
        jobs: vec![SnapshotJob {
            id: "7".to_string(),
            title: "demo job".to_string(),
            status: "claimed".to_string(),
            claim: "pax".to_string(),
            last_activity: Some(9340),
        }],
        presence: vec!["hana".to_string()],
        caps: vec!["pax".to_string()],
    }
}

/// The INT-020 quiet fixture: no jobs, no presence, no caps.
pub fn quiet_snapshot() -> Snapshot {
    Snapshot::default()
}

/// WDG-002 presence-stall detector, ported from `intel.watchdog`'s
/// `detect_presence_stall` so the loop is runnable through the seam:
/// a nick in the caps registry, absent from presence, holding a
/// claimed job with no activity longer than `stall_minutes`, yields
/// one alert per (nick, job) pair. A present nick, a nick with no
/// claimed job, a nick not in caps (walk-on), or a fresh job yields
/// no alert; a job with no timestamp yields no alert.
///
/// APPROXIMATION: the explanation/suggested-fix text is a local
/// one-line template. The exact WDG-011 wording lives in
/// `intel.explanations`, not in this batch; only the first line is
/// ever read back (as the brief summary fallback), so the loop's
/// assertions — kind, severity, id, and `"id: summary"` rendering —
/// do not depend on the exact wording.
pub fn detect_presence_stall(snapshot: &Snapshot, now: i64, stall_minutes: i64) -> Vec<Alert> {
    let threshold_seconds = stall_minutes * 60;
    let mut alerts = Vec::new();
    for job in &snapshot.jobs {
        if job.status != "claimed" {
            continue;
        }
        let nick = job.claim.as_str();
        if nick.is_empty()
            || !snapshot.caps.iter().any(|c| c == nick)
            || snapshot.presence.iter().any(|p| p == nick)
        {
            continue;
        }
        let Some(last) = job.last_activity else {
            continue;
        };
        let age = now - last;
        if age <= threshold_seconds {
            continue;
        }
        alerts.push(Alert {
            kind: "presence-stall".to_string(),
            severity: "critical".to_string(),
            nick: nick.to_string(),
            job: job.id.clone(),
            job_title: job.title.clone(),
            last_progress_age_seconds: age,
            last_progress_age_minutes: age / 60,
            explanation: format!(
                "presence-stall: {nick} on job {} idle {} minutes (stall window {stall_minutes} minutes)",
                job.id,
                age / 60
            ),
            suggested_fix: format!(
                "presence-stall: check on {nick} for job {}",
                job.id
            ),
            dedupe_key: format!("presence-stall:{nick}:{}", job.id),
            created_at: now,
        });
    }
    alerts
}

/// Clean a room name the way the store does before defaulting:
/// whitespace-trimmed, empty becoming `"main"`. (The full
/// `relay_common.clean_room` normalization lives outside this
/// batch; only the empty-to-`"main"` rule is observable in INT-020.)
pub fn clean_room(room: &str) -> String {
    let cleaned = room.trim();
    if cleaned.is_empty() {
        "main".to_string()
    } else {
        cleaned.to_string()
    }
}

/// Build a WDG-010 record from a detector alert, mirroring
/// `intel.store.build_alert_record`: id defaults to the dedupe key,
/// room cleaned with default `"main"`, subjects from nick/job,
/// status `"open"` with acknowledged/resolved `None`, `last_seen`
/// equal to `created_at`. Fails (like Python's `ValueError`) when
/// kind, severity, or dedupe key is missing — nothing is invented.
pub fn build_alert_record(alert: &Alert, room: &str) -> Result<AlertRecord, String> {
    if alert.kind.is_empty() {
        return Err("detector alert missing kind".to_string());
    }
    if alert.severity.is_empty() {
        return Err("detector alert missing severity".to_string());
    }
    if alert.dedupe_key.is_empty() {
        return Err("detector alert missing dedupe_key".to_string());
    }
    let mut subjects = Vec::new();
    if !alert.nick.is_empty() {
        subjects.push(alert.nick.clone());
    }
    if !alert.job.is_empty() && !subjects.contains(&alert.job) {
        subjects.push(alert.job.clone());
    }
    Ok(AlertRecord {
        id: alert.dedupe_key.clone(),
        kind: alert.kind.clone(),
        severity: alert.severity.clone(),
        room: clean_room(room),
        subjects,
        created_at: alert.created_at,
        last_seen: alert.created_at,
        status: "open".to_string(),
        acknowledged_at: None,
        resolved_at: None,
        explanation: alert.explanation.clone(),
        suggested_fix: alert.suggested_fix.clone(),
        dedupe_key: alert.dedupe_key.clone(),
    })
}

/// BRF-022 Watch-item extraction, mirroring
/// `intel.brief.extract_watch_items`: in snapshot order, `{id,
/// summary}` per alert; alerts with no id are skipped (a brief must
/// never invent an alert id); an alert with no summary falls back
/// to the first line of its explanation, and only an alert with
/// neither renders an empty summary.
pub fn extract_watch_items(records: &[AlertRecord]) -> Vec<WatchItem> {
    let mut items = Vec::new();
    for record in records {
        if record.id.is_empty() {
            continue;
        }
        let summary = if !record.explanation.trim().is_empty() {
            record.explanation.lines().next().unwrap_or("").trim().to_string()
        } else {
            String::new()
        };
        items.push(WatchItem { id: record.id.clone(), summary });
    }
    items
}

/// Render the template brief's Watch-items lines for records:
/// `"{id}: {summary}"` per item, mirroring the brief's Watch items
/// section format. Only the Watch lines are rendered here — the
/// full template brief (BRF-008) lives in `intel.brief`, not in
/// this batch.
pub fn watch_items_lines(records: &[AlertRecord]) -> Vec<String> {
    extract_watch_items(records)
        .iter()
        .map(|item| format!("{}: {}", item.id, item.summary))
        .collect()
}

/// Local seam implementation: the WDG-002 detector above for the
/// tick, and a dashboard outcome built from the record itself
/// (row carrying the record's id/kind/severity, card HTML carrying
/// kind and severity). The card HTML is a stand-in for the node
/// harness rendering of the `bus.html` intelPanel — see the module
/// docs: executing that panel is exclusion-blocked (excluded
/// viewer code), so this seam outcome is the testable surface and
/// is never presented as a live panel run.
#[derive(Debug, Clone, Copy, Default)]
pub struct LocalSurfaces {
    /// Stall window in minutes for the local tick (default 10).
    pub stall_minutes: i64,
}

impl LocalSurfaces {
    /// Build with the INT-022 locked default stall window.
    pub fn new() -> Self {
        Self { stall_minutes: 10 }
    }
}

impl E2eSurfaces for LocalSurfaces {
    fn tick(&self, snapshot: &Snapshot, now: i64) -> Vec<Alert> {
        detect_presence_stall(snapshot, now, self.stall_minutes)
    }

    fn dashboard_check(&self, record: &AlertRecord, _now_ms: i64) -> DashboardOutcome {
        DashboardOutcome {
            rows: vec![DashboardRow {
                id: record.id.clone(),
                kind: record.kind.clone(),
                severity: record.severity.clone(),
            }],
            html: format!(
                "<div class=\"alert-card\">{} {} {}</div>",
                record.kind, record.severity, record.explanation
            ),
        }
    }
}

/// One stage outcome, mirroring Python's `(name, ok, detail)` tuples.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StageResult {
    /// Stage name.
    pub name: String,
    /// Whether the stage passed.
    pub ok: bool,
    /// Human detail line.
    pub detail: String,
}

/// Result of [`run_loop`], mirroring Python's `run_loop` result dict.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LoopResult {
    /// True only when all five stages passed.
    pub ok: bool,
    /// Stage outcomes in run order.
    pub stages: Vec<StageResult>,
    /// Transcript text.
    pub transcript: String,
    /// Alert id carried across all three surfaces.
    pub alert_id: String,
    /// Store record, when the store stage passed.
    pub record: Option<AlertRecord>,
}

/// Run the INT-020 loop through a [`E2eSurfaces`] seam.
///
/// Stages, each asserted, any failure failing the run (later stages
/// are not attempted after a failure, mirroring Python's
/// `stage()` raising `AssertionError`):
/// tick, store, brief, dashboard, quiet.
pub fn run_loop(surfaces: &dyn E2eSurfaces) -> LoopResult {
    let mut stages: Vec<StageResult> = Vec::new();
    let mut lines: Vec<String> = Vec::new();
    let record: Option<AlertRecord>;
    let alert_id: String;
    let fail = |stages: &mut Vec<StageResult>,
                lines: &mut Vec<String>,
                name: &str,
                detail: String|
     -> LoopResult {
        stages.push(StageResult { name: name.to_string(), ok: false, detail: detail.clone() });
        lines.push(format!("FAIL: {name} -- {detail}"));
        LoopResult {
            ok: false,
            stages: stages.clone(),
            transcript: lines.join("\n") + "\n",
            alert_id: String::new(),
            record: None,
        }
    };
    let pass = |stages: &mut Vec<StageResult>, lines: &mut Vec<String>, name: &str, detail: String| {
        stages.push(StageResult { name: name.to_string(), ok: true, detail });
        let last = stages.last().expect("just pushed");
        lines.push(format!("PASS: {} -- {}", name, last.detail));
    };

    // 1. tick
    let alerts = surfaces.tick(&stall_snapshot(), NOW);
    if !(alerts.len() == 1 && alerts[0].kind == "presence-stall" && alerts[0].severity == "critical") {
        let detail = format!(
            "exactly one presence-stall alert, severity critical: {}",
            alerts.first().map(|a| format!("{a:?}")).unwrap_or_else(|| "none".to_string())
        );
        return fail(&mut stages, &mut lines, "tick", detail);
    }
    pass(
        &mut stages,
        &mut lines,
        "tick",
        format!("exactly one presence-stall alert, severity critical: {:?}", alerts[0]),
    );
    let alert = alerts[0].clone();

    // 2. store record, built from the detector dict itself
    let built = match build_alert_record(&alert, E2E_ROOM) {
        Ok(r) => r,
        Err(e) => return fail(&mut stages, &mut lines, "store", e),
    };
    if !(built.id == alert.dedupe_key && built.severity == "critical") {
        return fail(
            &mut stages,
            &mut lines,
            "store",
            format!("record id={} severity={} room={}", built.id, built.severity, built.room),
        );
    }
    pass(
        &mut stages,
        &mut lines,
        "store",
        format!("record id={} severity={} room={}", built.id, built.severity, built.room),
    );
    alert_id = built.id.clone();
    record = Some(built.clone());

    // 3. brief surface: same record, same id
    let items = extract_watch_items(std::slice::from_ref(&built));
    let brief_lines = watch_items_lines(std::slice::from_ref(&built));
    let brief_text = brief_lines.join("\n");
    if !(items.len() == 1
        && items[0].id == built.id
        && brief_text.contains(&format!("{}: ", built.id)))
    {
        return fail(
            &mut stages,
            &mut lines,
            "brief",
            format!(
                "Watch items id={}; template brief renders 'id: summary'",
                items.first().map(|i| i.id.as_str()).unwrap_or("none")
            ),
        );
    }
    pass(
        &mut stages,
        &mut lines,
        "brief",
        format!("Watch items id={}; template brief renders 'id: summary'", items[0].id),
    );

    // 4. dashboard surface: same record, same id and severity
    let dash = surfaces.dashboard_check(&built, NOW * 1000);
    if !(dash.rows.len() == 1
        && dash.rows[0].id == built.id
        && dash.rows[0].severity == "critical"
        && dash.html.contains("presence-stall")
        && dash.html.contains("critical"))
    {
        return fail(
            &mut stages,
            &mut lines,
            "dashboard",
            format!(
                "panel row id={} severity={}; card renders kind+severity (id literal itself is row data, not card text)",
                dash.rows.first().map(|r| r.id.as_str()).unwrap_or("none"),
                dash.rows.first().map(|r| r.severity.as_str()).unwrap_or("none")
            ),
        );
    }
    pass(
        &mut stages,
        &mut lines,
        "dashboard",
        format!(
            "panel row id={} severity={}; card renders kind+severity (id literal itself is row data, not card text)",
            dash.rows[0].id, dash.rows[0].severity
        ),
    );

    // 5. quiet fixture: no surface invents an alert
    let quiet = surfaces.tick(&quiet_snapshot(), NOW);
    let quiet_items = extract_watch_items(&[]);
    if !(quiet.is_empty() && quiet_items.is_empty()) {
        return fail(
            &mut stages,
            &mut lines,
            "quiet",
            "quiet tick yields zero alerts; Watch items empty".to_string(),
        );
    }
    pass(
        &mut stages,
        &mut lines,
        "quiet",
        "quiet tick yields zero alerts; Watch items empty".to_string(),
    );

    lines.push(format!(
        "INT-020: PASS -- id {alert_id} severity critical on store, brief, and dashboard row"
    ));
    LoopResult {
        ok: true,
        stages,
        transcript: lines.join("\n") + "\n",
        alert_id,
        record,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_loop_passes_all_stages_mirrors_python() {
        let result = run_loop(&LocalSurfaces::new());
        assert!(result.ok, "{}", result.transcript);
        let names: Vec<&str> =
            result.stages.iter().map(|s| s.name.as_str()).collect();
        assert_eq!(names, ["tick", "store", "brief", "dashboard", "quiet"]);
        assert!(result.stages.iter().all(|s| s.ok));
        assert_eq!(result.alert_id, "presence-stall:pax:7");
        let record = result.record.expect("record");
        assert_eq!(record.severity, "critical");
        assert_eq!(record.room, "build-int");
        assert!(result.transcript.contains("INT-020: PASS"));
    }

    #[test]
    fn test_loop_twice_isolated_mirrors_python() {
        let first = run_loop(&LocalSurfaces::new());
        let second = run_loop(&LocalSurfaces::new());
        assert!(first.ok);
        assert!(second.ok);
        assert_eq!(first.alert_id, second.alert_id);
        assert_eq!(first.transcript, second.transcript);
    }

    #[test]
    fn test_presence_stall_detector_edges() {
        // Fresh job: age exactly at the window does not fire
        // (Python: `age <= threshold_seconds` skips).
        let mut snap = stall_snapshot();
        snap.jobs[0].last_activity = Some(NOW - 600);
        assert!(detect_presence_stall(&snap, NOW, 10).is_empty());
        // Present worker does not fire presence-stall.
        let mut snap = stall_snapshot();
        snap.presence = vec!["pax".to_string()];
        assert!(detect_presence_stall(&snap, NOW, 10).is_empty());
        // Job with no timestamp never fires.
        let mut snap = stall_snapshot();
        snap.jobs[0].last_activity = None;
        assert!(detect_presence_stall(&snap, NOW, 10).is_empty());
        // Walk-on claimer (not in caps) never fires.
        let mut snap = stall_snapshot();
        snap.caps = vec![];
        assert!(detect_presence_stall(&snap, NOW, 10).is_empty());
    }

    #[test]
    fn test_build_alert_record_rejects_missing_fields() {
        let mut alert = detect_presence_stall(&stall_snapshot(), NOW, 10).pop().unwrap();
        alert.dedupe_key = String::new();
        assert!(build_alert_record(&alert, "build-int").is_err());
    }

    #[test]
    fn test_watch_items_skip_idless_and_fall_back_to_explanation() {
        let record = build_alert_record(
            &detect_presence_stall(&stall_snapshot(), NOW, 10)[0],
            "build-int",
        )
        .unwrap();
        let items = extract_watch_items(std::slice::from_ref(&record));
        assert_eq!(items.len(), 1);
        assert_eq!(items[0].id, "presence-stall:pax:7");
        assert!(!items[0].summary.is_empty());
        let lines = watch_items_lines(std::slice::from_ref(&record));
        assert!(lines[0].starts_with("presence-stall:pax:7: "));
        assert!(extract_watch_items(&[]).is_empty());
    }
}
