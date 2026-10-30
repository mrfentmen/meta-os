//! T052 [B31] port of `os/tests/test_os_overseer_unit.py` (same name roots).
//!
//! OS-015 overseer tick unit: file pins only, no live systemd. Pure reads.
//!
//! TREE DRIFT (documented, not hidden): the Python names `os/services/…`,
//! `os/build-image.sh`, `os/build-live.sh`, root `mos.py`/`mos/…`,
//! `os/README.md`, `plan/META_OS.md` — units and build scripts live under
//! the folded tree (`os/os/…`), `mos.*` was never folded (`os/mos*`),
//! the OS-015 section lives in `os/os/README.md` (not `os/README.md`),
//! and the spec record lives in `os/plan/META_OS.md`.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

pub const CASES: &[&str] = &[
    "unit exists",
    "unit ordering wants and secrets gate",
    "service identity workdir and oneshot",
    "exec runs mos tick with no secret on command line",
    "install target and image routes",
    "timer is the loop",
    "mospy is the named process",
    "readme section and spec record",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[];

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
}
fn os_inner() -> PathBuf {
    root().join("os").join("os")
}
fn os_top() -> PathBuf {
    root().join("os")
}
fn read(p: &Path) -> String {
    std::fs::read_to_string(p).unwrap_or_default()
}
fn unit() -> PathBuf {
    os_inner().join("services").join("relay-overseer.service")
}
fn timer() -> PathBuf {
    os_inner().join("services").join("relay-overseer.timer")
}
fn target() -> PathBuf {
    os_inner().join("services").join("relay.target")
}
fn mos_shim() -> PathBuf {
    os_top().join("mos.py")
}
fn mos_cli() -> PathBuf {
    os_top().join("mos").join("cli.py")
}
fn overseer() -> PathBuf {
    os_top().join("mos").join("overseer.py")
}
fn readme() -> PathBuf {
    os_inner().join("README.md")
}
fn spec() -> PathBuf {
    os_top().join("plan").join("META_OS.md")
}
fn build_image() -> PathBuf {
    os_inner().join("build-image.sh")
}
fn build_live() -> PathBuf {
    os_inner().join("build-live.sh")
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
    fn test_unit_ordering_wants_and_secrets_gate() {
        let unit = &sections(&read(&unit()))["Unit"];
        let get = |k: &str| unit.get(k).cloned().unwrap_or_default().join(" ");
        for dep in ["network-online.target", "relay-bus.service", "relay-jobs.service"] {
            assert!(get("After").contains(dep), "After missing {dep}");
            assert!(get("Wants").contains(dep), "Wants missing {dep}");
        }
        assert_eq!(unit.get("PartOf").cloned().unwrap_or_default(), ["relay.target"]);
        assert_eq!(unit.get("ConditionPathExists").cloned().unwrap_or_default(), ["/etc/metaos/secrets.env"]);
    }

    #[test]
    fn test_service_identity_workdir_and_oneshot() {
        let svc = &sections(&read(&unit()))["Service"];
        let get = |k: &str| svc.get(k).cloned().unwrap_or_default();
        assert_eq!(get("Type"), ["oneshot"]);
        assert_eq!(get("User"), ["relay"]);
        assert_eq!(get("Group"), ["relay"]);
        assert_eq!(get("WorkingDirectory"), ["/opt/relay"]);
        assert_eq!(get("EnvironmentFile"), ["/etc/metaos/secrets.env"]);
    }

    #[test]
    fn test_exec_runs_mos_tick_with_no_secret_on_command_line() {
        let svc = &sections(&read(&unit()))["Service"];
        let exec = svc.get("ExecStart").cloned().unwrap_or_default().join(" ");
        assert_eq!(exec, "/usr/bin/python3 /opt/relay/mos.py tick");
        assert!(!exec.contains("token"));
        assert!(!exec.contains("secret"));
        let env = svc.get("Environment").cloned().unwrap_or_default().join(" ");
        assert!(env.contains("MUSE_RELAY_TOKEN_FILE=/etc/metaos/token"), "{env}");
    }

    #[test]
    fn test_install_target_and_image_routes() {
        let install = &sections(&read(&unit()))["Install"];
        assert_eq!(install.get("WantedBy").cloned().unwrap_or_default(), ["relay.target"]);
        assert!(read(&target()).contains("relay-overseer.timer"));
        assert!(read(&build_image()).contains("relay-overseer.service"));
        assert!(read(&build_image()).contains("relay.target.wants"));
        assert!(read(&build_live()).contains("services/*.service"));
    }

    #[test]
    fn test_timer_is_the_loop() {
        let timer = sections(&read(&timer()));
        assert_eq!(timer["Timer"].get("Unit").cloned().unwrap_or_default(), ["relay-overseer.service"]);
        assert_eq!(timer["Timer"].get("OnBootSec").cloned().unwrap_or_default(), ["2min"]);
        assert_eq!(timer["Timer"].get("OnUnitActiveSec").cloned().unwrap_or_default(), ["5min"]);
        assert_eq!(timer["Install"].get("WantedBy").cloned().unwrap_or_default(), ["relay.target"]);
    }

    #[test]
    fn test_mospy_is_the_named_process() {
        assert!(read(&mos_shim()).contains("from mos.cli import main"));
        let cli = read(&mos_cli());
        for needle in ["\"tick\"", "overseer.tick", "set_defaults(fn=cmd_tick)"] {
            assert!(cli.contains(needle), "cli.py missing {needle}");
        }
        let ov = read(&overseer());
        for needle in ["def tick", "jobs.main([\"sweep\"])", "prune_stale"] {
            assert!(ov.contains(needle), "overseer.py missing {needle}");
        }
    }

    #[test]
    fn test_readme_section_and_spec_record() {
        let readme = read(&readme());
        assert!(readme.contains("OS-015"));
        assert!(readme.contains("relay-overseer.service"));
        let spec = read(&spec());
        assert!(spec.contains("OS-015"));
        assert!(spec.contains("relay-overseer.service"));
    }
}
