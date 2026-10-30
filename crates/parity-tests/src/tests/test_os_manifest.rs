//! T051 [B31] port of `os/tests/test_os_manifest.py` (same name roots).
//!
//! OS-010 package manifest: the frozen set, exactly. Pure file reads.
//!
//! TREE DRIFT (documented, not hidden): the Python names `os/packages.txt`,
//! `os/live-build/…`, `os/README.md` — the files live under the folded
//! tree (`os/os/…`).

use std::path::{Path, PathBuf};

pub const CASES: &[&str] = &[
    "packages txt is exactly the frozen set",
    "no duplicates and no version pins",
    "spec set present",
    "header states unpinned and owed diff",
    "openssh disabled by default noted",
    "live build list matches packages txt",
    "readme carries os010 section with limit",
    "no em dash in manifest files",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[];

/// The frozen set, in file order: 11 proven debootstrap packages, then
/// the spec set (python3-venv + five spec extras as real Debian names).
pub const EXPECTED_PACKAGES: &[&str] = &[
    "systemd", "systemd-sysv", "udev", "dbus", "linux-image-amd64",
    "initramfs-tools", "python3", "curl", "ca-certificates", "iproute2",
    "git", "python3-venv", "redis-tools", "chromium", "fonts-dejavu",
    "openssh-server", "qemu-guest-agent",
];
pub const SPEC_PACKAGES: &[&str] = &[
    "python3-venv", "redis-tools", "chromium", "fonts-dejavu",
    "openssh-server", "qemu-guest-agent",
];

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
}
fn os_inner() -> PathBuf {
    root().join("os").join("os")
}
fn manifest() -> PathBuf {
    os_inner().join("packages.txt")
}
fn package_list() -> PathBuf {
    os_inner().join("live-build/config/package-lists/metaos.list.chroot")
}
fn readme() -> PathBuf {
    os_inner().join("README.md")
}
fn read(p: &Path) -> String {
    std::fs::read_to_string(p).unwrap_or_default()
}
fn names(p: &Path) -> Vec<String> {
    read(p).lines().map(str::trim).filter(|l| !l.is_empty() && !l.starts_with('#')).map(str::to_string).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_packages_txt_is_exactly_the_frozen_set() {
        assert_eq!(names(&manifest()), EXPECTED_PACKAGES);
    }

    #[test]
    fn test_no_duplicates_and_no_version_pins() {
        let ns = names(&manifest());
        let mut seen = std::collections::HashSet::new();
        for n in &ns {
            assert!(seen.insert(n.clone()), "duplicate package entry in packages.txt: {n}");
            assert!(!n.contains('='), "version pin {n} is a guess until the dpkg -l diff lands");
        }
    }

    #[test]
    fn test_spec_set_present() {
        let ns = names(&manifest());
        for name in SPEC_PACKAGES {
            assert!(ns.iter().any(|n| n == name), "{name}");
        }
    }

    #[test]
    fn test_header_states_unpinned_and_owed_diff() {
        let text = read(&manifest());
        assert!(text.contains("NOT PINNED"));
        assert!(text.contains("dpkg -l"));
        let flat: Vec<String> = text.lines().map(|l| l.trim_start_matches(['#', ' ']).trim().to_string()).collect();
        assert!(flat.join(" ").contains("owed to a build host run"));
    }

    #[test]
    fn test_openssh_disabled_by_default_noted() {
        assert!(read(&manifest()).contains("disabled by default"));
    }

    #[test]
    fn test_live_build_list_matches_packages_txt() {
        let a: std::collections::HashSet<_> = names(&package_list()).into_iter().collect();
        let b: std::collections::HashSet<_> = names(&manifest()).into_iter().collect();
        assert_eq!(a, b);
    }

    #[test]
    fn test_readme_carries_os010_section_with_limit() {
        let text = read(&readme());
        assert!(text.contains("## Package manifest (OS-010, first light)"));
        assert!(text.contains("dpkg -l"));
        assert!(text.contains("UNPROVEN"));
    }

    #[test]
    fn test_no_em_dash_in_manifest_files() {
        for p in [manifest(), package_list()] {
            assert!(!read(&p).contains('\u{2014}'), "{} carries an em dash", p.display());
        }
    }
}
