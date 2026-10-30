//! Crate `os-jobs` — Meta OS Rust rebuild skeleton (B00).
//!
//! Batch B16 — Jobs service. Owner: Milo.
//! Source files this batch ports:
//! - `os/jobs.py`
//! - `os/tests/test_claims.py`
//! - `os/tests/test_intel_brief_environment_jobs.py`
//! - `os/tests/test_jobs.py`
//! - `os/tests/test_jobs_req.py`
//! - `os/tests/test_os_jobs_unit.py`
//!
//! Skeleton only: no logic yet. The Python/Node sources listed above are
//! the spec — port behavior, do not redesign. See BATCHES.md for the
//! compile gates and the parity rule.
//!
//! Crate `os-jobs` — Meta OS Rust rebuild skeleton (B00).
//!
//! Batch B16 — Jobs service. Owner: Milo.
//! Source files this batch ports:
//! - `os/jobs.py`
//! - `os/tests/test_claims.py`
//! - `os/tests/test_intel_brief_environment_jobs.py`
//! - `os/tests/test_jobs.py`
//! - `os/tests/test_jobs_req.py`
//! - `os/tests/test_os_jobs_unit.py`
//!
//! Skeleton only: no logic yet. The Python/Node sources listed above are
//! the spec — port behavior, do not redesign. See BATCHES.md for the
//! compile gates and the parity rule.
//!
//! Port notes (B16, Milo). `os/jobs.py` is a command-line queue service
//! whose state lives in an Upstash Redis behind a REST API; the bus
//! carries only short wire announcements. This crate ports the command
//! logic, the pure helpers (artifact refs, keyring, HMAC signing,
//! canonical payloads), and the brief environment jobs surface. Two
//! seams keep the port std-only and testable:
//!
//! * [`JobStore`] abstracts the state backend. [`FakeStore`] is the
//!   in-memory implementation the tests use (it mirrors the Python
//!   tests' FakeUpstash, including TTL expiry driven by the clock).
//!   A live Upstash REST transport is NOT included: Rust's std has
//!   no HTTPS client, so a real transport needs a separate crate
//!   decision; it is deliberately left as the trait boundary rather
//!   than faked.
//! * [`Clock`] abstracts time. [`FakeClock`] lets tests advance time
//!   the way the Python tests advance their fake.
//!
//! Commands return [`CmdOutcome`] (exit code, stdout, stderr), the
//! same triple the Python tests capture from `run_cli`.
//!
//! Approximations, stated plainly (see also the final report):
//! * `relay_common`'s nick-claim cache is not ported: every
//!   [`JobQueue::nick_claim`] call reads the store. The cache is a
//!   performance optimization; claim outcomes are unchanged.
//! * `send`/`poll`/`watch`/`presence`/DM-room behavior from
//!   `test_claims.py` belongs to other batches (bus messaging, relay)
//!   and is NOT ported here; only the nick-claim surface `jobs.py`
//!   depends on (`nick_holder`, and the claim itself for the spoof
//!   warning) is ported.
//! * `compose_template_brief` itself belongs to the intel batches;
//!   only its jobs input (`environment_jobs_record`) and the four
//!   `environment_lines` are ported here.
//! * Artifact-reference versions that overflow `u64` are treated as
//!   malformed; Python accepts arbitrary-precision versions. Real
//!   versions are small; this never triggers in practice.
//! * `clean_room`'s error uses a small Python-style repr; exotic
//!   control characters in a room name may render differently.

use std::cell::Cell;
use std::collections::HashMap;
use std::rc::Rc;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

/// Default claim-lease length, seconds (30 minutes).
pub const LEASE_DEFAULT: u64 = 1800;
/// Default job namespace prefix (`MUSE_RELAY_JOBNS` overrides it).
pub const DEFAULT_NS: &str = "muse-bus:job";
/// Signature version written by new posts.
pub const SIG_VERSION: &str = "2";
/// Nick-claim TTL, seconds; mirrors `relay_common.NICKCLAIM_TTL`,
/// which equals `PRESENCE_TTL` (the reservation lapses exactly when
/// presence does).
pub const NICKCLAIM_TTL: u64 = 120;
/// Presence TTL, seconds; kept equal to [`NICKCLAIM_TTL`] by
/// construction, as the Python test pins.
pub const PRESENCE_TTL: u64 = 120;

/// A state-backend failure. [`FakeStore`] never produces one; a real
/// transport maps its failures here.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StoreError(pub String);

impl std::fmt::Display for StoreError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for StoreError {}

/// Time source, in whole Unix seconds.
pub trait Clock {
    fn now_secs(&self) -> u64;
}

/// Wall-clock time.
pub struct SystemClock;

impl Clock for SystemClock {
    fn now_secs(&self) -> u64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0)
    }
}

/// Controllable clock for tests; mirrors the Python fake's `now` /
/// `advance`.
pub struct FakeClock {
    now: Cell<u64>,
}

impl FakeClock {
    pub fn new(start: u64) -> Self {
        FakeClock { now: Cell::new(start) }
    }

    pub fn advance(&self, secs: u64) {
        self.now.set(self.now.get().saturating_add(secs));
    }
}

impl Clock for FakeClock {
    fn now_secs(&self) -> u64 {
        self.now.get()
    }
}

/// How a `set` command treats an existing key.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SetMode {
    /// Set only when the key is absent (or expired): `SET NX`.
    Nx,
    /// Set only when the key is present (and unexpired): `SET XX`.
    Xx,
}

/// The state backend seam. Keys, fields, and values are plain
/// strings: the Upstash REST path-quoting layer lives in the
/// transport, not here (see [`url_quote`]).
pub trait JobStore {
    fn incr(&mut self, key: &str) -> Result<u64, StoreError>;
    fn hset(&mut self, key: &str, fields: &[(&str, &str)]) -> Result<(), StoreError>;
    fn hgetall(&mut self, key: &str) -> Result<Vec<(String, String)>, StoreError>;
    fn hdel(&mut self, key: &str, fields: &[&str]) -> Result<(), StoreError>;
    fn get(&mut self, key: &str) -> Result<Option<String>, StoreError>;
    /// Returns true when the value was stored (`OK` from the server).
    fn set(
        &mut self,
        key: &str,
        value: &str,
        mode: Option<SetMode>,
        ex_secs: Option<u64>,
    ) -> Result<bool, StoreError>;
    fn del(&mut self, key: &str) -> Result<(), StoreError>;
    /// Refresh the TTL of an existing string key; false when absent.
    fn expire(&mut self, key: &str, secs: u64) -> Result<bool, StoreError>;
    fn zadd(&mut self, key: &str, score: i64, member: &str) -> Result<(), StoreError>;
    fn zrange(&mut self, key: &str) -> Result<Vec<String>, StoreError>;
}

/// In-memory [`JobStore`], mirroring the Python tests' FakeUpstash:
/// string keys carry optional TTLs evaluated against the shared
/// clock, hashes hold job fields, zsets hold the job index.
pub struct FakeStore {
    clock: Rc<FakeClock>,
    strings: HashMap<String, (String, Option<u64>)>,
    hashes: HashMap<String, HashMap<String, String>>,
    zsets: HashMap<String, Vec<(i64, String)>>,
}

impl FakeStore {
    pub fn new(clock: Rc<FakeClock>) -> Self {
        FakeStore {
            clock,
            strings: HashMap::new(),
            hashes: HashMap::new(),
            zsets: HashMap::new(),
        }
    }

    fn now(&self) -> u64 {
        self.clock.now_secs()
    }

    fn purge(&mut self, key: &str) {
        if let Some((_, expiry)) = self.strings.get(key) {
            if expiry.map_or(false, |e| self.now() >= e) {
                self.strings.remove(key);
            }
        }
    }
}

impl JobStore for FakeStore {
    fn incr(&mut self, key: &str) -> Result<u64, StoreError> {
        self.purge(key);
        let cur = self
            .strings
            .get(key)
            .and_then(|(v, _)| v.parse::<u64>().ok())
            .unwrap_or(0);
        let next = cur + 1;
        self.strings
            .insert(key.to_string(), (next.to_string(), None));
        Ok(next)
    }

    fn hset(&mut self, key: &str, fields: &[(&str, &str)]) -> Result<(), StoreError> {
        let entry = self.hashes.entry(key.to_string()).or_default();
        for (f, v) in fields {
            entry.insert(f.to_string(), v.to_string());
        }
        Ok(())
    }

    fn hgetall(&mut self, key: &str) -> Result<Vec<(String, String)>, StoreError> {
        match self.hashes.get(key) {
            Some(map) => {
                let mut pairs: Vec<(String, String)> =
                    map.iter().map(|(k, v)| (k.clone(), v.clone())).collect();
                pairs.sort();
                Ok(pairs)
            }
            None => Ok(Vec::new()),
        }
    }

    fn hdel(&mut self, key: &str, fields: &[&str]) -> Result<(), StoreError> {
        if let Some(map) = self.hashes.get_mut(key) {
            for f in fields {
                map.remove(*f);
            }
        }
        Ok(())
    }

    fn get(&mut self, key: &str) -> Result<Option<String>, StoreError> {
        self.purge(key);
        Ok(self.strings.get(key).map(|(v, _)| v.clone()))
    }

    fn set(
        &mut self,
        key: &str,
        value: &str,
        mode: Option<SetMode>,
        ex_secs: Option<u64>,
    ) -> Result<bool, StoreError> {
        self.purge(key);
        let exists = self.strings.contains_key(key);
        match mode {
            Some(SetMode::Nx) if exists => return Ok(false),
            Some(SetMode::Xx) if !exists => return Ok(false),
            _ => {}
        }
        let expiry = ex_secs.map(|ttl| self.now() + ttl);
        self.strings
            .insert(key.to_string(), (value.to_string(), expiry));
        Ok(true)
    }

    fn del(&mut self, key: &str) -> Result<(), StoreError> {
        self.strings.remove(key);
        self.hashes.remove(key);
        self.zsets.remove(key);
        Ok(())
    }

    fn expire(&mut self, key: &str, secs: u64) -> Result<bool, StoreError> {
        self.purge(key);
        let now = self.now();
        match self.strings.get_mut(key) {
            Some((_, expiry)) => {
                *expiry = Some(now + secs);
                Ok(true)
            }
            None => Ok(false),
        }
    }

    fn zadd(&mut self, key: &str, score: i64, member: &str) -> Result<(), StoreError> {
        let set = self.zsets.entry(key.to_string()).or_default();
        set.retain(|(_, m)| m != member);
        set.push((score, member.to_string()));
        Ok(())
    }

    fn zrange(&mut self, key: &str) -> Result<Vec<String>, StoreError> {
        match self.zsets.get(key) {
            Some(set) => {
                let mut sorted = set.clone();
                sorted.sort();
                Ok(sorted.into_iter().map(|(_, m)| m).collect())
            }
            None => Ok(Vec::new()),
        }
    }
}

// ---------------------------------------------------------------------------
// Small pure helpers ported from `os/jobs.py` and `relay_common.py`.
// ---------------------------------------------------------------------------

/// `urllib.parse.quote(s, safe="")`: percent-encode everything except
/// the unreserved set. Used for REST path segments by the transport.
pub fn url_quote(s: &str) -> String {
    let mut out = String::new();
    for &b in s.as_bytes() {
        let unreserved = b.is_ascii_alphanumeric() || matches!(b, b'_' | b'.' | b'-' | b'~');
        if unreserved {
            out.push(b as char);
        } else {
            out.push_str(&format!("%{:02X}", b));
        }
    }
    out
}

/// `urllib.parse.unquote`: percent-decode `%XX` sequences; a malformed
/// `%` sequence is left as-is. (`unquote`, not `unquote_plus`: `+`
/// stays `+`.)
pub fn url_unquote(s: &str) -> String {
    let bytes = s.as_bytes();
    let mut out: Vec<u8> = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'%'
            && i + 2 < bytes.len()
            && bytes[i + 1].is_ascii_hexdigit()
            && bytes[i + 2].is_ascii_hexdigit()
        {
            let hex = &s[i + 1..i + 3];
            out.push(u8::from_str_radix(hex, 16).unwrap_or(b'%'));
            i += 3;
        } else {
            out.push(bytes[i]);
            i += 1;
        }
    }
    String::from_utf8_lossy(&out).into_owned()
}

/// A small Python-style `repr` for short strings: single quotes, with
/// backslash and single-quote escaped. Used only in error messages
/// (`clean_room`, keyring, artifact refs) to match Python's text.
pub fn python_repr(s: &str) -> String {
    let mut out = String::from("'");
    for c in s.chars() {
        match c {
            '\\' => out.push_str("\\\\"),
            '\'' => out.push_str("\\'"),
            _ => out.push(c),
        }
    }
    out.push('\'');
    out
}

/// `relay_common.clean_room`: lowercase, strip, keep `[a-z0-9_-]`;
/// `""` means the default room. A non-empty room that cleans to
/// nothing is an error.
pub fn clean_room(room: &str) -> Result<String, String> {
    let clean: String = room
        .trim()
        .to_lowercase()
        .chars()
        .filter(|c| c.is_ascii_alphanumeric() || *c == '_' || *c == '-')
        .collect();
    if !room.is_empty() && clean.is_empty() {
        return Err(format!("invalid room name: {}", python_repr(room)));
    }
    Ok(clean)
}

/// `relay_common.bus_key`: the default room is the legacy `muse-bus`
/// list; any other room is `muse-bus:room:<clean>`.
pub fn bus_key(room: &str) -> Result<String, String> {
    let clean = clean_room(room)?;
    if clean.is_empty() {
        Ok("muse-bus".to_string())
    } else {
        Ok(format!("muse-bus:room:{}", clean))
    }
}

/// Key builders. `MUSE_RELAY_JOBNS` overrides the `muse-bus:job`
/// prefix in Python; here the namespace travels on the queue.
pub fn seq_key(ns: &str) -> String {
    format!("{}seq", ns)
}

pub fn job_key(ns: &str, jid: &str) -> String {
    format!("{}:{}", ns, jid)
}

pub fn spec_key(ns: &str, jid: &str) -> String {
    format!("{}:{}:spec", ns, jid)
}

pub fn claim_key(ns: &str, jid: &str) -> String {
    format!("{}:{}:claim", ns, jid)
}

pub fn index_key(ns: &str) -> String {
    format!("{}index", ns)
}

/// `relay_common._nickclaim_key`: the nick reservation key. The nick
/// itself is URL-quoted, as in the Python transport path.
pub fn nickclaim_key(nick: &str) -> String {
    format!("muse-bus:nickclaim:{}", url_quote(nick))
}

/// SHA-256, implemented from scratch: Rust's std has no hash crates,
/// and this crate takes no external dependencies.
pub fn sha256(data: &[u8]) -> [u8; 32] {
    const K: [u32; 64] = [
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
    let mut h: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c,
        0x1f83d9ab, 0x5be0cd19,
    ];
    let bit_len = (data.len() as u64) * 8;
    let mut msg = data.to_vec();
    msg.push(0x80);
    while msg.len() % 64 != 56 {
        msg.push(0);
    }
    msg.extend_from_slice(&bit_len.to_be_bytes());
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
            let temp1 = hh
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(K[i])
                .wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let temp2 = s0.wrapping_add(maj);
            hh = g;
            g = f;
            f = e;
            e = d.wrapping_add(temp1);
            d = c;
            c = b;
            b = a;
            a = temp1.wrapping_add(temp2);
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
    for (i, word) in h.iter().enumerate() {
        out[i * 4..i * 4 + 4].copy_from_slice(&word.to_be_bytes());
    }
    out
}

/// HMAC-SHA256, as `hmac.new(secret, payload, hashlib.sha256)`.
pub fn hmac_sha256(secret: &[u8], payload: &[u8]) -> [u8; 32] {
    let mut key = secret.to_vec();
    if key.len() > 64 {
        key = sha256(&key).to_vec();
    }
    key.resize(64, 0);
    let mut inner = Vec::with_capacity(64 + payload.len());
    for b in &key {
        inner.push(b ^ 0x36);
    }
    inner.extend_from_slice(payload);
    let inner_hash = sha256(&inner);
    let mut outer = Vec::with_capacity(64 + 32);
    for b in &key {
        outer.push(b ^ 0x5c);
    }
    outer.extend_from_slice(&inner_hash);
    sha256(&outer)
}

/// Lowercase hex, as Python's `hexdigest`.
pub fn hex_digest(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

/// Constant-time-ish equality for signature comparison (Python uses
/// `hmac.compare_digest`).
pub fn ct_eq(a: &str, b: &str) -> bool {
    if a.len() != b.len() {
        return false;
    }
    let mut diff = 0u8;
    for (x, y) in a.bytes().zip(b.bytes()) {
        diff |= x ^ y;
    }
    diff == 0
}

/// Escape one string exactly as Python's `json.dumps` with
/// `ensure_ascii=True` (the default): `"`, `\`, control characters,
/// and every non-ASCII character become `\uXXXX` (with surrogate
/// pairs above the BMP).
pub fn json_escape(s: &str) -> String {
    let mut out = String::from("\"");
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\u{0008}' => out.push_str("\\b"),
            '\u{000C}' => out.push_str("\\f"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c if (c as u32) <= 0x7E => out.push(c),
            c => {
                let n = c as u32;
                if n <= 0xFFFF {
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

/// Canonical JSON for one flat string map: keys sorted, separators
/// `(",", ":")`, as `json.dumps(payload, sort_keys=True,
/// separators=(",", ":"))`.
pub fn canonical_json(pairs: &[(&str, &str)]) -> Vec<u8> {
    let mut sorted: Vec<(&str, &str)> = pairs.to_vec();
    sorted.sort_by(|a, b| a.0.cmp(b.0));
    let mut out = String::from("{");
    for (i, (k, v)) in sorted.iter().enumerate() {
        if i > 0 {
            out.push(',');
        }
        out.push_str(&json_escape(k));
        out.push(':');
        out.push_str(&json_escape(v));
    }
    out.push('}');
    out.into_bytes()
}

fn field<'a>(fields: &'a HashMap<String, String>, key: &str) -> &'a str {
    fields.get(key).map(|s| s.as_str()).unwrap_or("")
}

/// `_canonical_payload_v1`: title/spec/accept/branch/base/room.
pub fn canonical_payload_v1(fields: &HashMap<String, String>, spec: &str) -> Vec<u8> {
    canonical_json(&[
        ("title", field(fields, "title")),
        ("spec", spec),
        ("accept", field(fields, "accept")),
        ("branch", field(fields, "branch")),
        ("base", field(fields, "base")),
        ("room", field(fields, "room")),
    ])
}

/// `_canonical_payload_v2`: v1 fields plus the exact job instance
/// identity (jid/kid/created_at/expires_at/nonce), so a captured
/// signature cannot be transplanted onto another job.
pub fn canonical_payload_v2(
    jid: &str,
    kid: &str,
    fields: &HashMap<String, String>,
    spec: &str,
) -> Vec<u8> {
    canonical_json(&[
        ("jid", jid),
        ("kid", kid),
        ("title", field(fields, "title")),
        ("spec", spec),
        ("accept", field(fields, "accept")),
        ("branch", field(fields, "branch")),
        ("base", field(fields, "base")),
        ("room", field(fields, "room")),
        ("created_at", field(fields, "created_at")),
        ("expires_at", field(fields, "expires_at")),
        ("nonce", field(fields, "nonce")),
    ])
}

/// `_sign_job_v1`.
pub fn sign_job_v1(secret: &[u8], fields: &HashMap<String, String>, spec: &str) -> String {
    hex_digest(&hmac_sha256(secret, &canonical_payload_v1(fields, spec)))
}

/// `_sign_job_v2`.
pub fn sign_job_v2(
    secret: &[u8],
    jid: &str,
    kid: &str,
    fields: &HashMap<String, String>,
    spec: &str,
) -> String {
    hex_digest(&hmac_sha256(
        secret,
        &canonical_payload_v2(jid, kid, fields, spec),
    ))
}

// ---------------------------------------------------------------------------
// Artifact references (OS-094) and signed jobs (HMAC keyring).
// ---------------------------------------------------------------------------

/// `parse_artifact_ref`: `(job id, name, version)` for a well-formed
/// OS-083 reference `artifact:<job>/<name>@v<version>`, else `None`.
/// Name rules mirror `mos/artifact_store._validate_name`: a relative
/// POSIX path with no empty, `.` or `..` segments, no backslash, no
/// NUL. Version counts from 1, so v0 is malformed.
pub fn parse_artifact_ref(r: &str) -> Option<(String, String, u64)> {
    let rest = r.strip_prefix("artifact:")?;
    let slash = rest.find('/')?;
    let job = &rest[..slash];
    if job.is_empty()
        || !job
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '_' | '-'))
    {
        return None;
    }
    let tail = &rest[slash + 1..];
    // The regex `.+@v(\d+)$` is greedy: the LAST `@v<digits>` at the
    // end of the string wins as the version split.
    let mut split: Option<usize> = None;
    for (i, _) in tail.match_indices("@v") {
        let ver = &tail[i + 2..];
        if !ver.is_empty() && ver.bytes().all(|b| b.is_ascii_digit()) {
            split = Some(i);
        }
    }
    let at = split?;
    let name = &tail[..at];
    let version: u64 = tail[at + 2..].parse().ok()?;
    if version < 1 {
        return None;
    }
    if name.is_empty()
        || name.starts_with('/')
        || name.contains('\\')
        || name.contains('\0')
        || name.split('/').any(|p| p.is_empty() || p == "." || p == "..")
    {
        return None;
    }
    Some((job.to_string(), name.to_string(), version))
}

/// `_split_artifacts`: a comma-joined hash field back into refs.
pub fn split_artifacts(value: &str) -> Vec<String> {
    value
        .split(',')
        .map(|p| p.trim().to_string())
        .filter(|p| !p.is_empty())
        .collect()
}

/// `_validate_artifact_refs`: an error naming the first malformed
/// ref, else `None`. A malformed reference is a hard error, never a
/// warning: it can never resolve.
pub fn validate_artifact_refs(refs: &[String]) -> Option<String> {
    for r in refs {
        if parse_artifact_ref(r).is_none() {
            return Some(format!(
                "malformed artifact reference: {} (want artifact:<job>/<name>@v<version>)",
                python_repr(r)
            ));
        }
    }
    None
}

/// A parsed crew keyring: kid -> secret bytes, in file order.
pub struct Keyring {
    pub keys: Vec<(String, Vec<u8>)>,
    pub default_kid: String,
}

impl Keyring {
    pub fn get(&self, kid: &str) -> Option<&[u8]> {
        self.keys
            .iter()
            .find(|(k, _)| k == kid)
            .map(|(_, s)| s.as_slice())
    }

    pub fn kids_sorted(&self) -> Vec<String> {
        let mut kids: Vec<String> = self.keys.iter().map(|(k, _)| k.clone()).collect();
        kids.sort();
        kids
    }
}

/// `_read_keyring` over file content (the path is only used in error
/// text, as in Python). The first key signs; all keys verify, so
/// keys rotate by adding a new kid line. A legacy single-token file
/// still works as kid `"default"`.
pub fn parse_keyring(path: &str, content: &str) -> Result<Keyring, String> {
    let decoded = String::from_utf8_lossy(content.as_bytes());
    let lines: Vec<String> = decoded
        .lines()
        .map(|ln| ln.trim().to_string())
        .filter(|ln| !ln.is_empty())
        .collect();
    if lines.is_empty() {
        return Err(format!("secret file {} is empty", python_repr(path)));
    }
    let mut keys: Vec<(String, Vec<u8>)> = Vec::new();
    if lines.iter().any(|ln| ln.contains(':')) {
        for ln in &lines {
            if ln.matches(':').count() != 1 {
                return Err(format!(
                    "bad keyring line (want kid:secret): {}",
                    python_repr(ln)
                ));
            }
            let mut parts = ln.splitn(2, ':');
            let kid = parts.next().unwrap_or("").trim().to_string();
            let sec = parts.next().unwrap_or("").trim().to_string();
            if kid.is_empty() || sec.is_empty() || kid.chars().any(|c| c.is_whitespace()) {
                return Err(format!("bad keyring line: {}", python_repr(ln)));
            }
            keys.push((kid, sec.into_bytes()));
        }
    } else {
        if lines.len() > 1 {
            return Err(format!(
                "{}: multiple secrets need kid:secret lines",
                python_repr(path)
            ));
        }
        keys.push(("default".to_string(), lines[0].clone().into_bytes()));
    }
    let default_kid = keys[0].0.clone();
    Ok(Keyring { keys, default_kid })
}

/// Read a keyring file from disk (UTF-8, lossy, as Python decodes
/// with `"replace"`).
pub fn read_keyring_file(path: &str) -> Result<Keyring, String> {
    match std::fs::read(path) {
        Ok(bytes) => parse_keyring(path, &String::from_utf8_lossy(&bytes)),
        Err(e) => Err(format!(
            "cannot read secret file {}: {}",
            python_repr(path),
            e
        )),
    }
}

/// The four signature verdicts from `verify_job`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Verdict {
    Ok,
    Bad,
    Unsigned,
    Expired,
}

impl Verdict {
    pub fn as_str(&self) -> &'static str {
        match self {
            Verdict::Ok => "OK",
            Verdict::Bad => "BAD",
            Verdict::Unsigned => "UNSIGNED",
            Verdict::Expired => "EXPIRED",
        }
    }
}

/// Why `verify_job` failed instead of returning a verdict.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum VerifyError {
    UnknownJob(String),
    Malformed(String),
}

// ---------------------------------------------------------------------------
// The queue itself: one `JobQueue` owns a store, a clock, an identity,
// and the announcement sink. Every command returns the (code, stdout,
// stderr) triple the Python CLI prints.
// ---------------------------------------------------------------------------

/// The (exit code, stdout, stderr) triple of one command run.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CmdOutcome {
    pub code: i32,
    pub out: String,
    pub err: String,
}

impl CmdOutcome {
    fn new(code: i32, out: String, err: String) -> Self {
        CmdOutcome { code, out, err }
    }
}

fn push_line(buf: &mut String, text: &str) {
    buf.push_str(text);
    buf.push('\n');
}

/// Arguments to `post`. The spec is already resolved: a Python
/// `--spec -` (stdin) is read by the caller before calling.
pub struct PostArgs {
    pub title: String,
    pub spec: String,
    pub accept: String,
    pub branch: String,
    pub base: String,
    pub room: String,
    pub lease: i64,
    pub files: String,
    pub deps: String,
    pub req: String,
    pub max_attempts: Option<i64>,
    pub artifacts: String,
    pub secret_file: Option<String>,
    pub kid: String,
    pub expires: Option<i64>,
}

impl Default for PostArgs {
    fn default() -> Self {
        PostArgs {
            title: String::new(),
            spec: String::new(),
            accept: String::new(),
            branch: String::new(),
            base: String::new(),
            room: String::new(),
            lease: LEASE_DEFAULT as i64,
            files: String::new(),
            deps: String::new(),
            req: String::new(),
            max_attempts: None,
            artifacts: String::new(),
            secret_file: None,
            kid: String::new(),
            expires: None,
        }
    }
}

static NONCE_COUNTER: AtomicU64 = AtomicU64::new(0);

/// A 16-hex-char nonce. Python uses `secrets.token_hex(8)` (CSPRNG);
/// std has no CSPRNG, so this mixes wall time with a process counter.
/// The signature's security comes from the HMAC key, and the nonce
/// only needs to differ between posts; a caller that needs
/// cryptographic nonces should supply one via a future constructor
/// argument. Tests only require the nonce to be present.
fn fresh_nonce(now: u64) -> String {
    let n = NONCE_COUNTER.fetch_add(1, Ordering::Relaxed);
    format!("{:016x}", (now ^ n.wrapping_mul(0x9E3779B97F4A7C15)) & 0xFFFF_FFFF_FFFF_FFFF)
}

/// Normalize `--req` the way `mos/capabilities.find_for` reads it:
/// lowercase, comma-joined, deduped, order kept.
pub fn normalize_req(req: &str) -> String {
    let mut seen: Vec<String> = Vec::new();
    for part in req.split(',') {
        let norm = part.trim().to_lowercase();
        if !norm.is_empty() && !seen.contains(&norm) {
            seen.push(norm);
        }
    }
    seen.join(",")
}

/// `_valid_id`: all digits and numerically greater than zero
/// (`"01"` counts; `"0"` and `"00"` do not).
pub fn valid_id(jid: &str) -> bool {
    !jid.is_empty()
        && jid.bytes().all(|b| b.is_ascii_digit())
        && jid.bytes().any(|b| b != b'0')
}

/// The job queue: a store, a clock, an identity, and the recorded
/// wire announcements (`(bus key, "nick: text")`).
pub struct JobQueue<S: JobStore> {
    pub store: S,
    pub clock: Rc<dyn Clock>,
    pub ns: String,
    pub nick: String,
    pub host: String,
    pub announcements: Vec<(String, String)>,
}

impl<S: JobStore> JobQueue<S> {
    pub fn new(store: S, clock: Rc<dyn Clock>, ns: &str, nick: &str, host: &str) -> Self {
        JobQueue {
            store,
            clock,
            ns: ns.to_string(),
            nick: nick.to_string(),
            host: host.to_string(),
            announcements: Vec::new(),
        }
    }

    /// Act as a different agent (the Python tests' `set_nick`).
    pub fn set_nick(&mut self, nick: &str, host: &str) {
        self.nick = nick.to_string();
        self.host = host.to_string();
    }

    pub fn now(&self) -> u64 {
        self.clock.now_secs()
    }

    /// Announcements pushed to one bus key, in order.
    pub fn pushes_to(&self, key: &str) -> Vec<String> {
        self.announcements
            .iter()
            .filter(|(k, _)| k == key)
            .map(|(_, m)| m.clone())
            .collect()
    }

    // -- low-level store helpers -----------------------------------------

    /// `_hset` semantics: empty values are skipped (empty path
    /// segments 400 on Upstash REST); a call with nothing left is
    /// skipped entirely.
    fn hset(&mut self, key: &str, fields: &[(&str, &str)]) -> Result<(), StoreError> {
        let kept: Vec<(&str, &str)> = fields
            .iter()
            .copied()
            .filter(|(_, v)| !v.is_empty())
            .collect();
        if kept.is_empty() {
            return Ok(());
        }
        self.store.hset(key, &kept)
    }

    fn hdel(&mut self, key: &str, fields: &[&str]) -> Result<(), StoreError> {
        if fields.is_empty() {
            return Ok(());
        }
        self.store.hdel(key, fields)
    }

    /// Test/diagnostic aid: write a raw string key (mirrors the
    /// Python tests' direct `api_get("set/...")` tampering).
    pub fn store_set_raw(
        &mut self,
        key: &str,
        value: &str,
        ex_secs: Option<u64>,
    ) -> Result<bool, StoreError> {
        self.store.set(key, value, None, ex_secs)
    }

    /// Test/diagnostic aid: write raw hash fields.
    pub fn store_hset_raw(
        &mut self,
        key: &str,
        fields: &[(&str, &str)],
    ) -> Result<(), StoreError> {
        self.store.hset(key, fields)
    }

    /// Test/diagnostic aid: read a raw string key.
    pub fn store_get_raw(&mut self, key: &str) -> Option<String> {
        self.store.get(key).ok().flatten()
    }

    // -- reads ------------------------------------------------------------

    /// `job_get`: `(fields, spec)` or `(None, "")` for an unknown or
    /// invalid id. A spec-read failure yields `""`, as in Python.
    pub fn job_get(&mut self, jid: &str) -> (Option<HashMap<String, String>>, String) {
        if !valid_id(jid) {
            return (None, String::new());
        }
        let pairs = match self.store.hgetall(&job_key(&self.ns, jid)) {
            Ok(p) => p,
            Err(_) => return (None, String::new()),
        };
        if pairs.is_empty() {
            return (None, String::new());
        }
        let fields: HashMap<String, String> = pairs.into_iter().collect();
        let spec = self
            .store
            .get(&spec_key(&self.ns, jid))
            .ok()
            .flatten()
            .unwrap_or_default();
        (Some(fields), spec)
    }

    /// `nick_holder`: the instance holding a nick's claim, or `None`
    /// when unclaimed or on lookup failure. The stored value is
    /// URL-decoded once, as in Python.
    pub fn nick_holder(&mut self, nick: &str) -> Option<String> {
        match self.store.get(&nickclaim_key(nick)) {
            Ok(Some(v)) if !v.is_empty() => Some(url_unquote(&v)),
            _ => None,
        }
    }

    /// The nick-claim check from `relay_common`, minus its
    /// check-cache (a performance optimization; outcomes are
    /// unchanged). Returns `None` when the check itself failed
    /// (stay quiet), else `(held, holder)`.
    pub fn nick_claim(&mut self, _force: bool) -> Option<(bool, String)> {
        let key = nickclaim_key(&self.nick);
        let cur = match self.store.get(&key) {
            Ok(v) => v,
            Err(_) => return None,
        };
        match cur {
            None => {
                let ok = self
                    .store
                    .set(&key, &self.host, Some(SetMode::Nx), Some(NICKCLAIM_TTL))
                    .ok()?;
                if ok {
                    Some((true, self.host.clone()))
                } else {
                    // Lost the race; whoever won is the holder.
                    match self.store.get(&key).ok().flatten() {
                        Some(cur) if cur == self.host => Some((true, self.host.clone())),
                        Some(cur) => Some((false, url_unquote(&cur))),
                        None => Some((false, "?".to_string())),
                    }
                }
            }
            Some(cur) if cur == self.host => {
                let _ = self.store.expire(&key, NICKCLAIM_TTL);
                Some((true, self.host.clone()))
            }
            Some(cur) => Some((false, url_unquote(&cur))),
        }
    }

    /// `nick_conflict_holder`: the holder of our own nick when it is
    /// someone else, else `None`.
    pub fn nick_conflict_holder(&mut self) -> Option<String> {
        let nick = self.nick.clone();
        match self.nick_holder(&nick) {
            Some(holder) if holder != self.host => Some(holder),
            _ => None,
        }
    }

    /// `_creator_warning`: warn when the job poster's nick is now
    /// held by someone else.
    pub fn creator_warning(&mut self, h: &HashMap<String, String>) -> Option<String> {
        let poster = h.get("created_by")?;
        let host = h.get("created_host")?;
        if poster.is_empty() || host.is_empty() {
            return None;
        }
        let holder = self.nick_holder(poster)?;
        if holder != *host {
            return Some(format!(
                "WARNING: job was posted by '{}' on host '{}' but that nick is now claimed by '{}' — verify before working it",
                poster, host, holder
            ));
        }
        None
    }

    /// `_announce`: best-effort wire message; never fails the state
    /// change. A bad room name only warns on stderr, as in Python.
    fn announce(&mut self, room: &str, text: &str, err: &mut String) {
        match bus_key(room) {
            Ok(key) => {
                let msg = format!("{}: {}", self.nick, text);
                self.announcements.push((key, msg));
            }
            Err(e) => push_line(err, &format!("WARNING: announce failed ({})", e)),
        }
    }

    /// `_mutex_holder`: the claim mutex holder, `"?"` when the lookup
    /// fails (mirrors Python's exception fallback). `None` means the
    /// mutex is gone (lease expired).
    fn mutex_holder(&mut self, jid: &str) -> Option<String> {
        match self.store.get(&claim_key(&self.ns, jid)) {
            Ok(v) => v,
            Err(_) => Some("?".to_string()),
        }
    }

    /// `_requeue_fields`: reset a claimed job to open (lease expired
    /// or overseer override).
    fn requeue_fields(
        &mut self,
        jid: &str,
        room: &str,
        err: &mut String,
    ) -> Result<(), StoreError> {
        let key = job_key(&self.ns, jid);
        self.hdel(&key, &["claim", "claim_host", "claimed_at", "lease_until"])?;
        self.hset(&key, &[("status", "open")])?;
        let _ = self.store.del(&claim_key(&self.ns, jid));
        self.announce(room, &format!("REQUEUE:{}", jid), err);
        Ok(())
    }

    /// `_claim_or_requeue`: if the job is claimed but its mutex is
    /// gone, the lease expired: reopen it and return fresh fields.
    fn claim_or_requeue(
        &mut self,
        jid: &str,
        h: HashMap<String, String>,
        err: &mut String,
    ) -> Result<HashMap<String, String>, StoreError> {
        if h.get("status").map(|s| s.as_str()) == Some("claimed")
            && self.mutex_holder(jid).is_none()
        {
            let room = h.get("room").cloned().unwrap_or_default();
            self.requeue_fields(jid, &room, err)?;
            let (fresh, _) = self.job_get(jid);
            return Ok(fresh.unwrap_or(h));
        }
        Ok(h)
    }

    /// `verify_job`: `OK` / `BAD` / `UNSIGNED` / `EXPIRED`. Unknown
    /// ids and malformed expiry values are errors, as in Python
    /// (where `cmd_verify` turns them into exit code 2).
    pub fn verify_job(
        &mut self,
        jid: &str,
        keyring: &Keyring,
    ) -> Result<Verdict, VerifyError> {
        let (h, spec) = self.job_get(jid);
        let h = match h {
            Some(h) => h,
            None => return Err(VerifyError::UnknownJob(jid.to_string())),
        };
        let sig = match h.get("sig") {
            Some(s) if !s.is_empty() => s.clone(),
            _ => return Ok(Verdict::Unsigned),
        };
        let version = h.get("sig_v").map(|s| s.as_str()).unwrap_or("1");
        if version == "1" {
            let secret = match keyring.get("default") {
                Some(s) => s,
                None => return Ok(Verdict::Bad),
            };
            let good = ct_eq(&sign_job_v1(secret, &h, &spec), &sig);
            return Ok(if good { Verdict::Ok } else { Verdict::Bad });
        }
        if version != "2" {
            return Ok(Verdict::Bad);
        }
        let kid = h.get("sig_kid").map(|s| s.as_str()).unwrap_or("");
        let secret = match keyring.get(kid) {
            Some(s) => s,
            None => return Ok(Verdict::Bad),
        };
        let exp = h.get("expires_at").map(|s| s.as_str()).unwrap_or("");
        if !exp.is_empty() {
            let exp_secs: i64 = match exp.parse() {
                Ok(n) => n,
                Err(_) => {
                    return Err(VerifyError::Malformed(format!(
                        "invalid literal for int() with base 10: {}",
                        python_repr(exp)
                    )))
                }
            };
            if self.now() as i64 > exp_secs {
                return Ok(Verdict::Expired);
            }
        }
        let good = ct_eq(&sign_job_v2(secret, jid, kid, &h, &spec), &sig);
        Ok(if good { Verdict::Ok } else { Verdict::Bad })
    }

    fn require_claimer(
        h: &HashMap<String, String>,
        jid: &str,
        nick: &str,
    ) -> Result<(), CmdOutcome> {
        if h.get("claim").map(|s| s.as_str()) != Some(nick) {
            let claimer = h.get("claim").cloned().unwrap_or_else(|| "?".to_string());
            return Err(CmdOutcome::new(
                2,
                String::new(),
                format!(
                    "ERROR: job {} is claimed by '{}', not you\n",
                    jid, claimer
                ),
            ));
        }
        Ok(())
    }

    /// `_renew_lease`: renew the claim mutex; false on failure.
    /// `SET XX` first, then `SET NX` if the mutex expired out from
    /// under us.
    fn renew_lease(&mut self, jid: &str, lease: u64) -> bool {
        let key = claim_key(&self.ns, jid);
        let nick = self.nick.clone();
        let r = self
            .store
            .set(&key, &nick, Some(SetMode::Xx), Some(lease));
        let ok = match r {
            Ok(true) => true,
            _ => self
                .store
                .set(&key, &nick, Some(SetMode::Nx), Some(lease))
                .unwrap_or(false),
        };
        if !ok {
            return false;
        }
        let now = self.now();
        self.hset(
            &job_key(&self.ns, jid),
            &[
                ("lease_until", &now.wrapping_add(lease).to_string()),
                ("lease", &lease.to_string()),
            ],
        )
        .is_ok()
    }
}

// ---------------------------------------------------------------------------
// Commands: `cmd_post`, `cmd_list`, `cmd_show`, `cmd_attach`,
// `cmd_claim`, `cmd_heartbeat`, `cmd_progress`, `cmd_done`,
// `cmd_blocked`, `cmd_cancel`, `cmd_requeue`, `cmd_sweep`,
// `cmd_verify` from `os/jobs.py`, in that order.
// ---------------------------------------------------------------------------

/// Minimal JSON values, serialized with Python's `json.dumps`
/// defaults: separators `(", ", ": ")`, ASCII-escaped strings, keys
/// in insertion order. Used only by `list --json`.
enum JsonVal {
    Str(String),
    Int(i64),
    Null,
    Arr(Vec<JsonVal>),
    Obj(Vec<(String, JsonVal)>),
}

impl JsonVal {
    fn dump(&self, out: &mut String) {
        match self {
            JsonVal::Str(s) => out.push_str(&json_escape(s)),
            JsonVal::Int(n) => out.push_str(&n.to_string()),
            JsonVal::Null => out.push_str("null"),
            JsonVal::Arr(items) => {
                out.push('[');
                for (i, item) in items.iter().enumerate() {
                    if i > 0 {
                        out.push_str(", ");
                    }
                    item.dump(out);
                }
                out.push(']');
            }
            JsonVal::Obj(pairs) => {
                out.push('{');
                for (i, (k, v)) in pairs.iter().enumerate() {
                    if i > 0 {
                        out.push_str(", ");
                    }
                    out.push_str(&json_escape(k));
                    out.push_str(": ");
                    v.dump(out);
                }
                out.push('}');
            }
        }
    }
}

impl<S: JobStore> JobQueue<S> {
    /// `cmd_post`. The spec is already resolved (see [`PostArgs`]).
    /// Validation order mirrors Python exactly: empty spec, room,
    /// lease, artifact refs — all before any state change.
    pub fn post(&mut self, args: PostArgs) -> CmdOutcome {
        let mut out = String::new();
        let mut err = String::new();
        if args.spec.trim().is_empty() {
            push_line(&mut err, "ERROR: --spec is empty");
            return CmdOutcome::new(2, out, err);
        }
        let room = match clean_room(&args.room) {
            Ok(r) => r,
            Err(e) => {
                push_line(&mut err, &format!("ERROR: {}", e));
                return CmdOutcome::new(2, out, err);
            }
        };
        if args.lease < 60 {
            push_line(&mut err, "ERROR: --lease needs at least 60s");
            return CmdOutcome::new(2, out, err);
        }
        // OS-094: validate before any state change, so a bad ref
        // posts nothing.
        let post_artifacts = split_artifacts(&args.artifacts);
        if let Some(art_err) = validate_artifact_refs(&post_artifacts) {
            push_line(&mut err, &format!("ERROR: {}", art_err));
            return CmdOutcome::new(2, out, err);
        }
        let now = self.now();
        let jid = match self.store.incr(&seq_key(&self.ns)) {
            Ok(n) => n.to_string(),
            Err(e) => {
                push_line(&mut err, &format!("RELAY_ERROR: post failed ({})", e));
                return CmdOutcome::new(2, out, err);
            }
        };
        let mut fields: HashMap<String, String> = HashMap::new();
        fields.insert("title".to_string(), args.title.clone());
        fields.insert("room".to_string(), room.clone());
        fields.insert("branch".to_string(), args.branch.clone());
        fields.insert("base".to_string(), args.base.clone());
        fields.insert("accept".to_string(), args.accept.clone());
        fields.insert("status".to_string(), "open".to_string());
        fields.insert("lease".to_string(), args.lease.to_string());
        fields.insert("created_by".to_string(), self.nick.clone());
        fields.insert("created_host".to_string(), self.host.clone());
        fields.insert("created_at".to_string(), now.to_string());
        fields.insert("files".to_string(), args.files.clone());
        fields.insert("deps".to_string(), args.deps.clone());
        fields.insert("attempts".to_string(), "0".to_string());
        fields.insert("artifacts".to_string(), post_artifacts.join(","));
        // DSP-012: required capability names, normalized the same
        // way mos/capabilities.find_for reads them.
        fields.insert("req".to_string(), normalize_req(&args.req));
        fields.insert(
            "max_attempts".to_string(),
            args.max_attempts
                .map(|n| n.to_string())
                .unwrap_or_default(),
        );
        let key = job_key(&self.ns, &jid);
        let refs: Vec<(&str, &str)> = fields
            .iter()
            .map(|(k, v)| (k.as_str(), v.as_str()))
            .collect();
        let write_result = self
            .hset(&key, &refs)
            .and_then(|_| self.store.set(&spec_key(&self.ns, &jid), &args.spec, None, None))
            .and_then(|_| {
                self.store
                    .zadd(&index_key(&self.ns), now as i64, &jid)
            });
        if let Err(e) = write_result {
            push_line(&mut err, &format!("RELAY_ERROR: post failed ({})", e));
            return CmdOutcome::new(2, out, err);
        }
        // FND-009: a dep that does not resolve warns loudly but
        // never blocks the post — the poster may be racing a job
        // still posting.
        for dep in args.deps.split(',').map(|d| d.trim()).filter(|d| !d.is_empty()) {
            let (dep_h, _) = self.job_get(dep);
            if dep_h.is_none() {
                push_line(
                    &mut err,
                    &format!(
                        "WARNING: dep {} does not exist — posting job {} anyway",
                        dep, jid
                    ),
                );
            }
        }
        if let Some(secret_file) = &args.secret_file {
            let keyring = match read_keyring_file(secret_file) {
                Ok(k) => k,
                Err(e) => {
                    push_line(&mut err, &format!("ERROR: {}", e));
                    return CmdOutcome::new(2, out, err);
                }
            };
            let kid = if args.kid.is_empty() {
                keyring.default_kid.clone()
            } else {
                args.kid.clone()
            };
            let secret = match keyring.get(&kid) {
                Some(s) => s.to_vec(),
                None => {
                    push_line(
                        &mut err,
                        &format!(
                            "ERROR: unknown kid {} (keyring has: {})",
                            python_repr(&kid),
                            keyring.kids_sorted().join(", ")
                        ),
                    );
                    return CmdOutcome::new(2, out, err);
                }
            };
            if let Some(expires) = args.expires {
                if expires <= 0 {
                    push_line(
                        &mut err,
                        "ERROR: --expires needs a positive number of seconds",
                    );
                    return CmdOutcome::new(2, out, err);
                }
            }
            let nonce = fresh_nonce(now);
            let expires_at = match args.expires {
                Some(e) => (now as i64 + e).to_string(),
                None => String::new(),
            };
            let mut sig_fields = fields.clone();
            sig_fields.insert("nonce".to_string(), nonce.clone());
            sig_fields.insert("expires_at".to_string(), expires_at.clone());
            let sig = sign_job_v2(&secret, &jid, &kid, &sig_fields, &args.spec);
            let nick = self.nick.clone();
            let sig_refs: Vec<(&str, &str)> = [
                ("sig", sig.as_str()),
                ("sig_v", SIG_VERSION),
                ("sig_kid", kid.as_str()),
                ("signed_by", nick.as_str()),
                ("nonce", nonce.as_str()),
                ("expires_at", expires_at.as_str()),
            ]
            .to_vec();
            if let Err(e) = self.hset(&key, &sig_refs) {
                push_line(&mut err, &format!("RELAY_ERROR: signing failed ({})", e));
                return CmdOutcome::new(2, out, err);
            }
            push_line(&mut err, &format!("SIGNED {} kid={}", jid, kid));
        }
        self.announce(&room, &format!("JOB:{} {}", jid, args.title), &mut err);
        push_line(&mut out, &format!("JOB {}", jid));
        CmdOutcome::new(0, out, err)
    }

    /// `cmd_list`, text or `--json` (FND-013).
    pub fn list(&mut self, status_filter: &str, json: bool) -> CmdOutcome {
        let mut out = String::new();
        let mut err = String::new();
        let ids = match self.store.zrange(&index_key(&self.ns)) {
            Ok(ids) => ids,
            Err(e) => {
                push_line(&mut err, &format!("RELAY_ERROR: list failed ({})", e));
                return CmdOutcome::new(2, out, err);
            }
        };
        let mut rows: Vec<(String, String, String, String)> = Vec::new();
        let mut docs: Vec<JsonVal> = Vec::new();
        for jid in ids {
            let pairs = match self.store.hgetall(&job_key(&self.ns, &jid)) {
                Ok(p) => p,
                Err(_) => continue,
            };
            if pairs.is_empty() {
                continue;
            }
            let h: HashMap<String, String> = pairs.into_iter().collect();
            let status = h.get("status").cloned().unwrap_or_else(|| "?".to_string());
            if status_filter != "all" && status != status_filter {
                continue;
            }
            rows.push((
                jid.clone(),
                status.clone(),
                h.get("claim").cloned().unwrap_or_else(|| "-".to_string()),
                h.get("title").cloned().unwrap_or_default(),
            ));
            if json {
                let attempts = match h.get("attempts") {
                    None => Some(0),
                    Some(v) if v.is_empty() => None,
                    Some(v) => v.trim().parse::<i64>().ok(),
                };
                let claim = match h.get("claim") {
                    Some(v) if !v.is_empty() => JsonVal::Str(v.clone()),
                    _ => JsonVal::Null,
                };
                let opt_int = |v: Option<&String>| match v {
                    None => JsonVal::Null,
                    Some(s) if s.is_empty() => JsonVal::Null,
                    Some(s) => match s.trim().parse::<i64>() {
                        Ok(n) => JsonVal::Int(n),
                        Err(_) => JsonVal::Null,
                    },
                };
                docs.push(JsonVal::Obj(vec![
                    ("id".to_string(), JsonVal::Str(jid.clone())),
                    (
                        "title".to_string(),
                        JsonVal::Str(h.get("title").cloned().unwrap_or_default()),
                    ),
                    ("status".to_string(), JsonVal::Str(status.clone())),
                    ("claim".to_string(), claim),
                    (
                        "files".to_string(),
                        JsonVal::Str(h.get("files").cloned().unwrap_or_default()),
                    ),
                    (
                        "deps".to_string(),
                        JsonVal::Str(h.get("deps").cloned().unwrap_or_default()),
                    ),
                    (
                        "artifacts".to_string(),
                        JsonVal::Arr(
                            split_artifacts(h.get("artifacts").map(|s| s.as_str()).unwrap_or(""))
                                .into_iter()
                                .map(JsonVal::Str)
                                .collect(),
                        ),
                    ),
                    (
                        "req".to_string(),
                        JsonVal::Str(h.get("req").cloned().unwrap_or_default()),
                    ),
                    (
                        "attempts".to_string(),
                        match attempts {
                            Some(n) => JsonVal::Int(n),
                            None => JsonVal::Null,
                        },
                    ),
                    (
                        "lease_until".to_string(),
                        opt_int(h.get("lease_until")),
                    ),
                    (
                        "last_progress_at".to_string(),
                        opt_int(h.get("last_progress_at")),
                    ),
                ]));
            }
        }
        if json {
            let mut doc = String::new();
            JsonVal::Arr(docs).dump(&mut doc);
            push_line(&mut out, &doc);
            return CmdOutcome::new(0, out, err);
        }
        if rows.is_empty() {
            push_line(&mut out, "NO_JOBS");
            return CmdOutcome::new(0, out, err);
        }
        push_line(
            &mut out,
            &format!("{:<6}{:<10}{:<12}TITLE", "ID", "STATUS", "CLAIM"),
        );
        for (jid, status, claim, title) in rows {
            push_line(
                &mut out,
                &format!("{:<6}{:<10}{:<12}{}", jid, status, claim, title),
            );
        }
        CmdOutcome::new(0, out, err)
    }

    /// `cmd_show`: the job's set fields in fixed order, then the spec.
    pub fn show(&mut self, jid: &str) -> CmdOutcome {
        let mut out = String::new();
        let mut err = String::new();
        let (h, spec) = self.job_get(jid);
        let h = match h {
            Some(h) => h,
            None => {
                push_line(&mut err, &format!("ERROR: no such job: {}", jid));
                return CmdOutcome::new(2, out, err);
            }
        };
        for f in [
            "title", "status", "room", "branch", "base", "accept", "files", "deps",
            "artifacts", "req", "attempts", "max_attempts", "last_progress_at",
            "last_heartbeat_at", "claim", "claim_host", "claimed_at", "lease_until",
            "result_commit", "note", "created_by", "created_host", "created_at",
            "lease", "signed_by", "sig_v", "sig_kid", "expires_at", "nonce",
        ] {
            if let Some(v) = h.get(f) {
                if !v.is_empty() {
                    push_line(&mut out, &format!("{}: {}", f, v));
                }
            }
        }
        if let Some(w) = self.creator_warning(&h) {
            push_line(&mut err, &w);
        }
        push_line(&mut out, "--- spec ---");
        push_line(&mut out, &spec);
        CmdOutcome::new(0, out, err)
    }

    /// `cmd_attach` (OS-094): append artifact refs, deduped. No
    /// claimer gate: a resuming worker, the overseer, or a driver
    /// process may attach.
    pub fn attach(&mut self, jid: &str, refs: &[String]) -> CmdOutcome {
        let mut out = String::new();
        let mut err = String::new();
        let (h, _) = self.job_get(jid);
        let h = match h {
            Some(h) => h,
            None => {
                push_line(&mut err, &format!("ERROR: no such job: {}", jid));
                return CmdOutcome::new(2, out, err);
            }
        };
        let refs: Vec<String> = refs
            .iter()
            .map(|r| r.trim().to_string())
            .filter(|r| !r.is_empty())
            .collect();
        if let Some(art_err) = validate_artifact_refs(&refs) {
            push_line(&mut err, &format!("ERROR: {}", art_err));
            return CmdOutcome::new(2, out, err);
        }
        let existing = split_artifacts(h.get("artifacts").map(|s| s.as_str()).unwrap_or(""));
        // Note: like Python, this dedupes against the stored list
        // only; a repeated ref inside one call is stored twice.
        let added: Vec<String> = refs
            .iter()
            .filter(|r| !existing.contains(r))
            .cloned()
            .collect();
        if !added.is_empty() {
            let mut joined = existing.clone();
            joined.extend(added.iter().cloned());
            let key = job_key(&self.ns, jid);
            if let Err(e) = self.hset(&key, &[("artifacts", &joined.join(","))]) {
                push_line(&mut err, &format!("RELAY_ERROR: attach failed ({})", e));
                return CmdOutcome::new(2, out, err);
            }
            push_line(&mut out, &format!("ATTACHED {} {}", jid, added.join(",")));
        } else {
            push_line(&mut out, &format!("ATTACHED {} (already present)", jid));
        }
        CmdOutcome::new(0, out, err)
    }

    /// `cmd_claim`: atomic claim via `SET NX`; exactly one worker
    /// wins the race. With `--secret-file`, a BAD or EXPIRED
    /// signature refuses loudly (exit 1, REJECTED alert).
    pub fn claim(
        &mut self,
        jid: &str,
        room_override: &str,
        lease: i64,
        secret_file: Option<&str>,
    ) -> CmdOutcome {
        let mut out = String::new();
        let mut err = String::new();
        let (h, _) = self.job_get(jid);
        let mut h = match h {
            Some(h) => h,
            None => {
                push_line(&mut err, &format!("ERROR: no such job: {}", jid));
                return CmdOutcome::new(2, out, err);
            }
        };
        if let Some(secret_path) = secret_file {
            if h.get("sig").map(|s| !s.is_empty()).unwrap_or(false) {
                let keyring = match read_keyring_file(secret_path) {
                    Ok(k) => k,
                    Err(e) => {
                        push_line(&mut err, &format!("ERROR: {}", e));
                        return CmdOutcome::new(2, out, err);
                    }
                };
                match self.verify_job(jid, &keyring) {
                    Ok(verdict @ (Verdict::Bad | Verdict::Expired)) => {
                        let room = if !room_override.is_empty() {
                            room_override.to_string()
                        } else {
                            h.get("room").cloned().unwrap_or_default()
                        };
                        let signed_by = h
                            .get("signed_by")
                            .cloned()
                            .unwrap_or_else(|| "?".to_string());
                        let nick = self.nick.clone();
                        self.announce(
                            &room,
                            &format!(
                                "REJECTED:{} {} signed_by={} rejected_by={}",
                                jid,
                                verdict.as_str(),
                                signed_by,
                                nick
                            ),
                            &mut err,
                        );
                        push_line(
                            &mut err,
                            &format!(
                                "ERROR: job {} signature {} — not claiming",
                                jid,
                                verdict.as_str()
                            ),
                        );
                        return CmdOutcome::new(1, out, err);
                    }
                    Ok(_) => {}
                    Err(VerifyError::UnknownJob(_)) => {
                        // Cannot happen: the job was just read. Treat
                        // as a transport failure, as Python's generic
                        // handler would.
                        push_line(&mut err, "RELAY_ERROR: verify failed (job vanished)");
                        return CmdOutcome::new(2, out, err);
                    }
                    Err(VerifyError::Malformed(m)) => {
                        push_line(&mut err, &format!("RELAY_ERROR: verify failed ({})", m));
                        return CmdOutcome::new(2, out, err);
                    }
                }
            } else {
                push_line(
                    &mut err,
                    &format!(
                        "WARNING: job {} is unsigned — claiming without verification",
                        jid
                    ),
                );
            }
        }
        match self.claim_or_requeue(jid, h, &mut err) {
            Ok(fresh) => h = fresh,
            Err(e) => {
                push_line(&mut err, &format!("RELAY_ERROR: claim failed ({})", e));
                return CmdOutcome::new(2, out, err);
            }
        }
        if h.get("status").map(|s| s.as_str()) != Some("open") {
            let status = h.get("status").cloned().unwrap_or_default();
            let mut msg = format!("ERROR: job {} is {}", jid, status);
            if status == "claimed" {
                msg.push_str(&format!(
                    " (claimed by {})",
                    h.get("claim").cloned().unwrap_or_default()
                ));
            }
            push_line(&mut err, &msg);
            return CmdOutcome::new(2, out, err);
        }
        if lease < 60 {
            push_line(&mut err, "ERROR: --lease needs at least 60s");
            return CmdOutcome::new(2, out, err);
        }
        let claim_key_str = claim_key(&self.ns, jid);
        let nick = self.nick.clone();
        let won = match self.store.set(
            &claim_key_str,
            &nick,
            Some(SetMode::Nx),
            Some(lease as u64),
        ) {
            Ok(w) => w,
            Err(e) => {
                push_line(&mut err, &format!("RELAY_ERROR: claim failed ({})", e));
                return CmdOutcome::new(2, out, err);
            }
        };
        if !won {
            let holder = self.mutex_holder(jid).unwrap_or_else(|| "?".to_string());
            push_line(
                &mut err,
                &format!("ERROR: lost the race — job {} claimed by '{}'", jid, holder),
            );
            return CmdOutcome::new(2, out, err);
        }
        let now = self.now();
        let key = job_key(&self.ns, jid);
        let owned: Vec<(String, String)> = vec![
            ("status".to_string(), "claimed".to_string()),
            ("claim".to_string(), nick.clone()),
            ("claim_host".to_string(), self.host.clone()),
            ("claimed_at".to_string(), now.to_string()),
            ("lease_until".to_string(), (now + lease as u64).to_string()),
            ("lease".to_string(), lease.to_string()),
        ];
        let refs: Vec<(&str, &str)> = owned
            .iter()
            .map(|(k, v)| (k.as_str(), v.as_str()))
            .collect();
        if let Err(e) = self.hset(&key, &refs) {
            // Roll back the mutex so the job stays open and
            // claimable instead of claimed-but-unworkable until
            // the lease expires. Best-effort: never mask the
            // original error.
            let _ = self.store.del(&claim_key_str);
            push_line(&mut err, &format!("RELAY_ERROR: claim record failed ({})", e));
            return CmdOutcome::new(2, out, err);
        }
        if let Some(w) = self.creator_warning(&h) {
            push_line(&mut err, &w);
        }
        let room = if !room_override.is_empty() {
            room_override.to_string()
        } else {
            h.get("room").cloned().unwrap_or_default()
        };
        self.announce(&room, &format!("CLAIM:{} by {}", jid, nick), &mut err);
        push_line(&mut out, &format!("CLAIMED {} by {}", jid, nick));
        CmdOutcome::new(0, out, err)
    }

    /// `cmd_heartbeat`: renew the claim lease. `lease_opt` of 0
    /// keeps the current lease, as the Python `--lease 0` default.
    pub fn heartbeat(&mut self, jid: &str, lease_opt: i64) -> CmdOutcome {
        let mut out = String::new();
        let mut err = String::new();
        let (h, _) = self.job_get(jid);
        let h = match h {
            Some(h) => h,
            None => {
                push_line(&mut err, &format!("ERROR: no such job: {}", jid));
                return CmdOutcome::new(2, out, err);
            }
        };
        if let Err(outcome) = Self::require_claimer(&h, jid, &self.nick.clone()) {
            return outcome;
        }
        let lease = if lease_opt != 0 {
            lease_opt as u64
        } else {
            h.get("lease")
                .and_then(|v| v.parse::<u64>().ok())
                .unwrap_or(LEASE_DEFAULT)
        };
        if self.renew_lease(jid, lease) {
            // FND-011: heartbeat timestamp is advisory — a failed
            // stamp must never fail the lease renewal itself.
            let now = self.now().to_string();
            let key = job_key(&self.ns, jid);
            let _ = self.hset(&key, &[("last_heartbeat_at", &now)]);
            push_line(&mut out, &format!("LEASE_RENEWED {} {}s", jid, lease));
            CmdOutcome::new(0, out, err)
        } else {
            push_line(&mut err, &format!("ERROR: lost the lease on job {}", jid));
            CmdOutcome::new(2, out, err)
        }
    }

    /// `cmd_progress`: note progress and renew the lease.
    pub fn progress(&mut self, jid: &str, note: &str, room_override: &str) -> CmdOutcome {
        let mut out = String::new();
        let mut err = String::new();
        let (h, _) = self.job_get(jid);
        let h = match h {
            Some(h) => h,
            None => {
                push_line(&mut err, &format!("ERROR: no such job: {}", jid));
                return CmdOutcome::new(2, out, err);
            }
        };
        if let Err(outcome) = Self::require_claimer(&h, jid, &self.nick.clone()) {
            return outcome;
        }
        let lease = h
            .get("lease")
            .and_then(|v| v.parse::<u64>().ok())
            .unwrap_or(LEASE_DEFAULT);
        if !self.renew_lease(jid, lease) {
            push_line(&mut err, &format!("ERROR: lost the lease on job {}", jid));
            return CmdOutcome::new(2, out, err);
        }
        let now = self.now().to_string();
        let key = job_key(&self.ns, jid);
        if let Err(e) = self.hset(&key, &[("note", note), ("last_progress_at", &now)]) {
            push_line(&mut err, &format!("RELAY_ERROR: note save failed ({})", e));
            return CmdOutcome::new(2, out, err);
        }
        let room = if !room_override.is_empty() {
            room_override.to_string()
        } else {
            h.get("room").cloned().unwrap_or_default()
        };
        self.announce(&room, &format!("PROGRESS:{} {}", jid, note), &mut err);
        push_line(&mut out, &format!("PROGRESS {}", jid));
        CmdOutcome::new(0, out, err)
    }

    /// `cmd_done`: finish with a commit hash.
    pub fn done(
        &mut self,
        jid: &str,
        commit: &str,
        note: &str,
        room_override: &str,
    ) -> CmdOutcome {
        let mut out = String::new();
        let mut err = String::new();
        let (h, _) = self.job_get(jid);
        let h = match h {
            Some(h) => h,
            None => {
                push_line(&mut err, &format!("ERROR: no such job: {}", jid));
                return CmdOutcome::new(2, out, err);
            }
        };
        if let Err(outcome) = Self::require_claimer(&h, jid, &self.nick.clone()) {
            return outcome;
        }
        let now = self.now().to_string();
        let key = job_key(&self.ns, jid);
        let result = self
            .hset(
                &key,
                &[
                    ("status", "done"),
                    ("result_commit", commit),
                    ("note", note),
                    ("done_at", &now),
                ],
            )
            .and_then(|_| {
                self.hdel(
                    &key,
                    &["claim", "claim_host", "claimed_at", "lease_until"],
                )
            })
            .and_then(|_| self.store.del(&claim_key(&self.ns, jid)));
        if let Err(e) = result {
            push_line(&mut err, &format!("RELAY_ERROR: done failed ({})", e));
            return CmdOutcome::new(2, out, err);
        }
        let room = if !room_override.is_empty() {
            room_override.to_string()
        } else {
            h.get("room").cloned().unwrap_or_default()
        };
        self.announce(&room, &format!("DONE:{} {}", jid, commit), &mut err);
        push_line(&mut out, &format!("DONE {} {}", jid, commit));
        CmdOutcome::new(0, out, err)
    }

    /// `cmd_blocked`: mark blocked and release the claim.
    pub fn blocked(
        &mut self,
        jid: &str,
        reason: &str,
        room_override: &str,
    ) -> CmdOutcome {
        let mut out = String::new();
        let mut err = String::new();
        let (h, _) = self.job_get(jid);
        let h = match h {
            Some(h) => h,
            None => {
                push_line(&mut err, &format!("ERROR: no such job: {}", jid));
                return CmdOutcome::new(2, out, err);
            }
        };
        if let Err(outcome) = Self::require_claimer(&h, jid, &self.nick.clone()) {
            return outcome;
        }
        let now = self.now().to_string();
        let key = job_key(&self.ns, jid);
        let result = self
            .hset(
                &key,
                &[
                    ("status", "blocked"),
                    ("note", reason),
                    ("blocked_at", &now),
                ],
            )
            .and_then(|_| {
                self.hdel(
                    &key,
                    &["claim", "claim_host", "claimed_at", "lease_until"],
                )
            })
            .and_then(|_| self.store.del(&claim_key(&self.ns, jid)));
        if let Err(e) = result {
            push_line(&mut err, &format!("RELAY_ERROR: blocked failed ({})", e));
            return CmdOutcome::new(2, out, err);
        }
        let room = if !room_override.is_empty() {
            room_override.to_string()
        } else {
            h.get("room").cloned().unwrap_or_default()
        };
        self.announce(&room, &format!("BLOCKED:{} {}", jid, reason), &mut err);
        push_line(&mut out, &format!("BLOCKED {}", jid));
        CmdOutcome::new(0, out, err)
    }

    /// `cmd_cancel` (DSP-011): only an open job can be cancelled.
    /// No bus announcement: the dispatch undo report is the record.
    pub fn cancel(&mut self, jid: &str, reason: &str) -> CmdOutcome {
        let mut out = String::new();
        let mut err = String::new();
        let (h, _) = self.job_get(jid);
        let h = match h {
            Some(h) => h,
            None => {
                push_line(&mut err, &format!("ERROR: no such job: {}", jid));
                return CmdOutcome::new(2, out, err);
            }
        };
        if h.get("status").map(|s| s.as_str()) != Some("open") {
            let status = h.get("status").cloned().unwrap_or_default();
            push_line(
                &mut err,
                &format!(
                    "ERROR: job {} is {}, not open (only an open job can be cancelled)",
                    jid, status
                ),
            );
            return CmdOutcome::new(2, out, err);
        }
        let now = self.now().to_string();
        let key = job_key(&self.ns, jid);
        if let Err(e) = self.hset(
            &key,
            &[
                ("status", "cancelled"),
                ("note", reason),
                ("cancelled_at", &now),
            ],
        ) {
            push_line(&mut err, &format!("RELAY_ERROR: cancel failed ({})", e));
            return CmdOutcome::new(2, out, err);
        }
        push_line(&mut out, &format!("CANCELLED {}", jid));
        CmdOutcome::new(0, out, err)
    }

    /// `cmd_requeue`: reopen a lease-expired claim. FND-010: the
    /// attempt budget is enforced here — a job that burned its
    /// budget is failed-final, not open.
    pub fn requeue(&mut self, jid: &str, room_override: &str) -> CmdOutcome {
        let mut out = String::new();
        let mut err = String::new();
        let (h, _) = self.job_get(jid);
        let h = match h {
            Some(h) => h,
            None => {
                push_line(&mut err, &format!("ERROR: no such job: {}", jid));
                return CmdOutcome::new(2, out, err);
            }
        };
        if h.get("status").map(|s| s.as_str()) != Some("claimed") {
            let status = h.get("status").cloned().unwrap_or_default();
            push_line(
                &mut err,
                &format!("ERROR: job {} is {}, not claimed", jid, status),
            );
            return CmdOutcome::new(2, out, err);
        }
        if self.mutex_holder(jid).is_some() {
            let claimer = h.get("claim").cloned().unwrap_or_else(|| "None".to_string());
            push_line(
                &mut err,
                &format!(
                    "ERROR: lease on job {} still active (held by '{}')",
                    jid, claimer
                ),
            );
            return CmdOutcome::new(2, out, err);
        }
        let attempts: i64 = h
            .get("attempts")
            .and_then(|v| v.parse::<i64>().ok())
            .unwrap_or(0);
        let max_attempts = h.get("max_attempts").cloned().unwrap_or_default();
        if !max_attempts.is_empty() {
            if let Ok(max) = max_attempts.parse::<i64>() {
                if attempts >= max {
                    let key = job_key(&self.ns, jid);
                    let result = self
                        .hset(&key, &[("status", "failed-final")])
                        .and_then(|_| {
                            self.hdel(
                                &key,
                                &["claim", "claim_host", "claimed_at", "lease_until"],
                            )
                        });
                    if let Err(e) = result {
                        push_line(
                            &mut err,
                            &format!("RELAY_ERROR: failed-final failed ({})", e),
                        );
                        return CmdOutcome::new(2, out, err);
                    }
                    push_line(
                        &mut err,
                        &format!(
                            "ERROR: job {} reached max_attempts ({}) — marked failed-final, not requeued",
                            jid, max_attempts
                        ),
                    );
                    return CmdOutcome::new(2, out, err);
                }
            }
            // An unparseable stored max_attempts cannot come from
            // `post` (which writes an integer or nothing); treat it
            // as unlimited rather than failing the requeue.
        }
        let key = job_key(&self.ns, jid);
        if let Err(e) = self.hset(&key, &[("attempts", &(attempts + 1).to_string())]) {
            push_line(
                &mut err,
                &format!("RELAY_ERROR: attempts update failed ({})", e),
            );
            return CmdOutcome::new(2, out, err);
        }
        let room = if !room_override.is_empty() {
            room_override.to_string()
        } else {
            h.get("room").cloned().unwrap_or_default()
        };
        if let Err(e) = self.requeue_fields(jid, &room, &mut err) {
            push_line(&mut err, &format!("RELAY_ERROR: requeue failed ({})", e));
            return CmdOutcome::new(2, out, err);
        }
        push_line(&mut out, &format!("REQUEUED {}", jid));
        CmdOutcome::new(0, out, err)
    }

    /// `cmd_sweep`: requeue all lease-expired claims, then REPORT
    /// dependency-dead candidates (FND-012: the scan never mutates
    /// a hash). Missing deps are not flagged here; the watchdog's
    /// missing-dep detector owns those.
    pub fn sweep(&mut self, room_override: &str) -> CmdOutcome {
        let mut out = String::new();
        let mut err = String::new();
        let ids = match self.store.zrange(&index_key(&self.ns)) {
            Ok(ids) => ids,
            Err(e) => {
                push_line(&mut err, &format!("RELAY_ERROR: sweep failed ({})", e));
                return CmdOutcome::new(2, out, err);
            }
        };
        let mut n = 0;
        for jid in &ids {
            let (h, _) = self.job_get(jid);
            let h = match h {
                Some(h) => h,
                None => continue,
            };
            if h.get("status").map(|s| s.as_str()) == Some("claimed")
                && self.mutex_holder(jid).is_none()
            {
                let room = if !room_override.is_empty() {
                    room_override.to_string()
                } else {
                    h.get("room").cloned().unwrap_or_default()
                };
                match self.requeue_fields(jid, &room, &mut err) {
                    Ok(()) => {
                        push_line(&mut out, &format!("REQUEUED {}", jid));
                        n += 1;
                    }
                    Err(e) => {
                        push_line(
                            &mut err,
                            &format!("WARNING: requeue {} failed ({})", jid, e),
                        );
                    }
                }
            }
        }
        let mut dep_dead = 0;
        for jid in &ids {
            let (h, _) = self.job_get(jid);
            let h = match h {
                Some(h) => h,
                None => continue,
            };
            let status = h.get("status").map(|s| s.as_str()).unwrap_or("");
            if status != "open" && status != "claimed" {
                continue;
            }
            let deps = h.get("deps").cloned().unwrap_or_default();
            for dep in deps.split(',').map(|d| d.trim()).filter(|d| !d.is_empty()) {
                let (dep_h, _) = self.job_get(dep);
                if let Some(dep_h) = dep_h {
                    let dep_status = dep_h.get("status").map(|s| s.as_str()).unwrap_or("");
                    if dep_status == "blocked" || dep_status == "failed-final" {
                        push_line(
                            &mut out,
                            &format!("DEP_DEAD {} dep {} {}", jid, dep, dep_status),
                        );
                        dep_dead += 1;
                    }
                }
            }
        }
        if n == 0 && dep_dead == 0 {
            push_line(&mut out, "SWEEP_CLEAN");
        }
        CmdOutcome::new(0, out, err)
    }

    /// `cmd_verify`: print the verdict; exit 0 only on OK.
    pub fn verify(&mut self, jid: &str, secret_file: &str) -> CmdOutcome {
        let mut out = String::new();
        let mut err = String::new();
        let keyring = match read_keyring_file(secret_file) {
            Ok(k) => k,
            Err(e) => {
                push_line(&mut err, &format!("ERROR: {}", e));
                return CmdOutcome::new(2, out, err);
            }
        };
        match self.verify_job(jid, &keyring) {
            Ok(v) => {
                push_line(&mut out, v.as_str());
                CmdOutcome::new(if v == Verdict::Ok { 0 } else { 1 }, out, err)
            }
            Err(VerifyError::UnknownJob(_)) => {
                push_line(&mut err, &format!("ERROR: no such job: {}", jid));
                CmdOutcome::new(2, out, err)
            }
            Err(VerifyError::Malformed(m)) => {
                push_line(&mut err, &format!("ERROR: {}", m));
                CmdOutcome::new(2, out, err)
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Brief environment surface: `environment_jobs_record` and
// `environment_lines` from `os/intel/brief.py` (OS-103), the jobs
// quarter of the boot-brief environment record. The rest of
// `brief.py` (the composer itself, bus/budget quarters) belongs to
// the intel batches; only the jobs input and the four lines are
// ported here, because this batch's test file pins them.
// ---------------------------------------------------------------------------

/// A dynamically-typed job-record value, mirroring Python's dict
/// values: strings, ints, and bools are distinct (a bool id is NOT
/// carried; a bool is not an int here, as in Python's `isinstance`
/// checks).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Value {
    Str(String),
    Int(i64),
    Bool(bool),
}

/// One entry of a jobs list passed to [`environment_jobs_record`]:
/// either a dict or something else (skipped, never guessed).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EnvInput {
    Dict(HashMap<String, Value>),
    Other,
}

/// `environment_jobs_record`: the "jobs" part of an environment
/// record, read from a stated jobs list. Only claimed jobs count
/// as work in progress: an entry counts only when its status is
/// `"claimed"` and it carries a non-empty string claim nick and a
/// non-empty string title. The id is carried only when it is a
/// non-empty string or an int, and is otherwise left out rather
/// than invented. Returns `None` when the input is not a list, so
/// the caller leaves "jobs" out of the record and the Working now
/// line reads not reported; an empty list returns `[]` and renders
/// as nobody holds a claimed job. Never raises.
pub fn environment_jobs_record(
    jobs: Option<&[EnvInput]>,
) -> Option<Vec<HashMap<String, Value>>> {
    let jobs = jobs?;
    let mut claimed = Vec::new();
    for job in jobs {
        let dict = match job {
            EnvInput::Dict(d) => d,
            EnvInput::Other => continue,
        };
        if dict.get("status") != Some(&Value::Str("claimed".to_string())) {
            continue;
        }
        let nick = match dict.get("claim") {
            Some(Value::Str(s)) if !s.is_empty() => s.clone(),
            _ => continue,
        };
        let title = match dict.get("title") {
            Some(Value::Str(s)) if !s.is_empty() => s.clone(),
            _ => continue,
        };
        let mut entry: HashMap<String, Value> = HashMap::new();
        entry.insert("title".to_string(), Value::Str(title));
        entry.insert("status".to_string(), Value::Str("claimed".to_string()));
        entry.insert("claim".to_string(), Value::Str(nick));
        match dict.get("id") {
            Some(Value::Str(s)) if !s.is_empty() => {
                entry.insert("id".to_string(), Value::Str(s.clone()));
            }
            Some(Value::Int(n)) => {
                entry.insert("id".to_string(), Value::Int(*n));
            }
            _ => {}
        }
        claimed.push(entry);
    }
    Some(claimed)
}

/// One part of an environment record for [`environment_lines`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EnvRepo {
    pub branch: String,
    pub commit: String,
    /// `dirty == 0` renders "clean"; a positive int renders its
    /// uncommitted-file count; anything else renders nothing.
    pub dirty: Option<i64>,
    pub as_of: Option<i64>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EnvBus {
    pub rooms: Vec<String>,
    pub messages: Option<i64>,
    pub as_of: Option<i64>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EnvBudget {
    pub lane: Option<String>,
    pub spent: Option<i64>,
    pub cap: Option<i64>,
    pub remaining: Option<i64>,
    pub as_of: Option<i64>,
}

/// An environment record. `jobs: None` means the key is absent
/// (Working now reads not reported); `Some(vec)` renders the
/// claimed jobs, or "nobody holds a claimed job" when empty.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct EnvRecord {
    pub repo: Option<EnvRepo>,
    pub bus: Option<EnvBus>,
    pub jobs: Option<Vec<HashMap<String, Value>>>,
    pub budget: Option<EnvBudget>,
    pub as_of: Option<i64>,
}

fn days_from_civil(year: i64, month: u32, day: u32) -> i64 {
    // Howard Hinnant's civil-from-days inverse.
    let y = if month <= 2 { year - 1 } else { year };
    let era = if y >= 0 { y } else { y - 399 } / 400;
    let yoe = y - era * 400;
    let mp = ((month + 9) % 12) as i64;
    let doy = (153 * mp + 2) / 5 + day as i64 - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146097 + doe - 719468
}

fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719468;
    let era = if z >= 0 { z } else { z - 146096 } / 146097;
    let doe = z - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    (if m <= 2 { y + 1 } else { y }, m, d)
}

/// Weekday of a day count: 0 = Sunday. 1970-01-01 was a Thursday.
fn weekday_of_days(z: i64) -> i64 {
    (z + 4).rem_euclid(7)
}

fn nth_weekday_of_month(year: i64, month: u32, weekday: i64, n: i64) -> i64 {
    let first = days_from_civil(year, month, 1);
    let first_wd = weekday_of_days(first);
    let delta = (weekday - first_wd).rem_euclid(7);
    first + delta + (n - 1) * 7
}

/// US Eastern offset for a UTC timestamp: UTC-4 during daylight
/// time (second Sunday of March 07:00 UTC through first Sunday of
/// November 06:00 UTC), UTC-5 otherwise. This is the
/// `America/New_York` rule `zoneinfo` applies in Python.
fn eastern_offset_secs(utc_ts: i64) -> i64 {
    let days = utc_ts.div_euclid(86400);
    let (year, _, _) = civil_from_days(days);
    let dst_start =
        nth_weekday_of_month(year, 3, 0, 2) * 86400 + 7 * 3600;
    let dst_end =
        nth_weekday_of_month(year, 11, 0, 1) * 86400 + 6 * 3600;
    if utc_ts >= dst_start && utc_ts < dst_end {
        -4 * 3600
    } else {
        -5 * 3600
    }
}

/// `_format_brief_time`: a stored timestamp as `"YYYY-MM-DD HH:MM
/// ET"` in America/New_York, or `None` for a non-numeric stamp.
pub fn format_brief_time(ts: i64) -> String {
    let local = ts + eastern_offset_secs(ts);
    let days = local.div_euclid(86400);
    let secs_of_day = local.rem_euclid(86400);
    let (year, month, day) = civil_from_days(days);
    let hour = secs_of_day / 3600;
    let minute = (secs_of_day % 3600) / 60;
    format!(
        "{:04}-{:02}-{:02} {:02}:{:02} ET",
        year, month, day, hour, minute
    )
}

/// `_environment_age_label`: `" (as of ...)"` for a known time,
/// `" (snapshot time not reported)"` otherwise.
pub fn environment_age_label(as_of: Option<i64>) -> String {
    match as_of {
        Some(ts) => format!(" (as of {})", format_brief_time(ts)),
        None => " (snapshot time not reported)".to_string(),
    }
}

/// `environment_lines`: the four launch-environment lines for a
/// boot brief, in order: Repo, Bus, Working now, Budget. A missing
/// record or field is reported as not reported, never guessed; an
/// empty jobs list means nobody holds a claimed job, never a padded
/// name.
pub fn environment_lines(env: &EnvRecord) -> [String; 4] {
    let repo_line = match &env.repo {
        Some(repo) if !repo.branch.is_empty() && !repo.commit.is_empty() => {
            let tree = match repo.dirty {
                Some(0) => ", clean".to_string(),
                Some(d) if d > 0 => {
                    format!(
                        ", {} uncommitted file{}",
                        d,
                        if d != 1 { "s" } else { "" }
                    )
                }
                _ => String::new(),
            };
            format!(
                "Repo: {} at {}{}{}",
                repo.branch,
                repo.commit,
                tree,
                environment_age_label(repo.as_of)
            )
        }
        _ => "Repo state: not reported in this snapshot".to_string(),
    };
    let bus_line = match &env.bus {
        Some(bus) => {
            let rooms: Vec<&str> = bus
                .rooms
                .iter()
                .map(|r| r.as_str())
                .filter(|r| !r.is_empty())
                .collect();
            let mut parts: Vec<String> = Vec::new();
            if let Some(m) = bus.messages {
                parts.push(format!("{} messages", m));
            }
            if !rooms.is_empty() {
                parts.push(format!(
                    "in room{} {}",
                    if rooms.len() != 1 { "s" } else { "" },
                    rooms.join(", ")
                ));
            }
            if parts.is_empty() {
                "Bus state: not reported in this snapshot".to_string()
            } else {
                format!("Bus: {}{}", parts.join(" "), environment_age_label(bus.as_of))
            }
        }
        None => "Bus state: not reported in this snapshot".to_string(),
    };
    let working_line = match &env.jobs {
        None => "Working now: not reported in this snapshot".to_string(),
        Some(jobs) => {
            let mut claimed: Vec<String> = Vec::new();
            for job in jobs {
                if job.get("status") != Some(&Value::Str("claimed".to_string())) {
                    continue;
                }
                let nick = match job.get("claim") {
                    Some(Value::Str(s)) if !s.is_empty() => s,
                    _ => continue,
                };
                let title = match job.get("title") {
                    Some(Value::Str(s)) if !s.is_empty() => s,
                    _ => continue,
                };
                claimed.push(format!("{}: {}", nick, title));
            }
            if claimed.is_empty() {
                format!(
                    "Working now: nobody holds a claimed job in this snapshot{}",
                    environment_age_label(env.as_of)
                )
            } else {
                format!(
                    "Working now: {}{}",
                    claimed.join("; "),
                    environment_age_label(env.as_of)
                )
            }
        }
    };
    let budget_line = match &env.budget {
        Some(budget) => {
            let remaining = match budget.remaining {
                Some(r) => Some(r),
                None => match (budget.spent, budget.cap) {
                    (Some(s), Some(c)) => Some(c - s),
                    _ => None,
                },
            };
            match (&budget.lane, remaining) {
                (Some(lane), Some(r)) if !lane.is_empty() => {
                    let cap_part = match budget.cap {
                        Some(c) => format!(" of {} cap", c),
                        None => String::new(),
                    };
                    format!(
                        "Budget: {} lane: {} remaining{}{}",
                        lane,
                        r,
                        cap_part,
                        environment_age_label(budget.as_of)
                    )
                }
                _ => "Budget: not reported in this snapshot".to_string(),
            }
        }
        None => "Budget: not reported in this snapshot".to_string(),
    };
    [repo_line, bus_line, working_line, budget_line]
}

// ---------------------------------------------------------------------------
// Rust tests mirroring the Python test files, same name roots. One
// module per Python test file; test names mirror the Python test
// names. Where a Python test exercises a module owned by another
// batch (send/poll/watch/presence/DM rooms in test_claims.py, the
// brief composer in test_intel_brief_environment_jobs.py), the case
// is NOT faked here — it is listed in the completion report as
// out of B16 scope.
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU64, Ordering};

    const START: u64 = 1_700_000_000;

    fn test_queue() -> (Rc<FakeClock>, JobQueue<FakeStore>) {
        let clock = Rc::new(FakeClock::new(START));
        let store = FakeStore::new(clock.clone());
        let q = JobQueue::new(store, clock.clone(), "muse-bus:tjob", "tester", "host-a");
        (clock, q)
    }

    fn post_simple(q: &mut JobQueue<FakeStore>, title: &str, spec: &str) -> CmdOutcome {
        let mut args = PostArgs::default();
        args.title = title.to_string();
        args.spec = spec.to_string();
        q.post(args)
    }

    fn post_extra(
        q: &mut JobQueue<FakeStore>,
        title: &str,
        spec: &str,
        f: impl Fn(&mut PostArgs),
    ) -> CmdOutcome {
        let mut args = PostArgs::default();
        args.title = title.to_string();
        args.spec = spec.to_string();
        f(&mut args);
        q.post(args)
    }

    fn fields<S: JobStore>(q: &mut JobQueue<S>, jid: &str) -> HashMap<String, String> {
        let (h, _) = q.job_get(jid);
        h.expect("job must exist")
    }

    fn spec_of(q: &mut JobQueue<FakeStore>, jid: &str) -> String {
        let (_, spec) = q.job_get(jid);
        spec
    }

    static SECRET_COUNTER: AtomicU64 = AtomicU64::new(0);

    fn secret_file(content: &str) -> std::path::PathBuf {
        let n = SECRET_COUNTER.fetch_add(1, Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!(
            "os-jobs-test-{}-{}",
            std::process::id(),
            n
        ));
        std::fs::write(&path, content).expect("write secret file");
        path
    }

    fn value_dict(pairs: &[(&str, Value)]) -> HashMap<String, Value> {
        pairs
            .iter()
            .map(|(k, v)| (k.to_string(), v.clone()))
            .collect()
    }

    fn s(v: &str) -> Value {
        Value::Str(v.to_string())
    }

    // -- pure helpers --------------------------------------------------------

    mod pure_tests {
        use super::super::*;

        #[test]
        fn test_sha256_vectors() {
            assert_eq!(
                hex_digest(&sha256(b"")),
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            );
            assert_eq!(
                hex_digest(&sha256(b"abc")),
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
            );
        }

        #[test]
        fn test_canonical_v1_payload_and_signature() {
            // Vectors computed from Python's json.dumps + hmac.
            let mut fields = HashMap::new();
            fields.insert("title".to_string(), "T".to_string());
            assert_eq!(
                String::from_utf8(canonical_payload_v1(&fields, "s")).unwrap(),
                r#"{"accept":"","base":"","branch":"","room":"","spec":"s","title":"T"}"#
            );
            assert_eq!(
                sign_job_v1(b"crew-secret-abc", &fields, "s"),
                "48971b55907bfe5f14d193c7db09f69081a6211cd36d8278d4d7836e950ff694"
            );
        }

        #[test]
        fn test_canonical_v2_payload_and_signature() {
            let mut fields = HashMap::new();
            fields.insert("title".to_string(), "T".to_string());
            fields.insert("created_at".to_string(), "1700000000".to_string());
            fields.insert("expires_at".to_string(), String::new());
            fields.insert("nonce".to_string(), "0123456789abcdef".to_string());
            assert_eq!(
                String::from_utf8(canonical_payload_v2("1", "default", &fields, "s"))
                    .unwrap(),
                r#"{"accept":"","base":"","branch":"","created_at":"1700000000","expires_at":"","jid":"1","kid":"default","nonce":"0123456789abcdef","room":"","spec":"s","title":"T"}"#
            );
            assert_eq!(
                sign_job_v2(b"crew-secret-abc", "1", "default", &fields, "s"),
                "c0417079971137b31ab5b33015d578ae8a473e5b9dc51583dda3b557ad1f41c5"
            );
        }

        #[test]
        fn test_canonical_v2_unicode_escaping_matches_python() {
            // Python ensure_ascii escapes every non-ASCII character.
            let mut fields = HashMap::new();
            fields.insert("title".to_string(), "café ☃".to_string());
            fields.insert("created_at".to_string(), "1700000000".to_string());
            fields.insert("expires_at".to_string(), String::new());
            fields.insert("nonce".to_string(), "n".to_string());
            assert_eq!(
                String::from_utf8(canonical_payload_v2("1", "default", &fields, "spéc"))
                    .unwrap(),
                r#"{"accept":"","base":"","branch":"","created_at":"1700000000","expires_at":"","jid":"1","kid":"default","nonce":"n","room":"","spec":"sp\u00e9c","title":"caf\u00e9 \u2603"}"#
            );
            assert_eq!(
                sign_job_v2(b"crew-secret-abc", "1", "default", &fields, "spéc"),
                "735a8d3dcb6dff289e2476d7f46345485e5ffc4612069777fb14b49e2fa14741"
            );
        }

        #[test]
        fn test_artifact_ref_valid_and_malformed() {
            assert_eq!(
                parse_artifact_ref("artifact:12/report.txt@v3"),
                Some((
                    "12".to_string(),
                    "report.txt".to_string(),
                    3
                ))
            );
            assert_eq!(
                parse_artifact_ref("artifact:job-1/a/b/c@v10"),
                Some(("job-1".to_string(), "a/b/c".to_string(), 10))
            );
            // Greedy name: the LAST @v<digits> at the end wins.
            assert_eq!(
                parse_artifact_ref("artifact:1/x@v2@v3"),
                Some(("1".to_string(), "x@v2".to_string(), 3))
            );
            for bad in [
                "artifact:1/name@v0",       // version counts from 1
                "artifact:1/@v1",           // empty name
                "artifact:1/a/../b@v1",     // .. segment
                "artifact:1/a/./b@v1",      // . segment
                "artifact:1/a//b@v1",       // empty segment
                "artifact:1/a\\b@v1",       // backslash
                "artifact:1/name",          // no @v
                "artifact:1/name@v",        // no digits
                "artifact:/name@v1",        // empty job
                "artifact:1!/name@v1",      // bad job char
                "not-a-ref",
                "",
            ] {
                assert_eq!(parse_artifact_ref(bad), None, "{}", bad);
            }
            assert_eq!(split_artifacts("a, b,,c "), vec!["a", "b", "c"]);
            assert!(validate_artifact_refs(&["artifact:1/x@v1".to_string()]).is_none());
            assert!(validate_artifact_refs(&["bogus".to_string()])
                .unwrap()
                .contains("malformed artifact reference"));
        }

        #[test]
        fn test_keyring_parsing() {
            let ring = parse_keyring(
                "k",
                "crew-2026-09:crew-secret-abc\ncrew-2026-10:crew-secret-def\n",
            )
            .unwrap();
            assert_eq!(ring.default_kid, "crew-2026-09");
            assert_eq!(ring.get("crew-2026-10"), Some(b"crew-secret-def".as_slice()));
            assert_eq!(ring.kids_sorted(), vec!["crew-2026-09", "crew-2026-10"]);
            let legacy = parse_keyring("k", "crew-secret-abc\n").unwrap();
            assert_eq!(legacy.default_kid, "default");
            assert!(parse_keyring("k", "").is_err());
            assert!(parse_keyring("k", "a\nb\n").is_err());
            assert!(parse_keyring("k", "a:b:c\n").is_err());
            assert!(parse_keyring("k", ":secret\n").is_err());
        }

        #[test]
        fn test_clean_room_and_bus_key() {
            assert_eq!(clean_room("build-x").unwrap(), "build-x");
            assert_eq!(clean_room("Build_X!").unwrap(), "build_x");
            assert_eq!(clean_room("").unwrap(), "");
            assert!(clean_room("!!!").is_err());
            assert_eq!(bus_key("").unwrap(), "muse-bus");
            assert_eq!(bus_key("build-x").unwrap(), "muse-bus:room:build-x");
        }

        #[test]
        fn test_url_quote_unquote_roundtrip() {
            let original = "pct %25 slash %2F end";
            let quoted = url_quote(original);
            assert_eq!(url_unquote(&quoted), original);
            assert_eq!(url_quote("a/b c"), "a%2Fb%20c");
            assert_eq!(url_unquote("a%2Fb%20c"), "a/b c");
            assert_eq!(url_unquote("bad%zz"), "bad%zz");
        }

        #[test]
        fn test_brief_time_eastern_conversion() {
            // Values computed from Python's zoneinfo America/New_York.
            assert_eq!(format_brief_time(1793093400), "2026-10-27 05:30 ET");
            assert_eq!(format_brief_time(1772953199), "2026-03-08 01:59 ET");
            assert_eq!(format_brief_time(1772953200), "2026-03-08 03:00 ET");
            assert_eq!(format_brief_time(1793512799), "2026-11-01 01:59 ET");
            assert_eq!(format_brief_time(1793512800), "2026-11-01 01:00 ET");
            assert_eq!(format_brief_time(1768478400), "2026-01-15 07:00 ET");
        }
    }

    // -- test_jobs.py: post ---------------------------------------------------

    mod post_tests {
        use super::*;

        #[test]
        fn test_post_creates_job() {
            let (_clock, mut q) = test_queue();
            let outcome = post_extra(&mut q, "Fix login", "make it work\nsecond line", |a| {
                a.accept = "tests pass".to_string();
                a.branch = "w/login".to_string();
            });
            assert_eq!(outcome.code, 0);
            assert!(outcome.out.contains("JOB 1"));
            let h = fields(&mut q, "1");
            assert_eq!(h["title"], "Fix login");
            assert_eq!(h["status"], "open");
            assert_eq!(h["accept"], "tests pass");
            assert_eq!(h["branch"], "w/login");
            assert_eq!(h["created_by"], "tester");
            assert_eq!(h["created_host"], "host-a");
            assert_eq!(spec_of(&mut q, "1"), "make it work\nsecond line");
            assert!(q.pushes_to("muse-bus").contains(&"tester: JOB:1 Fix login".to_string()));
        }

        #[test]
        fn test_post_spec_from_stdin() {
            // The caller resolves `--spec -` (stdin) before calling.
            let (_clock, mut q) = test_queue();
            let outcome = post_simple(&mut q, "T", "stdin spec here");
            assert_eq!(outcome.code, 0);
            assert_eq!(spec_of(&mut q, "1"), "stdin spec here");
        }

        #[test]
        fn test_post_empty_spec_rejected() {
            let (_clock, mut q) = test_queue();
            let outcome = post_simple(&mut q, "T", "   ");
            assert_eq!(outcome.code, 2);
            assert!(outcome.err.contains("empty"));
        }

        #[test]
        fn test_post_announces_to_room() {
            let (_clock, mut q) = test_queue();
            let outcome = post_extra(&mut q, "T", "s", |a| {
                a.room = "build-x".to_string();
            });
            assert_eq!(outcome.code, 0);
            assert_eq!(fields(&mut q, "1")["room"], "build-x");
            assert!(q
                .pushes_to("muse-bus:room:build-x")
                .contains(&"tester: JOB:1 T".to_string()));
        }

        #[test]
        fn test_post_lease_too_short_rejected() {
            let (_clock, mut q) = test_queue();
            let outcome = post_extra(&mut q, "T", "s", |a| a.lease = 59);
            assert_eq!(outcome.code, 2);
            assert!(outcome.err.contains("at least 60s"));
        }

        #[test]
        fn test_post_bad_artifact_ref_posts_nothing() {
            let (_clock, mut q) = test_queue();
            let outcome = post_extra(&mut q, "T", "s", |a| {
                a.artifacts = "bogus".to_string();
            });
            assert_eq!(outcome.code, 2);
            assert!(outcome.err.contains("malformed artifact reference"));
            assert!(q.job_get("1").0.is_none());
        }
    }

    // -- test_jobs.py: claim ---------------------------------------------------

    mod claim_tests {
        use super::*;

        fn setup_claimed() -> (Rc<FakeClock>, JobQueue<FakeStore>) {
            let (clock, mut q) = test_queue();
            post_simple(&mut q, "T", "s");
            (clock, q)
        }

        #[test]
        fn test_claim_lifecycle() {
            let (_clock, mut q) = setup_claimed();
            let outcome = q.claim("1", "", 1800, None);
            assert_eq!(outcome.code, 0);
            assert!(outcome.out.contains("CLAIMED 1 by tester"));
            let h = fields(&mut q, "1");
            assert_eq!(h["status"], "claimed");
            assert_eq!(h["claim"], "tester");
            assert!(q.pushes_to("muse-bus").contains(&"tester: CLAIM:1 by tester".to_string()));
        }

        #[test]
        fn test_claim_missing_job() {
            let (_clock, mut q) = setup_claimed();
            let outcome = q.claim("99", "", 1800, None);
            assert_eq!(outcome.code, 2);
            assert!(outcome.err.contains("no such job"));
        }

        #[test]
        fn test_claim_twice_fails() {
            let (_clock, mut q) = setup_claimed();
            q.claim("1", "", 1800, None);
            q.set_nick("worker2", "host-b");
            let outcome = q.claim("1", "", 1800, None);
            assert_eq!(outcome.code, 2);
            assert!(outcome.err.contains("claimed by tester"));
        }

        #[test]
        fn test_lost_race() {
            let (_clock, mut q) = setup_claimed();
            q.store_set_raw("muse-bus:tjob:1:claim", "other", Some(1800))
                .unwrap();
            let outcome = q.claim("1", "", 1800, None);
            assert_eq!(outcome.code, 2);
            assert!(outcome.err.contains("lost the race"));
        }

        #[test]
        fn test_ids_increment() {
            let (_clock, mut q) = setup_claimed();
            post_simple(&mut q, "T2", "s");
            let outcome = q.list("all", false);
            assert!(outcome.out.contains('1'));
            assert!(outcome.out.contains('2'));
        }

        #[test]
        fn test_claim_mutex_rolled_back_when_hset_fails() {
            // Mirrors both Python rollback tests (patched _hset and
            // replaced _hset): the mutex SET NX wins, then the
            // claim-record write blows up, and cmd_claim must
            // best-effort delete the mutex so the job stays open.
            let clock = Rc::new(FakeClock::new(START));
            let store = FailHsetStore {
                inner: FakeStore::new(clock.clone()),
                fail: Cell::new(false),
            };
            let mut q = JobQueue::new(store, clock, "muse-bus:tjob", "tester", "host-a");
            let mut args = PostArgs::default();
            args.title = "T".to_string();
            args.spec = "s".to_string();
            assert_eq!(q.post(args).code, 0);
            q.store.fail.set(true);
            let outcome = q.claim("1", "", 1800, None);
            assert_eq!(outcome.code, 2);
            assert!(outcome.err.contains("claim record failed"));
            assert_eq!(q.store_get_raw("muse-bus:tjob:1:claim"), None);
            assert_eq!(fields(&mut q, "1")["status"], "open");
        }
    }

    /// A store wrapper that fails every `hset`, for the claim
    /// rollback tests.
    struct FailHsetStore {
        inner: FakeStore,
        fail: Cell<bool>,
    }

    impl JobStore for FailHsetStore {
        fn incr(&mut self, key: &str) -> Result<u64, StoreError> {
            self.inner.incr(key)
        }
        fn hset(&mut self, key: &str, fields: &[(&str, &str)]) -> Result<(), StoreError> {
            if self.fail.get() {
                return Err(StoreError("boom".to_string()));
            }
            self.inner.hset(key, fields)
        }
        fn hgetall(&mut self, key: &str) -> Result<Vec<(String, String)>, StoreError> {
            self.inner.hgetall(key)
        }
        fn hdel(&mut self, key: &str, fields: &[&str]) -> Result<(), StoreError> {
            self.inner.hdel(key, fields)
        }
        fn get(&mut self, key: &str) -> Result<Option<String>, StoreError> {
            self.inner.get(key)
        }
        fn set(
            &mut self,
            key: &str,
            value: &str,
            mode: Option<SetMode>,
            ex_secs: Option<u64>,
        ) -> Result<bool, StoreError> {
            self.inner.set(key, value, mode, ex_secs)
        }
        fn del(&mut self, key: &str) -> Result<(), StoreError> {
            self.inner.del(key)
        }
        fn expire(&mut self, key: &str, secs: u64) -> Result<bool, StoreError> {
            self.inner.expire(key, secs)
        }
        fn zadd(&mut self, key: &str, score: i64, member: &str) -> Result<(), StoreError> {
            self.inner.zadd(key, score, member)
        }
        fn zrange(&mut self, key: &str) -> Result<Vec<String>, StoreError> {
            self.inner.zrange(key)
        }
    }

    // -- test_jobs.py: progress / done / blocked / cancel / leases ----------

    mod progress_done_tests {
        use super::*;

        fn setup_claimed() -> (Rc<FakeClock>, JobQueue<FakeStore>) {
            let (clock, mut q) = test_queue();
            post_simple(&mut q, "T", "s");
            q.claim("1", "", 1800, None);
            (clock, q)
        }

        #[test]
        fn test_progress_renews_and_notes() {
            let (clock, mut q) = setup_claimed();
            let before = fields(&mut q, "1")["lease_until"].clone();
            clock.advance(60);
            let outcome = q.progress("1", "half done", "");
            assert_eq!(outcome.code, 0);
            let h = fields(&mut q, "1");
            assert_eq!(h["note"], "half done");
            assert!(h["lease_until"].parse::<u64>().unwrap() > before.parse::<u64>().unwrap());
            assert!(q
                .pushes_to("muse-bus")
                .contains(&"tester: PROGRESS:1 half done".to_string()));
        }

        #[test]
        fn test_heartbeat_renews() {
            let (clock, mut q) = setup_claimed();
            let before = fields(&mut q, "1")["lease_until"].clone();
            clock.advance(60);
            let outcome = q.heartbeat("1", 0);
            assert_eq!(outcome.code, 0);
            assert!(outcome.out.contains("LEASE_RENEWED 1"));
            let h = fields(&mut q, "1");
            assert!(h["lease_until"].parse::<u64>().unwrap() > before.parse::<u64>().unwrap());
        }

        #[test]
        fn test_done() {
            let (_clock, mut q) = setup_claimed();
            let outcome = q.done("1", "abc123", "ship", "");
            assert_eq!(outcome.code, 0);
            assert!(outcome.out.contains("DONE 1 abc123"));
            let h = fields(&mut q, "1");
            assert_eq!(h["status"], "done");
            assert_eq!(h["result_commit"], "abc123");
            assert_eq!(q.store_get_raw("muse-bus:tjob:1:claim"), None);
            assert!(q.pushes_to("muse-bus").contains(&"tester: DONE:1 abc123".to_string()));
        }

        #[test]
        fn test_done_by_other_fails() {
            let (_clock, mut q) = setup_claimed();
            q.set_nick("worker2", "host-b");
            let outcome = q.done("1", "x", "", "");
            assert_eq!(outcome.code, 2);
            assert!(outcome.err.contains("claimed by 'tester'"));
        }

        #[test]
        fn test_blocked_releases() {
            let (_clock, mut q) = setup_claimed();
            let outcome = q.blocked("1", "need API key", "");
            assert_eq!(outcome.code, 0);
            assert_eq!(fields(&mut q, "1")["status"], "blocked");
            assert_eq!(q.store_get_raw("muse-bus:tjob:1:claim"), None);
            assert!(q
                .pushes_to("muse-bus")
                .contains(&"tester: BLOCKED:1 need API key".to_string()));
        }

        #[test]
        fn test_claim_blocked_fails() {
            let (_clock, mut q) = setup_claimed();
            q.blocked("1", "x", "");
            let outcome = q.claim("1", "", 1800, None);
            assert_eq!(outcome.code, 2);
            assert!(outcome.err.contains("is blocked"));
        }
    }

    mod cancel_tests {
        use super::*;

        #[test]
        fn test_cancel_open_job() {
            let (_clock, mut q) = test_queue();
            post_simple(&mut q, "T", "s");
            let outcome = q.cancel("1", "undone");
            assert_eq!(outcome.code, 0);
            assert!(outcome.out.contains("CANCELLED 1"));
            let h = fields(&mut q, "1");
            assert_eq!(h["status"], "cancelled");
            assert_eq!(h["note"], "undone");
            assert!(!h["cancelled_at"].is_empty());
        }

        #[test]
        fn test_cancelled_job_cannot_be_claimed() {
            let (_clock, mut q) = test_queue();
            post_simple(&mut q, "T", "s");
            q.cancel("1", "cancelled");
            let outcome = q.claim("1", "", 1800, None);
            assert_eq!(outcome.code, 2);
            assert!(outcome.err.contains("is cancelled"));
        }

        #[test]
        fn test_cancel_claimed_job_refused() {
            let (_clock, mut q) = test_queue();
            post_simple(&mut q, "T", "s");
            q.claim("1", "", 1800, None);
            let outcome = q.cancel("1", "cancelled");
            assert_eq!(outcome.code, 2);
            assert!(outcome.err.contains("not open"));
            assert_eq!(fields(&mut q, "1")["status"], "claimed");
        }

        #[test]
        fn test_cancel_missing_job_refused() {
            let (_clock, mut q) = test_queue();
            let outcome = q.cancel("99", "cancelled");
            assert_eq!(outcome.code, 2);
            assert!(outcome.err.contains("no such job"));
        }

        #[test]
        fn test_cancel_twice_refused() {
            let (_clock, mut q) = test_queue();
            post_simple(&mut q, "T", "s");
            q.cancel("1", "cancelled");
            let outcome = q.cancel("1", "cancelled");
            assert_eq!(outcome.code, 2);
            assert!(outcome.err.contains("not open"));
        }

        #[test]
        fn test_list_status_cancelled() {
            let (_clock, mut q) = test_queue();
            post_simple(&mut q, "T", "s");
            q.cancel("1", "cancelled");
            let outcome = q.list("cancelled", false);
            assert_eq!(outcome.code, 0);
            assert!(outcome.out.contains("cancelled"));
            let outcome = q.list("open", false);
            assert_eq!(outcome.out, "NO_JOBS\n");
        }
    }

    mod lease_expiry_tests {
        use super::*;

        #[test]
        fn test_expired_claim_can_be_reclaimed() {
            let (clock, mut q) = test_queue();
            post_simple(&mut q, "T", "s");
            q.claim("1", "", 100, None);
            clock.advance(200);
            q.set_nick("worker2", "host-b");
            let outcome = q.claim("1", "", 1800, None);
            assert_eq!(outcome.code, 0, "{}", outcome.err);
            assert_eq!(fields(&mut q, "1")["claim"], "worker2");
            assert!(q.pushes_to("muse-bus").contains(&"worker2: REQUEUE:1".to_string()));
        }

        #[test]
        fn test_requeue_refuses_active_lease() {
            let (_clock, mut q) = test_queue();
            post_simple(&mut q, "T", "s");
            q.claim("1", "", 100, None);
            let outcome = q.requeue("1", "");
            assert_eq!(outcome.code, 2);
            assert!(outcome.err.contains("still active"));
        }

        #[test]
        fn test_requeue_after_expiry() {
            let (clock, mut q) = test_queue();
            post_simple(&mut q, "T", "s");
            q.claim("1", "", 100, None);
            clock.advance(200);
            let outcome = q.requeue("1", "");
            assert_eq!(outcome.code, 0);
            assert!(outcome.out.contains("REQUEUED 1"));
            assert_eq!(fields(&mut q, "1")["status"], "open");
        }

        #[test]
        fn test_sweep() {
            let (clock, mut q) = test_queue();
            post_simple(&mut q, "T", "s");
            q.claim("1", "", 1800, None);
            post_simple(&mut q, "T2", "s");
            q.claim("2", "", 100, None);
            clock.advance(50);
            q.heartbeat("1", 500);
            clock.advance(200);
            let outcome = q.sweep("");
            assert_eq!(outcome.code, 0);
            assert!(outcome.out.contains("REQUEUED 2"));
            assert!(!outcome.out.contains("REQUEUED 1"));
            assert_eq!(fields(&mut q, "1")["status"], "claimed");
        }
    }

    mod trust_warning_tests {
        use super::*;

        #[test]
        fn test_claim_warns_on_spoofed_poster() {
            let (_clock, mut q) = test_queue();
            post_simple(&mut q, "T", "s");
            // Someone else now holds the 'tester' nick claim.
            q.store_set_raw("muse-bus:nickclaim:tester", "host-evil", Some(300))
                .unwrap();
            q.set_nick("worker2", "host-b");
            let outcome = q.claim("1", "", 1800, None);
            assert_eq!(outcome.code, 0);
            assert!(outcome.err.contains("now claimed by 'host-evil'"));
        }
    }

    mod list_show_tests {
        use super::*;

        #[test]
        fn test_list_and_show() {
            let (_clock, mut q) = test_queue();
            post_extra(&mut q, "First", "spec-one", |a| {
                a.accept = "it works".to_string();
            });
            post_simple(&mut q, "Second", "s2");
            q.claim("2", "", 1800, None);
            let outcome = q.list("open", false);
            assert!(outcome.out.contains("First"));
            assert!(!outcome.out.contains("Second"));
            let outcome = q.show("1");
            assert!(outcome.out.contains("title: First"));
            assert!(outcome.out.contains("accept: it works"));
            assert!(outcome.out.contains("spec-one"));
        }
    }

    mod encoding_tests {
        use super::*;

        #[test]
        fn test_hgetall_roundtrips_literal_percent() {
            // The read path must invert the write path exactly once:
            // a stored literal "%25"/"%2F" comes back byte-identical.
            let (_clock, mut q) = test_queue();
            let val = "pct %25 slash %2F end";
            q.store_hset_raw("muse-bus:tjob:enc", &[("note", val)])
                .unwrap();
            let pairs = q.store.hgetall("muse-bus:tjob:enc").unwrap();
            let map: HashMap<String, String> = pairs.into_iter().collect();
            assert_eq!(map["note"], val);
        }
    }

    // -- test_jobs.py: signed jobs --------------------------------------------

    mod signed_job_tests {
        use super::*;

        struct Fixture {
            secret: std::path::PathBuf,
            other_secret: std::path::PathBuf,
        }

        fn fixture() -> Fixture {
            Fixture {
                secret: secret_file("crew-secret-abc\n"),
                other_secret: secret_file("wrong-secret-xyz"),
            }
        }

        fn post_signed(q: &mut JobQueue<FakeStore>, fx: &Fixture) -> CmdOutcome {
            post_extra(q, "T", "do the thing", |a| {
                a.secret_file = Some(fx.secret.to_string_lossy().into_owned());
            })
        }

        #[test]
        fn test_post_signed_stores_sig() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            let outcome = post_signed(&mut q, &fx);
            assert_eq!(outcome.code, 0);
            assert!(outcome.out.contains("JOB 1"));
            let h = fields(&mut q, "1");
            assert!(h.contains_key("sig"));
            assert_eq!(h["signed_by"], "tester");
            assert_eq!(h["sig"].len(), 64); // sha256 hex
            let _ = std::fs::remove_file(&fx.secret);
            let _ = std::fs::remove_file(&fx.other_secret);
        }

        #[test]
        fn test_post_unsigned_has_no_sig() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            let outcome = post_simple(&mut q, "T", "s");
            assert_eq!(outcome.code, 0);
            assert!(!fields(&mut q, "1").contains_key("sig"));
            let _ = std::fs::remove_file(&fx.secret);
            let _ = std::fs::remove_file(&fx.other_secret);
        }

        #[test]
        fn test_post_bad_secret_file_errors() {
            let (_clock, mut q) = test_queue();
            let outcome = post_extra(&mut q, "T", "s", |a| {
                a.secret_file = Some("/nonexistent/secret".to_string());
            });
            assert_eq!(outcome.code, 2);
            assert!(outcome.err.contains("cannot read secret file"));
        }

        #[test]
        fn test_verify_ok() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            post_signed(&mut q, &fx);
            let outcome = q.verify("1", &fx.secret.to_string_lossy());
            assert_eq!(outcome.code, 0);
            assert_eq!(outcome.out.trim(), "OK");
            let _ = std::fs::remove_file(&fx.secret);
            let _ = std::fs::remove_file(&fx.other_secret);
        }

        #[test]
        fn test_verify_unsigned() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            post_simple(&mut q, "T", "s");
            let outcome = q.verify("1", &fx.secret.to_string_lossy());
            assert_eq!(outcome.code, 1);
            assert_eq!(outcome.out.trim(), "UNSIGNED");
            let _ = std::fs::remove_file(&fx.secret);
            let _ = std::fs::remove_file(&fx.other_secret);
        }

        #[test]
        fn test_verify_wrong_secret() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            post_signed(&mut q, &fx);
            let outcome = q.verify("1", &fx.other_secret.to_string_lossy());
            assert_eq!(outcome.code, 1);
            assert_eq!(outcome.out.trim(), "BAD");
            let _ = std::fs::remove_file(&fx.secret);
            let _ = std::fs::remove_file(&fx.other_secret);
        }

        #[test]
        fn test_verify_tampered_spec() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            post_signed(&mut q, &fx);
            // Attacker rewrites the spec in the store directly.
            q.store_set_raw("muse-bus:tjob:1:spec", "do the EVIL thing", None)
                .unwrap();
            let outcome = q.verify("1", &fx.secret.to_string_lossy());
            assert_eq!(outcome.code, 1);
            assert_eq!(outcome.out.trim(), "BAD");
            let _ = std::fs::remove_file(&fx.secret);
            let _ = std::fs::remove_file(&fx.other_secret);
        }

        #[test]
        fn test_verify_tampered_field() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            post_extra(&mut q, "Original title", "s", |a| {
                a.secret_file = Some(fx.secret.to_string_lossy().into_owned());
            });
            q.store_hset_raw("muse-bus:tjob:1", &[("title", "PWNED title")])
                .unwrap();
            let outcome = q.verify("1", &fx.secret.to_string_lossy());
            assert_eq!(outcome.code, 1);
            assert_eq!(outcome.out.trim(), "BAD");
            let _ = std::fs::remove_file(&fx.secret);
            let _ = std::fs::remove_file(&fx.other_secret);
        }

        #[test]
        fn test_verify_unknown_job() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            let outcome = q.verify("99", &fx.secret.to_string_lossy());
            assert_eq!(outcome.code, 2);
            assert!(outcome.err.contains("no such job"));
            let _ = std::fs::remove_file(&fx.secret);
            let _ = std::fs::remove_file(&fx.other_secret);
        }

        #[test]
        fn test_claim_signed_ok() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            post_signed(&mut q, &fx);
            let outcome = q.claim("1", "", 1800, Some(&fx.secret.to_string_lossy()));
            assert_eq!(outcome.code, 0);
            assert!(outcome.out.contains("CLAIMED 1"));
            let _ = std::fs::remove_file(&fx.secret);
            let _ = std::fs::remove_file(&fx.other_secret);
        }

        #[test]
        fn test_claim_refuses_tampered() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            post_signed(&mut q, &fx);
            q.store_set_raw("muse-bus:tjob:1:spec", "do the EVIL thing", None)
                .unwrap();
            let outcome = q.claim("1", "", 1800, Some(&fx.secret.to_string_lossy()));
            assert_eq!(outcome.code, 1);
            assert!(outcome.err.contains("signature BAD"));
            assert_eq!(fields(&mut q, "1")["status"], "open"); // still unclaimed
            let _ = std::fs::remove_file(&fx.secret);
            let _ = std::fs::remove_file(&fx.other_secret);
        }

        #[test]
        fn test_claim_unsigned_with_secret_still_works() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            post_simple(&mut q, "T", "s");
            let outcome = q.claim("1", "", 1800, Some(&fx.secret.to_string_lossy()));
            assert_eq!(outcome.code, 0);
            assert!(outcome.out.contains("CLAIMED 1"));
            let _ = std::fs::remove_file(&fx.secret);
            let _ = std::fs::remove_file(&fx.other_secret);
        }

        #[test]
        fn test_show_displays_signed_by() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            post_signed(&mut q, &fx);
            let outcome = q.show("1");
            assert_eq!(outcome.code, 0);
            assert!(outcome.out.contains("signed_by: tester"));
            let _ = std::fs::remove_file(&fx.secret);
            let _ = std::fs::remove_file(&fx.other_secret);
        }
    }

    // -- test_jobs.py: v2 hardening ------------------------------------------

    mod hardening_tests {
        use super::*;

        struct Fixture {
            keyring: std::path::PathBuf,
            legacy: std::path::PathBuf,
        }

        fn fixture() -> Fixture {
            Fixture {
                keyring: secret_file(
                    "crew-2026-09:crew-secret-abc\ncrew-2026-10:crew-secret-def\n",
                ),
                legacy: secret_file("crew-secret-abc\n"),
            }
        }

        fn post_signed(q: &mut JobQueue<FakeStore>, fx: &Fixture, extra: &[&str]) -> CmdOutcome {
            let mut args = PostArgs::default();
            args.title = "T".to_string();
            args.spec = "s".to_string();
            args.secret_file = Some(fx.keyring.to_string_lossy().into_owned());
            let mut i = 0;
            while i < extra.len() {
                match extra[i] {
                    "--kid" => args.kid = extra[i + 1].to_string(),
                    "--expires" => args.expires = Some(extra[i + 1].parse().unwrap()),
                    _ => {}
                }
                i += 2;
            }
            q.post(args)
        }

        fn verify(q: &mut JobQueue<FakeStore>, jid: &str, path: &std::path::Path) -> CmdOutcome {
            q.verify(jid, &path.to_string_lossy())
        }

        fn cleanup(fx: &Fixture) {
            let _ = std::fs::remove_file(&fx.keyring);
            let _ = std::fs::remove_file(&fx.legacy);
        }

        #[test]
        fn test_post_defaults_to_first_kid() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            assert_eq!(post_signed(&mut q, &fx, &[]).code, 0);
            let h = fields(&mut q, "1");
            assert_eq!(h["sig_kid"], "crew-2026-09");
            assert_eq!(h["sig_v"], "2");
            assert!(!h["nonce"].is_empty());
            let outcome = verify(&mut q, "1", &fx.keyring);
            assert_eq!(outcome.code, 0);
            assert_eq!(outcome.out.trim(), "OK");
            cleanup(&fx);
        }

        #[test]
        fn test_post_explicit_kid() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            assert_eq!(post_signed(&mut q, &fx, &["--kid", "crew-2026-10"]).code, 0);
            assert_eq!(fields(&mut q, "1")["sig_kid"], "crew-2026-10");
            let outcome = verify(&mut q, "1", &fx.keyring);
            assert_eq!(outcome.code, 0);
            assert_eq!(outcome.out.trim(), "OK");
            cleanup(&fx);
        }

        #[test]
        fn test_post_unknown_kid_rejected() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            let outcome = post_signed(&mut q, &fx, &["--kid", "nope"]);
            assert_eq!(outcome.code, 2);
            assert!(outcome.err.contains("unknown kid"));
            cleanup(&fx);
        }

        #[test]
        fn test_verify_unknown_kid_is_bad() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            post_signed(&mut q, &fx, &["--kid", "crew-2026-10"]);
            let other = secret_file("crew-2026-09:crew-secret-abc\n");
            let outcome = verify(&mut q, "1", &other);
            assert_eq!(outcome.code, 1);
            assert_eq!(outcome.out.trim(), "BAD");
            let _ = std::fs::remove_file(&other);
            cleanup(&fx);
        }

        #[test]
        fn test_legacy_single_token_file_still_works() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            let mut args = PostArgs::default();
            args.title = "T".to_string();
            args.spec = "s".to_string();
            args.secret_file = Some(fx.legacy.to_string_lossy().into_owned());
            assert_eq!(q.post(args).code, 0);
            assert_eq!(fields(&mut q, "1")["sig_kid"], "default");
            let outcome = verify(&mut q, "1", &fx.legacy);
            assert_eq!(outcome.code, 0);
            assert_eq!(outcome.out.trim(), "OK");
            cleanup(&fx);
        }

        #[test]
        fn test_v1_signature_still_verifies() {
            // A job signed before the v2 upgrade (old payload, no sig_v).
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            post_simple(&mut q, "T", "s");
            let (h, spec) = q.job_get("1");
            let h = h.unwrap();
            let sig = sign_job_v1(b"crew-secret-abc", &h, &spec);
            q.store_hset_raw("muse-bus:tjob:1", &[("sig", &sig), ("signed_by", "tester")])
                .unwrap();
            let outcome = verify(&mut q, "1", &fx.legacy);
            assert_eq!(outcome.code, 0);
            assert_eq!(outcome.out.trim(), "OK");
            cleanup(&fx);
        }

        #[test]
        fn test_expiry() {
            let (clock, mut q) = test_queue();
            let fx = fixture();
            post_signed(&mut q, &fx, &["--expires", "3600"]);
            let outcome = verify(&mut q, "1", &fx.keyring);
            assert_eq!(outcome.out.trim(), "OK");
            clock.advance(3601);
            let outcome = verify(&mut q, "1", &fx.keyring);
            assert_eq!(outcome.code, 1);
            assert_eq!(outcome.out.trim(), "EXPIRED");
            cleanup(&fx);
        }

        #[test]
        fn test_claim_refuses_expired_and_alerts() {
            let (clock, mut q) = test_queue();
            let fx = fixture();
            post_signed(&mut q, &fx, &["--expires", "3600"]);
            clock.advance(7200);
            let outcome = q.claim("1", "", 1800, Some(&fx.keyring.to_string_lossy()));
            assert_eq!(outcome.code, 1);
            assert!(outcome.err.contains("EXPIRED"));
            assert!(q
                .pushes_to("muse-bus")
                .iter()
                .any(|m| m.contains("REJECTED:1 EXPIRED")));
            cleanup(&fx);
        }

        #[test]
        fn test_claim_refuses_tampered_and_alerts() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            post_signed(&mut q, &fx, &[]);
            q.store_hset_raw("muse-bus:tjob:1", &[("title", "TAMPERED")])
                .unwrap();
            let outcome = q.claim("1", "", 1800, Some(&fx.keyring.to_string_lossy()));
            assert_eq!(outcome.code, 1);
            assert!(outcome.err.contains("BAD"));
            assert!(q
                .pushes_to("muse-bus")
                .iter()
                .any(|m| m.contains("REJECTED:1 BAD")));
            cleanup(&fx);
        }

        #[test]
        fn test_transplanted_signature_fails() {
            // A signature lifted from job 1 does not verify on job 2:
            // the signature is bound to the exact job id.
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            post_signed(&mut q, &fx, &[]);
            post_signed(&mut q, &fx, &[]);
            let h1 = fields(&mut q, "1");
            let copy = |f: &str| h1.get(f).cloned().unwrap_or_default();
            let sig = copy("sig");
            let sig_v = copy("sig_v");
            let sig_kid = copy("sig_kid");
            let signed_by = copy("signed_by");
            let nonce = copy("nonce");
            let expires_at = copy("expires_at");
            q.store_hset_raw(
                "muse-bus:tjob:2",
                &[
                    ("sig", sig.as_str()),
                    ("sig_v", sig_v.as_str()),
                    ("sig_kid", sig_kid.as_str()),
                    ("signed_by", signed_by.as_str()),
                    ("nonce", nonce.as_str()),
                    ("expires_at", expires_at.as_str()),
                ],
            )
            .unwrap();
            let outcome = verify(&mut q, "2", &fx.keyring);
            assert_eq!(outcome.code, 1);
            assert_eq!(outcome.out.trim(), "BAD");
            cleanup(&fx);
        }

        #[test]
        fn test_show_displays_sig_fields() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            post_signed(&mut q, &fx, &["--expires", "3600"]);
            let outcome = q.show("1");
            assert_eq!(outcome.code, 0);
            assert!(outcome.out.contains("sig_kid: crew-2026-09"));
            assert!(outcome.out.contains("sig_v: 2"));
            assert!(outcome.out.contains("nonce: "));
            cleanup(&fx);
        }

        #[test]
        fn test_unsigned_claim_still_allowed_with_warning() {
            let (_clock, mut q) = test_queue();
            let fx = fixture();
            post_simple(&mut q, "T", "s");
            let outcome = q.claim("1", "", 1800, Some(&fx.keyring.to_string_lossy()));
            assert_eq!(outcome.code, 0);
            assert!(outcome.err.contains("unsigned"));
            cleanup(&fx);
        }
    }

    // -- test_jobs_req.py ------------------------------------------------------

    mod req_tests {
        use super::*;

        #[test]
        fn test_post_stores_normalized_req() {
            let (_clock, mut q) = test_queue();
            post_extra(&mut q, "Fix login", "make it work", |a| {
                a.req = "Python, GIT,python".to_string();
            });
            assert_eq!(fields(&mut q, "1")["req"], "python,git");
        }

        #[test]
        fn test_post_without_req_stores_empty() {
            let (_clock, mut q) = test_queue();
            post_simple(&mut q, "T", "s");
            assert_eq!(fields(&mut q, "1").get("req").map(|s| s.as_str()).unwrap_or(""), "");
        }

        #[test]
        fn test_list_json_and_show_carry_req() {
            let (_clock, mut q) = test_queue();
            post_extra(&mut q, "T", "s", |a| {
                a.req = "python".to_string();
            });
            let outcome = q.list("all", true);
            assert_eq!(outcome.code, 0);
            assert!(outcome.out.contains("\"req\": \"python\""));
            let outcome = q.show("1");
            assert_eq!(outcome.code, 0);
            assert!(outcome.out.contains("req: python"));
        }
    }

    // -- test_jobs.py: job fields (FND-008/009/010/011/013) --------------------

    mod job_fields_tests {
        use super::*;

        fn post(q: &mut JobQueue<FakeStore>, extra: &[&str]) -> CmdOutcome {
            let mut args = PostArgs::default();
            args.title = "T".to_string();
            args.spec = "s".to_string();
            let mut i = 0;
            while i < extra.len() {
                match extra[i] {
                    "--files" => args.files = extra[i + 1].to_string(),
                    "--deps" => args.deps = extra[i + 1].to_string(),
                    "--max-attempts" => {
                        args.max_attempts = Some(extra[i + 1].parse().unwrap())
                    }
                    _ => {}
                }
                i += 2;
            }
            q.post(args)
        }

        #[test]
        fn test_files_stored_and_shown() {
            let (_clock, mut q) = test_queue();
            post(&mut q, &["--files", "a.py,b.py"]);
            assert_eq!(fields(&mut q, "1")["files"], "a.py,b.py");
            let outcome = q.show("1");
            assert_eq!(outcome.code, 0);
            assert!(outcome.out.contains("files: a.py,b.py"));
        }

        #[test]
        fn test_deps_stored_and_shown() {
            let (_clock, mut q) = test_queue();
            post(&mut q, &[]);
            let outcome = post(&mut q, &["--deps", "1"]);
            assert_eq!(outcome.code, 0);
            assert!(!outcome.err.contains("WARNING"));
            assert_eq!(fields(&mut q, "2")["deps"], "1");
            let outcome = q.show("2");
            assert!(outcome.out.contains("deps: 1"));
        }

        #[test]
        fn test_deps_missing_warns_but_posts() {
            let (_clock, mut q) = test_queue();
            let outcome = post(&mut q, &["--deps", "99"]);
            assert_eq!(outcome.code, 0);
            assert!(outcome.err.contains("WARNING"));
            assert!(outcome.err.contains("dep 99"));
            assert_eq!(fields(&mut q, "1")["deps"], "99");
        }

        #[test]
        fn test_attempts_walk_to_failed_final() {
            let (clock, mut q) = test_queue();
            post(&mut q, &["--max-attempts", "2"]);
            for expected in ["1", "2"] {
                let outcome = q.claim("1", "", 100, None);
                assert_eq!(outcome.code, 0, "{}", outcome.err);
                clock.advance(200);
                let outcome = q.requeue("1", "");
                assert_eq!(outcome.code, 0, "{}", outcome.err);
                assert!(outcome.out.contains("REQUEUED 1"));
                let h = fields(&mut q, "1");
                assert_eq!(h["attempts"], expected);
                assert_eq!(h["status"], "open");
            }
            let outcome = q.claim("1", "", 100, None);
            assert_eq!(outcome.code, 0, "{}", outcome.err);
            clock.advance(200);
            let outcome = q.requeue("1", "");
            assert_ne!(outcome.code, 0);
            assert!(outcome.err.contains("max_attempts"));
            assert_eq!(fields(&mut q, "1")["status"], "failed-final");
        }

        #[test]
        fn test_attempts_unlimited_requeues() {
            let (clock, mut q) = test_queue();
            post(&mut q, &[]);
            assert_eq!(q.claim("1", "", 100, None).code, 0);
            clock.advance(200);
            let outcome = q.requeue("1", "");
            assert_eq!(outcome.code, 0, "{}", outcome.err);
            let h = fields(&mut q, "1");
            assert_eq!(h["attempts"], "1");
            assert_eq!(h["status"], "open");
        }

        #[test]
        fn test_progress_and_heartbeat_stamps() {
            let (_clock, mut q) = test_queue();
            post(&mut q, &[]);
            q.claim("1", "", 100, None);
            let outcome = q.progress("1", "half done", "");
            assert_eq!(outcome.code, 0, "{}", outcome.err);
            let h = fields(&mut q, "1");
            assert!(h["last_progress_at"].chars().all(|c| c.is_ascii_digit()));
            assert!(!h["last_progress_at"].is_empty());
            let outcome = q.show("1");
            assert!(outcome.out.contains("last_progress_at: "));
            let outcome = q.heartbeat("1", 500);
            assert_eq!(outcome.code, 0, "{}", outcome.err);
            let h = fields(&mut q, "1");
            assert!(h["last_heartbeat_at"].chars().all(|c| c.is_ascii_digit()));
            assert!(!h["last_heartbeat_at"].is_empty());
        }

        #[test]
        fn test_list_json_shape_and_values() {
            let (_clock, mut q) = test_queue();
            post(&mut q, &[]);
            post(&mut q, &["--files", "a.py,b.py", "--deps", "1", "--max-attempts", "3"]);
            let outcome = q.list("all", true);
            assert_eq!(outcome.code, 0, "{}", outcome.err);
            // Pinned byte-for-byte: key order and Python json.dumps
            // default separators, as the Python test pins the key set.
            let expected = "[{\"id\": \"1\", \"title\": \"T\", \"status\": \"open\", \"claim\": null, \"files\": \"\", \"deps\": \"\", \"artifacts\": [], \"req\": \"\", \"attempts\": 0, \"lease_until\": null, \"last_progress_at\": null}, {\"id\": \"2\", \"title\": \"T\", \"status\": \"open\", \"claim\": null, \"files\": \"a.py,b.py\", \"deps\": \"1\", \"artifacts\": [], \"req\": \"\", \"attempts\": 0, \"lease_until\": null, \"last_progress_at\": null}]\n";
            assert_eq!(outcome.out, expected);
            q.claim("2", "", 100, None);
            let outcome = q.list("claimed", true);
            assert!(outcome.out.contains("\"id\": \"2\""));
            assert!(outcome.out.contains("\"claim\": \"tester\""));
            assert!(outcome.out.contains("\"lease_until\": 1700000100"));
        }

        #[test]
        fn test_list_json_empty() {
            let (_clock, mut q) = test_queue();
            let outcome = q.list("all", true);
            assert_eq!(outcome.code, 0, "{}", outcome.err);
            assert_eq!(outcome.out, "[]\n");
        }
    }

    // -- test_jobs.py: sweep dep-dead (FND-012) --------------------------------

    mod sweep_dep_dead_tests {
        use super::*;

        fn post(q: &mut JobQueue<FakeStore>, deps: &str) {
            let mut args = PostArgs::default();
            args.title = "T".to_string();
            args.spec = "s".to_string();
            args.deps = deps.to_string();
            assert_eq!(q.post(args).code, 0);
        }

        fn block_job(q: &mut JobQueue<FakeStore>, jid: &str) {
            assert_eq!(q.claim(jid, "", 500, None).code, 0);
            let outcome = q.blocked(jid, "waiting on vendor", "");
            assert_eq!(outcome.code, 0, "{}", outcome.err);
            assert_eq!(fields(q, jid)["status"], "blocked");
        }

        #[test]
        fn test_open_job_with_blocked_dep_flagged_no_mutation() {
            let (_clock, mut q) = test_queue();
            post(&mut q, "");
            block_job(&mut q, "1");
            post(&mut q, "1");
            let before = fields(&mut q, "2");
            let outcome = q.sweep("");
            assert_eq!(outcome.code, 0, "{}", outcome.err);
            assert!(outcome.out.contains("DEP_DEAD 2 dep 1 blocked"));
            assert!(!outcome.out.contains("SWEEP_CLEAN"));
            assert_eq!(fields(&mut q, "2"), before);
        }

        #[test]
        fn test_claimed_job_with_blocked_dep_flagged() {
            let (_clock, mut q) = test_queue();
            post(&mut q, "");
            block_job(&mut q, "1");
            post(&mut q, "1");
            q.claim("2", "", 500, None);
            let outcome = q.sweep("");
            assert_eq!(outcome.code, 0, "{}", outcome.err);
            assert!(outcome.out.contains("DEP_DEAD 2 dep 1 blocked"));
            assert_eq!(fields(&mut q, "2")["status"], "claimed");
        }

        #[test]
        fn test_failed_final_dep_flagged() {
            let (clock, mut q) = test_queue();
            let mut args = PostArgs::default();
            args.title = "T".to_string();
            args.spec = "s".to_string();
            args.max_attempts = Some(1);
            assert_eq!(q.post(args).code, 0);
            for _ in 0..2 {
                q.claim("1", "", 100, None);
                clock.advance(200);
                q.requeue("1", "");
            }
            assert_eq!(fields(&mut q, "1")["status"], "failed-final");
            post(&mut q, "1");
            let outcome = q.sweep("");
            assert_eq!(outcome.code, 0, "{}", outcome.err);
            assert!(outcome.out.contains("DEP_DEAD 2 dep 1 failed-final"));
        }

        #[test]
        fn test_open_or_done_dep_not_flagged() {
            let (_clock, mut q) = test_queue();
            post(&mut q, "");
            post(&mut q, "1");
            let outcome = q.sweep("");
            assert_eq!(outcome.code, 0, "{}", outcome.err);
            assert!(!outcome.out.contains("DEP_DEAD"));
            assert!(outcome.out.contains("SWEEP_CLEAN"));
            q.claim("1", "", 500, None);
            q.done("1", "abc", "", "");
            let outcome = q.sweep("");
            assert_eq!(outcome.code, 0, "{}", outcome.err);
            assert!(!outcome.out.contains("DEP_DEAD"));
        }
    }

    // -- test_claims.py: nick-claim surface jobs.py depends on -----------------
    // The send/poll/watch/presence/DM-room cases in that file test
    // modules owned by other batches (relay, bus messaging) and are
    // NOT ported here; see the completion report.

    mod nick_claim_tests {
        use super::*;

        #[test]
        fn test_first_claim_wins() {
            let (_clock, mut q) = test_queue();
            assert_eq!(q.nick_claim(false), Some((true, "host-a".to_string())));
            q.set_nick("tester", "host-b");
            assert_eq!(q.nick_claim(false), Some((false, "host-a".to_string())));
            assert_eq!(q.nick_conflict_holder(), Some("host-a".to_string()));
        }

        #[test]
        fn test_winner_sees_no_conflict() {
            let (_clock, mut q) = test_queue();
            q.nick_claim(false);
            assert_eq!(q.nick_conflict_holder(), None);
        }

        #[test]
        fn test_claim_renewed_by_heartbeat() {
            // Python renews via presence_beat; the renewal itself is
            // the nick-claim re-check, which refreshes the TTL.
            let (clock, mut q) = test_queue();
            q.nick_claim(false);
            clock.advance(100); // within the TTL
            q.nick_claim(false); // renew
            q.set_nick("tester", "host-b");
            assert_eq!(q.nick_claim(false), Some((false, "host-a".to_string())));
        }

        #[test]
        fn test_claim_ttl_matches_presence_interval() {
            // The reservation lapses exactly when presence does.
            assert_eq!(NICKCLAIM_TTL, PRESENCE_TTL);
            let (clock, mut q) = test_queue();
            q.nick_claim(false);
            clock.advance(NICKCLAIM_TTL + 1); // no renewal: both lapse
            q.set_nick("tester", "host-b");
            assert_eq!(q.nick_claim(true), Some((true, "host-b".to_string())));
        }

        #[test]
        fn test_claim_expires() {
            let (clock, mut q) = test_queue();
            q.nick_claim(false);
            clock.advance(400); // past the TTL, no renewal
            q.set_nick("tester", "host-b");
            assert_eq!(q.nick_claim(true), Some((true, "host-b".to_string())));
        }

        #[test]
        fn test_conflict_clears_when_holder_leaves() {
            let (clock, mut q) = test_queue();
            q.nick_claim(false); // host-a
            q.set_nick("tester", "host-b");
            assert_eq!(q.nick_claim(false).unwrap().0, false);
            clock.advance(400);
            assert_eq!(q.nick_claim(true), Some((true, "host-b".to_string())));
            assert_eq!(q.nick_conflict_holder(), None);
        }

        #[test]
        fn test_nick_holder_readonly() {
            let (_clock, mut q) = test_queue();
            assert_eq!(q.nick_holder("tester"), None);
            q.nick_claim(false);
            assert_eq!(q.nick_holder("tester"), Some("host-a".to_string()));
        }
    }

    // -- test_intel_brief_environment_jobs.py -----------------------------------

    mod environment_jobs_tests {
        use super::*;

        fn jobs_fixture() -> Vec<EnvInput> {
            vec![
                EnvInput::Dict(value_dict(&[
                    ("id", s("5")),
                    ("title", s("brief panel")),
                    ("status", s("claimed")),
                    ("claim", s("rowan")),
                ])),
                EnvInput::Dict(value_dict(&[
                    ("id", s("6")),
                    ("title", s("open job")),
                    ("status", s("open")),
                ])),
                EnvInput::Dict(value_dict(&[
                    ("id", s("7")),
                    ("title", s("blocked job")),
                    ("status", s("blocked")),
                    ("claim", s("milo")),
                ])),
                EnvInput::Dict(value_dict(&[
                    ("id", s("8")),
                    ("title", s("no nick")),
                    ("status", s("claimed")),
                ])),
                EnvInput::Dict(value_dict(&[
                    ("id", s("9")),
                    ("status", s("claimed")),
                    ("claim", s("pax")),
                ])),
                EnvInput::Other, // "not a job"
                EnvInput::Dict(value_dict(&[
                    ("id", s("10")),
                    ("title", s("watchdog")),
                    ("status", s("claimed")),
                    ("claim", s("milo")),
                ])),
            ]
        }

        #[test]
        fn test_only_claimed_jobs_with_nick_and_title_survive_in_order() {
            let record = environment_jobs_record(Some(&jobs_fixture())).unwrap();
            let triples: Vec<(Option<String>, String, String)> = record
                .iter()
                .map(|e| {
                    let id = match e.get("id") {
                        Some(Value::Str(v)) => Some(v.clone()),
                        _ => None,
                    };
                    let claim = match e.get("claim") {
                        Some(Value::Str(v)) => v.clone(),
                        _ => String::new(),
                    };
                    let title = match e.get("title") {
                        Some(Value::Str(v)) => v.clone(),
                        _ => String::new(),
                    };
                    (id, claim, title)
                })
                .collect();
            assert_eq!(
                triples,
                vec![
                    (Some("5".to_string()), "rowan".to_string(), "brief panel".to_string()),
                    (Some("10".to_string()), "milo".to_string(), "watchdog".to_string()),
                ]
            );
        }

        #[test]
        fn test_unusable_id_is_left_out_not_invented() {
            let input = vec![
                EnvInput::Dict(value_dict(&[
                    ("id", s("")),
                    ("title", s("job")),
                    ("status", s("claimed")),
                    ("claim", s("rowan")),
                ])),
                EnvInput::Dict(value_dict(&[
                    ("title", s("other")),
                    ("status", s("claimed")),
                    ("claim", s("milo")),
                ])),
            ];
            let record = environment_jobs_record(Some(&input)).unwrap();
            assert_eq!(
                record[0],
                value_dict(&[
                    ("title", s("job")),
                    ("status", s("claimed")),
                    ("claim", s("rowan")),
                ])
            );
            assert!(!record[1].contains_key("id"));
        }

        #[test]
        fn test_no_claimed_job_returns_empty_not_none() {
            let input = vec![EnvInput::Dict(value_dict(&[
                ("id", s("6")),
                ("title", s("open job")),
                ("status", s("open")),
            ]))];
            assert_eq!(environment_jobs_record(Some(&input)).unwrap(), Vec::new());
        }

        #[test]
        fn test_non_list_returns_none_so_line_reads_not_reported() {
            assert_eq!(environment_jobs_record(None), None);
            // A dict is not a list: the caller passes None here, and
            // the Working now line reads not reported.
            let env = EnvRecord::default();
            let lines = environment_lines(&env);
            assert!(lines[2].contains("not reported"));
        }

        #[test]
        fn test_builder_record_renders_working_line_and_others_not_reported() {
            let jobs = environment_jobs_record(Some(&jobs_fixture())).unwrap();
            let env = EnvRecord {
                jobs: Some(jobs),
                as_of: Some(1793093400),
                ..Default::default()
            };
            let lines = environment_lines(&env);
            assert!(lines[2].contains("rowan: brief panel"));
            assert!(lines[2].contains("milo: watchdog"));
            assert!(!lines[2].contains("open job"));
            assert!(lines[0].contains("not reported"));
            assert!(lines[1].contains("not reported"));
            assert!(lines[3].contains("not reported"));
        }

        #[test]
        fn test_boot_template_brief_carries_builder_working_line() {
            // The full template composer belongs to the intel
            // batches; its Working now line IS environment_lines'
            // third line, so that is what is pinned here.
            let jobs = environment_jobs_record(Some(&jobs_fixture())).unwrap();
            let env = EnvRecord {
                jobs: Some(jobs),
                as_of: Some(1793093400),
                ..Default::default()
            };
            let lines = environment_lines(&env);
            assert!(lines[2].starts_with("Working now: rowan: brief panel"));
        }
    }

    // -- test_os_jobs_unit.py: the boot unit file -------------------------------

    mod jobs_unit_tests {
        use std::collections::HashMap;
        use std::path::PathBuf;

        fn repo_root() -> PathBuf {
            // crates/os-jobs -> repo root.
            PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .join("..")
                .join("..")
        }

        fn read(rel: &str) -> String {
            let path = repo_root().join(rel);
            std::fs::read_to_string(&path)
                .unwrap_or_else(|e| panic!("read {}: {}", path.display(), e))
        }

        /// The Python test's `sections()` parser: skip blank and `#`
        /// lines; `[Section]` headers; `key=value` pairs (repeat
        /// keys accumulate).
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
                if let Some(sec) = &section {
                    if let Some(eq) = line.find('=') {
                        let key = line[..eq].trim().to_string();
                        let val = line[eq + 1..].trim().to_string();
                        out.entry(sec.clone())
                            .or_default()
                            .entry(key)
                            .or_default()
                            .push(val);
                    }
                }
            }
            out
        }

        #[test]
        fn test_unit_exists() {
            assert!(repo_root().join("os/os/services/relay-jobs.service").exists());
        }

        #[test]
        fn test_unit_ordering_target_and_secrets_gate() {
            let unit = sections(&read("os/os/services/relay-jobs.service"))["Unit"].clone();
            let after = unit.get("After").cloned().unwrap_or_default().join(" ");
            assert!(after.contains("network-online.target"));
            assert!(after.contains("relay-bus.service"));
            assert_eq!(unit.get("PartOf").cloned().unwrap_or_default(), vec!["relay.target"]);
            assert_eq!(
                unit.get("ConditionPathExists").cloned().unwrap_or_default(),
                vec!["/etc/metaos/secrets.env"]
            );
        }

        #[test]
        fn test_service_identity_workdir_and_oneshot() {
            let svc = sections(&read("os/os/services/relay-jobs.service"))["Service"].clone();
            assert_eq!(svc.get("Type").cloned().unwrap_or_default(), vec!["oneshot"]);
            assert_eq!(svc.get("User").cloned().unwrap_or_default(), vec!["relay"]);
            assert_eq!(svc.get("Group").cloned().unwrap_or_default(), vec!["relay"]);
            assert_eq!(
                svc.get("WorkingDirectory").cloned().unwrap_or_default(),
                vec!["/opt/relay"]
            );
            assert_eq!(
                svc.get("EnvironmentFile").cloned().unwrap_or_default(),
                vec!["/etc/metaos/secrets.env"]
            );
        }

        #[test]
        fn test_exec_runs_jobs_sweep_with_no_secret_on_command_line() {
            let svc = sections(&read("os/os/services/relay-jobs.service"))["Service"].clone();
            let exec_start = svc.get("ExecStart").cloned().unwrap_or_default().join(" ");
            assert_eq!(exec_start, "/usr/bin/python3 /opt/relay/jobs.py sweep");
            assert!(!exec_start.contains("token"));
            assert!(!exec_start.contains("secret"));
            let env = svc.get("Environment").cloned().unwrap_or_default().join(" ");
            assert!(env.contains("MUSE_RELAY_TOKEN_FILE=/etc/metaos/token"));
        }

        #[test]
        fn test_install_and_target_want_each_other() {
            let install = sections(&read("os/os/services/relay-jobs.service"))["Install"].clone();
            assert_eq!(
                install.get("WantedBy").cloned().unwrap_or_default(),
                vec!["relay.target"]
            );
            assert!(read("os/os/services/relay.target").contains("relay-jobs.service"));
        }

        #[test]
        fn test_image_route_enables_and_live_route_stages() {
            let build_image = read("os/os/build-image.sh");
            assert!(build_image.contains("relay-jobs.service"));
            assert!(build_image.contains("relay.target.wants"));
            assert!(read("os/os/build-live.sh").contains("services/*.service"));
        }

        #[test]
        fn test_jobspy_is_the_named_process() {
            let jobs = read("os/jobs.py");
            assert!(jobs.contains("\"sweep\""));
            assert!(jobs.contains("set_defaults(fn=cmd_sweep)"));
            assert!(jobs.contains("def cmd_sweep"));
            assert!(jobs.contains("_requeue_fields"));
            assert!(jobs.contains("REQUEUED"));
        }

        #[test]
        fn test_readme_section_and_spec_record() {
            let readme = read("os/os/README.md");
            assert!(readme.contains("OS-014"));
            assert!(readme.contains("relay-jobs.service"));
            let spec = read("os/plan/META_OS.md");
            assert!(spec.contains("OS-014"));
            assert!(spec.contains("relay-jobs.service"));
        }
    }
}
