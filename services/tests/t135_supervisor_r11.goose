// services/tests/t135_supervisor_r11.goose
//
// Round 11 (R11-187..192) — the supervisor's capacity, handle and policy edges.
// t52 drives the state machine, t75 the load ceiling, t83 the deep lifecycle.
// This driver adds the edges those three leave open: the name rules at both ends,
// the 33rd registration, a dependency chain, self- and bad-dependency refusals,
// and every restart decision including the healthy-run reset and the spent budget.
//
// It cannot prove a real process restart: no spawn call exists. It proves the
// decision and the state moves that a real restart would be built on.
//
// Status: written, run pending (the coordinator runs it and fills r11/supervisor.md §5).

import supervisor.supervisor;
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

fn say_int(n: i64) {
    var b: u8[>..] = [];
    let _ = append_int(b, 32, n);
    say(b[..]);
}

fn main() {
    say("t135 supervisor round 11\n");

    check("the table starts empty", sup_slot_count() == 0);

    // ------------------------------------------------------------------
    // 1. name rules: empty and NAME_MAX are both refused, before any slot is used
    // ------------------------------------------------------------------
    var empty: u8[..1] = [0; 1];
    let _e_slot, e_code = sup_register(empty[..0], -1, true);
    check("an empty name is E_INVAL", e_code == E_INVAL);

    var long: u8[..40] = [0; 40];
    var lf: i64 = 0;
    while lf < 31 { long[lf] = 76; lf = lf + 1; }   // 'L': a real 31-byte name
    let _l_slot, l_code = sup_register(long[..32], -1, true);
    check("a name of NAME_MAX bytes is E_INVAL", l_code == E_INVAL);
    let l2_slot, l2_code = sup_register(long[..31], -1, true);
    check("a name of NAME_MAX-1 bytes is accepted", l2_code == CODE_OK);
    check("the accepted name occupies slot 0", l2_slot == 0);
    check("the long name is findable", sup_find(long[..31]) == 0);
    check("the two refused names created no rows", sup_slot_count() == 1);

    // Duplicate refusal, checked here while the table has room: at a full table capacity is
    // checked first, so the same duplicate reports E_NOROOM (asserted in section 2).
    let _dup_slot, dup_code = sup_register(long[..31], -1, true);
    check("a duplicate name at a non-full table is E_STATE", dup_code == E_STATE);

    // ------------------------------------------------------------------
    // 2. fill to MAX_SERVICES, with four slots carrying deliberate dependencies
    // ------------------------------------------------------------------
    var slots: i64[..32] = [0; 32];
    slots[0] = l2_slot;
    var fill_ok = true;
    var i: i64 = 1;
    while i < 32 {
        var n: u8[..4] = [0; 4];
        n[0] = 's';
        n[1] = (48 + (i / 10)) as u8;
        n[2] = (48 + (i % 10)) as u8;
        var need: i64 = -1;
        var enabled: bool = true;
        if i == 1 { need = 0; }          // depends on slot 0
        if i == 2 { need = 0; enabled = false; }   // disabled, but has a dependency
        if i == 3 { need = 3; }          // depends on itself
        if i == 4 { need = 99; }         // depends on nothing that exists
        let slot, code = sup_register(n[..3], need, enabled);
        if code == CODE_OK { slots[i] = slot; } else { fill_ok = false; }
        i = i + 1;
    }
    check("32 registrations accepted", fill_ok && sup_slot_count() == 32);

    var n33: u8[..4] = [0; 4];
    n33[0] = 's';
    n33[1] = '3';
    n33[2] = '2';
    let _x_slot, x_code = sup_register(n33[..3], -1, true);
    check("the 33rd registration is E_NOROOM", x_code == E_NOROOM);
    let _d_slot, d_code = sup_register("s01", -1, true);
    // FINDING: sup_register checks capacity before it checks for a duplicate, so at a full
    // table a duplicate name reports E_NOROOM. The duplicate refusal itself is asserted above,
    // while the table had room.
    check("a duplicate name at a full table is E_NOROOM (capacity checked first)",
          d_code == E_NOROOM);

    // ------------------------------------------------------------------
    // 3. handles: live, stale, and unknown names
    // ------------------------------------------------------------------
    let h1, h1_code = sup_lookup("s01");
    check("lookup finds a registered name", h1 > 0 && h1_code == CODE_OK);
    check("a fresh handle resolves to its slot", sup_resolve(h1) == slots[1]);
    check("a handle past the table is 0", sup_handle(32) == 0);
    let nh, n_code = sup_lookup("nope");
    check("an unknown name is E_NOTFOUND with handle 0", nh == 0 && n_code == E_NOTFOUND);

    // ------------------------------------------------------------------
    // 4. the state machine's edges
    // ------------------------------------------------------------------
    let s0 = slots[0];
    check("a new slot is STOPPED", sup_state(s0) == ST_STOPPED);
    check("STOPPED -> RUNNING is refused", sup_set_state(s0, ST_RUNNING) == E_STATE
          && sup_state(s0) == ST_STOPPED);
    check("STOPPED -> STARTING", sup_set_state(s0, ST_STARTING) == CODE_OK);
    check("STARTING -> RUNNING", sup_set_state(s0, ST_RUNNING) == CODE_OK);
    check("RUNNING -> RUNNING is refused (it is a heartbeat)",
          sup_set_state(s0, ST_RUNNING) == E_STATE);
    check("a bad slot index is E_INVAL", sup_set_state(999, ST_RUNNING) == E_INVAL);
    check("release of a running slot is E_STATE", sup_release(s0) == E_STATE);

    // ------------------------------------------------------------------
    // 5. dependencies
    // ------------------------------------------------------------------
    let c0, c0_code = sup_can_start(s0);
    check("a boot service can start", c0 && c0_code == CODE_OK);
    let c1, c1_code = sup_can_start(slots[1]);
    check("a service whose dependency is running can start", c1 && c1_code == CODE_OK);
    let c2, c2_code = sup_can_start(slots[2]);
    check("a disabled service cannot start", !c2 && c2_code == E_STATE);
    let c3, c3_code = sup_can_start(slots[3]);
    check("a self-dependency is refused", !c3 && c3_code == E_STATE);
    let c4, c4_code = sup_can_start(slots[4]);
    check("a dependency past the table is E_INVAL", !c4 && c4_code == E_INVAL);

    // ------------------------------------------------------------------
    // 6. heartbeats, including the backwards clock
    // ------------------------------------------------------------------
    let s1 = slots[1];
    check("STARTING slot 1", sup_set_state(s1, ST_STARTING) == CODE_OK);
    check("RUNNING slot 1", sup_set_state(s1, ST_RUNNING) == CODE_OK);
    check("a heartbeat from a running service is accepted", sup_beat(s1, 500) == CODE_OK);
    check("time since the beat", sup_ms_since_beat(s1, 600) == 100);
    check("a backwards clock reads as fresh", sup_ms_since_beat(s1, 400) == 0);
    check("a beat from a stopped service is E_STATE", sup_beat(slots[2], 0) == E_STATE);

    // ------------------------------------------------------------------
    // 7. release: legal only from STOPPED, and it invalidates the handle
    // ------------------------------------------------------------------
    check("RUNNING -> STOPPING", sup_set_state(s0, ST_STOPPING) == CODE_OK);
    check("STOPPING -> STOPPED", sup_set_state(s0, ST_STOPPED) == CODE_OK);
    let stale = sup_handle(s0);
    check("release from STOPPED", sup_release(s0) == CODE_OK);
    check("the old handle no longer resolves", sup_resolve(stale) == -1);
    check("the released name is gone", sup_find(long[..31]) == -1);
    let dep_ok, dep_code = sup_can_start(slots[1]);
    check("a service whose dependency was released cannot start",
          !dep_ok && dep_code == E_STATE);

    // ------------------------------------------------------------------
    // 8. policy: every decision, the backoff, the reset, and the budget
    // ------------------------------------------------------------------
    let s5 = slots[5];
    check("a bad policy is E_INVAL", sup_set_policy(s5, 9, 0, 100, 30000) == E_INVAL);
    check("base_ms of zero is E_INVAL", sup_set_policy(s5, RP_ON_FAIL, 0, 0, 30000) == E_INVAL);
    check("max_ms below base_ms is E_INVAL",
          sup_set_policy(s5, RP_ON_FAIL, 0, 1000, 500) == E_INVAL);
    check("a negative restart budget is E_INVAL",
          sup_set_policy(s5, RP_ON_FAIL, -1, 100, 30000) == E_INVAL);

    check("set RP_NEVER", sup_set_policy(s5, RP_NEVER, 0, 100, 30000) == CODE_OK);
    let dn, dn_ms = sup_decide(s5, false, 0);
    check("RP_NEVER gives up on an unclean exit", dn == RT_GIVE_UP && dn_ms == 0);

    let s6 = slots[6];
    check("set RP_ON_FAIL", sup_set_policy(s6, RP_ON_FAIL, 0, 100, 30000) == CODE_OK);
    let dc, dc_ms = sup_decide(s6, true, 0);
    check("RP_ON_FAIL leaves on a clean exit", dc == RT_LEAVE && dc_ms == 0);

    let s7 = slots[7];
    check("set RP_ALWAYS", sup_set_policy(s7, RP_ALWAYS, 0, 100, 30000) == CODE_OK);
    let da, da_ms = sup_decide(s7, true, 0);
    check("RP_ALWAYS restarts a clean exit at once", da == RT_NOW && da_ms == 0);

    let s8 = slots[8];
    check("set the backoff ladder", sup_set_policy(s8, RP_ON_FAIL, 0, 100, 30000) == CODE_OK);
    check("backoff attempt 0 is base_ms", sup_backoff_ms(s8, 0) == 100);
    check("backoff attempt 1 doubles", sup_backoff_ms(s8, 1) == 200);
    check("backoff attempt 2 doubles", sup_backoff_ms(s8, 2) == 400);
    check("backoff attempt 8 is below the cap", sup_backoff_ms(s8, 8) == 25600);
    check("backoff attempt 9 is capped", sup_backoff_ms(s8, 9) == 30000);
    check("a large attempt stays at the cap", sup_backoff_ms(s8, 500) == 30000);

    // budget: two restarts allowed, the third exit gives up
    let s9 = slots[9];
    check("set a two-restart budget", sup_set_policy(s9, RP_ON_FAIL, 2, 100, 30000) == CODE_OK);
    check("slot 9 is RUNNING", sup_set_state(s9, ST_STARTING) == CODE_OK
          && sup_set_state(s9, ST_RUNNING) == CODE_OK);
    let d1, ms1 = sup_on_exit(s9, false, 1);
    check("first crash restarts after 100 ms", d1 == RT_AFTER && ms1 == 100);
    check("first crash is counted", sup_slot_restarts(s9) == 1);
    check("first crash leaves RESTARTING", sup_state(s9) == ST_RESTARTING);
    let d2, ms2 = sup_on_exit(s9, false, 1);
    check("second crash restarts after 200 ms", d2 == RT_AFTER && ms2 == 200);
    check("second crash is counted", sup_slot_restarts(s9) == 2);
    let d3, ms3 = sup_on_exit(s9, false, 1);
    check("the third crash gives up", d3 == RT_GIVE_UP && ms3 == 0);
    check("giving up leaves FAILED, not STOPPED", sup_state(s9) == ST_FAILED);

    // a healthy run resets the attempt count: 30 s of uptime before the crash
    let s10 = slots[10];
    check("set an unlimited policy", sup_set_policy(s10, RP_ON_FAIL, 0, 100, 30000) == CODE_OK);
    check("slot 10 is RUNNING", sup_set_state(s10, ST_STARTING) == CODE_OK
          && sup_set_state(s10, ST_RUNNING) == CODE_OK);
    let h1, hms1 = sup_on_exit(s10, false, 1);
    check("a short run costs one attempt", h1 == RT_AFTER && sup_slot_restarts(s10) == 1);
    let h2, hms2 = sup_on_exit(s10, false, 30000);
    check("a healthy run resets to the base delay", h2 == RT_AFTER && hms2 == 100);

    // a clean exit under ON_FAIL walks STOPPING -> STOPPED, never jumps
    let s11 = slots[11];
    check("slot 11 is RUNNING", sup_set_state(s11, ST_STARTING) == CODE_OK
          && sup_set_state(s11, ST_RUNNING) == CODE_OK);
    let lc, lms = sup_on_exit(s11, true, 1);
    check("a clean exit leaves", lc == RT_LEAVE && lms == 0);
    check("a clean exit ends STOPPED", sup_state(s11) == ST_STOPPED);

    // restart_ready is the only way out of RESTARTING, and only from RESTARTING
    let s13 = slots[13];
    check("slot 13 is RUNNING", sup_set_state(s13, ST_STARTING) == CODE_OK
          && sup_set_state(s13, ST_RUNNING) == CODE_OK);
    let _r, _rms = sup_on_exit(s13, false, 1);
    check("slot 13 waits in RESTARTING", sup_state(s13) == ST_RESTARTING);
    check("restart_ready from RESTARTING is accepted", sup_restart_ready(s13) == CODE_OK);
    check("restart_ready moves to STARTING", sup_state(s13) == ST_STARTING);
    check("restart_ready from STARTING is E_STATE", sup_restart_ready(s13) == E_STATE);

    // ------------------------------------------------------------------
    // 9. load: 640 name lookups, 500 found and 140 unknown
    // ------------------------------------------------------------------
    var ok_n: i64 = 0;
    var bad_n: i64 = 0;
    var k: i64 = 0;
    while k < 500 {
        let _lh, lcode = sup_lookup("s10");
        if lcode == CODE_OK { ok_n = ok_n + 1; }
        k = k + 1;
    }
    k = 0;
    while k < 140 {
        let _uh, ucode = sup_lookup("zz");
        if ucode == E_NOTFOUND { bad_n = bad_n + 1; }
        k = k + 1;
    }
    check("load: every known lookup resolved", ok_n == 500);
    check("load: every unknown lookup refused", bad_n == 140);

    say("LOAD supervisor ops=");
    say_int(ok_n + bad_n);
    say(" ok=");
    say_int(ok_n);
    say(" refused=");
    say_int(bad_n);
    say("\n");

    say("t135 done  pass=");
    say_int(t_pass);
    say(" fail=");
    say_int(t_fail);
    say("\n");
    if t_fail > 0 { sys_exit(1); }
}
