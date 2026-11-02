// services/net/ip.goose
//
// B-L1-95 — IPv4 header build/parse and checksums.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// ONE ADDRESS TYPE IN THE WHOLE LAYER
// -----------------------------------
// `Ipv4` comes from `netcfg` and is used by netcfg, socket, dhcp, dns and these protocol
// modules. An earlier draft of this file defined its own `Ip4` with i64 fields; that was
// deleted, not aliased. Two address types in one layer is two parsers, two comparisons and
// a conversion at every boundary -- and the conversion is where "10.0.0.1" quietly becomes
// something else.
//
// SCOPE, STATED ONCE
// ------------------
// IPv4 only: no options, no fragmentation (a frame that would need it is refused, not
// silently sent), no IPv6, no routing beyond "on my subnet or hand it to the gateway".
// A fragmenting implementation that is half right is worse than one that says no.
//
// CHECKSUMS ARE COMPUTED, NOT COPIED
// ----------------------------------
// The header checksum is one's-complement over the 20-byte header with the checksum field
// zeroed. The parse side recomputes and refuses a mismatch with E_CORRUPT: a stack that
// trusts a checksum it did not verify delivers corruption to a service and blames it.

import common.err.err;
import netcfg.netcfg;

let IP_HDR_MIN: i64 = 20;
let IP_MTU: i64 = 1500;
let IP_PROTO_ICMP: i64 = 1;
let IP_PROTO_TCP: i64 = 6;
let IP_PROTO_UDP: i64 = 17;
let IP_FLAG_DF: i64 = 0x4000;      // don't fragment

struct IpView {
    src: Ipv4,
    dst: Ipv4,
    proto: i64,
    ttl: i64,
    payload_off: i64,
    payload_len: i64,
    frag: i64,            // fragment offset field as read; 0 means "not a fragment"
}

fn ip_view_none() -> IpView {
    return IpView {
        src: ip4_any(), dst: ip4_any(), proto: 0, ttl: 0,
        payload_off: 0, payload_len: 0, frag: 0,
    };
}

// ---------------------------------------------------------------------------
// Header
// ---------------------------------------------------------------------------

fn ip_sum16(b: u8[..1500]&, off: i64, n: i64) -> i64 {
    var sum: i64 = 0;
    var i = off;
    while i + 1 < off + n {
        sum = sum + (((b[i] as i64) << 8) | (b[i + 1] as i64));
        i = i + 2;
    }
    if (n % 2) != 0 {
        sum = sum + ((b[off + n - 1] as i64) << 8);
    }
    while sum > 0xffff { sum = (sum & 0xffff) + (sum >> 16); }
    return (~sum) & 0xffff;
}

fn ip_build(pkt: u8[..1500]&, src: Ipv4&, dst: Ipv4&, proto: i64, ttl: i64, payload: const u8[:]) -> i64, i64 {
    let total = IP_HDR_MIN + payload.len;
    if total > IP_MTU { return 0, E_NOROOM; }
    if ttl < 1 || ttl > 255 { return 0, E_INVAL; }

    var i: i64 = 0;
    while i < IP_HDR_MIN { pkt[i] = 0; i = i + 1; }
    pkt[0] = 0x45;                                  // v4, 5 words
    pkt[1] = 0;                                     // DSCP/ECN: best effort
    pkt[2] = ((total >> 8) & 0xff) as u8;
    pkt[3] = (total & 0xff) as u8;
    pkt[4] = 0; pkt[5] = 0;                         // identification: 0, we do not fragment
    pkt[6] = ((IP_FLAG_DF >> 8) & 0xff) as u8;
    pkt[7] = 0;
    pkt[8] = (ttl & 0xff) as u8;
    pkt[9] = (proto & 0xff) as u8;
    pkt[10] = 0; pkt[11] = 0;                       // checksum placeholder
    pkt[12] = src.a; pkt[13] = src.b; pkt[14] = src.c; pkt[15] = src.d;
    pkt[16] = dst.a; pkt[17] = dst.b; pkt[18] = dst.c; pkt[19] = dst.d;

    i = 0;
    while i < payload.len {
        pkt[IP_HDR_MIN + i] = payload[i];
        i = i + 1;
    }

    let sum = ip_sum16(pkt, 0, IP_HDR_MIN);
    pkt[10] = ((sum >> 8) & 0xff) as u8;
    pkt[11] = (sum & 0xff) as u8;
    return total, CODE_OK;
}

fn ip_parse_header(pkt: u8[..1500]&, len: i64) -> IpView, i64 {
    if len < IP_HDR_MIN { return ip_view_none(), E_CORRUPT; }
    if (pkt[0] as i64) != 0x45 { return ip_view_none(), E_UNSUPPORTED; }   // options/V6
    let total = (((pkt[2] as i64) << 8) | (pkt[3] as i64));
    if total < IP_HDR_MIN || total > len { return ip_view_none(), E_CORRUPT; }
    let frag = (((pkt[6] as i64) & 0x1f) << 8) | (pkt[7] as i64);
    if frag != 0 { return ip_view_none(), E_UNSUPPORTED; }                 // fragmentation

    // Verify before trusting: zero the field, recompute, compare, restore.
    let stored = (((pkt[10] as i64) << 8) | (pkt[11] as i64));
    pkt[10] = 0; pkt[11] = 0;
    let want = ip_sum16(pkt, 0, IP_HDR_MIN);
    pkt[10] = ((stored >> 8) & 0xff) as u8;
    pkt[11] = (stored & 0xff) as u8;
    if stored != want { return ip_view_none(), E_CORRUPT; }

    return IpView {
        src: ip4(pkt[12], pkt[13], pkt[14], pkt[15]),
        dst: ip4(pkt[16], pkt[17], pkt[18], pkt[19]),
        proto: pkt[9] as i64,
        ttl: pkt[8] as i64,
        payload_off: IP_HDR_MIN,
        payload_len: total - IP_HDR_MIN,
        frag: 0,
    }, CODE_OK;
}

// Is this packet addressed to us, or to everyone? Broadcast is checked first because a
// broadcast frame's destination never equals the interface address, and a receiver that
// checks equality only drops every broadcast on the wire.
fn ip_for_us(v: IpView&, my_addr: Ipv4&) -> bool {
    if ip4_equal(v.dst, my_addr) { return true; }
    if v.dst.a == 255 && v.dst.b == 255 && v.dst.c == 255 && v.dst.d == 255 { return true; }
    return false;
}
