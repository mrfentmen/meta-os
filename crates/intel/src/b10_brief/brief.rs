//! Port of `os/intel/brief.py` — the brief engine surface.
//!
//! Frozen shapes: `BRIEF:<room>:<ts>` records, `brief --since` windows,
//! budget trimming (never invent), secret redaction, verbatim quotes.
//! This module ports the pure record/window/format layer; Spark
//! composition (`compose_spark_brief`) stays behind the B11 client trait
//! and is represented here as an injected renderer so tests stay offline.

use std::collections::HashMap;

#[derive(Debug, Clone, PartialEq)]
pub struct BriefRecord {
    pub room: String,
    pub ts: i64,
    pub text: String,
    pub kind: String,
}

pub fn brief_index_key(room: &str) -> String {
    format!("muse-bus:intel:brief:index:{room}")
}

/// Parse `--since` windows: "2h", "3d", "45m", "all", or a unix ts.
pub fn parse_since(s: &str, now: i64) -> Result<Option<i64>, String> {
    let t = s.trim();
    if t.eq_ignore_ascii_case("all") {
        return Ok(None);
    }
    if let Ok(ts) = t.parse::<i64>() {
        if ts >= 0 {
            return Ok(Some(ts));
        }
        return Err(format!("bad --since: {s}"));
    }
    let (num, unit) = t.split_at(t.len().saturating_sub(1));
    let n: i64 = num.parse().map_err(|_| format!("bad --since: {s}"))?;
    let secs = match unit {
        "m" => n * 60,
        "h" => n * 3600,
        "d" => n * 86400,
        _ => return Err(format!("bad --since: {s}")),
    };
    Ok(Some(now - secs))
}

/// Validate a brief record (room/ts/text required; kind known).
pub fn validate_brief_record(r: &BriefRecord) -> Result<(), String> {
    if r.room.is_empty() {
        return Err("brief: missing room".to_string());
    }
    if r.ts < 0 {
        return Err("brief: bad ts".to_string());
    }
    if r.text.trim().is_empty() {
        return Err("brief: empty text".to_string());
    }
    const KINDS: &[&str] = &["morning", "ondemand", "boot", "onjoin", "daily"];
    if !KINDS.contains(&r.kind.as_str()) {
        return Err(format!("brief: unknown kind {}", r.kind));
    }
    Ok(())
}

/// Frozen announcement line for a stored brief.
pub fn format_brief_announcement(room: &str, ts: i64) -> String {
    format!("BRIEF:{room}:{ts}")
}

pub fn brief_failure_line(room: &str, err: &str) -> String {
    format!("Brief for {room} failed: {err}")
}

/// Frozen brief constants from `os/intel/brief.py` (BRF-007/028).
pub const BRIEF_SECTIONS: &[&str] =
    &["Decisions", "In flight", "Owners", "Blocked and why", "Watch items"];
pub const BRIEF_KINDS: &[&str] = &["morning", "onjoin", "ondemand"];
/// BRF-028: regeneration guard window in seconds.
pub const BRIEF_REGENERATION_WINDOW_SECONDS: i64 = 300;

/// Word budget per brief kind (BRIEF_BUDGETS); None for unknown kinds.
pub fn brief_budget(kind: &str) -> Option<usize> {
    match kind {
        "morning" => Some(220),
        "onjoin" => Some(150),
        "ondemand" => Some(300),
        _ => None,
    }
}

/// BRF-026: the canned one-liner for a brief failure kind.
///
/// This is Python's `brief_failure_line(kind)`; it raises (here: Err)
/// on an unknown kind — a failure line must never be invented.
pub fn failure_copy_for_kind(kind: &str) -> Result<&'static str, String> {
    match kind {
        "unavailable" => Ok("No brief is available right now. Try again in a few minutes."),
        "spark_down" => Ok("The brief writer is down, so no fresh brief could be written. Try again later."),
        "no_data" => Ok("No brief yet, this room has no activity to brief on."),
        _ => Err(format!("unknown brief failure kind: '{kind}'")),
    }
}

/// BRF-007 rewrite pass: cut a brief to its word budget.
///
/// Drops bullet lines (`- `) from the end first, keeping section
/// headings and the window line. If still over budget with no
/// bullets left, truncates by words with a ` (trimmed)` marker.
/// A brief already within budget is returned unchanged.
/// Ported oddity: Python slices `words[:budget - 1]`, so a zero
/// budget keeps all but the last word; that is preserved here.
pub fn trim_to_budget(text: &str, budget: usize) -> String {
    if text.split_whitespace().count() <= budget {
        return text.to_string();
    }
    let mut lines: Vec<&str> = text.split('\n').collect();
    while lines.join("\n").split_whitespace().count() > budget {
        match lines.iter().rposition(|l| l.starts_with("- ")) {
            Some(idx) => {
                lines.remove(idx);
            }
            None => break,
        }
    }
    let trimmed = lines.join("\n");
    if trimmed.split_whitespace().count() > budget {
        let words: Vec<&str> = trimmed.split_whitespace().collect();
        let end = if budget == 0 {
            words.len().saturating_sub(1)
        } else {
            budget - 1
        };
        let end = end.min(words.len());
        format!("{} (trimmed)", words[..end].join(" "))
    } else {
        trimmed
    }
}

/// BRF-007 prompt files per brief kind (v1), and the v2 files
/// (BRF-019): only morning and onjoin have a v2; ondemand has none
/// on purpose — a v2 request for ondemand gets no file, never a
/// silent v1 fallback under a v2 label.
pub const BRIEF_PROMPT_FILES: &[(&str, &str)] = &[
    ("morning", "brief_morning.md"),
    ("onjoin", "brief_onjoin.md"),
    ("ondemand", "brief_ondemand.md"),
];
pub const BRIEF_PROMPT_V2_FILES: &[(&str, &str)] = &[
    ("morning", "brief_morning_v2.md"),
    ("onjoin", "brief_onjoin_v2.md"),
];

/// BRF-007 follow-up: path of the prompt file for a kind.
/// `version` is "v1" or "v2"; anything else has no file, as do
/// unknown kinds and (for v2) ondemand. Those cases return None
/// instead of guessing a filename that does not exist.
/// `prompts_dir` overrides the carried fixtures dir; with None the
/// base is the crate's carried `fixtures/b10/prompts` (the Python
/// default is the prompts dir next to `brief.py`).
pub fn brief_prompt_path(
    kind: &str,
    prompts_dir: Option<&str>,
    version: &str,
) -> Option<String> {
    let files = match version {
        "v1" => BRIEF_PROMPT_FILES,
        "v2" => BRIEF_PROMPT_V2_FILES,
        _ => return None,
    };
    let name = files.iter().find(|(k, _)| *k == kind)?.1;
    let base = match prompts_dir {
        Some(d) => d.to_string(),
        None => format!("{}/fixtures/b10/prompts", env!("CARGO_MANIFEST_DIR")),
    };
    let base = base.trim_end_matches('/');
    Some(format!("{base}/{name}"))
}

/// BRF-007 follow-up: text of the prompt file for a kind.
/// Returns "" for an unknown kind, an unknown version, or an
/// unreadable file, never raising, so a missing prompt file can
/// never fail a brief: the composer then sends no system text.
pub fn load_brief_prompt(
    kind: &str,
    prompts_dir: Option<&str>,
    version: &str,
) -> String {
    match brief_prompt_path(kind, prompts_dir, version) {
        Some(path) => std::fs::read_to_string(path).unwrap_or_default(),
        None => String::new(),
    }
}

/// Trim snapshot text to a char budget without inventing content.
pub fn cap_snapshot_window(text: &str, budget: usize) -> String {
    if text.len() <= budget {
        return text.to_string();
    }
    format!("{}…[trimmed]", &text[..budget])
}

/// Redact `KEY=secret` values for known secret-ish keys.
pub fn redact_secrets(lines: &[String]) -> Vec<String> {
    lines
        .iter()
        .map(|l| {
            if let Some(eq) = l.find('=') {
                let key = l[..eq].to_uppercase();
                if key.contains("SECRET") || key.contains("TOKEN") || key.contains("KEY") {
                    return format!("{}=<redacted>", &l[..eq]);
                }
            }
            l.clone()
        })
        .collect()
}

pub fn brief_age_seconds(now: i64, ts: i64) -> i64 {
    (now - ts).max(0)
}

pub fn brief_exceeds_budget(text: &str, budget: usize) -> bool {
    text.len() > budget
}

/// OS-051: a previous-session record carried on a boot snapshot.
pub struct PreviousSession {
    pub last_brief_at: String,
    pub jobs_completed: Vec<String>,
    pub open_threads: Vec<String>,
}

/// OS-051: the one-line previous-session digest for a boot brief.
///
/// Returns None when there is no record or no last-brief time — a
/// boot brief with no previous-session record says nothing about a
/// previous session, never invents one. Empty titles are dropped;
/// the parenthesised title lists are dropped when a list is empty.
pub fn previous_session_digest(record: Option<&PreviousSession>) -> Option<String> {
    let record = record?;
    if record.last_brief_at.trim().is_empty() {
        return None;
    }
    let completed: Vec<&str> = record
        .jobs_completed
        .iter()
        .map(String::as_str)
        .filter(|t| !t.is_empty())
        .collect();
    let threads: Vec<&str> = record
        .open_threads
        .iter()
        .map(String::as_str)
        .filter(|t| !t.is_empty())
        .collect();
    let mut completed_part = format!(
        "{} job{} completed",
        completed.len(),
        if completed.len() == 1 { "" } else { "s" }
    );
    if !completed.is_empty() {
        completed_part.push_str(&format!(" ({})", completed.join("; ")));
    }
    let mut threads_part = format!(
        "{} open thread{}",
        threads.len(),
        if threads.len() == 1 { "" } else { "s" }
    );
    if !threads.is_empty() {
        threads_part.push_str(&format!(" ({})", threads.join("; ")));
    }
    Some(format!(
        "Previous session: last brief {}, {}, {}",
        record.last_brief_at, completed_part, threads_part
    ))
}

/// OS-062: the system-state input for a boot brief.
///
/// `None` fields mean "not reported in this snapshot"; a present
/// but empty list means "none reported" — never padded, never
/// guessed. A down gateway is reported as down, never omitted.
pub struct SystemState {
    pub drivers: Option<Vec<String>>,
    pub gateway_healthy: Option<bool>,
    pub skill_apps: Option<Vec<String>>,
}

/// OS-062: the three drivers + tools + apps lines, in that order,
/// one line each. These are not bullet lines, so the BRF-007
/// budget trim never drops them ahead of a watch item.
pub fn system_state_lines(state: &SystemState) -> Vec<String> {
    let drivers_line = match &state.drivers {
        None => "Drivers: not reported in this snapshot".to_string(),
        Some(drivers) => {
            let names: Vec<&str> = drivers
                .iter()
                .map(String::as_str)
                .filter(|n| !n.is_empty())
                .collect();
            if names.is_empty() {
                "Drivers: no drivers reported".to_string()
            } else {
                format!("Drivers: {} available", names.join(", "))
            }
        }
    };
    let tools_line = match state.gateway_healthy {
        Some(true) => "Tools: MCP gateway healthy".to_string(),
        Some(false) => {
            "Tools: MCP gateway down, so agents cannot reach their tools through it".to_string()
        }
        None => "Tools: MCP gateway health not reported in this snapshot".to_string(),
    };
    let apps_line = match &state.skill_apps {
        None => "Skill apps: not reported in this snapshot".to_string(),
        Some(apps) => {
            let names: Vec<&str> = apps
                .iter()
                .map(String::as_str)
                .filter(|n| !n.is_empty())
                .collect();
            if names.is_empty() {
                "Skill apps: no skill apps mounted".to_string()
            } else {
                format!("Skill apps: {} mounted", names.join(", "))
            }
        }
    };
    vec![drivers_line, tools_line, apps_line]
}

/// OS-127: the recovery input for a boot brief: the jobs the lease
/// sweep recovered at this boot, the sweep's own recovered count to
/// reconcile against, and any job records the sweep found corrupted.
/// `None` means the Python record lacked that key or it was not a
/// list / not an int — never padded, never guessed.
#[derive(Debug, Clone, PartialEq)]
pub struct RecoveryRecord {
    pub corrupted: Option<Vec<CorruptedEntry>>,
    pub recovered: Option<Vec<RecoveredEntry>>,
    pub sweep_count: Option<i64>,
}

/// One entry of a recovery record's `corrupted` list, as Python
/// reads it: a dict (id and/or title, either possibly absent) or a
/// plain string, or anything else (which names nothing).
#[derive(Debug, Clone, PartialEq)]
pub enum CorruptedEntry {
    Job { id: String, title: String },
    Plain(String),
    Other,
}

/// One entry of a recovery record's `recovered` list: a usable job
/// record (non-empty id and title) or an unreadable one. The caller
/// marks entries unreadable; a record that is not a dict, or has an
/// empty id or title, is unreadable in Python, never skipped.
#[derive(Debug, Clone, PartialEq)]
pub enum RecoveredEntry {
    Job { id: String, title: String, baton_step: BatonStep },
    Unreadable,
}

/// A recovered job's baton step, as Python reads it: an int step, a
/// non-empty string step verbatim, or anything else (not reported).
/// An empty string step counts as not reported, matching Python's
/// `isinstance(step, str) and step` check.
#[derive(Debug, Clone, PartialEq)]
pub enum BatonStep {
    Number(i64),
    Text(String),
    Missing,
}

/// OS-127: the one in-flight-jobs-recovered line for a boot brief.
///
/// The line is reconciled, not merely counted: a clean count is
/// rendered only when the sweep count equals the number of recovered
/// job records, and only then are the titles and baton steps named.
/// Any other shape says recovery is incomplete instead of a false
/// all-clear: a sweep count that disagrees with the record count, a
/// record with no sweep count to reconcile against, a corrupted job
/// (named, so the reader knows which job did not recover cleanly),
/// or an unreadable recovered record. A clean shutdown is a
/// reconciled record with zero recovered jobs, and it reads zero
/// recovered plainly. The line is not a bullet line, so the BRF-007
/// budget trim never drops it ahead of a watch item, and it is
/// redacted by the composer, not here.
///
/// `None` means the snapshot carries no recovery record at all.
pub fn recovery_line(record: Option<&RecoveryRecord>) -> String {
    const PREFIX: &str = "In-flight jobs recovered at this boot: ";
    let record = match record {
        None => return format!("{PREFIX}not reported in this snapshot"),
        Some(r) => r,
    };
    if let Some(corrupted) = &record.corrupted {
        if !corrupted.is_empty() {
            let mut names: Vec<String> = Vec::new();
            for job in corrupted {
                match job {
                    CorruptedEntry::Job { id, title } => {
                        if !id.is_empty() && !title.is_empty() {
                            names.push(format!("job {id} {title}"));
                        } else if !id.is_empty() {
                            names.push(format!("job {id}"));
                        } else if !title.is_empty() {
                            names.push(title.clone());
                        }
                    }
                    CorruptedEntry::Plain(s) => {
                        if !s.is_empty() {
                            names.push(s.clone());
                        }
                    }
                    CorruptedEntry::Other => {}
                }
            }
            if !names.is_empty() {
                let listed: Vec<String> = names
                    .iter()
                    .map(|n| format!("{n} has a corrupted record"))
                    .collect();
                return format!("{PREFIX}recovery incomplete, {}", listed.join("; "));
            }
            return format!(
                "{PREFIX}recovery incomplete, a corrupted job record could not be named"
            );
        }
    }
    let recovered: &[RecoveredEntry] = record.recovered.as_deref().unwrap_or(&[]);
    let mut usable: Vec<(&str, &str, &BatonStep)> = Vec::new();
    let mut unreadable = false;
    for job in recovered {
        match job {
            RecoveredEntry::Job { id, title, baton_step } => {
                usable.push((id.as_str(), title.as_str(), baton_step))
            }
            RecoveredEntry::Unreadable => unreadable = true,
        }
    }
    if unreadable {
        return format!("{PREFIX}recovery incomplete, a recovered job record is unreadable");
    }
    let sweep = match record.sweep_count {
        None => {
            return format!(
                "{PREFIX}recovery incomplete, no lease sweep count to reconcile against"
            )
        }
        Some(s) => s,
    };
    if sweep != usable.len() as i64 {
        return format!(
            "{PREFIX}recovery incomplete, the lease sweep reports {sweep} recovered but {} job records were recovered",
            usable.len()
        );
    }
    if usable.is_empty() {
        return format!("{PREFIX}0 recovered");
    }
    let parts: Vec<String> = usable
        .iter()
        .map(|(id, title, step)| {
            let step_text = match step {
                BatonStep::Number(n) => format!("baton step {n}"),
                BatonStep::Text(s) if !s.is_empty() => s.clone(),
                _ => "step not reported".to_string(),
            };
            format!("job {id} {title} (resumed at {step_text})")
        })
        .collect();
    format!("{PREFIX}{} recovered: {}", usable.len(), parts.join("; "))
}

/// INT-027 follow-up: the Sources lines for a morning brief, from a
/// stated list of source pointers (a lane file, an eval log, a fixture
/// manifest), named verbatim and in order. A pointer is never guessed
/// from a job title; the list is supplied by the caller that builds
/// the brief snapshot. An absent list, an empty list, or a list with
/// no usable entry returns no lines at all, so a brief without
/// pointers renders no Sources section rather than a padded one, and
/// older briefs keep their exact shape. The lines are plain lines,
/// not bullets, so the BRF-007 budget trim never drops a source
/// pointer ahead of a watch item, and they are redacted by the
/// composer, not here. Pointers name locations, not dated facts, so
/// they carry no age label. Python skips non-string entries; in Rust
/// the caller passes string items, so that case is type-level, and
/// empty strings are skipped here to match Python's filter.
///
/// `None` means the snapshot carries no `source_pointers` list.
pub fn source_pointer_lines(pointers: Option<&[&str]>) -> Vec<String> {
    match pointers {
        None => Vec::new(),
        Some(list) => list
            .iter()
            .filter(|s| !s.is_empty())
            .map(|s| format!("Source: {s}"))
            .collect(),
    }
}

/// Minimal morning-brief composer: sections in frozen order, no invention.
pub fn compose_brief(room: &str, sections: &HashMap<String, String>) -> BriefRecord {
    const ORDER: &[&str] = &["held", "priority", "watch", "decisions", "recovery"];
    let mut text = format!("Morning brief for {room}\n");
    for k in ORDER {
        if let Some(v) = sections.get(*k) {
            if !v.trim().is_empty() {
                text.push_str(&format!("\n## {k}\n{v}\n"));
            }
        }
    }
    BriefRecord { room: room.to_string(), ts: 0, text, kind: "morning".to_string() }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn since_windows() {
        assert_eq!(parse_since("all", 1000).unwrap(), None);
        assert_eq!(parse_since("2h", 10000).unwrap(), Some(10000 - 7200));
        assert!(parse_since("bogus", 0).is_err());
    }

    #[test]
    fn record_validation() {
        let r = BriefRecord { room: "main".into(), ts: 1, text: "hi".into(), kind: "morning".into() };
        assert!(validate_brief_record(&r).is_ok());
        let bad = BriefRecord { kind: "nope".into(), ..r };
        assert!(validate_brief_record(&bad).is_err());
    }

    #[test]
    fn frozen_announcement() {
        assert_eq!(format_brief_announcement("main", 9), "BRIEF:main:9");
    }

    #[test]
    fn redaction() {
        let out = redact_secrets(&["API_TOKEN=abc".into(), "ROOM=main".into()]);
        assert_eq!(out[0], "API_TOKEN=<redacted>");
        assert_eq!(out[1], "ROOM=main");
    }

    #[test]
    fn failure_copy_and_budgets() {
        assert_eq!(
            failure_copy_for_kind("unavailable").unwrap(),
            "No brief is available right now. Try again in a few minutes."
        );
        assert_eq!(
            failure_copy_for_kind("spark_down").unwrap(),
            "The brief writer is down, so no fresh brief could be written. Try again later."
        );
        assert_eq!(
            failure_copy_for_kind("no_data").unwrap(),
            "No brief yet, this room has no activity to brief on."
        );
        assert!(failure_copy_for_kind("other").is_err());
        assert_eq!(brief_budget("morning"), Some(220));
        assert_eq!(brief_budget("onjoin"), Some(150));
        assert_eq!(brief_budget("ondemand"), Some(300));
        assert_eq!(brief_budget("daily"), None);
        assert_eq!(BRIEF_REGENERATION_WINDOW_SECONDS, 300);
    }

    #[test]
    fn previous_session_digest_lines() {
        let rec = PreviousSession {
            last_brief_at: "2026-10-30 08:00 ET".into(),
            jobs_completed: vec!["A".into(), "B".into()],
            open_threads: vec!["C".into()],
        };
        assert_eq!(
            previous_session_digest(Some(&rec)).unwrap(),
            "Previous session: last brief 2026-10-30 08:00 ET, 2 jobs completed (A; B), 1 open thread (C)"
        );
        let empty = PreviousSession {
            last_brief_at: "2026-10-30 08:00 ET".into(),
            jobs_completed: vec![],
            open_threads: vec![],
        };
        assert_eq!(
            previous_session_digest(Some(&empty)).unwrap(),
            "Previous session: last brief 2026-10-30 08:00 ET, 0 jobs completed, 0 open threads"
        );
        assert_eq!(previous_session_digest(None), None);
        let no_time = PreviousSession { last_brief_at: String::new(), jobs_completed: vec![], open_threads: vec![] };
        assert_eq!(previous_session_digest(Some(&no_time)), None);
    }

    #[test]
    fn system_state_lines_report_missing_down_and_empty() {
        let full = SystemState {
            drivers: Some(vec!["d1".into(), "d2".into()]),
            gateway_healthy: Some(true),
            skill_apps: Some(vec!["app".into()]),
        };
        assert_eq!(
            system_state_lines(&full),
            vec![
                "Drivers: d1, d2 available",
                "Tools: MCP gateway healthy",
                "Skill apps: app mounted",
            ]
        );
        let missing = SystemState { drivers: None, gateway_healthy: None, skill_apps: None };
        assert_eq!(
            system_state_lines(&missing),
            vec![
                "Drivers: not reported in this snapshot",
                "Tools: MCP gateway health not reported in this snapshot",
                "Skill apps: not reported in this snapshot",
            ]
        );
        let down_empty = SystemState {
            drivers: Some(vec![]),
            gateway_healthy: Some(false),
            skill_apps: Some(vec![]),
        };
        assert_eq!(
            system_state_lines(&down_empty),
            vec![
                "Drivers: no drivers reported",
                "Tools: MCP gateway down, so agents cannot reach their tools through it",
                "Skill apps: no skill apps mounted",
            ]
        );
    }

    #[test]
    fn trim_drops_bullets_then_truncates() {
        let t = "Window: x\n## Watch items\n- one two\n- three four\n- five six";
        assert_eq!(trim_to_budget(t, 5), "Window: x\n## Watch items");
        assert_eq!(trim_to_budget(t, 100), t);
        assert_eq!(trim_to_budget("a b c d e f", 3), "a b (trimmed)");
        assert_eq!(trim_to_budget("one two three", 3), "one two three");
    }

    #[test]
    fn recovery_line_reconciles_or_says_incomplete() {
        assert_eq!(
            recovery_line(None),
            "In-flight jobs recovered at this boot: not reported in this snapshot"
        );
        let clean_zero = RecoveryRecord { corrupted: None, recovered: Some(vec![]), sweep_count: Some(0) };
        assert_eq!(recovery_line(Some(&clean_zero)), "In-flight jobs recovered at this boot: 0 recovered");
        let clean_two = RecoveryRecord {
            corrupted: None,
            recovered: Some(vec![
                RecoveredEntry::Job { id: "T1".into(), title: "Alpha".into(), baton_step: BatonStep::Number(3) },
                RecoveredEntry::Job { id: "T2".into(), title: "Beta".into(), baton_step: BatonStep::Text("checkpoint".into()) },
                RecoveredEntry::Job { id: "T3".into(), title: "Gamma".into(), baton_step: BatonStep::Missing },
            ]),
            sweep_count: Some(3),
        };
        assert_eq!(
            recovery_line(Some(&clean_two)),
            "In-flight jobs recovered at this boot: 3 recovered: job T1 Alpha (resumed at baton step 3); job T2 Beta (resumed at checkpoint); job T3 Gamma (resumed at step not reported)"
        );
        let corrupted = RecoveryRecord {
            corrupted: Some(vec![
                CorruptedEntry::Job { id: "T9".into(), title: "Delta".into() },
                CorruptedEntry::Plain("old job".into()),
            ]),
            recovered: None,
            sweep_count: None,
        };
        assert_eq!(
            recovery_line(Some(&corrupted)),
            "In-flight jobs recovered at this boot: recovery incomplete, job T9 Delta has a corrupted record; old job has a corrupted record"
        );
        let unnameable = RecoveryRecord {
            corrupted: Some(vec![CorruptedEntry::Other, CorruptedEntry::Job { id: String::new(), title: String::new() }]),
            recovered: None,
            sweep_count: None,
        };
        assert_eq!(
            recovery_line(Some(&unnameable)),
            "In-flight jobs recovered at this boot: recovery incomplete, a corrupted job record could not be named"
        );
        let unreadable = RecoveryRecord {
            corrupted: None,
            recovered: Some(vec![RecoveredEntry::Unreadable]),
            sweep_count: Some(1),
        };
        assert_eq!(
            recovery_line(Some(&unreadable)),
            "In-flight jobs recovered at this boot: recovery incomplete, a recovered job record is unreadable"
        );
        let no_sweep = RecoveryRecord { corrupted: None, recovered: Some(vec![]), sweep_count: None };
        assert_eq!(
            recovery_line(Some(&no_sweep)),
            "In-flight jobs recovered at this boot: recovery incomplete, no lease sweep count to reconcile against"
        );
        let mismatch = RecoveryRecord {
            corrupted: None,
            recovered: Some(vec![
                RecoveredEntry::Job { id: "T1".into(), title: "Alpha".into(), baton_step: BatonStep::Missing },
            ]),
            sweep_count: Some(2),
        };
        assert_eq!(
            recovery_line(Some(&mismatch)),
            "In-flight jobs recovered at this boot: recovery incomplete, the lease sweep reports 2 recovered but 1 job records were recovered"
        );
    }

    #[test]
    fn source_pointers_verbatim_in_order_or_no_lines() {
        assert_eq!(
            source_pointer_lines(Some(&["plan/lanes/HANA.md", "intel/evals/log.md"])),
            vec![
                "Source: plan/lanes/HANA.md",
                "Source: intel/evals/log.md",
            ]
        );
        assert_eq!(source_pointer_lines(None), Vec::<String>::new());
        assert_eq!(source_pointer_lines(Some(&[])), Vec::<String>::new());
        assert_eq!(source_pointer_lines(Some(&[""])), Vec::<String>::new());
    }
}
