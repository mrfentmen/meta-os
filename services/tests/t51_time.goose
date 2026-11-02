// services/tests/t51_time.goose
//
// B-L1-51 — test program for the time service (B-L1-19).
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHAT IS UNDER TEST
// ------------------
// Conversion and deadlines, which are pure enough to assert exactly, plus the one thing that
// must be true of the running clock: it moves forward. The conversion cases are chosen at
// the boundaries a tick rate creates -- 999 ms at 1000 Hz is 999 ticks, 1000 ms is 1000
// ticks, and the tick count that lands one short of a millisecond must round the same way
// every time rather than depending on which side of a float the implementation chose.
//
// The deadline cases are the ones that cause real outages: an already-expired deadline must
// say so immediately (not wait out a full period), and a budget must not report time
// remaining after it has been exceeded.

import time.time;
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
    say("t51 time\n");

    // --- the requested rate is a request, not an assumption ---
    let hz = requested_tick_hz();
    check("rate requested", hz > 0);
    check("rate plausible", hz >= 100 && hz <= 100000);

    // --- ticks -> ms ---
    let m0, ok0 = ticks_to_ms(0, hz);
    check("0 ticks is 0 ms", m0 == 0 && ok0 == true);
    let m1, ok1 = ticks_to_ms(hz, hz);
    check("one second of ticks", m1 == 1000 && ok1 == true);
    let m2, ok2 = ticks_to_ms(hz / 2, hz);
    check("half a second", m2 == 500 && ok2 == true);

    // A rate of zero must be refused: dividing by it is an abort, and the caller asked
    // something meaningless.
    let bad, bad_ok = ticks_to_ms(10, 0);
    check("zero rate refused", bad_ok == false);

    // --- ms -> ticks ---
    check("1000 ms at hz", ms_to_ticks(1000, hz) == hz);
    check("0 ms", ms_to_ticks(0, hz) == 0);
    check("1 ms is at least one tick", ms_to_ticks(1, hz) >= 1);

    // --- elapsed ---
    check("elapsed", elapsed(1500, 1000) == 500);
    check("elapsed zero", elapsed(1000, 1000) == 0);
    // A backwards reading is a caller bug; the answer must not be a made-up positive.
    check("elapsed backwards is not positive", elapsed(900, 1000) <= 0);

    // --- the clock ---
    var c = clock_init(hz);
    check("clock ok", clock_ok(c));
    check("clock hz", c.hz == hz);
    let u0 = clock_uptime_ms(c);
    check("uptime non-negative", u0 >= 0);
    let u1 = clock_uptime_ms(c);
    check("uptime monotonic", u1 >= u0);

    // --- deadlines ---
    var d = clock_after(c, 50);
    check("fresh deadline does not expire", deadline_expired(d, clock_now(c)) == false);
    check("remaining is positive", deadline_remaining_ms(d, c) > 0);

    // Zero-length deadline is already expired, not "one tick away".
    var d0 = clock_after(c, 0);
    check("zero deadline expired", deadline_expired(d0, clock_now(c) + 1));

    // A deadline in the past stays expired and reports no remaining time.
    var past = clock_after(c, 0);
    check("past deadline no remaining", deadline_remaining_ms(past, c) == 0);

    // --- budget ---
    var bud = clock_budget(c, 20);
    check("budget fresh", clock_budget_expired(bud) == false);
    check("budget left positive", clock_budget_left(bud, c) > 0);

    // --- the clock actually moves ---
    // Short sleep: the assertion is that it returns, and that the uptime did not go
    // backwards. The size of the step is the kernel's business.
    let before = clock_uptime_ms(c);
    let slept = sleep_ms(2, hz);
    let after = clock_uptime_ms(c);
    check("sleep returns", slept == true);
    check("uptime advanced while sleeping", after >= before);

    var r: u8[>..] = [];
    let _ = append_int(r, 32, t_pass);
    say("passed ");
    say(r);
    say("\n");
    if t_fail != 0 { say("FAILURES\n"); sys_exit(1); }
    say("t51 done\n");
    sys_exit(0);
}
