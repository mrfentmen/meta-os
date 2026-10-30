//! B25 saved — port of `os/saved.py`.
//!
//! Bookmarks live in `muse-bus:saved:<nick>`, newest first, capped
//! at 200 entries. Each entry carries id, room, nick, text, ts,
//! saved_ts.

pub const SAVE_CAP: usize = 200;

/// Redis key holding (nick or our) saved messages, newest first.
pub fn save_key(nick: &str) -> String {
    format!("muse-bus:saved:{nick}")
}

/// Human room label: `""` -> `main`, else `#room`.
pub fn room_label(room: &str) -> String {
    if room.is_empty() {
        "main".to_string()
    } else {
        format!("#{room}")
    }
}

/// Saved entry shape (JSON blob).
#[derive(Debug, Clone, PartialEq)]
pub struct SavedEntry {
    pub id: String,
    pub room: String,
    pub nick: String,
    pub text: String,
    pub ts: Option<i64>,
    pub saved_ts: i64,
}

/// Render one `list` line: `[id] #room nick: text`.
pub fn render_line(e: &SavedEntry) -> String {
    format!("[{}] {} {}: {}", e.id, room_label(&e.room), e.nick, e.text)
}

/// Filter by room (`None` = all), newest first preserved.
pub fn filter_room<'a>(entries: &'a [SavedEntry], room: Option<&str>) -> Vec<&'a SavedEntry> {
    match room {
        None => entries.iter().collect(),
        Some(r) => entries.iter().filter(|e| e.room == r).collect(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn key_and_label_shapes() {
        assert_eq!(save_key("milo"), "muse-bus:saved:milo");
        assert_eq!(room_label(""), "main");
        assert_eq!(room_label("news"), "#news");
        assert_eq!(SAVE_CAP, 200);
    }

    #[test]
    fn list_filter_and_render() {
        let es = vec![
            SavedEntry { id: "1".into(), room: "".into(), nick: "m".into(), text: "hi".into(), ts: None, saved_ts: 1 },
            SavedEntry { id: "n-1".into(), room: "news".into(), nick: "a".into(), text: "x".into(), ts: None, saved_ts: 2 },
        ];
        assert_eq!(filter_room(&es, None).len(), 2);
        assert_eq!(filter_room(&es, Some("news")).len(), 1);
        assert_eq!(render_line(&es[0]), "[1] main m: hi");
    }
}
