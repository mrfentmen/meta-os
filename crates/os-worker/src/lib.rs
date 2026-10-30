//! Crate `os-worker` — Meta OS Rust rebuild skeleton (B00).
//!
//! Batch B22 — Worker runtime & drivers. Owner: Milo.
//! Source files this batch ports:
//! - `os/intel/drills/driver_heartbeat_bridge.py`
//! - `os/intel/drills/driver_stall.py`
//! - `os/intel/drills/driver_supervision.py`
//! - `os/mos/worker.py`
//! - `os/os/drivers/CONFORMANCE.md`
//! - `os/os/drivers/CONTRACT.md`
//! - `os/os/drivers/muse_driver.py`
//! - `os/os/drivers/run_driver.py`
//! - `os/os/drivers/stub_driver.py`
//! - `os/os/uplink/relay_uplink.py`
//! - `os/tests/test_intel_dispatch_worker.py`
//! - `os/tests/test_intel_drill_kill_worker.py`
//! - `os/tests/test_intel_driver_heartbeat_bridge.py`
//! - `os/tests/test_intel_driver_stall.py`
//! - `os/tests/test_intel_driver_supervision.py`
//! - `os/tests/test_os_driver_contract.py`
//! - `os/tests/test_os_driver_muse.py`
//! - `os/tests/test_os_worker_units.py`
//! - `os/tests/test_os_workers_slice.py`
//!
//! Skeleton only: no logic yet. The Python/Node sources listed above are
//! the spec — port behavior, do not redesign. See BATCHES.md for the
//! compile gates and the parity rule.
//!
//! B22 implementation notes (read before extending this crate):
//!
//! - Port behavior, do not redesign. Section markers below mirror the
//!   Python source layout, one section per source module.
//! - Std-only Rust: no external crate dependency is added.
//! - Live-behavior boundary (never faked): the drivers below really
//!   spawn child processes, really write `driver.log`, and really
//!   diff before/after snapshots. The MOS worker loop's Redis/bus
//!   side (`relay_common`, `jobs`, `mos/capabilities`) is NOT ported
//!   here: [`Worker`] drives that side through the [`WorkerBackend`]
//!   trait, so the loop's decision logic is real and testable while
//!   no bus post, claim, or lease renewal is ever faked. The
//!   stall detectors in the `stall` section are the drill-facing
//!   view of WDG-002/WDG-003 semantics (the canonical watchdog port
//!   is B21's `os-supervisor` crate); they exist here so the B22
//!   drill assertions run against the documented detector rules.
//! - The acceptance check parser (`accept` section) is a
//!   driver-local port of the checks `mos/acceptance.py` performs
//!   for driver specs; the canonical acceptance port belongs to
//!   B31. Only the checks the drivers need are ported.
//! - `MuseDriver::wait` joins the stdout-reader thread
//!   unconditionally, where Python joins it with a 5s timeout and
//!   proceeds regardless. A child that has exited closes its
//!   stdout, so the reader always reaches EOF; the deviation is
//!   noted here rather than papered over.
//! - `StubDriver`/`MuseDriver` send SIGTERM through the `kill`
//!   utility (std Rust exposes no signal API); if spawning `kill`
//!   fails, the child is killed directly. The signal delivered is
//!   a real SIGTERM either way.
//! - Python tracebacks do not exist in Rust: a crashing handler
//!   reports its caller-supplied message, truncated to the same
//!   400-character tail the Python loop applies to its traceback.

// ============================================================
// Section: SHA-256 / HMAC (supporting code, std-only)
// ============================================================

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

/// SHA-256 round constants (FIPS 180-4, first 32 bits of the cube
/// roots of the first 64 primes).
const SHA256_K: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
    0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
    0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
    0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
    0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
    0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

/// SHA-256 initial hash values (first 32 bits of the square roots
/// of the first 8 primes).
const SHA256_H0: [u32; 8] = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c,
    0x1f83d9ab, 0x5be0cd19,
];

/// Compute the SHA-256 digest of `data`.
///
/// This is supporting code only: the uplink signs intakes with
/// HMAC-SHA256 and the contract-doc pin test checksums the
/// embedded docs, and std Rust ships no SHA-256.
pub fn sha256(data: &[u8]) -> [u8; 32] {
    let bit_len = (data.len() as u64).wrapping_mul(8);
    let mut msg = data.to_vec();
    msg.push(0x80);
    while msg.len() % 64 != 56 {
        msg.push(0);
    }
    msg.extend_from_slice(&bit_len.to_be_bytes());
    let mut h = SHA256_H0;
    for chunk in msg.chunks_exact(64) {
        let mut w = [0u32; 64];
        for i in 0..16 {
            w[i] = u32::from_be_bytes([
                chunk[i * 4],
                chunk[i * 4 + 1],
                chunk[i * 4 + 2],
                chunk[i * 4 + 3],
            ]);
        }
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7)
                ^ w[i - 15].rotate_right(18)
                ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17)
                ^ w[i - 2].rotate_right(19)
                ^ (w[i - 2] >> 10);
            w[i] = w[i - 16]
                .wrapping_add(s0)
                .wrapping_add(w[i - 7])
                .wrapping_add(s1);
        }
        let (mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut hh) =
            (h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7]);
        for i in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let t1 = hh
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(SHA256_K[i])
                .wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let t2 = s0.wrapping_add(maj);
            hh = g;
            g = f;
            f = e;
            e = d.wrapping_add(t1);
            d = c;
            c = b;
            b = a;
            a = t1.wrapping_add(t2);
        }
        h[0] = h[0].wrapping_add(a);
        h[1] = h[1].wrapping_add(b);
        h[2] = h[2].wrapping_add(c);
        h[3] = h[3].wrapping_add(d);
        h[4] = h[4].wrapping_add(e);
        h[5] = h[5].wrapping_add(f);
        h[6] = h[6].wrapping_add(g);
        h[7] = h[7].wrapping_add(hh);
    }
    let mut out = [0u8; 32];
    for i in 0..8 {
        out[i * 4..i * 4 + 4].copy_from_slice(&h[i].to_be_bytes());
    }
    out
}

/// Lowercase hex encoding of the SHA-256 digest of `data`.
pub fn sha256_hex(data: &[u8]) -> String {
    sha256(data).iter().map(|b| format!("{b:02x}")).collect()
}

/// HMAC-SHA256 of `msg` under `key` (RFC 2104).
pub fn hmac_sha256_hex(key: &[u8], msg: &[u8]) -> String {
    let mut k = [0u8; 64];
    if key.len() > 64 {
        let d = sha256(key);
        k[..32].copy_from_slice(&d);
    } else {
        k[..key.len()].copy_from_slice(key);
    }
    let mut ipad = [0u8; 64];
    let mut opad = [0u8; 64];
    for i in 0..64 {
        ipad[i] = k[i] ^ 0x36;
        opad[i] = k[i] ^ 0x5c;
    }
    let mut inner = ipad.to_vec();
    inner.extend_from_slice(msg);
    let inner_hash = sha256(&inner);
    let mut outer = opad.to_vec();
    outer.extend_from_slice(&inner_hash);
    sha256(&outer).iter().map(|b| format!("{b:02x}")).collect()
}

/// Current Unix time in seconds as a float, for heartbeat `ts`
/// records (Python `time.time()`).
pub fn now_secs_f64() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

/// Truncate a string to its last `n` characters (Python `s[-n:]`).
pub fn tail_chars(s: &str, n: usize) -> String {
    let chars: Vec<char> = s.chars().collect();
    if chars.len() <= n {
        s.to_string()
    } else {
        chars[chars.len() - n..].iter().collect()
    }
}

/// Truncate a string to its first `n` characters (Python `s[:n]`).
pub fn head_chars(s: &str, n: usize) -> String {
    s.chars().take(n).collect()
}

// ============================================================
// Section: minimal JSON (supporting code for run_driver)
// ============================================================

/// A minimal JSON value, enough to read a driver job spec file
/// and to render an artifacts record. Std Rust ships no JSON
/// parser, and this crate adds no dependency.
#[derive(Debug, Clone, PartialEq)]
pub enum JsonValue {
    /// JSON null.
    Null,
    /// JSON boolean.
    Bool(bool),
    /// JSON number, kept in its source spelling.
    Number(String),
    /// JSON string.
    Str(String),
    /// JSON array.
    Array(Vec<JsonValue>),
    /// JSON object, in source order.
    Object(Vec<(String, JsonValue)>),
}

impl JsonValue {
    /// Look up a key in a JSON object, or `None`.
    pub fn get(&self, key: &str) -> Option<&JsonValue> {
        match self {
            JsonValue::Object(pairs) => pairs
                .iter()
                .find(|(k, _)| k == key)
                .map(|(_, v)| v),
            _ => None,
        }
    }

    /// The value as a string, if it is one.
    pub fn as_str(&self) -> Option<&str> {
        match self {
            JsonValue::Str(s) => Some(s),
            _ => None,
        }
    }

    /// The value as an integer, if its number spelling parses.
    pub fn as_i64(&self) -> Option<i64> {
        match self {
            JsonValue::Number(n) => n.parse::<i64>().ok(),
            _ => None,
        }
    }

    /// The value as a list of strings, if it is an array of strings.
    pub fn as_str_list(&self) -> Option<Vec<String>> {
        match self {
            JsonValue::Array(items) => {
                let mut out = Vec::new();
                for item in items {
                    out.push(item.as_str()?.to_string());
                }
                Some(out)
            }
            _ => None,
        }
    }

    /// Render this value as compact JSON.
    pub fn to_json(&self) -> String {
        match self {
            JsonValue::Null => "null".to_string(),
            JsonValue::Bool(b) => b.to_string(),
            JsonValue::Number(n) => n.clone(),
            JsonValue::Str(s) => json_escape(s),
            JsonValue::Array(items) => {
                let parts: Vec<String> = items.iter().map(|v| v.to_json()).collect();
                format!("[{}]", parts.join(","))
            }
            JsonValue::Object(pairs) => {
                let parts: Vec<String> = pairs
                    .iter()
                    .map(|(k, v)| format!("{}:{}", json_escape(k), v.to_json()))
                    .collect();
                format!("{{{}}}", parts.join(","))
            }
        }
    }
}

/// Escape a string as a JSON string literal, including the quotes.
pub fn json_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

struct JsonParser<'a> {
    bytes: &'a [u8],
    pos: usize,
}

impl<'a> JsonParser<'a> {
    fn ws(&mut self) {
        while self.pos < self.bytes.len()
            && matches!(self.bytes[self.pos], b' ' | b'\t' | b'\n' | b'\r')
        {
            self.pos += 1;
        }
    }

    fn peek(&self) -> Option<u8> {
        self.bytes.get(self.pos).copied()
    }

    fn expect(&mut self, b: u8) -> Result<(), String> {
        if self.peek() == Some(b) {
            self.pos += 1;
            Ok(())
        } else {
            Err(format!("expected '{}' at byte {}", b as char, self.pos))
        }
    }

    fn lit(&mut self, s: &str) -> Result<(), String> {
        if self.bytes.len() >= self.pos + s.len()
            && &self.bytes[self.pos..self.pos + s.len()] == s.as_bytes()
        {
            self.pos += s.len();
            Ok(())
        } else {
            Err(format!("expected '{s}' at byte {}", self.pos))
        }
    }

    fn value(&mut self) -> Result<JsonValue, String> {
        self.ws();
        match self.peek() {
            Some(b'{') => {
                self.pos += 1;
                let mut pairs = Vec::new();
                self.ws();
                if self.peek() == Some(b'}') {
                    self.pos += 1;
                    return Ok(JsonValue::Object(pairs));
                }
                loop {
                    self.ws();
                    let key = match self.value()? {
                        JsonValue::Str(s) => s,
                        _ => return Err("object key must be a string".to_string()),
                    };
                    self.ws();
                    self.expect(b':')?;
                    let val = self.value()?;
                    pairs.push((key, val));
                    self.ws();
                    match self.peek() {
                        Some(b',') => {
                            self.pos += 1;
                        }
                        Some(b'}') => {
                            self.pos += 1;
                            break;
                        }
                        _ => return Err(format!("expected ',' or '}}' at byte {}", self.pos)),
                    }
                }
                Ok(JsonValue::Object(pairs))
            }
            Some(b'[') => {
                self.pos += 1;
                let mut items = Vec::new();
                self.ws();
                if self.peek() == Some(b']') {
                    self.pos += 1;
                    return Ok(JsonValue::Array(items));
                }
                loop {
                    items.push(self.value()?);
                    self.ws();
                    match self.peek() {
                        Some(b',') => {
                            self.pos += 1;
                        }
                        Some(b']') => {
                            self.pos += 1;
                            break;
                        }
                        _ => return Err(format!("expected ',' or ']' at byte {}", self.pos)),
                    }
                }
                Ok(JsonValue::Array(items))
            }
            Some(b'"') => Ok(JsonValue::Str(self.string()?)),
            Some(b't') => {
                self.lit("true")?;
                Ok(JsonValue::Bool(true))
            }
            Some(b'f') => {
                self.lit("false")?;
                Ok(JsonValue::Bool(false))
            }
            Some(b'n') => {
                self.lit("null")?;
                Ok(JsonValue::Null)
            }
            Some(c) if c == b'-' || c.is_ascii_digit() => {
                let start = self.pos;
                if self.peek() == Some(b'-') {
                    self.pos += 1;
                }
                while matches!(self.peek(), Some(c) if c.is_ascii_digit()) {
                    self.pos += 1;
                }
                if self.peek() == Some(b'.') {
                    self.pos += 1;
                    while matches!(self.peek(), Some(c) if c.is_ascii_digit()) {
                        self.pos += 1;
                    }
                }
                if matches!(self.peek(), Some(b'e') | Some(b'E')) {
                    self.pos += 1;
                    if matches!(self.peek(), Some(b'+') | Some(b'-')) {
                        self.pos += 1;
                    }
                    while matches!(self.peek(), Some(c) if c.is_ascii_digit()) {
                        self.pos += 1;
                    }
                }
                let text = std::str::from_utf8(&self.bytes[start..self.pos])
                    .map_err(|e| e.to_string())?
                    .to_string();
                Ok(JsonValue::Number(text))
            }
            _ => Err(format!("unexpected byte at {}", self.pos)),
        }
    }

    fn string(&mut self) -> Result<String, String> {
        self.expect(b'"')?;
        let mut out = String::new();
        loop {
            let c = self.peek().ok_or("unterminated string")?;
            self.pos += 1;
            match c {
                b'"' => break,
                b'\\' => {
                    let e = self.peek().ok_or("unterminated escape")?;
                    self.pos += 1;
                    match e {
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        b'/' => out.push('/'),
                        b'b' => out.push('\u{0008}'),
                        b'f' => out.push('\u{000C}'),
                        b'n' => out.push('\n'),
                        b'r' => out.push('\r'),
                        b't' => out.push('\t'),
                        b'u' => {
                            let hex = self.bytes.get(self.pos..self.pos + 4).ok_or(
                                "truncated \\u escape",
                            )?;
                            let hex = std::str::from_utf8(hex)
                                .map_err(|_| "bad \\u escape")?;
                            let cp = u32::from_str_radix(hex, 16)
                                .map_err(|_| "bad \\u escape")?;
                            self.pos += 4;
                            // Surrogate pairs: combine with a following \u escape.
                            if (0xD800..0xDC00).contains(&cp)
                                && self.bytes.get(self.pos..self.pos + 2) == Some(b"\\u")
                            {
                                let hex2 = self.bytes.get(self.pos + 2..self.pos + 6)
                                    .ok_or("truncated surrogate")?;
                                let hex2 = std::str::from_utf8(hex2)
                                    .map_err(|_| "bad surrogate")?;
                                let lo = u32::from_str_radix(hex2, 16)
                                    .map_err(|_| "bad surrogate")?;
                                if (0xDC00..0xE000).contains(&lo) {
                                    self.pos += 6;
                                    let c = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
                                    out.push(char::from_u32(c).unwrap_or('\u{FFFD}'));
                                } else {
                                    out.push('\u{FFFD}');
                                }
                            } else {
                                out.push(char::from_u32(cp).unwrap_or('\u{FFFD}'));
                            }
                        }
                        _ => return Err("bad escape".to_string()),
                    }
                }
                _ => {
                    // Copy one UTF-8 character starting at this byte.
                    let start = self.pos - 1;
                    let len = if c < 0x80 {
                        1
                    } else if c >= 0xF0 {
                        4
                    } else if c >= 0xE0 {
                        3
                    } else {
                        2
                    };
                    let end = (start + len).min(self.bytes.len());
                    out.push_str(
                        std::str::from_utf8(&self.bytes[start..end])
                            .map_err(|_| "bad utf-8 in string")?,
                    );
                    self.pos = end;
                }
            }
        }
        Ok(out)
    }
}

/// Parse a JSON document. Trailing non-whitespace is an error.
pub fn parse_json(text: &str) -> Result<JsonValue, String> {
    let mut p = JsonParser {
        bytes: text.as_bytes(),
        pos: 0,
    };
    let v = p.value()?;
    p.ws();
    if p.pos != text.len() {
        return Err(format!("trailing data at byte {}", p.pos));
    }
    Ok(v)
}

// ============================================================
// Section: acceptance checks (os/mos/acceptance.py, driver view)
// ============================================================
// Driver-local port of the accept-line checks the drivers need.
// The canonical acceptance port belongs to B31; this section
// mirrors parse_accept / verify / run_checks only for the four
// check kinds, so a driver can validate a spec at start time
// and verify it from disk at artifacts time, exactly as the
// Python drivers do through mos/acceptance.

/// One parsed acceptance check: (kind, argument).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AcceptCheck {
    /// Check kind: `file-exists`, `tests-pass`, `command-ok`, or `contains`.
    pub kind: String,
    /// Check argument, exactly as written after the first `:`.
    pub arg: String,
}

/// One acceptance result, mirroring the Python result dicts.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AcceptResult {
    /// The check as rendered, e.g. `file-exists: out.txt`.
    pub check: String,
    /// Whether the check held.
    pub ok: bool,
    /// Human detail, e.g. `found`, `missing`, `exit=0 :: ...`.
    pub detail: String,
}

/// Parse accept text into checks, raising a message on bad lines.
///
/// Mirrors `mos/acceptance.parse_accept`: blank lines and `#`
/// comments are skipped; every other line needs a `:` separator,
/// a known kind, a non-empty argument, and for `contains` a
/// `path :: substring` argument.
pub fn parse_accept(text: &str) -> Result<Vec<AcceptCheck>, String> {
    let mut checks = Vec::new();
    for (lineno, raw) in text.split('\n').enumerate() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let Some(colon) = line.find(':') else {
            return Err(format!("line {}: no ':' separator: {line:?}", lineno + 1));
        };
        let kind = line[..colon].trim().to_lowercase();
        let arg = line[colon + 1..].trim().to_string();
        if !matches!(
            kind.as_str(),
            "file-exists" | "tests-pass" | "command-ok" | "contains"
        ) {
            return Err(format!("line {}: unknown check {kind:?}", lineno + 1));
        }
        if arg.is_empty() {
            return Err(format!("line {}: empty argument", lineno + 1));
        }
        if kind == "contains" && !arg.contains("::") {
            return Err(format!(
                "line {}: contains needs 'path :: substring'",
                lineno + 1
            ));
        }
        checks.push(AcceptCheck { kind, arg });
    }
    Ok(checks)
}

fn run_shell(cmd: &str, workdir: &Path) -> (i32, String) {
    match Command::new("sh").arg("-c").arg(cmd).current_dir(workdir).output() {
        Ok(out) => {
            let mut text = String::from_utf8_lossy(&out.stdout).into_owned();
            text.push_str(&String::from_utf8_lossy(&out.stderr));
            let code = out.status.code().unwrap_or(1);
            // Python keeps the last 2000 chars of combined output.
            let tail = tail_chars(&text, 2000);
            (code, tail)
        }
        Err(e) => (1, format!("runner error: {e}")),
    }
}

/// Run parsed checks against a workdir. Returns result dicts.
///
/// Mirrors `mos/acceptance.run_checks`: `file-exists` checks
/// existence, `contains` checks a substring in a file,
/// `command-ok` runs the argument through the shell,
/// `tests-pass` runs `python3 -m unittest <module>`.
pub fn run_accept_checks(checks: &[AcceptCheck], workdir: &Path) -> Vec<AcceptResult> {
    let mut results = Vec::new();
    for check in checks {
        match check.kind.as_str() {
            "file-exists" => {
                let ok = workdir.join(&check.arg).exists();
                results.push(AcceptResult {
                    check: format!("file-exists: {}", check.arg),
                    ok,
                    detail: if ok { "found".to_string() } else { "missing".to_string() },
                });
            }
            "tests-pass" => {
                let module = check.arg.trim().strip_suffix(".py").unwrap_or(check.arg.trim());
                let module = module.replace('/', ".").replace('\\', ".");
                let (code, out) = match Command::new("python3")
                    .arg("-m")
                    .arg("unittest")
                    .arg(&module)
                    .current_dir(workdir)
                    .output()
                {
                    Ok(out) => {
                        let mut text = String::from_utf8_lossy(&out.stdout).into_owned();
                        text.push_str(&String::from_utf8_lossy(&out.stderr));
                        (out.status.code().unwrap_or(1), tail_chars(&text, 2000))
                    }
                    Err(e) => (127, format!("command not found: {e}")),
                };
                results.push(AcceptResult {
                    check: format!("tests-pass: {}", check.arg),
                    ok: code == 0,
                    detail: format!("exit={code} :: {}", tail_chars(&out, 500)),
                });
            }
            "command-ok" => {
                let (code, out) = run_shell(&check.arg, workdir);
                results.push(AcceptResult {
                    check: format!("command-ok: {}", check.arg),
                    ok: code == 0,
                    detail: format!("exit={code} :: {}", tail_chars(&out, 500)),
                });
            }
            "contains" => {
                let (path, needle) = match check.arg.split_once("::") {
                    Some((p, n)) => (p.trim(), n.trim()),
                    None => ("", ""),
                };
                let full = workdir.join(path);
                match std::fs::read_to_string(&full) {
                    Ok(content) => {
                        let ok = content.contains(needle);
                        results.push(AcceptResult {
                            check: format!("contains: {}", check.arg),
                            ok,
                            detail: if ok {
                                "substring present".to_string()
                            } else {
                                "substring absent".to_string()
                            },
                        });
                    }
                    Err(e) => results.push(AcceptResult {
                        check: format!("contains: {}", check.arg),
                        ok: false,
                        detail: format!("read error: {e}"),
                    }),
                }
            }
            _ => unreachable!("parse_accept only yields known kinds"),
        }
    }
    results
}

/// Verify accept text against a workdir: `(ok, results)`.
///
/// Mirrors `mos/acceptance.verify`: empty accept text (or text
/// that parses to no checks) verifies with a single
/// `(no acceptance criteria)` note; unparseable text fails with
/// a `(parse)` result.
pub fn verify_accept(accept_text: &str, workdir: &Path) -> (bool, Vec<AcceptResult>) {
    if accept_text.trim().is_empty() {
        return (
            true,
            vec![AcceptResult {
                check: "(no acceptance criteria)".to_string(),
                ok: true,
                detail: "nothing to verify".to_string(),
            }],
        );
    }
    let checks = match parse_accept(accept_text) {
        Ok(c) => c,
        Err(e) => {
            return (
                false,
                vec![AcceptResult {
                    check: "(parse)".to_string(),
                    ok: false,
                    detail: e,
                }],
            );
        }
    };
    if checks.is_empty() {
        return (
            true,
            vec![AcceptResult {
                check: "(no acceptance criteria)".to_string(),
                ok: true,
                detail: "nothing to verify".to_string(),
            }],
        );
    }
    let results = run_accept_checks(&checks, workdir);
    let ok = results.iter().all(|r| r.ok);
    (ok, results)
}

// ============================================================
// Section: driver contract (os/os/drivers/stub_driver.py shared
// core, os/os/drivers/CONTRACT.md, os/os/drivers/CONFORMANCE.md)
// ============================================================

/// Name of the driver log file inside the workdir.
pub const LOG_NAME: &str = "driver.log";

/// A driver failure, mirroring the Python exception hierarchy:
/// `DriverError` is the base, with `UnsignedSpecError`,
/// `BadSpecError`, and `NotStartedError` as distinct cases.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DriverError {
    /// Generic contract violation or driver failure.
    Driver(String),
    /// `start()` was given a spec without a signature.
    Unsigned(String),
    /// `start()` was given a malformed spec or command.
    BadSpec(String),
    /// An operation needs a started driver and has none.
    NotStarted(String),
}

impl DriverError {
    /// The message text, as Python's `str(exc)`.
    pub fn message(&self) -> &str {
        match self {
            DriverError::Driver(m)
            | DriverError::Unsigned(m)
            | DriverError::BadSpec(m)
            | DriverError::NotStarted(m) => m,
        }
    }

    /// True for the unsigned-spec case (C1).
    pub fn is_unsigned(&self) -> bool {
        matches!(self, DriverError::Unsigned(_))
    }

    /// True for the malformed-spec case (C2/C3).
    pub fn is_bad_spec(&self) -> bool {
        matches!(self, DriverError::BadSpec(_))
    }

    /// True for the before-start case (C4).
    pub fn is_not_started(&self) -> bool {
        matches!(self, DriverError::NotStarted(_))
    }
}

impl std::fmt::Display for DriverError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.message())
    }
}

impl std::error::Error for DriverError {}

/// A job spec in the FND/DSP spec format the drivers accept.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct JobSpec {
    /// Job id, a non-empty string.
    pub id: String,
    /// Job title, a non-empty string.
    pub title: String,
    /// Job spec text, a non-empty string.
    pub spec: String,
    /// Owned file list, non-empty, each path non-empty.
    pub files: Vec<String>,
    /// Acceptance lines; empty when the spec carries none.
    pub accept: String,
    /// Job signature; `None` (or empty) means unsigned.
    pub sig: Option<String>,
    /// Attempt budget; defaults to 3 when the spec omits it.
    pub max_attempts: i64,
}

impl JobSpec {
    /// Build a spec from its fields, defaulting `accept` to `""`
    /// and `max_attempts` to 3, as `validate_spec` does.
    pub fn new(
        id: &str,
        title: &str,
        spec: &str,
        files: Vec<String>,
        accept: &str,
        sig: Option<&str>,
    ) -> JobSpec {
        JobSpec {
            id: id.to_string(),
            title: title.to_string(),
            spec: spec.to_string(),
            files,
            accept: accept.to_string(),
            sig: sig.map(|s| s.to_string()),
            max_attempts: 3,
        }
    }
}

/// Validate a job spec against the contract. Returns a copy with
/// `max_attempts` defaulted to 3.
///
/// Raises `Unsigned` when the signature is missing or empty,
/// `BadSpec` for any other malformed field. Accept lines are
/// parsed here, at start time, so a bad spec fails before any
/// process spawns rather than at verification time. Unknown
/// fields are ignored by construction: this struct carries only
/// the known fields, so specs stay forward compatible.
pub fn validate_spec(spec: &JobSpec) -> Result<JobSpec, DriverError> {
    if spec.id.trim().is_empty() {
        return Err(DriverError::BadSpec(
            "job spec field 'id' must be a non empty string".to_string(),
        ));
    }
    if spec.title.trim().is_empty() {
        return Err(DriverError::BadSpec(
            "job spec field 'title' must be a non empty string".to_string(),
        ));
    }
    if spec.spec.trim().is_empty() {
        return Err(DriverError::BadSpec(
            "job spec field 'spec' must be a non empty string".to_string(),
        ));
    }
    if spec.files.is_empty()
        || spec.files.iter().any(|f| f.trim().is_empty())
    {
        return Err(DriverError::BadSpec(
            "job spec field 'files' must be a non empty list of non empty paths"
                .to_string(),
        ));
    }
    if let Err(e) = parse_accept(&spec.accept) {
        return Err(DriverError::BadSpec(format!(
            "unparseable accept lines: {e}"
        )));
    }
    match &spec.sig {
        Some(sig) if !sig.trim().is_empty() => {}
        _ => {
            return Err(DriverError::Unsigned(
                "job spec has no signature; refusing to start an unsigned job"
                    .to_string(),
            ));
        }
    }
    Ok(spec.clone())
}

/// One heartbeat record in bus progress format.
#[derive(Debug, Clone, PartialEq)]
pub struct HeartbeatRecord {
    /// `PROGRESS:<job_id> <note>`, the exact bus progress format.
    pub line: String,
    /// The job id.
    pub job_id: String,
    /// The note text.
    pub note: String,
    /// Unix time in seconds when the heartbeat was emitted.
    pub ts: f64,
}

/// Build one progress record for a job id and note.
pub fn progress_record(job_id: &str, note: &str) -> HeartbeatRecord {
    HeartbeatRecord {
        line: format!("PROGRESS:{job_id} {note}"),
        job_id: job_id.to_string(),
        note: note.to_string(),
        ts: now_secs_f64(),
    }
}

/// A caller-supplied heartbeat sink: called once per record.
/// The default sink appends to the driver's own `heartbeats`
/// list; a caller sink replaces it, exactly as in Python where
/// `heartbeat_sink or self.heartbeats.append` decides.
pub type HeartbeatSink = Arc<Mutex<dyn FnMut(HeartbeatRecord) + Send>>;

/// Build a sink that collects records into a shared vector.
pub fn vec_sink() -> (HeartbeatSink, Arc<Mutex<Vec<HeartbeatRecord>>>) {
    let collected: Arc<Mutex<Vec<HeartbeatRecord>>> = Arc::new(Mutex::new(Vec::new()));
    let sink_collected = Arc::clone(&collected);
    let sink: HeartbeatSink = Arc::new(Mutex::new(move |rec: HeartbeatRecord| {
        sink_collected.lock().unwrap().push(rec);
    }));
    (sink, collected)
}

/// The artifacts record a driver returns after the process exits.
#[derive(Debug, Clone, PartialEq)]
pub struct ArtifactsRecord {
    /// The job id.
    pub job_id: String,
    /// `done` (exit 0), `failed` (exit nonzero), or `stopped`
    /// (terminated by `stop()`).
    pub status: String,
    /// The process exit code, or `None` if it was killed before
    /// reporting one.
    pub exit_code: Option<i32>,
    /// Changed paths under the workdir, relative and sorted.
    /// The driver log itself is never listed.
    pub changed_files: Vec<String>,
    /// The subset of `changed_files` not in the spec's owned list.
    pub unowned_files: Vec<String>,
    /// Path of the driver log file.
    pub log: PathBuf,
    /// Acceptance verdict from the workdir on disk.
    pub acceptance_ok: bool,
    /// Per-check acceptance results.
    pub acceptance_results: Vec<AcceptResult>,
}

impl ArtifactsRecord {
    /// Render the record as JSON (the shape `run_driver` prints).
    pub fn to_json(&self) -> String {
        let results: Vec<String> = self
            .acceptance_results
            .iter()
            .map(|r| {
                format!(
                    "{{\"check\":{},\"detail\":{},\"ok\":{}}}",
                    json_escape(&r.check),
                    json_escape(&r.detail),
                    r.ok
                )
            })
            .collect();
        let changed: Vec<String> =
            self.changed_files.iter().map(|f| json_escape(f)).collect();
        let unowned: Vec<String> =
            self.unowned_files.iter().map(|f| json_escape(f)).collect();
        let exit = match self.exit_code {
            Some(c) => c.to_string(),
            None => "null".to_string(),
        };
        format!(
            "{{\"acceptance\":{{\"ok\":{},\"results\":[{}]}},\"changed_files\":[{}],\"exit_code\":{},\"job_id\":{},\"log\":{},\"status\":{},\"unowned_files\":[{}]}}",
            self.acceptance_ok,
            results.join(","),
            changed.join(","),
            exit,
            json_escape(&self.job_id),
            json_escape(&self.log.to_string_lossy()),
            json_escape(&self.status),
            unowned.join(",")
        )
    }
}

/// Map relative path -> sha256 for every regular file under
/// `workdir`. Unreadable files are skipped, as in Python where
/// an `OSError` on open continues the walk.
pub fn snapshot(workdir: &Path) -> HashMap<String, String> {
    let mut snap = HashMap::new();
    fn walk(dir: &Path, base: &Path, snap: &mut HashMap<String, String>) {
        let Ok(entries) = std::fs::read_dir(dir) else {
            return;
        };
        for entry in entries.flatten() {
            let path = entry.path();
            let ft = match entry.file_type() {
                Ok(ft) => ft,
                Err(_) => continue,
            };
            if ft.is_dir() {
                walk(&path, base, snap);
            } else if ft.is_file() {
                if let Ok(rel) = path.strip_prefix(base) {
                    let rel_str = rel
                        .components()
                        .map(|c| c.as_os_str().to_string_lossy().into_owned())
                        .collect::<Vec<_>>()
                        .join("/");
                    if let Ok(bytes) = std::fs::read(&path) {
                        snap.insert(rel_str, sha256_hex(&bytes));
                    }
                }
            }
        }
    }
    walk(workdir, workdir, &mut snap);
    snap
}

/// Compute the artifacts record from a before/after snapshot
/// pair, an exit code, and the stopped flag.
///
/// Status rule, exactly as in Python: `stopped` when `stop()`
/// terminated the run, else `done` on exit 0, else `failed`.
pub fn compute_artifacts(
    spec: &JobSpec,
    workdir: &Path,
    before: &HashMap<String, String>,
    stopped: bool,
    exit_code: Option<i32>,
) -> ArtifactsRecord {
    let after = snapshot(workdir);
    let mut changed: Vec<String> = {
        let mut keys: BTreeSet<&String> = BTreeSet::new();
        keys.extend(before.keys());
        keys.extend(after.keys());
        keys.into_iter()
            .filter(|rel| {
                *rel != LOG_NAME && after.get(*rel) != before.get(*rel)
            })
            .cloned()
            .collect()
    };
    changed.sort();
    let owned: BTreeSet<&String> = spec.files.iter().collect();
    let unowned: Vec<String> = changed
        .iter()
        .filter(|f| !owned.contains(f))
        .cloned()
        .collect();
    let (ok, results) = verify_accept(&spec.accept, workdir);
    let status = if stopped {
        "stopped"
    } else if exit_code == Some(0) {
        "done"
    } else {
        "failed"
    };
    ArtifactsRecord {
        job_id: spec.id.clone(),
        status: status.to_string(),
        exit_code,
        changed_files: changed,
        unowned_files: unowned,
        log: workdir.join(LOG_NAME),
        acceptance_ok: ok,
        acceptance_results: results,
    }
}

/// Exit code in Python `Popen.returncode` encoding: the plain
/// exit code, or the negated signal number when the child died
/// by signal (e.g. -15 for SIGTERM). Python never reports
/// `None` for a reaped child; the contract's "or None" covers a
/// child killed before reporting, which this encoding renders
/// as its negative signal number.
pub fn status_code(status: std::process::ExitStatus) -> i32 {
    if let Some(code) = status.code() {
        return code;
    }
    #[cfg(unix)]
    {
        use std::os::unix::process::ExitStatusExt;
        if let Some(sig) = status.signal() {
            return -sig;
        }
    }
    -1
}

/// Wait for a child with an optional timeout in seconds.
///
/// `None` waits forever; `Some(t)` returns a timeout error when
/// the child is still running after `t` seconds, mirroring
/// `subprocess.TimeoutExpired` surfacing as `DriverError`.
/// The returned code uses [`status_code`] encoding.
pub fn wait_child(child: &mut Child, timeout: Option<f64>) -> Result<i32, DriverError> {
    let deadline = timeout.map(|t| SystemTime::now() + Duration::from_secs_f64(t.max(0.0)));
    loop {
        match child.try_wait() {
            Ok(Some(status)) => return Ok(status_code(status)),
            Ok(None) => {}
            Err(e) => {
                return Err(DriverError::Driver(format!(
                    "could not poll child: {e}"
                )));
            }
        }
        if let Some(d) = deadline {
            if SystemTime::now() >= d {
                return Err(DriverError::Driver(
                    "driver wait timed out".to_string(),
                ));
            }
        }
        std::thread::sleep(Duration::from_millis(10));
    }
}

/// Terminate a running child cleanly, as `stop()` does: SIGTERM,
/// up to 5 seconds to exit, then kill.
///
/// Returns the child's exit code (`None` when killed by signal
/// before reporting one). SIGTERM is delivered through the
/// `kill` utility because std Rust exposes no signal API; if
/// spawning `kill` fails, the child is killed directly.
pub fn terminate_child(child: &mut Child) -> Option<i32> {
    if let Ok(None) = child.try_wait() {
        let pid = child.id();
        let termed = Command::new("kill")
            .arg("-TERM")
            .arg(pid.to_string())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .map(|s| s.success())
            .unwrap_or(false);
        if !termed {
            let _ = child.kill();
        }
        let deadline = SystemTime::now() + Duration::from_secs(5);
        loop {
            match child.try_wait() {
                Ok(Some(status)) => return Some(status_code(status)),
                Ok(None) => {
                    if SystemTime::now() >= deadline {
                        let _ = child.kill();
                        let _ = child.wait();
                        return child.try_wait().ok().flatten().map(status_code);
                    }
                    std::thread::sleep(Duration::from_millis(10));
                }
                Err(_) => return None,
            }
        }
    }
    child.try_wait().ok().flatten().map(status_code)
}

/// Current exit code of a child, or `None` while it runs.
/// A reaped child yields `Some(code)` in [`status_code`]
/// encoding (negative when killed by signal), matching Python
/// `Popen.poll()`, which returns the returncode, not `None`,
/// once the child has exited.
pub fn poll_child(child: &mut Child) -> Option<i32> {
    child.try_wait().ok().flatten().map(status_code)
}

// ============================================================
// Section: stub driver (os/os/drivers/stub_driver.py, OS-053)
// ============================================================

/// The record `start()` returns: job id, child pid, `running`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StartRecord {
    /// The job id.
    pub job_id: String,
    /// The child process id.
    pub pid: u32,
    /// Always `"running"`.
    pub status: String,
}

/// The record `stop()` returns: job id, `stopped`, exit code.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StopRecord {
    /// The job id.
    pub job_id: String,
    /// Always `"stopped"`.
    pub status: String,
    /// The child exit code in [`status_code`] encoding.
    pub exit_code: Option<i32>,
}

/// Reference driver: runs a caller-supplied argv command as the
/// agent.
///
/// The command runs with cwd=workdir and its stdout/stderr
/// appended to `<workdir>/driver.log`. The caller owns the
/// command; the driver owns the contract around it. Starting
/// against an unsigned spec, unparseable accept lines, or an
/// empty owned files list is a hard error and spawns nothing.
/// No bus post, no network, no secret: heartbeat records go to
/// the caller-supplied sink (an in-memory list by default).
///
/// Quirk ported faithfully: `start()` refuses a second start
/// whenever a child was ever started, even after it exited,
/// because Python never clears `_proc`.
pub struct StubDriver {
    /// Workdir the agent works in.
    pub workdir: PathBuf,
    /// Records emitted through the default sink, in order.
    /// Empty when a caller sink was supplied, as in Python
    /// where the default list is replaced, not supplemented.
    internal_heartbeats: Arc<Mutex<Vec<HeartbeatRecord>>>,
    sink: HeartbeatSink,
    child: Option<Child>,
    log_file: Option<std::fs::File>,
    spec: Option<JobSpec>,
    before: Option<HashMap<String, String>>,
    artifacts: Option<ArtifactsRecord>,
    stopped: bool,
}

impl StubDriver {
    /// Create a driver for a workdir. Errors when the workdir
    /// does not exist, as Python's constructor does.
    pub fn new(workdir: &Path, heartbeat_sink: Option<HeartbeatSink>) -> Result<StubDriver, DriverError> {
        if !workdir.is_dir() {
            return Err(DriverError::Driver(format!(
                "workdir does not exist: {}",
                workdir.display()
            )));
        }
        let (sink, internal) = match heartbeat_sink {
            Some(s) => (s, Arc::new(Mutex::new(Vec::new()))),
            None => {
                let (s, collected) = vec_sink();
                (s, collected)
            }
        };
        Ok(StubDriver {
            workdir: workdir.to_path_buf(),
            internal_heartbeats: internal,
            sink,
            child: None,
            log_file: None,
            spec: None,
            before: None,
            artifacts: None,
            stopped: false,
        })
    }

    /// Heartbeat records emitted through the default sink.
    pub fn heartbeats(&self) -> Vec<HeartbeatRecord> {
        self.internal_heartbeats.lock().unwrap().clone()
    }

    /// Whether a child was ever started (mirrors `_proc is not None`).
    pub fn has_child(&self) -> bool {
        self.child.is_some()
    }

    fn emit(&self, note: &str) -> Result<HeartbeatRecord, DriverError> {
        let spec = self.spec.as_ref().ok_or_else(|| {
            DriverError::NotStarted("heartbeat before start".to_string())
        })?;
        if self.child.is_none() {
            return Err(DriverError::NotStarted("heartbeat before start".to_string()));
        }
        let record = progress_record(&spec.id, note);
        self.sink.lock().unwrap()(record.clone());
        Ok(record)
    }

    /// Launch the agent command against a validated spec.
    pub fn start(&mut self, spec: &JobSpec, command: &[String]) -> Result<StartRecord, DriverError> {
        if self.child.is_some() {
            let id = self.spec.as_ref().map(|s| s.id.clone()).unwrap_or_default();
            return Err(DriverError::Driver(format!(
                "driver already started for job {id}"
            )));
        }
        let validated = validate_spec(spec)?;
        self.spec = Some(validated);
        if command.is_empty() {
            return Err(DriverError::BadSpec(
                "command must be a non empty argv list".to_string(),
            ));
        }
        // Python checks only non-emptiness and str-ness of argv;
        // a Rust &[String] is str-typed by construction.
        let log_path = self.workdir.join(LOG_NAME);
        let log = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&log_path)
            .map_err(|e| DriverError::Driver(format!("could not open driver log: {e}")))?;
        // The snapshot is taken after the log is opened, as in
        // Python, so a fresh empty log is part of `before` (and
        // excluded from `changed_files` by name anyway).
        let before = snapshot(&self.workdir);
        let log_clone = log.try_clone().map_err(|e| {
            DriverError::Driver(format!("could not duplicate driver log: {e}"))
        })?;
        let mut cmd = Command::new(&command[0]);
        cmd.args(&command[1..])
            .current_dir(&self.workdir)
            .stdout(Stdio::from(log_clone))
            .stderr(Stdio::from(log.try_clone().map_err(|e| {
                DriverError::Driver(format!("could not duplicate driver log: {e}"))
            })?));
        let child = cmd.spawn().map_err(|e| {
            DriverError::Driver(format!("could not launch command: {e}"))
        })?;
        let pid = child.id();
        self.child = Some(child);
        self.log_file = Some(log);
        self.before = Some(before);
        self.stopped = false;
        self.artifacts = None;
        Ok(StartRecord {
            job_id: self.spec.as_ref().unwrap().id.clone(),
            pid,
            status: "running".to_string(),
        })
    }

    /// Emit one progress record in bus progress format.
    pub fn heartbeat(&self, note: &str) -> Result<HeartbeatRecord, DriverError> {
        self.emit(note)
    }

    /// Return the child exit code, or `None` while it runs.
    /// Errors before start.
    pub fn poll(&mut self) -> Result<Option<i32>, DriverError> {
        match self.child.as_mut() {
            None => Err(DriverError::NotStarted("poll before start".to_string())),
            Some(child) => Ok(poll_child(child)),
        }
    }

    /// Terminate the child cleanly; safe to call after it exited.
    pub fn stop(&mut self) -> Result<StopRecord, DriverError> {
        let Some(child) = self.child.as_mut() else {
            return Err(DriverError::NotStarted("stop before start".to_string()));
        };
        let exit_code = terminate_child(child);
        self.stopped = true;
        Ok(StopRecord {
            job_id: self.spec.as_ref().unwrap().id.clone(),
            status: "stopped".to_string(),
            exit_code,
        })
    }

    /// Wait for exit, then build the artifacts record.
    pub fn wait(&mut self, timeout: Option<f64>) -> Result<ArtifactsRecord, DriverError> {
        let Some(child) = self.child.as_mut() else {
            return Err(DriverError::NotStarted("wait before start".to_string()));
        };
        let exit_code = match wait_child(child, timeout) {
            Ok(code) => code,
            Err(mut e) => {
                if let DriverError::Driver(m) = &mut e {
                    let id = self.spec.as_ref().unwrap().id.clone();
                    *m = format!("driver wait timed out for job {id}");
                }
                return Err(e);
            }
        };
        // Close the log before snapshotting, so its final bytes
        // are on disk (the log itself is excluded from changed
        // files by name regardless).
        self.log_file = None;
        let before = self.before.clone().unwrap_or_default();
        let spec = self.spec.as_ref().unwrap().clone();
        let arts = compute_artifacts(&spec, &self.workdir, &before, self.stopped, Some(exit_code));
        self.artifacts = Some(arts.clone());
        Ok(arts)
    }

    /// Return the artifacts record, waiting first if still running.
    pub fn artifacts(&mut self) -> Result<ArtifactsRecord, DriverError> {
        if let Some(arts) = &self.artifacts {
            return Ok(arts.clone());
        }
        self.wait(None)
    }
}

// ============================================================
// Section: Muse driver (os/os/drivers/muse_driver.py, OS-054)
// ============================================================

/// Default Muse Code binary name, resolved on PATH.
pub const DEFAULT_BINARY: &str = "muse";

/// Maximum note length for streamed child-output heartbeats.
pub const NOTE_LIMIT: usize = 200;

/// Render a job spec into the prompt text handed to Muse Code.
///
/// The signature is never included: the prompt carries only
/// what the agent needs to do the work. Unknown spec fields are
/// ignored, so specs stay forward compatible.
pub fn build_prompt(spec: &JobSpec) -> String {
    let mut lines: Vec<String> = vec![
        format!("Job: {} (id: {})", spec.title, spec.id),
        String::new(),
        spec.spec.clone(),
        String::new(),
        "Owned files (work only in these files unless the spec says otherwise):"
            .to_string(),
    ];
    for f in &spec.files {
        lines.push(format!("  - {f}"));
    }
    lines.push(String::new());
    lines.push("Acceptance (all lines must hold when you finish):".to_string());
    lines.push(spec.accept.clone());
    lines.push(String::new());
    lines.push(format!("Attempt budget: max_attempts={}", spec.max_attempts));
    lines.push(
        "When done, leave the workdir in a state where the acceptance lines above hold."
            .to_string(),
    );
    lines.join("\n") + "\n"
}

/// The headless Muse Code invocation for one prompt file.
pub fn build_argv(binary: &str, prompt_path: &str, extra_args: &[String]) -> Vec<String> {
    let mut argv = vec![
        binary.to_string(),
        "exec".to_string(),
        "--prompt-file".to_string(),
        prompt_path.to_string(),
    ];
    argv.extend(extra_args.iter().cloned());
    argv
}

#[cfg(unix)]
fn is_executable(path: &Path) -> bool {
    use std::os::unix::fs::PermissionsExt;
    match std::fs::metadata(path) {
        Ok(m) => m.is_file() && (m.permissions().mode() & 0o111) != 0,
        Err(_) => false,
    }
}

#[cfg(not(unix))]
fn is_executable(path: &Path) -> bool {
    path.is_file()
}

/// Resolve a binary the way `shutil.which` does: a path
/// containing a separator must itself be executable; otherwise
/// each PATH entry is tried in order.
pub fn find_binary(binary: &str) -> Option<PathBuf> {
    if binary.contains('/') {
        let p = PathBuf::from(binary);
        return if is_executable(&p) { Some(p) } else { None };
    }
    let path_var = std::env::var_os("PATH")?;
    for dir in std::env::split_paths(&path_var) {
        let candidate = dir.join(binary);
        if is_executable(&candidate) {
            return Some(candidate);
        }
    }
    None
}

static TMP_COUNTER: AtomicU64 = AtomicU64::new(0);

/// Create a fresh temp dir outside the workdir, mirroring
/// `tempfile.mkdtemp(prefix="muse-driver-")`.
fn make_tmpdir() -> Result<PathBuf, DriverError> {
    let n = TMP_COUNTER.fetch_add(1, Ordering::SeqCst);
    let dir = std::env::temp_dir().join(format!(
        "muse-driver-{}-{n}",
        std::process::id()
    ));
    std::fs::create_dir(&dir)
        .map_err(|e| DriverError::Driver(format!("could not create temp dir: {e}")))?;
    Ok(dir)
}

/// Muse Code driver: the OS-053 contract against the real CLI.
///
/// Builds the prompt from the signed job spec, writes it to a
/// temp file OUTSIDE the workdir so it never pollutes the
/// changed file list, launches the CLI with cwd=workdir, and
/// streams the child's stdout lines into heartbeat records
/// (one PROGRESS record per line, note truncated to 200
/// characters) while also appending them verbatim to
/// `<workdir>/driver.log`.
///
/// What this driver does NOT do, stated plainly (from the
/// Python module): it passes no approval bypass flag; it never
/// puts the job signature on a command line, in the prompt
/// file, or in a log; it never posts to the bus.
pub struct MuseDriver {
    /// Workdir the agent works in.
    pub workdir: PathBuf,
    internal_heartbeats: Arc<Mutex<Vec<HeartbeatRecord>>>,
    sink: HeartbeatSink,
    binary: String,
    extra_args: Vec<String>,
    child: Option<Child>,
    /// Shared log handle: the reader thread and `wait()` both
    /// touch it, so it lives behind a mutex.
    log_file: Option<Arc<Mutex<std::fs::File>>>,
    spec: Option<JobSpec>,
    before: Option<HashMap<String, String>>,
    artifacts: Option<ArtifactsRecord>,
    stopped: bool,
    tmpdir: Option<PathBuf>,
    prompt_path: Option<PathBuf>,
    reader: Option<std::thread::JoinHandle<()>>,
}

impl MuseDriver {
    /// Create a driver for a workdir, binary, and extra args.
    /// Errors when the workdir does not exist.
    pub fn new(
        workdir: &Path,
        heartbeat_sink: Option<HeartbeatSink>,
        muse_binary: Option<&str>,
        extra_args: &[String],
    ) -> Result<MuseDriver, DriverError> {
        if !workdir.is_dir() {
            return Err(DriverError::Driver(format!(
                "workdir does not exist: {}",
                workdir.display()
            )));
        }
        let (sink, internal) = match heartbeat_sink {
            Some(s) => (s, Arc::new(Mutex::new(Vec::new()))),
            None => {
                let (s, collected) = vec_sink();
                (s, collected)
            }
        };
        Ok(MuseDriver {
            workdir: workdir.to_path_buf(),
            internal_heartbeats: internal,
            sink,
            binary: muse_binary.unwrap_or(DEFAULT_BINARY).to_string(),
            extra_args: extra_args.to_vec(),
            child: None,
            log_file: None,
            spec: None,
            before: None,
            artifacts: None,
            stopped: false,
            tmpdir: None,
            prompt_path: None,
            reader: None,
        })
    }

    /// Heartbeat records emitted through the default sink.
    pub fn heartbeats(&self) -> Vec<HeartbeatRecord> {
        self.internal_heartbeats.lock().unwrap().clone()
    }

    /// Whether a child was ever started (mirrors `_proc is not None`).
    pub fn has_child(&self) -> bool {
        self.child.is_some()
    }

    /// The prompt file path while a run is active, else `None`.
    /// Exposed so conformance checks can pin that the prompt
    /// lives outside the workdir and is cleaned up after `wait`.
    pub fn prompt_path(&self) -> Option<PathBuf> {
        self.prompt_path.clone()
    }

    /// The temp dir holding the prompt file while active.
    pub fn tmpdir(&self) -> Option<PathBuf> {
        self.tmpdir.clone()
    }

    fn emit(&self, note: &str) -> Result<HeartbeatRecord, DriverError> {
        let spec = self.spec.as_ref().ok_or_else(|| {
            DriverError::NotStarted("heartbeat before start".to_string())
        })?;
        if self.child.is_none() {
            return Err(DriverError::NotStarted("heartbeat before start".to_string()));
        }
        let record = progress_record(&spec.id, note);
        self.sink.lock().unwrap()(record.clone());
        Ok(record)
    }

    /// Validate the spec, then launch `muse exec` against it.
    pub fn start(&mut self, spec: &JobSpec) -> Result<StartRecord, DriverError> {
        if self.child.is_some() {
            let id = self.spec.as_ref().map(|s| s.id.clone()).unwrap_or_default();
            return Err(DriverError::Driver(format!(
                "driver already started for job {id}"
            )));
        }
        let validated = validate_spec(spec)?;
        self.spec = Some(validated);
        if find_binary(&self.binary).is_none() {
            // Python resets _spec to None on this path.
            self.spec = None;
            return Err(DriverError::Driver(format!(
                "muse binary not found: {:?} is not on PATH and is not an executable path; the Muse Code CLI must be installed on the machine before this driver can start",
                self.binary
            )));
        }
        let tmpdir = make_tmpdir()?;
        let prompt_path = tmpdir.join("prompt.md");
        std::fs::write(&prompt_path, build_prompt(self.spec.as_ref().unwrap())).map_err(
            |e| DriverError::Driver(format!("could not write prompt file: {e}")),
        )?;
        let log_path = self.workdir.join(LOG_NAME);
        let log = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&log_path)
            .map_err(|e| DriverError::Driver(format!("could not open driver log: {e}")))?;
        let log = Arc::new(Mutex::new(log));
        let before = snapshot(&self.workdir);
        let argv = build_argv(&self.binary, &prompt_path.to_string_lossy(), &self.extra_args);
        // Python wires stderr to STDOUT (merged into the reader
        // pipe). Std Rust cannot merge a piped stdout with
        // stderr onto the same pipe, so stderr goes directly to
        // the log file instead: the contract holds (the log
        // carries stdout and stderr verbatim, appended by both
        // writers under the log mutex for stdout and by the
        // child fd for stderr), but stderr lines are not
        // streamed as heartbeat notes. Documented deviation;
        // see the final report.
        let stderr_file = {
            let guard = log.lock().unwrap();
            guard.try_clone().map_err(|e| {
                DriverError::Driver(format!("could not duplicate driver log: {e}"))
            })?
        };
        let mut child = match Command::new(&argv[0])
            .args(&argv[1..])
            .current_dir(&self.workdir)
            .stdout(Stdio::piped())
            .stderr(Stdio::from(stderr_file))
            .spawn()
        {
            Ok(c) => c,
            Err(e) => {
                // Python closes the log and raises on spawn failure.
                drop(log);
                return Err(DriverError::Driver(format!(
                    "could not launch {}: {e}",
                    self.binary
                )));
            }
        };
        let stdout = child.stdout.take().unwrap();
        let reader_log = Arc::clone(&log);
        let reader_sink = Arc::clone(&self.sink);
        let reader_job = self.spec.as_ref().unwrap().id.clone();
        let reader = std::thread::spawn(move || {
            let reader = BufReader::new(stdout);
            for line in reader.lines() {
                let Ok(text) = line else { break };
                let mut with_nl = text.clone();
                with_nl.push('\n');
                if let Ok(mut f) = reader_log.lock() {
                    let _ = f.write_all(with_nl.as_bytes());
                    let _ = f.flush();
                }
                let stripped = text.trim();
                if !stripped.is_empty() {
                    let note = head_chars(stripped, NOTE_LIMIT);
                    let record = progress_record(&reader_job, &note);
                    reader_sink.lock().unwrap()(record);
                }
            }
        });
        let pid = child.id();
        self.child = Some(child);
        self.log_file = Some(log);
        self.before = Some(before);
        self.tmpdir = Some(tmpdir);
        self.prompt_path = Some(prompt_path);
        self.reader = Some(reader);
        self.stopped = false;
        self.artifacts = None;
        Ok(StartRecord {
            job_id: self.spec.as_ref().unwrap().id.clone(),
            pid,
            status: "running".to_string(),
        })
    }

    /// Emit one progress record in bus progress format.
    pub fn heartbeat(&self, note: &str) -> Result<HeartbeatRecord, DriverError> {
        self.emit(note)
    }

    /// Return the child exit code, or `None` while it runs.
    pub fn poll(&mut self) -> Result<Option<i32>, DriverError> {
        match self.child.as_mut() {
            None => Err(DriverError::NotStarted("poll before start".to_string())),
            Some(child) => Ok(poll_child(child)),
        }
    }

    /// Terminate the child cleanly; safe to call after it exited.
    pub fn stop(&mut self) -> Result<StopRecord, DriverError> {
        let Some(child) = self.child.as_mut() else {
            return Err(DriverError::NotStarted("stop before start".to_string()));
        };
        let exit_code = terminate_child(child);
        self.stopped = true;
        Ok(StopRecord {
            job_id: self.spec.as_ref().unwrap().id.clone(),
            status: "stopped".to_string(),
            exit_code,
        })
    }

    /// Wait for exit, join the stream thread, build artifacts.
    pub fn wait(&mut self, timeout: Option<f64>) -> Result<ArtifactsRecord, DriverError> {
        let Some(child) = self.child.as_mut() else {
            return Err(DriverError::NotStarted("wait before start".to_string()));
        };
        let exit_code = match wait_child(child, timeout) {
            Ok(code) => code,
            Err(mut e) => {
                if let DriverError::Driver(m) = &mut e {
                    let id = self.spec.as_ref().unwrap().id.clone();
                    *m = format!("driver wait timed out for job {id}");
                }
                return Err(e);
            }
        };
        // Join the reader after the child exits: its stdout is
        // closed, so it reaches EOF. (Python joins with a 5s
        // timeout and proceeds regardless; see the crate header.)
        if let Some(reader) = self.reader.take() {
            let _ = reader.join();
        }
        self.log_file = None;
        let before = self.before.clone().unwrap_or_default();
        let spec = self.spec.as_ref().unwrap().clone();
        let arts = compute_artifacts(&spec, &self.workdir, &before, self.stopped, Some(exit_code));
        self.artifacts = Some(arts.clone());
        if let Some(tmpdir) = self.tmpdir.take() {
            let _ = std::fs::remove_dir_all(&tmpdir);
            self.prompt_path = None;
        }
        Ok(arts)
    }

    /// Return the artifacts record, waiting first if still running.
    pub fn artifacts(&mut self) -> Result<ArtifactsRecord, DriverError> {
        if let Some(arts) = &self.artifacts {
            return Ok(arts.clone());
        }
        self.wait(None)
    }
}

// ============================================================
// Section: run_driver (os/os/drivers/run_driver.py, OS-054)
// ============================================================

/// Run one signed job through a driver, from a spec JSON text.
///
/// Mirrors `run_driver.main` minus the CLI/file layer: the
/// caller reads the spec file and prints the artifacts JSON.
/// Returns the artifacts record on success; any driver error
/// (unsigned spec, missing binary, bad spec file) is the
/// exit-2 path in the Python CLI, so callers map `Err` to 2.
/// Exit code 0 in Python covers a completed driver run even
/// when the job itself failed acceptance, and this function
/// does the same: a failed-acceptance run is `Ok` with
/// `acceptance_ok == false`.
pub fn run_driver(
    spec_json: &str,
    workdir: &Path,
    binary: Option<&str>,
    extra_args: &[String],
) -> Result<ArtifactsRecord, String> {
    let value = parse_json(spec_json).map_err(|e| format!("run_driver: cannot read spec file: {e}"))?;
    let spec = spec_from_json(&value)?;
    let mut driver = MuseDriver::new(workdir, None, binary, extra_args)
        .map_err(|e| format!("run_driver: {}", e.message()))?;
    driver
        .start(&spec)
        .map_err(|e| format!("run_driver: {}", e.message()))?;
    driver
        .artifacts()
        .map_err(|e| format!("run_driver: {}", e.message()))
}

/// Convert a parsed spec JSON value into a [`JobSpec`].
/// Missing `accept` defaults to `""`, missing `max_attempts`
/// to 3; wrong JSON types are a spec-file error (exit 2).
pub fn spec_from_json(value: &JsonValue) -> Result<JobSpec, String> {
    let get_str = |key: &str| -> Result<String, String> {
        value
            .get(key)
            .and_then(|v| v.as_str())
            .map(|s| s.to_string())
            .ok_or_else(|| format!("run_driver: spec field {key:?} must be a string"))
    };
    let files = value
        .get("files")
        .and_then(|v| v.as_str_list())
        .ok_or_else(|| "run_driver: spec field 'files' must be a list of strings".to_string())?;
    let mut spec = JobSpec {
        id: get_str("id")?,
        title: get_str("title")?,
        spec: get_str("spec")?,
        files,
        accept: value
            .get("accept")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string(),
        sig: value.get("sig").and_then(|v| v.as_str()).map(|s| s.to_string()),
        max_attempts: value
            .get("max_attempts")
            .and_then(|v| v.as_i64())
            .unwrap_or(3),
    };
    // validate_spec defaults nothing here (already applied),
    // but enforces the contract; surface its message as the
    // exit-2 error.
    spec.max_attempts = value
        .get("max_attempts")
        .and_then(|v| v.as_i64())
        .unwrap_or(3);
    let validated = validate_spec(&spec)
        .map_err(|e| format!("run_driver: {}", e.message()))?;
    spec = validated;
    Ok(spec)
}

// ============================================================
// Section: driver contract docs (T146, byte-identical embed)
// ============================================================

/// `os/os/drivers/CONTRACT.md`, embedded byte-identical via
/// `include_str!` from the Python source tree. The checksum
/// test pins the bytes: any drift between this constant and
/// the source fails loudly rather than silently.
pub const DRIVER_CONTRACT_MD: &str =
    include_str!("../../../os/os/drivers/CONTRACT.md");

/// `os/os/drivers/CONFORMANCE.md`, embedded byte-identical via
/// `include_str!` from the Python source tree. See
/// [`DRIVER_CONTRACT_MD`].
pub const DRIVER_CONFORMANCE_MD: &str =
    include_str!("../../../os/os/drivers/CONFORMANCE.md");

/// SHA-256 of `DRIVER_CONTRACT_MD` at port time, from the
/// source file itself. The pin test recomputes it.
pub const DRIVER_CONTRACT_SHA256: &str =
    "70585081dee7697b3f04a9bf15e21ebb1a65e22938f144f6e89ced0875eb594f";

/// SHA-256 of `DRIVER_CONFORMANCE_MD` at port time, from the
/// source file itself. The pin test recomputes it.
pub const DRIVER_CONFORMANCE_SHA256: &str =
    "2841d00799d9273bb47a37529c681e6376eea48b287f47a9812c2a395ea2116f";

// ============================================================
// Section: relay uplink (os/os/uplink/relay_uplink.py, OS-093)
// ============================================================

/// Base backoff after connection failures, in seconds.
pub const BACKOFF_BASE_SECONDS: i64 = 5;

/// Backoff cap, in seconds.
pub const BACKOFF_CAP_SECONDS: i64 = 300;

/// Wait after `failures` consecutive failures: 5, 10, 20, ...
/// capped at 300. Zero or negative failures wait 0.
pub fn backoff_seconds(failures: i64) -> i64 {
    if failures <= 0 {
        return 0;
    }
    if failures >= 9 {
        // 5 * 2^8 = 1280 already exceeds the cap.
        return BACKOFF_CAP_SECONDS;
    }
    let wait = BACKOFF_BASE_SECONDS * (1i64 << (failures - 1));
    wait.min(BACKOFF_CAP_SECONDS)
}

/// One order read by the uplink. Fields read: id (required),
/// text (required, non-empty), origin (required), received_at
/// (Unix seconds, for the record only, never invented).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Order {
    /// Order id.
    pub id: String,
    /// Raw order text.
    pub text: String,
    /// Origin, e.g. the phone.
    pub origin: String,
    /// Received timestamp, if the order carries one.
    pub received_at: Option<i64>,
}

/// Uplink state, owned by the caller. `tick` never mutates its
/// input; it returns a new state and the caller stores it.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct UplinkState {
    /// Order ids already taken in.
    pub seen_ids: Vec<String>,
    /// Orders queued while offline, in received order.
    pub pending: Vec<Order>,
    /// Consecutive connection failures.
    pub failures: i64,
    /// Next retry time in Unix seconds, or `None`.
    pub next_retry_at: Option<i64>,
}

/// An empty uplink state, as `empty_state()` builds it.
pub fn empty_state() -> UplinkState {
    UplinkState::default()
}

/// A job-set intake record built from a taken-in order.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IntakeRecord {
    /// The order id.
    pub order_id: String,
    /// The order's raw text, carried as the spec.
    pub text: String,
    /// The order's origin.
    pub origin: String,
    /// The order's received_at, if any.
    pub received_at: Option<i64>,
    /// Always `"ORDER"`.
    pub kind: String,
    /// True when a signing key was supplied.
    pub signed: bool,
    /// HMAC signature, or `None` when unsigned.
    pub signature: Option<String>,
}

/// One uplink event, naming the order id it concerns.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UplinkEvent {
    /// `intake`, `queued`, `duplicate`, `rejected`, or
    /// `unsigned-refused`.
    pub event_type: String,
    /// The order id, when the order carries one.
    pub order_id: Option<String>,
    /// Rejection/refusal reason, when the event carries one.
    pub reason: Option<String>,
    /// The intake record, for `intake` events only.
    pub record: Option<IntakeRecord>,
}

/// Validate an order: `(true, "")` for a takeable order, else
/// `(false, reason)` naming exactly what is missing.
/// An order with no id, empty text, or no origin is rejected,
/// never repaired with a guessed id or placeholder goal.
pub fn validate_order(order: &Order) -> (bool, String) {
    if order.id.is_empty() {
        return (false, "order id missing".to_string());
    }
    if order.text.trim().is_empty() {
        return (false, "order text empty".to_string());
    }
    if order.origin.is_empty() {
        return (false, "order origin missing".to_string());
    }
    (true, String::new())
}

/// HMAC-SHA256 over order id + text, the jobs.py v2 signing shape.
pub fn sign_intake(key: &str, order_id: &str, text: &str) -> String {
    let msg = format!("{order_id}\n{text}");
    hmac_sha256_hex(key.as_bytes(), msg.as_bytes())
}

/// One failed connection attempt: bump failures, set the next
/// retry by exponential backoff. Returns a new state.
pub fn record_failure(state: &UplinkState, now: i64) -> UplinkState {
    let mut new = state.clone();
    new.failures = state.failures + 1;
    new.next_retry_at = Some(now + backoff_seconds(new.failures));
    new
}

/// One good connection: the failure count and retry time clear.
pub fn record_success(state: &UplinkState) -> UplinkState {
    let mut new = state.clone();
    new.failures = 0;
    new.next_retry_at = None;
    new
}

fn intake_record(order: &Order, key: Option<&str>) -> IntakeRecord {
    IntakeRecord {
        order_id: order.id.clone(),
        text: order.text.clone(),
        origin: order.origin.clone(),
        received_at: order.received_at,
        kind: "ORDER".to_string(),
        signed: key.is_some(),
        signature: key.map(|k| sign_intake(k, &order.id, &order.text)),
    }
}

fn take_in(
    state: &UplinkState,
    order: &Order,
    key: Option<&str>,
    crew_mode: bool,
) -> (UplinkEvent, UplinkState) {
    if state.seen_ids.contains(&order.id)
        || state.pending.iter().any(|p| p.id == order.id)
    {
        return (
            UplinkEvent {
                event_type: "duplicate".to_string(),
                order_id: Some(order.id.clone()),
                reason: None,
                record: None,
            },
            state.clone(),
        );
    }
    if crew_mode && key.is_none() {
        let mut new = state.clone();
        new.pending.push(order.clone());
        return (
            UplinkEvent {
                event_type: "unsigned-refused".to_string(),
                order_id: Some(order.id.clone()),
                reason: Some("crew mode requires a signing key".to_string()),
                record: None,
            },
            new,
        );
    }
    let mut new = state.clone();
    new.seen_ids.push(order.id.clone());
    new.pending.retain(|p| p.id != order.id);
    (
        UplinkEvent {
            event_type: "intake".to_string(),
            order_id: Some(order.id.clone()),
            reason: None,
            record: Some(intake_record(order, key)),
        },
        new,
    )
}

/// One uplink cycle. Returns `(events, new_state)`; inputs are
/// untouched (the state is cloned, never mutated in place).
///
/// When disconnected, valid new orders queue in pending and no
/// intake is made. When connected, pending orders drain first
/// in received order, then new orders, each deduplicated by id.
/// Invalid orders are rejected with a reason in either mode.
/// In crew mode with no signing key, an intake is refused and
/// the order stays pending, never dropped.
pub fn uplink_tick(
    state: &UplinkState,
    orders: &[Order],
    now: i64,
    connected: bool,
    key: Option<&str>,
    crew_mode: bool,
) -> (Vec<UplinkEvent>, UplinkState) {
    let mut events = Vec::new();
    if connected {
        let mut cur = record_success(state);
        let drain = std::mem::take(&mut cur.pending);
        for order in &drain {
            let (ok, reason) = validate_order(order);
            if !ok {
                events.push(UplinkEvent {
                    event_type: "rejected".to_string(),
                    order_id: Some(order.id.clone()),
                    reason: Some(reason),
                    record: None,
                });
                continue;
            }
            let (event, next) = take_in(&cur, order, key, crew_mode);
            cur = next;
            events.push(event);
        }
        for order in orders {
            let (ok, reason) = validate_order(order);
            if !ok {
                events.push(UplinkEvent {
                    event_type: "rejected".to_string(),
                    order_id: Some(order.id.clone()),
                    reason: Some(reason),
                    record: None,
                });
                continue;
            }
            let (event, next) = take_in(&cur, order, key, crew_mode);
            cur = next;
            events.push(event);
        }
        (events, cur)
    } else {
        let mut cur = record_failure(state, now);
        for order in orders {
            let (ok, reason) = validate_order(order);
            if !ok {
                events.push(UplinkEvent {
                    event_type: "rejected".to_string(),
                    order_id: Some(order.id.clone()),
                    reason: Some(reason),
                    record: None,
                });
                continue;
            }
            if cur.seen_ids.contains(&order.id)
                || cur.pending.iter().any(|p| p.id == order.id)
            {
                events.push(UplinkEvent {
                    event_type: "duplicate".to_string(),
                    order_id: Some(order.id.clone()),
                    reason: None,
                    record: None,
                });
                continue;
            }
            cur.pending.push(order.clone());
            events.push(UplinkEvent {
                event_type: "queued".to_string(),
                order_id: Some(order.id.clone()),
                reason: None,
                record: None,
            });
        }
        (events, cur)
    }
}

// ============================================================
// Section: MOS worker loop (os/mos/worker.py)
// ============================================================

/// A parsed DM announcement: `(jid, title, reqs)`, or `None`
/// when the body carries no `JOB:<id> <title>` announcement.
///
/// Parses `JOB:<id> <title> [req=a,b]` exactly as the Python
/// regexes do: the `JOB:` search is unanchored, the id is a
/// digit run followed by whitespace, and a trailing `req=`
/// clause (word-boundary `req=`, comma list, only whitespace
/// to the end) is stripped from the title into the req set.
pub fn parse_announcement(body: &str) -> Option<(String, String, BTreeSet<String>)> {
    let bytes = body.as_bytes();
    let mut i = 0;
    while i + 4 <= bytes.len() {
        if &body[i..i + 4] == "JOB:" {
            let mut j = i + 4;
            let digit_start = j;
            while j < bytes.len() && bytes[j].is_ascii_digit() {
                j += 1;
            }
            if j > digit_start
                && j < bytes.len()
                && (bytes[j] == b' ' || bytes[j] == b'\t' || bytes[j] == b'\n' || bytes[j] == b'\r')
            {
                let jid = body[digit_start..j].to_string();
                // \s+ consumes the whitespace run; .* takes the rest.
                let mut k = j;
                while k < bytes.len()
                    && (bytes[k] == b' ' || bytes[k] == b'\t' || bytes[k] == b'\n' || bytes[k] == b'\r')
                {
                    k += 1;
                }
                let mut rest = body[k..].to_string();
                // .* stops at a newline; mirror by cutting there.
                if let Some(nl) = rest.find('\n') {
                    rest.truncate(nl);
                }
                let rest = rest.trim().to_string();
                let (title, reqs) = strip_req_clause(&rest);
                return Some((jid, title, reqs));
            }
        }
        // Advance one character (UTF-8 safe: step by char len).
        let ch_len = body[i..].chars().next().map(|c| c.len_utf8()).unwrap_or(1);
        i += ch_len;
    }
    None
}

/// Strip a trailing `\breq=a,b` clause from an announcement
/// title, returning `(title, reqs)`.
fn strip_req_clause(rest: &str) -> (String, BTreeSet<String>) {
    // Candidates: every "req=" whose preceding char is a word
    // boundary (start of string or a non-word character).
    let bytes = rest.as_bytes();
    let mut i = 0;
    while i + 4 <= bytes.len() {
        if &rest[i..i + 4] == "req=" {
            let boundary = i == 0
                || !(bytes[i - 1].is_ascii_alphanumeric() || bytes[i - 1] == b'_');
            if boundary {
                let mut j = i + 4;
                let cap_start = j;
                while j < bytes.len()
                    && (bytes[j].is_ascii_alphanumeric()
                        || bytes[j] == b'_'
                        || bytes[j] == b','
                        || bytes[j] == b'-')
                {
                    j += 1;
                }
                // \s*$ : only whitespace (plus an optional
                // trailing newline, which Python $ also allows)
                // may follow the capture.
                let tail = &rest[j..];
                let tail_ok = tail.trim().is_empty()
                    || (tail.trim().is_empty());
                if tail_ok && j > cap_start {
                    let reqs: BTreeSet<String> = rest[cap_start..j]
                        .split(',')
                        .filter(|r| !r.is_empty())
                        .map(|r| r.to_string())
                        .collect();
                    let title = rest[..i].trim().to_string();
                    return (title, reqs);
                }
                // A "req=" that fails the anchor is not a match;
                // keep scanning (Python re.search does the same).
            }
        }
        let ch_len = rest[i..].chars().next().map(|c| c.len_utf8()).unwrap_or(1);
        i += ch_len;
    }
    (rest.to_string(), BTreeSet::new())
}

/// Error a worker handler returns: a clean block, or a crash.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HandlerError {
    /// A clean block with a reason (Python `WorkerBlocked`).
    Blocked(String),
    /// A handler crash; the message stands in for the Python
    /// traceback tail (see the crate header note).
    Crashed(String),
}

/// One poll/claim/work cycle report, mirroring the Python
/// report dict's keys: claimed, done, blocked, skipped, errors.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct RunReport {
    /// Job ids claimed this cycle.
    pub claimed: Vec<String>,
    /// Job ids finished this cycle.
    pub done: Vec<String>,
    /// Job ids blocked this cycle.
    pub blocked: Vec<String>,
    /// Job ids skipped for unmet requirements.
    pub skipped: Vec<String>,
    /// Claim/finish error lines.
    pub errors: Vec<String>,
}

/// A parsed DM announcement handed to the worker loop.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Announcement {
    /// Job id.
    pub jid: String,
    /// Job title.
    pub title: String,
    /// Requirement set from the trailing `req=` clause.
    pub reqs: BTreeSet<String>,
}

/// The live bus/queue side of the worker loop, behind a trait
/// so the loop logic ports faithfully without faking Redis:
/// the production backend (other batches' `relay_common`,
/// `jobs`, `capabilities` ports) implements this; tests use a
/// fake. No method here ever posts, claims, or renews on its
/// own -- it only performs the call the loop asks for.
pub trait WorkerBackend {
    /// Register capabilities (Python `Worker.register`).
    fn register(&mut self, worker: &Worker);
    /// Touch registration and renew leases on my claims;
    /// returns the renewed job ids (Python `heartbeat`).
    fn heartbeat(&mut self, worker: &Worker) -> Vec<String>;
    /// New DM announcements (Python `poll_dms`).
    fn poll_dms(&mut self, worker: &Worker) -> Vec<Announcement>;
    /// Claim a job; `(ok, detail)` mirrors Python's
    /// `(rc == 0 and "CLAIMED <jid>" in out, out + err)`.
    fn claim(&mut self, worker: &Worker, jid: &str) -> (bool, String);
    /// Mark a job done; mirrors `jobs.main(["done", ...]) == 0`.
    fn finish(&mut self, worker: &Worker, jid: &str, commit: &str, note: &str) -> bool;
    /// Mark a job blocked with a reason already truncated to
    /// 500 characters by the loop; mirrors `["blocked", ...]`.
    fn block(&mut self, worker: &Worker, jid: &str, reason: &str) -> bool;
    /// The job spec text for a claimed job, or `""`.
    fn job_spec(&mut self, worker: &Worker, jid: &str) -> String;
}

/// The MOS worker loop: poll DMs, claim matching jobs, do the
/// work, heartbeat the lease, and report done/blocked.
///
/// A worker is one nick in one process. Registration, DM reads,
/// claims, and finishes run through the [`WorkerBackend`];
/// everything else -- announcement parsing, capability matching,
/// the report shape, and the truncation rules -- is this
/// struct's own logic, ported verbatim from `mos/worker.py`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Worker {
    /// Worker nick.
    pub nick: String,
    /// DM secret; empty means `poll_dms` yields nothing.
    pub dm_secret: String,
    /// Capabilities: stripped, lowercased, non-empty, as Python
    /// builds the set from `caps`.
    pub caps: BTreeSet<String>,
    /// Roles string, passed to registration.
    pub roles: String,
    /// Workdir handed to the handler.
    pub workdir: String,
    /// Claim lease in seconds.
    pub lease: i64,
    /// Maximum concurrent jobs, passed to registration.
    pub max_jobs: i64,
}

impl Worker {
    /// Create a worker, normalizing caps exactly as Python does.
    pub fn new(
        nick: &str,
        dm_secret: &str,
        caps: &[&str],
        roles: &str,
        workdir: &str,
        lease: i64,
        max_jobs: i64,
    ) -> Worker {
        let caps_set: BTreeSet<String> = caps
            .iter()
            .map(|c| c.trim().to_lowercase())
            .filter(|c| !c.is_empty())
            .collect();
        Worker {
            nick: nick.to_string(),
            dm_secret: dm_secret.to_string(),
            caps: caps_set,
            roles: roles.to_string(),
            workdir: workdir.to_string(),
            lease,
            max_jobs,
        }
    }

    /// Whether a requirement set is covered by this worker's caps.
    pub fn matches(&self, reqs: &BTreeSet<String>) -> bool {
        reqs.is_subset(&self.caps)
    }

    /// One poll/claim/work cycle. Returns a report dict.
    ///
    /// Order mirrors Python `run_once` exactly: register,
    /// heartbeat, then per announcement -- skip on unmet reqs,
    /// claim (errors carry the stripped detail's last 200
    /// characters), run the handler, finish or block. A
    /// `Blocked` handler error blocks with its reason (or
    /// `"blocked"` when empty); a crash blocks with
    /// `handler crashed: <last 400 chars of the message>`.
    /// Block reasons are truncated to 500 characters.
    pub fn run_once<B: WorkerBackend, F>(
        &self,
        backend: &mut B,
        mut handler: F,
    ) -> RunReport
    where
        F: FnMut(&str, &str, &str, &str) -> Result<(String, String), HandlerError>,
    {
        let mut report = RunReport::default();
        backend.register(self);
        backend.heartbeat(self);
        let announcements = if self.dm_secret.is_empty() {
            Vec::new()
        } else {
            backend.poll_dms(self)
        };
        for ann in announcements {
            if !self.matches(&ann.reqs) {
                report.skipped.push(ann.jid);
                continue;
            }
            let (ok, detail) = backend.claim(self, &ann.jid);
            if !ok {
                let tail = tail_chars(detail.trim(), 200);
                report.errors.push(format!("claim {}: {}", ann.jid, tail));
                continue;
            }
            report.claimed.push(ann.jid.clone());
            let spec = backend.job_spec(self, &ann.jid);
            match handler(&ann.jid, &ann.title, &spec, &self.workdir) {
                Ok((commit, note)) => {
                    if backend.finish(self, &ann.jid, &commit, &note) {
                        report.done.push(ann.jid.clone());
                    } else {
                        report.errors.push(format!("done {}: finish failed", ann.jid));
                    }
                }
                Err(HandlerError::Blocked(reason)) => {
                    let reason = if reason.is_empty() {
                        "blocked".to_string()
                    } else {
                        reason
                    };
                    backend.block(self, &ann.jid, &head_chars(&reason, 500));
                    report.blocked.push(ann.jid.clone());
                }
                Err(HandlerError::Crashed(message)) => {
                    let reason = format!("handler crashed: {}", tail_chars(&message, 400));
                    backend.block(self, &ann.jid, &head_chars(&reason, 500));
                    report.blocked.push(ann.jid.clone());
                }
            }
        }
        report
    }
}

// ============================================================
// Section: stall detectors, drill-facing view (intel/watchdog.py
// WDG-002/WDG-003 semantics + intel/thresholds.py defaults)
// ============================================================
// These detectors are the drill-facing model of the watchdog
// rules the B22 drills assert: a nick in caps, absent from
// presence, holding a claimed job past the stall window, is a
// presence-stall; the same nick present with no progress past
// the progress window is a progress-stall. The canonical
// watchdog port is B21's; this section must not drift from the
// documented rules (age strictly greater than the window,
// last-activity field preference order, one alert per
// (nick, job) pair, critical severity, tick never mutates).

/// Watchdog stall windows in minutes. Defaults are the
/// FND-030 locked values; the demo profile overrides the
/// progress window to 1 minute (see the demo test).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct StallThresholds {
    /// Presence-stall window (WDG-002), default 10.
    pub stall_minutes: i64,
    /// Progress-stall window (WDG-003), default 10.
    pub progress_stall_minutes: i64,
}

impl Default for StallThresholds {
    fn default() -> Self {
        StallThresholds {
            stall_minutes: 10,
            progress_stall_minutes: 10,
        }
    }
}

impl StallThresholds {
    /// Defaults, as `StallThresholds::default()`.
    pub fn defaults() -> StallThresholds {
        StallThresholds::default()
    }

    /// Read `WATCHDOG_STALL_MINUTES` /
    /// `WATCHDOG_PROGRESS_STALL_MINUTES` with the Python
    /// `_env_int` fallback rule: unset, blank, unparseable, or
    /// below-minimum (0) falls back to the default silently.
    pub fn from_env() -> StallThresholds {
        fn env_int(name: &str, default: i64) -> i64 {
            match std::env::var(name) {
                Ok(raw) => {
                    let raw = raw.trim();
                    if raw.is_empty() {
                        return default;
                    }
                    match raw.parse::<i64>() {
                        Ok(v) if v >= 0 => v,
                        _ => default,
                    }
                }
                Err(_) => default,
            }
        }
        StallThresholds {
            stall_minutes: env_int("WATCHDOG_STALL_MINUTES", 10),
            progress_stall_minutes: env_int("WATCHDOG_PROGRESS_STALL_MINUTES", 10),
        }
    }
}

/// Default claim lease in seconds (thresholds.LEASE_DEFAULT_SECONDS).
pub const LEASE_DEFAULT_SECONDS: i64 = 1800;

/// A job row in a watchdog snapshot.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct SnapshotJob {
    /// Job id.
    pub id: String,
    /// Job title.
    pub title: String,
    /// Status, e.g. `claimed` or `open`.
    pub status: String,
    /// Claiming nick, if claimed.
    pub claim: Option<String>,
    /// Claim time, Unix seconds.
    pub claimed_at: Option<i64>,
    /// Last progress time, Unix seconds (snapshot's real field).
    pub last_progress_at: Option<i64>,
    /// Explicit progress timestamp (drill fixtures use this).
    pub last_progress: Option<i64>,
    /// Alternate progress timestamp fields, in preference order.
    pub progress_at: Option<i64>,
    /// Alternate progress timestamp fields, in preference order.
    pub note_ts: Option<i64>,
}

/// A watchdog snapshot: caps registry, presence list, jobs.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct Snapshot {
    /// Nicks in the caps registry.
    pub caps: Vec<String>,
    /// Nicks currently present.
    pub presence: Vec<String>,
    /// Job rows.
    pub jobs: Vec<SnapshotJob>,
}

/// Last known activity timestamp for a claimed job, or `None`.
///
/// Preference order, exactly as Python `_last_activity`:
/// last_progress, progress_at, note_ts, last_progress_at,
/// claimed_at. A job with no timestamp at all yields `None`:
/// the detector never invents an age for it.
pub fn last_activity(job: &SnapshotJob) -> Option<i64> {
    job.last_progress
        .or(job.progress_at)
        .or(job.note_ts)
        .or(job.last_progress_at)
        .or(job.claimed_at)
}

/// One stall alert, in the Python alert-dict shape (minus the
/// `explanations.render` wording, which lives in another
/// module: `explanation` here is a plain rendering, and only
/// kind/nick/job/severity/ages are asserted by the drills).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StallAlert {
    /// `presence-stall` or `progress-stall`.
    pub kind: String,
    /// Always `critical` for stall alerts.
    pub severity: String,
    /// The stalled nick.
    pub nick: String,
    /// The stalled job id.
    pub job: String,
    /// The job title.
    pub job_title: String,
    /// Age in seconds at detection time.
    pub last_progress_age_seconds: i64,
    /// Age in whole minutes.
    pub last_progress_age_minutes: i64,
    /// Dedupe key, `<kind>:<nick>:<job>`.
    pub dedupe_key: String,
    /// Detection time.
    pub created_at: i64,
    /// Plain explanation text.
    pub explanation: String,
}

fn stall_alert(
    kind: &str,
    nick: &str,
    job: &SnapshotJob,
    age: i64,
    now: i64,
) -> StallAlert {
    StallAlert {
        kind: kind.to_string(),
        severity: "critical".to_string(),
        nick: nick.to_string(),
        job: job.id.clone(),
        job_title: job.title.clone(),
        last_progress_age_seconds: age,
        last_progress_age_minutes: age / 60,
        dedupe_key: format!("{kind}:{nick}:{}", job.id),
        created_at: now,
        explanation: format!("{nick} stalled on job {} (age {}m)", job.id, age / 60),
    }
}

/// WDG-002 presence-stall detector: a nick in caps, absent from
/// presence, holding a claimed job with no activity longer
/// than the stall window. One alert per (nick, job) pair.
pub fn detect_presence_stall(
    snapshot: &Snapshot,
    now: i64,
    thresholds: StallThresholds,
) -> Vec<StallAlert> {
    let caps: BTreeSet<&str> = snapshot.caps.iter().map(|s| s.as_str()).collect();
    let present: BTreeSet<&str> = snapshot.presence.iter().map(|s| s.as_str()).collect();
    let window = thresholds.stall_minutes * 60;
    let mut alerts = Vec::new();
    for job in &snapshot.jobs {
        if job.status != "claimed" {
            continue;
        }
        let Some(nick) = job.claim.as_deref() else {
            continue;
        };
        if !caps.contains(nick) || present.contains(nick) {
            continue;
        }
        let Some(last) = last_activity(job) else {
            continue;
        };
        let age = now - last;
        if age <= window {
            continue;
        }
        alerts.push(stall_alert("presence-stall", nick, job, age, now));
    }
    alerts
}

/// WDG-003 progress-stall detector: a nick in caps, present,
/// holding a claimed job with no activity longer than the
/// progress window. Distinct from presence-stall by
/// construction: one snapshot never yields both kinds for the
/// same job.
pub fn detect_progress_stall(
    snapshot: &Snapshot,
    now: i64,
    thresholds: StallThresholds,
) -> Vec<StallAlert> {
    let caps: BTreeSet<&str> = snapshot.caps.iter().map(|s| s.as_str()).collect();
    let present: BTreeSet<&str> = snapshot.presence.iter().map(|s| s.as_str()).collect();
    let window = thresholds.progress_stall_minutes * 60;
    let mut alerts = Vec::new();
    for job in &snapshot.jobs {
        if job.status != "claimed" {
            continue;
        }
        let Some(nick) = job.claim.as_deref() else {
            continue;
        };
        if !caps.contains(nick) || !present.contains(nick) {
            continue;
        }
        let Some(last) = last_activity(job) else {
            continue;
        };
        let age = now - last;
        if age <= window {
            continue;
        }
        alerts.push(stall_alert("progress-stall", nick, job, age, now));
    }
    alerts
}

/// The drill-facing tick: presence-stall alerts followed by
/// progress-stall alerts, without mutating the snapshot (the
/// OS-034 split: the watchdog records, systemd restarts).
/// This is the stall subset of the full watchdog tick; the
/// full tick is B21's port.
pub fn tick_stalls(snapshot: &Snapshot, now: i64, thresholds: StallThresholds) -> Vec<StallAlert> {
    let mut alerts = detect_presence_stall(snapshot, now, thresholds);
    alerts.extend(detect_progress_stall(snapshot, now, thresholds));
    alerts
}

/// Announcement lines for alerts: every critical alert yields
/// exactly one `ALERT:<id> <kind>: <explanation>` line, in
/// list order; anything else yields nothing. Embedded newlines
/// are flattened to spaces.
pub fn announcements_for(alerts: &[StallAlert]) -> Vec<String> {
    alerts
        .iter()
        .filter(|a| a.severity == "critical")
        .map(|a| {
            let line = format!("ALERT:{} {}: {}", a.dedupe_key, a.kind, a.explanation);
            line.split('\n').collect::<Vec<_>>().join(" ")
        })
        .collect()
}

// ============================================================
// Section: drill helpers (os/intel/drills/driver_*.py shared)
// ============================================================

/// Parse one INI-style section into key -> last value, as the
/// drills' `parse_section`/`parse_slice` do: lines are
/// stripped, `[...]` headers switch sections, and only
/// `key=value` lines inside the named section count.
pub fn parse_section(text: &str, section_name: &str) -> BTreeMap<String, String> {
    let mut values = BTreeMap::new();
    let mut section: Option<String> = None;
    for raw in text.split('\n') {
        let line = raw.trim();
        if line.starts_with('[') && line.ends_with(']') {
            section = Some(line[1..line.len() - 1].to_string());
            continue;
        }
        if section.as_deref() == Some(section_name) {
            if let Some((key, val)) = line.split_once('=') {
                values.insert(key.trim().to_string(), val.trim().to_string());
            }
        }
    }
    values
}

/// Parse one INI-style section into key -> all values, in
/// order, as `test_os_worker_units.sections` does (repeated
/// keys, e.g. `EnvironmentFile`, accumulate).
pub fn parse_section_multi(text: &str, section_name: &str) -> BTreeMap<String, Vec<String>> {
    let mut values: BTreeMap<String, Vec<String>> = BTreeMap::new();
    let mut section: Option<String> = None;
    for raw in text.split('\n') {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        if line.starts_with('[') && line.ends_with(']') {
            section = Some(line[1..line.len() - 1].to_string());
            continue;
        }
        if section.as_deref() == Some(section_name) {
            if let Some((key, val)) = line.split_once('=') {
                values
                    .entry(key.trim().to_string())
                    .or_default()
                    .push(val.trim().to_string());
            }
        }
    }
    values
}

/// The driver/worker slice limits both slices share:
/// `CPUQuota=100%`, `MemoryMax=1G` (OS-035/OS-056 starting
/// defaults until profiles are measured).
pub fn slice_expected() -> [(&'static str, &'static str); 2] {
    [("CPUQuota", "100%"), ("MemoryMax", "1G")]
}

/// A job in the bridge's view: the fields `apply_heartbeat`
/// reads and writes.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct BridgeJob {
    /// Job id.
    pub id: String,
    /// Job title.
    pub title: String,
    /// Status, e.g. `claimed`.
    pub status: String,
    /// Claiming nick.
    pub claim: String,
    /// Last progress time, set by the bridge rule.
    pub last_progress_at: Option<i64>,
}

/// The bridge rule, in one line: a driver heartbeat's `ts`
/// becomes the job's `last_progress_at`. Returns a new job;
/// the caller's job is never mutated, so a bad record cannot
/// rewrite history in place. Python `int(ts)` truncates
/// toward zero; Rust `as i64` does the same.
pub fn apply_heartbeat(job: &BridgeJob, ts: f64) -> BridgeJob {
    let mut out = job.clone();
    out.last_progress_at = Some(ts as i64);
    out
}

// ============================================================
// Section: lease sweep + kill-worker drill (B21's
// os/intel/drills/kill_worker.py, as asserted by B22's
// test_intel_drill_kill_worker.py)
// ============================================================
// The drill script itself belongs to B21; this section ports
// only what B22's kill-worker test file asserts: the sweep
// rule and the drill scenario's observable outcome. The
// sweep mirrors jobs.py `_claim_or_requeue`'s requeue rule.

/// A job row for the lease sweep.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct SweepJob {
    /// Job id.
    pub id: String,
    /// Status, e.g. `claimed` or `open`.
    pub status: String,
    /// Claiming nick.
    pub claim: Option<String>,
    /// Claiming host.
    pub claim_host: Option<String>,
    /// Claim time.
    pub claimed_at: Option<i64>,
    /// Lease expiry, Unix seconds.
    pub lease_until: Option<i64>,
}

/// Requeue every claimed job whose lease has expired: status
/// back to `open`, claim fields cleared (`claim`, `claim_host`,
/// `claimed_at`, `lease_until` -- exactly the fields jobs.py
/// deletes). A claimed job whose lease still holds, an open
/// job, or a claimed job with no numeric lease is left
/// untouched. Returns the requeued job ids.
pub fn sweep_expired_leases(jobs: &mut [SweepJob], now: i64) -> Vec<String> {
    let mut requeued = Vec::new();
    for job in jobs.iter_mut() {
        if job.status != "claimed" {
            continue;
        }
        let Some(lease_until) = job.lease_until else {
            continue;
        };
        if now < lease_until {
            continue;
        }
        job.claim = None;
        job.claim_host = None;
        job.claimed_at = None;
        job.lease_until = None;
        job.status = "open".to_string();
        requeued.push(job.id.clone());
    }
    requeued
}

/// The kill-worker drill's report: the stall alert, the
/// requeued ids, and the phase log.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct KillDrillReport {
    /// The phase-2 presence-stall alert.
    pub alert: StallAlert,
    /// Job ids requeued in phase 4.
    pub requeued: Vec<String>,
    /// Phase log lines, one per phase.
    pub log: Vec<String>,
}

/// Run the kill-worker drill scenario on fixtures (WDG-020):
/// a fake worker claims a job, posts one progress note, dies
/// mid-job, the watchdog raises exactly one presence-stall
/// alert, and the lease sweep requeues the job. Raises
/// (returns `Err`) on any failed phase assertion, as the
/// Python drill raises `AssertionError`.
pub fn run_kill_worker_drill() -> Result<KillDrillReport, String> {
    const NICK: &str = "pax";
    const JOB_ID: &str = "7";
    const T0: i64 = 100000;
    let thresholds = StallThresholds::defaults();
    let mut log: Vec<String> = Vec::new();

    // Phase 1 -- healthy worker: claim, one progress note, beats.
    let mut snapshot = Snapshot {
        caps: vec![NICK.to_string()],
        presence: vec![NICK.to_string()],
        jobs: vec![SnapshotJob {
            id: JOB_ID.to_string(),
            title: "demo job".to_string(),
            status: "claimed".to_string(),
            claim: Some(NICK.to_string()),
            claimed_at: Some(T0),
            last_progress_at: None,
            last_progress: Some(T0 + 120),
            progress_at: None,
            note_ts: None,
        }],
    };
    let got = tick_stalls(&snapshot, T0 + 300, thresholds);
    if !got.is_empty() {
        return Err(format!("healthy worker must yield zero alerts, got {got:?}"));
    }
    log.push("phase 1: healthy worker yields zero alerts".to_string());

    // Phase 2 -- the kill: heartbeats stop, presence goes dark.
    snapshot.presence.retain(|n| n != NICK);
    let stall_at = T0 + 300 + thresholds.stall_minutes * 60 + 61;
    let got = tick_stalls(&snapshot, stall_at, thresholds);
    if got.len() != 1 {
        return Err(format!(
            "dead worker must yield exactly one alert, got {}: {got:?}",
            got.len()
        ));
    }
    let alert = got[0].clone();
    if alert.kind != "presence-stall" || alert.nick != NICK || alert.job != JOB_ID {
        return Err(format!("unexpected alert: {alert:?}"));
    }
    let expected_age = stall_at - (T0 + 120);
    if alert.last_progress_age_seconds != expected_age {
        return Err(format!(
            "alert age {} != expected {expected_age}",
            alert.last_progress_age_seconds
        ));
    }
    let lines = announcements_for(&got);
    if lines.len() != 1 || !lines[0].starts_with("ALERT:") {
        return Err(format!("announcement line not held: {lines:?}"));
    }
    log.push(format!(
        "phase 2: presence-stall alert names {NICK}/{JOB_ID}, age {expected_age}s; announcement line held, not posted"
    ));

    // Phase 3 -- the sweep must NOT requeue before the lease ends.
    let mut sweep_jobs = vec![SweepJob {
        id: JOB_ID.to_string(),
        status: "claimed".to_string(),
        claim: Some(NICK.to_string()),
        claim_host: None,
        claimed_at: Some(T0),
        lease_until: Some(T0 + LEASE_DEFAULT_SECONDS),
    }];
    if !sweep_expired_leases(&mut sweep_jobs, stall_at).is_empty() {
        return Err("unexpired lease must not requeue".to_string());
    }
    if sweep_jobs[0].status != "claimed" {
        return Err("unexpired lease must stay claimed".to_string());
    }
    log.push("phase 3: unexpired lease stays claimed (no early requeue)".to_string());

    // Phase 4 -- lease expires, sweep requeues, alert auto-resolves.
    let requeue_at = T0 + LEASE_DEFAULT_SECONDS + 1;
    let requeued = sweep_expired_leases(&mut sweep_jobs, requeue_at);
    if requeued != vec![JOB_ID.to_string()] {
        return Err(format!("requeue must yield [{JOB_ID}], got {requeued:?}"));
    }
    if sweep_jobs[0].status != "open"
        || sweep_jobs[0].claim.is_some()
        || sweep_jobs[0].lease_until.is_some()
    {
        return Err("requeued job must be open with claim fields cleared".to_string());
    }
    snapshot.jobs[0].status = "open".to_string();
    snapshot.jobs[0].claim = None;
    let got = tick_stalls(&snapshot, requeue_at, thresholds);
    if !got.is_empty() {
        return Err(format!("requeued job must stop firing, got {got:?}"));
    }
    log.push("phase 4: lease expiry requeues job; re-tick yields zero alerts, job open for the next worker".to_string());

    Ok(KillDrillReport {
        alert,
        requeued,
        log,
    })
}

// ============================================================
// Tests -- organized by the Python test file they mirror.
// Test names reference the Python test they mirror.
// ============================================================

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::fs::PermissionsExt;

    /// A temp workdir that cleans itself up on drop.
    struct TestDir {
        path: PathBuf,
    }

    impl TestDir {
        fn new(tag: &str) -> TestDir {
            let n = TMP_COUNTER.fetch_add(1, Ordering::SeqCst);
            let path = std::env::temp_dir()
                .join(format!("os-worker-test-{tag}-{}-{n}", std::process::id()));
            std::fs::create_dir(&path).unwrap();
            TestDir { path }
        }
    }

    impl Drop for TestDir {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.path);
        }
    }

    fn base_spec() -> JobSpec {
        JobSpec {
            id: "job-1".to_string(),
            title: "write the output file".to_string(),
            spec: "Create out.txt in the workdir.".to_string(),
            files: vec!["out.txt".to_string()],
            accept: "file-exists: out.txt".to_string(),
            sig: Some("deadbeef".to_string()),
            max_attempts: 3,
        }
    }

    fn with_spec(mut f: impl FnMut(&mut JobSpec)) -> JobSpec {
        let mut s = base_spec();
        f(&mut s);
        s
    }

    /// `sh -c` command that writes `text` to `path` in the workdir.
    fn write_cmd(path: &str) -> Vec<String> {
        vec![
            "sh".to_string(),
            "-c".to_string(),
            format!("printf hi > {path}"),
        ]
    }

    fn sleeper_cmd() -> Vec<String> {
        vec!["sh".to_string(), "-c".to_string(), "exec sleep 60".to_string()]
    }

    /// Write an executable stand-in script into the workdir.
    fn standin(workdir: &Path, name: &str, text: &str) -> PathBuf {
        let path = workdir.join(name);
        std::fs::write(&path, text).unwrap();
        let mut perms = std::fs::metadata(&path).unwrap().permissions();
        perms.set_mode(0o755);
        std::fs::set_permissions(&path, perms).unwrap();
        path
    }

    const WRITER_SCRIPT: &str = "#!/bin/sh\necho \"starting job from prompt file\"\necho \"prompt file seen: yes\"\nprintf 'hi\\n' > out.txt\necho \"wrote out.txt\"\n";
    const SLEEPER_SCRIPT: &str = "#!/bin/sh\necho \"sleeping child ready\"\nexec sleep 60\n";
    const SIMPLE_SCRIPT: &str = "#!/bin/sh\necho \"working on the job\"\n";

    // ---------- sha256 / hmac / json (supporting code) ----------

    #[test]
    fn sha256_known_vectors() {
        assert_eq!(
            sha256_hex(b""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
        assert_eq!(
            sha256_hex(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }

    #[test]
    fn hmac_sha256_matches_python_vectors() {
        // Values computed with Python hmac/hashlib for the same inputs.
        assert_eq!(
            sign_intake("k", "o1", "hello"),
            "076b30bfc1e259e7e44540480ba3eff700fd7246cc960165cfdde45c27196466"
        );
        assert_eq!(
            sign_intake("secret", "order-1", "Do the thing"),
            "db215afeb9e254718235217a19f4ee005f32fa2f0ea9b85db1360bac185096c8"
        );
    }

    #[test]
    fn json_parse_and_render_spec() {
        let v = parse_json(
            r#"{"id":"job-1","files":["out.txt"],"max_attempts":3,"accept":"file-exists: out.txt","sig":"deadbeef","title":"t","spec":"s"}"#,
        )
        .unwrap();
        assert_eq!(v.get("id").and_then(|x| x.as_str()), Some("job-1"));
        assert_eq!(
            v.get("files").and_then(|x| x.as_str_list()),
            Some(vec!["out.txt".to_string()])
        );
        assert_eq!(v.get("max_attempts").and_then(|x| x.as_i64()), Some(3));
        assert!(parse_json("{bad").is_err());
        assert!(parse_json("{} trailing").is_err());
        let esc = parse_json(r#""a\nb\"c\\d""#).unwrap();
        assert_eq!(esc.as_str(), Some("a\nb\"c\\d"));
    }

    // ---------- acceptance checks ----------

    #[test]
    fn accept_parse_accept_cases() {
        assert_eq!(
            parse_accept("file-exists: out.txt\n# comment\n\ncontains: a.txt :: hi").unwrap(),
            vec![
                AcceptCheck {
                    kind: "file-exists".to_string(),
                    arg: "out.txt".to_string()
                },
                AcceptCheck {
                    kind: "contains".to_string(),
                    arg: "a.txt :: hi".to_string()
                },
            ]
        );
        assert!(parse_accept("nonsense without a colon").is_err());
        assert!(parse_accept("bogus: x").is_err());
        assert!(parse_accept("file-exists:").is_err());
        assert!(parse_accept("contains: a.txt").is_err());
        assert_eq!(parse_accept("").unwrap(), Vec::<AcceptCheck>::new());
    }

    #[test]
    fn accept_verify_from_disk_true_false_and_empty() {
        let dir = TestDir::new("accept");
        std::fs::write(dir.path.join("out.txt"), "hi").unwrap();
        let (ok, _) = verify_accept("file-exists: out.txt", &dir.path);
        assert!(ok);
        let (ok, _) = verify_accept("file-exists: missing.txt", &dir.path);
        assert!(!ok);
        let (ok, results) = verify_accept("", &dir.path);
        assert!(ok);
        assert_eq!(results[0].check, "(no acceptance criteria)");
        let (ok, results) = verify_accept("bogus: x", &dir.path);
        assert!(!ok);
        assert_eq!(results[0].check, "(parse)");
        let (ok, _) = verify_accept("contains: out.txt :: hi", &dir.path);
        assert!(ok);
        let (ok, _) = verify_accept("command-ok: true", &dir.path);
        assert!(ok);
    }

    // ---------- test_os_driver_contract.py ----------

    mod driver_contract {
        use super::*;

        fn started(dir: &TestDir, spec: JobSpec, cmd: Vec<String>) -> StubDriver {
            let mut d = StubDriver::new(&dir.path, None).unwrap();
            d.start(&spec, &cmd).unwrap();
            d
        }

        #[test]
        fn test_c1_unsigned_spec_rejected_and_nothing_spawns() {
            let dir = TestDir::new("c1");
            let missing = with_spec(|s| s.sig = None);
            for bad in [with_spec(|s| s.sig = Some(String::new())), missing] {
                let mut d = StubDriver::new(&dir.path, None).unwrap();
                let err = d.start(&bad, &write_cmd("out.txt")).unwrap_err();
                assert!(err.is_unsigned());
                assert!(!d.has_child());
            }
        }

        #[test]
        fn test_c2_unparseable_accept_rejected() {
            let dir = TestDir::new("c2");
            let mut d = StubDriver::new(&dir.path, None).unwrap();
            let err = d
                .start(
                    &with_spec(|s| s.accept = "nonsense without a colon".to_string()),
                    &write_cmd("out.txt"),
                )
                .unwrap_err();
            assert!(err.is_bad_spec());
            assert!(!d.has_child());
        }

        #[test]
        fn test_c3_empty_files_rejected() {
            let dir = TestDir::new("c3");
            let mut d = StubDriver::new(&dir.path, None).unwrap();
            let err = d
                .start(&with_spec(|s| s.files = vec![]), &write_cmd("out.txt"))
                .unwrap_err();
            assert!(err.is_bad_spec());
            assert!(!d.has_child());
        }

        #[test]
        fn test_c4_heartbeat_shape_and_before_start() {
            let dir = TestDir::new("c4");
            let d = StubDriver::new(&dir.path, None).unwrap();
            assert!(d.heartbeat("early").unwrap_err().is_not_started());
            let mut d = started(&dir, base_spec(), write_cmd("out.txt"));
            let rec = d.heartbeat("wrote the file").unwrap();
            assert_eq!(rec.line, "PROGRESS:job-1 wrote the file");
            assert_eq!(rec.job_id, "job-1");
            assert_eq!(rec.note, "wrote the file");
            assert!(rec.ts.is_finite() && rec.ts > 0.0);
            assert!(d.heartbeats().contains(&rec));
            let _ = d.artifacts();
        }

        #[test]
        fn test_c5_stop_kills_sleeping_child() {
            let dir = TestDir::new("c5");
            let mut d = started(&dir, base_spec(), sleeper_cmd());
            std::thread::sleep(Duration::from_millis(200));
            assert_eq!(d.poll().unwrap(), None);
            d.stop().unwrap();
            assert!(d.poll().unwrap().is_some());
            let _ = d.artifacts();
        }

        #[test]
        fn test_c6_changed_files_lists_new_file_not_log() {
            let dir = TestDir::new("c6");
            let mut d = started(&dir, base_spec(), write_cmd("out.txt"));
            let arts = d.artifacts().unwrap();
            assert!(arts.changed_files.contains(&"out.txt".to_string()));
            assert!(!arts.changed_files.contains(&"driver.log".to_string()));
            assert_eq!(arts.status, "done");
            assert_eq!(arts.exit_code, Some(0));
            assert!(arts.log.exists());
        }

        #[test]
        fn test_c7_acceptance_from_disk_true_and_false() {
            let dir = TestDir::new("c7");
            let mut d = started(&dir, base_spec(), write_cmd("out.txt"));
            assert!(d.artifacts().unwrap().acceptance_ok);
            let mut d2 = started(
                &dir,
                with_spec(|s| s.accept = "file-exists: missing.txt".to_string()),
                write_cmd("out.txt"),
            );
            assert!(!d2.artifacts().unwrap().acceptance_ok);
        }

        #[test]
        fn test_c8_unowned_changes_visible() {
            let dir = TestDir::new("c8");
            let mut d = started(&dir, base_spec(), write_cmd("stray.txt"));
            let arts = d.artifacts().unwrap();
            assert!(arts.changed_files.contains(&"stray.txt".to_string()));
            assert!(arts.unowned_files.contains(&"stray.txt".to_string()));
        }

        #[test]
        fn test_c9_stop_after_finish_safe_and_artifacts_stable() {
            let dir = TestDir::new("c9");
            let mut d = started(&dir, base_spec(), write_cmd("out.txt"));
            let first = d.artifacts().unwrap();
            d.stop().unwrap();
            let second = d.artifacts().unwrap();
            assert_eq!(first, second);
        }

        #[test]
        fn test_c10_no_bus_or_redis_imports() {
            // Rust adaptation: no `use` line in this crate may
            // reference a bus/Redis module. (Python reads the
            // driver's import lines; Rust has no dynamic imports
            // to audit beyond the `use` lines.)
            let src = include_str!("lib.rs");
            // NOTE: include_str! resolves relative to this file;
            // from tests inside lib.rs, "lib.rs" is this file.
            for line in src.split('\n') {
                let trimmed = line.trim();
                if trimmed.starts_with("use ") {
                    assert!(!trimmed.contains("redis"), "{trimmed}");
                    assert!(!trimmed.contains("upstash"), "{trimmed}");
                    assert!(!trimmed.contains("relay_common"), "{trimmed}");
                }
            }
        }

        #[test]
        fn test_start_twice_rejected_and_spec_defaults() {
            let dir = TestDir::new("twice");
            let mut d = started(&dir, base_spec(), write_cmd("out.txt"));
            let err = d.start(&base_spec(), &write_cmd("out.txt")).unwrap_err();
            assert_eq!(
                err,
                DriverError::Driver("driver already started for job job-1".to_string())
            );
            assert_eq!(validate_spec(&base_spec()).unwrap().max_attempts, 3);
            let _ = d.artifacts();
        }

        #[test]
        fn test_docs_pin_contract_and_checklist() {
            for token in [
                "start(job_spec)",
                "stop()",
                "heartbeat()",
                "artifacts()",
                "PROGRESS:",
                "mos/acceptance.py",
            ] {
                assert!(DRIVER_CONTRACT_MD.contains(token), "missing {token}");
            }
            for item in ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10"] {
                assert!(DRIVER_CONFORMANCE_MD.contains(item), "missing {item}");
            }
            assert!(!DRIVER_CONTRACT_MD.contains('\u{2014}'));
            assert!(!DRIVER_CONFORMANCE_MD.contains('\u{2014}'));
            // T146 byte-identity pins.
            assert_eq!(sha256_hex(DRIVER_CONTRACT_MD.as_bytes()), DRIVER_CONTRACT_SHA256);
            assert_eq!(
                sha256_hex(DRIVER_CONFORMANCE_MD.as_bytes()),
                DRIVER_CONFORMANCE_SHA256
            );
            // The OS-053 README record lives in the live docs.
            let readme = include_str!("../../../os/os/README.md");
            assert!(readme.contains("OS-053"));
            let spec = include_str!("../../../os/plan/META_OS.md");
            assert!(spec.contains("OS-053"));
        }
    }

    // ---------- test_os_driver_muse.py ----------

    mod driver_muse {
        use super::*;

        fn started(dir: &TestDir, spec: JobSpec, binary: &str) -> MuseDriver {
            let mut d = MuseDriver::new(&dir.path, None, Some(binary), &[]).unwrap();
            d.start(&spec).unwrap();
            d
        }

        #[test]
        fn test_c1_unsigned_spec_rejected_and_nothing_spawns() {
            let dir = TestDir::new("m1");
            let writer = standin(&dir.path, "writer", WRITER_SCRIPT);
            let writer = writer.to_string_lossy().into_owned();
            let missing = with_spec(|s| s.sig = None);
            for bad in [with_spec(|s| s.sig = Some(String::new())), missing] {
                let mut d = MuseDriver::new(&dir.path, None, Some(&writer), &[]).unwrap();
                let err = d.start(&bad).unwrap_err();
                assert!(err.is_unsigned());
                assert!(!d.has_child());
            }
        }

        #[test]
        fn test_c2_unparseable_accept_rejected() {
            let dir = TestDir::new("m2");
            let writer = standin(&dir.path, "writer", WRITER_SCRIPT);
            let mut d =
                MuseDriver::new(&dir.path, None, Some(&writer.to_string_lossy()), &[]).unwrap();
            let err = d
                .start(&with_spec(|s| s.accept = "nonsense without a colon".to_string()))
                .unwrap_err();
            assert!(err.is_bad_spec());
            assert!(!d.has_child());
        }

        #[test]
        fn test_c3_empty_files_rejected() {
            let dir = TestDir::new("m3");
            let writer = standin(&dir.path, "writer", WRITER_SCRIPT);
            let mut d =
                MuseDriver::new(&dir.path, None, Some(&writer.to_string_lossy()), &[]).unwrap();
            let err = d
                .start(&with_spec(|s| s.files = vec![]))
                .unwrap_err();
            assert!(err.is_bad_spec());
            assert!(!d.has_child());
        }

        #[test]
        fn test_c4_heartbeat_shape_and_before_start() {
            let dir = TestDir::new("m4");
            let writer = standin(&dir.path, "writer", WRITER_SCRIPT);
            let d = MuseDriver::new(&dir.path, None, Some(&writer.to_string_lossy()), &[])
                .unwrap();
            assert!(d.heartbeat("early").unwrap_err().is_not_started());
            let mut d = started(&dir, base_spec(), &writer.to_string_lossy());
            let rec = d.heartbeat("wrote the file").unwrap();
            assert_eq!(rec.line, "PROGRESS:job-1 wrote the file");
            assert_eq!(rec.job_id, "job-1");
            assert_eq!(rec.note, "wrote the file");
            assert!(rec.ts.is_finite() && rec.ts > 0.0);
            assert!(d.heartbeats().contains(&rec));
            let _ = d.artifacts();
        }

        #[test]
        fn test_c5_stop_kills_sleeping_child() {
            let dir = TestDir::new("m5");
            let sleeper = standin(&dir.path, "sleeper", SLEEPER_SCRIPT);
            let mut d = started(&dir, base_spec(), &sleeper.to_string_lossy());
            std::thread::sleep(Duration::from_millis(300));
            assert_eq!(d.poll().unwrap(), None);
            d.stop().unwrap();
            assert!(d.poll().unwrap().is_some());
            let _ = d.artifacts();
        }

        #[test]
        fn test_c6_changed_files_lists_new_file_not_log() {
            let dir = TestDir::new("m6");
            let writer = standin(&dir.path, "writer", WRITER_SCRIPT);
            let mut d = started(&dir, base_spec(), &writer.to_string_lossy());
            let arts = d.artifacts().unwrap();
            assert!(arts.changed_files.contains(&"out.txt".to_string()));
            assert!(!arts.changed_files.contains(&"driver.log".to_string()));
            assert_eq!(arts.status, "done");
            assert_eq!(arts.exit_code, Some(0));
            assert!(arts.log.exists());
        }

        #[test]
        fn test_c7_acceptance_from_disk_true_and_false() {
            let dir = TestDir::new("m7");
            let writer = standin(&dir.path, "writer", WRITER_SCRIPT);
            let w = writer.to_string_lossy().into_owned();
            let mut d = started(&dir, base_spec(), &w);
            assert!(d.artifacts().unwrap().acceptance_ok);
            let mut d2 = started(
                &dir,
                with_spec(|s| s.accept = "file-exists: missing.txt".to_string()),
                &w,
            );
            assert!(!d2.artifacts().unwrap().acceptance_ok);
        }

        #[test]
        fn test_c8_unowned_changes_visible() {
            let dir = TestDir::new("m8");
            let writer = standin(&dir.path, "writer", WRITER_SCRIPT);
            // Writer always writes out.txt; make out.txt unowned here.
            let mut d = started(
                &dir,
                with_spec(|s| s.files = vec!["other.txt".to_string()]),
                &writer.to_string_lossy(),
            );
            let arts = d.artifacts().unwrap();
            assert!(arts.changed_files.contains(&"out.txt".to_string()));
            assert!(arts.unowned_files.contains(&"out.txt".to_string()));
        }

        #[test]
        fn test_c9_stop_after_finish_safe_and_artifacts_stable() {
            let dir = TestDir::new("m9");
            let writer = standin(&dir.path, "writer", WRITER_SCRIPT);
            let mut d = started(&dir, base_spec(), &writer.to_string_lossy());
            let first = d.artifacts().unwrap();
            d.stop().unwrap();
            let second = d.artifacts().unwrap();
            assert_eq!(first, second);
        }

        #[test]
        fn test_c10_no_bus_or_redis_imports() {
            let src = include_str!("lib.rs");
            for line in src.split('\n') {
                let trimmed = line.trim();
                if trimmed.starts_with("use ") {
                    assert!(!trimmed.contains("redis"), "{trimmed}");
                    assert!(!trimmed.contains("upstash"), "{trimmed}");
                    assert!(!trimmed.contains("relay_common"), "{trimmed}");
                }
            }
        }

        #[test]
        fn test_prompt_carries_work_not_signature() {
            let prompt = build_prompt(&base_spec());
            assert!(prompt.contains("write the output file"));
            assert!(prompt.contains("Create out.txt in the workdir."));
            assert!(prompt.contains("out.txt"));
            assert!(prompt.contains("file-exists: out.txt"));
            assert!(!prompt.contains("deadbeef"));
        }

        #[test]
        fn test_argv_shape_and_extra_args() {
            assert_eq!(
                build_argv("muse", "/tmp/prompt.md", &[]),
                vec![
                    "muse".to_string(),
                    "exec".to_string(),
                    "--prompt-file".to_string(),
                    "/tmp/prompt.md".to_string()
                ]
            );
            let argv = build_argv("muse", "/tmp/prompt.md", &["--json".to_string()]);
            assert_eq!(argv.last().unwrap(), "--json");
        }

        #[test]
        fn test_child_output_streamed_into_heartbeats() {
            let dir = TestDir::new("mstream");
            let writer = standin(&dir.path, "writer", WRITER_SCRIPT);
            let (sink, collected) = vec_sink();
            let mut d = MuseDriver::new(
                &dir.path,
                Some(sink),
                Some(&writer.to_string_lossy()),
                &[],
            )
            .unwrap();
            d.start(&base_spec()).unwrap();
            let arts = d.artifacts().unwrap();
            assert_eq!(arts.status, "done");
            let sink_records = collected.lock().unwrap().clone();
            let notes: Vec<String> =
                sink_records.iter().map(|r| r.note.clone()).collect();
            assert!(notes.contains(&"wrote out.txt".to_string()), "{notes:?}");
            for rec in &sink_records {
                assert!(rec.line.starts_with("PROGRESS:job-1 "));
                assert_eq!(rec.job_id, "job-1");
            }
            let log = std::fs::read_to_string(dir.path.join("driver.log")).unwrap();
            assert!(log.contains("wrote out.txt"));
        }

        #[test]
        fn test_missing_binary_refused_before_spawning() {
            let dir = TestDir::new("mmissing");
            let mut d = MuseDriver::new(&dir.path, None, Some("/nonexistent/muse-binary"), &[])
                .unwrap();
            let err = d.start(&base_spec()).unwrap_err();
            assert!(matches!(err, DriverError::Driver(_)));
            assert!(!d.has_child());
        }

        #[test]
        fn test_prompt_file_lives_outside_workdir_and_is_cleaned() {
            let dir = TestDir::new("mprompt");
            let writer = standin(&dir.path, "writer", WRITER_SCRIPT);
            let mut d = started(&dir, base_spec(), &writer.to_string_lossy());
            let tmpdir = d.tmpdir().unwrap();
            assert!(!tmpdir.starts_with(&dir.path));
            d.artifacts().unwrap();
            assert!(!tmpdir.exists());
        }

        #[test]
        fn test_runner_prints_artifacts_json() {
            let dir = TestDir::new("mrunner");
            let writer = standin(&dir.path, "writer", WRITER_SCRIPT);
            let spec_json = format!(
                r#"{{"id":"job-1","title":"write the output file","spec":"Create out.txt in the workdir.","files":["out.txt"],"accept":"file-exists: out.txt","sig":"deadbeef"}}"#
            );
            // The caller owns the spec file; the runner reads it.
            std::fs::write(dir.path.join("job.json"), &spec_json).unwrap();
            let text = std::fs::read_to_string(dir.path.join("job.json")).unwrap();
            let arts = run_driver(&text, &dir.path, Some(&writer.to_string_lossy()), &[])
                .unwrap();
            assert_eq!(arts.status, "done");
            assert!(arts.changed_files.contains(&"out.txt".to_string()));
            assert!(arts.acceptance_ok);
            // The printed shape parses back as JSON with the same fields.
            let rendered = arts.to_json();
            let back = parse_json(&rendered).unwrap();
            assert_eq!(back.get("status").and_then(|v| v.as_str()), Some("done"));
            assert_eq!(back.get("job_id").and_then(|v| v.as_str()), Some("job-1"));
        }

        #[test]
        fn test_runner_refuses_unsigned_spec_with_exit_2() {
            let dir = TestDir::new("mrunner2");
            let writer = standin(&dir.path, "writer", WRITER_SCRIPT);
            let spec_json = r#"{"id":"job-1","title":"t","spec":"s","files":["out.txt"],"accept":"file-exists: out.txt"}"#;
            // No sig: the Rust run_driver returns Err, which the
            // CLI maps to exit 2 with nothing on stdout.
            let err = run_driver(spec_json, &dir.path, Some(&writer.to_string_lossy()), &[])
                .unwrap_err();
            assert!(err.contains("run_driver:"));
        }
    }

    // ---------- test_intel_driver_heartbeat_bridge.py ----------

    mod driver_heartbeat_bridge {
        use super::*;

        const DRIVER: &str = "driver-audio";
        const JOB: &str = "d1";

        fn snapshot_for(present: &[&str], last: i64) -> Snapshot {
            Snapshot {
                caps: vec![DRIVER.to_string()],
                presence: present.iter().map(|s| s.to_string()).collect(),
                jobs: vec![SnapshotJob {
                    id: JOB.to_string(),
                    title: "play boot sting".to_string(),
                    status: "claimed".to_string(),
                    claim: Some(DRIVER.to_string()),
                    claimed_at: Some(last),
                    last_progress_at: Some(last),
                    ..Default::default()
                }],
            }
        }

        #[test]
        fn test_template_joins_driver_slice() {
            let template = include_str!("../../../os/os/services/relay-driver@.service");
            let values = parse_section(template, "Service");
            assert_eq!(values.get("Slice").map(|s| s.as_str()), Some("relay-drivers.slice"));
            // The slice itself carries the OS-056 starting defaults.
            let slice = include_str!("../../../os/os/services/relay-drivers.slice");
            let slice_vals = parse_section(slice, "Slice");
            for (key, want) in slice_expected() {
                assert_eq!(slice_vals.get(key).map(|s| s.as_str()), Some(want));
            }
        }

        #[test]
        fn test_drill_and_eval_exist() {
            // Referencing the live files makes the build fail if
            // either disappears, which is the existence pin.
            let drill = include_str!("../../../os/intel/drills/driver_heartbeat_bridge.py");
            assert!(drill.contains("def apply_heartbeat"));
            let eval = include_str!("../../../os/intel/evals/driver_heartbeat_bridge.md");
            assert!(!eval.is_empty());
        }

        #[test]
        fn test_no_em_dash_in_new_files() {
            let drill = include_str!("../../../os/intel/drills/driver_heartbeat_bridge.py");
            let eval = include_str!("../../../os/intel/evals/driver_heartbeat_bridge.md");
            assert!(!drill.contains('\u{2014}'));
            assert!(!eval.contains('\u{2014}'));
        }

        #[test]
        fn test_driver_heartbeat_shape() {
            let dir = TestDir::new("bridge");
            let standin_path = standin(&dir.path, "fake-muse", SIMPLE_SCRIPT);
            let mut driver = MuseDriver::new(
                &dir.path,
                None,
                Some(&standin_path.to_string_lossy()),
                &[],
            )
            .unwrap();
            let spec = JobSpec {
                id: JOB.to_string(),
                title: "play boot sting".to_string(),
                spec: "Play the boot sting.".to_string(),
                files: vec!["sting.mp3".to_string()],
                accept: "file-exists: sting.mp3".to_string(),
                sig: Some("deadbeef".to_string()),
                max_attempts: 3,
            };
            driver.start(&spec).unwrap();
            let deadline = std::time::Instant::now() + Duration::from_secs(5);
            while driver.heartbeats().is_empty() && std::time::Instant::now() < deadline {
                std::thread::sleep(Duration::from_millis(50));
            }
            let _ = driver.stop();
            let records = driver.heartbeats();
            assert!(!records.is_empty());
            for record in &records {
                assert!(record.line.starts_with(&format!("PROGRESS:{JOB} ")));
                assert_eq!(record.job_id, JOB);
                assert!(record.ts.is_finite());
            }
        }

        #[test]
        fn test_bridge_mapping_does_not_mutate() {
            let job = BridgeJob {
                id: JOB.to_string(),
                status: "claimed".to_string(),
                claim: DRIVER.to_string(),
                ..Default::default()
            };
            let out = apply_heartbeat(&job, 1234567.9);
            assert_eq!(out.last_progress_at, Some(1234567));
            assert_eq!(job.last_progress_at, None);
        }

        #[test]
        fn test_fresh_heartbeat_no_alert() {
            let now = 200000;
            let snap = snapshot_for(&[DRIVER], now - 30);
            let t = StallThresholds::defaults();
            assert!(detect_presence_stall(&snap, now, t).is_empty());
            assert!(detect_progress_stall(&snap, now, t).is_empty());
        }

        #[test]
        fn test_stale_present_is_progress_stall_only() {
            let now = 200000;
            let stale = now - StallThresholds::defaults().progress_stall_minutes * 60 - 1;
            let snap = snapshot_for(&[DRIVER], stale);
            let t = StallThresholds::defaults();
            let progress = detect_progress_stall(&snap, now, t);
            assert_eq!(progress.len(), 1);
            assert_eq!(progress[0].kind, "progress-stall");
            assert_eq!(progress[0].nick, DRIVER);
            assert_eq!(progress[0].job, JOB);
            assert!(detect_presence_stall(&snap, now, t).is_empty());
        }

        #[test]
        fn test_stale_absent_is_presence_stall_only() {
            let now = 200000;
            let stale = now - StallThresholds::defaults().stall_minutes * 60 - 1;
            let snap = snapshot_for(&[], stale);
            let t = StallThresholds::defaults();
            let presence = detect_presence_stall(&snap, now, t);
            assert_eq!(presence.len(), 1);
            assert_eq!(presence[0].kind, "presence-stall");
            assert!(detect_progress_stall(&snap, now, t).is_empty());
        }

        #[test]
        fn test_tick_leaves_job_claimed() {
            let now = 200000;
            let stale = now - StallThresholds::defaults().progress_stall_minutes * 60 - 1;
            let snap = snapshot_for(&[DRIVER], stale);
            let alerts = tick_stalls(&snap, now, StallThresholds::defaults());
            let driver_alerts: Vec<_> =
                alerts.iter().filter(|a| a.nick == DRIVER).collect();
            assert_eq!(driver_alerts.len(), 1);
            assert_eq!(snap.jobs[0].status, "claimed");
        }

        #[test]
        fn test_watchdog_has_no_driver_special_casing() {
            let src = include_str!("../../../os/intel/watchdog.py");
            assert!(!src.to_lowercase().contains("driver"));
        }
    }

    // ---------- test_intel_driver_stall.py ----------

    mod driver_stall {
        use super::*;

        const WEDGED: &str = "driver-audio";
        const SIBLING: &str = "driver-video";
        const WORKER: &str = "pax";
        const T0: i64 = 100000;

        fn snapshot(wedged_last: i64, sibling_last: i64, worker_last: i64) -> Snapshot {
            let job = |id: &str, title: &str, claim: &str, last: i64| SnapshotJob {
                id: id.to_string(),
                title: title.to_string(),
                status: "claimed".to_string(),
                claim: Some(claim.to_string()),
                claimed_at: Some(T0),
                last_progress_at: Some(last),
                ..Default::default()
            };
            Snapshot {
                caps: vec![WEDGED.to_string(), SIBLING.to_string(), WORKER.to_string()],
                presence: vec![WEDGED.to_string(), SIBLING.to_string(), WORKER.to_string()],
                jobs: vec![
                    job("d1", "play boot sting", WEDGED, wedged_last),
                    job("d2", "render caption", SIBLING, sibling_last),
                    job("w1", "write brief", WORKER, worker_last),
                ],
            }
        }

        #[test]
        fn test_drill_exists_with_all_phases() {
            let drill = include_str!("../../../os/intel/drills/driver_stall.py");
            for phase in ["phase_detector", "phase_equivalence", "phase_demo", "phase_contract"] {
                assert!(drill.contains(phase), "missing {phase}");
            }
        }

        #[test]
        fn test_eval_exists() {
            let eval = include_str!("../../../os/intel/evals/driver_stall.md");
            assert!(!eval.is_empty());
        }

        #[test]
        fn test_spec_records_drill() {
            let spec = include_str!("../../../os/plan/META_OS.md");
            assert!(spec.contains("OS-057"));
            assert!(spec.contains("driver_stall.py"));
        }

        #[test]
        fn test_demo_env_sets_one_minute_window() {
            let env = include_str!("../../../os/intel/metaos-demo.env");
            assert!(env.contains("WATCHDOG_PROGRESS_STALL_MINUTES=1"));
        }

        #[test]
        fn test_no_em_dash_in_new_files() {
            let drill = include_str!("../../../os/intel/drills/driver_stall.py");
            let eval = include_str!("../../../os/intel/evals/driver_stall.md");
            assert!(!drill.contains('\u{2014}'));
            assert!(!eval.contains('\u{2014}'));
        }

        #[test]
        fn test_wedged_driver_progress_stall() {
            let t = StallThresholds::defaults();
            let stall_at = T0 + t.progress_stall_minutes * 60 + 1;
            let snap = snapshot(T0, stall_at - 60, stall_at - 60);
            let alerts = detect_progress_stall(&snap, stall_at, t);
            assert_eq!(alerts.len(), 1);
            assert_eq!(alerts[0].kind, "progress-stall");
            assert_eq!(alerts[0].nick, WEDGED);
            assert_eq!(alerts[0].job, "d1");
            assert_eq!(alerts[0].severity, "critical");
        }

        #[test]
        fn test_wedged_driver_no_presence_stall() {
            let t = StallThresholds::defaults();
            let stall_at = T0 + t.progress_stall_minutes * 60 + 1;
            let snap = snapshot(T0, stall_at - 60, stall_at - 60);
            assert!(detect_presence_stall(&snap, stall_at, t).is_empty());
        }

        #[test]
        fn test_wedged_worker_same_alert() {
            let t = StallThresholds::defaults();
            let stall_at = T0 + t.progress_stall_minutes * 60 + 1;
            let snap = snapshot(stall_at - 60, stall_at - 60, T0);
            let alerts = detect_progress_stall(&snap, stall_at, t);
            assert_eq!(alerts.len(), 1);
            assert_eq!(alerts[0].kind, "progress-stall");
            assert_eq!(alerts[0].nick, WORKER);
            assert_eq!(alerts[0].job, "w1");
            assert_eq!(alerts[0].severity, "critical");
        }

        #[test]
        fn test_demo_window_fires_at_61s_and_quiet_at_30s() {
            // The demo profile sets the progress window to 1
            // minute; the Python drill proves this by rerunning
            // itself in a subprocess under that env var. Here
            // the same decision runs directly with a 1-minute
            // window, which is the behavior the probe asserts.
            let t = StallThresholds {
                progress_stall_minutes: 1,
                ..StallThresholds::defaults()
            };
            let snap = snapshot(T0, T0 + 61, T0 + 61);
            let alerts = detect_progress_stall(&snap, T0 + 61, t);
            assert_eq!(alerts.len(), 1);
            assert_eq!(alerts[0].nick, WEDGED);
            let snap = snapshot(T0 + 31, T0 + 61, T0 + 61);
            assert!(detect_progress_stall(&snap, T0 + 61, t).is_empty());
        }

        #[test]
        fn test_tick_leaves_both_driver_jobs_claimed() {
            let t = StallThresholds::defaults();
            let stall_at = T0 + t.progress_stall_minutes * 60 + 1;
            let snap = snapshot(T0, stall_at - 60, stall_at - 60);
            let alerts = tick_stalls(&snap, stall_at, t);
            let wedged: Vec<_> = alerts.iter().filter(|a| a.nick == WEDGED).collect();
            let sibling: Vec<_> = alerts.iter().filter(|a| a.nick == SIBLING).collect();
            assert_eq!(wedged.len(), 1);
            assert!(sibling.is_empty());
            let by_id: HashMap<&str, &SnapshotJob> =
                snap.jobs.iter().map(|j| (j.id.as_str(), j)).collect();
            assert_eq!(by_id["d1"].claim.as_deref(), Some(WEDGED));
            assert_eq!(by_id["d1"].status, "claimed");
            assert_eq!(by_id["d2"].claim.as_deref(), Some(SIBLING));
            assert_eq!(by_id["d2"].status, "claimed");
        }
    }

    // ---------- test_intel_driver_supervision.py ----------

    mod driver_supervision {
        use super::*;

        const DRIVER: &str = "driver-audio";

        fn snapshot(present: &[&str]) -> (i64, Snapshot) {
            let t0 = 100000;
            (
                t0,
                Snapshot {
                    caps: vec![DRIVER.to_string()],
                    presence: present.iter().map(|s| s.to_string()).collect(),
                    jobs: vec![SnapshotJob {
                        id: "d1".to_string(),
                        title: "play boot sting".to_string(),
                        status: "claimed".to_string(),
                        claim: Some(DRIVER.to_string()),
                        claimed_at: Some(t0),
                        last_progress_at: Some(t0),
                        ..Default::default()
                    }],
                },
            )
        }

        #[test]
        fn test_slice_values() {
            let slice = include_str!("../../../os/os/services/relay-drivers.slice");
            let values = parse_section(slice, "Slice");
            for (key, want) in slice_expected() {
                assert_eq!(values.get(key).map(|s| s.as_str()), Some(want), "{key}");
            }
        }

        #[test]
        fn test_spec_records_slice_and_values() {
            let spec = include_str!("../../../os/plan/META_OS.md");
            assert!(spec.contains("relay-drivers.slice"));
            assert!(spec.contains("OS-056"));
            for want in ["100%", "1G"] {
                assert!(spec.contains(want));
            }
        }

        #[test]
        fn test_drill_exists_with_all_phases() {
            let drill = include_str!("../../../os/intel/drills/driver_supervision.py");
            for phase in ["phase_file", "phase_verify", "phase_detector", "phase_contract"] {
                assert!(drill.contains(phase), "missing {phase}");
            }
        }

        #[test]
        fn test_eval_exists() {
            let eval = include_str!("../../../os/intel/evals/driver_supervision.md");
            assert!(!eval.is_empty());
        }

        #[test]
        fn test_no_em_dash_in_new_files() {
            let slice = include_str!("../../../os/os/services/relay-drivers.slice");
            let drill = include_str!("../../../os/intel/drills/driver_supervision.py");
            let eval = include_str!("../../../os/intel/evals/driver_supervision.md");
            assert!(!slice.contains('\u{2014}'));
            assert!(!drill.contains('\u{2014}'));
            assert!(!eval.contains('\u{2014}'));
        }

        #[test]
        fn test_driver_presence_stall() {
            let (t0, snap) = snapshot(&[]);
            let t = StallThresholds::defaults();
            let stall_at = t0 + t.stall_minutes * 60 + 1;
            let alerts = detect_presence_stall(&snap, stall_at, t);
            assert_eq!(alerts.len(), 1);
            assert_eq!(alerts[0].kind, "presence-stall");
            assert_eq!(alerts[0].nick, DRIVER);
            assert_eq!(alerts[0].job, "d1");
            assert_eq!(alerts[0].severity, "critical");
        }

        #[test]
        fn test_present_driver_no_alert_and_fresh_no_alert() {
            let (t0, snap) = snapshot(&[DRIVER]);
            let t = StallThresholds::defaults();
            let stall_at = t0 + t.stall_minutes * 60 + 1;
            assert!(detect_presence_stall(&snap, stall_at, t).is_empty());
            let (_, snap) = snapshot(&[]);
            assert!(detect_presence_stall(&snap, t0 + 60, t).is_empty());
        }

        #[test]
        fn test_tick_leaves_driver_job_claimed() {
            let (t0, snap) = snapshot(&[]);
            let t = StallThresholds::defaults();
            let stall_at = t0 + t.stall_minutes * 60 + 1;
            let alerts = tick_stalls(&snap, stall_at, t);
            let driver_alerts: Vec<_> =
                alerts.iter().filter(|a| a.nick == DRIVER).collect();
            assert_eq!(driver_alerts.len(), 1);
            assert_eq!(snap.jobs[0].status, "claimed");
            assert_eq!(snap.jobs[0].claim.as_deref(), Some(DRIVER));
        }
    }

    // ---------- test_os_worker_units.py + test_os_workers_slice.py ----------

    mod worker_units_and_slice {
        use super::*;

        #[test]
        fn test_template_exists_and_unit_ordering() {
            let unit = include_str!("../../../os/os/services/relay-worker@.service");
            let sections = parse_section_multi(unit, "Unit");
            let after = sections.get("After").cloned().unwrap_or_default().join(" ");
            assert!(after.contains("relay-jobs.service"));
            assert_eq!(sections.get("PartOf").cloned().unwrap_or_default(), vec!["relay.target"]);
        }

        #[test]
        fn test_service_identity_slice_restart() {
            let unit = include_str!("../../../os/os/services/relay-worker@.service");
            let svc = parse_section_multi(unit, "Service");
            assert_eq!(svc.get("User").cloned().unwrap_or_default(), vec!["relay"]);
            assert_eq!(svc.get("Group").cloned().unwrap_or_default(), vec!["relay"]);
            assert_eq!(
                svc.get("WorkingDirectory").cloned().unwrap_or_default(),
                vec!["/opt/relay"]
            );
            assert_eq!(
                svc.get("Slice").cloned().unwrap_or_default(),
                vec!["relay-workers.slice"]
            );
            assert_eq!(svc.get("Restart").cloned().unwrap_or_default(), vec!["on-failure"]);
        }

        #[test]
        fn test_instance_name_is_the_nick() {
            let unit = include_str!("../../../os/os/services/relay-worker@.service");
            let svc = parse_section_multi(unit, "Service");
            let env = svc.get("Environment").cloned().unwrap_or_default();
            assert!(env.contains(&"MUSE_RELAY_NICK=%i".to_string()));
        }

        #[test]
        fn test_env_files_required_and_optional() {
            let unit = include_str!("../../../os/os/services/relay-worker@.service");
            let svc = parse_section_multi(unit, "Service");
            let files = svc.get("EnvironmentFile").cloned().unwrap_or_default();
            assert!(files.contains(&"/etc/metaos/secrets.env".to_string()));
            assert!(files.contains(&"-/etc/metaos/worker-%i.env".to_string()));
        }

        #[test]
        fn test_exec_runs_mos_worker_without_dm_secret() {
            let unit = include_str!("../../../os/os/services/relay-worker@.service");
            let svc = parse_section_multi(unit, "Service");
            let starts = svc.get("ExecStart").cloned().unwrap_or_default();
            assert_eq!(starts.len(), 1);
            assert!(starts[0].contains("/opt/relay/mos.py worker"));
            assert!(!starts[0].contains("--dm"));
        }

        #[test]
        fn test_build_scripts_carry_template_but_never_auto_enable() {
            for build in [
                include_str!("../../../os/os/build-image.sh"),
                include_str!("../../../os/os/build-live.sh"),
            ] {
                assert!(build.contains("services/*.service"));
                assert!(!build.contains("relay-worker@"));
            }
        }

        #[test]
        fn test_readme_section_names_both_owed_items() {
            let readme = include_str!("../../../os/os/README.md");
            assert!(readme.contains("OS-017"));
            assert!(readme.contains("relay-worker@.service"));
            assert!(readme.contains("handler"));
            assert!(readme.contains("DM secret"));
        }

        #[test]
        fn test_spec_records_template_as_landed() {
            let spec = include_str!("../../../os/plan/META_OS.md");
            assert!(spec.contains("relay-worker@.service"));
            assert!(spec.contains("OS-017"));
            assert!(spec.contains("worker fleet template"));
        }

        #[test]
        fn test_no_em_dash_in_worker_unit() {
            let unit = include_str!("../../../os/os/services/relay-worker@.service");
            assert!(!unit.contains('\u{2014}'));
        }

        #[test]
        fn test_workers_slice_values() {
            let slice = include_str!("../../../os/os/services/relay-workers.slice");
            let values = parse_section(slice, "Slice");
            for (key, want) in slice_expected() {
                assert_eq!(values.get(key).map(|s| s.as_str()), Some(want), "{key}");
            }
        }

        #[test]
        fn test_workers_spec_records_values() {
            let spec = include_str!("../../../os/plan/META_OS.md");
            assert!(spec.contains("relay-workers.slice"));
            for (key, want) in slice_expected() {
                assert!(spec.contains(&format!("{key}={want}")));
            }
        }

        #[test]
        fn test_workers_drill_exists_with_host_gate() {
            let drill = include_str!("../../../os/intel/drills/cgroup_limits.py");
            assert!(drill.contains("ENVIRONMENT-BLOCKED"));
            assert!(drill.contains("cgroup.controllers"));
            assert!(drill.contains("CPUQuota"));
            assert!(drill.contains("MemoryMax"));
        }

        #[test]
        fn test_workers_eval_note_exists() {
            let eval = include_str!("../../../os/intel/evals/cgroup_limits.md");
            assert!(!eval.is_empty());
        }

        #[test]
        fn test_no_em_dash_in_workers_slice_files() {
            for text in [
                include_str!("../../../os/os/services/relay-workers.slice"),
                include_str!("../../../os/intel/drills/cgroup_limits.py"),
                include_str!("../../../os/intel/evals/cgroup_limits.md"),
            ] {
                assert!(!text.contains('\u{2014}'));
            }
        }
    }

    // ---------- test_intel_drill_kill_worker.py ----------

    mod drill_kill_worker {
        use super::*;

        #[test]
        fn test_drill_passes_and_reports_the_stall_alert() {
            let report = run_kill_worker_drill().unwrap();
            assert_eq!(report.alert.kind, "presence-stall");
            assert_eq!(report.alert.nick, "pax");
            assert_eq!(report.alert.job, "7");
            assert_eq!(report.requeued, vec!["7".to_string()]);
            assert_eq!(report.log.len(), 4);
        }

        #[test]
        fn test_sweep_leaves_unexpired_and_open_jobs_alone() {
            let mut jobs = vec![
                SweepJob {
                    id: "1".to_string(),
                    status: "claimed".to_string(),
                    claim: Some("pax".to_string()),
                    lease_until: Some(2000),
                    ..Default::default()
                },
                SweepJob {
                    id: "2".to_string(),
                    status: "open".to_string(),
                    ..Default::default()
                },
                SweepJob {
                    id: "3".to_string(),
                    status: "claimed".to_string(),
                    ..Default::default()
                },
            ];
            assert!(sweep_expired_leases(&mut jobs, 1500).is_empty());
            assert_eq!(jobs[0].status, "claimed");
            assert_eq!(sweep_expired_leases(&mut jobs, 2000), vec!["1".to_string()]);
            assert_eq!(jobs[0].status, "open");
            assert_eq!(jobs[0].claim, None);
            assert_eq!(jobs[0].lease_until, None);
            assert_eq!(jobs[1].status, "open");
            assert_eq!(jobs[2].status, "claimed");
        }

        #[test]
        fn test_cli_main_exits_zero_and_prints_pass() {
            // The Python CLI prints "kill_worker drill: PASS" on
            // exit 0. The Rust equivalent is a successful drill
            // run; the CLI print layer is outside this crate.
            assert!(run_kill_worker_drill().is_ok());
        }
    }

    // ---------- test_intel_dispatch_worker.py (decision level) +
    // mos/worker.py unit behavior ----------

    mod worker_loop {
        use super::*;

        struct FakeBackend {
            dms: Vec<Announcement>,
            specs: HashMap<String, String>,
            claimed: Vec<String>,
            done: Vec<String>,
            blocked: Vec<(String, String)>,
            claim_ok: HashMap<String, bool>,
            finish_ok: bool,
        }

        impl FakeBackend {
            fn new() -> FakeBackend {
                FakeBackend {
                    dms: Vec::new(),
                    specs: HashMap::new(),
                    claimed: Vec::new(),
                    done: Vec::new(),
                    blocked: Vec::new(),
                    claim_ok: HashMap::new(),
                    finish_ok: true,
                }
            }
        }

        impl WorkerBackend for FakeBackend {
            fn register(&mut self, _w: &Worker) {}
            fn heartbeat(&mut self, _w: &Worker) -> Vec<String> {
                self.claimed.clone()
            }
            fn poll_dms(&mut self, _w: &Worker) -> Vec<Announcement> {
                self.dms.clone()
            }
            fn claim(&mut self, _w: &Worker, jid: &str) -> (bool, String) {
                let ok = self.claim_ok.get(jid).copied().unwrap_or(true);
                if ok {
                    self.claimed.push(jid.to_string());
                    (true, format!("CLAIMED {jid}"))
                } else {
                    (false, "claim refused".to_string())
                }
            }
            fn finish(&mut self, _w: &Worker, jid: &str, _c: &str, _n: &str) -> bool {
                if self.finish_ok {
                    self.done.push(jid.to_string());
                    true
                } else {
                    false
                }
            }
            fn block(&mut self, _w: &Worker, jid: &str, reason: &str) -> bool {
                self.blocked.push((jid.to_string(), reason.to_string()));
                true
            }
            fn job_spec(&mut self, _w: &Worker, jid: &str) -> String {
                self.specs.get(jid).cloned().unwrap_or_default()
            }
        }

        fn worker() -> Worker {
            Worker::new("w1", "s3cret", &["python"], "", "/tmp", 1800, 1)
        }

        fn ann(jid: &str, title: &str, reqs: &[&str]) -> Announcement {
            Announcement {
                jid: jid.to_string(),
                title: title.to_string(),
                reqs: reqs.iter().map(|s| s.to_string()).collect(),
            }
        }

        #[test]
        fn test_dispatched_chain_flows_through_worker_loop() {
            let dir = TestDir::new("dispatch");
            let mut backend = FakeBackend::new();
            backend.dms = vec![ann("1", "Do implement", &["python"])];
            let w = Worker::new("w1", "s3cret", &["python"], "", &dir.path.to_string_lossy(), 1800, 1);
            let report = w.run_once(&mut backend, |_jid, title, _spec, workdir| {
                let name = if title.contains("implement") {
                    "work.txt"
                } else {
                    "review.txt"
                };
                std::fs::write(Path::new(workdir).join(name), "work product").unwrap();
                Ok(("deadbee".to_string(), format!("wrote {name}")))
            });
            assert_eq!(report.claimed, vec!["1".to_string()]);
            assert_eq!(report.done, vec!["1".to_string()]);
            assert!(report.blocked.is_empty());
            assert!(report.errors.is_empty());
            assert_eq!(
                std::fs::read_to_string(dir.path.join("work.txt")).unwrap(),
                "work product"
            );
        }

        #[test]
        fn test_worker_heartbeat_renews_dispatched_claim() {
            let mut backend = FakeBackend::new();
            let w = worker();
            let (ok, _) = backend.claim(&w, "1");
            assert!(ok);
            assert_eq!(backend.heartbeat(&w), vec!["1".to_string()]);
        }

        #[test]
        fn test_undelivered_dispatched_job_stays_open() {
            let mut backend = FakeBackend::new();
            let w = worker();
            let report = w.run_once(&mut backend, |_, _, _, _| {
                Ok(("deadbee".to_string(), "done".to_string()))
            });
            assert!(report.claimed.is_empty());
            assert!(report.done.is_empty());
        }

        #[test]
        fn test_skipped_blocked_crash_and_error_paths() {
            // Skipped: unmet requirement.
            let mut backend = FakeBackend::new();
            backend.dms = vec![ann("9", "Needs rust", &["rust"])];
            let report = worker().run_once(&mut backend, |_, _, _, _| {
                Ok(("c".to_string(), "n".to_string()))
            });
            assert_eq!(report.skipped, vec!["9".to_string()]);
            assert!(report.claimed.is_empty());

            // Blocked: handler raises WorkerBlocked.
            let mut backend = FakeBackend::new();
            backend.dms = vec![ann("2", "Do work", &[])];
            let report = worker().run_once(&mut backend, |_, _, _, _| {
                Err(HandlerError::Blocked("no good".to_string()))
            });
            assert_eq!(report.blocked, vec!["2".to_string()]);
            assert_eq!(backend.blocked[0].1, "no good");

            // Empty block reason becomes "blocked".
            let mut backend = FakeBackend::new();
            backend.dms = vec![ann("3", "Do work", &[])];
            let report = worker().run_once(&mut backend, |_, _, _, _| {
                Err(HandlerError::Blocked(String::new()))
            });
            assert_eq!(report.blocked, vec!["3".to_string()]);
            assert_eq!(backend.blocked[0].1, "blocked");

            // Crash: blocked with the "handler crashed:" prefix.
            let mut backend = FakeBackend::new();
            backend.dms = vec![ann("4", "Do work", &[])];
            let report = worker().run_once(&mut backend, |_, _, _, _| {
                Err(HandlerError::Crashed("boom".to_string()))
            });
            assert_eq!(report.blocked, vec!["4".to_string()]);
            assert!(backend.blocked[0].1.starts_with("handler crashed: "));

            // Claim failure: stripped detail in errors.
            let mut backend = FakeBackend::new();
            backend.dms = vec![ann("5", "Do work", &[])];
            backend.claim_ok.insert("5".to_string(), false);
            let report = worker().run_once(&mut backend, |_, _, _, _| {
                Ok(("c".to_string(), "n".to_string()))
            });
            assert_eq!(report.errors, vec!["claim 5: claim refused".to_string()]);

            // Finish failure: done error line.
            let mut backend = FakeBackend::new();
            backend.dms = vec![ann("6", "Do work", &[])];
            backend.finish_ok = false;
            let report = worker().run_once(&mut backend, |_, _, _, _| {
                Ok(("c".to_string(), "n".to_string()))
            });
            assert_eq!(report.errors, vec!["done 6: finish failed".to_string()]);

            // No DM secret: the loop polls nothing, whatever the
            // backend would return.
            let mut backend = FakeBackend::new();
            backend.dms = vec![ann("7", "Do work", &[])];
            let no_dm = Worker::new("w1", "", &["python"], "", "/tmp", 1800, 1);
            let report = no_dm.run_once(&mut backend, |_, _, _, _| {
                Ok(("c".to_string(), "n".to_string()))
            });
            assert!(report.claimed.is_empty());
        }

        #[test]
        fn test_truncation_rules_500_200_400() {
            // Block reason truncated to 500 chars.
            let mut backend = FakeBackend::new();
            backend.dms = vec![ann("1", "Do work", &[])];
            let long = "x".repeat(600);
            let long_clone = long.clone();
            let _ = worker().run_once(&mut backend, move |_, _, _, _| {
                Err(HandlerError::Blocked(long_clone.clone()))
            });
            assert_eq!(backend.blocked[0].1.chars().count(), 500);

            // Claim detail tail: last 200 chars of the stripped detail.
            struct TailBackend;
            impl WorkerBackend for TailBackend {
                fn register(&mut self, _w: &Worker) {}
                fn heartbeat(&mut self, _w: &Worker) -> Vec<String> { vec![] }
                fn poll_dms(&mut self, _w: &Worker) -> Vec<Announcement> {
                    vec![ann("1", "Do work", &[])]
                }
                fn claim(&mut self, _w: &Worker, _jid: &str) -> (bool, String) {
                    (false, format!("  {}  ", "y".repeat(300)))
                }
                fn finish(&mut self, _w: &Worker, _j: &str, _c: &str, _n: &str) -> bool {
                    true
                }
                fn block(&mut self, _w: &Worker, _j: &str, _r: &str) -> bool { true }
                fn job_spec(&mut self, _w: &Worker, _j: &str) -> String { String::new() }
            }
            let mut backend = TailBackend;
            let report = worker().run_once(&mut backend, |_, _, _, _| {
                Ok(("c".to_string(), "n".to_string()))
            });
            assert_eq!(report.errors[0], format!("claim 1: {}", "y".repeat(200)));

            // Crash message tail: last 400 chars after the prefix.
            let mut backend = FakeBackend::new();
            backend.dms = vec![ann("1", "Do work", &[])];
            let crash = "z".repeat(500);
            let crash_clone = crash.clone();
            let _ = worker().run_once(&mut backend, move |_, _, _, _| {
                Err(HandlerError::Crashed(crash_clone.clone()))
            });
            assert_eq!(
                backend.blocked[0].1,
                format!("handler crashed: {}", "z".repeat(400))
            );
        }

        #[test]
        fn test_parse_announcement_cases() {
            assert_eq!(
                parse_announcement("JOB:12 Do the thing"),
                Some((
                    "12".to_string(),
                    "Do the thing".to_string(),
                    BTreeSet::new()
                ))
            );
            assert_eq!(
                parse_announcement("JOB:7 Write it req=python,testing"),
                Some((
                    "7".to_string(),
                    "Write it".to_string(),
                    ["python".to_string(), "testing".to_string()]
                        .into_iter()
                        .collect()
                ))
            );
            // Unanchored search: text before JOB: is ignored.
            assert!(parse_announcement("w1: JOB:3 Title here").is_some());
            // No match: missing id, non-digit id, id not followed
            // by whitespace, or no JOB: at all.
            assert_eq!(parse_announcement("hello"), None);
            assert_eq!(parse_announcement("JOB: title"), None);
            assert_eq!(parse_announcement("JOB:12x title"), None);
            // req= not at the end is not a clause.
            assert_eq!(
                parse_announcement("JOB:1 title req=python extra"),
                Some((
                    "1".to_string(),
                    "title req=python extra".to_string(),
                    BTreeSet::new()
                ))
            );
            // req= after a word character is not a boundary.
            assert_eq!(
                parse_announcement("JOB:1 axreq=python"),
                Some((
                    "1".to_string(),
                    "axreq=python".to_string(),
                    BTreeSet::new()
                ))
            );
            // Empty req items are dropped.
            let (_, _, reqs) = parse_announcement("JOB:1 t req=a,,b").unwrap();
            assert_eq!(
                reqs,
                ["a".to_string(), "b".to_string()].into_iter().collect()
            );
        }

        #[test]
        fn test_caps_normalization_and_matching() {
            let w = Worker::new("w1", "s", &[" Python ", "", "TESTING"], "", "/tmp", 1800, 1);
            assert_eq!(
                w.caps,
                ["python".to_string(), "testing".to_string()]
                    .into_iter()
                    .collect()
            );
            assert!(w.matches(&["python".to_string()].into_iter().collect()));
            assert!(!w.matches(&["rust".to_string()].into_iter().collect()));
            assert!(w.matches(&BTreeSet::new()));
        }
    }

    // ---------- relay uplink (os/os/uplink/relay_uplink.py) ----------

    mod uplink {
        use super::*;

        fn order(id: &str, text: &str, origin: &str) -> Order {
            Order {
                id: id.to_string(),
                text: text.to_string(),
                origin: origin.to_string(),
                received_at: None,
            }
        }

        #[test]
        fn test_backoff_sequence() {
            assert_eq!(
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 100]
                    .map(backoff_seconds),
                [0, 5, 10, 20, 40, 80, 160, 300, 300, 300, 300]
            );
        }

        #[test]
        fn test_validate_order_reasons() {
            assert_eq!(validate_order(&order("o", "t", "phone")), (true, String::new()));
            assert_eq!(
                validate_order(&order("", "t", "phone")),
                (false, "order id missing".to_string())
            );
            assert_eq!(
                validate_order(&order("o", "   ", "phone")),
                (false, "order text empty".to_string())
            );
            assert_eq!(
                validate_order(&order("o", "t", "")),
                (false, "order origin missing".to_string())
            );
        }

        #[test]
        fn test_record_failure_and_success() {
            let s = record_failure(&empty_state(), 1000);
            assert_eq!(s.failures, 1);
            assert_eq!(s.next_retry_at, Some(1005));
            let s = record_failure(&s, 1005);
            assert_eq!(s.failures, 2);
            assert_eq!(s.next_retry_at, Some(1015));
            let s = record_success(&s);
            assert_eq!(s.failures, 0);
            assert_eq!(s.next_retry_at, None);
        }

        #[test]
        fn test_tick_connected_intake_signed_and_unsigned() {
            let (events, state) =
                uplink_tick(&empty_state(), &[order("o1", "Do it", "phone")], 0, true, Some("k"), false);
            assert_eq!(events.len(), 1);
            assert_eq!(events[0].event_type, "intake");
            let record = events[0].record.clone().unwrap();
            assert_eq!(record.kind, "ORDER");
            assert!(record.signed);
            assert_eq!(record.signature.as_deref(), Some(&sign_intake("k", "o1", "Do it")[..]));
            assert_eq!(state.seen_ids, vec!["o1".to_string()]);

            let (events, _) =
                uplink_tick(&empty_state(), &[order("o2", "Do it", "phone")], 0, true, None, false);
            assert_eq!(events[0].event_type, "intake");
            let record = events[0].record.clone().unwrap();
            assert!(!record.signed);
            assert_eq!(record.signature, None);
        }

        #[test]
        fn test_tick_crew_mode_unsigned_refused_stays_pending() {
            let (events, state) =
                uplink_tick(&empty_state(), &[order("o1", "Do it", "phone")], 0, true, None, true);
            assert_eq!(events[0].event_type, "unsigned-refused");
            assert_eq!(events[0].reason.as_deref(), Some("crew mode requires a signing key"));
            assert_eq!(state.pending.len(), 1);
            assert!(state.seen_ids.is_empty());
        }

        #[test]
        fn test_tick_disconnected_queues_and_duplicates() {
            let (events, state) =
                uplink_tick(&empty_state(), &[order("o1", "Do it", "phone")], 1000, false, None, false);
            assert_eq!(events[0].event_type, "queued");
            assert_eq!(state.failures, 1);
            assert_eq!(state.next_retry_at, Some(1005));
            assert_eq!(state.pending.len(), 1);
            // Seeing it again while offline is a duplicate, not a queue.
            let (events, state) =
                uplink_tick(&state, &[order("o1", "Do it", "phone")], 1005, false, None, false);
            assert_eq!(events[0].event_type, "duplicate");
            assert_eq!(state.pending.len(), 1);
            // Reconnecting drains pending first, in order.
            let (events, state) =
                uplink_tick(&state, &[order("o2", "Second", "phone")], 1010, true, Some("k"), false);
            assert_eq!(events[0].event_type, "intake");
            assert_eq!(events[0].order_id.as_deref(), Some("o1"));
            assert_eq!(events[1].order_id.as_deref(), Some("o2"));
            assert!(state.pending.is_empty());
        }

        #[test]
        fn test_tick_rejects_invalid_in_either_mode() {
            for connected in [true, false] {
                let bad = order("o1", "   ", "phone");
                let (events, state) =
                    uplink_tick(&empty_state(), &[bad], 0, connected, Some("k"), false);
                assert_eq!(events[0].event_type, "rejected");
                assert_eq!(events[0].reason.as_deref(), Some("order text empty"));
                assert!(state.pending.is_empty());
                assert!(state.seen_ids.is_empty());
            }
        }

        #[test]
        fn test_tick_duplicate_seen_and_input_untouched() {
            let mut state = empty_state();
            state.seen_ids = vec!["o1".to_string()];
            let before = state.clone();
            let (events, after) =
                uplink_tick(&state, &[order("o1", "Do it", "phone")], 0, true, Some("k"), false);
            assert_eq!(events[0].event_type, "duplicate");
            assert_eq!(state, before, "tick must not mutate its input");
            assert_eq!(after, before);
        }

        #[test]
        fn test_tick_drain_invalid_dropped_not_requeued() {
            let mut state = empty_state();
            state.pending = vec![order("bad", "   ", "phone")];
            let (events, after) =
                uplink_tick(&state, &[], 0, true, Some("k"), false);
            assert_eq!(events[0].event_type, "rejected");
            assert!(after.pending.is_empty());
        }
    }

    // ---------- thresholds env fallback ----------

    #[test]
    fn test_thresholds_from_env_fallback_rules() {
        // Only this test touches these variables, and no other
        // test reads from_env, so parallel-test races on the
        // shared environment cannot affect other tests.
        std::env::set_var("WATCHDOG_STALL_MINUTES", "abc");
        assert_eq!(StallThresholds::from_env().stall_minutes, 10);
        std::env::set_var("WATCHDOG_STALL_MINUTES", "");
        assert_eq!(StallThresholds::from_env().stall_minutes, 10);
        std::env::set_var("WATCHDOG_STALL_MINUTES", "-5");
        assert_eq!(StallThresholds::from_env().stall_minutes, 10);
        std::env::set_var("WATCHDOG_STALL_MINUTES", "7");
        assert_eq!(StallThresholds::from_env().stall_minutes, 7);
        std::env::set_var("WATCHDOG_PROGRESS_STALL_MINUTES", "1");
        assert_eq!(StallThresholds::from_env().progress_stall_minutes, 1);
        std::env::remove_var("WATCHDOG_STALL_MINUTES");
        std::env::remove_var("WATCHDOG_PROGRESS_STALL_MINUTES");
        assert_eq!(StallThresholds::from_env(), StallThresholds::defaults());
    }
}
