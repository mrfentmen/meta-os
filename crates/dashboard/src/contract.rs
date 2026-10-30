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

pub fn is_stale(age_seconds: i64) -> bool {
    age_seconds >= BRIEF_STALE_SECONDS
}

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

/// DSH-021 error rows. A rejected token (401/403) renders the token row;
/// any other read failure renders unreachable; empty reads are empty
/// states, never errors; panels degrade independently.
#[derive(Debug, Clone, PartialEq)]
pub enum SourceError {
    TokenRejected,
    Unreachable,
}

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

/// Keyless rename log entry (signing test): v=1, cmd=rename, args,
/// actor — and no `sig` key, since renames are keyless now.
#[derive(Debug, Clone, PartialEq)]
pub struct RenameLogEntry {
    pub actor: String,
    pub nick: String,
    pub display: String,
}

impl RenameLogEntry {
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
}
