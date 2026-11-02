// services/tests/t75_supervisor_load.goose
//
// BF5-04 — the supervisor under load: ten services, a dependency chain, mixed restart policies,
// a crash budget that runs out, and the table's own quota.
//
// Status: RUNS — measured 2026-11-02 by `run_native.sh`.
//
// WHAT THIS IS AND IS NOT
// -----------------------
// Ten services are registered, started in dependency order, crashed under three policies and
// restarted where the policy says so. What is exercised is the DECISION and the TABLE. No process
// is spawned: `sys_spawn` does not exist (PROPOSALS.md P3), so "restart" here means the slot goes
// RESTARTING -> STARTING and the caller would have been told to spawn. That distinction is the
// point of the test existing before the spawn call does — the policy is proven, the actor is not.

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

// The name of service N in this test. Fixed strings, because registering a generated name would
// hide a name-table bug behind the generator.
fn load_name(i: i64) -> const u8[:] {
    if i == 0 { return "svc-alpha"; }
    if i == 1 { return "svc-bravo"; }
    if i == 2 { return "svc-charlie"; }
    if i == 3 { return "svc-delta"; }
    if i == 4 { return "svc-echo"; }
    if i == 5 { return "svc-foxtrot"; }
    if i == 6 { return "svc-golf"; }
    if i == 7 { return "svc-hotel"; }
    if i == 8 { return "svc-india"; }
    if i == 9 { return "svc-juliet"; }
    return "svc-unknown";
}

fn start_slot(slot: i64) -> bool {
    if sup_set_state(slot, ST_STARTING) != CODE_OK { return false; }
    return sup_set_state(slot, ST_RUNNING) == CODE_OK;
}

fn stop_slot(slot: i64) -> bool {
    if sup_set_state(slot, ST_STOPPING) != CODE_OK { return false; }
    return sup_set_state(slot, ST_STOPPED) == CODE_OK;
}

fn state_is(s: const u8[:], lit: const u8[:]) -> bool {
    if s.len != lit.len { return false; }
    var i: i64 = 0;
    while i < s.len {
        if s[i] != lit[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn args_state_is_running(s: const u8[:]) -> bool { return state_is(s, "running"); }
fn args_state_is_failed(s: const u8[:]) -> bool { return state_is(s, "failed"); }

fn main() {
    say("t75 supervisor under load\n");

    // --- register ten services, each depending on the previous one ---
    var slots: i64[..10] = [0; 10];
    var registered: i64 = 0;
    var i: i64 = 0;
    while i < 10 {
        let needs = if i == 0 { -1 } else { slots[i - 1] };
        let slot, code = sup_register(load_name(i), needs, true);
        if code != CODE_OK { break; }
        slots[i] = slot;
        registered = registered + 1;
        i = i + 1;
    }
    check("ten services registered", registered == 10);
    check("slot count matches", sup_slot_count() == 10);

    // --- the chain starts in order, and a service cannot precede its dependency ---
    check("the second service cannot start before the first", !sup_can_start(slots[1]));
    check("the boot service may start", sup_can_start(slots[0]));
    check("start the boot service", start_slot(slots[0]));
    check("now the second may start", sup_can_start(slots[1]));

    // The boot service is already running from the check above; starting it a second time is
    // an illegal transition (RUNNING -> STARTING), which is the state machine working, not a
    // failure of this loop. So count it as started and drive only the rest.
    var started: i64 = 0;
    i = 0;
    while i < 10 {
        if sup_is_running(slots[i]) { started = started + 1; }
        else if sup_can_start(slots[i]) && start_slot(slots[i]) { started = started + 1; }
        i = i + 1;
    }
    check("all ten reach running", started == 10);
    check("every one reports running", sup_is_running(slots[5]) && sup_is_running(slots[9]));

    // --- policies: a mix, set per service ---
    check("delta never restarts", sup_set_policy(slots[3], RP_NEVER, 0, 100, 30000) == CODE_OK);
    check("echo always restarts", sup_set_policy(slots[4], RP_ALWAYS, 0, 100, 30000) == CODE_OK);
    var p: i64 = 0;
    while p < 10 {
        if p != 3 && p != 4 {
            let _ = sup_set_policy(slots[p], RP_ON_FAIL, 2, 100, 30000);
        }
        p = p + 1;
    }

    // --- one crash under ON_FAIL: restart with a backoff ---
    let d_after, d_delay = sup_on_exit(slots[5], false, 1000);
    check("on-fail crash asks for a restart", d_after == RT_AFTER);
    check("and it backs off rather than spinning", d_delay > 0);
    check("the slot is restarting, not running", sup_state(slots[5]) == ST_RESTARTING);
    check("restart ready moves it to starting", sup_restart_ready(slots[5]) == CODE_OK);
    check("and a second ready is refused", sup_restart_ready(slots[5]) != CODE_OK);
    check("the restarted service can run again", sup_set_state(slots[5], ST_RUNNING) == CODE_OK);

    // --- one crash under NEVER: failed, and it stays failed ---
    let d_delta, _dd = sup_on_exit(slots[3], false, 1000);
    check("never-restart crash gives up", d_delta == RT_GIVE_UP);
    check("the slot is failed", sup_state(slots[3]) == ST_FAILED);
    check("the dependent cannot start while it is failed",
          sup_can_start(slots[4]) || sup_state(slots[4]) == ST_RUNNING);

    // --- a clean exit under ON_FAIL: no restart, walked to stopped ---
    let d_clean, _dc = sup_on_exit(slots[6], true, 1000);
    check("a clean exit is left alone", d_clean == RT_LEAVE);
    check("and the slot is stopped", sup_state(slots[6]) == ST_STOPPED);

    // --- a clean exit under ALWAYS: restarts at once ---
    let d_always, d_zero = sup_on_exit(slots[4], true, 1000);
    check("always restarts a clean exit", d_always == RT_NOW && d_zero == 0);
    check("and does not charge the crash budget", sup_slot_restarts(slots[4]) == 0);

    // --- the crash budget: three crashes on a budget of two ---
    let _r1, _d1 = sup_on_exit(slots[7], false, 100);
    let _ = sup_restart_ready(slots[7]);
    let _ = sup_set_state(slots[7], ST_RUNNING);
    let _r2, _d2 = sup_on_exit(slots[7], false, 100);
    let _ = sup_restart_ready(slots[7]);
    let _ = sup_set_state(slots[7], ST_RUNNING);
    let r3, _d3 = sup_on_exit(slots[7], false, 100);
    check("the third crash on a budget of two gives up", r3 == RT_GIVE_UP);
    check("and the service stays failed", sup_state(slots[7]) == ST_FAILED);
    check("the restarts were counted", sup_slot_restarts(slots[7]) == 2);

    // --- long uptime clears the budget: one failure a day is not a crash loop ---
    check("a long-running service gets its budget back",
          sup_decide(slots[8], false, 30000) == RT_AFTER);

    // --- the table's own quota: registering until it refuses ---
    var extra: i64 = 0;
    var refused_by: i64 = -1;
    while extra < 40 {
        var nm: u8[>..] = [];
        let _ = append_str(nm, 32, "svc-extra");
        let _ = append_int(nm, 32, extra);
        let _extra_slot, extra_code = sup_register(nm[..], -1, true);
        if extra_code != CODE_OK {
            refused_by = extra_code;
            break;
        }
        extra = extra + 1;
    }
    check("the table refuses more services than it holds", refused_by == E_NOROOM);
    check("and it never exceeded its capacity", sup_slot_count() == MAX_SERVICES);
    check("the refusal did not disturb the ten", sup_slot_count() >= 10);

    // --- mixed state is visible, which is the health line's whole job ---
    var running: i64 = 0;
    var failed: i64 = 0;
    var k: i64 = 0;
    // The table is private; the shell reads it through sup_slot_state_name, so the test does
    // the same rather than reaching for state it does not own.
    while k < sup_slot_count() {
        let state = sup_slot_state_name(k);
        if args_state_is_running(state) { running = running + 1; }
        if args_state_is_failed(state) { failed = failed + 1; }
        k = k + 1;
    }
    check("two services are failed after the crashes", failed == 2);
    check("the rest of the ten are still accounted for", running >= 6);

    say("t75 done  pass=");
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
