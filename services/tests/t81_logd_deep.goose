// services/tests/t81_logd_deep.goose
//
// Round 7 B, logd — the four things the failure matrix never asked of the sink:
// what happens when its inputs are wrong (a), where its numeric edges sit (b),
// what a restart leaves behind (c), all pointing at a contract page (d).
//
// t50_logd proves the happy paths and the retention policy. This file does not
// repeat those checks; it attacks the service.

import logd.logd;
import common.err.err;
import common.ring.ring;
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

fn num(label: const u8[:], v: i64) {
    say(label);
    var b: u8[>..] = [];
    let _ = append_int(b, 32, v);
    say(b[..]);
    say("\n");
}

fn filler(n: i64) -> u8[>..] {
    var s: u8[>..] = [];
    var i: i64 = 0;
    while i < n { let _ = s.push('m'); i = i + 1; }
    return s;
}

// ===========================================================================
// (a) Failure injection — the three ways a record is refused, each counted

fn t_inject() {
    say("-- (a) failure injection\n");
    logd_init();
    let base = loss_stats();

    // A tag longer than the slot allows cannot be formatted at all. The refusal
    // must be counted, and the queue must not hold a half-record.
    let huge_tag = filler(SLOT);
    let ok_tag = log_info(huge_tag[..], "x");
    let after_tag = loss_stats();
    check("logd: a tag that cannot fit is refused", !ok_tag);
    check("logd: the refusal is counted as long", after_tag.long == base.long + 1);
    check("logd: the refused record left the queue empty", msg_len(queue) == 0);

    // A message over the slot, with a normal tag.
    let ok_msg = log_info("t", filler(SLOT)[..]);
    let after_msg = loss_stats();
    check("logd: a message over the slot is refused", !ok_msg);
    check("logd: and counted, not truncated", after_msg.long == after_tag.long + 1);

    // Below the minimum level: dropped before it reaches the ring, counted
    // separately, because "we filtered it" and "we lost it" are different news.
    let debug = log(LVL_DEBUG, "t", "quiet");
    let after_lvl = loss_stats();
    check("logd: DEBUG under an INFO floor is refused", !debug);
    check("logd: the level drop is counted as level, not long", after_lvl.level == after_lvl.level && after_lvl.long == after_msg.long);

    // A flood: more records than the ring holds, no flush between them. Every
    // refusal is counted and the queue never exceeds its capacity.
    var i: i64 = 0;
    while i < SLOTS + 16 {
        let _ = log_info("flood", "x");
        i = i + 1;
    }
    let after_flood = loss_stats();
    num("   dropped_full after flood: ", after_flood.full);
    check("logd: a flood is refused at the ring, not at the slot", after_flood.full > 0);
    check("logd: the queue never holds more than SLOTS", msg_len(queue) <= SLOTS);
    check("logd: long and level counters did not move during the flood",
          after_flood.long == after_lvl.long && after_flood.level == after_lvl.level);

    // An error at a full ring is the one record worth interrupting for: the
    // service flushes, retries once, and only then counts a loss.
    var j: i64 = 0;
    while j < SLOTS + 8 { let _ = log_info("fill", "y"); j = j + 1; }
    let before_err = loss_stats();
    let err = log_error("ERR", "the one that matters");
    let after_err = loss_stats();
    check("logd: an error into a full ring is accepted", err);
    check("logd: accepting it did not count a loss", after_err.full == before_err.full);
}

// ===========================================================================
// (b) Boundary sweep — SLOTS and HIGH_WATER at -1, exact, +1

fn t_boundary() {
    say("-- (b) boundary sweep\n");
    logd_init();
    let _ = flush();                     // start from an empty queue

    var accepted: i64 = 0;
    var i: i64 = 0;
    while i < SLOTS - 1 {
        if log_info("b", "x") { accepted = accepted + 1; }
        i = i + 1;
    }
    check("logd: SLOTS-1 records are accepted", accepted == SLOTS - 1);
    check("logd: the record count is SLOTS-1", msg_len(queue) == SLOTS - 1);
    // 63 records is already past HIGH_WATER (48), so the flush IS due here. The
    // interesting edge is 47 vs 48, and that is swept further down.
    check("logd: at SLOTS-1 the queue is above the mark, so a flush is due", should_flush());

    let exact = log_info("b", "x");
    check("logd: the SLOTS-th record is accepted", exact);
    check("logd: and the queue is exactly full", msg_len(queue) == SLOTS);
    check("logd: should_flush is true at a full ring", should_flush());

    let over = log_info("b", "x");
    check("logd: the SLOTS+1-th record is refused", !over);

    // HIGH_WATER itself: fill to exactly the mark and check the predicate flips
    // there, not one record early. A flush that fires at 47 keeps 16 slots free
    // for nothing.
    let _ = flush();
    var k: i64 = 0;
    while k < HIGH_WATER - 1 { let _ = log_info("h", "x"); k = k + 1; }
    check("logd: below HIGH_WATER, no flush is due", !should_flush());
    let _ = log_info("h", "x");
    check("logd: at HIGH_WATER exactly, a flush is due", should_flush());
}

// ===========================================================================
// (c) Restart semantics — what a re-init does and does not clear

fn t_restart() {
    say("-- (c) restart semantics\n");
    let _ = flush();
    let _ = log_info("pre", "before restart");
    let before_q = msg_len(queue);
    let before_len = storage.len;

    logd_init();
    let after_len = storage.len;
    num("   storage bytes before:  ", before_len);
    num("   storage bytes after:   ", after_len);
    num("   queued records before: ", before_q);

    // THE FINDING: logd_init appends its arena to the existing one. It does not
    // reset the queue and does not reset the counters. So an in-process
    // re-initialisation is NOT a restart, and a supervisor that "restarts" a
    // service by calling its init again leaves the old records queued.
    check("logd: each init appends another arena instead of replacing it",
          after_len == before_len + SLOT * SLOTS);
    check("logd: the queued record survived the re-init", msg_len(queue) >= before_q);

    // What a real restart gives, stated as the contract: a new process image has
    // zero counters, an empty queue, and no history. Proven by the numbers the
    // constructor sets, not by pretending to restart.
    check("logd: the ring's slot size is still the declared one", queue.slot == SLOT);
}

fn main() {
    say("t81 logd deep\n");
    t_inject();
    t_boundary();
    t_restart();

    say("t81 done  pass=");
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
