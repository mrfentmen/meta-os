//! B24 transport abstraction (stands in for excluded `relay_common`).
//!
//! Python `poll.py`/`send.py`/`watch.py` import `relay_common` for
//! `bus_get`, `bus_push`, `presence_beat`, `mark_seen`, nick helpers,
//! room keys, and `MAX_TEXT`. That module is excluded from the rebuild
//! by the clean-repo ruling, so this trait carries only what B24 needs.
//! Behavior is ported from the in-tree callers; exclusion-blocked cases
//! are named in the completion report, never faked.

/// Max message body length (`relay_common.MAX_TEXT`).
pub const MAX_TEXT: usize = 2000;

/// Minimal bus transport needed by B24.
pub trait BusTransport {
    /// `bus_get(seen, -1, key=key)` — messages from offset onward.
    fn bus_get(&self, seen: i64, key: &str) -> Result<Vec<String>, String>;
    /// Heartbeat; failures are logged, never fatal.
    fn presence_beat(&self, _key: &str) -> Result<(), String> {
        Ok(())
    }
    /// Read receipt; failures are logged, never fatal.
    fn mark_seen(&self, _key: &str, _nick: &str, _seen: i64) -> Result<(), String> {
        Ok(())
    }
    /// Canonical nick + own display-name prefixes (`own_prefixes()`).
    fn own_prefixes(&self, nick: &str) -> Vec<String> {
        vec![nick.to_string()]
    }
}

/// Room name for a bus key: `muse-bus:room:<name>` -> `<name>`,
/// anything else (default-room list) -> `""`.
///
/// Ports `store.room_for_key`.
pub fn room_for_key(key: &str) -> String {
    const PREFIX: &str = "muse-bus:room:";
    if let Some(rest) = key.strip_prefix(PREFIX) {
        rest.to_string()
    } else {
        String::new()
    }
}

/// Bus list key for a room (`bus_key`): `""` -> default list.
pub fn bus_key(room: &str) -> String {
    if room.is_empty() {
        "muse-bus".to_string()
    } else {
        format!("muse-bus:room:{room}")
    }
}
