// services/tests/t137_timesync_r11.goose
//
// Round 11, timesync (R11-199..204): the smear, the millisecond round trip, and the
// invariant that a refused reply never moves the clock.
//
// What the earlier drivers already prove: t77/t80 drive the reply refusals, one offset
// computation, and a 1-second correction. This driver adds the part nobody had measured:
// the smear closes a gap without ever going backwards or overshooting, the fractional
// timestamp is exact at the millisecond edges, and every refusal leaves the clock where it
// was. Nothing here sleeps or waits: the smear is stepped by hand.
//
// Status: RUNS after the coordinator's native run; written 2026-11-02.

import timesync.timesync;
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

fn main() {
    say("t137 timesync r11\n");

    // ======================================================================
    // 1. a request is a request, and its stamp survives the wire
    // ======================================================================
    var req: u8[..48] = [0; 48];
    let built = ntp_build_request(req, 5000);
    check("build: 48 bytes written", built == NTP_PACKET);
    check("build: LI 0, version 4, mode 3", req[0] == 0x23);
    check("build: stratum and identifiers are the server's", req[1] == 0);
    check("build: transmit stamp reads back as the clock it was given",
          ntp_read_time(req[..], 40) == ts_now_ms(5000));

    // The fraction is 32 bits: the edges are the milliseconds that either truncate to
    // nothing (1 ms) or nearly overflow the second (999 ms).
    var edge: i64[..6] = [0; 6];
    edge[0] = 0;
    edge[1] = 1;
    edge[2] = 7;
    edge[3] = 999;
    edge[4] = 1001;
    edge[5] = 123456789;
    var exact = true;
    var i: i64 = 0;
    while i < 6 {
        let _ = ntp_build_request(req, edge[i]);
        if ntp_read_time(req[..], 40) != ts_now_ms(edge[i]) { exact = false; }
        i = i + 1;
    }
    check("build: the millisecond fraction is exact at every edge", exact);

    // ======================================================================
    // 2. RFC 5905 arithmetic, on a reply whose asymmetry is known
    // ======================================================================
    // Request leaves at mono 1000, reply arrives at 1100. The server saw it at unix 1050
    // and sent at 1080: leg one is +50 ms, leg two is -20 ms, so the offset is their
    // average (+15) and the round trip is 100 - 30 = 70.
    var pkt: u8[..48] = [0; 48];
    pkt[0] = 0x24;        // LI 0, VN 4, mode 4 (server)
    pkt[1] = 1;           // stratum 1
    ntp_put_time(pkt, 32, 1050);
    ntp_put_time(pkt, 40, 1080);
    check("reply: accepted", ntp_apply_reply(pkt[..], 1000, 1100) == CODE_OK);
    check("reply: offset is the average of the two legs", ts_pending_ms() == 15);
    check("reply: round trip subtracts the server's 30 ms", ts_last_roundtrip_ms() == 70);
    check("reply: applying a measurement does not step the clock", ts_now_ms(0) == 0);

    // ======================================================================
    // 3. the smear: forward only, bounded, never past the target
    // ======================================================================
    let first = ts_smear_step(1100);
    check("smear: the first step is a tenth of the error", first == 1);
    check("smear: the applied offset moved, the measurement did not",
          ts_now_ms(0) == 1 && ts_pending_ms() == 14);

    var steps: i64 = 1;
    var mono: i64 = 1100;
    var forward_only = true;
    var prev = ts_now_ms(0);
    while ts_pending_ms() != 0 && steps < 100 {
        let _ = ts_smear_step(mono);
        let cur = ts_now_ms(0);
        if cur <= prev { forward_only = false; }
        if ts_pending_ms() < 0 { forward_only = false; }   // overshoot is a second jump
        prev = cur;
        steps = steps + 1;
        mono = mono + 10;
    }
    check("smear: the gap closes", ts_pending_ms() == 0);
    check("smear: every step moves forward and none overshoots", forward_only);
    check("smear: the settled offset is the measured one", ts_now_ms(0) == 15);
    check("smear: a settled offset is a no-op", ts_smear_step(5000) == 0);

    // ======================================================================
    // 4. every refusal, and the clock that must not move for any of them
    // ======================================================================
    let before = ts_now_ms(0);
    pkt[0] = 0x23;        // client mode: not a reply
    check("refuse: a client-mode packet is E_CORRUPT",
          ntp_apply_reply(pkt[..], 1200, 1300) == E_CORRUPT);
    check("refuse: a rejected packet does not move the clock", ts_now_ms(0) == before);

    pkt[0] = 0x24;
    pkt[1] = 0;           // stratum 0: kiss-o'-death
    check("refuse: stratum 0 is E_REFUSED", ntp_apply_reply(pkt[..], 1200, 1300) == E_REFUSED);

    pkt[0] = (0xE4 as u8);   // LI 3: the server is unsynchronised
    pkt[1] = 1;
    check("refuse: an unsynchronised server is E_UNSUPPORTED",
          ntp_apply_reply(pkt[..], 1200, 1300) == E_UNSUPPORTED);

    pkt[0] = 0x24;
    ntp_put_time(pkt, 40, 0);
    check("refuse: a reply with no transmit time is E_CORRUPT",
          ntp_apply_reply(pkt[..], 1200, 1300) == E_CORRUPT);

    // Send stamped 490 ms after receive, on a 100 ms round trip: impossible.
    ntp_put_time(pkt, 32, 1210);
    ntp_put_time(pkt, 40, 1700);
    check("refuse: a negative delay is E_CORRUPT",
          ntp_apply_reply(pkt[..], 1200, 1300) == E_CORRUPT);

    // A server with a different idea of the date: 100,000,000 ms is beyond a day.
    ntp_put_time(pkt, 32, 100000000);
    ntp_put_time(pkt, 40, 100000030);
    check("refuse: an offset beyond a day is E_INVAL",
          ntp_apply_reply(pkt[..], 1200, 1300) == E_INVAL);

    var short: u8[..10] = [0; 10];
    check("refuse: a packet shorter than 48 bytes is E_CORRUPT",
          ntp_apply_reply(short[..], 1200, 1300) == E_CORRUPT);

    check("refuse: no refusal in this section moved the clock", ts_now_ms(0) == before);
    check("refuse: no refusal left a pending correction", ts_pending_ms() == 0);

    // ======================================================================
    // 5. load: 100 builds and reads with the offset settled
    // ======================================================================
    var ops: i64 = 0;
    var okc: i64 = 0;
    var k: i64 = 0;
    while k < 100 {
        let made = ntp_build_request(req, k * 1000);
        if made == NTP_PACKET && ntp_read_time(req[..], 40) == ts_now_ms(k * 1000) {
            okc = okc + 1;
        }
        ops = ops + 1;
        k = k + 1;
    }
    check("load: 100 request stamps, no drift", okc == 100);

    say("LOAD timesync ops=");
    var ob: u8[>..] = [];
    let _ = append_int(ob, 32, ops);
    say(ob[..]);
    say(" ok=");
    var kb: u8[>..] = [];
    let _ = append_int(kb, 32, okc);
    say(kb[..]);
    say(" refused=0\n");

    say("t137 done  pass=");
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
