//! Validation caps from `relay/relay.mjs` — refusals are 400s upstream.
//!
//! Ported oddity, noted: the original measures length with JS
//! `String.length`, which counts UTF-16 code units, not characters.
//! A single astral character (e.g. an emoji) counts as 2 there and
//! as 1 in Rust's `chars()`. `utf16_len` below reproduces the JS
//! count so cap behavior matches exactly.

/// Room names: `/^[a-z0-9-]{1,32}$/`.
pub fn valid_room(room: &str) -> bool {
    let len = room.len();
    if len < 1 || len > 32 {
        return false;
    }
    room.bytes()
        .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
}

/// Severities: exactly "info" | "warning" | "critical".
pub fn valid_severity(severity: &str) -> bool {
    matches!(severity, "info" | "warning" | "critical")
}

pub const MAX_BODY_BYTES: usize = 16384;
pub const MAX_NICK_CHARS: usize = 40;
pub const MAX_TEXT_CHARS: usize = 2000;
pub const MAX_TOPIC_CHARS: usize = 64;

/// Length in UTF-16 code units, matching JS `String.length`.
pub fn utf16_len(value: &str) -> usize {
    value.chars().map(|c| if (c as u32) > 0xFFFF { 2 } else { 1 }).sum()
}

/// The original's `isSingleLine`: a string of 1..=max units with no
/// control characters (U+0000–U+001F or U+007F). Note the original's
/// regex does not exclude U+0080–U+009F, so neither do we.
pub fn is_single_line(value: &str, max: usize) -> bool {
    let len = utf16_len(value);
    if len < 1 || len > max {
        return false;
    }
    !value
        .chars()
        .any(|c| (c as u32) < 0x20 || (c as u32) == 0x7F)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn room_names() {
        assert!(valid_room("main"));
        assert!(valid_room("1"));
        assert!(valid_room("a-b-9"));
        assert!(valid_room(&"a".repeat(32)));
        // Mirrors the JS suite's refusal cases:
        assert!(!valid_room("Bad Room"));
        assert!(!valid_room("UPPER"));
        assert!(!valid_room(""));
        assert!(!valid_room(&"a".repeat(33)));
        assert!(!valid_room("under_score"));
        assert!(!valid_room("with.dot"));
    }

    #[test]
    fn severities() {
        assert!(valid_severity("info"));
        assert!(valid_severity("warning"));
        assert!(valid_severity("critical"));
        assert!(!valid_severity("loud"));
        assert!(!valid_severity("INFO"));
        assert!(!valid_severity(""));
    }

    #[test]
    fn single_line_rules() {
        // Mirrors the JS suite's refusal cases:
        assert!(!is_single_line("", MAX_NICK_CHARS));
        assert!(!is_single_line("pa\nx", MAX_NICK_CHARS));
        assert!(!is_single_line("two\nlines", MAX_TEXT_CHARS));
        assert!(!is_single_line(&"x".repeat(2001), MAX_TEXT_CHARS));
        assert!(!is_single_line(&"x".repeat(41), MAX_NICK_CHARS));
        assert!(!is_single_line(&"x".repeat(65), MAX_TOPIC_CHARS));
        assert!(is_single_line("pax", MAX_NICK_CHARS));
        assert!(is_single_line(&"x".repeat(2000), MAX_TEXT_CHARS));
        // Control characters other than newline also refuse:
        assert!(!is_single_line("a\tb", MAX_TEXT_CHARS));
        assert!(!is_single_line("a\u{7f}b", MAX_TEXT_CHARS));
    }

    #[test]
    fn utf16_length_matches_js() {
        // "😀" is 1 Rust char but 2 JS string-length units.
        assert_eq!(utf16_len("😀"), 2);
        assert_eq!(utf16_len("abc"), 3);
        // So 20 emoji hit the 40-unit nick cap exactly, 21 exceed it.
        assert!(is_single_line(&"😀".repeat(20), MAX_NICK_CHARS));
        assert!(!is_single_line(&"😀".repeat(21), MAX_NICK_CHARS));
    }
}
