// services/net/loopback.goose
//
// B-L1-105 — Loopback v2, the semantics half (the impairment half is tests/harness/link.goose).
//
// Status: RUNS — reached by tests/t85_net_deep (154 checks, exit 0). Measured 2026-11-02 by audit_status.py.
//
// WHAT v1 DID AND WHY IT WAS NOT ENOUGH
// -------------------------------------
// v1 was one test helper: "an address starting with 127 is local". That is true and it is
// also only half of what loopback means. v2 states the whole contract the stack needs:
//
//   1. WHICH ADDRESSES ARE LOOPBACK. All of 127.0.0.0/8, per RFC 1122 -- not only
//      127.0.0.1. A stack that special-cases the single address sends 127.0.0.2 out on the
//      wire, where nothing answers.
//   2. WHICH ADDRESS THE INTERFACE HAS. 127.0.0.1 with a /8 mask, always configured, never
//      DHCP: the interface exists before any driver does.
//   3. WHERE A DESTINATION GOES. One function decides local / on-subnet / via-gateway, so
//      the three callers (udp, tcp, icmp) cannot disagree about it.
//   4. A DELIVERY PATH THAT STAYS INSIDE. `lo_deliver` copies the datagram back into the
//      caller's receive buffer and reports it, so a socket test can complete a full
//      send/receive round trip with no driver and no peer.
//
// WHAT IT IS NOT
// --------------
// Not an interface abstraction with MTUs and counters. There is one loopback, it is
// always up, and its MTU is the IP MTU. If a second loopback ever appears, that is the day
// this becomes a table -- not before.

import common.err.err;
import netcfg.netcfg;
import net.ip;

let LO_ADDR_A: u8 = 127;
let LO_MTU: i64 = IP_MTU;

fn lo_addr() -> Ipv4 {
    return ip4(127, 0, 0, 1);
}

fn lo_mask() -> Ipv4 {
    return ip4(255, 0, 0, 0);       // /8, per RFC 1122
}

// All of 127.0.0.0/8, not just 127.0.0.1. See the header.
fn lo_is_loopback(addr: Ipv4&) -> bool {
    return addr.a == LO_ADDR_A;
}

fn lo_configured() -> bool {
    // Always: nothing configures loopback, and nothing can un-configure it.
    return true;
}

// ---------------------------------------------------------------------------
// Route selection
// ---------------------------------------------------------------------------

// Where does a packet for `dst` go?
//
//   0 = loopback (deliver locally, never touch a driver)
//   1 = the local interface's own address (also local; a host may address itself)
//   2 = on the interface's subnet (send directly, ARP for dst)
//   3 = off-subnet (send to the gateway, ARP for the gateway)
//
// E_NO_ADDRESS when the interface has no address: an unconfigured machine must fail to
// send rather than pick a route from 0.0.0.0, which is how a packet gets a source address
// that no reply can reach.
fn lo_route(dst: Ipv4&, local: Ipv4&, mask: Ipv4&, gw: Ipv4&) -> i64, i64 {
    if lo_is_loopback(dst) { return 0, CODE_OK; }
    if ip4_zero(local) { return -1, E_NO_ADDRESS; }
    if ip4_equal(dst, local) { return 1, CODE_OK; }
    if ip4_same_subnet(dst, local, mask) { return 2, CODE_OK; }
    if ip4_zero(gw) { return -1, E_UNREACHABLE; }
    return 3, CODE_OK;
}

// The address an outgoing packet carries as its source. Loopback traffic sources from
// 127.0.0.1 so that a datagram delivered by lo_deliver looks exactly like one that went
// out and came back.
fn lo_source_for(route: i64, local: Ipv4&) -> Ipv4 {
    if route == 0 { return lo_addr(); }
    return local;
}

// ---------------------------------------------------------------------------
// Delivery
// ---------------------------------------------------------------------------

// Copy a datagram to the receive side. This is the loopback driver's whole transmit path:
// the bytes are copied, the length is returned, and nothing leaves the machine.
//
// Refuses an oversized datagram (E_NOROOM) rather than truncating it: a truncated
// datagram that still parses is a payload corruption the application will blame on the
// far end.
fn lo_deliver(src: Ipv4&, dst: Ipv4&, payload: const u8[:], out: u8[>..]&, cap: i64) -> i64, i64 {
    if !lo_is_loopback(dst) && !ip4_equal(dst, src) { return 0, E_UNREACHABLE; }
    if payload.len > LO_MTU { return 0, E_NOROOM; }
    if payload.len > cap { return 0, E_NOROOM; }
    var i: i64 = 0;
    while i < payload.len {
        out.push(payload[i]);
        i = i + 1;
    }
    return payload.len, CODE_OK;
}

// Build the full IP datagram a loopback send would produce, so a test can assert on the
// header as well as the payload -- source 127.0.0.1, TTL 64, the caller's protocol.
fn lo_build(src: Ipv4&, dst: Ipv4&, proto: i64, payload: const u8[:], pkt: u8[..1500]&) -> i64, i64 {
    if payload.len > LO_MTU - IP_HDR_MIN { return 0, E_NOROOM; }
    return ip_build(pkt, src, dst, proto, 64, payload);
}
