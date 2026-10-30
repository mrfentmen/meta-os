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
}
