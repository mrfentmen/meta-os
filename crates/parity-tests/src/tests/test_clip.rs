//! T034 [B31] port of `os/tests/test_clip.py` — `ClipboardHelperTest` roots.
//!
//! Clipboard tool fallbacks (`os/clipboard.py`): first working tool wins,
//! runtime failures fall through, missing tools are LOUD (`ClipboardError`
//! naming the fallback list / every attempt). The runner is injected so
//! tests run fully offline (mirrors the Python `FakeToolbox`).
//!
//! Blocked (need excluded `relay_common` store + `send`/`paste` CLIs,
//! named not dropped): all `ClipSendTest` / `ClipPullTest` flows — clip
//! store+envelope, latest-wins, 20-history cap, empty/no-tool/combination
//! refusals, cross-machine round trip, `--stdout` dump, no-clip marker,
//! corrupt-hash / missing-blob refusals, paste tool fallback, per-nick
//! isolation.

use std::path::PathBuf;

pub const CASES: &[&str] = &[
    "read uses first working tool",
    "read falls through failing tool",
    "read no tools installed is loud",
    "read all tools fail is loud",
    "write returns tool name and sends data",
    "write no tools is loud",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[
    "ClipSendTest: clip stores blob and envelope (needs relay_common store + send CLI)",
    "ClipSendTest: latest wins (needs relay_common store + send CLI)",
    "ClipSendTest: history capped at 20 (needs relay_common store + send CLI)",
    "ClipSendTest: empty clipboard rejected (needs relay_common store + send CLI)",
    "ClipSendTest: no tool is loud (needs relay_common store + send CLI)",
    "ClipSendTest: combinations refused (needs send CLI arg parsing)",
    "ClipPullTest: round trip between machines (needs relay_common + paste CLI)",
    "ClipPullTest: stdout dumps raw bytes (needs relay_common + paste CLI)",
    "ClipPullTest: no clip prints marker (needs relay_common + paste CLI)",
    "ClipPullTest: corrupt hash rejected (needs relay_common blob store + paste CLI)",
    "ClipPullTest: missing blob rejected (needs relay_common blob store + paste CLI)",
    "ClipPullTest: no tool points at stdout (needs relay_common + paste CLI)",
    "ClipPullTest: per-nick isolation (needs relay_common + paste CLI)",
];

pub const READ_TOOLS: &[&[&str]] = &[
    &["xclip", "-selection", "clipboard", "-out"],
    &["xsel", "--clipboard", "--output"],
    &["pbpaste"],
    &["wl-paste", "--no-newline"],
    &["termux-clipboard-get"],
    &["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
];
pub const WRITE_TOOLS: &[&[&str]] = &[
    &["xclip", "-selection", "clipboard", "-in"],
    &["xsel", "--clipboard", "--input"],
    &["pbcopy"],
    &["wl-copy"],
    &["termux-clipboard-set"],
    &["powershell", "-NoProfile", "-Command", "$input | Set-Clipboard"],
];

#[derive(Debug, Clone, PartialEq)]
pub struct ClipboardError(pub String);

impl std::fmt::Display for ClipboardError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}
impl std::error::Error for ClipboardError {}

/// Tool execution seam (mirrors the Python `FakeToolbox` patch points).
pub trait Runner {
    fn installed(&self, cmd: &[&str]) -> bool;
    /// Returns `Ok(stdout)` or `Err(note)` for one attempt.
    fn attempt(&self, cmd: &[&str], data: Option<&[u8]>) -> Result<Vec<u8>, String>;
}

/// PATH-backed runner (production).
pub struct PathRunner;
impl PathRunner {
    fn which(name: &str) -> Option<PathBuf> {
        std::env::var_os("PATH").and_then(|p| {
            std::env::split_paths(&p).map(|d| d.join(name)).find(|c| c.is_file())
        })
    }
}
impl Runner for PathRunner {
    fn installed(&self, cmd: &[&str]) -> bool {
        Self::which(cmd[0]).is_some()
    }
    fn attempt(&self, cmd: &[&str], data: Option<&[u8]>) -> Result<Vec<u8>, String> {
        use std::io::Write;
        use std::process::Stdio;
        let mut child = std::process::Command::new(cmd[0])
            .args(&cmd[1..])
            .stdin(if data.is_some() { Stdio::piped() } else { Stdio::null() })
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| format!("{}: {e}", cmd[0]))?;
        if let Some(d) = data {
            child.stdin.take().unwrap().write_all(d).map_err(|e| format!("{}: {e}", cmd[0]))?;
        }
        let out = child.wait_with_output().map_err(|e| format!("{}: {e}", cmd[0]))?;
        if !out.status.success() {
            let err = String::from_utf8_lossy(&out.stderr).trim().chars().take(120).collect::<String>();
            let mut note = format!("{}: rc={}", cmd[0], out.status.code().unwrap_or(-1));
            if !err.is_empty() {
                note.push(' ');
                note.push_str(&err);
            }
            return Err(note);
        }
        Ok(out.stdout)
    }
}

pub fn clipboard_read<R: Runner>(runner: &R, tools: &[&[&str]]) -> Result<Vec<u8>, ClipboardError> {
    let mut attempts = vec![];
    for cmd in tools {
        if !runner.installed(cmd) {
            continue;
        }
        match runner.attempt(cmd, None) {
            Ok(out) => return Ok(out),
            Err(note) => attempts.push(note),
        }
    }
    if attempts.is_empty() {
        let names: Vec<_> = tools.iter().map(|c| c[0]).collect();
        return Err(ClipboardError(format!(
            "no clipboard tool found (looked for: {}) — install one, e.g. 'apt install xclip' (or wl-clipboard, xsel)",
            names.join(", ")
        )));
    }
    Err(ClipboardError(format!("clipboard read failed — {}", attempts.join("; "))))
}

pub fn clipboard_write<R: Runner>(runner: &R, data: &[u8], tools: &[&[&str]]) -> Result<String, ClipboardError> {
    let mut attempts = vec![];
    for cmd in tools {
        if !runner.installed(cmd) {
            continue;
        }
        match runner.attempt(cmd, Some(data)) {
            Ok(_) => return Ok(cmd[0].to_string()),
            Err(note) => attempts.push(note),
        }
    }
    if attempts.is_empty() {
        let names: Vec<_> = tools.iter().map(|c| c[0]).collect();
        return Err(ClipboardError(format!(
            "no clipboard tool found (looked for: {}) — install one, e.g. 'apt install xclip' (or wl-clipboard, xsel)",
            names.join(", ")
        )));
    }
    Err(ClipboardError(format!("clipboard write failed — {}", attempts.join("; "))))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;
    use std::sync::{Arc, Mutex};

    struct FakeTool {
        payload: Vec<u8>,
        fail: bool,
        received: Arc<Mutex<Vec<Vec<u8>>>>,
    }
    struct FakeBox {
        tools: HashMap<String, FakeTool>,
    }
    impl FakeBox {
        fn add(&mut self, name: &str, payload: &[u8], fail: bool) {
            self.tools.insert(name.into(), FakeTool {
                payload: payload.to_vec(), fail,
                received: Arc::new(Mutex::new(vec![])),
            });
        }
        fn received(&self, name: &str) -> Vec<Vec<u8>> {
            self.tools[name].received.lock().unwrap().clone()
        }
    }
    impl Runner for FakeBox {
        fn installed(&self, cmd: &[&str]) -> bool {
            self.tools.contains_key(cmd[0])
        }
        fn attempt(&self, cmd: &[&str], data: Option<&[u8]>) -> Result<Vec<u8>, String> {
            let t = self.tools.get(cmd[0]).unwrap();
            if t.fail {
                return Err(format!("{}: simulated tool failure", cmd[0]));
            }
            if let Some(d) = data {
                t.received.lock().unwrap().push(d.to_vec());
            }
            Ok(t.payload.clone())
        }
    }
    fn toolbox() -> FakeBox {
        FakeBox { tools: HashMap::new() }
    }

    #[test]
    fn test_read_uses_first_working_tool() {
        let mut b = toolbox();
        b.add("first", b"a", false);
        b.add("second", b"b", false);
        let tools: Vec<&[&str]> = vec![&["first"], &["second"]];
        assert_eq!(clipboard_read(&b, &tools).unwrap(), b"a");
    }

    #[test]
    fn test_read_falls_through_failing_tool() {
        let mut b = toolbox();
        b.add("bad", b"", true);
        b.add("good", b"ok", false);
        let tools: Vec<&[&str]> = vec![&["bad"], &["good"]];
        assert_eq!(clipboard_read(&b, &tools).unwrap(), b"ok");
    }

    #[test]
    fn test_read_no_tools_installed_is_loud() {
        let b = toolbox();
        let tools: Vec<&[&str]> = vec![&["nothing-here"], &["also-missing"]];
        let err = clipboard_read(&b, &tools).unwrap_err();
        assert!(err.0.contains("no clipboard tool found"), "{err}");
        assert!(err.0.contains("nothing-here"), "{err}");
        assert!(err.0.contains("install"), "{err}");
    }

    #[test]
    fn test_read_all_tools_fail_is_loud() {
        let mut b = toolbox();
        b.add("xclip", b"", true);
        b.add("xsel", b"", true);
        let tools: Vec<&[&str]> = vec![&["xclip"], &["xsel"]];
        let err = clipboard_read(&b, &tools).unwrap_err();
        assert!(err.0.contains("clipboard read failed"), "{err}");
        assert!(err.0.contains("xclip"), "{err}");
        assert!(err.0.contains("simulated tool failure"), "{err}");
    }

    #[test]
    fn test_write_returns_tool_name_and_sends_data() {
        let mut b = toolbox();
        b.add("writer", b"", false);
        let tools: Vec<&[&str]> = vec![&["writer"]];
        assert_eq!(clipboard_write(&b, b"hello", &tools).unwrap(), "writer");
        assert_eq!(b.received("writer"), vec![b"hello".to_vec()]);
    }

    #[test]
    fn test_write_no_tools_is_loud() {
        let b = toolbox();
        let tools: Vec<&[&str]> = vec![&["missing-tool"]];
        let err = clipboard_write(&b, b"x", &tools).unwrap_err();
        assert!(err.0.contains("no clipboard tool found"), "{err}");
    }
}
