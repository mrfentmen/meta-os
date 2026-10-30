//! HTTP server layer for the Meta Nuntius relay.
//!
//! Ports the `createRelayServer` request handling from
//! `relay/relay.mjs`: routes, validation refusals (400 JSON errors),
//! watermark polling, health, and the per-request viewer read. Served
//! over std-only TCP (`serve`), one thread per connection.
//!
//! Ported oddities, noted:
//! - A malformed `%` escape (or non-UTF-8 bytes) in the room segment
//!   makes the original's `decodeURIComponent` throw, which its
//!   catch-all turns into a 500. This port returns 500 for those too
//!   (same shape, Rust-side message text).
//! - The oversized-body cap applies to POST bodies only: like the
//!   original (which only reads bodies on POST routes), GET requests
//!   never have their bodies read.
//! - `since` uses JS `Number.parseInt` semantics (leading-digit
//!   prefix parses, e.g. `"3abc"` reads as 3).

use std::collections::HashMap;
use std::fs;
use std::io::{BufRead, BufReader, Read};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::thread;

use crate::json::escape;
use crate::notify::{message_line, notify_id, notify_line};
use crate::store::RoomStore;
use crate::validation::{
    is_single_line, valid_room, valid_severity, MAX_BODY_BYTES, MAX_NICK_CHARS,
    MAX_TEXT_CHARS, MAX_TOPIC_CHARS,
};

// ---------------------------------------------------------------------------
// Small wire helpers
// ---------------------------------------------------------------------------

/// `decodeURIComponent` for room path segments (`%XX` + UTF-8).
/// `Err` when the original would throw (bad escape or non-UTF-8
/// bytes) — the caller maps that to a 500, like the original's
/// catch-all.
pub fn percent_decode(input: &str) -> Result<String, ()> {
    fn hex(byte: u8) -> Option<u8> {
        (byte as char).to_digit(16).map(|d| d as u8)
    }
    let bytes = input.as_bytes();
    let mut out: Vec<u8> = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'%' {
            // Need two hex digits after '%'; anything else is what
            // makes the original's decodeURIComponent throw.
            if i + 2 >= bytes.len() {
                return Err(());
            }
            match (hex(bytes[i + 1]), hex(bytes[i + 2])) {
                (Some(h), Some(l)) => {
                    out.push(h * 16 + l);
                    i += 3;
                    continue;
                }
                _ => return Err(()),
            }
        }
        out.push(bytes[i]);
        i += 1;
    }
    String::from_utf8(out).map_err(|_| ())
}

/// JS `Number.parseInt(raw, 10)` semantics for the `since` query param:
/// leading whitespace, optional sign, then ASCII digits; no digits
/// (or empty input) means NaN. Returns `None` for NaN.
fn js_parse_int(raw: &str) -> Option<i64> {
    let s = raw.trim_start_matches([' ', '\t', '\n', '\r', '\u{0C}', '\u{0B}']);
    let (s, neg) = match s.strip_prefix('-') {
        Some(rest) => (rest, true),
        None => (s.strip_prefix('+').unwrap_or(s), false),
    };
    let digits: String = s.chars().take_while(|c| c.is_ascii_digit()).collect();
    if digits.is_empty() {
        return None;
    }
    // Values here are tiny room indexes; saturate on overflow.
    let mut value: i64 = 0;
    for ch in digits.chars() {
        value = value
            .saturating_mul(10)
            .saturating_add((ch as u8 - b'0') as i64);
    }
    Some(if neg { -value } else { value })
}

/// Port of the `since` handling in `GET /rooms/<room>/messages`:
/// missing `since` (or NaN, or `< -1`) returns the whole room (`-1`).
pub fn parse_since(raw: Option<&str>) -> i64 {
    match raw {
        None => -1,
        Some(v) => match js_parse_int(v) {
            Some(n) if n >= -1 => n,
            _ => -1,
        },
    }
}

fn split_since(target: &str) -> Option<String> {
    let (_, query) = target.split_once('?')?;
    query.split('&').find_map(|pair| {
        let (k, v) = match pair.split_once('=') {
            Some((k, v)) => (k, v),
            None => (pair, ""),
        };
        if k == "since" {
            Some(v.to_string())
        } else {
            None
        }
    })
}

// ---------------------------------------------------------------------------
// Request-body JSON (POST {nick,text} / {severity,topic,text})
// ---------------------------------------------------------------------------

/// Parsed POST body: the string-valued fields. A field that is missing
/// or non-string is simply absent — both refuse with the same field
/// validation message upstream, exactly like the original's
/// `isSingleLine(undefined)` path.
#[derive(Debug, Default)]
struct BodyFields {
    fields: HashMap<String, String>,
}

impl BodyFields {
    fn get(&self, key: &str) -> Option<&str> {
        self.fields.get(key).map(String::as_str)
    }
}

/// Parse a POST body into its string fields.
/// `Err(true)` = body is not valid JSON (400 "not valid JSON");
/// the oversized-body refusal is checked before this is called.
fn parse_body(body: &[u8]) -> Result<BodyFields, bool> {
    let text = std::str::from_utf8(body).map_err(|_| true)?;
    parse_object_strings(text).ok_or(true)
}

/// Minimal JSON object parser: returns the string-valued fields,
/// skipping non-string values; `None` when the text is not a JSON
/// object at all (malformed shape, trailing garbage, ...).
fn parse_object_strings(text: &str) -> Option<BodyFields> {
    let bytes = text.as_bytes();
    let mut pos = 0;
    let mut fields = BodyFields::default();

    fn skip_ws(bytes: &[u8], pos: &mut usize) {
        while *pos < bytes.len() && matches!(bytes[*pos], b' ' | b'\t' | b'\n' | b'\r') {
            *pos += 1;
        }
    }
    fn parse_string(bytes: &[u8], pos: &mut usize) -> Option<String> {
        if bytes.get(*pos) != Some(&b'"') {
            return None;
        }
        *pos += 1;
        let mut out = String::new();
        loop {
            let c = *bytes.get(*pos)?;
            *pos += 1;
            match c {
                b'"' => return Some(out),
                b'\\' => {
                    let e = *bytes.get(*pos)?;
                    *pos += 1;
                    match e {
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        b'/' => out.push('/'),
                        b'b' => out.push('\u{08}'),
                        b'f' => out.push('\u{0C}'),
                        b'n' => out.push('\n'),
                        b'r' => out.push('\r'),
                        b't' => out.push('\t'),
                        b'u' => {
                            if *pos + 4 > bytes.len() {
                                return None;
                            }
                            let hex: String = bytes[*pos..*pos + 4]
                                .iter()
                                .map(|b| *b as char)
                                .collect();
                            let hi = u32::from_str_radix(&hex, 16).ok()?;
                            *pos += 4;
                            if (0xD800..0xDC00).contains(&hi) {
                                if bytes.get(*pos..*pos + 2) != Some(&[b'\\', b'u']) {
                                    return None;
                                }
                                *pos += 2;
                                if *pos + 4 > bytes.len() {
                                    return None;
                                }
                                let hex2: String = bytes[*pos..*pos + 4]
                                    .iter()
                                    .map(|b| *b as char)
                                    .collect();
                                let lo = u32::from_str_radix(&hex2, 16).ok()?;
                                *pos += 4;
                                if !(0xDC00..0xE000).contains(&lo) {
                                    return None;
                                }
                                let cp = 0x10000 + ((hi - 0xD800) << 10) + (lo - 0xDC00);
                                out.push(char::from_u32(cp)?);
                            } else if (0xDC00..0xE000).contains(&hi) {
                                return None;
                            } else {
                                out.push(char::from_u32(hi)?);
                            }
                        }
                        _ => return None,
                    }
                }
                0x00..=0x1F => return None,
                _ => {
                    // Decode one UTF-8 char starting at this byte.
                    let rest = std::str::from_utf8(&bytes[*pos - 1..]).ok()?;
                    let ch = rest.chars().next()?;
                    out.push(ch);
                    *pos += ch.len_utf8() - 1;
                }
            }
        }
    }
    // Skip any JSON value (for non-string fields).
    fn skip_value(bytes: &[u8], pos: &mut usize) -> Option<()> {
        skip_ws(bytes, pos);
        match *bytes.get(*pos)? {
            b'"' => {
                parse_string(bytes, pos)?;
            }
            b'{' => {
                *pos += 1;
                skip_ws(bytes, pos);
                if bytes.get(*pos) == Some(&b'}') {
                    *pos += 1;
                    return Some(());
                }
                loop {
                    parse_string(bytes, pos)?;
                    skip_ws(bytes, pos);
                    if bytes.get(*pos) != Some(&b':') {
                        return None;
                    }
                    *pos += 1;
                    skip_value(bytes, pos)?;
                    skip_ws(bytes, pos);
                    match *bytes.get(*pos)? {
                        b',' => {
                            *pos += 1;
                        }
                        b'}' => {
                            *pos += 1;
                            return Some(());
                        }
                        _ => return None,
                    }
                }
            }
            b'[' => {
                *pos += 1;
                skip_ws(bytes, pos);
                if bytes.get(*pos) == Some(&b']') {
                    *pos += 1;
                    return Some(());
                }
                loop {
                    skip_value(bytes, pos)?;
                    skip_ws(bytes, pos);
                    match *bytes.get(*pos)? {
                        b',' => {
                            *pos += 1;
                        }
                        b']' => {
                            *pos += 1;
                            return Some(());
                        }
                        _ => return None,
                    }
                }
            }
            b't' => {
                if bytes.get(*pos..*pos + 4) != Some(&[b't', b'r', b'u', b'e']) {
                    return None;
                }
                *pos += 4;
            }
            b'f' => {
                if bytes.get(*pos..*pos + 5) != Some(&[b'f', b'a', b'l', b's', b'e']) {
                    return None;
                }
                *pos += 5;
            }
            b'n' => {
                if bytes.get(*pos..*pos + 4) != Some(&[b'n', b'u', b'l', b'l']) {
                    return None;
                }
                *pos += 4;
            }
            c if c == b'-' || c.is_ascii_digit() => {
                while *pos < bytes.len()
                    && matches!(
                        bytes[*pos],
                        b'-' | b'+' | b'.' | b'e' | b'E' | b'0'..=b'9'
                    )
                {
                    *pos += 1;
                }
            }
            _ => return None,
        }
        Some(())
    }

    skip_ws(bytes, &mut pos);
    if bytes.get(pos) != Some(&b'{') {
        return None;
    }
    pos += 1;
    skip_ws(bytes, &mut pos);
    if bytes.get(pos) == Some(&b'}') {
        pos += 1;
        skip_ws(bytes, &mut pos);
        return if pos == bytes.len() { Some(fields) } else { None };
    }
    loop {
        let key = parse_string(bytes, &mut pos)?;
        skip_ws(bytes, &mut pos);
        if bytes.get(pos) != Some(&b':') {
            return None;
        }
        pos += 1;
        skip_ws(bytes, &mut pos);
        if bytes.get(pos) == Some(&b'"') {
            let value = parse_string(bytes, &mut pos)?;
            fields.fields.insert(key, value);
        } else {
            skip_value(bytes, &mut pos)?;
        }
        skip_ws(bytes, &mut pos);
        match *bytes.get(pos)? {
            b',' => {
                pos += 1;
            }
            b'}' => {
                pos += 1;
                break;
            }
            _ => return None,
        }
    }
    skip_ws(bytes, &mut pos);
    if pos != bytes.len() {
        return None;
    }
    Some(fields)
}

// ---------------------------------------------------------------------------
// Relay: routing over the room store
// ---------------------------------------------------------------------------

/// The relay: a [`RoomStore`] plus routing and the viewer file.
/// Mirrors `createRelayServer` state and endpoints.
pub struct Relay {
    store: RoomStore,
    viewer_path: Option<PathBuf>,
}

impl Relay {
    /// Create a relay; a present-but-unreadable store file fails boot,
    /// like the original's `readFileSync` throw.
    pub fn new(store_file: Option<PathBuf>) -> Self {
        Self::with_viewer(store_file, None)
    }

    /// Create a relay with an explicit viewer file for `GET /`.
    /// `None` resolves per request: `RELAY_VIEWER_FILE` env, then
    /// `relay/viewer.html` relative to the current directory.
    pub fn with_viewer(store_file: Option<PathBuf>, viewer_path: Option<PathBuf>) -> Self {
        let store = match store_file {
            None => RoomStore::memory(),
            Some(path) => RoomStore::with_file(path.clone()).unwrap_or_else(|err| {
                panic!(
                    "Meta Nuntius: failed to read store file {}: {err}",
                    path.display()
                )
            }),
        };
        Self { store, viewer_path }
    }

    fn viewer_path(&self) -> Option<PathBuf> {
        if let Some(p) = &self.viewer_path {
            return Some(p.clone());
        }
        if let Ok(p) = std::env::var("RELAY_VIEWER_FILE") {
            if !p.is_empty() {
                return Some(PathBuf::from(p));
            }
        }
        let candidate = Path::new("relay/viewer.html");
        if candidate.exists() {
            return Some(candidate.to_path_buf());
        }
        None
    }

    /// Port of `GET /health`: `{ok: true, rooms: <count>, store}`.
    pub fn health_body(&self) -> String {
        format!(
            "{{\"ok\":true,\"rooms\":{},\"store\":\"{}\"}}",
            self.store.room_count(),
            self.store.store_kind()
        )
    }

    /// Route one HTTP exchange without touching sockets.
    /// Returns `(status, content_type, body)`.
    pub fn handle(&mut self, method: &str, target: &str, body: &[u8]) -> (u16, String, String) {
        const JSON: &str = "application/json";
        let bad = |msg: String| (400u16, JSON.to_string(), error_body(&msg));
        let not_found = || (404u16, JSON.to_string(), error_body("not found"));

        let path = target.split('?').next().unwrap_or(target);
        let segments: Vec<&str> = path.split('/').filter(|p| !p.is_empty()).collect();

        if method == "GET" && (path == "/" || path.is_empty()) {
            let html = self
                .viewer_path()
                .as_ref()
                .and_then(|p| fs::read_to_string(p).ok());
            return match html {
                Some(html) => (200, "text/html; charset=utf-8".to_string(), html),
                None => (
                    500,
                    "text/plain".to_string(),
                    "viewer.html is missing beside relay.mjs".to_string(),
                ),
            };
        }

        if method == "GET" && path == "/health" {
            return (200, JSON.to_string(), self.health_body());
        }

        if segments.len() == 3 && segments[0] == "rooms" {
            let room = match percent_decode(segments[1]) {
                Ok(room) => room,
                Err(()) => {
                    return (
                        500,
                        JSON.to_string(),
                        error_body("internal error: invalid percent-encoding in room name"),
                    );
                }
            };
            if !valid_room(&room) {
                return bad("room name must match [a-z0-9-]{1,32}".to_string());
            }
            let action = segments[2];

            if method == "POST" && action == "messages" {
                if body.len() > MAX_BODY_BYTES {
                    return (400, JSON.to_string(), error_body("request body too large or unreadable"));
                }
                let fields = match parse_body(body) {
                    Ok(fields) => fields,
                    Err(_) => return (400, JSON.to_string(), error_body("request body is not valid JSON")),
                };
                let nick = fields.get("nick").unwrap_or("");
                let text = fields.get("text").unwrap_or("");
                if fields.get("nick").is_none() || !is_single_line(nick, MAX_NICK_CHARS) {
                    return bad(format!(
                        "nick must be a single line of 1-{MAX_NICK_CHARS} chars"
                    ));
                }
                if fields.get("text").is_none() || !is_single_line(text, MAX_TEXT_CHARS) {
                    return bad(format!(
                        "text must be a single line of 1-{MAX_TEXT_CHARS} chars"
                    ));
                }
                let line = message_line(nick, text, now_secs());
                let index = self.store.append(&room, &line);
                return (201, JSON.to_string(), format!("{{\"index\":{index}}}"));
            }

            if method == "POST" && action == "notify" {
                if body.len() > MAX_BODY_BYTES {
                    return (400, JSON.to_string(), error_body("request body too large or unreadable"));
                }
                let fields = match parse_body(body) {
                    Ok(fields) => fields,
                    Err(_) => return (400, JSON.to_string(), error_body("request body is not valid JSON")),
                };
                let severity = fields.get("severity").unwrap_or("");
                let topic = fields.get("topic").unwrap_or("");
                let text = fields.get("text").unwrap_or("");
                if !valid_severity(severity) {
                    return bad(
                        r#"severity must be one of "info", "warning", "critical""#.to_string(),
                    );
                }
                if fields.get("topic").is_none() || !is_single_line(topic, MAX_TOPIC_CHARS) {
                    return bad(format!(
                        "topic must be a single line of 1-{MAX_TOPIC_CHARS} chars"
                    ));
                }
                if fields.get("text").is_none() || !is_single_line(text, MAX_TEXT_CHARS) {
                    return bad(format!(
                        "text must be a single line of 1-{MAX_TEXT_CHARS} chars"
                    ));
                }
                let id = notify_id(&room, topic, severity, text);
                let line = notify_line(&id, severity, topic, text, now_secs());
                let index = self.store.append(&room, &line);
                return (
                    201,
                    JSON.to_string(),
                    format!("{{\"index\":{index},\"id\":\"{}\"}}", escape(&id)),
                );
            }

            if method == "GET" && action == "messages" {
                let since = parse_since(split_since(target).as_deref());
                let total = self.store.messages(&room).len();
                let lines = self.store.messages_since(&room, since);
                let mut out = format!(
                    "{{\"room\":\"{}\",\"total\":{total},\"messages\":[",
                    escape(&room)
                );
                for (i, line) in lines.iter().enumerate() {
                    if i > 0 {
                        out.push(',');
                    }
                    out.push('"');
                    out.push_str(&escape(line));
                    out.push('"');
                }
                out.push_str("]}");
                return (200, JSON.to_string(), out);
            }
        }

        not_found()
    }
}

fn error_body(message: &str) -> String {
    format!("{{\"error\":\"{}\"}}", escape(message))
}

fn now_secs() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

// ---------------------------------------------------------------------------
// Minimal std-only HTTP serving (no external server dependency)
// ---------------------------------------------------------------------------

/// Serve `relay` on `listener` forever, one thread per connection.
pub fn serve(listener: TcpListener, relay: Arc<Mutex<Relay>>) -> std::io::Result<()> {
    for stream in listener.incoming() {
        match stream {
            Ok(stream) => {
                let relay = Arc::clone(&relay);
                thread::spawn(move || {
                    if let Err(err) = handle_connection(stream, relay) {
                        eprintln!("Meta Nuntius: connection error: {err}");
                    }
                });
            }
            Err(err) => eprintln!("Meta Nuntius: accept failed: {err}"),
        }
    }
    Ok(())
}

fn handle_connection(stream: TcpStream, relay: Arc<Mutex<Relay>>) -> std::io::Result<()> {
    let mut reader = BufReader::new(stream.try_clone()?);
    let mut request_line = String::new();
    if reader.read_line(&mut request_line)? == 0 {
        return Ok(());
    }
    let request_line = request_line.trim_end().to_string();
    let mut parts = request_line.split_whitespace();
    let method = parts.next().unwrap_or("").to_string();
    let target = parts.next().unwrap_or("/").to_string();

    let mut content_length: usize = 0;
    loop {
        let mut line = String::new();
        reader.read_line(&mut line)?;
        if line.trim_end().is_empty() {
            break;
        }
        if let Some((name, value)) = line.split_once(':') {
            if name.trim().eq_ignore_ascii_case("content-length") {
                content_length = value.trim().parse::<usize>().unwrap_or(0);
            }
        }
    }

    // Like the original (which only reads bodies on POST routes),
    // GET bodies are never read; POST bodies are capped.
    let (body, overflow) = if method == "POST" {
        let capped = content_length.min(MAX_BODY_BYTES + 1);
        let mut body = vec![0u8; capped];
        if capped > 0 {
            reader.read_exact(&mut body)?;
        }
        (body, content_length > MAX_BODY_BYTES)
    } else {
        (Vec::new(), false)
    };

    let (status, content_type, response_body) = match relay.lock() {
        Ok(mut guard) => guard.handle(&method, &target, &body),
        Err(_) => (
            500,
            "application/json".to_string(),
            error_body("internal error: relay lock poisoned"),
        ),
    };
    let (status, response_body) = if overflow {
        (
            400,
            error_body("request body too large or unreadable"),
        )
    } else {
        (status, response_body)
    };

    let reason = match status {
        200 => "OK",
        201 => "Created",
        400 => "Bad Request",
        404 => "Not Found",
        500 => "Internal Server Error",
        _ => "OK",
    };
    let response = format!(
        "HTTP/1.1 {status} {reason}\r\nContent-Type: {content_type}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{response_body}",
        response_body.len()
    );
    let mut stream = reader.into_inner();
    use std::io::Write as _;
    stream.write_all(response.as_bytes())?;
    stream.flush()?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Parity tests — name roots mirror relay/relay.test.mjs
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write as _;
    use std::net::TcpListener;
    use std::time::Duration;

    fn test_relay() -> Relay {
        Relay::with_viewer(None, Some(PathBuf::from("/nonexistent-viewer.html")))
    }

    fn post_messages(relay: &mut Relay, room: &str, body: &str) -> (u16, String) {
        let (status, content_type, raw) = relay.handle("POST", &format!("/rooms/{room}/messages"), body.as_bytes());
        assert_eq!(content_type, "application/json");
        (status, raw)
    }

    #[test]
    fn append_then_poll_by_watermark() {
        let mut relay = test_relay();
        let (status, raw) =
            post_messages(&mut relay, "main", r#"{"nick":"pax","text":"first line"}"#);
        assert_eq!(status, 201);
        assert!(raw.contains(r#""index":0"#), "{raw}");
        let (status, raw) =
            post_messages(&mut relay, "main", r#"{"nick":"del","text":"second line"}"#);
        assert_eq!(status, 201);
        assert!(raw.contains(r#""index":1"#), "{raw}");

        let (status, _, all) = relay.handle("GET", "/rooms/main/messages?since=-1", &[]);
        assert_eq!(status, 200);
        assert!(all.contains(r#""room":"main""#));
        assert!(all.contains(r#""total":2"#));
        assert!(all.contains("pax: first line [ts:"));
        assert!(all.contains("del: second line [ts:"));

        let (_, _, after_first) = relay.handle("GET", "/rooms/main/messages?since=0", &[]);
        assert!(after_first.contains("del: second line [ts:"));
        assert!(!after_first.contains("pax: first line"));
        // Same messages as slicing the full response after the first line.
        assert!(all.contains(after_first.split('[').last().unwrap_or("")));

        let (_, _, caught_up) = relay.handle("GET", "/rooms/main/messages?since=1", &[]);
        assert!(caught_up.contains(r#""messages":[]"#));
        assert!(caught_up.contains(r#""total":2"#));

        let (status, _, no_since) = relay.handle("GET", "/rooms/main/messages", &[]);
        assert_eq!(status, 200);
        assert!(no_since.contains("pax: first line [ts:"));
        assert!(no_since.contains("del: second line [ts:"));
    }

    #[test]
    fn rooms_are_isolated() {
        let mut relay = test_relay();
        post_messages(&mut relay, "main", r#"{"nick":"pax","text":"first line"}"#);
        post_messages(&mut relay, "main", r#"{"nick":"del","text":"second line"}"#);
        post_messages(&mut relay, "1", r#"{"nick":"hana","text":"room one only"}"#);

        let (_, _, room1) = relay.handle("GET", "/rooms/1/messages?since=-1", &[]);
        assert!(room1.contains(r#""total":1"#));
        let (_, _, main) = relay.handle("GET", "/rooms/main/messages?since=-1", &[]);
        assert!(main.contains(r#""total":2"#)); // unchanged by the room-1 post
        assert!(!main.contains("room one"));
    }

    #[test]
    fn notify_line_format_and_deterministic_id() {
        let mut relay = test_relay();
        let payload = r#"{"severity":"info","topic":"trio-result","text":"trio job trio-abc product ignis completed: category steam or fog"}"#;
        let (status, _, posted) = relay.handle("POST", "/rooms/main/notify", payload.as_bytes());
        assert_eq!(status, 201);
        // Same golden id the pure-core test pins (Node hashlib value).
        assert!(posted.contains(r#""id":"ntf-27c8a8f20499356d""#));

        let (_, _, again) = relay.handle("POST", "/rooms/main/notify", payload.as_bytes());
        assert!(again.contains(r#""id":"ntf-27c8a8f20499356d""#)); // same basis, same id

        let index: i64 = posted
            .split("\"index\":")
            .nth(1)
            .and_then(|s| s.split([',', '}']).next())
            .and_then(|s| s.parse().ok())
            .unwrap();
        let (_, _, lines) = relay.handle(
            "GET",
            &format!("/rooms/main/messages?since={}", index - 1),
            &[],
        );
        assert!(lines.contains(
            "relay: NOTIFY:ntf-27c8a8f20499356d info [trio-result] trio job trio-abc product ignis completed: category steam or fog [ts:"
        ));
    }

    #[test]
    fn validation_refusals() {
        let mut relay = test_relay();
        let big = "x".repeat(2001);
        let cases: Vec<(&str, &str, String)> = vec![
            ("POST", "/rooms/main/messages", r#"{"nick":"","text":"x"}"#.to_string()),
            ("POST", "/rooms/main/messages", r#"{"nick":"pax","text":""}"#.to_string()),
            ("POST", "/rooms/main/messages", r#"{"nick":"pa\nx","text":"x"}"#.to_string()),
            ("POST", "/rooms/main/messages", r#"{"nick":"pax","text":"two\nlines"}"#.to_string()),
            ("POST", "/rooms/main/messages", format!(r#"{{"nick":"pax","text":"{big}"}}"#)),
            ("POST", "/rooms/main/notify", r#"{"severity":"loud","topic":"t","text":"x"}"#.to_string()),
            ("POST", "/rooms/main/notify", r#"{"severity":"info","topic":"","text":"x"}"#.to_string()),
            ("POST", "/rooms/Bad%20Room/messages", r#"{"nick":"pax","text":"x"}"#.to_string()),
            ("GET", "/rooms/Bad%20Room/messages", String::new()),
            ("POST", "/rooms/UPPER/messages", r#"{"nick":"pax","text":"x"}"#.to_string()),
        ];
        for (method, route, body) in &cases {
            let (status, content_type, raw) = relay.handle(method, route, body.as_bytes());
            assert_eq!(status, 400, "{method} {route} {body}");
            assert_eq!(content_type, "application/json");
            assert!(raw.contains(r#""error""#), "{method} {route}");
        }
    }

    #[test]
    fn refusals_for_bad_json_and_oversized_bodies() {
        let mut relay = test_relay();
        let (status, _, raw) =
            relay.handle("POST", "/rooms/main/messages", b"not json at all");
        assert_eq!(status, 400);
        assert!(raw.contains("not valid JSON"));

        let big = vec![b'x'; MAX_BODY_BYTES + 1];
        let (status, _, raw) = relay.handle("POST", "/rooms/main/messages", &big);
        assert_eq!(status, 400);
        assert!(raw.contains("too large"));

        // Unknown routes are 404 JSON, like the original's fallthrough.
        let (status, _, raw) = relay.handle("GET", "/nope", &[]);
        assert_eq!(status, 404);
        assert!(raw.contains("not found"));

        // Malformed % in the room segment is a 500, mirroring the
        // original's decodeURIComponent throw in its catch-all.
        let (status, _, _) = relay.handle("GET", "/rooms/%zz/messages", &[]);
        assert_eq!(status, 500);
    }

    #[test]
    fn health_names_the_memory_store() {
        let mut relay = test_relay();
        post_messages(&mut relay, "main", r#"{"nick":"pax","text":"first line"}"#);
        post_messages(&mut relay, "1", r#"{"nick":"hana","text":"room one only"}"#);
        let (status, _, health) = relay.handle("GET", "/health", &[]);
        assert_eq!(status, 200);
        assert!(health.contains(r#""ok":true"#));
        assert!(health.contains(r#""store":"memory""#));
        assert!(health.contains(r#""rooms":2"#)); // main + 1 were used above
    }

    #[test]
    fn health_names_the_file_store() {
        let dir = std::env::temp_dir().join(format!("nuntius-http-{}", std::process::id()));
        let _ = fs::create_dir_all(&dir);
        let store = dir.join("relay.jsonl");
        let _ = fs::remove_file(&store);
        let mut relay = Relay::with_viewer(
            Some(store.clone()),
            Some(PathBuf::from("/nonexistent-viewer.html")),
        );
        post_messages(&mut relay, "main", r#"{"nick":"pax","text":"hi"}"#);
        let (_, _, health) = relay.handle("GET", "/health", &[]);
        assert!(health.contains(r#""store":"file""#));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn viewer_is_served_at_slash() {
        // Serve the real in-tree viewer asset without porting it: the
        // relay reads viewer.html from disk per request (500 when missing).
        let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let viewer = manifest.join("../../relay/viewer.html");
        assert!(viewer.exists(), "in-tree relay/viewer.html must exist");
        let mut relay = Relay::with_viewer(None, Some(viewer));
        let (status, content_type, body) = relay.handle("GET", "/", &[]);
        assert_eq!(status, 200);
        assert!(content_type.starts_with("text/html"));
        assert!(body.contains("Meta Nuntius"));
        assert!(body.contains("Notifications"));

        // Missing viewer -> 500 plain text, like the original.
        let mut missing =
            Relay::with_viewer(None, Some(PathBuf::from("/nonexistent-viewer.html")));
        let (status, content_type, body) = missing.handle("GET", "/", &[]);
        assert_eq!(status, 500);
        assert_eq!(content_type, "text/plain");
        assert_eq!(body, "viewer.html is missing beside relay.mjs");
    }

    #[test]
    fn file_store_persists_lines_across_a_restart() {
        let dir = std::env::temp_dir().join(format!("nuntius-restart-{}", std::process::id()));
        let _ = fs::create_dir_all(&dir);
        let store = dir.join("relay.jsonl");
        let _ = fs::remove_file(&store);
        let viewer = Some(PathBuf::from("/nonexistent-viewer.html"));

        {
            let mut first = Relay::with_viewer(Some(store.clone()), viewer.clone());
            post_messages(&mut first, "main", r#"{"nick":"milo","text":"persisted line"}"#);
            let (status, _, _) = first.handle(
                "POST",
                "/rooms/ops/notify",
                br#"{"severity":"warning","topic":"trio-result","text":"trio job trio-x product ignis failed: boom"}"#,
            );
            assert_eq!(status, 201);
            let (_, _, health) = first.handle("GET", "/health", &[]);
            assert!(health.contains(r#""store":"file""#));
        }

        {
            let mut second = Relay::with_viewer(Some(store.clone()), viewer);
            let (_, _, main) = second.handle("GET", "/rooms/main/messages?since=-1", &[]);
            assert!(main.contains(r#""total":1"#));
            assert!(main.contains("milo: persisted line [ts:"));
            let (_, _, ops) = second.handle("GET", "/rooms/ops/messages?since=-1", &[]);
            assert!(ops.contains(r#""total":1"#));
            assert!(ops.contains("relay: NOTIFY:ntf-"));
            assert!(ops.contains("warning [trio-result]"));
        }

        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn since_parsing_matches_parseint() {
        assert_eq!(parse_since(None), -1);
        assert_eq!(parse_since(Some("-1")), -1);
        assert_eq!(parse_since(Some("0")), 0);
        assert_eq!(parse_since(Some("1")), 1);
        assert_eq!(parse_since(Some("abc")), -1);
        assert_eq!(parse_since(Some("")), -1);
        assert_eq!(parse_since(Some("-2")), -1);
        assert_eq!(parse_since(Some("3abc")), 3);
        assert_eq!(percent_decode("Bad%20Room").unwrap(), "Bad Room");
        assert_eq!(percent_decode("%31").unwrap(), "1");
        assert!(percent_decode("%zz").is_err());
    }

    // -- live socket test (binds an ephemeral localhost port) --------------

    fn http_round_trip(request: &str) -> String {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        let relay = Arc::new(Mutex::new(test_relay()));
        let server_relay = Arc::clone(&relay);
        thread::spawn(move || {
            let (stream, _) = listener.accept().unwrap();
            handle_connection(stream, server_relay).unwrap();
        });
        std::thread::sleep(Duration::from_millis(50));
        let mut stream = TcpStream::connect(format!("127.0.0.1:{port}")).unwrap();
        stream.write_all(request.as_bytes()).unwrap();
        let mut response = String::new();
        stream.read_to_string(&mut response).unwrap();
        response
    }

    #[test]
    fn live_http_post_then_get() {
        let body = r#"{"nick":"pax","text":"hello"}"#;
        let request = format!(
            "POST /rooms/main/messages HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
            body.len(),
            body
        );
        let response = http_round_trip(&request);
        assert!(response.starts_with("HTTP/1.1 201"), "{response}");
        assert!(response.contains(r#""index":0"#));
    }
}
