// services/notify/notify.goose
//
// Layer 5, face service 7: the top-bar notification feed.
//
// WHAT THIS IS
// ------------
// One feed for the things the machine has to say to the user: a board post arrived, an
// update is available, a receipt landed, a service degraded. Before this, each of those
// would have been a line in the log (where nobody looks) or a badge on one app's tile (which
// the user is not looking at either).
//
// Four properties, and each one is here because the obvious version gets it wrong:
//
//   1. **Duplicates are one notification, not twelve.** A producer that retries, or a feed
//      that fires on every tick, must not fill the bar with the same sentence. Identical
//      (source, text) inside `NT_DEDUPE_MS` returns the id that is already there and a
//      code that says so, so the caller can tell "shown" from "already shown".
//   2. **A dismissal is a record, not a deletion.** Dismissing frees the slot — a full feed
//      of dismissed items must not be a feed that can never show anything again — but the
//      dismissal itself is kept in a ring with its time, so "the user saw this and closed
//      it" survives the slot being reused. That ring is the audit trail for the bar.
//   3. **Refusal is counted.** A thirteenth notification with twelve on screen is refused
//      with `E_NO_SPACE` and counted. Silently dropping the oldest is how a feed loses the
//      one message that mattered; the counter is how a caller finds out it is over capacity.
//   4. **The bar dot is derived, not told.** `nt_worst()` is computed from what is in the
//      feed, so nothing has to keep a second severity variable in sync with the list.
//
// WHAT IT IS NOT
// --------------
// Not a log. It holds at most `NT_MAX` items, it is gone on restart, and there is no
// severity policy that lets an error jump the queue — an honest "refused, and here is the
// count" is the contract instead of a priority scheme nobody would test. Not a transport:
// it does not write to the screen, it hands lines to whoever draws the bar.
//
// Status: RUNS — reached by tests/t95_notify.goose (exit 0). Measured 2026-11-02 by audit_status.py.

import common.err.err;
import common.fmt.fmt;

// Severity. Ordered: a bar draws the highest number in the feed.
let SEV_INFO: i64 = 1;
let SEV_WARN: i64 = 2;
let SEV_ERROR: i64 = 3;

// Above the error range, like the updater client's result codes, so a caller can test
// "not an error" as a group.
let NT_DUPLICATE: i64 = 9101;

let NT_MAX: i64 = 12;
let NT_TEXT_MAX: i64 = 96;      // text is 1..95 bytes, printable ASCII
let NT_SRC_MAX: i64 = 16;       // source is 1..15 bytes
let NT_DEDUPE_MS: i64 = 3000;   // one sentence per source per three seconds
let NT_LOG_MAX: i64 = 8;        // the dismissal ring; the total is unbounded

struct Note {
    id: i64,
    sev: i64,
    when_ms: i64,
    text_len: i64,
    text: u8[..96] = [0; 96],
    source_len: i64,
    source: u8[..16] = [0; 16],
    used: bool,
    dirty: bool,
}

struct Dismissal {
    id: i64,
    sev: i64,
    when_ms: i64,
}

var notes: Note[..12] = [Note { .. }; 12];
var count: i64 = 0;
var next_id: i64 = 1;
var refusals: i64 = 0;
var dupes: i64 = 0;
var dismissals: Dismissal[..8] = [Dismissal { .. }; 8];
var dismissal_total: i64 = 0;
var g_inited: bool = false;

fn nt_init() {
    var i: i64 = 0;
    while i < NT_MAX {
        notes[i].id = 0;
        notes[i].sev = 0;
        notes[i].when_ms = 0;
        notes[i].text_len = 0;
        notes[i].source_len = 0;
        notes[i].used = false;
        notes[i].dirty = false;
        var j: i64 = 0;
        while j < NT_TEXT_MAX { notes[i].text[j] = 0; j = j + 1; }
        j = 0;
        while j < NT_SRC_MAX { notes[i].source[j] = 0; j = j + 1; }
        i = i + 1;
    }
    count = 0;
    next_id = 1;
    refusals = 0;
    dupes = 0;
    i = 0;
    while i < NT_LOG_MAX {
        dismissals[i].id = 0;
        dismissals[i].sev = 0;
        dismissals[i].when_ms = 0;
        i = i + 1;
    }
    dismissal_total = 0;
    g_inited = true;
}

fn nt_ensure() {
    if !g_inited { nt_init(); }
}

fn nt_sev_ok(s: i64) -> bool {
    return s >= SEV_INFO && s <= SEV_ERROR;
}

fn nt_sev_name(s: i64) -> const u8[:] {
    if s == SEV_INFO { return "info"; }
    if s == SEV_WARN { return "warn"; }
    if s == SEV_ERROR { return "error"; }
    return "?";
}

fn nt_find(id: i64) -> i64 {
    var i: i64 = 0;
    while i < count {
        if notes[i].used && notes[i].id == id { return i; }
        i = i + 1;
    }
    return -1;
}

fn nt_printable(s: const u8[:]) -> bool {
    var i: i64 = 0;
    while i < s.len {
        if s[i] < 32 || s[i] > 126 { return false; }
        i = i + 1;
    }
    return true;
}

fn nt_text_eq(at: i64, s: const u8[:]) -> bool {
    if notes[at].text_len != s.len { return false; }
    var i: i64 = 0;
    while i < s.len {
        if notes[at].text[i] != s[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn nt_source_eq(at: i64, s: const u8[:]) -> bool {
    if notes[at].source_len != s.len { return false; }
    var i: i64 = 0;
    while i < s.len {
        if notes[at].source[i] != s[i] { return false; }
        i = i + 1;
    }
    return true;
}

// The id already showing this sentence from this source, or -1. Only the dedupe window
// counts: a board event repeated an hour later is a new event, and suppressing it would
// hide a second post that happens to read like the first.
fn nt_dup(source: const u8[:], text: const u8[:], now_ms: i64) -> i64 {
    var i: i64 = 0;
    while i < count {
        if notes[i].used && notes[i].sev != 0 && nt_source_eq(i, source) && nt_text_eq(i, text) {
            let age = now_ms - notes[i].when_ms;
            if age >= 0 && age <= NT_DEDUPE_MS { return notes[i].id; }
        }
        i = i + 1;
    }
    return -1;
}

// Post one notification. Returns (id, code): the id is the existing one for a duplicate
// and -1 for a refusal.
//
// The order of the checks is the contract: shape, then duplicate, then capacity. Capacity
// last, because a duplicate that is refused for space is a caller being told to grow a feed
// that is already showing the message.
fn nt_post(source: const u8[:], sev: i64, text: const u8[:], now_ms: i64) -> i64, i64 {
    nt_ensure();
    if !nt_sev_ok(sev) { return -1, E_INVAL; }
    if source.len == 0 { return -1, E_INVAL; }
    if source.len >= NT_SRC_MAX { return -1, E_NOROOM; }
    if text.len == 0 { return -1, E_INVAL; }
    if text.len >= NT_TEXT_MAX { return -1, E_NOROOM; }
    if !nt_printable(source) || !nt_printable(text) { return -1, E_INVAL; }

    let dup = nt_dup(source, text, now_ms);
    if dup >= 0 {
        dupes = dupes + 1;
        return dup, NT_DUPLICATE;
    }

    if count >= NT_MAX {
        refusals = refusals + 1;
        return -1, E_NO_SPACE;
    }

    let n = count;
    notes[n].id = next_id;
    notes[n].sev = sev;
    notes[n].when_ms = now_ms;
    notes[n].text_len = text.len;
    notes[n].source_len = source.len;
    notes[n].used = true;
    notes[n].dirty = true;
    var i: i64 = 0;
    while i < NT_TEXT_MAX { notes[n].text[i] = 0; i = i + 1; }
    i = 0;
    while i < text.len { notes[n].text[i] = text[i]; i = i + 1; }
    i = 0;
    while i < NT_SRC_MAX { notes[n].source[i] = 0; i = i + 1; }
    i = 0;
    while i < source.len { notes[n].source[i] = source[i]; i = i + 1; }
    count = count + 1;
    next_id = next_id + 1;
    return notes[n].id, CODE_OK;
}

// Dismiss one notification. The slot is freed (the array compacts, so the feed never fills
// with closed items) and the dismissal is appended to the ring.
//
// The ring overwrites its oldest entry when full and keeps counting: it is a log, and the
// total is the number that matters. `nt_dismissal_at` returns ids from the ring, so after
// nine dismissals the first is gone from the ring and still counted in the total.
fn nt_dismiss(id: i64, now_ms: i64) -> i64 {
    nt_ensure();
    let at = nt_find(id);
    if at < 0 { return E_NOTFOUND; }

    let slot = dismissal_total % NT_LOG_MAX;
    dismissals[slot].id = notes[at].id;
    dismissals[slot].sev = notes[at].sev;
    dismissals[slot].when_ms = now_ms;
    dismissal_total = dismissal_total + 1;

    // Compact: every note after `at` moves down one slot.
    var i = at;
    while i + 1 < count {
        notes[i] = notes[i + 1];
        i = i + 1;
    }
    if count > 0 {
        count = count - 1;
        notes[count].id = 0;
        notes[count].sev = 0;
        notes[count].when_ms = 0;
        notes[count].text_len = 0;
        notes[count].source_len = 0;
        notes[count].used = false;
        notes[count].dirty = false;
    }
    return CODE_OK;
}

// --- readers ---------------------------------------------------------------

fn nt_count() -> i64 { return count; }
fn nt_id_at(i: i64) -> i64 { if i < 0 || i >= count { return 0; } return notes[i].id; }
fn nt_sev_at(i: i64) -> i64 { if i < 0 || i >= count { return 0; } return notes[i].sev; }
fn nt_when_at(i: i64) -> i64 { if i < 0 || i >= count { return 0; } return notes[i].when_ms; }

fn nt_text_at(i: i64) -> const u8[:] {
    if i < 0 || i >= count { return ""; }
    return notes[i].text[..notes[i].text_len];
}

fn nt_source_at(i: i64) -> const u8[:] {
    if i < 0 || i >= count { return ""; }
    return notes[i].source[..notes[i].source_len];
}

// Unread means "newer than the id the bar last showed". Ids are monotonic across
// dismissals, so a cursor that points at a dismissed id still means what it meant.
fn nt_unread(since_id: i64) -> i64 {
    var n: i64 = 0;
    var i: i64 = 0;
    while i < count {
        if notes[i].used && notes[i].id > since_id { n = n + 1; }
        i = i + 1;
    }
    return n;
}

// The dot on the bar: the highest severity on screen, or 0 when the feed is empty. Derived
// from the notes, never stored, so it cannot disagree with them.
fn nt_worst() -> i64 {
    var w: i64 = 0;
    var i: i64 = 0;
    while i < count {
        if notes[i].used && notes[i].sev > w { w = notes[i].sev; }
        i = i + 1;
    }
    return w;
}

fn nt_refusal_total() -> i64 { return refusals; }
fn nt_duplicate_total() -> i64 { return dupes; }
fn nt_dismissal_total() -> i64 { return dismissal_total; }

fn nt_dismissal_at(i: i64) -> i64 {
    if i < 0 || i >= NT_LOG_MAX { return 0; }
    return dismissals[i].id;
}

fn nt_dismissal_sev_at(i: i64) -> i64 {
    if i < 0 || i >= NT_LOG_MAX { return 0; }
    return dismissals[i].sev;
}

fn nt_dismissal_when_at(i: i64) -> i64 {
    if i < 0 || i >= NT_LOG_MAX { return 0; }
    return dismissals[i].when_ms;
}

// The feed as lines for the bar: "<id> <sev> <text>\n", newest last, skipping everything at
// or before `since_id`. Returns (lines, code).
fn nt_fetch(since_id: i64, out: u8[>..]&) -> i64, i64 {
    nt_ensure();
    var n: i64 = 0;
    var i: i64 = 0;
    while i < count {
        if notes[i].used && notes[i].id > since_id {
            let _a = append_int(out, 4096, notes[i].id);
            let _b = append_str(out, 4096, " ");
            let _c = append_str(out, 4096, nt_sev_name(notes[i].sev));
            let _d = append_str(out, 4096, " ");
            let _e = append_str(out, 4096, nt_text_at(i));
            let _f = append_str(out, 4096, "\n");
            n = n + 1;
        }
        i = i + 1;
    }
    return n, CODE_OK;
}
