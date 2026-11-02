// services/updater/signature.goose
//
// B-L1-123 — Updater signature interface.
//
// Status: DESIGNED. Not written against a primitive, not compiled, not run.
//
// WHY THIS FILE HAS NO VERIFIER IN IT
// -----------------------------------
// The task says the implementation status stays DESIGNED until a verified primitive lands, and
// "no hand-rolled crypto claims". So this file contains:
//
//   1. the INTERFACE the updater calls (types + the one function that decides)
//   2. the MANIFEST SIGNING FORMAT, byte by byte, so two implementations can agree
//   3. the REFUSAL: sig_verify_manifest returns E_UNSUPPORTED, always, today
//
// That last point is the honest part. An updater that "verifies" with a function that always
// says yes is worse than one that has no verification at all, because it is described as
// verified. The refusal is loud, specific, and cannot be configured away.
//
// THE PRIMITIVE, WHEN IT LANDS
// ----------------------------
// Ed25519, detached signature, over the canonical manifest bytes defined below. Not ECDSA (two
// encodings, both in the wild, one of them malleable), not RSA (padding modes, and a key big
// enough to be slow on the machines this targets), and not SHA-256-as-a-MAC (a shared secret
// on a machine the attacker may already own).
//
// Where it comes from, in preference order:
//   1. a constant-time implementation with test vectors in the tree (RFC 8032 section 7.1)
//   2. a vetted crate/package reviewed as part of the build
//   3. nothing -- the updater keeps refusing, and the OS ships without signing
//
// WHAT "CANONICAL" MEANS HERE
// ---------------------------
// The manifest text is signed exactly as it appears on the wire, with the signature block
// itself excluded. No re-serialisation, no key reordering, no whitespace normalisation: a
// canonicalisation step is a second parser, and the classic signature bypass lives in the gap
// between the bytes that were signed and the bytes that were executed.
//
//   signed_bytes = manifest bytes from offset 0 up to (but excluding) the line
//                  "signature <alg> <keyid> <base64>"
//
// The signature line must be the LAST line, must appear exactly once, and any manifest whose
// text after the signature line is not empty is refused before any crypto runs.

import common.err.err;
import common.enc.enc;
import updater.updater;

let SIG_DESIGNED: i64 = 0;        // interface exists, no verifier
let SIG_VERIFIED: i64 = 1;        // a primitive is present and the vectors pass

let SIG_ALG_ED25519: i64 = 1;
let SIG_KEY_ID_MAX: i64 = 16;
let SIG_BYTES_MAX: i64 = 64;      // Ed25519 signatures are 64 bytes

struct SigBlock {
    alg: i64,
    key_id: u8[..16],
    key_id_len: i64,
    sig: u8[..64],
    sig_len: i64,
    line_off: i64,                // where the signature line starts in the manifest text
}

// What the updater is allowed to claim about its own verification, in one call. The report
// prints this word; nothing else may.
fn sig_status() -> i64 {
    return SIG_DESIGNED;
}

fn sig_status_name() -> const u8[:] {
    if sig_status() == SIG_DESIGNED { return "DESIGNED"; }
    return "VERIFIED";
}

// THE ONE FUNCTION THE UPDATER CALLS.
//
// Today: always E_UNSUPPORTED, with no way to opt out. When a primitive lands, this body
// becomes the parse + verify + constant-time compare, and `sig_status()` changes -- both in
// the same commit, so the claim and the code cannot drift.
fn sig_verify_manifest(text: const u8[:], trusted: const u8[:]) -> i64, i64 {
    if text.len == 0 { return 0, E_INVAL; }
    // A deliberate refusal, not a stub that forgot to be written.
    return 0, E_UNSUPPORTED;
}

// ---------------------------------------------------------------------------
// Format (parsed only when a primitive exists; kept here so the format has one home)
// ---------------------------------------------------------------------------

// "signature ed25519 <keyid> <base64sig>", the last line of a manifest.
//
// The parser is written even though verification is not, because the FORMAT is the part that
// has to be agreed before anyone implements anything. It is exercised by its own test
// (B-L1-131's hostile inputs cover it), and it does no crypto: it splits, decodes Base64, and
// reports whether the shape is legal.
fn sig_parse(text: const u8[:]) -> SigBlock, i64 {
    var b: SigBlock = SigBlock {
        alg: 0,
        key_id: [],
        key_id_len: 0,
        sig: [],
        sig_len: 0,
        line_off: 0,
    };
    b.alg = 0;
    b.key_id_len = 0;
    b.sig_len = 0;
    b.line_off = -1;
    var i: i64 = 0;
    while i < SIG_KEY_ID_MAX { b.key_id[i] = 0; i = i + 1; }
    i = 0;
    while i < SIG_BYTES_MAX { b.sig[i] = 0; i = i + 1; }

    // Find the last line that starts with "signature ".
    var at: i64 = 0;
    var line_start: i64 = 0;
    var found: i64 = -1;
    var found_start: i64 = 0;
    var found_end: i64 = 0;
    while at <= text.len {
        let at_end = at == text.len;
        let is_nl = !at_end && text[at] == 10;
        if at_end || is_nl {
            if sig_line_matches(text, line_start, at) {
                found = found + 1;
                found_start = line_start;
                found_end = at;
                if found > 0 { return b, E_INVAL; }     // exactly one signature line
            }
            line_start = at + 1;
        }
        at = at + 1;
    }
    if found < 0 { return b, E_NOTFOUND; }
    b.line_off = found_start;

    // Nothing may follow the signature line.
    if found_end != text.len { return b, E_INVAL; }

    // signature <alg> <keyid> <b64>
    var p = found_start + 10;                 // past "signature "
    var alg_end = p;
    while alg_end < found_end && text[alg_end] != ' ' { alg_end = alg_end + 1; }
    if alg_end >= found_end { return b, E_INVAL; }
    if !sig_bytes_eq(text[p..alg_end], "ed25519") { return b, E_CORRUPT; }
    b.alg = SIG_ALG_ED25519;

    p = alg_end + 1;
    var kid_end = p;
    while kid_end < found_end && text[kid_end] != ' ' { kid_end = kid_end + 1; }
    if kid_end >= found_end { return b, E_INVAL; }
    let kid_len = kid_end - p;
    if kid_len == 0 || kid_len > SIG_KEY_ID_MAX { return b, E_INVAL; }
    var k: i64 = 0;
    while k < kid_len {
        b.key_id[k] = text[p + k];
        k = k + 1;
    }
    b.key_id_len = kid_len;

    p = kid_end + 1;
    if p >= found_end { return b, E_INVAL; }
    var sig_out: u8[>..] = [];
    let n, code = b64_decode(text[p..found_end], sig_out, SIG_BYTES_MAX);
    if code != CODE_OK { return b, code; }
    if n != 64 { return b, E_INVAL; }         // an Ed25519 signature is exactly 64 bytes
    var s: i64 = 0;
    while s < 64 {
        b.sig[s] = sig_out[s];
        s = s + 1;
    }
    b.sig_len = n;
    return b, CODE_OK;
}

fn sig_line_matches(text: const u8[:], start: i64, end: i64) -> bool {
    let prefix = "signature ";
    if end - start < prefix.len { return false; }
    var i: i64 = 0;
    while i < prefix.len {
        if text[start + i] != prefix[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn sig_bytes_eq(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

// The bytes that would be signed: everything before the signature line. Returned as a length,
// because a slice of the caller's buffer is all anyone needs and copying it would be a second
// copy of the thing being signed.
fn sig_signed_len(b: SigBlock&) -> i64 {
    if b.line_off < 0 { return -1; }
    return b.line_off;
}

// Which key ids this build trusts. Empty today, and the empty case is the important one: a
// verifier with no trusted keys must refuse, not accept unverified updates.
fn sig_trusted_key_count() -> i64 {
    return 0;
}
