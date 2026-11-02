// services/tests/t122_logd_r11.goose
//
// Round 11 driver for `logd`: the ring's three edges (high water, full, slot size), the
// four loss counters, and the rotation store's segment ceiling and retention.
//
// Why these assertions: the loss counters are the only thing that makes "the log is
// incomplete" a fact rather than a suspicion, and a counter that is never crossed is a
// number nobody has tested. Each edge below is crossed with a value on the wrong side.
//
// Status: WRITTEN (Round 11 worker). Not compiled or run here; the coordinator runs it.

import logd.logd;
import logd.rotate;
import common.err.err;
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

fn same(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn main() {
    say("t122 logd ring and rotation\n");
    logd_init();

    // ======================================================================
    // 1. the level floor and the slot ceiling
    // ======================================================================
    check("log: an INFO record is accepted", log_info("test", "one"));
    // min_level is INFO, so DEBUG is refused before it reaches the ring and is counted.
    check("log: a DEBUG record is refused by the level floor", !log(LVL_DEBUG, "test", "dbg"));
    let st1 = loss_stats();
    check("loss_stats: the level refusal is counted", st1.level == 1);

    // A record that cannot fit a slot is refused, not truncated, and the caller's buffer
    // is left EMPTY: a half-written record would be shipped as a complete line.
    var big: u8[..200] = [0x41; 200];
    check("log: a message past the slot is refused", !log(LVL_INFO, "t", big[..]));
    let st2 = loss_stats();
    check("loss_stats: the long refusal is counted", st2.long == 1);

    // format_record with an explicit cap: a fitting record fills the buffer, a long one
    // leaves it empty.
    var fits: u8[>..] = [];
    check("format_record: a fitting record renders", format_record(fits, SLOT, LVL_INFO, "t", big[..140])
          && fits.len > 0);
    var nofit: u8[>..] = [];
    check("format_record: an over-slot record leaves the buffer empty",
          !format_record(nofit, SLOT, LVL_INFO, "t", big[..]) && nofit.len == 0);

    // ======================================================================
    // 2. high water, the full ring, and the flush
    // ======================================================================
    // One record is already queued from section 1. Fill to HIGH_WATER exactly.
    var i: i64 = 1;
    while i < HIGH_WATER {
        let _ = log_info("test", "fill");
        i = i + 1;
    }
    check("should_flush: true exactly at HIGH_WATER", should_flush());

    // Fill to SLOTS, then one past it: the ring refuses and the loss is counted.
    var j: i64 = HIGH_WATER;
    var queued_ok = true;
    while j < SLOTS {
        if !log_info("test", "fill") { queued_ok = false; }
        j = j + 1;
    }
    check("log: every slot up to SLOTS accepts", queued_ok);
    check("log: one past SLOTS is refused", !log_info("test", "over"));
    let st3 = loss_stats();
    check("loss_stats: the full refusal is counted", st3.full == 1);

    let sent = flush();
    check("flush: drains every queued record", sent == SLOTS);
    check("flush: the second flush has nothing to send", flush() == 0);
    let st4 = loss_stats();
    check("loss_stats: written follows the flush", st4.written == SLOTS);

    // ======================================================================
    // 3. rotation: the eight-segment ceiling
    // ======================================================================
    var s = rot_new(100, 8);
    let idx0, c0 = rot_append(s, 1, 60);
    check("rot_append: the first segment is open", c0 == CODE_OK && idx0 == 0 && s.count == 1);
    let idx1, c1 = rot_append(s, 1, 60);
    check("rot_append: a segment over max_bytes rolls", c1 == CODE_OK && idx1 == 1 && s.count == 2);
    check("rot_append: the old segment is sealed", s.segs[0].sealed);

    // One segment per day until the store is at ROT_SEG_MAX. The store already holds two
    // segments (day 1, rolled once), so days 2..7 are the six that reach the ceiling; day 8
    // would be the ninth append, and the ninth is refused by the check below.
    var day: i64 = 2;
    var filled = true;
    while day < ROT_SEG_MAX {
        let _idx, code = rot_append(s, day, 10);
        if code != CODE_OK { filled = false; }
        day = day + 1;
    }
    check("rot_append: eight segments fill the store", filled && s.count == ROT_SEG_MAX);
    let _over, cover = rot_append(s, 99, 10);
    check("rot_append: the ninth segment is E_NOROOM", cover == E_NOROOM);

    // Retention never drops the newest segment, even when keep is smaller than the store.
    var p = rot_new(100, 3);
    var d: i64 = 1;
    while d <= 5 {
        let _pi, pc = rot_append(p, d, 10);
        if pc != CODE_OK { break; }
        d = d + 1;
    }
    check("rot_new: five segments before pruning", p.count == 5);
    check("rot_prune: drops beyond keep", rot_prune(p) == 2 && p.count == 3);
    let kept, _bytes, dropped, _rot = rot_stats(p);
    check("rot_stats: count and drop total agree", kept == 3 && dropped == 2);

    // The export name is the day shape a human greps, and the first day of the epoch is
    // 19700101 by construction.
    var name: u8[>..] = [];
    let nlen = rot_export_name("logd", 0, 0, name, 64);
    check("rot_export_name: the epoch day renders", nlen == 24
          && same(name[..], "export-logd-19700101.log"));

    // ======================================================================
    // 4. load: ten times a normal batch through the sink
    // ======================================================================
    var ops: i64 = 0;
    var ok: i64 = 0;
    var refused: i64 = 0;
    while ops < 240 {
        if log_info("test", "l") { ok = ok + 1; } else { refused = refused + 1; }
        ops = ops + 1;
    }
    let _drained = flush();
    say("LOAD logd ops=");
    var ob: u8[>..] = [];
    let _ = append_int(ob, 32, ops);
    say(ob[..]);
    say(" ok=");
    var kb: u8[>..] = [];
    let _ = append_int(kb, 32, ok);
    say(kb[..]);
    say(" refused=");
    var rb: u8[>..] = [];
    let _ = append_int(rb, 32, refused);
    say(rb[..]);
    say("\n");

    say("t122 done  pass=");
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
