//! T056 [B31] port of `os/tests/test_os_target_unit.py` (same name roots).
//!
//! OS-016 boot target + ready gate: file pins only, no live systemd.
//!
//! TREE DRIFT (documented, not hidden): the Python names `os/services/…`,
//! `os/bin/…`, `os/build-image.sh`, `os/packer/…`, `os/README.md`,
//! `plan/META_OS.md` — units, scripts and packer config live under the
//! folded tree (`os/os/…`); the spec record in `os/plan/META_OS.md`.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

pub const CASES: &[&str] = &[
    "target wants full os016 set",
    "target keeps preexisting base ordering",
    "target enabled identically on all image routes",
    "target names worker template exclusion",
    "ready orders after every checked unit",
    "ready does not wait on the brief",
    "ready is oneshot checklist under relay target",
    "gate probes the gateable set",
    "marker write is guarded and block is reported",
    "gate documents the oneshot and timer limits",
    "no secret on any command line",
    "readme carries os016 section with exclusions",
    "spec carries os016 record",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[];

pub const TARGET_SET: &[&str] = &[
    "relay-dashboard.service",
    "relay-bus.service",
    "relay-jobs.service",
    "relay-overseer.timer",
    "relay-ready.service",
    "relay-watchdog.service",
    "relay-brief.service",
    "relay-watchman.service",
    "metaos-firstboot.service",
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
fn target() -> PathBuf {
    os_inner().join("services").join("relay.target")
}
fn ready() -> PathBuf {
    os_inner().join("services").join("relay-ready.service")
}
fn checklist() -> PathBuf {
    os_inner().join("bin").join("metaos-boot-checklist")
}
fn build_image() -> PathBuf {
    os_inner().join("build-image.sh")
}
fn packer() -> PathBuf {
    os_inner().join("packer").join("metaos.pkr.hcl")
}
fn hook() -> PathBuf {
    os_inner().join("live-build/config/hooks/live/0900-metaos-services.hook.chroot")
}
fn readme() -> PathBuf {
    os_inner().join("README.md")
}
fn spec() -> PathBuf {
    root().join("os").join("plan").join("META_OS.md")
}

fn sections(text: &str) -> HashMap<String, HashMap<String, Vec<String>>> {
    let mut out: HashMap<String, HashMap<String, Vec<String>>> = HashMap::new();
    let mut section: Option<String> = None;
    for raw in text.lines() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        if line.starts_with('[') && line.ends_with(']') {
            section = Some(line[1..line.len() - 1].to_string());
            out.entry(section.clone().unwrap()).or_default();
            continue;
        }
        if let (Some(s), Some(eq)) = (section.clone(), line.find('=')) {
            let (k, v) = line.split_at(eq);
            out.entry(s).or_default().entry(k.trim().to_string()).or_default().push(v[1..].trim().to_string());
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_target_wants_full_os016_set() {
        let unit = &sections(&read(&target()))["Unit"];
        let wants = unit.get("Wants").cloned().unwrap_or_default().join(" ");
        for member in TARGET_SET {
            assert!(wants.contains(member), "{member}");
        }
    }

    #[test]
    fn test_target_keeps_preexisting_base_ordering() {
        let unit = &sections(&read(&target()))["Unit"];
        let get = |k: &str| unit.get(k).cloned().unwrap_or_default().join(" ");
        assert!(get("Wants").contains("multi-user.target"));
        assert!(get("After").contains("multi-user.target"));
        assert!(get("After").contains("network-online.target"));
    }

    #[test]
    fn test_target_enabled_identically_on_all_image_routes() {
        for path in [build_image(), packer(), hook()] {
            let text = read(&path);
            for member in ["relay-watchdog.service", "relay-brief.service", "relay-watchman.service"] {
                assert!(text.contains(member), "{} missing {member}", path.display());
            }
        }
    }

    #[test]
    fn test_target_names_worker_template_exclusion() {
        let text = read(&target());
        assert!(text.contains("relay-worker@.service"));
        let unit = &sections(&text)["Unit"];
        let wants = unit.get("Wants").cloned().unwrap_or_default().join(" ");
        assert!(!wants.contains("relay-worker@.service"));
    }

    #[test]
    fn test_ready_orders_after_every_checked_unit() {
        let unit = &sections(&read(&ready()))["Unit"];
        let after = unit.get("After").cloned().unwrap_or_default().join(" ");
        for dep in ["relay-dashboard.service", "relay-bus.service", "relay-jobs.service", "relay-overseer.timer", "relay-watchdog.service", "metaos-firstboot.service"] {
            assert!(after.contains(dep), "{dep}");
        }
    }

    #[test]
    fn test_ready_does_not_wait_on_the_brief() {
        let unit = &sections(&read(&ready()))["Unit"];
        let after = unit.get("After").cloned().unwrap_or_default().join(" ");
        assert!(!after.contains("relay-brief.service"));
    }

    #[test]
    fn test_ready_is_oneshot_checklist_under_relay_target() {
        let parsed = sections(&read(&ready()));
        assert_eq!(parsed["Service"].get("Type").cloned().unwrap_or_default(), ["oneshot"]);
        assert_eq!(parsed["Service"].get("RemainAfterExit").cloned().unwrap_or_default(), ["yes"]);
        assert_eq!(parsed["Service"].get("ExecStart").cloned().unwrap_or_default(), ["/usr/local/bin/metaos-boot-checklist"]);
        assert_eq!(parsed["Unit"].get("PartOf").cloned().unwrap_or_default(), ["relay.target"]);
        assert_eq!(parsed["Install"].get("WantedBy").cloned().unwrap_or_default(), ["relay.target"]);
    }

    #[test]
    fn test_gate_probes_the_gateable_set() {
        let text = read(&checklist());
        for unit in ["relay-dashboard.service", "relay-watchdog.service", "relay-bus.service", "relay-overseer.timer"] {
            assert!(text.contains(unit), "{unit}");
        }
        assert!(text.contains("systemctl show"));
        assert!(text.contains("relay-jobs.service"));
    }

    #[test]
    fn test_marker_write_is_guarded_and_block_is_reported() {
        let text = read(&checklist());
        assert!(text.contains("if [ \"$GATE_OK\" = \"1\" ]; then"));
        assert!(text.contains("/run/metaos/ready"));
        let guarded = text.split("if [ \"$GATE_OK\" = \"1\" ]; then").nth(1).unwrap();
        assert!(guarded.contains("/run/metaos/ready"));
        assert!(text.contains("BLOCKED"));
        assert!(text.contains("marker not written"));
    }

    #[test]
    fn test_gate_documents_the_oneshot_and_timer_limits() {
        let text = read(&checklist());
        assert!(text.contains("RemainAfterExit"));
        assert!(text.contains("2 minutes after boot"));
    }

    #[test]
    fn test_no_secret_on_any_command_line() {
        assert!(!read(&checklist()).contains("MUSE_RELAY_TOKEN="));
    }

    #[test]
    fn test_readme_carries_os016_section_with_exclusions() {
        let text = read(&readme());
        assert!(text.contains("Boot target and ready gate (OS-016"));
        assert!(text.contains("relay-worker@"));
        assert!(text.contains("OS-118"));
    }

    #[test]
    fn test_spec_carries_os016_record() {
        let text = read(&spec());
        assert!(text.contains("Boot target and ready gate (OS-016"));
        assert!(text.contains("tests/test_os_target_unit.py"));
    }
}
