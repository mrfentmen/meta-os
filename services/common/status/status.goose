// services/common/status/status.goose
//
// BF4-09 — one status shape across the whole OS.
//
// THE SHAPE, AND WHERE IT COMES FROM
// ----------------------------------
// The kernel already prints, on every `status` command:
//
//     STATUS tasks=7 ticks=380 heap_free_kb=31
//
// Pax ruled (F2) that for the STATUS line the shape the kernel prints wins, and Hana
// reconciles the exact strings in shell-spec.md. This module is that shape for the
// services side: a `KEY=value` run, space separated, one line, no prose. The reader is
// a program first -- the shell's status command, the supervisor's health poll, and the
// agent's structured view all parse the same bytes -- so the format is fixed rather
// than pretty.
//
// A service line is:
//
//     SERVICE <name> state=<STATE> ticks=<n> <key>=<value>...
//
// `name` is the service's directory name, `state` is the supervisor's state number
// (the ST_* constants, which the supervisor owns), and `ticks` is the service's clock
// reading at the moment it built the line. Everything after that is the service's own
// facts, and the keys are the service's to choose -- what is fixed is `KEY=value`, one
// space between fields, one newline at the end, no field containing a space.
//
// WHY NOT A STRUCT WITH A FORMAT METHOD
// -------------------------------------
// The layer has no allocator and no formatted printing that can be shared without
// pulling in the whole format library, so the caller passes its buffer and capacity,
// exactly as the ring and format libraries do. Each call appends; the buffer is the
// caller's, and it is never written past `cap`.
//
// WHAT THIS DOES NOT DO
// ---------------------
// It does not gather the facts. A service that reports `state=1` without checking its
// own state is a status line that lies, and no formatter can prevent that -- which is
// why every service that uses this reads its numbers from the same variables its
// behaviour uses, not from constants.

import common.fmt.fmt;

let ST_OK_MARK: u8 = 61;        // '='
let ST_SPACE: u8 = 32;

// A key that contains '=', ' ' or newline makes the line unparseable, so it is checked
// BEFORE anything is written. The refusal must leave the buffer exactly as it was: a
// half-written field is a record the caller will ship because it did not check.
fn key_ok(key: const u8[:]) -> bool {
    if key.len == 0 { return false; }
    var i: i64 = 0;
    while i < key.len {
        let c = key[i];
        if c == 61 || c == 32 || c == 10 { return false; }
        i = i + 1;
    }
    return true;
}

// `SERVICE <name>` -- the prefix every line starts with, written by this function so
// that `status_name` and every service agree on it. A name with a space in it would
// break `status_name`, so it is refused here rather than discovered by a reader.
fn status_open(out: u8[>..]&, cap: i64, name: const u8[:]) -> bool {
    if name.len == 0 { return false; }
    if !key_ok(name) { return false; }   // validated before the prefix is written
    let prefix: const u8[:] = "SERVICE ";
    var i: i64 = 0;
    while i < prefix.len {
        if !append_char(out, cap, prefix[i]) { return false; }
        i = i + 1;
    }
    return append_str(out, cap, name);
}

// ` <key>=<value>`: one field, with its leading space. The space is written here so a
// caller cannot forget it and produce a line whose fields run together.
//
// A key containing '=' or ' ' would make the line unparseable, so it is refused rather
// than written: a status line that only sometimes parses is worse than a short one.
// A refusal after the leading space has been written leaves one extra byte in the
// buffer; the caller sees `false` and must discard the line, not pad it.
// ` <key>=<value>`, all or nothing.
//
// The size is computed first and the whole field is refused if it will not fit, because
// append_str writes what it can before returning false: without this check a short cap
// leaves half a field in the buffer, and a caller that (correctly) discards a false result
// is still left with a record it has to reset. One field, one decision.
fn status_field(out: u8[>..]&, cap: i64, key: const u8[:], v: i64) -> bool {
    if !key_ok(key) { return false; }
    let need = 1 + key.len + 1 + digits_needed(v, 10);
    if need > room_left(out, cap) { return false; }
    if !append_char(out, cap, ST_SPACE) { return false; }
    if !append_str(out, cap, key) { return false; }
    if !append_char(out, cap, ST_OK_MARK) { return false; }
    return append_int(out, cap, v);
}

// A field whose value is a word rather than a number (`mode=idle`). Same refusal rule:
// the value may not contain a space, because the space is the separator.
fn status_field_word(out: u8[>..]&, cap: i64, key: const u8[:], word: const u8[:]) -> bool {
    if !key_ok(key) || !key_ok(word) { return false; }
    let need = 1 + key.len + 1 + word.len;
    if need > room_left(out, cap) { return false; }
    if !append_char(out, cap, ST_SPACE) { return false; }
    if !append_str(out, cap, key) { return false; }
    if !append_char(out, cap, ST_OK_MARK) { return false; }
    return append_str(out, cap, word);
}

fn status_end(out: u8[>..]&, cap: i64) -> bool {
    return append_nl(out, cap);
}

// ---------------------------------------------------------------------------
// Reading it back, for the shell and for the tests
// ---------------------------------------------------------------------------

// The number behind `key=` in a status line, or (0, false) when the key is absent or
// its value is not a number. A linear scan: the line is one screen wide.
fn status_get(line: const u8[:], key: const u8[:]) -> i64, bool {
    if key.len == 0 { return 0, false; }
    var i: i64 = 0;
    while i + key.len + 1 <= line.len {
        var hit = true;
        var k: i64 = 0;
        while k < key.len {
            if line[i + k] != key[k] { hit = false; break; }
            k = k + 1;
        }
        // The key must start a field: at the beginning, or after a space.
        if hit && i > 0 && line[i - 1] != 32 { hit = false; }
        if hit && line[i + key.len] == ST_OK_MARK {
            var p = i + key.len + 1;
            var neg = false;
            if p < line.len && line[p] == 45 { neg = true; p = p + 1; }   // '-'
            var v: i64 = 0;
            var digits: i64 = 0;
            while p < line.len {
                let c = line[p];
                if c < 48 || c > 57 { break; }
                v = v * 10 + (c - 48);
                digits = digits + 1;
                p = p + 1;
            }
            if digits == 0 { return 0, false; }
            if neg { v = 0 - v; }
            return v, true;
        }
        i = i + 1;
    }
    return 0, false;
}

// The first field's key after `SERVICE <name>`, so a reader can check which service a
// line belongs to without knowing its field order.
fn status_name(line: const u8[:]) -> const u8[:] {
    let prefix: const u8[:] = "SERVICE ";
    if line.len <= prefix.len { return line[0..0]; }
    var i: i64 = 0;
    while i < prefix.len {
        if line[i] != prefix[i] { return line[0..0]; }
        i = i + 1;
    }
    var start = prefix.len;
    var end = start;
    while end < line.len && line[end] != 32 { end = end + 1; }
    return line[start..end];
}
