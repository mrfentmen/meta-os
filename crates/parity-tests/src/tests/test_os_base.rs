//! T044 [B31] port of `os/tests/test_os_base.py` (same name roots).
//!
//! OS-005 frozen base: Debian 12 bookworm amd64, pinned by `build-all.sh`.
//! Pure file reads — no bus, no Redis, no network. Fully portable.
//!
//! TREE DRIFT (documented, not hidden): the Python names `os/BASE.md`,
//! `os/build-all.sh`, … — all absent since the `os/` fold (commit
//! `520a067`; the files live under `os/os/`). The Python test errors
//! `FileNotFoundError` on this tree; the port follows the folded tree
//! (`os/os/`) so the freeze is actually verified instead of erroring.

use std::path::PathBuf;

pub const CASES: &[&str] = &[
    "base doc names frozen base and source",
    "build script pins bookworm suite and mirror",
    "no second base in build files",
    "preseed names no suite or mirror",
    "base doc carries no em dash",
    "base doc states checksum limit honestly",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[];

/// Second-base codenames forbidden in build files (case-insensitive).
pub const FORBIDDEN_CODENAMES: &[&str] = &[
    "bullseye", "trixie", "forky", "sid", "ubuntu", "fedora", "centos", "rhel", "archlinux",
];

pub const BUILD_FILES: &[&str] = &[
    "build-all.sh",
    "build-image.sh",
    "preseed.cfg",
    "packages.txt",
    "grub-early.cfg",
    "README-FIRSTBOOT.md",
];

pub const BUILD_DIRS: &[&str] = &["services", "bin", "firstboot"];

pub fn os_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("os")
        .join("os")
}

pub fn read_os(rel: &str) -> String {
    std::fs::read_to_string(os_dir().join(rel)).unwrap_or_default()
}

pub fn build_file_list() -> Vec<String> {
    let mut found: Vec<String> = BUILD_FILES.iter().map(|s| s.to_string()).collect();
    for dir in BUILD_DIRS {
        if let Ok(rd) = std::fs::read_dir(os_dir().join(dir)) {
            let mut names: Vec<String> = rd
                .flatten()
                .filter(|e| e.file_type().map(|t| t.is_file()).unwrap_or(false))
                .map(|e| e.file_name().to_string_lossy().into_owned())
                .collect();
            names.sort();
            for n in names {
                found.push(format!("{dir}/{n}"));
            }
        }
    }
    found
}

/// Token match approximating `\b(codenames)\b` (case-insensitive).
pub fn second_base_in(text: &str) -> Option<String> {
    let lower = text.to_lowercase();
    let mut token = String::new();
    let mut found: Option<String> = None;
    let mut flush = |token: &mut String, found: &mut Option<String>| {
        if FORBIDDEN_CODENAMES.contains(&token.as_str()) {
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
    fn test_base_doc_names_the_frozen_base_and_source() {
        let text = read_os("BASE.md");
        for needle in [
            "Debian 12",
            "bookworm",
            "amd64",
            "http://deb.debian.org/debian",
            "build-all.sh",
        ] {
            assert!(text.contains(needle), "BASE.md missing {needle:?}");
        }
    }

    #[test]
    fn test_build_script_pins_bookworm_suite_and_mirror() {
        let text = read_os("build-all.sh");
        assert!(text.contains("bookworm"));
        assert!(text.contains("http://deb.debian.org/debian"));
    }

    #[test]
    fn test_no_second_base_in_build_files() {
        for rel in build_file_list() {
            let text = read_os(&rel);
            assert_eq!(second_base_in(&text), None, "{rel} names a second base");
        }
    }

    #[test]
    fn test_preseed_names_no_suite_or_mirror() {
        let text = read_os("preseed.cfg");
        assert!(!text.contains("bookworm"));
        assert!(!text.contains("http://"));
        assert_eq!(second_base_in(&text), None);
    }

    #[test]
    fn test_base_doc_carries_no_em_dash() {
        assert!(!read_os("BASE.md").contains('\u{2014}'));
    }

    #[test]
    fn test_base_doc_states_checksum_limit_honestly() {
        let text = read_os("BASE.md");
        for needle in ["no ISO", "OS-007", "metaos-<date>.img.sha256"] {
            assert!(text.contains(needle), "BASE.md missing {needle:?}");
        }
    }
}
