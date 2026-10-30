//! Port of `os/intel/gate.py` — attempt budgets + escalation gate.
//!
//! A job parks when its attempt budget is spent or its blocker is Dale's
//! call (money/permission/direction — explicit `blocker_kind`, never
//! inferred). Parking fires exactly one blocked push; a second tick over an
//! already-parked job journals nothing. Figures read like WDG-008: ints or
//! integer-valued strings; bools/floats/non-numeric/negative/zero-max are
//! unbudgeted. Done jobs never park; jobs without ids are skipped.

pub const DALE_CALL_KINDS: &[&str] = &["money", "permission", "direction"];

#[derive(Debug, Clone, PartialEq)]
pub struct JobRecord {
    pub id: Option<String>,
    pub status: String,
    pub attempts: Option<JobInt>,
    pub max_attempts: Option<JobInt>,
    pub blocker_kind: Option<String>,
    pub note: String,
}

#[derive(Debug, Clone, PartialEq)]
pub enum JobInt {
    Int(i64),
    Str(String),
    Bool(bool),
    Float(f64),
}

pub fn as_int(v: &JobInt) -> Option<i64> {
    match v {
        JobInt::Bool(_) => None,
        JobInt::Float(_) => None,
        JobInt::Int(n) => (*n >= 0).then_some(*n),
        JobInt::Str(s) => {
            let t = s.trim();
            if t.is_empty() {
                return None;
            }
            // integer-valued strings only (no '.', no exponent)
            if t.chars().any(|c| c == '.' || c == 'e' || c == 'E') {
                return None;
            }
            let n: i64 = t.parse().ok()?;
            (n >= 0).then_some(n)
        }
    }
}

pub fn attempts_left(job: &JobRecord) -> Option<i64> {
    let max = job.max_attempts.as_ref().and_then(as_int)?;
    if max == 0 {
        return None;
    }
    let used = job.attempts.as_ref().and_then(as_int).unwrap_or(0);
    Some(max - used)
}

pub fn budget_exhausted(job: &JobRecord) -> bool {
    matches!(attempts_left(job), Some(n) if n <= 0)
}

pub fn is_dale_call(job: &JobRecord) -> bool {
    job.blocker_kind
        .as_deref()
        .is_some_and(|k| DALE_CALL_KINDS.contains(&k))
}

pub fn question_for(job: &JobRecord) -> Option<String> {
    if is_dale_call(job) {
        Some(format!(
            "Job {} blocked on {}: {}",
            job.id.clone().unwrap_or_default(),
            job.blocker_kind.clone().unwrap_or_default(),
            job.note
        ))
    } else if budget_exhausted(job) {
        Some(format!("Job {} spent its attempt budget", job.id.clone().unwrap_or_default()))
    } else {
        None
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct JournalRecord {
    pub dedupe_key: String,
    pub kind: String,
    pub job_id: String,
    pub text: String,
}

/// One gate tick: returns new journal records (park + escalation payload).
/// Jobs already parked (`park:<id>` in journal) yield nothing.
pub fn gate_tick(jobs: &[JobRecord], journal: &[JournalRecord]) -> Vec<JournalRecord> {
    let mut out = Vec::new();
    for job in jobs {
        let Some(id) = job.id.clone() else { continue };
        if id.is_empty() {
            continue;
        }
        if job.status == "done" {
            continue;
        }
        let should_park = budget_exhausted(job) || is_dale_call(job);
        if !should_park {
            continue;
        }
        let park_key = format!("park:{id}");
        if journal.iter().any(|r| r.dedupe_key == park_key) || out.iter().any(|r: &JournalRecord| r.dedupe_key == park_key) {
            continue;
        }
        let question = question_for(job).unwrap_or_default();
        out.push(JournalRecord {
            dedupe_key: park_key,
            kind: "parked".to_string(),
            job_id: id.clone(),
            text: question.clone(),
        });
        out.push(JournalRecord {
            dedupe_key: format!("escalate:{id}"),
            kind: "blocked-push".to_string(),
            job_id: id,
            text: question,
        });
    }
    out
}

pub fn gate_brief_lines(records: &[JournalRecord]) -> Vec<String> {
    records
        .iter()
        .filter(|r| r.kind == "parked")
        .map(|r| format!("Parked {}: {}", r.job_id, r.text))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn job(id: &str, attempts: i64, max: i64) -> JobRecord {
        JobRecord {
            id: Some(id.to_string()),
            status: "open".to_string(),
            attempts: Some(JobInt::Int(attempts)),
            max_attempts: Some(JobInt::Int(max)),
            blocker_kind: None,
            note: String::new(),
        }
    }

    #[test]
    fn bools_are_not_ints() {
        assert_eq!(as_int(&JobInt::Bool(true)), None);
        assert_eq!(as_int(&JobInt::Float(2.5)), None);
        assert_eq!(as_int(&JobInt::Str("2.5".to_string())), None);
        assert_eq!(as_int(&JobInt::Str("3".to_string())), Some(3));
    }

    #[test]
    fn zero_max_is_unbudgeted() {
        let j = job("a", 99, 0);
        assert_eq!(attempts_left(&j), None);
        assert!(!budget_exhausted(&j));
    }

    #[test]
    fn done_never_parks() {
        let mut j = job("a", 9, 3);
        j.status = "done".to_string();
        assert!(gate_tick(&[j], &[]).is_empty());
    }

    #[test]
    fn dale_call_parks_by_kind_not_note() {
        let mut j = job("b", 0, 10);
        j.blocker_kind = Some("money".to_string());
        j.note = "need $5".to_string();
        assert!(is_dale_call(&j));
        assert_eq!(gate_tick(&[j.clone()], &[]).len(), 2);
        // dependency kind stays quiet
        j.blocker_kind = Some("dependency".to_string());
        assert!(gate_tick(&[j], &[]).is_empty());
    }

    #[test]
    fn second_tick_journals_nothing() {
        let j = job("c", 5, 3);
        let first = gate_tick(&[j.clone()], &[]);
        assert_eq!(first.len(), 2);
        let second = gate_tick(&[j], &first);
        assert!(second.is_empty());
    }
}
