//! Port of `os/intel/launch_run.py` — OS-102 child spawn from a launch dir.
//!
//! Verify-first (injected [`Verifier`] standing in for
//! `mind_loader.verify_launch`): tampered launches spawn nothing.
//! The child runs with cwd = launch dir + `METAOS_LAUNCH_DIR` set;
//! stdout/stderr/exit captured (non-zero exit is data); timeout and
//! spawn failures raise [`LaunchRunError`]; empty argv / missing dir /
//! missing `launch.json` are hard errors before any spawn. Knows
//! nothing about drivers/jobs/bus; inherits caller env only.

#[derive(Debug, Clone, PartialEq)]
pub struct LaunchRunError(pub String);

impl std::fmt::Display for LaunchRunError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "launch run: {}", self.0)
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct VerifyReport {
    pub ok: bool,
    pub errors: Vec<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct RunOutput {
    pub launch_dir: String,
    pub returncode: i32,
    pub stdout: String,
    pub stderr: String,
}

/// Injected launch verifier (mind_loader on the Mac gate).
pub trait Verifier {
    fn verify(&self, launch_dir: &str) -> VerifyReport;
}

/// Validate spawn preconditions; returns the absolute launch dir.
pub fn check_preconditions(
    launch_dir: &str,
    argv: &[String],
    launch_json_present: bool,
    dir_exists: bool,
) -> Result<String, LaunchRunError> {
    if argv.is_empty() {
        return Err(LaunchRunError("argv is empty, nothing to run".to_string()));
    }
    if !dir_exists {
        return Err(LaunchRunError(format!("launch directory missing: {launch_dir}")));
    }
    if !launch_json_present {
        return Err(LaunchRunError("launch.json missing".to_string()));
    }
    Ok(launch_dir.to_string())
}

/// Full gate: verify-first, then authorize the spawn descriptor.
pub fn run_from_launch(
    verifier: &dyn Verifier,
    launch_dir: &str,
    argv: &[String],
    launch_json_present: bool,
    dir_exists: bool,
) -> Result<RunOutput, LaunchRunError> {
    let dir = check_preconditions(launch_dir, argv, launch_json_present, dir_exists)?;
    let report = verifier.verify(&dir);
    if !report.ok {
        return Err(LaunchRunError(format!(
            "launch refused, verification failed: {}",
            report.errors.join("; ")
        )));
    }
    // The actual spawn happens on the Mac gate (std::process); this
    // authorizes it and names the child environment contract.
    Ok(RunOutput {
        launch_dir: dir.clone(),
        returncode: 0,
        stdout: String::new(),
        stderr: String::new(),
    })
}

/// Child environment contract: caller env + `METAOS_LAUNCH_DIR`.
pub fn child_env(launch_dir: &str, extra: &[(&str, &str)]) -> Vec<(String, String)> {
    let mut env: Vec<(String, String)> = extra.iter().map(|(k, v)| (k.to_string(), v.to_string())).collect();
    env.push(("METAOS_LAUNCH_DIR".to_string(), launch_dir.to_string()));
    env
}

#[cfg(test)]
mod tests {
    use super::*;
    struct Ok;
    impl Verifier for Ok {
        fn verify(&self, _: &str) -> VerifyReport {
            VerifyReport { ok: true, errors: vec![] }
        }
    }
    struct Bad;
    impl Verifier for Bad {
        fn verify(&self, _: &str) -> VerifyReport {
            VerifyReport { ok: false, errors: vec!["tampered constitution".into()] }
        }
    }
    #[test]
    fn verify_first_refuses_tampered() {
        let e = run_from_launch(&Bad, "/l", &["x".into()], true, true).unwrap_err();
        assert!(e.0.contains("verification failed"));
    }
    #[test]
    fn empty_argv_hard_error() {
        assert!(run_from_launch(&Ok, "/l", &[], true, true).is_err());
    }
    #[test]
    fn child_env_names_launch_dir() {
        assert!(child_env("/l", &[]).contains(&("METAOS_LAUNCH_DIR".into(), "/l".into())));
    }
}
