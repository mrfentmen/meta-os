// services/tests/t53_watchdog.goose
//
// B-L1-53 — test program for the health watchdog (B-L1-23).
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHAT IS UNDER TEST
// ------------------
// The watchdog decides that a service is dead. Getting that wrong in either direction is
// expensive: too eager and the layer restarts healthy services (which is how a slow boot
// becomes a restart loop), too slow and a dead service keeps its name while doing nothing.
//
// The cases are therefore about the allowances, not the happy path:
//   - a beat inside the grace period is not a miss;
//   - a miss inside `miss_allow` is silent, and one past it escalates EXACTLY ONCE (a
//     second escalation would spend the service's retry budget on one death);
//   - a check that happens rarely still counts the periods it missed, rather than
//     under-reporting as "one miss";
//   - a beat clears the count, because the count answers "how long silent", not "how often
//     late";
//   - a clock that goes backwards is not a death. If it were, one wall-clock correction
//     would report every service in the layer at once.

import watchdog.watchdog;
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
    say("t53 watchdog\n");

    // --- registration rules ---
    check("zero handle refused", wd_watch(0, 100, 0, 1, 0) == E_INVAL);
    check("negative period refused", wd_watch(11, -1, 0, 1, 0) == E_INVAL);
    check("negative grace refused", wd_watch(11, 100, -1, 1, 0) == E_INVAL);
    check("negative allowance refused", wd_watch(11, 100, 0, -1, 0) == E_INVAL);
    check("watch accepted", wd_watch(11, 100, 10, 1, 0) == CODE_OK);
    check("re-arming is refused", wd_watch(11, 100, 10, 1, 0) == E_STATE);
    check("find", wd_find(11) >= 0);

    // --- inside the period: fine ---
    let slot = wd_find(11);
    let s0, m0 = wd_check_one(slot, 50);
    check("inside the period is fine", s0 == WD_FINE && m0 == 0);

    // --- still inside the grace window: fine ---
    let s1, _ = wd_check_one(slot, 105);
    check("inside grace is fine", s1 == WD_FINE);

    // --- past period+grace, allowance 1: silent on the first miss ---
    let s2, m2 = wd_check_one(slot, 120);
    check("first late check is silent", s2 == WD_SILENT && m2 >= 1);

    // --- a second, much later check: past the allowance, escalates once ---
    let s3, m3 = wd_check_one(slot, 400);
    check("past allowance is dead", s3 == WD_DEAD && m3 > m2);
    // The escalation must not repeat: one death, one restart budget.
    let s4, _ = wd_check_one(slot, 410);
    check("dead is reported, not re-escalated", s4 == WD_STILL_DEAD);
    // And the same lateness is not counted twice: misses must not grow while nothing
    // happens, because that is how a single stall exhausts a retry budget.
    let s5, m5 = wd_check_one(slot, 411);
    check("misses do not inflate on repeated checks", m5 <= m3 + 1);

    // --- a beat clears everything ---
    check("beat accepted", wd_beat(11, 500) == CODE_OK);
    let s6, m6 = wd_check_one(slot, 505);
    check("after beat: fine and count cleared", s6 == WD_FINE && m6 == 0);

    // --- a clock that went backwards is not a miss ---
    // The deadline was set at 500+110; a check at 10 is in the past and must be fine,
    // because a wall-clock correction must never look like a mass death.
    let s7, m7 = wd_check_one(slot, 10);
    check("backwards clock is not a miss", s7 == WD_FINE && m7 == 0);

    // --- counting periods, not checks ---
    // A service that was silent for ~10 periods must report ~10 misses on one check, not 1.
    check("beat before the long silence", wd_beat(11, 1000) == CODE_OK);
    let s8, m8 = wd_check_one(slot, 1000 + 110 + 1100);
    check("misses count whole periods", m8 >= 10);

    // --- unwatch: a clean stop is not a death ---
    check("unwatch", wd_unwatch(11) == CODE_OK);
    check("unwatch twice fails", wd_unwatch(11) == E_NOTFOUND);
    check("gone from the table", wd_find(11) < 0);

    // --- next_dead returns at most one, and names it ---
    check("watch A", wd_watch(21, 100, 0, 0, 0) == CODE_OK);
    check("watch B", wd_watch(22, 100, 0, 0, 0) == CODE_OK);
    let h_first, _ = wd_next_dead(100000);
    check("next_dead names one handle", h_first == 21);
    // The second call finds the other one: escalation is one per call by design.
    let h_second, _ = wd_next_dead(100000);
    check("next_dead advances", h_second == 22);
    // A third call has nothing left to escalate.
    let h_third, code_third = wd_next_dead(100000);
    check("nothing left to escalate", h_third == 0 && code_third == E_NOTFOUND);

    // --- the health numbers add up ---
    let healthy, bad, lateness = wd_count(100000);
    check("counts are non-negative", healthy >= 0 && bad >= 0 && lateness >= 0);
    check("two watched services are accounted for", healthy + bad > 0);

    var r: u8[>..] = [];
    let _ = append_int(r, 32, t_pass);
    say("passed ");
    say(r);
    say("\n");
    if t_fail != 0 { say("FAILURES\n"); sys_exit(1); }
    say("t53 done\n");
    sys_exit(0);
}
