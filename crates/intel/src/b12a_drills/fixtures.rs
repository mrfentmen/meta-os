//! Shared drill fixtures from `os/intel/drills/kill_worker.py`
//! (WDG-020) — the FakeWorker and the lease sweep rule that
//! demo_catch_time, demo_silent_failure, and power_cut stage
//! their snapshots with.
//!
//! kill_worker.py is a sibling drill file outside B12a's 39
//! (its own drill port belongs to its owning batch); what
//! lives here is only the fixture surface those three B12a
//! drills import, ported with its exact behavior: the worker
//! edits the snapshot in place, killing it means presence
//! stops and heartbeats stop, and it never deletes its own
//! job. The sweep mirrors jobs.py's `_claim_or_requeue`
//! requeue rule on the fixture snapshot.

use super::deps::Thresholds;
use super::value::Value;

/// A fixture worker: claims, heartbeats, posts progress, dies.
pub struct FakeWorker {
    pub nick: String,
    pub alive: bool,
}

impl FakeWorker {
    pub fn new(nick: &str) -> Self {
        FakeWorker {
            nick: nick.to_string(),
            alive: true,
        }
    }

    /// Claim a job at `now`: the job record carries the lease
    /// fields from thresholds, and the claim heartbeats.
    pub fn claim(&mut self, snapshot: &mut Value, job_id: &str, now: i64, t: &Thresholds) -> Value {
        let job = Value::obj(vec![
            ("id", Value::s(job_id)),
            ("title", Value::s("demo job")),
            ("status", Value::s("claimed")),
            ("claim", Value::s(&self.nick)),
            ("claimed_at", Value::Int(now)),
            ("lease", Value::Int(t.lease_default_seconds)),
            ("lease_until", Value::Int(now + t.lease_default_seconds)),
        ]);
        match snapshot.get("jobs") {
            Value::List(mut items) => {
                items.push(job.clone());
                snapshot.set("jobs", Value::List(items));
            }
            _ => snapshot.set("jobs", Value::List(vec![job.clone()])),
        }
        self.heartbeat(snapshot, now);
        job
    }

    /// Presence plus last_heartbeat on every job this nick claims.
    pub fn heartbeat(&mut self, snapshot: &mut Value, now: i64) {
        let mut presence: Vec<Value> = snapshot
            .get("presence")
            .as_list()
            .cloned()
            .unwrap_or_default();
        if !presence.iter().any(|n| n.as_str() == Some(&self.nick)) {
            presence.push(Value::s(&self.nick));
        }
        snapshot.set("presence", Value::List(presence));
        if let Value::List(mut items) = snapshot.get("jobs") {
            for job in items.iter_mut() {
                if job.get("claim").as_str() == Some(&self.nick) {
                    job.set("last_heartbeat", Value::Int(now));
                }
            }
            snapshot.set("jobs", Value::List(std::mem::take(&mut items)));
        }
    }

    /// Progress: last_progress on claimed jobs, plus the room
    /// message.
    pub fn progress(&mut self, snapshot: &mut Value, now: i64, text: &str) {
        if let Value::List(mut items) = snapshot.get("jobs") {
            for job in items.iter_mut() {
                if job.get("claim").as_str() == Some(&self.nick) {
                    job.set("last_progress", Value::Int(now));
                }
            }
            snapshot.set("jobs", Value::List(std::mem::take(&mut items)));
        }
        let message = Value::obj(vec![
            ("nick", Value::s(&self.nick)),
            ("text", Value::s(text)),
        ]);
        match snapshot.get("messages") {
            Value::List(mut items) => {
                items.push(message);
                snapshot.set("messages", Value::List(items));
            }
            _ => snapshot.set("messages", Value::List(vec![message])),
        }
    }

    /// Kill: stop heartbeats and drop out of presence, mid-job.
    pub fn kill(&mut self, snapshot: &mut Value) {
        self.alive = false;
        if let Value::List(items) = snapshot.get("presence") {
            let kept: Vec<Value> = items
                .into_iter()
                .filter(|n| n.as_str() != Some(&self.nick))
                .collect();
            snapshot.set("presence", Value::List(kept));
        }
    }
}

/// `sweep_expired_leases(snapshot, now)` — a claimed job whose
/// lease_until has passed reopens: status open, the claim
/// fields (claim, claim_host, claimed_at, lease_until) are
/// deleted. Returns the requeued job ids.
pub fn sweep_expired_leases(snapshot: &mut Value, now: i64) -> Vec<String> {
    let mut requeued: Vec<String> = Vec::new();
    if let Value::List(mut items) = snapshot.get("jobs") {
        for job in items.iter_mut() {
            if job.get("status").as_str() != Some("claimed") {
                continue;
            }
            let lease_until = match job.get("lease_until") {
                Value::Int(v) => v,
                Value::Float(f) => f as i64,
                _ => continue,
            };
            if now < lease_until {
                continue;
            }
            job.remove("claim");
            job.remove("claim_host");
            job.remove("claimed_at");
            job.remove("lease_until");
            job.set("status", Value::s("open"));
            requeued.push(job.get("id").py_str());
        }
        snapshot.set("jobs", Value::List(std::mem::take(&mut items)));
    }
    requeued
}
