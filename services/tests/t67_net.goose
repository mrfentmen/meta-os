// services/tests/t67_net.goose
//
// B-L1-95..100 — protocol pack: IP, ARP, ICMP, UDP, TCP.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHAT THIS IS FOR
// ----------------
// Every module under test computes something a receiver will verify: a checksum, a
// sequence comparison, a length. So the cases are round trips and corruptions, not field
// presences. A header builder that writes the right bytes and a parser that recomputes the
// checksum are tested together, because they have to agree and neither is interesting alone.
//
// The TCP section exists mostly for the wrap: `seq_lt(4294967290, 5)` is the comparison that
// a `<` gets wrong once every 4 GB.

import common.bytes.bytes;
import common.err.err;
import common.fmt.fmt;
import common.sys.sys;
import net.ip;
import net.arp;
import net.icmp;
import net.udp;
import net.tcp;
import netcfg.netcfg;

var t_pass: i64 = 0;
var t_fail: i64 = 0;

fn say(s: const u8[:]) { let _ = sys_write_serial(s); }

fn check(name: const u8[:], cond: bool) {
    if cond { t_pass = t_pass + 1; say("ok   "); }
    else { t_fail = t_fail + 1; say("FAIL "); }
    say(name);
    say("\n");
}

fn a() -> Ipv4 { return ip4(10, 0, 0, 2); }
fn b() -> Ipv4 { return ip4(10, 0, 0, 1); }
fn gw() -> Ipv4 { return ip4(10, 0, 0, 254); }

fn main() {
    say("t67 network protocols\n");

    // ================= IP =================
    let x, ok1 = ip4_parse("192.168.1.20");
    check("parse a dotted quad", ok1 && x.a == 192 && x.d == 20);
    let _, ok2 = ip4_parse("1.2.3");
    check("three parts refused", !ok2);
    let _, ok3 = ip4_parse("1.2.3.256");
    check("256 refused", !ok3);
    let _, ok4 = ip4_parse("1.2.3.4.5");
    check("five parts refused", !ok4);
    let _, ok5 = ip4_parse("1.2.3.");
    check("trailing dot refused", !ok5);
    let _, ok6 = ip4_parse("1.2.3.-4");
    check("negative part refused", !ok6);

    var pkt: u8[..1500] = [];
    var src_ip = a();
    var dst_ip = b();
    let total, bc = ip_build(pkt, src_ip, dst_ip, IP_PROTO_UDP, 64, "payload");
    check("build a packet", bc == CODE_OK && total == 27);
    check("version/ihl byte", pkt[0] == 0x45);
    check("ttl written", pkt[8] == 64);
    check("proto written", pkt[9] == 17);
    check("DF flag set", pkt[6] == 0x40);
    check("src written", pkt[12] == 10 && pkt[15] == 2);
    check("dst written", pkt[16] == 10 && pkt[19] == 1);

    let view, vc = ip_parse_header(pkt, total);
    check("parse our own packet", vc == CODE_OK);
    var want_src = a();
    var want_dst = b();
    check("src round trips", ip4_equal(view.src, want_src));
    check("dst round trips", ip4_equal(view.dst, want_dst));
    check("payload length", view.payload_len == 7);
    check("proto round trips", view.proto == IP_PROTO_UDP);

    pkt[15] = 99;                                  // flip a source byte: checksum must fail
    let _, cbc = ip_parse_header(pkt, total);
    check("corrupt header is refused", cbc == E_CORRUPT);

    var big: u8[>..] = [];
    var i: i64 = 0;
    while i < 1500 { big.push('x'); i = i + 1; }
    var pkt2: u8[..1500] = [];
    var s2 = a();
    var d2 = b();
    let _, oversized = ip_build(pkt2, s2, d2, IP_PROTO_UDP, 64, big[..]);
    check("oversized payload refused", oversized == E_NOROOM);
    let _, ttl0 = ip_build(pkt2, s2, d2, IP_PROTO_UDP, 0, "x");
    check("ttl 0 refused", ttl0 == E_INVAL);

    var bc_pkt: u8[..1500] = [];
    var ref_ip_build_1 = a();
    var ref_ip_build_2 = ip4(255, 255, 255, 255);
    let _bc_len, _bc_code = ip_build(bc_pkt, ref_ip_build_1, ref_ip_build_2, IP_PROTO_UDP, 64, "x");
    let bc_view, _ = ip_parse_header(bc_pkt, 21);
    var my_addr = a();
    var other_addr = gw();
    check("broadcast is for us", ip_for_us(bc_view, my_addr));
    check("someone else's address is not", !ip_for_us(view, other_addr));

    // ================= ARP =================
    var arp_buf: u8[..1500] = [];
    var ref_arp_build_3 = mac(0, 1, 2, 3, 4, 5);
    var ref_arp_build_4 = a();
    var ref_arp_build_5 = mac_zero();
    var ref_arp_build_6 = gw();
    let alen, ac = arp_build(arp_buf, ARP_OP_REQUEST, ref_arp_build_3, ref_arp_build_4, ref_arp_build_5, ref_arp_build_6);
    check("build an ARP request", ac == CODE_OK && alen == 28);
    let msg, mc = arp_parse(arp_buf, alen);
    check("parse it back", mc == CODE_OK && msg.op == ARP_OP_REQUEST);
    var sent_from = a();
    var sent_to = gw();
    check("sender ip", ip4_equal(msg.sender_ip, sent_from));
    check("target ip", ip4_equal(msg.target_ip, sent_to));
    check("sender mac", msg.sender_mac.m5 == 5);
    var ref_arp_build_7 = mac_zero();
    var ref_arp_build_8 = a();
    var ref_arp_build_9 = mac_zero();
    var ref_arp_build_10 = gw();
    let _, bad_op = arp_build(arp_buf, 7, ref_arp_build_7, ref_arp_build_8, ref_arp_build_9, ref_arp_build_10);
    check("unknown ARP op refused at build", bad_op == E_INVAL);
    arp_buf[1] = 6;                                // hardware type 6: not ethernet
    let _, hw = arp_parse(arp_buf, alen);
    check("non-ethernet ARP refused", hw == E_UNSUPPORTED);

    arp_cache_clear();
    var ref_arp_cache_put_11 = gw();
    var ref_arp_cache_put_12 = mac(1, 1, 1, 1, 1, 1);
    arp_cache_put(ref_arp_cache_put_11, ref_arp_cache_put_12, 1000);
    var ref_arp_cache_lookup_13 = gw();
    let cached, hit = arp_cache_lookup(ref_arp_cache_lookup_13, 1000);
    check("cache hit", hit && cached.m0 == 1);
    var ref_arp_cache_lookup_14 = ip4(10, 0, 0, 99);
    let _, miss = arp_cache_lookup(ref_arp_cache_lookup_14, 1000);
    check("cache miss", !miss);
    var ref_arp_cache_lookup_15 = gw();
    let _, expired = arp_cache_lookup(ref_arp_cache_lookup_15, 1000 + ARP_TTL_MS + 1);
    check("entry expires", !expired);
    arp_cache_clear();
    var slot: i64 = 0;
    while slot < 9 {
        var ref_arp_cache_put_16 = ip4(10, 0, 0, (slot + 10) as u8);
        var ref_arp_cache_put_17 = mac(0, 0, 0, 0, 0, slot);
        arp_cache_put(ref_arp_cache_put_16, ref_arp_cache_put_17, 1000 + slot);
        slot = slot + 1;
    }
    check("cache is capped at 8", arp_cache_count(1000) == 8);
    var ref_arp_cache_lookup_18 = ip4(10, 0, 0, 18);
    let _, last = arp_cache_lookup(ref_arp_cache_lookup_18, 1000);
    check("the newest entry is the one that survived", last);

    // ================= ICMP =================
    var ic: u8[..1500] = [];
    let ilen, icc = icmp_build_echo(ic, ICMP_ECHO_REQUEST, 7, 1, "pingdata");
    check("build an echo request", icc == CODE_OK && ilen == 16);
    let req, rqc = icmp_parse(ic, ilen);
    check("parse the request", rqc == CODE_OK && req.kind == ICMP_ECHO_REQUEST);
    check("a request is not a reply to us", !icmp_is_reply_to(req, 7, 1));
    check("classify request", by_eq(icmp_classify(req), "echo-request"));

    var ic2: u8[..1500] = [];
    let rlen, _ = icmp_build_echo(ic2, ICMP_ECHO_REPLY, 7, 1, "pingdata");
    let rep, rpc = icmp_parse(ic2, rlen);
    check("reply is recognised", rpc == CODE_OK && icmp_is_reply_to(rep, 7, 1));
    check("a different sequence is not ours", !icmp_is_reply_to(rep, 7, 2));
    check("payload matches byte for byte", icmp_payload_matches(ic2, rep, "pingdata"));
    check("a different payload does not match", !icmp_payload_matches(ic2, rep, "pingdat"));
    ic2[1] = 1;                                    // corrupt the code byte -> checksum fails
    let _, badc = icmp_parse(ic2, rlen);
    check("corrupt ICMP is refused", badc == E_CORRUPT);

    // ================= UDP =================
    var u: u8[..1500] = [];
    var ref_udp_build_19 = a();
    var ref_udp_build_20 = b();
    let ulen, uc = udp_build(u, ref_udp_build_19, ref_udp_build_20, 40000, 53, "query");
    check("build a datagram", uc == CODE_OK && ulen == 13);
    var ref_udp_parse_21 = a();
    var ref_udp_parse_22 = b();
    let dv, dvc = udp_parse(u, ulen, ref_udp_parse_21, ref_udp_parse_22);
    check("parse it back", dvc == CODE_OK);
    check("ports round trip", dv.src_port == 40000 && dv.dst_port == 53);
    check("payload length", dv.payload_len == 5);
    check("checksum verified", dv.checksum_ok);
    var ref_udp_parse_23 = a();
    var ref_udp_parse_24 = b();
    let _, short = udp_parse(u, ulen - 1, ref_udp_parse_23, ref_udp_parse_24);
    check("truncated datagram refused", short == E_CORRUPT);
    var ref_udp_parse_25 = b();
    var ref_udp_parse_26 = a();
    let _, wronglen = udp_parse(u, ulen, ref_udp_parse_25, ref_udp_parse_26);
    check("wrong pseudo-header refused", wronglen == E_CORRUPT);
    u[6] = 0; u[7] = 0;                            // sender omitted the checksum
    var ref_udp_parse_27 = a();
    var ref_udp_parse_28 = b();
    let dv2, dvc2 = udp_parse(u, ulen, ref_udp_parse_27, ref_udp_parse_28);
    check("zero checksum is accepted but marked unchecked", dvc2 == CODE_OK && !dv2.checksum_ok);

    // ================= TCP =================
    // Wrap arithmetic, the reason this file has a TCP section at all.
    check("seq_lt across the wrap", seq_lt(4294967290, 5));
    check("seq_lt normal order", seq_lt(5, 10));
    check("seq_lt is false the other way", !seq_lt(10, 5));
    check("seq_le equal", seq_le(10, 10));
    check("advance wraps to zero", seq_advance(4294967295, 1) == 0);
    check("diff across the wrap is small positive", seq_diff(5, 4294967290) == 11);
    check("in window", seq_before_window(103, 100, 10));
    check("past the window", !seq_before_window(120, 100, 10));

    var seg: u8[..1500] = [];
    let slen, stc = tcp_build(seg, 1234, 80, 1000, 2000, SYN | ACK, 4096, "", a(), b());
    check("build a SYN/ACK", stc == CODE_OK && slen == 20);
    let th, thc = tcp_parse(seg, slen);
    check("parse the header", thc == CODE_OK);
    check("ports", th.src_port == 1234 && th.dst_port == 80);
    check("seq/ack", th.seq == 1000 && th.ack == 2000);
    check("flags", (th.flags & SYN) != 0 && (th.flags & ACK) != 0);
    check("window", th.window == 4096);
    check("no payload", th.payload_len == 0);
    let _, tiny = tcp_parse(seg, 10);
    check("truncated TCP refused", tiny == E_CORRUPT);

    var seg2: u8[..1500] = [];
    let _s2_len, _s2_code = tcp_build(seg2, 1234, 80, 1001, 2000, PSH | ACK, 4096, "hello", a(), b());
    let th2, _ = tcp_parse(seg2, 25);
    check("payload length in a data segment", th2.payload_len == 5);

    // State machine: the four-way handshake, then the two ways it ends.
    check("active open", tcp_open_active(TS_CLOSED) == TS_SYN_SENT);
    check("SYN/ACK establishes", tcp_next(TS_SYN_SENT, SYN | ACK) == TS_ESTABLISHED);
    check("passive open", tcp_open_passive(TS_CLOSED) == TS_LISTEN);
    check("SYN in LISTEN moves to SYN_RECEIVED", tcp_next(TS_LISTEN, SYN) == TS_SYN_RECEIVED);
    check("ACK completes the passive open", tcp_next(TS_SYN_RECEIVED, ACK) == TS_ESTABLISHED);
    check("FIN in ESTABLISHED is CLOSE_WAIT", tcp_next(TS_ESTABLISHED, FIN) == TS_CLOSE_WAIT);
    check("local close from CLOSE_WAIT is LAST_ACK", tcp_close_local(TS_CLOSE_WAIT) == TS_LAST_ACK);
    check("ACK in LAST_ACK is CLOSED", tcp_next(TS_LAST_ACK, ACK) == TS_CLOSED);
    check("local close from ESTABLISHED is FIN_WAIT_1", tcp_close_local(TS_ESTABLISHED) == TS_FIN_WAIT_1);
    check("ACK in FIN_WAIT_1 is FIN_WAIT_2", tcp_next(TS_FIN_WAIT_1, ACK) == TS_FIN_WAIT_2);
    check("FIN in FIN_WAIT_2 is TIME_WAIT", tcp_next(TS_FIN_WAIT_2, FIN) == TS_TIME_WAIT);
    check("RST closes from anywhere", tcp_next(TS_ESTABLISHED, RST) == TS_CLOSED);
    check("state names are stable", by_eq(tcp_state_name(TS_TIME_WAIT), "TIME_WAIT"));

    // Retransmit: backoff, cap, and giving up.
    var timer = tcp_timer_init(0);
    tcp_timer_arm(timer, 1000);
    check("timer not due yet", !tcp_timer_due(timer, 1100));
    check("timer due after RTO", tcp_timer_due(timer, 1200));
    check("expire keeps going", tcp_timer_expire(timer, 1200));
    check("RTO doubled", timer.rto_ms == 400);
    var k: i64 = 0;
    var alive = true;
    while k < 10 && alive { alive = tcp_timer_expire(timer, 2000 + k); k = k + 1; }
    check("gives up after RTO_TRIES", !alive && tcp_timer_given_up(timer));
    check("RTO is capped", timer.rto_ms <= RTO_MAX_MS);
    tcp_timer_ack(timer, 3000);
    check("an ack resets the backoff", timer.rto_ms == RTO_MIN_MS && timer.tries == 0);

    say("t67 done  pass=");
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
