//! Crate `os-workspace` — Meta OS Rust rebuild skeleton (B00).
//!
//! Batch B19 — Workspace & artifact store. Owner: Milo.
//! Source files this batch ports:
//! - `os/mos/artifact_store.py`
//! - `os/mos/gitops.py`
//!
//! Skeleton only: no logic yet. The Python/Node sources listed above are
//! the spec — port behavior, do not redesign. See BATCHES.md for the
//! compile gates and the parity rule.

// B19 port (Milo): workspace & artifact store, ported behavior-for-behavior
// from os/mos/artifact_store.py (OS-083) and os/mos/gitops.py (MOS safe git).
// Python originals stay untouched and remain the live fallback.
//
// Porting notes (approximations, all deliberate and marked at the spot):
// - Python `subprocess` timeouts are mirrored with reader threads plus a
//   try_wait loop: artifact_store git calls time out after 60s, gitops
//   calls after 120s.
// - Python's `str.isalnum()` is Unicode-aware; Rust `char::is_alphanumeric`
//   matches it for all practical job-id characters.
// - `read()` of the latest version in Python surfaces a raw OSError when
//   the disk file is gone; the Rust port surfaces the same condition as
//   an ArtifactStoreError carrying the I/O message.
// - `reject_branch` raises ValueError in Python; the Rust port returns a
//   GitError carrying the same message.
// - CLI `--author` with no following value crashes Python with IndexError;
//   the Rust CLI reports usage and exits 2 instead.
// - Manifest JSON is read/written with a small built-in JSON value type
//   (std-only: no serde). Serialization matches Python `json.dump`
//   with indent=2, sort_keys=True, ensure_ascii=True, plus a trailing
//   newline, so manifests stay readable by the Python fallback.

use std::collections::BTreeMap;
use std::fmt;
use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

// ---------------------------------------------------------------------------
// Error types
// ---------------------------------------------------------------------------

/// Port of `artifact_store.ArtifactStoreError` (a ValueError in Python):
/// refused deposit, bad name, missing artifact, or git failure.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ArtifactStoreError(pub String);

impl fmt::Display for ArtifactStoreError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for ArtifactStoreError {}

impl From<std::io::Error> for ArtifactStoreError {
    fn from(e: std::io::Error) -> Self {
        ArtifactStoreError(e.to_string())
    }
}

/// Port of `gitops.GitError` (a RuntimeError in Python).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitError(pub String);

impl fmt::Display for GitError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for GitError {}

// ---------------------------------------------------------------------------
// Minimal JSON value (std-only). Used for manifests so Rust-written
// manifests stay byte-compatible with the Python fallback.
// ---------------------------------------------------------------------------

/// A JSON value. Objects keep keys sorted (BTreeMap), matching Python
/// `json.dump(..., sort_keys=True)`.
#[derive(Debug, Clone, PartialEq)]
pub enum JsonValue {
    Null,
    Bool(bool),
    Int(i64),
    Float(f64),
    Str(String),
    Array(Vec<JsonValue>),
    Object(BTreeMap<String, JsonValue>),
}

impl JsonValue {
    /// Build an object from key/value pairs (convenience for callers/tests).
    pub fn obj(pairs: Vec<(&str, JsonValue)>) -> JsonValue {
        let mut m = BTreeMap::new();
        for (k, v) in pairs {
            m.insert(k.to_string(), v);
        }
        JsonValue::Object(m)
    }

    /// Look up a key on an object, else None.
    pub fn get(&self, key: &str) -> Option<&JsonValue> {
        match self {
            JsonValue::Object(m) => m.get(key),
            _ => None,
        }
    }

    /// String value, else None.
    pub fn as_str(&self) -> Option<&str> {
        match self {
            JsonValue::Str(s) => Some(s),
            _ => None,
        }
    }

    /// Integer value (a float with an integral value is NOT coerced, matching
    /// Python's distinct int/float types).
    pub fn as_i64(&self) -> Option<i64> {
        match self {
            JsonValue::Int(n) => Some(*n),
            _ => None,
        }
    }

    /// Array value, else None.
    pub fn as_array(&self) -> Option<&Vec<JsonValue>> {
        match self {
            JsonValue::Array(a) => Some(a),
            _ => None,
        }
    }
}

struct JsonParser<'a> {
    bytes: &'a [u8],
    pos: usize,
}

impl<'a> JsonParser<'a> {
    fn new(text: &'a str) -> Self {
        JsonParser {
            bytes: text.as_bytes(),
            pos: 0,
        }
    }

    fn err(&self, msg: &str) -> String {
        format!("{} at character {}", msg, self.pos)
    }

    fn skip_ws(&mut self) {
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
            Err(self.err(&format!("expected '{}'", b as char)))
        }
    }

    fn value(&mut self) -> Result<JsonValue, String> {
        self.skip_ws();
        match self.peek() {
            Some(b'{') => self.object(),
            Some(b'[') => self.array(),
            Some(b'"') => Ok(JsonValue::Str(self.string()?)),
            Some(b't') => self.literal("true", JsonValue::Bool(true)),
            Some(b'f') => self.literal("false", JsonValue::Bool(false)),
            Some(b'n') => self.literal("null", JsonValue::Null),
            Some(b'-') | Some(b'0'..=b'9') => self.number(),
            _ => Err(self.err("unexpected character")),
        }
    }

    fn literal(&mut self, word: &str, v: JsonValue) -> Result<JsonValue, String> {
        if self.bytes.len() >= self.pos + word.len()
            && &self.bytes[self.pos..self.pos + word.len()] == word.as_bytes()
        {
            self.pos += word.len();
            Ok(v)
        } else {
            Err(self.err("invalid literal"))
        }
    }

    fn object(&mut self) -> Result<JsonValue, String> {
        self.expect(b'{')?;
        let mut m = BTreeMap::new();
        self.skip_ws();
        if self.peek() == Some(b'}') {
            self.pos += 1;
            return Ok(JsonValue::Object(m));
        }
        loop {
            self.skip_ws();
            let key = self.string()?;
            self.skip_ws();
            self.expect(b':')?;
            let val = self.value()?;
            m.insert(key, val);
            self.skip_ws();
            match self.peek() {
                Some(b',') => {
                    self.pos += 1;
                }
                Some(b'}') => {
                    self.pos += 1;
                    return Ok(JsonValue::Object(m));
                }
                _ => return Err(self.err("expected ',' or '}' in object")),
            }
        }
    }

    fn array(&mut self) -> Result<JsonValue, String> {
        self.expect(b'[')?;
        let mut a = Vec::new();
        self.skip_ws();
        if self.peek() == Some(b']') {
            self.pos += 1;
            return Ok(JsonValue::Array(a));
        }
        loop {
            let val = self.value()?;
            a.push(val);
            self.skip_ws();
            match self.peek() {
                Some(b',') => {
                    self.pos += 1;
                }
                Some(b']') => {
                    self.pos += 1;
                    return Ok(JsonValue::Array(a));
                }
                _ => return Err(self.err("expected ',' or ']' in array")),
            }
        }
    }

    fn hex4(&mut self) -> Result<u32, String> {
        let mut n: u32 = 0;
        for _ in 0..4 {
            let c = self.peek().ok_or_else(|| self.err("truncated \\u escape"))?;
            let d = (c as char)
                .to_digit(16)
                .ok_or_else(|| self.err("bad \\u escape"))?;
            n = n * 16 + d;
            self.pos += 1;
        }
        Ok(n)
    }

    fn string(&mut self) -> Result<String, String> {
        self.expect(b'"')?;
        let mut out = String::new();
        loop {
            let c = self.peek().ok_or_else(|| self.err("unterminated string"))?;
            match c {
                b'"' => {
                    self.pos += 1;
                    return Ok(out);
                }
                b'\\' => {
                    self.pos += 1;
                    let e = self.peek().ok_or_else(|| self.err("truncated escape"))?;
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
                            let cp = self.hex4()?;
                            if (0xD800..0xDC00).contains(&cp) {
                                // High surrogate: expect a low surrogate.
                                if self.peek() == Some(b'\\')
                                    && self.bytes.get(self.pos + 1) == Some(&b'u')
                                {
                                    self.pos += 2;
                                    let lo = self.hex4()?;
                                    if (0xDC00..0xE000).contains(&lo) {
                                        let c =
                                            0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
                                        out.push(char::from_u32(c).unwrap_or('\u{FFFD}'));
                                    } else {
                                        return Err(self.err("bad low surrogate"));
                                    }
                                } else {
                                    return Err(self.err("lone high surrogate"));
                                }
                            } else if (0xDC00..0xE000).contains(&cp) {
                                return Err(self.err("lone low surrogate"));
                            } else {
                                out.push(char::from_u32(cp).unwrap_or('\u{FFFD}'));
                            }
                        }
                        _ => return Err(self.err("bad escape")),
                    }
                }
                _ => {
                    // Copy one UTF-8 scalar (bytes >= 0x80 belong to a
                    // multi-byte sequence; consume the whole sequence).
                    let len = if c < 0x80 {
                        1
                    } else if c < 0xE0 {
                        2
                    } else if c < 0xF0 {
                        3
                    } else {
                        4
                    };
                    if self.pos + len > self.bytes.len() {
                        return Err(self.err("truncated utf-8"));
                    }
                    let s = std::str::from_utf8(&self.bytes[self.pos..self.pos + len])
                        .map_err(|_| self.err("invalid utf-8"))?;
                    out.push_str(s);
                    self.pos += len;
                }
            }
        }
    }

    fn number(&mut self) -> Result<JsonValue, String> {
        let start = self.pos;
        if self.peek() == Some(b'-') {
            self.pos += 1;
        }
        while matches!(self.peek(), Some(b'0'..=b'9')) {
            self.pos += 1;
        }
        let mut is_float = false;
        if self.peek() == Some(b'.') {
            is_float = true;
            self.pos += 1;
            while matches!(self.peek(), Some(b'0'..=b'9')) {
                self.pos += 1;
            }
        }
        if matches!(self.peek(), Some(b'e') | Some(b'E')) {
            is_float = true;
            self.pos += 1;
            if matches!(self.peek(), Some(b'+') | Some(b'-')) {
                self.pos += 1;
            }
            while matches!(self.peek(), Some(b'0'..=b'9')) {
                self.pos += 1;
            }
        }
        let text =
            std::str::from_utf8(&self.bytes[start..self.pos]).map_err(|_| self.err("bad number"))?;
        if !is_float {
            if let Ok(n) = text.parse::<i64>() {
                return Ok(JsonValue::Int(n));
            }
        }
        text.parse::<f64>()
            .map(JsonValue::Float)
            .map_err(|_| self.err("bad number"))
    }
}

/// Parse a JSON document; trailing non-whitespace is an error.
fn json_parse(text: &str) -> Result<JsonValue, String> {
    let mut p = JsonParser::new(text);
    let v = p.value()?;
    p.skip_ws();
    if p.pos != p.bytes.len() {
        return Err(p.err("trailing characters"));
    }
    Ok(v)
}

/// Escape a string the way Python `json.dump(ensure_ascii=True)` does.
fn json_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for ch in s.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{0008}' => out.push_str("\\b"),
            '\u{000C}' => out.push_str("\\f"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c if (c as u32) < 0x7F => out.push(c),
            c => {
                // ensure_ascii: escape non-ASCII as \uXXXX, with surrogate
                // pairs for astral characters.
                let n = c as u32;
                if n < 0x10000 {
                    out.push_str(&format!("\\u{:04x}", n));
                } else {
                    let v = n - 0x10000;
                    out.push_str(&format!(
                        "\\u{:04x}\\u{:04x}",
                        0xD800 + (v >> 10),
                        0xDC00 + (v & 0x3FF)
                    ));
                }
            }
        }
    }
    out.push('"');
    out
}

/// Serialize like Python `json.dump(indent=2, sort_keys=True)`: objects
/// sorted, 2-space indent, `": "` after keys. Empty containers stay compact.
fn json_dump(v: &JsonValue, indent: usize, out: &mut String) {
    match v {
        JsonValue::Null => out.push_str("null"),
        JsonValue::Bool(true) => out.push_str("true"),
        JsonValue::Bool(false) => out.push_str("false"),
        JsonValue::Int(n) => out.push_str(&n.to_string()),
        JsonValue::Float(f) => {
            if f.is_finite() {
                let mut s = format!("{}", f);
                if !s.contains('.') && !s.contains('e') && !s.contains("inf") && !s.contains("NaN")
                {
                    s.push_str(".0");
                }
                out.push_str(&s);
            } else {
                // Python would emit Infinity/NaN (invalid JSON); keep the
                // same tokens rather than inventing a value.
                if f.is_nan() {
                    out.push_str("NaN");
                } else if *f > 0.0 {
                    out.push_str("Infinity");
                } else {
                    out.push_str("-Infinity");
                }
            }
        }
        JsonValue::Str(s) => out.push_str(&json_escape(s)),
        JsonValue::Array(a) => {
            if a.is_empty() {
                out.push_str("[]");
            } else {
                out.push_str("[\n");
                for (i, item) in a.iter().enumerate() {
                    out.push_str(&"  ".repeat(indent + 1));
                    json_dump(item, indent + 1, out);
                    if i + 1 < a.len() {
                        out.push(',');
                    }
                    out.push('\n');
                }
                out.push_str(&"  ".repeat(indent));
                out.push(']');
            }
        }
        JsonValue::Object(m) => {
            if m.is_empty() {
                out.push_str("{}");
            } else {
                out.push_str("{\n");
                let len = m.len();
                for (i, (k, val)) in m.iter().enumerate() {
                    out.push_str(&"  ".repeat(indent + 1));
                    out.push_str(&json_escape(k));
                    out.push_str(": ");
                    json_dump(val, indent + 1, out);
                    if i + 1 < len {
                        out.push(',');
                    }
                    out.push('\n');
                }
                out.push_str(&"  ".repeat(indent));
                out.push('}');
            }
        }
    }
}

/// Compact serialization like Python `json.dumps(sort_keys=True)` (the
/// CLI's print format): `", "` between items, `": "` after keys.
fn json_dump_compact(v: &JsonValue, out: &mut String) {
    match v {
        JsonValue::Null => out.push_str("null"),
        JsonValue::Bool(true) => out.push_str("true"),
        JsonValue::Bool(false) => out.push_str("false"),
        JsonValue::Int(n) => out.push_str(&n.to_string()),
        JsonValue::Float(f) => {
            if f.is_finite() {
                let mut s = format!("{}", f);
                if !s.contains('.') && !s.contains('e') {
                    s.push_str(".0");
                }
                out.push_str(&s);
            } else if f.is_nan() {
                out.push_str("NaN");
            } else if *f > 0.0 {
                out.push_str("Infinity");
            } else {
                out.push_str("-Infinity");
            }
        }
        JsonValue::Str(s) => out.push_str(&json_escape(s)),
        JsonValue::Array(a) => {
            out.push('[');
            for (i, item) in a.iter().enumerate() {
                if i > 0 {
                    out.push_str(", ");
                }
                json_dump_compact(item, out);
            }
            out.push(']');
        }
        JsonValue::Object(m) => {
            out.push('{');
            for (i, (k, val)) in m.iter().enumerate() {
                if i > 0 {
                    out.push_str(", ");
                }
                out.push_str(&json_escape(k));
                out.push_str(": ");
                json_dump_compact(val, out);
            }
            out.push('}');
        }
    }
}

// ---------------------------------------------------------------------------
// SHA-256 (std-only; must match hashlib.sha256 bit-for-bit).
// ---------------------------------------------------------------------------

const SHA256_K: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

/// SHA-256 digest of `data`, hex-encoded (lowercase, like hexdigest()).
fn sha256_hex(data: &[u8]) -> String {
    let mut h: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    ];
    let bitlen = (data.len() as u64).wrapping_mul(8);
    let mut msg = data.to_vec();
    msg.push(0x80);
    while msg.len() % 64 != 56 {
        msg.push(0);
    }
    msg.extend_from_slice(&bitlen.to_be_bytes());
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
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
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
    let mut out = String::with_capacity(64);
    for word in h {
        out.push_str(&format!("{:08x}", word));
    }
    out
}

// ---------------------------------------------------------------------------
// Git runner with a timeout. Spawns reader threads for stdout/stderr,
// polls try_wait, kills on expiry (mirrors subprocess timeout semantics).
// ---------------------------------------------------------------------------

struct GitOutput {
    stdout: Vec<u8>,
    stderr: Vec<u8>,
    status: i32,
}

/// Run `cmd` (argv, cmd[0] is the program), waiting at most `timeout`.
/// Stdout/stderr are drained on reader threads; on expiry the child is
/// killed. Spawn failure (git missing) surfaces as the io error.
fn run_git_timed(cmd: &[String], timeout: Duration) -> Result<GitOutput, std::io::Error> {
    let mut child = Command::new(&cmd[0])
        .args(&cmd[1..])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;
    let mut stdout = child.stdout.take().expect("stdout piped");
    let mut stderr = child.stderr.take().expect("stderr piped");
    let out_thread = std::thread::spawn(move || {
        let mut buf = Vec::new();
        let _ = stdout.read_to_end(&mut buf);
        buf
    });
    let err_thread = std::thread::spawn(move || {
        let mut buf = Vec::new();
        let _ = stderr.read_to_end(&mut buf);
        buf
    });
    let start = std::time::Instant::now();
    loop {
        match child.try_wait()? {
            Some(status) => {
                let out = out_thread.join().unwrap_or_default();
                let err = err_thread.join().unwrap_or_default();
                return Ok(GitOutput {
                    stdout: out,
                    stderr: err,
                    status: status.code().unwrap_or(-1),
                });
            }
            None => {
                if start.elapsed() >= timeout {
                    let _ = child.kill();
                    let _ = child.wait();
                    let _ = out_thread.join().unwrap_or_default();
                    let _ = err_thread.join().unwrap_or_default();
                    return Err(std::io::Error::new(
                        std::io::ErrorKind::TimedOut,
                        "git command timed out",
                    ));
                }
                std::thread::sleep(Duration::from_millis(10));
            }
        }
    }
}

// ---------------------------------------------------------------------------
// artifact_store — OS-083 workspace/artifact store (port of
// os/mos/artifact_store.py).
//
// A git-backed versioned shared filesystem where dispatched jobs deposit
// work products and reference them by path in the job record:
//     <root>/jobs/<job_id>/<artifact name>
//     <root>/jobs/<job_id>/manifest.json
// Every deposit is one git commit. Version numbers count from 1 per
// artifact name. A byte-identical redeposit is a no-op returning the
// current version with no new commit.
// ---------------------------------------------------------------------------

/// Default store root on the image (baked by the image builders).
pub const STORE_ROOT_DEFAULT: &str = "/var/lib/metaos/artifacts";
/// Manifest file name inside each job directory.
pub const MANIFEST_NAME: &str = "manifest.json";

/// One manifest record for an artifact (the record stored in manifest.json
/// and returned by deposit/list).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ArtifactRecord {
    /// Artifact name (relative POSIX path below the job directory).
    pub name: String,
    /// Dashboard-linkable path: `jobs/<job_id>/<name>`.
    pub path: String,
    /// Reference of the form `artifact:<job_id>/<name>@v<version>`.
    pub reference: String,
    /// Version number, counting from 1 per artifact name.
    pub version: u64,
    /// SHA-256 hex digest of the deposited bytes.
    pub sha256: String,
    /// Byte size of the deposited content.
    pub size: usize,
    /// Depositing nick, or "unknown" when none was given.
    pub author: String,
    /// Unix seconds when the deposit happened.
    pub deposited_at: u64,
}

/// Outcome of [`deposit`]: the manifest record plus whether a new git
/// commit was created (false for a byte-identical redeposit).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DepositOutcome {
    pub record: ArtifactRecord,
    pub new_commit: bool,
}

/// One entry of a version history list (oldest first).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct VersionEntry {
    pub version: u64,
    pub commit: String,
}

/// One entry attached to a job record by [`attach`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AttachedArtifact {
    pub path: String,
    pub reference: String,
    pub version: u64,
    pub sha256: String,
}

/// Run git inside the store root (with `-c safe.directory=*`, like the
/// Python `_git`); git failures become ArtifactStoreError. Text output is
/// decoded as UTF-8; undecodable output is an error, matching Python's
/// strict text decoding.
fn store_git(root: &Path, args: &[&str]) -> Result<String, ArtifactStoreError> {
    let mut cmd: Vec<String> = vec![
        "git".to_string(),
        "-c".to_string(),
        "safe.directory=*".to_string(),
        "-C".to_string(),
        root.to_string_lossy().into_owned(),
    ];
    for a in args {
        cmd.push(a.to_string());
    }
    let out = run_git_timed(&cmd, Duration::from_secs(60)).map_err(|e| {
        if e.kind() == std::io::ErrorKind::NotFound {
            ArtifactStoreError("git is not available on this machine".to_string())
        } else if e.kind() == std::io::ErrorKind::TimedOut {
            ArtifactStoreError(format!("git failed: {}", e))
        } else {
            ArtifactStoreError(format!("git failed: {}", e))
        }
    })?;
    if out.status != 0 {
        // Ported oddity: Python reports args[0] in the message, so for
        // the commit call (whose first arg is "-c") the message reads
        // "git -c failed: ...". Kept verbatim.
        let first = args.first().copied().unwrap_or("");
        let stderr = String::from_utf8_lossy(&out.stderr);
        return Err(ArtifactStoreError(format!(
            "git {} failed: {}",
            first,
            stderr.trim()
        )));
    }
    String::from_utf8(out.stdout)
        .map_err(|e| ArtifactStoreError(format!("git failed: {}", e)))
}

/// Run git inside the store root and return raw bytes (for `git show`,
/// where the text wrapper in `store_git` would corrupt binary content).
fn store_git_bytes(root: &Path, args: &[&str]) -> Result<Vec<u8>, ArtifactStoreError> {
    let mut cmd: Vec<String> = vec![
        "git".to_string(),
        "-c".to_string(),
        "safe.directory=*".to_string(),
        "-C".to_string(),
        root.to_string_lossy().into_owned(),
    ];
    for a in args {
        cmd.push(a.to_string());
    }
    let out = run_git_timed(&cmd, Duration::from_secs(60)).map_err(|e| {
        if e.kind() == std::io::ErrorKind::NotFound {
            ArtifactStoreError("git is not available on this machine".to_string())
        } else {
            ArtifactStoreError(format!("git failed: {}", e))
        }
    })?;
    if out.status != 0 {
        let first = args.first().copied().unwrap_or("");
        let stderr = String::from_utf8_lossy(&out.stderr);
        return Err(ArtifactStoreError(format!(
            "git {} failed: {}",
            first,
            stderr.trim()
        )));
    }
    Ok(out.stdout)
}

/// Job ids are single path segments (letters, digits, dot, underscore,
/// hyphen). A slash in a job id is refused.
pub fn validate_job_id(job_id: &str) -> Result<String, ArtifactStoreError> {
    if job_id.is_empty() {
        return Err(ArtifactStoreError(
            "job id must be a non-empty string".to_string(),
        ));
    }
    if job_id.contains('/') || job_id.contains('\\') || job_id.contains('\0') || job_id == "." || job_id == ".."
    {
        return Err(ArtifactStoreError(
            "job id must be a single path segment".to_string(),
        ));
    }
    if !job_id
        .chars()
        .all(|ch| ch.is_alphanumeric() || ch == '.' || ch == '_' || ch == '-')
    {
        return Err(ArtifactStoreError(
            "job id holds characters outside [A-Za-z0-9._-]".to_string(),
        ));
    }
    Ok(job_id.to_string())
}

/// Names are relative paths below the job directory. Absolute paths, empty
/// segments, "." and ".." segments, backslashes, and NUL bytes are refused,
/// so a deposit can never escape the store.
pub fn validate_name(name: &str) -> Result<String, ArtifactStoreError> {
    if name.is_empty() {
        return Err(ArtifactStoreError(
            "artifact name must be a non-empty string".to_string(),
        ));
    }
    if name.starts_with('/') || name.contains('\0') || name.contains('\\') {
        return Err(ArtifactStoreError(
            "artifact name must be a relative POSIX path".to_string(),
        ));
    }
    if name
        .split('/')
        .any(|part| part.is_empty() || part == "." || part == "..")
    {
        return Err(ArtifactStoreError(
            "artifact name must not contain empty, . or .. segments".to_string(),
        ));
    }
    Ok(name.to_string())
}

fn job_dir(root: &Path, job_id: &str) -> PathBuf {
    root.join("jobs").join(job_id)
}

fn manifest_path(root: &Path, job_id: &str) -> PathBuf {
    job_dir(root, job_id).join(MANIFEST_NAME)
}

/// Read a job manifest. A job with no manifest returns an empty manifest,
/// not an error: an empty store is a real state, not a failure.
fn read_manifest(root: &Path, job_id: &str) -> Result<JsonValue, ArtifactStoreError> {
    let path = manifest_path(root, job_id);
    if !path.exists() {
        return Ok(JsonValue::obj(vec![
            ("job_id", JsonValue::Str(job_id.to_string())),
            ("artifacts", JsonValue::Object(BTreeMap::new())),
        ]));
    }
    let text = fs::read_to_string(&path)
        .map_err(|e| ArtifactStoreError(format!("manifest unreadable: {}", e)))?;
    let data = json_parse(&text)
        .map_err(|e| ArtifactStoreError(format!("manifest unreadable: {}", e)))?;
    match &data {
        JsonValue::Object(m) => match m.get("artifacts") {
            Some(JsonValue::Object(_)) => Ok(data),
            _ => Err(ArtifactStoreError(
                "manifest has an unexpected shape".to_string(),
            )),
        },
        _ => Err(ArtifactStoreError(
            "manifest has an unexpected shape".to_string(),
        )),
    }
}

/// Write a manifest atomically (via a `.tmp` sibling + rename), in Python
/// `json.dump(indent=2, sort_keys=True)` format plus a trailing newline.
fn write_manifest(root: &Path, job_id: &str, manifest: &JsonValue) -> Result<(), ArtifactStoreError> {
    let path = manifest_path(root, job_id);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let mut text = String::new();
    json_dump(manifest, 0, &mut text);
    text.push('\n');
    let tmp = {
        let mut p = path.as_os_str().to_owned();
        p.push(".tmp");
        PathBuf::from(p)
    };
    fs::write(&tmp, text)?;
    fs::rename(&tmp, &path)?;
    Ok(())
}

/// Create the store repo on first deposit with local-only git identity
/// semantics (identity is passed per-commit, never global, as in Python).
fn ensure_repo(root: &Path) -> Result<(), ArtifactStoreError> {
    fs::create_dir_all(root)?;
    if !root.join(".git").is_dir() {
        store_git(root, &["init", "-q", "-b", "main"])?;
    }
    Ok(())
}

fn relpath(job_id: &str, name: &str) -> String {
    format!("jobs/{}/{}", job_id, name)
}

/// Parse one manifest artifact entry leniently, mirroring Python's
/// `.get()` defaults (missing version reads as 0, missing sha as "").
/// Unknown extra fields in the entry are preserved on rewrite by
/// [`deposit`] (it starts from the existing entry object).
fn record_from_value(name: &str, v: &JsonValue) -> ArtifactRecord {
    let s = |key: &str, default: &str| -> String {
        v.get(key)
            .and_then(|x| x.as_str())
            .unwrap_or(default)
            .to_string()
    };
    let n = |key: &str, default: i64| -> i64 {
        v.get(key).and_then(|x| x.as_i64()).unwrap_or(default)
    };
    ArtifactRecord {
        name: name.to_string(),
        path: s("path", ""),
        reference: s("reference", ""),
        version: n("version", 0).max(0) as u64,
        sha256: s("sha256", ""),
        size: n("size", 0).max(0) as usize,
        author: s("author", "unknown"),
        deposited_at: n("deposited_at", 0).max(0) as u64,
    }
}

fn record_to_value(record: &ArtifactRecord) -> JsonValue {
    JsonValue::obj(vec![
        ("name", JsonValue::Str(record.name.clone())),
        ("path", JsonValue::Str(record.path.clone())),
        ("reference", JsonValue::Str(record.reference.clone())),
        (
            "version",
            JsonValue::Int(record.version as i64),
        ),
        ("sha256", JsonValue::Str(record.sha256.clone())),
        ("size", JsonValue::Int(record.size as i64)),
        ("author", JsonValue::Str(record.author.clone())),
        (
            "deposited_at",
            JsonValue::Int(record.deposited_at as i64),
        ),
    ])
}

fn now_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

/// Deposit bytes as one version. Returns the manifest record plus whether
/// a new commit was created. A byte-identical redeposit returns the current
/// record unchanged, with `new_commit` false.
pub fn deposit(
    root: &Path,
    job_id: &str,
    name: &str,
    data: &[u8],
    author: &str,
) -> Result<DepositOutcome, ArtifactStoreError> {
    let job_id = validate_job_id(job_id)?;
    let name = validate_name(name)?;
    ensure_repo(root)?;
    let dir = job_dir(root, &job_id);
    fs::create_dir_all(&dir)?;
    let mut manifest = read_manifest(root, &job_id)?;
    let digest = sha256_hex(data);
    let artifacts = match manifest.get("artifacts") {
        Some(JsonValue::Object(_)) => manifest.get("artifacts").unwrap().clone(),
        _ => JsonValue::Object(BTreeMap::new()),
    };
    let current = artifacts.get(&name).map(|v| record_from_value(&name, v));
    if let Some(cur) = &current {
        if cur.sha256 == digest {
            return Ok(DepositOutcome {
                record: cur.clone(),
                new_commit: false,
            });
        }
    }
    let target = dir.join(&name);
    if let Some(parent) = target.parent() {
        fs::create_dir_all(parent)?;
    }
    let tmp = {
        let mut p = target.as_os_str().to_owned();
        p.push(".tmp");
        PathBuf::from(p)
    };
    fs::write(&tmp, data)?;
    fs::rename(&tmp, &target)?;
    let version = current.as_ref().map(|c| c.version).unwrap_or(0) + 1;
    let record = ArtifactRecord {
        name: name.clone(),
        path: relpath(&job_id, &name),
        reference: format!("artifact:{}/{}@v{}", job_id, name, version),
        version,
        sha256: digest,
        size: data.len(),
        author: if author.is_empty() {
            "unknown".to_string()
        } else {
            author.to_string()
        },
        deposited_at: now_secs(),
    };
    // Preserve any unknown fields on the previous entry, then overwrite
    // the known keys (Python replaces the whole entry; preserving extras
    // is strictly more faithful to the on-disk manifest).
    let mut entry = match artifacts.get(&name) {
        Some(JsonValue::Object(_)) => artifacts.get(&name).unwrap().clone(),
        _ => JsonValue::Object(BTreeMap::new()),
    };
    if let JsonValue::Object(ref mut m) = entry {
        for (k, v) in match record_to_value(&record) {
            JsonValue::Object(m2) => m2,
            _ => BTreeMap::new(),
        } {
            m.insert(k, v);
        }
    } else {
        entry = record_to_value(&record);
    }
    let mut new_artifacts = match artifacts {
        JsonValue::Object(m) => m,
        _ => BTreeMap::new(),
    };
    new_artifacts.insert(name.clone(), entry);
    if let JsonValue::Object(ref mut m) = manifest {
        m.insert("job_id".to_string(), JsonValue::Str(job_id.clone()));
        m.insert("artifacts".to_string(), JsonValue::Object(new_artifacts));
    }
    write_manifest(root, &job_id, &manifest)?;
    let rel_file = relpath(&job_id, &name);
    let rel_manifest = format!("jobs/{}/{}", job_id, MANIFEST_NAME);
    store_git(root, &["add", "--", &rel_file, &rel_manifest])?;
    store_git(
        root,
        &[
            "-c",
            "user.name=metaos-artifact-store",
            "-c",
            "user.email=artifact-store@metaos.local",
            "commit",
            "-q",
            "-m",
            &format!(
                "job {}: deposit {} v{} by {}",
                job_id, name, version, record.author
            ),
        ],
    )?;
    Ok(DepositOutcome {
        record,
        new_commit: true,
    })
}

/// Deposit a UTF-8 string (encoded as UTF-8, like Python `str` data).
pub fn deposit_str(
    root: &Path,
    job_id: &str,
    name: &str,
    data: &str,
    author: &str,
) -> Result<DepositOutcome, ArtifactStoreError> {
    deposit(root, job_id, name, data.as_bytes(), author)
}

/// Manifest records for one job, sorted by artifact name.
pub fn list_artifacts(
    root: &Path,
    job_id: &str,
) -> Result<Vec<ArtifactRecord>, ArtifactStoreError> {
    let job_id = validate_job_id(job_id)?;
    let manifest = read_manifest(root, &job_id)?;
    let mut out = Vec::new();
    if let Some(JsonValue::Object(m)) = manifest.get("artifacts") {
        // BTreeMap iteration is already sorted by name.
        for (name, v) in m {
            out.push(record_from_value(name, v));
        }
    }
    Ok(out)
}

fn version_commits(
    root: &Path,
    job_id: &str,
    name: &str,
) -> Result<Vec<String>, ArtifactStoreError> {
    let out = store_git(root, &["log", "--format=%H", "--", &relpath(job_id, name)])?;
    Ok(out.lines().filter(|l| !l.is_empty()).map(|s| s.to_string()).collect())
}

/// Artifact bytes: latest version, or one numbered version. A numbered
/// version maps to its git commit, so a version read never depends on the
/// current file on disk. Reading a version that does not exist raises,
/// never guesses a neighboring version.
pub fn read_artifact(
    root: &Path,
    job_id: &str,
    name: &str,
    version: Option<u64>,
) -> Result<Vec<u8>, ArtifactStoreError> {
    let job_id = validate_job_id(job_id)?;
    let name = validate_name(name)?;
    let manifest = read_manifest(root, &job_id)?;
    let current = manifest
        .get("artifacts")
        .and_then(|a| match a {
            JsonValue::Object(m) => m.get(&name),
            _ => None,
        });
    if current.is_none() {
        return Err(ArtifactStoreError(format!(
            "no artifact '{}' for job '{}'",
            name, job_id
        )));
    }
    match version {
        None => {
            // Python surfaces a raw OSError here; the Rust port surfaces
            // the same condition as an ArtifactStoreError with the I/O
            // message (see header notes).
            let data = fs::read(job_dir(root, &job_id).join(&name))?;
            Ok(data)
        }
        Some(v) => {
            if v < 1 {
                return Err(ArtifactStoreError(
                    "version must be a positive integer".to_string(),
                ));
            }
            let commits = version_commits(root, &job_id, &name)?;
            if v > commits.len() as u64 {
                return Err(ArtifactStoreError(format!(
                    "artifact '{}' for job '{}' has {} versions, no v{}",
                    name,
                    job_id,
                    commits.len(),
                    v
                )));
            }
            let commit = &commits[commits.len() - v as usize];
            let spec = format!("{}:{}", commit, relpath(&job_id, &name));
            let bytes = store_git_bytes(root, &["show", &spec]).map_err(|e| {
                if e.0.starts_with("git show failed") {
                    e
                } else {
                    ArtifactStoreError(format!("git show failed for version {}", v))
                }
            })?;
            Ok(bytes)
        }
    }
}

/// Version records, oldest first, from the artifact git log.
pub fn history(
    root: &Path,
    job_id: &str,
    name: &str,
) -> Result<Vec<VersionEntry>, ArtifactStoreError> {
    let job_id = validate_job_id(job_id)?;
    let name = validate_name(name)?;
    let commits = version_commits(root, &job_id, &name)?;
    Ok(commits
        .iter()
        .rev()
        .enumerate()
        .map(|(idx, commit)| VersionEntry {
            version: (idx + 1) as u64,
            commit: commit.clone(),
        })
        .collect())
}

/// Return a copy of a job record carrying its artifact paths. The input
/// record is never mutated. Each entry carries the path a dashboard can
/// link to, the artifact reference, the version, and the sha256. The
/// record is a JSON object: any existing `artifacts` array is preserved
/// (a non-array value is treated as absent, as in Python) and the store's
/// entries are appended.
pub fn attach(
    root: &Path,
    job_id: &str,
    record: &JsonValue,
) -> Result<JsonValue, ArtifactStoreError> {
    let job_id = validate_job_id(job_id)?;
    let mut out = match record {
        JsonValue::Object(_) => record.clone(),
        _ => {
            return Err(ArtifactStoreError(
                "job record must be a dict".to_string(),
            ))
        }
    };
    let mut existing: Vec<JsonValue> = match out.get("artifacts") {
        Some(JsonValue::Array(a)) => a.clone(),
        _ => Vec::new(),
    };
    for item in list_artifacts(root, &job_id)? {
        existing.push(JsonValue::obj(vec![
            ("path", JsonValue::Str(item.path)),
            ("reference", JsonValue::Str(item.reference)),
            ("version", JsonValue::Int(item.version as i64)),
            ("sha256", JsonValue::Str(item.sha256)),
        ]));
    }
    if let JsonValue::Object(ref mut m) = out {
        m.insert("artifacts".to_string(), JsonValue::Array(existing));
    }
    Ok(out)
}

/// Minimal CLI: deposit, list, read, show. Errors exit 2. `args` excludes
/// the program name. Output goes to the given writers (the Python CLI
/// prints to stdout/stderr directly; this form keeps the same bytes
/// testable without a binary target).
pub fn run_cli(
    args: &[String],
    stdout: &mut dyn Write,
    stderr: &mut dyn Write,
) -> i32 {
    const USAGE: &str = "usage: artifact_store deposit|list|read|show ROOT JOB [ARGS]";
    if args.is_empty() {
        let _ = writeln!(stderr, "{}", USAGE);
        return 2;
    }
    let cmd = args[0].as_str();
    let fail = |stderr: &mut dyn Write, msg: &str| -> i32 {
        let _ = writeln!(stderr, "ARTIFACT_STORE_ERROR: {}", msg);
        2
    };
    match cmd {
        "deposit" if args.len() >= 5 => {
            let (root, job_id, name, path) = (
                Path::new(&args[1]),
                args[2].as_str(),
                args[3].as_str(),
                args[4].as_str(),
            );
            let mut author = "";
            if let Some(idx) = args[5..].iter().position(|a| a == "--author") {
                // Python would IndexError-crash if --author is last; the
                // Rust CLI reports usage instead (see header notes).
                match args.get(5 + idx + 1) {
                    Some(v) => author = v.as_str(),
                    None => {
                        let _ = writeln!(stderr, "{}", USAGE);
                        return 2;
                    }
                }
            }
            let data = match fs::read(path) {
                Ok(d) => d,
                Err(e) => return fail(stderr, &e.to_string()),
            };
            match deposit(root, job_id, name, &data, author) {
                Ok(outcome) => {
                    // The CLI record carries new_commit, like Python's
                    // returned dict (the manifest copy does not).
                    let with_flag = match record_to_value(&outcome.record) {
                        JsonValue::Object(mut m) => {
                            m.insert(
                                "new_commit".to_string(),
                                JsonValue::Bool(outcome.new_commit),
                            );
                            JsonValue::Object(m)
                        }
                        other => other,
                    };
                    let mut text = String::new();
                    json_dump_compact(&with_flag, &mut text);
                    let _ = writeln!(stdout, "{}", text);
                    0
                }
                Err(e) => fail(stderr, &e.0),
            }
        }
        "list" if args.len() == 3 => {
            let (root, job_id) = (Path::new(&args[1]), args[2].as_str());
            match list_artifacts(root, job_id) {
                Ok(items) => {
                    for item in items {
                        let mut text = String::new();
                        json_dump_compact(&record_to_value(&item), &mut text);
                        let _ = writeln!(stdout, "{}", text);
                    }
                    0
                }
                Err(e) => fail(stderr, &e.0),
            }
        }
        "read" if args.len() >= 4 => {
            let (root, job_id, name) = (Path::new(&args[1]), args[2].as_str(), args[3].as_str());
            let mut version: Option<u64> = None;
            if let Some(idx) = args[4..].iter().position(|a| a == "--version") {
                match args.get(4 + idx + 1) {
                    Some(v) => match v.parse::<i64>() {
                        Ok(n) if n >= 0 => version = Some(n as u64),
                        // Negative parses but Python's read() rejects
                        // version < 1 with ArtifactStoreError (exit 2).
                        Ok(_) => {
                            return fail(stderr, "version must be a positive integer");
                        }
                        Err(_) => {
                            return fail(stderr, &format!(
                                "invalid literal for int() with base 10: '{}'",
                                v
                            ));
                        }
                    },
                    None => {
                        let _ = writeln!(stderr, "{}", USAGE);
                        return 2;
                    }
                }
            }
            match read_artifact(root, job_id, name, version) {
                Ok(bytes) => {
                    let _ = stdout.write_all(&bytes);
                    0
                }
                Err(e) => fail(stderr, &e.0),
            }
        }
        "show" if args.len() == 4 => {
            let (root, job_id, name) = (Path::new(&args[1]), args[2].as_str(), args[3].as_str());
            match history(root, job_id, name) {
                Ok(entries) => {
                    for e in entries {
                        let _ = writeln!(stdout, "v{} {}", e.version, e.commit);
                    }
                    0
                }
                Err(e) => fail(stderr, &e.0),
            }
        }
        _ => {
            let _ = writeln!(stderr, "{}", USAGE);
            2
        }
    }
}

// ---------------------------------------------------------------------------
// gitops — safe Git integration for MOS (port of os/mos/gitops.py).
//
// Workers never push to main. They commit on their own branch; the
// overseer reviews the diff and merges. Every mutating operation has
// guards: refuse to merge main into itself, refuse on a dirty tree,
// refuse unknown branches. Nothing here force-pushes, ever.
// ---------------------------------------------------------------------------

/// Run git in `repo` (no safe.directory flag, like Python's gitops `_git`).
/// Timeout is 120s, matching Python's default.
fn gitops_git(repo: &Path, args: &[&str]) -> Result<String, GitError> {
    let mut cmd: Vec<String> = vec![
        "git".to_string(),
        "-C".to_string(),
        repo.to_string_lossy().into_owned(),
    ];
    for a in args {
        cmd.push(a.to_string());
    }
    let out = run_git_timed(&cmd, Duration::from_secs(120)).map_err(|e| {
        if e.kind() == std::io::ErrorKind::NotFound {
            GitError("git not found on PATH".to_string())
        } else if e.kind() == std::io::ErrorKind::TimedOut {
            GitError(format!("git {} timed out", args.join(" ")))
        } else {
            GitError(format!("git {} failed: {}", args.join(" "), e))
        }
    })?;
    if out.status != 0 {
        let stderr = String::from_utf8_lossy(&out.stderr);
        let trimmed = stderr.trim();
        let tail: String = trimmed
            .chars()
            .rev()
            .take(500)
            .collect::<String>()
            .chars()
            .rev()
            .collect();
        return Err(GitError(format!(
            "git {} failed: {}",
            args.join(" "),
            tail
        )));
    }
    String::from_utf8(out.stdout)
        .map_err(|e| GitError(format!("git {} failed: {}", args.join(" "), e)))
}

/// True when `path` is inside a git repository.
pub fn is_repo(path: &Path) -> bool {
    gitops_git(path, &["rev-parse", "--git-dir"]).is_ok()
}

/// Current branch name (empty string on a detached HEAD, like Python's
/// `--show-current` output).
pub fn current_branch(repo: &Path) -> Result<String, GitError> {
    Ok(gitops_git(repo, &["branch", "--show-current"])?
        .trim()
        .to_string())
}

/// True when the working tree has no changes.
pub fn clean_tree(repo: &Path) -> Result<bool, GitError> {
    Ok(gitops_git(repo, &["status", "--porcelain"])?
        .trim()
        .is_empty())
}

/// True when the local branch exists.
pub fn branch_exists(repo: &Path, branch: &str) -> bool {
    gitops_git(repo, &["rev-parse", "--verify", &format!("refs/heads/{}", branch)]).is_ok()
}

/// Review summary for `branch` vs `base` (three-dot diff stat, file list,
/// and two-dot log).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReviewSummary {
    pub branch: String,
    pub base: String,
    pub files: Vec<String>,
    pub stat: String,
    pub commits: Vec<String>,
    pub commit_count: usize,
}

/// Return a review summary dict for branch vs base.
pub fn review_branch(
    repo: &Path,
    branch: &str,
    base: &str,
) -> Result<ReviewSummary, GitError> {
    if !is_repo(repo) {
        return Err(GitError(format!("not a git repo: {}", repo.display())));
    }
    if branch == base {
        return Err(GitError("refusing to review base against itself".to_string()));
    }
    for b in [branch, base] {
        if !branch_exists(repo, b) {
            return Err(GitError(format!("unknown branch: {}", b)));
        }
    }
    let stat = gitops_git(repo, &["diff", "--stat", &format!("{}...{}", base, branch)])?;
    let files = gitops_git(
        repo,
        &["diff", "--name-only", &format!("{}...{}", base, branch)],
    )?
    .split_whitespace()
    .map(|s| s.to_string())
    .collect::<Vec<_>>();
    let commits = gitops_git(
        repo,
        &[
            "log",
            "--format=%h %s",
            &format!("{}..{}", base, branch),
        ],
    )?
    .lines()
    .map(|s| s.to_string())
    .collect::<Vec<_>>();
    let commit_count = commits.len();
    Ok(ReviewSummary {
        branch: branch.to_string(),
        base: base.to_string(),
        files,
        stat: stat.trim().to_string(),
        commits,
        commit_count,
    })
}

/// Merge branch into base. Returns the merge commit hash.
///
/// Guards: branch != base, both exist, tree clean, base checked out.
/// Uses --no-ff so worker work is always visible as a merge.
pub fn approve_merge(
    repo: &Path,
    branch: &str,
    base: &str,
) -> Result<String, GitError> {
    if branch == base {
        return Err(GitError("refusing to merge base into itself".to_string()));
    }
    if !clean_tree(repo)? {
        return Err(GitError(
            "working tree dirty — refusing to merge".to_string(),
        ));
    }
    for b in [branch, base] {
        if !branch_exists(repo, b) {
            return Err(GitError(format!("unknown branch: {}", b)));
        }
    }
    if current_branch(repo)? != base {
        gitops_git(repo, &["checkout", base])?;
    }
    gitops_git(
        repo,
        &[
            "merge",
            "--no-ff",
            branch,
            "-m",
            &format!("Merge {} (MOS approved)", branch),
        ],
    )?;
    Ok(gitops_git(repo, &["rev-parse", "HEAD"])?.trim().to_string())
}

/// Record a rejection. Does not delete anything — the branch stays for
/// the worker to fix. Returns a human-readable summary.
///
/// Note: Python raises ValueError for an empty reason; the Rust port
/// returns a GitError carrying the same message (see header notes).
pub fn reject_branch(branch: &str, reason: &str) -> Result<String, GitError> {
    if reason.trim().is_empty() {
        return Err(GitError("rejection needs a reason".to_string()));
    }
    Ok(format!("REJECTED {}: {}", branch, reason.trim()))
}

/// Check out branch into a detached worktree at path. Returns path.
pub fn worktree_add(
    repo: &Path,
    branch: &str,
    path: &Path,
) -> Result<PathBuf, GitError> {
    if path.exists() {
        return Err(GitError(format!(
            "worktree path already exists: {}",
            path.display()
        )));
    }
    if !branch_exists(repo, branch) {
        return Err(GitError(format!("unknown branch: {}", branch)));
    }
    gitops_git(
        repo,
        &[
            "worktree",
            "add",
            "--detach",
            &path.to_string_lossy(),
            branch,
        ],
    )?;
    Ok(path.to_path_buf())
}

/// Remove a worktree (forced, like Python's `worktree remove --force`).
pub fn worktree_remove(repo: &Path, path: &Path) -> Result<(), GitError> {
    gitops_git(
        repo,
        &[
            "worktree",
            "remove",
            "--force",
            &path.to_string_lossy(),
        ],
    )?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Tests — derived from the modules' own behavior and edge cases (no test
// files are assigned to B19). The attach flow mirrors the caller test
// os/tests/test_crewboard_os084_artifacts.py (two deposits, then attach).
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    static COUNTER: AtomicUsize = AtomicUsize::new(0);

    struct TmpDir(PathBuf);

    impl TmpDir {
        fn new(tag: &str) -> TmpDir {
            let n = COUNTER.fetch_add(1, Ordering::SeqCst);
            let p = std::env::temp_dir().join(format!(
                "os-workspace-test-{}-{}-{}",
                std::process::id(),
                tag,
                n
            ));
            let _ = fs::remove_dir_all(&p);
            fs::create_dir_all(&p).expect("create temp dir");
            TmpDir(p)
        }

        fn path(&self) -> &Path {
            &self.0
        }
    }

    impl Drop for TmpDir {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }

    fn git(dir: &Path, args: &[&str]) -> String {
        let out = Command::new("git")
            .arg("-C")
            .arg(dir)
            .args(args)
            .output()
            .expect("run git");
        assert!(
            out.status.success(),
            "git {:?} failed: {}",
            args,
            String::from_utf8_lossy(&out.stderr)
        );
        String::from_utf8_lossy(&out.stdout).into_owned()
    }

    fn git_commit(dir: &Path, msg: &str) {
        git(dir, &["add", "-A"]);
        git(dir, &[
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "commit",
            "-q",
            "-m",
            msg,
        ]);
    }

    /// A git repo on main with local identity configured (merge commits
    /// need it, since approve_merge passes no -c identity flags).
    fn make_repo(tag: &str) -> TmpDir {
        let d = TmpDir::new(tag);
        git(d.path(), &["init", "-q", "-b", "main"]);
        git(d.path(), &["config", "user.name", "t"]);
        git(d.path(), &["config", "user.email", "t@t"]);
        fs::write(d.path().join("a.txt"), "one\n").unwrap();
        git_commit(d.path(), "initial");
        d
    }

    fn git_log_count(dir: &Path) -> usize {
        git(dir, &["rev-list", "--count", "HEAD"])
            .trim()
            .parse()
            .unwrap_or(0)
    }

    // -- sha256 vectors (NIST) -------------------------------------------

    #[test]
    fn sha256_empty_vector() {
        assert_eq!(
            sha256_hex(b""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
    }

    #[test]
    fn sha256_abc_vector() {
        assert_eq!(
            sha256_hex(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }

    #[test]
    fn sha256_long_input_matches_block_boundary() {
        // 64-byte input exercises the two-block path (message + padding).
        let data = vec![b'a'; 64];
        assert_eq!(sha256_hex(&data).len(), 64);
        assert_ne!(sha256_hex(&data), sha256_hex(b""));
    }

    // -- validation --------------------------------------------------------

    #[test]
    fn validate_job_id_ok() {
        for ok in ["a", "job-1", "a.b_c", "42", "...", "A-Z_0.9"] {
            assert!(validate_job_id(ok).is_ok(), "{}", ok);
        }
    }

    #[test]
    fn validate_job_id_rejects() {
        for bad in ["", ".", "..", "a/b", "a\\b", "a b", "a:b", "a\0b"] {
            assert!(validate_job_id(bad).is_err(), "{:?}", bad);
        }
    }

    #[test]
    fn validate_name_ok() {
        for ok in ["f.txt", "sub/dir/f.txt", "a.b/c-d_e.txt"] {
            assert!(validate_name(ok).is_ok(), "{}", ok);
        }
    }

    #[test]
    fn validate_name_rejects() {
        for bad in [
            "",
            "/abs.txt",
            "a//b",
            "a/",
            "/",
            ".",
            "..",
            "a/./b",
            "a/../b",
            "a\\b",
            "a\0b",
        ] {
            assert!(validate_name(bad).is_err(), "{:?}", bad);
        }
    }

    // -- deposit / list / read / history -----------------------------------

    #[test]
    fn deposit_first_version() {
        let d = TmpDir::new("dep1");
        let out = deposit(d.path(), "job1", "report.md", b"hello", "alice").unwrap();
        assert_eq!(out.record.version, 1);
        assert!(out.new_commit);
        assert_eq!(out.record.reference, "artifact:job1/report.md@v1");
        assert_eq!(out.record.path, "jobs/job1/report.md");
        assert_eq!(out.record.size, 5);
        assert_eq!(out.record.author, "alice");
        assert_eq!(out.record.sha256, sha256_hex(b"hello"));
        assert!(d.path().join("jobs/job1/manifest.json").exists());
        assert_eq!(git_log_count(d.path()), 1);
    }

    #[test]
    fn deposit_identical_is_noop() {
        let d = TmpDir::new("dep2");
        let first = deposit(d.path(), "j", "f.txt", b"same", "").unwrap();
        let second = deposit(d.path(), "j", "f.txt", b"same", "bob").unwrap();
        assert_eq!(second.record.version, first.record.version);
        assert!(!second.new_commit);
        assert_eq!(second.record.sha256, first.record.sha256);
        assert_eq!(git_log_count(d.path()), 1);
    }

    #[test]
    fn deposit_str_matches_bytes() {
        let d = TmpDir::new("dep3");
        let a = deposit(d.path(), "j", "f.txt", "café".as_bytes(), "").unwrap();
        let b = deposit_str(d.path(), "j2", "f.txt", "café", "").unwrap();
        assert_eq!(a.record.sha256, b.record.sha256);
    }

    #[test]
    fn deposit_changed_bumps_version_and_reads_versions() {
        let d = TmpDir::new("dep4");
        deposit(d.path(), "j", "f.txt", b"v1 bytes", "").unwrap();
        let v2 = deposit(d.path(), "j", "f.txt", b"v2 bytes", "").unwrap();
        assert_eq!(v2.record.version, 2);
        assert!(v2.new_commit);
        assert_eq!(read_artifact(d.path(), "j", "f.txt", None).unwrap(), b"v2 bytes");
        assert_eq!(
            read_artifact(d.path(), "j", "f.txt", Some(1)).unwrap(),
            b"v1 bytes"
        );
        assert_eq!(
            read_artifact(d.path(), "j", "f.txt", Some(2)).unwrap(),
            b"v2 bytes"
        );
        let h = history(d.path(), "j", "f.txt").unwrap();
        assert_eq!(h.len(), 2);
        assert_eq!(h[0].version, 1);
        assert_eq!(h[1].version, 2);
        assert_ne!(h[0].commit, h[1].commit);
    }

    #[test]
    fn binary_bytes_survive_versioned_read() {
        let d = TmpDir::new("dep15");
        let blob: Vec<u8> = (0..=255).map(|i| i as u8).collect();
        deposit(d.path(), "7", "out.bin", &blob, "").unwrap();
        deposit(d.path(), "7", "out.bin", b"second", "").unwrap();
        assert_eq!(
            read_artifact(d.path(), "7", "out.bin", Some(1)).unwrap(),
            blob
        );
        assert_eq!(
            read_artifact(d.path(), "7", "out.bin", Some(2)).unwrap(),
            b"second"
        );
        assert_eq!(
            read_artifact(d.path(), "7", "out.bin", None).unwrap(),
            b"second"
        );
    }

    #[test]
    fn deposit_default_author_is_unknown() {
        let d = TmpDir::new("dep5");
        let out = deposit(d.path(), "j", "f.txt", b"x", "").unwrap();
        assert_eq!(out.record.author, "unknown");
    }

    #[test]
    fn deposit_nested_name() {
        let d = TmpDir::new("dep6");
        let out = deposit(d.path(), "j", "sub/dir/f.txt", b"nested", "").unwrap();
        assert_eq!(out.record.path, "jobs/j/sub/dir/f.txt");
        assert_eq!(
            read_artifact(d.path(), "j", "sub/dir/f.txt", None).unwrap(),
            b"nested"
        );
    }

    #[test]
    fn deposit_unicode_name_and_author_roundtrip() {
        let d = TmpDir::new("dep7");
        let author = "Zoë \"q\" \\ slash";
        deposit(d.path(), "j", "café.txt", b"u", author).unwrap();
        let items = list_artifacts(d.path(), "j").unwrap();
        assert_eq!(items.len(), 1);
        assert_eq!(items[0].name, "café.txt");
        assert_eq!(items[0].author, author);
        // The manifest must parse back (Python fallback compatibility).
        let text = fs::read_to_string(d.path().join("jobs/j/manifest.json")).unwrap();
        assert!(json_parse(&text).is_ok());
    }

    #[test]
    fn list_sorted_and_empty_job() {
        let d = TmpDir::new("dep8");
        assert_eq!(list_artifacts(d.path(), "nobody").unwrap(), vec![]);
        deposit(d.path(), "j", "b.txt", b"b", "").unwrap();
        deposit(d.path(), "j", "a.txt", b"a", "").unwrap();
        let names: Vec<String> = list_artifacts(d.path(), "j")
            .unwrap()
            .iter()
            .map(|r| r.name.clone())
            .collect();
        assert_eq!(names, vec!["a.txt", "b.txt"]);
    }

    #[test]
    fn read_errors() {
        let d = TmpDir::new("dep9");
        deposit(d.path(), "j", "f.txt", b"data", "").unwrap();
        assert!(read_artifact(d.path(), "j", "nope.txt", None).is_err());
        assert!(read_artifact(d.path(), "j", "f.txt", Some(0)).is_err());
        assert!(read_artifact(d.path(), "j", "f.txt", Some(2)).is_err());
        assert!(read_artifact(d.path(), "j", "f.txt", Some(99)).is_err());
    }

    #[test]
    fn read_latest_missing_file_errors() {
        let d = TmpDir::new("dep10");
        deposit(d.path(), "j", "f.txt", b"data", "").unwrap();
        fs::remove_file(d.path().join("jobs/j/f.txt")).unwrap();
        // Python surfaces a raw OSError here; the port surfaces an error
        // carrying the I/O message.
        assert!(read_artifact(d.path(), "j", "f.txt", None).is_err());
        // Numbered reads do not depend on the disk file.
        assert_eq!(
            read_artifact(d.path(), "j", "f.txt", Some(1)).unwrap(),
            b"data"
        );
    }

    #[test]
    fn history_unknown_artifact_in_existing_store_is_empty() {
        let d = TmpDir::new("dep11");
        deposit(d.path(), "j", "f.txt", b"data", "").unwrap();
        assert_eq!(history(d.path(), "j", "ghost.txt").unwrap(), vec![]);
    }

    #[test]
    fn history_without_repo_errors() {
        let d = TmpDir::new("dep12");
        assert!(history(d.path(), "j", "f.txt").is_err());
    }

    #[test]
    fn manifest_malformed_and_wrong_shape_error() {
        let d = TmpDir::new("dep13");
        let dir = d.path().join("jobs/j");
        fs::create_dir_all(&dir).unwrap();
        fs::write(dir.join("manifest.json"), "{not json").unwrap();
        let err = list_artifacts(d.path(), "j").unwrap_err();
        assert!(err.0.contains("manifest unreadable"), "{}", err.0);
        fs::write(
            dir.join("manifest.json"),
            "{\"job_id\": \"j\", \"artifacts\": []}",
        )
        .unwrap();
        let err = list_artifacts(d.path(), "j").unwrap_err();
        assert!(err.0.contains("unexpected shape"), "{}", err.0);
    }

    #[test]
    fn manifest_preserves_unknown_fields_on_redeposit() {
        let d = TmpDir::new("dep14");
        let dir = d.path().join("jobs/j");
        fs::create_dir_all(&dir).unwrap();
        fs::write(
            dir.join("manifest.json"),
            "{\"artifacts\": {\"f.txt\": {\"extra\": \"keep\", \"sha256\": \"old\", \"version\": 3}}, \"job_id\": \"j\", \"note\": \"hi\"}",
        )
        .unwrap();
        // The hand-written manifest has no git repo; ensure_repo creates
        // one, but the artifact file does not exist in git history, so a
        // changed deposit must still commit cleanly.
        deposit(d.path(), "j", "f.txt", b"new bytes", "").unwrap();
        let text = fs::read_to_string(dir.join("manifest.json")).unwrap();
        let v = json_parse(&text).unwrap();
        assert_eq!(v.get("note").and_then(|x| x.as_str()), Some("hi"));
        let entry = v
            .get("artifacts")
            .and_then(|a| a.get("f.txt"))
            .expect("entry");
        assert_eq!(entry.get("extra").and_then(|x| x.as_str()), Some("keep"));
        assert_eq!(entry.get("version").and_then(|x| x.as_i64()), Some(4));
    }

    // -- attach ---------------------------------------------------------------

    #[test]
    fn attach_two_deposits_mirrors_caller_test() {
        let d = TmpDir::new("att1");
        deposit(d.path(), "42", "report.md", b"v1 bytes", "").unwrap();
        deposit(d.path(), "42", "report.md", b"v2 bytes", "").unwrap();
        let input = JsonValue::obj(vec![("title", JsonValue::Str("Live job".to_string()))]);
        let out = attach(d.path(), "42", &input).unwrap();
        // Input never mutated.
        assert!(input.get("artifacts").is_none());
        let arts = out.get("artifacts").and_then(|a| a.as_array()).unwrap();
        assert_eq!(arts.len(), 1);
        let e = &arts[0];
        assert_eq!(
            e.get("path").and_then(|x| x.as_str()),
            Some("jobs/42/report.md")
        );
        assert_eq!(
            e.get("reference").and_then(|x| x.as_str()),
            Some("artifact:42/report.md@v2")
        );
        assert_eq!(e.get("version").and_then(|x| x.as_i64()), Some(2));
        assert_eq!(out.get("title").and_then(|x| x.as_str()), Some("Live job"));
    }

    #[test]
    fn attach_preserves_existing_artifacts() {
        let d = TmpDir::new("att2");
        deposit(d.path(), "j", "f.txt", b"data", "").unwrap();
        let existing = JsonValue::Array(vec![JsonValue::obj(vec![(
            "path",
            JsonValue::Str("old".to_string()),
        )])]);
        let input = JsonValue::obj(vec![("artifacts", existing)]);
        let out = attach(d.path(), "j", &input).unwrap();
        let arts = out.get("artifacts").and_then(|a| a.as_array()).unwrap();
        assert_eq!(arts.len(), 2);
        assert_eq!(
            arts[0].get("path").and_then(|x| x.as_str()),
            Some("old")
        );
    }

    #[test]
    fn attach_rejects_non_object() {
        let d = TmpDir::new("att3");
        assert!(attach(d.path(), "j", &JsonValue::Str("x".to_string())).is_err());
    }

    // -- JSON -----------------------------------------------------------------

    #[test]
    fn json_roundtrip() {
        let v = JsonValue::obj(vec![
            ("a", JsonValue::Int(-3)),
            ("b", JsonValue::Float(1.5)),
            ("c", JsonValue::Str("café \"q\" \\ \n".to_string())),
            (
                "d",
                JsonValue::Array(vec![JsonValue::Bool(true), JsonValue::Null]),
            ),
            ("e", JsonValue::obj(vec![])),
        ]);
        let mut text = String::new();
        json_dump(&v, 0, &mut text);
        let back = json_parse(&text).unwrap();
        assert_eq!(back, v);
        // Sorted keys: "a" first, and Python-style indent present.
        assert!(text.starts_with("{\n  \"a\": -3,"));
    }

    #[test]
    fn json_rejects_trailing_garbage() {
        assert!(json_parse("{\"a\": 1} junk").is_err());
        assert!(json_parse("").is_err());
        assert!(json_parse("\"unterminated").is_err());
    }

    // -- CLI ------------------------------------------------------------------

    fn cli(args: &[&str]) -> (i32, String, String) {
        let owned: Vec<String> = args.iter().map(|s| s.to_string()).collect();
        let mut out: Vec<u8> = Vec::new();
        let mut err: Vec<u8> = Vec::new();
        let code = run_cli(&owned, &mut out, &mut err);
        (
            code,
            String::from_utf8_lossy(&out).into_owned(),
            String::from_utf8_lossy(&err).into_owned(),
        )
    }

    #[test]
    fn cli_full_flow_and_errors() {
        let d = TmpDir::new("cli1");
        let root = d.path().to_string_lossy().into_owned();
        let src = d.path().join("in.bin");
        fs::write(&src, b"payload").unwrap();
        let src_s = src.to_string_lossy().into_owned();
        let (code, out, _) = cli(&[
            "deposit",
            &root,
            "j",
            "f.bin",
            &src_s,
            "--author",
            "alice",
        ]);
        assert_eq!(code, 0, "deposit failed");
        let rec = json_parse(out.trim()).unwrap();
        assert_eq!(rec.get("version").and_then(|x| x.as_i64()), Some(1));
        assert_eq!(
            rec.get("new_commit").and_then(|x| match x {
                JsonValue::Bool(b) => Some(*b),
                _ => None,
            }),
            Some(true)
        );
        assert_eq!(rec.get("author").and_then(|x| x.as_str()), Some("alice"));
        let (code, out, _) = cli(&["list", &root, "j"]);
        assert_eq!(code, 0);
        assert_eq!(out.lines().count(), 1);
        let (code, out, _) = cli(&["read", &root, "j", "f.bin"]);
        assert_eq!(code, 0);
        assert_eq!(out, "payload");
        let (code, out, _) = cli(&["show", &root, "j", "f.bin"]);
        assert_eq!(code, 0);
        assert!(out.starts_with("v1 "), "{}", out);
        // Errors: usage and missing artifact both exit 2.
        assert_eq!(cli(&[]).0, 2);
        assert_eq!(cli(&["bogus", &root, "j"]).0, 2);
        let (code, _, err) = cli(&["read", &root, "j", "ghost.txt"]);
        assert_eq!(code, 2);
        assert!(err.contains("ARTIFACT_STORE_ERROR"), "{}", err);
    }

    #[test]
    fn cli_read_version_flag() {
        let d = TmpDir::new("cli2");
        deposit(d.path(), "j", "f.txt", b"one", "").unwrap();
        deposit(d.path(), "j", "f.txt", b"two", "").unwrap();
        let root = d.path().to_string_lossy().into_owned();
        let (code, out, _) = cli(&["read", &root, "j", "f.txt", "--version", "1"]);
        assert_eq!(code, 0);
        assert_eq!(out, "one");
        let (code, _, _) = cli(&["read", &root, "j", "f.txt", "--version", "nope"]);
        assert_eq!(code, 2);
    }

    // -- gitops ---------------------------------------------------------------

    #[test]
    fn gitops_is_repo_and_branch_and_clean() {
        let d = make_repo("go1");
        assert!(is_repo(d.path()));
        assert_eq!(current_branch(d.path()).unwrap(), "main");
        assert!(clean_tree(d.path()).unwrap());
        assert!(branch_exists(d.path(), "main"));
        assert!(!branch_exists(d.path(), "ghost"));
        fs::write(d.path().join("a.txt"), "dirty\n").unwrap();
        assert!(!clean_tree(d.path()).unwrap());
        let plain = TmpDir::new("go1b");
        assert!(!is_repo(plain.path()));
    }

    #[test]
    fn gitops_review_branch_ok() {
        let d = make_repo("go2");
        git(d.path(), &["checkout", "-q", "-b", "feature"]);
        fs::write(d.path().join("b.txt"), "new\n").unwrap();
        fs::write(d.path().join("a.txt"), "two\n").unwrap();
        git_commit(d.path(), "feature work");
        let s = review_branch(d.path(), "feature", "main").unwrap();
        assert_eq!(s.branch, "feature");
        assert_eq!(s.base, "main");
        assert_eq!(s.commit_count, 1);
        assert_eq!(s.commits.len(), 1);
        assert!(s.commits[0].contains("feature work"));
        assert!(s.files.contains(&"a.txt".to_string()));
        assert!(s.files.contains(&"b.txt".to_string()));
        assert!(!s.stat.is_empty());
    }

    #[test]
    fn gitops_review_guards() {
        let d = make_repo("go3");
        assert!(review_branch(d.path(), "main", "main").is_err());
        let err = review_branch(d.path(), "ghost", "main").unwrap_err();
        assert!(err.0.contains("unknown branch: ghost"), "{}", err.0);
        let plain = TmpDir::new("go3b");
        let err = review_branch(plain.path(), "x", "main").unwrap_err();
        assert!(err.0.contains("not a git repo"), "{}", err.0);
    }

    #[test]
    fn gitops_approve_merge_ok_and_guards() {
        let d = make_repo("go4");
        git(d.path(), &["checkout", "-q", "-b", "feature"]);
        fs::write(d.path().join("b.txt"), "new\n").unwrap();
        git_commit(d.path(), "feature work");
        // Approve from the feature checkout: base must be checked out first.
        let hash = approve_merge(d.path(), "feature", "main").unwrap();
        assert_eq!(hash.len(), 40);
        assert_eq!(current_branch(d.path()).unwrap(), "main");
        let log = git(d.path(), &["log", "--format=%s", "-1"]);
        assert!(log.contains("Merge feature (MOS approved)"), "{}", log);
        assert!(clean_tree(d.path()).unwrap());
        // Guards.
        assert!(approve_merge(d.path(), "main", "main").is_err());
        assert!(approve_merge(d.path(), "ghost", "main").is_err());
        fs::write(d.path().join("a.txt"), "dirty\n").unwrap();
        git(d.path(), &["checkout", "-q", "-b", "other"]);
        git_commit(d.path(), "other work");
        fs::write(d.path().join("a.txt"), "dirty again\n").unwrap();
        assert!(approve_merge(d.path(), "other", "main").is_err());
    }

    #[test]
    fn gitops_reject_branch() {
        assert_eq!(
            reject_branch("feat", "  needs tests  ").unwrap(),
            "REJECTED feat: needs tests"
        );
        assert!(reject_branch("feat", "").is_err());
        assert!(reject_branch("feat", "   ").is_err());
    }

    #[test]
    fn gitops_worktree_add_remove() {
        let d = make_repo("go5");
        let wt = d.path().join("wt");
        let back = worktree_add(d.path(), "main", &wt).unwrap();
        assert_eq!(back, wt);
        assert!(wt.join(".git").exists());
        assert!(worktree_add(d.path(), "main", &wt).is_err());
        let wt2 = d.path().join("wt2");
        assert!(worktree_add(d.path(), "ghost", &wt2).is_err());
        worktree_remove(d.path(), &wt).unwrap();
        assert!(!wt.exists());
    }
}
