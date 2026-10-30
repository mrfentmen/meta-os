//! Capability registry (`os/mos/capabilities.py`).
//!
//! DM secrets: a worker shares its DM dead-drop secret at
//! registration so the overseer can dispatch via DM. DM rooms are
//! obscurity, not encryption — never put real credentials here.

use std::collections::BTreeMap;

/// Namespace prefix, mirroring `MUSE_RELAY_CAPNS` (`muse-bus:cap`).
pub const CAPNS_DEFAULT: &str = "muse-bus:cap";
/// Freshness window in seconds (`MUSE_RELAY_CAP_STALE`, 15 min).
pub const STALE_AFTER_DEFAULT: u64 = 900;

/// One capability record (the hash fields `register` writes).
#[derive(Debug, Clone, Default)]
pub struct Record {
    pub caps: String,
    pub roles: String,
    pub max_jobs: String,
    pub host: String,
    pub updated: String,
    pub dm: Option<String>,
    pub info: Option<String>,
}

/// In-memory capability registry with jobs.py index semantics.
pub struct Registry {
    /// nick -> record (the `<ns>:<nick>` hashes)
    records: BTreeMap<String, Record>,
    /// nick -> updated score (the `<ns>:index` zset)
    index: BTreeMap<String, u64>,
    /// nick -> claimed-job count (the live jobs-index read;
    /// caller-supplied here so the gate pins without a transport)
    claims: BTreeMap<String, usize>,
    pub ns: String,
    pub host: String,
}

impl Registry {
    pub fn new(host: &str) -> Self {
        Registry {
            records: BTreeMap::new(),
            index: BTreeMap::new(),
            claims: BTreeMap::new(),
            ns: CAPNS_DEFAULT.to_string(),
            host: host.to_string(),
        }
    }

    /// Freshness window: env override or the 15-minute default.
    /// Mirrors `STALE_AFTER` (`MUSE_RELAY_CAP_STALE`).
    pub fn stale_after() -> u64 {
        std::env::var("MUSE_RELAY_CAP_STALE")
            .ok()
            .and_then(|v| v.trim().parse::<u64>().ok())
            .unwrap_or(STALE_AFTER_DEFAULT)
    }

    /// Register (or refresh) an agent. Mirrors
    /// `capabilities.register`.
    #[allow(clippy::too_many_arguments)]
    pub fn register(
        &mut self,
        nick: &str,
        capabilities: &[&str],
        roles: &str,
        max_jobs: u64,
        dm_secret: &str,
        info: &str,
        now: u64,
    ) -> Result<(), String> {
        if nick.trim().is_empty() {
            return Err("nick required".to_string());
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
            return Err("at least one capability required".to_string());
        }
        let updated = now.to_string();
        self.records.insert(
            nick.to_string(),
            Record {
                caps: caps.join(","),
                roles: roles.to_string(),
                max_jobs: max_jobs.to_string(),
                host: self.host.clone(),
                updated: updated.clone(),
                dm: if dm_secret.is_empty() {
                    None
                } else {
                    Some(dm_secret.to_string())
                },
                info: if info.is_empty() {
                    None
                } else {
                    Some(info.to_string())
                },
            },
        );
        self.index.insert(nick.to_string(), now);
        Ok(())
    }

    /// Heartbeat: mark this agent fresh. Returns false if unknown.
    pub fn touch(&mut self, nick: &str, now: u64) -> bool {
        if self.records.get(nick).is_none() {
            return false;
        }
        if let Some(rec) = self.records.get_mut(nick) {
            rec.updated = now.to_string();
        }
        self.index.insert(nick.to_string(), now);
        true
    }

    pub fn unregister(&mut self, nick: &str) {
        self.records.remove(nick);
        self.index.remove(nick);
    }

    /// The capability record dict, or `None`. Mirrors
    /// `capabilities.get`.
    pub fn get(&self, nick: &str) -> Option<&Record> {
        self.records.get(nick)
    }

    /// `{nick: record}` for every registered agent.
    pub fn agents(&self) -> BTreeMap<String, &Record> {
        self.records.iter().map(|(k, v)| (k.clone(), v)).collect()
    }

    /// Caller-supplied claim count (the live jobs-index read).
    pub fn set_active_claims(&mut self, nick: &str, n: usize) {
        self.claims.insert(nick.to_string(), n);
    }

    /// How many jobs this nick currently holds claimed.
    pub fn active_claims(&self, nick: &str) -> usize {
        self.claims.get(nick).copied().unwrap_or(0)
    }

    fn fresh(&self, record: &Record, now: u64) -> bool {
        match record.updated.parse::<u64>() {
            Ok(updated) => now.saturating_sub(updated) <= Self::stale_after(),
            Err(_) => false,
        }
    }

    /// Nicks whose caps cover all requirements, fresh, with
    /// capacity. Returns the sorted nick list. Mirrors
    /// `capabilities.find_for`.
    pub fn find_for(&self, requirements: &[&str], now: u64) -> Vec<String> {
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
        let mut out = Vec::new();
        for (nick, rec) in &self.records {
            if !self.fresh(rec, now) {
                continue;
            }
            let caps: Vec<&str> = rec.caps.split(',').collect();
            if !reqs.iter().all(|r| caps.contains(&r.as_str())) {
                continue;
            }
            let max_jobs: usize = rec.max_jobs.parse().unwrap_or(1).max(1);
            if self.active_claims(nick) >= max_jobs {
                continue;
            }
            out.push(nick.clone());
        }
        out.sort();
        out
    }

    /// Unregister agents whose heartbeat is stale. Returns removed
    /// nicks, sorted. Mirrors `capabilities.prune_stale`.
    pub fn prune_stale(&mut self, now: u64) -> Vec<String> {
        let stale: Vec<String> = self
            .records
            .iter()
            .filter(|(_, rec)| !self.fresh(rec, now))
            .map(|(nick, _)| nick.clone())
            .collect();
        for nick in &stale {
            self.unregister(nick);
        }
        let mut out = stale;
        out.sort();
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn reg() -> Registry {
        Registry::new("host-a")
    }

    #[test]
    fn register_and_get() {
        let mut r = reg();
        r.register("w1", &["Python", " testing "], "builder", 2, "s3cret", "x", 1000)
            .unwrap();
        let rec = r.get("w1").unwrap();
        assert_eq!(rec.caps, "python,testing");
        assert_eq!(rec.roles, "builder");
        assert_eq!(rec.max_jobs, "2");
        assert_eq!(rec.dm.as_deref(), Some("s3cret"));
        assert_eq!(rec.host, "host-a");
    }

    #[test]
    fn register_requires_caps() {
        let mut r = reg();
        assert!(r.register("w1", &[], "", 1, "", "", 1000).is_err());
        assert!(r.register("", &["python"], "", 1, "", "", 1000).is_err());
    }

    #[test]
    fn touch_unknown_returns_false() {
        let mut r = reg();
        assert!(!r.touch("ghost", 1000));
    }

    #[test]
    fn touch_refreshes() {
        let mut r = reg();
        r.register("w1", &["python"], "", 1, "", "", 1000).unwrap();
        assert!(r.touch("w1", 1100));
    }

    #[test]
    fn unregister() {
        let mut r = reg();
        r.register("w1", &["python"], "", 1, "", "", 1000).unwrap();
        r.unregister("w1");
        assert!(r.get("w1").is_none());
        assert!(r.agents().is_empty());
    }

    #[test]
    fn find_for_matches_superset() {
        let mut r = reg();
        r.register("w1", &["python", "testing"], "", 1, "", "", 1000).unwrap();
        r.register("w2", &["python"], "", 1, "", "", 1000).unwrap();
        r.register("w3", &["docs"], "", 1, "", "", 1000).unwrap();
        assert_eq!(r.find_for(&["python"], 1100), vec!["w1", "w2"]);
        assert_eq!(r.find_for(&["python", "testing"], 1100), vec!["w1"]);
        assert_eq!(r.find_for(&["rust"], 1100), Vec::<String>::new());
        assert_eq!(r.find_for(&[], 1100), vec!["w1", "w2", "w3"]);
    }

    #[test]
    fn find_for_respects_capacity() {
        let mut r = reg();
        r.register("w1", &["python"], "", 1, "", "", 1000).unwrap();
        // w1 claims a job elsewhere (the live jobs-index read).
        r.set_active_claims("w1", 1);
        assert_eq!(r.find_for(&["python"], 1100), Vec::<String>::new());
    }

    #[test]
    fn find_for_skips_stale() {
        let mut r = reg();
        r.register("w1", &["python"], "", 1, "", "", 1).unwrap();
        // Age the heartbeat past STALE_AFTER.
        assert_eq!(r.find_for(&["python"], 1 + STALE_AFTER_DEFAULT + 1), Vec::<String>::new());
        let pruned = r.prune_stale(1 + STALE_AFTER_DEFAULT + 1);
        assert_eq!(pruned, vec!["w1"]);
        assert!(r.get("w1").is_none());
    }

    #[test]
    fn prune_keeps_fresh() {
        let mut r = reg();
        r.register("w1", &["python"], "", 1, "", "", 1000).unwrap();
        r.register("w2", &["python"], "", 1, "", "", 1000).unwrap();
        assert_eq!(r.prune_stale(1100), Vec::<String>::new());
        assert_eq!(r.agents().len(), 2);
    }

    #[test]
    fn key_names_follow_capns() {
        // Key shape the live transport uses (documented for the
        // wiring half): <ns>:<nick> and <ns>:index.
        let r = reg();
        assert_eq!(format!("{}:w1", r.ns), "muse-bus:cap:w1");
        assert_eq!(format!("{}:index", r.ns), "muse-bus:cap:index");
    }
}
