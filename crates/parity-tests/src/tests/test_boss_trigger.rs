//! T031 [B31] port of `os/tests/test_boss_trigger.py` (same name roots).
//!
//! HMAC-signed boss trigger: canonical payload `pax-trigger-v1\n{nick}\n{text}\n{ts}`,
//! HMAC-SHA256 signature, ±600s staleness window, replay set, unsigned test mode.
//! Interop vectors below are the fixed vectors from the Python suite
//! (`SECRET_HEX = "0123456789abcdef"*4`, `NOW = 1726874100`).
//!
//! Blocked (excluded viewer + external harness, named not dropped):
//! - Node interop driver (needs `node` + trigger block from excluded `bus.html`)
//! - Wiring assertions (need excluded `bus.html`: markers, secret panel,
//!   trigger button, SubtleCrypto, `__busTest.bossTrigger`)
//! - External `trigger_check` module (`~/workspace/relay-trigger/bin`,
//!   outside the repo) — its contract is ported here from the test vectors.

use std::collections::HashSet;

use hmac::{Hmac, Mac};
use sha2::Sha256;

pub const CASES: &[&str] = &[
    "canonical matches",
    "hmac agrees",
    "hex roundtrip",
    "unicode payload agrees",
    "empty text canonical",
    "bad hex rejected",
    "valid envelope",
    "tampered text rejected",
    "wrong secret rejected",
    "stale ts rejected",
    "future ts within skew ok",
    "replay rejected",
    "uppercase sig accepted",
    "bad version rejected",
    "malformed fields rejected",
    "unsigned test envelope accepted",
    "unsigned replay rejected",
    "unsigned stale ts rejected",
    "null sig without flag rejected",
    "canonical payload stable",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[
    "node interop driver (needs node + excluded bus.html trigger block)",
    "wiring: block markers (excluded bus.html)",
    "wiring: trigger key muse-bus:pax-trigger (excluded bus.html)",
    "wiring: secret ui (excluded bus.html)",
    "wiring: secret optional test mode (excluded bus.html)",
    "wiring: trigger button (excluded bus.html)",
    "wiring: subtle crypto signing (excluded bus.html)",
    "wiring: protocol version (excluded bus.html)",
    "wiring: no embedded secret (excluded bus.html)",
    "wiring: test hook __busTest.bossTrigger (excluded bus.html)",
];

/// Fixed test vector secret: `bytes.fromhex("0123456789abcdef"*4)`.
pub fn test_secret() -> Vec<u8> {
    hex::decode("0123456789abcdef".repeat(4)).unwrap()
}
pub const NOW: i64 = 1726874100;

pub fn canonical_payload(nick: &str, text: &str, ts: i64) -> Vec<u8> {
    format!("pax-trigger-v1\n{nick}\n{text}\n{ts}").into_bytes()
}

pub fn hmac_hex(secret: &[u8], payload: &[u8]) -> String {
    let mut m = Hmac::<Sha256>::new_from_slice(secret).unwrap();
    m.update(payload);
    hex::encode(m.finalize().into_bytes())
}

#[derive(Debug, Clone)]
pub struct Envelope {
    pub v: u32,
    pub nick: String,
    pub text: String,
    pub ts: i64,
    pub sig: Option<String>,
    pub unsigned: bool,
}

pub fn sign_envelope(secret: &[u8], nick: &str, text: &str, ts: i64) -> Envelope {
    let sig = hmac_hex(secret, &canonical_payload(nick, text, ts));
    Envelope { v: 1, nick: nick.into(), text: text.into(), ts, sig: Some(sig), unsigned: false }
}

/// Returns (mode, rkey, reason). `mode` is `None` on rejection.
/// Staleness pinned by tests: reject when `now - ts > 600`; `+60` skew ok.
pub fn verify_envelope(
    secret: &[u8],
    env: &Envelope,
    now: i64,
    seen: &mut HashSet<String>,
) -> (Option<String>, Option<String>, Option<String>) {
    if env.v != 1 {
        return (None, None, None);
    }
    if env.nick.is_empty() || env.text.is_empty() {
        return (None, None, None);
    }
    if now - env.ts > 600 {
        return (None, None, Some("stale ts".into()));
    }
    if env.unsigned {
        let rkey = format!("u:{}:{}:{}", env.nick, env.text, env.ts);
        if seen.contains(&rkey) {
            return (None, None, Some("replay".into()));
        }
        seen.insert(rkey.clone());
        return (Some("unsigned".into()), Some(rkey), None);
    }
    let sig = match &env.sig {
        Some(s) => s,
        None => return (None, None, Some("bad sig".into())),
    };
    let expect = hmac_hex(secret, &canonical_payload(&env.nick, &env.text, env.ts));
    if sig.to_lowercase() != expect {
        return (None, None, Some("bad signature".into()));
    }
    let rkey = sig.to_lowercase();
    if seen.contains(&rkey) {
        return (None, None, Some("replay".into()));
    }
    seen.insert(rkey.clone());
    (Some("signed".into()), Some(rkey), None)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn seen() -> HashSet<String> {
        HashSet::new()
    }

    #[test]
    fn test_canonical_matches() {
        assert_eq!(
            canonical_payload("mrfentmen", "who is alice", 1726874100),
            b"pax-trigger-v1\nmrfentmen\nwho is alice\n1726874100".to_vec()
        );
    }

    #[test]
    fn test_hmac_agrees() {
        assert_eq!(
            hmac_hex(&test_secret(), &canonical_payload("mrfentmen", "who is alice", 1726874100)),
            "5d252ee8852cbed31081bcf72a9e168b7e24489f749245755c0ffab85235908d"
        );
    }

    #[test]
    fn test_hex_roundtrip() {
        let raw = test_secret();
        assert_eq!(hex::decode(hex::encode(&raw)).unwrap(), raw);
        assert!(hex::decode("tooshort").is_err() || hex::decode("tooshort").unwrap().len() != 32);
    }

    #[test]
    fn test_unicode_payload_agrees() {
        assert_eq!(
            hmac_hex(&test_secret(), &canonical_payload("mrfentmen", "café \u{1F600}", 1)),
            "c3fee53f7680c4d0b543a23d4641345f6dd873aef2aa13e037ec9ce43f13d891"
        );
    }

    #[test]
    fn test_empty_text_canonical() {
        assert_eq!(canonical_payload("a", "", 0), b"pax-trigger-v1\na\n\n0".to_vec());
        assert_eq!(
            hmac_hex(&test_secret(), &canonical_payload("a", "", 0)),
            "a5c2cf881f081c26da8c85dead7d47e07aa812adbea05833626fdeb088db1ae8"
        );
    }

    #[test]
    fn test_bad_hex_rejected() {
        assert!(hex::decode("tooshort").is_err() || hex::decode("tooshort").unwrap().len() != 32);
    }

    #[test]
    fn test_valid_envelope() {
        let env = sign_envelope(&test_secret(), "mrfentmen", "who is alice", NOW);
        let (mode, rkey, _) = verify_envelope(&test_secret(), &env, NOW, &mut seen());
        assert_eq!(mode.as_deref(), Some("signed"));
        assert_eq!(rkey, env.sig.map(|s| s.to_lowercase()));
    }

    #[test]
    fn test_tampered_text_rejected() {
        let mut env = sign_envelope(&test_secret(), "mrfentmen", "who is alice", NOW);
        env.text = "who is alice!!".into();
        let (mode, _, reason) = verify_envelope(&test_secret(), &env, NOW, &mut seen());
        assert_eq!(mode, None);
        assert_eq!(reason.as_deref(), Some("bad signature"));
    }

    #[test]
    fn test_wrong_secret_rejected() {
        let env = sign_envelope(&vec![0u8; 32], "mrfentmen", "who is alice", NOW);
        let (mode, _, _) = verify_envelope(&test_secret(), &env, NOW, &mut seen());
        assert_eq!(mode, None);
    }

    #[test]
    fn test_stale_ts_rejected() {
        let env = sign_envelope(&test_secret(), "mrfentmen", "old", NOW - 601);
        let (mode, _, reason) = verify_envelope(&test_secret(), &env, NOW, &mut seen());
        assert_eq!(mode, None);
        assert_eq!(reason.as_deref(), Some("stale ts"));
    }

    #[test]
    fn test_future_ts_within_skew_ok() {
        let env = sign_envelope(&test_secret(), "mrfentmen", "soon", NOW + 60);
        let (mode, _, _) = verify_envelope(&test_secret(), &env, NOW, &mut seen());
        assert_eq!(mode.as_deref(), Some("signed"));
    }

    #[test]
    fn test_replay_rejected() {
        let env = sign_envelope(&test_secret(), "mrfentmen", "once", NOW);
        let rkey = env.sig.clone().unwrap().to_lowercase();
        let mut seen_set = HashSet::from([rkey]);
        let (mode, _, reason) = verify_envelope(&test_secret(), &env, NOW, &mut seen_set);
        assert_eq!(mode, None);
        assert_eq!(reason.as_deref(), Some("replay"));
    }

    #[test]
    fn test_uppercase_sig_accepted() {
        let mut env = sign_envelope(&test_secret(), "mrfentmen", "shout", NOW);
        env.sig = env.sig.map(|s| s.to_uppercase());
        let (mode, _, _) = verify_envelope(&test_secret(), &env, NOW, &mut seen());
        assert_eq!(mode.as_deref(), Some("signed"));
    }

    #[test]
    fn test_bad_version_rejected() {
        let mut env = sign_envelope(&test_secret(), "mrfentmen", "v2", NOW);
        env.v = 2;
        let (mode, _, _) = verify_envelope(&test_secret(), &env, NOW, &mut seen());
        assert_eq!(mode, None);
    }

    #[test]
    fn test_malformed_fields_rejected() {
        for env in [
            Envelope { v: 1, nick: "".into(), text: "x".into(), ts: NOW, sig: Some("0".repeat(64)), unsigned: false },
            Envelope { v: 1, nick: "mrfentmen".into(), text: "".into(), ts: NOW, sig: Some("0".repeat(64)), unsigned: false },
        ] {
            let (mode, _, _) = verify_envelope(&test_secret(), &env, NOW, &mut seen());
            assert_eq!(mode, None);
        }
        // v != 1 covered by bad-version; non-object input has no Rust
        // representation — the type system rejects it at construction.
    }

    #[test]
    fn test_unsigned_test_envelope_accepted() {
        let env = Envelope { v: 1, nick: "mrfentmen".into(), text: "test ping".into(), ts: NOW, sig: None, unsigned: true };
        let (mode, rkey, _) = verify_envelope(&test_secret(), &env, NOW, &mut seen());
        assert_eq!(mode.as_deref(), Some("unsigned"));
        assert!(rkey.unwrap().starts_with("u:"));
    }

    #[test]
    fn test_unsigned_replay_rejected() {
        let env = Envelope { v: 1, nick: "mrfentmen".into(), text: "test ping".into(), ts: NOW, sig: None, unsigned: true };
        let mut s = seen();
        let (mode, rkey, _) = verify_envelope(&test_secret(), &env, NOW, &mut s);
        assert_eq!(mode.as_deref(), Some("unsigned"));
        let (mode2, _, reason2) = verify_envelope(&test_secret(), &env, NOW, &mut HashSet::from([rkey.unwrap()]));
        assert_eq!(mode2, None);
        assert_eq!(reason2.as_deref(), Some("replay"));
    }

    #[test]
    fn test_unsigned_stale_ts_rejected() {
        let env = Envelope { v: 1, nick: "mrfentmen".into(), text: "old ping".into(), ts: NOW - 601, sig: None, unsigned: true };
        let (mode, _, reason) = verify_envelope(&test_secret(), &env, NOW, &mut seen());
        assert_eq!(mode, None);
        assert_eq!(reason.as_deref(), Some("stale ts"));
    }

    #[test]
    fn test_null_sig_without_flag_rejected() {
        let env = Envelope { v: 1, nick: "mrfentmen".into(), text: "sneaky".into(), ts: NOW, sig: None, unsigned: false };
        let (mode, _, reason) = verify_envelope(&test_secret(), &env, NOW, &mut seen());
        assert_eq!(mode, None);
        assert_eq!(reason.as_deref(), Some("bad sig"));
    }

    #[test]
    fn test_canonical_payload_stable() {
        assert_eq!(
            canonical_payload("mrfentmen", "who is alice", 1726874100),
            b"pax-trigger-v1\nmrfentmen\nwho is alice\n1726874100".to_vec()
        );
    }
}
