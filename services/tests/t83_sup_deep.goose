// services/tests/t83_sup_deep.goose
//
// Round 7 B, supervisor — the failure paths, the boundaries, and what a restart of
// the supervisor itself would mean.
//
// t30_supervisor proves the happy path. This file attacks it: illegal transitions,
// a restart budget that has to run out, a table that has to fill, handles that go
// stale, and the one question nobody had asked — does releasing a slot actually
// free it? (Answer: no. Section (c) is what proved it.)
//
// Status: RUNS — set by `audit_status.py` from the runner's row, not by hand.

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

fn num(label: const u8[:], v: i64) {
    say(label);
    var b: u8[>..] = [];
    let _ = append_int(b, 32, v);
    say(b[..]);
    say("\n");
}

// A distinct name per slot, built without a formatter so the test does not depend
// on one: "svc07" style, always shorter than NAME_MAX.
fn gen_name(n: i64) -> u8[>..] {
    var s: u8[>..] = [];
    let _ = s.push('s');
    let _ = s.push('v');
    let _ = s.push('c');
    if n >= 10 {
        let hi: u8 = (48 + (n / 10)) as u8;
        let _ = s.push(hi);
    }
    let lo: u8 = (48 + (n % 10)) as u8;
    let _ = s.push(lo);
    return s;
}

fn repeat(n: i64) -> u8[>..] {
    var s: u8[>..] = [];
    var i: i64 = 0;
    while i < n { let _ = s.push('x'); i = i + 1; }
    return s;
}

// ===========================================================================
// (a) Failure injection

fn t_inject() {
    say("-- (a) failure injection\n");

    // An illegal move must be refused AND must change nothing. A supervisor that
    // accepts a jump will later report a dead service as running.
    let a, ca = sup_register("a", -1, true);
    check("sup: register 'a'", a == 0 && ca == CODE_OK);
    check("sup: STOPPED -> RUNNING refused", sup_set_state(0, ST_RUNNING) == E_STATE);
    check("sup: state unchanged by refusal", sup_state(0) == ST_STOPPED);
    check("sup: STOPPED -> STARTING ok", sup_set_state(0, ST_STARTING) == CODE_OK);
    check("sup: STARTING -> RUNNING ok", sup_set_state(0, ST_RUNNING) == CODE_OK);
    check("sup: RUNNING -> STARTING refused", sup_set_state(0, ST_STARTING) == E_STATE);
    check("sup: state is RUNNING", sup_state(0) == ST_RUNNING);
    check("sup: RUNNING -> STOPPED is not a legal jump", sup_set_state(0, ST_STOPPED) == E_STATE);

    // Out-of-range slots answer, they do not read memory.
    check("sup: set_state(-1)", sup_set_state(-1, ST_RUNNING) == E_INVAL);
    check("sup: set_state(past end)", sup_set_state(99, ST_RUNNING) == E_INVAL);
    check("sup: state(-1) is -1", sup_state(-1) == -1);
    check("sup: state(past end) is -1", sup_state(99) == -1);
    check("sup: is_running(-1)", !sup_is_running(-1));

    // Registration refusals.
    let dup, cdup = sup_register("a", -1, true);
    check("sup: duplicate name refused", dup == -1 && cdup == E_STATE);
    let cnt = sup_slot_count();
    let empty, cempty = sup_register("", -1, true);
    check("sup: empty name refused", empty == -1 && cempty == E_INVAL);
    let long = sup_register(repeat(NAME_MAX), -1, true);
    check("sup: name of exactly NAME_MAX refused", long == -1);
    check("sup: refusals did not grow the table", sup_slot_count() == cnt);

    // A heartbeat from something that is not up is a state disagreement.
    check("sup: beat from STOPPED refused", sup_beat(1, 100) == E_INVAL);
    let b, cb = sup_register("b", -1, true);
    check("sup: register 'b'", b == 1 && cb == CODE_OK);
    check("sup: beat from STOPPED refused (registered)", sup_beat(1, 100) == E_STATE);
    check("sup: ms_since_beat on a never-beaten slot", sup_ms_since_beat(1, 500) == 500);
    check("sup: clock going backwards reads as fresh", sup_ms_since_beat(1, 0) == 0);

    // Dependency gate.
    let c, cc = sup_register("c", 2, true);          // needs slot 2, not running
    check("sup: register 'c'", c == 2 && cc == CODE_OK);
    let okc, codec = sup_can_start(2);
    check("sup: cannot start before its dependency", !okc && codec == E_STATE);
    let me, cme = sup_register("selfy", 3, true);
    check("sup: register self-dependency", me == 3 && cme == CODE_OK);
    let oks, codes = sup_can_start(3);
    check("sup: cannot depend on itself", !oks && codes == E_STATE);
    let bad, cbad = sup_register("bad", 99, true);
    check("sup: register a dependency past the end", bad == 4 && cbad == CODE_OK);
    let okb, codeb = sup_can_start(4);
    check("sup: dependency index past the end is E_INVAL", !okb && codeb == E_INVAL);
    let dis, cdis = sup_register("dis", -1, false);
    check("sup: register disabled", dis == 5 && cdis == CODE_OK);
    let okd, coded = sup_can_start(5);
    check("sup: disabled service cannot start", !okd && coded == E_STATE);

    // Release is refused while the service is anything but STOPPED.
    check("sup: release while RUNNING refused", sup_release(0) == E_STATE);
    check("sup: release out of range", sup_release(99) == E_INVAL);

    // --- the restart budget -------------------------------------------------
    // Three crashes with max_restarts = 2: two restarts, then give up. The entry
    // must stay FAILED, not STOPPED: "stopped" reads as a decision that went well.
    let x, cx = sup_register("crash", -1, true);
    check("sup: register 'crash'", x == 6 && cx == CODE_OK);
    check("sup: policy on 'crash'", sup_set_policy(6, RP_ON_FAIL, 2, 10, 1000) == CODE_OK);
    check("sup: crash -> STARTING", sup_set_state(6, ST_STARTING) == CODE_OK);
    check("sup: crash -> RUNNING", sup_set_state(6, ST_RUNNING) == CODE_OK);

    let d1, w1 = sup_on_exit(6, false, 0);
    check("sup: crash 1 -> RT_AFTER", d1 == RT_AFTER);
    check("sup: crash 1 delay is base", w1 == 10);
    check("sup: crash 1 counted", sup_slot_restarts(6) == 1);
    check("sup: crash 1 leaves RESTARTING", sup_state(6) == ST_RESTARTING);
    check("sup: restart_ready -> STARTING", sup_restart_ready(6) == CODE_OK);
    check("sup: restart is STARTING", sup_state(6) == ST_STARTING);
    check("sup: restart -> RUNNING", sup_set_state(6, ST_RUNNING) == CODE_OK);

    let d2, w2 = sup_on_exit(6, false, 0);
    check("sup: crash 2 -> RT_AFTER", d2 == RT_AFTER);
    check("sup: crash 2 delay doubled", w2 == 20);
    check("sup: crash 2 counted", sup_slot_restarts(6) == 2);
    check("sup: restart 2 ready", sup_restart_ready(6) == CODE_OK);
    check("sup: restart 2 -> RUNNING", sup_set_state(6, ST_RUNNING) == CODE_OK);

    let d3, w3 = sup_on_exit(6, false, 0);
    check("sup: budget exhausted -> RT_GIVE_UP", d3 == RT_GIVE_UP);
    check("sup: give-up has no delay", w3 == 0);
    check("sup: give-up leaves FAILED, not STOPPED", sup_state(6) == ST_FAILED);
    check("sup: give-up does not count another restart", sup_slot_restarts(6) == 2);

    // A service that stayed up earns a clean slate; otherwise anything failing
    // once a week would exhaust its budget eventually.
    check("sup: restart it manually", sup_set_state(6, ST_RESTARTING) != E_STATE);
    check("sup: back to STARTING", sup_set_state(6, ST_STARTING) != E_STATE);
    let d4, w4 = sup_on_exit(6, false, 30000);      // uptime == max_ms
    check("sup: long uptime resets the budget", d4 == RT_AFTER && w4 == 10);
    check("sup: attempts reset to 1", sup_slot_restarts(6) == 1);

    // Policy boundaries.
    check("sup: policy -> RP_NEVER", sup_set_policy(6, RP_NEVER, 5, 10, 100) == CODE_OK);
    let dnever, wnever = sup_on_exit(6, false, 0);
    check("sup: RP_NEVER gives up on a crash", dnever == RT_GIVE_UP && wnever == 0);
    check("sup: invalid policy number refused",
          sup_set_policy(6, 7, 5, 10, 100) == E_INVAL);
    check("sup: base_ms 0 refused", sup_set_policy(6, RP_ON_FAIL, 5, 0, 100) == E_INVAL);
    check("sup: max_ms < base_ms refused", sup_set_policy(6, RP_ON_FAIL, 5, 200, 100) == E_INVAL);
    check("sup: negative max_restarts refused", sup_set_policy(6, RP_ON_FAIL, -1, 10, 100) == E_INVAL);
    check("sup: policy out of range slot", sup_set_policy(99, RP_ON_FAIL, 1, 10, 100) == E_INVAL);

    // A clean exit is not a crash: RP_ON_FAIL leaves it alone, RP_ALWAYS restarts
    // it at once with no backoff.
    let y, cy = sup_register("clean", -1, true);
    check("sup: register 'clean'", y == 7 && cy == CODE_OK);
    check("sup: clean -> STARTING", sup_set_state(7, ST_STARTING) == CODE_OK);
    check("sup: clean -> RUNNING", sup_set_state(7, ST_RUNNING) == CODE_OK);
    let d5, w5 = sup_on_exit(7, true, 5);
    check("sup: clean exit under ON_FAIL -> RT_LEAVE", d5 == RT_LEAVE && w5 == 0);
    check("sup: clean exit walked to STOPPED, not jumped", sup_state(7) == ST_STOPPED);
    check("sup: clean exit policy", sup_set_policy(7, RP_ALWAYS, 3, 10, 100) == CODE_OK);
    check("sup: clean -> STARTING again", sup_set_state(7, ST_STARTING) == CODE_OK);
    check("sup: clean -> RUNNING again", sup_set_state(7, ST_RUNNING) == CODE_OK);
    let d6, w6 = sup_on_exit(7, true, 5);
    check("sup: clean exit under ALWAYS -> RT_NOW", d6 == RT_NOW && w6 == 0);
    check("sup: ALWAYS leaves it STOPPED for the caller to spawn", sup_state(7) == ST_STOPPED);
    check("sup: ALWAYS did not charge a restart", sup_slot_restarts(7) == 0);
}

// ===========================================================================
// (b) Boundary sweep

fn t_bounds() {
    say("-- (b) boundary sweep\n");

    // Backoff: base 10, cap 1000. Doubling, then flat at the cap. The loop is
    // checked from attempt 0 so the first restart is never the slow one.
    check("sup: set policy for backoff sweep", sup_set_policy(0, RP_ON_FAIL, 20, 10, 1000) == CODE_OK);
    check("sup: backoff attempt 0 == base", sup_backoff_ms(0, 0) == 10);
    check("sup: backoff attempt 1", sup_backoff_ms(0, 1) == 20);
    check("sup: backoff attempt 2", sup_backoff_ms(0, 2) == 40);
    check("sup: backoff attempt 3", sup_backoff_ms(0, 3) == 80);
    check("sup: backoff attempt 4", sup_backoff_ms(0, 4) == 160);
    check("sup: backoff attempt 5", sup_backoff_ms(0, 5) == 320);
    check("sup: backoff attempt 6", sup_backoff_ms(0, 6) == 640);
    check("sup: backoff attempt 7 hits the cap", sup_backoff_ms(0, 7) == 1000);
    check("sup: backoff stays at the cap", sup_backoff_ms(0, 40) == 1000);
    check("sup: backoff does not overflow at 62", sup_backoff_ms(0, 62) == 1000);

    // Handles: 0 is never valid, a stale handle resolves to nothing.
    let h0 = sup_handle(0);
    check("sup: handle is non-zero", h0 > 0);
    check("sup: handle resolves to its slot", sup_resolve(h0) == 0);
    check("sup: handle 0 does not resolve", sup_resolve(0) == -1);
    check("sup: negative handle does not resolve", sup_resolve(-5) == -1);
    check("sup: handle out of range is 0", sup_handle(99) == 0);
    check("sup: handle names its service", sup_name_of(h0) == "a");

    // Name length boundary: NAME_MAX-1 is the longest name that fits.
    let before = sup_slot_count();
    let n31, c31 = sup_register(repeat(NAME_MAX - 1), -1, true);
    check("sup: name of NAME_MAX-1 accepted", n31 >= 0 && c31 == CODE_OK);
    check("sup: NAME_MAX-1 registration grew the table", sup_slot_count() == before + 1);
    check("sup: name of NAME_MAX refused", sup_register(repeat(NAME_MAX), -1, true) == -1);

    // MAX_SERVICES: fill to the boundary and prove the next one is refused. The
    // table is static, so this is the last chance to register in this program.
    var i = sup_slot_count();
    while i < MAX_SERVICES {
        let s, c = sup_register(gen_name(i), -1, true);
        if c != CODE_OK { say("FAIL sup: fill refused early\n"); t_fail = t_fail + 1; return; }
        i = i + 1;
    }
    check("sup: table filled to MAX_SERVICES", sup_slot_count() == MAX_SERVICES);
    let over, cover = sup_register("overflow", -1, true);
    check("sup: MAX_SERVICES+1 refused", over == -1 && cover == E_NOROOM);
    check("sup: refused registration did not grow the table", sup_slot_count() == MAX_SERVICES);
    check("sup: slot past the end has no name", sup_slot_name(MAX_SERVICES).len == 0);
    check("sup: state name of a bad slot", sup_slot_state_name(MAX_SERVICES) == "unknown");
    check("sup: restarts of a bad slot", sup_slot_restarts(MAX_SERVICES) == -1);
    check("sup: enabled of a bad slot", !sup_slot_enabled(MAX_SERVICES));
}

// ===========================================================================
// (c) Restart semantics

fn t_restart() {
    say("-- (c) restart semantics\n");

    // There is no reset entry point and no unregister. Every entry stays in the
    // table for the life of the process, which is the honest statement: a
    // supervisor "restart" is a new address space with table_len == 0, and the
    // only thing that can produce one is the kernel spawning the service again.
    let n_now = sup_slot_count();
    check("sup: table stays at MAX_SERVICES after all failures", n_now == MAX_SERVICES);

    // Release is documented as freeing a slot for reuse. It does not: the entry
    // keeps its name, its slot, and table_len never shrinks, so sup_register (which
    // always appends) can never fill the freed slot. This is a defect in the
    // doc-comment, not in the refusal -- but the effect is real: after releasing a
    // service the table is still full, and a re-register is refused twice over.
    check("sup: bring slot 1 to STOPPED", sup_set_state(1, ST_FAILED) != E_STATE);
    check("sup: FAILED -> STOPPED", sup_set_state(1, ST_STOPPED) == CODE_OK);
    let old_name = sup_slot_name(1);
    check("sup: release a stopped slot", sup_release(1) == CODE_OK);
    check("sup: release did not shrink the table (no unregister exists)", sup_slot_count() == n_now);
    check("sup: release clears the name", sup_slot_name(1).len == 0);
    // The released slot's name is gone, so a re-register is not refused as a
    // duplicate -- it is refused because sup_register always appends and the table
    // is full. The slot that was released cannot be handed out again: the only
    // API that can create an entry is the one that cannot reach a freed slot.
    let rereg, crereg = sup_register(old_name, -1, true);
    check("sup: a released slot cannot be re-registered (table appends, never reuses)",
          rereg == -1 && crereg == E_NOROOM);
    check("sup: registering a new name still fails with the table full",
          sup_register("z", -1, true) == -1);
    check("sup: released slot's restarts reset", sup_slot_restarts(1) == 0);
    check("sup: released slot is disabled", !sup_slot_enabled(1));

    // Because release bumps the generation, every handle issued before it is dead.
    // This is the property that makes a handle worth having, and it survives even
    // though the slot cannot yet be refilled.
    let h_new = sup_handle(1);
    check("sup: new handle resolves after release", sup_resolve(h_new) == 1);
    let h_old = h_new - 1;
    check("sup: the previous generation's handle is dead", sup_resolve(h_old) == -1);
    check("sup: a dead handle has no name", sup_name_of(h_old).len == 0);

    // Generation wrap: 70 000 releases is past HANDLE_GEN_MAX, so the counter has
    // to wrap without ever colliding with slot 2's handle range. A wrap that landed
    // ON HANDLE_GEN_MAX would make slot 1's handle equal (2*MAX + 0).
    var wrap_ok = true;
    var k: i64 = 0;
    // Slot 1's handles live in [(1+1)*MAX, (1+2)*MAX); slot 2's begin at 3*MAX.
    let ceiling = (1 + 2) * HANDLE_GEN_MAX;
    while k < 70000 {
        if sup_release(1) != CODE_OK { wrap_ok = false; break; }
        let h = sup_handle(1);
        if h <= 0 || h >= ceiling { wrap_ok = false; break; }
        if sup_resolve(h) != 1 { wrap_ok = false; break; }
        k = k + 1;
    }
    check("sup: 70000 releases wrap the generation without collision", wrap_ok);
    num("     releases performed: ", k);
    check("sup: generation never reached the slot-2 handle range", sup_handle(1) < ceiling);

    // What is lost on a real restart, stated as a fact the reader can check: the
    // table and every counter in it live in `var` module storage, so a fresh process
    // begins at table_len == 0 and this driver's own first check proves it -- the
    // first register in t_inject landed on slot 0.
    check("sup: slot 0 is the first entry a fresh process creates (table_len starts 0)", sup_slot_name(0)[..] == "a"[..]);
}

fn main() {
    say("t83 supervisor deep\n");
    t_inject();
    t_bounds();
    t_restart();

    say("t83 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
}
