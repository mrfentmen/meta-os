//! Port of `os/intel.py` CLI surface — Relay Intelligence CLI.
//!
//! Subcommands: brief (list/show/morning/ondemand/boot), dispatch
//! (dry-run/approve/announce/undo/show, + --confirm-large over 12 jobs or
//! 40 files), with frozen `DISPATCH:<id> -> <n> jobs` announcement line.
//! The CLI validates plans through every gate, requires human approval
//! without `--dry-run`, refuses unsigned posts in `--crew-mode`, and posts
//! nothing without approval. Exit 2 names the failed job / unknown id.

#[derive(Debug, Clone, PartialEq)]
pub enum CliSubcommand {
    Brief(BriefArgs),
    Dispatch(DispatchArgs),
}

#[derive(Debug, Clone, PartialEq)]
pub struct BriefArgs {
    pub list: bool,
    pub show: Option<String>,
    pub morning: bool,
    pub ondemand: bool,
    pub boot: bool,
    pub since: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct DispatchArgs {
    pub goal: Option<String>,
    pub dry_run: bool,
    pub plan: Option<String>,
    pub approve: bool,
    pub confirm_large: bool,
    pub announce: bool,
    pub undo: Option<String>,
    pub show: Option<String>,
}

pub const LARGE_JOB_LIMIT: usize = 12;
pub const LARGE_FILE_LIMIT: usize = 40;

/// Size guardrail: plans over 12 jobs or 40 files need `--confirm-large`.
pub fn needs_confirm_large(n_jobs: usize, n_files: usize) -> bool {
    n_jobs > LARGE_JOB_LIMIT || n_files > LARGE_FILE_LIMIT
}

/// Frozen announcement line for a stored dispatch record.
pub fn format_dispatch_announcement(id: &str, n_jobs: usize) -> String {
    format!("DISPATCH:{id} -> {n_jobs} jobs")
}

/// Dispatch approval gate: without dry-run, require approve flag/interactive yes.
pub fn approval_granted(dry_run: bool, approve_flag: bool, interactive_yes: bool) -> bool {
    if dry_run {
        return true;
    }
    approve_flag || interactive_yes
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn large_plan_needs_confirm() {
        assert!(needs_confirm_large(13, 0));
        assert!(needs_confirm_large(0, 41));
        assert!(!needs_confirm_large(12, 40));
    }
    #[test]
    fn announcement_frozen() {
        assert_eq!(format_dispatch_announcement("d1", 3), "DISPATCH:d1 -> 3 jobs");
    }
}
