//! Port of `os/intel/baton.py` — the OS-125 baton pass composer.
//!
//! The baton hands a job to the next worker with title, deposited
//! progress, remaining files/steps, and acceptance checks. Pure text
//! composition; the claim move itself belongs to the overseer.

#[derive(Debug, Clone, PartialEq)]
pub struct BatonSpec {
    pub job_id: String,
    pub goal: String,
    pub progress: String,
    pub files: Vec<String>,
    pub steps: Vec<String>,
    pub acceptance: Vec<String>,
}

pub fn remaining_files(spec: &BatonSpec, done: &[String]) -> Vec<String> {
    spec.files.iter().filter(|f| !done.contains(f)).cloned().collect()
}

pub fn remaining_steps(spec: &BatonSpec, done: &[String]) -> Vec<String> {
    spec.steps.iter().filter(|s| !done.contains(s)).cloned().collect()
}

pub fn acceptance_checks(spec: &BatonSpec) -> Vec<String> {
    spec.acceptance.clone()
}

pub fn compose_baton(spec: &BatonSpec, from_nick: &str, to_nick: &str) -> String {
    format!(
        "BATON {} from {from_nick} to {to_nick}\ngoal: {}\nprogress: {}\nfiles: {}\nsteps: {}\nacceptance: {}",
        spec.job_id,
        spec.goal,
        if spec.progress.is_empty() { "(none deposited)" } else { &spec.progress },
        if spec.files.is_empty() { "(none)".to_string() } else { spec.files.join(", ") },
        if spec.steps.is_empty() { "(none)".to_string() } else { spec.steps.join(", ") },
        if spec.acceptance.is_empty() { "(none)".to_string() } else { spec.acceptance.join("; ") },
    )
}

pub fn baton_brief_lines(job_id: &str, from: &str, to: &str) -> Vec<String> {
    vec![format!("Baton {job_id} passed from {from} to {to}")]
}

/// A posted job as seen by the baton pass tick: the job id, the worker
/// currently holding it, and the files still to touch.
#[derive(Debug, Clone, PartialEq)]
pub struct BatonPassJob {
    pub id: String,
    pub from_worker: String,
    pub remaining_files: Vec<String>,
}

/// One journal baton-pass record (baton.py `baton_pass_tick` record
/// shape). The record carries the baton material, never a push: the
/// overseer moves the claim from this record, and this module never
/// moves it itself.
#[derive(Debug, Clone, PartialEq)]
pub struct BatonPassRecord {
    pub kind: String,
    pub dedupe_key: String,
    pub job: String,
    pub from_worker: String,
    pub to_worker: String,
    pub remaining_files: Vec<String>,
    pub passed_at: i64,
}

/// One baton pass tick: one new baton-pass record for the named job
/// handed to `to_worker`, or nothing when the job id or the next
/// worker is empty, the job is unknown, or the pass is already
/// journaled (keys passed in). Returns the new record only; the
/// caller appends it. Inputs are never mutated.
pub fn baton_pass_tick(
    jobs: &[BatonPassJob],
    job_id: &str,
    to_worker: &str,
    journal_keys: &[String],
    now: i64,
) -> Vec<BatonPassRecord> {
    if job_id.trim().is_empty() || to_worker.trim().is_empty() {
        return Vec::new();
    }
    let job = match jobs.iter().find(|j| j.id == job_id) {
        Some(job) => job,
        None => return Vec::new(),
    };
    let dedupe_key = format!("baton:{job_id}");
    if journal_keys.contains(&dedupe_key) {
        return Vec::new();
    }
    vec![BatonPassRecord {
        kind: "baton-pass".to_string(),
        dedupe_key,
        job: job_id.to_string(),
        from_worker: job.from_worker.clone(),
        to_worker: to_worker.to_string(),
        remaining_files: job.remaining_files.clone(),
        passed_at: now,
    }]
}

/// One frozen line per baton-pass record, in record order (baton.py
/// `baton_brief_lines` format). Other record kinds render nothing, so
/// a mixed journal briefs only its passes.
pub fn pass_brief_lines(records: &[BatonPassRecord]) -> Vec<String> {
    records
        .iter()
        .filter(|r| r.kind == "baton-pass")
        .map(|r| {
            format!(
                "Baton passed job {} from {} to {}: {} file(s) still to touch.",
                r.job,
                r.from_worker,
                r.to_worker,
                r.remaining_files.len()
            )
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    fn spec() -> BatonSpec {
        BatonSpec { job_id: "j".into(), goal: "g".into(), progress: "p".into(), files: vec!["a".into(), "b".into()], steps: vec!["s1".into()], acceptance: vec!["ok".into()] }
    }
    #[test]
    fn remaining_subtracts_done() {
        assert_eq!(remaining_files(&spec(), &["a".into()]), vec!["b".to_string()]);
    }
    #[test]
    fn compose_names_parties() {
        assert!(compose_baton(&spec(), "m", "h").contains("from m to h"));
    }

    fn pass_job() -> BatonPassJob {
        BatonPassJob { id: "j1".into(), from_worker: "hana".into(), remaining_files: vec!["a".into(), "b".into()] }
    }

    #[test]
    fn baton_pass_tick_one_record_and_dedupes() {
        let recs = baton_pass_tick(&[pass_job()], "j1", "rowan", &[], 42);
        assert_eq!(recs.len(), 1);
        assert_eq!(recs[0].kind, "baton-pass");
        assert_eq!(recs[0].dedupe_key, "baton:j1");
        assert_eq!(recs[0].from_worker, "hana");
        assert_eq!(recs[0].to_worker, "rowan");
        assert_eq!(recs[0].passed_at, 42);
        // Already journaled: the same pass journals nothing new.
        let keys = vec![recs[0].dedupe_key.clone()];
        assert!(baton_pass_tick(&[pass_job()], "j1", "rowan", &keys, 43).is_empty());
    }

    #[test]
    fn baton_pass_tick_skips_empty_and_unknown() {
        assert!(baton_pass_tick(&[pass_job()], "", "rowan", &[], 0).is_empty());
        assert!(baton_pass_tick(&[pass_job()], "j1", "", &[], 0).is_empty());
        assert!(baton_pass_tick(&[pass_job()], "nope", "rowan", &[], 0).is_empty());
        assert!(baton_pass_tick(&[], "j1", "rowan", &[], 0).is_empty());
    }

    #[test]
    fn pass_brief_lines_counts_remaining_and_skips_other_kinds() {
        let recs = baton_pass_tick(&[pass_job()], "j1", "rowan", &[], 42);
        assert_eq!(
            pass_brief_lines(&recs),
            vec!["Baton passed job j1 from hana to rowan: 2 file(s) still to touch.".to_string()]
        );
        let other = BatonPassRecord { kind: "wake".into(), ..recs[0].clone() };
        assert!(pass_brief_lines(&[other]).is_empty());
    }
}
