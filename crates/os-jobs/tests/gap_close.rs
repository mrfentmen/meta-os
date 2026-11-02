//! B035 — test-gap close. The crate's `mod encoding_tests` (lib.rs 3286)
//! held one test, the smallest group in the crate. Its module surface is
//! the pure encoding/parity helpers: quoting, escaping, hashing, keyrings,
//! canonical payloads. These are the cases that group was missing, taken
//! to the level of the crate's best-covered group.
//!
//! All assertions are fixed vectors or exact comparisons, so a drift in
//! the encoders fails here rather than silently changing a signature.

use os_jobs::{
    canonical_json, canonical_payload_v1, canonical_payload_v2, ct_eq, hex_digest, hmac_sha256,
    json_escape, python_repr, sha256, url_quote, url_unquote,
};
use std::collections::HashMap;

#[test]
fn url_quote_percent_encodes_everything_but_unreserved() {
    assert_eq!(url_quote("a b/c+d~._-"), "a%20b%2Fc%2Bd~._-");
}

#[test]
fn url_unquote_leaves_malformed_sequences_alone() {
    assert_eq!(url_unquote("%2F%20+%zz%"), "/ +%zz%");
}

#[test]
fn url_quote_unquote_round_trips_utf8() {
    let quoted = url_quote("é/ü");
    assert_eq!(quoted, "%C3%A9%2F%C3%BC");
    assert_eq!(url_unquote(&quoted), "é/ü");
}

#[test]
fn json_escape_handles_quote_backslash_and_controls() {
    assert_eq!(
        json_escape("a\"b\\c\n\t\u{0001}"),
        "\"a\\\"b\\\\c\\n\\t\\u0001\""
    );
}

#[test]
fn json_escape_surrogate_pairs_beyond_the_bmp() {
    assert_eq!(json_escape("\u{1F600}"), "\"\\ud83d\\ude00\"");
}

#[test]
fn canonical_json_sorts_keys_and_uses_compact_separators() {
    let bytes = canonical_json(&[("b", "2"), ("a", "1")]);
    assert_eq!(String::from_utf8(bytes).unwrap(), "{\"a\":\"1\",\"b\":\"2\"}");
}

#[test]
fn python_repr_escapes_quote_and_backslash() {
    assert_eq!(python_repr("a'b\\c"), "'a\\'b\\\\c'");
}

#[test]
fn hex_digest_is_lowercase_and_zero_padded() {
    assert_eq!(hex_digest(&[0x00, 0x0f, 0x10, 0xff]), "000f10ff");
}

#[test]
fn ct_eq_is_length_aware_and_content_aware() {
    assert!(ct_eq("abc", "abc"));
    assert!(!ct_eq("abc", "abd"));
    assert!(!ct_eq("abc", "ab"));
}

#[test]
fn sha256_matches_the_published_vector() {
    assert_eq!(
        hex_digest(&sha256(b"abc")),
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    );
}

#[test]
fn hmac_sha256_matches_the_published_vector() {
    assert_eq!(
        hex_digest(&hmac_sha256(
            b"key",
            b"The quick brown fox jumps over the lazy dog"
        )),
        "f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8"
    );
}

#[test]
fn canonical_payload_v1_is_the_sorted_six_field_shape() {
    let mut fields = HashMap::new();
    fields.insert("title".to_string(), "T".to_string());
    fields.insert("accept".to_string(), "A".to_string());
    fields.insert("branch".to_string(), "B".to_string());
    fields.insert("base".to_string(), "C".to_string());
    fields.insert("room".to_string(), "R".to_string());
    assert_eq!(
        String::from_utf8(canonical_payload_v1(&fields, "S")).unwrap(),
        "{\"accept\":\"A\",\"base\":\"C\",\"branch\":\"B\",\"room\":\"R\",\"spec\":\"S\",\"title\":\"T\"}"
    );
}

#[test]
fn canonical_payload_v2_binds_job_and_key_id() {
    let fields = HashMap::new();
    let one = canonical_payload_v2("1", "k1", &fields, "S");
    let two = canonical_payload_v2("1", "k2", &fields, "S");
    let other_job = canonical_payload_v2("2", "k1", &fields, "S");
    assert_ne!(one, two, "kid must be inside the signature");
    assert_ne!(one, other_job, "jid must be inside the signature");
    assert!(String::from_utf8(one).unwrap().contains("\"kid\":\"k1\""));
}
