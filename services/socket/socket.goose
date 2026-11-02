// services/socket/socket.goose
//
// Layer 4, service 17: what a socket means here.
//
// Status: WRITTEN (not COMPILED). Verified via goose-mcp@1.1.0: structs with
// literals (reference#32), static arrays, `while`/`if`, `T&` references
// (reference#46), multi-value returns.
//
// SCOPE, SAID ONCE
// ----------------
// Datagram sockets. A TCP socket needs buffers, retransmission, windows and a
// connection state machine that belongs in B-L1-99/100, and defining "socket" to mean
// both before either exists produces a contract that fits neither. When TCP lands it
// adds a stream kind to this table -- it does not replace it.
//
// THE TRANSPORT IS NOT HERE
// -------------------------
// This file owns handles, lifetimes, ports and the state machine. Turning a send into
// bytes on a link is B-L1-98 (UDP): `sk_take_send` hands the next queued datagram to
// whatever implements the transport, and there is nothing in this file that pretends to
// have sent it. That split is what keeps a socket test driveable with no network at all.
//
// WHY HANDLES AND NOT INDICES
// ---------------------------
// Same reason the supervisor uses handles (B-L1-22): a slot index handed to a client is
// a slot index that will one day belong to somebody else. A socket handle is
// (slot+1) * 256 + generation, so a closed and reused socket does not answer to its old
// handle.

import common.err.err;
import netcfg.netcfg;

let SK_MAX: i64 = 16;
let SK_GEN_MAX: i64 = 255;
let SK_PORT_MIN: i64 = 1024;        // below 1024 is privileged; nothing here is privileged yet
let SK_PORT_MAX: i64 = 65535;
let SK_EPHEMERAL_MIN: i64 = 49152;
// 512 bytes, not 1400: 16 sockets x 2 queued x 1400 would be 89 KiB of static storage in
// a service that has a 64 KiB allowance (requirement A10), and a queue that cannot be
// allocated is worse than a smaller datagram. B-L1-98 can raise this when the budget is
// measured rather than assumed.
let SK_DGRAM_MAX: i64 = 512;
let SK_QUEUE: i64 = 2;              // datagrams queued per socket

let S_CLOSED: i64 = 0;
let S_OPEN: i64 = 1;
let S_BOUND: i64 = 2;
let S_CONNECTED: i64 = 3;

struct Datagram {
    to: Ipv4,
    port: i64,
    len: i64,
    data: u8[..512],
}

struct Sock {
    state: i64,
    gen: i64,
    local_port: i64,        // 0 = not assigned
    remote: Ipv4,
    remote_port: i64,
    // Outbound queue: a send that cannot be taken immediately is queued, not dropped,
    // because a caller that got CODE_OK from sk_send has been told the data is ours now.
    out_count: i64,
    out_head: i64,
    out: Datagram[..4],
    received: i64,
    sent: i64,
    dropped: i64,
}
var socks: Sock[..16] = [];
var ephemeral_next: i64 = SK_EPHEMERAL_MIN;

// ---------------------------------------------------------------------------
// Handles
// ---------------------------------------------------------------------------

fn sk_handle(slot: i64) -> i64 {
    if slot < 0 || slot >= SK_MAX { return 0; }
    if socks[slot].state == S_CLOSED { return 0; }
    return (slot + 1) * 256 + socks[slot].gen;
}

fn sk_resolve(h: i64) -> i64 {
    if h <= 0 { return -1; }
    let slot = (h / 256) - 1;
    if slot < 0 || slot >= SK_MAX { return -1; }
    if socks[slot].state == S_CLOSED { return -1; }
    if socks[slot].gen != (h % 256) { return -1; }
    return slot;
}

// ---------------------------------------------------------------------------
// Lifetime
// ---------------------------------------------------------------------------

fn sk_open() -> i64, i64 {
    var i: i64 = 0;
    while i < SK_MAX {
        if socks[i].state == S_CLOSED {
            // A fresh generation every time the slot is used: handle 3 from a socket that
            // closed must not reach the socket that took its place.
            socks[i].gen = socks[i].gen + 1;
            if socks[i].gen >= SK_GEN_MAX { socks[i].gen = 1; }
            socks[i].state = S_OPEN;
            socks[i].local_port = 0;
            socks[i].remote = ip4_any();
            socks[i].remote_port = 0;
            socks[i].out_count = 0;
            socks[i].out_head = 0;
            socks[i].received = 0;
            socks[i].sent = 0;
            socks[i].dropped = 0;
            return sk_handle(i), CODE_OK;
        }
        i = i + 1;
    }
    return 0, E_NOROOM;
}

// Bind to a local port. Explicit ports are checked for the privileged range and for
// duplicates; 0 asks for an ephemeral one.
//
// Duplicate detection is a scan, not a table: 16 sockets scanned on bind is nothing, and
// a second structure to keep in step would be the thing that drifts.
fn sk_bind(h: i64, port: i64) -> i64, i64 {
    let slot = sk_resolve(h);
    if slot < 0 { return 0, E_STATE; }
    if socks[slot].state != S_OPEN { return 0, E_STATE; }

    var chosen = port;
    if chosen == 0 {
        chosen = sk_alloc_ephemeral();
        if chosen < 0 { return 0, E_NOROOM; }
    } else {
        if chosen < SK_PORT_MIN || chosen > SK_PORT_MAX { return 0, E_INVAL; }
        if sk_port_in_use(chosen) { return 0, E_BUSY; }
    }
    socks[slot].local_port = chosen;
    socks[slot].state = S_BOUND;
    return chosen, CODE_OK;
}

fn sk_alloc_ephemeral() -> i64 {
    var tries: i64 = 0;
    var candidate = ephemeral_next;
    while tries < 4096 {
        if candidate > SK_PORT_MAX { candidate = SK_EPHEMERAL_MIN; }
        if !sk_port_in_use(candidate) {
            ephemeral_next = candidate + 1;
            if ephemeral_next > SK_PORT_MAX { ephemeral_next = SK_EPHEMERAL_MIN; }
            return candidate;
        }
        candidate = candidate + 1;
        tries = tries + 1;
    }
    return -1;
}

fn sk_port_in_use(port: i64) -> bool {
    var i: i64 = 0;
    while i < SK_MAX {
        if socks[i].state != S_CLOSED && socks[i].local_port == port { return true; }
        i = i + 1;
    }
    return false;
}

fn sk_connect(h: i64, addr: Ipv4&, port: i64) -> i64 {
    let slot = sk_resolve(h);
    if slot < 0 { return E_STATE; }
    if socks[slot].state != S_OPEN && socks[slot].state != S_BOUND { return E_STATE; }
    if port <= 0 || port > SK_PORT_MAX { return E_INVAL; }
    if ip4_zero(addr) { return E_INVAL; }        // 0.0.0.0 is not a destination
    // Connecting a datagram socket is not a handshake: it records a default destination
    // so later sends need not repeat it. Anything claiming otherwise would be TCP.
    socks[slot].remote = addr;
    socks[slot].remote_port = port;
    socks[slot].state = S_CONNECTED;
    return CODE_OK;
}

fn sk_close(h: i64) -> i64 {
    let slot = sk_resolve(h);
    if slot < 0 { return E_STATE; }
    // Queued datagrams are dropped with the socket, and counted: a close that silently
    // discarded three queued sends is a bug report nobody can file.
    if socks[slot].out_count > 0 { socks[slot].dropped = socks[slot].dropped + socks[slot].out_count; }
    socks[slot].state = S_CLOSED;
    socks[slot].local_port = 0;
    socks[slot].out_count = 0;
    socks[slot].out_head = 0;
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// Sending
// ---------------------------------------------------------------------------

// Queue a datagram. On a connected socket the destination is the socket's; otherwise the
// caller must name one, and a send with no destination is refused rather than sent into
// the void.
fn sk_send(h: i64, to: Ipv4&, port: i64, data: const u8[:]) -> i64 {
    let slot = sk_resolve(h);
    if slot < 0 { return E_STATE; }
    if socks[slot].state == S_OPEN { return E_STATE; }      // not even bound
    if data.len == 0 { return E_INVAL; }
    if data.len > SK_DGRAM_MAX { return E_NOROOM; }         // one datagram, not a stream
    if socks[slot].out_count >= SK_QUEUE { return E_BUSY; }

    var dest_ip = to;
    var dest_port = port;
    if socks[slot].state == S_CONNECTED {
        if port == 0 && ip4_zero(to) {
            dest_ip = socks[slot].remote;
            dest_port = socks[slot].remote_port;
        }
    }
    if dest_port <= 0 || dest_port > SK_PORT_MAX { return E_INVAL; }
    if ip4_zero(dest_ip) { return E_INVAL; }

    let at = (socks[slot].out_head + socks[slot].out_count) % SK_QUEUE;
    socks[slot].out[at].to = dest_ip;
    socks[slot].out[at].port = dest_port;
    socks[slot].out[at].len = data.len;
    var i: i64 = 0;
    while i < data.len {
        socks[slot].out[at].data[i] = data[i];
        i = i + 1;
    }
    socks[slot].out_count = socks[slot].out_count + 1;
    return CODE_OK;
}

// Take the next queued datagram for transmission. The caller (the UDP layer) copies it
// out and reports the outcome with sk_send_result -- one in, one out, so a datagram is
// never counted as both queued and sent.
fn sk_take_send(h: i64, out: Datagram&) -> bool {
    let slot = sk_resolve(h);
    if slot < 0 { return false; }
    if socks[slot].out_count <= 0 { return false; }
    out.to = socks[slot].out[socks[slot].out_head].to;
    out.port = socks[slot].out[socks[slot].out_head].port;
    out.len = socks[slot].out[socks[slot].out_head].len;
    var i: i64 = 0;
    while i < out.len {
        out.data[i] = socks[slot].out[socks[slot].out_head].data[i];
        i = i + 1;
    }
    socks[slot].out_head = (socks[slot].out_head + 1) % SK_QUEUE;
    socks[slot].out_count = socks[slot].out_count - 1;
    return true;
}

fn sk_send_result(h: i64, ok: bool) -> i64 {
    let slot = sk_resolve(h);
    if slot < 0 { return E_STATE; }
    if ok { socks[slot].sent = socks[slot].sent + 1; } else { socks[slot].dropped = socks[slot].dropped + 1; }
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// Receiving
// ---------------------------------------------------------------------------

// Match an incoming datagram to a socket by local port. Returns the handle, or 0.
//
// Port 0 never matches: an unbound socket cannot be the destination of anything, and a
// broadcast-to-all fallback would deliver traffic to sockets that never asked for it.
fn sk_match(port: i64) -> i64 {
    if port <= 0 { return 0; }
    var i: i64 = 0;
    while i < SK_MAX {
        if socks[i].state != S_CLOSED && socks[i].local_port == port {
            socks[i].received = socks[i].received + 1;
            return sk_handle(i);
        }
        i = i + 1;
    }
    return 0;
}

fn sk_stats(h: i64) -> i64, i64, i64 {
    let slot = sk_resolve(h);
    if slot < 0 { return 0, 0, E_STATE; }
    return socks[slot].sent, socks[slot].received, socks[slot].dropped;
}
