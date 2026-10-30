//! Port of `os/intel/alerts.py` — alert lifecycle helpers.
//!
//! Thin wrappers over `b09_core::store` so the CLI, dashboard, and
//! watchdog call the lifecycle by the same names: open -> acknowledged
//! -> resolved; auto-resolve for unfired; re-fire starts a fresh open
//! occurrence (WDG-013/WDG-014).

pub use crate::b09_core::store::{alert_status, Store};

pub fn acknowledge_alert(store: &mut Store, id: &str, now: i64) -> bool {
    store.acknowledge_alert(id, now)
}

pub fn resolve_alert(store: &mut Store, id: &str, now: i64) -> bool {
    store.resolve_alert(id, now)
}

pub fn auto_resolve_cleared(store: &mut Store, firing: &[String], now: i64) -> Vec<String> {
    store.auto_resolve_cleared(firing, now)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::b09_core::store::AlertRecord;
    #[test]
    fn lifecycle_wraps_store() {
        let mut s = Store::default();
        s.write_alert(AlertRecord { id: "a".into(), kind: "k".into(), severity: "h".into(), room: "main".into(), explanation: "e".into(), created_at: 1, last_seen: 1, status: "open".into(), dedupe_key: "d".into(), resolved_at: None, acknowledged_at: None }).unwrap();
        assert!(acknowledge_alert(&mut s, "a", 2));
        assert!(resolve_alert(&mut s, "a", 3));
    }
}
