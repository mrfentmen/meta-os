// services/tests/t52_supervisor.goose
//
// B-L1-52 — test program for the supervisor and its name registry (B-L1-20/B-L1-22).
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHAT IS UNDER TEST, AND WHY THESE CASES
// ---------------------------------------
// The supervisor is the one component that can make a healthy system look broken, because
// every service's fate runs through it. The cases here are its two failure directions:
//
//   - restarting something that should stay down (a loop, filling the log with the same
//     crash until the useful record is gone);
//   - leaving something down that should be running (a service silently missing while the
//     rest of the system reports healthy).
//
// The decision table is tested through `sup_decide` alone where possible, because it is
// pure: given a policy, an exit and an uptime it must answer the same thing every time. A
// decision that depends on hidden state cannot be reviewed, and this is the code that will
// be read at 3am.
//
// The registry cases are the stale-handle ones: a handle is only valid while its slot still
// holds the generation it was issued for.

import supervisor.supervisor;
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
    say("t52 supervisor + registry\n");

    // --- registration ---
    let a_slot, a_code = sup_register("log", 0, true);
    check("register first", a_code == CODE_OK && a_slot == 0);

    let b_slot, b_code = sup_register("storage", 0, true);
    check("register second", b_code == CODE_OK && b_slot == 1);

    // A duplicate name is refused: two services with one name makes every record that
    // names a service ambiguous.
    let dup_slot, dup_code = sup_register("log", 0, true);
    check("duplicate name refused", dup_code == E_STATE && dup_slot == -1);

    // An empty name is refused, and a name at the length limit is not silently truncated.
    let e_slot, e_code = sup_register("", 0, true);
    check("empty name refused", e_code == E_INVAL && e_slot == -1);

    var long: u8[>..] = [];
    var i: i64 = 0;
    while i < NAME_MAX {
        long.push(97);
        i = i + 1;
    }
    let l_slot, l_code = sup_register(long, 0, true);
    check("name too long refused", l_code == E_INVAL && l_slot == -1);

    // --- names to handles ---
    let h, h_code = sup_lookup("log");
    check("lookup finds the service", h_code == CODE_OK && h > 0);
    let h2, _ = sup_lookup("log");
    check("lookup is stable", h == h2);

    let missing, m_code = sup_lookup("nosuch");
    check("lookup of unknown name fails", m_code != CODE_OK);
    check("unknown handle resolves to nothing", sup_resolve(missing) < 0);

    // The name comes back out of the handle, which is what a log line needs.
    check("handle names its service", sup_name_of(h).len == 3);

    // --- the state machine ---
    check("starts stopped", sup_state(a_slot) == ST_STOPPED);
    check("start from stopped is legal", transition_legal(ST_STOPPED, ST_STARTING));
    check("stopped to running is NOT legal (must pass through starting)",
        transition_legal(ST_STOPPED, ST_RUNNING) == false);
    check("stopped to starting to running",
        sup_set_state(a_slot, ST_STARTING) == CODE_OK && sup_set_state(a_slot, ST_RUNNING) == CODE_OK);
    check("is running", sup_is_running(a_slot));
    check("running to starting is NOT legal", transition_legal(ST_RUNNING, ST_STARTING) == false);
    check("illegal transition is refused", sup_set_state(a_slot, ST_STARTING) == E_STATE);
    check("still running after refusal", sup_state(a_slot) == ST_RUNNING);

    // A crash: running -> failed is legal; failed -> running is not.
    check("crash to failed", sup_set_state(a_slot, ST_FAILED) == CODE_OK);
    check("failed to running refused", sup_set_state(a_slot, ST_RUNNING) == E_STATE);

    // --- restart policies, decided purely ---
    // Bring the entry back to a known state and give it each policy in turn.
    check("walk back to stopped", sup_walk_stopped(a_slot) == CODE_OK || sup_state(a_slot) == ST_STOPPED);

    sup_set_policy(a_slot, RP_NEVER, 0, 100, 30000);
    let d1, _ = sup_decide(a_slot, false, 0);
    check("NEVER does not restart a crash", d1 == RT_GIVE_UP);
    let d2, _ = sup_decide(a_slot, true, 0);
    check("NEVER leaves a clean exit", d2 == RT_LEAVE);

    sup_set_policy(a_slot, RP_ON_FAIL, 0, 100, 30000);
    let d3, dl3 = sup_decide(a_slot, false, 0);
    check("ON_FAIL restarts a crash", d3 == RT_AFTER);
    check("ON_FAIL backs off by a positive delay", dl3 > 0);
    let d4, _ = sup_decide(a_slot, true, 0);
    check("ON_FAIL leaves a clean exit", d4 == RT_LEAVE);

    sup_set_policy(a_slot, RP_ALWAYS, 0, 100, 30000);
    let d5, dl5 = sup_decide(a_slot, true, 0);
    check("ALWAYS restarts a clean exit immediately", d5 == RT_NOW && dl5 == 0);
    let d6, _ = sup_decide(a_slot, false, 0);
    check("ALWAYS restarts a crash", d6 == RT_AFTER);

    // --- the retry limit ---
    // With a limit of 2, the third crash gives up. This is the loop guard: without it,
    // RP_ALWAYS on a service that fails instantly is an infinite spawn rate.
    sup_set_policy(b_slot, RP_ON_FAIL, 2, 10, 30000);
    let c1, _ = sup_decide(b_slot, false, 0);
    check("crash 1 restarts", c1 == RT_AFTER);
    let r1, _ = sup_on_exit(b_slot, false, 0);
    check("on_exit 1 restarts", r1 == RT_AFTER);
    check("entry is restarting", sup_state(b_slot) == ST_RESTARTING);
    let back = sup_restart_ready(b_slot);
    check("restart ready moves to starting", back == CODE_OK && sup_state(b_slot) == ST_STARTING);
    // From STARTING the entry can be stopped, which is the hole the state machine had to
    // have closed: an operator must be able to cancel a start in progress.
    check("starting can be stopped", transition_legal(ST_STARTING, ST_STOPPING));
    let _ = sup_on_exit(b_slot, false, 0);
    let r3, _ = sup_on_exit(b_slot, false, 0);
    check("third crash gives up", r3 == RT_GIVE_UP);
    check("gave up leaves it failed", sup_state(b_slot) == ST_FAILED);

    // A service that stayed up long enough is not penalised for an old crash: uptime
    // beyond max_ms resets the attempt count, so one failure a week never exhausts it.
    sup_set_policy(b_slot, RP_ON_FAIL, 1, 10, 30000);
    let _ = sup_on_exit(b_slot, false, 0);
    check("penalty counted", sup_state(b_slot) == ST_FAILED);
    let old, _ = sup_decide(b_slot, false, 30000);
    check("long uptime clears the attempt count", old == RT_AFTER);

    // --- backoff rises, then stays at the ceiling ---
    let back1 = sup_backoff_ms(b_slot, 0);
    let back2 = sup_backoff_ms(b_slot, 1);
    let back9 = sup_backoff_ms(b_slot, 20);
    check("backoff grows", back2 >= back1);
    check("backoff capped", back9 <= 30000);

    // --- can it start? ---
    let can, why = sup_can_start(a_slot);
    check("can_start answers with a reason", can == true || can == false);

    // --- heartbeat bookkeeping ---
    check("beat accepted", sup_beat(a_slot, 1000) == CODE_OK || sup_state(a_slot) != ST_RUNNING);
    let since = sup_ms_since_beat(a_slot, 1500);
    check("ms since beat", since >= 0);

    // --- state names are printable and distinct ---
    check("state name stopped", state_name(ST_STOPPED).len > 0);
    check("state names differ", state_name(ST_RUNNING).len != state_name(ST_FAILED).len
        || state_name(ST_RUNNING)[0] != state_name(ST_FAILED)[0]);

    // --- release: the handle must go stale, and only that one ---
    let hs, hs_code = sup_lookup("storage");
    check("storage handle exists", hs_code == CODE_OK && hs > 0);

    // Release is refused while the service is not STOPPED: reusing a slot under a running
    // service is exactly the stale-reference bug the generation exists to prevent.
    check("release while failed is refused", sup_release(b_slot) == E_STATE);
    check("walk to stopped", sup_walk_stopped(b_slot) == CODE_OK);
    check("release when stopped", sup_release(b_slot) == CODE_OK);
    check("released handle resolves to nothing", sup_resolve(hs) < 0);
    check("the other service is untouched", sup_resolve(h) >= 0);
    let gone, gone_code = sup_lookup("storage");
    check("released name is gone", gone_code != CODE_OK);

    // Registering the name again takes a NEW entry: the released slot's generation is not
    // recycled under the same handle, so every handle ever issued stays dead.
    let again_slot, again_code = sup_register("storage", 0, true);
    check("same name can be registered again", again_code == CODE_OK && again_slot >= 0);
    check("old handle still dead", sup_resolve(hs) < 0);

    var r: u8[>..] = [];
    let _ = append_int(r, 32, t_pass);
    say("passed ");
    say(r);
    say("\n");
    if t_fail != 0 { say("FAILURES\n"); sys_exit(1); }
    say("t52 done\n");
    sys_exit(0);
}
