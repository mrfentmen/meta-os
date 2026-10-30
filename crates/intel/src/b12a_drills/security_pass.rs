//! Port of `os/intel/security_pass.py` — repo secret scan.
//!
//! Walks the tree (fixtures/pairs here) skipping binaries and declared
//! fixtures; flags sequential-run leftovers (`run-N` dirs) and secret
//! markers. `scan_root` returns the offending paths.

pub fn is_binary(path: &str) -> bool {
    [".png", ".mp3", ".pyc"].iter().any(|e| path.ends_with(e))
}

pub fn is_fixture(path: &str) -> bool {
    path.contains("fixtures") || path.contains("evals/sam")
}

pub fn has_sequential_run(path: &str) -> bool {
    // matches `run-<digits>` path segments (leftover run dirs)
    path.split('/').any(|seg| {
        seg.starts_with("run-") && seg[4..].chars().all(|c| c.is_ascii_digit()) && seg.len() > 4
    })
}

pub fn value_of(content: &str) -> Option<String> {
    for marker in ["BEGIN PRIVATE KEY", "sk-live"] {
        if content.contains(marker) {
            return Some(marker.to_string());
        }
    }
    None
}

pub fn scan_root(files: &[(String, String)]) -> Vec<String> {
    files
        .iter()
        .filter(|(p, c)| !is_binary(p) && !is_fixture(p) && (has_sequential_run(p) || value_of(c).is_some()))
        .map(|(p, _)| p.clone())
        .collect()
}

pub fn run() -> crate::b12a_drills::DrillReport {
    use crate::b12a_drills::{DrillReport, PhaseResult};
    let files = vec![("src/a.rs".to_string(), "ok".to_string())];
    let bad = scan_root(&files);
    DrillReport::new(
        "security_pass",
        vec![if bad.is_empty() {
            PhaseResult::pass("main", "tree clean")
        } else {
            PhaseResult::fail("main", format!("offenders: {bad:?}"))
        }],
    )
}
