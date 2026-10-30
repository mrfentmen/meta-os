//! Carried deployment assets (T153–T156): the 39 `os/os/` files are
//! carried byte-identical under `crates/os-boot/assets/os/`, mirroring
//! the source layout. They are deployment assets (systemd units, shell
//! scripts, image-build config, docs), not Rust code — never rewritten,
//! never "ported" by rewriting them.
//!
//! Layout rule: entry `os/<rest>` means source file
//! `<repo>/os/<rest>` (the folded OS tree) and asset file
//! `<crate>/assets/<rest-with-os-prefix>` — i.e. the asset path is
//! `assets/os/<rest>` where `<rest>` is the path under the folded
//! `os/` tree's `os/` subtree. In the manifest below each entry is the
//! path under the folded tree (`os/services/...`, `os/bin/...`, ...),
//! so source = `<repo>/os/<entry>` and asset =
//! `<crate>/assets/<entry>`.
//!
//! Mode note: the folded tree records every one of these files as
//! mode 100644 in git (the fold normalized modes), so byte-identity is
//! the criterion; no exec-bit assertion is made (the working tree
//! itself checks them out 660, which would make a mode test
//! environment-fragile).

/// Carried files, grouped by SUPER_PROMPT task:
/// T153 (systemd services, first half), T154 (services, second half),
/// T155 (docs, bin, build scripts), T156 (firstboot, grub, live-build,
/// packages, packer, preseed, test-boot).
///
/// Each entry is the path under the folded `os/` tree.
pub const CARRIED: &[&str] = &[
    // T153 — systemd deployment assets (first half).
    "os/services/metaos-firstboot.service",
    "os/services/relay-brief.service",
    "os/services/relay-bus.service",
    "os/services/relay-dashboard.service",
    "os/services/relay-driver@.service",
    "os/services/relay-drivers.slice",
    "os/services/relay-jobs.service",
    "os/services/relay-mcp-gateway.service",
    "os/services/relay-memory.service",
    "os/services/relay-overseer.service",
    // T154 — systemd deployment assets (second half).
    "os/services/relay-overseer.timer",
    "os/services/relay-ready.service",
    "os/services/relay-uplink.service",
    "os/services/relay-watchdog.service",
    "os/services/relay-watchdog.service.d/demo-thresholds.conf",
    "os/services/relay-watchman-watch.service",
    "os/services/relay-watchman.service",
    "os/services/relay-worker@.service",
    "os/services/relay-workers.slice",
    "os/services/relay.target",
    // T155 — docs, bin scripts, build scripts.
    "os/BASE.md",
    "os/README-FIRSTBOOT.md",
    "os/README.md",
    "os/bin/metaos-boot-checklist",
    "os/bin/metaos-secrets-sweep",
    "os/bin/metaos-update",
    "os/build-all.sh",
    "os/build-image.sh",
    "os/build-live.sh",
    "os/build-packer.sh",
    // T156 — firstboot, grub, live-build, packages, packer, preseed, test-boot.
    "os/firstboot/metaos-firstboot",
    "os/grub-early.cfg",
    "os/live-build/auto/config",
    "os/live-build/config/hooks/live/0900-metaos-services.hook.chroot",
    "os/live-build/config/package-lists/metaos.list.chroot",
    "os/packages.txt",
    "os/packer/metaos.pkr.hcl",
    "os/preseed.cfg",
    "os/test-boot.sh",
];

/// Number of carried files (T153 10 + T154 10 + T155 10 + T156 9).
pub const CARRIED_COUNT: usize = 39;

/// Resolve the source path for a manifest entry (repo `<repo>/os/<entry>`).
pub fn source_path(entry: &str) -> std::path::PathBuf {
    let manifest = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    manifest.join("../../os").join(entry)
}

/// Resolve the asset path for a manifest entry (`<crate>/assets/<entry>`).
pub fn asset_path(entry: &str) -> std::path::PathBuf {
    let manifest = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    manifest.join("assets").join(entry)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_carried_manifest_count() {
        assert_eq!(CARRIED.len(), CARRIED_COUNT);
    }

    #[test]
    fn test_carried_files_byte_identical() {
        // T153–T156 done-when: every file inventoried and byte-identical
        // to its source. One assertion per file so a failure names it.
        for entry in CARRIED {
            let src = source_path(entry);
            let dst = asset_path(entry);
            let src_bytes = std::fs::read(&src)
                .unwrap_or_else(|e| panic!("source missing for {entry}: {e}"));
            let dst_bytes = std::fs::read(&dst)
                .unwrap_or_else(|e| panic!("asset missing for {entry}: {e}"));
            assert_eq!(
                src_bytes, dst_bytes,
                "carried file differs from source: {entry}"
            );
        }
    }

    #[test]
    fn test_carried_units_look_like_units() {
        // Spot sanity on the carried systemd units: they carry the
        // section headers a unit file must have (content check only;
        // byte-identity above is the binding criterion).
        for entry in CARRIED {
            if entry.ends_with(".service") || entry.ends_with(".slice") || entry.ends_with(".target") || entry.ends_with(".timer") {
                let text = std::fs::read_to_string(asset_path(entry)).unwrap();
                assert!(
                    text.contains("[Unit]"),
                    "carried unit without [Unit] section: {entry}"
                );
            }
        }
    }
}
