//! B15 — Dashboard backend contract (`contract`).
//!
//! The cleaned tree has no dashboard server module (the viewer was
//! fold-excluded) — this batch is the documented backend contract from
//! `os/docs/DASHBOARD_SPEC.md` plus its parity tests. No viewer is
//! invented; viewer/Node/browser-dependent parity cases are marked
//! exclusion-blocked, never faked green.
//!
//! Contracts encoded here (section refs are DASHBOARD_SPEC.md):
//! - §4 brief payload (BRF-042) + staleness (BRF-043, stale at ≥2h) +
//!   visual-check verdicts (STR-004) + DSH-031 open-map defaults
//! - §5 dispatch payloads (DSP-037 preview) + request-only approve
//!   (DSH-038) + never-auto-post (DSP-040)
//! - §6 alerts feed order (DSH-013, newest-first, id-stable)
//! - DSH-014 alert lifecycle rules (WDG-014: open -> acknowledged
//!   -> resolved, idempotent re-ack/re-resolve, refused ack on
//!   resolved, unresolved-critical header count, write gate off)
//! - §8 deep links (DSH-022), demo mode (DSH-028, exact `demo=1`),
//!   today counters (DSH-032)
//! - §9 error/empty states (DSH-021, per-source, independent panels)
//! - readonly token (GOV-002 posting off), OS-043 boot checklist,
//!   OS-084 banner, INT-031 rollback pins, smoke checklist
//! - DSH-019 accessibility: DSH-018 palette WCAG contrast ratios

/// Brief kinds (BRF-042 / FND-032): exactly morning | onjoin | ondemand.
pub const BRIEF_KINDS: &[&str] = &["morning", "onjoin", "ondemand"];

/// Stale at age >= 2h (BRF-043).
pub const BRIEF_STALE_SECONDS: i64 = 7200;

/// Visual-check verdicts (STR-004 ground truth).
pub const VERDICTS: &[&str] = &["build ok", "build broken", "unclear"];

/// BRF-042 brief payload record: `id` is `brief:<room>:<ts>`, `kind`
/// is one of [`BRIEF_KINDS`], `generated_at` is the brief timestamp,
/// `age_seconds` is its age at render, and `template` marks a
/// template brief (never shown as if Spark wrote it).
#[derive(Debug, Clone, PartialEq)]
pub struct BriefPayload {
    pub id: String,
    pub room: String,
    pub kind: String,
    pub generated_at: i64,
    pub age_seconds: i64,
    pub template: bool,
}

/// Validate the BRF-042 payload shape. `id` must be `brief:<room>:<ts>`.
pub fn validate_brief_payload(p: &BriefPayload) -> Result<(), String> {
    if !BRIEF_KINDS.contains(&p.kind.as_str()) {
        return Err(format!("bad brief kind: {}", p.kind));
    }
    let want = format!("brief:{}:{}", p.room, p.generated_at);
    if p.id != want {
        return Err(format!("bad brief id: {}", p.id));
    }
    if p.room.is_empty() || p.generated_at < 0 || p.age_seconds < 0 {
        return Err("bad brief timestamps".to_string());
    }
    Ok(())
}

/// Template briefs are never displayed as if Spark wrote them.
pub fn template_marker(template: bool) -> Option<&'static str> {
    template.then_some("TEMPLATE")
}

/// BRF-043 staleness: stale at age >= [`BRIEF_STALE_SECONDS`] (2h).
pub fn is_stale(age_seconds: i64) -> bool {
    age_seconds >= BRIEF_STALE_SECONDS
}

/// BRF-043 stale label: `None` while fresh, otherwise
/// `"<age> old — regenerate for current state"`.
pub fn stale_label(age_seconds: i64) -> Option<String> {
    if !is_stale(age_seconds) {
        return None;
    }
    Some(format!("{} old — regenerate for current state", human_age(age_seconds)))
}

fn human_age(secs: i64) -> String {
    if secs < 3600 {
        format!("{} min ago", secs / 60)
    } else {
        format!("{} h {} min", secs / 3600, (secs % 3600) / 60)
    }
}

/// DSH-018 palette foregrounds (DSH-019 accessibility audit).
pub const PALETTE_FOREGROUNDS: &[(&str, &str)] = &[
    ("critical", "#f85149"),
    ("warning", "#d29922"),
    ("info", "#58a6ff"),
    ("muted", "#8b949e"),
    ("working", "#3fb950"),
    ("body", "#c9d1d9"),
];

/// Panel backgrounds the DSH-018 foregrounds render on.
pub const PALETTE_BACKGROUNDS: &[&str] = &["#0d1117", "#161b22"];

/// WCAG relative luminance of a `#rrggbb` color, mirroring the
/// `test_dashboard_accessibility.py` audit math exactly.
pub fn wcag_luminance(hex: &str) -> f64 {
    let channel = |i: usize| -> f64 {
        let v = u8::from_str_radix(&hex[i..i + 2], 16).unwrap_or(0) as f64 / 255.0;
        if v <= 0.03928 {
            v / 12.92
        } else {
            ((v + 0.055) / 1.055).powf(2.4)
        }
    };
    0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5)
}

/// WCAG contrast ratio between two `#rrggbb` colors.
pub fn wcag_contrast_ratio(fg: &str, bg: &str) -> f64 {
    let (a, b) = (wcag_luminance(fg), wcag_luminance(bg));
    (a.max(b) + 0.05) / (a.min(b) + 0.05)
}

/// Unknown verdicts render verbatim with `?`, never mapped.
pub fn verdict_icon(verdict: &str) -> (&str, &str) {
    match verdict {
        "build ok" => ("✓", verdict),
        "build broken" => ("✗", verdict),
        "unclear" => ("?", verdict),
        other => ("?", other),
    }
}

/// DSH-031: Blocked open, the other four closed by default.
pub fn default_open(section: &str) -> bool {
    section == "blocked"
}

/// DSH-031 / INT-025: the five Brief sections in render order.
/// The keys are the record's section keys; the display titles are
/// what the panel renders in each `<summary>` (pinned by
/// test_dashboard_brief_sections.py and
/// test_intel_brief_dashboard_consistency.py).
pub const BRIEF_SECTION_ORDER: &[&str] =
    &["decisions", "in_flight", "owners", "blocked", "watch_items"];

/// DSH-031 / INT-025 display title for a Brief section key, in
/// [`BRIEF_SECTION_ORDER`]; `None` for an unknown section key.
pub fn brief_section_title(section: &str) -> Option<&'static str> {
    match section {
        "decisions" => Some("Decisions"),
        "in_flight" => Some("In flight"),
        "owners" => Some("Owners"),
        "blocked" => Some("Blocked and why"),
        "watch_items" => Some("Watch items"),
        _ => None,
    }
}

/// DSH-013 alerts-feed card: id, creation timestamp, and whether
/// the alert is resolved (resolved cards collapse to the count).
#[derive(Debug, Clone, PartialEq)]
pub struct AlertCard {
    pub id: String,
    pub created_at: i64,
    pub resolved: bool,
}

/// DSH-013 feed: newest first, ties break on id (stable).
pub fn alerts_feed(mut cards: Vec<AlertCard>) -> Vec<AlertCard> {
    cards.sort_by(|a, b| (b.created_at, &b.id).cmp(&(a.created_at, &a.id)));
    cards
}

/// Only open cards are addressable (DSH-014: resolved collapse to the count).
pub fn addressable_cards(cards: &[AlertCard]) -> Vec<&AlertCard> {
    cards.iter().filter(|c| !c.resolved).collect()
}

/// DSH-022 deep links. Non-intel hashes parse to nothing.
#[derive(Debug, Clone, PartialEq)]
pub enum DeepLink {
    Brief(String),
    Alert(String),
}

/// DSH-022 deep-link parse: `#intel/brief/<id>` and
/// `#intel/alert/<id>` resolve; anything else, and an empty id,
/// parses to nothing.
pub fn parse_deep_link(hash: &str) -> Option<DeepLink> {
    let h = hash.strip_prefix('#')?;
    let rest = h.strip_prefix("intel/")?;
    if let Some(id) = rest.strip_prefix("brief/") {
        if id.is_empty() {
            return None;
        }
        Some(DeepLink::Brief(id.to_string()))
    } else if let Some(id) = rest.strip_prefix("alert/") {
        if id.is_empty() {
            return None;
        }
        Some(DeepLink::Alert(id.to_string()))
    } else {
        None
    }
}

/// A brief link resolves only inside the 7-brief history window.
pub fn resolve_brief_link(id: &str, history_ts: &[i64]) -> Option<i64> {
    id.parse::<i64>().ok().filter(|ts| history_ts.contains(ts))
}

/// DSH-028: exact `demo=1` query param enables demo mode.
/// `demo=10` (prefix trap), empty, or absent stays off.
pub fn demo_mode_on(query: &str) -> bool {
    query.split('&').any(|pair| {
        let mut kv = pair.splitn(2, '=');
        kv.next() == Some("demo") && kv.next() == Some("1")
    })
}

/// DSH-032 today counters record: jobs done, briefs, alerts fired,
/// and alerts resolved, as rendered in the "today" line.
#[derive(Debug, Clone, PartialEq)]
pub struct TodayCounts {
    pub jobs_done: usize,
    pub briefs: usize,
    pub alerts_fired: usize,
    pub alerts_resolved: usize,
}

/// DSH-032: briefs count distinct timestamps (history + current deduped).
pub fn today_counts(
    jobs_done_today: usize,
    brief_ts: &[i64],
    alerts_fired_today: usize,
    alerts_resolved_today: usize,
) -> TodayCounts {
    let mut uniq = brief_ts.to_vec();
    uniq.sort();
    uniq.dedup();
    TodayCounts {
        jobs_done: jobs_done_today,
        briefs: uniq.len(),
        alerts_fired: alerts_fired_today,
        alerts_resolved: alerts_resolved_today,
    }
}

/// DSH-032 record-level counting. The viewer used its local date; the
/// Python fixtures are zone-agnostic by construction (-1h/-2h same day,
/// -25h previous day in either zone), so the port uses the UTC calendar
/// day (timestamp / 86400). A record missing the relevant timestamp is
/// never counted.
pub fn same_day(a: i64, b: i64) -> bool {
    a.div_euclid(86400) == b.div_euclid(86400)
}

/// DSH-032 job record for record-level counting: only status
/// `"done"` with a same-day `done_at` counts as done today.
#[derive(Debug, Clone, PartialEq)]
pub struct TodayJob {
    pub status: String,
    pub done_at: Option<i64>,
}

/// DSH-032 alert record for record-level counting: a same-day
/// `created_at` counts as fired, a same-day `resolved_at` as
/// resolved, independently of each other.
#[derive(Debug, Clone, PartialEq)]
pub struct TodayAlert {
    pub created_at: Option<i64>,
    pub resolved_at: Option<i64>,
}

/// DSH-032: count from the records the panels already read. Jobs need
/// status "done" + a same-day `done_at`; briefs count distinct same-day
/// timestamps across the history window plus the current brief (a brief
/// that is also the newest history entry counts once); alerts count a
/// same-day `created_at` as fired and a same-day `resolved_at` as
/// resolved, independently of each other.
pub fn count_today_records(
    jobs: &[TodayJob],
    history_ts: &[i64],
    current_brief_ts: Option<i64>,
    alerts: &[TodayAlert],
    now: i64,
) -> TodayCounts {
    let jobs_done = jobs
        .iter()
        .filter(|j| j.status == "done" && j.done_at.map_or(false, |t| same_day(t, now)))
        .count();
    let mut brief_day: Vec<i64> = history_ts
        .iter()
        .copied()
        .filter(|t| same_day(*t, now))
        .collect();
    if let Some(t) = current_brief_ts {
        if same_day(t, now) {
            brief_day.push(t);
        }
    }
    brief_day.sort();
    brief_day.dedup();
    let alerts_fired = alerts
        .iter()
        .filter(|a| a.created_at.map_or(false, |t| same_day(t, now)))
        .count();
    let alerts_resolved = alerts
        .iter()
        .filter(|a| a.resolved_at.map_or(false, |t| same_day(t, now)))
        .count();
    TodayCounts {
        jobs_done,
        briefs: brief_day.len(),
        alerts_fired,
        alerts_resolved,
    }
}

/// DSH-032 header-strip line, exact wording from the fixture.
pub fn today_line(c: &TodayCounts) -> String {
    format!(
        "today · jobs done {} · briefs {} · alerts fired {} / resolved {}",
        c.jobs_done, c.briefs, c.alerts_fired, c.alerts_resolved
    )
}

/// DSH-021 error rows. A rejected token (401/403) renders the token row;
/// any other read failure renders unreachable; empty reads are empty
/// states, never errors; panels degrade independently.
#[derive(Debug, Clone, PartialEq)]
pub enum SourceError {
    TokenRejected,
    Unreachable,
}

/// DSH-021 error-row text for a panel: a rejected token names the
/// token row; any other read failure names the paused bus store.
pub fn error_row(panel: &str, err: &SourceError) -> String {
    match err {
        SourceError::TokenRejected => {
            format!("No token, or this token can't read {panel}. Paste a token above to load {panel}.")
        }
        SourceError::Unreachable => {
            format!("Can't reach the bus store — {panel} is paused. The log above is unaffected.")
        }
    }
}

/// GOV-002: viewer posting is off; "Brief me now" ships disabled.
pub fn brief_me_now_enabled() -> (bool, &'static str) {
    (false, "posting is off for this build")
}

/// DSH-038: dispatch approve is request-only; the CLI posts, never the panel.
pub fn dispatch_approve_is_request_only() -> bool {
    true
}

/// DSP-040: dispatch never auto-posts.
pub fn dispatch_may_auto_post() -> bool {
    false
}

/// INT-031 rollback pins: the runbook must name these exact steps.
pub const ROLLBACK_STEPS: &[&str] = &[
    "Deployments",
    "All deployments",
    "Rollback to this deployment",
    "muse-relay-live",
];

/// INT-031 rollback-runbook check: the runbook must name every
/// [`ROLLBACK_STEPS`] step, plus the valid-target rule, the
/// preview-invalid rule, the official docs citation, and an explicit
/// previous production deployment id.
pub fn rollback_runbook_ok(runbook: &str) -> Result<(), String> {
    for step in ROLLBACK_STEPS {
        if !runbook.contains(step) {
            return Err(format!("missing rollback step: {step}"));
        }
    }
    if !runbook.contains("successfully built") {
        return Err("missing valid-target rule".to_string());
    }
    if !runbook.contains("Preview deployments are **not** valid") {
        return Err("missing preview-invalid rule".to_string());
    }
    if !runbook.contains("https://developers.cloudflare.com/pages/configuration/rollbacks/") {
        return Err("missing official docs citation".to_string());
    }
    if !runbook.contains("Previous production deployment id") {
        return Err("previous deployment id not explicitly addressed".to_string());
    }
    Ok(())
}

/// §7 crew-board rules (DSH-023, DSH-024, DSH-025, OS-084 artifact
/// part) + the keyless signing builders (test_crewboard_signing).
/// The card/detail HTML rendering itself lives in the fold-excluded
/// `crew-board.html` and stays exclusion-blocked; what is ported here
/// is the rule each renderer applies, checked against the exact
/// fixture values of the five `test_crewboard_*.py` files.

/// Escape `&`, `<`, `>` for HTML text/attribute rendering, `&` first
/// (so an input `&amp;` becomes `&amp;amp;`, as the fixtures show).
pub fn html_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            _ => out.push(c),
        }
    }
    out
}

/// Percent-encode an alert id for the §8 hash route, as the ribbon
/// fixtures show: `alert:1` -> `alert%3A1`, `alert:<x>` ->
/// `alert%3A%3Cx%3E`. Alphanumerics and `-_.~` pass through.
pub fn route_encode_id(id: &str) -> String {
    let mut out = String::new();
    for b in id.bytes() {
        let c = b as char;
        if c.is_ascii_alphanumeric() || matches!(c, '-' | '_' | '.' | '~') {
            out.push(c);
        } else {
            out.push_str(&format!("%{b:02X}"));
        }
    }
    out
}

/// One §6 alert record, as the ribbon fixtures carry it.
#[derive(Debug, Clone, PartialEq)]
pub struct CrewAlert {
    pub id: Option<String>,
    pub kind: String,
    pub severity: String,
    pub status: Option<String>,
    pub resolved_at: Option<i64>,
    pub subjects: Vec<String>,
}

/// The ribbon a job card carries, if any: escaped kind text plus the
/// §8 hash-route link, or no link when the alert has no id.
#[derive(Debug, Clone, PartialEq)]
pub struct Ribbon {
    pub text: String,
    pub href: Option<String>,
}

fn subject_names_job(subject: &str, job_id: &str) -> bool {
    let s = subject.trim();
    if s == job_id {
        return true;
    }
    // The store names jobs bare ("42"); the spec §6 example names
    // them "job 42" — both forms match, case-insensitively.
    let lower = s.to_ascii_lowercase();
    if let Some(rest) = lower.strip_prefix("job ") {
        return rest.trim() == job_id;
    }
    false
}

/// DSH-025: the first open critical alert naming the job wins.
/// Warning/info alerts never ribbon; resolved alerts (status
/// `resolved`, or a legacy `resolved_at`) never ribbon; an
/// acknowledged alert is still outstanding, so it keeps its ribbon.
pub fn alert_ribbon(job_id: &str, alerts: &[CrewAlert]) -> Option<Ribbon> {
    for a in alerts {
        if a.severity.to_ascii_lowercase() != "critical" {
            continue;
        }
        if a.status.as_deref() == Some("resolved") || a.resolved_at.is_some() {
            continue;
        }
        if !a.subjects.iter().any(|s| subject_names_job(s, job_id)) {
            continue;
        }
        return Some(Ribbon {
            text: format!("critical alert: {}", html_escape(&a.kind)),
            href: a
                .id
                .as_ref()
                .map(|id| format!("bus.html#intel/alert/{}", route_encode_id(id))),
        });
    }
    None
}

/// DSH-024 attempts badge: text `attempts a/m`, neutral below
/// max-1, amber at max-1, red at max and over. Absent when either
/// field is absent, blank, or non-numeric.
#[derive(Debug, Clone, PartialEq)]
pub struct AttemptsBadge {
    pub text: String,
    pub class: String,
}

/// DSH-024 attempts badge: parses `attempts`/`max_attempts` as
/// integers (absent, blank, or non-numeric -> no badge) and picks
/// the pill class — neutral below max-1, warn at max-1, danger at
/// max and over.
pub fn attempts_badge(
    attempts: Option<&str>,
    max_attempts: Option<&str>,
) -> Option<AttemptsBadge> {
    let a: i64 = attempts?.trim().parse().ok()?;
    let m: i64 = max_attempts?.trim().parse().ok()?;
    let class = if a >= m {
        "pill attempts danger"
    } else if a == m - 1 {
        "pill attempts warn"
    } else {
        "pill attempts"
    };
    Some(AttemptsBadge {
        text: format!("attempts {a}/{m}"),
        class: class.to_string(),
    })
}

/// DSH-023 files line: comma-split, blank tokens dropped, each file
/// name HTML-escaped. Absent (old jobs, blank fields) -> None.
pub fn files_line(files: Option<&str>) -> Option<String> {
    let parts: Vec<String> = files?
        .split(',')
        .map(|t| t.trim())
        .filter(|t| !t.is_empty())
        .map(html_escape)
        .collect();
    if parts.is_empty() {
        None
    } else {
        Some(format!("files: {}", parts.join(", ")))
    }
}

/// DSH-023 deps line: comma-split, blank tokens dropped, each dep
/// rendered `#n`. Absent (old jobs, blank fields) -> None.
pub fn deps_line(deps: Option<&str>) -> Option<String> {
    let parts: Vec<&str> = deps?
        .split(',')
        .map(|t| t.trim())
        .filter(|t| !t.is_empty())
        .collect();
    if parts.is_empty() {
        None
    } else {
        Some(format!(
            "deps: {}",
            parts
                .iter()
                .map(|t| format!("#{t}"))
                .collect::<Vec<_>>()
                .join(", ")
        ))
    }
}

/// One OS-083 attach() artifact entry, as the OS-084 fixtures carry it.
#[derive(Debug, Clone, PartialEq)]
pub struct Artifact {
    pub path: Option<String>,
    pub reference: String,
    pub version: i64,
    pub sha256: String,
}

/// A rendered artifact link: escaped store-relative path, file name
/// plus version as the label, reference as the title.
#[derive(Debug, Clone, PartialEq)]
pub struct ArtifactLink {
    pub href: String,
    pub label: String,
    pub title: String,
}

/// OS-084 artifact part: absolute, escaping (`..` segment),
/// empty-segment, or missing paths are dropped, never linked.
pub fn artifact_link(a: &Artifact) -> Option<ArtifactLink> {
    let path = a.path.as_deref()?;
    if path.starts_with('/') {
        return None;
    }
    let segments: Vec<&str> = path.split('/').collect();
    if segments.iter().any(|s| s.is_empty() || *s == "..") {
        return None;
    }
    let name = segments.last()?;
    Some(ArtifactLink {
        href: html_escape(path),
        label: format!("{} v{}", html_escape(name), a.version),
        title: html_escape(&a.reference),
    })
}

/// JSON string encoding with `ensure_ascii=True`, as `pyStr` in the
/// signing test must match Python's `json.dumps(case, ensure_ascii=True)`:
/// ASCII passes through (DEL included), non-ASCII becomes `\uXXXX`,
/// astral characters become surrogate pairs.
pub fn py_str_json(s: &str) -> String {
    let mut out = String::from("\"");
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{08}' => out.push_str("\\b"),
            '\u{0C}' => out.push_str("\\f"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c if (c as u32) <= 0x7f => out.push(c),
            c if (c as u32) <= 0xFFFF => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => {
                let v = c as u32 - 0x10000;
                out.push_str(&format!(
                    "\\u{:04x}\\u{:04x}",
                    0xD800 + (v >> 10),
                    0xDC00 + (v & 0x3FF)
                ));
            }
        }
    }
    out.push('"');
    out
}

/// Nonce shape from the signing test: exactly 16 lowercase hex chars.
/// Nonce generation itself is random in the viewer; only the shape
/// rule is ported here.
pub fn is_nonce_hex(s: &str) -> bool {
    s.len() == 16
        && s.bytes()
            .all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f'))
}

/// DSH-014 alert lifecycle (WDG-014, mirrored from
/// `os/intel/store.py`): open -> acknowledged -> resolved. The
/// card HTML rendering and the Node driver halves of
/// `test_dashboard_alert_lifecycle.py` read the fold-excluded
/// viewer and stay exclusion-blocked; what is ported here is the
/// transition rule the driver pins, checked against the same
/// fixture values (alert:1 open critical, alert:2 acknowledged
/// warning, alert:3 resolved info).

/// One alert record, lifecycle fields only.
#[derive(Debug, Clone, PartialEq)]
pub struct LifecycleAlert {
    pub id: String,
    pub severity: String,
    pub status: Option<String>,
    pub acknowledged_at: Option<i64>,
    pub acknowledged_by: Option<String>,
    pub resolved_at: Option<i64>,
}

/// WDG-014 status, legacy-safe: an explicit status wins when it is
/// one of open/acknowledged/resolved; a pre-WDG-014 record derives
/// it from timestamps (resolved_at -> resolved, acknowledged_at ->
/// acknowledged, otherwise open).
pub fn alert_lifecycle_status(a: &LifecycleAlert) -> &'static str {
    if let Some(s) = a.status.as_deref() {
        if matches!(s, "open" | "acknowledged" | "resolved") {
            return match s {
                "open" => "open",
                "acknowledged" => "acknowledged",
                _ => "resolved",
            };
        }
    }
    if a.resolved_at.is_some() {
        "resolved"
    } else if a.acknowledged_at.is_some() {
        "acknowledged"
    } else {
        "open"
    }
}

/// Outcome of an ack/resolve attempt, in the driver-visible words
/// of `test_dashboard_alert_lifecycle.py`.
#[derive(Debug, Clone, PartialEq)]
pub enum LifecycleResult {
    Acknowledged(LifecycleAlert),
    AlreadyAcknowledged,
    RefusedResolved,
    Resolved(LifecycleAlert),
    AlreadyResolved,
    NotFound,
}

fn find_alert_mut<'a>(
    alerts: &'a mut [LifecycleAlert],
    id: &str,
) -> Option<&'a mut LifecycleAlert> {
    alerts.iter_mut().find(|a| a.id == id)
}

/// WDG-014 ack: open -> acknowledged, stamping now and by. Re-ack
/// is idempotent (stamp untouched); acking a resolved alert is
/// refused; a missing id is not found. Mirrors
/// `os/intel/store.py::acknowledge_alert` (None -> NotFound,
/// ValueError on resolved -> RefusedResolved).
pub fn acknowledge_alert(
    alerts: &mut [LifecycleAlert],
    id: &str,
    now: i64,
    by: &str,
) -> LifecycleResult {
    let Some(a) = find_alert_mut(alerts, id) else {
        return LifecycleResult::NotFound;
    };
    match alert_lifecycle_status(a) {
        "resolved" => LifecycleResult::RefusedResolved,
        "acknowledged" => LifecycleResult::AlreadyAcknowledged,
        _ => {
            a.status = Some("acknowledged".to_string());
            a.acknowledged_at = Some(now);
            a.acknowledged_by = Some(by.to_string());
            LifecycleResult::Acknowledged(a.clone())
        }
    }
}

/// WDG-014 resolve: open/acknowledged -> resolved, stamping now
/// and keeping any acknowledged_at/by, so the record shows the
/// full walk. Re-resolve is idempotent; a missing id is not
/// found. Mirrors `os/intel/store.py::resolve_alert`.
pub fn resolve_alert(
    alerts: &mut [LifecycleAlert],
    id: &str,
    now: i64,
) -> LifecycleResult {
    let Some(a) = find_alert_mut(alerts, id) else {
        return LifecycleResult::NotFound;
    };
    if alert_lifecycle_status(a) == "resolved" {
        return LifecycleResult::AlreadyResolved;
    }
    a.status = Some("resolved".to_string());
    a.resolved_at = Some(now);
    LifecycleResult::Resolved(a.clone())
}

/// Header critical count (DSH-014): only unresolved criticals
/// count — a resolved critical leaves the count.
pub fn unresolved_critical_count(alerts: &[LifecycleAlert]) -> usize {
    alerts
        .iter()
        .filter(|a| {
            a.severity.to_ascii_lowercase() == "critical"
                && alert_lifecycle_status(a) != "resolved"
        })
        .count()
}

/// DSH-014 resolved-collapse count: the number behind the
/// panel's "N resolved" line. The collapse rendering itself is
/// HTML over the fold-excluded viewer and stays
/// exclusion-blocked; only the count rule is ported here.
pub fn resolved_count(alerts: &[LifecycleAlert]) -> usize {
    alerts
        .iter()
        .filter(|a| alert_lifecycle_status(a) == "resolved")
        .count()
}

/// DSH-014 / spec §0: the live viewer write is gated off until
/// Dale's viewer posting decision lands — the buttons ship
/// disabled with this note, and no live write path exists.
pub fn alert_write_enabled() -> (bool, &'static str) {
    (false, "posting is off for this build")
}

/// Keyless rename log entry (signing test): v=1, cmd=rename, args,
/// actor — and no `sig` key, since renames are keyless now.
#[derive(Debug, Clone, PartialEq)]
pub struct RenameLogEntry {
    pub actor: String,
    pub nick: String,
    pub display: String,
}

impl RenameLogEntry {
    /// Keyless rename log JSON: `{"v":1,"cmd":"rename","args":{"nick":…,
    /// "display":…},"actor":…}` with [`py_str_json`] string encoding
    /// and no `sig` key.
    pub fn to_json(&self) -> String {
        format!(
            "{{\"v\":1,\"cmd\":\"rename\",\"args\":{{\"nick\":{},\"display\":{}}},\"actor\":{}}}",
            py_str_json(&self.nick),
            py_str_json(&self.display),
            py_str_json(&self.actor)
        )
    }
}

/// Name-registry entry written by a keyless rename.
#[derive(Debug, Clone, PartialEq)]
pub struct NamesHashEntry {
    pub display: String,
    pub set_by: String,
    pub set_at: i64,
}

impl NamesHashEntry {
    /// Name-registry JSON: `{"display":…,"set_by":…,"set_at":…}` with
    /// [`py_str_json`] string encoding.
    pub fn to_json(&self) -> String {
        format!(
            "{{\"display\":{},\"set_by\":{},\"set_at\":{}}}",
            py_str_json(&self.display),
            py_str_json(&self.set_by),
            self.set_at
        )
    }
}

/// Name-history entry written by a keyless rename.
#[derive(Debug, Clone, PartialEq)]
pub struct NamesHistoryEntry {
    pub nick: String,
    pub display: String,
    pub set_by: String,
    pub set_at: i64,
}

impl NamesHistoryEntry {
    /// Name-history JSON: `{"nick":…,"display":…,"set_by":…,"set_at":…}`
    /// with [`py_str_json`] string encoding.
    pub fn to_json(&self) -> String {
        format!(
            "{{\"nick\":{},\"display\":{},\"set_by\":{},\"set_at\":{}}}",
            py_str_json(&self.nick),
            py_str_json(&self.display),
            py_str_json(&self.set_by),
            self.set_at
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn payload() -> BriefPayload {
        BriefPayload {
            id: "brief:main:100".into(),
            room: "main".into(),
            kind: "morning".into(),
            generated_at: 100,
            age_seconds: 900,
            template: false,
        }
    }

    #[test]
    fn brief_contract_validates() {
        assert!(validate_brief_payload(&payload()).is_ok());
        let mut bad = payload();
        bad.kind = "evening".into();
        assert!(validate_brief_payload(&bad).is_err());
        bad = payload();
        bad.id = "brief:other:100".into();
        assert!(validate_brief_payload(&bad).is_err());
    }

    #[test]
    fn staleness_threshold() {
        assert!(!is_stale(7199));
        assert!(is_stale(7200));
        assert!(stale_label(12600).unwrap().contains("regenerate"));
        assert!(stale_label(900).is_none());
    }

    #[test]
    fn verdicts_never_remapped() {
        assert_eq!(verdict_icon("build ok").0, "✓");
        assert_eq!(verdict_icon("weird"), ("?", "weird"));
    }

    #[test]
    fn deep_links_parse() {
        assert_eq!(parse_deep_link("#intel/brief/123"), Some(DeepLink::Brief("123".into())));
        assert_eq!(parse_deep_link("#intel/alert/a1"), Some(DeepLink::Alert("a1".into())));
        assert_eq!(parse_deep_link("#other/x"), None);
        assert_eq!(parse_deep_link("#intel/brief/"), None);
    }

    #[test]
    fn demo_prefix_trap() {
        assert!(demo_mode_on("demo=1"));
        assert!(demo_mode_on("a=1&demo=1&b=2"));
        assert!(!demo_mode_on("demo=10"));
        assert!(!demo_mode_on(""));
    }

    #[test]
    fn today_briefs_dedupe() {
        let c = today_counts(2, &[1, 1, 2], 3, 1);
        assert_eq!((c.jobs_done, c.briefs), (2, 2));
    }

    #[test]
    fn today_records_match_fixture() {
        // os/tests/test_dashboard_today_counters.py fixture values:
        // NOW 1793102100 (2026-10-27 07:55 EDT / 11:55 UTC).
        let now = 1793102100;
        let today = now - 3600;
        let today_brief = now - 7200;
        let yesterday = now - 90000;
        let jobs = vec![
            TodayJob { status: "done".into(), done_at: Some(today) },
            TodayJob { status: "done".into(), done_at: Some(yesterday) },
            TodayJob { status: "done".into(), done_at: None },
            TodayJob { status: "open".into(), done_at: None },
        ];
        let alerts = vec![
            TodayAlert { created_at: Some(today), resolved_at: Some(today) },
            TodayAlert { created_at: Some(today), resolved_at: None },
            TodayAlert { created_at: Some(yesterday), resolved_at: Some(today) },
            TodayAlert { created_at: Some(yesterday), resolved_at: None },
            TodayAlert { created_at: None, resolved_at: Some(today) },
        ];
        // Step 1: current brief is also the newest history entry: counts once.
        let c = count_today_records(
            &jobs,
            &[yesterday, today_brief],
            Some(today_brief),
            &alerts,
            now,
        );
        assert_eq!(
            (c.jobs_done, c.briefs, c.alerts_fired, c.alerts_resolved),
            (1, 1, 2, 3)
        );
        assert_eq!(
            today_line(&c),
            "today · jobs done 1 · briefs 1 · alerts fired 2 / resolved 3"
        );
        // Step 2: a current brief with no history entry still counts once.
        let c2 = count_today_records(&jobs, &[], Some(today), &alerts, now);
        assert_eq!(c2.briefs, 1);
        // Step 3: a yesterday brief counts zero.
        let c3 = count_today_records(&jobs, &[], Some(yesterday), &alerts, now);
        assert_eq!(c3.briefs, 0);
    }
}
