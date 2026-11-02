// services/tests/t77_gaps.goose
//
// B1 — the four services the failure matrix left blank, driven.
//
// WHAT THIS FILE IS FOR
// ---------------------
// FAILURE_MATRIX.md named four services whose columns were empty because nothing drove
// them at all: `devices`, `session`, `socket`, `timesync`. A blank cell in a failure
// matrix is not a gap in the matrix, it is a gap in the evidence. This file gives each
// one a driver and exercises the ways each can fail, plus the one path that must work.
//
// The failures chosen are the ones that would be silent: a table that fills up, a
// handle that outlives its socket, a login that succeeds when it should not, a clock
// that accepts a reply it should refuse.
//
// Status: RUNS — set by `audit_status.py` from the runner's row, not by hand.

import devices.devices;
import devices.hotplug;
import session.session;
import session.login;
import socket.socket;
import timesync.timesync;
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

fn eq(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn filler() -> u8[..1500] {
    var f: u8[..1500] = [0; 1500];
    var i: i64 = 0;
    while i < 1500 { f[i] = 65; i = i + 1; }
    return f;
}

fn main() {
    say("t77 gap services\n");
    t_devices();
    t_hotplug();
    t_session();
    t_socket();
    t_timesync();

    say("t77 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
}

// ===========================================================================
// 1. devices — a table that fills, a transition that is not a transition
// ===========================================================================
fn t_devices() {
    say("--- devices\n");
    var slot, code = dev_add(DEV_SERIAL, "uart", 1016 as u64, 4, 0, 0);
    check("a good device registers", code == CODE_OK && slot >= 0);

    let s2, c2 = dev_add(DEV_SERIAL, "uart2", 0 as u64, 5, 0, 0);
    check("a second device of the same kind is refused (E_STATE)", c2 == E_STATE && s2 < 0);

    let s3, c3 = dev_add(DEV_TIMER, "", 0 as u64, 0, 0, 0);
    check("an empty name is refused (E_INVAL)", c3 == E_INVAL);

    let s4, c4 = dev_add(DEV_NONE, "nothing", 0 as u64, 0, 0, 0);
    check("kind 0 is refused (E_INVAL)", c4 == E_INVAL);

    let s5, c5 = dev_add(DEV_KEYBOARD, "this-name-is-far-too-long", 0 as u64, 1, 0, 0);
    check("a 25-byte name is refused (E_INVAL)", c5 == E_INVAL);

    check("marking a slot that does not exist is E_INVAL", dev_mark(99, DS_READY) == E_INVAL);
    check("DETECTED -> READY is legal", dev_mark(slot, DS_READY) == CODE_OK);
    check("READY -> DETECTED is not a transition (E_STATE)", dev_mark(slot, DS_DETECTED) == E_STATE);
    check("READY -> FAULT is legal", dev_mark(slot, DS_FAULT) == CODE_OK);
    check("dev_ready is false while faulted", !dev_ready(DEV_SERIAL));
    let d1, d2, dc = dev_detail(DEV_SERIAL);
    check("detail of a faulted device refuses (E_STATE), not stale numbers", dc == E_STATE && d1 == 0 && d2 == 0);

    // Fill the table: DEV_MAX is 16 and one is taken.
    var kind: i64 = 7;
    var added: i64 = 0;
    while kind < 30 {
        let s, c = dev_add(kind, "dev", 0 as u64, 0, 0, 0);
        if c == CODE_OK { added = added + 1; }
        kind = kind + 1;
    }
    check("the table stops at DEV_MAX", added == 15);
    let s16, c16 = dev_add(31, "overflow", 0 as u64, 0, 0, 0);
    check("past DEV_MAX is E_NOROOM, not a silent overwrite", c16 == E_NOROOM && s16 < 0);
    check("the devices already registered are untouched", dev_find(7) >= 0 && dev_find(DEV_SERIAL) >= 0 && dev_find(DEV_TIMER) == -1);
}

// ===========================================================================
// 2. hotplug — a subscriber that misses events must be told how many
// ===========================================================================
fn t_hotplug() {
    say("--- devices/hotplug\n");
    var hp = hp_new();
    check("an empty mask is not a subscriber", hp_subscribe(hp, 0) < 0);

    let id = hp_subscribe(hp, 1 << HP_ADD);
    check("a subscriber with a mask registers", id > 0);
    let _bad_delivered, bad_code = hp_raise(hp, 0, 0, DEV_SERIAL, 0);
    check("an unknown event kind is refused (E_INVAL)", bad_code == E_INVAL);

    var i: i64 = 0;
    while i < HP_QUEUE + 3 {
        let _ = hp_raise(hp, HP_ADD, 0, DEV_SERIAL, i as i64);
        i = i + 1;
    }
    let raised, dropped, subs, pending = hp_stats(hp);
    check("the overflow is counted, not silent", dropped == 3);
    check("the queue holds exactly its capacity", pending == HP_QUEUE);
    check("every raise was counted as raised", raised == HP_QUEUE + 3);

    var delivered: i64 = 0;
    var sub_dropped: i64 = 0;
    let ok = hp_sub_stats(hp, id, delivered, sub_dropped);
    check("the subscriber's own loss is reported", ok && sub_dropped == 3);
    check("the subscriber's waiting count is what survived the queue", delivered == HP_QUEUE);
    check("delivered + dropped is exactly what was raised", delivered + sub_dropped == raised);

    var ev: HotEvent = HotEvent { seq: 0, kind: 0, dev_slot: -1, dev_kind: 0, at_ms: 0 };
    check("a queued event can be taken", hp_next(hp, ev));
    check("the oldest was dropped, so the first one out is seq 4", ev.seq == 4);
    var drained: i64 = 1;
    while hp_next(hp, ev) { drained = drained + 1; }
    check("draining stops at the end instead of repeating an event", drained == HP_QUEUE);
}

// ===========================================================================
// 3. session — a login that must not succeed, and a cap that must refuse
// ===========================================================================
fn type_str(f: LoginFlow&, s: const u8[:]) -> i64 {
    var i: i64 = 0;
    var code = CODE_OK;
    while i < s.len {
        code = login_key(f, s[i]);
        i = i + 1;
    }
    return code;
}

fn t_session() {
    say("--- session\n");
    ses_init();

    let bad1, bc1 = ses_open(0, 0, 0, 0, 0);
    check("owner 0 is refused (E_INVAL)", bc1 == E_INVAL && bad1 == SES_NO_SESSION);
    let bad2, bc2 = ses_open(OWNER_USER, 0, 0, 0, 0);
    check("a user session with no user id is refused (E_INVAL)", bc2 == E_INVAL);
    let bad3, bc3 = ses_open(OWNER_AGENT, 0, 0, 0, 0);
    check("an agent session with no agent handle is refused (E_INVAL)", bc3 == E_INVAL);

    // --- the login flow, then the defect it exposes
    var f = login_new();
    let _ = login_start(f, 0);
    check("Enter on an empty name is refused (E_INVAL)", login_key(f, 13) == E_INVAL);
    check("a control byte never enters a field (E_INVAL)", login_key(f, 1) == E_INVAL);

    var long_name: u8[..32] = [0; 32];
    var i: i64 = 0;
    while i < 31 { long_name[i] = 97; i = i + 1; }
    var overlong = CODE_OK;
    i = 0;
    while i < 31 {
        let c = login_key(f, long_name[i]);
        if c != CODE_OK { overlong = c; }
        i = i + 1;
    }
    check("a name past the field is refused (E_NOROOM)", overlong == E_NOROOM);

    // A wrong token three times ends the flow; a fourth keystroke is not accepted.
    var g = login_new();
    let _ = login_start(g, 0);
    let _ = type_str(g, "mrfentmen");
    let _ = login_key(g, 13);
    var attempts: i64 = 0;
    var last: i64 = CODE_OK;
    while attempts < LG_ATTEMPTS {
        let _ = type_str(g, "wrong");
        let _ = login_key(g, 13);
        let id, code = login_submit(g, "s3cret", OWNER_USER, 7, 0);
        last = code;
        attempts = attempts + 1;
    }
    check("three wrong tokens end the flow (E_AUTH)", last == E_AUTH);
    check("a failed flow takes no more keystrokes (E_STATE)", login_key(g, 97) == E_STATE);

    // An empty expected token must refuse every login: a config that failed to load is
    // not a config that accepts anyone.
    var h = login_new();
    let _ = login_start(h, 0);
    let _ = type_str(h, "mrfentmen");
    let _ = login_key(h, 13);
    let _ = type_str(h, "anything");
    let _ = login_key(h, 13);
    let hid, hcode = login_submit(h, "", OWNER_USER, 7, 0);
    check("an empty expected token refuses the login (E_AUTH)", hcode == E_AUTH && hid == SES_NO_SESSION);

    // --- the path that must work: right name, right token, a real session
    var k = login_new();
    let _ = login_start(k, 0);
    let _ = type_str(k, "mrfentmen");
    let _ = login_key(k, 13);
    let _ = type_str(k, "s3cret");
    let _ = login_key(k, 13);
    let sid, scode = login_submit(k, "s3cret", OWNER_USER, 7, 0);
    check("a correct token opens a session", scode == CODE_OK && sid > 0);
    check("the flow is ACTIVE after login", k.state == LG_ACTIVE);
    check("the session is resolvable", ses_resolve(sid) >= 0);
    if scode == CODE_OK {
        let _ = login_end(k);
        check("logout closes it", ses_state(sid) == SS_CLOSED);
    }

    // --- the cap
    ses_init();
    var opened: i64 = 0;
    var n: i64 = 0;
    while n < SES_CAP {
        let id, code = ses_open(OWNER_USER, 7, 0, 0, n as i64);
        if code == CODE_OK { opened = opened + 1; }
        n = n + 1;
    }
    check("the session table fills to its capacity", opened == SES_CAP);
    let extra, xcode = ses_open(OWNER_USER, 7, 0, 0, 0);
    check("past the cap is E_NO_SPACE, not a reused slot", xcode == E_NO_SPACE && extra == SES_NO_SESSION);
}

// ===========================================================================
// 4. socket — a handle that outlives its socket, and a queue that fills
// ===========================================================================
fn t_socket() {
    say("--- socket\n");
    var dst = ip4(10, 0, 0, 1);
    var none = ip4(0, 0, 0, 0);
    let h, code = sk_open();
    check("a socket opens", code == CODE_OK && h != 0);

    check("an unknown handle is refused (E_STATE)", sk_send(9999, dst, 53, "x") == E_STATE);
    check("sending before bind is refused (E_STATE)", sk_send(h, dst, 53, "x") == E_STATE);

    let p1, pc1 = sk_bind(h, 80);
    check("a privileged port is refused (E_INVAL)", pc1 == E_INVAL && p1 == 0);
    let p2, pc2 = sk_bind(h, 70000);
    check("a port past 65535 is refused (E_INVAL)", pc2 == E_INVAL);
    let p3, pc3 = sk_bind(h, 5555);
    check("a normal port binds", pc3 == CODE_OK && p3 == 5555);
    let p4, pc4 = sk_bind(h, 5556);
    check("binding twice is E_STATE", pc4 == E_STATE);

    let h2, _c2 = sk_open();
    let p5, pc5 = sk_bind(h2, 5555);
    check("a duplicate bind is E_BUSY", pc5 == E_BUSY);

    check("a zero-length datagram is refused (E_INVAL)", sk_send(h, dst, 53, "") == E_INVAL);
    let big = filler();
    check("a datagram past the MTU is refused (E_NOROOM)", sk_send(h, dst, 53, big[0..600]) == E_NOROOM);
    check("a datagram to 0.0.0.0 is refused (E_INVAL)", sk_send(h, none, 53, "x") == E_INVAL);
    check("a datagram to port 0 is refused (E_INVAL)", sk_send(h, dst, 0, "x") == E_INVAL);

    check("first datagram queues", sk_send(h, dst, 53, "one") == CODE_OK);
    check("second datagram queues", sk_send(h, dst, 53, "two") == CODE_OK);
    check("a third datagram is refused while two are queued (E_BUSY)",
          sk_send(h, dst, 53, "three") == E_BUSY);

    let _ = sk_close(h);
    check("the closed socket's handle no longer resolves", sk_send(h, dst, 53, "late") == E_STATE);

    // Fill the table, then ask for one more.
    var n: i64 = 0;
    var opened: i64 = 0;
    while n < SK_MAX {
        let s, c = sk_open();
        if c == CODE_OK { opened = opened + 1; }
        n = n + 1;
    }
    check("the socket table has a hard cap", opened < SK_MAX);
    let s9, c9 = sk_open();
    check("past the cap is E_NOROOM", c9 == E_NOROOM && s9 == 0);
}

// ===========================================================================
// 5. timesync — every reply the clock must refuse
// ===========================================================================
fn t_timesync() {
    say("--- timesync\n");
    var pkt: u8[..48] = [0; 48];

    check("a short packet is E_CORRUPT", ntp_apply_reply(pkt[0..10], 1000, 1050) == E_CORRUPT);

    // A well-formed reply first, so every later refusal is a single changed byte and not a
    // packet that was never valid.
    pkt[0] = (0 << 6 | NTP_MODE_SERVER) as u8;   // LI 0, VN 0, mode 4
    pkt[1] = 2;                                   // stratum 2: a real server
    ntp_put_time(pkt, 32, 6000);                  // server receive
    ntp_put_time(pkt, 40, 6010);                  // server transmit

    check("a well-formed reply is accepted", ntp_apply_reply(pkt[..], 1000, 1050) == CODE_OK);
    // offset = ((6000 - 1000) + (6010 - 1050)) / 2 = 4980; the applied offset is not moved
    // by the measurement -- the smear closes it.
    check("the measured offset is the target, not the applied clock", ts_pending_ms() == 4980);
    // The 10 ms between the server's receive and transmit must survive the timestamp's
    // fraction field: it was truncated to 0 before the scaling was corrected, which put
    // every measurement a few ms out.
    check("a 10 ms server turnaround is measured exactly", ts_last_roundtrip_ms() == 40);

    pkt[0] = NTP_MODE_CLIENT as u8;
    check("a client-mode packet is not a reply (E_CORRUPT)", ntp_apply_reply(pkt[..], 1000, 1050) == E_CORRUPT);
    pkt[0] = (0 << 6 | NTP_MODE_SERVER) as u8;

    pkt[1] = 0;
    check("stratum 0 is a kiss-o'-death and is refused (E_REFUSED)", ntp_apply_reply(pkt[..], 1000, 1050) == E_REFUSED);
    pkt[1] = 2;

    pkt[0] = ((3 << 6) | NTP_MODE_SERVER) as u8;
    check("leap indicator 3 means the server is unsynchronised (E_UNSUPPORTED)",
          ntp_apply_reply(pkt[..], 1000, 1050) == E_UNSUPPORTED);
    pkt[0] = (0 << 6 | NTP_MODE_SERVER) as u8;

    var z: i64 = 40;
    while z < 48 { pkt[z] = 0; z = z + 1; }
    check("a reply with no transmit time is refused (E_CORRUPT)", ntp_apply_reply(pkt[..], 1000, 1050) == E_CORRUPT);

    // A server two days away is a wrong server, not a wrong clock.
    ntp_put_time(pkt, 32, 6000 + 2 * 86400000);
    ntp_put_time(pkt, 40, 6010 + 2 * 86400000);
    check("an offset beyond a day is refused (E_INVAL)", ntp_apply_reply(pkt[..], 1000, 1050) == E_INVAL);

    // A negative delay: the server claims 100 ms of processing on a 50 ms round trip.
    ntp_put_time(pkt, 32, 6000);
    ntp_put_time(pkt, 40, 6100);
    check("impossible timestamps are refused (E_CORRUPT)", ntp_apply_reply(pkt[..], 1000, 1050) == E_CORRUPT);

    // And the smear: it moves toward the target and never past it.
    ntp_put_time(pkt, 32, 6000);
    ntp_put_time(pkt, 40, 6010);
    check("a good reply after refusals is still accepted", ntp_apply_reply(pkt[..], 1000, 1050) == CODE_OK);
    var steps: i64 = 0;
    var overshot = false;
    while ts_pending_ms() != 0 && steps < 200 {
        let before = ts_pending_ms();
        let _step = ts_smear_step(0);
        let after = ts_pending_ms();
        if (before > 0 && after < 0) || (before < 0 && after > 0) { overshot = true; }
        steps = steps + 1;
    }
    check("the smear closes the gap", ts_pending_ms() == 0);
    check("the smear takes more than one step (no visible jump)", steps > 1);
    check("the smear never overshoots the target", !overshot);
}
