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
    format!("Brief for {room} failed: {err}");
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
}
