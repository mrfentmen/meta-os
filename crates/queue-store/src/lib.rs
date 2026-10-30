//! Crate `queue-store` — Meta OS Rust rebuild (B02).
//!
//! Batch B02 — Queue store (Upstash store + repo layer). Owner: Rowan.
//! Sources: `server/queue/trio_repo.py`, `server/queue/trio_store.py`.
//! Port behavior, do not redesign.
//!
//! Notes on port oddities:
//! - `trio_repo.py` loads `js/products.js` by spawning node. The Rust port
//!   embeds the three product records so the queue stays offline; the JS
//!   file remains the source of truth and any id/category drift is a bug.
//! - `LocalSqliteStore` uses rusqlite (bundled); semantics match the
//!   Python sqlite3 fallback including NX/XX lease expiry.

use std::collections::{BTreeMap, HashMap};
use std::sync::{Mutex, MutexGuard};
use std::time::{SystemTime, UNIX_EPOCH};

use serde_json::Value;

// ---------------------------------------------------------------------------
// Repo layer (trio_repo.py)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct ProductProfile {
    pub id: &'static str,
    pub display_name: &'static str,
    pub department: &'static str,
    pub categories: &'static [&'static str],
    pub limitations: &'static str,
}

pub static PRODUCTS: &[ProductProfile] = &[
    ProductProfile {
        id: "vigiles",
        display_name: "Meta Vigiles",
        department: "NYPD-oriented — visual incident awareness",
        categories: &[
            "normal activity",
            "energetic movement",
            "ambiguous gesture",
            "staged verbal dispute",
            "physical contact",
            "person down",
            "possible altercation",
            "indeterminate",
        ],
        limitations: "Prototype for visual incident awareness. No face recognition, no identity tracking, no automatic dispatch.",
    },
    ProductProfile {
        id: "ignis",
        display_name: "Meta Ignis",
        department: "FDNY-oriented — fire and smoke hazard awareness",
        categories: &[
            "visible smoke",
            "visible flame",
            "steam or fog",
            "flame-like lighting",
            "obscured or distant hazard",
            "no hazard visible",
            "indeterminate",
        ],
        limitations: "Not a certified fire-detection system. No automatic dispatch.",
    },
    ProductProfile {
        id: "medicus",
        display_name: "Meta Medicus",
        department: "FDNY EMS-oriented — medical incident scene awareness",
        categories: &[
            "person on ground",
            "crowd gathered around a person",
            "vehicle collision scene",
            "blocked crew access",
            "person motionless",
            "normal activity",
            "indeterminate",
        ],
        limitations: "Scene awareness only. No diagnosis, no dispatch. Every assessment requires human verification.",
    },
];

pub fn product_ids() -> HashMap<String, ()> {
    PRODUCTS.iter().map(|p| (p.id.to_string(), ())).collect()
}

pub fn product_profile(product: &str) -> Option<&'static ProductProfile> {
    PRODUCTS.iter().find(|p| p.id == product)
}

// ---------------------------------------------------------------------------
// Key layout + host resolution (trio_store.py)
// ---------------------------------------------------------------------------

pub fn namespace() -> String {
    std::env::var("TRIO_JOB_NS").unwrap_or_else(|_| "trio".to_string())
}

pub const RESULT_PREFIX: &str = "trio";

pub fn job_key(ns: &str, jid: &str) -> String {
    format!("{ns}:{jid}")
}
pub fn envelope_key(ns: &str, jid: &str) -> String {
    format!("{ns}:{jid}:job")
}
pub fn claim_key(ns: &str, jid: &str) -> String {
    format!("{ns}:{jid}:claim")
}
pub fn index_key(ns: &str) -> String {
    format!("{ns}index")
}
pub fn result_key(jid: &str) -> String {
    format!("{RESULT_PREFIX}:{jid}:result")
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TrioStoreConfigError(pub String);

impl std::fmt::Display for TrioStoreConfigError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}
impl std::error::Error for TrioStoreConfigError {}

fn host_of_url(candidate: &str) -> Option<String> {
    let c = candidate.trim();
    if c.is_empty() {
        return None;
    }
    // Bare host or full URL — take hostname.
    let with_scheme = if c.contains("://") { c.to_string() } else { format!("https://{c}") };
    // Minimal parse: strip scheme, then host up to / : ? #.
    let after = with_scheme.splitn(2, "://").nth(1)?;
    let host = after.split(['/', '?', '#']).next()?.split(':').next()?;
    if host.is_empty() { None } else { Some(host.to_string()) }
}

pub fn resolve_upstash_host(env_host: &str, credential_rest_url: Option<&str>) -> Result<String, TrioStoreConfigError> {
    let env = env_host.trim();
    if !env.is_empty() {
        if let Some(h) = host_of_url(env) {
            return Ok(h);
        }
    }
    if let Some(u) = credential_rest_url {
        if let Some(h) = host_of_url(u) {
            return Ok(h);
        }
    }
    Err(TrioStoreConfigError(
        "Upstash store host is not configured: set TRIO_UPSTASH_HOST to the store host (or its full REST URL), or store the REST URL on the custom.upstash credential record. The host is deployment configuration and is never hardcoded.".to_string(),
    ))
}

pub fn resolve_upstash_host_from_env() -> Result<String, TrioStoreConfigError> {
    let env = std::env::var("TRIO_UPSTASH_HOST").unwrap_or_default();
    resolve_upstash_host(&env, None)
}

// ---------------------------------------------------------------------------
// Backend surface
// ---------------------------------------------------------------------------

pub trait StoreBackend {
    fn ping(&mut self) -> bool;
    fn get(&mut self, key: &str) -> Option<String>;
    fn set_body(&mut self, key: &str, body: &str) -> String;
    fn delete(&mut self, keys: &[&str]) -> usize;
    fn set_nx_ex(&mut self, key: &str, value: &str, lease_secs: u64) -> bool;
    fn set_xx_ex(&mut self, key: &str, value: &str, lease_secs: u64) -> bool;
    fn hset(&mut self, key: &str, mapping: &HashMap<String, String>) -> usize;
    fn hgetall(&mut self, key: &str) -> HashMap<String, String>;
    fn zadd(&mut self, key: &str, score: i64, member: &str) -> usize;
    fn zrange(&mut self, key: &str) -> Vec<String>;
}

fn now_secs() -> i64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs() as i64).unwrap_or(0)
}

/// In-memory backend — test stand-in with the same NX/XX lease semantics.
#[derive(Default)]
pub struct InMemoryStore {
    kv: HashMap<String, (String, Option<i64>)>,
    hashes: HashMap<String, HashMap<String, String>>,
    zsets: HashMap<String, BTreeMap<String, i64>>,
}

impl InMemoryStore {
    fn live(&mut self, key: &str) -> Option<String> {
        let now = now_secs();
        if let Some((v, exp)) = self.kv.get(key) {
            if let Some(e) = exp {
                if now > *e {
                    self.kv.remove(key);
                    return None;
                }
            }
            return Some(v.clone());
        }
        None
    }
}

impl StoreBackend for InMemoryStore {
    fn ping(&mut self) -> bool { true }
    fn get(&mut self, key: &str) -> Option<String> { self.live(key) }
    fn set_body(&mut self, key: &str, body: &str) -> String {
        self.kv.insert(key.to_string(), (body.to_string(), None));
        "OK".to_string()
    }
    fn delete(&mut self, keys: &[&str]) -> usize {
        let mut n = 0;
        for k in keys {
            if self.kv.remove(*k).is_some() { n += 1; }
            self.hashes.remove(*k);
            self.zsets.remove(*k);
        }
        n
    }
    fn set_nx_ex(&mut self, key: &str, value: &str, lease_secs: u64) -> bool {
        if self.live(key).is_some() { return false; }
        self.kv.insert(key.to_string(), (value.to_string(), Some(now_secs() + lease_secs as i64)));
        true
    }
    fn set_xx_ex(&mut self, key: &str, value: &str, lease_secs: u64) -> bool {
        if self.live(key).is_none() { return false; }
        self.kv.insert(key.to_string(), (value.to_string(), Some(now_secs() + lease_secs as i64)));
        true
    }
    fn hset(&mut self, key: &str, mapping: &HashMap<String, String>) -> usize {
        let h = self.hashes.entry(key.to_string()).or_default();
        let mut n = 0;
        for (f, v) in mapping {
            if v.is_empty() { continue; }
            h.insert(f.clone(), v.clone());
            n += 1;
        }
        n
    }
    fn hgetall(&mut self, key: &str) -> HashMap<String, String> {
        self.hashes.get(key).cloned().unwrap_or_default()
    }
    fn zadd(&mut self, key: &str, score: i64, member: &str) -> usize {
        self.zsets.entry(key.to_string()).or_default().insert(member.to_string(), score);
        1
    }
    fn zrange(&mut self, key: &str) -> Vec<String> {
        match self.zsets.get(key) {
            None => vec![],
            Some(m) => {
                let mut v: Vec<_> = m.iter().collect();
                v.sort_by_key(|(_, s)| **s);
                v.into_iter().map(|(k, _)| k.clone()).collect()
            }
        }
    }
}

/// SQLite fallback — mirrors `LocalSqliteStore` over a file.
pub struct SqliteStore {
    conn: Mutex<rusqlite::Connection>,
}

impl SqliteStore {
    pub fn open(path: &str) -> rusqlite::Result<Self> {
        let conn = rusqlite::Connection::open(path)?;
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT, expires INTEGER);
             CREATE TABLE IF NOT EXISTS hashes (key TEXT, field TEXT, value TEXT, PRIMARY KEY (key, field));
             CREATE TABLE IF NOT EXISTS zsets (key TEXT, member TEXT, score REAL, PRIMARY KEY (key, member));",
        )?;
        Ok(Self { conn: Mutex::new(conn) })
    }
    fn lock(&self) -> MutexGuard<'_, rusqlite::Connection> {
        self.conn.lock().unwrap()
    }
}

impl StoreBackend for SqliteStore {
    fn ping(&mut self) -> bool { true }
    fn get(&mut self, key: &str) -> Option<String> {
        let c = self.lock();
        let row: (String, Option<i64>) = c.query_row(
            "SELECT value, expires FROM kv WHERE key=?1", [key],
            |r| Ok((r.get::<_, String>(0)?, r.get::<_, Option<i64>>(1)?)),
        ).ok()?;
        let (v, exp) = row;
        if let Some(e) = exp {
            if now_secs() > e {
                drop(c);
                let c = self.lock();
                let _ = c.execute("DELETE FROM kv WHERE key=?1", [key]);
                return None;
            }
        }
        Some(v)
    }
    fn set_body(&mut self, key: &str, body: &str) -> String {
        let c = self.lock();
        let _ = c.execute("INSERT OR REPLACE INTO kv VALUES (?1,?2,NULL)", [key, body]);
        "OK".to_string()
    }
    fn delete(&mut self, keys: &[&str]) -> usize {
        let c = self.lock();
        let mut n = 0;
        for k in keys {
            n += c.execute("DELETE FROM kv WHERE key=?1", [*k]).unwrap_or(0) as usize;
            let _ = c.execute("DELETE FROM hashes WHERE key=?1", [*k]);
            let _ = c.execute("DELETE FROM zsets WHERE key=?1", [*k]);
        }
        n
    }
    fn set_nx_ex(&mut self, key: &str, value: &str, lease_secs: u64) -> bool {
        if self.get(key).is_some() { return false; }
        let c = self.lock();
        c.execute("INSERT INTO kv VALUES (?1,?2,?3)",
            rusqlite::params![key, value, now_secs() + lease_secs as i64]).is_ok()
    }
    fn set_xx_ex(&mut self, key: &str, value: &str, lease_secs: u64) -> bool {
        if self.get(key).is_none() { return false; }
        let c = self.lock();
        c.execute("UPDATE kv SET value=?1, expires=?2 WHERE key=?3",
            rusqlite::params![value, now_secs() + lease_secs as i64, key]).is_ok()
    }
    fn hset(&mut self, key: &str, mapping: &HashMap<String, String>) -> usize {
        let c = self.lock();
        let mut n = 0;
        for (f, v) in mapping {
            if v.is_empty() { continue; }
            if c.execute("INSERT OR REPLACE INTO hashes VALUES (?1,?2,?3)",
                rusqlite::params![key, f, v]).is_ok() { n += 1; }
        }
        n
    }
    fn hgetall(&mut self, key: &str) -> HashMap<String, String> {
        let c = self.lock();
        let mut out = HashMap::new();
        if let Ok(mut st) = c.prepare("SELECT field, value FROM hashes WHERE key=?1") {
            if let Ok(rows) = st.query_map([key], |r| Ok((r.get::<_, String>(0)?, r.get::<_, String>(1)?))) {
                for r in rows.flatten() { out.insert(r.0, r.1); }
            }
        }
        out
    }
    fn zadd(&mut self, key: &str, score: i64, member: &str) -> usize {
        let c = self.lock();
        c.execute("INSERT OR REPLACE INTO zsets VALUES (?1,?2,?3)",
            rusqlite::params![key, member, score as f64]).unwrap_or(0) as usize
    }
    fn zrange(&mut self, key: &str) -> Vec<String> {
        let c = self.lock();
        let mut out = vec![];
        if let Ok(mut st) = c.prepare("SELECT member FROM zsets WHERE key=?1 ORDER BY score") {
            if let Ok(rows) = st.query_map([key], |r| r.get::<_, String>(0)) {
                for r in rows.flatten() { out.push(r); }
            }
        }
        out
    }
}

// ---------------------------------------------------------------------------
// Job semantics
// ---------------------------------------------------------------------------

pub struct JobStore<B: StoreBackend> {
    pub backend: B,
    pub ns: String,
}

impl<B: StoreBackend> JobStore<B> {
    pub fn new(backend: B, ns: &str) -> Self {
        Self { backend, ns: ns.to_string() }
    }
    pub fn submit(&mut self, envelope: &Value) -> (String, bool) {
        let jid = envelope.get("id").and_then(Value::as_str).unwrap_or("").to_string();
        if !self.backend.hgetall(&job_key(&self.ns, &jid)).is_empty() {
            return (jid, false);
        }
        let now = now_secs();
        self.backend.set_body(&envelope_key(&self.ns, &jid), &envelope.to_string());
        let mut m = HashMap::new();
        m.insert("status".to_string(), "open".to_string());
        m.insert("kind".to_string(), envelope.get("kind").and_then(Value::as_str).unwrap_or("").to_string());
        m.insert("version".to_string(), envelope.get("version").map(|v| v.to_string()).unwrap_or_default());
        m.insert("product".to_string(), envelope.get("product").and_then(Value::as_str).unwrap_or("").to_string());
        m.insert("timestamp".to_string(), envelope.get("timestamp").and_then(Value::as_str).unwrap_or("").to_string());
        m.insert("created_at".to_string(), now.to_string());
        self.backend.hset(&job_key(&self.ns, &jid), &m);
        self.backend.zadd(&index_key(&self.ns), now, &jid);
        (jid, true)
    }
    pub fn job_fields(&mut self, jid: &str) -> HashMap<String, String> {
        self.backend.hgetall(&job_key(&self.ns, jid))
    }
    pub fn job_envelope(&mut self, jid: &str) -> Option<Value> {
        let raw = self.backend.get(&envelope_key(&self.ns, jid))?;
        serde_json::from_str::<Value>(&raw).ok().filter(|v| v.is_object())
    }
    pub fn open_job_ids(&mut self) -> Vec<String> {
        self.backend.zrange(&index_key(&self.ns)).into_iter()
            .filter(|jid| self.backend.hgetall(&job_key(&self.ns, jid)).get("status").map(|s| s == "open").unwrap_or(false))
            .collect()
    }
    pub fn get_result(&mut self, jid: &str) -> Option<Value> {
        let raw = self.backend.get(&result_key(jid))?;
        serde_json::from_str::<Value>(&raw).ok().filter(|v| v.is_object())
    }
    pub fn claim(&mut self, jid: &str, who: &str, lease: u64) -> bool {
        if !self.backend.set_nx_ex(&claim_key(&self.ns, jid), who, lease) { return false; }
        let now = now_secs();
        let mut m = HashMap::new();
        m.insert("status".to_string(), "claimed".to_string());
        m.insert("claim".to_string(), who.to_string());
        m.insert("claimed_at".to_string(), now.to_string());
        m.insert("lease_until".to_string(), (now + lease as i64).to_string());
        m.insert("lease".to_string(), lease.to_string());
        self.backend.hset(&job_key(&self.ns, jid), &m);
        true
    }
    pub fn renew_claim(&mut self, jid: &str, who: &str, lease: u64) -> bool {
        self.backend.set_xx_ex(&claim_key(&self.ns, jid), who, lease)
    }
    pub fn release_claim(&mut self, jid: &str) {
        let k = claim_key(&self.ns, jid);
        self.backend.delete(&[k.as_str()]);
    }
    pub fn put_result(&mut self, result: &Value) {
        let jid = result.get("job_id").and_then(Value::as_str).unwrap_or("");
        self.backend.set_body(&result_key(jid), &result.to_string());
    }
    pub fn finish(&mut self, jid: &str, status: &str, note: &str) {
        let mut m = HashMap::new();
        m.insert("status".to_string(), status.to_string());
        m.insert("note".to_string(), note.to_string());
        m.insert("done_at".to_string(), now_secs().to_string());
        self.backend.hset(&job_key(&self.ns, jid), &m);
        self.release_claim(jid);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_env_host_wins() {
        assert_eq!(resolve_upstash_host("fake-store.example.invalid", None).unwrap(), "fake-store.example.invalid");
    }
    #[test]
    fn test_env_full_url_yields_its_host() {
        assert_eq!(resolve_upstash_host("https://fake-store.example.invalid/", None).unwrap(), "fake-store.example.invalid");
    }
    #[test]
    fn test_unconfigured_raises_typed_error() {
        let e = resolve_upstash_host("", None).unwrap_err();
        assert!(e.0.contains("TRIO_UPSTASH_HOST"));
    }
    #[test]
    fn test_result_round_trip_exact_keys() {
        let mut jobs = JobStore::new(InMemoryStore::default(), "trio-test");
        let result = serde_json::json!({
            "job_id": "trio-abc", "status": "ok", "assessment": {"x": 1},
            "error": null, "model": "muse-spark-1.3", "latency_ms": 12,
            "completed_at": "2026-10-30T06:01:00.000Z",
        });
        jobs.put_result(&result);
        let got = jobs.get_result("trio-abc").unwrap();
        assert_eq!(got, result);
        assert_eq!(result_key("trio-abc"), "trio:trio-abc:result");
    }
    #[test]
    fn test_store_full_round_trip() {
        let mut jobs = JobStore::new(InMemoryStore::default(), "trio-test");
        let env = serde_json::json!({"id": "trio-hosttest", "kind": "trio-assessment", "version": 1, "product": "ignis", "timestamp": "2026-10-30T06:00:00.000Z"});
        let (jid, created) = jobs.submit(&env);
        assert!(created);
        assert_eq!(jobs.open_job_ids(), vec![jid.clone()]);
        assert!(jobs.claim(&jid, "tester", 60));
        assert!(!jobs.claim(&jid, "other", 60));
        jobs.put_result(&serde_json::json!({"job_id": jid, "status": "ok"}));
        assert_eq!(jobs.get_result(&jid).unwrap()["status"], "ok");
        jobs.finish(&jid, "done", "");
        assert_eq!(jobs.job_fields(&jid)["status"], "done");
    }
}
