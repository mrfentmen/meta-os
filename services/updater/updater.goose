// services/updater/updater.goose
//
// Layer 4, service 18: the updater. Manifest parsing (B-L1-34), verification and the
// apply plan (B-L1-35), and the rollback record (B-L1-36).
//
// Status: RUNS — reached by tests/t58_updater (35 checks, exit 0). Measured 2026-11-02 by audit_status.py. Verified via goose-mcp@1.1.0: structs with
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
import common.hash.hash;   // sha256 + equal_constant_time for verification (B-L1-35)

let MF_MAX_FILES: i64 = 8;
let MF_PATH_MAX: i64 = 32;
let MF_DIGEST_HEX: i64 = 64;
let MF_DIGEST_BYTES: i64 = 32;
let MF_ORIGIN_MAX: i64 = 64;
let MF_VERSION_MAX: i64 = 16;

let SLOT_A: i64 = 0;
let SLOT_B: i64 = 1;

struct ManifestFile {
    path: u8[..32] = [0; 32],
    path_len: i64,
    digest: u8[..32] = [0; 32],        // raw bytes: parsing hex once beats comparing hex strings
    digest_len: i64,
    size: i64,
}

struct Manifest {
    version: u8[..16] = [0; 16],
    version_len: i64,
    origin: u8[..64] = [0; 64],
    origin_len: i64,
    slot: i64,
    count: i64,
    files: ManifestFile[..8] = [ManifestFile { .. }; 8],
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
    var m: Manifest = Manifest {
        version: [0; 16],
        version_len: 0,
        origin: [0; 64],
        origin_len: 0,
        slot: 0,
        count: 0,
        files: [ManifestFile { .. }; 8],
    };
    m.version_len = 0;
    m.origin_len = 0;
    m.slot = -1;
    m.count = 0;

    var pos: i64 = 0;
    while pos < text.len {
        // one line
        var end = pos;
        while end < text.len && text[end] != 0x0A { end = end + 1; }
        var s = pos;
        var e = end;
        // trim spaces and CR
        while s < e && (text[s] == 0x20 || text[s] == 0x09) { s = s + 1; }
        while e > s && (text[e - 1] == 0x20 || text[e - 1] == 0x09 || text[e - 1] == 0x0D) { e = e - 1; }
        pos = end + 1;

        if s == e { continue; }                  // blank line
        if text[s] == 0x23 { continue; }         // '#' comment

        let eq = find_byte(text, s, e, 0x3D);    // '='
        if eq < 0 { return m, E_BAD_MANIFEST; }
        var ks = s;
        var ke = eq;
        while ke > ks && (text[ke - 1] == 0x20 || text[ke - 1] == 0x09) { ke = ke - 1; }
        var vs = eq + 1;
        while vs < e && (text[vs] == 0x20 || text[vs] == 0x09) { vs = vs + 1; }

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
    while p < e && text[p] != 0x20 && text[p] != 0x09 { p = p + 1; }
    let path_len = p - vs;
    if path_len <= 0 || path_len >= MF_PATH_MAX { return E_BAD_MANIFEST; }
    if has_dotdot(text, vs, p) { return E_BAD_MANIFEST; }   // escapes the update root

    while p < e && (text[p] == 0x20 || text[p] == 0x09) { p = p + 1; }
    let hex_start = p;
    while p < e && text[p] != 0x20 && text[p] != 0x09 { p = p + 1; }
    if p - hex_start != MF_DIGEST_HEX { return E_BAD_MANIFEST; }
    let hex_end = p;

    while p < e && (text[p] == 0x20 || text[p] == 0x09) { p = p + 1; }
    var size: i64 = 0;
    var digits: i64 = 0;
    while p < e {
        if text[p] < 0x30 || text[p] > 0x39 { return E_BAD_MANIFEST; }
        size = size * 10 + ((text[p] - 0x30) as i64);
        if size < 0 { return E_BAD_MANIFEST; }             // overflow
        digits = digits + 1;
        p = p + 1;
    }
    if digits == 0 || digits > 12 { return E_BAD_MANIFEST; }

    let slot = m.count;
    var i: i64 = 0;
    while i < path_len {
        m.files[slot].path[i] = text[vs + i];
        i = i + 1;
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
        d = d + 1;
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
        j = j + 1;
    }

    m.count = m.count + 1;
    return CODE_OK;
}

fn paths_equal(a: u8[..32]&, alen: i64, b: u8[..32]&, blen: i64) -> bool {
    if alen != blen { return false; }
    var i: i64 = 0;
    while i < alen {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn has_dotdot(text: u8[:], s: i64, e: i64) -> bool {
    var i = s;
    while i + 1 < e {
        if text[i] == 0x2E && text[i + 1] == 0x2E { return true; }
        i = i + 1;
    }
    return false;
}

fn find_byte(text: u8[:], s: i64, e: i64, b: u8) -> i64 {
    var i = s;
    while i < e {
        if text[i] == b { return i; }
        i = i + 1;
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
        i = i + 1;
    }
    return n;
}

fn copy64(text: u8[:], s: i64, e: i64, dst: u8[..64]&) -> i64 {
    let n = e - s;
    if n <= 0 || n >= MF_ORIGIN_MAX { return -1; }
    var i: i64 = 0;
    while i < n {
        dst[i] = text[s + i];
        i = i + 1;
    }
    return n;
}

fn match_lit(text: u8[:], s: i64, e: i64, lit: const u8[:]) -> bool {
    if e - s != lit.len { return false; }
    var i: i64 = 0;
    while i < lit.len {
        if text[s + i] != lit[i] { return false; }
        i = i + 1;
    }
    return true;
}

// ---------------------------------------------------------------------------
// B-L1-35: verification and the apply plan
// ---------------------------------------------------------------------------
//
// Verification answers one question per file: are these the bytes the manifest named.
// Two checks, in this order:
//
//   1. SIZE first. It is free, and it distinguishes the two failures a person actually
//      needs to tell apart -- "the transfer stopped" (wrong size, wrong hash) from "the
//      bytes changed" (right size, wrong hash).
//   2. SHA-256, compared with the constant-time helper from common/hash. Comparing
//      digests with an early-exit compare leaks how many leading bytes matched, which is
//      exactly the information needed to forge a digest one byte at a time.
//
// What verification does NOT do: it does not check a signature. There is no key, no
// trusted root and no chain yet (B-L1-123). A hash tells you the bytes match the
// manifest; it says nothing about who wrote the manifest. Saying so here is the only
// honest position until B-L1-123 lands.

let SLOT_NONE: i64 = -1;

fn upd_verify_file(m: Manifest&, idx: i64, content: u8[:]) -> i64 {
    if idx < 0 || idx >= m.count { return E_INVAL; }
    if content.len != m.files[idx].size { return E_VERIFY; }     // truncated or padded

    var digest: u8[>..] = [];
    if !sha256(content, digest, 32) { return E_VERIFY; }
    if digest.len != MF_DIGEST_BYTES { return E_VERIFY; }
    if !equal_constant_time(digest[..], m.files[idx].digest[..]) { return E_VERIFY; }
    return CODE_OK;
}

// Verify every file against the content supplied for it. `contents` is indexed by the
// same position as `m.files`: a verifier that matched files by name would have to build a
// lookup, and a name lookup is where "the file that is not in the list" gets skipped.
// Verify every file against the content supplied for it. Contents are indexed by the
// same position as `m.files`: a verifier that matched by name would need a lookup, and a
// name lookup is where "the file that is not in the list" gets skipped.
//
// Returns (verified_count, code). A failure returns the count verified so far with the
// failing code -- partial information the caller needs to say which file failed.
//
// The content table is bytes plus a length per slot rather than an array of slices:
// slices of different lengths are different types and cannot share an array element.

let UPD_CONTENT_MAX: i64 = 4096;

struct ContentSet {
    slots: u8[..32768] = [0; 32768],          // 8 x 4096
    len: i64[..8] = [0; 8],
}

fn content_get(cs: ContentSet&, idx: i64, out: u8[..4096]&) -> i64 {
    if idx < 0 || idx >= MF_MAX_FILES { return -1; }
    let n = cs.len[idx];
    if n <= 0 { return -1; }
    // A slot is UPD_CONTENT_MAX bytes. A longer length is corrupt input, not a bigger read:
    // copying it would run past `out` and into whatever follows the caller's buffer.
    if n > UPD_CONTENT_MAX { return -1; }
    let base = idx * UPD_CONTENT_MAX;
    var i: i64 = 0;
    while i < n {
        out[i] = cs.slots[base + i];
        i = i + 1;
    }
    return n;
}

fn upd_verify_all(m: Manifest&, cs: ContentSet&) -> i64, i64 {
    var buf: u8[..4096] = [0; 4096];
    var verified: i64 = 0;
    var i: i64 = 0;
    while i < m.count {
        let n = content_get(cs, i, buf);
        if n < 0 { return verified, E_VERIFY; }
        let code = upd_verify_file(m, i, buf[..n]);
        if code != CODE_OK { return verified, code; }
        verified = verified + 1;
        i = i + 1;
    }
    return verified, CODE_OK;
}

// The A/B rule (OS-114): an update installs into the slot that is NOT running and takes
// effect on the next boot. That is what makes a failed update recoverable -- the running
// system was never touched, so "roll back" is "boot the other slot".
//
// The plan is data, and it refuses to exist when the premises are wrong:
//   - the manifest's target slot must not be the active slot (installing over the running
//     system removes the ability to fall back);
//   - there must be at least one file, each with a positive size.
//
// It does NOT check free space: the storage contract (B-L1-25) has no "how much room in
// this slot" query, so a plan claiming to have checked would be lying. The apply step
// (B-L1-74, once storage is bound) is where that check belongs, and this note says so.

let UPD_APPLY_NONE: i64 = 0;      // nothing to do
let UPD_APPLY_SLOT: i64 = 1;      // write the files into the inactive slot
let UPD_APPLY_REBOOT: i64 = 2;    // slot written; activation is a reboot

struct Plan {
    action: i64,
    target_slot: i64,
    active_slot: i64,
    files: i64,
    bytes: i64,
    version: u8[..16] = [0; 16],
    version_len: i64,
}

fn upd_plan(m: Manifest&, active_slot: i64) -> Plan, i64 {
    var p: Plan = Plan {
        action: 0,
        target_slot: 0,
        active_slot: 0,
        files: 0,
        bytes: 0,
        version: [0; 16],
        version_len: 0,
    };
    p.action = UPD_APPLY_NONE;
    p.target_slot = SLOT_NONE;
    p.active_slot = active_slot;
    p.files = 0;
    p.bytes = 0;
    p.version_len = 0;

    if active_slot != SLOT_A && active_slot != SLOT_B { return p, E_INVAL; }
    if m.slot != SLOT_A && m.slot != SLOT_B { return p, E_BAD_MANIFEST; }
    if m.slot == active_slot { return p, E_STATE; }      // would overwrite the running system
    if m.count <= 0 { return p, E_BAD_MANIFEST; }

    var total: i64 = 0;
    var i: i64 = 0;
    while i < m.count {
        if m.files[i].size <= 0 { return p, E_BAD_MANIFEST; }
        total = total + m.files[i].size;
        if total < 0 { return p, E_BAD_MANIFEST; }       // overflow
        i = i + 1;
    }

    p.action = UPD_APPLY_SLOT;
    p.target_slot = m.slot;
    p.files = m.count;
    p.bytes = total;
    var v: i64 = 0;
    while v < m.version_len && v < MF_VERSION_MAX {
        p.version[v] = m.version[v];
        v = v + 1;
    }
    p.version_len = v;
    return p, CODE_OK;
}
// ---------------------------------------------------------------------------
// B-L1-36: the rollback record
// ---------------------------------------------------------------------------
//
// The A/B rule only works if something remembers WHICH slot booted successfully. That
// memory has to survive a crash mid-update, which means it has to be on storage, in a
// fixed layout, with a checksum -- a half-written record read as valid is worse than no
// record at all, because it sends the next boot to a slot nobody tested.
//
// Layout of the 512-byte record blk (offsets in bytes):
//
//     0    magic   "MOSU"       4 bytes: not our block -> refuse, never guess
//     4    format  u32          1; bump in the same commit that changes a field
//     8    state   u32          R_PENDING / R_CONFIRMED / R_ROLLED_BACK
//     12   slot    u32          SLOT_A / SLOT_B
//     16   version 16 bytes     NUL padded
//     32   files   u32
//     36   bytes   u32          total bytes written for this update
//     40   applied_ms u64       uptime when the update was applied
//     48   seq     u32          monotonically increasing; higher seq is newer
//     52   crc     u32          CRC32 over bytes 0..52 of the block
//     ..   zero fill to 512
//
// WHY THE CHECKSUM IS OVER THE HEADER ONLY
// ----------------------------------------
// The payload area is reserved. Checksumming bytes nobody writes would make an upgrade
// that starts using them invalidate every old record. Over the fields we define, a torn
// write is caught and a future field is free.

let UPD_REC_MAGIC0: u8 = 0x4D;      // 'M'
let UPD_REC_MAGIC1: u8 = 0x4F;      // 'O'
let UPD_REC_MAGIC2: u8 = 0x53;      // 'S'
let UPD_REC_MAGIC3: u8 = 0x55;      // 'U'
let UPD_REC_FORMAT: i64 = 1;
let UPD_REC_BYTES: i64 = 512;
let UPD_REC_HDR: i64 = 52;
let UPD_REC_KEEP: i64 = 4;          // in-memory history depth

let R_PENDING: i64 = 0;             // written, not yet booted successfully
let R_CONFIRMED: i64 = 1;           // that slot booted and reported healthy
let R_ROLLED_BACK: i64 = 2;         // we came back from it

struct UpdRecord {
    seq: i64,
    state: i64,
    slot: i64,
    version: u8[..16] = [0; 16],
    version_len: i64,
    files: i64,
    bytes: i64,
    applied_ms: i64,
}

var rec_history: UpdRecord[..4] = [UpdRecord { .. }; 4];
var rec_count: i64 = 0;
var rec_next_seq: i64 = 1;

fn upd_record_make(plan: Plan&, now_ms: i64) -> UpdRecord {
    var r: UpdRecord = UpdRecord {
        seq: 0,
        state: 0,
        slot: 0,
        version: [0; 16],
        version_len: 0,
        files: 0,
        bytes: 0,
        applied_ms: 0,
    };
    r.seq = rec_next_seq;
    rec_next_seq = rec_next_seq + 1;
    r.state = R_PENDING;             // never CONFIRMED by the writer: only a boot can say that
    r.slot = plan.target_slot;
    r.files = plan.files;
    r.bytes = plan.bytes;
    r.applied_ms = now_ms;
    var i: i64 = 0;
    while i < plan.version_len && i < 16 {
        r.version[i] = plan.version[i];
        i = i + 1;
    }
    r.version_len = i;
    return r;
}

// Encode into a caller block. Returns bytes written (UPD_REC_BYTES) or -1.
fn upd_record_encode(r: UpdRecord&, blk: u8[..512]&) -> i64 {
    if blk.len < UPD_REC_BYTES { return -1; }
    var i: i64 = 0;
    while i < UPD_REC_BYTES {
        blk[i] = 0;
        i = i + 1;
    }
    blk[0] = UPD_REC_MAGIC0;
    blk[1] = UPD_REC_MAGIC1;
    blk[2] = UPD_REC_MAGIC2;
    blk[3] = UPD_REC_MAGIC3;
    put_u32(blk, 4, UPD_REC_FORMAT);
    put_u32(blk, 8, r.state);
    put_u32(blk, 12, r.slot);
    var v: i64 = 0;
    while v < r.version_len && v < 16 {
        blk[16 + v] = r.version[v];
        v = v + 1;
    }
    put_u32(blk, 32, r.files);
    put_u32(blk, 36, r.bytes);
    put_u64(blk, 40, r.applied_ms);
    put_u32(blk, 48, r.seq);

    let crc = crc32(blk[..UPD_REC_HDR]);
    put_u32(blk, 52, crc as i64);
    return UPD_REC_BYTES;
}

// Decode a block. Every check has a reason, and all of them are refusals rather than
// repairs: a repaired record is a guess about which slot is safe to boot.
fn upd_record_decode(blk: const u8[:], out: UpdRecord&) -> i64 {
    if blk.len < UPD_REC_BYTES { return E_CORRUPT; }
    if blk[0] != UPD_REC_MAGIC0 || blk[1] != UPD_REC_MAGIC1 {
        return E_CORRUPT;                              // not our block
    }
    if blk[2] != UPD_REC_MAGIC2 || blk[3] != UPD_REC_MAGIC3 {
        return E_CORRUPT;
    }
    let format = upd_get_u32(blk, 4);
    if format != UPD_REC_FORMAT { return E_UNSUPPORTED; }   // newer format: do not guess
    let stored = upd_get_u32(blk, 52);
    let actual = crc32(blk[..UPD_REC_HDR]);
    if stored != (actual as i64) { return E_CORRUPT; }      // torn write

    out.state = upd_get_u32(blk, 8);
    out.slot = upd_get_u32(blk, 12);
    if out.slot != SLOT_A && out.slot != SLOT_B { return E_CORRUPT; }
    if out.state != R_PENDING && out.state != R_CONFIRMED && out.state != R_ROLLED_BACK {
        return E_CORRUPT;
    }
    out.files = upd_get_u32(blk, 32);
    out.bytes = upd_get_u32(blk, 36);
    out.applied_ms = get_u64(blk, 40);
    out.seq = upd_get_u32(blk, 48);

    var v: i64 = 0;
    while v < 16 && blk[16 + v] != 0 {
        out.version[v] = blk[16 + v];
        v = v + 1;
    }
    out.version_len = v;
    return CODE_OK;
}

fn upd_record_push(r: UpdRecord&) {
    if rec_count < UPD_REC_KEEP {
        rec_history[rec_count] = r;
        rec_count = rec_count + 1;
        return;
    }
    // Shift down: the history is small and shifts once per update, not per boot.
    var i: i64 = 1;
    while i < UPD_REC_KEEP {
        rec_history[i - 1] = rec_history[i];
        i = i + 1;
    }
    rec_history[UPD_REC_KEEP - 1] = r;
}

// Confirm the slot that just booted. Called ONCE per boot, after the services report
// healthy -- a confirmation written before health is a lie the next boot believes.
fn upd_record_confirm(slot: i64, now_ms: i64) -> i64 {
    var r: UpdRecord = UpdRecord {
        seq: 0,
        state: 0,
        slot: 0,
        version: [0; 16],
        version_len: 0,
        files: 0,
        bytes: 0,
        applied_ms: 0,
    };
    r.seq = rec_next_seq;
    rec_next_seq = rec_next_seq + 1;
    r.state = R_CONFIRMED;
    r.slot = slot;
    r.files = 0;
    r.bytes = 0;
    r.applied_ms = now_ms;
    r.version_len = 0;
    upd_record_push(r);
    return CODE_OK;
}

// Which slot is the safe one to boot?
//
// The newest CONFIRMED record wins. With no confirmed record at all the answer is
// SLOT_NONE, and the caller must not invent one: "probably A" is how a machine with a
// broken fallback boots the broken slot forever.
// How many records the in-memory history holds (capped at UPD_REC_KEEP). Exposed so the
// cap is testable without reaching into module state.
fn upd_record_count() -> i64 { return rec_count; }

fn upd_record_safe_slot() -> i64 {
    var best_seq: i64 = -1;
    var best_slot: i64 = SLOT_NONE;
    var i: i64 = 0;
    while i < rec_count {
        if rec_history[i].state == R_CONFIRMED && rec_history[i].seq > best_seq {
            best_seq = rec_history[i].seq;
            best_slot = rec_history[i].slot;
        }
        i = i + 1;
    }
    return best_slot;
}

fn put_u32(blk: u8[..512]&, at: i64, v: i64) {
    blk[at] = ((v >> 24) & 0xFF) as u8;
    blk[at + 1] = ((v >> 16) & 0xFF) as u8;
    blk[at + 2] = ((v >> 8) & 0xFF) as u8;
    blk[at + 3] = (v & 0xFF) as u8;
}

fn put_u64(blk: u8[..512]&, at: i64, v: i64) {
    put_u32(blk, at, (v >> 32) & 0xFFFFFFFF);
    put_u32(blk, at + 4, v & 0xFFFFFFFF);
}

fn upd_get_u32(blk: const u8[:], at: i64) -> i64 {
    return (blk[at] as i64 * 16777216) + (blk[at + 1] as i64 * 65536) + (blk[at + 2] as i64 * 256) + (blk[at + 3] as i64);
}

fn get_u64(blk: const u8[:], at: i64) -> i64 {
    return (upd_get_u32(blk, at) * 4294967296) + upd_get_u32(blk, at + 4);
}
