//! T032 [B31] port of `os/tests/test_bus_rename.py` (same name roots).
//!
//! Tap-to-rename builders: `pyStr` JSON escaping, nonce shape, rename-log /
//! names-hash / names-history entry shapes, keyless admin verify (`admin.py`
//! `_verify_envelope`: no sig → None, never a failure), `qNick` encoding,
//! `parseNames`, `labelFor`, case-insensitive `isAdmin`.
//!
//! Blocked (needs `node` + excluded `bus.html`, named not dropped):
//! - JS interop runs (builder block + DOM presence runs)
//! - Wiring assertions (tappable nicks, modal, write paths, keyless UI,
//!   display validation, lifecycle hooks, renderPresence integration)

use hmac::{Hmac, Mac};
use rand::RngCore;
use serde_json::{json, Map, Value};
use sha2::Sha256;

pub const CASES: &[&str] = &[
    "pystr matches json dumps",
    "nonce shape",
    "log entry is valid json",
    "log entry is keyless",
    "keyless entry passes admin verify",
    "names hash entry shape",
    "history entry shape",
    "qnick encoding",
    "parse names object form",
    "parse names flat array form",
    "parse names nullish",
    "label for",
    "is admin case insensitive",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[
    "node interop: builder block run (excluded bus.html /*__SIGNING_START__*/)",
    "node interop: presence DOM run (excluded bus.html + IIFE)",
    "wiring: nicks become tappable buttons (excluded bus.html)",
    "wiring: rename modal present (excluded bus.html)",
    "wiring: admin set check keyless (excluded bus.html)",
    "wiring: three write paths (excluded bus.html)",
    "wiring: no admin key anywhere in flow (excluded bus.html)",
    "wiring: display name validation (excluded bus.html)",
    "wiring: feature hooked into chat lifecycle (excluded bus.html)",
    "wiring: core render uses display names (excluded bus.html)",
    "wiring: poll uses window.renderPresence (excluded bus.html)",
    "wiring: display fn exposed (needs node DOM run)",
    "wiring: loadNames parses Upstash shape (needs node DOM run)",
];

/// `pyStr`: JSON string literal with `ensure_ascii=True` semantics.
pub fn py_str(s: &str) -> String {
    let mut out = String::from("\"");
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\t' => out.push_str("\\t"),
            '\r' => out.push_str("\\r"),
            '\u{08}' => out.push_str("\\b"),
            '\u{0c}' => out.push_str("\\f"),
            c if c == ' ' || c.is_ascii_graphic() => out.push(c),
            c if (c as u32) < 0x20 || (c as u32) == 0x7f => {
                out.push_str(&format!("\\u{:04x}", c as u32))
            }
            c if (c as u32) < 0x10000 => {
                out.push_str(&format!("\\u{:04x}", c as u32))
            }
            c => {
                // Astral: UTF-16 surrogate pair, like ensure_ascii.
                let v = c as u32 - 0x10000;
                out.push_str(&format!("\\u{:04x}\\u{:04x}", 0xd800 + (v >> 10), 0xdc00 + (v & 0x3ff)));
            }
        }
    }
    // ASCII fast path already covered; non-ASCII always escaped above.
    out.push('"');
    out
}

/// `randHexBytes(8)`: 16 lowercase hex chars.
pub fn rand_hex_bytes(n: usize) -> String {
    let mut b = vec![0u8; n];
    rand::thread_rng().fill_bytes(&mut b);
    hex::encode(b)
}

pub fn rename_log_entry(actor: &str, nick: &str, display: &str) -> Value {
    json!({"v": 1, "cmd": "rename",
           "args": {"nick": nick, "display": display}, "actor": actor})
}

pub fn names_hash_entry(display: &str, by: &str, at: i64) -> Value {
    json!({"display": display, "set_by": by, "set_at": at})
}

pub fn names_history_entry(nick: &str, display: &str, by: &str, at: i64) -> Value {
    json!({"nick": nick, "display": display, "set_by": by, "set_at": at})
}

/// `admin.py::_verify_envelope`: keyless (no sig) → None (not a failure);
/// signed but no key → false; else HMAC compare over the canonical envelope.
pub fn admin_verify_envelope(secret: Option<&[u8]>, canonical: &[u8], sig: Option<&str>) -> Option<bool> {
    let sig = sig?;
    let secret = secret?;
    let mut m = Hmac::<Sha256>::new_from_slice(secret).unwrap();
    m.update(canonical);
    let expect = m.finalize().into_bytes();
    let got = hex::decode(sig).unwrap_or_default();
    // Constant-time compare, mirroring hmac.compare_digest.
    if expect.len() != got.len() {
        return Some(false);
    }
    let mut diff = 0u8;
    for (a, b) in expect.iter().zip(got.iter()) {
        diff |= a ^ b;
    }
    Some(diff == 0)
}

/// Canonical admin envelope: JSON {v,cmd,args,actor,ts,nonce}, sorted keys,
/// compact separators — mirrors `admin.py::_canonical_envelope`.
pub fn admin_canonical(v: u32, cmd: &str, args: &Value, actor: &str, ts: i64, nonce: &str) -> Vec<u8> {
    let mut m = Map::new();
    m.insert("actor".into(), Value::String(actor.into()));
    m.insert("args".into(), args.clone());
    m.insert("cmd".into(), Value::String(cmd.into()));
    m.insert("nonce".into(), Value::String(nonce.into()));
    m.insert("ts".into(), json!(ts));
    m.insert("v".into(), json!(v));
    // BTreeMap-backed serde_json Map serializes keys sorted already.
    serde_json::to_vec(&Value::Object(m)).unwrap()
}

/// `qNick`: alphanumerics kept, everything else %XX uppercase.
pub fn qnick(nick: &str) -> String {
    let mut out = String::new();
    for b in nick.bytes() {
        if b.is_ascii_alphanumeric() {
            out.push(b as char);
        } else {
            out.push_str(&format!("%{b:02X}"));
        }
    }
    out
}

/// `parseNames` object form: keep JSON values with non-empty display.
pub fn parse_names_obj(entries: &[(&str, &str)]) -> Map<String, Value> {
    let mut out = Map::new();
    for (nick, raw) in entries {
        if let Ok(Value::Object(o)) = serde_json::from_str::<Value>(raw) {
            if let Some(Value::String(d)) = o.get("display") {
                if !d.is_empty() {
                    out.insert(nick.to_string(), Value::String(d.clone()));
                }
            }
        }
    }
    out
}

/// `parseNames` flat-array form: pairwise (key, value), tail junk dropped.
pub fn parse_names_arr(items: &[&str]) -> Map<String, Value> {
    let mut out = Map::new();
    for pair in items.chunks(2) {
        if pair.len() < 2 {
            break;
        }
        let refs: Vec<(&str, &str)> = vec![(pair[0], pair[1])];
        for (k, v) in parse_names_obj(&refs) {
            out.insert(k, v);
        }
    }
    out
}

pub fn label_for(map: &Map<String, Value>, nick: &str) -> String {
    match map.get(nick).and_then(Value::as_str) {
        Some(d) => d.to_string(),
        None => nick.to_string(),
    }
}

/// `isAdmin`: case-insensitive exact membership (ASCII names).
pub fn is_admin(admins: &[&str], nick: &str) -> bool {
    let n = nick.to_lowercase();
    admins.iter().any(|a| a.to_lowercase() == n)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pystr_matches_json_dumps() {
        let cases = [
            ("plain", "\"plain\""),
            ("quote \" and backslash \\", "\"quote \\\" and backslash \\\\\""),
            ("line1\nline2\ttab\rcarriage", "\"line1\\nline2\\ttab\\rcarriage\""),
            ("café", "\"caf\\u00e9\""),
            ("emoji \u{1F600}", "\"emoji \\ud83d\\ude00\""),
            ("del\x7f", "\"del\\u007f\""),
            ("", "\"\""),
            ("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\""),
        ];
        for (case, expect) in cases {
            assert_eq!(py_str(case), expect, "pyStr mismatch for {case:?}");
        }
    }

    #[test]
    fn test_nonce_shape() {
        let n = rand_hex_bytes(8);
        assert_eq!(n.len(), 16);
        assert!(n.chars().all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase()));
    }

    #[test]
    fn test_log_entry_is_valid_json() {
        let env = rename_log_entry("Mrfentmen", "alice", "Alice Cooper");
        assert_eq!(env["v"], 1);
        assert_eq!(env["cmd"], "rename");
        assert_eq!(env["args"], json!({"nick": "alice", "display": "Alice Cooper"}));
        assert_eq!(env["actor"], "Mrfentmen");
    }

    #[test]
    fn test_log_entry_is_keyless() {
        let env = rename_log_entry("Mrfentmen", "alice", "Alice Cooper");
        assert!(env.get("sig").is_none());
    }

    #[test]
    fn test_keyless_entry_passes_admin_verify() {
        let env = rename_log_entry("Mrfentmen", "alice", "Alice Cooper");
        assert_eq!(admin_verify_envelope(Some(b"key"), b"{}", env.get("sig").and_then(Value::as_str)), None);
    }

    #[test]
    fn test_names_hash_entry_shape() {
        assert_eq!(
            names_hash_entry("Alice Cooper", "Mrfentmen", 1758390000),
            json!({"display": "Alice Cooper", "set_by": "Mrfentmen", "set_at": 1758390000})
        );
    }

    #[test]
    fn test_history_entry_shape() {
        assert_eq!(
            names_history_entry("alice", "Alice Cooper", "Mrfentmen", 1758390000),
            json!({"nick": "alice", "display": "Alice Cooper", "set_by": "Mrfentmen", "set_at": 1758390000})
        );
    }

    #[test]
    fn test_qnick_encoding() {
        assert_eq!(qnick("alice"), "alice");
        assert_eq!(qnick("a b/c:d"), "a%20b%2Fc%3Ad");
        assert_eq!(qnick("Mrfentmen"), "Mrfentmen");
    }

    #[test]
    fn test_parse_names_object_form() {
        let got = parse_names_obj(&[
            ("alice", r#"{"display":"Alice Cooper","set_by":"Mrfentmen","set_at":1}"#),
            ("bob", "not-json"),
            ("carol", r#"{"display":"","set_by":"Mrfentmen","set_at":1}"#),
        ]);
        assert_eq!(got.len(), 1);
        assert_eq!(got["alice"], Value::String("Alice Cooper".into()));
    }

    #[test]
    fn test_parse_names_flat_array_form() {
        let got = parse_names_arr(&["alice", r#"{"display":"Alice Cooper"}"#, "bob", "junk"]);
        assert_eq!(got.len(), 1);
        assert_eq!(got["alice"], Value::String("Alice Cooper".into()));
    }

    #[test]
    fn test_parse_names_nullish() {
        assert!(parse_names_obj(&[]).is_empty());
        assert!(parse_names_arr(&[]).is_empty());
    }

    #[test]
    fn test_label_for() {
        let mut m = Map::new();
        m.insert("alice".into(), Value::String("Alice Cooper".into()));
        assert_eq!(label_for(&m, "alice"), "Alice Cooper");
        assert_eq!(label_for(&Map::new(), "alice"), "alice");
    }

    #[test]
    fn test_is_admin_case_insensitive() {
        let admins = ["Mrfentmen", "del", "mute"];
        assert!(is_admin(&admins, "mrfentmen"));
        assert!(is_admin(&admins, "MRFENTMEN"));
        assert!(is_admin(&admins, "Mrfentmen"));
        assert!(!is_admin(&admins, "bob"));
        assert!(!is_admin(&[], "mrfentmen"));
    }
}
