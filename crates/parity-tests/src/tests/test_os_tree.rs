//! T057 [B31] port of `os/tests/test_os_tree.py` (same name roots).
//!
//! OS tree shape: every expected file exists, shell scripts parse,
//! build-image references no lane sources, referenced inputs exist,
//! every enabled unit ships a `[Unit]` section, preseed/packages pins,
//! README honesty limits, no em dashes. Pure reads + syntax checks.
//!
//! TREE DRIFT: the Python `os/…` root — the tree lives under the folded
//! `os/os/` directory.

use std::path::{Path, PathBuf};

pub const CASES: &[&str] = &[
    "tree files exist",
    "bash scripts syntax clean",
    "sh scripts syntax clean",
    "build image code lines reference no lane src",
    "build image referenced inputs exist",
    "enabled units exist in services",
    "preseed carries os009 answers",
    "packages list carries proven set",
    "readme states honesty limits",
    "new os docs carry no em dash",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[];

pub const TREE_FILES: &[&str] = &[
    "build-image.sh",
    "build-all.sh",
    "preseed.cfg",
    "packages.txt",
    "README.md",
    "grub-early.cfg",
    "README-FIRSTBOOT.md",
    "services/relay.target",
    "services/relay-bus.service",
    "services/relay-dashboard.service",
    "services/relay-jobs.service",
    "services/relay-overseer.service",
    "services/relay-overseer.timer",
    "services/relay-ready.service",
    "services/metaos-firstboot.service",
    "firstboot/metaos-firstboot",
    "bin/metaos-boot-checklist",
    "bin/metaos-update",
];

/// Units build-image.sh enables into a target.
pub const ENABLED_UNITS: &[&str] = &[
    "relay-dashboard.service",
    "relay-bus.service",
    "relay-jobs.service",
    "relay-overseer.timer",
    "relay-ready.service",
    "metaos-firstboot.service",
    "relay-overseer.service",
    "relay-watchdog.service",
    "relay-brief.service",
];

pub const BASH_SCRIPTS: &[&str] = &["build-image.sh", "build-all.sh"];
pub const SH_SCRIPTS: &[&str] = &[
    "firstboot/metaos-firstboot",
    "bin/metaos-boot-checklist",
    "bin/metaos-update",
];

pub const PROVEN_PACKAGES: &[&str] = &[
    "systemd", "systemd-sysv", "udev", "dbus", "linux-image-amd64",
    "initramfs-tools", "python3", "curl", "ca-certificates", "iproute2", "git",
];

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
}
fn os_dir() -> PathBuf {
    root().join("os").join("os")
}
fn read_rel(rel: &str) -> String {
    std::fs::read_to_string(os_dir().join(rel)).unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tree_files_exist() {
        for rel in TREE_FILES {
            assert!(os_dir().join(rel).is_file(), "{rel}");
        }
    }

    #[test]
    fn test_bash_scripts_syntax_clean() {
        for rel in BASH_SCRIPTS {
            let out = std::process::Command::new("bash").arg("-n").arg(os_dir().join(rel)).output().expect("bash failed");
            assert!(out.status.success(), "{rel}: {}", String::from_utf8_lossy(&out.stderr));
        }
    }

    #[test]
    fn test_sh_scripts_syntax_clean() {
        for rel in SH_SCRIPTS {
            let out = std::process::Command::new("sh").arg("-n").arg(os_dir().join(rel)).output().expect("sh failed");
            assert!(out.status.success(), "{rel}: {}", String::from_utf8_lossy(&out.stderr));
        }
    }

    #[test]
    fn test_build_image_code_lines_reference_no_lane_src() {
        for line in read_rel("build-image.sh").lines() {
            if line.trim_start().starts_with('#') {
                continue;
            }
            for lane in ["src/units", "src/bin", "src/grub", "src/README"] {
                assert!(!line.contains(lane), "{line}");
            }
        }
    }

    #[test]
    fn test_build_image_referenced_inputs_exist() {
        for rel in ["services", "firstboot", "bin", "grub-early.cfg", "README-FIRSTBOOT.md"] {
            assert!(os_dir().join(rel).exists(), "{rel}");
        }
    }

    #[test]
    fn test_enabled_units_exist_in_services() {
        for unit in ENABLED_UNITS {
            let text = read_rel(&format!("services/{unit}"));
            assert!(text.contains("[Unit]"), "{unit}");
        }
    }

    #[test]
    fn test_preseed_carries_os009_answers() {
        let text = read_rel("preseed.cfg");
        for needle in ["relay", "en_US.UTF-8", "Etc/UTC", "password *"] {
            assert!(text.contains(needle), "preseed missing {needle:?}");
        }
    }

    #[test]
    fn test_packages_list_carries_proven_set() {
        let text = read_rel("packages.txt");
        for package in PROVEN_PACKAGES {
            assert!(text.contains(package), "{package}");
        }
    }

    #[test]
    fn test_readme_states_honesty_limits() {
        let text = read_rel("README.md");
        for needle in ["Unproven", "Unpinned", "not claimed working from this tree"] {
            assert!(text.contains(needle), "README missing {needle:?}");
        }
    }

    #[test]
    fn test_new_os_docs_carry_no_em_dash() {
        for rel in ["README.md", "preseed.cfg", "packages.txt"] {
            assert!(!read_rel(rel).contains('\u{2014}'), "{rel}");
        }
    }
}
