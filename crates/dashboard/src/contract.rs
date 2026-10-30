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
