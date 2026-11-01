// services/net/packet.goose
//
// Layer 4, service 13: the packet interface every network service is written against.
//
// Status: WRITTEN (not COMPILED). Verified via goose-mcp@1.1.0: structs with
// literals (reference#32), static arrays, `while`/`if`, slices `a[x..y]`,
// `T&` references (reference#46), extern fn with symbol (spec#40), multi-value returns.
//
// WHY AN INTERFACE AND NOT A DRIVER
// ---------------------------------
// There is no network driver in the kernel yet (K3 is interrupts, K6 is syscalls).
// Writing the DHCP client, the DNS client and the socket layer against a driver means
// all three wait for the driver, and then all three are rewritten when the driver's
// actual shape appears. Writing them against this interface means the driver plugs in
// underneath and none of them change.
//
// The interface is deliberately small: send a frame on a link, receive a frame from a
// link, ask what a link is. Everything else -- IP, ARP, UDP, TCP -- is built on these
// two calls (B-L1-95..101).
//
// WHAT IS A REQUIREMENT VERSUS A FACT HERE
// ----------------------------------------
// FACT: the two externs below are the shape the kernel must provide, and they are
// declared here so the requirement has a name.
// REQUIREMENT: they do not exist. `services/common/sys/sys.goose` declares six calls
// and none of them is a packet. This file is the interface, not its implementation;
// B-L1-73 (bind the packet interface) is the task that turns this into something with
// a backend, and it is blocked on Layer 3.
//
// The counters, framing checks, MTU handling and validation below are all real and
// run today against any backend that implements the two symbols.

import common.err.err;

// The largest frame this layer will carry. 1514 = 14 (Ethernet header) + 1500 (MTU),
// which is the number every other layer assumes; a larger value here would be a frame
// no real link accepts, and a smaller one silently truncates.
let FRAME_MAX: i64 = 1514;
let ETH_HDR_MIN: i64 = 14;

let LINK_DOWN: i64 = 0;
let LINK_UP: i64 = 1;
let LINK_FAULT: i64 = 2;

// ---------------------------------------------------------------------------
// The kernel's side (requirement, not fact)
// ---------------------------------------------------------------------------

// Send one frame on a link. Returns bytes accepted, or a negative error.
// `sys_net_recv` polls: there is no wait primitive in the kernel surface, so a
// receiver polls with a budget (see pkt_recv). Both are declared with explicit C
// symbols because the shim (BUILD.md) links by name.
extern fn sys_net_send(link: i64, frame: const u8[:]) -> i64 = "sys_net_send";
extern fn sys_net_recv(link: i64, out: u8[..1514]&) -> i64 = "sys_net_recv";

// ---------------------------------------------------------------------------
// Links
// ---------------------------------------------------------------------------

struct Link {
    id: i64,                // kernel link index
    mtu: i64,               // payload MTU; FRAME_MAX is the hard ceiling
    mac: u8[..6],
    state: i64,
    sent: i64,
    received: i64,
    dropped: i64,           // frames refused here (too large, link down, bad length)
}
var links: Link[..4];
var link_count: i64 = 0;

fn pkt_add_link(id: i64, mac0: u8, mac1: u8, mac2: u8, mac3: u8, mac4: u8, mac5: u8, mtu: i64) -> i64, i64 {
    if link_count >= 4 { return -1, E_NOROOM; }
    if id < 0 { return -1, E_INVAL; }
    // 576 is the IPv4 minimum every host must accept; below that, DHCP and DNS
    // responses do not fit and the failure appears much later as a truncated message.
    if mtu < 576 || mtu + ETH_HDR_MIN > FRAME_MAX { return -1, E_INVAL; }
    if pkt_find(id) >= 0 { return -1, E_STATE; }

    let l = link_count;
    links[l].id = id;
    links[l].mtu = mtu;
    links[l].mac[0] = mac0;
    links[l].mac[1] = mac1;
    links[l].mac[2] = mac2;
    links[l].mac[3] = mac3;
    links[l].mac[4] = mac4;
    links[l].mac[5] = mac5;
    links[l].state = LINK_DOWN;
    links[l].sent = 0;
    links[l].received = 0;
    links[l].dropped = 0;

    link_count++;
    return l, CODE_OK;
}

fn pkt_find(id: i64) -> i64 {
    var i: i64 = 0;
    while i < link_count {
        if links[i].id == id { return i; }
        i++;
    }
    return -1;
}

fn pkt_set_state(id: i64, state: i64) -> i64 {
    let l = pkt_find(id);
    if l < 0 { return E_NOTFOUND; }
    if state != LINK_DOWN && state != LINK_UP && state != LINK_FAULT { return E_INVAL; }
    links[l].state = state;
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// Sending
// ---------------------------------------------------------------------------

// Send a whole frame. `frame` is the complete link-layer frame including the 14-byte
// header, because a caller that hands over a payload and expects this layer to build a
// header would be guessing at a header this layer does not own.
//
// Refusals are counted, not silent: a frame dropped by the interface is the first thing
// anyone debugging a network failure wants to know about, and a counter is the only
// record that survives the moment it happened.
fn pkt_send(id: i64, frame: const u8[:]) -> i64 {
    let l = pkt_find(id);
    if l < 0 { return E_NOTFOUND; }
    if links[l].state != LINK_UP {
        links[l].dropped++;
        return E_NO_LINK;
    }
    if frame.len < ETH_HDR_MIN {
        links[l].dropped++;
        return E_INVAL;          // too short to be a frame at all
    }
    if frame.len > links[l].mtu + ETH_HDR_MIN {
        links[l].dropped++;
        return E_INVAL;          // would be fragmented by the interface, which is Layer 3's
    }
    let sent = sys_net_send(links[l].id, frame);
    if sent < 0 {
        links[l].dropped++;
        if sent == -2 { return E_NO_LINK; }
        return E_IO;
    }
    // A partial send is a driver bug, not a short frame: a frame either goes or it does
    // not, and pretending half of it went would leave the peer with a broken packet.
    if sent != frame.len {
        links[l].dropped++;
        return E_IO;
    }
    links[l].sent++;
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// Receiving
// ---------------------------------------------------------------------------

// Poll for one frame. Returns (bytes, code); bytes = 0 with CODE_OK means "nothing
// arrived", which is not an error and must not be logged as one -- an idle link would
// otherwise fill the log with failures.
//
// The caller owns the buffer and its lifetime; `out` must be FRAME_MAX.
fn pkt_recv(id: i64, out: u8[..1514]&) -> i64, i64 {
    let l = pkt_find(id);
    if l < 0 { return 0, E_NOTFOUND; }
    if links[l].state != LINK_UP { return 0, E_NO_LINK; }

    let got = sys_net_recv(links[l].id, out);
    if got < 0 {
        if got == -2 { return 0, E_NO_LINK; }
        return 0, E_IO;
    }
    if got == 0 { return 0, CODE_OK; }
    if got < ETH_HDR_MIN || got > FRAME_MAX {
        // A frame shorter than its own header, or larger than the interface allows, is
        // corruption. Refused here rather than passed up for every parser to reject.
        links[l].dropped++;
        return 0, E_CORRUPT;
    }
    links[l].received++;
    return got, CODE_OK;
}

// ---------------------------------------------------------------------------
// Small helpers the protocol layers share
// ---------------------------------------------------------------------------

// Broadcast MAC, the destination every discovery protocol (ARP, DHCP) uses.
fn pkt_is_broadcast(mac: u8[..6]&) -> bool {
    var i: i64 = 0;
    while i < 6 {
        if mac[i] != 0xFF { return false; }
        i++;
    }
    return true;
}

// Is this frame addressed to us? Unicast to our MAC or broadcast. Anything else is
// another host's traffic that a shared medium delivered -- normal on a hub, and never
// something this layer should answer.
fn pkt_for_us(id: i64, frame: const u8[:]) -> bool {
    let l = pkt_find(id);
    if l < 0 { return false; }
    if frame.len < 6 { return false; }
    var i: i64 = 0;
    var all_ff = true;
    var same = true;
    while i < 6 {
        if frame[i] != 0xFF { all_ff = false; }
        if frame[i] != links[l].mac[i] { same = false; }
        i++;
    }
    return all_ff || same;
}

// Counters for the health line (B-L1-124).
fn pkt_stats(id: i64) -> i64, i64, i64 {
    let l = pkt_find(id);
    if l < 0 { return 0, 0, E_NOTFOUND; }
    return links[l].sent, links[l].received, links[l].dropped;
}
