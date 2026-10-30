//! Minimal JSON string handling for the file store's JSONL records
//! ({"room": ..., "line": ...}), mirroring `JSON.stringify` /
//! `JSON.parse` for exactly this shape. No external crates.
//!
//! Escaping matches `JSON.stringify`: `"` and `\` escaped, control
//! characters as `\b \f \n \r \t` or `\u00xx`; all other characters
//! (including non-ASCII) pass through unescaped.

/// Escape one string as a JSON string body (without quotes).
pub fn escape(value: &str) -> String {
    let mut out = String::with_capacity(value.len());
    for c in value.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{08}' => out.push_str("\\b"),
            '\u{0c}' => out.push_str("\\f"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out
}

/// Serialize one store record: `{"room":"...","line":"..."}`.
pub fn record_line(room: &str, line: &str) -> String {
    format!(
        "{{\"room\":\"{}\",\"line\":\"{}\"}}",
        escape(room),
        escape(line)
    )
}
