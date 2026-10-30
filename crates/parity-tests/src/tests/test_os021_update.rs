//! T036 [B31] port of `os/tests/test_os021_update.py` (same name roots).
//!
//! OS-021 update path: runs the REAL `metaos-update` shell script against
//! fixture git trees in temp dirs through the `METAOS_RELAY_ROOT` test
//! hook — apply/rollback semantics, refusal codes, target untouched on
//! failure. No root, no network, no live systemd (the script absorbs
//! `systemctl` failure itself).
//!
//! TREE DRIFT (documented, not hidden): the Python names
//! `os/bin/metaos-update` and `os/README.md` — the script and docs live
//! under the folded tree (`os/os/bin/`, `os/os/README.md`).

use std::path::{Path, PathBuf};
use std::process::Command;

pub const CASES: &[&str] = &[
    "apply moves tree and keeps previous",
    "rollback swaps and second rollback swaps back",
    "rollback without previous refuses",
    "missing bundle is usage error",
    "corrupt bundle refuses and leaves target",
    "non git target refuses",
    "no args without hook exits before touching target",
    "script defaults to opt relay and names hook",
    "readme documents rollback",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[];

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
}
fn script_path() -> PathBuf {
    root().join("os").join("os").join("bin").join("metaos-update")
}
fn readme_path() -> PathBuf {
    root().join("os").join("os").join("README.md")
}

fn git(cwd: &Path, args: &[&str]) -> String {
    let out = Command::new("git")
        .arg("-c")
        .arg("user.email=test@metaos.local")
        .arg("-c")
        .arg("user.name=Meta OS test")
        .arg("-C")
        .arg(cwd)
        .args(args)
        .output()
        .expect("git failed to spawn");
    assert!(out.status.success(), "git {args:?} failed: {}", String::from_utf8_lossy(&out.stderr));
    String::from_utf8_lossy(&out.stdout).trim().to_string()
}

struct Fixture {
    _tmp: tempfile::TempDir,
    live: PathBuf,
    src: PathBuf,
    bundle: PathBuf,
    v1: String,
    v2: String,
}

impl Fixture {
    fn setup() -> Self {
        let tmp = tempfile::tempdir().unwrap();
        let live = tmp.path().join("relay");
        let src = tmp.path().join("src");
        std::fs::create_dir_all(&live).unwrap();
        std::fs::create_dir_all(&src).unwrap();
        let v1 = Self::make_repo(&live, "v1\n");
        let v2 = Self::make_repo(&src, "v2\n");
        let bundle = tmp.path().join("update.bundle");
        git(&src, &["bundle", "create", bundle.to_str().unwrap(), "main"]);
        Fixture { _tmp: tmp, live, src, bundle, v1, v2 }
    }

    fn make_repo(path: &Path, content: &str) -> String {
        git(path, &["init", "-q", "-b", "main"]);
        std::fs::write(path.join("app.txt"), content).unwrap();
        git(path, &["add", "app.txt"]);
        git(path, &["commit", "-q", "-m", "fixture"]);
        git(path, &["rev-parse", "HEAD"])
    }

    fn run(&self, args: &[&str], relay_root: Option<&Path>) -> (i32, String, String) {
        let mut cmd = Command::new("sh");
        cmd.arg(script_path()).args(args).env("METAOS_RELAY_ROOT", relay_root.unwrap_or(&self.live));
        // Without hook: drop the variable entirely.
        if relay_root.is_none() && args.is_empty() {
            cmd.env_remove("METAOS_RELAY_ROOT");
        }
        let out = cmd.output().expect("script failed to spawn");
        (
            out.status.code().unwrap_or(-1),
            String::from_utf8_lossy(&out.stdout).into_owned(),
            String::from_utf8_lossy(&out.stderr).into_owned(),
        )
    }

    fn live_content(&self) -> String {
        std::fs::read_to_string(self.live.join("app.txt")).unwrap()
    }
    fn live_head(&self) -> String {
        git(&self.live, &["rev-parse", "HEAD"])
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_apply_moves_tree_and_keeps_previous() {
        let f = Fixture::setup();
        let (code, stdout, stderr) = f.run(&[f.bundle.to_str().unwrap()], Some(&f.live));
        assert_eq!(code, 0, "{stderr}");
        assert!(stdout.contains("applied"), "{stdout}");
        assert_eq!(f.live_content(), "v2\n");
        assert_eq!(f.live_head(), f.v2);
        let prev = f.live.parent().unwrap().join("relay.prev");
        assert!(prev.is_dir());
        assert_eq!(std::fs::read_to_string(prev.join("app.txt")).unwrap(), "v1\n");
        assert_eq!(git(&prev, &["rev-parse", "HEAD"]), f.v1);
    }

    #[test]
    fn test_rollback_swaps_and_second_rollback_swaps_back() {
        let f = Fixture::setup();
        assert_eq!(f.run(&[f.bundle.to_str().unwrap()], Some(&f.live)).0, 0);
        let (code, stdout, stderr) = f.run(&["--rollback"], Some(&f.live));
        assert_eq!(code, 0, "{stderr}");
        assert!(stdout.contains("rolled back"), "{stdout}");
        assert_eq!(f.live_content(), "v1\n");
        assert_eq!(f.live_head(), f.v1);
        let prev = f.live.parent().unwrap().join("relay.prev");
        assert_eq!(std::fs::read_to_string(prev.join("app.txt")).unwrap(), "v2\n");
        assert_eq!(f.run(&["--rollback"], Some(&f.live)).0, 0);
        assert_eq!(f.live_content(), "v2\n");
        assert_eq!(f.live_head(), f.v2);
    }

    #[test]
    fn test_rollback_without_previous_refuses() {
        let f = Fixture::setup();
        let (code, _, stderr) = f.run(&["--rollback"], Some(&f.live));
        assert_eq!(code, 1);
        assert!(stderr.contains("no previous tree"), "{stderr}");
        assert_eq!(f.live_content(), "v1\n");
    }

    #[test]
    fn test_missing_bundle_is_usage_error() {
        let f = Fixture::setup();
        let missing = f._tmp.path().join("nope.bundle");
        let (code, _, stderr) = f.run(&[missing.to_str().unwrap()], Some(&f.live));
        assert_eq!(code, 2);
        assert!(stderr.contains("usage"), "{stderr}");
        assert_eq!(f.live_content(), "v1\n");
        assert!(!f.live.parent().unwrap().join("relay.prev").exists());
    }

    #[test]
    fn test_corrupt_bundle_refuses_and_leaves_target() {
        let f = Fixture::setup();
        let bad = f._tmp.path().join("bad.bundle");
        std::fs::write(&bad, "this is not a git bundle\n").unwrap();
        let (code, _, _) = f.run(&[bad.to_str().unwrap()], Some(&f.live));
        assert_ne!(code, 0);
        assert_eq!(f.live_content(), "v1\n");
        assert_eq!(f.live_head(), f.v1);
        assert!(!f.live.parent().unwrap().join("relay.prev").exists());
    }

    #[test]
    fn test_non_git_target_refuses() {
        let f = Fixture::setup();
        let plain = f._tmp.path().join("plain");
        std::fs::create_dir_all(&plain).unwrap();
        let (code, _, stderr) = f.run(&[f.bundle.to_str().unwrap()], Some(&plain));
        assert_eq!(code, 1);
        assert!(stderr.contains("not a git checkout"), "{stderr}");
    }

    #[test]
    fn test_no_args_without_hook_exits_before_touching_target() {
        let f = Fixture::setup();
        let mut cmd = Command::new("sh");
        cmd.arg(script_path()).env_remove("METAOS_RELAY_ROOT");
        // Ensure a clean environment even if the runner exports the hook.
        let out = cmd.output().expect("script failed to spawn");
        assert_eq!(out.status.code(), Some(2));
        let stderr = String::from_utf8_lossy(&out.stderr);
        assert!(stderr.contains("usage"), "{stderr}");
        assert_eq!(f.live_content(), "v1\n");
    }

    #[test]
    fn test_script_defaults_to_opt_relay_and_names_hook() {
        let text = std::fs::read_to_string(script_path()).unwrap();
        assert!(text.contains("TARGET=${METAOS_RELAY_ROOT:-/opt/relay}"));
        assert!(text.contains("METAOS_RELAY_ROOT"));
    }

    #[test]
    fn test_readme_documents_rollback() {
        let text = std::fs::read_to_string(readme_path()).unwrap();
        assert!(text.contains("metaos-update --rollback"));
        assert!(text.contains("second"));
        assert!(text.contains("swaps back"));
    }
}
