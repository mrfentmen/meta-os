// services/tests/harness/link.goose
//
// B-L1-105 — Loopback harness v2.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHY A HARNESS AND NOT A DRIVER
// ------------------------------
// The protocol tests need three things a real driver never gives them on demand: a
// datagram that is never delivered, a datagram delivered twice, and two datagrams
// delivered out of order. Those are the three cases every protocol bug lives in, and none
// of them can be scheduled through a loopback interface that always works.
//
// So this is a *packet pair* with the impairment decisions expressed as data: a `Link` is
// two endpoints, one queue, and three counters. "Drop every 3rd packet" is a field, not a
// code change, and the test that relies on it says so in one line.
//
// WHAT IS DELIBERATELY IGNORED
// ----------------------------
// Corruption is not here. A link that flips bits at random produces failures that are
// indistinguishable from bugs in the parser under test; corruption cases belong in the
// checked-in hostile-input packs (Wave K) where the expected failure is written down next
// to the bytes. Loss, duplicate and reorder are timing behaviours and belong here.
//
// The queue is fixed (LINK_SLOTS packets) and full means E_BUSY, not "drop the oldest":
// a harness that silently dropped on overflow would make a slow receiver look like a lossy
// link, which is exactly the ambiguity this file exists to remove.

import common.err.err;

let LINK_SLOTS: i64 = 8;
let LINK_PKT: i64 = 1500;
let LINK_BYTES: i64 = 12000;          // LINK_SLOTS * LINK_PKT, flat storage

struct Link {
    slots: u8[..12000] = [0; 12000],               // packet i lives at [i*LINK_PKT .. i*LINK_PKT+len)
    lens: i64[..8] = [0; 8],
    head: i64,                        // index of the next packet to deliver
    count: i64,
    drop_every: i64,                  // 0 = never drop
    dup_every: i64,                   // 0 = never duplicate
    reorder_every: i64,               // 0 = preserve order
    sent: i64,
    dropped: i64,
    duped: i64,
    delivered: i64,
}

// A clean link. Knobs are set afterwards with link_impair, so a test that wants one
// impairment does not have to name the other two.
fn link_new() -> Link {
    var l: Link = Link {
        slots: [0; 12000],
        lens: [0; 8],
        head: 0,
        count: 0,
        drop_every: 0,
        dup_every: 0,
        reorder_every: 0,
        sent: 0,
        dropped: 0,
        duped: 0,
        delivered: 0,
    };
    var i: i64 = 0;
    while i < LINK_BYTES { l.slots[i] = 0; i = i + 1; }
    i = 0;
    while i < LINK_SLOTS { l.lens[i] = 0; i = i + 1; }
    l.head = 0;
    l.count = 0;
    l.drop_every = 0;
    l.dup_every = 0;
    l.reorder_every = 0;
    l.sent = 0;
    l.dropped = 0;
    l.duped = 0;
    l.delivered = 0;
    return l;
}

// Any argument <= 0 disables that impairment. Every Nth *sent* packet is affected, counted
// from 1, so "drop_every = 3" drops sends 3, 6, 9.
fn link_impair(l: Link&, drop_every: i64, dup_every: i64, reorder_every: i64) {
    l.drop_every = drop_every;
    l.dup_every = dup_every;
    l.reorder_every = reorder_every;
}

fn link_pending(l: Link&) -> i64 {
    return l.count;
}

// Send a datagram towards the far endpoint. Returns the code; E_BUSY means the queue was
// full -- the caller must drain, not retry blindly.
fn link_send(l: Link&, pkt: const u8[:]) -> i64, i64 {
    if pkt.len > LINK_PKT { return 0, E_NOROOM; }
    l.sent = l.sent + 1;

    if l.drop_every > 0 && (l.sent % l.drop_every) == 0 {
        l.dropped = l.dropped + 1;
        return 0, CODE_OK;            // a drop is a normal outcome on this link
    }
    if l.count >= LINK_SLOTS { return 0, E_BUSY; }

    let code = link_put(l, pkt);
    if code != CODE_OK { return 0, code; }
    var placed: i64 = 1;

    if l.dup_every > 0 && (l.sent % l.dup_every) == 0 {
        if l.count >= LINK_SLOTS { return placed, E_BUSY; }
        let dcode = link_put(l, pkt);
        if dcode != CODE_OK { return placed, dcode; }
        l.duped = l.duped + 1;
        placed = placed + 1;
    }

    // Reorder: the packet just queued overtakes the one before it. Doing it here, at send
    // time, means the receive side never has to guess what "out of order" was supposed to
    // look like.
    if l.reorder_every > 0 && (l.sent % l.reorder_every) == 0 && l.count >= 2 {
        link_swap(l, link_slot_at(l, l.count - 2), link_slot_at(l, l.count - 1));
    }
    return placed, CODE_OK;
}

// Deliver the oldest queued datagram into `out`. Returns (bytes, code); (0, CODE_OK) means
// nothing was pending -- an empty link is not an error, and telling those apart is the
// whole reason both values are returned.
fn link_recv(l: Link&, out: u8[>..]&, cap: i64) -> i64, i64 {
    if l.count == 0 { return 0, CODE_OK; }
    let slot = link_slot_at(l, 0);
    let n = l.lens[slot];
    if n > cap { return 0, E_NOROOM; }
    var i: i64 = 0;
    while i < n {
        out.push(l.slots[slot * LINK_PKT + i]);
        i = i + 1;
    }
    l.head = (l.head + 1) % LINK_SLOTS;
    l.count = l.count - 1;
    l.delivered = l.delivered + 1;
    return n, CODE_OK;
}

// (sent, dropped, duped, delivered) — the four numbers a protocol test asserts on.
fn link_stats(l: Link&) -> i64, i64, i64, i64 {
    return l.sent, l.dropped, l.duped, l.delivered;
}

// ---------------------------------------------------------------------------
// Internals
// ---------------------------------------------------------------------------

fn link_slot_at(l: Link&, pos: i64) -> i64 {
    return (l.head + pos) % LINK_SLOTS;
}

fn link_put(l: Link&, pkt: const u8[:]) -> i64 {
    let slot = link_slot_at(l, l.count);
    var i: i64 = 0;
    while i < pkt.len {
        l.slots[slot * LINK_PKT + i] = pkt[i];
        i = i + 1;
    }
    l.lens[slot] = pkt.len;
    l.count = l.count + 1;
    return CODE_OK;
}

fn link_swap(l: Link&, a: i64, b: i64) {
    var tmp: u8[..1500] = [0; 1500];
    let an = l.lens[a];
    let bn = l.lens[b];
    var i: i64 = 0;
    while i < an { tmp[i] = l.slots[a * LINK_PKT + i]; i = i + 1; }
    i = 0;
    while i < bn { l.slots[a * LINK_PKT + i] = l.slots[b * LINK_PKT + i]; i = i + 1; }
    i = 0;
    while i < an { l.slots[b * LINK_PKT + i] = tmp[i]; i = i + 1; }
    l.lens[a] = bn;
    l.lens[b] = an;
}
