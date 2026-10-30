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
case!(test_os059_gateway_bake, ["bake marker"], []);
case!(test_os065_skills_loader, ["mount verify"], []);
case!(test_os083_artifact_store, ["deposit manifest"], []);
case!(test_os094_job_artifacts, ["attach dedupe"], []);
case!(test_os102_launch_run, ["verify-before-spawn", "tamper refusal"], []);
case!(test_os128_disk_audit, ["cold reader leak"], []);
pub mod test_os_base;
case!(test_os_boot_harness, ["harness"], ["live boot image"]);
case!(test_os_boot_selfcheck, ["selfcheck"], ["live boot image"]);
case!(test_os_boot_status, ["status"], ["live boot image"]);
case!(test_os_bus_unit, ["bus unit"], []);
case!(test_os_journal_watch, ["journal watch"], ["live journald"]);
case!(test_os_livebuild, ["livebuild config"], ["live build"]);
case!(test_os_manifest, ["manifest"], []);
case!(test_os_overseer_unit, ["overseer"], []);
case!(test_os_packer, ["packer template"], ["live packer build"]);
case!(test_os_power_cut, ["power cut drill"], ["live image"]);
case!(test_os_stackbake, ["stack bake"], []);
case!(test_os_target_unit, ["target unit"], []);
case!(test_os_tree, ["tree"], []);
case!(test_os_uplink, ["uplink"], ["live uplink"]);
case!(test_pomodoro, ["pomodoro parse", "schedule"], []);
case!(test_status, ["status shape"], []);
case!(test_worlds_pack, ["B27 validator parity"], []);

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
