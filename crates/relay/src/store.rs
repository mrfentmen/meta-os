//! Room store from `relay/relay.mjs`: rooms map to ordered lines,
//! appends return the new line's 0-based index, and an optional JSONL
//! file persists every appended line and reloads on boot.
//!
//! Reload tolerance mirrors the original: blank lines skipped, and a
//! torn final record (unparseable JSON, or non-string room/line)
//! is skipped with an error note — it must not stop the relay from
//! booting. A store-file append failure is likewise logged and the
//! line stays in memory; the index is still returned.

use crate::json::{parse_record, record_line};
use std::collections::HashMap;
use std::fs::{self, OpenOptions};
use std::io::{self, Write};
use std::path::PathBuf;

pub struct RoomStore {
    rooms: HashMap<String, Vec<String>>,
    store_file: Option<PathBuf>,
}

impl RoomStore {
    /// In-memory store only (no `RELAY_STORE_FILE`).
    pub fn memory() -> Self {
        RoomStore {
            rooms: HashMap::new(),
            store_file: None,
        }
    }

    /// Store backed by a JSONL file: existing records reload on boot.
    /// An unreadable existing file is an error (the original's
    /// `readFileSync` would throw at boot); unparseable records
    /// inside a readable file are skipped.
    pub fn with_file(store_file: PathBuf) -> io::Result<Self> {
        let mut store = RoomStore {
            rooms: HashMap::new(),
            store_file: Some(store_file.clone()),
        };
        if store_file.exists() {
            let text = fs::read_to_string(&store_file)?;
            for raw in text.split('\n') {
                if raw.trim().is_empty() {
                    continue;
                }
                match parse_record(raw) {
                    Some((room, line)) => {
                        store.rooms.entry(room).or_default().push(line);
                    }
                    None => {
                        eprintln!("Meta Nuntius: skipped an unparseable store record");
                    }
                }
            }
        }
        Ok(store)
    }

    /// Append a line to a room; returns its 0-based index.
    pub fn append(&mut self, room: &str, line: &str) -> usize {
        let lines = self.rooms.entry(room.to_string()).or_default();
        let index = lines.len();
        lines.push(line.to_string());
        if let Some(path) = &self.store_file {
            let record = record_line(room, line);
            let result = OpenOptions::new()
                .create(true)
                .append(true)
                .open(path)
                .and_then(|mut f| writeln!(f, "{}", record));
            if let Err(err) = result {
                eprintln!("Meta Nuntius: store append failed: {}", err);
            }
        }
        index
    }

    /// Lines in a room, in order; empty when the room is unknown
    /// (the original answers `rooms.get(room) || []`).
    pub fn messages(&self, room: &str) -> &[String] {
        self.rooms.get(room).map(|v| v.as_slice()).unwrap_or(&[])
    }

    /// Lines after index `since` (`since = -1` returns the whole room;
    /// any `since < -1` is treated as -1, mirroring the original's
    /// `Number.isFinite(since) || since < -1` guard).
    pub fn messages_since(&self, room: &str, since: i64) -> &[String] {
        let lines = self.messages(room);
        let since = if since < -1 { -1 } else { since };
        let start = (since + 1).max(0) as usize;
        if start >= lines.len() {
            &[]
        } else {
            &lines[start..]
        }
    }

    /// Number of rooms (the original's `/health` `rooms` field).
    pub fn room_count(&self) -> usize {
        self.rooms.len()
    }

    /// "memory" or "file" (the original's `/health` `store` field).
    pub fn store_kind(&self) -> &'static str {
        if self.store_file.is_some() {
            "file"
        } else {
            "memory"
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_path(tag: &str) -> PathBuf {
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        env::temp_dir().join(format!("nuntius-test-{}-{}.jsonl", tag, stamp))
    }

    #[test]
    fn append_indices_and_isolation() {
        // Mirrors the JS suite's first two tests (watermark indices,
        // rooms isolated from each other).
        let mut store = RoomStore::memory();
        assert_eq!(store.append("main", "pax: first line [ts:1]"), 0);
        assert_eq!(store.append("main", "del: second line [ts:2]"), 1);
        assert_eq!(store.append("1", "hana: room one only [ts:3]"), 0);
        assert_eq!(store.messages("main").len(), 2);
        assert_eq!(store.messages("1").len(), 1);
        assert!(store.messages("main").iter().all(|l| !l.contains("room one")));
        assert_eq!(store.room_count(), 2);
        assert_eq!(store.store_kind(), "memory");
    }

    #[test]
    fn since_semantics() {
        let mut store = RoomStore::memory();
        store.append("main", "a [ts:1]");
        store.append("main", "b [ts:2]");
        assert_eq!(store.messages_since("main", -1).len(), 2);
        assert_eq!(store.messages_since("main", 0), ["b [ts:2]"]);
        assert!(store.messages_since("main", 1).is_empty());
        assert_eq!(store.messages_since("main", -99).len(), 2);
        assert!(store.messages_since("nope", -1).is_empty());
    }

    #[test]
    fn file_store_persists_across_reload() {
        // Mirrors the JS suite's file-store test (without the HTTP
        // layer, which is the next slice).
        let path = temp_path("persist");
        {
            let mut first = RoomStore::with_file(path.clone()).unwrap();
            assert_eq!(first.store_kind(), "file");
            first.append("main", "milo: persisted line [ts:1]");
            first.append("ops", "relay: NOTIFY:ntf-x warning [trio-result] boom [ts:2]");
        }
        let second = RoomStore::with_file(path.clone()).unwrap();
        assert_eq!(second.messages("main").len(), 1);
        assert!(second.messages("main")[0].contains("persisted line"));
        assert_eq!(second.messages("ops").len(), 1);
        fs::remove_file(&path).unwrap();
    }

    #[test]
    fn reload_skips_torn_records() {
        let path = temp_path("torn");
        fs::write(
            &path,
            concat!(
                "{\"room\":\"main\",\"line\":\"good [ts:1]\"}\n",
                "\n",
                "{\"room\":\"main\",\"line\":unterminated\n",
                "{\"room\":3,\"line\":\"bad type\"}\n",
                "{\"room\":\"main\",\"line\":\"after torn [ts:2]\"}\n",
            ),
        )
        .unwrap();
        let store = RoomStore::with_file(path.clone()).unwrap();
        assert_eq!(store.messages("main").len(), 2);
        assert!(store.messages("main")[0].contains("good"));
        assert!(store.messages("main")[1].contains("after torn"));
        fs::remove_file(&path).unwrap();
    }
}
