// services/settings/settings.goose
//
// Layer 5, face service 1: the desktop's settings store.
//
// WHAT THIS IS
// ------------
// A fixed table of typed settings — colour, mode, animation, wallpaper index,
// hostname — with three properties the desktop needs and a plain key/value map does
// not give:
//
//   1. **Validation at the write**, not at the read. A mode of 9 or a colour of
//      0x1ffffff is refused when it is set, so no consumer has to defend against a
//      value that could never have been written.
//   2. **A dirty count that means something.** Writing the value that is already
//      there is not a change and does not dirty the entry, so "unsaved" is accurate
//      and a save does not run for nothing.
//   3. **An atomic import.** A settings file that is corrupt in the middle applies
//      nothing, rather than half of it. Parsing happens into a staging copy; the live
//      table is replaced only after the whole blob validates.
//
// WHAT IT IS NOT
// --------------
// Not a general key/value store: the key set is closed and each key has a type and a
// range. A store that accepts any key at runtime cannot validate anything, because it
// does not know what a key means.
//
// Status: RUNS — reached by tests/t86_settings (exit 0). Measured 2026-11-02 by audit_status.py.

import common.err.err;

// ---------------------------------------------------------------------------
// Keys (closed set)

let SK_WALLPAPER: i64 = 1;      // index into the wallpaper registry
let SK_BG: i64 = 2;             // 0xRRGGBB
let SK_BAR: i64 = 3;            // 0xRRGGBB
let SK_MODE: i64 = 4;           // 1 = dark, 2 = light
let SK_ANIM: i64 = 5;           // 0 or 1
let SK_HOSTNAME: i64 = 6;       // text
let SK_MAX_ID: i64 = 6;

let KT_INT: i64 = 1;
let KT_TEXT: i64 = 2;

let SET_MAX: i64 = 24;          // entries; one per key plus room for named profiles
let SET_TEXT_MAX: i64 = 32;     // including the terminator slot
let SET_COLOR_MAX: i64 = 0xffffff;
let SET_WALLPAPER_MAX: i64 = 7;

let MODE_DARK: i64 = 1;
let MODE_LIGHT: i64 = 2;

struct Entry {
    id: i64,
    kind: i64,
    ival: i64,
    text: u8[..32] = [0; 32],
    text_len: i64,
    used: bool,
    dirty: bool,
}

var entries: Entry[..24] = [Entry { .. }; 24];
var entry_count: i64 = 0;
var g_inited: bool = false;

// ---------------------------------------------------------------------------
// Key metadata

fn st_kind(id: i64) -> i64 {
    if id == SK_WALLPAPER { return KT_INT; }
    if id == SK_BG { return KT_INT; }
    if id == SK_BAR { return KT_INT; }
    if id == SK_MODE { return KT_INT; }
    if id == SK_ANIM { return KT_INT; }
    if id == SK_HOSTNAME { return KT_TEXT; }
    return 0;
}

fn st_name(id: i64) -> const u8[:] {
    if id == SK_WALLPAPER { return "wallpaper"; }
    if id == SK_BG { return "background"; }
    if id == SK_BAR { return "bar"; }
    if id == SK_MODE { return "mode"; }
    if id == SK_ANIM { return "animation"; }
    if id == SK_HOSTNAME { return "hostname"; }
    return "";
}

// The range check, in one place. `ok` is the only way a value enters the table, so a
// caller cannot store a mode the compositor would have to interpret.
fn st_in_range(id: i64, v: i64) -> bool {
    if id == SK_WALLPAPER { return v >= 0 && v <= SET_WALLPAPER_MAX; }
    if id == SK_BG || id == SK_BAR { return v >= 0 && v <= SET_COLOR_MAX; }
    if id == SK_MODE { return v == MODE_DARK || v == MODE_LIGHT; }
    if id == SK_ANIM { return v == 0 || v == 1; }
    return false;
}

fn st_find(id: i64) -> i64 {
    var i: i64 = 0;
    while i < entry_count {
        if entries[i].id == id { return i; }
        i = i + 1;
    }
    return -1;
}

// ---------------------------------------------------------------------------
// Init and defaults

fn st_defaults() {
    let _ = st_put_int(SK_WALLPAPER, 0);
    let _ = st_put_int(SK_BG, 0x101820);
    let _ = st_put_int(SK_BAR, 0x202830);
    let _ = st_put_int(SK_MODE, MODE_DARK);
    let _ = st_put_int(SK_ANIM, 1);
    let _ = st_put_text(SK_HOSTNAME, "meta");
}

fn st_init() {
    var i: i64 = 0;
    while i < SET_MAX {
        entries[i].used = false;
        entries[i].dirty = false;
        entries[i].id = 0;
        entries[i].kind = 0;
        entries[i].ival = 0;
        entries[i].text_len = 0;
        var j: i64 = 0;
        while j < SET_TEXT_MAX { entries[i].text[j] = 0; j = j + 1; }
        i = i + 1;
    }
    entry_count = 0;
    g_inited = true;
    st_defaults();
    // Defaults are the starting state, not a change the user made.
    st_clear_dirty();
}

fn st_ensure() {
    if !g_inited { st_init(); }
}

fn st_put_int(id: i64, v: i64) -> i64 {
    if st_kind(id) != KT_INT { return E_INVAL; }
    if !st_in_range(id, v) { return E_INVAL; }
    let at = st_find(id);
    if at < 0 {
        if entry_count >= SET_MAX { return E_NO_SPACE; }
        let n = entry_count;
        entries[n].id = id;
        entries[n].kind = KT_INT;
        entries[n].ival = v;
        entries[n].text_len = 0;
        entries[n].used = true;
        entries[n].dirty = true;
        entry_count = entry_count + 1;
        return CODE_OK;
    }
    if entries[at].ival == v { return CODE_OK; }    // not a change, not dirty
    entries[at].ival = v;
    entries[at].dirty = true;
    return CODE_OK;
}

fn st_get_int(id: i64) -> i64, i64 {
    if st_kind(id) != KT_INT { return 0, E_INVAL; }
    let at = st_find(id);
    if at < 0 { return 0, E_NOTFOUND; }
    return entries[at].ival, CODE_OK;
}

fn st_put_text(id: i64, s: const u8[:]) -> i64 {
    if st_kind(id) != KT_TEXT { return E_INVAL; }
    if s.len == 0 { return E_INVAL; }
    if s.len >= SET_TEXT_MAX { return E_NOROOM; }
    var i: i64 = 0;
    while i < s.len {
        if s[i] < 32 || s[i] > 126 { return E_INVAL; }   // printable only
        i = i + 1;
    }
    // A hostname with a space is a hostname every consumer has to quote.
    if id == SK_HOSTNAME {
        i = 0;
        while i < s.len {
            if s[i] == 32 { return E_INVAL; }
            i = i + 1;
        }
    }
    let at = st_find(id);
    if at < 0 {
        if entry_count >= SET_MAX { return E_NO_SPACE; }
        let n = entry_count;
        entries[n].id = id;
        entries[n].kind = KT_TEXT;
        entries[n].ival = 0;
        entries[n].used = true;
        entries[n].dirty = true;
        entry_count = entry_count + 1;
        st_write_text(n, s);
        return CODE_OK;
    }
    if entries[at].text_len == s.len && st_text_eq(at, s) { return CODE_OK; }
    st_write_text(at, s);
    entries[at].dirty = true;
    return CODE_OK;
}

fn st_write_text(at: i64, s: const u8[:]) {
    var i: i64 = 0;
    while i < SET_TEXT_MAX { entries[at].text[i] = 0; i = i + 1; }
    i = 0;
    while i < s.len {
        entries[at].text[i] = s[i];
        i = i + 1;
    }
    entries[at].text_len = s.len;
}

fn st_text_eq(at: i64, s: const u8[:]) -> bool {
    var i: i64 = 0;
    while i < s.len {
        if entries[at].text[i] != s[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn st_get_text(id: i64) -> const u8[:], i64 {
    if st_kind(id) != KT_TEXT { return "", E_INVAL; }
    let at = st_find(id);
    if at < 0 { return "", E_NOTFOUND; }
    return entries[at].text[..entries[at].text_len], CODE_OK;
}

// ---------------------------------------------------------------------------
// Dirty tracking

fn st_dirty_count() -> i64 {
    var n: i64 = 0;
    var i: i64 = 0;
    while i < entry_count {
        if entries[i].dirty { n = n + 1; }
        i = i + 1;
    }
    return n;
}

fn st_clear_dirty() {
    var i: i64 = 0;
    while i < entry_count {
        entries[i].dirty = false;
        i = i + 1;
    }
}

fn st_count() -> i64 { return entry_count; }

// ---------------------------------------------------------------------------
// Persistence: "id=value\n" for ints, "id:text\n" for text, in key order.
//
// No key name, no quoting, no version: the key set is closed and the parser accepts
// only ids it knows, so a file written by a different build is refused rather than
// half-applied. A version byte is a promise to migrate, and there is nothing yet to
// migrate.

fn st_export(out: u8[..512]&) -> i64 {
    var n: i64 = 0;
    var id: i64 = 1;
    while id <= SK_MAX_ID {
        let at = st_find(id);
        if at >= 0 {
            n = n + st_emit_id(out, n, id);
            if entries[at].kind == KT_INT {
                n = n + st_emit_int(out, n, entries[at].ival);
            } else {
                var k: i64 = 0;
                while k < entries[at].text_len {
                    out[n] = entries[at].text[k];
                    n = n + 1;
                    k = k + 1;
                }
            }
            out[n] = 10;
            n = n + 1;
        }
        id = id + 1;
    }
    return n;
}

fn st_emit_id(out: u8[..512]&, n: i64, id: i64) -> i64 {
    out[n] = (48 + id) as u8;
    out[n + 1] = 61;                 // '='
    return 2;
}

fn st_emit_int(out: u8[..512]&, n: i64, v: i64) -> i64 {
    var tmp: u8[..24] = [0; 24];
    var k: i64 = 0;
    var x = v;
    if x == 0 {
        out[n] = 48;
        return 1;
    }
    while x > 0 {
        tmp[k] = (48 + (x % 10)) as u8;
        x = x / 10;
        k = k + 1;
    }
    var i: i64 = 0;
    while i < k {
        out[n + i] = tmp[k - 1 - i];
        i = i + 1;
    }
    return k;
}

fn st_parse_dec(s: const u8[:], from: i64, to: i64) -> i64, bool {
    if to <= from { return 0, false; }
    var v: i64 = 0;
    var i = from;
    while i < to {
        if s[i] < 48 || s[i] > 57 { return 0, false; }
        v = v * 10 + (s[i] - 48);
        i = i + 1;
    }
    return v, true;
}

// Import atomically: build a staged table from the current one, apply every line to
// the stage, and commit only if every line was valid. A corrupt file leaves the live
// settings exactly as they were.
fn st_import(data: const u8[:]) -> i64 {
    st_ensure();
    var staged: Entry[..24] = [Entry { .. }; 24];
    var i: i64 = 0;
    while i < entry_count {
        staged[i] = entries[i];
        i = i + 1;
    }
    var staged_count = entry_count;

    var pos: i64 = 0;
    var lines: i64 = 0;
    while pos < data.len {
        var end = pos;
        while end < data.len && data[end] != 10 { end = end + 1; }
        if end == pos { return E_CORRUPT; }                  // blank line
        let eq = st_find_char(data, pos, end, 61);
        if eq < 0 { return E_CORRUPT; }                      // no '='
        let idv, idok = st_parse_dec(data, pos, eq);
        if !idok { return E_CORRUPT; }
        if idv < 1 || idv > SK_MAX_ID { return E_CORRUPT; }  // unknown key: refuse the file
        let val_from = eq + 1;
        if val_from >= end { return E_CORRUPT; }             // empty value
        let kind = st_kind(idv);
        var at = st_stage_find(staged, staged_count, idv);

        if kind == KT_INT {
            let v, vok = st_parse_dec(data, val_from, end);
            if !vok { return E_CORRUPT; }
            if !st_in_range(idv, v) { return E_CORRUPT; }    // out of range: refuse
            if at < 0 {
                if staged_count >= SET_MAX { return E_NO_SPACE; }
                at = staged_count;
                staged[at].id = idv;
                staged[at].kind = KT_INT;
                staged[at].text_len = 0;
                staged[at].used = true;
                staged_count = staged_count + 1;
            }
            staged[at].ival = v;
            staged[at].dirty = false;
        } else {
            let tl = end - val_from;
            if tl >= SET_TEXT_MAX { return E_NOROOM; }
            var k: i64 = 0;
            while k < tl {
                if data[val_from + k] < 32 || data[val_from + k] > 126 { return E_CORRUPT; }
                k = k + 1;
            }
            if at < 0 {
                if staged_count >= SET_MAX { return E_NO_SPACE; }
                at = staged_count;
                staged[at].id = idv;
                staged[at].kind = KT_TEXT;
                staged[at].ival = 0;
                staged[at].used = true;
                staged_count = staged_count + 1;
            }
            var w: i64 = 0;
            while w < SET_TEXT_MAX { staged[at].text[w] = 0; w = w + 1; }
            k = 0;
            while k < tl {
                staged[at].text[k] = data[val_from + k];
                k = k + 1;
            }
            staged[at].text_len = tl;
            staged[at].dirty = false;
        }
        lines = lines + 1;
        pos = end + 1;
    }
    if lines == 0 { return E_CORRUPT; }                      // an empty file is not settings

    i = 0;
    while i < staged_count {
        entries[i] = staged[i];
        i = i + 1;
    }
    entry_count = staged_count;
    g_inited = true;
    return lines;
}

fn st_stage_find(staged: Entry[..24]&, count: i64, id: i64) -> i64 {
    var i: i64 = 0;
    while i < count {
        if staged[i].id == id { return i; }
        i = i + 1;
    }
    return -1;
}

fn st_find_char(data: const u8[:], from: i64, to: i64, ch: u8) -> i64 {
    var i = from;
    while i < to {
        if data[i] == ch { return i; }
        i = i + 1;
    }
    return -1;
}
