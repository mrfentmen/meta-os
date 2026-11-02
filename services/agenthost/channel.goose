// services/agenthost/channel.goose
//
// B-L1-117 — Agent message channel: agent-to-agent messages, queued, with honest states.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// THE FOUR STATES, AND WHAT EACH ONE PROMISES
// -------------------------------------------
//   QUEUED     accepted by the host; not yet read by the recipient
//   DELIVERED  copied into the recipient's buffer by ch_recv
//   EXPIRED    its deadline passed while still queued; the body was dropped
//   REJECTED   never queued: no such agent, missing capability, or no room
//
// "DELIVERED" means delivered, not acknowledged and not processed. The host cannot know
// whether an agent acted on a message, and a state name that implies it would be the first
// lie in the whole agent layer. There is no "READ" state for the same reason.
//
// CAPABILITIES ON BOTH ENDS
// -------------------------
// Sending needs CAP_MSG. So does receiving: an agent that did not ask to receive messages must
// not have a queue growing for it, because that queue is memory the host cannot reclaim
// without deciding to drop someone's messages. Refusing at send time (E_DENIED) is a failure
// the sender sees; growing a queue nobody drains is a failure nobody sees until the boot OOMs.
//
// MESSAGES EXPIRE, AND THE BODY IS WHAT EXPIRES
// --------------------------------------------
// A deadline is required (ttl_ms > 0). A queued message with no deadline is a message that
// outlives the agent that cares about it -- an agent-to-agent ping from three boots ago is
// never useful and always occupies a slot. Expiry preserves the slot's metadata, so the
// health line can say "12 expired for this pair" instead of the messages vanishing.
//
// SELF-SEND IS REFUSED
// --------------------
// An agent messaging itself is either a bug or a loop. E_INVAL costs a caller nothing and
// prevents a queue that fills with its own output.

import common.err.err;
import common.fmt.fmt;
import agenthost.agenthost;

let CH_SLOTS: i64 = 16;
let CH_BODY: i64 = 64;

let MSG_QUEUED: i64 = 0;
let MSG_DELIVERED: i64 = 1;
let MSG_EXPIRED: i64 = 2;
let MSG_REJECTED: i64 = 3;

struct Msg {
    id: i64,
    from_handle: i64,
    to_handle: i64,
    queued_ms: i64,
    deadline_ms: i64,
    state: i64,
    len: i64,
    body: u8[..64],
}

struct Channel {
    msgs: Msg[..16],
    count: i64,
    next_id: i64,
    sent: i64,
    delivered: i64,
    rejected: i64,
    expired: i64,
    full_events: i64,
}

fn ch_new() -> Channel {
    var c: Channel = Channel {
        msgs: [],
        count: 0,
        next_id: 0,
        sent: 0,
        delivered: 0,
        rejected: 0,
        expired: 0,
        full_events: 0,
    };
    var i: i64 = 0;
    while i < CH_SLOTS {
        c.msgs[i] = Msg { id: 0, from_handle: 0, to_handle: 0, queued_ms: 0, deadline_ms: 0, state: MSG_REJECTED, len: 0, body: ch_zero_body() };
        i = i + 1;
    }
    c.count = 0;
    c.next_id = 1;
    c.sent = 0;
    c.delivered = 0;
    c.rejected = 0;
    c.expired = 0;
    c.full_events = 0;
    return c;
}

fn ch_zero_body() -> u8[..64] {
    var b: u8[..64] = [];
    var i: i64 = 0;
    while i < CH_BODY { b[i] = 0; i = i + 1; }
    return b;
}

// ---------------------------------------------------------------------------
// Send
// ---------------------------------------------------------------------------

// Queue a message. Returns (id, code).
//
// The order of the refusals matters: capability first, then existence, then room. A sender
// without CAP_MSG learns nothing about whether the recipient exists, which is the smallest
// courtesy available in a host that keeps a name table.
fn ch_send(c: Channel&, from: i64, to: i64, body: const u8[:], now_ms: i64, ttl_ms: i64) -> i64, i64 {
    if !ah_caps_have(from, CAP_MSG) { c.rejected = c.rejected + 1; return 0, E_DENIED; }
    if !ah_caps_have(to, CAP_MSG) { c.rejected = c.rejected + 1; return 0, E_DENIED; }
    if !ah_is_live(to) { c.rejected = c.rejected + 1; return 0, E_NO_AGENT; }
    if from == to { c.rejected = c.rejected + 1; return 0, E_INVAL; }
    if body.len > CH_BODY { c.rejected = c.rejected + 1; return 0, E_NOROOM; }
    if ttl_ms <= 0 { c.rejected = c.rejected + 1; return 0, E_INVAL; }

    let slot = ch_free_slot(c);
    if slot < 0 {
        c.rejected = c.rejected + 1;
        c.full_events = c.full_events + 1;
        return 0, E_BUSY;
    }

    var m: Msg = Msg {
        id: 0,
        from_handle: 0,
        to_handle: 0,
        queued_ms: 0,
        deadline_ms: 0,
        state: 0,
        len: 0,
        body: [],
    };
    m.id = c.next_id;
    c.next_id = c.next_id + 1;
    m.from_handle = from;
    m.to_handle = to;
    m.queued_ms = now_ms;
    m.deadline_ms = now_ms + ttl_ms;
    m.state = MSG_QUEUED;
    m.len = body.len;
    m.body = ch_zero_body();
    var i: i64 = 0;
    while i < body.len {
        m.body[i] = body[i];
        i = i + 1;
    }
    c.msgs[slot] = m;
    c.count = c.count + 1;
    c.sent = c.sent + 1;
    return m.id, CODE_OK;
}

// ---------------------------------------------------------------------------
// Receive
// ---------------------------------------------------------------------------

// Take the oldest queued message for `for_handle` and copy its body out.
// Returns (id, code): id 0 with CODE_OK means the queue held nothing for this agent --
// an empty inbox is not an error.
fn ch_recv(c: Channel&, for_handle: i64, now_ms: i64, out: u8[>..]&, cap: i64) -> i64, i64 {
    ch_expire(c, now_ms);

    var slot = ch_oldest_for(c, for_handle);
    if slot < 0 { return 0, CODE_OK; }
    if c.msgs[slot].len > cap { return 0, E_NOROOM; }

    var i: i64 = 0;
    while i < c.msgs[slot].len {
        out.push(c.msgs[slot].body[i]);
        i = i + 1;
    }
    let id = c.msgs[slot].id;
    c.msgs[slot].state = MSG_DELIVERED;
    c.msgs[slot].len = 0;            // the body is gone once delivered: no second read
    c.delivered = c.delivered + 1;
    c.count = c.count - 1;
    return id, CODE_OK;
}

// Drop every message whose deadline has passed. Returns the count expired, and it is safe to
// call from a poll loop: expiry is a property of time, not of anyone asking.
fn ch_expire(c: Channel&, now_ms: i64) -> i64 {
    var n: i64 = 0;
    var i: i64 = 0;
    while i < CH_SLOTS {
        if c.msgs[i].state == MSG_QUEUED && c.msgs[i].id != 0 && now_ms >= c.msgs[i].deadline_ms {
            c.msgs[i].state = MSG_EXPIRED;
            c.msgs[i].len = 0;
            c.expired = c.expired + 1;
            c.count = c.count - 1;
            n = n + 1;
        }
        i = i + 1;
    }
    return n;
}

// ---------------------------------------------------------------------------
// Reporting
// ---------------------------------------------------------------------------

fn ch_pending_for(c: Channel&, h: i64) -> i64 {
    var n: i64 = 0;
    var i: i64 = 0;
    while i < CH_SLOTS {
        if c.msgs[i].state == MSG_QUEUED && c.msgs[i].id != 0 && c.msgs[i].to_handle == h { n = n + 1; }
        i = i + 1;
    }
    return n;
}

// (sent, delivered, rejected, expired) -- the four counters the health line reports. A
// rejected count that climbs while delivered stays flat is a misconfigured capability.
fn ch_stats(c: Channel&) -> i64, i64, i64, i64 {
    return c.sent, c.delivered, c.rejected, c.expired;
}

fn ch_state_name(s: i64) -> const u8[:] {
    if s == MSG_QUEUED { return "queued"; }
    if s == MSG_DELIVERED { return "delivered"; }
    if s == MSG_EXPIRED { return "expired"; }
    return "rejected";
}

// One line per channel: "queued 2 sent 14 delivered 11 rejected 1 expired 2 full 0".
fn ch_status(c: Channel&, out: u8[>..]&, cap: i64) -> bool {
    if !append_str(out, cap, "queued ") { return false; }
    if !append_int(out, cap, c.count) { return false; }
    if !append_str(out, cap, " sent ") { return false; }
    if !append_int(out, cap, c.sent) { return false; }
    if !append_str(out, cap, " delivered ") { return false; }
    if !append_int(out, cap, c.delivered) { return false; }
    if !append_str(out, cap, " rejected ") { return false; }
    if !append_int(out, cap, c.rejected) { return false; }
    if !append_str(out, cap, " expired ") { return false; }
    if !append_int(out, cap, c.expired) { return false; }
    if !append_str(out, cap, " full ") { return false; }
    return append_int(out, cap, c.full_events);
}

// ---------------------------------------------------------------------------
// Internals
// ---------------------------------------------------------------------------

fn ch_free_slot(c: Channel&) -> i64 {
    var i: i64 = 0;
    while i < CH_SLOTS {
        // A delivered or expired slot is reusable: its metadata has already been counted.
        if c.msgs[i].state == MSG_DELIVERED || c.msgs[i].state == MSG_EXPIRED || c.msgs[i].id == 0 { return i; }
        i = i + 1;
    }
    return -1;
}

// Oldest by id, not by slot index: slots are reused, and "oldest slot" is the message that
// happened to land lowest, which after a few deliveries is the newest one.
fn ch_oldest_for(c: Channel&, h: i64) -> i64 {
    var best: i64 = -1;
    var best_id: i64 = 0;
    var i: i64 = 0;
    while i < CH_SLOTS {
        if c.msgs[i].state == MSG_QUEUED && c.msgs[i].id != 0 && c.msgs[i].to_handle == h {
            if best < 0 || c.msgs[i].id < best_id {
                best = i;
                best_id = c.msgs[i].id;
            }
        }
        i = i + 1;
    }
    return best;
}
