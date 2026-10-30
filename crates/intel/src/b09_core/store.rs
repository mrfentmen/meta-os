//! Port of `os/intel/store.py` — Redis records for Relay Intelligence.
//!
//! Key layout under `<prefix>:intel:*` (prefix default `muse-bus`,
//! override `MUSE_RELAY_KEY_PREFIX`): brief/alert(+index)/notify(+index)/
//! dispatch/watchdog/selfcheck/boot-status records, spend ledger, watchman
//! beats. `write_*` validates shape before storing and maintains the index;
//! raw `put_*` does not. Lifecycle: open -> acknowledged -> resolved;
//! re-fire inside cooldown advances `last_seen`; resolved re-firing starts a
//! fresh open occurrence. In Rust: an in-memory [`Store`] with the same key
//! builders and validation rules (Redis I/O stays at the boundary).

use std::collections::HashMap;

pub fn key_prefix() -> String {
    std::env::var("MUSE_RELAY_KEY_PREFIX").unwrap_or_else(|_| "muse-bus".to_string())
}

pub fn brief_key(room: &str, ts: i64) -> String {
    format!("{}:intel:brief:{room}:{ts}", key_prefix())
}
pub fn alert_key(id: &str) -> String {
    format!("{}:intel:alert:{id}", key_prefix())
}
pub fn alert_index_key() -> String {
    format!("{}:intel:alert:index", key_prefix())
}
pub fn notify_key(id: &str) -> String {
    format!("{}:intel:notify:{id}", key_prefix())
}
pub fn notify_index_key() -> String {
    format!("{}:intel:notify:index", key_prefix())
}
pub fn dispatch_key(id: &str) -> String {
    format!("{}:intel:dispatch:{id}", key_prefix())
}

#[derive(Debug, Clone, PartialEq)]
pub struct AlertRecord {
    pub id: String,
    pub kind: String,
    pub severity: String,
    pub room: String,
    pub explanation: String,
    pub created_at: i64,
    pub last_seen: i64,
    pub status: String, // open | acknowledged | resolved
    pub dedupe_key: String,
    pub resolved_at: Option<i64>,
    pub acknowledged_at: Option<i64>,
}

/// Validate the WDG-010 alert shape.
pub fn validate_alert(r: &AlertRecord) -> Result<(), String> {
    if r.id.is_empty() {
        return Err("alert: missing id".to_string());
    }
    if r.kind.is_empty() {
        return Err("alert: missing kind".to_string());
    }
    if r.explanation.is_empty() {
        return Err("alert: missing explanation".to_string());
    }
    if r.dedupe_key.is_empty() {
        return Err("alert: missing dedupe_key".to_string());
    }
    Ok(())
}

pub fn alert_status(r: &AlertRecord) -> &str {
    &r.status
}

/// In-memory store mirroring the Redis layout (boundary adapter).
#[derive(Debug, Default)]
pub struct Store {
    pub strings: HashMap<String, String>,
    pub zindex: HashMap<String, Vec<(i64, String)>>,
    pub alerts: HashMap<String, AlertRecord>,
}

impl Store {
    pub fn put_brief(&mut self, room: &str, ts: i64, json: &str) {
        self.strings.insert(brief_key(room, ts), json.to_string());
    }
    pub fn get_brief(&self, room: &str, ts: i64) -> Option<&String> {
        self.strings.get(&brief_key(room, ts))
    }
    /// Validated write: maintains the alert index.
    pub fn write_alert(&mut self, mut r: AlertRecord) -> Result<(), String> {
        validate_alert(&r)?;
        if r.last_seen == 0 {
            r.last_seen = r.created_at;
        }
        if r.status.is_empty() {
            r.status = "open".to_string();
        }
        // Re-fire inside cooldown keeps acknowledged status, advances last_seen.
        if let Some(prev) = self.alerts.get(&r.id) {
            if prev.status == "acknowledged" && r.status == "open" {
                r.status = "acknowledged".to_string();
                r.acknowledged_at = prev.acknowledged_at;
            }
            if prev.status == "resolved" && r.status == "open" {
                // fresh occurrence: keep open, new created_at wins
            }
        }
        self.strings.insert(alert_key(&r.id), format!("{}|{}|{}", r.kind, r.status, r.explanation));
        self.alerts.insert(r.id.clone(), r.clone());
        let idx = self.zindex.entry(alert_index_key()).or_default();
        idx.retain(|(_, m)| m != &r.id);
        idx.push((r.created_at, r.id.clone()));
        Ok(())
    }
    pub fn get_alert(&self, id: &str) -> Option<&AlertRecord> {
        self.alerts.get(id)
    }
    pub fn query_alerts(&self) -> Vec<&AlertRecord> {
        let mut v: Vec<&AlertRecord> = self.alerts.values().collect();
        v.sort_by_key(|a| a.created_at);
        v
    }
    pub fn acknowledge_alert(&mut self, id: &str, at: i64) -> bool {
        if let Some(a) = self.alerts.get_mut(id) {
            if a.status == "open" {
                a.status = "acknowledged".to_string();
                a.acknowledged_at = Some(at);
                return true;
            }
        }
        false
    }
    pub fn resolve_alert(&mut self, id: &str, at: i64) -> bool {
        if let Some(a) = self.alerts.get_mut(id) {
            a.status = "resolved".to_string();
            a.resolved_at = Some(at);
            return true;
        }
        false
    }
    /// Auto-resolve alerts whose dedupe keys are absent from `firing`.
    pub fn auto_resolve_cleared(&mut self, firing: &[String], at: i64) -> Vec<String> {
        let mut out = Vec::new();
        for a in self.alerts.values_mut() {
            if a.status != "resolved" && !firing.contains(&a.dedupe_key) {
                a.status = "resolved".to_string();
                a.resolved_at = Some(at);
                out.push(a.id.clone());
            }
        }
        out
    }
    // Spend ledger: "<prefix>:intel:spend" list of (ts, amount_cents, label).
    pub fn record_spend(&mut self, ts: i64, cents: i64, label: &str) {
        let key = format!("{}:intel:spend", key_prefix());
        let entry = self.strings.entry(key).or_default();
        if !entry.is_empty() {
            entry.push('\n');
        }
        entry.push_str(&format!("{ts}:{cents}:{label}"));
    }
    pub fn spend_total(&self) -> i64 {
        let key = format!("{}:intel:spend", key_prefix());
        self.strings.get(&key).map(|s| {
            s.lines()
                .filter_map(|l| l.split(':').nth(1)?.parse::<i64>().ok())
                .sum()
        }).unwrap_or(0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn alert(id: &str) -> AlertRecord {
        AlertRecord {
            id: id.to_string(),
            kind: "k".to_string(),
            severity: "high".to_string(),
            room: "main".to_string(),
            explanation: "e".to_string(),
            created_at: 10,
            last_seen: 10,
            status: "open".to_string(),
            dedupe_key: format!("d:{id}"),
            resolved_at: None,
            acknowledged_at: None,
        }
    }

    #[test]
    fn write_validates_shape() {
        let mut s = Store::default();
        let mut bad = alert("x");
        bad.explanation.clear();
        assert!(s.write_alert(bad).is_err());
    }

    #[test]
    fn ack_and_resolve_lifecycle() {
        let mut s = Store::default();
        s.write_alert(alert("a")).unwrap();
        assert!(s.acknowledge_alert("a", 11));
        assert_eq!(s.get_alert("a").unwrap().status, "acknowledged");
        assert!(s.resolve_alert("a", 12));
        assert_eq!(s.get_alert("a").unwrap().status, "resolved");
    }

    #[test]
    fn auto_resolve_clears_unfired() {
        let mut s = Store::default();
        s.write_alert(alert("a")).unwrap();
        let r = s.auto_resolve_cleared(&[], 20);
        assert_eq!(r, vec!["a".to_string()]);
    }

    #[test]
    fn spend_ledger_sums() {
        let mut s = Store::default();
        s.record_spend(1, 100, "x");
        s.record_spend(2, 50, "y");
        assert_eq!(s.spend_total(), 150);
    }
}
