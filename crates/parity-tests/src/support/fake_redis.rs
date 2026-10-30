//! B31 `fake_redis` — port of `os/tests/fake_redis.py`.
//!
//! In-memory fake of the Upstash REST surface: strings with TTL/SET-NX,
//! hashes, sets, lists (incl. LREM count semantics), sorted sets,
//! `bus_push` log. Injectable clock for expiry tests.

use std::collections::{HashMap, HashSet};

#[derive(Debug, Clone)]
struct StrVal {
    value: String,
    expire_at: Option<f64>,
}

#[derive(Debug, Default)]
pub struct FakeUpstash {
    pub strings: HashMap<String, StrVal>,
    pub hashes: HashMap<String, HashMap<String, String>>,
    pub sets: HashMap<String, HashSet<String>>,
    pub lists: HashMap<String, Vec<String>>,
    pub zsets: HashMap<String, HashMap<String, f64>>,
    pub now_t: f64,
    pub pushes: Vec<(String, String)>,
}

impl FakeUpstash {
    pub fn new() -> Self {
        Self {
            now_t: 1_700_000_000.0,
            ..Default::default()
        }
    }

    pub fn now(&self) -> f64 {
        self.now_t
    }

    pub fn advance(&mut self, secs: f64) {
        self.now_t += secs;
    }

    fn purge(&mut self, key: &str) {
        if let Some(v) = self.strings.get(key) {
            if let Some(exp) = v.expire_at {
                if exp <= self.now_t {
                    self.strings.remove(key);
                }
            }
        }
    }

    pub fn get(&mut self, key: &str) -> Option<String> {
        self.purge(key);
        self.strings.get(key).map(|v| v.value.clone())
    }

    /// SET with NX/XX/EX options. Returns "OK" or None (condition failed).
    pub fn set(&mut self, key: &str, val: &str, nx: bool, xx: bool, ex: Option<f64>) -> Option<String> {
        self.purge(key);
        let cur = self.strings.get(key).map(|v| v.value.clone());
        if nx && cur.is_some() {
            return None;
        }
        if xx && cur.is_none() {
            return None;
        }
        self.strings.insert(
            key.to_string(),
            StrVal {
                value: val.to_string(),
                expire_at: ex.map(|s| self.now_t + s),
            },
        );
        Some("OK".to_string())
    }

    pub fn ttl(&mut self, key: &str) -> i64 {
        self.purge(key);
        match self.strings.get(key) {
            None => -2,
            Some(v) => match v.expire_at {
                None => -1,
                Some(exp) => (exp - self.now_t).max(0.0) as i64,
            },
        }
    }

    pub fn bus_push(&mut self, body: &str, key: Option<&str>) -> usize {
        let k = key.unwrap_or("muse-bus").to_string();
        let lst = self.lists.entry(k.clone()).or_default();
        lst.push(body.to_string());
        self.pushes.push((k, body.to_string()));
        self.pushes.len()
    }

    pub fn lrange(&self, key: &str, start: i64, stop: i64) -> Vec<String> {
        let lst = match self.lists.get(key) {
            Some(l) => l,
            None => return vec![],
        };
        let len = lst.len() as i64;
        let stop = if stop < 0 { len + stop } else { stop };
        if start > stop || start >= len {
            return vec![];
        }
        let s = start.max(0) as usize;
        let e = (stop.min(len - 1) as i64) as usize;
        lst[s..=e].to_vec()
    }

    /// LREM key count value — 0 removes all, >0 from head, <0 from tail.
    pub fn lrem(&mut self, key: &str, count: i64, value: &str) -> usize {
        let lst = match self.lists.get_mut(key) {
            Some(l) => l,
            None => return 0,
        };
        let mut idxs: Vec<usize> = lst
            .iter()
            .enumerate()
            .filter(|(_, v)| v.as_str() == value)
            .map(|(i, _)| i)
            .collect();
        if count > 0 {
            idxs.truncate(count as usize);
        } else if count < 0 {
            let n = (-count) as usize;
            idxs = idxs.into_iter().rev().take(n).collect();
        }
        idxs.sort_unstable_by(|a, b| b.cmp(a));
        for i in idxs.iter() {
            lst.remove(*i);
        }
        idxs.len()
    }

    pub fn zadd(&mut self, key: &str, score: f64, member: &str) {
        self.zsets
            .entry(key.to_string())
            .or_default()
            .insert(member.to_string(), score);
    }

    pub fn zrangebyscore(&self, key: &str, lo: f64, hi: f64) -> Vec<String> {
        let mut pairs: Vec<(&String, f64)> = match self.zsets.get(key) {
            Some(z) => z.iter().map(|(m, s)| (m, *s)).collect(),
            None => return vec![],
        };
        pairs.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap().then(a.0.cmp(b.0)));
        pairs
            .into_iter()
            .filter(|(_, s)| *s >= lo && *s <= hi)
            .map(|(m, _)| m.clone())
            .collect()
    }

    pub fn pushes_to(&self, key: &str) -> Vec<String> {
        self.pushes
            .iter()
            .filter(|(k, _)| k == key)
            .map(|(_, b)| b.clone())
            .collect()
    }
}

impl Default for FakeUpstash {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn set_nx_and_ttl() {
        let mut f = FakeUpstash::new();
        assert_eq!(f.set("k", "v", true, false, None), Some("OK".into()));
        assert_eq!(f.set("k", "v2", true, false, None), None);
        f.set("e", "v", false, false, Some(10.0));
        assert!(f.ttl("e") <= 10 && f.ttl("e") >= 0);
        f.advance(20.0);
        assert_eq!(f.get("e"), None);
        assert_eq!(f.ttl("e"), -2);
        assert_eq!(f.ttl("nope"), -2);
    }

    #[test]
    fn lrem_semantics() {
        let mut f = FakeUpstash::new();
        for v in ["a", "b", "a", "a"] {
            f.bus_push(v, Some("L"));
        }
        assert_eq!(f.lrem("L", 1, "a"), 1);
        assert_eq!(f.lrange("L", 0, -1), vec!["b", "a", "a"]);
        assert_eq!(f.lrem("L", 0, "a"), 2);
        assert_eq!(f.lrange("L", 0, -1), vec!["b"]);
    }

    #[test]
    fn zrangebyscore_order() {
        let mut f = FakeUpstash::new();
        f.zadd("Z", 20.0, "b");
        f.zadd("Z", 10.0, "a");
        assert_eq!(f.zrangebyscore("Z", 0.0, 15.0), vec!["a"]);
    }
}
