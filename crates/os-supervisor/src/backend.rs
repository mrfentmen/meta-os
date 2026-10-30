//! Minimal MOS backend seam for the overseer and reconciler.
//!
//! The live overseer reads the jobs queue (B16), the capability
//! registry (B18), the bus (excluded transport), acceptance
//! results (B31), and git worktrees (B19). Those owners live on
//! other branches; this module is the small in-memory seam the
//! B21 logic is pinned against, with identical state-machine
//! rules. The live wiring swaps this seam for the real stores at
//! integration, without changing the orchestration.

use std::collections::BTreeMap;

/// One job record (the jobs.py hash shape the overseer reads).
#[derive(Debug, Clone, Default)]
pub struct JobRecord {
    pub id: String,
    pub title: String,
    pub spec: String,
    pub accept: String,
    pub status: String,
    pub claim: String,
    pub branch: String,
    pub room: String,
    pub verified: bool,
    pub result_commit: String,
    pub note: String,
}

/// One capability record.
#[derive(Debug, Clone, Default)]
pub struct CapRecord {
    pub caps: Vec<String>,
    pub dm_secret: String,
    pub updated: u64,
    pub max_jobs: usize,
}

/// In-memory jobs + capabilities backend.
#[derive(Debug, Default)]
pub struct Backend {
    pub jobs: BTreeMap<String, JobRecord>,
    pub index: Vec<String>,
    pub caps: BTreeMap<String, CapRecord>,
    pub announcements: Vec<(String, String)>,
    pub dms: Vec<(String, String)>,
    pub now: u64,
    pub stale_after: u64,
}

impl Backend {
    pub fn new() -> Self {
        Backend {
            stale_after: 900,
            ..Default::default()
        }
    }

    pub fn post_job(&mut self, title: &str, spec: &str, accept: &str, branch: &str, room: &str, req: &str) -> String {
        let jid = (self.index.len() + 1).to_string();
        self.jobs.insert(
            jid.clone(),
            JobRecord {
                id: jid.clone(),
                title: title.to_string(),
                spec: spec.to_string(),
                accept: accept.to_string(),
                status: "open".to_string(),
                branch: branch.to_string(),
                room: room.to_string(),
                ..Default::default()
            },
        );
        let _ = req;
        self.index.push(jid.clone());
        jid
    }

    pub fn find_for(&self, reqs: &[String]) -> Vec<String> {
        let mut out = Vec::new();
        for (nick, rec) in &self.caps {
            if self.now.saturating_sub(rec.updated) > self.stale_after {
                continue;
            }
            if !reqs.iter().all(|r| rec.caps.iter().any(|c| c == r)) {
                continue;
            }
            let claimed = self
                .jobs
                .values()
                .filter(|j| j.status == "claimed" && j.claim == *nick)
                .count();
            if claimed >= rec.max_jobs.max(1) {
                continue;
            }
            out.push(nick.clone());
        }
        out.sort();
        out
    }

    pub fn prune_stale(&mut self) -> Vec<String> {
        let stale: Vec<String> = self
            .caps
            .iter()
            .filter(|(_, rec)| self.now.saturating_sub(rec.updated) > self.stale_after)
            .map(|(nick, _)| nick.clone())
            .collect();
        for nick in &stale {
            self.caps.remove(nick);
        }
        let mut out = stale;
        out.sort();
        out
    }

    pub fn announce(&mut self, room: &str, text: &str) {
        self.announcements.push((room.to_string(), text.to_string()));
    }
}
