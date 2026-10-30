//! T050 [B31] port of `os/tests/test_os_livebuild.py` (same name roots).
//!
//! OS-008 fallback pipeline: live-build config, package list, services
//! hook, wrapper guards/staging/steps, docs. Pure file reads + `sh`/`bash
//! `-n syntax checks. No build runs.
//!
//! TREE DRIFT (documented, not hidden): the Python names `os/…` —
//! everything lives under the folded tree (`os/os/…`).

use std::path::{Path, PathBuf};

pub const CASES: &[&str] = &[
    "config exists and names bookworm amd64 iso hybrid",
    "config states unproven limit",
    "no second base in live build files",
    "config shell syntax",
    "covers packages txt names",
    "covers spec extras as real package names",
    "no versions pinned here",
    "hook enables exactly the build image unit set",
    "hook enables nothing else from services",
    "no unit copy lives in live build tree",
    "hook shell syntax",
    "wrapper guards",
    "wrapper stages from repo sources and cleans up",
    "wrapper build steps and output naming",
    "wrapper bash syntax",
    "readme carries os008 section with limit",
    "base carries fallback divergences",
    "new doc sections carry no em dash",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[];

/// Second-base codenames forbidden outside the frozen bookworm base.
pub const FORBIDDEN: &[&str] = &["bullseye", "trixie", "forky", "sid", "ubuntu", "fedora", "centos", "rhel", "archlinux"];

pub const ENABLED_UNITS: &[&str] = &[
    "relay-dashboard.service",
    "relay-bus.service",
    "relay-jobs.service",
    "relay-overseer.timer",
    "relay-ready.service",
    "relay-overseer.service",
    "relay-watchdog.service",
    "relay-brief.service",
];
pub const FIRSTBOOT_UNIT: &str = "metaos-firstboot.service";
pub const NOT_ENABLED_UNITS: &[&str] = &["relay-worker@.service"];
pub const SPEC_EXTRA_PACKAGES: &[&str] = &[
    "redis-tools",
    "chromium",
    "fonts-dejavu",
    "openssh-server",
    "qemu-guest-agent",
];

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
}
fn os_inner() -> PathBuf {
    root().join("os").join("os")
}
fn live_dir() -> PathBuf {
    os_inner().join("live-build")
}
fn config() -> PathBuf {
    live_dir().join("auto").join("config")
}
fn package_list() -> PathBuf {
    live_dir().join("config/package-lists/metaos.list.chroot")
}
fn hook() -> PathBuf {
    live_dir().join("config/hooks/live/0900-metaos-services.hook.chroot")
}
fn wrapper() -> PathBuf {
    os_inner().join("build-live.sh")
}
fn read(p: &Path) -> String {
    std::fs::read_to_string(p).unwrap_or_default()
}

fn live_build_files() -> Vec<PathBuf> {
    let mut out = vec![];
    let mut stack = vec![live_dir()];
    while let Some(d) = stack.pop() {
        if let Ok(rd) = std::fs::read_dir(&d) {
            for e in rd.flatten() {
                let p = e.path();
                if p.is_dir() {
                    stack.push(p);
                } else {
                    out.push(p);
                }
            }
        }
    }
    out.sort();
    out
}

fn name_list(text: &str) -> Vec<String> {
    text.lines().map(str::trim).filter(|l| !l.is_empty() && !l.starts_with('#')).map(str::to_string).collect()
}

fn second_base_in(text: &str) -> Option<String> {
    let lower = text.to_lowercase();
    let mut token = String::new();
    let mut found: Option<String> = None;
    let mut flush = |token: &mut String, found: &mut Option<String>| {
        if FORBIDDEN.contains(&token.as_str()) {
            *found = Some(token.clone());
        }
        token.clear();
    };
    for c in lower.chars() {
        if c.is_ascii_alphanumeric() {
            token.push(c);
        } else {
            flush(&mut token, &mut found);
            if found.is_some() {
                break;
            }
        }
    }
    flush(&mut token, &mut found);
    found
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_exists_and_names_bookworm_amd64_iso_hybrid() {
        let text = read(&config());
        assert!(text.starts_with("#!/bin/sh"));
        assert!(text.contains("--distribution bookworm"));
        assert!(text.contains("--architectures amd64"));
        assert!(text.contains("--binary-images iso-hybrid"));
        assert!(!text.contains("--debian-installer"), "fallback ISO is a live session, no installer");
    }

    #[test]
    fn test_config_states_unproven_limit() {
        assert!(read(&config()).contains("UNPROVEN"));
    }

    #[test]
    fn test_no_second_base_in_live_build_files() {
        for path in live_build_files() {
            assert_eq!(second_base_in(&read(&path)), None, "second base codename in {}", path.display());
        }
    }

    #[test]
    fn test_config_shell_syntax() {
        let out = std::process::Command::new("sh").arg("-n").arg(config()).output().expect("sh failed");
        assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
    }

    #[test]
    fn test_covers_packages_txt_names() {
        let listed = name_list(&read(&package_list()));
        for name in name_list(&read(&os_inner().join("packages.txt"))) {
            assert!(listed.contains(&name), "packages.txt name {name} missing from live list");
        }
    }

    #[test]
    fn test_covers_spec_extras_as_real_package_names() {
        let listed = name_list(&read(&package_list()));
        for name in SPEC_EXTRA_PACKAGES {
            assert!(listed.contains(&name.to_string()), "{name} missing from live list");
        }
    }

    #[test]
    fn test_no_versions_pinned_here() {
        for name in name_list(&read(&package_list())) {
            assert!(!name.contains('='), "version pin {name} belongs to OS-010, not here");
        }
    }

    #[test]
    fn test_hook_enables_exactly_the_build_image_unit_set() {
        let text = read(&hook());
        for unit in ENABLED_UNITS {
            assert!(text.contains(unit), "hook missing {unit}");
        }
        assert!(text.contains(FIRSTBOOT_UNIT));
        assert!(text.contains("relay.target.wants"));
        assert!(text.contains("multi-user.target.wants"));
    }

    #[test]
    fn test_hook_enables_nothing_else_from_services() {
        let text = read(&hook());
        let code: Vec<&str> = text.lines().filter(|l| !l.trim_start().starts_with('#')).collect();
        let code = code.join("\n");
        for unit in NOT_ENABLED_UNITS {
            assert!(!code.contains(unit), "hook enables {unit}");
        }
    }

    #[test]
    fn test_no_unit_copy_lives_in_live_build_tree() {
        for path in live_build_files() {
            let s = path.to_string_lossy();
            assert!(!s.ends_with(".service") && !s.ends_with(".timer"), "unit copy in live-build tree: {}", path.display());
        }
    }

    #[test]
    fn test_hook_shell_syntax() {
        let out = std::process::Command::new("sh").arg("-n").arg(hook()).output().expect("sh failed");
        assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
    }

    #[test]
    fn test_wrapper_guards() {
        let text = read(&wrapper());
        assert!(text.starts_with("#!/bin/bash"));
        for needle in ["set -euo pipefail", "git -C", "status --porcelain", "id -u", "lb", "mksquashfs", "xorriso", "sha256sum"] {
            assert!(text.contains(needle), "wrapper missing {needle:?}");
        }
    }

    #[test]
    fn test_wrapper_stages_from_repo_sources_and_cleans_up() {
        let text = read(&wrapper());
        for needle in ["services/*.service", "services/*.timer", "services/relay.target", "firstboot/metaos-firstboot", "bin/metaos-boot-checklist", "bin/metaos-update", "config/includes.chroot", "trap cleanup EXIT"] {
            assert!(text.contains(needle), "wrapper missing {needle:?}");
        }
        assert!(std::fs::read_dir(os_inner().join("services")).unwrap().any(|e| e.unwrap().file_name().to_string_lossy().ends_with(".service")));
        assert!(std::fs::read_dir(os_inner().join("services")).unwrap().any(|e| e.unwrap().file_name().to_string_lossy().ends_with(".timer")));
        assert!(os_inner().join("services/relay.target").exists());
        assert!(os_inner().join("firstboot/metaos-firstboot").exists());
    }

    #[test]
    fn test_wrapper_build_steps_and_output_naming() {
        let text = read(&wrapper());
        for needle in ["lb clean", "lb config", "lb build", "live-image-amd64.hybrid.iso", "metaos-$DATE.iso", "sha256sum"] {
            assert!(text.contains(needle), "wrapper missing {needle:?}");
        }
    }

    #[test]
    fn test_wrapper_bash_syntax() {
        let out = std::process::Command::new("bash").arg("-n").arg(wrapper()).output().expect("bash failed");
        assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
    }

    #[test]
    fn test_readme_carries_os008_section_with_limit() {
        let text = read(&os_inner().join("README.md"));
        assert!(text.contains("Fallback pipeline (OS-008"));
        assert!(text.contains("UNPROVEN"));
    }

    #[test]
    fn test_base_carries_fallback_divergences() {
        let text = read(&os_inner().join("BASE.md"));
        assert!(text.contains("Fallback pipeline divergences (OS-008)"));
        assert!(text.contains("live ISO"));
        assert!(text.contains("does not install"));
    }

    #[test]
    fn test_new_doc_sections_carry_no_em_dash() {
        for rel in ["README.md", "BASE.md"] {
            let text = read(&os_inner().join(rel));
            let start = text.find("OS-008").expect("OS-008 section missing");
            assert!(!text[start..].contains('\u{2014}'), "em dash in OS-008 section of {rel}");
        }
    }
}
