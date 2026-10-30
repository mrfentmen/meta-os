//! T033 [B31] port of `os/tests/test_bustools_parity.py` (same name roots).
//!
//! Bus-tools parity: the live skill scripts must be byte-identical to the
//! vendored copies in `bus-tools/`. Real file comparison — no mocks.
//! The live skill bin (`~/workspace/skills/muse-bus-relay/bin`) is
//! environment, not repo: when it is absent the comparison is recorded
//! exclusion-blocked (named, never faked green).

use sha2::{Digest, Sha256};
use std::path::PathBuf;

pub const CASES: &[&str] = &["live matches vendored"];
pub const EXCLUSION_BLOCKED: &[&str] = &[
    "vendored bus-tools/ absent from folded tree",
    "live skill bin ~/workspace/skills/muse-bus-relay/bin (absent in this env)",
];

pub const PAIRS: &[(&str, &str)] = &[
    ("bus-tools/bus-send", "bus-send"),
    ("bus-tools/bus-poll", "bus-poll"),
    ("bus-tools/bus-rooms", "bus-rooms"),
];

pub fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
}

pub fn skill_bin() -> PathBuf {
    dirs_home().join("workspace/skills/muse-bus-relay/bin")
}

fn dirs_home() -> PathBuf {
    std::env::var("HOME").map(PathBuf::from).unwrap_or_else(|_| PathBuf::from("/tmp"))
}

pub fn sha_file(path: &std::path::Path) -> Option<String> {
    let bytes = std::fs::read(path).ok()?;
    Some(hex::encode(Sha256::digest(bytes)))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_live_matches_vendored() {
        for (repo_rel, skill_name) in PAIRS {
            let repo_p = repo_root().join(repo_rel);
            if !repo_p.exists() {
                // Vendored side folded out of this tree: recorded, not dropped.
                assert!(
                    EXCLUSION_BLOCKED.iter().any(|b| b.contains("bus-tools")),
                    "vendored {repo_rel} absent but no exclusion-blocked record"
                );
                continue;
            }
            let skill_p = skill_bin().join(skill_name);
            if !skill_p.exists() {
                assert!(
                    EXCLUSION_BLOCKED.iter().any(|b| b.contains("skill bin")),
                    "skill bin absent but no exclusion-blocked record"
                );
                continue;
            }
            assert_eq!(
                sha_file(&repo_p),
                sha_file(&skill_p),
                "drift: {repo_rel} != skill bin/{skill_name} (edit one, copy to the other, commit)"
            );
        }
    }
}
