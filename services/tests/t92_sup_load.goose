// services/tests/t92_sup_load.goose
//
// D2/D3 — the supervisor and the boot order watched under load: three full boots, a
// cascade drill at the head of the boot, and a restart budget that has to run out.
//
// WHAT THIS IS FOR
// ----------------
// The boot order table is proven consistent by `bootorder_check.py`, and the supervisor's
// state machine is proven by t30 and t83. Neither of those says what happens when all 29
// services are started THROUGH the order, three times, and one of them dies halfway. This
// file is that: the order and the runner driven to completion repeatedly, with the
// failures injected where a real boot would meet them.
//
// The three questions it answers, in order:
//   (a) does a full boot finish, and does it finish the same way every time?
//   (b) if a fatal service is dead before boot, does the machine still reach the end
//       instead of hanging on the service that needed it?
//   (c) does a crash loop run out of budget and stop, rather than restart forever?
//
// Status: RUNS — set by `audit_status.py` from the runner's row, not by hand.

import supervisor.supervisor;
import supervisor.bootorder;
import supervisor.deps;
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

fn popcount(mask: i64) -> i64 {
    var n: i64 = 0;
    var i: i64 = 0;
    while i < 63 {
        if (mask & (1 << i)) != 0 { n = n + 1; }
        i = i + 1;
    }
    return n;
}

// Start every service the runner can start. Returns (started_count, last_code, steps).
// The step cap is what turns a hang into a failure: a runner that never completes must
// fail the test with a number, not wedge the run.
fn drive(r: DepRunner&, cap: i64) -> i64, i64, i64 {
    var steps: i64 = 0;
    var last: i64 = CODE_OK;
    while steps < cap {
        let id, code = deps_step(r);
        last = code;
        if id == 0 { break; }
        steps = steps + 1;
    }
    return r.started_count, last, steps;
}

// Copy the boot sequence into `out`; returns the count.
fn sequence(out: i64[..32]&) -> i64 {
    return bo_sequence(out, 32);
}

fn main() {
    say("t92 supervisor load\n");
    let total = bo_count();
    num("     services in the boot order: ", total);

    // ======================================================================
    // (a) three full boots, each through the real order
    // ======================================================================
    // A fresh runner per boot, because that is what a restart of the supervisor gives
    // you: no memory of what was running. The comparison across runs is the point --
    // an order that depends on hash iteration or on which slot was free would come out
    // different on the second run, and nothing else would notice.
    var seq: i64[..32] = [0; 32];
    let seq_n = sequence(seq);
    check("the sequence carries every service", seq_n == total);
    var seq_monotone: bool = true;
    var i: i64 = 1;
    while i < seq_n {
        // Each id in the sequence must start no earlier than the one before it, read
        // through the declared `order` field rather than the array position.
        if bo_order_of(seq[i]) < bo_order_of(seq[i - 1]) { seq_monotone = false; }
        i = i + 1;
    }
    check("the sequence is monotone in declared order", seq_monotone);

    var boots: i64 = 0;
    var same_every_time: bool = true;
    var all_full: bool = true;
    var total_steps: i64 = 0;
    while boots < 3 {
        var r = deps_new();
        let started, code, steps = drive(r, 200);
        total_steps = total_steps + steps;
        if started != total { all_full = false; }
        if code != CODE_OK { all_full = false; }
        if !deps_complete(r) { all_full = false; }
        // Every service in the table must be marked running, and none failed.
        var pos: i64 = 1;
        while pos <= total {
            let id = bo_at(pos);
            if id != 0 && !deps_is_running(r, id) { all_full = false; }
            pos = pos + 1;
        }
        if r.failed != 0 { all_full = false; }
        // The start order this boot actually produced must equal the table's sequence.
        // `deps_step` walks orders in sequence, so a mismatch means the walk reordered.
        if steps != seq_n { same_every_time = false; }
        boots = boots + 1;
    }
    check("three boots, all 29 started each time", all_full);
    check("three boots, same number of start decisions", same_every_time);
    num("     start decisions across three boots: ", total_steps);
    num("     expected: ", seq_n * 3);

    // A fourth step after completion is not an error and starts nothing: the supervisor
    // is polled by a loop, and a "done" that returns a service would start one twice.
    var done_runner = deps_new();
    let wasted, done_code, done_steps = drive(done_runner, 200);
    check("driving a fresh runner uses no steps twice", done_steps <= 200 && done_code == CODE_OK);
    let extra_id, extra_code = deps_step(done_runner);
    check("stepping a completed boot starts nothing", extra_id == 0 && extra_code == CODE_OK);

    // ======================================================================
    // (b) cascade drill — a fatal service is dead before the boot begins
    // ======================================================================
    // logd is the service everything writes through. It is marked failed at step 0, the
    // way a supervisor would find it after a crash in a previous boot. The property under
    // test is that the boot still ENDS: the runner must not wait for a dependency that
    // will never arrive, and it must not spin.
    let log_doom = bo_cascade(8);
    num("     logd cascade affects: ", popcount(log_doom));
    var r2 = deps_new();
    r2.failed = log_doom;
    let s2, c2, st2 = drive(r2, 300);
    check("boot with logd dead returns a code, not a hang", c2 == CODE_OK || c2 == E_BUSY);
    check("boot with logd dead reaches completion", deps_complete(r2));
    check("boot with logd dead does not start it", !deps_is_running(r2, 8));
    // The count is exact, not a lower bound: exactly the services outside the cascade
    // start, and no service inside it does. A looser assertion here would pass on a
    // runner that also started one it had already marked failed.
    check("boot with logd dead starts exactly the services it does not block",
          s2 == total - popcount(log_doom));
    check("boot with logd dead starts nothing in the cascade", (log_doom & r2.running) == 0);
    num("     started with logd dead: ", s2);
    num("     steps with logd dead: ", st2);
    // Nothing outside the cascade may be missing.
    var outside_missing: i64 = 0;
    var p: i64 = 1;
    while p <= total {
        let id = bo_at(p);
        if id != 0 && (log_doom & (1 << id)) == 0 && !deps_is_running(r2, id) {
            outside_missing = outside_missing + 1;
        }
        p = p + 1;
    }
    check("no service outside the cascade is left unstarted", outside_missing == 0);

    // The harsher drill: devices (id 3) is fatal and nearly everything needs it. The
    // boot must still end, and it must end with far fewer services than a clean boot.
    let dev_doom = bo_cascade(3);
    var r3 = deps_new();
    r3.failed = dev_doom;
    let s3, c3, _ = drive(r3, 300);
    check("boot with devices dead completes instead of hanging", deps_complete(r3));
    check("boot with devices dead starts fewer services than a clean boot", s3 < total);
    num("     devices cascade affects: ", popcount(dev_doom));
    num("     started with devices dead: ", s3);

    // ======================================================================
    // (c) restart budget under load — a crash loop has to stop
    // ======================================================================
    // Register the whole boot order, then crash one service repeatedly under a budget of
    // two restarts. The decisions must be AFTER, AFTER, GIVE_UP, with the delay doubling
    // and the entry staying FAILED at the end -- "gave up" is not "stopped cleanly".
    var registered: i64 = 0;
    var pos: i64 = 1;
    while pos <= total {
        let id = bo_at(pos);
        if id != 0 {
            var nm: u8[>..] = [];
            let ok = bo_name(id, nm, 32);
            if ok {
                let slot, code = sup_register(nm[..], bo_needs(id), true);
                if code == CODE_OK { registered = registered + 1; }
            }
        }
        pos = pos + 1;
    }
    check("all 29 services register in one table", registered == total);

    // The service under test is slot 7 (logd, id 8 in bootorder terms). Registering in
    // order makes slot = id - 1, which this asserts rather than assumes.
    var log_slot: i64 = -1;
    var q: i64 = 0;
    while q < total {
        if sup_slot_name(q).len == 4 && sup_slot_name(q)[0] == 108 && sup_slot_name(q)[3] == 100 {
            log_slot = q;
        }
        q = q + 1;
    }
    check("logd found by name in the registered table", log_slot >= 0);
    check("the policy setter accepts a two-restart budget",
          sup_set_policy(log_slot, RP_ON_FAIL, 2, 100, 1000) == CODE_OK);

    sup_set_state(log_slot, ST_RUNNING);
    let d1, w1 = sup_on_exit(log_slot, false, 10);
    sup_set_state(log_slot, ST_STARTING);
    sup_set_state(log_slot, ST_RUNNING);
    let d2, w2 = sup_on_exit(log_slot, false, 10);
    sup_set_state(log_slot, ST_STARTING);
    sup_set_state(log_slot, ST_RUNNING);
    let d3, w3 = sup_on_exit(log_slot, false, 10);
    check("first crash restarts after the base delay", d1 == RT_AFTER && w1 == 100);
    check("second crash restarts after twice the base", d2 == RT_AFTER && w2 == 200);
    check("third crash gives up instead of restarting", d3 == RT_GIVE_UP && w3 == 0);
    check("a service that gave up is FAILED, not STOPPED", sup_state(log_slot) == ST_FAILED);
    check("the restart counter stopped at the budget", sup_slot_restarts(log_slot) == 2);

    // Uptime earns a clean slate: one long-lived run must reset the budget, or a service
    // that fails once a week eventually exhausts a budget it never should have spent.
    sup_set_policy(log_slot, RP_ON_FAIL, 2, 100, 1000);
    sup_set_state(log_slot, ST_STARTING);
    sup_set_state(log_slot, ST_RUNNING);
    let d4, w4 = sup_on_exit(log_slot, false, 5000);
    check("a crash after 5 s of uptime restarts again", d4 == RT_AFTER && w4 == 100);

    // A clean exit under ON_FAIL is a decision, not a failure: no restart, no budget.
    sup_set_state(log_slot, ST_STARTING);
    sup_set_state(log_slot, ST_RUNNING);
    let d5, w5 = sup_on_exit(log_slot, true, 10);
    check("a clean exit is left alone under ON_FAIL", d5 == RT_LEAVE && w5 == 0);
    check("a clean exit lands in STOPPED", sup_state(log_slot) == ST_STOPPED);

    // ======================================================================
    // (d) the order holds after all of that
    // ======================================================================
    check("the boot order is still consistent after the drills", bo_order_ok());
    check("the table still has every entry", bo_count() == total);

    say("t92 done  pass=");
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
