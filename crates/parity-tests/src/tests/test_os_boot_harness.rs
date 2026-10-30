//! T045 [B31] port of `os/tests/test_os_boot_harness.py` (same name roots).
//!
//! OS-019 QEMU boot harness: pins the script (bash-clean, embedded Python
//! clients compile), its argument guards (real negative runs), the launch
//! contract text, and the README's stated unproven limit. No boot happens:
//! the QEMU run stays explicitly UNPROVEN until a build host runs it.
//!
//! TREE DRIFT (documented, not hidden): the Python names `os/test-boot.sh`
//! and `os/README.md` -- the script lives under the folded tree
//! (`os/os/test-boot.sh`) and the OS-019 section in `os/os/README.md`.

use std::path::{Path, PathBuf};

pub const CASES: &[&str] = &[
    "script exists and bash clean",
    "embedded python compiles",
    "no image is usage error",
    "missing image fails naming path",
    "bad numbers fail",
    "non ppm screenshot fails",
    "missing qemu fails naming binary",
    "launch contract in script",
    "readme section states unproven limit",
    "no em dash in new content",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[
    "QEMU boot run (no qemu-system-x86_64 binary and no test image in this env)",
];

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
}
fn script_path() -> PathBuf {
    root().join("os").join("os").join("test-boot.sh")
}
fn readme_path() -> PathBuf {
    root().join("os").join("os").join("README.md")
}
fn read(p: &Path) -> String {
    std::fs::read_to_string(p).unwrap_or_default()
}

const QGA_DEVICE: &str = "org.qemu.guest_agent.0";
const READY_MARKER: &str = "/run/metaos/ready";
const VERSION_FILE: &str = "/etc/metaos-version";

/// Yield (name, body) for every `<<'NAME' ... NAME` heredoc.
fn heredoc_bodies(text: &str) -> Vec<(String, String)> {
    let mut bodies = vec![];
    let lines: Vec<&str> = text.lines().collect();
    let mut i = 0;
    while i < lines.len() {
        let t = lines[i].trim_end();
        if let Some(start) = t.find("<<'") {
            let rest = &t[start + 3..];
            if let Some(end) = rest.find('\'') {
                let name = &rest[..end];
                if name.chars().all(|c| c.is_ascii_alphanumeric() || c == '_')
                    && rest[end + 1..].trim().is_empty()
                {
                    i += 1;
                    let mut body = vec![];
                    while i < lines.len() && lines[i] != name {
                        body.push(lines[i]);
                        i += 1;
                    }
                    bodies.push((name.to_string(), body.join("\n")));
                }
            }
        }
        i += 1;
    }
    bodies
}

fn run_script(args: &[&str], path_override: Option<&std::ffi::OsStr>) -> (i32, String, String) {
    let mut cmd = std::process::Command::new("bash");
    cmd.arg(script_path());
    cmd.args(args);
    if let Some(p) = path_override {
        cmd.env("PATH", p);
    }
    let out = cmd.output().expect("bash failed to spawn");
    (
        out.status.code().unwrap_or(-1),
        String::from_utf8_lossy(&out.stdout).into_owned(),
        String::from_utf8_lossy(&out.stderr).into_owned(),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_script_exists_and_bash_clean() {
        assert!(script_path().is_file(), "os/os/test-boot.sh missing");
        let out = std::process::Command::new("bash").arg("-n").arg(script_path()).output().expect("bash failed");
        assert!(out.status.success(), "bash -n failed: {}", String::from_utf8_lossy(&out.stderr));
    }

    #[test]
    fn test_embedded_python_compiles() {
        let text = read(&script_path());
        let bodies = heredoc_bodies(&text);
        let names: Vec<&str> = bodies.iter().map(|(n, _)| n.as_str()).collect();
        for want in ["QGA_WAIT_PY", "QGA_VERSION_PY", "MON_PY"] {
            assert!(names.contains(&want), "heredoc {want} missing");
        }
        for (name, body) in &bodies {
            assert!(!body.trim().is_empty(), "empty heredoc {name}");
            let mut child = std::process::Command::new("python3")
                .args(["-c", &format!("import sys; compile(sys.stdin.read(), '<{name}>', 'exec')")])
                .stdin(std::process::Stdio::piped())
                .stdout(std::process::Stdio::null())
                .stderr(std::process::Stdio::piped())
                .spawn()
                .expect("python3 failed to spawn");
            use std::io::Write;
            child.stdin.take().unwrap().write_all(body.as_bytes()).unwrap();
            let out = child.wait_with_output().unwrap();
            assert!(out.status.success(), "heredoc {name} does not compile: {}", String::from_utf8_lossy(&out.stderr));
        }
    }

    #[test]
    fn test_no_image_is_usage_error() {
        let (code, _, stderr) = run_script(&[], None);
        assert_ne!(code, 0);
        assert!(stderr.to_lowercase().contains("usage"), "{stderr}");
    }

    #[test]
    fn test_missing_image_fails_naming_path() {
        let (code, stdout, stderr) = run_script(&["/tmp/does-not-exist-metaos.img"], None);
        assert_ne!(code, 0);
        assert!((stdout + &stderr).contains("/tmp/does-not-exist-metaos.img"));
    }

    #[test]
    fn test_bad_numbers_fail() {
        let tmp = tempfile::Builder::new().suffix(".img").tempfile().unwrap();
        let img = tmp.path().to_string_lossy().into_owned();
        for (flag, value) in [("--timeout", "abc"), ("--timeout", "0"), ("--memory", "-1"), ("--cpus", "x")] {
            let (code, _, _) = run_script(&[&img, flag, value], None);
            assert_ne!(code, 0, "{flag} {value} should fail");
        }
    }

    #[test]
    fn test_non_ppm_screenshot_fails() {
        let tmp = tempfile::Builder::new().suffix(".img").tempfile().unwrap();
        let (code, stdout, stderr) = run_script(&[&tmp.path().to_string_lossy(), "--screenshot", "/tmp/shot.png"], None);
        assert_ne!(code, 0);
        assert!((stdout + &stderr).contains(".ppm"));
    }

    #[test]
    fn test_missing_qemu_fails_naming_binary() {
        let empty = tempfile::tempdir().unwrap();
        let img = tempfile::Builder::new().suffix(".img").tempfile().unwrap();
        let out = std::process::Command::new("/bin/bash")
            .arg(script_path())
            .arg(img.path())
            .env("PATH", empty.path())
            .output()
            .expect("bash failed to spawn");
        assert!(!out.status.success());
        let both = String::from_utf8_lossy(&out.stdout).into_owned() + &String::from_utf8_lossy(&out.stderr);
        assert!(both.contains("qemu-system-x86_64"), "{both}");
    }

    #[test]
    fn test_launch_contract_in_script() {
        let text = read(&script_path());
        for needle in ["snapshot=on", QGA_DEVICE, READY_MARKER, VERSION_FILE, "screendump", "monitor", "serial"] {
            assert!(text.contains(needle), "launch contract missing {needle:?}");
        }
        let code: Vec<&str> = text.lines().filter(|l| !l.trim_start().starts_with('#')).collect();
        let code = code.join("\n");
        assert!(!code.contains("-netdev"));
        assert!(!code.contains("-nic "));
        assert!(text.contains("trap cleanup EXIT"));
        assert!(text.contains("guest-exec"));
    }

    #[test]
    fn test_readme_section_states_unproven_limit() {
        let text = read(&readme_path());
        for needle in ["OS-019", "test-boot.sh", "UNPROVEN", "screendump"] {
            assert!(text.contains(needle), "README missing {needle:?}");
        }
    }

    #[test]
    fn test_no_em_dash_in_new_content() {
        assert!(!read(&script_path()).contains('\u{2014}'));
        assert!(!include_str!("test_os_boot_harness.rs").contains('\u{2014}'));
    }
}
