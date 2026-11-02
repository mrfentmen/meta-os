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

use super::window::{SourceWindow, WindowHours};

/// One snapshot message (nick + text), as `extract_decisions` reads it.
/// `ts` is the message's Unix timestamp when it carries a numeric
/// one; `None` is an untimed message, which the window cap can never
/// age out (Python keeps messages without a numeric `ts` the same way).
/// A non-integer `ts` has no form in this crate's i64-second
/// convention yet and arrives as `None` — kept, never dropped.
#[derive(Debug, Clone, PartialEq)]
pub struct SnapMessage {
    pub nick: String,
    pub text: String,
    pub ts: Option<i64>,
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
/// `source_window` is the cap record a previous cap wrote (BRF-023);
/// `None` is a fresh, never-capped snapshot. The cap reads it only
/// for its prior `messages_dropped` count, so re-capping never
/// resets the drop count.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct Snapshot {
    pub messages: Vec<SnapMessage>,
    pub jobs: Vec<SnapJob>,
    pub alerts: Vec<SnapAlert>,
    pub source_window: Option<SourceWindow>,
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

/// BRF-023: cap a snapshot's source window, as `generate_brief`
/// (and `compose_brief` inside it) applies it.
///
/// Default cap in Python: last 500 messages or last 24 hours,
/// whichever is smaller; callers pass both explicitly, and `None`
/// on either side means no cap on that side. Messages stay in
/// snapshot order; when a cap cuts, the oldest messages go first.
/// A timed message at or after `now - max_hours * 3600` is kept;
/// an untimed message (`ts: None`) is never aged out, only counted
/// down by the message cap. Jobs and alerts pass through unchanged
/// — the cap is a message window cap, not a job cap. The returned
/// snapshot carries the new `source_window` dict naming the cap
/// values actually applied (`max_messages`, `max_hours`,
/// `messages_kept`, `messages_dropped`).
///
/// BRF-024: capping an already-capped snapshot must not reset the
/// drop count — a prior dict window's `messages_dropped` is added
/// to this cap's drops, so a second cap inside `compose_brief`
/// cannot report 0 dropped while the record reports the true count.
/// A text-form prior window carries no drop count and adds nothing.
///
/// Ported oddity: Python slices `messages[-max_messages:]`, and
/// `-0` is `0`, so a zero message cap counts every message as
/// dropped yet keeps them all. That is preserved here, not fixed:
/// a zero cap reports `messages_dropped` = all and keeps the list.
pub fn cap_snapshot_window(
    snapshot: &Snapshot,
    max_messages: Option<i64>,
    max_hours: Option<f64>,
    now: Option<i64>,
) -> Snapshot {
    let current = match now {
        Some(t) => t,
        None => std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs() as i64)
            .unwrap_or(0),
    };
    let mut messages = snapshot.messages.clone();
    let mut dropped: i64 = 0;
    if let Some(hours) = max_hours {
        let cutoff = current as f64 - hours * 3600.0;
        let kept: Vec<SnapMessage> = messages
            .into_iter()
            .filter(|m| match m.ts {
                None => true,
                Some(ts) => (ts as f64) >= cutoff,
            })
            .collect();
        dropped += (snapshot.messages.len() as i64) - (kept.len() as i64);
        messages = kept;
    }
    if let Some(m) = max_messages {
        let len = messages.len() as i64;
        if len > m {
            dropped += len - m;
            messages = if m >= 0 {
                if m == 0 {
                    messages
                } else {
                    messages.split_off((len - m) as usize)
                }
            } else {
                let skip = m.saturating_neg().min(len) as usize;
                messages.split_off(skip)
            };
        }
    }
    if let Some(SourceWindow::Dict {
        messages_dropped: Some(prior),
        ..
    }) = &snapshot.source_window
    {
        dropped += *prior;
    }
    let window_hours = max_hours.map(|h| {
        if h.is_finite() && h.fract() == 0.0 {
            WindowHours::Int(h as i64)
        } else {
            WindowHours::Float(h)
        }
    });
    let messages_kept = messages.len() as i64;
    Snapshot {
        messages,
        jobs: snapshot.jobs.clone(),
        alerts: snapshot.alerts.clone(),
        source_window: Some(SourceWindow::Dict {
            max_messages,
            max_hours: window_hours,
            messages_kept: Some(messages_kept),
            messages_dropped: Some(dropped),
        }),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn msg(nick: &str, text: &str, ts: Option<i64>) -> SnapMessage {
        SnapMessage {
            nick: nick.into(),
            text: text.into(),
            ts,
        }
    }

    fn snap(messages: Vec<SnapMessage>) -> Snapshot {
        Snapshot {
            messages,
            jobs: vec![],
            alerts: vec![],
            source_window: None,
        }
    }

    fn window_of(s: &Snapshot) -> (Option<i64>, Option<WindowHours>, Option<i64>, Option<i64>) {
        match &s.source_window {
            Some(SourceWindow::Dict {
                max_messages,
                max_hours,
                messages_kept,
                messages_dropped,
            }) => (
                *max_messages,
                max_hours.clone(),
                *messages_kept,
                *messages_dropped,
            ),
            _ => (None, None, None, None),
        }
    }

    #[test]
    fn cap_time_drops_old_keeps_untimed_in_order() {
        let s = snap(vec![
            msg("a", "old", Some(100)),
            msg("b", "no time", None),
            msg("c", "fresh", Some(900)),
        ]);
        let capped = cap_snapshot_window(&s, None, Some(1.0), Some(4000));
        let texts: Vec<&str> = capped.messages.iter().map(|m| m.text.as_str()).collect();
        assert_eq!(texts, ["no time", "fresh"]);
        assert_eq!(
            window_of(&capped),
            (None, Some(WindowHours::Int(1)), Some(2), Some(1))
        );
    }

    #[test]
    fn cap_count_keeps_last_n_and_reports_drops() {
        let s = snap(vec![
            msg("a", "one", Some(1)),
            msg("b", "two", Some(2)),
            msg("c", "three", Some(3)),
        ]);
        let capped = cap_snapshot_window(&s, Some(2), None, Some(10));
        let texts: Vec<&str> = capped.messages.iter().map(|m| m.text.as_str()).collect();
        assert_eq!(texts, ["two", "three"]);
        assert_eq!(window_of(&capped), (Some(2), None, Some(2), Some(1)));
    }

    #[test]
    fn cap_recaps_add_prior_drops_instead_of_resetting() {
        let mut s = snap(vec![msg("a", "one", Some(1)), msg("b", "two", Some(2))]);
        s.source_window = Some(SourceWindow::Dict {
            max_messages: Some(500),
            max_hours: Some(WindowHours::Int(24)),
            messages_kept: Some(2),
            messages_dropped: Some(5),
        });
        let capped = cap_snapshot_window(&s, Some(1), None, Some(10));
        assert_eq!(capped.messages.len(), 1);
        assert_eq!(capped.messages[0].text, "two");
        assert_eq!(window_of(&capped), (Some(1), None, Some(1), Some(6)));
    }

    #[test]
    fn cap_zero_message_cap_counts_drops_but_keeps_all() {
        let s = snap(vec![msg("a", "one", Some(1)), msg("b", "two", Some(2))]);
        let capped = cap_snapshot_window(&s, Some(0), None, Some(10));
        assert_eq!(capped.messages.len(), 2);
        assert_eq!(window_of(&capped), (Some(0), None, Some(2), Some(2)));
    }

    #[test]
    fn cap_no_caps_passes_messages_through_with_window_record() {
        let s = snap(vec![msg("a", "one", Some(1))]);
        let capped = cap_snapshot_window(&s, None, None, Some(10));
        assert_eq!(capped.messages.len(), 1);
        assert_eq!(window_of(&capped), (None, None, Some(1), Some(0)));
    }
}
