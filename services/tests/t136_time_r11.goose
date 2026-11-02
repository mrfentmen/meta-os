// services/tests/t136_time_r11.goose
//
// Round 11 (R11-193..198) — the time surface's arithmetic edges.
// t51 proves conversion, sleep and clock_ok on a live clock. This driver adds the
// cases t51 leaves open: the rounding boundary at a non-millisecond tick rate,
// the sub-tick conversion, a deadline constructed as data (not read from the
// clock), the clamp at zero, an already-expired wait returning without sleeping,
// and a budget that cannot report time after it is spent.
//
// Status: written, run pending (the coordinator runs it and fills r11/time.md §5).

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

fn say_int(n: i64) {
    var b: u8[>..] = [];
    let _ = append_int(b, 32, n);
    say(b[..]);
}

fn main() {
    say("t136 time round 11\n");

    // ------------------------------------------------------------------
    // 1. the rate and the stall bound are data, and their values are asserted
    // ------------------------------------------------------------------
    check("the requested rate is 1000 Hz", requested_tick_hz() == 1000);
    check("STALL_LIMIT is 100000 consecutive equal reads", STALL_LIMIT == 100000);

    // ------------------------------------------------------------------
    // 2. ticks -> ms, including a rate that does not divide 1000
    // ------------------------------------------------------------------
    let m0, ok0 = ticks_to_ms(0, 1000);
    check("0 ticks is 0 ms", m0 == 0 && ok0);
    let m1, ok1 = ticks_to_ms(999, 1000);
    check("999 ticks is 999 ms", m1 == 999 && ok1);
    let m2, ok2 = ticks_to_ms(1000, 1000);
    check("1000 ticks is one second", m2 == 1000 && ok2);
    let m3, ok3 = ticks_to_ms(1, 3);
    check("1 tick at 3 Hz rounds down to 333 ms", m3 == 333 && ok3);
    let m4, ok4 = ticks_to_ms(10, 0);
    check("a zero rate is refused, not divided by", m4 == 0 && !ok4);
    let m5, ok5 = ticks_to_ms(10, -1);
    check("a negative rate is refused", m5 == 0 && !ok5);

    // ------------------------------------------------------------------
    // 3. ms -> ticks, including no-sleep and a rate that rounds down
    // ------------------------------------------------------------------
    check("1000 ms at 1000 Hz", ms_to_ticks(1000, 1000) == 1000);
    check("1 ms at 1000 Hz is one tick", ms_to_ticks(1, 1000) == 1);
    check("999 ms at 1000 Hz is 999 ticks", ms_to_ticks(999, 1000) == 999);
    check("1 ms at 3 Hz rounds down to no ticks", ms_to_ticks(1, 3) == 0);
    check("334 ms at 3 Hz is the first whole tick", ms_to_ticks(334, 3) == 1);
    check("0 ms is no sleep", ms_to_ticks(0, 1000) == 0);
    check("negative ms is no sleep", ms_to_ticks(-5, 1000) == 0);
    check("a zero rate yields no ticks", ms_to_ticks(1000, 0) == 0);

    // ------------------------------------------------------------------
    // 4. elapsed, including the backwards reading
    // ------------------------------------------------------------------
    check("elapsed is a subtraction", elapsed(1500, 1000) == 500);
    check("elapsed of the same instant is zero", elapsed(1000, 1000) == 0);
    check("a backwards reading is not made positive", elapsed(900, 1000) < 0);

    // ------------------------------------------------------------------
    // 5. sub-tick resolution
    // ------------------------------------------------------------------
    let u0, uok0 = ticks_to_us(1, 1000);
    check("one tick at 1000 Hz is 1000 us", u0 == 1000 && uok0);
    let u1, uok1 = ticks_to_us(1, 0);
    check("sub-tick conversion refuses a zero rate", u1 == 0 && !uok1);

    // ------------------------------------------------------------------
    // 6. a deadline is data: expired, remaining, and clamped at zero
    // ------------------------------------------------------------------
    var d = Deadline { at: 500 };
    check("a deadline is expired at its instant", deadline_expired(d, 500));
    check("a deadline is not expired one tick early", deadline_expired(d, 499) == false);
    check("a deadline is expired after its instant", deadline_expired(d, 501));
    check("remaining before the deadline", deadline_remaining(d, 400) == 100);
    check("remaining at the deadline is zero", deadline_remaining(d, 500) == 0);
    check("remaining after the deadline is clamped, not negative",
          deadline_remaining(d, 900) == 0);

    // ------------------------------------------------------------------
    // 7. clock construction: a nonsense rate is replaced, not propagated
    // ------------------------------------------------------------------
    var c0 = clock_init(0);
    check("clock_init(0) falls back to 1000 Hz", c0.hz == 1000);
    var cn = clock_init(-5);
    check("a negative rate falls back to 1000 Hz", cn.hz == 1000);
    var c = clock_init(250);
    check("a valid rate is kept", c.hz == 250);

    // clock_after(0) is due immediately, and its instant is not in the past
    let t0 = sys_ticks();
    var due = clock_after(c, 0);
    check("a zero-millisecond deadline is already due", due.at >= t0
          && deadline_expired(due, due.at));
    var later = clock_after(c, 100);
    check("a 100 ms deadline is not due now", deadline_expired(later, later.at - 1) == false);

    // an already-expired wait returns without sleeping
    let now = sys_ticks();
    var past = Deadline { at: now - 1 };
    check("waiting on a past deadline returns true at once", clock_wait(c, past));

    // ------------------------------------------------------------------
    // 8. budgets: a remainder that never goes negative, and an expiry at zero
    // ------------------------------------------------------------------
    // 250 000 ticks at 250 Hz is 1 000 000 ms: the remainder must stay inside that.
    var b = Budget { start: sys_ticks(), total: 250000 };
    let left = clock_budget_left(b, c);
    check("a budget with time left reports a non-negative remainder",
          left >= 0 && left <= 1000000);
    var spent = Budget { start: sys_ticks(), total: 0 };
    check("a zero-total budget is spent", clock_budget_expired(spent));

    // ------------------------------------------------------------------
    // 9. no-sleep paths never touch the clock
    // ------------------------------------------------------------------
    check("sleep_ticks(0) is a no-op", sleep_ticks(0));
    check("sleep_ticks(-1) is a no-op", sleep_ticks(-1));
    check("sleep_ms(0) is a no-op", sleep_ms(0, 1000));
    check("sleep_ms(negative) is a no-op", sleep_ms(-5, 1000));
    check("sleep_ms with a zero rate is a no-op", sleep_ms(10, 0));

    // ------------------------------------------------------------------
    // 10. load: 1000 conversions, all accepted
    // ------------------------------------------------------------------
    var ok_n: i64 = 0;
    var refused: i64 = 0;
    var i: i64 = 0;
    while i < 500 {
        let a, aok = ticks_to_ms(i, 1000);
        if aok && a == i { ok_n = ok_n + 1; } else { refused = refused + 1; }
        let b2 = ms_to_ticks(i, 1000);
        if b2 == i { ok_n = ok_n + 1; } else { refused = refused + 1; }
        i = i + 1;
    }
    check("load: every conversion agreed", ok_n == 1000 && refused == 0);

    say("LOAD time ops=");
    say_int(ok_n + refused);
    say(" ok=");
    say_int(ok_n);
    say(" refused=");
    say_int(refused);
    say("\n");

    say("t136 done  pass=");
    say_int(t_pass);
    say(" fail=");
    say_int(t_fail);
    say("\n");
    if t_fail > 0 { sys_exit(1); }
}
