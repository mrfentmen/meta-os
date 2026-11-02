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

/// One job as the previous brief carried it: its id and the status it
/// carried then. Python skips a previous-brief entry with no id, and
/// keeps only the first entry when an id repeats; the caller builds
/// this list with those rules applied.
#[derive(Debug, Clone, PartialEq)]
pub struct PreviousBriefJob {
    pub id: String,
    pub status: String,
}

/// One job in the current window, as the comparison reads it: its id,
/// title, and current status. Python skips a current job with no id;
/// a missing title reads as empty, and a missing status reads as
/// empty. The caller builds this list with those rules applied.
#[derive(Debug, Clone, PartialEq)]
pub struct CurrentJob {
    pub id: String,
    pub title: String,
    pub status: String,
}

/// A previous-brief record for the since-last-brief comparison: the
/// jobs it carried, and its age label. Python derives the label from
/// the record's `as_of` time through `_environment_age_label`:
/// `" (as of YYYY-MM-DD HH:MM ET)"`, or
/// `" (snapshot time not reported)"` when the record gives no time.
/// This crate has no time dependency, so the caller supplies the
/// label already formed, the same way `previous_session_digest`
/// takes its last-brief time as a string.
///
/// `None` (no record at all) yields no lines: a template brief
/// without a previous-brief record says nothing about newness
/// rather than claiming it, and older briefs keep their exact shape.
pub struct PreviousBrief {
    pub jobs: Vec<PreviousBriefJob>,
    pub age_label: String,
}

/// BRF-019 follow-up: the since-last-brief lines for a morning
/// brief, closing cold-start gap 2 (old news and new news looking
/// identical) for the template brief from a stated record.
///
/// A current job whose status differs from its previous-brief status
/// reads as changed, with the old status and the new status both
/// named; a current job with no previous-brief entry reads as new;
/// a job whose status is unchanged is not listed at all. When the
/// comparison finds nothing changed, the single line reads nothing
/// changed, never a padded change, so a reader can tell the diff
/// was checked and the window held nothing new. Every line carries
/// its age label. The lines are plain lines, not bullets, so the
/// BRF-007 budget trim never drops a change ahead of a watch item,
/// and they are redacted by the composer, not here. This closes gap
/// 2 for the template brief only: a Spark-composed brief carrying
/// these lines, and an independent lane member's cold-start re-run,
/// are still owed.
pub fn since_last_brief_lines(
    previous: Option<&PreviousBrief>,
    current: &[CurrentJob],
) -> Vec<String> {
    let previous = match previous {
        None => return Vec::new(),
        Some(p) => p,
    };
    let mut prev: Vec<(&str, &str)> = Vec::new();
    for job in &previous.jobs {
        if job.id.is_empty() {
            continue;
        }
        if prev.iter().any(|(id, _)| *id == job.id.as_str()) {
            continue;
        }
        prev.push((job.id.as_str(), job.status.as_str()));
    }
    let mut lines: Vec<String> = Vec::new();
    for job in current {
        if job.id.is_empty() {
            continue;
        }
        match prev.iter().find(|(id, _)| *id == job.id.as_str()) {
            None => lines.push(format!(
                "New since your last brief: {} {} ({})",
                job.id, job.title, job.status
            )),
            Some((_, old)) if *old != job.status.as_str() => lines.push(format!(
                "Changed since your last brief: {} {}: {} -> {}",
                job.id, job.title, old, job.status
            )),
            Some(_) => {}
        }
    }
    if lines.is_empty() {
        return vec![format!(
            "Nothing changed since your last brief{}",
            previous.age_label
        )];
    }
    lines
        .iter()
        .map(|l| format!("{l}{}", previous.age_label))
        .collect()
}

/// A priority-order record for the priority-order lines: the job
/// ids in priority order, first first, and its age label. Python
/// derives the label from the record's `as_of` time through
/// `_environment_age_label`: `" (as of YYYY-MM-DD HH:MM ET)"`, or
/// `" (snapshot time not reported)"` when the record gives no time.
/// This crate has no time dependency, so the caller supplies the
/// label already formed, the same way `PreviousBrief` does.
///
/// `None` (no record at all) yields no lines: a snapshot without
/// the record carries none, so older briefs keep their exact shape.
/// The order list itself is kept as given; duplicate, empty, and
/// unknown ids are skipped inside the function, never padded.
pub struct PriorityOrder {
    pub order: Vec<String>,
    pub age_label: String,
}

/// INT-027 follow-up: the priority-order lines for a morning
/// brief, closing cold-start gap 1 (no priority order: the brief
/// lists jobs by section, never by lane task id or dependency
/// order) for the template brief from a stated record.
///
/// A job id in the order is named with its title from the
/// snapshot's jobs list, in record order, numbered from 1; an id
/// with no matching job is skipped, never padded with an invented
/// title, and a job the record does not list is not listed here
/// at all, never guessed into an order. A duplicate id in the
/// order is listed once, at its first place. An order list with
/// no usable entry reads none reported, never a padded order.
/// Every line carries its age label. The lines are plain lines,
/// not bullets, so the BRF-007 budget trim never drops the order
/// ahead of a watch item, and they are redacted by the composer,
/// not here. This closes gap 1 for the template brief only: a
/// Spark-composed brief carrying these lines, and an independent
/// lane member's cold-start re-run, are still owed. The In flight
/// lines it leaves alone keep their pinned shape.
pub fn priority_order_lines(
    record: Option<&PriorityOrder>,
    current: &[CurrentJob],
) -> Vec<String> {
    let record = match record {
        None => return Vec::new(),
        Some(r) => r,
    };
    // First title wins for a repeated id; a job with no id is
    // skipped. An id with an empty title still counts as known,
    // so it renders as its bare id, never a padded title.
    let mut titles: Vec<(&str, &str)> = Vec::new();
    for job in current {
        if job.id.is_empty() {
            continue;
        }
        if titles.iter().any(|(id, _)| *id == job.id.as_str()) {
            continue;
        }
        titles.push((job.id.as_str(), job.title.as_str()));
    }
    let mut seen: Vec<&str> = Vec::new();
    let mut lines: Vec<String> = Vec::new();
    for job_id in &record.order {
        if job_id.is_empty() || seen.contains(&job_id.as_str()) {
            continue;
        }
        let Some((_, title)) = titles.iter().find(|(id, _)| *id == job_id.as_str()) else {
            continue;
        };
        seen.push(job_id.as_str());
        if title.is_empty() {
            lines.push(format!("Priority {}: {}", lines.len() + 1, job_id));
        } else {
            lines.push(format!("Priority {}: {} {}", lines.len() + 1, job_id, title));
        }
    }
    if lines.is_empty() {
        return vec![format!(
            "Priority order: none reported{}",
            record.age_label
        )];
    }
    lines
        .iter()
        .map(|l| format!("{l}{}", record.age_label))
        .collect()
}

/// One blocked-contact entry: the blocked job's id and the nick to
/// ask about it, if one was stated. Python reads the entry's `ask`
/// only when it is a non-empty string; anything else reads as no
/// nick, never a guessed one.
#[derive(Debug, Clone, PartialEq)]
pub struct BlockedContact {
    pub job_id: String,
    pub ask: String,
}

/// A blocked-contacts record for the blocked-contact lines: the
/// stated contact entries, and its age label. Python derives the
/// label from the record's `as_of` time through
/// `_environment_age_label`: `" (as of YYYY-MM-DD HH:MM ET)"`, or
/// `" (snapshot time not reported)"` when the record gives no time.
/// This crate has no time dependency, so the caller supplies the
/// label already formed, the same way `PreviousBrief` does.
///
/// `None` (no record at all) yields no lines: a snapshot without
/// the record carries none, so older briefs keep their exact shape.
/// A malformed Python record (not a dict, or contacts not a list)
/// also yields no lines, so the caller maps those to `None` here.
pub struct BlockedContacts {
    pub contacts: Vec<BlockedContact>,
    pub age_label: String,
}

/// INT-027 follow-up: the blocked-contacts lines for a morning
/// brief, closing cold-start gap 5 (no ask-nick on the blocked job:
/// the blocked line names the job and its reason, but no owner to
/// ask about it) for the template brief from a stated record.
///
/// The lines cover every blocked job in the snapshot, in snapshot
/// order, not only the jobs the record names: a blocked job with a
/// contact entry reads "Ask <nick> about <id> <title>", and a
/// blocked job with no usable entry reads "<id> <title>: owner not
/// reported in this window", the v2 rule 8 wording, never a guessed
/// nick. A contact entry for a job that is not blocked in this
/// snapshot is ignored; a blocked job with no id cannot be named
/// here and is skipped, though its blocked line still names it in
/// the Blocked section. A record over a window with no blocked jobs
/// reads none reported, never a padded contact. Every line carries
/// its age label. The lines are plain lines, not bullets, so the
/// BRF-007 budget trim never drops a contact ahead of a watch item,
/// and they are redacted by the composer, not here. This closes gap
/// 5 for the template brief only: a Spark-composed brief carrying
/// these lines, and an independent lane member's cold-start re-run,
/// are still owed, the same caveats INT-027 carries.
pub fn blocked_contact_lines(
    record: Option<&BlockedContacts>,
    current: &[CurrentJob],
) -> Vec<String> {
    let record = match record {
        None => return Vec::new(),
        Some(r) => r,
    };
    // First entry wins for a repeated job id; an entry with no
    // job id is skipped, never a contact for an unnamed job.
    let mut asks: Vec<(&str, &str)> = Vec::new();
    for contact in &record.contacts {
        if contact.job_id.is_empty() {
            continue;
        }
        if asks.iter().any(|(id, _)| *id == contact.job_id.as_str()) {
            continue;
        }
        asks.push((contact.job_id.as_str(), contact.ask.as_str()));
    }
    let mut lines: Vec<String> = Vec::new();
    for job in current {
        if job.status != "blocked" || job.id.is_empty() {
            continue;
        }
        let label = if job.title.is_empty() {
            job.id.clone()
        } else {
            format!("{} {}", job.id, job.title)
        };
        match asks.iter().find(|(id, _)| *id == job.id.as_str()) {
            Some((_, ask)) if !ask.is_empty() => {
                lines.push(format!("Ask {ask} about {label}"))
            }
            _ => lines.push(format!("{label}: owner not reported in this window")),
        }
    }
    if lines.is_empty() {
        return vec![format!(
            "Blocked contacts: none reported{}",
            record.age_label
        )];
    }
    lines
        .iter()
        .map(|l| format!("{l}{}", record.age_label))
        .collect()
}

/// One held decision: a question waiting on a word, plus the nick
/// it waits on. An empty decider reads as decider not reported,
/// never a guessed nick; the caller builds this list with that
/// rule applied, and an entry with no usable question is skipped
/// before it ever reaches this list.
/// A held-decisions record for the held-decisions lines: the
/// decisions it carries, and its age label. Python derives the
/// label from the record's `as_of` time through
/// `_environment_age_label`: `" (as of YYYY-MM-DD HH:MM ET)"`, or
/// `" (snapshot time not reported)"` when the record gives no time.
/// This crate has no time dependency, so the caller supplies the
/// label already formed, the same way `BlockedContacts` does.
///
/// Unlike the sibling line-builders in this file, `None` (no
/// record at all) does NOT yield no lines here: Python's
/// `held_decisions_lines` treats a non-dict record as an empty
/// record and reads none reported, and the parity tests pin that
/// (`test_empty_record_reads_none_reported` calls it with
/// `"not a record"`). The composer still gates the section on the
/// record existing, so a brief without the record carries no
/// section; this function on its own reports the empty state.
#[derive(Debug, Clone, PartialEq)]
pub struct HeldDecision {
    pub question: String,
    pub decider: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct HeldDecisions {
    pub decisions: Vec<HeldDecision>,
    pub age_label: String,
}

/// INT-027 follow-up: the held-decisions lines for a morning
/// brief, closing cold-start gap 3 (no held decisions) for the
/// template brief from a stated record.
///
/// A question is named verbatim from the record; an entry without
/// a question is skipped, never padded; a decision without a
/// decider reads decider not reported, never a guessed nick. A
/// record with no usable entries reads none reported, never a
/// padded decision, so a reader can tell the held list was
/// checked and held nothing. Every line carries its age label.
/// The lines are plain lines, not bullets, so the BRF-007 budget
/// trim never drops a decision waiting on a word ahead of a watch
/// item, and they are redacted by the composer, not here. This
/// closes gap 3 for the template brief only: a Spark-composed
/// brief carrying these lines, and an independent lane member's
/// cold-start re-run, are still owed.
pub fn held_decisions_lines(record: Option<&HeldDecisions>) -> Vec<String> {
    let (decisions, age_label) = match record {
        None => (&[][..], " (snapshot time not reported)"),
        Some(r) => (&r.decisions[..], r.age_label.as_str()),
    };
    let mut lines: Vec<String> = Vec::new();
    for entry in decisions {
        if entry.question.is_empty() {
            continue;
        }
        if entry.decider.is_empty() {
            lines.push(format!(
                "Held decision: {} (decider not reported)",
                entry.question
            ));
        } else {
            lines.push(format!(
                "Held decision: {} (waiting on {})",
                entry.question, entry.decider
            ));
        }
    }
    if lines.is_empty() {
        return vec![format!("Held decisions: none reported{}", age_label)];
    }
    lines
        .iter()
        .map(|l| format!("{}{}", l, age_label))
        .collect()
}

/// One on-join snapshot job: id/title/status plus the `lane` field
/// `onjoin_template_lines` reads, and claim/note for the owner and
/// blocked extractors. A missing lane reads as empty, never guessed.
#[derive(Debug, Clone, PartialEq)]
pub struct OnjoinJob {
    pub id: String,
    pub title: String,
    pub status: String,
    pub lane: String,
    pub claim: String,
    pub note: String,
}

/// One newcomer capability record. Python appends `; roles: {roles}`
/// whenever roles is a string at all — even an empty one — so
/// `roles` is `Option` here: `None` means not a string, `Some`
/// (even empty) appends. A caps text that is empty states nothing
/// and yields no line.
#[derive(Debug, Clone, PartialEq)]
pub struct OnjoinCaps {
    pub caps: String,
    pub roles: Option<String>,
}

/// The on-join template snapshot, in the normalized form the
/// extractors read. `presence` is `None` when the snapshot carries
/// no presence list at all (then no owner is marked not online);
/// `Some` (even empty) marks every owner not in the list. The
/// caller splits bus-string messages into author nicks first,
/// mirroring `_message_parts`, and maps a non-dict snapshot,
/// non-list jobs, and a non-dict or non-list-contacts
/// blocked_contacts record to the empty / `None` forms here —
/// Python reads all of those as empty, never raising. A dict
/// presence reaches here as its key list, in key order.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct OnjoinSnapshot {
    pub crew_building: String,
    pub jobs: Vec<OnjoinJob>,
    pub message_authors: Vec<String>,
    pub presence: Option<Vec<String>>,
    pub caps: Vec<(String, OnjoinCaps)>,
    pub blocked_contacts: Option<Vec<BlockedContact>>,
    pub alerts: Vec<super::sections::SnapAlert>,
}

/// BRF-018 follow-up: the four BRF-002 on-join sections for a
/// template brief, in prompt order: What this crew is building,
/// Your likely lane, What is blocked, Who to ask.
///
/// The crew sentence is the snapshot's stated `crew_building`
/// string when it is non-blank, else the prompt's own not-stated
/// sentence. The likely-lane line names an open job's `lane`
/// field in the v2 rule 9 form when the record carries one, and
/// names a newcomer's capability record verbatim when one is
/// stated for a newcomer; when neither is stated it says so and
/// points to the first owner to ask for a first job (or says
/// plainly that no owner is recorded). Blocked lines quote
/// reasons verbatim, or read "Nothing blocked in this window".
/// Who to ask names the claimed-job owners, marking one "not
/// online in this window" only when the snapshot carries a
/// presence list that does not name them, plus the
/// blocked-contact ask nick when the snapshot carries a
/// blocked_contacts record. The four section lines are plain
/// lines, not bullets, so the BRF-007 budget trim cannot drop a
/// blocked job or an ask-nick ahead of any other line; the
/// additive INT-004 sections below use the morning bullet form,
/// so under trim they drop first. This never raises.
///
/// Faithful quirks, pinned, not fixed: an open job with a title
/// but no lane still appends its "Open job:" line while leaving
/// the has-lane-or-caps flag false, so the no-capability lines
/// follow it too; the blocked-contact label is `{id} {title}`
/// unstripped, unlike the open-job label, which is stripped.
pub fn onjoin_template_lines(snapshot: &OnjoinSnapshot) -> Vec<String> {
    use super::sections::{extract_blocked, extract_owners, extract_watch_items, SnapJob, Snapshot};
    let snap = Snapshot {
        messages: Vec::new(),
        jobs: snapshot
            .jobs
            .iter()
            .map(|j| SnapJob {
                id: j.id.clone(),
                title: j.title.clone(),
                status: j.status.clone(),
                claim: j.claim.clone(),
                note: j.note.clone(),
                last_progress_at: None,
                claimed_at: None,
            })
            .collect(),
        alerts: snapshot.alerts.clone(),
    };
    let mut lines: Vec<String> = Vec::new();
    lines.push("What this crew is building".to_string());
    let crew = snapshot.crew_building.trim();
    if !crew.is_empty() {
        lines.push(crew.to_string());
    } else {
        lines.push("The room's current work is not stated in this window".to_string());
    }
    lines.push(String::new());
    lines.push("Your likely lane".to_string());
    let mut lane_lines: Vec<String> = Vec::new();
    let mut has_lane_or_caps = false;
    if let Some(job) = snapshot.jobs.iter().find(|j| j.status == "open") {
        if !job.lane.is_empty() {
            lane_lines.push(format!(
                "The open job {} belongs to the {} lane",
                job.title, job.lane
            ));
            has_lane_or_caps = true;
        } else if !job.title.is_empty() {
            let label = format!("{} {}", job.id, job.title);
            lane_lines.push(format!("Open job: {}", label.trim()));
        }
    }
    // Newcomers, in presence order: present with no prior message,
    // duplicates dropped, empty nicks ignored.
    let mut newcomers: Vec<&str> = Vec::new();
    if let Some(presence) = &snapshot.presence {
        for nick in presence {
            if nick.is_empty()
                || snapshot.message_authors.iter().any(|a| a == nick)
                || newcomers.contains(&nick.as_str())
            {
                continue;
            }
            newcomers.push(nick.as_str());
        }
    }
    for newcomer in &newcomers {
        let Some((_, record)) = snapshot.caps.iter().find(|(n, _)| n == newcomer) else {
            continue;
        };
        if record.caps.is_empty() {
            continue;
        }
        let mut caps_line = format!("{newcomer}'s capability record lists {}", record.caps);
        if let Some(roles) = &record.roles {
            caps_line.push_str(&format!("; roles: {roles}"));
        }
        lane_lines.push(caps_line);
        has_lane_or_caps = true;
    }
    let owners = extract_owners(&snap);
    let ask_nick = owners.first().map(|o| o.nick.as_str()).unwrap_or("");
    lines.extend(lane_lines);
    if !has_lane_or_caps {
        lines.push(
            "No capability record and no open job lane are stated in this window.".to_string(),
        );
        if !ask_nick.is_empty() {
            lines.push(format!("Ask {ask_nick} for a first job"));
        } else {
            lines.push("No owner is recorded in this window".to_string());
        }
    }
    lines.push(String::new());
    lines.push("What is blocked".to_string());
    let blocked = extract_blocked(&snap);
    if blocked.is_empty() {
        lines.push("Nothing blocked in this window".to_string());
    } else {
        for job in &blocked {
            lines.push(format!("{} {}: {}", job.id, job.title, job.reason));
        }
    }
    lines.push(String::new());
    lines.push("Who to ask".to_string());
    let presence_nicks: Option<Vec<&str>> = snapshot
        .presence
        .as_ref()
        .map(|p| p.iter().map(|n| n.as_str()).collect());
    let mut ask_lines: Vec<String> = Vec::new();
    for owner in &owners {
        let titles: Vec<&str> = owner.jobs.iter().map(|j| j.title.as_str()).collect();
        let mut line = format!("{}: {}", owner.nick, titles.join(", "));
        if let Some(present) = &presence_nicks {
            if !present.contains(&owner.nick.as_str()) {
                line.push_str(" (not online in this window)");
            }
        }
        ask_lines.push(line);
    }
    if let Some(contacts) = &snapshot.blocked_contacts {
        // First entry wins for a repeated job id; an entry with no
        // job id is skipped, never a contact for an unnamed job.
        let mut asks: Vec<(&str, &str)> = Vec::new();
        for contact in contacts {
            if contact.job_id.is_empty() {
                continue;
            }
            if asks.iter().any(|(id, _)| *id == contact.job_id.as_str()) {
                continue;
            }
            asks.push((contact.job_id.as_str(), contact.ask.as_str()));
        }
        for job in &blocked {
            let label = format!("{} {}", job.id, job.title);
            match asks.iter().find(|(id, _)| *id == job.id.as_str()) {
                Some((_, ask)) if !ask.is_empty() => {
                    ask_lines.push(format!("Ask {ask} about {label}"));
                }
                _ => {
                    ask_lines.push(format!("{label}: owner not reported in this window"));
                }
            }
        }
    }
    if ask_lines.is_empty() {
        lines.push("No owner is recorded in this window".to_string());
    } else {
        lines.extend(ask_lines);
    }
    // INT-004 additive sections, after the four on-join sections
    // and only when they have content: a brief with no blocked job
    // carries no additive Blocked section, and one with no alerts
    // carries no additive Watch section.
    if !blocked.is_empty() {
        lines.push(String::new());
        lines.push("Blocked and why".to_string());
        for job in &blocked {
            lines.push(format!("- {} {}: {}", job.id, job.title, job.reason));
        }
    }
    let watch_items = extract_watch_items(&snap);
    if !watch_items.is_empty() {
        lines.push(String::new());
        lines.push("Watch items".to_string());
        for item in &watch_items {
            lines.push(format!("- {}: {}", item.id, item.summary));
        }
    }
    lines
}

/// OS-103: the launch-environment input for a boot brief: the repo
/// state, the bus state, the claimed jobs, and the budget record.
/// `None` fields mean "not reported in this snapshot"; a present but
/// empty value means "none reported" — never padded, never guessed.
/// Each sub-record carries its own preformed age label, the same
/// pattern as `PreviousBrief`: `\" (as of YYYY-MM-DD HH:MM ET)\"`,
/// or `\" (snapshot time not reported)\"` when the record gives no
/// time. This crate has no time dependency, so the caller supplies
/// the label already formed. A caller maps a non-string branch,
/// commit, lane, nick, or title to an empty string, and a non-int
/// (including a bool) dirty / messages / cap / spent / remaining
/// value to `None`, mirroring Python's `isinstance` checks.
#[derive(Debug, Clone, PartialEq)]
pub struct EnvironmentRepo {
    pub branch: String,
    pub commit: String,
    pub dirty: Option<i64>,
    pub age_label: String,
}

/// One bus record: non-empty room names only, and the message count
/// when the record carries an int for it.
#[derive(Debug, Clone, PartialEq)]
pub struct EnvironmentBus {
    pub rooms: Vec<String>,
    pub messages: Option<i64>,
    pub age_label: String,
}

/// One job as the working-now line reads it: only `claimed` jobs
/// with a non-empty claim nick and a non-empty title count.
#[derive(Debug, Clone, PartialEq)]
pub struct EnvironmentJob {
    pub status: String,
    pub claim: String,
    pub title: String,
}

/// One budget record: lane plus spent and cap, or remaining directly.
/// When `remaining` is `None` but cap and spent are both present,
/// the remaining value is derived as cap minus spent.
#[derive(Debug, Clone, PartialEq)]
pub struct EnvironmentBudget {
    pub lane: String,
    pub cap: Option<i64>,
    pub spent: Option<i64>,
    pub remaining: Option<i64>,
    pub age_label: String,
}

/// The whole environment record. `jobs: None` means the snapshot
/// carries no `jobs` key at all, which reads as not reported;
/// `Some(vec![])` means an empty jobs list, which reads as nobody
/// holding a claimed job. `working_age_label` is the label from the
/// environment record's own `as_of` time.
#[derive(Debug, Clone, PartialEq)]
pub struct Environment {
    pub repo: Option<EnvironmentRepo>,
    pub bus: Option<EnvironmentBus>,
    pub jobs: Option<Vec<EnvironmentJob>>,
    pub working_age_label: String,
    pub budget: Option<EnvironmentBudget>,
}

/// OS-103: the four launch-environment lines for a boot brief, in
/// that order, one line each: Repo, Bus, Working now, Budget.
///
/// A missing record or a missing field is reported as not reported,
/// never guessed; an empty jobs list means nobody holds a claimed
/// job, never a padded name. The lines are redacted by the composer,
/// not here, and they are not bullet lines, so the BRF-007 budget
/// trim never drops them ahead of a watch item.
pub fn environment_lines(env: Option<&Environment>) -> Vec<String> {
    let env = match env {
        None => {
            return vec![
                "Repo state: not reported in this snapshot".to_string(),
                "Bus state: not reported in this snapshot".to_string(),
                "Working now: not reported in this snapshot".to_string(),
                "Budget: not reported in this snapshot".to_string(),
            ]
        }
        Some(e) => e,
    };
    let repo_line = match &env.repo {
        Some(repo) if !repo.branch.is_empty() && !repo.commit.is_empty() => {
            let tree = match repo.dirty {
                Some(0) => ", clean".to_string(),
                Some(d) if d > 0 => format!(
                    ", {} uncommitted file{}",
                    d,
                    if d != 1 { "s" } else { "" }
                ),
                _ => String::new(),
            };
            format!(
                "Repo: {} at {}{}{}",
                repo.branch, repo.commit, tree, repo.age_label
            )
        }
        _ => "Repo state: not reported in this snapshot".to_string(),
    };
    let bus_line = match &env.bus {
        Some(bus) => {
            let rooms: Vec<&str> = bus
                .rooms
                .iter()
                .map(String::as_str)
                .filter(|r| !r.is_empty())
                .collect();
            let mut parts: Vec<String> = Vec::new();
            if let Some(messages) = bus.messages {
                parts.push(format!("{messages} messages"));
            }
            if !rooms.is_empty() {
                parts.push(format!(
                    "in room{} {}",
                    if rooms.len() != 1 { "s" } else { "" },
                    rooms.join(", ")
                ));
            }
            if parts.is_empty() {
                "Bus state: not reported in this snapshot".to_string()
            } else {
                format!("Bus: {}{}", parts.join(" "), bus.age_label)
            }
        }
        None => "Bus state: not reported in this snapshot".to_string(),
    };
    let working_line = match &env.jobs {
        None => "Working now: not reported in this snapshot".to_string(),
        Some(jobs) => {
            let claimed: Vec<String> = jobs
                .iter()
                .filter(|j| j.status == "claimed" && !j.claim.is_empty() && !j.title.is_empty())
                .map(|j| format!("{}: {}", j.claim, j.title))
                .collect();
            if claimed.is_empty() {
                format!(
                    "Working now: nobody holds a claimed job in this snapshot{}",
                    env.working_age_label
                )
            } else {
                format!(
                    "Working now: {}{}",
                    claimed.join("; "),
                    env.working_age_label
                )
            }
        }
    };
    let budget_line = match &env.budget {
        Some(budget) => {
            let remaining = match budget.remaining {
                Some(r) => Some(r),
                None => match (budget.cap, budget.spent) {
                    (Some(cap), Some(spent)) => Some(cap - spent),
                    _ => None,
                },
            };
            match (budget.lane.is_empty(), remaining) {
                (false, Some(remaining)) => {
                    let cap_part = match budget.cap {
                        Some(cap) => format!(" of {cap} cap"),
                        None => String::new(),
                    };
                    format!(
                        "Budget: {} lane: {} remaining{}{}",
                        budget.lane, remaining, cap_part, budget.age_label
                    )
                }
                _ => "Budget: not reported in this snapshot".to_string(),
            }
        }
        None => "Budget: not reported in this snapshot".to_string(),
    };
    vec![repo_line, bus_line, working_line, budget_line]
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

    #[test]
    fn since_last_brief_new_changed_unchanged_and_nothing() {
        let prev = PreviousBrief {
            jobs: vec![
                PreviousBriefJob { id: "T1".into(), status: "open".into() },
                PreviousBriefJob { id: "T2".into(), status: "done".into() },
                // First entry wins for a repeated id.
                PreviousBriefJob { id: "T2".into(), status: "open".into() },
                PreviousBriefJob { id: "".into(), status: "open".into() },
            ],
            age_label: " (as of 2026-10-30 08:00 ET)".into(),
        };
        let current = vec![
            CurrentJob { id: "T1".into(), title: "Alpha".into(), status: "done".into() },
            CurrentJob { id: "T2".into(), title: "Beta".into(), status: "done".into() },
            CurrentJob { id: "T3".into(), title: "Gamma".into(), status: "open".into() },
            CurrentJob { id: "".into(), title: "NoId".into(), status: "open".into() },
        ];
        assert_eq!(
            since_last_brief_lines(Some(&prev), &current),
            vec![
                "Changed since your last brief: T1 Alpha: open -> done (as of 2026-10-30 08:00 ET)",
                "New since your last brief: T3 Gamma (open) (as of 2026-10-30 08:00 ET)",
            ]
        );
        // No record at all says nothing about newness.
        assert_eq!(since_last_brief_lines(None, &current), Vec::<String>::new());
        // A checked window with nothing new says so, with the
        // not-reported label when the record gives no time.
        let unreported = PreviousBrief {
            jobs: vec![PreviousBriefJob { id: "T2".into(), status: "done".into() }],
            age_label: " (snapshot time not reported)".into(),
        };
        let same = vec![CurrentJob { id: "T2".into(), title: "Beta".into(), status: "done".into() }];
        assert_eq!(
            since_last_brief_lines(Some(&unreported), &same),
            vec!["Nothing changed since your last brief (snapshot time not reported)"]
        );
    }

    #[test]
    fn priority_order_lines_record_order_dupes_unknown_and_none() {
        let record = PriorityOrder {
            order: vec![
                "T2".into(),
                "T1".into(),
                "T9".into(),
                "T2".into(),
                "".into(),
                "T3".into(),
            ],
            age_label: " (as of 2026-10-30 08:00 ET)".into(),
        };
        let current = vec![
            CurrentJob { id: "T1".into(), title: "Alpha".into(), status: "open".into() },
            CurrentJob { id: "T2".into(), title: "Beta".into(), status: "open".into() },
            // First title wins for a repeated id; an empty title
            // still counts as known and renders as a bare id.
            CurrentJob { id: "T2".into(), title: "Other".into(), status: "open".into() },
            CurrentJob { id: "T3".into(), title: "".into(), status: "open".into() },
            CurrentJob { id: "".into(), title: "NoId".into(), status: "open".into() },
        ];
        assert_eq!(
            priority_order_lines(Some(&record), &current),
            vec![
                "Priority 1: T2 Beta (as of 2026-10-30 08:00 ET)",
                "Priority 2: T1 Alpha (as of 2026-10-30 08:00 ET)",
                "Priority 3: T3 (as of 2026-10-30 08:00 ET)",
            ]
        );
        // No record at all says nothing about an order.
        assert_eq!(priority_order_lines(None, &current), Vec::<String>::new());
        // An order with no usable entry reads none reported,
        // never a padded order.
        let unusable = PriorityOrder {
            order: vec!["T9".into(), "".into()],
            age_label: " (snapshot time not reported)".into(),
        };
        assert_eq!(
            priority_order_lines(Some(&unusable), &current),
            vec!["Priority order: none reported (snapshot time not reported)"]
        );
        let empty = PriorityOrder { order: vec![], age_label: " (snapshot time not reported)".into() };
        assert_eq!(
            priority_order_lines(Some(&empty), &current),
            vec!["Priority order: none reported (snapshot time not reported)"]
        );
    }

    #[test]
    fn blocked_contact_lines_ask_first_wins_non_blocked_ignored_and_none() {
        let record = BlockedContacts {
            contacts: vec![
                BlockedContact { job_id: "7".into(), ask: "milo".into() },
                // First entry wins for a repeated job id.
                BlockedContact { job_id: "7".into(), ask: "pax".into() },
                // A contact for a job that is not blocked is ignored.
                BlockedContact { job_id: "3".into(), ask: "pax".into() },
                BlockedContact { job_id: "".into(), ask: "rowan".into() },
            ],
            age_label: " (as of 2026-10-30 08:00 ET)".into(),
        };
        let current = vec![
            CurrentJob { id: "7".into(), title: "spark client".into(), status: "blocked".into() },
            CurrentJob { id: "3".into(), title: "brief panel".into(), status: "claimed".into() },
            CurrentJob { id: "9".into(), title: "watchdog loop".into(), status: "blocked".into() },
            CurrentJob { id: "".into(), title: "NoId".into(), status: "blocked".into() },
        ];
        assert_eq!(
            blocked_contact_lines(Some(&record), &current),
            vec![
                "Ask milo about 7 spark client (as of 2026-10-30 08:00 ET)",
                "9 watchdog loop: owner not reported in this window (as of 2026-10-30 08:00 ET)",
            ]
        );
        // No record at all says nothing about contacts.
        assert_eq!(blocked_contact_lines(None, &current), Vec::<String>::new());
        // A record over a window with no blocked jobs reads none
        // reported, never a padded contact.
        let claimed = vec![
            CurrentJob { id: "3".into(), title: "brief panel".into(), status: "claimed".into() },
        ];
        assert_eq!(
            blocked_contact_lines(Some(&record), &claimed),
            vec!["Blocked contacts: none reported (as of 2026-10-30 08:00 ET)"]
        );
        // An entry with no ask, and a blocked job with no title,
        // both read owner-not-reported / bare id, never guessed.
        let no_ask = BlockedContacts {
            contacts: vec![BlockedContact { job_id: "7".into(), ask: "".into() }],
            age_label: " (snapshot time not reported)".into(),
        };
        let bare = vec![
            CurrentJob { id: "7".into(), title: "".into(), status: "blocked".into() },
        ];
        assert_eq!(
            blocked_contact_lines(Some(&no_ask), &bare),
            vec!["7: owner not reported in this window (snapshot time not reported)"]
        );
    }

    #[test]
    fn held_decisions_lines_verbatim_decider_none_and_no_record() {
        let record = HeldDecisions {
            decisions: vec![
                HeldDecision { question: "Approve posting brief announcements?".into(), decider: "dale".into() },
                HeldDecision { question: "Pick the boot target for demo day?".into(), decider: "dale".into() },
                // No decider reads not reported, never a guessed nick.
                HeldDecision { question: "Which gateway for the demo?".into(), decider: "".into() },
                // No question is skipped, never padded.
                HeldDecision { question: "".into(), decider: "dale".into() },
            ],
            age_label: " (as of 2026-10-30 08:00 ET)".into(),
        };
        assert_eq!(
            held_decisions_lines(Some(&record)),
            vec![
                "Held decision: Approve posting brief announcements? (waiting on dale) (as of 2026-10-30 08:00 ET)",
                "Held decision: Pick the boot target for demo day? (waiting on dale) (as of 2026-10-30 08:00 ET)",
                "Held decision: Which gateway for the demo? (decider not reported) (as of 2026-10-30 08:00 ET)",
            ]
        );
        // An empty record reads none reported, never a padded decision.
        let empty = HeldDecisions { decisions: vec![], age_label: " (snapshot time not reported)".into() };
        assert_eq!(
            held_decisions_lines(Some(&empty)),
            vec!["Held decisions: none reported (snapshot time not reported)"]
        );
        // Python pins the non-record case the same way: a record
        // that is not a dict reads none reported, not no lines.
        assert_eq!(
            held_decisions_lines(None),
            vec!["Held decisions: none reported (snapshot time not reported)"]
        );
    }

    #[test]
    fn onjoin_template_lines_four_sections_plus_additive() {
        use super::super::sections::SnapAlert;
        let snapshot = OnjoinSnapshot {
            crew_building: "a trio of 911 apps".into(),
            jobs: vec![
                OnjoinJob { id: "7".into(), title: "spark client".into(), status: "open".into(), lane: "ignis".into(), claim: "".into(), note: "".into() },
                OnjoinJob { id: "9".into(), title: "watchdog loop".into(), status: "blocked".into(), lane: "".into(), claim: "".into(), note: "needs a key".into() },
                OnjoinJob { id: "3".into(), title: "brief panel".into(), status: "claimed".into(), lane: "".into(), claim: "pax".into(), note: "".into() },
            ],
            message_authors: vec!["pax".into()],
            presence: Some(vec!["milo".into(), "pax".into()]),
            caps: vec![("milo".into(), OnjoinCaps { caps: "rust, tests".into(), roles: Some("gate".into()) })],
            blocked_contacts: Some(vec![
                BlockedContact { job_id: "9".into(), ask: "milo".into() },
            ]),
            alerts: vec![SnapAlert { id: "WDG-1".into(), summary: "queue stalled".into(), explanation: "".into() }],
        };
        assert_eq!(
            onjoin_template_lines(&snapshot),
            vec![
                "What this crew is building",
                "a trio of 911 apps",
                "",
                "Your likely lane",
                "The open job spark client belongs to the ignis lane",
                "milo's capability record lists rust, tests; roles: gate",
                "",
                "What is blocked",
                "9 watchdog loop: needs a key",
                "",
                "Who to ask",
                // pax is in presence, so no not-online mark.
                "pax: brief panel",
                "Ask milo about 9 watchdog loop",
                "",
                "Blocked and why",
                "- 9 watchdog loop: needs a key",
                "",
                "Watch items",
                "- WDG-1: queue stalled",
            ]
        );
        // An empty snapshot says everything plainly, never invents.
        let empty = OnjoinSnapshot::default();
        assert_eq!(
            onjoin_template_lines(&empty),
            vec![
                "What this crew is building",
                "The room's current work is not stated in this window",
                "",
                "Your likely lane",
                "No capability record and no open job lane are stated in this window.",
                "No owner is recorded in this window",
                "",
                "What is blocked",
                "Nothing blocked in this window",
                "",
                "Who to ask",
                "No owner is recorded in this window",
            ]
        );
        // Pinned quirk: an open job with a title but no lane still
        // appends its "Open job:" line AND the no-capability lines.
        let title_only = OnjoinSnapshot {
            jobs: vec![
                OnjoinJob { id: "7".into(), title: "spark client".into(), status: "open".into(), lane: "".into(), claim: "".into(), note: "".into() },
                OnjoinJob { id: "3".into(), title: "brief panel".into(), status: "claimed".into(), lane: "".into(), claim: "pax".into(), note: "".into() },
            ],
            presence: None,
            ..OnjoinSnapshot::default()
        };
        let lines = onjoin_template_lines(&title_only);
        assert!(lines.contains(&"Open job: 7 spark client".to_string()));
        assert!(lines.contains(
            &"No capability record and no open job lane are stated in this window.".to_string()
        ));
        assert!(lines.contains(&"Ask pax for a first job".to_string()));
        // No presence list at all means no not-online mark.
        assert!(lines.contains(&"pax: brief panel".to_string()));
        assert!(!lines.iter().any(|l| l.contains("not online")));
    }

    #[test]
    fn environment_lines_full_missing_and_empty() {
        let full = Environment {
            repo: Some(EnvironmentRepo {
                branch: "main".into(),
                commit: "abc1234".into(),
                dirty: Some(2),
                age_label: " (as of 2026-10-30 08:00 ET)".into(),
            }),
            bus: Some(EnvironmentBus {
                rooms: vec!["main".into(), "".into(), "ops".into()],
                messages: Some(5),
                age_label: " (snapshot time not reported)".into(),
            }),
            jobs: Some(vec![
                EnvironmentJob { status: "claimed".into(), claim: "milo".into(), title: "gate run".into() },
                EnvironmentJob { status: "open".into(), claim: "".into(), title: "unclaimed".into() },
                EnvironmentJob { status: "claimed".into(), claim: "".into(), title: "no nick".into() },
            ]),
            working_age_label: " (as of 2026-10-30 08:00 ET)".into(),
            budget: Some(EnvironmentBudget {
                lane: "intel".into(),
                cap: Some(100),
                spent: Some(30),
                remaining: None,
                age_label: " (snapshot time not reported)".into(),
            }),
        };
        assert_eq!(
            environment_lines(Some(&full)),
            vec![
                "Repo: main at abc1234, 2 uncommitted files (as of 2026-10-30 08:00 ET)",
                "Bus: 5 messages in rooms main, ops (snapshot time not reported)",
                "Working now: milo: gate run (as of 2026-10-30 08:00 ET)",
                "Budget: intel lane: 70 remaining of 100 cap (snapshot time not reported)",
            ]
        );
        // No record at all: every line says not reported, never guessed.
        assert_eq!(
            environment_lines(None),
            vec![
                "Repo state: not reported in this snapshot",
                "Bus state: not reported in this snapshot",
                "Working now: not reported in this snapshot",
                "Budget: not reported in this snapshot",
            ]
        );
        // Clean tree, one file, direct remaining, empty jobs list.
        let edge = Environment {
            repo: Some(EnvironmentRepo {
                branch: "main".into(),
                commit: "abc1234".into(),
                dirty: Some(0),
                age_label: " (snapshot time not reported)".into(),
            }),
            bus: Some(EnvironmentBus {
                rooms: vec![],
                messages: None,
                age_label: " (snapshot time not reported)".into(),
            }),
            jobs: Some(vec![]),
            working_age_label: " (snapshot time not reported)".into(),
            budget: Some(EnvironmentBudget {
                lane: "intel".into(),
                cap: None,
                spent: None,
                remaining: Some(12),
                age_label: " (snapshot time not reported)".into(),
            }),
        };
        let lines = environment_lines(Some(&edge));
        assert_eq!(lines[0], "Repo: main at abc1234, clean (snapshot time not reported)");
        assert_eq!(lines[1], "Bus state: not reported in this snapshot");
        assert_eq!(
            lines[2],
            "Working now: nobody holds a claimed job in this snapshot (snapshot time not reported)"
        );
        assert_eq!(lines[3], "Budget: intel lane: 12 remaining (snapshot time not reported)");
        // One uncommitted file reads singular; a missing branch or
        // commit reads as not reported, never a half line.
        let singular = Environment {
            repo: Some(EnvironmentRepo {
                branch: "main".into(),
                commit: "abc1234".into(),
                dirty: Some(1),
                age_label: "".into(),
            }),
            bus: None,
            jobs: None,
            working_age_label: "".into(),
            budget: None,
        };
        let lines = environment_lines(Some(&singular));
        assert_eq!(lines[0], "Repo: main at abc1234, 1 uncommitted file");
        let no_branch = Environment { repo: Some(EnvironmentRepo {
            branch: "".into(),
            commit: "abc1234".into(),
            dirty: None,
            age_label: "".into(),
        }), ..singular.clone() };
        assert_eq!(
            environment_lines(Some(&no_branch))[0],
            "Repo state: not reported in this snapshot"
        );
    }
}
