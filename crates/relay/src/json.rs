//! Minimal JSON string handling for the file store's JSONL records
//! (`{"room": ..., "line": ...}`), mirroring `JSON.stringify` /
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

struct Parser<'a> {
    chars: std::str::Chars<'a>,
    peeked: Option<Option<char>>,
}

impl<'a> Parser<'a> {
    fn new(s: &'a str) -> Self {
        Parser {
            chars: s.chars(),
            peeked: None,
        }
    }

    fn peek(&mut self) -> Option<char> {
        if self.peeked.is_none() {
            self.peeked = Some(self.chars.next());
        }
        self.peeked.unwrap()
    }

    fn next(&mut self) -> Option<char> {
        if let Some(p) = self.peeked.take() {
            p
        } else {
            self.chars.next()
        }
    }

    fn skip_ws(&mut self) {
        while matches!(self.peek(), Some(c) if c.is_whitespace()) {
            self.next();
        }
    }

    fn expect(&mut self, want: char) -> Option<()> {
        self.skip_ws();
        if self.next() == Some(want) {
            Some(())
        } else {
            None
        }
    }

    fn parse_string(&mut self) -> Option<String> {
        self.skip_ws();
        if self.next() != Some('"') {
            return None;
        }
        let mut out = String::new();
        loop {
            match self.next()? {
                '"' => return Some(out),
                '\\' => match self.next()? {
                    '"' => out.push('"'),
                    '\\' => out.push('\\'),
                    '/' => out.push('/'),
                    'b' => out.push('\u{08}'),
                    'f' => out.push('\u{0c}'),
                    'n' => out.push('\n'),
                    'r' => out.push('\r'),
                    't' => out.push('\t'),
                    'u' => {
                        let hi = self.parse_hex4()?;
                        if (0xD800..0xDC00).contains(&hi) {
                            // High surrogate: expect a low surrogate.
                            if self.next() != Some('\\') || self.next() != Some('u') {
                                return None;
                            }
                            let lo = self.parse_hex4()?;
                            if !(0xDC00..0xE000).contains(&lo) {
                                return None;
                            }
                            let cp = 0x10000 + ((hi - 0xD800) << 10) + (lo - 0xDC00);
                            out.push(char::from_u32(cp)?);
                        } else if (0xDC00..0xE000).contains(&hi) {
                            return None; // Lone low surrogate.
                        } else {
                            out.push(char::from_u32(hi)?);
                        }
                    }
                    _ => return None,
                },
                c if (c as u32) < 0x20 => return None, // Raw control in string.
                c => out.push(c),
            }
        }
    }

    fn parse_hex4(&mut self) -> Option<u32> {
        let mut v = 0u32;
        for _ in 0..4 {
            let c = self.next()?;
            let d = c.to_digit(16)?;
            v = v * 16 + d;
        }
        Some(v)
    }

    fn skip_value(&mut self) -> Option<()> {
        self.skip_ws();
        match self.peek()? {
            '"' => {
                self.parse_string()?;
            }
            '{' => {
                self.next();
                self.skip_ws();
                if self.peek() == Some('}') {
                    self.next();
                    return Some(());
                }
                loop {
                    self.parse_string()?;
                    self.expect(':')?;
                    self.skip_value()?;
                    self.skip_ws();
                    match self.next()? {
                        ',' => continue,
                        '}' => return Some(()),
                        _ => return None,
                    }
                }
            }
            '[' => {
                self.next();
                self.skip_ws();
                if self.peek() == Some(']') {
                    self.next();
                    return Some(());
                }
                loop {
                    self.skip_value()?;
                    self.skip_ws();
                    match self.next()? {
                        ',' => continue,
                        ']' => return Some(()),
                        _ => return None,
                    }
                }
            }
            't' => {
                for want in ['t', 'r', 'u', 'e'] {
                    if self.next() != Some(want) {
                        return None;
                    }
                }
            }
            'f' => {
                for want in ['f', 'a', 'l', 's', 'e'] {
                    if self.next() != Some(want) {
                        return None;
                    }
                }
            }
            'n' => {
                for want in ['n', 'u', 'l', 'l'] {
                    if self.next() != Some(want) {
                        return None;
                    }
                }
            }
            c if c == '-' || c.is_ascii_digit() => {
                while matches!(self.peek(), Some(c) if c == '-' || c == '+' || c == '.' || c == 'e' || c == 'E' || c.is_ascii_digit())
                {
                    self.next();
                }
            }
            _ => return None,
        }
        Some(())
    }
}

/// Parse one store record. Returns `(room, line)` when the record is
/// a JSON object with string `room` and `line` fields (extra fields
/// ignored, like the original's `typeof` checks); `None` otherwise —
/// the caller skips such records, mirroring the original's torn-record
/// tolerance.
pub fn parse_record(raw: &str) -> Option<(String, String)> {
    let mut p = Parser::new(raw);
    p.expect('{')?;
    let mut room: Option<String> = None;
    let mut line: Option<String> = None;
    p.skip_ws();
    if p.peek() == Some('}') {
        p.next();
    } else {
        loop {
            let key = p.parse_string()?;
            p.expect(':')?;
            if key == "room" || key == "line" {
                let value = p.parse_string()?;
                if key == "room" {
                    room = Some(value);
                } else {
                    line = Some(value);
                }
            } else {
                p.skip_value()?;
            }
            p.skip_ws();
            match p.next()? {
                ',' => continue,
                '}' => break,
                _ => return None,
            }
        }
    }
    p.skip_ws();
    if p.next().is_some() {
        return None; // Trailing garbage.
    }
    match (room, line) {
        (Some(r), Some(l)) => Some((r, l)),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trip() {
        let raw = record_line("main", "pax: say \"hi\" \\ back [ts:1]");
        assert_eq!(
            parse_record(&raw).unwrap(),
            ("main".to_string(), "pax: say \"hi\" \\ back [ts:1]".to_string())
        );
    }

    #[test]
    fn parse_tolerances() {
        // Extra fields ignored; fields in any order.
        assert_eq!(
            parse_record(r#"{"line":"x","room":"r","n":1}"#).unwrap(),
            ("r".to_string(), "x".to_string())
        );
        // Malformed records are None (caller skips them):
        assert!(parse_record("not json").is_none());
        assert!(parse_record(r#"{"room":"r"}"#).is_none());
        assert!(parse_record(r#"{"room":3,"line":"x"}"#).is_none());
        assert!(parse_record(r#"{"room":"r","line":"x"} trailing"#).is_none());
        assert!(parse_record("").is_none());
    }

    #[test]
    fn escape_controls() {
        assert_eq!(escape("a\"b\\c"), "a\\\"b\\\\c");
        assert_eq!(escape("tab\there"), "tab\\there");
    }
}
