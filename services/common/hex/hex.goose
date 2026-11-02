// services/common/hex/hex.goose
//
// B-L1-70 — gap library 3. Base16 (hex) encoding and strict decoding.
//
// Status: RUNS — reached by tests/t64_hex (25 checks, exit 0). Measured 2026-11-02 by audit_status.py.
//
// WHY A WHOLE MODULE FOR THIS
// ---------------------------
// Hex is the wire format for two things in this layer: digests (the manifest stores SHA-256
// as 64 characters, because a byte array in a text config is unreadable and a byte array in
// a log is unprintable) and byte dumps in `audit` records. Both places have the same
// requirement: **a decoder that rejects bad input instead of guessing**. A hex decoder that
// skips whitespace, accepts a stray `0x`, or stops at the first invalid character turns
// "verify this digest" into "verify this prefix", and a prefix match is not a match.
//
// So `hex_decode` here is deliberately strict:
//   - the length must be even;
//   - every character must be [0-9a-fA-F];
//   - the output size must be known before decoding (it is `in.len / 2`);
//   - on any failure it writes NOTHING and returns -1.
//
// The last rule matters. A decoder that writes half a digest and then reports failure
// leaves a caller that ignores the return value comparing against attacker-chosen bytes.
//
// `STDLIB_GAPS.md` lists Goose's `base64` module (2 symbols) as provided; hex is not there,
// and the updater manifest uses hex because a human has to read those digests in a diff.

let HEX_LOWER: const u8[:] = "0123456789abcdef";

// Two characters per input byte, so the exact output size is always known before encoding.
fn hex_encoded_len(n: i64) -> i64 {
    if n < 0 { return 0; }
    return n * 2;
}

// Encode into the caller's buffer. Returns the number of characters written, which is
// `hex_encoded_len(src.len)` on success and less when `cap` is short -- the caller compares,
// because a truncated digest that still looks like a digest is the worst output this module
// can produce.
fn hex_encode(dst: u8[>..]&, cap: i64, src: const u8[:], upper: bool) -> i64 {
    var i: i64 = 0;
    while i < src.len && dst.len + 2 <= cap {
        let b = src[i];
        dst.push(hex_char((b >> 4) & 0xf, upper));
        dst.push(hex_char(b & 0xf, upper));
        i = i + 1;
    }
    return i * 2;
}

// One nibble as a character. Arithmetic rather than a lookup string, because indexing a
// string literal is a slice operation this layer has no sample for and this does not need.
fn hex_char(v: u8, upper: bool) -> u8 {
    if v < 10 { return '0' + v; }
    if upper { return 'A' + (v - 10); }
    return 'a' + (v - 10);
}

// Decode hex into the caller's buffer. Returns the number of BYTES written, or -1 on any
// invalid input, in which case nothing was written.
//
// `dst` gets whole bytes pushed; `cap` is a byte limit, not a character limit, so a caller
// sizing for a 32-byte digest passes 32.
fn hex_decode(dst: u8[>..]&, cap: i64, src: const u8[:]) -> i64 {
    if src.len % 2 != 0 { return -1; }
    let need = src.len / 2;
    if need > cap - dst.len { return -1; }
    // Validate the whole input first: this is the rule at the top of the file, and it is
    // why the loop that writes is separate from the loop that checks.
    var i: i64 = 0;
    while i < src.len {
        if hex_nibble(src[i]) < 0 { return -1; }
        i = i + 1;
    }
    i = 0;
    while i < src.len {
        let hi = hex_nibble(src[i]);
        let lo = hex_nibble(src[i + 1]);
        dst.push(((hi << 4) | lo) as u8);
        i = i + 2;
    }
    return need;
}

fn hex_nibble(c: u8) -> i64 {
    if c >= '0' && c <= '9' { return c - '0'; }
    if c >= 'a' && c <= 'f' { return c - 'a' + 10; }
    if c >= 'A' && c <= 'F' { return c - 'A' + 10; }
    return -1;
}

// Is this exactly a hex string of the given byte length? Used for digest fields, where the
// question is "is this a 32-byte digest" and not "is this mostly hex".
fn hex_is_exact(s: const u8[:], bytes: i64) -> bool {
    if s.len != bytes * 2 { return false; }
    var i: i64 = 0;
    while i < s.len {
        if hex_nibble(s[i]) < 0 { return false; }
        i = i + 1;
    }
    return true;
}

// Case-insensitive equality of two hex strings. Compares the *decoded* nibbles, so `AB` and
// `ab` match without a separate normalisation step -- and still in time proportional to the
// length, with no early exit on the first differing character.
fn hex_eq_ci(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    if a.len % 2 != 0 { return false; }
    var diff: i64 = 0;
    var i: i64 = 0;
    while i < a.len {
        let x = hex_nibble(a[i]);
        let y = hex_nibble(b[i]);
        if x < 0 || y < 0 { return false; }
        diff = diff | (x ^ y);
        i = i + 1;
    }
    return diff == 0;
}

// ---------------------------------------------------------------------------
// What this library deliberately does NOT do
// ---------------------------------------------------------------------------
//
// - **No `0x` prefix, no separators, no whitespace.** `hex_decode("0x1f")` is -1. Every
//   tolerance here is a chance for a digest to be checked against the wrong bytes.
// - **No `hex_decode` into a `u8[..]` fixed array by index.** Pushing into a growable slice
//   is the one form verified in the samples; an indexed write into a caller array is left
//   to `by_copy`-style helpers where the bound is explicit.
// - **No constant-time claim beyond `hex_eq_ci`.** That function ORs differences rather
//   than returning early, but this layer does not claim it is a side-channel defence for
//   secrets -- digest comparison of a public manifest is not a secret comparison, and
//   `common/hash.equal_constant_time` is where that argument is made properly.
// - **No base64.** Immediate follow-on task territory, and the two encodings have
//   different strictness arguments; sharing a file would blur both.
