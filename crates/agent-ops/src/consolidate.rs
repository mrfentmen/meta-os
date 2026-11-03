//! Semantic memory consolidation (sleep cycles).
//!
//! Raw run records bloat: every package-install log and retry is kept
//! forever, and queries slow down. Consolidation runs when the agent is
//! idle: it scores each record, keeps what teaches (failures with
//! lessons, surprising successes, first-seen errors), and drops noise
//! (routine installs, identical repeats). Output is a compact lesson
//! set plus a drop report — the ledger stays append-only; consolidation
//! never rewrites history, it writes a NEW condensed record.

/// One raw record awaiting consolidation.
#[derive(Debug, Clone)]
pub struct Record {
    pub id: String,
    /// e.g. "install", "retry", "success", "failure", "lesson".
    pub kind: String,
    pub text: String,
    /// 0 = routine, higher = worth keeping.
    pub signal: u8,
}

/// A condensed lesson surviving consolidation.
#[derive(Debug, Clone, PartialEq)]
pub struct Lesson {
    pub from_ids: Vec<String>,
    pub lesson: String,
}

#[derive(Debug)]
pub struct Consolidation {
    pub kept: Vec<Record>,
    pub dropped: Vec<String>,
    pub lessons: Vec<Lesson>,
}

/// Score a record. Deterministic and legible: explicit kinds beat
/// keyword guessing, but unknown kinds fall back to signal level.
pub fn score(r: &Record) -> u8 {
    match r.kind.as_str() {
        "lesson" => 100,
        "failure" => 80,
        "success" if r.signal >= 50 => 70,
        "success" => 20,
        "retry" => 30,
        "install" => 5,
        _ => r.signal.min(60),
    }
}

/// Consolidate: keep score >= keep_at, group kept failures/successes
/// with lessons into lesson entries, report the dropped ids.
pub fn consolidate(records: Vec<Record>, keep_at: u8) -> Consolidation {
    let mut kept = Vec::new();
    let mut dropped = Vec::new();
    for r in records {
        if score(&r) >= keep_at {
            kept.push(r);
        } else {
            dropped.push(r.id);
        }
    }
    // Group by lesson-ish text overlap is out of scope for a
    // deterministic core; group by kind for the condensed view.
    let mut lessons = Vec::new();
    let mut by_kind: std::collections::BTreeMap<&str, Vec<&Record>> = std::collections::BTreeMap::new();
    for r in &kept {
        by_kind.entry(r.kind.as_str()).or_default().push(r);
    }
    for (kind, rs) in by_kind {
        if rs.len() >= 2 {
            lessons.push(Lesson {
                from_ids: rs.iter().map(|r| r.id.clone()).collect(),
                lesson: format!("{}x {}: {}", rs.len(), kind, rs[0].text.chars().take(120).collect::<String>()),
            });
        }
    }
    Consolidation { kept, dropped, lessons }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rec(id: &str, kind: &str, text: &str, signal: u8) -> Record {
        Record { id: id.into(), kind: kind.into(), text: text.into(), signal }
    }

    #[test]
    fn noise_dropped_lessons_kept() {
        let rs = vec![
            rec("1", "install", "fetched 40 packages", 5),
            rec("2", "retry", "attempt 3 same flags", 30),
            rec("3", "failure", "dns down, use mirror", 80),
            rec("4", "failure", "mirror timeout, retry once", 75),
            rec("5", "success", "mirror worked", 70),
            rec("6", "lesson", "always set the mirror first", 100),
        ];
        let c = consolidate(rs, 50);
        assert!(c.dropped.contains(&"1".to_string()));
        assert!(c.dropped.contains(&"2".to_string()));
        assert_eq!(c.kept.len(), 4);
        assert!(!c.lessons.is_empty());
    }

    #[test]
    fn everything_below_threshold_drops() {
        let rs = vec![rec("1", "install", "x", 1)];
        let c = consolidate(rs, 90);
        assert!(c.kept.is_empty());
        assert_eq!(c.dropped, vec!["1"]);
    }
}
