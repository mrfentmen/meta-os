// services/tests/t116_dns_r11.goose
//
// Round 11, dns (R11-073..078): every limit this resolver declares, every refusal it
// can make, and the query state machine between them.
//
// WHAT IS NEW HERE
// ----------------
// `tests/t79_limit_drivers` proves the three name limits by breaking them and proves
// that a self-referential pointer is refused. It does not prove the jump cap from the
// other side — that a chain of exactly DNS_MAX_JUMPS links still resolves, and the
// thirty-third is what stops it. That boundary is the difference between a cap and a
// parser that refuses long names by accident.
//
// The packet is built here, byte by byte, because a resolver tested against its own
// builder shares the builder's bugs. The answer below is what a server sends: the
// question copied, the response bits set, one A record whose owner is a pointer to
// offset 12.
//
// Status: written for Round 11; run by the coordinator.

import dns.dns;
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

fn be16(pkt: const u8[:], at: i64) -> i64 {
    return (pkt[at] as i64) * 256 + (pkt[at + 1] as i64);
}

fn a4(a: i64, b: i64, c: i64, d: i64) -> Ipv4 {
    return Ipv4 { a: a as u8, b: b as u8, c: c as u8, d: d as u8 };
}

fn put_u32(out: u8[..512]&, at: i64, v: i64) {
    out[at] = ((v >> 24) & 0xFF) as u8;
    out[at + 1] = ((v >> 16) & 0xFF) as u8;
    out[at + 2] = ((v >> 8) & 0xFF) as u8;
    out[at + 3] = (v & 0xFF) as u8;
}

// A server reply: the query with the response bits set, then one A record whose owner
// name is the compression pointer every real server uses (0xC0 0x0C).
fn build_answer(out: u8[..512]&, q: u8[..512]&, qlen: i64, addr: Ipv4, ttl: i64) -> i64 {
    var i: i64 = 0;
    while i < qlen {
        out[i] = q[i];
        i = i + 1;
    }
    out[2] = 0x81;              // QR = 1, RD = 1
    out[3] = 0x80;              // RA = 1, rcode 0
    out[6] = 0;                 // ANCOUNT = 1
    out[7] = 1;
    out[8] = 0;
    out[9] = 0;
    out[10] = 0;
    out[11] = 0;

    var p = qlen;
    out[p] = 0xC0;              // pointer to the question name at 12
    out[p + 1] = 0x0C;
    p = p + 2;
    out[p] = 0;                 // TYPE = A
    out[p + 1] = 1;
    p = p + 2;
    out[p] = 0;                 // CLASS = IN
    out[p + 1] = 1;
    p = p + 2;
    put_u32(out, p, ttl);
    p = p + 4;
    out[p] = 0;                 // RDLENGTH = 4
    out[p + 1] = 4;
    p = p + 2;
    out[p] = addr.a;
    out[p + 1] = addr.b;
    out[p + 2] = addr.c;
    out[p + 3] = addr.d;
    return p + 4;
}

fn main() {
    say("t116 dns round 11\n");

    // ======================================================================
    // 1. building: the header, and the four ways a name cannot be encoded
    // ======================================================================
    var q: u8[..512] = [0; 512];
    let qlen = dns_build_a_query(q, "example.com", 0x1234);
    check("build: a normal name builds", qlen > 12);
    check("build: the id is on the wire, big-endian", be16(q, 0) == 0x1234);
    check("build: recursion desired, opcode 0", q[2] == 0x01);
    check("build: one question, no answers", be16(q, 4) == 1 && be16(q, 6) == 0);
    check("build: the first label is 7 bytes of 'example'", q[12] == 7 && q[13] == 'e');
    check("build: QTYPE A and QCLASS IN at the tail", be16(q, qlen - 4) == T_A && be16(q, qlen - 2) == C_IN);

    // The name loop once reused the header loop's counter and dropped the first 12
    // characters. This asserts the name is encoded from byte 0.
    check("build: the name is encoded from byte 0, not offset 12", q[12] == 7);

    check("build: an empty name is refused", dns_build_a_query(q, "", 1) == -1);
    check("build: a leading dot is an empty label", dns_build_a_query(q, ".com", 1) == -1);
    check("build: a doubled dot is an empty label", dns_build_a_query(q, "a..com", 1) == -1);

    // A trailing dot is legal and must encode the same wire bytes as no trailing dot.
    var qa: u8[..512] = [0; 512];
    var qb: u8[..512] = [0; 512];
    let la = dns_build_a_query(qa, "example.com", 7);
    let lb = dns_build_a_query(qb, "example.com.", 7);
    check("build: a trailing dot is accepted", la > 12 && lb == la);
    var same_name = true;
    var si: i64 = 0;
    while si < la {
        if qa[si] != qb[si] { same_name = false; }
        si = si + 1;
    }
    check("build: trailing dot produces identical bytes", same_name);

    // One label one byte over its own cap. 63 is the largest encodable label.
    var lab63: u8[>..] = [];
    var c63: i64 = 0;
    while c63 < 63 { let _ = lab63.push('a'); c63 = c63 + 1; }
    let _ = lab63.push('.');
    let _ = lab63.push('c');
    let _ = lab63.push('o');
    let _ = lab63.push('m');
    check("build: a 63-byte label is accepted", dns_build_a_query(q, lab63[..], 7) > 0);

    var lab64: u8[>..] = [];
    var c64: i64 = 0;
    while c64 < 64 { let _ = lab64.push('a'); c64 = c64 + 1; }
    let _ = lab64.push('.');
    let _ = lab64.push('c');
    let _ = lab64.push('o');
    let _ = lab64.push('m');
    check("build: a 64-byte label is refused", dns_build_a_query(q, lab64[..], 7) == -1);

    // Exactly 255 bytes is the format's cap: four 63-byte labels plus three dots.
    var nm255: u8[>..] = [];
    var nl: i64 = 0;
    while nl < 4 {
        var cc: i64 = 0;
        while cc < 63 { let _ = nm255.push('a'); cc = cc + 1; }
        if nl < 3 { let _ = nm255.push('.'); }
        nl = nl + 1;
    }
    check("build: a 255-byte name is accepted", dns_build_a_query(q, nm255[..], 7) > 0);
    let _ = nm255.push('b');
    check("build: a 256-byte name is refused", dns_build_a_query(q, nm255[..], 7) == -1);

    // ======================================================================
    // 2. reading names: pointers, and what a pointer may not do
    // ======================================================================
    // A backwards chain of exactly DNS_MAX_JUMPS pointers, rooted at offset 0. This is
    // the success side of the cap: 32 jumps resolve, 33 do not.
    var chain: u8[..256] = [0; 256];
    var ci: i64 = 1;
    while ci <= 33 {
        chain[2 * ci] = 0xC0;
        chain[(2 * ci) + 1] = (2 * (ci - 1)) as u8;
        ci = ci + 1;
    }
    var nb: u8[..256] = [0; 256];
    let _, _, ok32 = dns_read_name(chain[..], 2 * DNS_MAX_JUMPS, nb);
    check("read: exactly DNS_MAX_JUMPS backwards jumps resolve", ok32);
    let _, _, ok33 = dns_read_name(chain[..], 2 * (DNS_MAX_JUMPS + 1), nb);
    check("read: one jump past the cap is refused", !ok33);

    // A forward pointer can read a section the packet is still writing.
    var fwd: u8[..256] = [0; 256];
    fwd[12] = 0xC0;
    fwd[13] = 20;
    let _, _, okf = dns_read_name(fwd[..], 12, nb);
    check("read: a forward pointer is refused", !okf);

    // A pointer to its own offset is a one-instruction infinite loop.
    var selfp: u8[..256] = [0; 256];
    selfp[12] = 0xC0;
    selfp[13] = 12;
    let _, _, oks = dns_read_name(selfp[..], 12, nb);
    check("read: a same-offset pointer is refused", !oks);

    // 0x40 and 0x80 are reserved label types, not lengths.
    var res: u8[..256] = [0; 256];
    res[12] = 0x40;
    let _, _, okr = dns_read_name(res[..], 12, nb);
    check("read: a reserved label type is refused", !okr);

    // A 14-byte packet: the length byte at 12 claims five bytes and only one follows.
    var trunc: u8[..14] = [0; 14];
    trunc[12] = 5;
    let _, _, okt = dns_read_name(trunc[..], 12, nb);
    check("read: a label that runs past the packet is refused", !okt);

    // A name that would decode past 255 bytes is refused, not truncated into a
    // different name.
    var wide: u8[..512] = [0; 512];
    var wa: i64 = 0;
    while wa < 5 {
        wide[wa * 64] = 63;
        var wc: i64 = 0;
        while wc < 63 { wide[(wa * 64) + 1 + wc] = 97; wc = wc + 1; }
        wa = wa + 1;
    }
    wide[5 * 64] = 0;
    var wnb: u8[..256] = [0; 256];
    let _, _, okw = dns_read_name(wide[..], 0, wnb);
    check("read: a name past DNS_NAME_MAX is refused", !okw);

    // ======================================================================
    // 3. parsing: one good answer, then each refusal by name
    // ======================================================================
    // The build section reused `q` for the 63- and 255-byte name probes, so the buffer no
    // longer holds the question these fixtures claim to answer: the A record would be
    // appended at the old qlen, in the middle of a name. Rebuild the canonical question.
    let pqlen = dns_build_a_query(q, "example.com", 0x1234);
    check("parse: the fixture's question is rebuilt", pqlen == qlen);
    var resp: u8[..512] = [0; 512];
    let rlen = build_answer(resp, q, pqlen, a4(93, 184, 216, 34), 300);
    check("parse: the reply is longer than the question", rlen > pqlen);

    var ans: Answer = Answer { addr: Ipv4 { a: 0, b: 0, c: 0, d: 0 }, ttl: 0, rcode: 0 };
    let ac = dns_parse_a(resp, 0x1234, ans);
    check("parse: a well-formed answer parses", ac == CODE_OK);
    check("parse: the address is the record's", ans.addr.a == 93 && ans.addr.d == 34);
    check("parse: the ttl is the record's", ans.ttl == 300);
    check("parse: rcode is OK", ans.rcode == RCODE_OK);

    // Wrong transaction id: a reply to somebody else's question.
    var a2: Answer = Answer { addr: Ipv4 { a: 0, b: 0, c: 0, d: 0 }, ttl: 0, rcode: 0 };
    check("parse: a wrong id is E_STATE", dns_parse_a(resp, 0x9999, a2) == E_STATE);

    // QR clear: not a response at all.
    var notresp: u8[..512] = [0; 512];
    let _ = build_answer(notresp, q, pqlen, a4(1, 1, 1, 1), 60);
    notresp[2] = 0x01;
    check("parse: a query is not a response", dns_parse_a(notresp, 0x1234, a2) == E_CORRUPT);

    // QDCOUNT != 1: a shape this parser does not claim to understand.
    var twoq: u8[..512] = [0; 512];
    let _ = build_answer(twoq, q, pqlen, a4(1, 1, 1, 1), 60);
    twoq[5] = 2;
    check("parse: QDCOUNT != 1 is E_CORRUPT", dns_parse_a(twoq, 0x1234, a2) == E_CORRUPT);

    // ANCOUNT = 0: a working server with nothing to say.
    var noans: u8[..512] = [0; 512];
    let _ = build_answer(noans, q, pqlen, a4(1, 1, 1, 1), 60);
    noans[6] = 0;
    noans[7] = 0;
    check("parse: no answers is E_RESOLVE", dns_parse_a(noans, 0x1234, a2) == E_RESOLVE);

    // An A record whose RDLENGTH is not 4 is a different record pretending to be A.
    var badlen: u8[..512] = [0; 512];
    let _ = build_answer(badlen, q, pqlen, a4(1, 1, 1, 1), 60);
    badlen[pqlen + 11] = 6;
    check("parse: an A record that is not 4 bytes is E_CORRUPT",
          dns_parse_a(badlen, 0x1234, a2) == E_CORRUPT);

    // NXDOMAIN is an answer, not a parse failure: the caller must be able to tell a
    // name that does not exist from a wire that ate the packet.
    var nx: u8[..512] = [0; 512];
    let _ = build_answer(nx, q, pqlen, a4(0, 0, 0, 0), 0);
    nx[3] = ((nx[3] & 0xF0) | RCODE_NXDOMAIN) as u8;
    var a3: Answer = Answer { addr: Ipv4 { a: 0, b: 0, c: 0, d: 0 }, ttl: 0, rcode: 0 };
    let nxc = dns_parse_a(nx, 0x1234, a3);
    check("parse: NXDOMAIN is a reportable answer", nxc == CODE_OK && a3.rcode == RCODE_NXDOMAIN);

    // Any other non-zero rcode is a resolver failure, reported as one.
    var sf: u8[..512] = [0; 512];
    let _ = build_answer(sf, q, pqlen, a4(1, 1, 1, 1), 60);
    sf[3] = ((sf[3] & 0xF0) | RCODE_SERVFAIL) as u8;
    check("parse: SERVFAIL is E_RESOLVE", dns_parse_a(sf, 0x1234, a2) == E_RESOLVE);

    // Truncated before the header is even complete.
    check("parse: a packet under 12 bytes is E_CORRUPT",
          dns_parse_a(resp[..8], 0x1234, a2) == E_CORRUPT);

    // ======================================================================
    // 4. the query state machine
    // ======================================================================
    var qq = dns_query_init(0x77, 1000);
    check("query: starts idle with no attempts", qq.state == Q_IDLE && qq.attempts == 0);
    check("query: idle never expires", !dns_query_expired(qq, 5000));

    dns_query_sent(qq, 1000);
    check("query: sent sets state and counts the attempt", qq.state == Q_SENT && qq.attempts == 1);
    check("query: not expired one millisecond early", !dns_query_expired(qq, 1999));
    check("query: expired exactly at the timeout", dns_query_expired(qq, 2000));
    check("query: a backwards clock counts as expired", dns_query_expired(qq, 500));

    // A packet that is not ours must leave the query waiting, not fail it: on a busy
    // network most arriving packets belong to somebody else.
    var q2 = dns_query_init(0x99, 1000);
    dns_query_sent(q2, 0);
    let not_ours = dns_query_feed(q2, resp);
    check("query: somebody else's reply is E_STATE", not_ours == E_STATE);
    check("query: and the query is still waiting", q2.state == Q_SENT);

    var ours: u8[..512] = [0; 512];
    let _ = build_answer(ours, q, pqlen, a4(10, 0, 0, 7), 60);
    ours[0] = 0;
    ours[1] = 0x77;
    let fed = dns_query_feed(qq, ours);
    check("query: our answer completes it", fed == CODE_OK && qq.state == Q_DONE);
    check("query: the result is kept", qq.result.addr.a == 10 && qq.result.addr.d == 7);
    check("query: feeding a completed query is E_STATE", dns_query_feed(qq, ours) == E_STATE);

    // ======================================================================
    // 5. load: ten times a normal batch, half of it deliberately wrong-id replies
    // ======================================================================
    var ops: i64 = 100;
    var ok_n: i64 = 0;
    var refused_n: i64 = 0;
    var lq: u8[..512] = [0; 512];
    var lr: u8[..512] = [0; 512];
    var li: i64 = 0;
    while li < ops {
        let id = 1000 + li;
        let lql = dns_build_a_query(lq, "example.com", id);
        if lql > 0 {
            let _ = build_answer(lr, lq, lql, a4(93, 184, 216, 34), 60);
            var la2: Answer = Answer { addr: Ipv4 { a: 0, b: 0, c: 0, d: 0 }, ttl: 0, rcode: 0 };
            // Every tenth reply carries somebody else's id: a refusal, counted.
            if (li % 10) == 0 {
                let wrong = id + 5000;
                lr[0] = ((wrong >> 8) & 0xFF) as u8;
                lr[1] = (wrong & 0xFF) as u8;
                if dns_parse_a(lr, id, la2) == E_STATE { refused_n = refused_n + 1; }
            } else {
                if dns_parse_a(lr, id, la2) == CODE_OK { ok_n = ok_n + 1; }
            }
        }
        li = li + 1;
    }
    check("load: ninety good replies parsed", ok_n == 90);
    check("load: ten wrong-id replies refused", refused_n == 10);

    var lbuf: u8[>..] = [];
    let _ = append_str(lbuf, 512, "LOAD dns ops=");
    let _ = append_int(lbuf, 512, ops);
    let _ = append_str(lbuf, 512, " ok=");
    let _ = append_int(lbuf, 512, ok_n);
    let _ = append_str(lbuf, 512, " refused=");
    let _ = append_int(lbuf, 512, refused_n);
    say(lbuf[..]);
    say("\n");

    say("t116 done  pass=");
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
