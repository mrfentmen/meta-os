// services/tests/t125_net_r11.goose
//
// Round 11 — net: the link table's capacity, the payload caps nothing had crossed, and
// loopback delivery as a contract rather than a helper.
//
// WHAT t67 AND t85 ALREADY PROVE, AND WHAT THIS ADDS
// --------------------------------------------------
// t67 proves the protocol round trips. t85 feeds hostile input to the parsers and drives
// the ARP cache and one link's MTU edges. Neither fills the link table (four links), sends
// the 14-byte minimum frame, or drives the exact payload ceilings of UDP and ICMP on both
// sides. It also never calls `lo_deliver` or `lo_route` at all: loopback v2 is code with no
// driver, so this file is the only place its delivery path is asserted.
//
// WHAT IS NOT PROVEN HERE
// -----------------------
// A successful transmit needs a backend. The host shim refuses every frame by design, so
// the one send that reaches the syscall is asserted to be E_IO with the drop counter moved
// once — the same honest limitation t85 records.

import net.ip;
import net.arp;
import net.icmp;
import net.udp;
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

fn buf() -> u8[..1500] {
    var b: u8[..1500] = [0; 1500];
    return b;
}

fn me() -> Ipv4 { return ip4(10, 0, 2, 15); }
fn peer() -> Ipv4 { return ip4(10, 0, 2, 1); }
fn mask24() -> Ipv4 { return ip4(255, 255, 255, 0); }

fn t_links() {
    say("-- link table capacity and the minimum frame\n");

    // Four links fit. The fifth is refused, because the table is compiled to four and a
    // table that grows on demand would need an allocation-failure policy at the driver.
    let l0, c0 = pkt_add_link(0, 2, 0, 0, 0, 0, 1, 1500);
    check("pkt: link 0 is slot 0", l0 == 0 && c0 == CODE_OK);
    let _dup0, cdup0 = pkt_add_link(0, 2, 0, 0, 0, 0, 9, 1500);
    check("pkt: a duplicate id is E_STATE while the table has room", cdup0 == E_STATE);
    let l1, c1 = pkt_add_link(1, 2, 0, 0, 0, 0, 2, 576);
    check("pkt: link 1 is slot 1", l1 == 1 && c1 == CODE_OK);
    let l2, c2 = pkt_add_link(2, 2, 0, 0, 0, 0, 3, 1500);
    check("pkt: link 2 is slot 2", l2 == 2 && c2 == CODE_OK);
    let l3, c3 = pkt_add_link(3, 2, 0, 0, 0, 0, 4, 1500);
    check("pkt: link 3 is slot 3", l3 == 3 && c3 == CODE_OK);
    let _l4, c4 = pkt_add_link(4, 2, 0, 0, 0, 0, 5, 1500);
    check("pkt: the fifth link is E_NOROOM", c4 == E_NOROOM);
    let _dup, cdup = pkt_add_link(0, 2, 0, 0, 0, 0, 9, 1500);
    check("pkt: with the table full, capacity is refused before the duplicate (E_NOROOM)",
          cdup == E_NOROOM);

    check("pkt: all four links come up",
          pkt_set_state(0, LINK_UP) == CODE_OK && pkt_set_state(1, LINK_UP) == CODE_OK
          && pkt_set_state(2, LINK_UP) == CODE_OK && pkt_set_state(3, LINK_UP) == CODE_OK);

    check("pkt: send on an unknown link is E_NOTFOUND", pkt_send(9, "frame") == E_NOTFOUND);

    // The 14-byte minimum is a frame: header only, no payload. It reaches the shim, which
    // refuses it here, so the assertion is about the path, not about the wire.
    var f14: u8[..14] = [0; 14];
    f14[0] = 0x02; f14[1] = 0x00; f14[2] = 0x00;
    f14[3] = 0x00; f14[4] = 0x00; f14[5] = 0x15;
    let s14 = pkt_send(0, f14[..]);
    check("pkt: a 14-byte frame reaches the syscall (E_IO on this host)", s14 == E_IO);
    let sent, recv, drops = pkt_stats(0);
    check("pkt: the failed send is counted as a drop", drops == 1 && sent == 0 && recv == 0);

    // Addressed-to-us: our MAC, broadcast, or another host's frame.
    var f: u8[..1514] = [0; 1514];
    // Link 0 was added with MAC 02:00:00:00:00:01, so "for us" is that address.
    f[0] = 0x02; f[1] = 0x00; f[2] = 0x00;
    f[3] = 0x00; f[4] = 0x00; f[5] = 0x01;
    check("pkt: our unicast address is for us", pkt_for_us(0, f[..14]));
    f[5] = 0x99;
    check("pkt: another host's unicast is not for us", !pkt_for_us(0, f[..14]));
    f[0] = 0xff; f[1] = 0xff; f[2] = 0xff;
    f[3] = 0xff; f[4] = 0xff; f[5] = 0xff;
    check("pkt: broadcast is for us", pkt_for_us(0, f[..14]));
}

fn t_ip_edges() {
    say("-- IP: ttl, the 1500-byte ceiling, odd payloads\n");

    var b = buf();
    var src = me();
    var dst = peer();
    var empty: u8[>..] = [];

    let _n0, cttl0 = ip_build(b, src, dst, IP_PROTO_UDP, 0, empty[..]);
    check("ip: ttl 0 is refused at build", cttl0 == E_INVAL);
    let _n256, cttl256 = ip_build(b, src, dst, IP_PROTO_UDP, 256, empty[..]);
    check("ip: ttl 256 is refused at build", cttl256 == E_INVAL);

    var full: u8[>..] = [];
    var i: i64 = 0;
    while i < 1480 { let _ = full.push(0x42); i = i + 1; }
    let nfull, cfull = ip_build(b, src, dst, IP_PROTO_UDP, 64, full[..]);
    check("ip: a 1480-byte payload makes exactly 1500", cfull == CODE_OK && nfull == 1500);
    let _vfull, cpf = ip_parse_header(b, nfull);
    check("ip: the full-MTU packet parses", cpf == CODE_OK);

    let _oops = full.push(0x42);
    let nbig, cbig = ip_build(b, src, dst, IP_PROTO_UDP, 64, full[..]);
    check("ip: a 1481-byte payload is E_NOROOM", cbig == E_NOROOM && nbig == 0);

    // Odd payload: the checksum folds a trailing byte. A round trip is the assertion, since
    // an odd-length bug shows up as a parse refusal rather than a wrong number.
    var odd: u8[>..] = [];
    let _a = odd.push(0xde);
    let _b = odd.push(0xad);
    let _c = odd.push(0xbe);
    let nodd, codd = ip_build(b, src, dst, IP_PROTO_ICMP, 64, odd[..]);
    let vodd, cpodd = ip_parse_header(b, nodd);
    check("ip: a 3-byte payload round trips", codd == CODE_OK && cpodd == CODE_OK);
    check("ip: the odd payload length is preserved", vodd.payload_len == 3);
}

fn t_udp_edges() {
    say("-- UDP: port bounds and the 1480-byte ceiling\n");

    var b = buf();
    var src = me();
    var dst = peer();
    var pay: u8[>..] = [];
    let _p = pay.push(0x41);

    let _n0, csp0 = udp_build(b, src, dst, 0, 53, pay[..]);
    check("udp: source port 0 is refused", csp0 == E_INVAL);
    let _n1, cdp = udp_build(b, src, dst, 5353, 65536, pay[..]);
    check("udp: destination port 65536 is refused", cdp == E_INVAL);

    var max: u8[>..] = [];
    var i: i64 = 0;
    while i < 1472 { let _ = max.push(0x55); i = i + 1; }
    let nmax, cmax = udp_build(b, src, dst, 5353, 53, max[..]);
    check("udp: payload 1472 fills the IP MTU", cmax == CODE_OK && nmax == 1480);
    let vmax, cpmax = udp_parse(b, nmax, src, dst);
    check("udp: the maximum datagram parses and verifies", cpmax == CODE_OK && vmax.checksum_ok);
    check("udp: the maximum payload length", vmax.payload_len == 1472);

    let _over = max.push(0x55);
    let nover, cover = udp_build(b, src, dst, 5353, 53, max[..]);
    check("udp: payload 1473 is E_NOROOM", cover == E_NOROOM && nover == 0);

    // Zero-length payload: an eight-byte datagram, legal, and the checksum still covers it.
    var zero: u8[>..] = [];
    let nz, cz = udp_build(b, src, dst, 5353, 53, zero[..]);
    let vz, cpz = udp_parse(b, nz, src, dst);
    check("udp: a zero-length payload builds", cz == CODE_OK && nz == UDP_HDR);
    check("udp: a zero-length payload parses", cpz == CODE_OK && vz.payload_len == 0);
    check("udp: the empty datagram checksum verifies", vz.checksum_ok);
}

fn t_icmp_edges() {
    say("-- ICMP: the 1472 ceiling and the classifier\n");

    var b = buf();
    // The cap is the whole ICMP message (1472 = 1500 - 20 IP - 8 ICMP), so the payload
    // maximum is 1464, not 1472. The boundary is asserted on both sides.
    var pay: u8[>..] = [];
    var i: i64 = 0;
    while i < 1464 { let _ = pay.push(0x41); i = i + 1; }
    let nmax, cmax = icmp_build_echo(b, ICMP_ECHO_REQUEST, 1, 1, pay[..]);
    check("icmp: a 1464-byte payload makes 1472", cmax == CODE_OK && nmax == 1472);
    let _over = pay.push(0x41);
    let nover, cover = icmp_build_echo(b, ICMP_ECHO_REQUEST, 1, 1, pay[..]);
    check("icmp: a 1465-byte payload is E_NOROOM", cover == E_NOROOM && nover == 0);

    var small: u8[>..] = [];
    let _s = small.push(0x7a);
    let ns, cns = icmp_build_echo(b, ICMP_ECHO_REPLY, 7, 9, small[..]);
    let v, cp = icmp_parse(b, ns);
    check("icmp: a reply parses", cns == CODE_OK && cp == CODE_OK);
    let name = icmp_classify(v);
    check("icmp: a reply is classified echo-reply", name.len == 10);
    check("icmp: the reply matches its id and seq", icmp_is_reply_to(v, 7, 9));
    check("icmp: the payload matches before mutation", icmp_payload_matches(b, v, small[..]));
    b[ICMP_HDR] = 0x7b;
    check("icmp: one changed byte fails the payload match", !icmp_payload_matches(b, v, small[..]));

    let nd, _cd = icmp_build_echo(b, ICMP_DEST_UNREACH, 0, 0, small[..]);
    let vd, cpd = icmp_parse(b, nd);
    check("icmp: dest-unreachable parses", cpd == CODE_OK);
    check("icmp: dest-unreachable is classified", icmp_classify(vd).len == 16);
}

fn t_loopback() {
    say("-- loopback: routing and delivery\n");

    var lo = ip4(127, 0, 0, 2);
    var notlo = ip4(126, 0, 0, 1);
    check("lo: all of 127/8 is loopback", lo_is_loopback(lo));
    check("lo: 126/8 is not", !lo_is_loopback(notlo));
    check("lo: the interface is always configured", lo_configured());

    var local = me();
    var m = mask24();
    var gw = ip4(10, 0, 2, 1);
    var any = ip4_any();
    var lo1 = ip4(127, 0, 0, 1);

    let r0, c0 = lo_route(ip4(127, 0, 0, 1), local, m, gw);
    check("lo_route: 127/8 is local", r0 == 0 && c0 == CODE_OK);
    let r1, c1 = lo_route(local, local, m, gw);
    check("lo_route: our own address is local", r1 == 1 && c1 == CODE_OK);
    let r2, c2 = lo_route(ip4(10, 0, 2, 99), local, m, gw);
    check("lo_route: same subnet goes direct", r2 == 2 && c2 == CODE_OK);
    let r3, c3 = lo_route(ip4(10, 9, 9, 9), local, m, gw);
    check("lo_route: off-subnet goes via the gateway", r3 == 3 && c3 == CODE_OK);
    let r4, c4 = lo_route(ip4(10, 9, 9, 9), any, m, gw);
    check("lo_route: no address is E_NO_ADDRESS", r4 == -1 && c4 == E_NO_ADDRESS);
    let r5, c5 = lo_route(ip4(10, 9, 9, 9), local, m, any);
    check("lo_route: off-subnet with no gateway is E_UNREACHABLE", r5 == -1 && c5 == E_UNREACHABLE);
    let losrc = lo_source_for(0, local);
    check("lo_source_for: loopback sources from 127.0.0.1",
          ip4_equal(losrc, lo1));

    var payload: u8[>..] = [];
    let _a = payload.push(0x68);
    let _b = payload.push(0x69);
    var out: u8[>..] = [];
    let n, cdel = lo_deliver(local, lo1, payload[..], out, 1500);
    check("lo_deliver: a loopback datagram is delivered", cdel == CODE_OK && n == 2);
    check("lo_deliver: the bytes are copied exactly", out.len == 2 && out[0] == 0x68 && out[1] == 0x69);

    var big: u8[>..] = [];
    var i: i64 = 0;
    while i < 1501 { let _ = big.push(0x01); i = i + 1; }
    var bigout: u8[>..] = [];
    let nb, cb = lo_deliver(local, lo1, big[..], bigout, 4096);
    check("lo_deliver: a datagram past the IP MTU is E_NOROOM", cb == E_NOROOM && nb == 0);
    var small_out: u8[>..] = [];
    let _ns, cs = lo_deliver(local, lo1, payload[..], small_out, 1);
    check("lo_deliver: a caller cap smaller than the payload is E_NOROOM", cs == E_NOROOM);

    var away = ip4(10, 9, 9, 9);
    var out2: u8[>..] = [];
    let _n2, c2b = lo_deliver(local, away, payload[..], out2, 1500);
    check("lo_deliver: a non-loopback destination is E_UNREACHABLE", c2b == E_UNREACHABLE);
}

fn t_load() {
    say("-- load: 100 build/parse round trips\n");

    var b = buf();
    var src = me();
    var dst = peer();
    var pay: u8[>..] = [];
    let _a = pay.push(0x11);
    let _b = pay.push(0x22);
    var ops: i64 = 0;
    var ok: i64 = 0;
    var refused: i64 = 0;
    var i: i64 = 0;
    while i < 100 {
        let n, c = ip_build(b, src, dst, IP_PROTO_UDP, 64, pay[..]);
        let _v, cp = ip_parse_header(b, n);
        let un, uc = udp_build(b, src, dst, 5353, 53, pay[..]);
        let _uv, ucp = udp_parse(b, un, src, dst);
        ops = ops + 1;
        if c == CODE_OK && cp == CODE_OK && uc == CODE_OK && ucp == CODE_OK { ok = ok + 1; }
        else { refused = refused + 1; }
        i = i + 1;
    }
    check("load: every round trip succeeded", ok == ops);
    say("LOAD net ops=");
    var ob: u8[>..] = [];
    let _ = append_int(ob, 32, ops);
    say(ob[..]);
    say(" ok=");
    ob = [];
    let _ = append_int(ob, 32, ok);
    say(ob[..]);
    say(" refused=");
    ob = [];
    let _ = append_int(ob, 32, refused);
    say(ob[..]);
    say("\n");
}

fn main() {
    say("t125 net r11\n");
    t_links();
    t_ip_edges();
    t_udp_edges();
    t_icmp_edges();
    t_loopback();
    t_load();
    say("t125 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
    if t_fail > 0 { sys_exit(1); }
}
