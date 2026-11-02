// services/common/text/text.goose
//
// B-L1-142 — Gap library 4: fixed-buffer text operations.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// THE GAP THIS FILLS
// ------------------
// STDLIB_GAPS.md marks "String search/split/trim" as **provided** by `std` (`find`, `split`,
// `trim`, `to_lower`, ...). That is true and it is also the problem: those functions are written
// for a host with an allocator, and `split` returns a collection. A kernel-side service that
// wants the three tokens in "a=b=c" must not allocate a collection to look at them.
//
// So this file is the same operations with the allocation removed:
//   - trim into a span (start, length), no copy
//   - split by one byte into a span pair, no list
//   - case-insensitive equality, which `std.compare` does not offer
//   - prefix/suffix tests, and a bounded "starts with keyword" for dispatch
//
// WHAT IT IS NOT
// --------------
// Not a second `std.string`. Anything that returns a new string is not here, because returning
// a string means allocating it. Callers that need a copy use common.fmt's append_* into their
// own buffer.

// ---------------------------------------------------------------------------
// Spans
// ---------------------------------------------------------------------------

// The span of `s` between two offsets, trimmed of spaces and tabs at both ends.
// Returned as (start, len) rather than a slice because the caller usually wants to compare or
// copy, and both of those want offsets.
fn text_trim(s: const u8[:], start_in: i64, end_in: i64) -> i64, i64 {
    var end = end_in;
    var start = start_in;
    if start < 0 { start = 0; }
    if end > s.len { end = s.len; }
    if end < start { end = start; }
    var a = start;
    var b = end;
    while a < b {
        let c = s[a];
        if c == ' ' || c == 9 || c == 10 || c == 13 { a = a + 1; continue; }
        break;
    }
    while b > a {
        let c = s[b - 1];
        if c == ' ' || c == 9 || c == 10 || c == 13 { b = b - 1; continue; }
        break;
    }
    return a, b - a;
}

// First occurrence of `needle` in [start, end). Returns the offset, or -1.
// Naive search on purpose: the haystacks here are config lines and log records, and a naive
// search with no allocation is faster than a precomputed table nobody has room to store.
fn text_find(s: const u8[:], start_in: i64, end_in: i64, needle: const u8[:]) -> i64 {
    var start = start_in;
    var end = end_in;
    if needle.len == 0 { return start; }
    if start < 0 { start = 0; }
    if end > s.len { end = s.len; }
    var i = start;
    while i + needle.len <= end {
        var k: i64 = 0;
        var same = true;
        while k < needle.len {
            if s[i + k] != needle[k] { same = false; break; }
            k = k + 1;
        }
        if same { return i; }
        i = i + 1;
    }
    return -1;
}

// Split at the first `sep` in [start, end). The separator is consumed: the second span starts
// after it. When there is no separator, the second span is empty AND the bool is false -- the
// bool is the difference between "no separator" and "separator at the end".
fn text_split(s: const u8[:], start_in: i64, end_in: i64, sep: u8) -> i64, i64, i64, i64, bool {
    var start = start_in;
    var end = end_in;
    if start < 0 { start = 0; }
    if end > s.len { end = s.len; }
    var i = start;
    while i < end {
        if s[i] == sep {
            return start, i - start, i + 1, end - (i + 1), true;
        }
        i = i + 1;
    }
    return start, end - start, end, 0, false;
}

// ---------------------------------------------------------------------------
// Comparison
// ---------------------------------------------------------------------------

fn text_lower(c: u8) -> u8 {
    if c >= 'A' && c <= 'Z' { return (c + 32) as u8; }
    return c;
}

fn text_upper(c: u8) -> u8 {
    if c >= 'a' && c <= 'z' { return (c - 32) as u8; }
    return c;
}

// Case-insensitive equality, ASCII only. Stated because it matters: this is not Unicode case
// folding, and a service that accepts a Turkish dotless i in a command name gets a refusal.
fn text_eq_ci(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if text_lower(a[i]) != text_lower(b[i]) { return false; }
        i = i + 1;
    }
    return true;
}

fn text_has_prefix(s: const u8[:], prefix: const u8[:]) -> bool {
    if prefix.len > s.len { return false; }
    var i: i64 = 0;
    while i < prefix.len {
        if s[i] != prefix[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn text_has_suffix(s: const u8[:], suffix: const u8[:]) -> bool {
    if suffix.len > s.len { return false; }
    let off = s.len - suffix.len;
    var i: i64 = 0;
    while i < suffix.len {
        if s[off + i] != suffix[i] { return false; }
        i = i + 1;
    }
    return true;
}

// Does `s` start with one of a space-separated keyword list? Written for command dispatch,
// where the alternative is comparing against an array of strings allocated at start-up.
// Returns the offset just past the matched keyword, or -1.
fn text_keyword(s: const u8[:], keywords: const u8[:]) -> i64 {
    var at: i64 = 0;
    while at < keywords.len {
        var end = at;
        while end < keywords.len && keywords[end] != ' ' { end = end + 1; }
        let word = keywords[at..end];
        if word.len > 0 && text_has_prefix(s, word) {
            // A keyword must end at a boundary: "ls" must not match "lsof", and "time"
            // must not match "timesync". '=' counts as a boundary so "cmd=value" works.
            let after = word.len;
            if after == s.len || s[after] == ' ' || s[after] == 9 || s[after] == '=' { return after; }
        }
        at = end + 1;
    }
    return -1;
}

// ---------------------------------------------------------------------------
// Numbers in text
// ---------------------------------------------------------------------------

// Parse a non-negative decimal integer from a span. Returns (value, ok).
// Leading zeros are accepted ("007" is 7); a leading '-' is refused rather than wrapped.
fn text_parse_u64(s: const u8[:], start: i64, end: i64) -> i64, bool {
    if start < 0 || end > s.len || end <= start { return 0, false; }
    var v: i64 = 0;
    var i = start;
    while i < end {
        let c = s[i];
        if c < '0' || c > '9' { return 0, false; }
        if v > 922337203685477580 { return 0, false; }    // next *10 would overflow
        v = v * 10 + ((c - '0') as i64);
        i = i + 1;
    }
    return v, true;
}

// Write `v` as decimal into `out`, right-aligned to `width` with `pad_ch`. Returns the bytes
// written, or -1 when it does not fit -- never a truncated number, because a truncated number
// reads as a smaller valid one.
fn text_pad_int(out: u8[>..]&, cap: i64, v: i64, width_in: i64, pad_ch: u8) -> i64 {
    var width = width_in;
    if v < 0 || width < 0 { return -1; }
    var digits: i64 = 1;
    var x = v;
    while x >= 10 { digits = digits + 1; x = x / 10; }
    if digits > width { width = digits; }
    if out.len + width > cap { return -1; }

    var padn = width - digits;
    while padn > 0 { out.push(pad_ch); padn = padn - 1; }
    var buf: u8[..20] = [];
    var i: i64 = 0;
    x = v;
    while i < digits { buf[digits - 1 - i] = (48 + (x % 10)) as u8; x = x / 10; i = i + 1; }
    i = 0;
    while i < digits { out.push(buf[i]); i = i + 1; }
    return width;
}
