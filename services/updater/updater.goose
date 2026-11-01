// services/updater/updater.goose
//
// Layer 4, service 18: the updater. Manifest parsing (B-L1-34), verification and the
// apply plan (B-L1-35), and the rollback record (B-L1-36).
//
// Status: WRITTEN (not COMPILED). Verified via goose-mcp@1.1.0: structs with
// literals (reference#32), static arrays, `while`/`if`, slices, `T&` references
// (reference#46), `as` casts, multi-value returns.
//
// WHY A LINE FORMAT AND NOT JSON
// ------------------------------
// B-L1-120 builds a JSON subset and B-L1-122 the delta manifests. An updater that
// needed a parser nobody has written yet would be an updater that cannot be reviewed, so
// this one reads a format a person can read, diff and sign:
//
//     # meta-os update manifest v1
//     version = 0.2.0
//     origin  = https://updates.example.invalid/meta-os
//     slot    = b
//     file    = bin/console.c  9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08  18432
//
// The third field is the size. It is not redundant with the hash: a truncated download
// has a different hash AND a different size, and a size mismatch is the cheap check that
// tells a person "the transfer stopped" instead of "the bytes changed".
//
// WHAT PARSING REFUSES, AND WHY EACH ONE IS AN ATTACK OR AN ACCIDENT
// ------------------------------------------------------------------
// - **A key this build does not know** -> refused. Silently ignoring an unknown field is
//   how a signature field gets added in v2 and v1 clients keep installing unsigned
//   updates: they "ignore" the thing that would have protected them.
// - **A duplicate path** -> refused. Two entries for one file leave the installer to pick,
//   and an attacker who can add one line can then choose which one wins.
// - **More files than the table holds** -> refused, not truncated. A truncated manifest is
//   a partially updated system that claims success.
// - **A digest that is not 64 hex characters** -> refused. Short digests are how a
//   "verify" step gets downgraded to a prefix compare.
// - **A path containing `..`** -> refused. The manifest names files inside the update, not
//   places on the disk.

import common.err.err;

let MF_MAX_FILES: i64 = 8;
let MF_PATH_MAX: i64 = 32;
let MF_DIGEST_HEX: i64 = 64;
let MF_DIGEST_BYTES: i64 = 32;
let MF_ORIGIN_MAX: i64 = 64;
let MF_VERSION_MAX: i64 = 16;

let SLOT_A: i64 = 0;
let SLOT_B: i64 = 1;

struct ManifestFile {
    path: u8[..32],
    path_len: i64,
    digest: u8[..32],        // raw bytes: parsing hex once beats comparing hex strings
    digest_len: i64,
    size: i64,
}

struct Manifest {
    version: u8[..16],
    version_len: i64,
    origin: u8[..64],
    origin_len: i64,
    slot: i64,
    count: i64,
    files: ManifestFile[..8],
}

// ---------------------------------------------------------------------------
// Parsing
// ---------------------------------------------------------------------------

// Parse a whole manifest. Returns (manifest, code).
//
// A partial manifest is never returned as success: if any line is bad the whole document
// is refused, because an update installer that proceeds with the lines it understood is
// an installer that installs half an update and reports success.
fn upd_parse_manifest(text: u8[:]) -> Manifest, i64 {
    var m: Manifest;
    m.version_len = 0;
    m.origin_len = 0;
    m.slot = -1;
    m.count = 0;

    var pos: i64 = 0;
    while pos < text.len {
        // one line
        var end = pos;
        while end < text.len && text[end] != 0x0A { end++; }
        var s = pos;
        var e = end;
        // trim spaces and CR
        while s < e && (text[s] == 0x20 || text[s] == 0x09) { s++; }
        while e > s && (text[e - 1] == 0x20 || text[e - 1] == 0x09 || text[e - 1] == 0x0D) { e--; }
        pos = end + 1;

        if s == e { continue; }                  // blank line
        if text[s] == 0x23 { continue; }         // '#' comment

        let eq = find_byte(text, s, e, 0x3D);    // '='
        if eq < 0 { return m, E_BAD_MANIFEST; }
        var ks = s;
        var ke = eq;
        while ke > ks && (text[ke - 1] == 0x20 || text[ke - 1] == 0x09) { ke--; }
        var vs = eq + 1;
        while vs < e && (text[vs] == 0x20 || text[vs] == 0x09) { vs++; }

        if match_lit(text, ks, ke, "version") {
            let n = copy16(text, vs, e, m.version);
            if n <= 0 { return m, E_BAD_MANIFEST; }
            m.version_len = n;
        } else if match_lit(text, ks, ke, "origin") {
            let n = copy64(text, vs, e, m.origin);
            if n <= 0 { return m, E_BAD_MANIFEST; }
            m.origin_len = n;
        } else if match_lit(text, ks, ke, "slot") {
            if e - vs != 1 { return m, E_BAD_MANIFEST; }
            if text[vs] == 0x61 { m.slot = SLOT_A; }
            else if text[vs] == 0x62 { m.slot = SLOT_B; }
            else { return m, E_BAD_MANIFEST; }
        } else if match_lit(text, ks, ke, "file") {
            let code = parse_file_line(text, vs, e, m);
            if code != CODE_OK { return m, code; }
        } else {
            // Unknown key: refused, never ignored. See the header note.
            return m, E_BAD_MANIFEST;
        }
    }

    if m.version_len == 0 { return m, E_BAD_MANIFEST; }
    if m.slot < 0 { return m, E_BAD_MANIFEST; }
    if m.count == 0 { return m, E_BAD_MANIFEST; }
    return m, CODE_OK;
}

// `<path>  <64 hex>  <size>`
fn parse_file_line(text: u8[:], vs: i64, e: i64, m: Manifest&) -> i64 {
    if m.count >= MF_MAX_FILES { return E_BAD_MANIFEST; }

    var p = vs;
    while p < e && text[p] != 0x20 && text[p] != 0x09 { p++; }
    let path_len = p - vs;
    if path_len <= 0 || path_len >= MF_PATH_MAX { return E_BAD_MANIFEST; }
    if has_dotdot(text, vs, p) { return E_BAD_MANIFEST; }   // escapes the update root

    while p < e && (text[p] == 0x20 || text[p] == 0x09) { p++; }
    let hex_start = p;
    while p < e && text[p] != 0x20 && text[p] != 0x09 { p++; }
    if p - hex_start != MF_DIGEST_HEX { return E_BAD_MANIFEST; }
    let hex_end = p;

    while p < e && (text[p] == 0x20 || text[p] == 0x09) { p++; }
    var size: i64 = 0;
    var digits: i64 = 0;
    while p < e {
        if text[p] < 0x30 || text[p] > 0x39 { return E_BAD_MANIFEST; }
        size = size * 10 + ((text[p] - 0x30) as i64);
        if size < 0 { return E_BAD_MANIFEST; }             // overflow
        digits++;
        p++;
    }
    if digits == 0 || digits > 12 { return E_BAD_MANIFEST; }

    let slot = m.count;
    var i: i64 = 0;
    while i < path_len {
        m.files[slot].path[i] = text[vs + i];
        i++;
    }
    m.files[slot].path_len = path_len;

    // Hex to bytes. A digest kept as text would be compared with a text compare, and the
    // first implementation of that gets prefixes wrong.
    var d: i64 = 0;
    while d < MF_DIGEST_BYTES {
        let hi = hex_val(text[hex_start + d * 2]);
        let lo = hex_val(text[hex_start + d * 2 + 1]);
        if hi < 0 || lo < 0 { return E_BAD_MANIFEST; }
        m.files[slot].digest[d] = ((hi * 16) + lo) as u8;
        d++;
    }
    m.files[slot].digest_len = MF_DIGEST_BYTES;
    m.files[slot].size = size;

    // Duplicate paths refused: two entries for one file let an attacker who can add a line
    // choose which one the installer believes.
    var j: i64 = 0;
    while j < slot {
        if paths_equal(m.files[j].path, m.files[j].path_len, m.files[slot].path, m.files[slot].path_len) {
            return E_BAD_MANIFEST;
        }
        j++;
    }

    m.count++;
    return CODE_OK;
}

fn paths_equal(a: u8[..32]&, alen: i64, b: u8[..32]&, blen: i64) -> bool {
    if alen != blen { return false; }
    var i: i64 = 0;
    while i < alen {
        if a[i] != b[i] { return false; }
        i++;
    }
    return true;
}

fn has_dotdot(text: u8[:], s: i64, e: i64) -> bool {
    var i = s;
    while i + 1 < e {
        if text[i] == 0x2E && text[i + 1] == 0x2E { return true; }
        i++;
    }
    return false;
}

fn find_byte(text: u8[:], s: i64, e: i64, b: u8) -> i64 {
    var i = s;
    while i < e {
        if text[i] == b { return i; }
        i++;
    }
    return -1;
}

fn hex_val(c: u8) -> i64 {
    if c >= 0x30 && c <= 0x39 { return (c - 0x30) as i64; }
    if c >= 0x61 && c <= 0x66 { return ((c - 0x61) + 10) as i64; }   // a-f
    if c >= 0x41 && c <= 0x46 { return ((c - 0x41) + 10) as i64; }   // A-F
    return -1;
}

// Two functions rather than one generic: `u8[..16]` and `u8[..64]` are different types,
// and a single parameter would have to be one of them. Generic functions are not among the
// forms this lane has verified, so the duplication is the honest choice.
fn copy16(text: u8[:], s: i64, e: i64, dst: u8[..16]&) -> i64 {
    let n = e - s;
    if n <= 0 || n >= MF_VERSION_MAX { return -1; }
    var i: i64 = 0;
    while i < n {
        dst[i] = text[s + i];
        i++;
    }
    return n;
}

fn copy64(text: u8[:], s: i64, e: i64, dst: u8[..64]&) -> i64 {
    let n = e - s;
    if n <= 0 || n >= MF_ORIGIN_MAX { return -1; }
    var i: i64 = 0;
    while i < n {
        dst[i] = text[s + i];
        i++;
    }
    return n;
}

fn match_lit(text: u8[:], s: i64, e: i64, lit: const u8[:]) -> bool {
    if e - s != lit.len { return false; }
    var i: i64 = 0;
    while i < lit.len {
        if text[s + i] != lit[i] { return false; }
        i++;
    }
    return true;
}
