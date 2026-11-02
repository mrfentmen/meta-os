// services/tests/t85_net_deep.goose
//
// Round 7 B, net — hostile input, the cache at its edges, and the link table.
//
// t67_net proves the round trip: build a packet, parse it back, get the same fields.
// This file feeds the parsers things a hostile peer would send: a length field that
// disagrees with the buffer, a checksum that is present and wrong, an ARP reply for
// another hardware type, a fragment. It also fills the ARP cache and the link table
// to their boundaries and states what happens at MAX and MAX+1.
//
// WHAT IS NOT PROVEN HERE
// -----------------------
// The host shim refuses every frame: sys_net_send and sys_net_recv return -1 by
// design (os-build/layer1/host/host_shim.c). So a *successful* transmit and a
// *successful* receive are NO-HARNESS on this machine. Every refusal path before the
// syscall is driven, and the one path through it is asserted to be E_IO with the
// drop counter incremented once — that is the honest read of "the call was made".
//
// Status: RUNS — set by `audit_status.py` from the runner's row, not by hand.

import net.ip;
import net.arp;
import net.icmp;
import net.udp;
import net.tcp;
import net.packet;
import net.loopback;
import netcfg.netcfg;
import common.err.err;
import common.fmt.fmt;
import common.sys.sys;

var t_pass: i64 = 0;
var t_fail: i64 = 0;

fn say(s: const u8[:]) { let _ = sys_write_serial(s); }

fn check(name: const u8[:], cond: bool) {
    if cond { t_pass = t_pass + 1; say("ok   "); }
    else { t_fail = t_fail + 1; say("FAIL "); }
    say(name);
    say("\n");
}

fn num(label: const u8[:], v: i64) {
    say(label);
    var b: u8[>..] = [];
    let _ = append_int(b, 32, v);
    say(b[..]);
    say("\n");
}

fn buf() -> u8[..1500] {
    var b: u8[..1500] = [0; 1500];
    return b;
}

fn me() -> Ipv4 { return ip4(10, 0, 2, 15); }
fn peer() -> Ipv4 { return ip4(10, 0, 2, 1); }
fn mymac() -> Mac { return mac(0x02, 0x00, 0x00, 0x00, 0x00, 0x15); }
fn peermac() -> Mac { return mac(0x02, 0x00, 0x00, 0x00, 0x00, 0x01); }

// ===========================================================================
// (a1) IPv4

fn t_ip() {
    say("-- (a1) IPv4 parser\n");

    var src = me();
    var dst = peer();
    var b = buf();
    var payload: u8[>..] = [];
    let _ = payload.push(0xde);
    let _ = payload.push(0xad);

    let total, cb = ip_build(b, src, dst, IP_PROTO_UDP, 64, payload[..]);
    check("ip: build", cb == CODE_OK && total == IP_HDR_MIN + 2);
    let v, cp = ip_parse_header(b, total);
    check("ip: round trip parses", cp == CODE_OK);
    check("ip: source preserved", ip4_equal(v.src, src));
    check("ip: destination preserved", ip4_equal(v.dst, dst));
    check("ip: protocol preserved", v.proto == IP_PROTO_UDP);
    check("ip: ttl preserved", v.ttl == 64);
    check("ip: payload length", v.payload_len == 2);
    check("ip: not a fragment", v.frag == 0);

    // Truncated: shorter than a header.
    let _, c2 = ip_parse_header(b, IP_HDR_MIN - 1);
    check("ip: 19-byte buffer is E_CORRUPT", c2 == E_CORRUPT);

    // Version/IHL: anything but 0x45 is refused, not reinterpreted.
    let _ = ip_build(b, src, dst, IP_PROTO_UDP, 64, payload[..]);
    b[0] = 0x44;
    let _, c3 = ip_parse_header(b, total);
    check("ip: version 4 IHL 4 (no options) is E_UNSUPPORTED", c3 == E_UNSUPPORTED);

    // total-length lies: too small is corrupt, too large reads past the buffer.
    let _ = ip_build(b, src, dst, IP_PROTO_UDP, 64, payload[..]);
    b[2] = 0; b[3] = 10;
    let _, c4 = ip_parse_header(b, total);
    check("ip: total length 10 is E_CORRUPT", c4 == E_CORRUPT);

    let _ = ip_build(b, src, dst, IP_PROTO_UDP, 64, payload[..]);
    b[2] = 0; b[3] = 60;
    let _, c5 = ip_parse_header(b, total);
    check("ip: total length past the buffer is E_CORRUPT", c5 == E_CORRUPT);

    // Fragments are refused: this stack does not reassemble, and treating a
    // fragment as a whole packet is how a parser reads half a message.
    let _ = ip_build(b, src, dst, IP_PROTO_UDP, 64, payload[..]);
    b[7] = 1;
    let _, c6 = ip_parse_header(b, total);
    check("ip: fragment offset 1 is E_UNSUPPORTED", c6 == E_UNSUPPORTED);

    // A checksum that is present and wrong is refused.
    let _ = ip_build(b, src, dst, IP_PROTO_UDP, 64, payload[..]);
    b[10] = (b[10] ^ 0xff) as u8;
    let _, c7 = ip_parse_header(b, total);
    check("ip: flipped header checksum is E_CORRUPT", c7 == E_CORRUPT);

    // The parse zeroes and restores the checksum field; if it did not, the next
    // parse of the same buffer would pass for the wrong reason.
    let _ = ip_build(b, src, dst, IP_PROTO_ICMP, 1, payload[..]);
    let _, ca = ip_parse_header(b, total);
    let _, cb2 = ip_parse_header(b, total);
    check("ip: parsing twice in a row succeeds", ca == CODE_OK && cb2 == CODE_OK);

    // Broadcast is for us; another host's unicast is not.
    var bc = ip4_broadcast();
    let v10, _c10 = ip_parse_header(b, total);
    var other = ip4(10, 0, 2, 99);
    check("ip: another host's address is not for us", !ip_for_us(v10, other));

    var bcast = buf();
    let _ = ip_build(bcast, src, bc, IP_PROTO_ICMP, 64, payload[..]);
    let vb, cbcast = ip_parse_header(bcast, total);
    check("ip: a packet addressed to 255.255.255.255 parses", cbcast == CODE_OK);
    check("ip: broadcast destination is for us", ip_for_us(vb, bc));
}

// ===========================================================================
// (a2) ARP

fn t_arp() {
    say("-- (a2) ARP\n");

    var src = me();
    var dst = peer();
    var smac = mymac();
    var dmac = peermac();
    var zero = mac_zero();
    var b = buf();

    let n, cb = arp_build(b, ARP_OP_REQUEST, smac, src, zero, dst);
    check("arp: build a request", cb == CODE_OK && n == ARP_LEN);
    let m, cp = arp_parse(b, n);
    check("arp: round trip parses (build and parse agree on the protocol field)", cp == CODE_OK);
    check("arp: opcode preserved", m.op == ARP_OP_REQUEST);
    check("arp: sender ip preserved", ip4_equal(m.sender_ip, src));
    check("arp: target ip preserved", ip4_equal(m.target_ip, dst));

    let r, cr = arp_build(b, ARP_OP_REPLY, dmac, dst, smac, src);
    check("arp: build a reply", cr == CODE_OK && r == ARP_LEN);
    let m2, cp2 = arp_parse(b, r);
    check("arp: reply parses", cp2 == CODE_OK && m2.op == ARP_OP_REPLY);
    check("arp: reply sender mac", mac_eq(m2.sender_mac, dmac));

    let badn, cbad = arp_build(b, 9, smac, src, zero, dst);
    check("arp: opcode 9 refused at build", badn == 0 && cbad == E_INVAL);
    let _, cshort = arp_parse(b, ARP_LEN - 1);
    check("arp: 27-byte message is E_CORRUPT", cshort == E_CORRUPT);

    let _ = arp_build(b, ARP_OP_REQUEST, smac, src, zero, dst);
    b[1] = 6;                                    // hardware type 0x0006
    let _, chw = arp_parse(b, ARP_LEN);
    check("arp: wrong hardware type is E_UNSUPPORTED", chw == E_UNSUPPORTED);

    let _ = arp_build(b, ARP_OP_REQUEST, smac, src, zero, dst);
    b[2] = 0x86; b[3] = 0xdd;                    // IPv6 ethertype on an ARP frame
    let _, cpr = arp_parse(b, ARP_LEN);
    check("arp: wrong protocol type is E_UNSUPPORTED", cpr == E_UNSUPPORTED);

    let _ = arp_build(b, ARP_OP_REQUEST, smac, src, zero, dst);
    b[4] = 8;                                    // hardware length 8
    let _, chl = arp_parse(b, ARP_LEN);
    check("arp: hardware length 8 is E_UNSUPPORTED", chl == E_UNSUPPORTED);

    let _ = arp_build(b, ARP_OP_REQUEST, smac, src, zero, dst);
    b[6] = 0; b[7] = 3;                          // opcode 3
    let _, cop = arp_parse(b, ARP_LEN);
    check("arp: opcode 3 is E_UNSUPPORTED", cop == E_UNSUPPORTED);

    // The cache: a miss, a hit, the TTL boundary.
    arp_cache_clear();
    let miss, hit = arp_cache_lookup(dst, 0);
    check("arp: empty cache misses", !hit);
    check("arp: a miss returns the zero MAC", mac_eq(miss, zero));
    check("arp: count on an empty cache", arp_cache_count(0) == 0);

    arp_cache_put(dst, dmac, 1000);
    let got, hit2 = arp_cache_lookup(dst, 1000);
    check("arp: put then lookup hits", hit2 && mac_eq(got, dmac));
    check("arp: count after one put", arp_cache_count(1000) == 1);

    // Refresh in place: a second put of the same address must not take a slot.
    arp_cache_put(dst, dmac, 2000);
    check("arp: refresh does not consume a second slot", arp_cache_count(2000) == 1);
    check("arp: refresh extends the TTL", arp_cache_count(2000 + ARP_TTL_MS) == 1);

    // Exactly at the TTL the entry is still valid; one millisecond past it, it is
    // gone and its slot is freed.
    let _, hit_at = arp_cache_lookup(dst, 2000 + ARP_TTL_MS);
    check("arp: valid exactly at the TTL", hit_at);
    let past, hit_past = arp_cache_lookup(dst, 2000 + ARP_TTL_MS + 1);
    check("arp: expired one ms past the TTL", !hit_past);
    check("arp: an expired lookup returns the zero MAC", mac_eq(past, zero));
    check("arp: an expired entry is not counted", arp_cache_count(2000 + ARP_TTL_MS + 1) == 0);

    // Fill to ARP_SLOTS, then one past it. There is no refusal: the oldest entry is
    // evicted, because refusing makes the newest host unreachable while a dead entry
    // keeps a slot.
    arp_cache_clear();
    var i: i64 = 0;
    while i < ARP_SLOTS {
        var a = ip4(10, 0, 2, (50 + i) as u8);
        arp_cache_put(a, dmac, 5000 + i);
        i = i + 1;
    }
    check("arp: cache fills to ARP_SLOTS", arp_cache_count(5100) == ARP_SLOTS);
    var newest = ip4(10, 0, 2, 200);
    arp_cache_put(newest, dmac, 6000);
    check("arp: ARP_SLOTS+1 does not grow the cache", arp_cache_count(6000) == ARP_SLOTS);
    let _, hit_new = arp_cache_lookup(newest, 6000);
    check("arp: the newest entry is present after eviction", hit_new);
    var oldest = ip4(10, 0, 2, 50);
    let _, hit_old = arp_cache_lookup(oldest, 6000);
    check("arp: the oldest entry was the one evicted", !hit_old);
    num("     entries after eviction: ", arp_cache_count(6000));

    arp_cache_clear();
    check("arp: clear empties the cache", arp_cache_count(6000) == 0);
}

// ===========================================================================
// (a3) ICMP

fn t_icmp() {
    say("-- (a3) ICMP\n");

    var b = buf();
    var pay: u8[>..] = [];
    var i: i64 = 0;
    while i < 16 {
        let ch: u8 = (65 + (i % 26)) as u8;
        let _ = pay.push(ch);
        i = i + 1;
    }

    let n, cb = icmp_build_echo(b, ICMP_ECHO_REQUEST, 0x1234, 7, pay[..]);
    check("icmp: build an echo request", cb == CODE_OK && n == ICMP_HDR + 16);
    let v, cp = icmp_parse(b, n);
    check("icmp: round trip parses", cp == CODE_OK);
    check("icmp: kind preserved", v.kind == ICMP_ECHO_REQUEST);
    check("icmp: id preserved", v.id == 0x1234);
    check("icmp: seq preserved", v.seq == 7);
    check("icmp: payload length", v.payload_len == 16);
    check("icmp: payload matches what was sent", icmp_payload_matches(b, v, pay[..]));

    // A reply is a reply to us only with the same id AND sequence.
    let _ = icmp_build_echo(b, ICMP_ECHO_REPLY, 0x1234, 7, pay[..]);
    let v2, _cp2 = icmp_parse(b, n);
    check("icmp: reply matches the request", icmp_is_reply_to(v2, 0x1234, 7));
    check("icmp: right id, wrong seq is not our reply", !icmp_is_reply_to(v2, 0x1234, 8));
    check("icmp: wrong id is not our reply", !icmp_is_reply_to(v2, 0x1235, 7));

    let _, cshort = icmp_parse(b, ICMP_HDR - 1);
    check("icmp: 7-byte message is E_CORRUPT", cshort == E_CORRUPT);

    let _ = icmp_build_echo(b, ICMP_ECHO_REPLY, 1, 1, pay[..]);
    b[2] = (b[2] ^ 0xff) as u8;
    let _, cbad = icmp_parse(b, n);
    check("icmp: bad checksum is E_CORRUPT", cbad == E_CORRUPT);

    // Build refuses a payload that would not fit under the MTU.
    var big: u8[>..] = [];
    var k: i64 = 0;
    while k < 1473 {
        let _ = big.push(88);
        k = k + 1;
    }
    let bn, cbig = icmp_build_echo(b, ICMP_ECHO_REQUEST, 1, 1, big[..]);
    check("icmp: 1473-byte payload refused (MTU)", bn == 0 && cbig == E_NOROOM);
}

// ===========================================================================
// (a4) UDP

fn t_udp() {
    say("-- (a4) UDP\n");

    var src = me();
    var dst = peer();
    var b = buf();
    var pay: u8[>..] = [];
    let _ = pay.push(0x41);
    let _ = pay.push(0x42);

    let n, cb = udp_build(b, src, dst, 5353, 53, pay[..]);
    check("udp: build", cb == CODE_OK && n == UDP_HDR + 2);
    let v, cp = udp_parse(b, n, src, dst);
    check("udp: round trip parses", cp == CODE_OK);
    check("udp: source port", v.src_port == 5353);
    check("udp: destination port", v.dst_port == 53);
    check("udp: payload length", v.payload_len == 2);
    check("udp: the checksum verifies", v.checksum_ok);

    // The checksum is bound to the addresses. The same datagram parsed as if it came
    // from a different source must fail: that is the pseudo-header doing its job.
    var notme = ip4(10, 0, 2, 77);
    let _, c2 = udp_parse(b, n, notme, dst);
    check("udp: wrong source address fails the checksum", c2 == E_CORRUPT);

    let _, cshort = udp_parse(b, UDP_HDR - 1, src, dst);
    check("udp: 7-byte datagram is E_CORRUPT", cshort == E_CORRUPT);

    // Length field must equal the datagram: shorter is the overlap attack, longer
    // reads past the buffer.
    let _ = udp_build(b, src, dst, 5353, 53, pay[..]);
    b[4] = 0; b[5] = 4;
    let _, cshort2 = udp_parse(b, n, src, dst);
    check("udp: declared length below the header is E_CORRUPT", cshort2 == E_CORRUPT);

    let _ = udp_build(b, src, dst, 5353, 53, pay[..]);
    b[4] = 0; b[5] = 20;
    let _, clong = udp_parse(b, n, src, dst);
    check("udp: declared length past the datagram is E_CORRUPT", clong == E_CORRUPT);

    let _ = udp_build(b, src, dst, 5353, 53, pay[..]);
    b[6] = (b[6] ^ 0x01) as u8;
    let _, cbad = udp_parse(b, n, src, dst);
    check("udp: a wrong checksum is E_CORRUPT", cbad == E_CORRUPT);

    // A zero checksum means "not computed". It parses, and says so in the flag,
    // rather than being refused (every such peer would be unusable) or silently
    // accepted as verified.
    let _ = udp_build(b, src, dst, 5353, 53, pay[..]);
    b[6] = 0; b[7] = 0;
    let v0, c0 = udp_parse(b, n, src, dst);
    check("udp: zero checksum parses", c0 == CODE_OK);
    check("udp: zero checksum is reported unverified", !v0.checksum_ok);
}

// ===========================================================================
// (a5) TCP

fn t_tcp() {
    say("-- (a5) TCP\n");

    // Sequence arithmetic in the 2^32 space, including the wrap.
    check("tcp: seq_diff forward", seq_diff(10, 5) == 5);
    check("tcp: seq_diff backward", seq_diff(5, 10) == -5);
    check("tcp: seq_diff wraps across zero", seq_diff(1, SEQ_MOD - 1) == 2);
    // Serial arithmetic: SEQ_MOD-1 is one step BEFORE zero, so it is less than 1
    // even though it is a much larger number.
    check("tcp: seq_lt across the wrap", seq_lt(SEQ_MOD - 1, 1));
    check("tcp: 1 is after SEQ_MOD-1", !seq_lt(1, SEQ_MOD - 1));
    check("tcp: seq_advance wraps", seq_advance(SEQ_MOD - 1, 2) == 1);
    check("tcp: seq_le is inclusive", seq_le(5, 5) && !seq_lt(5, 5));

    var src = me();
    var dst = peer();
    var b = buf();
    var pay: u8[>..] = [];
    let _ = pay.push(0x7f);
    let _ = pay.push(0x00);
    let _ = pay.push(0x00);
    let _ = pay.push(0x01);
    let n, cb = tcp_build(b, 1234, 80, 1000, 0, SYN, 4096, pay[..], src, dst);
    check("tcp: build", cb == CODE_OK && n == TCP_HDR_MIN + 4);
    let h, cp = tcp_parse(b, n);
    check("tcp: round trip parses", cp == CODE_OK);
    check("tcp: ports preserved", h.src_port == 1234 && h.dst_port == 80);
    check("tcp: seq preserved", h.seq == 1000);
    check("tcp: flags preserved", h.flags == SYN);
    check("tcp: window preserved", h.window == 4096);
    check("tcp: payload length", h.payload_len == 4);

    let _, cshort = tcp_parse(b, TCP_HDR_MIN - 1);
    check("tcp: 19-byte segment is E_CORRUPT", cshort == E_CORRUPT);

    let _ = tcp_build(b, 1234, 80, 1000, 0, SYN, 4096, pay[..], src, dst);
    b[12] = 0x40;                                // data offset 4 words
    let _, cdo = tcp_parse(b, n);
    check("tcp: data offset below 5 words is E_CORRUPT", cdo == E_CORRUPT);

    let _ = tcp_build(b, 1234, 80, 1000, 0, SYN, 4096, pay[..], src, dst);
    b[12] = 0xf0;                                // 15 words = 60 bytes > 24
    let _, cdo2 = tcp_parse(b, n);
    check("tcp: data offset past the segment is E_CORRUPT", cdo2 == E_CORRUPT);

    // The state machine: the handshake in order, then the close.
    check("tcp: closed + open -> SYN_SENT", tcp_open_active(TS_CLOSED) == TS_SYN_SENT);
    check("tcp: closed + listen -> LISTEN", tcp_open_passive(TS_CLOSED) == TS_LISTEN);
    check("tcp: LISTEN + SYN -> SYN_RECEIVED", tcp_next(TS_LISTEN, SYN) == TS_SYN_RECEIVED);
    check("tcp: SYN_RECEIVED + ACK -> ESTABLISHED", tcp_next(TS_SYN_RECEIVED, ACK) == TS_ESTABLISHED);
    check("tcp: SYN_SENT + SYN+ACK -> ESTABLISHED", tcp_next(TS_SYN_SENT, SYN | ACK) == TS_ESTABLISHED);
    check("tcp: ESTABLISHED + FIN -> CLOSE_WAIT", tcp_next(TS_ESTABLISHED, FIN) == TS_CLOSE_WAIT);
    check("tcp: ESTABLISHED + RST -> CLOSED", tcp_next(TS_ESTABLISHED, RST) == TS_CLOSED);
    check("tcp: close_local from ESTABLISHED -> FIN_WAIT_1", tcp_close_local(TS_ESTABLISHED) == TS_FIN_WAIT_1);
    check("tcp: is_established", tcp_is_established(TS_ESTABLISHED) && !tcp_is_established(TS_LISTEN));
    check("tcp: is_closed", tcp_is_closed(TS_CLOSED) && !tcp_is_closed(TS_TIME_WAIT));

    // The retransmit timer: bounded growth, capped, and it gives up rather than
    // retrying forever.
    var t = tcp_timer_init(1000);
    // A timer that was never armed is never due: init does not start it.
    check("tcp: an unarmed timer is never due", !tcp_timer_due(t, 1000 + RTO_MIN_MS * 10));
    tcp_timer_arm(t, 1000);
    check("tcp: timer is not due one ms early", !tcp_timer_due(t, 1000 + RTO_MIN_MS - 1));
    check("tcp: timer is due at RTO_MIN", tcp_timer_due(t, 1000 + RTO_MIN_MS));
    var i: i64 = 0;
    var capped = true;
    while i < RTO_TRIES + 4 {
        let _ = tcp_timer_expire(t, 1000);
        if t.rto_ms > RTO_MAX_MS { capped = false; }
        i = i + 1;
    }
    check("tcp: RTO never exceeds RTO_MAX", capped);
    check("tcp: retries are bounded by RTO_TRIES", tcp_timer_given_up(t));
}

// ===========================================================================
// (b) Link boundaries

fn t_links() {
    say("-- (b) link boundaries\n");

    // mtu: 576 is the IPv4 minimum that must be accepted; below it is refused.
    let _, c0 = pkt_add_link(0, 2, 0, 0, 0, 0, 1, 575);
    check("pkt: mtu 575 refused (below the IPv4 minimum)", c0 == E_INVAL);
    let _, c1 = pkt_add_link(0, 2, 0, 0, 0, 0, 1, 1514 - ETH_HDR_MIN + 1);
    check("pkt: mtu whose frame exceeds FRAME_MAX refused", c1 == E_INVAL);
    let _, cneg = pkt_add_link(-1, 2, 0, 0, 0, 0, 1, 1500);
    check("pkt: negative link id refused", cneg == E_INVAL);

    let l0, ca = pkt_add_link(0, 2, 0, 0, 0, 0, 1, 1500);
    check("pkt: add link 0 with mtu 1500", ca == CODE_OK && l0 == 0);
    let _, cdup = pkt_add_link(0, 2, 0, 0, 0, 0, 2, 1500);
    check("pkt: duplicate link id refused", cdup == E_STATE);
    check("pkt: bring link 0 up", pkt_set_state(0, LINK_UP) == CODE_OK);
    check("pkt: unknown link state refused", pkt_set_state(0, 7) == E_INVAL);
    check("pkt: set_state on an unknown link", pkt_set_state(9, LINK_UP) == E_NOTFOUND);

    var frame: u8[..1514] = [0; 1514];
    var i: i64 = 0;
    while i < 1514 { frame[i] = 0xaa; i = i + 1; }

    // A frame shorter than the ethernet header is not a frame.
    let sent_tiny = pkt_send(0, frame[..ETH_HDR_MIN - 1]);
    check("pkt: 13-byte frame refused", sent_tiny == E_INVAL);
    let s1, r1, d1 = pkt_stats(0);
    check("pkt: the refusal was counted as a drop", d1 == 1 && s1 == 0 && r1 == 0);

    // A link with the IPv4 minimum MTU: a 1514-byte frame is refused there because
    // the interface would have to fragment, and fragmentation is Layer 3's decision.
    let _, cmtu = pkt_add_link(1, 2, 0, 0, 0, 0, 2, 576);
    check("pkt: add link 1 with mtu 576", cmtu == CODE_OK);
    check("pkt: bring link 1 up", pkt_set_state(1, LINK_UP) == CODE_OK);
    let too_big = pkt_send(1, frame[..1514]);
    check("pkt: a frame past mtu+header is refused", too_big == E_INVAL);
    let _s2, _r2, d2 = pkt_stats(1);
    check("pkt: the oversize refusal was counted on that link", d2 == 1);

    // A legal frame reaches the syscall. On this host the shim returns -1, so the
    // frame is refused with E_IO and counted once: the call was made, and the
    // failure is the harness's, not the stack's.
    let legal = pkt_send(0, frame[..1514]);
    check("pkt: a full-MTU frame on a host is E_IO (shim refuses frames)", legal == E_IO);
    let s3, _r3, d3 = pkt_stats(0);
    check("pkt: the syscall refusal was counted once", d3 == 2);
    check("pkt: a failed send did not increment sent", s3 == 0);

    // Down link: refused before any length check, counted.
    check("pkt: take the link down", pkt_set_state(0, LINK_DOWN) == CODE_OK);
    let down = pkt_send(0, frame[..1500]);
    check("pkt: send on a down link is E_NO_LINK", down == E_NO_LINK);
    let _s4, _r4, d4 = pkt_stats(0);
    check("pkt: the down-link refusal was counted", d4 == 3);

    var rx: u8[..1514] = [0; 1514];
    let got, crx = pkt_recv(0, rx);
    check("pkt: recv on a down link is E_NO_LINK", got == 0 && crx == E_NO_LINK);

    check("pkt: bring the link up", pkt_set_state(0, LINK_UP) == CODE_OK);
    let got2, crx2 = pkt_recv(0, rx);
    check("pkt: recv on an up link reaches the syscall (shim refuses: E_IO)", got2 == 0 && crx2 == E_IO);
    let g3, c3 = pkt_recv(9, rx);
    check("pkt: recv on an unknown link", g3 == 0 && c3 == E_NOTFOUND);

    // Fault is a third state, and it is not up.
    check("pkt: fault the link", pkt_set_state(0, LINK_FAULT) == CODE_OK);
    check("pkt: send on a faulted link is E_NO_LINK", pkt_send(0, frame[..1500]) == E_NO_LINK);

    // Broadcast and addressed-to-us, from the frame's first six bytes.
    var bc: u8[..6] = [0xff; 6];
    check("pkt: all-ones is broadcast", pkt_is_broadcast(bc));
    var one: u8[..6] = [0x02, 0x00, 0x00, 0x00, 0x00, 0x01];
    check("pkt: a unicast address is not broadcast", !pkt_is_broadcast(one));
    check("pkt: broadcast frame is for us", pkt_for_us(0, bc[..]));
    var othermac: u8[..6] = [0x02, 0x00, 0x00, 0x00, 0x00, 0x99];
    check("pkt: another host's MAC is not ours", !pkt_for_us(0, othermac[..]));
    check("pkt: our own MAC is ours (link 0 was added with ...01)", pkt_for_us(0, one[..]));
    var five: u8[..5] = [0x02, 0x00, 0x00, 0x00, 0x00];
    check("pkt: a frame under 6 bytes cannot be for us", !pkt_for_us(0, five[..]));
    check("pkt: for_us on an unknown link", !pkt_for_us(9, bc[..]));

    // Link table: 4 is the ceiling. The fifth is refused, and there is no removal,
    // so a process gets four links for its lifetime.
    let _, cc2 = pkt_add_link(2, 2, 0, 0, 0, 0, 3, 1500);
    let _, cc3 = pkt_add_link(3, 2, 0, 0, 0, 0, 4, 1500);
    check("pkt: four links fit", cc2 == CODE_OK && cc3 == CODE_OK);
    let _, c5 = pkt_add_link(4, 2, 0, 0, 0, 0, 5, 1500);
    check("pkt: the fifth link is E_NOROOM", c5 == E_NOROOM);
    check("pkt: the refused link is not findable", pkt_set_state(4, LINK_UP) == E_NOTFOUND);

    // There is no pkt_remove_link, so a link cannot be taken out of the table and
    // the ceiling is permanent for the process.
    let _, cre_add = pkt_add_link(0, 2, 0, 0, 0, 0, 1, 1500);
    // Refused because the table is full and nothing can free a slot: the ceiling is
    // a lifetime limit, not a concurrent one.
    check("pkt: a link cannot be removed and re-added (no removal exists)", cre_add == E_NOROOM);
}

// ===========================================================================
// (b2) Loopback

fn t_loopback() {
    say("-- (b2) loopback\n");

    var lo = lo_addr();
    var other = ip4(128, 0, 0, 1);
    var priv = ip4(10, 0, 2, 15);
    check("lo: 127.0.0.1 is loopback", lo_is_loopback(lo));
    var hi = ip4(127, 255, 255, 255);
    check("lo: 127.255.255.255 is loopback", lo_is_loopback(hi));
    check("lo: 128.0.0.1 is not loopback", !lo_is_loopback(other));
    check("lo: 10.0.2.15 is not loopback", !lo_is_loopback(priv));

    // A loopback datagram is built and parsed without a link or a syscall.
    var pay: u8[>..] = [];
    let _ = pay.push(0x55);
    let _ = pay.push(0xaa);
    var b = buf();
    let n, cb = lo_build(lo, lo, IP_PROTO_UDP, pay[..], b);
    check("lo: build a loopback packet", cb == CODE_OK && n == IP_HDR_MIN + 2);
    let v, cp = ip_parse_header(b, n);
    check("lo: the loopback packet parses", cp == CODE_OK);
    check("lo: source is loopback", ip4_equal(v.src, lo));
    check("lo: payload length", v.payload_len == 2);

    // Delivery returns the payload, not the header.
    var out: u8[>..] = [];
    let dn, cd = lo_deliver(lo, lo, pay[..], out, 64);
    check("lo: deliver", cd == CODE_OK && dn == 2);
    check("lo: delivered bytes are the payload", out.len == 2 && out[0] == 0x55 && out[1] == 0xaa);

    // A cap too small to hold the payload is refused, not truncated.
    var small: u8[>..] = [];
    let _sn, cs = lo_deliver(lo, lo, pay[..], small, 1);
    check("lo: deliver into a 1-byte cap refused", cs != CODE_OK);
}

fn main() {
    say("t85 net deep\n");
    t_ip();
    t_arp();
    t_icmp();
    t_udp();
    t_tcp();
    t_links();
    t_loopback();

    say("t85 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
}
