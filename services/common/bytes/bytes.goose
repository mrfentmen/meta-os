// services/common/bytes/bytes.goose
//
// B-L1-68 — gap library 1. Byte-array helpers over `u8[:]`, which `std` does not
// provide: `std`'s string functions (`find`, `split`, `trim`) are for Goose `string`,
// and every service here passes byte slices around because a record is bytes.
//
// Status: RUNS — reached by tests/t67_net (89 checks, exit 0). Measured 2026-11-02 by audit_status.py.
//
// WHY THIS EXISTS AT ALL
// ----------------------
// STDLIB_GAPS.md's audit order puts six kernel-boundary gaps first; those were closed by
// B-L1-09 (`common/sys`) before this task started. In audit order the first three gaps
// still without an owner were byte operations, span splitting and shifts, and hex. This is
// the first of them, and it is the one every parser in Wave K leans on.
//
// WHAT IT PROMISES
// ----------------
// - No allocation. Every function takes slices of storage the caller already owns.
// - No aborting on a caller's input. A search that finds nothing returns -1; a copy that
//   had less room than source returns what it copied. The only thing that aborts is an
//   out-of-bounds index handed to a function that documents it as a caller bug.
// - Deterministic results. Nothing here reads a clock, a random source or a global.
//
// WHY `by_find` TAKES A START OFFSET
// ----------------------------------
// A parser scanning a buffer needs to resume where it stopped. `find(hay, needle)` alone
// forces the caller to re-slice on every hit, and re-slicing is where an off-by-one turns
// into an infinite loop (needle found at 0 of the new slice, forever). `from` makes the
// progress explicit and testable.

// ---------------------------------------------------------------------------
// Comparison
// ---------------------------------------------------------------------------

fn by_eq(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

// Lexicographic: -1 when a < b, 0 when equal, 1 when a > b. Byte order, not locale.
// Signed compare on bytes is intentional: a record sorter that flips sign at 0x80 is a
// sorter whose output depends on which half of the alphabet the data came from.
fn by_cmp(a: const u8[:], b: const u8[:]) -> i64 {
    var n = a.len;
    if b.len < n { n = b.len; }
    var i: i64 = 0;
    while i < n {
        if a[i] < b[i] { return -1; }
        if a[i] > b[i] { return 1; }
        i = i + 1;
    }
    if a.len < b.len { return -1; }
    if a.len > b.len { return 1; }
    return 0;
}

// Case-insensitive equality for ASCII only. Used for config keywords and header names;
// never for a password or a path, where folding case is how two different names become one.
fn by_eq_ci(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if lower_ascii(a[i]) != lower_ascii(b[i]) { return false; }
        i = i + 1;
    }
    return true;
}

fn lower_ascii(c: u8) -> u8 {
    if c >= 'A' && c <= 'Z' { return c + 32; }
    return c;
}

fn upper_ascii(c: u8) -> u8 {
    if c >= 'a' && c <= 'z' { return c - 32; }
    return c;
}

// ---------------------------------------------------------------------------
// Copy and fill
// ---------------------------------------------------------------------------

// Copy as much of `src` as fits in `dst`, never past `dst.len`. Returns the count copied,
// which is `src.len` on success and something smaller when the destination is short.
// The caller is expected to compare the return value to `src.len` when truncation matters
// -- a copy that reports 12 of 40 bytes and is not checked is how a record loses its tail.
fn by_copy(dst: u8[>..]&, cap: i64, src: const u8[:]) -> i64 {
    var i: i64 = 0;
    while i < src.len && dst.len < cap {
        dst.push(src[i]);
        i = i + 1;
    }
    return i;
}

// Append `n` copies of `v`, stopping at `cap`. Returns how many were appended.
fn by_fill(dst: u8[>..]&, cap: i64, v: u8, n: i64) -> i64 {
    var i: i64 = 0;
    while i < n && dst.len < cap {
        dst.push(v);
        i = i + 1;
    }
    return i;
}

// Zero a fixed span in place. Separate from `by_fill` because clearing a table slot is a
// different intent from filling a buffer, and the two are read differently at 3am.
fn by_clear(dst: u8[>..]&) {
    var i: i64 = 0;
    while i < dst.len {
        dst[i] = 0;
        i = i + 1;
    }
}

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

// First index of `needle` at or after `from`, or -1. An empty needle returns `from` when
// `from` is in range -- which is the only answer that keeps a loop using the result from
// spinning forever: an empty match advances by zero, so a caller that passes a zero-length
// needle and ignores the no-progress rule has a bug, not a library problem.
fn by_find(hay: const u8[:], needle: const u8[:], from_in: i64) -> i64 {
    var from = from_in;
    if from < 0 { from = 0; }
    if needle.len == 0 { if from <= hay.len { return from; } return -1; }
    if needle.len > hay.len { return -1; }
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

fn by_find_byte(hay: const u8[:], b: u8, from_in: i64) -> i64 {
    var from = from_in;
    if from < 0 { from = 0; }
    var i = from;
    while i < hay.len {
        if hay[i] == b { return i; }
        i = i + 1;
    }
    return -1;
}

fn by_rfind_byte(hay: const u8[:], b: u8) -> i64 {
    var i = hay.len - 1;
    while i >= 0 {
        if hay[i] == b { return i; }
        i = i - 1;
    }
    return -1;
}

fn by_count_byte(hay: const u8[:], b: u8) -> i64 {
    var n: i64 = 0;
    var i: i64 = 0;
    while i < hay.len {
        if hay[i] == b { n = n + 1; }
        i = i + 1;
    }
    return n;
}

fn by_starts_with(hay: const u8[:], prefix: const u8[:]) -> bool {
    if prefix.len > hay.len { return false; }
    var i: i64 = 0;
    while i < prefix.len {
        if hay[i] != prefix[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn by_ends_with(hay: const u8[:], suffix: const u8[:]) -> bool {
    if suffix.len > hay.len { return false; }
    var start = hay.len - suffix.len;
    var i: i64 = 0;
    while i < suffix.len {
        if hay[start + i] != suffix[i] { return false; }
        i = i + 1;
    }
    return true;
}

// ---------------------------------------------------------------------------
// Trimming (as spans, not copies)
// ---------------------------------------------------------------------------

// Returns (start, end) of the content with ASCII whitespace removed at both ends.
// A span rather than a copy: the config parser and the shell both trim on the way in and
// then want the original bytes for an error message, so nothing is thrown away.
fn by_trim_span(s: const u8[:]) -> i64, i64 {
    var start: i64 = 0;
    var end = s.len;
    while start < end && is_space_byte(s[start]) { start = start + 1; }
    while end > start && is_space_byte(s[end - 1]) { end = end - 1; }
    return start, end;
}

fn is_space_byte(c: u8) -> bool {
    return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == 0x0b || c == 0x0c;
}

fn is_digit_byte(c: u8) -> bool {
    return c >= '0' && c <= '9';
}

fn is_hex_byte(c: u8) -> bool {
    if c >= '0' && c <= '9' { return true; }
    if c >= 'a' && c <= 'f' { return true; }
    if c >= 'A' && c <= 'F' { return true; }
    return false;
}

fn hex_value(c: u8) -> i64 {
    if c >= '0' && c <= '9' { return c - '0'; }
    if c >= 'a' && c <= 'f' { return c - 'a' + 10; }
    if c >= 'A' && c <= 'F' { return c - 'A' + 10; }
    return -1;
}

// ---------------------------------------------------------------------------
// Whole-buffer predicates
// ---------------------------------------------------------------------------

fn by_is_blank(s: const u8[:]) -> bool {
    var i: i64 = 0;
    while i < s.len {
        if !is_space_byte(s[i]) { return false; }
        i = i + 1;
    }
    return true;
}

fn by_all_digits(s: const u8[:]) -> bool {
    if s.len == 0 { return false; }
    var i: i64 = 0;
    while i < s.len {
        if !is_digit_byte(s[i]) { return false; }
        i = i + 1;
    }
    return true;
}

fn by_all_hex(s: const u8[:]) -> bool {
    if s.len == 0 { return false; }
    var i: i64 = 0;
    while i < s.len {
        if !is_hex_byte(s[i]) { return false; }
        i = i + 1;
    }
    return true;
}

// ---------------------------------------------------------------------------
// What this library deliberately does NOT do
// ---------------------------------------------------------------------------
//
// - **No reallocation.** A growable `u8[>..]` that needs to grow inside a helper is a
//   helper that can exhaust a fixed arena at a call site nobody inspected. Growth is the
//   caller's decision, made once, at the top.
// - **No case folding beyond ASCII.** `by_eq_ci` is for keywords. Unicode folding is a
//   table this layer does not carry, and a half-done version is worse than a refusal.
// - **No `memmove` semantics.** `by_copy` appends to a destination that does not overlap
//   the source. Overlapping copies are not needed by any service here; if one appears, it
//   gets its own function with its own test rather than a flag on this one.
// - **No sorting.** `std.sort` exists (verified by name in STDLIB_GAPS.md); this library
//   only supplies the comparator a caller would hand it.
// - **No hash.** `common/hash` owns CRC32 and SHA-256; a second, weaker hash here would
//   just be the one somebody reaches for by accident.
