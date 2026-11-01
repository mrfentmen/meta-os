// services/tests/t57_dhcp_dns.goose
//
// B-L1-57 — test program for DHCP and DNS over a loopback pair (B-L1-31/B-L1-32).
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// BOTH ENDS ARE IN THIS FILE
// --------------------------
// There is no network here and no mock of one: the test builds the client packet, builds the
// SERVER's reply by hand (the real bytes a real server sends, including the DHCP magic cookie
// and option numbers, and a DNS answer using a compression pointer), and feeds one to the
// other. That is a protocol exercise, not a simulated conversation: if either side gets an
// offset or an option number wrong, the peer in this file rejects it.
//
// The refusals are the interesting half. A DHCP client that binds 0.0.0.0, or a lease of
// zero seconds, or a mask nobody offered, has configured an interface that looks fine and is
// unreachable -- so each of those is built deliberately and must be refused. For DNS, an
// answer whose name is a compression pointer to the wrong offset must fail rather than
// returning the A record that happened to follow.

import dhcp.dhcp;
import dns.dns;
import netcfg.netcfg;
import common.sys.sys;

var t_pass: i64 = 0;
var t_fail: i64 = 0;

fn say(s: const u8[:]) { let _ = sys_write_serial(s); }

fn check(name: const u8[:], cond: bool) {
    if cond { t_pass++; say("ok   "); }
    else { t_fail++; say("FAIL "); }
    say(name);
    say("\n");
}

// ---------------------------------------------------------------------------
// DHCP client side
// ---------------------------------------------------------------------------

fn main() {
    say("t57 dhcp + dns loopback\n");

    var mac: u8[..6] = [0x02, 0x00, 0x5A, 0x11, 0x22, 0x33];
    let xid = 0x5A5A0001;

    var disc: u8[..576] = [];
    let n = dhcp_build_discover(disc, xid, mac);
    check("discover built", n > 243);
    check("discover is a BOOTREQUEST", disc[0] == 1);
    check("hardware type is ethernet", disc[1] == 1 && disc[2] == 6);
    check("xid echoed in the header", dhcp_get_u32(disc, 4) == xid);
    check("mac in chaddr", disc[28] == 0x02 && disc[33] == 0x33);
    check("magic cookie", disc[236] == 0x63 && disc[237] == 0x82 && disc[238] == 0x53 && disc[239] == 0x63);
    check("first option is message type", disc[240] == 53 && disc[241] == 1);
    check("message type is DISCOVER", dhcp_message_type(disc) == DHCP_DISCOVER);

    // --- the server's reply, built here ---
    var ack: u8[..576] = [];
    let ack_len = build_ack(ack, xid, mac, ip4(192, 168, 1, 50), ip4(255, 255, 255, 0),
        ip4(192, 168, 1, 1), 3600, ip4(192, 168, 1, 1));
    check("ack built", ack_len > 0);
    check("ack is a BOOTREPLY", ack[0] == 2);
    check("ack message type", dhcp_message_type(ack) == DHCP_ACK);

    var lease: Lease;
    let lc = dhcp_parse(ack, lease);
    check("ack parsed", lc == CODE_OK);
    check("address from yiaddr", lease.addr.a == 192 && lease.addr.d == 50);
    check("mask offered", lease.mask_given && lease.mask.a == 255 && lease.mask.d == 0);
    check("gateway offered", lease.gw_given && lease.gw.d == 1);
    check("server id", lease.server_given && lease.server_id.d == 1);
    // Seconds in the packet, milliseconds in the lease: the conversion is the whole point.
    check("lease in ms", lease.lease_ms == 3600000);
    // T1/T2 are derived when the server does not send them.
    check("t1 defaults to half", lease.t1_ms == lease.lease_ms / 2);
    check("t2 defaults to 7/8", lease.t2_ms == (lease.lease_ms / 8) * 7);
    check("t2 after t1", lease.t2_ms > lease.t1_ms);

    // --- refusals ---
    // 0.0.0.0 is not an offer.
    var zero_ack: u8[..576] = [];
    let _ = build_ack(zero_ack, xid, mac, ip4(0, 0, 0, 0), ip4(255, 255, 255, 0),
        ip4(192, 168, 1, 1), 3600, ip4(192, 168, 1, 1));
    var bad_lease: Lease;
    check("zero address refused", dhcp_parse(zero_ack, bad_lease) != CODE_OK);

    // No mask offered: refused rather than classful-guessed.
    var no_mask: u8[..576] = [];
    let _ = build_ack_options(no_mask, xid, mac, ip4(10, 0, 0, 9), 3600, 0);
    var nl: Lease;
    check("missing mask refused", dhcp_parse(no_mask, nl) != CODE_OK);

    // A zero lease would renew in a tight loop.
    var zero_lease: u8[..576] = [];
    let _ = build_ack_options(zero_lease, xid, mac, ip4(10, 0, 0, 9), 0, 1);
    var zl: Lease;
    check("zero lease refused", dhcp_parse(zero_lease, zl) != CODE_OK);

    // Truncated packet, wrong cookie, wrong op: each refused.
    var short: u8[..576] = [];
    let _ = build_ack(short, xid, mac, ip4(10, 0, 0, 9), ip4(255, 255, 255, 0), ip4(10, 0, 0, 1), 60, ip4(10, 0, 0, 1));
    check("truncated packet refused", dhcp_parse(short[..100], nl) != CODE_OK);
    short[236] = 0x00;
    check("wrong cookie refused", dhcp_parse(short, nl) != CODE_OK);
    let _ = build_ack(short, xid, mac, ip4(10, 0, 0, 9), ip4(255, 255, 255, 0), ip4(10, 0, 0, 1), 60, ip4(10, 0, 0, 1));
    short[0] = 1;
    check("request parsed as reply refused", dhcp_parse(short, nl) != CODE_OK);

    // --- the client state machine is initialised, not left at zero ---
    var c = dhcp_init(mac, xid);
    check("client starts idle", c.state == D_IDLE);
    check("client remembers its xid", c.xid == xid);
    check("client has no retries yet", c.retries == 0);

    // -----------------------------------------------------------------------
    // DNS
    // -----------------------------------------------------------------------
    var q: u8[..512] = [];
    let qlen = dns_build_a_query(q, "example.com", 0x1234);
    check("query built", qlen > 12);
    check("query id on the wire", be16(q, 0) == 0x1234);
    check("query is a standard query with recursion", (q[2] & 0x01) == 1);
    check("one question", be16(q, 4) == 1);
    check("no answers in a query", be16(q, 6) == 0);
    // The name is three parts: "example", "com", terminator.
    check("name encoded", q[12] == 7 && q[13] == 'e' && q[20] == 3 && q[21] == 'c');
    check("query type is A", be16(q, qlen - 4) == T_A);
    check("query class is IN", be16(q, qlen - 2) == C_IN);

    // --- the server's reply, built here, using a compression pointer ---
    var resp: u8[..512] = [];
    let rlen = build_dns_answer(resp, q, qlen, 0x1234, ip4(93, 184, 216, 34), 300);
    check("response built", rlen > qlen);

    var ans: Answer;
    let ac = dns_parse_a(resp, 0x1234, ans);
    check("answer parsed", ac == CODE_OK);
    check("answer address", ans.addr.a == 93 && ans.addr.d == 34);
    check("answer ttl", ans.ttl == 300);
    check("answer rcode is ok", ans.rcode == RCODE_OK);

    // --- refusals ---
    // Wrong transaction id: a reply that does not match the query is not an answer, however
    // plausible it looks (this is the poisoning path).
    var a2: Answer;
    check("wrong id refused", dns_parse_a(resp, 0x9999, a2) != CODE_OK);

    // NXDOMAIN is an answer with no address: reported as rcode, not as a bogus 0.0.0.0.
    var nx: u8[..512] = [];
    let nxlen = build_dns_answer(nx, q, qlen, 0x1234, ip4(0, 0, 0, 0), 0);
    nx[3] = (nx[3] & 0xF0) | RCODE_NXDOMAIN;
    // Recompute: the answer count stays 1 in this helper, so the parse must look at rcode.
    var a3: Answer;
    let nxc = dns_parse_a(nx, 0x1234, a3);
    check("nxdomain reports its rcode", nxc == CODE_OK && a3.rcode == RCODE_NXDOMAIN);

    // A pointer that leads nowhere must fail rather than read off the end.
    var broken: u8[..512] = [];
    let blen = build_dns_answer(broken, q, qlen, 0x1234, ip4(1, 2, 3, 4), 60);
    broken[qlen + 2] = 0xFF;      // first byte of the answer name: a pointer past the packet
    broken[qlen + 3] = 0xFF;
    var a4: Answer;
    check("dangling compression pointer refused", dns_parse_a(broken, 0x1234, a4) != CODE_OK);

    var r: u8[>..] = [];
    let _ = append_int(r, 32, t_pass);
    say("passed ");
    say(r);
    say("\n");
    if t_fail != 0 { say("FAILURES\n"); sys_exit(1); }
    say("t57 done\n");
    sys_exit(0);
}

// ---------------------------------------------------------------------------
// A DHCP server, in this file
// ---------------------------------------------------------------------------

fn build_ack(out: u8[..576]&, xid: i64, mac: u8[..6]&, yiaddr: Ipv4, mask: Ipv4, gw: Ipv4,
             lease_s: i64, server: Ipv4) -> i64 {
    var i: i64 = 0;
    while i < 240 {
        out[i] = 0;
        i++;
    }
    out[0] = 2;                 // BOOTREPLY
    out[1] = 1;
    out[2] = 6;
    put_u32_be(out, 4, xid);
    put_ip(out, 16, yiaddr);    // yiaddr: the address being offered
    var m: i64 = 0;
    while m < 6 {
        out[28 + m] = mac[m];
        m++;
    }
    out[236] = 0x63;
    out[237] = 0x82;
    out[238] = 0x53;
    out[239] = 0x63;

    var p: i64 = 240;
    p = option_u8(out, p, 53, DHCP_ACK);
    p = option_ip(out, p, 1, mask);
    p = option_ip(out, p, 3, gw);
    p = option_ip(out, p, 54, server);
    p = option_u32(out, p, 51, lease_s);
    out[p] = 255;               // END
    return p + 1;
}

// The same reply with only the address and the lease, so the "no mask" case is a real
// packet rather than a hand-edited one.
fn build_ack_options(out: u8[..576]&, xid: i64, mac: u8[..6]&, yiaddr: Ipv4, lease_s: i64,
                     give_mask: i64) -> i64 {
    var i: i64 = 0;
    while i < 240 {
        out[i] = 0;
        i++;
    }
    out[0] = 2;
    out[1] = 1;
    out[2] = 6;
    put_u32_be(out, 4, xid);
    put_ip(out, 16, yiaddr);
    var m: i64 = 0;
    while m < 6 {
        out[28 + m] = mac[m];
        m++;
    }
    out[236] = 0x63;
    out[237] = 0x82;
    out[238] = 0x53;
    out[239] = 0x63;
    var p: i64 = 240;
    p = option_u8(out, p, 53, DHCP_ACK);
    if give_mask != 0 { p = option_ip(out, p, 1, ip4(255, 255, 255, 0)); }
    p = option_u32(out, p, 51, lease_s);
    out[p] = 255;
    return p + 1;
}

fn option_u8(out: u8[..576]&, p: i64, code: i64, v: i64) -> i64 {
    out[p] = code as u8;
    out[p + 1] = 1;
    out[p + 2] = v as u8;
    return p + 3;
}

fn option_ip(out: u8[..576]&, p: i64, code: i64, v: Ipv4) -> i64 {
    out[p] = code as u8;
    out[p + 1] = 4;
    put_ip(out, p + 2, v);
    return p + 6;
}

fn option_u32(out: u8[..576]&, p: i64, code: i64, v: i64) -> i64 {
    out[p] = code as u8;
    out[p + 1] = 4;
    put_u32_be(out, p + 2, v);
    return p + 6;
}

fn put_u32_be(out: u8[..576]&, at: i64, v: i64) {
    out[at] = ((v >> 24) & 0xFF) as u8;
    out[at + 1] = ((v >> 16) & 0xFF) as u8;
    out[at + 2] = ((v >> 8) & 0xFF) as u8;
    out[at + 3] = (v & 0xFF) as u8;
}

fn put_ip(out: u8[..576]&, at: i64, v: Ipv4) {
    out[at] = v.a;
    out[at + 1] = v.b;
    out[at + 2] = v.c;
    out[at + 3] = v.d;
}

// ---------------------------------------------------------------------------
// A DNS server, in this file
// ---------------------------------------------------------------------------

// Copy the query, set the response bits, and append one A record whose name is a pointer to
// the question's name at offset 12 -- which is what every real server sends.
fn build_dns_answer(out: u8[..512]&, q: u8[..512]&, qlen: i64, id: i64, addr: Ipv4, ttl: i64) -> i64 {
    var i: i64 = 0;
    while i < qlen {
        out[i] = q[i];
        i++;
    }
    out[2] = 0x81;              // response, standard query
    out[3] = 0x80;              // recursion available, rcode 0
    out[6] = 0;
    out[7] = 1;                 // ANCOUNT = 1
    out[8] = 0;
    out[9] = 0;                 // NSCOUNT
    out[10] = 0;
    out[11] = 0;                // ARCOUNT

    var p = qlen;
    out[p] = 0xC0;              // compression pointer to offset 12
    out[p + 1] = 0x0C;
    p = p + 2;
    out[p] = 0;                 // TYPE = A (high byte)
    out[p + 1] = 1;
    p = p + 2;
    out[p] = 0;                 // CLASS = IN
    out[p + 1] = 1;
    p = p + 2;
    put_u32_512(out, p, ttl);
    p = p + 4;
    out[p] = 0;                 // RDLENGTH = 4
    out[p + 1] = 4;
    p = p + 2;
    out[p] = addr.a;
    out[p + 1] = addr.b;
    out[p + 2] = addr.c;
    out[p + 3] = addr.d;
    p = p + 4;
    return p;
}

fn put_u32_512(out: u8[..512]&, at: i64, v: i64) {
    out[at] = ((v >> 24) & 0xFF) as u8;
    out[at + 1] = ((v >> 16) & 0xFF) as u8;
    out[at + 2] = ((v >> 8) & 0xFF) as u8;
    out[at + 3] = (v & 0xFF) as u8;
}

fn be16(pkt: const u8[:], at: i64) -> i64 {
    return (pkt[at] as i64) * 256 + (pkt[at + 1] as i64);
}
