//! T039 [B31] port of `os/tests/test_os065_skills_loader.py` (same name roots).
//!
//! OS-065 skills loader. The 6 image-route pins run for real (file reads +
//! `bash -n` + em-dash scan). The 15 loader-behavior cases need the
//! `intel.skills_loader` module port — absent on main (intel crate is
//! still the B00 skeleton, Hana's B11 unmerged) — so they are recorded
//! exclusion-blocked with the exact missing subject, never dropped.
//!
//! TREE DRIFT (documented, not hidden): the Python names `os/build-image.sh`,
//! `os/build-live.sh`, `os/packer/metaos.pkr.hcl`, live hook under
//! `os/live-build/…` — the files live under the folded tree (`os/os/…`).
//! `os/intel/…` was never folded.

use std::path::{Path, PathBuf};

pub const CASES: &[&str] = &[
    "list fixture collection",
    "mount selected only",
    "manifest hashes match files",
    "verify tampered file names skill",
    "verify extra dir is unlisted mount",
    "verify missing manifest",
    "folder without skill md refused",
    "unknown name refused",
    "duplicate name refused",
    "traversal names refused",
    "skill dir symlink escape refused",
    "file symlink escape refused",
    "mount over existing refused",
    "empty mount writes empty manifest",
    "cli list mount verify",
    "build image bakes collection root",
    "build live stages collection root",
    "packer bakes collection root",
    "live hook owns collection root",
    "build scripts parse",
    "no em dash in new files",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[
    "list fixture collection (needs intel.skills_loader port, absent on main)",
    "mount selected only (needs intel.skills_loader port, absent on main)",
    "manifest hashes match files (needs intel.skills_loader port, absent on main)",
    "verify tampered file names skill (needs intel.skills_loader port, absent on main)",
    "verify extra dir is unlisted mount (needs intel.skills_loader port, absent on main)",
    "verify missing manifest (needs intel.skills_loader port, absent on main)",
    "folder without skill md refused (needs intel.skills_loader port, absent on main)",
    "unknown name refused (needs intel.skills_loader port, absent on main)",
    "duplicate name refused (needs intel.skills_loader port, absent on main)",
    "traversal names refused (needs intel.skills_loader port, absent on main)",
    "skill dir symlink escape refused (needs intel.skills_loader port, absent on main)",
    "file symlink escape refused (needs intel.skills_loader port, absent on main)",
    "mount over existing refused (needs intel.skills_loader port, absent on main)",
    "empty mount writes empty manifest (needs intel.skills_loader port, absent on main)",
    "cli list mount verify (needs intel.skills_loader port + CLI, absent on main)",
];

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
}
fn os_inner() -> PathBuf {
    root().join("os").join("os")
}
fn read(p: &Path) -> String {
    std::fs::read_to_string(p).unwrap_or_default()
}
fn fixtures() -> PathBuf {
    root().join("os").join("intel").join("examples").join("skills")
}
fn skills_loader_py() -> PathBuf {
    root().join("os").join("intel").join("skills_loader.py")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_build_image_bakes_collection_root() {
        let text = read(&os_inner().join("build-image.sh"));
        for needle in ["2e. OS-065", "/var/lib/metaos/skills", ".metaos-skills-root", "chown relay:relay /var/lib/metaos/skills"] {
            assert!(text.contains(needle), "build-image.sh missing {needle:?}");
        }
    }

    #[test]
    fn test_build_live_stages_collection_root() {
        let text = read(&os_inner().join("build-live.sh"));
        for needle in ["OS-065", "/var/lib/metaos/skills", ".metaos-skills-root"] {
            assert!(text.contains(needle), "build-live.sh missing {needle:?}");
        }
    }

    #[test]
    fn test_packer_bakes_collection_root() {
        let text = read(&os_inner().join("packer").join("metaos.pkr.hcl"));
        for needle in ["/var/lib/metaos/skills", ".metaos-skills-root", "chown -R relay:relay /var/lib/metaos/skills"] {
            assert!(text.contains(needle), "packer template missing {needle:?}");
        }
    }

    #[test]
    fn test_live_hook_owns_collection_root() {
        let text = read(&os_inner().join("live-build/config/hooks/live/0900-metaos-services.hook.chroot"));
        for needle in ["/var/lib/metaos/skills", "chown relay:relay /var/lib/metaos/skills"] {
            assert!(text.contains(needle), "live hook missing {needle:?}");
        }
    }

    #[test]
    fn test_build_scripts_parse() {
        for rel in ["build-image.sh", "build-live.sh"] {
            let out = std::process::Command::new("bash").arg("-n").arg(os_inner().join(rel)).output().expect("bash failed to spawn");
            assert!(out.status.success(), "{rel}: {}", String::from_utf8_lossy(&out.stderr));
        }
    }

    #[test]
    fn test_no_em_dash_in_new_files() {
        let mut paths = vec![skills_loader_py()];
        for fx in ["fixture-ledger/SKILL.md", "fixture-brief/SKILL.md"] {
            paths.push(fixtures().join(fx));
        }
        for p in &paths {
            assert!(p.is_file(), "missing {}", p.display());
            assert!(!read(p).contains('\u{2014}'), "{} carries an em dash", p.display());
        }
    }
}
