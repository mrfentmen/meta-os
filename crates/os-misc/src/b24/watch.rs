//! B24 watch — port of `os/watch.py` `watch_once`.
//!
//! One poll iteration over all targets. Prints/returns new messages
//! from other nicks, records them in the room store, advances seen.
//! Interval validation (`interval must be positive`) lives here.

use super::store::MessageStore;
use super::transport::BusTransport;

/// One watch target: `[label, key, seen_file, seen]`.
pub struct Target {
    pub label: String,
    pub key: String,
    pub seen_file: String,
    pub seen: i64,
}

/// A message ready for display.
pub struct Shown {
    pub room: String,
    pub line: String,
}

pub fn validate_interval(interval: f64) -> Result<(), String> {
    if interval <= 0.0 {
        return Err("interval must be positive".to_string());
    }
    Ok(())
}

/// One poll iteration. Returns lines to display.
pub fn watch_once<T: BusTransport>(
    bus: &T,
    targets: &mut [Target],
    nick: &str,
    open_store: &dyn Fn(&str) -> MessageStore,
) -> Result<Vec<Shown>, String> {
    let mut shown = vec![];
    for t in targets.iter_mut() {
        let msgs = bus
            .bus_get(t.seen, &t.key)
            .map_err(|e| format!("poll failed: {e}"))?;
        let _ = bus.presence_beat(&t.key);
        let st = open_store(&t.key);
        let mine = bus.own_prefixes(nick);
        for m in &msgs {
            if mine.iter().any(|p| m.starts_with(&format!("{p}:"))) {
                continue;
            }
            // Record incoming so FWD/SAVE-by-id works for others' lines.
            if let Some((from, text)) = m.split_once(": ") {
                if !from.is_empty() && !text.is_empty() && from != nick {
                    let _ = st.append(from, text, None);
                }
            }
            shown.push(Shown {
                room: t.key.clone(),
                line: m.clone(),
            });
        }
        t.seen += msgs.len() as i64;
        let _ = std::fs::write(&t.seen_file, t.seen.to_string());
        let _ = bus.mark_seen(&t.key, nick, t.seen);
    }
    Ok(shown)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn interval_must_be_positive() {
        assert!(validate_interval(10.0).is_ok());
        assert!(validate_interval(0.0).is_err());
        assert!(validate_interval(-1.0).is_err());
    }
}
