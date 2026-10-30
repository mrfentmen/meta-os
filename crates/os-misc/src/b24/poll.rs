//! B24 poll — port of `os/poll.py`.
//!
//! `poll_one` behavior: read seen offset, `bus_get`, heartbeat,
//! filter out own prefixes, record incoming into the room store,
//! advance + persist seen, write read receipt (best-effort).
//! Transport failures surface as `Err`; heartbeat/receipt failures
//! are swallowed into the returned warnings (never break the poll).

use super::store::MessageStore;
use super::transport::BusTransport;
use std::fs;

/// Outcome of one room poll.
pub struct PollOutcome {
    /// All messages returned by the bus.
    pub all: Vec<String>,
    /// Messages from other nicks.
    pub new_from_others: Vec<String>,
    /// Non-fatal warnings (heartbeat/store/seen/receipt).
    pub warnings: Vec<String>,
}

/// Read a seen-offset file; missing/garbage -> 0 (ports Python).
pub fn read_seen(path: &str) -> i64 {
    fs::read_to_string(path)
        .ok()
        .and_then(|s| s.trim().parse::<i64>().ok())
        .unwrap_or(0)
}

/// Poll one room key. `seen_file`: path tracking the read offset.
pub fn poll_one<T: BusTransport>(
    bus: &T,
    key: &str,
    seen_file: &str,
    nick: &str,
    store: &MessageStore,
) -> Result<PollOutcome, String> {
    let seen = read_seen(seen_file);
    let msgs = bus
        .bus_get(seen, key)
        .map_err(|e| format!("poll failed: {e}"))?;
    let mut warnings = vec![];
    if let Err(e) = bus.presence_beat(key) {
        warnings.push(format!("presence heartbeat failed: {e}"));
    }
    let mine = bus.own_prefixes(nick);
    let new_from_others: Vec<String> = msgs
        .iter()
        .filter(|m| !mine.iter().any(|p| m.starts_with(&format!("{p}:"))))
        .cloned()
        .collect();
    // Record incoming so they get ids usable with forward/saved tools.
    for m in &new_from_others {
        if let Some((from, text)) = m.split_once(": ") {
            if !from.is_empty() && !text.is_empty() && from != nick {
                // Best-effort; duplicates collapse in the store layer.
                let _ = store.append(from, text, None);
            }
        }
    }
    let next = seen + msgs.len() as i64;
    if let Err(e) = fs::write(seen_file, next.to_string()) {
        warnings.push(format!("seen write failed: {e}"));
    }
    if let Err(e) = bus.mark_seen(key, nick, next) {
        warnings.push(format!("read-receipt write failed: {e}"));
    }
    Ok(PollOutcome {
        all: msgs,
        new_from_others,
        warnings,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::VecDeque;
    use std::sync::Mutex;

    struct Fake {
        msgs: Mutex<VecDeque<String>>,
    }
    impl BusTransport for Fake {
        fn bus_get(&self, seen: i64, _key: &str) -> Result<Vec<String>, String> {
            let v: Vec<String> = self.msgs.lock().unwrap().clone().into();
            Ok(v.into_iter().skip(seen.max(0) as usize).collect())
        }
    }

    #[test]
    fn filters_own_and_advances() {
        let dir = std::env::temp_dir().join(format!(
            "os-misc-b24-poll-{}",
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&dir).unwrap();
        let seen = dir.join("seen").to_string_lossy().to_string();
        let store = MessageStore::new(dir.join("messages.jsonl"), String::new());
        let fake = Fake {
            msgs: Mutex::new(VecDeque::from([
                "milo: hi".to_string(),
                "pax: hello".to_string(),
            ])),
        };
        let out = poll_one(&fake, "muse-bus", &seen, "milo", &store).unwrap();
        assert_eq!(out.all.len(), 2);
        assert_eq!(out.new_from_others, vec!["pax: hello".to_string()]);
        assert_eq!(read_seen(&seen), 2);
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn missing_seen_starts_at_zero() {
        assert_eq!(read_seen("/definitely/not/here/seen-xyz"), 0);
    }
}
