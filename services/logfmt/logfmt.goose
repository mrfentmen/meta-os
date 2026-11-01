// services/logfmt/logfmt.goose
//
// Layer 4, service 12: the record shape every service emits through.
//
// Status: WRITTEN (not COMPILED). Verified via goose-mcp@1.1.0: structs with
// literals (reference#32), static arrays, `while`/`if`, slices `a[x..y]`, `T&`
// references (reference#46), multi-value returns.
//
// WHY A SHARED FORMAT AND NOT "JUST PRINT"
// ----------------------------------------
// Three services that each print their own idea of a log line produce three formats,
// and the tool that reads them has to know all three. Worse: when a service formats
// its own line, the timestamp and the level are typed by the caller -- so a warning
// logged by a helper becomes an error, and a line written after a 2-second sleep
// carries the time of the call, not of the event.
//
// So the record is a struct, one function fills in time and level, one function
// renders it, and one function parses it back. Everything else in the layer logs by
// calling `logfmt_emit`.
//
// THE LINE FORMAT
// ---------------
//
//     0042.300 W cons  console: 80x25 ready
//     ^^^^^^^^^ ^ ^^^^^  ^^^^^^^^^^^^^^^^^^
//     seconds   | tag    message
//               level
//
// Fixed-width uptime to the millisecond, a single-letter level, a 5-char tag. Fixed
// width is what makes a log greppable and sortable without a parser, and it is what
// makes the raster in a terminal line up. A JSON log line is better for machines and
// worse for the person reading a boot failure at 3am; the audit service (B-L1-41) is
// where machine-shaped records go.
//
// Milliseconds are seconds + ms rather than a bare millisecond count: `0042.300` is
// readable as "42 seconds in", where `42300` needs dividing in your head.

import common.err.err;

// ---------------------------------------------------------------------------
// Levels
// ---------------------------------------------------------------------------
//
// Five, and the letters are single characters so the column stays narrow. DEBUG is a
// letter and not a word because the common case -- a frame of a noisy subsystem --
// should not cost four extra bytes per line in a 64 KiB ring.

let LV_DEBUG: i64 = 0;
let LV_INFO: i64 = 1;
let LV_WARN: i64 = 2;
let LV_ERROR: i64 = 3;
let LV_FATAL: i64 = 4;

fn logfmt_level_letter(level: i64) -> u8 {
    if level == LV_DEBUG { return 0x44; }   // D
    if level == LV_INFO { return 0x49; }    // I
    if level == LV_WARN { return 0x57; }    // W
    if level == LV_ERROR { return 0x45; }   // E
    if level == LV_FATAL { return 0x46; }   // F
    return 0x3F;                            // '?' -- an unknown level is visible, not silent
}

fn logfmt_level_of(letter: u8) -> i64 {
    if letter == 0x44 { return LV_DEBUG; }
    if letter == 0x49 { return LV_INFO; }
    if letter == 0x57 { return LV_WARN; }
    if letter == 0x45 { return LV_ERROR; }
    if letter == 0x46 { return LV_FATAL; }
    return -1;
}

fn logfmt_level_name(level: i64) -> const u8[:] {
    if level == LV_DEBUG { return "debug"; }
    if level == LV_INFO { return "info"; }
    if level == LV_WARN { return "warn"; }
    if level == LV_ERROR { return "error"; }
    if level == LV_FATAL { return "fatal"; }
    return "unknown";
}

// ---------------------------------------------------------------------------
// The record
// ---------------------------------------------------------------------------

let TAG_MAX: i64 = 8;
let MSG_MAX: i64 = 160;
let LINE_MAX: i64 = 200;

struct Record {
    uptime_ms: i64,         // from the time service (B-L1-19), not from the caller
    level: i64,
    tag: u8[..8],           // who: the service's short name, NUL padded
    tag_len: i64,
    msg: u8[..160],
    msg_len: i64,
}

// Build a record. Uptime comes in as a parameter, but the caller is expected to pass
// the clock's value at the moment of the event; there is no separate "stamp it later"
// path, because a timestamp added later is the bug this format exists to prevent.
//
// A message longer than MSG_MAX is TRUNCATED and marked, not refused: dropping a log
// line because it is verbose loses the information entirely, while a truncated line
// still says what happened. The `...` marker is the difference between "the message
// ended" and "the message was cut".
fn logfmt_make(level: i64, tag: const u8[:], msg: const u8[:], uptime_ms: i64) -> Record {
    var r: Record;
    r.uptime_ms = uptime_ms;
    if level < LV_DEBUG { level = LV_DEBUG; }
    if level > LV_FATAL { level = LV_FATAL; }
    r.level = level;

    var t: i64 = 0;
    while t < tag.len && t < TAG_MAX - 1 {
        r.tag[t] = tag[t];
        t++;
    }
    r.tag[t] = 0;
    r.tag_len = t;

    var m: i64 = 0;
    var truncated = false;
    while m < msg.len {
        if m >= MSG_MAX - 3 { truncated = true; break; }
        r.msg[m] = msg[m];
        m++;
    }
    if truncated {
        r.msg[m] = 0x2E;      // .
        r.msg[m + 1] = 0x2E;
        r.msg[m + 2] = 0x2E;
        r.msg_len = m + 3;
    } else {
        r.msg_len = m;
    }
    return r;
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

// Render into a caller buffer. Returns bytes written, or -1 when the buffer cannot
// hold the line -- a partially rendered log line is worse than a dropped one, because
// it reads as a complete line with the end missing.
//
// Layout: `SSSS.mmm L TTTTT msg`, then a newline. Uptime seconds are zero-padded to
// four digits so the column holds for the first 2.7 hours; beyond that the field
// grows and the columns shift, which is the correct trade: an uptime of 10000 s should
// not be truncated to fit a column.
fn logfmt_render(r: Record&, out: u8[..200]&) -> i64 {
    var secs = r.uptime_ms / 1000;
    var ms = r.uptime_ms % 1000;
    if ms < 0 { ms = 0; }
    if secs < 0 { secs = 0; }

    var n: i64 = 0;
    if n + 6 > LINE_MAX { return -1; }
    // Four-digit field: pad the seconds with leading zeros while they fit in it, so
    // the level column does not move for the first 2.7 hours. Past 10000 s the field
    // grows and the columns shift, which is the right trade -- an uptime should not be
    // truncated to keep a column.
    if secs < 10 { out[n] = 0x30; n++; }
    if secs < 100 { out[n] = 0x30; n++; }
    if secs < 1000 { out[n] = 0x30; n++; }
    n = logfmt_put_int(out, n, secs);
    if n < 0 { return -1; }

    if n < LINE_MAX { out[n] = 0x2E; n++; } else { return -1; }   // .
    // milliseconds, always three digits
    var d100 = ms / 100;
    var d10 = (ms % 100) / 10;
    var d1 = ms % 10;
    if n + 3 > LINE_MAX { return -1; }
    out[n] = 0x30 + (d100 as u8); n++;
    out[n] = 0x30 + (d10 as u8); n++;
    out[n] = 0x30 + (d1 as u8); n++;

    if n < LINE_MAX { out[n] = 0x20; n++; } else { return -1; }
    out[n] = logfmt_level_letter(r.level); n++;
    if n < LINE_MAX { out[n] = 0x20; n++; } else { return -1; }

    var t: i64 = 0;
    while t < r.tag_len {
        if n >= LINE_MAX { return -1; }
        out[n] = r.tag[t];
        n++;
        t++;
    }
    while t < TAG_MAX - 1 {                     // pad the tag column
        if n >= LINE_MAX { return -1; }
        out[n] = 0x20;
        n++;
        t++;
    }

    if n < LINE_MAX { out[n] = 0x20; n++; } else { return -1; }
    var m: i64 = 0;
    while m < r.msg_len {
        if n >= LINE_MAX { return -1; }
        out[n] = r.msg[m];
        n++;
        m++;
    }
    if n >= LINE_MAX { return -1; }
    out[n] = 0x0A;
    n++;
    return n;
}

// Decimal, no padding. Returns the new length, or -1 when full.
fn logfmt_put_int(out: u8[..200]&, at: i64, v: i64) -> i64 {
    if v == 0 {
        if at >= LINE_MAX { return -1; }
        out[at] = 0x30;
        return at + 1;
    }
    // Digits are produced least-significant first into a scratch buffer, then copied
    // in order: writing them straight out would print the number backwards.
    var scratch: u8[..24];
    var n: i64 = 0;
    var x = v;
    while x > 0 && n < 23 {
        scratch[n] = 0x30 + ((x % 10) as u8);
        x = x / 10;
        n++;
    }
    var i = n - 1;
    while i >= 0 {
        if at >= LINE_MAX { return -1; }
        out[at] = scratch[i];
        at++;
        i--;
    }
    return at;
}

// ---------------------------------------------------------------------------
// Parsing back
// ---------------------------------------------------------------------------
//
// The reader (B-L1-108 export, B-L1-118 auditing) needs the record, not the line. One
// parser here, so the format has exactly one definition of "what a line means".
//
// Returns (record, ok). A malformed line is ok = false and fills nothing: a parser
// that guessed at a damaged line would put invented data into an audit trail.
fn logfmt_parse(line: const u8[:], out: Record&) -> bool {
    // Minimum: `0.000 I t msg\n`.
    if line.len < 10 { return false; }
    var i: i64 = 0;

    // seconds
    var secs: i64 = 0;
    var digits: i64 = 0;
    while i < line.len && line[i] >= 0x30 && line[i] <= 0x39 {
        secs = secs * 10 + ((line[i] - 0x30) as i64);
        i++;
        digits++;
    }
    if digits == 0 || digits > 9 { return false; }
    if i >= line.len || line[i] != 0x2E { return false; }
    i++;

    // milliseconds: exactly three
    if i + 3 > line.len { return false; }
    var ms: i64 = 0;
    var k: i64 = 0;
    while k < 3 {
        if line[i] < 0x30 || line[i] > 0x39 { return false; }
        ms = ms * 10 + ((line[i] - 0x30) as i64);
        i++;
        k++;
    }
    if ms > 999 { return false; }

    if i >= line.len || line[i] != 0x20 { return false; }
    i++;
    if i >= line.len { return false; }
    let level = logfmt_level_of(line[i]);
    if level < 0 { return false; }
    i++;
    if i >= line.len || line[i] != 0x20 { return false; }
    i++;

    // tag: up to TAG_MAX-1 non-space bytes
    var t: i64 = 0;
    while i < line.len && line[i] != 0x20 {
        if t >= TAG_MAX - 1 { return false; }
        out.tag[t] = line[i];
        t++;
        i++;
    }
    out.tag[t] = 0;
    out.tag_len = t;
    if i >= line.len || line[i] != 0x20 { return false; }
    i++;

    // message: to newline or end
    var m: i64 = 0;
    while i < line.len && line[i] != 0x0A {
        if m >= MSG_MAX { return false; }
        out.msg[m] = line[i];
        m++;
        i++;
    }
    out.msg_len = m;
    out.uptime_ms = secs * 1000 + ms;
    out.level = level;
    return true;
}
