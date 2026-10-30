//! Port of the `os/intel/brief.py` section derivation used by
//! `generate_brief` (BRF-004/005/006/022) — the five sections a
//! brief record carries, in render order. Pure snapshot rules, no
//! Spark call: the same derivation feeds the template brief and
//! the dashboard consistency check (INT-025), whose panel half
//! stays exclusion-blocked (it drives the fold-excluded viewer).
//!
//! Snapshot inputs are the normalized dict forms the Python
//! extractors read (`messages` with nick/text, `jobs` with
//! id/title/status/claim/note, `alerts` with id/summary or
//! explanation). String-form bus messages are split into nick/text
//! by the caller, mirroring `_message_parts`.

/// One snapshot message (nick + text), as `extract_decisions` reads it.
#[derive(Debug, Clone, PartialEq)]
pub struct SnapMessage {
    pub nick: String,
    pub text: String,
}

/// One snapshot job, as `extract_owners` / `extract_blocked` read it.
/// `last_progress_at` / `claimed_at` are Unix timestamps when the
/// record carries them; the fixtures carry neither, so both are None.
#[derive(Debug, Clone, PartialEq)]
pub struct SnapJob {
    pub id: String,
    pub title: String,
    pub status: String,
    pub claim: String,
    pub note: String,
    pub last_progress_at: Option<i64>,
    pub claimed_at: Option<i64>,
}

/// One snapshot alert, as `extract_watch_items` reads it.
#[derive(Debug, Clone, PartialEq)]
pub struct SnapAlert {
    pub id: String,
    pub summary: String,
    pub explanation: String,
}

/// A snapshot: messages, jobs, and alerts in dump order.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct Snapshot {
    pub messages: Vec<SnapMessage>,
    pub jobs: Vec<SnapJob>,
    pub alerts: Vec<SnapAlert>,
}

/// One marker decision: kind is `done`, `blocked`, or `decision`
/// (lowercased); text is the marker remainder verbatim; index is
/// the message position in the snapshot.
#[derive(Debug, Clone, PartialEq)]
pub struct Decision {
    pub kind: String,
    pub text: String,
    pub nick: String,
    pub index: usize,
}

/// One owner: a claim nick with its claimed jobs, in first-claim order.
#[derive(Debug, Clone, PartialEq)]
pub struct Owner {
    pub nick: String,
    pub jobs: Vec<OwnerJob>,
}

/// One owned job: id, title, and age (last progress, else claim, else none).
#[derive(Debug, Clone, PartialEq)]
pub struct OwnerJob {
    pub id: String,
    pub title: String,
    pub last_progress_age: Option<i64>,
}

/// One blocked job: id, title, and reason verbatim (the note, never trimmed).
#[derive(Debug, Clone, PartialEq)]
pub struct BlockedJob {
    pub id: String,
    pub title: String,
    pub reason: String,
}

/// One watch item: an alert id with its one-line summary, verbatim.
#[derive(Debug, Clone, PartialEq)]
pub struct WatchItem {
    pub id: String,
    pub summary: String,
}

/// The five brief sections, in render order.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct Sections {
    pub decisions: Vec<String>,
    pub in_flight: Vec<String>,
    pub owners: Vec<String>,
    pub blocked: Vec<String>,
    pub watch_items: Vec<String>,
}

/// BRF-004: decisions from message markers, in snapshot order.
/// A marker is `DONE:` / `BLOCKED:` / `DECISION:` (any case) at the
/// start of the text (leading whitespace allowed), with a non-empty
/// remainder. Messages with no marker are skipped, never reinterpreted.
pub fn extract_decisions(snapshot: &Snapshot) -> Vec<Decision> {
    let mut out = Vec::new();
    for (index, message) in snapshot.messages.iter().enumerate() {
        let Some((kind, text)) = parse_marker(&message.text) else {
            continue;
        };
        out.push(Decision {
            kind,
            text,
            nick: message.nick.clone(),
            index,
        });
    }
    out
}

/// Marker parse mirroring `_DECISION_RE` (`^\s*(DONE|BLOCKED|DECISION)
/// \s*:\s*(.+?)\s*$`, case-insensitive). No regex crate is used: the
/// head before the first colon must be exactly a marker word, and
/// the remainder after trimming must be non-empty.
fn parse_marker(text: &str) -> Option<(String, String)> {
    let t = text.trim_start();
    let (head, rest) = t.split_once(':')?;
    let kind = head.trim().to_ascii_lowercase();
    if kind != "done" && kind != "blocked" && kind != "decision" {
        return None;
    }
    let remainder = rest.trim();
    if remainder.is_empty() {
        return None;
    }
    Some((kind, remainder.to_string()))
}

/// BRF-006: claimed jobs mapped claim nick -> titles, in first-claim
/// order. Only jobs with status exactly `claimed` count as owned; a
/// done job never appears under an owner even if a stale claim
/// lingers. Age is `last_progress_at`, else `claimed_at`, else none.
pub fn extract_owners(snapshot: &Snapshot) -> Vec<Owner> {
    let mut owners: Vec<Owner> = Vec::new();
    for job in &snapshot.jobs {
        if job.claim.is_empty() || job.status != "claimed" {
            continue;
        }
        let age = job.last_progress_at.or(job.claimed_at);
        match owners.iter_mut().find(|o| o.nick == job.claim) {
            Some(owner) => owner.jobs.push(OwnerJob {
                id: job.id.clone(),
                title: job.title.clone(),
                last_progress_age: age,
            }),
            None => owners.push(Owner {
                nick: job.claim.clone(),
                jobs: vec![OwnerJob {
                    id: job.id.clone(),
                    title: job.title.clone(),
                    last_progress_age: age,
                }],
            }),
        }
    }
    owners
}

/// BRF-005: every blocked job, with its reason verbatim — the note
/// character-for-character, never paraphrased or trimmed. A blocked
/// job with no note gets reason `""`. Only status exactly `blocked`.
pub fn extract_blocked(snapshot: &Snapshot) -> Vec<BlockedJob> {
    snapshot
        .jobs
        .iter()
        .filter(|j| j.status == "blocked")
        .map(|j| BlockedJob {
            id: j.id.clone(),
            title: j.title.clone(),
            reason: j.note.clone(),
        })
        .collect()
}

/// BRF-022: open watchdog alerts, by reference, in snapshot order.
/// Alerts with no id are skipped — a brief never invents an alert
/// id. An alert with no usable summary falls back to the first line
/// of its explanation (INT-004: stored WDG-010 records carry
/// explanation, not summary); an alert with neither renders empty.
pub fn extract_watch_items(snapshot: &Snapshot) -> Vec<WatchItem> {
    let mut out = Vec::new();
    for alert in &snapshot.alerts {
        if alert.id.is_empty() {
            continue;
        }
        let mut summary = alert.summary.clone();
        if summary.trim().is_empty() {
            summary = alert
                .explanation
                .lines()
                .next()
                .map(|l| l.trim().to_string())
                .unwrap_or_default();
        }
        out.push(WatchItem {
            id: alert.id.clone(),
            summary,
        });
    }
    out
}

/// The `generate_brief` section assembly: the five sections from the
/// extractors, rendered exactly as the record carries them.
/// Decisions read `{kind}: {text}`; in-flight jobs `{id} {title}`
/// for open/claimed jobs; owners `{nick}: {titles joined ", "}`;
/// blocked `{id} {title}: {reason}`; watch items `{id}: {summary}`.
/// An empty section renders `No items.` in the panel, never an
/// invented item — the panel half of that rule stays
/// exclusion-blocked with the viewer.
pub fn derive_sections(snapshot: &Snapshot) -> Sections {
    Sections {
        decisions: extract_decisions(snapshot)
            .iter()
            .map(|d| format!("{}: {}", d.kind, d.text))
            .collect(),
        in_flight: snapshot
            .jobs
            .iter()
            .filter(|j| j.status == "open" || j.status == "claimed")
            .map(|j| format!("{} {}", j.id, j.title))
            .collect(),
        owners: extract_owners(snapshot)
            .iter()
            .map(|o| {
                let titles: Vec<&str> =
                    o.jobs.iter().map(|j| j.title.as_str()).collect();
                format!("{}: {}", o.nick, titles.join(", "))
            })
            .collect(),
        blocked: extract_blocked(snapshot)
            .iter()
            .map(|j| format!("{} {}: {}", j.id, j.title, j.reason))
            .collect(),
        watch_items: extract_watch_items(snapshot)
            .iter()
            .map(|w| format!("{}: {}", w.id, w.summary))
            .collect(),
    }
}
