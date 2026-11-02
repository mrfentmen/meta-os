// services/common/enc/enc.goose
//
// B-L1-121 — Encoding libraries: Base64 and UTF-8 validation, over fixed buffers.
//
// Status: RUNS — reached by tests/t79_limit_drivers (42 checks, exit 0). Measured 2026-11-02 by audit_status.py.
//
// WHY THESE TWO TOGETHER
// ----------------------
// They are the only encodings this layer actually speaks: Base64 for anything that has to
// travel through a text channel (a key pasted into a config, a manifest digest in a log
// line), UTF-8 because a console that accepts bytes it cannot decode draws rubbish and then
// gets blamed for it.
//
// BOTH ARE STRICT, ON PURPOSE
// ---------------------------
// - Base64 refuses padding in the middle, a length that is not a multiple of 4, and any
//   character outside the alphabet. A decoder that skips whitespace "for convenience"
//   accepts a truncated line and produces plausible garbage.
// - UTF-8 refuses overlong encodings, surrogates, code points above U+10FFFF, and
//   continuation bytes with no lead. Those four rules are the entire difference between
//   "decodes as UTF-8" and "some byte sequence that most browsers accept".
//
// NO ALLOCATION. Every function writes into the caller's buffer and returns the number of
// bytes written, or a negative error code. A decoder that allocated would be the only
// allocator in the layer, and the first one to be used by an agent-facing path.

import common.err.err;

// ---------------------------------------------------------------------------
// Base64
// ---------------------------------------------------------------------------

// RFC 4648 alphabet, standard (not URL-safe). URL-safe is a different table and is a
// separate function the day a URL needs it; switching alphabets by a flag is how a decoder
// accepts what the encoder never produced.
fn b64_char(v: i64) -> u8 {
    if v < 0 { return 0; }
    if v < 26 { return (65 + v) as u8; }        // A-Z
    if v < 52 { return (97 + v - 26) as u8; }   // a-z
    if v < 62 { return (48 + v - 52) as u8; }   // 0-9
    if v == 62 { return '+'; }
    return '/';
}

// -1 for anything not in the alphabet, including '='.
fn b64_value(c: u8) -> i64 {
    if c >= 'A' && c <= 'Z' { return (c - 'A') as i64; }
    if c >= 'a' && c <= 'z' { return 26 + ((c - 'a') as i64); }
    if c >= '0' && c <= '9' { return 52 + ((c - '0') as i64); }
    if c == '+' { return 62; }
    if c == '/' { return 63; }
    return -1;
}

fn b64_encoded_len(n: i64) -> i64 {
    if n < 0 { return -1; }
    return ((n + 2) / 3) * 4;
}

// Encode into `out`, padding with '='. Returns (bytes_written, code); E_NOROOM when the
// destination cannot hold b64_encoded_len(len) bytes -- a partial encode is never written,
// because half a Base64 string decodes to half a payload that looks complete.
fn b64_encode(src: const u8[:], out: u8[>..]&, cap: i64) -> i64, i64 {
    let need = b64_encoded_len(src.len);
    if need < 0 { return 0, E_INVAL; }
    if need > cap { return 0, E_NOROOM; }

    var i: i64 = 0;
    var produced: i64 = 0;
    while i + 3 <= src.len {
        let a = src[i] as i64;
        let b = src[i + 1] as i64;
        let c = src[i + 2] as i64;
        out.push(b64_char(a >> 2));
        out.push(b64_char(((a & 0x03) << 4) | (b >> 4)));
        out.push(b64_char(((b & 0x0F) << 2) | (c >> 6)));
        out.push(b64_char(c & 0x3F));
        produced = produced + 4;
        i = i + 3;
    }

    let rem = src.len - i;
    if rem == 1 {
        let a = src[i] as i64;
        out.push(b64_char(a >> 2));
        out.push(b64_char((a & 0x03) << 4));
        out.push('=');
        out.push('=');
        produced = produced + 4;
    } else if rem == 2 {
        let a = src[i] as i64;
        let b = src[i + 1] as i64;
        out.push(b64_char(a >> 2));
        out.push(b64_char(((a & 0x03) << 4) | (b >> 4)));
        out.push(b64_char((b & 0x0F) << 2));
        out.push('=');
        produced = produced + 4;
    }
    return produced, CODE_OK;
}

// Decode into `out`. Returns (bytes_written, code). Strict:
//   - length must be a non-zero multiple of 4 (an empty input decodes to empty, CODE_OK)
//   - '=' may appear only as the last one or two characters
//   - no whitespace, no newlines, no URL-safe '-' or '_'
//   - the unused low bits of the final quantum must be zero, so a corrupted tail cannot
//     decode to a different byte than the one that was encoded
fn b64_decode(src: const u8[:], out: u8[>..]&, cap: i64) -> i64, i64 {
    if src.len == 0 { return 0, CODE_OK; }
    if (src.len % 4) != 0 { return 0, E_INVAL; }

    var padn: i64 = 0;
    if src[src.len - 1] == '=' { padn = padn + 1; }
    if src[src.len - 2] == '=' { padn = padn + 1; }
    if padn > 2 { return 0, E_INVAL; }

    let need = (src.len / 4) * 3 - padn;
    if need > cap { return 0, E_NOROOM; }

    var i: i64 = 0;
    var produced: i64 = 0;
    while i < src.len {
        let c0 = b64_value(src[i]);
        let c1 = b64_value(src[i + 1]);
        let c2 = b64_soft(src[i + 2]);
        let c3 = b64_soft(src[i + 3]);
        if c0 < 0 || c1 < 0 { return produced, E_INVAL; }
        // Padding is only legal in the final quantum.
        if i + 4 < src.len && (src[i + 2] == '=' || src[i + 3] == '=') { return produced, E_INVAL; }

        out.push(((c0 << 2) | (c1 >> 4)) as u8);
        produced = produced + 1;
        if src[i + 2] != '=' {
            if c2 < 0 { return produced, E_INVAL; }
            out.push(((((c1 & 0x0F) << 4) | (c2 >> 2))) as u8);
            produced = produced + 1;
        }
        if src[i + 3] != '=' {
            if c3 < 0 { return produced, E_INVAL; }
            if c2 < 0 { return produced, E_INVAL; }
            out.push(((((c2 & 0x03) << 6) | c3)) as u8);
            produced = produced + 1;
        }
        // The bits past the end of the payload must be zero. A corrupted tail that decodes
        // to a different byte than the one encoded is otherwise indistinguishable from a
        // correct decode.
        if src[i + 3] == '=' && src[i + 2] != '=' && (c2 & 0x03) != 0 { return produced, E_INVAL; }
        if src[i + 2] == '=' && (c1 & 0x0F) != 0 { return produced, E_INVAL; }

        i = i + 4;
    }
    return produced, CODE_OK;
}

// A '=' reads as zero for the arithmetic but is checked before use.
fn b64_soft(c: u8) -> i64 {
    if c == '=' { return 0; }
    return b64_value(c);
}

// ---------------------------------------------------------------------------
// UTF-8
// ---------------------------------------------------------------------------

// Strict validation. Returns (code_points, code): E_INVAL for any sequence that is not
// shortest-form UTF-8 of a scalar value.
//
// The four refusals, spelled out because each one is a real attack surface in a parser that
// accepts bytes and hands them to something else:
//   1. continuation byte with no lead (0x80..0xBF first)
//   2. overlong forms (0xC0/0xC1 leads, and any form whose value fits in fewer bytes)
//   3. surrogates (U+D800..U+DFFF, encoded as 0xED 0xA0.. 0xBF)
//   4. beyond U+10FFFF (0xF5.. leads, and 0xF4 with a second byte above 0x8F)
fn utf8_validate(s: const u8[:]) -> i64, i64 {
    var i: i64 = 0;
    var points: i64 = 0;
    while i < s.len {
        let b0 = s[i] as i64;
        if b0 < 0x80 { i = i + 1; points = points + 1; continue; }

        var need: i64 = 0;
        var cp: i64 = 0;
        var min_cp: i64 = 0;
        if b0 >= 0xC2 && b0 <= 0xDF { need = 1; cp = b0 & 0x1F; min_cp = 0x80; }
        else if b0 >= 0xE0 && b0 <= 0xEF { need = 2; cp = b0 & 0x0F; min_cp = 0x800; }
        else if b0 >= 0xF0 && b0 <= 0xF4 { need = 3; cp = b0 & 0x07; min_cp = 0x10000; }
        else { return points, E_INVAL; }      // 0x80..0xC1 and 0xF5.. are never leads

        if i + need >= s.len { return points, E_INVAL; }   // truncated sequence
        var k: i64 = 1;
        while k <= need {
            let bk = s[i + k] as i64;
            if bk < 0x80 || bk > 0xBF { return points, E_INVAL; }
            cp = (cp << 6) | (bk & 0x3F);
            k = k + 1;
        }
        if cp < min_cp { return points, E_INVAL; }                   // overlong
        if cp >= 0xD800 && cp <= 0xDFFF { return points, E_INVAL; }  // surrogate
        if cp > 0x10FFFF { return points, E_INVAL; }
        i = i + need + 1;
        points = points + 1;
    }
    return points, CODE_OK;
}

// Bytes a code point occupies when encoded, or 0 when it is not a scalar value.
fn utf8_len_for(cp: i64) -> i64 {
    if cp < 0 { return 0; }
    if cp < 0x80 { return 1; }
    if cp < 0x800 { return 2; }
    if cp >= 0xD800 && cp <= 0xDFFF { return 0; }
    if cp < 0x10000 { return 3; }
    if cp <= 0x10FFFF { return 4; }
    return 0;
}

// Encode one code point. Returns (bytes_written, code).
fn utf8_encode(cp: i64, out: u8[>..]&, cap: i64) -> i64, i64 {
    let n = utf8_len_for(cp);
    if n == 0 { return 0, E_INVAL; }
    if n > cap { return 0, E_NOROOM; }
    if n == 1 {
        out.push(cp as u8);
    } else if n == 2 {
        out.push((0xC0 | (cp >> 6)) as u8);
        out.push((0x80 | (cp & 0x3F)) as u8);
    } else if n == 3 {
        out.push((0xE0 | (cp >> 12)) as u8);
        out.push((0x80 | ((cp >> 6) & 0x3F)) as u8);
        out.push((0x80 | (cp & 0x3F)) as u8);
    } else {
        out.push((0xF0 | (cp >> 18)) as u8);
        out.push((0x80 | ((cp >> 12) & 0x3F)) as u8);
        out.push((0x80 | ((cp >> 6) & 0x3F)) as u8);
        out.push((0x80 | (cp & 0x3F)) as u8);
    }
    return n, CODE_OK;
}

// Decode the code point at `at`. Returns (code_point, bytes_consumed, ok). Used by the
// display helpers to advance by character rather than by byte -- the difference between
// wrapping a line correctly and splitting a character in half.
fn utf8_next(s: const u8[:], at: i64) -> i64, i64, bool {
    if at < 0 || at >= s.len { return 0, 0, false; }
    let b0 = s[at] as i64;
    if b0 < 0x80 { return b0, 1, true; }

    var need: i64 = 0;
    var cp: i64 = 0;
    if b0 >= 0xC2 && b0 <= 0xDF { need = 1; cp = b0 & 0x1F; }
    else if b0 >= 0xE0 && b0 <= 0xEF { need = 2; cp = b0 & 0x0F; }
    else if b0 >= 0xF0 && b0 <= 0xF4 { need = 3; cp = b0 & 0x07; }
    else { return 0, 1, false; }

    if at + need >= s.len { return 0, 1, false; }
    var k: i64 = 1;
    while k <= need {
        let bk = s[at + k] as i64;
        if bk < 0x80 || bk > 0xBF { return 0, k, false; }
        cp = (cp << 6) | (bk & 0x3F);
        k = k + 1;
    }
    if cp >= 0xD800 && cp <= 0xDFFF { return 0, need + 1, false; }
    if cp > 0x10FFFF { return 0, need + 1, false; }
    return cp, need + 1, true;
}

// Column width of a string for the display layer: one column per code point, with the
// combining marks and full-width forms called out rather than guessed. A width table with
// every range in Unicode is a data problem for later; refusing to pretend is today's job.
fn utf8_columns(s: const u8[:]) -> i64, i64 {
    var at: i64 = 0;
    var cols: i64 = 0;
    while at < s.len {
        let cp, n, ok = utf8_next(s, at);
        if !ok { return cols, E_INVAL; }
        if n > 0 { at = at + n; } else { at = at + 1; }
        if cp >= 0x0300 && cp <= 0x036F { continue; }        // combining: zero width
        if cp >= 0x1100 && cp <= 0x115F { cols = cols + 2; continue; }   // Hangul Jamo
        if cp >= 0x2E80 && cp <= 0xA4CF { cols = cols + 2; continue; }   // CJK
        if cp >= 0xAC00 && cp <= 0xD7A3 { cols = cols + 2; continue; }   // Hangul syllables
        if cp >= 0xF900 && cp <= 0xFAFF { cols = cols + 2; continue; }   // CJK compat
        if cp >= 0xFF00 && cp <= 0xFF60 { cols = cols + 2; continue; }   // full-width forms
        cols = cols + 1;
    }
    return cols, CODE_OK;
}
