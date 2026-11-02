// services/agenthost/quota.goose
//
// B-L1-116 — Agent quotas: call rate and storage, as data plus a check.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHAT A QUOTA IS HERE
// --------------------
// Two numbers per agent: calls per window, and bytes of storage. Both are *limits on the
// host's protection of itself*, not a security control and not a billing meter. The
// distinction matters because it sets what this file must guarantee: a denied call is a
// recorded refusal that a caller can see and react to (E_QUOTA), and the check is cheap
// enough to run on every call. Anything stronger would need a clock the calling agent cannot
// influence, which this layer does not have.
//
// FIXED WINDOWS, AND WHY THE COUNTER RESETS LAZILY
// ------------------------------------------------
// A sliding window needs a timestamp per call. A fixed window needs one timestamp per agent
// and one counter, and its worst case (a burst across a boundary) is bounded at 2x the rate
// for one window. For a host keeping an agent from monopolising the machine, 2x is fine.
// The window is reset when a call arrives after it expired -- no timer, so a machine with no
// ticking clock still enforces the quota the moment it is asked to.
//
// ZERO MEANS UNLIMITED
// --------------------
// For both fields. A quota table with a default of "deny everything" would make a
// misconfigured host refuse its own services, which is the wrong failure direction for a
// limit that protects a machine from a guest.
//
// DENIALS ARE COUNTED PER AGENT AND NEVER CLEARED
// ----------------------------------------------
// The counter is what an operator looks at to answer "is this agent thrashing against its
// limit", and a counter that resets tells a lie over a long run.

import common.err.err;
import common.fmt.fmt;
import agenthost.agenthost;

struct Quota {
    call_rate: i64,        // calls allowed per window; 0 = unlimited
    window_ms: i64,
    storage_bytes: i64,    // 0 = unlimited
}

struct QuotaSlot {
    handle: i64,
    q: Quota,
    window_start_ms: i64,
    calls_in_window: i64,
    storage_used: i64,
    denied_calls: i64,
    denied_storage: i64,
    active: bool,
}

struct Quotas {
    slots: QuotaSlot[..24],
    count: i64,
}

fn quota_default() -> Quota {
    // 60 calls per second and 1 MiB of storage: enough for a chatty service, small enough
    // that a runaway loop is visible in the log within a second.
    return Quota { call_rate: 60, window_ms: 1000, storage_bytes: 1048576 };
}

fn quota_new() -> Quotas {
    var qs: Quotas = Quotas { slots: [], count: 0 };
    var i: i64 = 0;
    while i < AH_CAP {
        qs.slots[i] = QuotaSlot { handle: 0, q: quota_default(), window_start_ms: 0, calls_in_window: 0, storage_used: 0, denied_calls: 0, denied_storage: 0, active: false };
        i = i + 1;
    }
    qs.count = 0;
    return qs;
}

// Attach a quota to an agent. Returns E_NO_AGENT for a handle the host does not resolve --
// a quota on a slot that does not exist is a limit nobody is subject to.
fn quota_set(qs: Quotas&, h: i64, q: Quota) -> i64 {
    if ah_slot_of(h) < 0 { return E_NO_AGENT; }
    if q.window_ms <= 0 && q.call_rate > 0 { return E_INVAL; }
    if q.call_rate < 0 || q.storage_bytes < 0 { return E_INVAL; }

    var slot = quota_slot_of(qs, h);
    if slot < 0 {
        slot = quota_free_slot(qs);
        if slot < 0 { return E_NOROOM; }
        qs.slots[slot] = QuotaSlot { handle: h, q: q, window_start_ms: 0, calls_in_window: 0, storage_used: 0, denied_calls: 0, denied_storage: 0, active: true };
        qs.count = qs.count + 1;
        return CODE_OK;
    }
    qs.slots[slot].q = q;
    return CODE_OK;
}

fn quota_get(qs: Quotas&, h: i64) -> Quota, bool {
    let slot = quota_slot_of(qs, h);
    if slot < 0 { return quota_default(), false; }
    return qs.slots[slot].q, true;
}

// ---------------------------------------------------------------------------
// Checks
// ---------------------------------------------------------------------------

// May this agent make one call now? Returns CODE_OK and charges the call, or E_QUOTA and
// counts the denial.
//
// An agent with no quota row is unlimited: the table is an opt-in limit, and failing closed
// on a missing row would turn "the supervisor forgot to configure me" into an outage.
fn quota_call(qs: Quotas&, h: i64, now_ms: i64) -> i64 {
    let slot = quota_slot_of(qs, h);
    if slot < 0 { return CODE_OK; }
    let q = qs.slots[slot].q;
    if q.call_rate <= 0 { return CODE_OK; }

    if now_ms - qs.slots[slot].window_start_ms >= q.window_ms || now_ms < qs.slots[slot].window_start_ms {
        // A clock that went backwards starts a new window: a stuck window would deny forever.
        qs.slots[slot].window_start_ms = now_ms;
        qs.slots[slot].calls_in_window = 0;
    }
    if qs.slots[slot].calls_in_window >= q.call_rate {
        qs.slots[slot].denied_calls = qs.slots[slot].denied_calls + 1;
        return E_QUOTA;
    }
    qs.slots[slot].calls_in_window = qs.slots[slot].calls_in_window + 1;
    return CODE_OK;
}

// May this agent store `add` more bytes? E_QUOTA and a counted denial, or CODE_OK and the
// bytes charged. Separate from quota_charge so a caller that reserves can release.
fn quota_storage(qs: Quotas&, h: i64, add: i64) -> i64 {
    if add <= 0 { return E_INVAL; }
    let slot = quota_slot_of(qs, h);
    if slot < 0 { return CODE_OK; }
    let q = qs.slots[slot].q;
    if q.storage_bytes <= 0 {
        qs.slots[slot].storage_used = qs.slots[slot].storage_used + add;
        return CODE_OK;
    }
    if qs.slots[slot].storage_used + add > q.storage_bytes {
        qs.slots[slot].denied_storage = qs.slots[slot].denied_storage + 1;
        return E_QUOTA;
    }
    qs.slots[slot].storage_used = qs.slots[slot].storage_used + add;
    return CODE_OK;
}

// Give bytes back. Never below zero, and never an error for an agent with no row: releasing
// after a quota row was removed must not fail the close path.
fn quota_release(qs: Quotas&, h: i64, n: i64) -> i64 {
    if n <= 0 { return E_INVAL; }
    let slot = quota_slot_of(qs, h);
    if slot < 0 { return CODE_OK; }
    if n > qs.slots[slot].storage_used { qs.slots[slot].storage_used = 0; return CODE_OK; }
    qs.slots[slot].storage_used = qs.slots[slot].storage_used - n;
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// Reporting
// ---------------------------------------------------------------------------

// "calls 12/60 (window 1000ms) storage 4096/1048576 denied 3/0"
//
// The health line an operator reads once per boot. Percentages are deliberately absent: a
// percentage of an unlimited quota has no meaning, and the raw numbers answer the question.
fn quota_status(qs: Quotas&, h: i64, out: u8[>..]&, cap: i64) -> bool {
    let slot = quota_slot_of(qs, h);
    if slot < 0 { return append_str(out, cap, "no quota"); }
    let s = qs.slots[slot];

    if !append_str(out, cap, "calls ") { return false; }
    if !append_int(out, cap, s.calls_in_window) { return false; }
    if !append_str(out, cap, "/") { return false; }
    if s.q.call_rate <= 0 { if !append_str(out, cap, "unlimited") { return false; } }
    else { if !append_int(out, cap, s.q.call_rate) { return false; } }

    if !append_str(out, cap, " storage ") { return false; }
    if !append_int(out, cap, s.storage_used) { return false; }
    if !append_str(out, cap, "/") { return false; }
    if s.q.storage_bytes <= 0 { if !append_str(out, cap, "unlimited") { return false; } }
    else { if !append_int(out, cap, s.q.storage_bytes) { return false; } }

    if !append_str(out, cap, " denied ") { return false; }
    if !append_int(out, cap, s.denied_calls) { return false; }
    if !append_str(out, cap, "/") { return false; }
    return append_int(out, cap, s.denied_storage);
}

// (rows, denied_calls_total, denied_storage_total) for the host's own health line.
fn quota_totals(qs: Quotas&) -> i64, i64, i64 {
    var calls: i64 = 0;
    var storage: i64 = 0;
    var i: i64 = 0;
    while i < AH_CAP {
        if qs.slots[i].active {
            calls = calls + qs.slots[i].denied_calls;
            storage = storage + qs.slots[i].denied_storage;
        }
        i = i + 1;
    }
    return qs.count, calls, storage;
}

// Drop a row when the agent is reaped. The counters go with it: keeping a denial count for a
// handle that no longer resolves would make the totals climb forever.
fn quota_remove(qs: Quotas&, h: i64) -> i64 {
    let slot = quota_slot_of(qs, h);
    if slot < 0 { return E_NOTFOUND; }
    qs.slots[slot].active = false;
    qs.slots[slot].handle = 0;
    qs.count = qs.count - 1;
    return CODE_OK;
}

fn quota_slot_of(qs: Quotas&, h: i64) -> i64 {
    var i: i64 = 0;
    while i < AH_CAP {
        if qs.slots[i].active && qs.slots[i].handle == h { return i; }
        i = i + 1;
    }
    return -1;
}

fn quota_free_slot(qs: Quotas&) -> i64 {
    var i: i64 = 0;
    while i < AH_CAP {
        if !qs.slots[i].active { return i; }
        i = i + 1;
    }
    return -1;
}
