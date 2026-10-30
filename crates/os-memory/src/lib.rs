//! Crate `os-memory` — Meta OS Rust rebuild skeleton (B00).
//!
//! Batch B17 — Memory service. Owner: Milo.
//! Source files this batch ports:
//! - `os/mos/memory.py`
//! - `os/tests/test_intel_brief_memory_depth_caller.py`
//! - `os/tests/test_os078_memory.py`
//!
//! Skeleton only: no logic yet. The Python/Node sources listed above are
//! the spec — port behavior, do not redesign. See BATCHES.md for the
//! compile gates and the parity rule.
//!
//! B17 port notes (Milo, gate 1). The store part ports `os/mos/memory.py`
//! verbatim in behavior: journaled, versioned, per-agent + shared
//! namespaces under a store root. Two deliberate adaptations, both
//! forced by the crate shape rather than by choice:
//! - The Python CLI (`memory.py main()`) has no bin crate in this batch,
//!   so it is ported as the library function `run_cli`, which returns
//!   its exit code and captured stdout/stderr instead of writing to the
//!   process streams. Same commands, same outputs, same exit codes.
//! - The depth-caller tests exercise `with_memory_depth` and
//!   `memory_depth_lines`, which live in `os/intel/brief.py` (batch B10,
//!   Hana's crate), not in `memory.py`. The batch map assigns that test
//!   file to B17, so those two small, self-contained functions are
//!   ported here over the JSON value type; the full brief generator
//!   (`generate_morning_brief`, one test) stays with B10 and is listed
//!   in the completion report, not duplicated here.
//! - Rust has no `serde`: the journal JSON reader/writer below is a
//!   minimal std-only implementation covering the entry shape (objects,
//!   strings with escapes, integers, and the JSON scalars a journal
//!   line may carry). A journal line outside that shape raises exactly
//!   like the Python reader does.

use std::collections::BTreeMap;
use std::fmt;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

/// Store root baked on the image (default from `memory.py`).
pub const STORE_ROOT_DEFAULT: &str = "/var/lib/metaos/memory";
/// Subdirectory holding per-agent namespaces.
pub const AGENTS_DIR: &str = "agents";
/// Subdirectory holding the shared crew namespace.
pub const SHARED_DIR: &str = "shared";
/// Journal file name inside every namespace directory.
pub const JOURNAL_NAME: &str = "journal.jsonl";

// ---------------------------------------------------------------------------
// Minimal JSON value, parser, and serializer (std-only).
//
// The journal format is one JSON object per line. The parser accepts full
// JSON values; the shape checks in the journal reader then enforce the
// entry shape, mirroring `memory.py` (a line that does not parse, or
// does not carry the entry shape, raises).
// ---------------------------------------------------------------------------

/// A JSON value. Object members keep insertion order; lookups are linear,
/// which is fine for entry-sized objects.
#[derive(Clone, Debug, PartialEq)]
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
    /// Look up a key in an object, or `None` when this is not an object
    /// or the key is absent.
    pub fn get(&self, key: &str) -> Option<&Value> {
        match self {
            Value::Map(members) => members
                .iter()
                .find(|(k, _)| k == key)
                .map(|(_, v)| v),
            _ => None,
        }
    }

    /// The string value, or `None` for any other shape.
    pub fn as_str(&self) -> Option<&str> {
        match self {
            Value::Str(s) => Some(s),
            _ => None,
        }
    }

    /// `true` only for the JSON boolean `true` (Python's `is True`).
    pub fn is_json_true(&self) -> bool {
        matches!(self, Value::Bool(true))
    }
}

struct JsonParser<'a> {
    text: &'a str,
    pos: usize,
}

impl<'a> JsonParser<'a> {
    fn new(text: &'a str) -> Self {
        JsonParser { text, pos: 0 }
    }

    fn rest(&self) -> &'a str {
        &self.text[self.pos..]
    }

    fn skip_ws(&mut self) {
        while let Some(ch) = self.rest().chars().next() {
            if ch == ' ' || ch == '\t' || ch == '\n' || ch == '\r' {
                self.pos += ch.len_utf8();
            } else {
                break;
            }
        }
    }

    fn peek(&self) -> Option<char> {
        self.rest().chars().next()
    }

    fn eat(&mut self, expected: char) -> Result<(), String> {
        if self.peek() == Some(expected) {
            self.pos += expected.len_utf8();
            Ok(())
        } else {
            Err(format!("expected '{}'", expected))
        }
    }

    fn parse_document(&mut self) -> Result<Value, String> {
        self.skip_ws();
        let value = self.parse_value()?;
        self.skip_ws();
        if self.pos != self.text.len() {
            return Err("trailing characters after value".to_string());
        }
        Ok(value)
    }

    fn parse_value(&mut self) -> Result<Value, String> {
        self.skip_ws();
        match self.peek() {
            Some('{') => self.parse_object(),
            Some('[') => self.parse_array(),
            Some('"') => Ok(Value::Str(self.parse_string()?)),
            Some('t') => self.parse_literal("true", Value::Bool(true)),
            Some('f') => self.parse_literal("false", Value::Bool(false)),
            Some('n') => self.parse_literal("null", Value::Null),
            Some(ch) if ch == '-' || ch.is_ascii_digit() => self.parse_number(),
            Some(ch) => Err(format!("unexpected character '{}'", ch)),
            None => Err("unexpected end of input".to_string()),
        }
    }

    fn parse_literal(&mut self, word: &str, value: Value) -> Result<Value, String> {
        if self.rest().starts_with(word) {
            self.pos += word.len();
            Ok(value)
        } else {
            Err(format!("invalid literal, expected {}", word))
        }
    }

    fn parse_number(&mut self) -> Result<Value, String> {
        let start = self.pos;
        let bytes = self.text.as_bytes();
        let mut i = self.pos;
        if i < bytes.len() && bytes[i] == b'-' {
            i += 1;
        }
        let int_start = i;
        while i < bytes.len() && bytes[i].is_ascii_digit() {
            i += 1;
        }
        if i == int_start {
            return Err("invalid number".to_string());
        }
        let mut is_float = false;
        if i < bytes.len() && bytes[i] == b'.' {
            is_float = true;
            i += 1;
            let frac_start = i;
            while i < bytes.len() && bytes[i].is_ascii_digit() {
                i += 1;
            }
            if i == frac_start {
                return Err("invalid number fraction".to_string());
            }
        }
        if i < bytes.len() && (bytes[i] == b'e' || bytes[i] == b'E') {
            is_float = true;
            i += 1;
            if i < bytes.len() && (bytes[i] == b'+' || bytes[i] == b'-') {
                i += 1;
            }
            let exp_start = i;
            while i < bytes.len() && bytes[i].is_ascii_digit() {
                i += 1;
            }
            if i == exp_start {
                return Err("invalid number exponent".to_string());
            }
        }
        let literal = &self.text[start..i];
        self.pos = i;
        if is_float {
            literal
                .parse::<f64>()
                .map(Value::Float)
                .map_err(|_| "number out of range".to_string())
        } else {
            match literal.parse::<i64>() {
                Ok(n) => Ok(Value::Int(n)),
                Err(_) => literal
                    .parse::<f64>()
                    .map(Value::Float)
                    .map_err(|_| "number out of range".to_string()),
            }
        }
    }

    fn hex4(&mut self) -> Result<u32, String> {
        let mut code: u32 = 0;
        for _ in 0..4 {
            let ch = self.peek().ok_or("truncated unicode escape")?;
            let digit = ch
                .to_digit(16)
                .ok_or_else(|| format!("bad unicode escape '{}'", ch))?;
            code = code * 16 + digit;
            self.pos += ch.len_utf8();
        }
        Ok(code)
    }

    fn parse_string(&mut self) -> Result<String, String> {
        self.eat('"')?;
        let mut out = String::new();
        loop {
            let ch = self.peek().ok_or("unterminated string")?;
            match ch {
                '"' => {
                    self.pos += 1;
                    return Ok(out);
                }
                '\\' => {
                    self.pos += 1;
                    let esc = self.peek().ok_or("truncated escape")?;
                    self.pos += esc.len_utf8();
                    match esc {
                        '"' => out.push('"'),
                        '\\' => out.push('\\'),
                        '/' => out.push('/'),
                        'b' => out.push('\u{0008}'),
                        'f' => out.push('\u{000C}'),
                        'n' => out.push('\n'),
                        'r' => out.push('\r'),
                        't' => out.push('\t'),
                        'u' => {
                            let unit = self.hex4()?;
                            if (0xD800..0xDC00).contains(&unit) {
                                // High surrogate: a low surrogate must follow.
                                if self.peek() == Some('\\') {
                                    self.pos += 1;
                                    if self.peek() == Some('u') {
                                        self.pos += 1;
                                        let low = self.hex4()?;
                                        if (0xDC00..0xE000).contains(&low) {
                                            let c = 0x10000
                                                + ((unit - 0xD800) << 10)
                                                + (low - 0xDC00);
                                            out.push(
                                                char::from_u32(c).ok_or(
                                                    "invalid surrogate pair",
                                                )?,
                                            );
                                        } else {
                                            return Err(
                                                "lone high surrogate".to_string(),
                                            );
                                        }
                                    } else {
                                        return Err(
                                            "lone high surrogate".to_string(),
                                        );
                                    }
                                } else {
                                    return Err("lone high surrogate".to_string());
                                }
                            } else if (0xDC00..0xE000).contains(&unit) {
                                return Err("lone low surrogate".to_string());
                            } else {
                                out.push(
                                    char::from_u32(unit)
                                        .ok_or("invalid unicode escape")?,
                                );
                            }
                        }
                        other => {
                            return Err(format!("bad escape '\\{}'", other));
                        }
                    }
                }
                c if (c as u32) < 0x20 => {
                    return Err("unescaped control character in string".to_string());
                }
                c => {
                    out.push(c);
                    self.pos += c.len_utf8();
                }
            }
        }
    }

    fn parse_object(&mut self) -> Result<Value, String> {
        self.eat('{')?;
        let mut members = Vec::new();
        self.skip_ws();
        if self.peek() == Some('}') {
            self.pos += 1;
            return Ok(Value::Map(members));
        }
        loop {
            self.skip_ws();
            let key = self.parse_string()?;
            self.skip_ws();
            self.eat(':')?;
            let value = self.parse_value()?;
            members.push((key, value));
            self.skip_ws();
            match self.peek() {
                Some(',') => {
                    self.pos += 1;
                }
                Some('}') => {
                    self.pos += 1;
                    return Ok(Value::Map(members));
                }
                _ => return Err("expected ',' or '}' in object".to_string()),
            }
        }
    }

    fn parse_array(&mut self) -> Result<Value, String> {
        self.eat('[')?;
        let mut items = Vec::new();
        self.skip_ws();
        if self.peek() == Some(']') {
            self.pos += 1;
            return Ok(Value::List(items));
        }
        loop {
            let value = self.parse_value()?;
            items.push(value);
            self.skip_ws();
            match self.peek() {
                Some(',') => {
                    self.pos += 1;
                }
                Some(']') => {
                    self.pos += 1;
                    return Ok(Value::List(items));
                }
                _ => return Err("expected ',' or ']' in array".to_string()),
            }
        }
    }
}

/// Parse one JSON document. Mirrors `json.loads` for the shapes this crate
/// reads; anything else is a parse error.
pub fn parse_json(text: &str) -> Result<Value, String> {
    JsonParser::new(text).parse_document()
}

/// Serialize a JSON string the way `json.dumps` does with its default
/// `ensure_ascii`: non-ASCII characters become `\uXXXX` escapes (with
/// surrogate pairs above the BMP), and the usual short escapes apply.
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
                out.push_str(&format!("\\u{:04x}", c as u32));
            }
            c if (c as u32) < 0x80 => out.push(c),
            c if (c as u32) <= 0xFFFF => {
                out.push_str(&format!("\\u{:04x}", c as u32));
            }
            c => {
                let n = c as u32 - 0x10000;
                out.push_str(&format!(
                    "\\u{:04x}\\u{:04x}",
                    0xD800 + (n >> 10),
                    0xDC00 + (n & 0x3FF)
                ));
            }
        }
    }
    out.push('"');
}

/// Serialize a value. Object members are emitted in the order stored;
/// callers that need `sort_keys` order sort before calling.
pub fn write_json(value: &Value, out: &mut String) {
    match value {
        Value::Null => out.push_str("null"),
        Value::Bool(true) => out.push_str("true"),
        Value::Bool(false) => out.push_str("false"),
        Value::Int(n) => out.push_str(&n.to_string()),
        Value::Float(f) => {
            if f.is_finite() && f.fract() == 0.0 {
                out.push_str(&format!("{:.1}", f));
            } else {
                out.push_str(&f.to_string());
            }
        }
        Value::Str(s) => write_json_string(s, out),
        Value::List(items) => {
            out.push('[');
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push_str(", ");
                }
                write_json(item, out);
            }
            out.push(']');
        }
        Value::Map(members) => {
            out.push('{');
            for (i, (k, v)) in members.iter().enumerate() {
                if i > 0 {
                    out.push_str(", ");
                }
                write_json_string(k, out);
                out.push_str(": ");
                write_json(v, out);
            }
            out.push('}');
        }
    }
}

/// Serialize a value as a single JSON document with object keys sorted,
/// matching `json.dumps(..., sort_keys=True)` apart from item separators
/// (`json.dumps` uses `", "` and `": "` by default, as here).
pub fn to_json_sorted(value: &Value) -> String {
    fn sorted(value: &Value) -> Value {
        match value {
            Value::Map(members) => {
                let mut sorted: Vec<(String, Value)> = members
                    .iter()
                    .map(|(k, v)| (k.clone(), sorted(v)))
                    .collect();
                sorted.sort_by(|a, b| a.0.cmp(&b.0));
                Value::Map(sorted)
            }
            Value::List(items) => {
                Value::List(items.iter().map(sorted).collect())
            }
            other => other.clone(),
        }
    }
    let mut out = String::new();
    write_json(&sorted(value), &mut out);
    out
}

// ---------------------------------------------------------------------------
// Memory store: port of `os/mos/memory.py`.
// ---------------------------------------------------------------------------

/// Refused write, bad nick or key, missing entry, corrupt journal.
/// Mirrors `MemoryError`, a `ValueError` subclass in Python.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MemoryError(pub String);

impl fmt::Display for MemoryError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for MemoryError {}

impl From<io::Error> for MemoryError {
    fn from(err: io::Error) -> Self {
        MemoryError(err.to_string())
    }
}

/// One journal entry. `extra` carries any journal fields beyond the five
/// known ones: Python's reader returns the whole stored dict on read, so
/// extras round-trip instead of being dropped.
#[derive(Clone, Debug, PartialEq)]
pub struct Entry {
    pub key: String,
    pub version: i64,
    pub author: String,
    pub ts: i64,
    pub text: String,
    pub extra: Vec<(String, Value)>,
}

impl Entry {
    /// The entry as a JSON value (known fields plus extras).
    pub fn to_value(&self) -> Value {
        let mut members = vec![
            ("key".to_string(), Value::Str(self.key.clone())),
            ("version".to_string(), Value::Int(self.version)),
            ("author".to_string(), Value::Str(self.author.clone())),
            ("ts".to_string(), Value::Int(self.ts)),
            ("text".to_string(), Value::Str(self.text.clone())),
        ];
        members.extend(self.extra.iter().cloned());
        Value::Map(members)
    }

    /// The entry as one journal line, keys sorted like `json.dumps` with
    /// `sort_keys=True`.
    pub fn to_journal_line(&self) -> String {
        to_json_sorted(&self.to_value())
    }
}

/// The result of a write: the stored entry plus whether it created a new
/// version. Mirrors the dict `write` returns, with `new_version` included.
#[derive(Clone, Debug, PartialEq)]
pub struct WriteOutcome {
    pub entry: Entry,
    pub new_version: bool,
}

/// An agent's latest entries plus the shared latest entries, kept under
/// separate keys and never merged. Mirrors `read_all`.
#[derive(Clone, Debug, PartialEq)]
pub struct ReadAll {
    pub own: BTreeMap<String, Entry>,
    pub shared: BTreeMap<String, Entry>,
}

/// The two directories a launcher mounts into a process. Mirrors
/// `mount_paths`.
#[derive(Clone, Debug, PartialEq)]
pub struct MountPaths {
    pub own: PathBuf,
    pub shared: PathBuf,
}

/// The store namespaces `ensure_root` creates. Mirrors its return dict.
#[derive(Clone, Debug, PartialEq)]
pub struct EnsureRoot {
    pub agents: PathBuf,
    pub shared: PathBuf,
}

fn validate_agent(agent: &str) -> Result<(), MemoryError> {
    if agent.is_empty() {
        return Err(MemoryError(
            "agent nick must be a non-empty string".to_string(),
        ));
    }
    // Ported oddity, kept: Python checks slash/backslash/NUL and the
    // dot-only nicks in one branch before the charset branch, so a nick
    // like "a/b" reports "single path segment", not the charset message.
    if agent.contains('/')
        || agent.contains('\\')
        || agent.contains('\0')
        || agent == "."
        || agent == ".."
    {
        return Err(MemoryError(
            "agent nick must be a single path segment".to_string(),
        ));
    }
    // Python `str.isalnum` is Unicode-aware; `char::is_alphanumeric` is
    // the same class to the precision these nicks need.
    if !agent
        .chars()
        .all(|ch| ch.is_alphanumeric() || ch == '.' || ch == '_' || ch == '-')
    {
        return Err(MemoryError(
            "agent nick holds characters outside [A-Za-z0-9._-]".to_string(),
        ));
    }
    Ok(())
}

fn validate_key(key: &str) -> Result<(), MemoryError> {
    if key.is_empty() {
        return Err(MemoryError(
            "memory key must be a non-empty string".to_string(),
        ));
    }
    if key.starts_with('/') || key.contains('\0') || key.contains('\\') {
        return Err(MemoryError(
            "memory key must be a relative POSIX path".to_string(),
        ));
    }
    if key
        .split('/')
        .any(|part| part.is_empty() || part == "." || part == "..")
    {
        return Err(MemoryError(
            "memory key must not contain empty, . or .. segments".to_string(),
        ));
    }
    Ok(())
}

fn namespace_dir(root: &Path, agent: Option<&str>) -> Result<PathBuf, MemoryError> {
    match agent {
        None => Ok(root.join(SHARED_DIR)),
        Some(nick) => {
            validate_agent(nick)?;
            Ok(root.join(AGENTS_DIR).join(nick))
        }
    }
}

fn journal_path(root: &Path, agent: Option<&str>) -> Result<PathBuf, MemoryError> {
    Ok(namespace_dir(root, agent)?.join(JOURNAL_NAME))
}

/// Read one namespace's journal. A missing journal reads as empty; a
/// blank line is skipped; a line that does not parse, or does not carry
/// the entry shape, raises. Mirrors `_read_journal`.
fn read_journal(root: &Path, agent: Option<&str>) -> Result<Vec<Entry>, MemoryError> {
    let path = journal_path(root, agent)?;
    if !path.exists() {
        return Ok(Vec::new());
    }
    let text = fs::read_to_string(&path)
        .map_err(|err| MemoryError(format!("journal unreadable: {}", err)))?;
    let mut entries = Vec::new();
    for (index, line) in text.lines().enumerate() {
        let lineno = index + 1;
        if line.trim().is_empty() {
            continue;
        }
        let value = parse_json(line).map_err(|detail| {
            MemoryError(format!("journal line {} does not parse: {}", lineno, detail))
        })?;
        entries.push(entry_from_value(&value).ok_or_else(|| {
            MemoryError(format!("journal line {} has an unexpected shape", lineno))
        })?);
    }
    Ok(entries)
}

/// Validate one parsed journal line against the entry shape. `version`
/// and `ts` accept a JSON boolean as well as an integer: Python's
/// `isinstance(True, int)` is true, so a journal line carrying `true`
/// for those fields reads as version/ts 1 there, and it does here too.
/// That bool quirk is ported, not redesigned away.
fn entry_from_value(value: &Value) -> Option<Entry> {
    let key = value.get("key")?.as_str()?.to_string();
    let version = match value.get("version")? {
        Value::Int(n) => *n,
        Value::Bool(true) => 1,
        Value::Bool(false) => 0,
        _ => return None,
    };
    let text = value.get("text")?.as_str()?.to_string();
    let author = value.get("author")?.as_str()?.to_string();
    let ts = match value.get("ts")? {
        Value::Int(n) => *n,
        Value::Bool(true) => 1,
        Value::Bool(false) => 0,
        _ => return None,
    };
    let known = ["key", "version", "text", "author", "ts"];
    let mut extra = Vec::new();
    if let Value::Map(members) = value {
        for (k, v) in members {
            if !known.contains(&k.as_str()) {
                extra.push((k.clone(), v.clone()));
            }
        }
    }
    Some(Entry {
        key,
        version,
        author,
        ts,
        text,
        extra,
    })
}

fn append_entry(root: &Path, agent: Option<&str>, entry: &Entry) -> Result<(), MemoryError> {
    let path = journal_path(root, agent)?;
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    use std::io::Write as _;
    let mut handle = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&path)?;
    writeln!(handle, "{}", entry.to_journal_line())?;
    Ok(())
}

fn latest<'a>(entries: &'a [Entry], key: &str) -> Option<&'a Entry> {
    entries.iter().rev().find(|entry| entry.key == key)
}

fn now_unix() -> i64 {
    match SystemTime::now().duration_since(UNIX_EPOCH) {
        Ok(d) => d.as_secs() as i64,
        Err(err) => -(err.duration().as_secs() as i64),
    }
}

fn write_inner(
    root: &Path,
    agent: Option<&str>,
    key: &str,
    text: &str,
    author: &str,
    ts: Option<i64>,
) -> Result<WriteOutcome, MemoryError> {
    // Validation order mirrors Python: agent, then key, then the write.
    // (The non-string-text refusal has no Rust form: `text: &str` cannot
    // carry bytes, so the type system enforces it at compile time.)
    if let Some(nick) = agent {
        validate_agent(nick)?;
    }
    validate_key(key)?;
    let entries = read_journal(root, agent)?;
    if let Some(current) = latest(&entries, key) {
        if current.text == text {
            // Identical restatement: no new version, nothing appended.
            return Ok(WriteOutcome {
                entry: current.clone(),
                new_version: false,
            });
        }
    }
    let version = latest(&entries, key).map(|e| e.version).unwrap_or(0) + 1;
    let entry = Entry {
        key: key.to_string(),
        version,
        author: if author.is_empty() {
            "unknown".to_string()
        } else {
            author.to_string()
        },
        ts: ts.unwrap_or_else(now_unix),
        text: text.to_string(),
        extra: Vec::new(),
    };
    append_entry(root, agent, &entry)?;
    Ok(WriteOutcome {
        entry,
        new_version: true,
    })
}

/// Write a memory entry; returns it with a `new_version` flag. A write
/// identical to the key's latest text returns the current entry
/// unchanged with `new_version` false and appends nothing.
pub fn write(
    root: &Path,
    agent: &str,
    key: &str,
    text: &str,
    author: &str,
    ts: Option<i64>,
) -> Result<WriteOutcome, MemoryError> {
    write_inner(root, Some(agent), key, text, author, ts)
}

/// Write a shared crew memory entry (same rules as `write`).
pub fn write_shared(
    root: &Path,
    key: &str,
    text: &str,
    author: &str,
    ts: Option<i64>,
) -> Result<WriteOutcome, MemoryError> {
    write_inner(root, None, key, text, author, ts)
}

fn read_version(
    entries: &[Entry],
    key: &str,
    version: Option<i64>,
) -> Result<Entry, MemoryError> {
    let matches: Vec<&Entry> = entries.iter().filter(|e| e.key == key).collect();
    if matches.is_empty() {
        // Python formats the key with %r (single quotes); keys cannot
        // contain backslash or NUL, so plain single quotes match here.
        return Err(MemoryError(format!("no memory entry for key '{}'", key)));
    }
    match version {
        None => Ok((*matches[matches.len() - 1]).clone()),
        Some(v) => {
            if v < 1 {
                return Err(MemoryError(
                    "version must be a positive integer".to_string(),
                ));
            }
            if v as usize > matches.len() {
                return Err(MemoryError(format!(
                    "key '{}' has {} versions, no v{}",
                    key,
                    matches.len(),
                    v
                )));
            }
            Ok((*matches[(v - 1) as usize]).clone())
        }
    }
}

/// Latest entry for an agent key, or one numbered version. Never guesses:
/// a missing key or a version past the end raises.
pub fn read(
    root: &Path,
    agent: &str,
    key: &str,
    version: Option<i64>,
) -> Result<Entry, MemoryError> {
    validate_agent(agent)?;
    validate_key(key)?;
    let entries = read_journal(root, Some(agent))?;
    read_version(&entries, key, version)
}

/// Latest shared entry for a key, or one numbered version.
pub fn read_shared(
    root: &Path,
    key: &str,
    version: Option<i64>,
) -> Result<Entry, MemoryError> {
    validate_key(key)?;
    let entries = read_journal(root, None)?;
    read_version(&entries, key, version)
}

/// All versions of an agent key, oldest first.
pub fn history(root: &Path, agent: &str, key: &str) -> Result<Vec<Entry>, MemoryError> {
    validate_agent(agent)?;
    validate_key(key)?;
    Ok(read_journal(root, Some(agent))?
        .into_iter()
        .filter(|e| e.key == key)
        .collect())
}

/// All versions of a shared key, oldest first.
pub fn history_shared(root: &Path, key: &str) -> Result<Vec<Entry>, MemoryError> {
    validate_key(key)?;
    Ok(read_journal(root, None)?
        .into_iter()
        .filter(|e| e.key == key)
        .collect())
}

fn latest_map(entries: &[Entry]) -> BTreeMap<String, Entry> {
    let mut out = BTreeMap::new();
    for entry in entries {
        out.insert(entry.key.clone(), entry.clone());
    }
    out
}

/// Latest entries for one agent, keyed by key, sorted by key.
pub fn list_keys(root: &Path, agent: &str) -> Result<BTreeMap<String, Entry>, MemoryError> {
    validate_agent(agent)?;
    Ok(latest_map(&read_journal(root, Some(agent))?))
}

/// Latest shared entries, keyed by key, sorted by key.
pub fn list_shared_keys(root: &Path) -> Result<BTreeMap<String, Entry>, MemoryError> {
    Ok(latest_map(&read_journal(root, None)?))
}

/// An agent's own latest entries plus the shared latest entries, kept
/// under separate keys and never merged.
pub fn read_all(root: &Path, agent: &str) -> Result<ReadAll, MemoryError> {
    validate_agent(agent)?;
    Ok(ReadAll {
        own: list_keys(root, agent)?,
        shared: list_shared_keys(root)?,
    })
}

/// Directories a launcher mounts into a process at start: the agent's
/// memory home and the crew shelf.
pub fn mount_paths(root: &Path, agent: &str) -> Result<MountPaths, MemoryError> {
    validate_agent(agent)?;
    Ok(MountPaths {
        own: namespace_dir(root, Some(agent))?,
        shared: namespace_dir(root, None)?,
    })
}

/// Create the store namespaces if missing; idempotent. Returns the mount
/// base paths.
pub fn ensure_root(root: &Path) -> Result<EnsureRoot, MemoryError> {
    let agents_base = root.join(AGENTS_DIR);
    let shared_base = root.join(SHARED_DIR);
    fs::create_dir_all(&agents_base)?;
    fs::create_dir_all(&shared_base)?;
    Ok(EnsureRoot {
        agents: agents_base,
        shared: shared_base,
    })
}

// ---------------------------------------------------------------------------
// Minimal CLI: port of `memory.py main()`.
// ---------------------------------------------------------------------------

/// The outcome of one CLI invocation: exit code plus captured streams.
/// The Python CLI prints to the real streams and exits; this library form
/// returns the same bytes so tests can assert on them without a binary.
#[derive(Clone, Debug, PartialEq)]
pub struct CliOutcome {
    pub code: i32,
    pub stdout: String,
    pub stderr: String,
}

const CLI_USAGE: &str = "usage: memory ensure|write|write-shared|read|read-shared|list|history ROOT [ARGS]";

fn cli_error(message: &str) -> CliOutcome {
    CliOutcome {
        code: 2,
        stdout: String::new(),
        stderr: format!("MEMORY_ERROR: {}\n", message),
    }
}

fn cli_usage() -> CliOutcome {
    CliOutcome {
        code: 2,
        stdout: String::new(),
        stderr: format!("{}\n", CLI_USAGE),
    }
}

/// Run the memory CLI over argument words (program name excluded).
/// Errors exit 2, mirroring `main()`; the usage line is identical.
pub fn run_cli(argv: &[String]) -> CliOutcome {
    if argv.is_empty() {
        return cli_usage();
    }
    let cmd = argv[0].as_str();
    // Each branch mirrors the Python argument checks, including the
    // `--author` / `--version` flag scans over the trailing words.
    let find_flag = |argv: &[String], from: usize, flag: &str| -> Option<String> {
        if argv[from..].iter().any(|a| a == flag) {
            // Python's `argv.index(flag)` searches the whole list, so a
            // flag word appearing earlier as a value wins; mirror that.
            let pos = argv.iter().position(|a| a == flag)?;
            argv.get(pos + 1).cloned()
        } else {
            None
        }
    };
    match cmd {
        "ensure" if argv.len() == 2 => {
            let root = Path::new(&argv[1]);
            match ensure_root(root) {
                Ok(paths) => CliOutcome {
                    code: 0,
                    stdout: format!(
                        "{{\"agents\": {}, \"shared\": {}}}\n",
                        {
                            let mut s = String::new();
                            write_json_string(&paths.agents.to_string_lossy(), &mut s);
                            s
                        },
                        {
                            let mut s = String::new();
                            write_json_string(&paths.shared.to_string_lossy(), &mut s);
                            s
                        }
                    ),
                    stderr: String::new(),
                },
                Err(err) => cli_error(&err.0),
            }
        }
        "write" if argv.len() >= 5 => {
            let root = Path::new(&argv[1]);
            let author = find_flag(argv, 5, "--author").unwrap_or_default();
            match write(root, &argv[2], &argv[3], &argv[4], &author, None) {
                Ok(outcome) => CliOutcome {
                    code: 0,
                    stdout: format!("{}\n", outcome.entry.to_journal_line()),
                    stderr: String::new(),
                },
                Err(err) => cli_error(&err.0),
            }
        }
        "write-shared" if argv.len() >= 4 => {
            let root = Path::new(&argv[1]);
            let author = find_flag(argv, 4, "--author").unwrap_or_default();
            match write_shared(root, &argv[2], &argv[3], &author, None) {
                Ok(outcome) => CliOutcome {
                    code: 0,
                    stdout: format!("{}\n", outcome.entry.to_journal_line()),
                    stderr: String::new(),
                },
                Err(err) => cli_error(&err.0),
            }
        }
        "read" if argv.len() >= 4 => {
            let version = match find_flag(argv, 4, "--version") {
                Some(text) => match text.trim().parse::<i64>() {
                    Ok(v) => Some(v),
                    Err(_) => {
                        return cli_error(&format!(
                            "invalid literal for int() with base 10: '{}'",
                            text
                        ));
                    }
                },
                None => None,
            };
            match read(Path::new(&argv[1]), &argv[2], &argv[3], version) {
                Ok(entry) => CliOutcome {
                    code: 0,
                    stdout: format!("{}\n", entry.to_journal_line()),
                    stderr: String::new(),
                },
                Err(err) => cli_error(&err.0),
            }
        }
        "read-shared" if argv.len() >= 3 => {
            let version = match find_flag(argv, 3, "--version") {
                Some(text) => match text.trim().parse::<i64>() {
                    Ok(v) => Some(v),
                    Err(_) => {
                        return cli_error(&format!(
                            "invalid literal for int() with base 10: '{}'",
                            text
                        ));
                    }
                },
                None => None,
            };
            match read_shared(Path::new(&argv[1]), &argv[2], version) {
                Ok(entry) => CliOutcome {
                    code: 0,
                    stdout: format!("{}\n", entry.to_journal_line()),
                    stderr: String::new(),
                },
                Err(err) => cli_error(&err.0),
            }
        }
        "list" if argv.len() == 3 => {
            match list_keys(Path::new(&argv[1]), &argv[2]) {
                Ok(entries) => {
                    let mut stdout = String::new();
                    for (_, entry) in &entries {
                        stdout.push_str(&entry.to_journal_line());
                        stdout.push('\n');
                    }
                    CliOutcome {
                        code: 0,
                        stdout,
                        stderr: String::new(),
                    }
                }
                Err(err) => cli_error(&err.0),
            }
        }
        "history" if argv.len() == 4 => {
            match history(Path::new(&argv[1]), &argv[2], &argv[3]) {
                Ok(entries) => {
                    let mut stdout = String::new();
                    for entry in &entries {
                        stdout.push_str(&entry.to_journal_line());
                        stdout.push('\n');
                    }
                    CliOutcome {
                        code: 0,
                        stdout,
                        stderr: String::new(),
                    }
                }
                Err(err) => cli_error(&err.0),
            }
        }
        _ => cli_usage(),
    }
}

// ---------------------------------------------------------------------------
// Brief-time formatting and the memory-depth record: port of the
// `with_memory_depth` / `memory_depth_lines` / `_environment_age_label` /
// `_format_brief_time` slice of `os/intel/brief.py`.
// ---------------------------------------------------------------------------

/// Days from civil date (Howard Hinnant's algorithm), for the
/// timestamp-to-calendar conversion below.
fn days_from_civil(year: i64, month: i64, day: i64) -> i64 {
    let y = if month <= 2 { year - 1 } else { year };
    let era = if y >= 0 { y } else { y - 399 } / 400;
    let yoe = y - era * 400;
    let mp = if month > 2 { month - 3 } else { month + 9 };
    let doy = (153 * mp + 2) / 5 + day - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146097 + doe - 719468
}

/// Civil date from days since the Unix epoch (inverse of above).
fn civil_from_days(z: i64) -> (i64, i64, i64) {
    let z = z + 719468;
    let era = if z >= 0 { z } else { z - 146096 } / 146097;
    let doe = z - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = doy - (153 * mp + 2) / 5 + 1;
    let month = if mp < 10 { mp + 3 } else { mp - 9 };
    (if month <= 2 { y + 1 } else { y }, month, day)
}

/// Weekday of a day count (0 = Sunday). 1970-01-01 was a Thursday.
fn weekday_of_days(days: i64) -> i64 {
    (days + 4).rem_euclid(7)
}

/// The nth Sunday of a month, as a day count since the epoch.
fn nth_sunday(year: i64, month: i64, n: i64) -> i64 {
    let first = days_from_civil(year, month, 1);
    let offset = (7 - weekday_of_days(first)) % 7;
    first + offset + 7 * (n - 1)
}

/// Format a stored brief timestamp as `"YYYY-MM-DD HH:MM ET"` in
/// America/New_York, or `None` for a non-numeric timestamp. Mirrors
/// `_format_brief_time`, including the post-2007 US DST rules (second
/// Sunday of March 07:00 UTC to first Sunday of November 06:00 UTC).
/// `Float` stamps truncate toward zero like Python's `int()`.
pub fn format_brief_time(ts: &Value) -> Option<String> {
    let stamp: i64 = match ts {
        Value::Int(n) => *n,
        Value::Float(f) if f.is_finite() => *f as i64,
        _ => return None,
    };
    let year = civil_from_days(stamp.div_euclid(86400)).0;
    let dst_start = nth_sunday(year, 3, 2) * 86400 + 7 * 3600;
    let dst_end = nth_sunday(year, 11, 1) * 86400 + 6 * 3600;
    let offset = if stamp >= dst_start && stamp < dst_end {
        -4 * 3600
    } else {
        -5 * 3600
    };
    let local = stamp + offset;
    let days = local.div_euclid(86400);
    let secs = local.rem_euclid(86400);
    let (y, m, d) = civil_from_days(days);
    Some(format!(
        "{:04}-{:02}-{:02} {:02}:{:02} ET",
        y,
        m,
        d,
        secs / 3600,
        (secs % 3600) / 60
    ))
}

/// The age label for one environment line: `" (as of YYYY-MM-DD HH:MM ET)"`
/// from a numeric time, or `" (snapshot time not reported)"` otherwise.
/// Mirrors `_environment_age_label`.
pub fn environment_age_label(as_of: Option<&Value>) -> String {
    match as_of.and_then(format_brief_time) {
        Some(formatted) => format!(" (as of {})", formatted),
        None => " (snapshot time not reported)".to_string(),
    }
}

fn non_empty_str(value: Option<&Value>) -> Option<String> {
    match value {
        Some(Value::Str(s)) if !s.is_empty() => Some(s.clone()),
        _ => None,
    }
}

fn map_with(pairs: Vec<(String, Value)>) -> Value {
    Value::Map(pairs)
}

/// The morning-path caller that fills a snapshot's `memory_depth` record
/// from the snapshot's own stated lists. Mirrors `with_memory_depth`:
/// a snapshot that already carries `memory_depth` is returned unchanged;
/// a snapshot that yields nothing usable gets no record added; a
/// `memory_down` snapshot gets a record carrying that flag alone; the
/// caller's snapshot is never mutated; this never raises (there is no
/// raising path in the typed port, matching the guarded Python build).
/// `now` is the stamp in seconds, or the current time when `None`.
pub fn with_memory_depth(snapshot: &Value, now: Option<i64>) -> Value {
    let map = match snapshot {
        Value::Map(members) => members.clone(),
        _ => return map_with(Vec::new()),
    };
    let mut filled = map.clone();
    if filled.iter().any(|(k, _)| k == "memory_depth") {
        return Value::Map(filled);
    }
    let stamp = now.unwrap_or_else(now_unix);
    let mut record: Vec<(String, Value)> = vec![("as_of".to_string(), Value::Int(stamp))];
    let mut added = false;
    let snapshot_map = Value::Map(map);
    if snapshot_map
        .get("memory_down")
        .map(|v| v.is_json_true())
        .unwrap_or(false)
    {
        record.push(("memory_down".to_string(), Value::Bool(true)));
        added = true;
    } else {
        if let Some(Value::List(aged)) = snapshot_map.get("aged_decisions") {
            let mut usable = Vec::new();
            for entry in aged {
                let decision = match entry {
                    Value::Map(_) => non_empty_str(entry.get("decision")),
                    _ => None,
                };
                let Some(decision) = decision else {
                    continue;
                };
                let mut built = vec![("decision".to_string(), Value::Str(decision))];
                if let Some(date) = non_empty_str(entry.get("original_date")) {
                    built.push(("original_date".to_string(), Value::Str(date)));
                }
                usable.push(Value::Map(built));
            }
            if !usable.is_empty() {
                record.push(("aged_decisions".to_string(), Value::List(usable)));
                added = true;
            }
        }
        if let Some(Value::List(due)) = snapshot_map.get("due_commitments") {
            let mut usable = Vec::new();
            for entry in due {
                let commitment = match entry {
                    Value::Map(_) => non_empty_str(entry.get("commitment")),
                    _ => None,
                };
                let Some(commitment) = commitment else {
                    continue;
                };
                let mut built =
                    vec![("commitment".to_string(), Value::Str(commitment))];
                if let Some(date) = non_empty_str(entry.get("due")) {
                    built.push(("due".to_string(), Value::Str(date)));
                }
                usable.push(Value::Map(built));
            }
            if !usable.is_empty() {
                record.push(("due_commitments".to_string(), Value::List(usable)));
                added = true;
            }
        }
        if let Some(Value::List(context)) = snapshot_map.get("fresh_context") {
            let usable: Vec<Value> = context
                .iter()
                .filter_map(|item| non_empty_str(Some(item)).map(Value::Str))
                .collect();
            if !usable.is_empty() {
                record.push(("fresh_context".to_string(), Value::List(usable)));
                added = true;
            }
        }
    }
    if added {
        filled.push(("memory_depth".to_string(), Value::Map(record)));
    }
    Value::Map(filled)
}

/// The long-term-memory lines for a daily brief, in the brief's
/// plain-English standard. Mirrors `memory_depth_lines`: a down service
/// says so in one line and shows no item; a missing date reads
/// "not reported", never guessed; an entry without its text is skipped;
/// a category with no usable entries reads "none reported"; every other
/// line carries its age label from the record's `as_of` time.
pub fn memory_depth_lines(record: &Value) -> Vec<String> {
    let record = match record {
        Value::Map(_) => record,
        _ => &Value::Map(Vec::new()),
    };
    if record.get("memory_down").map(|v| v.is_json_true()).unwrap_or(false) {
        return vec!["Long-term memory: memory service down, so no aged decisions, due commitments, or fresh-agent context are shown"
            .to_string()];
    }
    let age = environment_age_label(record.get("as_of"));
    let mut lines = Vec::new();
    let mut usable_aged = Vec::new();
    if let Some(Value::List(aged)) = record.get("aged_decisions") {
        for entry in aged {
            let decision = match entry {
                Value::Map(_) => non_empty_str(entry.get("decision")),
                _ => None,
            };
            let Some(decision) = decision else {
                continue;
            };
            match non_empty_str(entry.get("original_date")) {
                Some(date) => usable_aged.push(format!("Aged decision: {} (from {})", decision, date)),
                None => usable_aged.push(format!(
                    "Aged decision: {} (original date not reported)",
                    decision
                )),
            }
        }
    }
    if usable_aged.is_empty() {
        lines.push(format!("Aged decisions: none reported{}", age));
    } else {
        for line in usable_aged {
            lines.push(format!("{}{}", line, age));
        }
    }
    let mut usable_due = Vec::new();
    if let Some(Value::List(due)) = record.get("due_commitments") {
        for entry in due {
            let commitment = match entry {
                Value::Map(_) => non_empty_str(entry.get("commitment")),
                _ => None,
            };
            let Some(commitment) = commitment else {
                continue;
            };
            match non_empty_str(entry.get("due")) {
                Some(date) => usable_due.push(format!("Due commitment: {} (due {})", commitment, date)),
                None => usable_due.push(format!(
                    "Due commitment: {} (due date not reported)",
                    commitment
                )),
            }
        }
    }
    if usable_due.is_empty() {
        lines.push(format!("Due commitments: none reported{}", age));
    } else {
        for line in usable_due {
            lines.push(format!("{}{}", line, age));
        }
    }
    let mut usable_context = Vec::new();
    if let Some(Value::List(context)) = record.get("fresh_context") {
        for item in context {
            if let Some(text) = non_empty_str(Some(item)) {
                usable_context.push(text);
            }
        }
    }
    if usable_context.is_empty() {
        lines.push(format!("Fresh-agent context: none reported{}", age));
    } else {
        for item in usable_context {
            lines.push(format!("Fresh-agent context: {}{}", item, age));
        }
    }
    lines
}

// ---------------------------------------------------------------------------
// Tests. Names reference the Python test they mirror; the store tests use
// fresh temporary roots, the bake tests read the folded tree, and the
// depth tests build snapshot values directly.
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    static COUNTER: AtomicUsize = AtomicUsize::new(0);

    fn temp_root() -> PathBuf {
        let n = COUNTER.fetch_add(1, Ordering::SeqCst);
        let dir = std::env::temp_dir()
            .join(format!("metaos-memory-test-{}-{}", std::process::id(), n));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).expect("create temp dir");
        dir
    }

    fn cleanup(dir: &Path) {
        let _ = fs::remove_dir_all(dir);
    }

    fn store_root(dir: &Path) -> PathBuf {
        dir.join("memory")
    }

    // Value builders for the depth tests.
    fn s(text: &str) -> Value {
        Value::Str(text.to_string())
    }

    fn i(n: i64) -> Value {
        Value::Int(n)
    }

    fn b(v: bool) -> Value {
        Value::Bool(v)
    }

    fn list(items: Vec<Value>) -> Value {
        Value::List(items)
    }

    fn map(pairs: Vec<(&str, Value)>) -> Value {
        Value::Map(
            pairs
                .into_iter()
                .map(|(k, v)| (k.to_string(), v))
                .collect(),
        )
    }

    fn snapshot_fixture() -> Value {
        map(vec![
            ("messages", list(vec![])),
            (
                "aged_decisions",
                list(vec![map(vec![
                    ("decision", s("freeze the demo fixture at noon")),
                    ("original_date", s("2026-10-01")),
                ])]),
            ),
            (
                "due_commitments",
                list(vec![map(vec![
                    ("commitment", s("ship the demo cut")),
                    ("due", s("2026-11-03")),
                ])]),
            ),
            (
                "fresh_context",
                list(vec![s(
                    "the demo room is build only, never a posting room",
                )]),
            ),
        ])
    }

    // -- Store tests: test_os078_memory.py, MemoryStoreTest -------------

    #[test]
    fn test_os078_write_and_read_round_trip() {
        let dir = temp_root();
        let root = store_root(&dir);
        let record = write(
            &root,
            "pax",
            "decisions/router.md",
            "Router is the queue, not the chat.",
            "pax",
            Some(1000),
        )
        .expect("write");
        assert_eq!(record.entry.version, 1);
        assert!(record.new_version);
        assert_eq!(record.entry.author, "pax");
        assert_eq!(record.entry.ts, 1000);
        let back = read(&root, "pax", "decisions/router.md", None).expect("read");
        assert_eq!(back.text, "Router is the queue, not the chat.");
        assert_eq!(back.version, 1);
        cleanup(&dir);
    }

    #[test]
    fn test_os078_versions_increment_and_versioned_read() {
        let dir = temp_root();
        let root = store_root(&dir);
        write(&root, "pax", "note.txt", "one", "", Some(1)).unwrap();
        write(&root, "pax", "note.txt", "two", "", Some(2)).unwrap();
        let record = write(&root, "pax", "note.txt", "three", "", Some(3)).unwrap();
        assert_eq!(record.entry.version, 3);
        assert_eq!(read(&root, "pax", "note.txt", Some(1)).unwrap().text, "one");
        assert_eq!(read(&root, "pax", "note.txt", Some(2)).unwrap().text, "two");
        assert_eq!(read(&root, "pax", "note.txt", None).unwrap().text, "three");
        let hist = history(&root, "pax", "note.txt").unwrap();
        assert_eq!(
            hist.iter().map(|e| e.version).collect::<Vec<_>>(),
            vec![1, 2, 3]
        );
        assert_eq!(
            hist.iter().map(|e| e.text.as_str()).collect::<Vec<_>>(),
            vec!["one", "two", "three"]
        );
        cleanup(&dir);
    }

    #[test]
    fn test_os078_identical_rewrite_is_a_noop() {
        let dir = temp_root();
        let root = store_root(&dir);
        write(&root, "milo", "k.md", "same", "", Some(1)).unwrap();
        let journal = root.join("agents").join("milo").join("journal.jsonl");
        let before = fs::read_to_string(&journal).unwrap();
        let record = write(&root, "milo", "k.md", "same", "", Some(2)).unwrap();
        assert_eq!(record.entry.version, 1);
        assert!(!record.new_version);
        let after = fs::read_to_string(&journal).unwrap();
        assert_eq!(before, after);
        cleanup(&dir);
    }

    #[test]
    fn test_os078_shared_namespace_versions_independently() {
        let dir = temp_root();
        let root = store_root(&dir);
        write(&root, "pax", "settled.md", "agent view", "", Some(1)).unwrap();
        write_shared(&root, "settled.md", "crew view", "", Some(2)).unwrap();
        write_shared(&root, "settled.md", "crew view v2", "", Some(3)).unwrap();
        assert_eq!(
            read(&root, "pax", "settled.md", None).unwrap().text,
            "agent view"
        );
        assert_eq!(
            read_shared(&root, "settled.md", None).unwrap().text,
            "crew view v2"
        );
        assert_eq!(
            read_shared(&root, "settled.md", Some(1)).unwrap().text,
            "crew view"
        );
        let all = read_all(&root, "pax").unwrap();
        assert_eq!(all.own["settled.md"].text, "agent view");
        assert_eq!(all.shared["settled.md"].text, "crew view v2");
        cleanup(&dir);
    }

    #[test]
    fn test_os078_shared_identical_rewrite_is_a_noop() {
        let dir = temp_root();
        let root = store_root(&dir);
        write_shared(&root, "s.md", "once", "", Some(1)).unwrap();
        let record = write_shared(&root, "s.md", "once", "", Some(2)).unwrap();
        assert_eq!(record.entry.version, 1);
        assert!(!record.new_version);
        assert_eq!(history_shared(&root, "s.md").unwrap().len(), 1);
        cleanup(&dir);
    }

    #[test]
    fn test_os078_key_validation_refuses_escape() {
        let dir = temp_root();
        let root = store_root(&dir);
        for bad in [
            "../escape",
            "/absolute",
            "a//b",
            "a/./b",
            "a/../b",
            "a\\b",
            "a\0b",
            "",
        ] {
            assert!(
                write(&root, "pax", bad, "x", "", None).is_err(),
                "agent write accepted bad key {:?}",
                bad
            );
            assert!(
                write_shared(&root, bad, "x", "", None).is_err(),
                "shared write accepted bad key {:?}",
                bad
            );
        }
        cleanup(&dir);
    }

    #[test]
    fn test_os078_agent_validation_refuses_slash() {
        let dir = temp_root();
        let root = store_root(&dir);
        for bad in ["a/b", ".", "..", "", "a\\b"] {
            assert!(
                write(&root, bad, "k.md", "x", "", None).is_err(),
                "accepted bad agent {:?}",
                bad
            );
        }
        cleanup(&dir);
    }

    #[test]
    fn test_os078_missing_key_and_bad_version_raise_never_guess() {
        let dir = temp_root();
        let root = store_root(&dir);
        assert!(read(&root, "pax", "nope.md", None).is_err());
        assert!(read_shared(&root, "nope.md", None).is_err());
        write(&root, "pax", "k.md", "v1", "", Some(1)).unwrap();
        assert!(read(&root, "pax", "k.md", Some(2)).is_err());
        assert!(read(&root, "pax", "k.md", Some(0)).is_err());
        cleanup(&dir);
    }

    #[test]
    fn test_os078_corrupt_journal_line_raises() {
        let dir = temp_root();
        let root = store_root(&dir);
        write(&root, "pax", "k.md", "good", "", Some(1)).unwrap();
        let journal = root.join("agents").join("pax").join("journal.jsonl");
        {
            use std::io::Write as _;
            let mut handle = fs::OpenOptions::new()
                .append(true)
                .open(&journal)
                .unwrap();
            writeln!(handle, "this is not json").unwrap();
        }
        assert!(read(&root, "pax", "k.md", None).is_err());
        {
            use std::io::Write as _;
            let mut handle = fs::OpenOptions::new()
                .append(true)
                .open(&journal)
                .unwrap();
            // A line with the wrong shape (missing fields) also raises.
            writeln!(handle, "{{\"key\": \"k.md\"}}").unwrap();
        }
        assert!(read(&root, "pax", "k.md", None).is_err());
        cleanup(&dir);
    }

    #[test]
    fn test_os078_wrong_shaped_entry_text_raises() {
        // Runtime form of the Python non-string-text refusal: a journal
        // line whose text is not a string fails the shape check on read.
        let dir = temp_root();
        let root = store_root(&dir);
        let journal_dir = root.join("agents").join("pax");
        fs::create_dir_all(&journal_dir).unwrap();
        fs::write(
            journal_dir.join("journal.jsonl"),
            "{\"key\": \"k.md\", \"version\": 1, \"author\": \"pax\", \"ts\": 1, \"text\": 42}\n",
        )
        .unwrap();
        assert!(read(&root, "pax", "k.md", None).is_err());
        cleanup(&dir);
    }

    #[test]
    fn test_os078_list_keys_sorted_and_shared_separate() {
        let dir = temp_root();
        let root = store_root(&dir);
        write(&root, "hana", "b.md", "b", "", Some(1)).unwrap();
        write(&root, "hana", "a.md", "a", "", Some(2)).unwrap();
        write_shared(&root, "z.md", "z", "", Some(3)).unwrap();
        let own = list_keys(&root, "hana").unwrap();
        let keys: Vec<&str> = own.keys().map(|k| k.as_str()).collect();
        assert_eq!(keys, vec!["a.md", "b.md"]);
        let shared = list_shared_keys(&root).unwrap();
        let shared_keys: Vec<&str> = shared.keys().map(|k| k.as_str()).collect();
        assert_eq!(shared_keys, vec!["z.md"]);
        assert!(!own.contains_key("z.md"));
        cleanup(&dir);
    }

    #[test]
    fn test_os078_mount_paths_name_own_and_shared() {
        let dir = temp_root();
        let root = store_root(&dir);
        let paths = mount_paths(&root, "rowan").unwrap();
        assert_eq!(paths.own, root.join("agents").join("rowan"));
        assert_eq!(paths.shared, root.join("shared"));
        cleanup(&dir);
    }

    #[test]
    fn test_os078_ensure_root_creates_namespaces_idempotently() {
        let dir = temp_root();
        let root = store_root(&dir);
        let first = ensure_root(&root).unwrap();
        assert!(first.agents.is_dir());
        assert!(first.shared.is_dir());
        let second = ensure_root(&root).unwrap();
        assert_eq!(first, second);
        cleanup(&dir);
    }

    // -- CLI tests: the in-process form of the Python subprocess test --

    fn cli(args: &[&str]) -> CliOutcome {
        let owned: Vec<String> = args.iter().map(|a| a.to_string()).collect();
        run_cli(&owned)
    }

    #[test]
    fn test_os078_cli_read_back_and_ensure_and_escape() {
        // Mirrors test_restart_read_back_via_cli_subprocess, with run_cli
        // standing in for the subprocess (same codes, same outputs).
        let dir = temp_root();
        let root = store_root(&dir);
        let root_str = root.to_string_lossy().to_string();
        write(&root, "pax", "decisions/x.md", "kept", "", Some(42)).unwrap();
        let out = cli(&["read", &root_str, "pax", "decisions/x.md"]);
        assert_eq!(out.code, 0, "stderr: {}", out.stderr);
        let value = parse_json(out.stdout.trim()).expect("read output parses");
        assert_eq!(value.get("text").and_then(|v| v.as_str()), Some("kept"));
        let out = cli(&["ensure", &root_str]);
        assert_eq!(out.code, 0, "stderr: {}", out.stderr);
        let out = cli(&["read", &root_str, "pax", "../escape.md"]);
        assert_eq!(out.code, 2);
        assert!(out.stderr.contains("MEMORY_ERROR"));
        cleanup(&dir);
    }

    #[test]
    fn test_os078_cli_write_list_history_and_shared() {
        let dir = temp_root();
        let root = store_root(&dir);
        let root_str = root.to_string_lossy().to_string();
        let out = cli(&["write", &root_str, "pax", "a.md", "hello"]);
        assert_eq!(out.code, 0, "stderr: {}", out.stderr);
        let out = cli(&["write-shared", &root_str, "s.md", "crew"]);
        assert_eq!(out.code, 0, "stderr: {}", out.stderr);
        let out = cli(&["list", &root_str, "pax"]);
        assert_eq!(out.code, 0);
        assert!(out.stdout.contains("\"a.md\""));
        let out = cli(&["history", &root_str, "pax", "a.md"]);
        assert_eq!(out.code, 0);
        assert!(out.stdout.contains("hello"));
        let out = cli(&["read-shared", &root_str, "s.md"]);
        assert_eq!(out.code, 0);
        assert!(out.stdout.contains("crew"));
        let out = cli(&["bogus", &root_str]);
        assert_eq!(out.code, 2);
        assert!(out.stdout.is_empty());
        let out = cli(&[]);
        assert_eq!(out.code, 2);
        assert!(out.stderr.contains("usage: memory"));
        cleanup(&dir);
    }

    #[test]
    fn test_os078_cli_write_author_and_version_flags() {
        let dir = temp_root();
        let root = store_root(&dir);
        let root_str = root.to_string_lossy().to_string();
        let out = cli(&[
            "write",
            &root_str,
            "pax",
            "k.md",
            "v1",
            "--author",
            "milo",
        ]);
        assert_eq!(out.code, 0, "stderr: {}", out.stderr);
        assert!(out.stdout.contains("\"milo\""));
        let out = cli(&["write", &root_str, "pax", "k.md", "v2"]);
        assert_eq!(out.code, 0);
        let out = cli(&["read", &root_str, "pax", "k.md", "--version", "1"]);
        assert_eq!(out.code, 0);
        assert!(out.stdout.contains("v1"));
        let out = cli(&["read", &root_str, "pax", "k.md", "--version", "nine"]);
        assert_eq!(out.code, 2);
        assert!(out.stderr.contains("MEMORY_ERROR"));
        cleanup(&dir);
    }

    // -- Bake tests: test_os078_memory.py, MemoryBakeTest -------------
    //
    // These pin the folded tree's image-bake files, exactly like the
    // Python tests pin the old tree's files. The repo root is two levels
    // above this crate's manifest directory.

    fn repo_root() -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("..")
    }

    fn os_fold() -> PathBuf {
        repo_root().join("os")
    }

    fn read_file(path: &Path) -> String {
        fs::read_to_string(path).unwrap_or_else(|_| panic!("read {:?}", path))
    }

    fn enablement_loop(text: &str) -> String {
        for line in text.lines() {
            if line.contains("for u in") {
                return line.to_string();
            }
        }
        String::new()
    }

    fn section(text: &str, start_marker: &str, end_marker: &str) -> String {
        let start = match text.find(start_marker) {
            Some(i) => i,
            None => return String::new(),
        };
        let end = text[start + start_marker.len()..]
            .find(end_marker)
            .map(|i| start + start_marker.len() + i)
            .unwrap_or(text.len());
        text[start..end].to_string()
    }

    #[test]
    fn test_os078_bake_unit_shape() {
        let text = read_file(&os_fold().join("os/services/relay-memory.service"));
        assert!(text.contains("WantedBy=relay.target"));
        assert!(text.contains("Type=oneshot"));
        assert!(text.contains("RemainAfterExit=yes"));
        assert!(text.contains("User=relay"));
        assert!(text.contains(
            "ExecStart=/usr/bin/python3 /opt/relay/mos/memory.py ensure /var/lib/metaos/memory"
        ));
        assert!(text.contains("PartOf=relay.target"));
    }

    #[test]
    fn test_os078_bake_target_wants_unit() {
        let text = read_file(&os_fold().join("os/services/relay.target"));
        assert!(text.contains("relay-memory.service"));
    }

    #[test]
    fn test_os078_bake_build_image_bakes_root_and_enables_unit() {
        let text = read_file(&os_fold().join("os/build-image.sh"));
        assert!(text.contains("mkdir -p \"$ROOTFS/var/lib/metaos/memory\""));
        assert!(text.contains(".metaos-memory-store"));
        assert!(text.contains(
            "chroot \"$ROOTFS\" chown relay:relay /var/lib/metaos/memory"
        ));
        assert!(enablement_loop(&text).contains("relay-memory.service"));
    }

    #[test]
    fn test_os078_bake_build_live_stages_root() {
        let text = read_file(&os_fold().join("os/build-live.sh"));
        assert!(text.contains("mkdir -p \"$STAGE/var/lib/metaos/memory\""));
        assert!(text.contains(".metaos-memory-store"));
    }

    #[test]
    fn test_os078_bake_hook_enables_unit_and_chowns_root() {
        let text = read_file(
            &os_fold()
                .join("os/live-build/config/hooks/live/0900-metaos-services.hook.chroot"),
        );
        assert!(enablement_loop(&text).contains("relay-memory.service"));
        assert!(text.contains("mkdir -p /var/lib/metaos/memory"));
        assert!(text.contains("chown relay:relay /var/lib/metaos/memory"));
    }

    #[test]
    fn test_os078_bake_packer_bakes_root_and_enables_unit() {
        let text = read_file(&os_fold().join("os/packer/metaos.pkr.hcl"));
        assert!(text.contains("mkdir -p /var/lib/metaos/memory"));
        assert!(text.contains(".metaos-memory-store"));
        assert!(text.contains("chown -R relay:relay /var/lib/metaos/memory"));
        assert!(enablement_loop(&text).contains("relay-memory.service"));
    }

    #[test]
    fn test_os078_bake_docs_record_first_light_without_em_dash() {
        let readme = read_file(&os_fold().join("os/README.md"));
        assert!(readme.contains("Memory service (OS-078, first light)"));
        let sec = section(
            &readme,
            "## Memory service (OS-078, first light)",
            "## Two routes, stated plainly",
        );
        assert!(!sec.contains('\u{2014}'));
        let spec = read_file(&repo_root().join("os/plan/META_OS.md"));
        assert!(spec.contains("Memory service (OS-078, Pax, first light)"));
        let note = section(
            &spec,
            "**Memory service (OS-078, Pax, first light):**",
            "### 2. Identity and capabilities",
        );
        assert!(!note.contains('\u{2014}'));
    }

    #[test]
    fn test_os078_bake_build_scripts_bash_syntax_clean() {
        for path in [
            os_fold().join("os/build-image.sh"),
            os_fold().join("os/build-live.sh"),
        ] {
            let status = std::process::Command::new("bash")
                .arg("-n")
                .arg(&path)
                .status()
                .expect("run bash -n");
            assert!(status.success(), "bash -n failed for {:?}", path);
        }
        let hook = os_fold()
            .join("os/live-build/config/hooks/live/0900-metaos-services.hook.chroot");
        let status = std::process::Command::new("sh")
            .arg("-n")
            .arg(&hook)
            .status()
            .expect("run sh -n");
        assert!(status.success(), "sh -n failed for hook");
    }

    #[test]
    fn test_os078_bake_memory_root_sweeps_clean_and_secret_value_flagged() {
        let dir = temp_root();
        let mem = dir
            .join("var")
            .join("lib")
            .join("metaos")
            .join("memory");
        fs::create_dir_all(&mem).unwrap();
        fs::write(
            mem.join(".metaos-memory-store"),
            "memory-store-root /var/lib/metaos/memory\n",
        )
        .unwrap();
        let sweep = os_fold().join("os/bin/metaos-secrets-sweep");
        let clean = std::process::Command::new("sh")
            .arg(&sweep)
            .arg(&dir)
            .output()
            .expect("run sweep");
        assert!(clean.status.success(), "clean sweep failed");
        let journal_dir = mem.join("agents").join("pax");
        fs::create_dir_all(&journal_dir).unwrap();
        fs::write(
            journal_dir.join("journal.jsonl"),
            "{\"key\": \"k.md\", \"version\": 1, \"author\": \"pax\", \"ts\": 1, \"text\": \"UPSTASH_TOKEN=deadbeef0123456789abcdef\"}\n",
        )
        .unwrap();
        let dirty = std::process::Command::new("sh")
            .arg(&sweep)
            .arg(&dir)
            .output()
            .expect("run sweep");
        assert!(!dirty.status.success(), "dirty sweep passed");
        let stdout = String::from_utf8_lossy(&dirty.stdout);
        assert!(stdout.contains("FINDING"));
        cleanup(&dir);
    }

    // -- Depth tests: test_intel_brief_memory_depth_caller.py ----------

    #[test]
    fn test_depth_fills_all_three_categories_with_one_stamp() {
        let filled = with_memory_depth(&snapshot_fixture(), Some(1793093400));
        let record = filled.get("memory_depth").expect("record");
        assert_eq!(record.get("as_of"), Some(&i(1793093400)));
        assert_eq!(
            record.get("aged_decisions"),
            Some(&list(vec![map(vec![
                ("decision", s("freeze the demo fixture at noon")),
                ("original_date", s("2026-10-01")),
            ])]))
        );
        assert_eq!(
            record.get("due_commitments"),
            Some(&list(vec![map(vec![
                ("commitment", s("ship the demo cut")),
                ("due", s("2026-11-03")),
            ])]))
        );
        assert_eq!(
            record.get("fresh_context"),
            Some(&list(vec![s(
                "the demo room is build only, never a posting room"
            )]))
        );
    }

    #[test]
    fn test_depth_filled_record_renders_memory_depth_lines() {
        let filled = with_memory_depth(&snapshot_fixture(), Some(1793093400));
        let record = filled.get("memory_depth").expect("record");
        let lines = memory_depth_lines(record);
        assert!(lines[0].contains(
            "Aged decision: freeze the demo fixture at noon (from 2026-10-01)"
        ));
        assert!(lines[1].contains("Due commitment: ship the demo cut (due 2026-11-03)"));
        assert!(lines[2].contains(
            "Fresh-agent context: the demo room is build only, never a posting room"
        ));
    }

    #[test]
    fn test_depth_hand_stated_record_wins_unchanged() {
        let stated = map(vec![
            (
                "aged_decisions",
                list(vec![map(vec![
                    ("decision", s("Hand-stated decision")),
                    ("original_date", s("2026-09-01")),
                ])]),
            ),
            ("as_of", i(1793093400)),
        ]);
        let snapshot = map(vec![
            ("memory_depth", stated.clone()),
            (
                "aged_decisions",
                list(vec![map(vec![
                    ("decision", s("stated list decision")),
                    ("original_date", s("2026-10-01")),
                ])]),
            ),
        ]);
        let filled = with_memory_depth(&snapshot, Some(1793093400));
        assert_eq!(filled.get("memory_depth"), Some(&stated));
    }

    #[test]
    fn test_depth_caller_snapshot_is_never_mutated() {
        let snapshot = snapshot_fixture();
        let original = snapshot.clone();
        let filled = with_memory_depth(&snapshot, Some(1793093400));
        assert_eq!(snapshot, original);
        assert!(snapshot.get("memory_depth").is_none());
        assert!(filled.get("memory_depth").is_some());
    }

    #[test]
    fn test_depth_snapshot_with_nothing_usable_gets_no_record() {
        let filled = with_memory_depth(
            &map(vec![("messages", list(vec![]))]),
            Some(1793093400),
        );
        assert!(filled.get("memory_depth").is_none());
        if let Value::Map(members) = &filled {
            let keys: Vec<&str> =
                members.iter().map(|(k, _)| k.as_str()).collect();
            assert_eq!(keys, vec!["messages"]);
        } else {
            panic!("filled is not a map");
        }
    }

    #[test]
    fn test_depth_malformed_entries_skipped_never_guessed() {
        let snapshot = map(vec![
            (
                "aged_decisions",
                list(vec![
                    map(vec![("decision", s(""))]),
                    map(vec![("original_date", s("2026-10-01"))]),
                    s("not a dict"),
                    i(42),
                    map(vec![
                        ("decision", s("dateless decision")),
                        ("original_date", s("")),
                    ]),
                    map(vec![
                        ("decision", s("dated decision")),
                        ("original_date", i(20261001)),
                    ]),
                ]),
            ),
            (
                "due_commitments",
                list(vec![
                    map(vec![("commitment", s(""))]),
                    map(vec![("due", s("2026-11-03"))]),
                    map(vec![
                        ("commitment", s("dateless commitment")),
                        ("due", s("")),
                    ]),
                    map(vec![
                        ("commitment", s("dated commitment")),
                        ("due", i(20261103)),
                    ]),
                ]),
            ),
            (
                "fresh_context",
                list(vec![s("real context"), s(""), i(42), Value::Null]),
            ),
        ]);
        let filled = with_memory_depth(&snapshot, Some(1793093400));
        let record = filled.get("memory_depth").expect("record");
        assert_eq!(
            record.get("aged_decisions"),
            Some(&list(vec![
                map(vec![("decision", s("dateless decision"))]),
                map(vec![("decision", s("dated decision"))]),
            ]))
        );
        assert_eq!(
            record.get("due_commitments"),
            Some(&list(vec![
                map(vec![("commitment", s("dateless commitment"))]),
                map(vec![("commitment", s("dated commitment"))]),
            ]))
        );
        assert_eq!(
            record.get("fresh_context"),
            Some(&list(vec![s("real context")]))
        );
        let lines = memory_depth_lines(record);
        assert!(lines[0].contains(
            "Aged decision: dateless decision (original date not reported)"
        ));
        assert!(lines[1].contains(
            "Aged decision: dated decision (original date not reported)"
        ));
        assert!(lines[2].contains(
            "Due commitment: dateless commitment (due date not reported)"
        ));
        assert!(lines[3].contains(
            "Due commitment: dated commitment (due date not reported)"
        ));
    }

    #[test]
    fn test_depth_memory_down_record_carries_no_item_beside_it() {
        let snapshot = map(vec![
            ("memory_down", b(true)),
            (
                "aged_decisions",
                list(vec![map(vec![
                    ("decision", s("should not show")),
                    ("original_date", s("2026-10-01")),
                ])]),
            ),
            ("fresh_context", list(vec![s("should not show")])),
        ]);
        let filled = with_memory_depth(&snapshot, Some(1793093400));
        assert_eq!(
            filled.get("memory_depth"),
            Some(&map(vec![
                ("as_of", i(1793093400)),
                ("memory_down", b(true)),
            ]))
        );
        assert_eq!(
            memory_depth_lines(filled.get("memory_depth").unwrap()),
            vec!["Long-term memory: memory service down, so no aged decisions, due commitments, or fresh-agent context are shown"
                .to_string()]
        );
    }

    #[test]
    fn test_depth_single_category_record_reads_other_categories_none_reported() {
        let snapshot = map(vec![(
            "aged_decisions",
            list(vec![map(vec![
                ("decision", s("freeze the demo fixture")),
                ("original_date", s("2026-10-01")),
            ])]),
        )]);
        let filled = with_memory_depth(&snapshot, Some(1793093400));
        let lines = memory_depth_lines(filled.get("memory_depth").unwrap());
        assert!(lines[0]
            .contains("Aged decision: freeze the demo fixture (from 2026-10-01)"));
        assert!(lines[1].contains("Due commitments: none reported"));
        assert!(lines[2].contains("Fresh-agent context: none reported"));
    }

    #[test]
    fn test_depth_default_stamp_is_an_int_when_now_is_not_given() {
        let filled = with_memory_depth(&snapshot_fixture(), None);
        assert!(matches!(
            filled.get("memory_depth").and_then(|r| r.get("as_of")),
            Some(Value::Int(_))
        ));
    }

    #[test]
    fn test_depth_non_dict_snapshot_gets_no_record() {
        assert_eq!(with_memory_depth(&Value::Null, None), Value::Map(vec![]));
        assert_eq!(
            with_memory_depth(&s("not a snapshot"), None),
            Value::Map(vec![])
        );
    }

    // -- Brief-time tests: `_format_brief_time` pins -------------------

    #[test]
    fn test_format_brief_time_known_values() {
        assert_eq!(
            format_brief_time(&i(1793093400)).as_deref(),
            Some("2026-10-27 05:30 ET")
        );
        assert_eq!(
            format_brief_time(&i(0)).as_deref(),
            Some("1969-12-31 19:00 ET")
        );
        assert_eq!(
            format_brief_time(&i(1767225600)).as_deref(),
            Some("2025-12-31 19:00 ET")
        );
        assert_eq!(
            format_brief_time(&i(1790000000)).as_deref(),
            Some("2026-09-21 10:13 ET")
        );
        assert_eq!(format_brief_time(&s("2026-10-27")), None);
        assert_eq!(format_brief_time(&b(true)), None);
        assert_eq!(
            environment_age_label(None),
            " (snapshot time not reported)"
        );
        assert_eq!(
            environment_age_label(Some(&i(1793093400))),
            " (as of 2026-10-27 05:30 ET)"
        );
    }

    #[test]
    fn test_format_brief_time_dst_boundaries() {
        // Spring forward 2026: 01:59 EST, then 03:00 EDT (02:00 never is).
        assert_eq!(
            format_brief_time(&i(1772953140)).as_deref(),
            Some("2026-03-08 01:59 ET")
        );
        assert_eq!(
            format_brief_time(&i(1772953200)).as_deref(),
            Some("2026-03-08 03:00 ET")
        );
        // Fall back 2026: 01:59 EDT, then 01:00 EST.
        assert_eq!(
            format_brief_time(&i(1793512740)).as_deref(),
            Some("2026-11-01 01:59 ET")
        );
        assert_eq!(
            format_brief_time(&i(1793512800)).as_deref(),
            Some("2026-11-01 01:00 ET")
        );
    }
}
