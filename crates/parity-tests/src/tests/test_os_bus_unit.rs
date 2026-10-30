//! T048 [B31] port of `os/tests/test_os_bus_unit.py` (same name roots).
//!
//! OS-013 relay bus unit: file pins only, no live bus. Pure file reads.
//!
//! TREE DRIFT (documented, not hidden): the Python names `os/services/…`,
//! `os/build-image.sh`, `os/build-live.sh`, repo-root `watch.py`,
//! `os/README.md`, `plan/META_OS.md` — the files live under the folded
//! tree (`os/os/…`, `os/watch.py`, `os/os/README.md`, `os/plan/META_OS.md`).
//! `os/README.md` carries no OS-013 section while `os/os/README.md` does.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

pub const CASES: &[&str] = &[
    "unit exists",
    "unit ordering target and secrets gate",
    "service identity workdir and restart",
    "exec runs watchpy with no secret on command line",
    "install and target want each other",
    "image route enables and live route stages",
    "watchpy is the named process",
    "readme section and spec record",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[];

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
}
fn os_inner() -> PathBuf {
    root().join("os").join("os")
}
fn read(p: &Path) -> String {
    std::fs::read_to_string(p).unwrap_or_default()
}
fn unit() -> PathBuf {
    os_inner().join("services").join("relay-bus.service")
}
fn target() -> PathBuf {
    os_inner().join("services").join("relay.target")
}
fn build_image() -> PathBuf {
    os_inner().join("build-image.sh")
}
fn build_live() -> PathBuf {
    os_inner().join("build-live.sh")
}
fn watch_py() -> PathBuf {
    root().join("os").join("watch.py")
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
    fn test_unit_exists() {
        assert!(unit().exists());
    }

    #[test]
    fn test_unit_ordering_target_and_secrets_gate() {
        let unit = &sections(&read(&unit()))["Unit"];
        let get = |k: &str| unit.get(k).cloned().unwrap_or_default().join(" ");
        assert!(get("After").contains("network-online.target"), "{:?}", get("After"));
        assert_eq!(unit.get("PartOf").cloned().unwrap_or_default(), ["relay.target"]);
        assert_eq!(unit.get("ConditionPathExists").cloned().unwrap_or_default(), ["/etc/metaos/secrets.env"]);
    }

    #[test]
    fn test_service_identity_workdir_and_restart() {
        let svc = &sections(&read(&unit()))["Service"];
        let get = |k: &str| svc.get(k).cloned().unwrap_or_default();
        assert_eq!(get("Type"), ["simple"]);
        assert_eq!(get("User"), ["relay"]);
        assert_eq!(get("Group"), ["relay"]);
        assert_eq!(get("WorkingDirectory"), ["/opt/relay"]);
        assert_eq!(get("Restart"), ["on-failure"]);
        assert_eq!(get("RestartSec"), ["5"]);
        assert_eq!(get("EnvironmentFile"), ["/etc/metaos/secrets.env"]);
    }

    #[test]
    fn test_exec_runs_watchpy_with_no_secret_on_command_line() {
        let svc = &sections(&read(&unit()))["Service"];
        let exec = svc.get("ExecStart").cloned().unwrap_or_default().join(" ");
        assert_eq!(exec, "/usr/bin/python3 /opt/relay/watch.py --interval 10");
        assert!(!exec.contains("--dm"));
        assert!(!exec.contains("token"));
    }

    #[test]
    fn test_install_and_target_want_each_other() {
        let install = &sections(&read(&unit()))["Install"];
        assert_eq!(install.get("WantedBy").cloned().unwrap_or_default(), ["relay.target"]);
        assert!(read(&target()).contains("relay-bus.service"));
    }

    #[test]
    fn test_image_route_enables_and_live_route_stages() {
        assert!(read(&build_image()).contains("relay-bus.service"));
        assert!(read(&build_image()).contains("relay.target.wants"));
        assert!(read(&build_live()).contains("services/*.service"));
    }

    #[test]
    fn test_watchpy_is_the_named_process() {
        let watch = read(&watch_py());
        assert!(watch.contains("\"--interval\""));
        assert!(watch.contains("presence_beat"));
    }

    #[test]
    fn test_readme_section_and_spec_record() {
        let readme = read(&readme());
        assert!(readme.contains("OS-013"));
        assert!(readme.contains("relay-bus.service"));
        let spec = read(&spec());
        assert!(spec.contains("OS-013"));
        assert!(spec.contains("relay-bus.service"));
    }
}
