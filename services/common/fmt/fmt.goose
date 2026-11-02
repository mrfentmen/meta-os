// services/common/fmt/fmt.goose
//
// No-heap formatting into caller buffers, with the overflow answer the work
// order asks for: a full buffer returns a trailing false and never overflows.
//
// Status: WRITTEN (not COMPILED). Verified via goose-mcp@1.1.0:
// - growable builder `var b: u8[>..] = [];` and `.len` ....... samples/03_strings.goose
// - `append`, `push` ....................................... samples/03_strings.goose
// - `format_int(out, v, base, width, padc)` ................ stdlib#9
// - bounds checks ABORT on failure, they do not wrap ....... reference#82
// - trailing-bool convention ............................... samples/04_errors.goose
//
// WHY THIS LIBRARY EXISTS AT ALL, when Goose's std already has `format`
// ---------------------------------------------------------------------------
// Because `format` into a fixed buffer has no "it did not fit" answer: an index
// out of bounds aborts the program (reference#82). A log line that overflows
// would therefore kill the service that was trying to report a problem -- the
// worst possible failure mode for a log path.
//
// So every function here checks capacity BEFORE it writes and returns `false`
// if the write would not fit. Nothing is ever truncated silently and nothing
// ever aborts for a reason the caller could have handled.
//
// THE CAP RULE
// ------------
// Builders (`u8[>..]`) grow on the data stack; they have no built-in limit. The
// caller passes `cap`, the number of bytes it is willing to let this buffer
// reach, and every function here refuses to cross it. A caller that passes the
// size of the storage it actually has gets an honest `false` instead of a
// stack it has quietly wrecked. The `cap` is not a suggestion.

// ---------------------------------------------------------------------------
// Size helpers
// ---------------------------------------------------------------------------

// Digits needed for a value in a base, ignoring padding. Used to decide whether
// a write fits without writing first. Worst case for i64 is 20 bytes ("-9223..."
// is 20 characters including the sign) and 64 for base 2 of a u64.
import std;

fn digits_needed(v: i64, base: i64) -> i64 {
    if base < 2 || base > 36 { return 0; }      // caller error, handled by caller
    var n = v;
    var count = 1;
    if n < 0 {
        count = count + 1;
        // i64's most negative value has no positive counterpart; its magnitude
        // is one more than the largest positive, so it needs one extra digit.
        // Comparing first avoids an overflow abort on a legal input.
        if n == -9223372036854775807 - 1 { return 20; }
        n = -n;
    }
    while n >= base {
        n = n / base;
        count = count + 1;
    }
    return count;
}

// Remaining room in `out` under the caller's cap. Never negative.
fn room_left(out: u8[>..]&, cap: i64) -> i64 {
    let used = out.len;
    if used >= cap { return 0; }
    return cap - used;
}

// True when the buffer has reached its cap and nothing more can be added.
fn full(out: u8[>..]&, cap: i64) -> bool {
    return out.len >= cap;
}

// How many bytes are actually in the buffer. Callers use this instead of
// `out.len` so that the intent ("what has been written") is explicit.
fn used(out: u8[>..]&, cap: i64) -> i64 {
    if out.len > cap { return cap; }    // defensive: cap is read-only downstream
    return out.len;
}

// ---------------------------------------------------------------------------
// Appenders: every one returns false rather than writing past the cap
// ---------------------------------------------------------------------------

fn append_str(out: u8[>..]&, cap: i64, s: const u8[:]) -> bool {
    if s.len > room_left(out, cap) { return false; }
    out.append(s);
    return true;
}

fn append_char(out: u8[>..]&, cap: i64, c: u8) -> bool {
    if room_left(out, cap) < 1 { return false; }
    out.push(c);
    return true;
}

// Signed decimal, no padding.
fn append_int(out: u8[>..]&, cap: i64, v: i64) -> bool {
    let need = digits_needed(v, 10);
    if need > room_left(out, cap) { return false; }
    format_int(out, v, 10, 0, ' ');
    return true;
}

// Signed decimal, right-aligned in `width` characters, zero-padded.
fn append_int_pad(out: u8[>..]&, cap: i64, v: i64, width: i64, pad_ch: u8) -> bool {
    var need = digits_needed(v, 10);
    if width > need { need = width; }
    if need > room_left(out, cap) { return false; }
    format_int(out, v, 10, width, pad_ch);
    return true;
}

// Unsigned in any base 2..36, right-aligned, with a pad character. Hex is
// `append_uint(out, cap, v, 16, 4, '0')`; binary, octal and base 36 are the
// same call with a different second number, which is why there is no
// `append_hex` wrapper duplicating it.
fn append_uint(out: u8[>..]&, cap: i64, v: u64, base: i64, width: i64, pad_ch: u8) -> bool {
    if base < 2 || base > 36 { return false; }
    // Digits for a u64: 64 in base 2, 13 in base 36. Count properly rather than
    // assuming the worst case, so a cap near the edge is not refused for a
    // value that would have fitted.
    var n = v;
    var need: i64 = 1;
    let b = base as u64;
    while n >= b {
        n = n / b;
        need = need + 1;
    }
    if width > need { need = width; }
    if need > room_left(out, cap) { return false; }
    format_uint(out, v, base, width, pad_ch);
    return true;
}

fn append_bool(out: u8[>..]&, cap: i64, b: bool) -> bool {
    if b { return append_str(out, cap, "true"); }
    return append_str(out, cap, "false");
}

// A newline. Separate because it is the single most common append and the
// failure of a newline is worth seeing at the call site.
fn append_nl(out: u8[>..]&, cap: i64) -> bool {
    return append_char(out, cap, '\n');
}

// ---------------------------------------------------------------------------
// Terminating a record
// ---------------------------------------------------------------------------
//
// Services write bytes, not strings: there is no terminator on the wire and the
// kernel is told the length. This helper exists for the one place a terminator
// does matter -- a buffer handed to a C shim that expects a NUL -- and it
// reserves the byte rather than writing past the cap.
fn terminate(out: u8[>..]&, cap: i64) -> bool {
    if room_left(out, cap) < 1 { return false; }
    out.push(0);
    return true;
}

// ---------------------------------------------------------------------------
// What this library deliberately does NOT do
// ---------------------------------------------------------------------------
//
// - No float formatting. `format_flt` exists in std (samples/03_strings.goose)
//   but a kernel log line does not need decimals, and every float path is a
//   place the no-libc build could pull in soft-float code. If something needs
//   floats later it is added with its own test (B-L1-45), not smuggled in here.
// - No truncation. A caller that wants "the first N bytes" says so explicitly;
//   a library that silently truncates makes every log line a possible lie.
// - No allocation, ever: `out` is the caller's storage and `cap` is its limit.
