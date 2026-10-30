//! T055 [B31] port of `os/tests/test_os_stackbake.py` (same name roots).
//!
//! OS-011 stack bake: the build-image bake script pins, README limits,
//! no venv step, no committed requirements files. File reads + `bash -n`.
//! No image is built here.
//!
//! TREE DRIFT: the Python names `os/build-image.sh`, `os/README.md` —
//! the files live under the folded tree (`os/os/…`).

use std::path::{Path, PathBuf};

pub const CASES: &[&str] = &[
    "script bash syntax",
    "refuses dirty checkout",
    "pinned commit captured from checkout head",
    "dirty guard runs before any image write",
    "source commit stamp file written from variable",
    "version stamp carries source commit line",
    "no hardcoded commit sha in script",
    "payload still excludes git",
    "stamp written after git removal",
    "readme has os011 section with limits",
    "readme states no venv step and why",
    "readme has no em dash",
    "no requirements file exists",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[];

/// 40-hex-word detector (`\b[0-9a-f]{40}\b`).
fn sha40_in(text: &str) -> Vec<String> {
    let mut hits = vec![];
    for line in text.lines() {
        let lower = line.to_lowercase();
        let mut token = String::new();
        let mut flush = |token: &mut String| {
            if token.len() == 40 && token.bytes().all(|b| b.is_ascii_hexdigit()) {
                hits.push(line.to_string());
            }
            token.clear();
        };
        for c in lower.chars().chain(std::iter::once(' ')) {
            if c.is_ascii_alphanumeric() {
                token.push(c);
            } else {
                flush(&mut token);
            }
        }
    }
    hits
}

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
}
fn os_inner() -> PathBuf {
    root().join("os").join("os")
}
fn read(p: &Path) -> String {
    std::fs::read_to_string(p).unwrap_or_default()
}
fn script() -> PathBuf {
    os_inner().join("build-image.sh")
}
fn readme() -> PathBuf {
    os_inner().join("README.md")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_script_bash_syntax() {
        let out = std::process::Command::new("bash").arg("-n").arg(script()).output().expect("bash failed");
        assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
    }

    #[test]
    fn test_refuses_dirty_checkout() {
        let s = read(&script());
        assert!(s.contains("git -C \"$PAYLOAD_SRC\" status --porcelain"));
        assert!(s.contains("refusing: checkout is dirty"));
    }

    #[test]
    fn test_pinned_commit_captured_from_checkout_head() {
        let s = read(&script());
        assert!(s.contains("PINNED_COMMIT=\"$(git -C \"$PAYLOAD_SRC\" rev-parse HEAD)\""));
        assert!(s.contains("refusing: no pinned commit resolved"));
    }

    #[test]
    fn test_dirty_guard_runs_before_any_image_write() {
        let s = read(&script());
        let guard = s.find("refusing: checkout is dirty").expect("guard missing");
        let first_write = s.find("> \"$ROOTFS/etc/hostname\"").expect("hostname write missing");
        assert!(guard < first_write);
    }

    #[test]
    fn test_source_commit_stamp_file_written_from_variable() {
        let s = read(&script());
        assert!(s.contains("echo \"$PINNED_COMMIT\" > \"$ROOTFS/opt/relay/.metaos-source-commit\""));
    }

    #[test]
    fn test_version_stamp_carries_source_commit_line() {
        let s = read(&script());
        assert!(s.contains("echo \"source-commit $PINNED_COMMIT\" >> \"$ROOTFS/etc/metaos-version\""));
    }

    #[test]
    fn test_no_hardcoded_commit_sha_in_script() {
        assert_eq!(sha40_in(&read(&script())), Vec::<String>::new());
    }

    #[test]
    fn test_payload_still_excludes_git() {
        let s = read(&script());
        assert!(s.contains("--exclude='.git'"));
        assert!(s.contains("rm -rf \"$ROOTFS/opt/relay/.git\""));
    }

    #[test]
    fn test_stamp_written_after_git_removal() {
        let s = read(&script());
        let removal = s.find("rm -rf \"$ROOTFS/opt/relay/.git\"").expect("removal missing");
        let stamp = s.find("echo \"$PINNED_COMMIT\" > \"$ROOTFS/opt/relay/.metaos-source-commit\"").expect("stamp missing");
        assert!(removal < stamp);
    }

    #[test]
    fn test_readme_has_os011_section_with_limits() {
        let text = read(&readme());
        for needle in ["OS-011", ".metaos-source-commit", "source-commit <sha>", "UNPROVEN", "Packer route"] {
            assert!(text.contains(needle), "README missing {needle:?}");
        }
    }

    #[test]
    fn test_readme_states_no_venv_step_and_why() {
        let text = read(&readme());
        assert!(text.contains("no venv step"));
        assert!(text.contains("standard library"));
    }

    #[test]
    fn test_readme_has_no_em_dash() {
        assert!(!read(&readme()).contains('\u{2014}'));
    }

    #[test]
    fn test_no_requirements_file_exists() {
        for name in ["requirements.txt", "requirements-dev.txt"] {
            assert!(!root().join(name).exists(), "{name} exists but the bake has no install step for it");
        }
    }
}
