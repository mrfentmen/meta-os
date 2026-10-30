//! Shared machinery for the audio check scripts
//! (`boot_audio_check.py`, `dem018_local_check.py`,
//! `final_mix_check.py`): each Python file carries its own copy
//! of `check` / `run` / `probe_duration` / `volumes`; the ports
//! share this one implementation of the same shapes.
//!
//! The subprocess seam is the `CmdRunner` trait — the real runner
//! is `std::process::Command`; tests drive the parsing and check
//! logic with scripted tool output. The Python timeout is
//! enforced by a kill-after-deadline wait, like subprocess.

use std::io::Read;
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

/// (returncode, stdout, stderr) — the subprocess.run result shape.
#[derive(Debug, Clone, PartialEq)]
pub struct CmdOut {
    pub code: i32,
    pub stdout: String,
    pub stderr: String,
}

pub trait CmdRunner {
    fn run(&self, argv: &[&str], timeout_s: u64) -> CmdOut;
}

/// The real runner: spawn, capture, kill after the deadline.
pub struct SystemRunner;

impl CmdRunner for SystemRunner {
    fn run(&self, argv: &[&str], timeout_s: u64) -> CmdOut {
        let spawned = Command::new(argv[0])
            .args(&argv[1..])
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn();
        let mut child = match spawned {
            Ok(child) => child,
            Err(err) => {
                return CmdOut {
                    code: -1,
                    stdout: String::new(),
                    stderr: format!("{}", err),
                }
            }
        };
        let deadline = Instant::now() + Duration::from_secs(timeout_s);
        let status = loop {
            match child.try_wait() {
                Ok(Some(status)) => break status,
                Ok(None) => {
                    if Instant::now() > deadline {
                        let _ = child.kill();
                        break child.wait().expect("wait after kill");
                    }
                    std::thread::sleep(Duration::from_millis(10));
                }
                Err(err) => {
                    return CmdOut {
                        code: -1,
                        stdout: String::new(),
                        stderr: format!("{}", err),
                    }
                }
            }
        };
        let mut stdout = String::new();
        let mut stderr = String::new();
        if let Some(mut out) = child.stdout.take() {
            let _ = out.read_to_string(&mut stdout);
        }
        if let Some(mut err) = child.stderr.take() {
            let _ = err.read_to_string(&mut stderr);
        }
        CmdOut {
            code: status.code().unwrap_or(-1),
            stdout,
            stderr,
        }
    }
}

/// The scripts' FAILURES list + printed lines.
#[derive(Debug, Default)]
pub struct CheckLog {
    pub lines: Vec<String>,
    pub failures: Vec<String>,
}

impl CheckLog {
    /// `check(name, ok, detail)` — prints PASS/FAIL, records fails.
    pub fn check(&mut self, name: &str, ok: bool, detail: &str) {
        self.lines
            .push(format!("{} {} {}", if ok { "PASS" } else { "FAIL" }, name, detail));
        if !ok {
            self.failures.push(name.to_string());
        }
    }

    pub fn print(&mut self, line: String) {
        self.lines.push(line);
    }
}

/// Python `repr(bytes)` for the 3-byte MP3 header detail.
pub fn py_bytes_repr(bytes: &[u8]) -> String {
    let mut out = String::from("b'");
    for byte in bytes {
        match byte {
            b'\'' => out.push_str("\\'"),
            b'\\' => out.push_str("\\\\"),
            0x20..=0x7E => out.push(*byte as char),
            _ => out.push_str(&format!("\\x{:02x}", byte)),
        }
    }
    out.push('\'');
    out
}

/// First 3 bytes of a file (the scripts' MP3 header read).
pub fn read_head3(path: &str) -> std::io::Result<Vec<u8>> {
    let mut file = std::fs::File::open(path)?;
    let mut buf = Vec::new();
    file.read_to_end(&mut buf)?;
    buf.truncate(3);
    Ok(buf)
}

/// `probe_duration`: ffprobe format=duration, parsed from stdout.
/// Err mirrors the source's RuntimeError("no duration for ...").
/// Each script's own subprocess timeout rides along (120 in
/// boot_audio_check/final_mix_check, 180 in dem018_local_check).
pub fn probe_duration<R: CmdRunner>(
    runner: &R,
    path: &str,
    timeout_s: u64,
) -> Result<f64, String> {
    let result = runner.run(
        &[
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1",
            path,
        ],
        timeout_s,
    );
    for line in result.stdout.lines() {
        if let Some(rest) = line.strip_prefix("duration=") {
            return rest
                .parse::<f64>()
                .map_err(|_| format!("no duration for {}", path));
        }
    }
    Err(format!("no duration for {}", path))
}

/// Parse one `name: <float> dB` figure from ffmpeg's volumedetect
/// stderr (the sources' `re.search(r"name:\s*(-?[\d.]+) dB")`).
fn volume_figure(stderr: &str, name: &str) -> Option<f64> {
    let needle = format!("{}:", name);
    let start = stderr.find(&needle)? + needle.len();
    let rest = &stderr[start..];
    let rest = rest.trim_start();
    let mut end = 0;
    for (i, ch) in rest.char_indices() {
        if ch.is_ascii_digit() || ch == '.' || (ch == '-' && i == 0) {
            end = i + ch.len_utf8();
        } else {
            break;
        }
    }
    if end == 0 {
        return None;
    }
    let number: f64 = rest[..end].parse().ok()?;
    if !rest[end..].starts_with(" dB") {
        return None;
    }
    Some(number)
}

/// `volumes`: (mean_volume, max_volume) from volumedetect.
/// Err mirrors RuntimeError("no volumedetect output for ...").
/// Some scripts use a longer subprocess timeout; `timeout_s`
/// carries the caller's value.
pub fn volumes<R: CmdRunner>(
    runner: &R,
    path: &str,
    timeout_s: u64,
) -> Result<(f64, f64), String> {
    let result = runner.run(
        &[
            "ffmpeg", "-i", path, "-af", "volumedetect", "-vn", "-sn", "-dn", "-f", "null",
            "/dev/null",
        ],
        timeout_s,
    );
    let mean = volume_figure(&result.stderr, "mean_volume");
    let maximum = volume_figure(&result.stderr, "max_volume");
    match (mean, maximum) {
        (Some(mean), Some(maximum)) => Ok((mean, maximum)),
        _ => Err(format!("no volumedetect output for {}", path)),
    }
}

/// `max_volume` only (dem018's variant).
pub fn max_volume<R: CmdRunner>(runner: &R, path: &str, timeout_s: u64) -> Result<f64, String> {
    let result = runner.run(
        &[
            "ffmpeg", "-i", path, "-af", "volumedetect", "-vn", "-sn", "-dn", "-f", "null",
            "/dev/null",
        ],
        timeout_s,
    );
    volume_figure(&result.stderr, "max_volume")
        .ok_or_else(|| format!("no volumedetect output for {}", path))
}

/// The decode probe both scripts run per file.
pub fn decodes_clean<R: CmdRunner>(runner: &R, path: &str, timeout_s: u64) -> CmdOut {
    runner.run(
        &["ffmpeg", "-v", "error", "-i", path, "-f", "null", "-"],
        timeout_s,
    )
}

/// First 200 chars of a stripped stderr (the scripts' detail cap).
pub fn stderr_head(stderr: &str) -> String {
    stderr.trim().chars().take(200).collect()
}
