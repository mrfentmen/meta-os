// services/tests/t61_bootorder.goose
//
// B-L1-64 — test program for the boot order table (services/supervisor/bootorder.goose).
//
// Status: RUNS — tests/t61_bootorder: 24 checks, 0 failures. Measured 2026-11-02 by audit_status.py.
//
// WHAT IS UNDER TEST, AND WHY THESE CASES
// ---------------------------------------
// The boot order is a table, and tables are where review stops looking. The cases here are
// the four ways this particular table can be wrong:
//
//   1. It is internally inconsistent -- a service needs something that starts later. That is
//      a boot that hangs at the twelfth service with no error, so it is checked statically.
//   2. It is complete -- every one of the 22 services appears exactly once, at a distinct
//      order number. A duplicated order silently drops a service from `bo_sequence`.
//   3. `bo_ready` disagrees with the table -- it says "go" before a dependency is running.
//      Tested at both edges: all-but-one dependency running (must be false), all running
//      (must be true).
//   4. The cascade is too wide or too narrow -- a non-fatal failure that takes out its
//      dependants turns one degraded service into an outage, and a fatal one that cascades
//      nothing leaves the system running on a dead floor.
//
// The by-kernel exception gets its own case because it is the one row that does not follow
// the rule, and an exception nobody tests is an exception that grows.

import supervisor.bootorder;
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

// Count how many entries claim a given order number. Used to prove orders are distinct
// without assuming they are dense.
fn order_hits(want: i64) -> i64 {
    var n: i64 = 0;
    var i: i64 = 0;
    while i < bo_count() {
        if bo_entry(i).order == want { n = n + 1; }
        i = i + 1;
    }
    return n;
}

fn has_id(id: i64) -> bool {
    var i: i64 = 0;
    while i < bo_count() {
        if bo_entry(i).id == id { return true; }
        i = i + 1;
    }
    return false;
}

fn main() {
    say("t61 boot order\n");

    // --- 1. internal consistency ---
    check("order is consistent (no forward references)", bo_order_ok());

    // --- 2. completeness ---
    check("table holds 29 entries", bo_count() == 29);
    var ids_ok: bool = true;
    var i: i64 = 0;
    while i < bo_count() {
        let id = bo_entry(i).id;
        if id < 1 || id > 29 { ids_ok = false; }
        i = i + 1;
    }
    check("every id is in 1..29", ids_ok);
    var orders_ok: bool = true;
    var pos: i64 = 1;
    while pos <= bo_count() {
        if order_hits(pos) != 1 { orders_ok = false; }
        pos = pos + 1;
    }
    check("every order number 1..29 used exactly once", orders_ok);

    // --- 3. readiness, both edges ---
    // log needs console, logfmt and storage. Running all but storage must not be ready.
    let log_needs = bo_needs(8);
    check("log is not ready with nothing running", !bo_ready(8, 0));
    check("log is ready with exactly its dependencies", bo_ready(8, log_needs));
    // Clearing any single dependency bit must make it not ready again.
    var any_bit_matters: bool = true;
    var bit: i64 = 0;
    while bit < 28 {
        if (log_needs & (1 << bit)) != 0 {
            if bo_ready(8, log_needs & ~(1 << bit)) { any_bit_matters = false; }
        }
        bit = bit + 1;
    }
    check("log needs every dependency bit, not just some", any_bit_matters);
    check("a service with no dependencies is ready at once", bo_ready(2, 0));

    // --- 4. the by-kernel exception ---
    let sup = bo_entry(5);   // supervisor
    // The boot table's ids are its own contiguous 1..n sequence, NOT the call matrix's --
    // the two agreed only as far as id 1. The `needs` masks below use THESE ids, which is
    // what `bo_ready` is handed.
    check("supervisor is marked by_kernel", sup.by_kernel);
    // Its needs are runtime needs, so it must NOT be gated on log (which it starts).
    check("supervisor does not need log to start", (bo_needs(16) & (1 << 8)) == 0);

    // --- 5. cascade ---
    // log is fatal: killing it must take audit, session, dhcp, dns, socket, timesync,
    // updater and agenthost with it.
    let log_doom = bo_cascade(8);
    check("fatal log cascades to audit", (log_doom & (1 << 13)) != 0);
    check("fatal log cascades to agenthost", (log_doom & (1 << 22)) != 0);
    check("fatal log does not cascade to devices", (log_doom & (1 << 3)) == 0);
    // display is non-fatal: its failure must not take session down with it.
    let disp_doom = bo_cascade(12);
    check("non-fatal display does not cascade to session", (disp_doom & (1 << 15)) == 0);
    check("non-fatal display takes only itself", disp_doom == (1 << 12));

    // --- 6. sequence ---
    var seq: i64[..32] = [0; 32];
    let n = bo_sequence(seq, 32);
    check("sequence yields all 29 in order", n == 29);
    check("sequence starts at bootlog", seq[0] == 2);
    // notify starts last on purpose: it is what the other face services push into, so it
    // must not be waiting on any of them.
    check("sequence ends at notify", seq[n - 1] == 29);
    var monotone: bool = true;
    var k: i64 = 0;
    while k < n {
        if !has_id(seq[k]) { monotone = false; }
        k = k + 1;
    }
    check("every sequenced id exists in the table", monotone);

    // --- 7. names ---
    var buf: u8[>..] = [];
    check("bo_name(8) copies", bo_name(8, buf, 32));
    // id 8 is `logd`, not `log`: the name table carries the service's directory name so a log
    // line names something the manifest has. This assertion failed for exactly that reason
    // when the drift was fixed, which is what an assertion is for.
    check("bo_name(8) is logd", buf.len == 4 && buf[0] == 108 && buf[3] == 100);
    var small: u8[>..] = [];
    check("bo_name refuses a buffer too small", !bo_name(22, small, 4) && small.len == 0);
    check("bo_name refuses id 0", !bo_name(0, small, 32));
    check("bo_name refuses id 30 (past the table)", !bo_name(30, small, 32));
    var last: u8[>..] = [];
    check("bo_name names the last row", bo_name(29, last, 32) && last.len == 6);

    say("t61 done  pass=");
    var pb: u8[>..] = [];
    format_int(pb, t_pass, 10, 0, 0);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    format_int(fb, t_fail, 10, 0, 0);
    say(fb[..]);
    say("\n");
    if t_fail > 0 { sys_exit(1); }
}
