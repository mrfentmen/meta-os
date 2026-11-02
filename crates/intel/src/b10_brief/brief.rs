//! Port of `os/intel/brief.py` — the brief engine surface.
//!
//! Frozen shapes: `BRIEF:<room>:<ts>` records, `brief --since` windows,
//! budget trimming (never invent), secret redaction, verbatim quotes.
//! This module ports the pure record/window/format layer; Spark
//! composition (`compose_spark_brief`) stays behind the B11 client trait
//! and is represented here as an injected renderer so tests stay offline.

use std::collections::HashMap;

use super::window::{RawMessage, SourceWindow, WindowHours};

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

/// OS-051: a stored brief record as `build_previous_session` reads it.
/// `generated_at` mirrors Python's `.get("generated_at", .get("ts"))`
/// exactly: outer None means the key is absent (fall through to
/// `ts`); Some(None) means the key is present but null (the format
/// fails, so the fallback is `last_brief_at`, never `ts`);
/// Some(Some(v)) is a numeric timestamp. A float timestamp arrives
/// already truncated to an int, mirroring Python's `int(ts)` at
/// format time; a bool timestamp has no Rust form (Python returns
/// None for it, which the `last_brief_at` fallback covers).
pub struct StoredBriefInput {
    pub generated_at: Option<Option<i64>>,
    pub ts: Option<i64>,
    pub last_brief_at: Option<String>,
}

/// OS-051: one shutdown job list entry, as `build_previous_session`
/// reads it. Only `title` and `status` are inputs; a non-dict entry
/// has no Rust form (Python skips it), and an empty title is
/// dropped, mirroring Python's truthiness check.
pub struct ShutdownJob {
    pub title: String,
    pub status: String,
}

/// OS-051: derive a previous-session record from stored state.
///
/// `last_brief` is a stored brief record (or brief index entry);
/// its `generated_at` (or `ts`) Unix timestamp becomes the
/// last-brief time, formatted by `format_brief_time`. `jobs` is the
/// job list as it stood at shutdown: status `done` jobs are the
/// jobs completed, status `open`/`claimed` jobs are the open
/// threads — this repo has no separate thread store, so the job
/// list is the thread list. Returns None when no usable last-brief
/// time exists, so no digest is ever built on a guessed time.
/// The returned record is the `previous_session` record a boot
/// snapshot carries. Order is snapshot order, duplicates kept.
pub fn build_previous_session(
    last_brief: Option<&StoredBriefInput>,
    jobs: Option<&[ShutdownJob]>,
) -> Option<PreviousSession> {
    let last_brief = last_brief?;
    let formatted = match last_brief.generated_at {
        Some(Some(ts)) => Some(format_brief_time(ts)),
        Some(None) => None,
        None => last_brief.ts.map(format_brief_time),
    };
    let last_brief_at = match formatted {
        Some(t) => t,
        None => match &last_brief.last_brief_at {
            Some(s) if !s.is_empty() => s.clone(),
            _ => return None,
        },
    };
    let mut jobs_completed = Vec::new();
    let mut open_threads = Vec::new();
    if let Some(jobs) = jobs {
        for job in jobs {
            if job.title.is_empty() {
                continue;
            }
            match job.status.as_str() {
                "done" => jobs_completed.push(job.title.clone()),
                "open" | "claimed" => open_threads.push(job.title.clone()),
                _ => {}
            }
        }
    }
    Some(PreviousSession { last_brief_at, jobs_completed, open_threads })
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

/// OS-117: one machine in a federation record: its name, the titles
/// its crew completed, and its cross-machine jobs. A caller maps a
/// non-string name, completion, id, title, or status to an empty
/// string (or `None` for status), mirroring Python's `isinstance`
/// checks; empty values are filtered here, never padded.
pub struct FederationMachine {
    pub name: String,
    pub completions: Vec<String>,
    pub cross_machine_jobs: Vec<CrossMachineJob>,
}

/// One cross-machine job: only a job with a non-empty id and a
/// non-empty title counts; a missing or empty status reads as no
/// status suffix, never a guessed one.
pub struct CrossMachineJob {
    pub id: String,
    pub title: String,
    pub status: Option<String>,
}

/// One trust event: `kind` is "join" or "refusal"; any other kind is
/// skipped. A missing machine name skips the event; a refusal with
/// no detail says the reason is not reported, never an invented one.
pub struct TrustEvent {
    pub kind: String,
    pub machine: String,
    pub detail: Option<String>,
}

/// The whole federation record: the joined machines plus the trust
/// events. The section exists only for a real crew of crews.
pub struct Federation {
    pub machines: Vec<FederationMachine>,
    pub trust_events: Vec<TrustEvent>,
}

/// OS-117: the crew-of-crews section lines for a morning brief, one
/// line per joined machine plus one line per trust event.
///
/// A record naming fewer than two usable machines (non-empty name)
/// returns no lines at all, so a single-machine brief renders the
/// section absent, never empty-padded. A machine with no completions
/// says nothing reported, never a padded title; a cross-machine job
/// without an id and a title is skipped, never guessed; a trust event
/// without a machine name is skipped, and a refusal without a detail
/// says the reason is not reported. Completions and job titles are
/// named verbatim from the record, never re-derived. These are bullet
/// lines in the section the composer adds, so they are redacted by
/// the composer, not here, and the BRF-007 budget trim may drop them
/// like any other section bullet when a brief runs over budget.
pub fn federation_lines(federation: Option<&Federation>) -> Vec<String> {
    let federation = match federation {
        None => return Vec::new(),
        Some(f) => f,
    };
    let usable: Vec<&FederationMachine> = federation
        .machines
        .iter()
        .filter(|m| !m.name.is_empty())
        .collect();
    if usable.len() < 2 {
        return Vec::new();
    }
    let mut lines: Vec<String> = Vec::new();
    for machine in usable {
        let completions: Vec<&str> = machine
            .completions
            .iter()
            .map(String::as_str)
            .filter(|t| !t.is_empty())
            .collect();
        let mut line = if completions.is_empty() {
            format!("- {}: no completions reported", machine.name)
        } else {
            format!(
                "- {}: completed {}",
                machine.name,
                completions.join(", ")
            )
        };
        let usable_cross: Vec<String> = machine
            .cross_machine_jobs
            .iter()
            .filter(|job| !job.id.is_empty() && !job.title.is_empty())
            .map(|job| {
                let status_text = match &job.status {
                    Some(status) if !status.is_empty() => format!(" ({status})"),
                    _ => String::new(),
                };
                format!("job {} {}{}", job.id, job.title, status_text)
            })
            .collect();
        if !usable_cross.is_empty() {
            line.push_str(&format!(
                "; cross-machine jobs: {}",
                usable_cross.join("; ")
            ));
        }
        lines.push(line);
    }
    for event in &federation.trust_events {
        if event.machine.is_empty() {
            continue;
        }
        let detail_text = match &event.detail {
            Some(detail) if !detail.is_empty() => format!(": {detail}"),
            _ => String::new(),
        };
        if event.kind == "join" {
            lines.push(format!(
                "- Trust: {} joined the federation{}",
                event.machine, detail_text
            ));
        } else if event.kind == "refusal" {
            if detail_text.is_empty() {
                lines.push(format!(
                    "- Trust: {} was refused (reason not reported)",
                    event.machine
                ));
            } else {
                lines.push(format!(
                    "- Trust: {} was refused{}",
                    event.machine, detail_text
                ));
            }
        }
    }
    lines
}

/// OS-079: one budget lane in a memory_budget record: lane name plus
/// spent and cap, or remaining directly. A caller maps a non-string
/// lane to an empty string and a non-int (including a bool) cap /
/// spent / remaining value to `None`, mirroring Python's `isinstance`
/// checks; an entry with an empty lane or no usable figure is skipped
/// here, never guessed. `age_label` is `Some` when the entry carries
/// its own `as_of` time, preformed like the record label; `None` falls
/// back to the record's label, mirroring Python's
/// `entry.get("as_of", record.get("as_of"))`.
#[derive(Debug, Clone, PartialEq)]
pub struct MemoryBudgetEntry {
    pub lane: String,
    pub cap: Option<i64>,
    pub spent: Option<i64>,
    pub remaining: Option<i64>,
    pub held: bool,
    pub age_label: Option<String>,
}

/// The whole memory_budget record. `settled_decisions: None` means the
/// snapshot carries no `settled_decisions` key at all, which reads as
/// not reported; `Some(vec![])` means an empty decision list, which
/// reads as none reported. `budgets: None` means no `budgets` key,
/// which reads as the not-reported spend line. `age_label` is the
/// record's own `as_of` time, preformed as
/// `" (as of YYYY-MM-DD HH:MM ET)"`, or
/// `" (snapshot time not reported)"` when the record gives no time;
/// this crate has no time dependency, so the caller supplies the
/// label already formed.
#[derive(Debug, Clone, PartialEq)]
pub struct MemoryBudget {
    pub memory_down: bool,
    pub settled_decisions: Option<Vec<String>>,
    pub budgets: Option<Vec<MemoryBudgetEntry>>,
    pub age_label: String,
}

/// OS-079: the settled-decisions line plus one spend-vs-budget line
/// per lane, opening a brief, right after the window line and before
/// the digest and the sections. A down memory service is said, never
/// hidden behind an absent line: with the service down, no settled
/// decision is shown and none is invented. A missing record field is
/// reported as not reported, never guessed; an empty decision list
/// reads none reported, never padded. A record with no usable budget
/// entry renders the not-reported line instead of a made-up figure.
/// These are not bullet lines, so the BRF-007 budget trim never drops
/// them ahead of a watch item, and they are redacted by the composer,
/// not here. A snapshot without the record carries no lines at all,
/// so older briefs keep their exact shape.
pub fn memory_budget_lines(record: Option<&MemoryBudget>) -> Vec<String> {
    let record = match record {
        None => return Vec::new(),
        Some(r) => r,
    };
    let settled = if record.memory_down {
        "Settled decisions from memory: memory service down, so no settled decisions are shown".to_string()
    } else {
        match &record.settled_decisions {
            None => {
                "Settled decisions from memory: not reported in this snapshot".to_string()
            }
            Some(decisions) => {
                let usable: Vec<&str> = decisions
                    .iter()
                    .map(String::as_str)
                    .filter(|d| !d.is_empty())
                    .collect();
                if usable.is_empty() {
                    "Settled decisions from memory: none reported".to_string()
                } else {
                    format!("Settled decisions from memory: {}", usable.join("; "))
                }
            }
        }
    };
    let mut lines = vec![format!("{}{}", settled, record.age_label)];
    let mut budget_lines: Vec<String> = Vec::new();
    if let Some(budgets) = &record.budgets {
        for entry in budgets {
            if entry.lane.is_empty() {
                continue;
            }
            let text = if let (Some(spent), Some(cap)) = (entry.spent, entry.cap) {
                format!(
                    "Spend: {} lane: {} of {} budget ({} remaining)",
                    entry.lane,
                    spent,
                    cap,
                    cap - spent
                )
            } else if let (Some(remaining), Some(cap)) = (entry.remaining, entry.cap) {
                format!(
                    "Spend: {} lane: {} remaining of {} cap",
                    entry.lane, remaining, cap
                )
            } else if let Some(remaining) = entry.remaining {
                format!("Spend: {} lane: {} remaining", entry.lane, remaining)
            } else {
                continue;
            };
            let mut text = text;
            if entry.held {
                // OS-085: a lane at cap holds new claims, and the hold
                // is visible in the budget line itself.
                text.push_str(" — new claims held");
            }
            let age = entry.age_label.as_deref().unwrap_or(&record.age_label);
            budget_lines.push(format!("{text}{age}"));
        }
    }
    if budget_lines.is_empty() {
        lines.push("Spend vs budget: not reported in this snapshot".to_string());
    } else {
        lines.extend(budget_lines);
    }
    lines
}

/// One aged decision in a memory_depth record: the decision string
/// plus its original date. `original_date: None` — or an empty string,
/// which Python reads the same way — means the original date was not
/// reported, never a guessed date.
#[derive(Debug, Clone, PartialEq)]
pub struct AgedDecision {
    pub decision: String,
    pub original_date: Option<String>,
}

/// One due commitment in a memory_depth record: the commitment string
/// plus its due date. `due: None` — or an empty string — means the due
/// date was not reported, never a guessed date.
#[derive(Debug, Clone, PartialEq)]
pub struct DueCommitment {
    pub commitment: String,
    pub due: Option<String>,
}

/// The whole memory_depth record. `None` for a category means the
/// snapshot carries no such key at all (or it was not a list), which
/// reads as that category's none-reported line; `Some(vec![])` means
/// an empty list, which reads the same way. `age_label` is the
/// record's own `as_of` time, preformed as
/// `" (as of YYYY-MM-DD HH:MM ET)"`, or
/// `" (snapshot time not reported)"` when the record gives no time;
/// this crate has no time dependency, so the caller supplies the
/// label already formed.
#[derive(Debug, Clone, PartialEq)]
pub struct MemoryDepth {
    pub memory_down: bool,
    pub aged_decisions: Option<Vec<AgedDecision>>,
    pub due_commitments: Option<Vec<DueCommitment>>,
    pub fresh_context: Option<Vec<String>>,
    pub age_label: String,
}

/// OS-092: the long-term-memory lines for a daily brief, in the
/// brief's plain-English standard. A down memory service is said in
/// one line — with no age label, exactly as Python returns it — and
/// shows no item at all, never hiding behind an absent section.
/// An aged decision or a due commitment is named verbatim; a missing
/// date reads not reported, never guessed. An entry without its text
/// is skipped, never padded. A category with no usable entries reads
/// none reported, never a padded item, and a record with no usable
/// entry at all still renders its three none-reported lines, so a
/// reader can tell the memory was checked and held nothing. These
/// are plain lines, not bullets, so the BRF-007 budget trim never
/// drops an aged commitment ahead of a watch item, and they are
/// redacted by the composer, not here. A snapshot without the record
/// carries no lines at all, so older briefs keep their exact shape.
pub fn memory_depth_lines(record: Option<&MemoryDepth>) -> Vec<String> {
    let record = match record {
        None => return Vec::new(),
        Some(r) => r,
    };
    if record.memory_down {
        return vec![
            "Long-term memory: memory service down, so no aged decisions, due commitments, or fresh-agent context are shown"
                .to_string(),
        ];
    }
    let age = &record.age_label;
    let mut lines: Vec<String> = Vec::new();
    let usable_aged: Vec<String> = record
        .aged_decisions
        .as_ref()
        .map(|aged| {
            aged.iter()
                .filter(|e| !e.decision.is_empty())
                .map(|e| match e.original_date.as_deref().filter(|d| !d.is_empty()) {
                    Some(date) => format!("Aged decision: {} (from {})", e.decision, date),
                    None => format!(
                        "Aged decision: {} (original date not reported)",
                        e.decision
                    ),
                })
                .collect()
        })
        .unwrap_or_default();
    if usable_aged.is_empty() {
        lines.push(format!("Aged decisions: none reported{age}"));
    } else {
        lines.extend(usable_aged.iter().map(|l| format!("{l}{age}")));
    }
    let usable_due: Vec<String> = record
        .due_commitments
        .as_ref()
        .map(|due| {
            due.iter()
                .filter(|e| !e.commitment.is_empty())
                .map(|e| match e.due.as_deref().filter(|d| !d.is_empty()) {
                    Some(date) => format!("Due commitment: {} (due {})", e.commitment, date),
                    None => format!(
                        "Due commitment: {} (due date not reported)",
                        e.commitment
                    ),
                })
                .collect()
        })
        .unwrap_or_default();
    if usable_due.is_empty() {
        lines.push(format!("Due commitments: none reported{age}"));
    } else {
        lines.extend(usable_due.iter().map(|l| format!("{l}{age}")));
    }
    let usable_context: Vec<&str> = record
        .fresh_context
        .as_ref()
        .map(|ctx| {
            ctx.iter()
                .map(String::as_str)
                .filter(|item| !item.is_empty())
                .collect()
        })
        .unwrap_or_default();
    if usable_context.is_empty() {
        lines.push(format!("Fresh-agent context: none reported{age}"));
    } else {
        lines.extend(
            usable_context
                .iter()
                .map(|item| format!("Fresh-agent context: {item}{age}")),
        );
    }
    lines
}

/// One job in a daily record's queue: both fields must be non-empty
/// to render; a job without both an id and a title is skipped, never
/// padded.
#[derive(Debug, Clone, PartialEq)]
pub struct DailyQueueJob {
    pub id: String,
    pub title: String,
}

/// One needs-word entry in a daily record: a plain question, or a
/// question plus the job id it waits on. `job: None` — or an empty
/// string — means no job id was stated, never a guessed job.
#[derive(Debug, Clone, PartialEq)]
pub struct NeedsWordEntry {
    pub question: String,
    pub job: Option<String>,
}

/// The whole daily record. `None` for a category means the snapshot
/// carries no such key at all (or it was not a list), which reads as
/// that category's none-reported line; `Some(vec![])` means an empty
/// list, which reads the same way. `age_label` is the record's own
/// `as_of` time, preformed as `" (as of YYYY-MM-DD HH:MM ET)"`, or
/// `" (snapshot time not reported)"` when the record gives no time;
/// this crate has no time dependency, so the caller supplies the
/// label already formed.
#[derive(Debug, Clone, PartialEq)]
pub struct Daily {
    pub overnight_results: Option<Vec<String>>,
    pub todays_queue: Option<Vec<DailyQueueJob>>,
    pub needs_word: Option<Vec<NeedsWordEntry>>,
    pub age_label: String,
}

/// OS-075: the daily brief section, in the brief's plain-English
/// standard. A result or a question is named verbatim from the
/// record; a queue job without both an id and a title is skipped,
/// and a needs-word entry without a question is skipped, never
/// padded. A category with no usable entries reads none reported,
/// never a padded item, and a record with no usable entry at all
/// still renders its three none-reported lines, so a reader can
/// tell the daily section was checked and held nothing, rather
/// than guessing whether it was checked. Every line carries its
/// age label, so a stale daily section is never silently presented
/// as current. The lines are plain lines, not bullets, so the
/// BRF-007 budget trim never drops a question waiting on a word
/// ahead of a watch item, and they are redacted by the composer,
/// not here. They render whenever the snapshot carries a daily
/// record, in a morning-format brief; a snapshot without the
/// record carries none, so older briefs keep their exact shape.
pub fn daily_lines(record: Option<&Daily>) -> Vec<String> {
    let record = match record {
        None => return Vec::new(),
        Some(r) => r,
    };
    let age = &record.age_label;
    let mut lines: Vec<String> = Vec::new();
    let usable_results: Vec<&str> = record
        .overnight_results
        .as_ref()
        .map(|results| {
            results.iter().map(String::as_str).filter(|item| !item.is_empty()).collect()
        })
        .unwrap_or_default();
    if usable_results.is_empty() {
        lines.push(format!("Overnight results: none reported{age}"));
    } else {
        lines.extend(
            usable_results.iter().map(|item| format!("Overnight result: {item}{age}")),
        );
    }
    let usable_queue: Vec<&DailyQueueJob> = record
        .todays_queue
        .as_ref()
        .map(|queue| {
            queue.iter().filter(|job| !job.id.is_empty() && !job.title.is_empty()).collect()
        })
        .unwrap_or_default();
    if usable_queue.is_empty() {
        lines.push(format!("Today's queue: none reported{age}"));
    } else {
        lines.extend(usable_queue.iter().map(|job| {
            format!("Today's queue: job {} {}{age}", job.id, job.title)
        }));
    }
    let usable_needs: Vec<String> = record
        .needs_word
        .as_ref()
        .map(|needs| {
            needs
                .iter()
                .filter(|entry| !entry.question.is_empty())
                .map(|entry| match entry.job.as_deref().filter(|job| !job.is_empty()) {
                    Some(job) => format!("{} (job {})", entry.question, job),
                    None => entry.question.clone(),
                })
                .collect()
        })
        .unwrap_or_default();
    if usable_needs.is_empty() {
        lines.push(format!("Needs your word: none reported{age}"));
    } else {
        lines.extend(
            usable_needs.iter().map(|item| format!("Needs your word: {item}{age}")),
        );
    }
    lines
}

/// STR-002: `_format_brief_time` — a stored brief timestamp as
/// `"YYYY-MM-DD HH:MM ET"` in America/New_York, the zone the
/// BRF-011 morning schedule uses. This crate has no time
/// dependency, so the conversion is done by hand: civil date from
/// days since the epoch (Howard Hinnant's algorithm), Eastern
/// daylight time from the second Sunday of March 07:00 UTC to the
/// first Sunday of November 06:00 UTC, otherwise Eastern standard
/// time. Python returns None for a non-numeric timestamp; Rust
/// timestamps are numeric by type, so there is no such case here.
/// The algorithm was checked against Python's zoneinfo for every
/// hour of 2026 plus the DST edges, with zero mismatches.
pub fn format_brief_time(ts: i64) -> String {
    fn civil_from_days(z: i64) -> (i64, i64, i64) {
        let z = z + 719468;
        let era = z.div_euclid(146097);
        let doe = z - era * 146097;
        let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
        let y = yoe + era * 400;
        let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
        let mp = (5 * doy + 2) / 153;
        let d = doy - (153 * mp + 2) / 5 + 1;
        let m = if mp < 10 { mp + 3 } else { mp - 9 };
        let y = if m <= 2 { y + 1 } else { y };
        (y, m, d)
    }
    fn days_from_civil(mut y: i64, m: i64, d: i64) -> i64 {
        if m <= 2 {
            y -= 1;
        }
        let era = y.div_euclid(400);
        let yoe = y - era * 400;
        let mp = if m > 2 { m - 3 } else { m + 9 };
        let doy = (153 * mp + 2) / 5 + d - 1;
        let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
        era * 146097 + doe - 719468
    }
    // Weekday with Sunday = 0: 1970-01-01 was a Thursday.
    fn weekday_sunday0(days: i64) -> i64 {
        (days + 4).rem_euclid(7)
    }
    let days = ts.div_euclid(86400);
    let (year, _, _) = civil_from_days(days);
    let first_sunday = |month: i64| -> i64 {
        let first = days_from_civil(year, month, 1);
        1 + (7 - weekday_sunday0(first)).rem_euclid(7)
    };
    let dst_start =
        days_from_civil(year, 3, first_sunday(3) + 7) * 86400 + 7 * 3600;
    let dst_end = days_from_civil(year, 11, first_sunday(11)) * 86400 + 6 * 3600;
    let offset = if dst_start <= ts && ts < dst_end {
        -4 * 3600
    } else {
        -5 * 3600
    };
    let local = ts + offset;
    let local_days = local.div_euclid(86400);
    let local_secs = local.rem_euclid(86400);
    let (y, m, d) = civil_from_days(local_days);
    format!(
        "{:04}-{:02}-{:02} {:02}:{:02} ET",
        y,
        m,
        d,
        local_secs / 3600,
        (local_secs % 3600) / 60
    )
}

/// OS-103: the age label for one environment line.
///
/// `as_of` is the Unix timestamp for when the line's source was
/// read. A known time formats as `" (as of YYYY-MM-DD HH:MM ET)"`
/// through `format_brief_time`; `None` yields
/// `" (snapshot time not reported)"`, so a field whose age is
/// unknown is never silently presented as current. Python
/// returns the not-reported label for any non-numeric `as_of`;
/// Rust timestamps are numeric by type, so the caller passes
/// `None` for those cases.
pub fn environment_age_label(as_of: Option<i64>) -> String {
    match as_of {
        Some(ts) => format!(" (as of {})", format_brief_time(ts)),
        None => " (snapshot time not reported)".to_string(),
    }
}

/// OS-103 follow-up: the "repo" part of an environment record,
/// read from a local git checkout at generation time.
///
/// Returns the current branch, the short commit, and the count
/// of uncommitted files (porcelain lines, so untracked files
/// count too), stamped with `now` or the current time. This is
/// only the repo quarter of the environment record: a caller
/// merges it with the bus, jobs, and budget parts from their own
/// sources, and a record with only this part still renders the
/// other three lines as not reported. Returns `None` instead of
/// failing when the path is not a git checkout, git is missing,
/// a command fails, the HEAD is detached (no branch to name),
/// or any output is unusable, so a repo the record does not
/// describe renders as not reported by `environment_lines`,
/// never guessed.
///
/// Two documented deviations from Python. First, Python
/// defaults `repo_path` to its own repo root (the parent of
/// `intel/`); a Rust binary has no source-tree location, so
/// `None` here means "no path given" and yields `None` — the
/// caller passes the checkout path. Second, Python caps each
/// git call at 10 seconds; `std::process::Command` has no
/// timeout, so that cap is not enforced here — the calls run
/// to completion, as on Python's success path.
#[derive(Debug, Clone, PartialEq)]
pub struct EnvironmentRepoRecord {
    pub branch: String,
    pub commit: String,
    pub dirty: i64,
    pub as_of: i64,
}

pub fn environment_repo_record(
    repo_path: Option<&str>,
    now: Option<i64>,
) -> Option<EnvironmentRepoRecord> {
    let path = repo_path?;
    let run = |args: &[&str]| -> Option<String> {
        let output = std::process::Command::new("git")
            .arg("-C")
            .arg(path)
            .args(args)
            .output()
            .ok()?;
        if !output.status.success() {
            return None;
        }
        Some(String::from_utf8_lossy(&output.stdout).into_owned())
    };
    let branch = run(&["rev-parse", "--abbrev-ref", "HEAD"])?;
    let commit = run(&["rev-parse", "--short", "HEAD"])?;
    let status = run(&["status", "--porcelain"])?;
    let branch = branch.trim().to_string();
    let commit = commit.trim().to_string();
    if branch.is_empty() || branch == "HEAD" || commit.is_empty() {
        return None;
    }
    let dirty = status
        .lines()
        .filter(|line| !line.trim().is_empty())
        .count() as i64;
    let as_of = match now {
        Some(t) => t,
        None => std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs() as i64)
            .unwrap_or(0),
    };
    Some(EnvironmentRepoRecord { branch, commit, dirty, as_of })
}

/// OS-103 follow-up: the "jobs" part of an environment record,
/// read from a stated jobs list at generation time.
///
/// The caller passes the snapshot's own jobs list — the same
/// list the brief composer already sees — and gets back the
/// list to store as the environment record's "jobs" value, in
/// job order. Only claimed jobs count as work in progress,
/// exactly as `environment_lines` renders them: an entry counts
/// only when its status is "claimed" and it carries a non-empty
/// claim nick and a non-empty title; open, blocked, done,
/// claim-less, title-less, and non-dict entries are skipped,
/// never guessed into a name. The id is carried only when it
/// is a non-empty string or an int, and is otherwise left out
/// rather than invented. Returns `None` when there is no
/// usable jobs list, so the caller leaves "jobs" out of the
/// record and the Working now line reads not reported instead
/// of falsely reading nobody holds a job; an empty list, or a
/// list with no claimed usable job, returns an empty list and
/// renders as nobody holds a claimed job. The list carries no
/// time of its own: the Working now line's age label comes
/// from the record's as_of, which the caller stamps when it
/// merges this part in, at the same instant the jobs list was
/// read. This is only the jobs quarter: a record carrying
/// only this part still renders repo, bus, and budget as not
/// reported. Never raises.
///
/// Typed-input mapping, following this module's convention:
/// the caller passes `None` for a non-list jobs value (Python
/// returns `None` for it), and `Some` for a list or tuple;
/// a non-dict entry has no typed form, so the caller drops
/// it before the call; a non-string status, claim, or title
/// maps to an empty string and is then filtered here; a
/// missing, bool, or other unusable id maps to `None`, and an
/// empty-string id is dropped here, never carried.
#[derive(Debug, Clone, PartialEq)]
pub enum EnvironmentJobId {
    Text(String),
    Int(i64),
}

/// One stated job as the caller sees it, before filtering: the
/// status, claim nick, and title verbatim, plus the id when the
/// caller could read one (a non-empty string or an int).
#[derive(Debug, Clone, PartialEq)]
pub struct RawEnvironmentJob {
    pub status: String,
    pub claim: String,
    pub title: String,
    pub id: Option<EnvironmentJobId>,
}

/// One entry of the jobs part, mirroring Python's entry dict:
/// title, status (always "claimed" here), and claim nick, plus
/// the id only when it was a non-empty string or an int.
#[derive(Debug, Clone, PartialEq)]
pub struct EnvironmentJobsEntry {
    pub title: String,
    pub status: String,
    pub claim: String,
    pub id: Option<EnvironmentJobId>,
}

pub fn environment_jobs_record(
    jobs: Option<&[RawEnvironmentJob]>,
) -> Option<Vec<EnvironmentJobsEntry>> {
    let jobs = jobs?;
    let mut claimed = Vec::new();
    for job in jobs {
        if job.status != "claimed" {
            continue;
        }
        if job.claim.is_empty() || job.title.is_empty() {
            continue;
        }
        let id = match &job.id {
            Some(EnvironmentJobId::Text(text)) if !text.is_empty() => {
                Some(EnvironmentJobId::Text(text.clone()))
            }
            Some(EnvironmentJobId::Int(value)) => {
                Some(EnvironmentJobId::Int(*value))
            }
            _ => None,
        };
        claimed.push(EnvironmentJobsEntry {
            title: job.title.clone(),
            status: "claimed".to_string(),
            claim: job.claim.clone(),
            id,
        });
    }
    Some(claimed)
}

/// OS-103 follow-up: the "bus" part of an environment record,
/// read from the snapshot's own messages list at generation
/// time.
///
/// The caller passes the snapshot's messages list — the same
/// list the brief composer already sees — and the room or rooms
/// that list covers, and gets back the dict to store as the
/// environment record's "bus" value: "rooms" (non-empty strings,
/// in caller order, duplicates dropped), "messages" (the count
/// of usable entries), and "as_of" (the stamp passed as `now`,
/// or the current time). Only dict and string entries count
/// toward the total; other entries are skipped, never guessed
/// into a message. The documented snapshot message shape carries
/// no room field, so rooms come from the caller, never from the
/// messages: a caller that states no room gets "rooms" as an
/// empty list, and the Bus line still carries the count, without
/// a room claim. The count is the count of messages in the passed
/// list — the snapshot window — never a claim about bus history
/// beyond that window. Returns `None` when there is no usable
/// messages list, so the caller leaves "bus" out of the record
/// and the Bus line reads not reported instead of falsely reading
/// zero messages; an empty list returns a record with 0 messages,
/// which renders as an empty window. This is only the bus quarter:
/// a record carrying only this part still renders repo, jobs, and
/// budget as not reported. Never fails.
///
/// Typed-input mapping, following this module's convention:
/// the caller passes `None` for a non-list messages value (Python
/// returns `None` for it) and for a rooms value that is neither a
/// string nor a list; a non-string room entry maps to
/// `BusRoom::Other` and is dropped here, and a non-dict,
/// non-string message maps to `RawMessage::Other` and is skipped
/// here. A non-int `now` maps to `None` and reads the wall clock,
/// mirroring Python's fallback to the current time.
#[derive(Debug, Clone, PartialEq)]
pub enum BusRoom {
    /// A room name as stated by the caller.
    Name(String),
    /// Any other shape: Python's `isinstance(room, str)` check
    /// drops it, so it can never name a room.
    Other,
}

/// The rooms a bus record covers, as the caller states them:
/// one room string, or a list of room entries.
#[derive(Debug, Clone, PartialEq)]
pub enum BusRooms {
    Single(String),
    List(Vec<BusRoom>),
}

/// One bus part, mirroring Python's record dict: rooms in caller
/// order, the usable message count, and the stamp.
#[derive(Debug, Clone, PartialEq)]
pub struct EnvironmentBusRecord {
    pub rooms: Vec<String>,
    pub messages: i64,
    pub as_of: i64,
}

pub fn environment_bus_record(
    messages: Option<&[RawMessage]>,
    rooms: Option<&BusRooms>,
    now: Option<i64>,
) -> Option<EnvironmentBusRecord> {
    let messages = messages?;
    let mut room_list: Vec<String> = Vec::new();
    if let Some(rooms) = rooms {
        let candidates: Vec<String> = match rooms {
            BusRooms::Single(room) => vec![room.clone()],
            BusRooms::List(entries) => entries
                .iter()
                .filter_map(|entry| match entry {
                    BusRoom::Name(name) => Some(name.clone()),
                    BusRoom::Other => None,
                })
                .collect(),
        };
        for room in candidates {
            if !room.is_empty() && !room_list.contains(&room) {
                room_list.push(room);
            }
        }
    }
    let count = messages
        .iter()
        .filter(|message| {
            matches!(message, RawMessage::Dict { .. } | RawMessage::Text(_))
        })
        .count() as i64;
    let as_of = match now {
        Some(t) => t,
        None => std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs() as i64)
            .unwrap_or(0),
    };
    Some(EnvironmentBusRecord {
        rooms: room_list,
        messages: count,
        as_of,
    })
}

/// STR-002 image extensions: the digest lists what the pointer
/// itself names, so only these extensions count as screenshots.
/// A `.txt`, `.pdf`, or extension-less pointer is a file share,
/// not a screenshot, and is skipped.
const IMAGE_EXTENSIONS: &[&str] = &[".png", ".jpg", ".jpeg", ".gif", ".webp"];

/// A raw snapshot message for the screenshot extractor, mirroring
/// what Python's `_message_parts` accepts, plus the dict entry's
/// numeric timestamp (None for a bus string, which carries no
/// time, so no time is claimed for it). This is separate from
/// `window::RawMessage` because that type carries no timestamp
/// and the digest needs one. A float timestamp arrives truncated
/// to an int, mirroring Python's `int(ts)` at format time; a bool
/// timestamp is not numeric in Python, so the caller passes None
/// for it.
#[derive(Debug, Clone, PartialEq)]
pub enum ScreenshotMessage {
    /// Dict form: nick/text as the store entry carries them, plus
    /// the entry's numeric ts when it has one.
    Dict {
        nick: String,
        text: String,
        ts: Option<i64>,
    },
    /// Bus string form: `"nick: text"`, or plain text with no nick.
    Text(String),
    /// Any other shape: Python returns `("", "")` with no time.
    Other,
}

/// One screenshot ref, mirroring Python's ref dict: one per
/// distinct image, in snapshot order with a repost moved to its
/// latest occurrence. `hash` is lowercased, `file` verbatim;
/// `caption` is the message text with every BLOB pointer removed,
/// whitespace-collapsed, possibly empty for a pointer-only post.
/// This digest produces no verdict: whether a screenshot shows a
/// working or broken build is the SAM pass's call, not this
/// extractor's, and no verdict field is invented here.
#[derive(Debug, Clone, PartialEq)]
pub struct ScreenshotRef {
    pub nick: String,
    pub file: String,
    pub hash: String,
    pub chunks: u64,
    pub ts: Option<i64>,
    pub caption: String,
}

fn is_hex_byte(b: u8) -> bool {
    b.is_ascii_hexdigit()
}

fn is_filename_byte(b: u8) -> bool {
    matches!(b, b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'.' | b'_' | b'-')
}

/// Scan one BLOB pointer at `bytes[start..]` where that slice
/// starts with `"BLOB:"`. Returns (hash, file, chunks, end) on a
/// match. Mirrors `_BLOB_POINTER_RE` =
/// `BLOB:([0-9a-fA-F]{16}):([A-Za-z0-9._-]+):(\d+)`.
fn scan_blob_pointer(bytes: &[u8], start: usize) -> Option<(String, String, u64, usize)> {
    let mut i = start + 5; // past "BLOB:"
    let hash_bytes = bytes.get(i..i + 16)?;
    if !hash_bytes.iter().all(|b| is_hex_byte(*b)) {
        return None;
    }
    let hash: String = hash_bytes.iter().map(|b| *b as char).collect();
    i += 16;
    if bytes.get(i) != Some(&b':') {
        return None;
    }
    i += 1;
    let file_start = i;
    while i < bytes.len() && is_filename_byte(bytes[i]) {
        i += 1;
    }
    if i == file_start {
        return None;
    }
    let file = std::str::from_utf8(&bytes[file_start..i]).ok()?.to_string();
    if bytes.get(i) != Some(&b':') {
        return None;
    }
    i += 1;
    let chunks_start = i;
    while i < bytes.len() && bytes[i].is_ascii_digit() {
        i += 1;
    }
    if i == chunks_start {
        return None;
    }
    // Digits only by construction; a count too large for u64 reads
    // as 0 rather than failing the whole brief.
    let chunks = std::str::from_utf8(&bytes[chunks_start..i])
        .ok()?
        .parse::<u64>()
        .unwrap_or(0);
    Some((hash, file, chunks, i))
}

/// All BLOB pointers in a message text, in order. A failed match
/// at one position advances one byte, mirroring regex finditer.
fn scan_blob_pointers(text: &str) -> Vec<(String, String, u64)> {
    let bytes = text.as_bytes();
    let mut out = Vec::new();
    let mut i = 0;
    while i + 5 <= bytes.len() {
        if &bytes[i..i + 5] == b"BLOB:" {
            if let Some((hash, file, chunks, end)) = scan_blob_pointer(bytes, i) {
                out.push((hash, file, chunks));
                i = end;
                continue;
            }
        }
        i += 1;
    }
    out
}

/// A message text with every BLOB pointer removed (any pointer,
/// image or not — Python's `sub` removes all regex matches),
/// whitespace-collapsed. All cut points are ASCII, so the kept
/// slices are always valid char boundaries.
fn strip_blob_pointers(text: &str) -> String {
    let bytes = text.as_bytes();
    let mut kept = String::new();
    let mut cursor = 0;
    let mut i = 0;
    while i + 5 <= bytes.len() {
        if &bytes[i..i + 5] == b"BLOB:" {
            if let Some((_, _, _, end)) = scan_blob_pointer(bytes, i) {
                kept.push_str(&text[cursor..i]);
                cursor = end;
                i = end;
                continue;
            }
        }
        i += 1;
    }
    kept.push_str(&text[cursor..]);
    kept
}

/// STR-002: screenshot digest for a brief record. Scans snapshot
/// messages for BLOB pointers naming an image file, in snapshot
/// order. Returns [] for an empty or missing message list, never
/// an error. The same image posted twice (same hash and file)
/// yields one ref, at its latest occurrence.
pub fn extract_screenshot_refs(
    messages: Option<&[ScreenshotMessage]>,
) -> Vec<ScreenshotRef> {
    let messages = match messages {
        None => return Vec::new(),
        Some(m) => m,
    };
    let mut refs: Vec<ScreenshotRef> = Vec::new();
    for message in messages {
        let (nick, text, ts) = match message {
            ScreenshotMessage::Dict { nick, text, ts } => {
                (nick.clone(), text.clone(), *ts)
            }
            ScreenshotMessage::Text(s) => match s.split_once(": ") {
                Some((nick, text)) => (nick.to_string(), text.to_string(), None),
                None => (String::new(), s.clone(), None),
            },
            ScreenshotMessage::Other => (String::new(), String::new(), None),
        };
        let caption = strip_blob_pointers(&text)
            .split_whitespace()
            .collect::<Vec<_>>()
            .join(" ");
        for (hash, file, chunks) in scan_blob_pointers(&text) {
            if !IMAGE_EXTENSIONS
                .iter()
                .any(|ext| file.to_lowercase().ends_with(ext))
            {
                continue;
            }
            let hash = hash.to_lowercase();
            let new_ref = ScreenshotRef {
                nick: nick.clone(),
                file: file.clone(),
                hash: hash.clone(),
                chunks,
                ts,
                caption: caption.clone(),
            };
            // Latest rule: a repost drops its earlier ref and moves
            // to the end, so each screenshot is handed over once.
            if let Some(idx) = refs
                .iter()
                .position(|r| r.hash == hash && r.file == file)
            {
                refs.remove(idx);
            }
            refs.push(new_ref);
        }
    }
    refs
}

/// STR-002: one plain line per screenshot ref, in ref order. Each
/// line names the sender, the file, and the time in ET when the
/// message carried one, else "time not reported" — never a guessed
/// time — plus the post's caption when it has one. The lines are
/// not bullets, so the BRF-007 budget trim drops section bullets
/// before it ever touches these lines. Returns [] for no refs, so
/// a brief without screenshots keeps its exact older shape.
pub fn screenshot_digest_lines(refs: Option<&[ScreenshotRef]>) -> Vec<String> {
    let refs = match refs {
        None => return Vec::new(),
        Some(r) => r,
    };
    refs.iter()
        .map(|r| {
            let when = r.ts.map(format_brief_time);
            let mut line = format!(
                "{} shared {} at {}",
                r.nick,
                r.file,
                when.as_deref().unwrap_or("time not reported")
            );
            if !r.caption.is_empty() {
                line.push_str(&format!(": {}", r.caption));
            }
            line
        })
        .collect()
}

/// BRF-029: nicks present in the room with no prior message.
///
/// A nick counts as new when it appears in the snapshot's
/// presence list but has authored none of the snapshot's
/// messages (dict entries or "nick: text" bus strings). Presence
/// order is kept, duplicates dropped, empty nicks ignored. A
/// nick that only holds a job claim or a caps entry is still
/// new — only a prior message counts, so jobs and caps are not
/// inputs here at all. Returns [] for no messages or no
/// presence, never an error.
#[derive(Debug, Clone, PartialEq)]
pub enum PresenceEntry {
    /// A presence-list entry, verbatim.
    Nick(String),
    /// Any other shape: Python's `isinstance(nick, str)` check
    /// skips it, so it can never be a new nick.
    Other,
}

/// A snapshot presence value: a list, or a dict (whose keys are
/// the presence list, mirroring `list(presence.keys())`).
#[derive(Debug, Clone, PartialEq)]
pub enum Presence {
    List(Vec<PresenceEntry>),
    DictKeys(Vec<String>),
}

pub fn detect_new_nicks(
    messages: Option<&[RawMessage]>,
    presence: Option<&Presence>,
) -> Vec<String> {
    let mut authors: Vec<String> = Vec::new();
    if let Some(messages) = messages {
        for message in messages {
            let (nick, _text) = super::window::message_parts(message);
            if !nick.is_empty() && !authors.contains(&nick) {
                authors.push(nick);
            }
        }
    }
    let present: Vec<String> = match presence {
        None => return Vec::new(),
        Some(Presence::List(entries)) => entries
            .iter()
            .filter_map(|e| match e {
                PresenceEntry::Nick(n) if !n.is_empty() => Some(n.clone()),
                _ => None,
            })
            .collect(),
        Some(Presence::DictKeys(keys)) => keys
            .iter()
            .filter(|k| !k.is_empty())
            .cloned()
            .collect(),
    };
    let mut new_nicks: Vec<String> = Vec::new();
    for nick in present {
        if authors.contains(&nick) || new_nicks.contains(&nick) {
            continue;
        }
        new_nicks.push(nick);
    }
    new_nicks
}

/// BRF-029: one offer record per new nick, mirroring Python's
/// offer dict: room (empty room reads as "main"), nick, kind
/// "onjoin", status "offered", offered_at, brief_generated
/// false, brief_id None. The offer is the whole effect: this
/// composes no brief text, stores nothing, and posts nothing.
/// A brief comes into being only when `generate_brief` is
/// invoked for that nick afterwards. `now` is a Unix time; when
/// None, the wall clock is read (Python's `time.time()`).
#[derive(Debug, Clone, PartialEq)]
pub struct OnjoinOffer {
    pub room: String,
    pub nick: String,
    pub kind: String,
    pub status: String,
    pub offered_at: i64,
    pub brief_generated: bool,
    pub brief_id: Option<String>,
}

pub fn offer_onjoin_brief(
    messages: Option<&[RawMessage]>,
    presence: Option<&Presence>,
    room: &str,
    now: Option<i64>,
) -> Vec<OnjoinOffer> {
    let offered_at = match now {
        Some(t) => t,
        None => std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs() as i64)
            .unwrap_or(0),
    };
    let clean_room = if room.is_empty() { "main" } else { room };
    detect_new_nicks(messages, presence)
        .into_iter()
        .map(|nick| OnjoinOffer {
            room: clean_room.to_string(),
            nick,
            kind: "onjoin".to_string(),
            status: "offered".to_string(),
            offered_at,
            brief_generated: false,
            brief_id: None,
        })
        .collect()
}

/// BRF-011: next 08:00 ET run time, as a Unix timestamp.
///
/// Uses America/New_York, so the 08:00 ET brief stays at 08:00
/// across daylight-saving changes. Returns the next `hour`:00
/// strictly after `now` (or after the current time when `now`
/// is None). Pure std, no timezone crate: the DST window is the
/// post-2007 US rule — second Sunday of March 07:00 UTC through
/// first Sunday of November 06:00 UTC — the same window
/// `format_brief_time` uses. `hour` is a wall-clock hour (8 by
/// default); 08:00 never falls in the spring gap or the autumn
/// repeat hour, so the wall-to-UTC conversion is unambiguous.
pub fn next_morning_run(now: Option<i64>, hour: i64) -> i64 {
    fn civil_from_days(z: i64) -> (i64, i64, i64) {
        let z = z + 719468;
        let era = z.div_euclid(146097);
        let doe = z - era * 146097;
        let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
        let y = yoe + era * 400;
        let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
        let mp = (5 * doy + 2) / 153;
        let d = doy - (153 * mp + 2) / 5 + 1;
        let m = if mp < 10 { mp + 3 } else { mp - 9 };
        let y = if m <= 2 { y + 1 } else { y };
        (y, m, d)
    }
    fn days_from_civil(mut y: i64, m: i64, d: i64) -> i64 {
        if m <= 2 {
            y -= 1;
        }
        let era = y.div_euclid(400);
        let yoe = y - era * 400;
        let mp = if m > 2 { m - 3 } else { m + 9 };
        let doy = (153 * mp + 2) / 5 + d - 1;
        let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
        era * 146097 + doe - 719468
    }
    // Weekday with Sunday = 0: 1970-01-01 was a Thursday.
    fn weekday_sunday0(days: i64) -> i64 {
        (days + 4).rem_euclid(7)
    }
    // Offset in seconds for a UTC instant: -4h inside the DST
    // window, -5h outside it.
    fn offset_at(ts: i64) -> i64 {
        let days = ts.div_euclid(86400);
        let (year, _, _) = civil_from_days(days);
        let first_sunday = |month: i64| -> i64 {
            let first = days_from_civil(year, month, 1);
            1 + (7 - weekday_sunday0(first)).rem_euclid(7)
        };
        let dst_start =
            days_from_civil(year, 3, first_sunday(3) + 7) * 86400 + 7 * 3600;
        let dst_end =
            days_from_civil(year, 11, first_sunday(11)) * 86400 + 6 * 3600;
        if dst_start <= ts && ts < dst_end {
            -4 * 3600
        } else {
            -5 * 3600
        }
    }
    let now = match now {
        Some(t) => t,
        None => std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs() as i64)
            .unwrap_or(0),
    };
    let local = now + offset_at(now);
    let local_days = local.div_euclid(86400);
    let local_secs = local.rem_euclid(86400);
    // The candidate is today at `hour`:00 local; strictly-after
    // means an exact hit rolls to tomorrow, mirroring Python's
    // `candidate <= current` check.
    let mut cand_days = local_days;
    if hour * 3600 <= local_secs {
        cand_days += 1;
    }
    let (year, _, _) = civil_from_days(cand_days);
    let first_sunday = |month: i64| -> i64 {
        let first = days_from_civil(year, month, 1);
        1 + (7 - weekday_sunday0(first)).rem_euclid(7)
    };
    let dst_start_day = days_from_civil(year, 3, first_sunday(3) + 7);
    let dst_end_day = days_from_civil(year, 11, first_sunday(11));
    // 08:00 is past both 02:00 transitions, so the date-range
    // check gives the right offset: DST on its start day, EST
    // on its end day.
    let offset = if dst_start_day <= cand_days && cand_days < dst_end_day {
        -4 * 3600
    } else {
        -5 * 3600
    };
    cand_days * 86400 + hour * 3600 - offset
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

/// BRF-028: a stored brief record as `_brief_text_from_record` reads it.
/// Only the fields that function touches: verbatim `text`, the stored
/// `source_window` (string or dict form, shared with `window`), and
/// the stored `sections` map. A record that predates the text field
/// carries `text: None` and renders from its sections instead.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct StoredBriefText {
    pub text: Option<String>,
    pub source_window: Option<SourceWindow>,
    pub sections: HashMap<String, Vec<String>>,
}

/// Render a float the way Python `str()` does: a whole float keeps
/// its `.0` (`24.0`, never `24`). Ported oddity: `_brief_text_from_record`
/// does NOT apply the BRF-024 whole-float-to-int rule `_window_line`
/// uses, so its dict window can read "last 24.0 hours" where the
/// window line reads "last 24 hours".
fn python_float(v: f64) -> String {
    if v.is_finite() && v.fract() == 0.0 {
        format!("{v:.1}")
    } else {
        v.to_string()
    }
}

fn opt_count(v: &Option<i64>) -> String {
    match v {
        Some(n) => n.to_string(),
        // Mirror Python's `.get` on a missing key: it renders None.
        None => "None".to_string(),
    }
}

/// BRF-028: text for a stored brief record.
///
/// A stored record's verbatim `text` wins exactly as stored — a
/// guard hit returns the brief that was generated, never a
/// recomposition. Blank or missing text renders from the stored
/// sections instead: the window line first (string windows render
/// verbatim even when empty; dict windows render their counts with
/// missing keys as `None`; a missing window renders no line at
/// all), then each frozen `BRIEF_SECTIONS` heading with its items
/// as `- ` bullets, or "Nothing reported in this window" when the
/// section is missing or empty. The result always ends with one
/// trailing newline, mirroring Python's `"\n".join(lines) + "\n"`.
/// A `None` record renders as a record with no text, no window,
/// and no sections. Section items are typed `Vec<String>`: a
/// non-list section value has no Rust form (Python would iterate
/// its characters, which is a malformed record, not a rendering).
pub fn brief_text_from_record(record: Option<&StoredBriefText>) -> String {
    if let Some(rec) = record {
        if let Some(text) = &rec.text {
            if !text.trim().is_empty() {
                return text.clone();
            }
        }
    }
    let mut lines: Vec<String> = Vec::new();
    if let Some(rec) = record {
        if let Some(window) = &rec.source_window {
            match window {
                SourceWindow::Text(t) => lines.push(format!("Window: {t}")),
                SourceWindow::Dict {
                    max_messages,
                    max_hours,
                    messages_kept,
                    messages_dropped,
                } => {
                    let hours = match max_hours {
                        Some(WindowHours::Int(v)) => v.to_string(),
                        Some(WindowHours::Float(v)) => python_float(*v),
                        None => "None".to_string(),
                    };
                    lines.push(format!(
                        "Window: last {} messages or last {} hours, {} kept, {} dropped",
                        opt_count(max_messages),
                        hours,
                        opt_count(messages_kept),
                        opt_count(messages_dropped)
                    ));
                }
            }
        }
    }
    for section in BRIEF_SECTIONS {
        let section = *section;
        lines.push(String::new());
        lines.push(section.to_string());
        match record.and_then(|rec| rec.sections.get(section)) {
            Some(items) if !items.is_empty() => {
                for item in items {
                    lines.push(format!("- {item}"));
                }
            }
            _ => lines.push("Nothing reported in this window".to_string()),
        }
    }
    format!("{}\n", lines.join("\n"))
}

/// A stored brief's timestamp as Python carries it: `ts` (or the
/// `generated_at` fallback) may be an int or a float; a bool is
/// rejected by Python's `isinstance` check, and a string or
/// missing key skips the entry. The Rust form can only carry
/// int/float, so a string timestamp has no Rust form — a store
/// adapter maps it to `None` (missing), which also falls back to
/// `generated_at` where Python would skip outright. That is a
/// malformed-entry edge, not a stored shape: `store_brief`
/// writes int timestamps.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum BriefTs {
    Int(i64),
    Float(f64),
}

impl BriefTs {
    fn as_f64(self) -> f64 {
        match self {
            BriefTs::Int(v) => v as f64,
            BriefTs::Float(v) => v,
        }
    }
}

/// One brief-index entry as `list_briefs` returns it, oldest
/// first: `ts` with the `generated_at` fallback. `None` on a
/// field means the key is missing (or, for a store adapter, that
/// the value was not an int/float).
#[derive(Debug, Clone, PartialEq)]
pub struct BriefIndexEntry {
    pub ts: Option<BriefTs>,
    pub generated_at: Option<BriefTs>,
}

/// A stored brief record as `find_recent_brief` returns it: the
/// guard fields (`kind`, `source_window`) plus the render fields
/// `brief_text_from_record` reads. The full record Python
/// returns carries more (room, model, spend_id), but the guard
/// only compares kind and window and the caller only renders
/// text — the rest arrives with `generate_brief`.
#[derive(Debug, Clone, PartialEq)]
pub struct StoredBriefRecord {
    pub kind: String,
    pub stored: StoredBriefText,
}

/// The brief store surface `find_recent_brief` reads.
/// `list_briefs` / `get_brief` themselves are Redis-backed
/// (`store_brief` / `get_brief` / `list_briefs`, BRF-009) and
/// land with `generate_brief`; until then the guard runs
/// against this trait, and tests run against a fake. `Err` on
/// either call is the Rust form of a Python store exception:
/// the guard fails open (list failure) or skips the entry (get
/// failure), never blocks a fresh brief.
pub trait BriefStore {
    fn list_briefs(&self, room: &str) -> Result<Vec<BriefIndexEntry>, String>;
    fn get_brief(&self, room: &str, ts: BriefTs) -> Result<Option<StoredBriefRecord>, String>;
}

/// Window equality the way Python dict equality does it: a text
/// window equals only the same text; a dict window equals only
/// a dict window with equal counts and equal hours — except
/// that Python numbers compare across int/float, so `Int(24)`
/// equals `Float(24.0)` here where derived `PartialEq` would
/// say no. Known gaps, same as the render form: a missing dict
/// key and a null-valued key both arrive as `None` and compare
/// equal here, where Python says missing != null; and extra
/// dict keys have no Rust form and are ignored.
fn source_window_equal(a: &Option<SourceWindow>, b: &Option<SourceWindow>) -> bool {
    match (a, b) {
        (None, None) => true,
        (Some(SourceWindow::Text(x)), Some(SourceWindow::Text(y))) => x == y,
        (
            Some(SourceWindow::Dict {
                max_messages: am,
                max_hours: ah,
                messages_kept: ak,
                messages_dropped: ad,
            }),
            Some(SourceWindow::Dict {
                max_messages: bm,
                max_hours: bh,
                messages_kept: bk,
                messages_dropped: bd,
            }),
        ) => {
            am == bm
                && ak == bk
                && ad == bd
                && match (ah, bh) {
                    (None, None) => true,
                    (Some(WindowHours::Int(x)), Some(WindowHours::Int(y))) => x == y,
                    (Some(WindowHours::Float(x)), Some(WindowHours::Float(y))) => x == y,
                    (Some(WindowHours::Int(x)), Some(WindowHours::Float(y))) => (*x as f64) == *y,
                    (Some(WindowHours::Float(x)), Some(WindowHours::Int(y))) => *x == (*y as f64),
                    _ => false,
                }
        }
        _ => false,
    }
}

/// BRF-028: find a stored brief for the same room, kind, window.
///
/// Returns the stored record when one was generated inside the
/// last 5 minutes, with the same kind and an equal
/// source_window — or `None`. Entries scan newest first, so
/// the most recent matching brief wins. A store list failure
/// returns `None` (fail open): the guard must never block a
/// fresh brief. Entries with no usable timestamp, a future
/// timestamp, or an unreadable record are skipped, never
/// fatal. A `None` record from the store is not a dict in
/// Python and is skipped the same way.
pub fn find_recent_brief(
    store: &dyn BriefStore,
    room: &str,
    kind: &str,
    source_window: &SourceWindow,
    now: Option<i64>,
) -> Option<StoredBriefRecord> {
    let current = match now {
        Some(t) => t,
        None => std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs() as i64)
            .unwrap_or(0),
    };
    let entries = match store.list_briefs(room) {
        Ok(entries) => entries,
        Err(_) => return None,
    };
    for entry in entries.iter().rev() {
        let ts = match entry.ts.or(entry.generated_at) {
            Some(ts) => ts,
            None => continue,
        };
        let ts_f = ts.as_f64();
        if ts_f > current as f64 {
            continue;
        }
        if current as f64 - ts_f > BRIEF_REGENERATION_WINDOW_SECONDS as f64 {
            continue;
        }
        let record = match store.get_brief(room, ts) {
            Ok(record) => record,
            Err(_) => continue,
        };
        let record = match record {
            Some(record) => record,
            None => continue,
        };
        if record.kind != kind {
            continue;
        }
        if !source_window_equal(&record.stored.source_window, &Some(source_window.clone())) {
            continue;
        }
        return Some(record);
    }
    None
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
    fn build_previous_session_splits_done_open_claimed() {
        // 1793620800 formats as 2026-11-02 07:00 ET (same vector
        // the next_morning_run tests use).
        let brief = StoredBriefInput {
            generated_at: Some(Some(1793620800)),
            ts: None,
            last_brief_at: None,
        };
        let jobs = vec![
            ShutdownJob { title: "Ship it".into(), status: "done".into() },
            ShutdownJob { title: "Thread A".into(), status: "open".into() },
            ShutdownJob { title: "Thread B".into(), status: "claimed".into() },
            ShutdownJob { title: "In flight".into(), status: "in_flight".into() },
            ShutdownJob { title: "".into(), status: "done".into() },
        ];
        let got = build_previous_session(Some(&brief), Some(&jobs)).unwrap();
        assert_eq!(got.last_brief_at, "2026-11-02 07:00 ET");
        assert_eq!(got.jobs_completed, vec!["Ship it"]);
        assert_eq!(got.open_threads, vec!["Thread A", "Thread B"]);
        // Absent generated_at falls through to ts; absent jobs
        // read as an empty list, never an error.
        let by_ts = StoredBriefInput {
            generated_at: None,
            ts: Some(1793620800),
            last_brief_at: None,
        };
        let got = build_previous_session(Some(&by_ts), None).unwrap();
        assert_eq!(got.last_brief_at, "2026-11-02 07:00 ET");
        assert!(got.jobs_completed.is_empty() && got.open_threads.is_empty());
        // Present-but-null generated_at falls back to last_brief_at,
        // never to ts: the Python `.get` default only applies when
        // the key is absent.
        let null_gen = StoredBriefInput {
            generated_at: Some(None),
            ts: Some(1793620800),
            last_brief_at: Some("2026-10-30 08:00 ET".into()),
        };
        let got = build_previous_session(Some(&null_gen), Some(&[])).unwrap();
        assert_eq!(got.last_brief_at, "2026-10-30 08:00 ET");
        // No usable time at all -> None, never a guessed time.
        assert_eq!(build_previous_session(None, Some(&jobs)), None);
        let no_time = StoredBriefInput {
            generated_at: None,
            ts: None,
            last_brief_at: Some(String::new()),
        };
        assert_eq!(build_previous_session(Some(&no_time), None), None);
    }

    #[test]
    fn brief_text_from_record_verbatim_and_sections() {
        // Verbatim text wins exactly as stored, even with sections present.
        let mut sections = HashMap::new();
        sections.insert("Decisions".to_string(), vec!["DONE: x".to_string()]);
        let stored = StoredBriefText {
            text: Some("Stored brief\nsecond line".into()),
            source_window: Some(SourceWindow::Text("yesterday".into())),
            sections,
        };
        assert_eq!(brief_text_from_record(Some(&stored)), "Stored brief\nsecond line");
        // Blank text falls through to the sections render.
        let mut sections = HashMap::new();
        sections.insert("Owners".to_string(), vec!["pax: ship it".to_string()]);
        let blank = StoredBriefText {
            text: Some("   \n".into()),
            source_window: Some(SourceWindow::Dict {
                max_messages: Some(500),
                max_hours: Some(WindowHours::Float(24.0)),
                messages_kept: Some(120),
                messages_dropped: Some(380),
            }),
            sections,
        };
        assert_eq!(
            brief_text_from_record(Some(&blank)),
            "Window: last 500 messages or last 24.0 hours, 120 kept, 380 dropped\n\
             \nDecisions\nNothing reported in this window\n\
             \nIn flight\nNothing reported in this window\n\
             \nOwners\n- pax: ship it\n\
             \nBlocked and why\nNothing reported in this window\n\
             \nWatch items\nNothing reported in this window\n"
        );
        // A missing dict key renders None; a fractional hour stays fractional.
        let partial = StoredBriefText {
            text: None,
            source_window: Some(SourceWindow::Dict {
                max_messages: None,
                max_hours: Some(WindowHours::Float(2.5)),
                messages_kept: None,
                messages_dropped: Some(0),
            }),
            sections: HashMap::new(),
        };
        let rendered = brief_text_from_record(Some(&partial));
        assert!(rendered.starts_with(
            "Window: last None messages or last 2.5 hours, None kept, 0 dropped\n"
        ));
        // No record at all: no window line, every section empty.
        assert_eq!(
            brief_text_from_record(None),
            "\nDecisions\nNothing reported in this window\n\
             \nIn flight\nNothing reported in this window\n\
             \nOwners\nNothing reported in this window\n\
             \nBlocked and why\nNothing reported in this window\n\
             \nWatch items\nNothing reported in this window\n"
        );
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

    #[test]
    fn memory_budget_lines_settled_spend_and_down() {
        let full = MemoryBudget {
            memory_down: false,
            settled_decisions: Some(vec![
                "freeze at 05:12".into(),
                "".into(),
                "green look carries over".into(),
            ]),
            budgets: Some(vec![
                MemoryBudgetEntry {
                    lane: "intel".into(),
                    cap: Some(100),
                    spent: Some(30),
                    remaining: None,
                    held: false,
                    age_label: None,
                },
                MemoryBudgetEntry {
                    lane: "relay".into(),
                    cap: Some(50),
                    spent: None,
                    remaining: Some(20),
                    held: true,
                    age_label: Some(" (as of 2026-10-30 08:00 ET)".into()),
                },
                MemoryBudgetEntry {
                    lane: "".into(),
                    cap: Some(10),
                    spent: Some(1),
                    remaining: None,
                    held: false,
                    age_label: None,
                },
                MemoryBudgetEntry {
                    lane: "ghost".into(),
                    cap: None,
                    spent: None,
                    remaining: None,
                    held: false,
                    age_label: None,
                },
            ]),
            age_label: " (snapshot time not reported)".into(),
        };
        assert_eq!(
            memory_budget_lines(Some(&full)),
            vec![
                "Settled decisions from memory: freeze at 05:12; green look carries over (snapshot time not reported)",
                "Spend: intel lane: 30 of 100 budget (70 remaining) (snapshot time not reported)",
                "Spend: relay lane: 20 remaining of 50 cap — new claims held (as of 2026-10-30 08:00 ET)",
            ]
        );
        // No record at all: no lines, so older briefs keep their shape.
        assert_eq!(memory_budget_lines(None), Vec::<String>::new());
        // Memory service down: no settled decision is shown, none invented.
        let down = MemoryBudget {
            memory_down: true,
            settled_decisions: Some(vec!["kept".into()]),
            budgets: None,
            age_label: " (snapshot time not reported)".into(),
        };
        assert_eq!(
            memory_budget_lines(Some(&down)),
            vec![
                "Settled decisions from memory: memory service down, so no settled decisions are shown (snapshot time not reported)",
                "Spend vs budget: not reported in this snapshot",
            ]
        );
        // Missing key reads not reported; empty list reads none reported.
        let missing = MemoryBudget {
            memory_down: false,
            settled_decisions: None,
            budgets: Some(vec![]),
            age_label: "".into(),
        };
        assert_eq!(
            memory_budget_lines(Some(&missing)),
            vec![
                "Settled decisions from memory: not reported in this snapshot",
                "Spend vs budget: not reported in this snapshot",
            ]
        );
        let empty = MemoryBudget {
            memory_down: false,
            settled_decisions: Some(vec![]),
            budgets: None,
            age_label: "".into(),
        };
        assert_eq!(
            memory_budget_lines(Some(&empty))[0],
            "Settled decisions from memory: none reported"
        );
    }

    #[test]
    fn memory_depth_lines_items_missing_dates_down_and_none() {
        let age = " (snapshot time not reported)";
        let full = MemoryDepth {
            memory_down: false,
            aged_decisions: Some(vec![
                AgedDecision { decision: "freeze at 05:12".into(), original_date: Some("2026-10-30".into()) },
                AgedDecision { decision: "".into(), original_date: Some("2026-10-01".into()) },
                AgedDecision { decision: "green look carries over".into(), original_date: None },
            ]),
            due_commitments: Some(vec![
                DueCommitment { commitment: "ship the demo script".into(), due: Some("2026-11-02".into()) },
                DueCommitment { commitment: "re-check the gate".into(), due: None },
            ]),
            fresh_context: Some(vec!["the bus moved rooms".into(), "".into()]),
            age_label: age.into(),
        };
        assert_eq!(
            memory_depth_lines(Some(&full)),
            vec![
                format!("Aged decision: freeze at 05:12 (from 2026-10-30){age}"),
                format!("Aged decision: green look carries over (original date not reported){age}"),
                format!("Due commitment: ship the demo script (due 2026-11-02){age}"),
                format!("Due commitment: re-check the gate (due date not reported){age}"),
                format!("Fresh-agent context: the bus moved rooms{age}"),
            ]
        );
        // Down service: one line, no items, no age label.
        let down = MemoryDepth {
            memory_down: true,
            aged_decisions: Some(vec![AgedDecision {
                decision: "must not show".into(),
                original_date: None,
            }]),
            due_commitments: None,
            fresh_context: None,
            age_label: age.into(),
        };
        assert_eq!(
            memory_depth_lines(Some(&down)),
            vec!["Long-term memory: memory service down, so no aged decisions, due commitments, or fresh-agent context are shown"]
        );
        // No usable entry at all: three none-reported lines.
        let empty = MemoryDepth {
            memory_down: false,
            aged_decisions: None,
            due_commitments: Some(vec![]),
            fresh_context: Some(vec!["".into()]),
            age_label: age.into(),
        };
        assert_eq!(
            memory_depth_lines(Some(&empty)),
            vec![
                format!("Aged decisions: none reported{age}"),
                format!("Due commitments: none reported{age}"),
                format!("Fresh-agent context: none reported{age}"),
            ]
        );
        // No record: no lines, so older briefs keep their shape.
        assert_eq!(memory_depth_lines(None), Vec::<String>::new());
    }

    #[test]
    fn daily_lines_results_queue_needs_empty_and_none() {
        let age = " (snapshot time not reported)";
        let full = Daily {
            overnight_results: Some(vec!["shipped the brief panel".into(), "".into()]),
            todays_queue: Some(vec![
                DailyQueueJob { id: "7".into(), title: "boot shot".into() },
                DailyQueueJob { id: "8".into(), title: "brief panel".into() },
                // No id, no title, or neither: skipped, never padded.
                DailyQueueJob { id: "".into(), title: "no id".into() },
                DailyQueueJob { id: "9".into(), title: "".into() },
            ]),
            needs_word: Some(vec![
                NeedsWordEntry {
                    question: "ship the demo cut?".into(),
                    job: Some("7".into()),
                },
                NeedsWordEntry { question: "go now".into(), job: None },
                // No question: skipped, never padded.
                NeedsWordEntry { question: "".into(), job: Some("7".into()) },
            ]),
            age_label: age.into(),
        };
        assert_eq!(
            daily_lines(Some(&full)),
            vec![
                format!("Overnight result: shipped the brief panel{age}"),
                format!("Today's queue: job 7 boot shot{age}"),
                format!("Today's queue: job 8 brief panel{age}"),
                format!("Needs your word: ship the demo cut? (job 7){age}"),
                format!("Needs your word: go now{age}"),
            ]
        );
        // A record with no usable entry at all still renders its
        // three none-reported lines.
        let empty = Daily {
            overnight_results: None,
            todays_queue: Some(vec![]),
            needs_word: Some(vec![NeedsWordEntry {
                question: String::new(),
                job: None,
            }]),
            age_label: age.into(),
        };
        assert_eq!(
            daily_lines(Some(&empty)),
            vec![
                format!("Overnight results: none reported{age}"),
                format!("Today's queue: none reported{age}"),
                format!("Needs your word: none reported{age}"),
            ]
        );
        // No record: no lines, so older briefs keep their shape.
        assert_eq!(daily_lines(None), Vec::<String>::new());
    }

    #[test]
    fn brief_time_formats() {
        // Python test vector, plus winter (EST) and both DST edges.
        assert_eq!(format_brief_time(1793101200), "2026-10-27 07:40 ET");
        assert_eq!(format_brief_time(1768478400), "2026-01-15 07:00 ET");
        assert_eq!(format_brief_time(1772953140), "2026-03-08 01:59 ET");
        assert_eq!(format_brief_time(1772953200), "2026-03-08 03:00 ET");
        assert_eq!(format_brief_time(1793512740), "2026-11-01 01:59 ET");
        assert_eq!(format_brief_time(1793512800), "2026-11-01 01:00 ET");
    }

    #[test]
    fn screenshot_refs_found_in_order_with_caption_and_time() {
        let img_a = "BLOB:0123456789abcdef:dashboard.png:2";
        let img_b = "BLOB:fedcba9876543210:brief-panel.jpg:1";
        let got = extract_screenshot_refs(Some(&[
            ScreenshotMessage::Dict {
                nick: "milo".into(),
                text: format!("look at this {img_a}"),
                ts: Some(1793101200),
            },
            ScreenshotMessage::Dict {
                nick: "rowan".into(),
                text: img_b.into(),
                ts: None,
            },
            ScreenshotMessage::Dict {
                nick: "pax".into(),
                text: "plain message, no image".into(),
                ts: None,
            },
        ]));
        assert_eq!(got.len(), 2);
        assert_eq!(got[0].nick, "milo");
        assert_eq!(got[0].file, "dashboard.png");
        assert_eq!(got[0].hash, "0123456789abcdef");
        assert_eq!(got[0].chunks, 2);
        assert_eq!(got[0].ts, Some(1793101200));
        assert_eq!(got[0].caption, "look at this");
        assert_eq!(got[1].nick, "rowan");
        assert_eq!(got[1].file, "brief-panel.jpg");
        assert_eq!(got[1].caption, "");
        assert_eq!(got[1].ts, None);
    }

    #[test]
    fn screenshot_refs_bus_string_has_no_time() {
        let got = extract_screenshot_refs(Some(&[ScreenshotMessage::Text(
            "milo: BLOB:0123456789abcdef:dashboard.png:2".into(),
        )]));
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].nick, "milo");
        assert_eq!(got[0].ts, None);
    }

    #[test]
    fn screenshot_refs_skip_non_image_and_bad_pointers() {
        let got = extract_screenshot_refs(Some(&[
            ScreenshotMessage::Dict {
                nick: "milo".into(),
                text: "file BLOB:0123456789abcdef:notes.txt:1".into(),
                ts: None,
            },
            ScreenshotMessage::Dict {
                nick: "milo".into(),
                text: "bad BLOB:abc:dashboard.png:1".into(),
                ts: None,
            },
            ScreenshotMessage::Dict {
                nick: "milo".into(),
                text: "upper BLOB:0011223344556677:crew-board.PNG:1".into(),
                ts: None,
            },
            ScreenshotMessage::Dict {
                nick: "milo".into(),
                text: "fake.png.txt BLOB:0123456789abcdef:fake.png.txt:1".into(),
                ts: None,
            },
        ]));
        assert_eq!(
            got.iter().map(|r| r.file.as_str()).collect::<Vec<_>>(),
            vec!["crew-board.PNG"]
        );
    }

    #[test]
    fn screenshot_refs_same_image_twice_yields_one_at_latest_post() {
        let img_a = "BLOB:0123456789abcdef:dashboard.png:2";
        let img_b = "BLOB:fedcba9876543210:brief-panel.jpg:1";
        let got = extract_screenshot_refs(Some(&[
            ScreenshotMessage::Dict {
                nick: "milo".into(),
                text: format!("old caption {img_a}"),
                ts: Some(1793101000),
            },
            ScreenshotMessage::Dict {
                nick: "rowan".into(),
                text: img_b.into(),
                ts: Some(1793101100),
            },
            ScreenshotMessage::Dict {
                nick: "milo".into(),
                text: format!("new caption {img_a}"),
                ts: Some(1793101200),
            },
        ]));
        assert_eq!(
            got.iter().map(|r| r.file.as_str()).collect::<Vec<_>>(),
            vec!["brief-panel.jpg", "dashboard.png"]
        );
        assert_eq!(got[1].caption, "new caption");
        assert_eq!(got[1].ts, Some(1793101200));
    }

    #[test]
    fn screenshot_refs_empty_is_empty_not_an_error() {
        assert_eq!(extract_screenshot_refs(None), Vec::new());
        assert_eq!(extract_screenshot_refs(Some(&[])), Vec::new());
    }

    #[test]
    fn screenshot_digest_lines_name_sender_file_and_time() {
        let refs = vec![
            ScreenshotRef {
                nick: "milo".into(),
                file: "dashboard.png".into(),
                hash: "0123456789abcdef".into(),
                chunks: 2,
                ts: Some(1793101200),
                caption: "look at this".into(),
            },
            ScreenshotRef {
                nick: "rowan".into(),
                file: "brief-panel.jpg".into(),
                hash: "fedcba9876543210".into(),
                chunks: 1,
                ts: None,
                caption: "".into(),
            },
        ];
        assert_eq!(
            screenshot_digest_lines(Some(&refs)),
            vec![
                "milo shared dashboard.png at 2026-10-27 07:40 ET: look at this",
                "rowan shared brief-panel.jpg at time not reported",
            ]
        );
        assert_eq!(screenshot_digest_lines(Some(&[])), Vec::<String>::new());
        assert_eq!(screenshot_digest_lines(None), Vec::<String>::new());
    }

    #[test]
    fn new_nick_yields_one_offer_record() {
        use super::super::window::RawMessage;
        let messages = vec![
            RawMessage::Dict {
                nick: "pax".into(),
                text: "DECISION: ship the panel".into(),
            },
            RawMessage::Text("milo: working on the watchdog".into()),
        ];
        let presence = Presence::List(vec![
            PresenceEntry::Nick("pax".into()),
            PresenceEntry::Nick("milo".into()),
            PresenceEntry::Nick("rowan".into()),
        ]);
        assert_eq!(
            detect_new_nicks(Some(&messages), Some(&presence)),
            vec!["rowan".to_string()]
        );
        assert_eq!(
            offer_onjoin_brief(
                Some(&messages),
                Some(&presence),
                "build",
                Some(1793000000)
            ),
            vec![OnjoinOffer {
                room: "build".into(),
                nick: "rowan".into(),
                kind: "onjoin".into(),
                status: "offered".into(),
                offered_at: 1793000000,
                brief_generated: false,
                brief_id: None,
            }]
        );
    }

    #[test]
    fn new_nicks_bus_string_dict_and_empty_presence() {
        use super::super::window::RawMessage;
        // A bus-string message counts as prior presence.
        let messages = vec![RawMessage::Text("rowan: just joined the room".into())];
        let presence = Presence::List(vec![
            PresenceEntry::Nick("rowan".into()),
            PresenceEntry::Nick("buffy".into()),
        ]);
        assert_eq!(
            detect_new_nicks(Some(&messages), Some(&presence)),
            vec!["buffy".to_string()]
        );
        // No messages: a present nick is new (a job claim or caps
        // entry is not an input here, so it cannot count).
        assert_eq!(
            detect_new_nicks(
                Some(&[]),
                Some(&Presence::List(vec![PresenceEntry::Nick(
                    "rowan".into()
                )]))
            ),
            vec!["rowan".to_string()]
        );
        // Dict presence: keys are the presence list.
        let messages = vec![RawMessage::Dict {
            nick: "rowan".into(),
            text: "hello".into(),
        }];
        assert_eq!(
            detect_new_nicks(
                Some(&messages),
                Some(&Presence::DictKeys(vec![
                    "rowan".into(),
                    "sam".into()
                ]))
            ),
            vec!["sam".to_string()]
        );
        // No presence, no messages, dupes, empties, non-strings:
        // none of these yield a nick.
        assert_eq!(detect_new_nicks(None, None), Vec::<String>::new());
        assert_eq!(
            detect_new_nicks(Some(&[]), None),
            Vec::<String>::new()
        );
        let messages = vec![RawMessage::Dict {
            nick: "pax".into(),
            text: "hi".into(),
        }];
        let presence = Presence::List(vec![
            PresenceEntry::Nick("pax".into()),
            PresenceEntry::Nick("pax".into()),
            PresenceEntry::Nick("".into()),
            PresenceEntry::Other,
        ]);
        assert_eq!(
            detect_new_nicks(Some(&messages), Some(&presence)),
            Vec::<String>::new()
        );
        assert_eq!(
            offer_onjoin_brief(Some(&messages), Some(&presence), "build", None),
            Vec::new()
        );
        // An empty room reads as "main", mirroring `room or "main"`.
        let presence = Presence::List(vec![PresenceEntry::Nick("sam".into())]);
        let offers =
            offer_onjoin_brief(Some(&[]), Some(&presence), "", Some(100));
        assert_eq!(offers.len(), 1);
        assert_eq!(offers[0].room, "main");
        assert_eq!(offers[0].nick, "sam");
        assert_eq!(offers[0].brief_generated, false);
        assert_eq!(offers[0].brief_id, None);
    }

    #[test]
    fn next_morning_run_strictly_after_and_dst() {
        // Vectors computed from Python's zoneinfo implementation
        // of next_morning_run (America/New_York).
        // 2026-11-02 07:00 EST -> same day 08:00 EST.
        assert_eq!(next_morning_run(Some(1793620800), 8), 1793624400);
        // Exactly 08:00 rolls to tomorrow: strictly after.
        assert_eq!(next_morning_run(Some(1793624400), 8), 1793710800);
        // After 08:00 -> tomorrow 08:00.
        assert_eq!(next_morning_run(Some(1793629800), 8), 1793710800);
        // Summer EDT, before 08:00 -> same day 08:00 EDT.
        assert_eq!(next_morning_run(Some(1784116740), 8), 1784116800);
        // DST start day (spring forward) 07:00 EDT -> 08:00 EDT.
        assert_eq!(next_morning_run(Some(1772967600), 8), 1772971200);
        // Day before DST start, after 08:00 -> DST day 08:00 EDT.
        assert_eq!(next_morning_run(Some(1772892000), 8), 1772971200);
        // DST end day (fall back) 07:00 EST -> 08:00 EST.
        assert_eq!(next_morning_run(Some(1793534400), 8), 1793538000);
        // Day before DST end, after 08:00 -> DST-end day 08:00 EST.
        assert_eq!(next_morning_run(Some(1793451600), 8), 1793538000);
        // Custom hour: 07:00 -> same day 09:00 EST.
        assert_eq!(next_morning_run(Some(1793620800), 9), 1793628000);
        // Year boundary: 2026-12-31 23:00 EST -> 2027-01-01 08:00 EST.
        assert_eq!(next_morning_run(Some(1798776000), 8), 1798808400);
    }

    struct FakeBriefStore {
        list: Result<Vec<BriefIndexEntry>, String>,
        records: Vec<(BriefTs, StoredBriefRecord)>,
        fail_get: Vec<BriefTs>,
    }

    impl BriefStore for FakeBriefStore {
        fn list_briefs(&self, _room: &str) -> Result<Vec<BriefIndexEntry>, String> {
            self.list.clone()
        }

        fn get_brief(&self, _room: &str, ts: BriefTs) -> Result<Option<StoredBriefRecord>, String> {
            if self.fail_get.iter().any(|f| f.as_f64() == ts.as_f64()) {
                return Err("store down".to_string());
            }
            Ok(self
                .records
                .iter()
                .find(|(t, _)| t.as_f64() == ts.as_f64())
                .map(|(_, r)| r.clone()))
        }
    }

    fn dict_window() -> SourceWindow {
        SourceWindow::Dict {
            max_messages: Some(500),
            max_hours: Some(WindowHours::Int(24)),
            messages_kept: Some(1),
            messages_dropped: Some(0),
        }
    }

    fn guard_record(kind: &str, window: SourceWindow) -> StoredBriefRecord {
        StoredBriefRecord {
            kind: kind.to_string(),
            stored: StoredBriefText {
                text: Some("guard brief".to_string()),
                source_window: Some(window),
                sections: HashMap::new(),
            },
        }
    }

    fn entry(ts: i64) -> BriefIndexEntry {
        BriefIndexEntry { ts: Some(BriefTs::Int(ts)), generated_at: None }
    }

    #[test]
    fn find_recent_brief_newest_match_wins() {
        // Oldest first, as list_briefs returns them; the newest
        // kind+window match wins, and a newer wrong-kind entry
        // is skipped, not returned.
        let store = FakeBriefStore {
            list: Ok(vec![entry(1793000000), entry(1793000100), entry(1793000150)]),
            records: vec![
                (BriefTs::Int(1793000000), guard_record("ondemand", dict_window())),
                (BriefTs::Int(1793000100), guard_record("ondemand", dict_window())),
                (BriefTs::Int(1793000150), guard_record("morning", dict_window())),
            ],
            fail_get: vec![],
        };
        let found =
            find_recent_brief(&store, "build", "ondemand", &dict_window(), Some(1793000200));
        assert!(found.is_some());
        assert_eq!(found.unwrap().stored.text.as_deref(), Some("guard brief"));
        // The match is the 1793000100 record: prove it by giving
        // that record distinct text through a second store.
        let store = FakeBriefStore {
            list: Ok(vec![entry(1793000000), entry(1793000100)]),
            records: vec![
                (
                    BriefTs::Int(1793000000),
                    StoredBriefRecord {
                        kind: "ondemand".to_string(),
                        stored: StoredBriefText {
                            text: Some("older".to_string()),
                            source_window: Some(dict_window()),
                            sections: HashMap::new(),
                        },
                    },
                ),
                (
                    BriefTs::Int(1793000100),
                    StoredBriefRecord {
                        kind: "ondemand".to_string(),
                        stored: StoredBriefText {
                            text: Some("newer".to_string()),
                            source_window: Some(dict_window()),
                            sections: HashMap::new(),
                        },
                    },
                ),
            ],
            fail_get: vec![],
        };
        assert_eq!(
            find_recent_brief(&store, "build", "ondemand", &dict_window(), Some(1793000200))
                .unwrap()
                .stored
                .text
                .as_deref(),
            Some("newer")
        );
    }

    #[test]
    fn find_recent_brief_stale_future_and_boundary() {
        // Stale (> 300s) and future entries are skipped; exactly
        // 300s old is inside the window (Python: `> 300` skips).
        let now = 1793001000;
        let store = FakeBriefStore {
            list: Ok(vec![entry(now - 301), entry(now + 10), entry(now - 300)]),
            records: vec![
                (BriefTs::Int(now - 301), guard_record("ondemand", dict_window())),
                (BriefTs::Int(now + 10), guard_record("ondemand", dict_window())),
                (BriefTs::Int(now - 300), guard_record("ondemand", dict_window())),
            ],
            fail_get: vec![],
        };
        assert!(find_recent_brief(&store, "build", "ondemand", &dict_window(), Some(now))
            .is_some());
        // With only stale and future entries, there is no hit.
        let store = FakeBriefStore {
            list: Ok(vec![entry(now - 301), entry(now + 10)]),
            records: vec![
                (BriefTs::Int(now - 301), guard_record("ondemand", dict_window())),
                (BriefTs::Int(now + 10), guard_record("ondemand", dict_window())),
            ],
            fail_get: vec![],
        };
        assert_eq!(
            find_recent_brief(&store, "build", "ondemand", &dict_window(), Some(now)),
            None
        );
    }

    #[test]
    fn find_recent_brief_window_equality() {
        // A text window never matches a dict window, and a
        // record with no window never matches a dict window.
        let store = FakeBriefStore {
            list: Ok(vec![entry(1793000000)]),
            records: vec![(
                BriefTs::Int(1793000000),
                guard_record("ondemand", SourceWindow::Text("yesterday".to_string())),
            )],
            fail_get: vec![],
        };
        assert_eq!(
            find_recent_brief(&store, "build", "ondemand", &dict_window(), Some(1793000100)),
            None
        );
        // Int hours equal float hours, mirroring Python's
        // `24 == 24.0` dict comparison.
        let float_window = SourceWindow::Dict {
            max_messages: Some(500),
            max_hours: Some(WindowHours::Float(24.0)),
            messages_kept: Some(1),
            messages_dropped: Some(0),
        };
        let store = FakeBriefStore {
            list: Ok(vec![entry(1793000000)]),
            records: vec![(BriefTs::Int(1793000000), guard_record("ondemand", float_window))],
            fail_get: vec![],
        };
        assert!(find_recent_brief(&store, "build", "ondemand", &dict_window(), Some(1793000100))
            .is_some());
    }

    #[test]
    fn find_recent_brief_fail_open_and_skip_unreadable() {
        // A list failure fails open: no guard hit, fresh brief.
        let store = FakeBriefStore {
            list: Err("store down".to_string()),
            records: vec![],
            fail_get: vec![],
        };
        assert_eq!(
            find_recent_brief(&store, "build", "ondemand", &dict_window(), Some(1793000100)),
            None
        );
        // A get failure on the newest entry skips it and the
        // older matching entry still hits.
        let store = FakeBriefStore {
            list: Ok(vec![entry(1793000000), entry(1793000100)]),
            records: vec![
                (BriefTs::Int(1793000000), guard_record("ondemand", dict_window())),
                (BriefTs::Int(1793000100), guard_record("ondemand", dict_window())),
            ],
            fail_get: vec![BriefTs::Int(1793000100)],
        };
        assert!(find_recent_brief(&store, "build", "ondemand", &dict_window(), Some(1793000200))
            .is_some());
    }

    #[test]
    fn find_recent_brief_ts_falls_back_to_generated_at() {
        // No `ts` key: `generated_at` is the timestamp.
        let store = FakeBriefStore {
            list: Ok(vec![BriefIndexEntry {
                ts: None,
                generated_at: Some(BriefTs::Int(1793000000)),
            }]),
            records: vec![(BriefTs::Int(1793000000), guard_record("ondemand", dict_window()))],
            fail_get: vec![],
        };
        assert!(find_recent_brief(&store, "build", "ondemand", &dict_window(), Some(1793000100))
            .is_some());
        // Neither key: the entry is skipped, not fatal.
        let store = FakeBriefStore {
            list: Ok(vec![BriefIndexEntry { ts: None, generated_at: None }]),
            records: vec![],
            fail_get: vec![],
        };
        assert_eq!(
            find_recent_brief(&store, "build", "ondemand", &dict_window(), Some(1793000100)),
            None
        );
    }

    #[test]
    fn environment_age_label_known_and_unknown() {
        // 2026-10-30 08:00 ET (daylight time) and 2026-01-15 08:00
        // ET (standard time): the label carries the formatted time.
        assert_eq!(
            environment_age_label(Some(1793361600)),
            " (as of 2026-10-30 08:00 ET)"
        );
        assert_eq!(
            environment_age_label(Some(1768482000)),
            " (as of 2026-01-15 08:00 ET)"
        );
        // Unknown age is never presented as current.
        assert_eq!(
            environment_age_label(None),
            " (snapshot time not reported)"
        );
    }

    // Real temp git checkouts, not a stubbed git, mirroring the
    // Python repo-record tests. Each test uses its own directory
    // (process id + test name) so parallel test runs cannot share
    // a checkout, and removes it afterwards.
    fn repo_test_dir(name: &str) -> std::path::PathBuf {
        std::env::temp_dir().join(format!(
            "intel-b10-repo-{}-{name}",
            std::process::id()
        ))
    }

    fn repo_git(path: &std::path::Path, args: &[&str]) {
        let status = std::process::Command::new("git")
            .arg("-C")
            .arg(path)
            .args(args)
            .status()
            .expect("git must run for the repo-record tests");
        assert!(status.success(), "git {args:?} failed in {path:?}");
    }

    fn repo_checkout(name: &str) -> std::path::PathBuf {
        let path = repo_test_dir(name);
        let _ = std::fs::remove_dir_all(&path);
        std::fs::create_dir_all(&path).expect("temp checkout dir");
        repo_git(&path, &["init", "-b", "testbranch"]);
        repo_git(&path, &["config", "user.email", "test@example.local"]);
        repo_git(&path, &["config", "user.name", "Test"]);
        std::fs::write(path.join("note.txt"), "hello\n").expect("note.txt");
        repo_git(&path, &["add", "note.txt"]);
        repo_git(&path, &["commit", "-m", "first"]);
        path
    }

    #[test]
    fn environment_repo_record_clean_checkout() {
        let path = repo_checkout("clean");
        let record = environment_repo_record(
            path.to_str(),
            Some(1793093400),
        )
        .expect("clean checkout yields a record");
        assert_eq!(record.branch, "testbranch");
        assert!(!record.commit.is_empty());
        assert_eq!(record.dirty, 0);
        assert_eq!(record.as_of, 1793093400);
        let _ = std::fs::remove_dir_all(&path);
    }

    #[test]
    fn environment_repo_record_modified_and_untracked_count_dirty() {
        let path = repo_checkout("dirty");
        std::fs::write(path.join("note.txt"), "hello\nmore\n")
            .expect("modify note.txt");
        std::fs::write(path.join("new.txt"), "untracked\n")
            .expect("new.txt");
        let record = environment_repo_record(
            path.to_str(),
            Some(1793093400),
        )
        .expect("dirty checkout yields a record");
        assert_eq!(record.dirty, 2);
        let _ = std::fs::remove_dir_all(&path);
    }

    #[test]
    fn environment_repo_record_non_checkout_returns_none() {
        let path = repo_test_dir("non-checkout");
        let _ = std::fs::remove_dir_all(&path);
        std::fs::create_dir_all(&path).expect("temp non-checkout dir");
        assert_eq!(
            environment_repo_record(path.to_str(), Some(1793093400)),
            None
        );
        let _ = std::fs::remove_dir_all(&path);
    }

    #[test]
    fn environment_repo_record_renders_repo_line_only() {
        let path = repo_checkout("render");
        let record = environment_repo_record(
            path.to_str(),
            Some(1793093400),
        )
        .expect("checkout yields a record");
        let env = Environment {
            repo: Some(EnvironmentRepo {
                branch: record.branch.clone(),
                commit: record.commit.clone(),
                dirty: Some(record.dirty),
                age_label: environment_age_label(Some(record.as_of)),
            }),
            bus: None,
            jobs: None,
            working_age_label: String::new(),
            budget: None,
        };
        let lines = environment_lines(Some(&env));
        assert!(lines[0].contains(&format!(
            "Repo: testbranch at {}",
            record.commit
        )));
        assert!(lines[0].contains("clean"));
        assert!(lines[1].contains("not reported"));
        assert!(lines[2].contains("not reported"));
        assert!(lines[3].contains("not reported"));
        let _ = std::fs::remove_dir_all(&path);
    }

    fn bus_messages() -> Vec<RawMessage> {
        use super::super::window::RawMessage;
        vec![
            RawMessage::Dict {
                nick: "rowan".into(),
                text: "hello".into(),
            },
            RawMessage::Text("milo: working on it".into()),
            RawMessage::Dict {
                nick: "pax".into(),
                text: "noted".into(),
            },
            RawMessage::Other,
            RawMessage::Other,
        ]
    }

    #[test]
    fn environment_bus_record_count_and_rooms_in_caller_order() {
        let record = environment_bus_record(
            Some(&bus_messages()),
            Some(&BusRooms::List(vec![
                BusRoom::Name("main".into()),
                BusRoom::Name("build".into()),
                BusRoom::Name("main".into()),
            ])),
            Some(1793093400),
        )
        .expect("a messages list yields a bus record");
        assert_eq!(record.messages, 3);
        assert_eq!(record.rooms, vec!["main".to_string(), "build".to_string()]);
        assert_eq!(record.as_of, 1793093400);
    }

    #[test]
    fn environment_bus_record_single_string_and_bad_rooms_dropped() {
        let messages = bus_messages();
        let single = environment_bus_record(
            Some(&messages),
            Some(&BusRooms::Single("main".into())),
            Some(1793093400),
        )
        .expect("a single room string yields a record");
        assert_eq!(single.rooms, vec!["main".to_string()]);
        let mixed = environment_bus_record(
            Some(&messages),
            Some(&BusRooms::List(vec![
                BusRoom::Name("main".into()),
                BusRoom::Name(String::new()),
                BusRoom::Other,
            ])),
            Some(1793093400),
        )
        .expect("a mixed room list yields a record");
        assert_eq!(mixed.rooms, vec!["main".to_string()]);
        let unstated = environment_bus_record(
            Some(&messages),
            None,
            Some(1793093400),
        )
        .expect("no rooms still yields a record");
        assert!(unstated.rooms.is_empty());
        assert_eq!(unstated.messages, 3);
    }

    #[test]
    fn environment_bus_record_non_list_returns_none() {
        assert_eq!(environment_bus_record(None, None, Some(1793093400)), None);
        let lines = environment_lines(None);
        assert!(lines[1].contains("not reported"));
    }

    #[test]
    fn environment_bus_record_empty_list_is_zero_not_not_reported() {
        let record = environment_bus_record(
            Some(&[]),
            Some(&BusRooms::Single("main".into())),
            Some(1793093400),
        )
        .expect("an empty list yields a record");
        assert_eq!(record.messages, 0);
        let env = Environment {
            repo: None,
            bus: Some(EnvironmentBus {
                rooms: record.rooms.clone(),
                messages: Some(record.messages),
                age_label: environment_age_label(Some(record.as_of)),
            }),
            jobs: None,
            working_age_label: String::new(),
            budget: None,
        };
        let lines = environment_lines(Some(&env));
        assert!(lines[1].contains("0 messages"));
        assert!(!lines[1].contains("not reported"));
    }

    #[test]
    fn environment_bus_record_renders_bus_line_and_others_not_reported() {
        let record = environment_bus_record(
            Some(&bus_messages()),
            Some(&BusRooms::Single("main".into())),
            Some(1793093400),
        )
        .expect("a messages list yields a record");
        let env = Environment {
            repo: None,
            bus: Some(EnvironmentBus {
                rooms: record.rooms.clone(),
                messages: Some(record.messages),
                age_label: environment_age_label(Some(record.as_of)),
            }),
            jobs: None,
            working_age_label: String::new(),
            budget: None,
        };
        let lines = environment_lines(Some(&env));
        assert!(lines[1].contains("Bus: 3 messages in room main"));
        assert!(lines[0].contains("not reported"));
        assert!(lines[2].contains("not reported"));
        assert!(lines[3].contains("not reported"));
    }
}
