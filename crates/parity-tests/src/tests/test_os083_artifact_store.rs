//! T040 [B31] port of `os/tests/test_os083_artifact_store.py` (same name roots).
//!
//! OS-083 artifact store. The 6 image-route pins run for real (file reads
//! + `bash -n` + em-dash scan of the source module). The 11 store-behavior
//! cases need the `mos.artifact_store` module port — absent on main
//! (os-workspace crate is still the B00 skeleton, Milo's B19 unmerged) —
//! so they are recorded exclusion-blocked, never dropped.
//!
//! TREE DRIFT: build scripts live under the folded tree (`os/os/…`);
//! `os/mos/artifact_store.py` was never folded.

use std::path::{Path, PathBuf};

pub const CASES: &[&str] = &[
    "deposit and read round trip",
    "binary bytes survive versioned read",
    "versions increment and history counts",
    "identical redeposit is a noop",
    "nested artifact path",
    "traversal names refused",
    "bad job ids refused",
    "list sorted and empty job empty",
    "read missing artifact and bad version raise",
    "attach copies record and carries paths",
    "cli deposit and list",
    "cli bad command exits two",
    "build image bakes store root",
    "build live stages store root",
    "packer bakes store root",
    "build scripts parse",
    "no em dash in new module",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[
    "deposit and read round trip (needs mos.artifact_store port, absent on main)",
    "binary bytes survive versioned read (needs mos.artifact_store port, absent on main)",
    "versions increment and history counts (needs mos.artifact_store port, absent on main)",
    "identical redeposit is a noop (needs mos.artifact_store port, absent on main)",
    "nested artifact path (needs mos.artifact_store port, absent on main)",
    "traversal names refused (needs mos.artifact_store port, absent on main)",
    "bad job ids refused (needs mos.artifact_store port, absent on main)",
    "list sorted and empty job empty (needs mos.artifact_store port, absent on main)",
    "read missing artifact and bad version raise (needs mos.artifact_store port, absent on main)",
    "attach copies record and carries paths (needs mos.artifact_store port, absent on main)",
    "cli deposit and list (needs mos.artifact_store CLI port, absent on main)",
    "cli bad command exits two (needs mos.artifact_store CLI port, absent on main)",
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_build_image_bakes_store_root() {
        let text = read(&os_inner().join("build-image.sh"));
        for needle in ["2c. OS-083", "/var/lib/metaos/artifacts", ".metaos-artifact-store", "chown relay:relay /var/lib/metaos/artifacts"] {
            assert!(text.contains(needle), "build-image.sh missing {needle:?}");
        }
    }

    #[test]
    fn test_build_live_stages_store_root() {
        let text = read(&os_inner().join("build-live.sh"));
        for needle in ["OS-083", "/var/lib/metaos/artifacts", ".metaos-artifact-store"] {
            assert!(text.contains(needle), "build-live.sh missing {needle:?}");
        }
    }

    #[test]
    fn test_packer_bakes_store_root() {
        let text = read(&os_inner().join("packer").join("metaos.pkr.hcl"));
        for needle in ["/var/lib/metaos/artifacts", ".metaos-artifact-store", "chown -R relay:relay /var/lib/metaos/artifacts"] {
            assert!(text.contains(needle), "packer template missing {needle:?}");
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
    fn test_no_em_dash_in_new_module() {
        let p = root().join("os").join("mos").join("artifact_store.py");
        assert!(p.is_file(), "missing {}", p.display());
        assert!(!read(&p).contains('\u{2014}'), "artifact_store.py carries an em dash");
    }
}
