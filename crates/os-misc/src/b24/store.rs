//! B24 store — port of `os/store.py`.
//!
//! Append-only JSONL log per room. IDs are `<room>-<counter>`
//! (bare counter for the default room), deterministic and unique
//! across rooms. Counter is derived from the highest id on disk so ids
//! survive restarts. Writes are atomic (tmp + rename).

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};

/// An edit was rejected (empty text, unknown id, wrong nick).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EditError(pub String);

impl std::fmt::Display for EditError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl std::error::Error for EditError {}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct EditRecord {
    pub text: String,
    pub ts: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Entry {
    pub id: String,
    pub room: String,
    pub nick: String,
    pub text: String,
    pub ts: i64,
    #[serde(default)]
    pub edited: bool,
    #[serde(default)]
    pub edit_history: Vec<EditRecord>,
}

/// Directory holding store files (`MUSE_RELAY_STORE_DIR` or `dir`).
pub fn store_path(dir: &Path, room: &str) -> PathBuf {
    let name = if room.is_empty() {
        "messages.jsonl".to_string()
    } else {
        format!("messages-{room}.jsonl")
    };
    dir.join(name)
}

fn now_ts() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0)
}

fn make_id(room: &str, seq: i64) -> String {
    if room.is_empty() {
        seq.to_string()
    } else {
        format!("{room}-{seq}")
    }
}

fn next_seq(entries: &[Entry]) -> i64 {
    let mut top: i64 = 0;
    for e in entries {
        if let Some(tail) = e.id.rsplit('-').next() {
            // Bare counters parse directly; `room-12` takes the tail.
            if let Ok(n) = tail.parse::<i64>() {
                if n > top {
                    top = n;
                }
            }
        }
    }
    top + 1
}

/// Append-only JSONL message log for one room.
pub struct MessageStore {
    pub path: PathBuf,
    pub room: String,
}

impl MessageStore {
    pub fn new(path: PathBuf, room: String) -> Self {
        Self { path, room }
    }

    pub fn entries(&self) -> Vec<Entry> {
        load(&self.path)
    }

    pub fn get(&self, mid: &str) -> Option<Entry> {
        load(&self.path).into_iter().find(|e| e.id == mid)
    }

    /// Record a sent message; returns the stored entry.
    pub fn append(&self, nick: &str, text: &str, ts: Option<i64>) -> Result<Entry, String> {
        if nick.is_empty() {
            return Err("nick is empty".to_string());
        }
        if text.is_empty() {
            return Err("message text is empty".to_string());
        }
        let mut entries = load(&self.path);
        let entry = Entry {
            id: make_id(&self.room, next_seq(&entries)),
            room: self.room.clone(),
            nick: nick.to_string(),
            text: text.to_string(),
            ts: ts.unwrap_or_else(now_ts),
            edited: false,
            edit_history: vec![],
        };
        entries.push(entry.clone());
        save(&self.path, &entries).map_err(|e| e.to_string())?;
        Ok(entry)
    }

    /// Apply an edit: history grows, text updates, flag sets.
    /// Only the original nick may edit its own message.
    pub fn edit(
        &self,
        mid: &str,
        editor_nick: &str,
        new_text: &str,
        ts: Option<i64>,
    ) -> Result<Entry, EditError> {
        if new_text.is_empty() {
            return Err(EditError("new text is empty".to_string()));
        }
        let mut entries = load(&self.path);
        let pos = entries
            .iter()
            .position(|e| e.id == mid)
            .ok_or_else(|| EditError(format!("no such message: {mid}")))?;
        if entries[pos].nick != editor_nick {
            return Err(EditError(format!(
                "message {mid} was sent by '{}'; only the original nick may edit it",
                entries[pos].nick
            )));
        }
        let at = ts.unwrap_or_else(now_ts);
        let old = entries[pos].text.clone();
        entries[pos]
            .edit_history
            .push(EditRecord { text: old, ts: at });
        entries[pos].text = new_text.to_string();
        entries[pos].edited = true;
        save(&self.path, &entries)
            .map_err(|e| EditError(format!("store write failed: {e}")))?;
        Ok(entries[pos].clone())
    }
}

fn load(path: &Path) -> Vec<Entry> {
    let data = match fs::read_to_string(path) {
        Ok(s) => s,
        Err(e) if e.kind() == io::ErrorKind::NotFound => return vec![],
        Err(_) => return vec![],
    };
    let mut out = vec![];
    for line in data.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        // Skip bad lines with a warning, like the Python.
        match serde_json::from_str::<HashMap<String, serde_json::Value>>(line) {
            Ok(_) => {}
            Err(_) => continue,
        }
        if let Ok(e) = serde_json::from_str::<Entry>(line) {
            if !e.id.is_empty() {
                out.push(e);
            }
        }
    }
    out
}

fn save(path: &Path, entries: &[Entry]) -> io::Result<()> {
    let tmp = path.with_extension("jsonl.tmp");
    let mut buf = String::new();
    for e in entries {
        // `sort_keys=True` equivalent: serde preserves struct order.
        buf.push_str(&serde_json::to_string(e).unwrap_or_default());
        buf.push('\n');
    }
    fs::write(&tmp, buf)?;
    fs::rename(&tmp, path)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn tmpdir() -> PathBuf {
        let n = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!("os-misc-b24-store-{n}-{}", std::process::id()))
    }

    #[test]
    fn append_ids_increment_and_survive() {
        let dir = tmpdir();
        fs::create_dir_all(&dir).unwrap();
        let st = MessageStore::new(store_path(&dir, ""), String::new());
        let a = st.append("milo", "ship it monday", Some(1758300000)).unwrap();
        assert_eq!(a.id, "1");
        let b = st.append("milo", "ship it tuesday", Some(1758300001)).unwrap();
        assert_eq!(b.id, "2");
        // Room ids carry the room prefix.
        let rst = MessageStore::new(store_path(&dir, "build-x"), "build-x".into());
        let r = rst.append("milo", "hello", Some(1758300002)).unwrap();
        assert_eq!(r.id, "build-x-1");
        // Reopen: counter continues.
        let st2 = MessageStore::new(store_path(&dir, ""), String::new());
        let c = st2.append("milo", "again", Some(1758300003)).unwrap();
        assert_eq!(c.id, "3");
        fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn edit_only_author_and_history() {
        let dir = tmpdir();
        fs::create_dir_all(&dir).unwrap();
        let st = MessageStore::new(store_path(&dir, ""), String::new());
        let e = st.append("milo", "ship it friday", Some(1758299000)).unwrap();
        let edited = st.edit(&e.id, "milo", "ship it monday", Some(1758300000)).unwrap();
        assert!(edited.edited);
        assert_eq!(edited.text, "ship it monday");
        assert_eq!(edited.edit_history.len(), 1);
        assert_eq!(edited.edit_history[0].text, "ship it friday");
        // Wrong nick rejected.
        assert!(st.edit(&e.id, "pax", "hijack", None).is_err());
        // Unknown id rejected.
        assert!(st.edit("9999", "milo", "x", None).is_err());
        // Empty text rejected.
        assert!(st.edit(&e.id, "milo", "", None).is_err());
        fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn bad_lines_skipped() {
        let dir = tmpdir();
        fs::create_dir_all(&dir).unwrap();
        let p = store_path(&dir, "");
        fs::write(&p, "not json\n{\"id\":\"1\",\"room\":\"\",\"nick\":\"m\",\"text\":\"hi\",\"ts\":1}\n").unwrap();
        let st = MessageStore::new(p, String::new());
        assert_eq!(st.entries().len(), 1);
        fs::remove_dir_all(&dir).ok();
    }
}
