// services/tests/t111_dashboard_r11.goose
//
// R11-043..048 — the dashboard feed's two limits (DF_MAX_KIND, DF_MAX_AGE_MS) and
// every refusal it can make, driven from a host process.
//
// The point this file defends: a metric is never invented. A never-sampled kind
// reports DF_NEVER, a stale one keeps its value and carries its age, and neither is
// printed as 0. The window boundary is tested on both sides (fresh exactly at the
// window, stale one millisecond past it), because an off-by-one here is a dashboard
// that lies about "now" by a whole window.
//
// Status: written for Round 11; the coordinator runs it and records the result.

import dashboard.dashboard;
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

fn bytes_eq(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn label_is(kind: i64, now_ms: i64, want: const u8[:]) -> bool {
    var out: u8[>..] = [];
    df_label(kind, now_ms, out);
    return bytes_eq(out[..], want);
}

fn main() {
    say("t111 dashboard r11\n");

    // ======================================================================
    // 1. the limits, as data
    // ======================================================================
    check("DF_MAX_KIND is 4", DF_MAX_KIND == 4);
    check("DF_MAX_AGE_MS is 60000", DF_MAX_AGE_MS == 60000);

    df_init();
    check("a fresh feed has nothing sampled", df_missing_count() == DF_MAX_KIND);

    // ======================================================================
    // 2. never is not zero
    // ======================================================================
    let v0, never = df_get(DF_CPU, 0);
    check("a never-sampled metric reports DF_NEVER", never == DF_NEVER);
    check("its value is 0 only because there is no value", v0 == 0);
    check("the label says never, and invents no unit", label_is(DF_DISK, 0, "disk never"));

    // ======================================================================
    // 3. range refusals
    // ======================================================================
    check("kind 0 is refused", df_put(0, 10, 0) == E_INVAL);
    check("a kind past DF_MAX_KIND is refused",
          df_put(DF_MAX_KIND + 1, 10, 0) == E_INVAL);
    check("a negative percentage is refused", df_put(DF_CPU, -1, 0) == E_INVAL);
    check("CPU over 100% is refused", df_put(DF_CPU, 101, 0) == E_INVAL);
    check("network bytes are not a percentage", df_put(DF_NET, 150, 0) == CODE_OK);

    // ======================================================================
    // 4. the staleness boundary, exactly
    // ======================================================================
    check("a sample is recorded", df_put(DF_CPU, 42, 1000) == CODE_OK);
    let v1, fresh = df_get(DF_CPU, 1000);
    check("at the sample time it is fresh", v1 == 42 && fresh == DF_FRESH);
    check("the CPU window is 2000 ms", df_window(DF_CPU) == 2000);
    check("exactly at the window it is still fresh", df_verdict(DF_CPU, 3000) == DF_FRESH);
    check("one millisecond past it is stale", df_verdict(DF_CPU, 3001) == DF_STALE);
    let v2, stale = df_get(DF_CPU, 3001);
    check("a stale metric keeps its value", v2 == 42 && stale == DF_STALE);
    check("the stale label carries the age", label_is(DF_CPU, 3001, "cpu 42% stale 2s"));

    // The clock does not go backwards: a past-stamped sample would read as fresh.
    check("a backwards clock is refused", df_put(DF_CPU, 43, 500) == E_STATE);

    // ======================================================================
    // 5. the window limit
    // ======================================================================
    check("a zero window is refused", df_set_window(DF_CPU, 0) == E_INVAL);
    check("a window past DF_MAX_AGE_MS is refused",
          df_set_window(DF_CPU, DF_MAX_AGE_MS + 1) == E_INVAL);
    check("exactly DF_MAX_AGE_MS is accepted",
          df_set_window(DF_CPU, DF_MAX_AGE_MS) == CODE_OK);
    check("the window reads back", df_window(DF_CPU) == DF_MAX_AGE_MS);

    check("a tight window is accepted", df_set_window(DF_MEM, 100) == CODE_OK);
    check("a mem sample is recorded", df_put(DF_MEM, 61, 10000) == CODE_OK);
    check("100 ms later the mem figure is fresh", df_verdict(DF_MEM, 10100) == DF_FRESH);
    check("101 ms later it is stale", df_verdict(DF_MEM, 10101) == DF_STALE);

    // ======================================================================
    // 6. counts, and the load loop
    // ======================================================================
    check("a disk sample is recorded", df_put(DF_DISK, 33, 20000) == CODE_OK);
    check("a net sample is recorded", df_put(DF_NET, 900, 20000) == CODE_OK);
    check("a mem sample is refreshed", df_put(DF_MEM, 62, 20000) == CODE_OK);
    check("a cpu sample is refreshed", df_put(DF_CPU, 44, 20000) == CODE_OK);
    check("all four metrics are present", df_missing_count() == 0);
    check("all four are fresh at 20000", df_fresh_count(20000) == DF_MAX_KIND);
    check("the fresh count falls as the short windows expire",
          df_fresh_count(30000) < DF_MAX_KIND);

    var ops: i64 = 0;
    var ok: i64 = 0;
    var refused: i64 = 0;
    var i: i64 = 0;
    while i < 1000 {
        let now = 30000 + i * 10;
        ops = ops + 1;
        if i % 100 == 0 {
            // One refusal per hundred, on a kind whose range is a percentage.
            if df_put(DF_CPU, 200, now) == E_INVAL { refused = refused + 1; }
        } else {
            let kind = 1 + (i % DF_MAX_KIND);
            if df_put(kind, i % 100, now) == CODE_OK { ok = ok + 1; }
        }
        i = i + 1;
    }
    check("the load loop kept every valid sample and refused every invalid one",
          ok == 990 && refused == 10);

    say("LOAD dashboard ops="); put_num(ops);
    say(" ok="); put_num(ok);
    say(" refused="); put_num(refused);
    say("\n");

    say("t111 done  pass="); put_num(t_pass);
    say(" fail="); put_num(t_fail);
    say("\n");
    if t_fail > 0 { sys_exit(1); }
}
