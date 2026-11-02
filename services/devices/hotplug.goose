// services/devices/hotplug.goose
//
// B-L1-113 — Device hot-plug events: add/remove model with subscriber notification.
//
// Status: RUNS — reached by tests/t77_gaps (73 checks, exit 0). Measured 2026-11-02 by audit_status.py.
//
// WHAT A HOT-PLUG EVENT IS, AND IS NOT
// ------------------------------------
// devices.goose owns the device table and its state machine. A hot-plug event is not a new
// state: it is a *statement that something changed*, queued so that interested services find
// out without polling the table. `hp_raise` is called by the device manager after the table
// has already been updated, so a subscriber that reads the table on notification always sees
// the new truth -- an event delivered before the state change is a race every subscriber
// would have to defend against separately.
//
// SUBSCRIBERS SELECT BY KIND
// --------------------------
// A mask says which event kinds an id wants. A subscriber that only cares about removal (a
// display service dropping a framebuffer) does not wake on every add. Delivered counts are
// per event, so the health line can say "raised 3, delivered to 2 subscribers".
//
// THE QUEUE IS SMALL AND LOSSY IN A STATED WAY
// --------------------------------------------
// Eight events. When it is full the OLDEST is dropped and counted, not the newest: a
// hot-plug storm is almost always a flapping device, and the most recent events are the ones
// that describe its current state. Dropping the newest would leave every subscriber one
// event behind reality, which is worse than missing the middle of a storm.
//
// Notification is a drain, not a callback. There are no function pointers in this layer, and
// a callback into a service that is mid-start is how a supervisor deadlocks.

import common.err.err;

let HP_QUEUE: i64 = 8;
let HP_SUBS: i64 = 8;

let HP_ADD: i64 = 1;
let HP_REMOVE: i64 = 2;
let HP_FAULT: i64 = 3;
let HP_READY: i64 = 4;

struct HotEvent {
    seq: i64,
    kind: i64,
    dev_slot: i64,
    dev_kind: i64,
    at_ms: i64,
}

struct HotSub {
    id: i64,
    mask: i64,          // bit per HP_* kind
    active: bool,
    delivered: i64,
    dropped: i64,       // events for this subscriber that were missed
}

struct HotPlug {
    events: HotEvent[..8] = [HotEvent { .. }; 8],
    head: i64,
    count: i64,
    next_seq: i64,
    next_sub: i64,
    subs: HotSub[..8] = [HotSub { .. }; 8],
    sub_count: i64,
    raised: i64,
    dropped: i64,
}

fn hp_new() -> HotPlug {
    var h: HotPlug = HotPlug {
        events: [HotEvent { .. }; 8],
        head: 0,
        count: 0,
        next_seq: 0,
        next_sub: 0,
        subs: [HotSub { .. }; 8],
        sub_count: 0,
        raised: 0,
        dropped: 0,
    };
    var i: i64 = 0;
    while i < HP_QUEUE {
        h.events[i] = HotEvent { seq: 0, kind: 0, dev_slot: -1, dev_kind: 0, at_ms: 0 };
        i = i + 1;
    }
    i = 0;
    while i < HP_SUBS {
        h.subs[i] = HotSub { id: 0, mask: 0, active: false, delivered: 0, dropped: 0 };
        i = i + 1;
    }
    h.head = 0;
    h.count = 0;
    h.next_seq = 1;
    h.next_sub = 1;
    h.sub_count = 0;
    h.raised = 0;
    h.dropped = 0;
    return h;
}

// Subscribe to a mask of HP_* kinds. Returns the subscriber id, or -1 when the table is
// full or the mask is empty -- a subscriber that silently failed to register would report
// "no events" forever, so the failure is the return value.
fn hp_subscribe(h: HotPlug&, mask: i64) -> i64 {
    if mask == 0 { return -1; }
    if h.sub_count >= HP_SUBS { return -1; }
    var slot: i64 = -1;
    var i: i64 = 0;
    while i < HP_SUBS {
        if !h.subs[i].active { slot = i; break; }
        i = i + 1;
    }
    if slot < 0 { return -1; }
    let id = h.next_sub;
    h.next_sub = h.next_sub + 1;
    h.subs[slot] = HotSub { id: id, mask: mask, active: true, delivered: 0, dropped: 0 };
    h.sub_count = h.sub_count + 1;
    return id;
}

fn hp_unsubscribe(h: HotPlug&, id: i64) -> i64 {
    var i: i64 = 0;
    while i < HP_SUBS {
        if h.subs[i].active && h.subs[i].id == id {
            h.subs[i].active = false;
            h.subs[i].mask = 0;
            h.sub_count = h.sub_count - 1;
            return CODE_OK;
        }
        i = i + 1;
    }
    return E_NOTFOUND;
}

// Raise an event. Returns (delivered_to, code). `delivered_to` counts subscribers whose
// mask includes this kind -- it is informational, not a promise that they have read it yet.
fn hp_raise(h: HotPlug&, kind: i64, dev_slot: i64, dev_kind: i64, at_ms: i64) -> i64, i64 {
    if kind < HP_ADD || kind > HP_READY { return 0, E_INVAL; }

    if h.count >= HP_QUEUE {
        // Drop the oldest: see the header. The subscriber-facing loss is counted per
        // subscriber so each one's health line is about its own missed events.
        let old = h.events[h.head];
        var i: i64 = 0;
        while i < HP_SUBS {
            if h.subs[i].active && (h.subs[i].mask & (1 << old.kind)) != 0 {
                h.subs[i].dropped = h.subs[i].dropped + 1;
                // `delivered` counts the events this subscriber still has waiting, not the
                // ones it was ever told about: an event counted as delivered and then lost
                // to the queue would make (delivered + dropped) larger than (raised), which
                // is a health line that cannot be true.
                if h.subs[i].delivered > 0 { h.subs[i].delivered = h.subs[i].delivered - 1; }
            }
            i = i + 1;
        }
        h.head = (h.head + 1) % HP_QUEUE;
        h.count = h.count - 1;
        h.dropped = h.dropped + 1;
    }

    let at = (h.head + h.count) % HP_QUEUE;
    h.events[at] = HotEvent { seq: h.next_seq, kind: kind, dev_slot: dev_slot, dev_kind: dev_kind, at_ms: at_ms };
    h.next_seq = h.next_seq + 1;
    h.count = h.count + 1;
    h.raised = h.raised + 1;

    var delivered: i64 = 0;
    var s: i64 = 0;
    while s < HP_SUBS {
        if h.subs[s].active && (h.subs[s].mask & (1 << kind)) != 0 {
            h.subs[s].delivered = h.subs[s].delivered + 1;
            delivered = delivered + 1;
        }
        s = s + 1;
    }
    return delivered, CODE_OK;
}

// Take the oldest queued event. Returns true when one was copied out.
fn hp_next(h: HotPlug&, out: HotEvent&) -> bool {
    if h.count == 0 { return false; }
    out = h.events[h.head];
    h.head = (h.head + 1) % HP_QUEUE;
    h.count = h.count - 1;
    return true;
}

fn hp_pending(h: HotPlug&) -> i64 {
    return h.count;
}

// (raised, dropped, subscribers, pending)
fn hp_stats(h: HotPlug&) -> i64, i64, i64, i64 {
    return h.raised, h.dropped, h.sub_count, h.count;
}

// Per-subscriber counters, for a health line that can name the service that is behind.
// Returns false for an unknown or retired id.
fn hp_sub_stats(h: HotPlug&, id: i64, delivered: i64&, dropped: i64&) -> bool {
    var i: i64 = 0;
    while i < HP_SUBS {
        if h.subs[i].id == id && h.subs[i].active {
            delivered = h.subs[i].delivered;
            dropped = h.subs[i].dropped;
            return true;
        }
        i = i + 1;
    }
    return false;
}

// Which device slot an event refers to, or -1. Callers use this to re-read the device table
// rather than trusting the event's snapshot of it: the table is the truth.
fn hp_event_slot(e: HotEvent&) -> i64 {
    return e.dev_slot;
}

fn hp_kind_name(kind: i64) -> const u8[:] {
    if kind == HP_ADD { return "add"; }
    if kind == HP_REMOVE { return "remove"; }
    if kind == HP_FAULT { return "fault"; }
    if kind == HP_READY { return "ready"; }
    return "unknown";
}
