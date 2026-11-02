//! B011 — test-gap close for `carried`, the module with the fewest tests (3).
//!
//! `cli` has 16 tests and `git` has 4. These 13 cases bring `carried` to 16, but the point is
//! coverage, not the number: every structural promise the manifest makes gets one assertion,
//! and each assertion names the entry it fails on.

use os_boot::carried::{asset_path, source_path, CARRIED, CARRIED_COUNT};
use std::collections::HashSet;
use std::path::Path;

fn assert_manifest_shape() {
    assert_eq!(CARRIED.len(), CARRIED_COUNT, "manifest and count disagree");
    assert_eq!(CARRIED.len(), 47, "the documented manifest size");
}

#[test]
fn manifest_has_no_duplicate_entries() {
    assert_manifest_shape();
    let unique: HashSet<&str> = CARRIED.iter().copied().collect();
    assert_eq!(unique.len(), CARRIED.len(), "a duplicate entry exists");
}

#[test]
fn manifest_has_no_empty_entries() {
    for (i, entry) in CARRIED.iter().enumerate() {
        assert!(!entry.trim().is_empty(), "entry {i} is empty");
    }
}

#[test]
fn every_entry_is_a_relative_path_without_traversal() {
    for entry in CARRIED {
        assert!(!entry.starts_with('/'), "absolute entry: {entry}");
        assert!(
            !entry.split('/').any(|part| part == ".."),
            "traversal in entry: {entry}"
        );
        assert!(Path::new(entry).is_relative(), "not relative: {entry}");
    }
}

#[test]
fn source_path_resolves_under_the_repo_os_tree() {
    for entry in CARRIED {
        let p = source_path(entry);
        let text = p.to_string_lossy();
        assert!(
            text.contains("/os/os/"),
            "source path is not <repo>/os/<entry>: {text}"
        );
        assert!(p.ends_with(entry), "source path lost the entry: {text}");
    }
}

#[test]
fn asset_path_mirrors_the_entry_under_assets() {
    for entry in CARRIED {
        let p = asset_path(entry);
        let text = p.to_string_lossy();
        assert!(
            text.contains("/assets/"),
            "asset path is not <crate>/assets/<entry>: {text}"
        );
        assert!(p.ends_with(entry), "asset path lost the entry: {text}");
    }
}

#[test]
fn t153_group_has_ten_systemd_entries() {
    assert_manifest_shape();
    assert_eq!(CARRIED[0], "os/services/metaos-firstboot.service");
    assert_eq!(CARRIED[9], "os/services/relay-overseer.service");
}

#[test]
fn t154_group_has_ten_systemd_entries() {
    assert_manifest_shape();
    assert_eq!(CARRIED[10], "os/services/relay-overseer.timer");
    assert_eq!(CARRIED[19], "os/services/relay.target");
}

#[test]
fn t155_group_has_ten_docs_and_build_entries() {
    assert_manifest_shape();
    assert_eq!(CARRIED[20], "os/BASE.md");
    assert_eq!(CARRIED[29], "os/build-packer.sh");
}

#[test]
fn t156_group_has_nine_image_entries() {
    assert_manifest_shape();
    assert_eq!(CARRIED[30], "os/firstboot/metaos-firstboot");
    assert_eq!(CARRIED[38], "os/test-boot.sh");
}

#[test]
fn custos_group_has_four_entries() {
    assert_manifest_shape();
    assert_eq!(CARRIED[39], "os/METAOS_CUSTOS.md");
    assert_eq!(CARRIED[42], "os/services/metaos-custos.timer");
}

#[test]
fn loop_group_has_four_entries() {
    assert_manifest_shape();
    assert_eq!(CARRIED[43], "os/bin/metaos-loop");
    assert_eq!(CARRIED[46], "os/METAOS_LOOP.md");
}

#[test]
fn every_asset_is_a_regular_file() {
    for entry in CARRIED {
        let p = asset_path(entry);
        let meta = std::fs::metadata(&p)
            .unwrap_or_else(|e| panic!("asset missing for {entry}: {e}"));
        assert!(meta.is_file(), "asset is not a regular file: {entry}");
    }
}

#[test]
fn every_asset_is_non_empty() {
    for entry in CARRIED {
        let p = asset_path(entry);
        let meta = std::fs::metadata(&p)
            .unwrap_or_else(|e| panic!("asset missing for {entry}: {e}"));
        assert!(meta.len() > 0, "asset is empty: {entry}");
    }
}
