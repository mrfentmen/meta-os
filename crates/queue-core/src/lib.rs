//! queue-core — Rust port of the Trio queue core (batch B01, owner Rowan).
//!
//! Ports the pure logic of two Python sources, without redesigning them:
//!   * `server/queue/queue_service.py` — `validate_envelope` (B01's source)
//!   * `server/queue/trio_store.py` — key layout + `JobStore` semantics
//!     (the store-agnostic core B02's transports build on)
//!
//! Deliberately zero-dependency (the repo's Node/Python sides are
//! stdlib-only too), so SHA-256 and strict base64 decoding are
//! implemented in-crate. The transport backends (Upstash Redis REST,
//! SQLite fallback) and the HTTP service are later pieces; this crate
//! is the store-agnostic core behind a `Backend` trait, with an
//! in-memory backend for tests and local use.
//!
//! The Python originals stay untouched as fallback until this port
//! compiles AND passes the same tests (bus order 2026-10-30 04:47).
//! JSON parsing lives at the HTTP layer, not here: `validate_envelope`
//! takes a parsed `Envelope`, so the Python "not a JSON object" case
//! is a parse-layer refusal, not a core case.

use std::collections::{BTreeMap, HashMap};
use std::time::{SystemTime, UNIX_EPOCH};

// ---------------------------------------------------------------------------
// SHA-256 (FIPS 180-4), hex output. No dependencies by design.
// ---------------------------------------------------------------------------

const K256: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

/// SHA-256 digest of `data`, lowercase hex — mirrors `hashlib.sha256`.
pub fn sha256_hex(data: &[u8]) -> String {
    let mut h: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
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
            w[i] = u32::from_be_bytes([chunk[4 * i], chunk[4 * i + 1], chunk[4 * i + 2], chunk[4 * i + 3]]);
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
                .wrapping_add(K256[i])
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
// Strict base64 decode (Python `b64decode(validate=True)` semantics).
// ---------------------------------------------------------------------------

fn b64_value(c: u8) -> Option<u8> {
    match c {
        b'A'..=b'Z' => Some(c - b'A'),
        b'a'..=b'z' => Some(c - b'a' + 26),
        b'0'..=b'9' => Some(c - b'0' + 52),
        b'+' => Some(62),
        b'/' => Some(63),
        _ => None,
    }
}

/// Strict base64 decode: rejects non-alphabet characters and bad padding.
pub fn base64_decode(input: &str) -> Result<Vec<u8>, &'static str> {
    let bytes = input.as_bytes();
    if bytes.len() % 4 != 0 {
        return Err("invalid base64 length");
    }
    let mut out = Vec::with_capacity(bytes.len() * 3 / 4);
    for quad in bytes.chunks_exact(4) {
        let mut vals = [0u8; 4];
        let mut pad = 0;
        for (i, &c) in quad.iter().enumerate() {
            if c == b'=' {
                if i < 2 {
                    return Err("invalid base64 padding");
                }
                pad += 1;
                vals[i] = 0;
            } else {
                if pad > 0 {
                    return Err("padding before end of base64 input");
                }
                vals[i] = b64_value(c).ok_or("invalid base64 character")?;
            }
        }
        if pad > 2 {
            return Err("invalid base64 padding");
        }
        out.push((vals[0] << 2) | (vals[1] >> 4));
        if pad < 2 {
            out.push((vals[1] << 4) | (vals[2] >> 2));
        }
        if pad < 1 {
            out.push((vals[2] << 6) | vals[3]);
        }
    }
    Ok(out)
}

// ---------------------------------------------------------------------------
// Envelope validation — mirrors queue_service.validate_envelope.
// ---------------------------------------------------------------------------

/// The image block of a trio-assessment v1 envelope.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EnvelopeImage {
    pub data_url: String,
    pub byte_length: usize,
    pub sha256: String,
}

/// A parsed trio-assessment v1 envelope (JSON parsing is the HTTP layer's
/// job; a non-object body never reaches this struct).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Envelope {
    pub version: i64,
    pub kind: String,
    pub id: String,
    pub product: String,
    pub timestamp: String,
    pub image: EnvelopeImage,
}

/// Deterministic job id — mirrors `buildQueueJob` in server/queue.mjs:
/// `trio-` + first 32 hex of sha256(product + "\0" + timestamp + "\0" + frame).
pub fn deterministic_job_id(product: &str, timestamp: &str, frame: &[u8]) -> String {
    let mut input = Vec::new();
    input.extend_from_slice(product.as_bytes());
    input.push(0);
    input.extend_from_slice(timestamp.as_bytes());
    input.push(0);
    input.extend_from_slice(frame);
    format!("trio-{}", &sha256_hex(&input)[..32])
}

/// Return an error string, or `None` when the envelope is fileable.
/// Error strings match `queue_service.validate_envelope` verbatim.
/// `product_ids` is the caller-supplied product list — the source of
/// truth stays `js/products.js`; this crate never hardcodes a copy.
pub fn validate_envelope(env: &Envelope, product_ids: &[&str]) -> Option<String> {
    if env.version != 1 || env.kind != "trio-assessment" {
        return Some("not a trio-assessment v1 envelope".to_string());
    }
    if env.id.is_empty() {
        return Some("envelope has no job id".to_string());
    }
    if !product_ids.contains(&env.product.as_str()) {
        return Some(format!("unknown product '{}'", env.product));
    }
    if env.timestamp.is_empty() {
        return Some("envelope has no timestamp".to_string());
    }
    let data_url = &env.image.data_url;
    let Some(b64) = data_url.strip_prefix("data:image/jpeg;base64,") else {
        return Some("image.dataUrl is not a JPEG data URL".to_string());
    };
    let raw = match base64_decode(b64) {
        Ok(raw) => raw,
        Err(_) => return Some("image.dataUrl does not base64-decode".to_string()),
    };
    if env.image.byte_length != raw.len() {
        return Some("image.byteLength does not match the decoded frame".to_string());
    }
    if env.image.sha256 != sha256_hex(&raw) {
        return Some("image.sha256 does not match the decoded frame".to_string());
    }
    None
}

// ---------------------------------------------------------------------------
// Key layout — mirrors trio_store.py (namespace via TRIO_JOB_NS there).
// ---------------------------------------------------------------------------

pub fn job_key(ns: &str, jid: &str) -> String {
    format!("{}:{}", ns, jid)
}

pub fn envelope_key(ns: &str, jid: &str) -> String {
    format!("{}:{}:job", ns, jid)
}

pub fn claim_key(ns: &str, jid: &str) -> String {
    format!("{}:{}:claim", ns, jid)
}

pub fn index_key(ns: &str) -> String {
    format!("{}index", ns)
}

/// Result keys always use the "trio" prefix (bus-424 ruling), independent
/// of the job namespace.
pub fn result_key(jid: &str) -> String {
    format!("trio:{}:result", jid)
}

// ---------------------------------------------------------------------------
// Backend trait — the Redis-command surface trio_store.py defines.
// ---------------------------------------------------------------------------

pub trait Backend {
    fn get(&mut self, key: &str) -> Option<String>;
    fn set_body(&mut self, key: &str, body: &str);
    fn delete(&mut self, keys: &[&str]) -> usize;
    fn set_nx_ex(&mut self, key: &str, value: &str, lease_secs: u64) -> bool;
    fn set_xx_ex(&mut self, key: &str, value: &str, lease_secs: u64) -> bool;
    /// Like both Python backends: empty values are skipped, never stored.
    fn hset(&mut self, key: &str, mapping: &[(&str, String)]) -> usize;
    fn hgetall(&mut self, key: &str) -> HashMap<String, String>;
    fn zadd(&mut self, key: &str, score: i64, member: &str);
    fn zrange(&mut self, key: &str) -> Vec<String>;
}

fn now_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

/// In-memory backend with the same command surface and expiry semantics
/// as `LocalSqliteStore` (expired keys read as absent).
#[derive(Default)]
pub struct MemoryBackend {
    kv: HashMap<String, (String, Option<u64>)>,
    hashes: HashMap<String, HashMap<String, String>>,
    zsets: HashMap<String, BTreeMap<String, i64>>,
}

impl MemoryBackend {
    pub fn new() -> Self {
        Self::default()
    }

    fn live(&mut self, key: &str) -> Option<String> {
        let (value, expires) = self.kv.get(key)?.clone();
        if let Some(exp) = expires {
            if now_secs() > exp {
                self.kv.remove(key);
                return None;
            }
        }
        Some(value)
    }
}

impl Backend for MemoryBackend {
    fn get(&mut self, key: &str) -> Option<String> {
        self.live(key)
    }

    fn set_body(&mut self, key: &str, body: &str) {
        self.kv.insert(key.to_string(), (body.to_string(), None));
    }

    fn delete(&mut self, keys: &[&str]) -> usize {
        let mut n = 0;
        for key in keys {
            if self.kv.remove(*key).is_some() {
                n += 1;
            }
            self.hashes.remove(*key);
            self.zsets.remove(*key);
        }
        n
    }

    fn set_nx_ex(&mut self, key: &str, value: &str, lease_secs: u64) -> bool {
        if self.live(key).is_some() {
            return false;
        }
        self.kv.insert(
            key.to_string(),
            (value.to_string(), Some(now_secs() + lease_secs)),
        );
        true
    }

    fn set_xx_ex(&mut self, key: &str, value: &str, lease_secs: u64) -> bool {
        if self.live(key).is_none() {
            return false;
        }
        self.kv.insert(
            key.to_string(),
            (value.to_string(), Some(now_secs() + lease_secs)),
        );
        true
    }

    fn hset(&mut self, key: &str, mapping: &[(&str, String)]) -> usize {
        let hash = self.hashes.entry(key.to_string()).or_default();
        let mut n = 0;
        for (field, value) in mapping {
            if value.is_empty() {
                continue;
            }
            hash.insert(field.to_string(), value.clone());
            n += 1;
        }
        n
    }

    fn hgetall(&mut self, key: &str) -> HashMap<String, String> {
        self.hashes.get(key).cloned().unwrap_or_default()
    }

    fn zadd(&mut self, key: &str, score: i64, member: &str) {
        self.zsets
            .entry(key.to_string())
            .or_default()
            .insert(member.to_string(), score);
    }

    fn zrange(&mut self, key: &str) -> Vec<String> {
        let mut pairs: Vec<(i64, String)> = self
            .zsets
            .get(key)
            .map(|m| m.iter().map(|(member, score)| (*score, member.clone())).collect())
            .unwrap_or_default();
        pairs.sort();
        pairs.into_iter().map(|(_, member)| member).collect()
    }
}

// ---------------------------------------------------------------------------
// JobStore — mirrors trio_store.JobStore method for method.
// ---------------------------------------------------------------------------

pub struct JobStore<B: Backend> {
    pub backend: B,
    pub ns: String,
}

impl<B: Backend> JobStore<B> {
    pub fn new(backend: B, ns: &str) -> Self {
        Self {
            backend,
            ns: ns.to_string(),
        }
    }

    /// File an envelope. Returns (jid, created) — idempotent on the
    /// deterministic id, exactly like the Python submit.
    pub fn submit(&mut self, env: &Envelope, envelope_json: &str, now: i64) -> (String, bool) {
        let jid = env.id.clone();
        if !self.backend.hgetall(&job_key(&self.ns, &jid)).is_empty() {
            return (jid, false);
        }
        self.backend
            .set_body(&envelope_key(&self.ns, &jid), envelope_json);
        self.backend.hset(
            &job_key(&self.ns, &jid),
            &[
                ("status", "open".to_string()),
                ("kind", env.kind.clone()),
                ("version", env.version.to_string()),
                ("product", env.product.clone()),
                ("timestamp", env.timestamp.clone()),
                ("created_at", now.to_string()),
            ],
        );
        self.backend.zadd(&index_key(&self.ns), now, &jid);
        (jid, true)
    }

    pub fn job_fields(&mut self, jid: &str) -> HashMap<String, String> {
        self.backend.hgetall(&job_key(&self.ns, jid))
    }

    pub fn job_envelope(&mut self, jid: &str) -> Option<String> {
        self.backend.get(&envelope_key(&self.ns, jid))
    }

    pub fn open_job_ids(&mut self) -> Vec<String> {
        let mut out = Vec::new();
        for jid in self.backend.zrange(&index_key(&self.ns)) {
            let fields = self.backend.hgetall(&job_key(&self.ns, &jid));
            if !fields.is_empty() && fields.get("status").map(String::as_str) == Some("open") {
                out.push(jid);
            }
        }
        out
    }

    pub fn get_result(&mut self, jid: &str) -> Option<String> {
        self.backend.get(&result_key(jid))
    }

    /// First claim wins (SET NX EX mutex + lease), exactly like jobs.py.
    pub fn claim(&mut self, jid: &str, who: &str, lease: u64, now: i64) -> bool {
        if !self
            .backend
            .set_nx_ex(&claim_key(&self.ns, jid), who, lease)
        {
            return false;
        }
        self.backend.hset(
            &job_key(&self.ns, jid),
            &[
                ("status", "claimed".to_string()),
                ("claim", who.to_string()),
                ("claimed_at", now.to_string()),
                ("lease_until", (now + lease as i64).to_string()),
                ("lease", lease.to_string()),
            ],
        );
        true
    }

    pub fn renew_claim(&mut self, jid: &str, who: &str, lease: u64) -> bool {
        self.backend.set_xx_ex(&claim_key(&self.ns, jid), who, lease)
    }

    pub fn release_claim(&mut self, jid: &str) {
        let key = claim_key(&self.ns, jid);
        let _ = self.backend.delete(&[key.as_str()]);
    }

    pub fn put_result(&mut self, job_id: &str, result_json: &str) {
        self.backend.set_body(&result_key(job_id), result_json);
    }

    pub fn finish(&mut self, jid: &str, status: &str, note: &str, now: i64) {
        self.backend.hset(
            &job_key(&self.ns, jid),
            &[
                ("status", status.to_string()),
                ("note", note.to_string()),
                ("done_at", now.to_string()),
            ],
        );
        self.release_claim(jid);
    }
}

// ---------------------------------------------------------------------------
// Tests — mirrors tests/queue-python/test_queue.py's EnvelopeTests and
// JobStore round-trips (same cases, same expected strings).
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    const PRODUCTS: [&str; 3] = ["vigiles", "ignis", "medicus"];
    const TIMESTAMP: &str = "2026-10-30T06:00:00.000Z";

    fn frame() -> Vec<u8> {
        (0..=255u8).cycle().take(1024).collect()
    }

    fn valid_envelope() -> Envelope {
        let raw = frame();
        Envelope {
            version: 1,
            kind: "trio-assessment".to_string(),
            id: deterministic_job_id("ignis", TIMESTAMP, &raw),
            product: "ignis".to_string(),
            timestamp: TIMESTAMP.to_string(),
            image: EnvelopeImage {
                data_url: format!(
                    "data:image/jpeg;base64,{}",
                    base64_encode_for_test(&raw)
                ),
                byte_length: raw.len(),
                sha256: sha256_hex(&raw),
            },
        }
    }

    // Test-only encoder (the crate itself only needs decoding).
    fn base64_encode_for_test(data: &[u8]) -> String {
        const ALPHABET: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
        let mut out = String::new();
        for chunk in data.chunks(3) {
            let b = [chunk[0], *chunk.get(1).unwrap_or(&0), *chunk.get(2).unwrap_or(&0)];
            let n = ((b[0] as u32) << 16) | ((b[1] as u32) << 8) | b[2] as u32;
            out.push(ALPHABET[(n >> 18) as usize & 63] as char);
            out.push(ALPHABET[(n >> 12) as usize & 63] as char);
            out.push(if chunk.len() > 1 { ALPHABET[(n >> 6) as usize & 63] as char } else { '=' });
            out.push(if chunk.len() > 2 { ALPHABET[n as usize & 63] as char } else { '=' });
        }
        out
    }

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
        // 1,000,000 x 'a' (multi-block padding boundary).
        assert_eq!(
            sha256_hex(&vec![b'a'; 1_000_000]),
            "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0"
        );
    }

    #[test]
    fn base64_round_trip_and_strictness() {
        let raw = frame();
        let enc = base64_encode_for_test(&raw);
        assert_eq!(base64_decode(&enc).unwrap(), raw);
        assert!(base64_decode("AB*C").is_err());
        assert!(base64_decode("ABC").is_err());
        assert!(base64_decode("A===").is_err());
    }

    #[test]
    fn envelope_validates() {
        let env = valid_envelope();
        assert_eq!(validate_envelope(&env, &PRODUCTS), None);
        // Deterministic id matches the node buildQueueJob mirror.
        assert_eq!(env.id, deterministic_job_id("ignis", TIMESTAMP, &frame()));
        assert!(env.id.starts_with("trio-"));
        assert_eq!(env.id.len(), 5 + 32);
    }

    #[test]
    fn envelope_tampered_byte_length_refused() {
        let mut env = valid_envelope();
        env.image.byte_length += 1;
        assert!(validate_envelope(&env, &PRODUCTS)
            .unwrap()
            .contains("byteLength"));
    }

    #[test]
    fn envelope_tampered_sha256_refused() {
        let mut env = valid_envelope();
        env.image.sha256 = "0".repeat(64);
        assert!(validate_envelope(&env, &PRODUCTS)
            .unwrap()
            .contains("sha256"));
    }

    #[test]
    fn envelope_unknown_product_refused() {
        let mut env = valid_envelope();
        env.product = "nope".to_string();
        assert!(validate_envelope(&env, &PRODUCTS)
            .unwrap()
            .contains("unknown product"));
    }

    #[test]
    fn envelope_wrong_kind_refused() {
        let mut env = valid_envelope();
        env.kind = "something-else".to_string();
        assert!(validate_envelope(&env, &PRODUCTS).is_some());
    }

    #[test]
    fn envelope_non_jpeg_data_url_refused() {
        let mut env = valid_envelope();
        env.image.data_url = "data:image/png;base64,AAAA".to_string();
        assert!(validate_envelope(&env, &PRODUCTS)
            .unwrap()
            .contains("JPEG data URL"));
    }

    #[test]
    fn key_layout_matches_python() {
        assert_eq!(job_key("trio", "j1"), "trio:j1");
        assert_eq!(envelope_key("trio", "j1"), "trio:j1:job");
        assert_eq!(claim_key("trio", "j1"), "trio:j1:claim");
        assert_eq!(index_key("trio"), "trioindex");
        // Result prefix is always "trio", independent of namespace.
        assert_eq!(result_key("j1"), "trio:j1:result");
    }

    #[test]
    fn job_store_submit_idempotent_and_round_trip() {
        let mut store = JobStore::new(MemoryBackend::new(), "trio-test");
        let env = valid_envelope();
        let json = "{\"version\":1}";
        let (jid, created) = store.submit(&env, json, 1_000);
        assert!(created);
        assert_eq!(jid, env.id);
        let (jid2, created2) = store.submit(&env, json, 1_001);
        assert_eq!(jid2, jid);
        assert!(!created2);
        assert_eq!(store.job_envelope(&jid).as_deref(), Some(json));
        assert_eq!(store.job_fields(&jid).get("status").map(String::as_str), Some("open"));
        assert_eq!(store.open_job_ids(), vec![jid.clone()]);
    }

    #[test]
    fn job_store_claim_renew_release_finish() {
        let mut store = JobStore::new(MemoryBackend::new(), "trio-test");
        let env = valid_envelope();
        store.submit(&env, "{}", 1_000);
        assert!(store.claim(&env.id, "agent-a", 60, 1_010));
        assert!(!store.claim(&env.id, "agent-b", 60, 1_011));
        assert!(store.renew_claim(&env.id, "agent-a", 60));
        // Faithful to Python: renew is SET XX — it succeeds for any
        // caller while the claim key exists (no owner check in
        // trio_store.renew_claim), it does not prove ownership.
        assert!(store.renew_claim(&env.id, "agent-b", 60));
        assert!(!store.renew_claim("no-such-job", "agent-a", 60));
        assert_eq!(store.job_fields(&env.id).get("status").map(String::as_str), Some("claimed"));
        assert!(store.open_job_ids().is_empty());
        store.release_claim(&env.id);
        assert!(store.claim(&env.id, "agent-b", 60, 1_020));
        store.finish(&env.id, "done", "", 1_030);
        assert_eq!(store.job_fields(&env.id).get("status").map(String::as_str), Some("done"));
        // finish releases the claim: a fresh claim now succeeds.
        assert!(store.claim(&env.id, "agent-c", 60, 1_040));
    }

    #[test]
    fn job_store_result_round_trip() {
        let mut store = JobStore::new(MemoryBackend::new(), "trio-test");
        let env = valid_envelope();
        store.submit(&env, "{}", 1_000);
        assert_eq!(store.get_result(&env.id), None);
        let result = "{\"job_id\":\"x\",\"status\":\"ok\"}";
        store.put_result(&env.id, result);
        assert_eq!(store.get_result(&env.id).as_deref(), Some(result));
    }
}
