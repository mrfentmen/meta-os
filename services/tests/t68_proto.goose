// services/tests/t68_proto.goose
//
// B-L1-106 — Test program: the protocol pack over the B-L1-105 harness.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// t67 checked each protocol module on its own. This file checks what only the harness can
// show: a datagram that is lost and must be retransmitted, a datagram delivered twice, two
// datagrams out of order, and a queue that fills and must say E_BUSY instead of quietly
// dropping. Those are the four behaviours a protocol stack gets wrong when it is only ever
// tested against a loopback that always works.

import common.err.err;
import common.fmt.fmt;
import common.sys.sys;
import netcfg.netcfg;
import net.arp;
import net.icmp;
import net.udp;
import net.tcp;
import tests.harness.link;

var t_pass: i64 = 0;
var t_fail: i64 = 0;

fn say(s: const u8[:]) { let _ = sys_write_serial(s); }

fn check(name: const u8[:], cond: bool) {
    if cond { t_pass = t_pass + 1; say("ok   "); }
    else { t_fail = t_fail + 1; say("FAIL "); }
    say(name);
    say("\n");
}

fn me() -> Ipv4 { return ip4(10, 0, 0, 2); }
fn peer() -> Ipv4 { return ip4(10, 0, 0, 1); }

// Drain the link into `buf` and parse it as TCP. Returns the header; the caller checks
// whether the parse succeeded by looking at the code it passed in.
var link_buf: u8[..1500] = [0; 1500];

fn main() {
    say("t68 protocol pack over the lossy-link harness\n");
    var mymac = mac(2, 0, 0, 0, 0, 2);
    var peermac = mac(2, 0, 0, 0, 0, 1);

    // ================= 1. ARP through the link =================
    var l = link_new();
    var ab: u8[..1500] = [0; 1500];
    var spa = me();
    var tha = mac_zero();
    var tpa = peer();
    let alen, acc = arp_build(ab, 1, mymac, spa, tha, tpa);
    check("build an ARP request", acc == CODE_OK && alen == 28);
    let _, lc1 = link_send(l, ab[..alen]);
    check("ARP request queued", lc1 == CODE_OK && link_pending(l) == 1);

    var ar: u8[..1500] = [0; 1500];
    var reply_spa = peer();
    var reply_tpa = me();
    let rlen, _ = arp_build(ar, 2, peermac, reply_spa, mymac, reply_tpa);
    let _, _ = link_send(l, ar[..rlen]);

    var got: u8[>..] = [];
    let n1, rc1 = link_recv(l, got, 1400);
    check("first packet out is the request", rc1 == CODE_OK && n1 == 28);
    var rb: u8[..1500] = [0; 1500];
    var i: i64 = 0;
    while i < n1 { rb[i] = got[i]; i = i + 1; }
    let m1, mc1 = arp_parse(rb, n1);
    check("parse it as an ARP request", mc1 == CODE_OK && m1.op == 1);

    got = [];
    let n2, rc2 = link_recv(l, got, 1400);
    check("second packet out is the reply", rc2 == CODE_OK && n2 == 28);
    i = 0;
    while i < n2 { rb[i] = got[i]; i = i + 1; }
    let m2, mc2 = arp_parse(rb, n2);
    check("parse it as an ARP reply", mc2 == CODE_OK && m2.op == 2);

    arp_cache_clear();
    var ref_arp_cache_put_1 = peer();
    arp_cache_put(ref_arp_cache_put_1, peermac, 1000);
    var ref_arp_cache_lookup_2 = peer();
    let _, hit = arp_cache_lookup(ref_arp_cache_lookup_2, 1000);
    check("the learned address is remembered", hit);

    // ================= 2. ICMP echo request/reply =================
    var ic: u8[..1500] = [0; 1500];
    let ilen, icc = icmp_build_echo(ic, ICMP_ECHO_REQUEST, 7, 1, "ping");
    check("build an echo request", icc == CODE_OK && ilen == 12);
    let req, rqc = icmp_parse(ic, ilen);
    check("parse the request", rqc == CODE_OK && req.kind == ICMP_ECHO_REQUEST);

    var ir: u8[..1500] = [0; 1500];
    let ilen2, _ = icmp_build_echo(ir, ICMP_ECHO_REPLY, 7, 1, "ping");
    let rep, rpc = icmp_parse(ir, ilen2);
    check("the reply is ours", rpc == CODE_OK && icmp_is_reply_to(rep, 7, 1));
    check("a reply with another sequence is not", !icmp_is_reply_to(rep, 7, 2));
    check("the payload comes back byte for byte", icmp_payload_matches(ir, rep, "ping"));

    // ================= 3. UDP through the link, plus corruption =================
    var u: u8[..1500] = [0; 1500];
    var ref_udp_build_3 = me();
    var ref_udp_build_4 = peer();
    let ulen, uc = udp_build(u, ref_udp_build_3, ref_udp_build_4, 4000, 4001, "hello");
    check("build a datagram", uc == CODE_OK && ulen == 13);
    let _, lc2 = link_send(l, u[..ulen]);
    check("datagram queued", lc2 == CODE_OK);

    got = [];
    let n3, _ = link_recv(l, got, 1400);
    var ub: u8[..1500] = [0; 1500];
    i = 0;
    while i < n3 { ub[i] = got[i]; i = i + 1; }
    var ref_udp_parse_5 = me();
    var ref_udp_parse_6 = peer();
    let dv, dvc = udp_parse(ub, n3, ref_udp_parse_5, ref_udp_parse_6);
    check("parse it back", dvc == CODE_OK && dv.dst_port == 4001 && dv.payload_len == 5);
    check("checksum verified after the trip", dv.checksum_ok);

    // The harness never corrupts bytes; the corruption case belongs here, where the
    // expected failure is written next to the bytes.
    ub[dv.payload_off] = ub[dv.payload_off] ^ 0x20;
    var ref_udp_parse_7 = me();
    var ref_udp_parse_8 = peer();
    let _, badc = udp_parse(ub, n3, ref_udp_parse_7, ref_udp_parse_8);
    check("a flipped payload byte is refused", badc == E_CORRUPT);

    // ================= 4. TCP: a lost SYN is retransmitted =================
    var l2 = link_new();
    var syn: u8[..1500] = [0; 1500];
    let slen, scc = tcp_build(syn, 50000, 80, 1000, 0, SYN, 4096, "", me(), peer());
    check("build a SYN", scc == CODE_OK && slen == 20);

    link_impair(l2, 1, 0, 0);                 // drop every 1st send: the SYN is lost
    let _, dc1 = link_send(l2, syn[..slen]);
    check("a dropped send is still success", dc1 == CODE_OK);
    check("nothing arrives", link_pending(l2) == 0);
    let sent, dropped, _, _ = link_stats(l2);
    check("the loss is counted", sent == 1 && dropped == 1);

    var timer = tcp_timer_init(0);
    tcp_timer_arm(timer, 0);
    check("the RTO has not fired early", !tcp_timer_due(timer, RTO_MIN_MS - 1));
    check("the RTO is due on time", tcp_timer_due(timer, RTO_MIN_MS));
    check("expiry says retransmit", tcp_timer_expire(timer, RTO_MIN_MS));
    check("the backoff doubled", timer.rto_ms == RTO_MIN_MS * 2);

    link_impair(l2, 0, 0, 0);                 // the link is clean again
    let _, _ = link_send(l2, syn[..slen]);
    got = [];
    let n4, rc4 = link_recv(l2, got, 1400);
    check("the retransmitted SYN arrives", rc4 == CODE_OK && n4 == 20);
    var tb: u8[..1500] = [0; 1500];
    i = 0;
    while i < n4 { tb[i] = got[i]; i = i + 1; }
    let th, thc = tcp_parse(tb, n4);
    check("it parses as the same segment", thc == CODE_OK && th.seq == 1000 && (th.flags & SYN) != 0);

    // ================= 5. TCP handshake and orderly close =================
    check("active open", tcp_open_active(TS_CLOSED) == TS_SYN_SENT);
    check("SYN/ACK establishes", tcp_next(TS_SYN_SENT, SYN | ACK) == TS_ESTABLISHED);
    check("passive open", tcp_open_passive(TS_CLOSED) == TS_LISTEN);
    check("SYN in LISTEN moves to SYN_RECEIVED", tcp_next(TS_LISTEN, SYN) == TS_SYN_RECEIVED);

    var cstate = TS_ESTABLISHED;
    cstate = tcp_close_local(cstate);
    check("closing from ESTABLISHED sends FIN", cstate == TS_FIN_WAIT_1);
    cstate = tcp_next(cstate, FIN | ACK);
    check("and waits in TIME_WAIT, not in CLOSED", cstate == TS_TIME_WAIT);

    // ================= 6. A full queue is E_BUSY, never a silent drop =================
    var l3 = link_new();
    var filled = true;
    var j: i64 = 0;
    while j < LINK_SLOTS {
        let _, qc = link_send(l3, syn[..slen]);
        if qc != CODE_OK { filled = false; }
        j = j + 1;
    }
    check("the queue accepts LINK_SLOTS packets", filled && link_pending(l3) == LINK_SLOTS);
    let _, over = link_send(l3, syn[..slen]);
    check("the next one is E_BUSY", over == E_BUSY);
    let _, _, _, delivered = link_stats(l3);
    check("and nothing was silently dropped", delivered == 0 && link_pending(l3) == LINK_SLOTS);

    // ================= 7. Duplicate and reorder knobs do what they say =================
    var l4 = link_new();
    link_impair(l4, 0, 1, 0);                 // duplicate every send
    let _, _ = link_send(l4, syn[..slen]);
    check("a duplicated send queues two", link_pending(l4) == 2);
    // link_stats returns (sent, dropped, duped, delivered); this line used to read the
    // second value, which is DROPPED, so it was checking the wrong counter.
    let _, _, duped, _ = link_stats(l4);
    check("the duplicate is counted", duped == 1);

    var l5 = link_new();
    var pa: u8[..4] = [0; 4];
    pa[0] = 'a'; pa[1] = 'a'; pa[2] = 'a'; pa[3] = 'a';
    var pb: u8[..4] = [0; 4];
    pb[0] = 'b'; pb[1] = 'b'; pb[2] = 'b'; pb[3] = 'b';
    link_impair(l5, 0, 0, 2);                 // reorder the 2nd send
    let _, _ = link_send(l5, pa[..]);
    let _, _ = link_send(l5, pb[..]);
    got = [];
    let n5, _ = link_recv(l5, got, 1400);
    check("the reordered packet comes out first", n5 == 4 && got[0] == 'b');
    got = [];
    let n6, _ = link_recv(l5, got, 1400);
    check("and the other one follows", n6 == 4 && got[0] == 'a');

    // ================= 8. An empty link is not an error =================
    var l6 = link_new();
    got = [];
    let n7, rc7 = link_recv(l6, got, 1400);
    check("an empty link returns zero bytes and CODE_OK", n7 == 0 && rc7 == CODE_OK);

    say("t68 done  pass=");
    var pb2: u8[>..] = [];
    let _ = append_int(pb2, 32, t_pass);
    say(pb2[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
    if t_fail > 0 { sys_exit(1); }
}
