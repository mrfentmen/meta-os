//! Crate `os-identity` — Meta OS Rust rebuild skeleton (B00).
//!
//! Batch B18 — Identity & capabilities service. Owner: Milo.
//! Source files this batch ports:
//! - `os/mos/capabilities.py`
//!
//! Port of `os/mos/capabilities.py`: the capability registry. Agents
//! register their capabilities (e.g. python, testing, docs) and
//! heartbeat them. The overseer assigns jobs only to agents whose
//! capabilities cover the job's requirements, who are fresh (recent
//! heartbeat), and who have spare job capacity.
//!
//! Keys (MUSE_RELAY_CAPNS overrides the muse-bus:cap prefix):
//!   <ns>:<nick>   hash: caps/roles/max_jobs/dm/host/updated
//!   <ns>:index    zset nick -> updated (for listing/pruning)
//!
//! DM secrets: a worker shares its DM dead-drop secret at registration
//! so the overseer can dispatch via DM. DM rooms are obscurity, not
//! encryption — this matches the bus threat model (nicks are
//! unauthenticated, friendly closed crew). Never put real credentials
//! here.
//!
//! Port notes (behavior-for-behavior against the Python source):
//! - The Python module talks to Upstash through `relay_common` HTTP
//!   calls (`hgetall`, `hset`, `zadd`, `zrem`, `zrange`, `del`). This
//!   crate is std-only, so storage is behind the [`CapStore`] trait:
//!   the transport adapter implements it (including the URL-quoting
//!   the Python code applies to hash field values and zset members —
//!   quoting is a transport detail, not registry logic, so the trait
//!   takes plain strings). [`MemoryStore`] is the in-memory
//!   implementation used by the tests.
//! - `register`/`touch` read the clock from the system clock, exactly
//!   as the Python code calls `time.time()` at call time. Freshness
//!   itself is the pure function [`is_fresh`], so tests control `now`
//!   directly for stale/fresh cases.
//! - Python reads `MUSE_RELAY_CAPNS` / `MUSE_RELAY_CAP_STALE` at import
//!   time and would raise at import on a non-numeric stale value.
//!   [`Config::from_env`] instead falls back to the defaults on a bad
//!   value (a library must not fail to load over one env var).
//! - Error paths mirror Python exactly: transport errors propagate
//!   from every operation EXCEPT `agents` (index read error -> empty
//!   list) and `active_claims` (jobs read error -> 0). In Rust those
//!   two are the only infallible fallbacks; everything else returns
//!   `Result`.
//! - Python's `active_claims` catches errors only on the jobs-index
//!   read; a per-job read error would propagate. Here the job reads
//!   are folded into one fallible [`CapStore::job_claims`] call, so a
//!   failure returns 0 (the same outcome as the Python zrange-error
//!   path).

use std::collections::{BTreeMap, HashMap};
use std::time::{SystemTime, UNIX_EPOCH};

/// Namespace for capability keys. Default `muse-bus:cap`, overridable
/// with the `MUSE_RELAY_CAPNS` environment variable.
pub const DEFAULT_CAPNS: &str = "muse-bus:cap";

/// Seconds after which an agent without a heartbeat counts as stale.
/// Default 900 (15 min), overridable with `MUSE_RELAY_CAP_STALE`.
pub const DEFAULT_STALE_AFTER: i64 = 900;

/// Registry configuration: key namespace plus the staleness window.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Config {
    pub capns: String,
    pub stale_after: i64,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            capns: DEFAULT_CAPNS.to_string(),
            stale_after: DEFAULT_STALE_AFTER,
        }
    }
}

impl Config {
    /// Read configuration from the environment, as the Python module
    /// does at import time (bad `MUSE_RELAY_CAP_STALE` falls back to
    /// the default instead of raising; see the port notes).
    pub fn from_env() -> Self {
        let mut cfg = Config::default();
        if let Ok(ns) = std::env::var("MUSE_RELAY_CAPNS") {
            if !ns.is_empty() {
                cfg.capns = ns;
            }
        }
        if let Ok(raw) = std::env::var("MUSE_RELAY_CAP_STALE") {
            if let Ok(v) = raw.trim().parse::<i64>() {
                cfg.stale_after = v;
            }
        }
        cfg
    }

    /// The hash key for one agent: `<ns>:<nick>`.
    pub fn key_for(&self, nick: &str) -> String {
        format!("{}:{}", self.capns, nick)
    }

    /// The index key: `<ns>:index`.
    pub fn index(&self) -> String {
        format!("{}:index", self.capns)
    }
}

/// A capability record as stored in the hash: the fields `register`
/// always writes (`caps`, `max_jobs`, `host`, `updated`) plus the
/// optional ones (`roles`, `dm`, `info`) that are only stored when
/// non-empty. Missing fields on read keep the Python defaults
/// (`caps` "", `max_jobs` "1", `updated` "0").
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct AgentRecord {
    pub caps: String,
    pub roles: Option<String>,
    pub max_jobs: String,
    pub host: String,
    pub updated: String,
    pub dm: Option<String>,
    pub info: Option<String>,
}

impl AgentRecord {
    /// Build a record from stored hash fields (unknown fields ignored).
    pub fn from_fields(fields: &HashMap<String, String>) -> Self {
        AgentRecord {
            caps: fields.get("caps").cloned().unwrap_or_default(),
            roles: fields.get("roles").cloned(),
            max_jobs: fields.get("max_jobs").cloned().unwrap_or_else(|| "1".to_string()),
            host: fields.get("host").cloned().unwrap_or_default(),
            updated: fields.get("updated").cloned().unwrap_or_else(|| "0".to_string()),
            dm: fields.get("dm").cloned(),
            info: fields.get("info").cloned(),
        }
    }

    /// Serialize back to stored hash fields, skipping empty values
    /// exactly as the Python `register` does (`if v != ""`).
    pub fn to_fields(&self) -> Vec<(String, String)> {
        let mut out: Vec<(String, String)> = Vec::new();
        let mut push = |k: &str, v: &str| {
            if !v.is_empty() {
                out.push((k.to_string(), v.to_string()));
            }
        };
        push("caps", &self.caps);
        if let Some(roles) = &self.roles {
            push("roles", roles);
        }
        push("max_jobs", &self.max_jobs);
        push("host", &self.host);
        push("updated", &self.updated);
        if let Some(dm) = &self.dm {
            push("dm", dm);
        }
        if let Some(info) = &self.info {
            push("info", info);
        }
        out
    }

    /// The capability set: `caps` split on commas, empties dropped.
    pub fn cap_set(&self) -> Vec<String> {
        self.caps
            .split(',')
            .filter(|c| !c.is_empty())
            .map(|c| c.to_string())
            .collect()
    }
}

/// Error from the backing store. The Python code lets transport
/// exceptions propagate except where it explicitly catches them
/// (`agents` -> empty, `active_claims` -> 0); the registry mirrors
/// those two fallbacks and propagates everything else via `Result`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StoreError(pub String);

impl std::fmt::Display for StoreError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "store error: {}", self.0)
    }
}

impl std::error::Error for StoreError {}

/// One job's claim state, for [`CapabilityRegistry::active_claims`].
/// The Python code reads each job's hash and looks at its `status`
/// and `claim` fields; the transport adapter supplies those pairs.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct JobClaim {
    pub status: String,
    pub claim: String,
}

/// Backing store for the registry: the hash + sorted-set operations
/// the Python code performs through `relay_common`, plus the job-claim
/// scan `active_claims` needs.
pub trait CapStore {
    /// All fields of a hash key, as (field, value) pairs; empty when
    /// the key does not exist.
    fn hgetall(&self, key: &str) -> Result<Vec<(String, String)>, StoreError>;
    /// Set fields on a hash key.
    fn hset(&mut self, key: &str, fields: &[(String, String)]) -> Result<(), StoreError>;
    /// Delete a key entirely.
    fn del(&mut self, key: &str) -> Result<(), StoreError>;
    /// Add a member to a sorted set at a score.
    fn zadd(&mut self, index: &str, score: i64, member: &str) -> Result<(), StoreError>;
    /// Remove a member from a sorted set.
    fn zrem(&mut self, index: &str, member: &str) -> Result<(), StoreError>;
    /// Members of a sorted set in score order (the Python code always
    /// asks for the full `0/-1` range).
    fn zrange(&self, index: &str) -> Result<Vec<String>, StoreError>;
    /// (status, claim) of every job, for `active_claims`.
    fn job_claims(&self) -> Result<Vec<JobClaim>, StoreError>;
}

/// Registration failures, mirroring the Python `ValueError`s.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RegisterError {
    NickRequired,
    AtLeastOneCapabilityRequired,
}

impl std::fmt::Display for RegisterError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            RegisterError::NickRequired => write!(f, "nick required"),
            RegisterError::AtLeastOneCapabilityRequired => {
                write!(f, "at least one capability required")
            }
        }
    }
}

impl std::error::Error for RegisterError {}

/// Errors from [`CapabilityRegistry::register`]: validation failures
/// or a backing-store failure (which Python would raise).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RegistryError {
    Validation(RegisterError),
    Store(StoreError),
}

impl std::fmt::Display for RegistryError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            RegistryError::Validation(e) => write!(f, "{}", e),
            RegistryError::Store(e) => write!(f, "{}", e),
        }
    }
}

impl std::error::Error for RegistryError {}

impl From<StoreError> for RegistryError {
    fn from(e: StoreError) -> Self {
        RegistryError::Store(e)
    }
}

/// Whether a record counts as fresh at `now`: `now - updated <=
/// stale_after`. An unparseable `updated` is not fresh (the Python
/// `ValueError` path returns `False`). A future `updated` is fresh,
/// since the difference is negative.
pub fn is_fresh(record: &AgentRecord, now: i64, stale_after: i64) -> bool {
    match record.updated.parse::<i64>() {
        Ok(updated) => now - updated <= stale_after,
        Err(_) => false,
    }
}

fn now_unix() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0)
}

/// The capability registry: registration, heartbeat, lookup, matching,
/// and pruning over a [`CapStore`].
pub struct CapabilityRegistry<S: CapStore> {
    store: S,
    config: Config,
    /// The overseer-side host id written into each record (the Python
    /// code uses `relay_common.INSTANCE_ID`).
    host: String,
}

impl<S: CapStore> CapabilityRegistry<S> {
    pub fn new(store: S, config: Config, host: String) -> Self {
        CapabilityRegistry { store, config, host }
    }

    pub fn store(&self) -> &S {
        &self.store
    }

    pub fn store_mut(&mut self) -> &mut S {
        &mut self.store
    }

    pub fn config(&self) -> &Config {
        &self.config
    }

    /// Register (or refresh) an agent. Capabilities are stripped,
    /// lowercased, deduplicated, and sorted; empty/blank entries are
    /// dropped. Returns `true`, mirroring the Python return value.
    pub fn register(
        &mut self,
        nick: &str,
        capabilities: &[&str],
        roles: &str,
        max_jobs: i64,
        dm_secret: &str,
        info: &str,
    ) -> Result<bool, RegistryError> {
        if nick.trim().is_empty() {
            return Err(RegistryError::Validation(RegisterError::NickRequired));
        }
        let mut caps: Vec<String> = capabilities
            .iter()
            .filter_map(|c| {
                let c = c.trim().to_lowercase();
                if c.is_empty() {
                    None
                } else {
                    Some(c)
                }
            })
            .collect();
        caps.sort();
        caps.dedup();
        if caps.is_empty() {
            return Err(RegistryError::Validation(
                RegisterError::AtLeastOneCapabilityRequired,
            ));
        }
        let now = now_unix();
        let record = AgentRecord {
            caps: caps.join(","),
            roles: if roles.is_empty() { None } else { Some(roles.to_string()) },
            max_jobs: max_jobs.to_string(),
            host: self.host.clone(),
            updated: now.to_string(),
            dm: if dm_secret.is_empty() { None } else { Some(dm_secret.to_string()) },
            info: if info.is_empty() { None } else { Some(info.to_string()) },
        };
        let fields = record.to_fields();
        let key = self.config.key_for(nick);
        self.store.hset(&key, &fields)?;
        self.store.zadd(&self.config.index(), now, nick)?;
        Ok(true)
    }

    /// Heartbeat: mark this agent fresh. `Ok(false)` if unknown;
    /// transport errors propagate (Python would raise, not return
    /// `False`, on a store failure).
    pub fn touch(&mut self, nick: &str) -> Result<bool, StoreError> {
        if self.get(nick)?.is_none() {
            return Ok(false);
        }
        let now = now_unix();
        let key = self.config.key_for(nick);
        self.store.hset(&key, &[("updated".to_string(), now.to_string())])?;
        self.store.zadd(&self.config.index(), now, nick)?;
        Ok(true)
    }

    /// Unregister an agent. Always `Ok(true)` on success, as Python
    /// always returns `True`; store errors propagate.
    pub fn unregister(&mut self, nick: &str) -> Result<bool, StoreError> {
        let key = self.config.key_for(nick);
        self.store.del(&key)?;
        self.store.zrem(&self.config.index(), nick)?;
        Ok(true)
    }

    /// Return the capability record, or `None` when the agent has no
    /// stored hash (the Python code returns `h or None`). Store
    /// errors propagate.
    pub fn get(&self, nick: &str) -> Result<Option<AgentRecord>, StoreError> {
        let pairs = self.store.hgetall(&self.config.key_for(nick))?;
        if pairs.is_empty() {
            return Ok(None);
        }
        let map: HashMap<String, String> = pairs.into_iter().collect();
        Ok(Some(AgentRecord::from_fields(&map)))
    }

    /// Every registered agent with its record, in index order. An
    /// index read error yields an empty list (the Python `except`
    /// path); agents with no stored hash are skipped; a per-agent
    /// read error propagates (Python would raise out of `agents`).
    pub fn agents(&self) -> Result<Vec<(String, AgentRecord)>, StoreError> {
        let ids = match self.store.zrange(&self.config.index()) {
            Ok(ids) => ids,
            Err(_) => return Ok(Vec::new()),
        };
        let mut out = Vec::new();
        for nick in ids {
            if let Some(rec) = self.get(&nick)? {
                out.push((nick, rec));
            }
        }
        Ok(out)
    }

    /// How many jobs this nick currently holds claimed. A jobs read
    /// error yields 0 (the Python `except` path).
    pub fn active_claims(&self, nick: &str) -> usize {
        match self.store.job_claims() {
            Ok(claims) => claims
                .iter()
                .filter(|c| c.status == "claimed" && c.claim == nick)
                .count(),
            Err(_) => 0,
        }
    }

    /// Nicks whose caps cover all requirements, fresh, with capacity.
    /// Requirements are stripped, lowercased, blanks dropped. Returns
    /// the sorted nick list. An empty requirement set matches every
    /// fresh agent with capacity (empty set is a subset of any caps).
    pub fn find_for(&self, requirements: &[&str]) -> Result<Vec<String>, StoreError> {
        let reqs: Vec<String> = requirements
            .iter()
            .filter_map(|r| {
                let r = r.trim().to_lowercase();
                if r.is_empty() {
                    None
                } else {
                    Some(r)
                }
            })
            .collect();
        let now = now_unix();
        let mut out = Vec::new();
        for (nick, rec) in self.agents()? {
            if !is_fresh(&rec, now, self.config.stale_after) {
                continue;
            }
            let caps: Vec<String> = rec.cap_set();
            if !reqs.iter().all(|r| caps.iter().any(|c| c == r)) {
                continue;
            }
            let max_jobs = rec.max_jobs.parse::<i64>().unwrap_or(1);
            if self.active_claims(&nick) >= std::cmp::max(1, max_jobs) as usize {
                continue;
            }
            out.push(nick);
        }
        out.sort();
        Ok(out)
    }

    /// Unregister agents whose heartbeat is stale. Returns the
    /// removed nicks, sorted.
    pub fn prune_stale(&mut self) -> Result<Vec<String>, StoreError> {
        let now = now_unix();
        let stale: Vec<String> = self
            .agents()?
            .into_iter()
            .filter(|(_, rec)| !is_fresh(rec, now, self.config.stale_after))
            .map(|(nick, _)| nick)
            .collect();
        let mut removed = Vec::new();
        for nick in stale {
            self.unregister(&nick)?;
            removed.push(nick);
        }
        removed.sort();
        Ok(removed)
    }
}

/// In-memory [`CapStore`], for tests and for embedding without a bus.
/// Sorted sets order members by (score, member), matching Upstash
/// `zrange` order for equal scores.
#[derive(Debug, Default)]
pub struct MemoryStore {
    hashes: HashMap<String, HashMap<String, String>>,
    zsets: HashMap<String, BTreeMap<String, i64>>,
    jobs: Vec<JobClaim>,
}

impl MemoryStore {
    pub fn new() -> Self {
        MemoryStore::default()
    }

    /// Directly set a job list for `active_claims` tests.
    pub fn set_jobs(&mut self, jobs: Vec<JobClaim>) {
        self.jobs = jobs;
    }

    /// Directly write a hash (lets tests craft stale or odd records).
    pub fn put_hash(&mut self, key: &str, fields: &[(&str, &str)]) {
        let entry = self.hashes.entry(key.to_string()).or_default();
        for (k, v) in fields {
            entry.insert(k.to_string(), v.to_string());
        }
    }

    /// Directly add an index member at a score.
    pub fn put_index_member(&mut self, index: &str, score: i64, member: &str) {
        self.zsets
            .entry(index.to_string())
            .or_default()
            .insert(member.to_string(), score);
    }
}

impl CapStore for MemoryStore {
    fn hgetall(&self, key: &str) -> Result<Vec<(String, String)>, StoreError> {
        Ok(self
            .hashes
            .get(key)
            .map(|h| h.iter().map(|(k, v)| (k.clone(), v.clone())).collect())
            .unwrap_or_default())
    }

    fn hset(&mut self, key: &str, fields: &[(String, String)]) -> Result<(), StoreError> {
        let entry = self.hashes.entry(key.to_string()).or_default();
        for (k, v) in fields {
            entry.insert(k.clone(), v.clone());
        }
        Ok(())
    }

    fn del(&mut self, key: &str) -> Result<(), StoreError> {
        self.hashes.remove(key);
        Ok(())
    }

    fn zadd(&mut self, index: &str, score: i64, member: &str) -> Result<(), StoreError> {
        self.zsets
            .entry(index.to_string())
            .or_default()
            .insert(member.to_string(), score);
        Ok(())
    }

    fn zrem(&mut self, index: &str, member: &str) -> Result<(), StoreError> {
        if let Some(set) = self.zsets.get_mut(index) {
            set.remove(member);
        }
        Ok(())
    }

    fn zrange(&self, index: &str) -> Result<Vec<String>, StoreError> {
        let mut pairs: Vec<(i64, String)> = self
            .zsets
            .get(index)
            .map(|set| set.iter().map(|(m, s)| (*s, m.clone())).collect())
            .unwrap_or_default();
        pairs.sort();
        Ok(pairs.into_iter().map(|(_, m)| m).collect())
    }

    fn job_claims(&self) -> Result<Vec<JobClaim>, StoreError> {
        Ok(self.jobs.clone())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn registry() -> CapabilityRegistry<MemoryStore> {
        CapabilityRegistry::new(MemoryStore::new(), Config::default(), "test-host".to_string())
    }

    fn reg_with_host(host: &str) -> CapabilityRegistry<MemoryStore> {
        CapabilityRegistry::new(MemoryStore::new(), Config::default(), host.to_string())
    }

    /// A store that fails every operation, for the Python `except` paths.
    #[derive(Debug, Default)]
    struct FailingStore;

    impl CapStore for FailingStore {
        fn hgetall(&self, _key: &str) -> Result<Vec<(String, String)>, StoreError> {
            Err(StoreError("boom".to_string()))
        }

        fn hset(&mut self, _key: &str, _fields: &[(String, String)]) -> Result<(), StoreError> {
            Err(StoreError("boom".to_string()))
        }

        fn del(&mut self, _key: &str) -> Result<(), StoreError> {
            Err(StoreError("boom".to_string()))
        }

        fn zadd(&mut self, _index: &str, _score: i64, _member: &str) -> Result<(), StoreError> {
            Err(StoreError("boom".to_string()))
        }

        fn zrem(&mut self, _index: &str, _member: &str) -> Result<(), StoreError> {
            Err(StoreError("boom".to_string()))
        }

        fn zrange(&self, _index: &str) -> Result<Vec<String>, StoreError> {
            Err(StoreError("boom".to_string()))
        }

        fn job_claims(&self) -> Result<Vec<JobClaim>, StoreError> {
            Err(StoreError("boom".to_string()))
        }
    }

    /// A store whose index read works but whose hash reads fail, so
    /// `agents` hits the propagating (non-caught) error path.
    #[derive(Debug, Default)]
    struct HashFailingStore;

    impl CapStore for HashFailingStore {
        fn hgetall(&self, _key: &str) -> Result<Vec<(String, String)>, StoreError> {
            Err(StoreError("boom".to_string()))
        }

        fn hset(&mut self, _key: &str, _fields: &[(String, String)]) -> Result<(), StoreError> {
            Ok(())
        }

        fn del(&mut self, _key: &str) -> Result<(), StoreError> {
            Ok(())
        }

        fn zadd(&mut self, _index: &str, _score: i64, _member: &str) -> Result<(), StoreError> {
            Ok(())
        }

        fn zrem(&mut self, _index: &str, _member: &str) -> Result<(), StoreError> {
            Ok(())
        }

        fn zrange(&self, _index: &str) -> Result<Vec<String>, StoreError> {
            Ok(vec!["milo".to_string()])
        }

        fn job_claims(&self) -> Result<Vec<JobClaim>, StoreError> {
            Ok(vec![])
        }
    }

    #[test]
    fn config_defaults_and_key_shapes() {
        let cfg = Config::default();
        assert_eq!(cfg.capns, "muse-bus:cap");
        assert_eq!(cfg.stale_after, 900);
        assert_eq!(cfg.key_for("milo"), "muse-bus:cap:milo");
        assert_eq!(cfg.index(), "muse-bus:cap:index");
        let custom = Config {
            capns: "test:cap".to_string(),
            stale_after: 60,
        };
        assert_eq!(custom.key_for("milo"), "test:cap:milo");
        assert_eq!(custom.index(), "test:cap:index");
    }

    #[test]
    fn register_normalizes_caps_sorted_lower_deduped() {
        let mut r = registry();
        assert_eq!(
            r.register("milo", &["Python", " testing ", "python", "DOCS"], "", 1, "", ""),
            Ok(true)
        );
        let rec = r.get("milo").unwrap().expect("registered");
        assert_eq!(rec.caps, "docs,python,testing");
        assert_eq!(rec.host, "test-host");
        assert_eq!(rec.max_jobs, "1");
        assert!(rec.roles.is_none(), "empty roles are not stored");
        assert!(rec.dm.is_none());
        assert!(rec.info.is_none());
        assert!(!rec.updated.is_empty());
    }

    #[test]
    fn register_stores_optional_fields_only_when_nonempty() {
        let mut r = registry();
        r.register("hana", &["docs"], "reviewer", 3, "dm-secret", "on mac")
            .unwrap();
        let rec = r.get("hana").unwrap().unwrap();
        assert_eq!(rec.roles.as_deref(), Some("reviewer"));
        assert_eq!(rec.max_jobs, "3");
        assert_eq!(rec.dm.as_deref(), Some("dm-secret"));
        assert_eq!(rec.info.as_deref(), Some("on mac"));
    }

    #[test]
    fn register_rejects_blank_nick_and_empty_caps() {
        let mut r = registry();
        assert!(matches!(
            r.register("", &["python"], "", 1, "", ""),
            Err(RegistryError::Validation(RegisterError::NickRequired))
        ));
        assert!(matches!(
            r.register("   ", &["python"], "", 1, "", ""),
            Err(RegistryError::Validation(RegisterError::NickRequired))
        ));
        assert!(matches!(
            r.register("milo", &[], "", 1, "", ""),
            Err(RegistryError::Validation(
                RegisterError::AtLeastOneCapabilityRequired
            ))
        ));
        assert!(matches!(
            r.register("milo", &["", "   "], "", 1, "", ""),
            Err(RegistryError::Validation(
                RegisterError::AtLeastOneCapabilityRequired
            ))
        ));
        assert!(r.get("milo").unwrap().is_none(), "failed register stores nothing");
    }

    #[test]
    fn register_refresh_overwrites_caps_and_keeps_index_single() {
        let mut r = registry();
        r.register("milo", &["python"], "", 1, "", "").unwrap();
        r.register("milo", &["testing"], "", 2, "", "").unwrap();
        let rec = r.get("milo").unwrap().unwrap();
        assert_eq!(rec.caps, "testing");
        assert_eq!(rec.max_jobs, "2");
        let agents = r.agents().unwrap();
        assert_eq!(agents.len(), 1, "re-register must not duplicate the index entry");
    }

    #[test]
    fn register_empty_host_is_not_stored() {
        // Faithful oddity: the Python pairs filter drops empty values,
        // so an empty INSTANCE_ID leaves no host field at all.
        let mut r = reg_with_host("");
        r.register("milo", &["python"], "", 1, "", "").unwrap();
        let stored = r.store().hashes.get("muse-bus:cap:milo").unwrap();
        assert!(!stored.contains_key("host"));
        assert_eq!(r.get("milo").unwrap().unwrap().host, "");
    }

    #[test]
    fn get_returns_none_for_unknown() {
        let r = registry();
        assert!(r.get("ghost").unwrap().is_none());
    }

    #[test]
    fn touch_heartbeat_unknown_false_known_true() {
        let mut r = registry();
        assert!(!r.touch("ghost").unwrap(), "touch of unknown agent is False");
        r.register("milo", &["python"], "", 1, "", "").unwrap();
        assert!(r.touch("milo").unwrap());
        assert!(r.get("milo").unwrap().is_some());
    }

    #[test]
    fn unregister_removes_hash_and_index() {
        let mut r = registry();
        r.register("milo", &["python"], "", 1, "", "").unwrap();
        assert!(r.unregister("milo").unwrap());
        assert!(r.get("milo").unwrap().is_none());
        assert!(r.agents().unwrap().is_empty());
        // Unregistering an unknown nick still returns True (Python).
        assert!(r.unregister("ghost").unwrap());
    }

    #[test]
    fn agents_skips_index_members_without_a_hash() {
        let mut r = registry();
        r.register("milo", &["python"], "", 1, "", "").unwrap();
        // An index member with no hash (dangling entry) is skipped.
        r.store_mut().put_index_member("muse-bus:cap:index", 1, "ghost");
        let names: Vec<String> = r
            .agents()
            .unwrap()
            .into_iter()
            .map(|(n, _)| n)
            .collect();
        assert_eq!(names, vec!["milo"]);
    }

    #[test]
    fn is_fresh_boundaries_and_bad_updated() {
        let fresh = AgentRecord {
            updated: "1000".to_string(),
            ..Default::default()
        };
        assert!(is_fresh(&fresh, 1900, 900), "exactly stale_after is fresh (<=)");
        assert!(!is_fresh(&fresh, 1901, 900));
        assert!(is_fresh(&fresh, 500, 900), "future updated is fresh (negative diff)");
        let bad = AgentRecord {
            updated: "not-a-number".to_string(),
            ..Default::default()
        };
        assert!(!is_fresh(&bad, 1900, 900), "unparseable updated is not fresh");
        let missing = AgentRecord::default();
        // Default updated is "0": ancient, hence stale at any real now.
        assert!(!is_fresh(&missing, 1900, 900));
    }

    #[test]
    fn find_for_matches_caps_freshness_and_capacity() {
        let mut r = registry();
        r.register("milo", &["python", "testing"], "", 1, "", "").unwrap();
        r.register("rowan", &["python"], "", 5, "", "").unwrap();
        // One claimed job fills milo's capacity of 1.
        r.store_mut().set_jobs(vec![JobClaim {
            status: "claimed".to_string(),
            claim: "milo".to_string(),
        }]);
        assert_eq!(r.find_for(&["python"]).unwrap(), vec!["rowan"]);
        assert_eq!(r.find_for(&["PYTHON"]).unwrap(), vec!["rowan"], "requirements lowercase");
        assert_eq!(r.find_for(&["python", "testing"]).unwrap(), Vec::<String>::new());
        assert_eq!(
            r.find_for(&[]).unwrap(),
            vec!["rowan"],
            "empty reqs match fresh agents with capacity"
        );
    }

    #[test]
    fn find_for_ignores_non_claimed_and_other_agents_jobs() {
        let mut r = registry();
        r.register("milo", &["python"], "", 1, "", "").unwrap();
        r.store_mut().set_jobs(vec![
            JobClaim { status: "done".to_string(), claim: "milo".to_string() },
            JobClaim { status: "claimed".to_string(), claim: "rowan".to_string() },
        ]);
        assert_eq!(r.active_claims("milo"), 0);
        assert_eq!(r.find_for(&["python"]).unwrap(), vec!["milo"]);
    }

    #[test]
    fn find_for_bad_max_jobs_falls_back_to_one() {
        let mut r = registry();
        r.register("milo", &["python"], "", 1, "", "").unwrap();
        // Corrupt the stored max_jobs to a non-number: Python falls back to 1.
        r.store_mut().put_hash("muse-bus:cap:milo", &[("max_jobs", "many")]);
        r.store_mut().set_jobs(vec![JobClaim {
            status: "claimed".to_string(),
            claim: "milo".to_string(),
        }]);
        assert_eq!(r.find_for(&["python"]).unwrap(), Vec::<String>::new());
    }

    #[test]
    fn find_for_skips_stale_agents() {
        let mut r = registry();
        r.register("milo", &["python"], "", 1, "", "").unwrap();
        // Backdate milo's heartbeat past the stale window.
        let stale = now_unix() - 3600;
        r.store_mut().put_hash("muse-bus:cap:milo", &[("updated", &stale.to_string())]);
        r.store_mut().put_index_member("muse-bus:cap:index", stale, "milo");
        assert_eq!(r.find_for(&["python"]).unwrap(), Vec::<String>::new());
    }

    #[test]
    fn find_for_results_are_sorted() {
        let mut r = registry();
        r.register("rowan", &["python"], "", 1, "", "").unwrap();
        r.register("milo", &["python"], "", 1, "", "").unwrap();
        r.register("hana", &["python"], "", 1, "", "").unwrap();
        assert_eq!(r.find_for(&["python"]).unwrap(), vec!["hana", "milo", "rowan"]);
    }

    #[test]
    fn prune_stale_removes_only_stale_sorted() {
        let mut r = registry();
        r.register("milo", &["python"], "", 1, "", "").unwrap();
        r.register("rowan", &["python"], "", 1, "", "").unwrap();
        r.register("hana", &["python"], "", 1, "", "").unwrap();
        let stale = now_unix() - 3600;
        for nick in ["rowan", "hana"] {
            r.store_mut().put_hash(
                &format!("muse-bus:cap:{}", nick),
                &[("updated", &stale.to_string())],
            );
            r.store_mut().put_index_member("muse-bus:cap:index", stale, nick);
        }
        assert_eq!(r.prune_stale().unwrap(), vec!["hana", "rowan"]);
        let names: Vec<String> = r
            .agents()
            .unwrap()
            .into_iter()
            .map(|(n, _)| n)
            .collect();
        assert_eq!(names, vec!["milo"]);
    }

    #[test]
    fn store_error_paths_match_python_fallbacks() {
        let r = CapabilityRegistry::new(FailingStore, Config::default(), "h".to_string());
        assert!(r.agents().unwrap().is_empty(), "agents() catches index errors -> empty");
        assert_eq!(r.active_claims("milo"), 0, "active_claims catches errors -> 0");
        assert!(r.get("milo").is_err(), "get() propagates store errors");
        assert_eq!(
            r.find_for(&["python"]).unwrap(),
            Vec::<String>::new(),
            "find_for over an empty agents() list"
        );
        let r2 = CapabilityRegistry::new(HashFailingStore, Config::default(), "h".to_string());
        assert!(
            r2.agents().is_err(),
            "agents() propagates per-agent read errors (only the index read is caught)"
        );
    }

    #[test]
    fn record_fields_round_trip_skip_empty() {
        let rec = AgentRecord {
            caps: "python,testing".to_string(),
            roles: None,
            max_jobs: "2".to_string(),
            host: "h".to_string(),
            updated: "123".to_string(),
            dm: None,
            info: Some("note".to_string()),
        };
        let fields = rec.to_fields();
        let map: HashMap<String, String> = fields.into_iter().collect();
        assert!(!map.contains_key("roles"));
        assert!(!map.contains_key("dm"));
        assert_eq!(map.get("info").map(|s| s.as_str()), Some("note"));
        let back = AgentRecord::from_fields(&map);
        assert_eq!(back, rec);
    }

    #[test]
    fn cap_set_drops_empties_from_ragged_caps() {
        let rec = AgentRecord {
            caps: "python,,testing,".to_string(),
            ..Default::default()
        };
        assert_eq!(rec.cap_set(), vec!["python", "testing"]);
    }
}
