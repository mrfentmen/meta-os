//! T038 [B31] port of `os/tests/test_os059_gateway_bake.py` (same name roots).
//!
//! OS-059 gateway bake: file-content pins on the three image routes,
//! the Packer template, the OS-012 sweep allowlist (run for real against
//! fixture rootfs dirs), shell syntax checks (`bash`/`sh -n`), docs.
//! Pure file reads + local script runs — no bus, no Redis, no network.
//!
//! TREE DRIFT (documented, not hidden): the Python names `os/…` and
//! `plan/META_OS.md` — the files live under the folded tree (`os/os/…`,
//! `os/plan/META_OS.md`).

use std::path::{Path, PathBuf};
use std::process::Command;

pub const CASES: &[&str] = &[
    "target wants gateway",
    "unit header no longer defers enablement",
    "enablement loop names gateway",
    "bake block copies only daemon and catalog",
    "bake block refuses missing source",
    "build image bash syntax",
    "hook enables gateway",
    "wrapper stages gateway and stamp",
    "wrapper bash syntax",
    "hook shell syntax",
    "file provisioners carry only daemon and catalog",
    "shell installs stamp and enables",
    "allowlisted gateway tree sweeps clean",
    "planted env file is finding",
    "planted venv and servers files are findings",
    "sweep script shell syntax",
    "readme carries os059 section without em dash",
    "spec records os059 bake",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[];

const GATEWAY_UNIT: &str = "relay-mcp-gateway.service";

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
fn unit() -> PathBuf {
    os_inner().join("services").join("relay-mcp-gateway.service")
}
fn build_image() -> PathBuf {
    os_inner().join("build-image.sh")
}
fn build_live() -> PathBuf {
    os_inner().join("build-live.sh")
}
fn hook() -> PathBuf {
    os_inner().join("live-build/config/hooks/live/0900-metaos-services.hook.chroot")
}
fn packer() -> PathBuf {
    os_inner().join("packer").join("metaos.pkr.hcl")
}
fn sweep() -> PathBuf {
    os_inner().join("bin").join("metaos-secrets-sweep")
}
fn readme() -> PathBuf {
    os_inner().join("README.md")
}
fn spec() -> PathBuf {
    root().join("os").join("plan").join("META_OS.md")
}

fn enablement_loop(text: &str) -> String {
    text.lines().find(|l| l.contains("for u in")).unwrap_or("").to_string()
}

fn bake_section(text: &str) -> String {
    let start = match text.find("2b. OS-059") {
        Some(i) => i,
        None => return String::new(),
    };
    let end = match text[start..].find("# metaos-update expects") {
        Some(i) => start + i,
        None => return String::new(),
    };
    text[start..end].to_string()
}

fn shell_check(shell: &str, flag: &str, path: &Path) -> (i32, String) {
    let out = Command::new(shell).arg(flag).arg(path).output().expect("shell failed to spawn");
    (out.status.code().unwrap_or(-1), String::from_utf8_lossy(&out.stderr).into_owned())
}

fn gateway_rootfs(extra: &[&str]) -> tempfile::TempDir {
    let tmp = tempfile::tempdir().unwrap();
    let gw = tmp.path().join("opt/relay/mcp-gateway");
    std::fs::create_dir_all(&gw).unwrap();
    for name in ["gateway.py", "backends.json", ".metaos-gateway-bake"] {
        std::fs::write(gw.join(name), "# fixture\n").unwrap();
    }
    for rel in extra {
        let p = gw.join(rel);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::fs::write(p, "# planted\n").unwrap();
    }
    tmp
}

fn run_sweep(rootfs: &Path) -> (i32, String) {
    let out = Command::new("sh").arg(sweep()).arg(rootfs).output().expect("sweep failed to spawn");
    (out.status.code().unwrap_or(-1), String::from_utf8_lossy(&out.stdout).into_owned())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_target_wants_gateway() {
        assert!(read(&target()).contains(GATEWAY_UNIT));
    }

    #[test]
    fn test_unit_header_no_longer_defers_enablement() {
        let text = read(&unit());
        assert!(text.contains("OS-059"));
        assert!(!text.contains("waits on OS-059"));
        assert!(!text.contains("does not Want"));
    }

    #[test]
    fn test_enablement_loop_names_gateway() {
        assert!(enablement_loop(&read(&build_image())).contains(GATEWAY_UNIT));
    }

    #[test]
    fn test_bake_block_copies_only_daemon_and_catalog() {
        let section = bake_section(&read(&build_image()));
        assert!(!section.is_empty(), "OS-059 bake block missing");
        for needle in ["gateway.py", "backends.json", ".metaos-gateway-bake", "sha256sum gateway.py backends.json", ".venv", "servers/"] {
            assert!(section.contains(needle), "bake block missing {needle:?}");
        }
        assert!(!section.contains("rsync"));
    }

    #[test]
    fn test_bake_block_refuses_missing_source() {
        let section = bake_section(&read(&build_image()));
        assert!(section.contains("no gateway.py in"));
        assert!(section.contains("no backends.json in"));
        assert!(section.contains("METAOS_GATEWAY_SRC"));
    }

    #[test]
    fn test_build_image_bash_syntax() {
        let (code, stderr) = shell_check("bash", "-n", &build_image());
        assert_eq!(code, 0, "{stderr}");
    }

    #[test]
    fn test_hook_enables_gateway() {
        assert!(enablement_loop(&read(&hook())).contains(GATEWAY_UNIT));
    }

    #[test]
    fn test_wrapper_stages_gateway_and_stamp() {
        let text = read(&build_live());
        for needle in ["opt/relay/mcp-gateway", "no gateway.py in", "no backends.json in", ".metaos-gateway-bake", "sha256sum gateway.py backends.json"] {
            assert!(text.contains(needle), "build-live missing {needle:?}");
        }
    }

    #[test]
    fn test_wrapper_bash_syntax() {
        let (code, stderr) = shell_check("bash", "-n", &build_live());
        assert_eq!(code, 0, "{stderr}");
    }

    #[test]
    fn test_hook_shell_syntax() {
        let (code, stderr) = shell_check("sh", "-n", &hook());
        assert_eq!(code, 0, "{stderr}");
    }

    #[test]
    fn test_file_provisioners_carry_only_daemon_and_catalog() {
        let text = read(&packer());
        assert!(text.contains("mcp-gateway/gateway.py"));
        assert!(text.contains("mcp-gateway/backends.json"));
        assert!(!text.contains("mcp-gateway/servers"));
        assert!(!text.contains("mcp-gateway/.venv"));
    }

    #[test]
    fn test_shell_installs_stamp_and_enables() {
        let text = read(&packer());
        for needle in ["/opt/relay/mcp-gateway/", ".metaos-gateway-bake", "sha256sum gateway.py backends.json", "chown -R relay:relay /opt/relay/mcp-gateway", GATEWAY_UNIT] {
            assert!(text.contains(needle), "packer missing {needle:?}");
        }
        assert!(!enablement_loop(&text).is_empty() || text.contains(GATEWAY_UNIT));
    }

    #[test]
    fn test_allowlisted_gateway_tree_sweeps_clean() {
        let tmp = gateway_rootfs(&[]);
        let (code, stdout) = run_sweep(tmp.path());
        assert_eq!(code, 0, "{stdout}");
        assert!(stdout.contains("clean"), "{stdout}");
    }

    #[test]
    fn test_planted_env_file_is_finding() {
        let tmp = gateway_rootfs(&[".env"]);
        let (code, stdout) = run_sweep(tmp.path());
        assert_eq!(code, 1, "{stdout}");
        assert!(stdout.contains("FINDING"), "{stdout}");
    }

    #[test]
    fn test_planted_venv_and_servers_files_are_findings() {
        for rel in [".venv/bin/python", "servers/printify-mcp/launch.sh", "gateway.db"] {
            let tmp = gateway_rootfs(&[rel]);
            let (code, stdout) = run_sweep(tmp.path());
            assert_eq!(code, 1, "{rel}: {stdout}");
            assert!(stdout.contains("FINDING"), "{rel}: {stdout}");
        }
    }

    #[test]
    fn test_sweep_script_shell_syntax() {
        let (code, stderr) = shell_check("sh", "-n", &sweep());
        assert_eq!(code, 0, "{stderr}");
    }

    #[test]
    fn test_readme_carries_os059_section_without_em_dash() {
        let text = read(&readme());
        assert!(text.contains("OS-059"));
        let start = text.find("Gateway bake (OS-059").expect("OS-059 section missing");
        let tail = &text[start..];
        let section = match tail[1..].find("\n## ") {
            Some(i) => &tail[..1 + i],
            None => tail,
        };
        assert!(!section.contains('\u{2014}'));
    }

    #[test]
    fn test_spec_records_os059_bake() {
        let text = read(&spec());
        assert!(text.contains("OS-059"));
        assert!(text.contains("relay-mcp-gateway.service"));
    }
}
