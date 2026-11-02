// services/dock/dock.goose
//
// Layer 5, face service 3: the dock.
//
// WHAT THIS IS
// ------------
// An ordered list of pinned applications, each with running state, plus the launch
// handshake the desktop needs: the dock asks, the supervisor spawns, and the dock is
// told what happened. Three rules carry the weight:
//
//   1. **A launch is pending until it is resolved.** Two clicks in 200 ms is one
//      launch, not two processes. A pending request inside `DK_DEDUPE_MS` is refused
//      with `E_BUSY` and is not counted as a second request.
//   2. **A launch that never reports is a failure.** `dk_expire` turns a pending
//      request older than `DK_LAUNCH_TIMEOUT_MS` into a failure, because the
//      alternative — leaving it pending forever — makes the dock show "starting" for
//      an app that will never appear.
//   3. **A running app cannot be unpinned.** Unpinning it would leave the window with
//      no dock entry, which is how a running app becomes unreachable.
//
// The dock does not spawn anything and does not own a pid: it records intent and
// outcome. Spawning is the supervisor's (B-L1-21), and a dock that also spawned would
// be a second authority over the same process table.
//
// Status: RUNS — reached by tests/t88_dock (exit 0). Measured 2026-11-02 by audit_status.py.

import common.err.err;

let DK_MAX: i64 = 12;
let DK_NAME_MAX: i64 = 16;
let DK_DEDUPE_MS: i64 = 1500;
let DK_LAUNCH_TIMEOUT_MS: i64 = 5000;

struct Item {
    id: i64,
    name: u8[..16] = [0; 16],
    name_len: i64,
    pinned: bool,
    running: bool,
    pending: bool,
    pending_since_ms: i64,
    launches: i64,
    failures: i64,
    expiries: i64,
}

// The array order IS the dock order: `dk_move` shifts entries, so reading the dock
// top to bottom needs no sort and no second index.
var items: Item[..12] = [Item { .. }; 12];
var count: i64 = 0;
var next_id: i64 = 1;

fn dk_init() {
    var i: i64 = 0;
    while i < DK_MAX {
        items[i].id = 0;
        items[i].name_len = 0;
        items[i].pinned = false;
        items[i].running = false;
        items[i].pending = false;
        items[i].pending_since_ms = 0;
        items[i].launches = 0;
        items[i].failures = 0;
        items[i].expiries = 0;
        var j: i64 = 0;
        while j < DK_NAME_MAX { items[i].name[j] = 0; j = j + 1; }
        i = i + 1;
    }
    count = 0;
    next_id = 1;
}

fn dk_find(id: i64) -> i64 {
    var i: i64 = 0;
    while i < count {
        if items[i].pinned && items[i].id == id { return i; }
        i = i + 1;
    }
    return -1;
}

fn dk_find_name(s: const u8[:]) -> i64 {
    var i: i64 = 0;
    while i < count {
        if items[i].pinned && items[i].name_len == s.len && dk_name_eq(i, s) { return i; }
        i = i + 1;
    }
    return -1;
}

fn dk_name_eq(i: i64, s: const u8[:]) -> bool {
    var k: i64 = 0;
    while k < s.len {
        if items[i].name[k] != s[k] { return false; }
        k = k + 1;
    }
    return true;
}

// Pin an app at the end of the dock. The id is stable and never reused, so a launch
// request that arrives after an unpin cannot hit whatever took the slot.
fn dk_pin(name: const u8[:]) -> i64, i64 {
    if name.len == 0 { return -1, E_INVAL; }
    if name.len >= DK_NAME_MAX { return -1, E_NOROOM; }
    var i: i64 = 0;
    while i < name.len {
        if name[i] < 32 || name[i] > 126 { return -1, E_INVAL; }
        i = i + 1;
    }
    if dk_find_name(name) >= 0 { return -1, E_STATE; }
    if count >= DK_MAX { return -1, E_NO_SPACE; }

    let n = count;
    items[n].id = next_id;
    next_id = next_id + 1;
    items[n].name_len = name.len;
    i = 0;
    while i < DK_NAME_MAX { items[n].name[i] = 0; i = i + 1; }
    i = 0;
    while i < name.len {
        items[n].name[i] = name[i];
        i = i + 1;
    }
    items[n].pinned = true;
    items[n].running = false;
    items[n].pending = false;
    items[n].launches = 0;
    items[n].failures = 0;
    items[n].expiries = 0;
    count = count + 1;
    return items[n].id, CODE_OK;
}

// Unpin. Refused while running or while a launch is pending: both would drop the only
// dock handle to a process that exists or is about to.
fn dk_unpin(id: i64) -> i64 {
    let at = dk_find(id);
    if at < 0 { return E_NOTFOUND; }
    if items[at].running { return E_BUSY; }
    if items[at].pending { return E_BUSY; }
    var i = at;
    while i < count - 1 {
        items[i] = items[i + 1];
        i = i + 1;
    }
    count = count - 1;
    var j: i64 = 0;
    while j < DK_NAME_MAX { items[count].name[j] = 0; j = j + 1; }
    items[count].pinned = false;
    items[count].id = 0;
    items[count].name_len = 0;
    return CODE_OK;
}

// Move a pinned app to `index` in the dock. Out-of-range indices are refused rather
// than clamped: a drag that lands past the end is a bug in the drag, and silently
// appending would hide it.
fn dk_move(id: i64, index: i64) -> i64 {
    let at = dk_find(id);
    if at < 0 { return E_NOTFOUND; }
    if index < 0 || index >= count { return E_INVAL; }
    if index == at { return CODE_OK; }
    let moving = items[at];
    var i = at;
    if index > at {
        while i < index {
            items[i] = items[i + 1];
            i = i + 1;
        }
    } else {
        while i > index {
            items[i] = items[i - 1];
            i = i - 1;
        }
    }
    items[index] = moving;
    return CODE_OK;
}

// Ask for a launch. One request per app per dedupe window.
fn dk_launch(id: i64, now_ms: i64) -> i64 {
    let at = dk_find(id);
    if at < 0 { return E_NOTFOUND; }
    if items[at].running { return E_BUSY; }
    if items[at].pending {
        if now_ms - items[at].pending_since_ms < DK_DEDUPE_MS { return E_BUSY; }
        // A request that is older than the window has already been given up on by
        // dk_expire; treating it as live would launch the app twice.
        items[at].pending = false;
    }
    items[at].pending = true;
    items[at].pending_since_ms = now_ms;
    items[at].launches = items[at].launches + 1;
    return CODE_OK;
}

// The outcome of a pending launch. A result with no pending request is E_STATE: a
// supervisor that reports a launch the dock never asked for is a supervisor talking
// about a different dock.
fn dk_result(id: i64, ok: bool) -> i64 {
    let at = dk_find(id);
    if at < 0 { return E_NOTFOUND; }
    if !items[at].pending { return E_STATE; }
    items[at].pending = false;
    items[at].running = ok;
    if !ok { items[at].failures = items[at].failures + 1; }
    return CODE_OK;
}

// Age out launches nothing answered. Returns how many were expired; each one is
// recorded as a failure, because an app that never started did not start.
fn dk_expire(now_ms: i64) -> i64 {
    var n: i64 = 0;
    var i: i64 = 0;
    while i < count {
        if items[i].pinned && items[i].pending && now_ms - items[i].pending_since_ms >= DK_LAUNCH_TIMEOUT_MS {
            items[i].pending = false;
            items[i].failures = items[i].failures + 1;
            items[i].expiries = items[i].expiries + 1;
            n = n + 1;
        }
        i = i + 1;
    }
    return n;
}

fn dk_running_off(id: i64) -> i64 {
    let at = dk_find(id);
    if at < 0 { return E_NOTFOUND; }
    if !items[at].running { return E_STATE; }
    items[at].running = false;
    return CODE_OK;
}

// --- readers ---------------------------------------------------------------

fn dk_count() -> i64 { return count; }

fn dk_id_at(i: i64) -> i64 {
    if i < 0 || i >= count { return 0; }
    return items[i].id;
}

fn dk_name_at(i: i64) -> const u8[:] {
    if i < 0 || i >= count { return ""; }
    return items[i].name[..items[i].name_len];
}

fn dk_running_at(i: i64) -> bool {
    if i < 0 || i >= count { return false; }
    return items[i].running;
}

fn dk_pending_at(i: i64) -> bool {
    if i < 0 || i >= count { return false; }
    return items[i].pending;
}

fn dk_launches_of(id: i64) -> i64 {
    let at = dk_find(id);
    if at < 0 { return -1; }
    return items[at].launches;
}

fn dk_failures_of(id: i64) -> i64 {
    let at = dk_find(id);
    if at < 0 { return -1; }
    return items[at].failures;
}

fn dk_expiries_of(id: i64) -> i64 {
    let at = dk_find(id);
    if at < 0 { return -1; }
    return items[at].expiries;
}

fn dk_running_count() -> i64 {
    var n: i64 = 0;
    var i: i64 = 0;
    while i < count {
        if items[i].running { n = n + 1; }
        i = i + 1;
    }
    return n;
}

fn dk_pending_count() -> i64 {
    var n: i64 = 0;
    var i: i64 = 0;
    while i < count {
        if items[i].pending { n = n + 1; }
        i = i + 1;
    }
    return n;
}

fn dk_find_by_name(s: const u8[:]) -> i64 {
    let at = dk_find_name(s);
    if at < 0 { return -1; }
    return items[at].id;
}
