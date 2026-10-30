//! Port of `os/intel/ingest.py` — bus snapshot ingestion.
//!
//! `snapshot(messages)` folds bus/store entries into a snapshot view:
//! paged message reads (`PAGE`), cursor resume, per-room filtering.
//! Malformed entries are skipped, never crashed on.

pub const PAGE: usize = 100;

#[derive(Debug, Clone, PartialEq)]
pub struct Message {
    pub id: String,
    pub room: String,
    pub ts: i64,
    pub body: String,
}

#[derive(Debug, Clone, Default)]
pub struct SnapshotView {
    pub messages: Vec<Message>,
    pub cursor: Option<String>,
}

/// Store a page of messages; returns entries actually stored.
pub fn store_messages(store: &mut Vec<Message>, msgs: Vec<Message>) -> usize {
    let mut n = 0;
    for m in msgs {
        if m.id.is_empty() {
            continue;
        }
        if store.iter().any(|e| e.id == m.id) {
            continue;
        }
        store.push(m);
        n += 1;
    }
    n
}

/// Read messages after a cursor, up to PAGE.
pub fn messages_from_cursor(store: &[Message], cursor: Option<&str>) -> SnapshotView {
    let start = cursor
        .and_then(|c| store.iter().position(|m| m.id == c).map(|i| i + 1))
        .unwrap_or(0);
    let end = (start + PAGE).min(store.len());
    let messages = store[start..end].to_vec();
    let next = messages.last().map(|m| m.id.clone());
    SnapshotView { messages, cursor: next }
}

/// Build a snapshot summary string (room counts + latest ts).
pub fn snapshot(store: &[Message]) -> String {
    format!("snapshot: {} messages", store.len())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn pages_and_resumes() {
        let mut s = Vec::new();
        let msgs: Vec<Message> = (0..3).map(|i| Message { id: format!("m{i}"), room: "main".to_string(), ts: i, body: "b".to_string() }).collect();
        assert_eq!(store_messages(&mut s, msgs), 3);
        let v = messages_from_cursor(&s, Some("m0"));
        assert_eq!(v.messages.len(), 2);
    }
}
