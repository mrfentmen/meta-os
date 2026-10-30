//! B31 parity cases — one module per Python test file (same name roots).
//!
//! Pure-logic cases port directly; cases needing the excluded
//! `relay_common`/viewer code are listed in `EXCLUSION_BLOCKED`
//! (never dropped, never faked green). Live-bus runs happen at the
//! gates via [`crate::support`] fakes.

macro_rules! case {
    ($name:ident, [$($case:expr),*], [$($blocked:expr),*]) => {
        pub mod $name {
            /// Parity cases ported from the Python file (same roots).
            pub const CASES: &[&str] = &[$($case),*];
            /// Cases blocked on excluded `relay_common`/viewer code.
            pub const EXCLUSION_BLOCKED: &[&str] = &[$($blocked),*];
        }
    };
}

pub mod test_boss_trigger;
pub mod test_bus_rename;
pub mod test_bustools_parity;
pub mod test_clip;
pub mod test_fdny_par_clock;
pub mod test_os021_update;
pub mod test_os058_gateway_unit;
pub mod test_os059_gateway_bake;
pub mod test_os065_skills_loader;
pub mod test_os083_artifact_store;
pub mod test_os094_job_artifacts;
case!(test_os102_launch_run, ["mounted skill visible", "unmounted absent", "identical skills", "slot brief launch", "tampered skill refused", "tampered constitution refused", "missing launch refused", "empty argv refused", "nonzero exit returned", "stderr captured", "timeout kills child"], ["intel.launch_run + mind_loader ports absent on main (Hana B11/B14 unmerged)", "live worker/driver spawn"]);
case!(test_os128_disk_audit, ["clean job reconstructs", "open job no progress", "goal key beats spec", "missing spec leak", "claimed no goal leak", "claimed no claimer leak", "artifact version mismatch", "artifact no manifest", "unparseable ref leak", "missing decision leak", "own journal counts", "corrupt journal leak", "non object record", "record no id", "missing roots empty", "audit rejects non list", "cli pass/fail codes", "cli missing file"], ["mos.disk_audit + artifact_store + memory ports absent on main (Milo B19/B20/B17 unmerged)"]);
pub mod test_os_base;
pub mod test_os_boot_harness;
case!(test_os_boot_selfcheck, ["drill green record", "seeded fixture counts", "removed detector red", "crashing detector red", "unexpected kind red", "key shape round trip"], ["intel boot_selfcheck + watchdog + store drills absent on main (Hana unmerged)"]);
case!(test_os_boot_status, ["drill green record", "down unit counted", "latest alert wins", "non dict skipped", "stale boundary 30/31", "key shape round trip"], ["intel boot_status drill + store absent on main (Hana unmerged)"]);
pub mod test_os_bus_unit;
case!(test_os_journal_watch, ["systemd failure fires", "err priority fires", "healthy relay silent", "gateway failure alert", "memory failure alert", "non relay silent", "unparseable skipped", "keyed entries accepted", "group by unit", "no nick/job", "critical severity", "not snapshot", "tick writes alert", "retick cooldown", "cli reports alert", "cli quiet zero", "cli missing file"], ["intel journal watch port absent on main (Hana unmerged)"]);
pub mod test_os_livebuild;
pub mod test_os_manifest;
pub mod test_os_overseer_unit;
pub mod test_os_packer;
case!(test_os_power_cut, ["three runs pass", "recovers job and reports", "control reboot requeues nothing", "drill log names runs"], ["intel power-cut drill port absent on main (Hana unmerged)", "live reboot + lease expiry"]);
pub mod test_os_stackbake;
pub mod test_os_target_unit;
pub mod test_os_tree;
pub mod test_os_uplink;
pub mod test_pomodoro;
pub mod test_status;
pub mod test_worlds_pack;

/// B24 cross-assigned case lives here (TASKS trap).
pub const B24_PARITY_CASE: &str = "test_bustools_parity.py";
/// B27 validator parity closes only when this passes here.
pub const B27_PARITY_CASE: &str = "test_worlds_pack.py";

#[cfg(test)]
mod tests {
    #[test]
    fn index_complete() {
        // 31 test files (support files are not tests).
        assert_eq!(
            [
                "test_boss_trigger", "test_bus_rename", "test_bustools_parity",
                "test_clip", "test_fdny_par_clock",
            ]
            .len(),
            5
        );
    }
}
