//! B110 — every refusal branch in `queue-core`, asserted against the code.
//!
//! The crate takes a parsed `Envelope`, so the parse-layer refusals Python's
//! `validate_envelope` performs (`not a JSON object`, `has no image object`,
//! non-string id/timestamp) are unreachable here and are recorded as gaps in
//! `os-build/records/queue-core-gaps.md`, not faked with a test.

use queue_core::{
    base64_decode, deterministic_job_id, sha256_hex, validate_envelope, Envelope, EnvelopeImage,
};

const PRODUCTS: [&str; 3] = ["vigiles", "ignis", "medicus"];
const TS: &str = "2026-11-02T00:00:00.000Z";

fn b64(data: &[u8]) -> String {
    const ALPHABET: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::new();
    for chunk in data.chunks(3) {
        let b = [
            chunk[0],
            *chunk.get(1).unwrap_or(&0),
            *chunk.get(2).unwrap_or(&0),
        ];
        let n = ((b[0] as u32) << 16) | ((b[1] as u32) << 8) | b[2] as u32;
        out.push(ALPHABET[(n >> 18) as usize & 63] as char);
        out.push(ALPHABET[(n >> 12) as usize & 63] as char);
        out.push(if chunk.len() > 1 {
            ALPHABET[(n >> 6) as usize & 63] as char
        } else {
            '='
        });
        out.push(if chunk.len() > 2 {
            ALPHABET[n as usize & 63] as char
        } else {
            '='
        });
    }
    out
}

fn frame() -> Vec<u8> {
    (0..=255u8).cycle().take(1024).collect()
}

fn valid() -> Envelope {
    let raw = frame();
    Envelope {
        version: 1,
        kind: "trio-assessment".to_string(),
        id: deterministic_job_id("ignis", TS, &raw),
        product: "ignis".to_string(),
        timestamp: TS.to_string(),
        image: EnvelopeImage {
            data_url: format!("data:image/jpeg;base64,{}", b64(&raw)),
            byte_length: raw.len(),
            sha256: sha256_hex(&raw),
        },
    }
}

#[test]
fn wrong_version_is_refused() {
    let mut env = valid();
    env.version = 2;
    assert_eq!(
        validate_envelope(&env, &PRODUCTS).as_deref(),
        Some("not a trio-assessment v1 envelope")
    );
}

#[test]
fn wrong_kind_is_refused() {
    let mut env = valid();
    env.kind = "trio-assessment-result".to_string();
    assert_eq!(
        validate_envelope(&env, &PRODUCTS).as_deref(),
        Some("not a trio-assessment v1 envelope")
    );
}

#[test]
fn empty_id_is_refused() {
    let mut env = valid();
    env.id.clear();
    assert_eq!(
        validate_envelope(&env, &PRODUCTS).as_deref(),
        Some("envelope has no job id")
    );
}

#[test]
fn unknown_product_is_refused_with_the_python_wording() {
    let mut env = valid();
    env.product = "nope".to_string();
    assert_eq!(
        validate_envelope(&env, &PRODUCTS).as_deref(),
        Some("unknown product 'nope'")
    );
}

#[test]
fn empty_product_list_refuses_every_product() {
    let env = valid();
    assert_eq!(
        validate_envelope(&env, &[]).as_deref(),
        Some("unknown product 'ignis'")
    );
}

#[test]
fn empty_timestamp_is_refused() {
    let mut env = valid();
    env.timestamp.clear();
    assert_eq!(
        validate_envelope(&env, &PRODUCTS).as_deref(),
        Some("envelope has no timestamp")
    );
}

#[test]
fn non_jpeg_data_url_is_refused() {
    let mut env = valid();
    env.image.data_url = "data:image/png;base64,AAAA".to_string();
    assert_eq!(
        validate_envelope(&env, &PRODUCTS).as_deref(),
        Some("image.dataUrl is not a JPEG data URL")
    );
    env.image.data_url = "https://example.invalid/frame.jpg".to_string();
    assert_eq!(
        validate_envelope(&env, &PRODUCTS).as_deref(),
        Some("image.dataUrl is not a JPEG data URL")
    );
}

#[test]
fn undecodable_base64_is_refused() {
    let mut env = valid();
    env.image.data_url = "data:image/jpeg;base64,!!!!".to_string();
    assert_eq!(
        validate_envelope(&env, &PRODUCTS).as_deref(),
        Some("image.dataUrl does not base64-decode")
    );
}

#[test]
fn byte_length_mismatch_is_refused() {
    let mut env = valid();
    env.image.byte_length += 1;
    assert_eq!(
        validate_envelope(&env, &PRODUCTS).as_deref(),
        Some("image.byteLength does not match the decoded frame")
    );
}

#[test]
fn sha256_mismatch_is_refused() {
    let mut env = valid();
    env.image.sha256 = "0".repeat(64);
    assert_eq!(
        validate_envelope(&env, &PRODUCTS).as_deref(),
        Some("image.sha256 does not match the decoded frame")
    );
}

#[test]
fn base64_errors_are_typed_strings() {
    assert_eq!(base64_decode("ABC"), Err("invalid base64 length"));
    assert_eq!(base64_decode("A==="), Err("invalid base64 padding"));
    assert_eq!(
        base64_decode("AB=C"),
        Err("padding before end of base64 input")
    );
    assert_eq!(base64_decode("AB*C"), Err("invalid base64 character"));
    assert_eq!(base64_decode("===="), Err("invalid base64 padding"));
}

#[test]
fn base64_accepts_the_empty_input() {
    assert_eq!(base64_decode(""), Ok(Vec::new()));
}

#[test]
fn base64_rejects_a_quad_with_too_much_padding() {
    // Three data characters plus three '=' is not a legal quad.
    assert!(base64_decode("A===").is_err());
    assert!(base64_decode("AB==").is_ok());
}
