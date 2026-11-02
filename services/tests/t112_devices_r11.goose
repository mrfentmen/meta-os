// services/tests/t112_devices_r11.goose
//
// R11-049..054 — the device table's capacity and state machine, and the hot-plug
// queue's two limits, driven from a host process.
//
// WHAT IS ACTUALLY CROSSED HERE
// -----------------------------
// DEV_MAX is reached by registering one device per kind: the table is one-entry-per-kind,
// so sixteen distinct kind numbers fill it and the seventeenth is refused with E_NOROOM.
// HP_SUBS is reached with nine subscriptions (the ninth gets -1), and HP_QUEUE with nine
// raised events, where the OLDEST must be the one dropped and the per-subscriber counters
// must still add up.
//
// The illegal transition asserted here is READY -> DETECTED: "became less ready without
// failing" is not something a driver can report, and allowing it would hide a missed FAULT.
//
// Status: written for Round 11; the coordinator runs it and records the result.

import devices.devices;
import devices.hotplug;
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

fn put_num(v: i64) {
    var b: u8[>..] = [];
    let _ = append_int(b, 32, v);
    say(b[..]);
}

fn main() {
    say("t112 devices r11\n");

    // ======================================================================
    // 1. the limits, as data
    // ======================================================================
    check("DEV_MAX is 16", DEV_MAX == 16);
    check("HP_QUEUE is 8", HP_QUEUE == 8);
    check("HP_SUBS is 8", HP_SUBS == 8);

    // ======================================================================
    // 2. registration refusals
    // ======================================================================
    let serial, sc = dev_add(DEV_SERIAL, "serial", 0x3f8 as u64, -1, 115200, 8);
    check("a serial device registers", serial >= 0 && sc == CODE_OK);
    let s2, sc2 = dev_add(DEV_SERIAL, "serial2", 0 as u64, -1, 0, 0);
    check("a second device of the same kind is refused", s2 == -1 && sc2 == E_STATE);
    check("an unknown device is not found", dev_find(DEV_KEYBOARD) == -1);
    check("a device that is detected is not yet ready", !dev_ready(DEV_SERIAL));
    let _a0, _b0, detail_code = dev_detail(DEV_SERIAL);
    check("details of a non-ready device are refused", detail_code == E_STATE);
    let n1, n1c = dev_add(DEV_BLOCK, "", 0 as u64, -1, 0, 0);
    check("an empty name is refused", n1 == -1 && n1c == E_INVAL);
    let n2, n2c = dev_add(DEV_BLOCK, "0123456789abcdef", 0 as u64, -1, 0, 0);
    check("a name of sixteen bytes is refused", n2 == -1 && n2c == E_INVAL);
    let n3, n3c = dev_add(DEV_NONE, "none", 0 as u64, -1, 0, 0);
    check("kind zero is refused", n3 == -1 && n3c == E_INVAL);

    // ======================================================================
    // 3. the state machine
    // ======================================================================
    check("DETECTED -> READY is legal", dev_mark(serial, DS_READY) == CODE_OK);
    check("a ready device answers yes", dev_ready(DEV_SERIAL));
    let a1, b1, c1 = dev_detail(DEV_SERIAL);
    check("the details are the ones registered", a1 == 115200 && b1 == 8 && c1 == CODE_OK);
    check("READY -> DETECTED is refused", dev_mark(serial, DS_DETECTED) == E_STATE);
    check("READY -> FAULT is legal", dev_mark(serial, DS_FAULT) == CODE_OK);
    check("a faulted device answers no", !dev_ready(DEV_SERIAL));
    let f0, f1, fcode = dev_detail(DEV_SERIAL);
    check("a faulted device hands back zeros and E_STATE",
          f0 == 0 && f1 == 0 && fcode == E_STATE);
    check("FAULT -> READY is the recovery", dev_mark(serial, DS_READY) == CODE_OK);
    check("an out-of-range slot is refused", dev_mark(99, DS_READY) == E_INVAL);

    let fb, fc = dev_add(DEV_FRAMEBUFFER, "framebuffer", 0 as u64, -1, 80, 25);
    check("a framebuffer registers", fb >= 0 && fc == CODE_OK);
    check("anything may vanish", dev_mark(fb, DS_ABSENT) == CODE_OK);
    check("an absent framebuffer is not ready", !dev_ready(DEV_FRAMEBUFFER));

    // ======================================================================
    // 4. DEV_MAX, reached by one device per kind
    // ======================================================================
    let kb, kc = dev_add(DEV_KEYBOARD, "keyboard", 0 as u64, -1, 0, 0);
    let tm, tc = dev_add(DEV_TIMER, "timer", 0 as u64, 0, 100, 0);
    let bl, bc = dev_add(DEV_BLOCK, "block", 0 as u64, -1, 0, 0);
    let nw, nc = dev_add(DEV_NET, "net", 0 as u64, -1, 0, 0);
    check("six named kinds register", kb >= 0 && tm >= 0 && bl >= 0 && nw >= 0
          && kc == CODE_OK && tc == CODE_OK && bc == CODE_OK && nc == CODE_OK);

    var k: i64 = 7;
    var added: i64 = 0;
    while k <= DEV_MAX {
        let slot, code = dev_add(k, "extra", 0 as u64, -1, 0, 0);
        if code == CODE_OK && slot >= 0 { added = added + 1; }
        k = k + 1;
    }
    check("ten more kinds fill the table to DEV_MAX", added == 10);
    let over, over_c = dev_add(DEV_MAX + 1, "overflow", 0 as u64, -1, 0, 0);
    check("the seventeenth device is refused with E_NOROOM",
          over == -1 && over_c == E_NOROOM);

    let ready, faulted, absent = dev_summary();
    check("the summary counts ready, faulted and absent",
          ready == 1 && faulted == 0 && absent == 1);
    check("the detected state holds the rest", dev_count_in(DS_DETECTED) == 14);

    // ======================================================================
    // 5. hot-plug: subscriptions, the queue, and the drop rule
    // ======================================================================
    var h = hp_new();
    var ids: i64[..8] = [0; 8];
    var s: i64 = 0;
    while s < HP_SUBS {
        ids[s] = hp_subscribe(h, 1 << HP_ADD);
        s = s + 1;
    }
    check("eight subscribers fill HP_SUBS",
          ids[0] > 0 && ids[7] > 0 && ids[7] == ids[0] + 7);
    check("the ninth subscriber is refused", hp_subscribe(h, 1 << HP_ADD) == -1);
    check("an empty mask is refused", hp_subscribe(h, 0) == -1);

    var raised_ok: i64 = 0;
    var r: i64 = 0;
    while r < HP_QUEUE + 1 {
        let delivered, rc = hp_raise(h, HP_ADD, 0, DEV_SERIAL, r);
        if rc == CODE_OK && delivered == HP_SUBS { raised_ok = raised_ok + 1; }
        r = r + 1;
    }
    check("nine events raise, eight fit", raised_ok == HP_QUEUE + 1);

    let raised, dropped, subs, pending = hp_stats(h);
    check("the queue dropped the oldest", raised == 9 && dropped == 1);
    check("the queue holds eight and drops one oldest", pending == HP_QUEUE && subs == 8);

    var e: HotEvent = HotEvent { seq: 0, kind: 0, dev_slot: -1, dev_kind: 0, at_ms: 0 };
    let first = hp_next(h, e);
    check("the oldest surviving event is sequence 2", first && e.seq == 2);
    var drained: i64 = 1;
    while hp_next(h, e) { drained = drained + 1; }
    check("the queue drains to empty", drained == HP_QUEUE && hp_pending(h) == 0);
    check("the last event is the newest", e.seq == 9);

    var delivered0: i64 = 0;
    var dropped0: i64 = 0;
    let stats_ok = hp_sub_stats(h, ids[0], delivered0, dropped0);
    check("one subscriber's counters add up to what it was told",
          stats_ok && delivered0 == 8 && dropped0 == 1);

    let badn, badc = hp_raise(h, 0, 0, 0, 0);
    check("an unknown event kind is refused", badn == 0 && badc == E_INVAL);
    check("unsubscribe succeeds", hp_unsubscribe(h, ids[0]) == CODE_OK);
    check("unsubscribing twice is not found", hp_unsubscribe(h, ids[0]) == E_NOTFOUND);
    let r2, d2, s2c, p2 = hp_stats(h);
    check("the subscriber count falls", r2 == 9 && d2 == 1 && s2c == 7 && p2 == 0);
    let n_add = hp_kind_name(HP_ADD);
    let n_remove = hp_kind_name(HP_REMOVE);
    let n_fault = hp_kind_name(HP_FAULT);
    let n_ready = hp_kind_name(HP_READY);
    check("the four event kinds have names",
          n_add.len == 3 && n_remove.len == 6
          && n_fault.len == 5 && n_ready.len == 5);

    // ======================================================================
    // 6. load: ten times a normal query batch over the full table
    // ======================================================================
    var ops: i64 = 0;
    var okq: i64 = 0;
    var refused: i64 = 0;
    var i: i64 = 0;
    while i < 700 {
        ops = ops + 1;
        if dev_find(DEV_SERIAL) >= 0 && dev_ready(DEV_SERIAL) { okq = okq + 1; }
        else { refused = refused + 1; }
        i = i + 1;
    }
    check("every query in the load batch answered", okq == 700 && refused == 0);

    say("LOAD devices ops="); put_num(ops);
    say(" ok="); put_num(okq);
    say(" refused="); put_num(refused);
    say("\n");

    say("t112 done  pass="); put_num(t_pass);
    say(" fail="); put_num(t_fail);
    say("\n");
    if t_fail > 0 { sys_exit(1); }
}
