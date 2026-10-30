//! `value` — a plain-dict value model for the B12a ports.
//!
//! The Python sources in this batch are written against plain
//! dicts/lists ("all plain dicts so fixtures stay readable"), with
//! `isinstance` checks and silent-skip behavior for malformed
//! entries. This enum is the Rust shape of that model: maps keep
//! insertion order, ints and floats stay distinct (Python prints
//! them differently), and every accessor mirrors the Python
//! defensive-read style of the sources.

use std::collections::BTreeMap;
use std::fmt::Write as _;

#[derive(Debug, Clone, PartialEq)]
pub enum Value {
    Null,
    Bool(bool),
    Int(i64),
    Float(f64),
    Str(String),
    List(Vec<Value>),
    Map(Vec<(String, Value)>),
}

impl Value {
    pub fn obj(pairs: Vec<(&str, Value)>) -> Value {
        Value::Map(pairs.into_iter().map(|(k, v)| (k.to_string(), v)).collect())
    }

    pub fn s(text: &str) -> Value {
        Value::Str(text.to_string())
    }

    pub fn is_dict(&self) -> bool {
        matches!(self, Value::Map(_))
    }

    pub fn is_list(&self) -> bool {
        matches!(self, Value::List(_))
    }

    /// `value.get(key)` — Null when absent or not a dict.
    pub fn get(&self, key: &str) -> Value {
        match self {
            Value::Map(pairs) => pairs
                .iter()
                .find(|(k, _)| k == key)
                .map(|(_, v)| v.clone())
                .unwrap_or(Value::Null),
            _ => Value::Null,
        }
    }

    pub fn contains_key(&self, key: &str) -> bool {
        matches!(self, Value::Map(pairs) if pairs.iter().any(|(k, _)| k == key))
    }

    pub fn set(&mut self, key: &str, val: Value) {
        if let Value::Map(pairs) = self {
            if let Some(slot) = pairs.iter_mut().find(|(k, _)| k == key) {
                slot.1 = val;
                return;
            }
            pairs.push((key.to_string(), val));
        }
    }

    /// `dict.pop(key, None)` — remove a key when present.
    pub fn remove(&mut self, key: &str) {
        if let Value::Map(pairs) = self {
            pairs.retain(|(k, _)| k != key);
        }
    }

    pub fn as_map(&self) -> Option<&Vec<(String, Value)>> {
        match self {
            Value::Map(pairs) => Some(pairs),
            _ => None,
        }
    }

    pub fn as_list(&self) -> Option<&Vec<Value>> {
        match self {
            Value::List(items) => Some(items),
            _ => None,
        }
    }

    /// Python `_text`: a non-empty string value, else None.
    pub fn as_text(&self) -> Option<&str> {
        match self {
            Value::Str(s) if !s.is_empty() => Some(s.as_str()),
            _ => None,
        }
    }

    pub fn as_str(&self) -> Option<&str> {
        match self {
            Value::Str(s) => Some(s.as_str()),
            _ => None,
        }
    }

    /// A string, accepting exactly what Python's isinstance(str) does.
    pub fn is_str(&self) -> bool {
        matches!(self, Value::Str(_))
    }

    /// Python `isinstance(v, (int, float)) and not isinstance(v, bool)`.
    pub fn as_number(&self) -> Option<f64> {
        match self {
            Value::Int(i) => Some(*i as f64),
            Value::Float(f) => Some(*f),
            _ => None,
        }
    }

    /// Python int check excluding bool.
    pub fn as_int(&self) -> Option<i64> {
        match self {
            Value::Int(i) => Some(*i),
            _ => None,
        }
    }

    pub fn is_bool(&self) -> bool {
        matches!(self, Value::Bool(_))
    }

    pub fn as_bool(&self) -> Option<bool> {
        match self {
            Value::Bool(b) => Some(*b),
            _ => None,
        }
    }

    pub fn is_null(&self) -> bool {
        matches!(self, Value::Null)
    }

    /// Python truthiness for the shapes fixtures use.
    pub fn truthy(&self) -> bool {
        match self {
            Value::Null => false,
            Value::Bool(b) => *b,
            Value::Int(i) => *i != 0,
            Value::Float(f) => *f != 0.0,
            Value::Str(s) => !s.is_empty(),
            Value::List(items) => !items.is_empty(),
            Value::Map(pairs) => !pairs.is_empty(),
        }
    }

    /// Python `str(value)` for the shapes the sources format with %s.
    pub fn py_str(&self) -> String {
        match self {
            Value::Null => "None".to_string(),
            Value::Bool(b) => if *b { "True" } else { "False" }.to_string(),
            Value::Int(i) => i.to_string(),
            Value::Float(f) => py_float_str(*f),
            Value::Str(s) => s.clone(),
            Value::List(items) => {
                let parts: Vec<String> = items.iter().map(|v| v.py_repr()).collect();
                format!("[{}]", parts.join(", "))
            }
            Value::Map(pairs) => {
                let parts: Vec<String> = pairs
                    .iter()
                    .map(|(k, v)| format!("'{}': {}", k, v.py_repr()))
                    .collect();
                format!("{{{}}}", parts.join(", "))
            }
        }
    }

    /// Python `repr(value)` for the shapes fixtures print.
    pub fn py_repr(&self) -> String {
        match self {
            Value::Str(s) => py_repr_str(s),
            _ => self.py_str(),
        }
    }
}

/// Python str(float): shortest round-trip, integral floats keep ".0".
pub fn py_float_str(f: f64) -> String {
    if f == f.trunc() && f.abs() < 1e16 && f.is_finite() {
        format!("{:.1}", f)
    } else {
        format!("{}", f)
    }
}

/// Python repr(str) with single quotes, escaping like CPython for
/// the common cases fixtures print.
pub fn py_repr_str(s: &str) -> String {
    let mut out = String::from("'");
    for ch in s.chars() {
        match ch {
            '\'' => out.push_str("\\'"),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => {
                let _ = write!(out, "\\x{:02x}", c as u32);
            }
            c => out.push(c),
        }
    }
    out.push('\'');
    out
}

/// Parse JSON text into a Value (objects keep document order).
/// Returns None on malformed input, mirroring a failed json.load.
pub fn parse_json(text: &str) -> Option<Value> {
    let bytes = text.as_bytes();
    let mut pos = 0usize;
    let value = parse_value(bytes, &mut pos)?;
    skip_ws(bytes, &mut pos);
    if pos != bytes.len() {
        return None;
    }
    Some(value)
}

fn skip_ws(bytes: &[u8], pos: &mut usize) {
    while *pos < bytes.len() && matches!(bytes[*pos], b' ' | b'\t' | b'\n' | b'\r') {
        *pos += 1;
    }
}

fn parse_value(bytes: &[u8], pos: &mut usize) -> Option<Value> {
    skip_ws(bytes, pos);
    match *bytes.get(*pos)? {
        b'{' => {
            *pos += 1;
            let mut pairs = Vec::new();
            skip_ws(bytes, pos);
            if bytes.get(*pos) == Some(&b'}') {
                *pos += 1;
                return Some(Value::Map(pairs));
            }
            loop {
                skip_ws(bytes, pos);
                let key = match parse_value(bytes, pos)? {
                    Value::Str(s) => s,
                    _ => return None,
                };
                skip_ws(bytes, pos);
                if bytes.get(*pos) != Some(&b':') {
                    return None;
                }
                *pos += 1;
                let val = parse_value(bytes, pos)?;
                pairs.push((key, val));
                skip_ws(bytes, pos);
                match bytes.get(*pos) {
                    Some(b',') => {
                        *pos += 1;
                    }
                    Some(b'}') => {
                        *pos += 1;
                        return Some(Value::Map(pairs));
                    }
                    _ => return None,
                }
            }
        }
        b'[' => {
            *pos += 1;
            let mut items = Vec::new();
            skip_ws(bytes, pos);
            if bytes.get(*pos) == Some(&b']') {
                *pos += 1;
                return Some(Value::List(items));
            }
            loop {
                items.push(parse_value(bytes, pos)?);
                skip_ws(bytes, pos);
                match bytes.get(*pos) {
                    Some(b',') => {
                        *pos += 1;
                    }
                    Some(b']') => {
                        *pos += 1;
                        return Some(Value::List(items));
                    }
                    _ => return None,
                }
            }
        }
        b'"' => parse_json_string(bytes, pos).map(Value::Str),
        b't' => {
            if bytes[*pos..].starts_with(b"true") {
                *pos += 4;
                Some(Value::Bool(true))
            } else {
                None
            }
        }
        b'f' => {
            if bytes[*pos..].starts_with(b"false") {
                *pos += 5;
                Some(Value::Bool(false))
            } else {
                None
            }
        }
        b'n' => {
            if bytes[*pos..].starts_with(b"null") {
                *pos += 4;
                Some(Value::Null)
            } else {
                None
            }
        }
        _ => parse_json_number(bytes, pos),
    }
}

fn parse_json_string(bytes: &[u8], pos: &mut usize) -> Option<String> {
    if bytes.get(*pos) != Some(&b'"') {
        return None;
    }
    *pos += 1;
    let mut out = String::new();
    loop {
        let byte = *bytes.get(*pos)?;
        *pos += 1;
        match byte {
            b'"' => return Some(out),
            b'\\' => {
                let esc = *bytes.get(*pos)?;
                *pos += 1;
                match esc {
                    b'"' => out.push('"'),
                    b'\\' => out.push('\\'),
                    b'/' => out.push('/'),
                    b'b' => out.push('\u{0008}'),
                    b'f' => out.push('\u{000C}'),
                    b'n' => out.push('\n'),
                    b'r' => out.push('\r'),
                    b't' => out.push('\t'),
                    b'u' => {
                        let hex = bytes.get(*pos..*pos + 4)?;
                        let code = u32::from_str_radix(std::str::from_utf8(hex).ok()?, 16).ok()?;
                        *pos += 4;
                        if (0xD800..0xDC00).contains(&code) {
                            // High surrogate: expect a low surrogate pair.
                            if bytes.get(*pos) == Some(&b'\\')
                                && bytes.get(*pos + 1) == Some(&b'u')
                            {
                                let hex2 = bytes.get(*pos + 2..*pos + 6)?;
                                let low =
                                    u32::from_str_radix(std::str::from_utf8(hex2).ok()?, 16)
                                        .ok()?;
                                if (0xDC00..0xE000).contains(&low) {
                                    *pos += 6;
                                    let c = 0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00);
                                    out.push(char::from_u32(c)?);
                                    continue;
                                }
                            }
                            return None;
                        }
                        out.push(char::from_u32(code)?);
                    }
                    _ => return None,
                }
            }
            _ => {
                // Consume one UTF-8 encoded char starting at byte.
                let start = *pos - 1;
                let len = utf8_len(byte)?;
                let end = start + len;
                if end > bytes.len() {
                    return None;
                }
                out.push_str(std::str::from_utf8(&bytes[start..end]).ok()?);
                *pos = end;
            }
        }
    }
}

fn utf8_len(first: u8) -> Option<usize> {
    match first {
        0x00..=0x7F => Some(1),
        0xC2..=0xDF => Some(2),
        0xE0..=0xEF => Some(3),
        0xF0..=0xF4 => Some(4),
        _ => None,
    }
}

fn parse_json_number(bytes: &[u8], pos: &mut usize) -> Option<Value> {
    let start = *pos;
    if bytes.get(*pos) == Some(&b'-') {
        *pos += 1;
    }
    let mut is_float = false;
    while let Some(b) = bytes.get(*pos) {
        match b {
            b'0'..=b'9' => *pos += 1,
            b'.' | b'e' | b'E' | b'+' | b'-' => {
                is_float = true;
                *pos += 1;
            }
            _ => break,
        }
    }
    if *pos == start {
        return None;
    }
    let text = std::str::from_utf8(&bytes[start..*pos]).ok()?;
    if !is_float {
        if let Ok(i) = text.parse::<i64>() {
            return Some(Value::Int(i));
        }
    }
    text.parse::<f64>().ok().map(Value::Float)
}

/// Serialize like Python `json.dumps` with default separators.
pub fn to_json(value: &Value) -> String {
    let mut out = String::new();
    write_json(value, &mut out, None);
    out
}

/// Serialize like Python `json.dumps(value, indent=N)` when indent set.
pub fn to_json_pretty(value: &Value, indent: usize) -> String {
    let mut out = String::new();
    write_json(value, &mut out, Some((indent, 0)));
    out
}

fn write_json(value: &Value, out: &mut String, indent: Option<(usize, usize)>) {
    match value {
        Value::Null => out.push_str("null"),
        Value::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        Value::Int(i) => {
            let _ = write!(out, "{}", i);
        }
        Value::Float(f) => out.push_str(&py_float_str(*f)),
        Value::Str(s) => write_json_string(s, out),
        Value::List(items) => {
            out.push('[');
            for (idx, item) in items.iter().enumerate() {
                if idx > 0 {
                    out.push(',');
                }
                if let Some((step, depth)) = indent {
                    out.push('\n');
                    out.push_str(&" ".repeat(step * (depth + 1)));
                    write_json(item, out, Some((step, depth + 1)));
                } else {
                    if idx > 0 {
                        out.push(' ');
                    }
                    write_json(item, out, None);
                }
            }
            if let Some((step, depth)) = indent {
                if !items.is_empty() {
                    out.push('\n');
                    out.push_str(&" ".repeat(step * depth));
                }
            }
            out.push(']');
        }
        Value::Map(pairs) => {
            // Python dicts preserve insertion order; sort only when the
            // caller built the map sorted. Kept as stored.
            let ordered: Vec<&(String, Value)> = pairs.iter().collect();
            out.push('{');
            for (idx, (key, val)) in ordered.iter().enumerate() {
                if idx > 0 {
                    out.push(',');
                }
                if let Some((step, depth)) = indent {
                    out.push('\n');
                    out.push_str(&" ".repeat(step * (depth + 1)));
                    write_json_string(key, out);
                    out.push_str(": ");
                    write_json(val, out, Some((step, depth + 1)));
                } else {
                    if idx > 0 {
                        out.push(' ');
                    }
                    write_json_string(key, out);
                    out.push_str(": ");
                    write_json(val, out, None);
                }
            }
            if let Some((step, depth)) = indent {
                if !pairs.is_empty() {
                    out.push('\n');
                    out.push_str(&" ".repeat(step * depth));
                }
            }
            out.push('}');
        }
    }
}

fn write_json_string(s: &str, out: &mut String) {
    out.push('"');
    for ch in s.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{0008}' => out.push_str("\\b"),
            '\u{000C}' => out.push_str("\\f"),
            c if (c as u32) < 0x20 => {
                let _ = write!(out, "\\u{:04x}", c as u32);
            }
            c => out.push(c),
        }
    }
    out.push('"');
}

/// Sorted-key map helper for fixtures that Python builds as dict
/// literals (key order in Python output follows insertion, so
/// callers insert in literal order; this helper is for lookups
/// where order does not matter).
pub fn sorted_map(pairs: Vec<(String, Value)>) -> Value {
    let mut map = BTreeMap::new();
    for (k, v) in pairs {
        map.insert(k, v);
    }
    Value::Map(map.into_iter().collect())
}
