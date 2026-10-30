//! T053 [B31] port of `os/tests/test_os_packer.py` (same name roots).
//!
//! OS-007 packer template + wrapper: file pins, a real preseed-transform
//! snippet run, shell syntax checks. No image builds.
//!
//! TREE DRIFT (documented, not hidden): the Python names `os/packer/…`,
//! `os/build-packer.sh`, `os/preseed.cfg`, `os/README.md` — the files
//! live under the folded tree (`os/os/…`).

use std::path::{Path, PathBuf};

pub const CASES: &[&str] = &[
    "template exists and names qemu source",
    "template bookworm only no second base",
    "template raw output and names",
    "template iso checksum is publisher file not invented hash",
    "template iso url has no default",
    "template ssh password sensitive and undefaulted",
    "template provisioners mirror build image glue",
    "no literal password in template or wrapper",
    "wrapper syntax clean",
    "wrapper guards",
    "wrapper generates password with openssl not a literal",
    "wrapper preseed transform changes exactly one line",
    "committed preseed still locked",
    "readme carries os007 section with unproven limit",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[];

/// Second-base codenames forbidden outside the frozen bookworm base.
pub const FORBIDDEN: &[&str] = &["bullseye", "trixie", "forky", "sid", "ubuntu", "fedora", "centos", "rhel", "archlinux"];

/// Units os/build-image.sh enables (OS-016 target set).
pub const ENABLED_UNITS: &[&str] = &[
    "relay-dashboard.service",
    "relay-bus.service",
    "relay-jobs.service",
    "relay-overseer.timer",
    "relay-ready.service",
    "metaos-firstboot.service",
    "relay-overseer.service",
    "relay-watchdog.service",
    "relay-brief.service",
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
fn template() -> PathBuf {
    os_inner().join("packer").join("metaos.pkr.hcl")
}
fn wrapper() -> PathBuf {
    os_inner().join("build-packer.sh")
}
fn preseed() -> PathBuf {
    os_inner().join("preseed.cfg")
}
fn readme() -> PathBuf {
    os_inner().join("README.md")
}

fn second_base_in(text: &str) -> Option<String> {
    let lower = text.to_lowercase();
    let mut token = String::new();
    for c in lower.chars().chain(std::iter::once(' ')) {
        if c.is_ascii_alphanumeric() {
            token.push(c);
        } else {
            if FORBIDDEN.contains(&token.as_str()) {
                return Some(token);
            }
            token.clear();
        }
    }
    None
}

/// Extract a `variable "name" { ... }` block body.
fn var_block(text: &str, name: &str) -> Option<String> {
    let start = text.find(&format!("variable \"{name}\""))?;
    let after = &text[start..];
    let end = after.find("\n}")?;
    Some(after[..end].to_string())
}

/// Literal `ssh_password = "…"` assignment with a real secret value.
fn literal_password_at(text: &str) -> Option<String> {
    for line in text.lines() {
        let t = line.trim();
        if let Some(i) = t.find("ssh_password") {
            let rest = &t[i..];
            if let Some(eq) = rest.find('=') {
                let val = rest[eq + 1..].trim();
                if val.starts_with('"') && val.len() > 10 && !val[1..].starts_with('%') && !val.contains("$") {
                    return Some(line.to_string());
                }
            }
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_template_exists_and_names_qemu_source() {
        let text = read(&template());
        assert!(template().is_file());
        assert!(text.contains("source \"qemu\" \"metaos\""));
        assert!(text.contains("sources = [\"source.qemu.metaos\"]"));
    }

    #[test]
    fn test_template_bookworm_only_no_second_base() {
        let text = read(&template());
        assert!(text.contains("bookworm"));
        assert_eq!(second_base_in(&text), None);
    }

    #[test]
    fn test_template_raw_output_and_names() {
        let text = read(&template());
        for needle in ["format            = \"raw\"", "vm_name           = \"metaos\"", "output_directory  = \"work/packer-out\"", "http_directory    = \"work/packer-http\""] {
            assert!(text.contains(needle), "template missing {needle:?}");
        }
    }

    #[test]
    fn test_template_iso_checksum_is_publisher_file_not_invented_hash() {
        let text = read(&template());
        assert!(text.contains("file:https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/SHA256SUMS"));
        assert!(!text.contains("iso_checksum      = \"sha256:"));
    }

    #[test]
    fn test_template_iso_url_has_no_default() {
        let text = read(&template());
        let block = var_block(&text, "iso_url").expect("iso_url block missing");
        assert!(block.lines().all(|l| !l.trim_start().starts_with("default")));
    }

    #[test]
    fn test_template_ssh_password_sensitive_and_undefaulted() {
        let text = read(&template());
        let block = var_block(&text, "ssh_password").expect("ssh_password block missing");
        assert!(block.contains("sensitive   = true"));
        assert!(!block.contains("default"));
        assert!(text.contains("ssh_username      = \"relay\""));
        assert!(text.contains("preseed-build.cfg"));
    }

    #[test]
    fn test_template_provisioners_mirror_build_image_glue() {
        let text = read(&template());
        for unit in ENABLED_UNITS {
            assert!(text.contains(unit), "template missing {unit}");
        }
        assert!(text.contains("/etc/metaos-version"));
        assert!(text.contains("(debian 12 bookworm, stock kernel)"));
        assert!(text.contains("autologin relay"));
        for dirname in ["services", "firstboot", "bin"] {
            assert!(text.contains(&format!("source      = \"{dirname}\"")), "template missing {dirname} source");
            assert!(os_inner().join(dirname).is_dir(), "provisioner source dir missing: {dirname}");
        }
    }

    #[test]
    fn test_no_literal_password_in_template_or_wrapper() {
        for p in [template(), wrapper()] {
            let text = read(&p);
            assert_eq!(literal_password_at(&text), None, "{} assigns ssh_password a literal", p.display());
            assert!(!text.contains("password123"));
        }
        assert!(read(&wrapper()).contains("printf 'ssh_password = \"%s\"\\n' \"$BUILD_PASS\""));
    }

    #[test]
    fn test_wrapper_syntax_clean() {
        let out = std::process::Command::new("bash").arg("-n").arg(wrapper()).output().expect("bash failed");
        assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
    }

    #[test]
    fn test_wrapper_guards() {
        let text = read(&wrapper());
        for needle in ["set -euo pipefail", "status --porcelain", "refusing: checkout is dirty", "packer", "qemu-system-x86_64", "openssl", "curl", "packer validate", "packer build", "sha256sum", "IMG=\"metaos-$DATE.img\"", "DATE=$(date +%F)"] {
            assert!(text.contains(needle), "wrapper missing {needle:?}");
        }
    }

    #[test]
    fn test_wrapper_generates_password_with_openssl_not_a_literal() {
        let text = read(&wrapper());
        assert!(text.contains("openssl rand -base64"));
        assert!(text.contains("openssl passwd -6"));
        assert!(text.contains("trap cleanup EXIT"));
        assert!(text.contains("rm -rf \"$HTTP_DIR\" \"$VAR_FILE\""));
    }

    #[test]
    fn test_wrapper_preseed_transform_changes_exactly_one_line() {
        let wrapper_text = read(&wrapper());
        let lines: Vec<&str> = wrapper_text.lines().collect();
        let start = lines.iter().position(|l| l.starts_with("sed ") && l.contains("user-password-crypted")).expect("sed transform missing");
        let snippet = lines[start..start + 2].join("\n");
        let tmp = tempfile::tempdir().unwrap();
        let out = std::process::Command::new("bash")
            .arg("-c").arg(&snippet)
            .current_dir(os_inner())
            .env("HTTP_DIR", tmp.path())
            .env("BUILD_HASH", "TESTHASH")
            .output().expect("bash failed");
        assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
        let orig_text = read(&preseed());
        let orig: Vec<&str> = orig_text.lines().collect();
        let built_text = read(&tmp.path().join("preseed-build.cfg"));
        let built: Vec<&str> = built_text.lines().collect();
        assert_eq!(orig.len(), built.len());
        let diffs: Vec<usize> = orig.iter().zip(built.iter()).enumerate().filter(|(_, (a, b))| a != b).map(|(i, _)| i).collect();
        assert_eq!(diffs.len(), 1);
        let i = diffs[0];
        assert!(orig[i].contains("user-password-crypted password *"));
        assert!(built[i].contains("user-password-crypted password TESTHASH"));
    }

    #[test]
    fn test_committed_preseed_still_locked() {
        assert!(read(&preseed()).contains("user-password-crypted password *"));
    }

    #[test]
    fn test_readme_carries_os007_section_with_unproven_limit() {
        let text = read(&readme());
        assert!(text.contains("OS-007"));
        assert!(text.contains("build-packer.sh"));
        assert!(text.contains("packer/metaos.pkr.hcl"));
        assert!(text.contains("UNPROVEN"));
        assert!(!text.contains('\u{2014}'));
    }
}
