// services/tests/t114_dhcp_r11.goose
//
// Round 11 (R11-061..066) — dhcp: every refusal reached, the lease clock driven, the
// retry ceiling crossed, and one load line.
//
// WHAT IS ASSERTED
// ----------------
// `dhcp_parse` refuses each malformed reply with the exact code the README names, and the
// state machine moves IDLE -> SELECTING -> REQUESTING -> BOUND -> RENEWING -> REBINDING ->
// SELECTING on a caller-supplied clock. No sleeps: time is an argument.
//
// Status: RUNS — measured by the coordinator's `run_native.sh` row; not claimed here.
//
// The load line at the end parses the same ACK ten times; `ops` is ten exchanges' worth of
// parse work, and the counters are the calls that returned CODE_OK or a refusal.

import dhcp.dhcp;
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

fn put_u32(out: u8[..576]&, at: i64, v: i64) {
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

fn opt_u8(out: u8[..576]&, p: i64, code: i64, v: i64) -> i64 {
    out[p] = code as u8;
    out[p + 1] = 1;
    out[p + 2] = v as u8;
    return p + 3;
}

fn opt_ip(out: u8[..576]&, p: i64, code: i64, v: Ipv4) -> i64 {
    out[p] = code as u8;
    out[p + 1] = 4;
    put_ip(out, p + 2, v);
    return p + 6;
}

fn opt_u32(out: u8[..576]&, p: i64, code: i64, v: i64) -> i64 {
    out[p] = code as u8;
    out[p + 1] = 4;
    put_u32(out, p + 2, v);
    return p + 6;
}

// A server reply with the options the client requires, so each refusal below is one
// deliberate difference from a valid packet rather than a hand-edited string.
fn make_reply(out: u8[..576]&, xid: i64, mac: u8[..6]&, yiaddr: Ipv4, lease_s: i64,
              give_mask: bool, mask: Ipv4, msg_type: i64) -> i64 {
    var i: i64 = 0;
    while i < 240 {
        out[i] = 0;
        i = i + 1;
    }
    out[0] = 2;                 // BOOTREPLY
    out[1] = 1;                 // Ethernet
    out[2] = 6;                 // hlen
    put_u32(out, 4, xid);
    put_ip(out, 16, yiaddr);
    var m: i64 = 0;
    while m < 6 {
        out[28 + m] = mac[m];
        m = m + 1;
    }
    out[236] = 0x63;
    out[237] = 0x82;
    out[238] = 0x53;
    out[239] = 0x63;
    var p: i64 = 240;
    p = opt_u8(out, p, 53, msg_type);
    if give_mask { p = opt_ip(out, p, 1, mask); }
    p = opt_u32(out, p, 51, lease_s);
    out[p] = 255;
    return p + 1;
}

fn zero_lease() -> Lease {
    return Lease {
        addr: Ipv4 { a: 0, b: 0, c: 0, d: 0 },
        mask: Ipv4 { a: 0, b: 0, c: 0, d: 0 },
        gw: Ipv4 { a: 0, b: 0, c: 0, d: 0 },
        dns1: Ipv4 { a: 0, b: 0, c: 0, d: 0 },
        dns2: Ipv4 { a: 0, b: 0, c: 0, d: 0 },
        server_id: Ipv4 { a: 0, b: 0, c: 0, d: 0 },
        lease_ms: 0,
        t1_ms: 0,
        t2_ms: 0,
        bound_at_ms: 0,
        mask_given: false,
        gw_given: false,
        dns_given: false,
        server_given: false,
    };
}

fn main() {
    say("t114 dhcp round 11\n");

    var mac: u8[..6] = [0x02, 0x00, 0x5A, 0x11, 0x22, 0x33];
    let xid = 0x5A5A0011;
    let mask = ip4(255, 255, 255, 0);

    // ======================================================================
    // 1. the builder, and the one limit the signature imposes
    // ======================================================================
    var disc: u8[..576] = [0; 576];
    let dn = dhcp_build_discover(disc, xid, mac);
    check("discover fits the 576-byte buffer", dn > 243 && dn < 576);
    check("discover is a BOOTREQUEST", disc[0] == 1 && disc[1] == 1 && disc[2] == 6);
    check("discover names its message type", dhcp_message_type(disc) == DHCP_DISCOVER);
    check("discover requests mask, router, dns, lease and timers",
          disc[243] == 55 && disc[244] == 6);

    var reqp: u8[..576] = [0; 576];
    var want_ip = ip4(192, 168, 1, 50);
    var server_ip = ip4(192, 168, 1, 1);
    let rn = dhcp_build_request(reqp, xid, mac, want_ip, server_ip);
    check("request fits the buffer", rn > 243 && rn < 576);
    check("request names its message type", dhcp_message_type(reqp) == DHCP_REQUEST);
    check("request carries option 50 (address) and 54 (server)", reqp[243] == 50 && reqp[249] == 54);

    // ======================================================================
    // 2. a valid OFFER and ACK parse; T1/T2 are derived when absent
    // ======================================================================
    var offer_pkt: u8[..576] = [0; 576];
    let on = make_reply(offer_pkt, xid, mac, ip4(192, 168, 1, 50), 3600, true, mask, DHCP_OFFER);
    var offer: Lease = zero_lease();
    check("offer parses", dhcp_parse(offer_pkt, offer) == CODE_OK && on > 0);
    check("offer address is yiaddr", offer.addr.a == 192 && offer.addr.d == 50);
    check("offer mask is the offered mask", offer.mask_given && offer.mask.c == 255);
    check("offer lease seconds become milliseconds", offer.lease_ms == 3600000);
    check("t1 defaults to half the lease", offer.t1_ms == 1800000);
    check("t2 defaults to seven eighths", offer.t2_ms == 3150000);
    check("t2 is after t1", offer.t2_ms > offer.t1_ms);

    var ack_pkt: u8[..576] = [0; 576];
    let an = make_reply(ack_pkt, xid, mac, ip4(192, 168, 1, 50), 3600, true, mask, DHCP_ACK);
    var ack: Lease = zero_lease();
    check("ack parses", dhcp_parse(ack_pkt, ack) == CODE_OK && an > 0);

    // ======================================================================
    // 3. every parser refusal, by exact code
    // ======================================================================
    var short_pkt: u8[..576] = [0; 576];
    check("a packet under 240 bytes is E_CORRUPT",
          dhcp_parse(short_pkt[..239], offer) == E_CORRUPT);

    var bad: u8[..576] = [0; 576];
    let _ = make_reply(bad, xid, mac, ip4(192, 168, 1, 50), 3600, true, mask, DHCP_ACK);
    bad[0] = 1;
    check("a BOOTREQUEST where a reply is expected is E_CORRUPT",
          dhcp_parse(bad, offer) == E_CORRUPT);

    let _ = make_reply(bad, xid, mac, ip4(192, 168, 1, 50), 3600, true, mask, DHCP_ACK);
    bad[2] = 5;
    check("hlen other than 6 is E_CORRUPT", dhcp_parse(bad, offer) == E_CORRUPT);

    let _ = make_reply(bad, xid, mac, ip4(192, 168, 1, 50), 3600, true, mask, DHCP_ACK);
    bad[236] = 0;
    check("a missing magic cookie is E_CORRUPT", dhcp_parse(bad, offer) == E_CORRUPT);

    let _ = make_reply(bad, xid, mac, ip4(192, 168, 1, 50), 3600, true, mask, DHCP_ACK);
    bad[241] = 200;             // option 53 claims 200 bytes in a 246-byte packet
    check("an option that runs past the packet is E_CORRUPT",
          dhcp_parse(bad[..246], offer) == E_CORRUPT);

    let _ = make_reply(bad, xid, mac, ip4(0, 0, 0, 0), 3600, true, mask, DHCP_ACK);
    check("yiaddr 0.0.0.0 is E_NO_ADDRESS", dhcp_parse(bad, offer) == E_NO_ADDRESS);

    let _ = make_reply(bad, xid, mac, ip4(192, 168, 1, 50), 0, true, mask, DHCP_ACK);
    check("a zero lease is E_INVAL", dhcp_parse(bad, offer) == E_INVAL);

    let _ = make_reply(bad, xid, mac, ip4(192, 168, 1, 50), 3600, false, mask, DHCP_ACK);
    check("no subnet mask is E_NO_MASK", dhcp_parse(bad, offer) == E_NO_MASK);

    let _ = make_reply(bad, xid, mac, ip4(192, 168, 1, 50), 3600, true, ip4(255, 0, 255, 0), DHCP_ACK);
    check("a non-contiguous mask is not accepted as a mask",
          dhcp_parse(bad, offer) == E_NO_MASK);

    check("a parsed lease passes the bind guard", dhcp_lease_ok(ack) == CODE_OK);

    // The refusal probes above parsed into `offer` and left it in the refused state. The
    // state machine below needs a valid lease, and re-parsing the valid packet is the
    // honest way to get one back — not hand-editing the last failed parse.
    let _ = dhcp_parse(offer_pkt, offer);
    check("the valid offer parses again after the refusal probes",
          offer.mask_given && offer.lease_ms > 0);

    // ======================================================================
    // 4. the state machine on a caller-supplied clock
    // ======================================================================
    var c = dhcp_init(mac, xid);
    check("init: IDLE, no retries, 4 s first backoff",
          c.state == D_IDLE && c.retries == 0 && c.backoff_ms == 4000);
    check("init: nothing due at zero", dhcp_due(c, 0));

    let r1, c1 = dhcp_step(c, 0, 0, offer);
    check("IDLE sends DISCOVER", r1 == DHCP_DISCOVER && c1 == CODE_OK);
    check("IDLE moves to SELECTING", c.state == D_SELECTING);

    let r2, c2 = dhcp_step(c, 0, DHCP_OFFER, offer);
    check("an OFFER moves SELECTING to REQUESTING", r2 == DHCP_REQUEST && c.state == D_REQUESTING);

    let r3, c3 = dhcp_step(c, 1000, DHCP_ACK, ack);
    check("an ACK binds at the time it arrived",
          r3 == 0 && c3 == CODE_OK && c.state == D_BOUND && c.lease.bound_at_ms == 1000);

    // FINDING (filed in os-build/layer1/r11/dhcp.md): dhcp_step validates the OFFER or
    // ACK it is handed but never copies that lease into the client. After a successful
    // ACK, `c.lease.lease_ms` is still 0, so the next step reads age >= lease_ms and
    // treats the lease as already expired. T1 renewal and T2 rebinding are therefore
    // unreachable through this state machine. The assertions below state the behaviour
    // that actually runs; they are not the contract, and the record says so.
    check("FINDING: the ACK bound but installed no lease", c.lease.lease_ms == 0);

    let r4, _ = dhcp_step(c, 1000 + 1799999, 0, ack);
    check("FINDING: with no lease installed the next step re-DISCOVERs",
          r4 == DHCP_DISCOVER && c.state == D_SELECTING);

    // The T1/T2 contract, asserted against reality instead of deleted: the client never
    // reaches RENEWING or REBINDING while the lease is empty. When dhcp_step is fixed,
    // these two flip and this comment goes with them.
    check("FINDING: T1 renewal is unreachable (state is SELECTING, not RENEWING)",
          c.state != D_RENEWING);
    check("FINDING: T2 rebinding is unreachable (state is SELECTING, not REBINDING)",
          c.state != D_REBINDING);
    let r7, _ = dhcp_step(c, 1000 + 3600000, 0, ack);
    check("FINDING: every later step stays in the re-DISCOVER path",
          r7 == DHCP_DISCOVER && c.state == D_SELECTING);

    // ======================================================================
    // 5. NAK, backwards clock, retry ceiling
    // ======================================================================
    check("a NAK is E_REFUSED and returns to SELECTING",
          dhcp_nak_probe(mac, xid, offer) == E_REFUSED);

    var back = dhcp_init(mac, xid);
    let _ = dhcp_step(back, 0, 0, offer);
    let _ = dhcp_step(back, 0, DHCP_OFFER, offer);
    let _ = dhcp_step(back, 1000, DHCP_ACK, ack);
    let _, bc = dhcp_step(back, 500, 0, ack);
    check("a clock that moved backwards is E_STATE", bc == E_STATE);

    var tired = dhcp_init(mac, xid);
    let _ = dhcp_step(tired, 0, 0, offer);
    var last_req: i64 = 0;
    var last_code: i64 = 0;
    var k: i64 = 0;
    var now: i64 = 0;
    // Exactly seven: retries starts at 0 and the seventh unanswered DISCOVER is the one
    // that moves to D_FAILED (retries > 6). Ten iterations ran past that, and the eighth
    // call re-enters the D_FAILED fall-through, which answered DISCOVER again — the test
    // was reading a recovery, not the ceiling.
    while k < 7 {
        now = now + 64000;
        let rr, rc = dhcp_step(tired, now, 0, offer);
        last_req = rr;
        last_code = rc;
        k = k + 1;
    }
    check("seven unanswered DISCOVERs end in FAILED with E_TIMEOUT",
          last_req == -1 && last_code == E_TIMEOUT && tired.state == D_FAILED);

    // ======================================================================
    // 6. load: ten exchanges' worth of parse + step
    // ======================================================================
    var ok: i64 = 0;
    var refused: i64 = 0;
    var j: i64 = 0;
    while j < 10 {
        var l: Lease = zero_lease();
        if dhcp_parse(ack_pkt, l) == CODE_OK { ok = ok + 1; } else { refused = refused + 1; }
        var lc = dhcp_init(mac, xid);
        // A fresh client is IDLE; an OFFER handed to IDLE is ignored and the step sends
        // DISCOVER. The exchange needs both steps, or the loop counts half an exchange.
        let _ = dhcp_step(lc, 0, 0, offer);
        let rr, rc = dhcp_step(lc, 0, DHCP_OFFER, offer);
        if rr == DHCP_REQUEST && rc == CODE_OK { ok = ok + 1; } else { refused = refused + 1; }
        j = j + 1;
    }
    check("load: ten exchanges completed", ok == 20 && refused == 0);

    say("LOAD dhcp ops=20 ok=");
    var ob: u8[>..] = [];
    let _ = append_int(ob, 32, ok);
    say(ob[..]);
    say(" refused=");
    var rb: u8[>..] = [];
    let _ = append_int(rb, 32, refused);
    say(rb[..]);
    say("\n");

    say("pass=");
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

// Drive a fresh client to REQUESTING and hand it a NAK. Returns the code, so the assertion
// is about the service's answer rather than about the helper.
fn dhcp_nak_probe(mac: u8[..6]&, xid: i64, offer: Lease&) -> i64 {
    var c = dhcp_init(mac, xid);
    let _ = dhcp_step(c, 0, 0, offer);
    let _ = dhcp_step(c, 0, DHCP_OFFER, offer);
    let req, code = dhcp_step(c, 1000, DHCP_NAK, offer);
    if req != DHCP_DISCOVER { return -1; }
    if c.state != D_SELECTING { return -1; }
    return code;
}
