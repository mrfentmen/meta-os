//! OS-078 bake pins (`os/tests/test_os078_memory.py`,
//! `MemoryBakeTest`): the memory service's image/boot wiring.
//!
//! The unit, target, build scripts, hook, packer template, README,
//! spec, and secrets-sweep script all live outside this crate
//! (B23 owns services/build, B28 owns docs, B30 owns the plan).
//! This module pins the memory-side contract strings the bake
//! tests assert and verifies the live files in the same checkout,
//! so a drift in either direction fails the suite.

/// Paths (relative to the `os/` subtree root) the bake pins read.
pub const UNIT: &str = "os/services/relay-memory.service";
pub const TARGET: &str = "os/services/relay.target";
pub const BUILD_IMAGE: &str = "os/build-image.sh";
pub const BUILD_LIVE: &str = "os/build-live.sh";
pub const HOOK: &str = "os/live-build/config/hooks/live/0900-metaos-services.hook.chroot";
pub const PACKER: &str = "os/packer/metaos.pkr.hcl";
pub const README: &str = "os/README.md";
pub const SPEC: &str = "plan/META_OS.md";
pub const SWEEP: &str = "os/bin/metaos-secrets-sweep";

/// The unit name every route must enable.
pub const MEMORY_UNIT: &str = "relay-memory.service";

/// Pinned memory-store strings (must appear in the named files).
pub const STORE_ROOT: &str = "/var/lib/metaos/memory";
pub const STORE_MARKER: &str = ".metaos-memory-store";
pub const UNIT_EXEC: &str =
    "ExecStart=/usr/bin/python3 /opt/relay/mos/memory.py ensure /var/lib/metaos/memory";

/// The `for u in` enablement loop line of a build script: the
/// script enables units by looping, and the memory unit must be
/// named on that line.
pub fn enablement_loop(text: &str) -> &str {
    for line in text.lines() {
        if line.contains("for u in") {
            return line;
        }
    }
    ""
}

/// Section of `text` between two markers (Python test helper).
pub fn section<'a>(text: &'a str, start_marker: &str, end_marker: &str) -> &'a str {
    let start = text.find(start_marker).map(|i| i + start_marker.len());
    match start {
        None => "",
        Some(s) => match text[s..].find(end_marker) {
            Some(e) => &text[s..s + e],
            None => &text[s..],
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn workspace_root() -> PathBuf {
        // The `os/` subtree root: the directory holding `services/`,
        // `tests/`, `mos/`, `intel/`, `os/`, `plan/`, `bin/` — the
        // same directory the Python suite resolves as
        // dirname(dirname(test_file)).
        let manifest = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
        manifest
            .join("..")
            .join("..")
            .join("os")
            .canonicalize()
            .unwrap_or_else(|_| manifest.join("..").join("..").join("os"))
    }

    fn read(rel: &str) -> String {
        std::fs::read_to_string(workspace_root().join(rel))
            .unwrap_or_else(|e| panic!("cannot read {rel}: {e}"))
    }

    #[test]
    fn unit_shape() {
        let text = read(UNIT);
        assert!(text.contains("WantedBy=relay.target"), "unit wants target");
        assert!(text.contains("Type=oneshot"));
        assert!(text.contains("RemainAfterExit=yes"));
        assert!(text.contains("User=relay"));
        assert!(text.contains(UNIT_EXEC), "ensure exec line");
        assert!(text.contains("PartOf=relay.target"));
    }

    #[test]
    fn target_wants_unit() {
        assert!(read(TARGET).contains(MEMORY_UNIT));
    }

    #[test]
    fn build_image_bakes_root_and_enables_unit() {
        let text = read(BUILD_IMAGE);
        assert!(text.contains("mkdir -p \"$ROOTFS/var/lib/metaos/memory\""));
        assert!(text.contains(STORE_MARKER));
        assert!(text.contains("chroot \"$ROOTFS\" chown relay:relay /var/lib/metaos/memory"));
        assert!(enablement_loop(&text).contains(MEMORY_UNIT));
    }

    #[test]
    fn build_live_stages_root() {
        let text = read(BUILD_LIVE);
        assert!(text.contains("mkdir -p \"$STAGE/var/lib/metaos/memory\""));
        assert!(text.contains(STORE_MARKER));
    }

    #[test]
    fn hook_enables_unit_and_chowns_root() {
        let text = read(HOOK);
        assert!(enablement_loop(&text).contains(MEMORY_UNIT));
        assert!(text.contains("mkdir -p /var/lib/metaos/memory"));
        assert!(text.contains("chown relay:relay /var/lib/metaos/memory"));
    }

    #[test]
    fn packer_bakes_root_and_enables_unit() {
        let text = read(PACKER);
        assert!(text.contains("mkdir -p /var/lib/metaos/memory"));
        assert!(text.contains(STORE_MARKER));
        assert!(text.contains("chown -R relay:relay /var/lib/metaos/memory"));
        assert!(enablement_loop(&text).contains(MEMORY_UNIT));
    }

    #[test]
    fn docs_record_first_light_without_em_dash() {
        let readme = read(README);
        assert!(readme.contains("Memory service (OS-078, first light)"));
        let sec = section(
            &readme,
            "## Memory service (OS-078, first light)",
            "## Two routes, stated plainly",
        );
        assert!(!sec.contains('—'), "no em dash in section");
        let spec = read(SPEC);
        assert!(spec.contains("Memory service (OS-078, Pax, first light)"));
        let note = section(
            &spec,
            "**Memory service (OS-078, Pax, first light):**",
            "### 2. Identity and capabilities",
        );
        assert!(!note.contains('—'), "no em dash in note");
    }

    #[test]
    fn build_scripts_bash_syntax_clean() {
        for path in [BUILD_IMAGE, BUILD_LIVE] {
            let full = workspace_root().join(path);
            let proc = std::process::Command::new("bash")
                .arg("-n")
                .arg(&full)
                .output()
                .expect("bash must exist for syntax check");
            assert!(
                proc.status.success(),
                "{path}: {}",
                String::from_utf8_lossy(&proc.stderr)
            );
        }
        let full = workspace_root().join(HOOK);
        let proc = std::process::Command::new("sh")
            .arg("-n")
            .arg(&full)
            .output()
            .expect("sh must exist for syntax check");
        assert!(proc.status.success());
    }

    #[test]
    fn memory_root_sweeps_clean_and_secret_value_flagged() {
        let tmp = std::env::temp_dir().join(format!(
            "metaos-memory-sweep-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .subsec_nanos()
        ));
        let mem = tmp.join("var/lib/metaos/memory");
        std::fs::create_dir_all(&mem).unwrap();
        std::fs::write(mem.join(STORE_MARKER), "memory-store-root /var/lib/metaos/memory\n").unwrap();
        let sweep = workspace_root().join(SWEEP);
        let clean = std::process::Command::new("sh")
            .arg(&sweep)
            .arg(&tmp)
            .output()
            .expect("sh must run the sweep");
        assert_eq!(clean.status.code(), Some(0), "{}", String::from_utf8_lossy(&clean.stdout));
        let journal_dir = mem.join("agents/pax");
        std::fs::create_dir_all(&journal_dir).unwrap();
        std::fs::write(
            journal_dir.join("journal.jsonl"),
            "{\"key\": \"k.md\", \"version\": 1, \"author\": \"pax\", \"ts\": 1, \"text\": \"UPSTASH_TOKEN=planted\"}\n",
        )
        .unwrap();
        let dirty = std::process::Command::new("sh")
            .arg(&sweep)
            .arg(&tmp)
            .output()
            .expect("sh must run the sweep");
        assert_eq!(dirty.status.code(), Some(1));
        assert!(
            String::from_utf8_lossy(&dirty.stdout).contains("FINDING"),
            "{}",
            String::from_utf8_lossy(&dirty.stdout)
        );
        std::fs::remove_dir_all(&tmp).ok();
    }
}
