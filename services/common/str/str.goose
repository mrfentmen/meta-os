// services/common/str/str.goose
//
// B-L1-69 — gap library 2. Splitting and tokenising `u8[:]` without allocating.
//
// Status: WRITTEN (not COMPILED).
//
// WHY A CURSOR AND NOT A LIST
// ---------------------------
// The obvious shape is `split(s, sep) -> [][]u8`, and it is the one thing this layer
// cannot have: building a list of slices needs an array of (start, end) pairs sized for the
// worst case, and "the worst case" for a config file is attacker-chosen. A malicious line of
// 100,000 commas becomes 100,001 spans, and the fixed buffer sized for 16 is a crash on
// input a remote peer chooses.
//
// So splitting is a cursor: `st_next` walks forward and returns one span at a time. Memory
// is O(1) in the number of fields, the caller stops when it wants, and a line with a
// million separators is slow rather than fatal.
//
// THE TWO CURSOR MODES, AND WHY BOTH EXIST
// ---------------------------------------
// - **single separator** (`st_sep`): config `key=value`, FS paths on `/`, record fields.
//   Consecutive separators produce empty fields, deliberately: `a,,b` is three fields, and
//   collapsing them would make an empty value indistinguishable from a missing one.
// - **whitespace** (`st_word`): shell-style tokens, where any run of spaces is one
//   separator and leading/trailing spaces produce no empty token.
//
// Multi-byte separators are NOT a cursor mode. They are one function (`st_lit_span`) that a
// caller loops over itself, because a cursor holding a slice of the caller's line is a
// dangling span waiting to happen once that line is reused -- and line reuse is the whole
// point of a fixed-buffer layer.
//
// NEITHER MODE UNDERSTANDS QUOTES. Quoting is the shell argument parser's job (B-L1-88),
// because quoting is a language feature and this file is not a language.

struct Split {
    start: i64,     // first byte of the input
    end: i64,       // one past the last byte
    pos: i64,       // next byte to examine
    sep: u8,        // the separator (mode 0); unused in whitespace mode
    words: bool,    // true = whitespace mode
    done: bool,
}

// Mode 0: split on exactly `sep`. `a,b` -> "a", "b"; `a,,b` -> "a", "", "b"; "" -> one
// empty span, which is what a caller iterating a config line expects.
fn st_sep(s: const u8[:], sep: u8) -> Split {
    return Split { start: 0, end: s.len, pos: 0, sep: sep, words: false, done: false };
}

// Mode 1: whitespace runs, no empty tokens.
fn st_word(s: const u8[:]) -> Split {
    return Split { start: 0, end: s.len, pos: 0, sep: ' ', words: true, done: false };
}

// The next span. Returns (start, end, found).
//
// `found == false` means the walk is over. An empty final field IS returned as found with
// start == end, so a caller cannot tell "no more fields" from "one more empty field" by
// looking at lengths alone -- which is why `found` is separate from the span.
fn st_next(sp: Split&, s: const u8[:]) -> i64, i64, bool {
    if sp.done { return 0, 0, false; }
    if sp.words { return st_next_word(sp, s); }
    return st_next_sep(sp, s);
}

fn st_next_sep(sp: Split&, s: const u8[:]) -> i64, i64, bool {
    if sp.pos > sp.end { sp.done = true; return 0, 0, false; }
    let from = sp.pos;
    var i = from;
    while i < sp.end && s[i] != sp.sep { i = i + 1; }
    sp.pos = i + 1;                 // step over the separator itself
    if i >= sp.end { sp.done = true; }
    return from, i, true;
}

fn st_next_word(sp: Split&, s: const u8[:]) -> i64, i64, bool {
    var i = sp.pos;
    while i < sp.end && str_is_space_byte(s[i]) { i = i + 1; }
    if i >= sp.end { sp.done = true; return 0, 0, false; }
    let from = i;
    while i < sp.end && !str_is_space_byte(s[i]) { i = i + 1; }
    sp.pos = i;
    if i >= sp.end { sp.done = true; }
    return from, i, true;
}

// One step of a multi-byte split. Call with `from = 0` first; the third return value is the
// offset to pass back as `from`, or -1 when there is no further separator.
//   (span_start, span_end, next_from)
fn st_lit_span(s: const u8[:], lit: const u8[:], from: i64) -> i64, i64, i64 {
    let at = st_find(s, lit, from);
    if at < 0 { return from, s.len, -1; }
    return from, at, at + lit.len;
}

// Local byte search: this module must not depend on `common/bytes`, or the day bytes wants
// str's trimming the two imports form a cycle. Sixty lines duplicated once is cheaper than
// an import cycle discovered by a linker.
fn st_find(hay: const u8[:], needle: const u8[:], from_in: i64) -> i64 {
    var from = from_in;
    if from < 0 { from = 0; }
    if needle.len == 0 || needle.len > hay.len { return -1; }
    var i = from;
    while i + needle.len <= hay.len {
        var k: i64 = 0;
        var hit = true;
        while k < needle.len {
            if hay[i + k] != needle[k] { hit = false; break; }
            k = k + 1;
        }
        if hit { return i; }
        i = i + 1;
    }
    return -1;
}

fn str_is_space_byte(c: u8) -> bool {
    return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == 0x0b || c == 0x0c;
}

// ---------------------------------------------------------------------------
// Counting, without a list
// ---------------------------------------------------------------------------

// How many spans `st_sep` would yield, without building any of them. Used by callers that
// must reject "too many fields" before processing any of them -- a fixed table indexed by
// field number needs to know that up front.
fn st_count_sep(s: const u8[:], sep: u8) -> i64 {
    var n: i64 = 1;
    var i: i64 = 0;
    while i < s.len {
        if s[i] == sep { n = n + 1; }
        i = i + 1;
    }
    return n;
}

fn st_count_word(s: const u8[:]) -> i64 {
    var n: i64 = 0;
    var in_word = false;
    var i: i64 = 0;
    while i < s.len {
        if str_is_space_byte(s[i]) {
            in_word = false;
        } else if !in_word {
            n = n + 1;
            in_word = true;
        }
        i = i + 1;
    }
    return n;
}

// ---------------------------------------------------------------------------
// Case conversion into caller storage
// ---------------------------------------------------------------------------

fn st_to_lower(dst: u8[>..]&, cap: i64, s: const u8[:]) -> i64 {
    var i: i64 = 0;
    while i < s.len && dst.len < cap {
        var c = s[i];
        if c >= 'A' && c <= 'Z' { c = c + 32; }
        dst.push(c);
        i = i + 1;
    }
    return i;
}

fn st_to_upper(dst: u8[>..]&, cap: i64, s: const u8[:]) -> i64 {
    var i: i64 = 0;
    while i < s.len && dst.len < cap {
        var c = s[i];
        if c >= 'a' && c <= 'z' { c = c - 32; }
        dst.push(c);
        i = i + 1;
    }
    return i;
}

// ---------------------------------------------------------------------------
// Slices that keep the caller's arithmetic honest
// ---------------------------------------------------------------------------

// The bytes of `s` between two indices, clamped instead of trusted. Every parser in Wave K
// computes a start and an end; one of them will compute end < start on hostile input, and
// an empty slice is a better outcome than an abort nobody can debug from a log line.
fn st_span(s: const u8[:], start: i64, end: i64) -> const u8[:] {
    var a = start;
    var b = end;
    if a < 0 { a = 0; }
    if b > s.len { b = s.len; }
    if b < a { b = a; }
    return s[a..b];
}

// Copy a span, reporting how much fit. The caller compares to (end - start) when a partial
// copy matters -- the trailing fields of a long line, most often.
fn st_copy_span(dst: u8[>..]&, cap: i64, s: const u8[:], start: i64, end: i64) -> i64 {
    let span = st_span(s, start, end);
    var i: i64 = 0;
    while i < span.len && dst.len < cap {
        dst.push(span[i]);
        i = i + 1;
    }
    return i;
}

// Clamped trim: the (start, end) of `s` with whitespace removed at both ends.
fn st_trim_span(s: const u8[:]) -> i64, i64 {
    var start: i64 = 0;
    var end = s.len;
    while start < end && str_is_space_byte(s[start]) { start = start + 1; }
    while end > start && str_is_space_byte(s[end - 1]) { end = end - 1; }
    return start, end;
}

// ---------------------------------------------------------------------------
// What this library deliberately does NOT do
// ---------------------------------------------------------------------------
//
// - **No quoting or escaping.** `st_word` splits on unquoted whitespace only in the sense
//   that it does not look for quotes at all; the shell parser (B-L1-88) layers quoting on
//   top and is the only place it belongs.
// - **No unicode.** A UTF-8 continuation byte is neither whitespace nor a separator, which
//   is correct for a byte-oriented split and is what a path or a config key needs.
// - **No mutation in place.** Upper/lower/trim write into caller buffers; nothing rewrites
//   the source, so a line can be tokenised and still be logged verbatim.
// - **No number parsing.** `std.parse_int` exists and is verified by name in
//   STDLIB_GAPS.md; a second integer parser here would be a second set of overflow bugs.
// - **No `join`.** Concatenation is `common/fmt`'s `append_str` plus a separator byte; a
//   join that allocates is the exact thing this file exists to avoid.
