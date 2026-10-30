//! Port of `os/intel/brief.py` `_message_parts` + `_window_line`
//! (BRF-013) — snapshot input normalization for the brief engine.
//!
//! `_message_parts` turns a store entry (dict) or a bus string into
//! (nick, text); `_window_line` renders the window line a brief
//! opens with. Both are pure: no store, bus, or Spark access, so
//! they sit beside `sections` (whose caller used to split string
//! messages by hand, mirroring `_message_parts`).

/// A raw snapshot message input, mirroring what `_message_parts` accepts.
#[derive(Debug, Clone, PartialEq)]
pub enum RawMessage {
    /// Dict form: nick/text as the store entry carries them. A key
    /// the entry lacks arrives as an empty string, mirroring
    /// `.get(key, "")`.
    Dict { nick: String, text: String },
    /// Bus string form: `"nick: text"`, or plain text with no nick.
    Text(String),
    /// Any other shape: Python returns `("", "")`.
    Other,
}

/// Mirror `_message_parts`: dict -> (nick, text); string -> split on
/// the first `": "` (no separator -> `("", whole string)`); else
/// `("", "")`.
pub fn message_parts(message: &RawMessage) -> (String, String) {
    match message {
        RawMessage::Dict { nick, text } => (nick.clone(), text.clone()),
        RawMessage::Text(s) => match s.split_once(": ") {
            Some((nick, text)) => (nick.to_string(), text.to_string()),
            None => (String::new(), s.clone()),
        },
        RawMessage::Other => (String::new(), String::new()),
    }
}

/// A `max_hours` value from a `source_window` dict: Python ints stay
/// ints; floats that are whole numbers render as ints (BRF-024:
/// the line reads "last 24 hours", never "last 24.0 hours").
#[derive(Debug, Clone, PartialEq)]
pub enum WindowHours {
    Int(i64),
    Float(f64),
}

impl WindowHours {
    fn render(&self) -> String {
        match self {
            WindowHours::Int(v) => v.to_string(),
            WindowHours::Float(v) => {
                if v.fract() == 0.0 {
                    (*v as i64).to_string()
                } else {
                    v.to_string()
                }
            }
        }
    }
}

/// A `source_window` value: dict form or plain string form.
#[derive(Debug, Clone, PartialEq)]
pub enum SourceWindow {
    Dict {
        max_messages: Option<i64>,
        max_hours: Option<WindowHours>,
        messages_kept: Option<i64>,
        messages_dropped: Option<i64>,
    },
    Text(String),
}

/// Snapshot window inputs for `_window_line`: the stated window (if
/// any) and the truncation start point (if any).
#[derive(Debug, Clone, PartialEq, Default)]
pub struct WindowInput {
    pub source_window: Option<SourceWindow>,
    pub window_start: Option<String>,
}

fn opt_count(v: &Option<i64>) -> String {
    match v {
        Some(n) => n.to_string(),
        // Mirror Python's `.get` on a missing key: it renders None.
        None => "None".to_string(),
    }
}

/// Mirror `_window_line` (BRF-013): a dict window renders verbatim
/// with its counts; a non-empty string window renders verbatim;
/// otherwise a stated start point says history before it is not in
/// the window; otherwise the line says plainly no window was
/// stated. A truncated window must state its start point, never
/// imply earlier history the machine does not have.
pub fn window_line(input: &WindowInput) -> String {
    match &input.source_window {
        Some(SourceWindow::Dict {
            max_messages,
            max_hours,
            messages_kept,
            messages_dropped,
        }) => {
            let hours = match max_hours {
                Some(h) => h.render(),
                None => "None".to_string(),
            };
            format!(
                "Window: last {} messages or last {} hours, {} kept, {} dropped",
                opt_count(max_messages),
                hours,
                opt_count(messages_kept),
                opt_count(messages_dropped)
            )
        }
        Some(SourceWindow::Text(t)) if !t.is_empty() => format!("Window: {t}"),
        _ => match &input.window_start {
            Some(start) if !start.is_empty() => format!(
                "Window: from {start} onward. Earlier history is not in this window."
            ),
            _ => "Window: not stated in this snapshot".to_string(),
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn message_parts_forms() {
        assert_eq!(
            message_parts(&RawMessage::Dict {
                nick: "pax".into(),
                text: "hi".into()
            }),
            ("pax".to_string(), "hi".to_string())
        );
        // Split on the FIRST ": " only; the marker stays in the text.
        assert_eq!(
            message_parts(&RawMessage::Text("milo: DONE: x".into())),
            ("milo".to_string(), "DONE: x".to_string())
        );
        assert_eq!(
            message_parts(&RawMessage::Text("plain hello".into())),
            (String::new(), "plain hello".to_string())
        );
        assert_eq!(
            message_parts(&RawMessage::Other),
            (String::new(), String::new())
        );
    }

    #[test]
    fn window_line_forms() {
        let dict = WindowInput {
            source_window: Some(SourceWindow::Dict {
                max_messages: Some(500),
                max_hours: Some(WindowHours::Float(24.0)),
                messages_kept: Some(120),
                messages_dropped: Some(380),
            }),
            window_start: None,
        };
        assert_eq!(
            window_line(&dict),
            "Window: last 500 messages or last 24 hours, 120 kept, 380 dropped"
        );
        let stated = WindowInput {
            source_window: Some(SourceWindow::Text("yesterday".into())),
            window_start: None,
        };
        assert_eq!(window_line(&stated), "Window: yesterday");
        let truncated = WindowInput {
            source_window: None,
            window_start: Some("2026-10-26 08:00".into()),
        };
        assert_eq!(
            window_line(&truncated),
            "Window: from 2026-10-26 08:00 onward. Earlier history is not in this window."
        );
        let unstated = WindowInput::default();
        assert_eq!(
            window_line(&unstated),
            "Window: not stated in this snapshot"
        );
    }
}
