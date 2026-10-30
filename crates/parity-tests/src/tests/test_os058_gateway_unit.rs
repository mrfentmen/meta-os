//! T037 [B31] port of `os/tests/test_os058_gateway_unit.py` (same name roots).
//!
//! OS-058 MCP gateway daemon unit: file pins only, no live gateway.
//! Pure file reads — no process, no Redis, no network, no systemd.
//!
//! TREE DRIFT (documented, not hidden): the Python names `os/services/…`,
//! `os/build-image.sh`, `os/README.md`, `plan/META_OS.md` — the service,
//! build and doc files live under the folded tree (`os/os/…`,
//! `os/plan/META_OS.md`); `os/README.md` carries no OS-058 section while
//! `os/os/README.md` does. The Python test errors/fails on this tree;
//! the port follows the folded tree so the pins are actually verified.

use std::collections::HashMap;
use std::path::PathBuf;

pub const CASES: &[&str] = &[
    "unit exists",
    "unit ordering target and secrets gate",
    "service identity workdir and restart",
    "exec runs gateway with no secret on command line",
    "install and target wiring live after bake",
    "image routes enable after bake",
    "header names bake and has no em dash",
    "readme section and spec record",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[];

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
}
fn os_inner() -> PathBuf {
    root().join("os").join("os")
}
fn read(p: &std::path::Path) -> String {
    std::fs::read_to_string(p).unwrap_or_default()
}
fn unit_path() -> PathBuf {
    os_inner().join("services").join("relay-mcp-gateway.service")
}
fn target_path() -> PathBuf {
    os_inner().join("services").join("relay.target")
}
fn build_image_path() -> PathBuf {
    os_inner().join("build-image.sh")
}
fn live_hook_path() -> PathBuf {
    os_inner()
        .join("live-build/config/hooks/live/0900-metaos-services.hook.chroot")
}
fn readme_path() -> PathBuf {
    os_inner().join("README.md")
}
fn spec_path() -> PathBuf {
    root().join("os").join("plan").join("META_OS.md")
}

/// Minimal systemd-unit parser mirroring the Python `sections()`.
pub fn sections(text: &str) -> HashMap<String, HashMap<String, Vec<String>>> {
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

pub fn enablement_loop(text: &str) -> String {
    text.lines().find(|l| l.trim().starts_with("for u in")).unwrap_or("").to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_unit_exists() {
        assert!(unit_path().exists());
    }

    #[test]
    fn test_unit_ordering_target_and_secrets_gate() {
        let unit = &sections(&read(&unit_path()))["Unit"];
        let after = unit.get("After").cloned().unwrap_or_default().join(" ");
        assert!(after.contains("network-online.target"), "{after}");
        let wants = unit.get("Wants").cloned().unwrap_or_default().join(" ");
        assert!(wants.contains("network-online.target"), "{wants}");
        assert_eq!(unit.get("PartOf").cloned().unwrap_or_default(), ["relay.target"]);
        assert_eq!(unit.get("ConditionPathExists").cloned().unwrap_or_default(), ["/etc/metaos/secrets.env"]);
    }

    #[test]
    fn test_service_identity_workdir_and_restart() {
        let svc = &sections(&read(&unit_path()))["Service"];
        let get = |k: &str| svc.get(k).cloned().unwrap_or_default();
        assert_eq!(get("Type"), ["simple"]);
        assert_eq!(get("User"), ["relay"]);
        assert_eq!(get("Group"), ["relay"]);
        assert_eq!(get("WorkingDirectory"), ["/opt/relay/mcp-gateway"]);
        assert_eq!(get("Restart"), ["on-failure"]);
        assert_eq!(get("RestartSec"), ["5"]);
        assert_eq!(get("EnvironmentFile"), ["/etc/metaos/secrets.env"]);
    }

    #[test]
    fn test_exec_runs_gateway_with_no_secret_on_command_line() {
        let svc = &sections(&read(&unit_path()))["Service"];
        let exec = svc.get("ExecStart").cloned().unwrap_or_default().join(" ");
        assert_eq!(exec, "/usr/bin/python3 /opt/relay/mcp-gateway/gateway.py");
        for bad in ["token", "secret", "key"] {
            assert!(!exec.contains(bad), "secret on command line: {exec}");
        }
    }

    #[test]
    fn test_install_and_target_wiring_live_after_bake() {
        let install = &sections(&read(&unit_path()))["Install"];
        assert_eq!(install.get("WantedBy").cloned().unwrap_or_default(), ["relay.target"]);
        assert!(read(&target_path()).contains("relay-mcp-gateway.service"));
    }

    #[test]
    fn test_image_routes_enable_after_bake() {
        assert!(enablement_loop(&read(&build_image_path())).contains("relay-mcp-gateway.service"));
        assert!(enablement_loop(&read(&live_hook_path())).contains("relay-mcp-gateway.service"));
    }

    #[test]
    fn test_header_names_bake_and_has_no_em_dash() {
        let text = read(&unit_path());
        assert!(text.contains("OS-059"));
        assert!(!text.contains("waits on the OS-059 bake"));
        assert!(!text.contains('\u{2014}'));
    }

    #[test]
    fn test_readme_section_and_spec_record() {
        let readme = read(&readme_path());
        assert!(readme.contains("OS-058"));
        assert!(readme.contains("relay-mcp-gateway.service"));
        let spec = read(&spec_path());
        assert!(spec.contains("OS-058"));
        assert!(spec.contains("relay-mcp-gateway.service"));
    }
}
