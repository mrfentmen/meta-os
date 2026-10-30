//! B31 `helpers` — port of `os/tests/helpers.py`.
//!
//! Python `RelayTestCase` patches `relay_common.api_get/api_post/bus_push`
//! onto [`super::fake_redis::FakeUpstash`], redirects seen/store paths
//! into a tmp dir, and isolates the job namespace. This module ports the
//! shape: tmp-dir routing, nick switching, push inspection.

use super::fake_redis::FakeUpstash;
use std::path::PathBuf;

/// Isolated harness: fake bus + tmp dirs for seen/store files.
pub struct Harness {
    pub fake: FakeUpstash,
    pub tmp: PathBuf,
    pub nick: String,
    pub instance: String,
}

impl Harness {
    pub fn new(nick: &str, instance: &str) -> Self {
        let nanos = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or(0);
        let tmp = std::env::temp_dir().join(format!("parity-{nanos}-{}", std::process::id()));
        std::fs::create_dir_all(&tmp).ok();
        Self {
            fake: FakeUpstash::new(),
            tmp,
            nick: nick.to_string(),
            instance: instance.to_string(),
        }
    }

    /// `tester`/`host-a` default (ports `setUp`).
    pub fn tester() -> Self {
        Self::new("tester", "host-a")
    }

    pub fn set_nick(&mut self, nick: &str, host: &str) {
        self.nick = nick.to_string();
        self.instance = host.to_string();
    }

    /// Seen path routed into tmp (ports the `seen_path` patches).
    pub fn seen_path(&self, room: &str) -> PathBuf {
        self.tmp.join(format!("seen-{}", if room.is_empty() { "main" } else { room }))
    }

    /// Store path routed into tmp (ports the `store_path` patch).
    pub fn store_path(&self, room: &str) -> PathBuf {
        self.tmp.join(if room.is_empty() {
            "messages.jsonl".to_string()
        } else {
            format!("messages-{room}.jsonl")
        })
    }

    pub fn pushes_to(&self, key: &str) -> Vec<String> {
        self.fake.pushes_to(key)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tmp_routing() {
        let h = Harness::tester();
        assert!(h.seen_path("").ends_with("seen-main"));
        assert!(h.store_path("build-x").ends_with("messages-build-x.jsonl"));
    }
}
