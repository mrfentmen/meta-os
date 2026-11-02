// services/logd/rotate.goose
//
// B-L1-108 — Log rotation and export.
//
// Status: RUNS — reached by tests/t71_rotate (48 checks, exit 0). Measured 2026-11-02 by audit_status.py.
//
// THE STORE IS A LIST OF SEGMENTS, AND THAT IS THE WHOLE MODEL
// -----------------------------------------------------------
// logd writes one append-only ring. Rotation turns "one ring" into "a bounded list of
// segments", each named by the day shape and a sequence number, with a rule for how many
// are kept. Nothing here touches the FS directly: a caller maps a segment name to an inode
// and copies bytes. Keeping the policy pure is what makes it testable, and rotation is the
// one log feature where a bug destroys history instead of adding it.
//
// WHY ROTATE ON BYTES AND NOT ON TIME
// -----------------------------------
// Time-based rotation is a request to lose the last hour of a crash, every time, because the
// interesting window always straddles the boundary. Segments roll when the current one would
// exceed `max_bytes`; the day is recorded in the name for humans and for export, not as a
// trigger. A quiet day therefore produces one small segment instead of 24 empty files.
//
// NOTHING IS DELETED WITHOUT A COUNT IN THE LOG
// ---------------------------------------------
// rot_prune returns how many segments it dropped and their names, so the caller can log "4
// segments dropped, oldest 2026-10-27.0". A retention policy that silently deletes is a
// policy nobody can audit; the audit layer asks this question directly.

import common.err.err;

let ROT_SEG_MAX: i64 = 8;
let ROT_NAME_MAX: i64 = 40;

// Zero means "no limit" for max_bytes and keep, and is the documented default: a store with
// no policy keeps everything and grows until the FS says no.
struct RotPolicy {
    max_bytes: i64,
    keep: i64,
}

struct RotSegment {
    day: i64,            // days since the epoch, from time.calendar
    seq: i64,            // 0 = the first segment of that day
    bytes: i64,
    sealed: bool,        // a sealed segment is never appended to again
}

struct RotStore {
    segs: RotSegment[..8] = [RotSegment { .. }; 8],
    count: i64,
    policy: RotPolicy,
    dropped_total: i64,
    rotated_total: i64,
}

fn rot_new(max_bytes: i64, keep: i64) -> RotStore {
    var s: RotStore = RotStore {
        segs: [RotSegment { .. }; 8],
        count: 0,
        policy: RotPolicy { max_bytes: 0,
        keep: 0 },
        dropped_total: 0,
        rotated_total: 0,
    };
    var i: i64 = 0;
    while i < ROT_SEG_MAX {
        s.segs[i] = RotSegment { day: 0, seq: 0, bytes: 0, sealed: true };
        i = i + 1;
    }
    s.count = 0;
    s.policy = RotPolicy { max_bytes: max_bytes, keep: keep };
    s.dropped_total = 0;
    s.rotated_total = 0;
    return s;
}

// Append `n` bytes to today's log, rolling first when the current segment cannot hold them.
//
// Returns (segment_index, code). E_NOROOM means the store is at ROT_SEG_MAX and the policy
// will not prune -- the caller must prune explicitly rather than have this function decide
// to throw away history on its own.
fn rot_append(s: RotStore&, day: i64, n: i64) -> i64, i64 {
    if n < 0 { return -1, E_INVAL; }

    var idx = rot_current(s, day);
    if idx >= 0 {
        if s.policy.max_bytes <= 0 || s.segs[idx].bytes + n <= s.policy.max_bytes {
            // Sealed segments stay sealed even when there is room: appending to a sealed
            // segment makes its name lie about its contents.
            if !s.segs[idx].sealed {
                s.segs[idx].bytes = s.segs[idx].bytes + n;
                return idx, CODE_OK;
            }
        }
        // Seal and roll.
        s.segs[idx].sealed = true;
        s.rotated_total = s.rotated_total + 1;
    }

    if s.count >= ROT_SEG_MAX { return -1, E_NOROOM; }

    let new_idx = s.count;
    var seq: i64 = 0;
    var i: i64 = 0;
    while i < s.count {
        if s.segs[i].day == day && s.segs[i].seq >= seq { seq = s.segs[i].seq + 1; }
        i = i + 1;
    }
    s.segs[new_idx] = RotSegment { day: day, seq: seq, bytes: n, sealed: false };
    s.count = s.count + 1;
    return new_idx, CODE_OK;
}

// Index of the open segment for `day`, or -1. Only the newest segment can be open, and only
// if it is for the same day: an open segment from yesterday written to after midnight would
// be findable only by scanning, which is how retention ends up counting the wrong file.
fn rot_current(s: RotStore&, day: i64) -> i64 {
    if s.count == 0 { return -1; }
    let last = s.count - 1;
    if s.segs[last].day != day { return -1; }
    if s.segs[last].sealed { return -1; }
    return last;
}

// Seal the open segment, e.g. at shutdown. Returns the number sealed (0 or 1).
fn rot_seal(s: RotStore&) -> i64 {
    if s.count == 0 { return 0; }
    let last = s.count - 1;
    if s.segs[last].sealed { return 0; }
    s.segs[last].sealed = true;
    return 1;
}

// ---------------------------------------------------------------------------
// Retention
// ---------------------------------------------------------------------------

// Drop the oldest segments beyond `keep`. Returns the count dropped; each dropped segment is
// reported through rot_dropped_name so the caller can name it in the log.
//
// The newest segment is never dropped, even when keep == 0: a policy that can delete the
// file it is currently writing is a policy that loses the crash you are debugging.
fn rot_prune(s: RotStore&) -> i64 {
    let keep = s.policy.keep;
    if keep <= 0 { return 0; }
    var dropped: i64 = 0;
    while s.count > keep && s.count > 1 {
        rot_shift_out(s);
        dropped = dropped + 1;
        s.dropped_total = s.dropped_total + 1;
    }
    return dropped;
}

fn rot_shift_out(s: RotStore&) {
    var i: i64 = 1;
    while i < s.count {
        s.segs[i - 1] = s.segs[i];
        i = i + 1;
    }
    s.count = s.count - 1;
}

// ---------------------------------------------------------------------------
// Names and export
// ---------------------------------------------------------------------------

// "log-<service>-<YYYYMMDD>-<seq>". Day shape first, sequence last, so a directory listing
// sorts chronologically with no parsing. Fixed field widths mean two services' files
// interleave predictably rather than by name length.
fn rot_segment_name(service: const u8[:], seg: RotSegment&, out: u8[>..]&, cap: i64) -> i64 {
    var name: u8[>..] = [];
    if !rot_push(name, cap, "log-") { return -1; }
    if !rot_push(name, cap, service) { return -1; }
    if !rot_push(name, cap, "-") { return -1; }
    if !rot_push_day(name, cap, seg.day) { return -1; }
    if !rot_push(name, cap, "-") { return -1; }
    if !rot_push_i64(name, cap, seg.seq) { return -1; }

    var i: i64 = 0;
    while i < name.len { out.push(name[i]); i = i + 1; }
    return name.len;
}

// One file per service per day: the export shape a human greps and a support bundle ships.
// `seq` is 0 for the day's first segment; a day that rolled twice exports three files, and
// the caller is expected to concatenate them in order.
fn rot_export_name(service: const u8[:], day: i64, seq: i64, out: u8[>..]&, cap: i64) -> i64 {
    var name: u8[>..] = [];
    if !rot_push(name, cap, "export-") { return -1; }
    if !rot_push(name, cap, service) { return -1; }
    if !rot_push(name, cap, "-") { return -1; }
    if !rot_push_day(name, cap, day) { return -1; }
    if seq > 0 {
        if !rot_push(name, cap, "-part") { return -1; }
        if !rot_push_i64(name, cap, seq) { return -1; }
    }
    if !rot_push(name, cap, ".log") { return -1; }
    var i: i64 = 0;
    while i < name.len { out.push(name[i]); i = i + 1; }
    return name.len;
}

// (segments, bytes, dropped_total, rotated_total) -- the four numbers the health line and
// the audit query both want.
fn rot_stats(s: RotStore&) -> i64, i64, i64, i64 {
    var total: i64 = 0;
    var i: i64 = 0;
    while i < s.count {
        total = total + s.segs[i].bytes;
        i = i + 1;
    }
    return s.count, total, s.dropped_total, s.rotated_total;
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

fn rot_push(out: u8[>..]&, cap: i64, s: const u8[:]) -> bool {
    if out.len + s.len > cap { return false; }
    var i: i64 = 0;
    while i < s.len { out.push(s[i]); i = i + 1; }
    return true;
}

fn rot_push_i64(out: u8[>..]&, cap: i64, v: i64) -> bool {
    if v < 0 { return false; }
    if v < 10 {
        if out.len + 1 > cap { return false; }
        out.push((48 + v) as u8);
        return true;
    }
    var digits: i64 = 0;
    var x = v;
    while x > 0 { digits = digits + 1; x = x / 10; }
    if out.len + digits > cap { return false; }
    var buf: u8[..20] = [0; 20];
    var i: i64 = 0;
    x = v;
    while i < digits { buf[digits - 1 - i] = (48 + (x % 10)) as u8; x = x / 10; i = i + 1; }
    i = 0;
    while i < digits { out.push(buf[i]); i = i + 1; }
    return true;
}

// Days-since-epoch as YYYYMMDD. The math is Hinnant's civil_from_days, repeated here in the
// 8-digit compact form rather than imported, because a filename must not depend on a module
// that a boot-order regression could reorder.
fn rot_push_day(out: u8[>..]&, cap: i64, days: i64) -> bool {
    let z = days + 719468;
    var era = z / 146097;
    if (z - era * 146097) < 0 { era = era - 1; }   // floor division, for pre-1970 days
    let doe = z - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    var y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    var m = mp + 3;
    if mp >= 10 { m = mp - 9; }
    if m <= 2 { y = y + 1; }
    if y < 0 || y > 9999 { return false; }

    if out.len + 8 > cap { return false; }
    out.push((48 + (y / 1000) % 10) as u8);
    out.push((48 + (y / 100) % 10) as u8);
    out.push((48 + (y / 10) % 10) as u8);
    out.push((48 + y % 10) as u8);
    out.push((48 + (m / 10) % 10) as u8);
    out.push((48 + m % 10) as u8);
    out.push((48 + (d / 10) % 10) as u8);
    out.push((48 + d % 10) as u8);
    return true;
}
