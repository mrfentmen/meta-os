//! Port of `os/intel/push.py` — the two pushes (OS-097, Hana lane).
//!
//! At most one push per job close and one per job park; no third type.
//! Pure builders: no network/Redis/Spark/bus/secret. Gates: done needs
//! status "done" + overseer verified stamp + all checks passed; blocked
//! needs status "blocked" + a question (caller question else stored note).
//! [`PushLedger`] dedupes (job id, push type). Blocked question quoted verbatim.

pub const PUSH_TYPES: &[&str] = &["done", "blocked"];

#[derive(Debug, Clone, PartialEq)]
pub struct JobView {
    pub id: String,
    pub title: String,
    pub status: String,
    pub verified: bool,
    pub note: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Check {
    pub check: String,
    pub ok: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Verification {
    pub ok: bool,
    pub checks: Vec<Check>,
    pub artifacts: Vec<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Push {
    pub push_type: String,
    pub job_id: String,
    pub title: String,
    pub text: String,
}

fn done_summary(job: &JobView, v: &Verification) -> String {
    let mut s = format!("All done: {}", job.title);
    if v.artifacts.is_empty() {
        s.push_str(" (no artifacts recorded)");
    } else {
        s.push_str(&format!(" (built: {})", v.artifacts.join(", ")));
    }
    if v.checks.is_empty() {
        s.push_str("; no acceptance criteria were recorded");
    } else {
        let passed = v.checks.iter().filter(|c| c.ok).count();
        s.push_str(&format!("; {}/{} checks passed", passed, v.checks.len()));
    }
    s
}

/// Done push, or `None` when any gate fails.
pub fn build_done_push(job: &JobView, verification: Option<&Verification>) -> Option<Push> {
    if job.status != "done" || !job.verified {
        return None;
    }
    let v = verification?;
    if !v.ok || v.checks.iter().any(|c| !c.ok) {
        return None;
    }
    Some(Push {
        push_type: "done".to_string(),
        job_id: job.id.clone(),
        title: job.title.clone(),
        text: done_summary(job, v),
    })
}

/// Blocked push, or `None` when status/question gates fail.
pub fn build_blocked_push(job: &JobView, question: Option<&str>) -> Option<Push> {
    if job.status != "blocked" {
        return None;
    }
    let q = question
        .map(str::to_string)
        .filter(|s| !s.trim().is_empty())
        .unwrap_or_else(|| job.note.clone());
    if q.trim().is_empty() {
        return None;
    }
    Some(Push {
        push_type: "blocked".to_string(),
        job_id: job.id.clone(),
        title: job.title.clone(),
        text: q, // verbatim (BRF-005)
    })
}

pub fn build_push(kind: &str, job: &JobView, verification: Option<&Verification>, question: Option<&str>) -> Result<Option<Push>, String> {
    match kind {
        "done" => Ok(build_done_push(job, verification)),
        "blocked" => Ok(build_blocked_push(job, question)),
        _ => Err(format!("unknown push type: {kind}")),
    }
}

pub fn validate_push(p: &Push) -> Result<(), String> {
    if !PUSH_TYPES.contains(&p.push_type.as_str()) {
        return Err(format!("bad push type: {}", p.push_type));
    }
    if p.job_id.is_empty() || p.text.is_empty() {
        return Err("push missing job/text".to_string());
    }
    Ok(())
}

/// Remembers emitted (job id, push type) pairs; repeats return `None`.
#[derive(Debug, Default)]
pub struct PushLedger {
    emitted: Vec<(String, String)>,
}

impl PushLedger {
    pub fn decide_push(&mut self, p: Push) -> Option<Push> {
        let key = (p.job_id.clone(), p.push_type.clone());
        if self.emitted.contains(&key) {
            return None;
        }
        self.emitted.push(key);
        Some(p)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn done_job() -> JobView {
        JobView { id: "j".into(), title: "T".into(), status: "done".into(), verified: true, note: String::new() }
    }
    fn ver() -> Verification {
        Verification { ok: true, checks: vec![Check { check: "c".into(), ok: true }], artifacts: vec!["a.py".into()] }
    }

    #[test]
    fn done_needs_all_three_gates() {
        assert!(build_done_push(&done_job(), Some(&ver())).is_some());
        let mut j = done_job();
        j.verified = false;
        assert!(build_done_push(&j, Some(&ver())).is_none());
        let mut v = ver();
        v.checks[0].ok = false;
        v.ok = false;
        assert!(build_done_push(&done_job(), Some(&v)).is_none());
        assert!(build_done_push(&done_job(), None).is_none());
    }

    #[test]
    fn blocked_quotes_verbatim() {
        let j = JobView { id: "b".into(), title: "T".into(), status: "blocked".into(), verified: false, note: "stored?".into() };
        assert_eq!(build_blocked_push(&j, None).unwrap().text, "stored?");
        assert_eq!(build_blocked_push(&j, Some("caller?")).unwrap().text, "caller?");
        let j2 = JobView { note: String::new(), ..j };
        assert!(build_blocked_push(&j2, None).is_none());
    }

    #[test]
    fn ledger_fires_once() {
        let mut l = PushLedger::default();
        let p = build_done_push(&done_job(), Some(&ver())).unwrap();
        assert!(l.decide_push(p.clone()).is_some());
        assert!(l.decide_push(p).is_none());
    }

    #[test]
    fn no_third_type() {
        assert!(build_push("other", &done_job(), None, None).is_err());
    }
}
