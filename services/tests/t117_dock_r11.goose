// services/tests/t117_dock_r11.goose
//
// Round 11, dock (R11-079..084): the two constants, the dedupe window at its exact
// edge, the launch timeout at its exact edge, and the rules that keep a running app
// reachable.
//
// WHAT IS NEW HERE
// ----------------
// `tests/t88_dock` uses "inside the window" and "at the timeout" as round numbers. The
// two boundaries that matter are the ones a caller can hit on the millisecond: a second
// click at DK_DEDUPE_MS must be a new launch, and a launch at DK_LAUNCH_TIMEOUT_MS must
// already be expired. This driver asserts both sides of each edge, plus the id rule
// (never reused) that makes a stale click harmless.
//
// Status: written for Round 11; run by the coordinator.

import dock.dock;
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

fn main() {
    say("t117 dock round 11\n");
    dk_init();
    check("dock: starts empty", dk_count() == 0);

    // ======================================================================
    // 1. pinning and the name cap
    // ======================================================================
    let a, ca = dk_pin("terminal");
    let b, cb = dk_pin("files");
    let c, cc = dk_pin("music");
    check("pin: three apps, ids 1..3", ca == CODE_OK && cb == CODE_OK && cc == CODE_OK
          && a == 1 && b == 2 && c == 3);
    check("pin: order is insertion order", dk_name_at(0).len == 8 && dk_name_at(1).len == 5);
    check("pin: music keeps its id at index 2", dk_id_at(2) == c);

    let _, dup = dk_pin("terminal");
    check("pin: a duplicate name is E_STATE", dup == E_STATE);
    let _, empty = dk_pin("");
    check("pin: an empty name is E_INVAL", empty == E_INVAL);

    // DK_NAME_MAX is the field width; the last byte is the terminator, so 16 is refused.
    var n16: u8[..16] = [0; 16];
    var fi: i64 = 0;
    while fi < DK_NAME_MAX { n16[fi] = 97; fi = fi + 1; }
    let _, over = dk_pin(n16[..DK_NAME_MAX]);
    check("pin: a name of DK_NAME_MAX bytes is E_NOROOM", over == E_NOROOM);

    var n15: u8[..16] = [0; 16];
    fi = 0;
    while fi < DK_NAME_MAX - 1 { n15[fi] = 97; fi = fi + 1; }
    let fifteen, c15 = dk_pin(n15[..DK_NAME_MAX - 1]);
    check("pin: a name of DK_NAME_MAX-1 bytes is accepted", c15 == CODE_OK && fifteen > 0);
    check("pin: find by name returns the id", dk_find_by_name("files") == b);

    // Control characters are not a name. The check is per byte, not a length check.
    var ctrl: u8[..8] = [0; 8];
    ctrl[0] = 1;
    ctrl[1] = 65;
    let _, cbad = dk_pin(ctrl[..2]);
    check("pin: a control byte is E_INVAL", cbad == E_INVAL);

    // The refused names did not grow the dock: four pins succeeded.
    check("pin: refusals left the count at four", dk_count() == 4);

    // ======================================================================
    // 2. ids are never reused, which is what makes a stale click harmless
    // ======================================================================
    check("id: unpin the 15-byte app", dk_unpin(fifteen) == CODE_OK);
    check("id: the count falls", dk_count() == 3);
    let again, cagain = dk_pin(n15[..DK_NAME_MAX - 1]);
    check("id: the same name re-pins with a new id", cagain == CODE_OK && again > fifteen);
    check("id: the old id resolves to nothing", dk_launch(fifteen, 0) == E_NOTFOUND);

    // ======================================================================
    // 3. ordering, and the indices that must be refused
    // ======================================================================
    check("move: back to index 0", dk_move(again, 0) == CODE_OK);
    check("move: the moved name is first", dk_name_at(0)[0] == 97);
    check("move: a negative index is E_INVAL", dk_move(again, -1) == E_INVAL);
    check("move: index == count is E_INVAL", dk_move(again, dk_count()) == E_INVAL);
    check("move: an unknown id is E_NOTFOUND", dk_move(999, 0) == E_NOTFOUND);
    check("move: to its own index is a no-op", dk_move(again, 0) == CODE_OK);

    // ======================================================================
    // 4. the dedupe window, both sides
    // ======================================================================
    check("launch: a click starts a launch", dk_launch(a, 1000) == CODE_OK);
    check("launch: it is pending and counted once", dk_pending_count() == 1
          && dk_launches_of(a) == 1);
    check("launch: one millisecond inside the window is E_BUSY",
          dk_launch(a, 1000 + DK_DEDUPE_MS - 1) == E_BUSY);
    check("launch: the refusal counted nothing", dk_launches_of(a) == 1);
    check("launch: exactly at the window is a new launch",
          dk_launch(a, 1000 + DK_DEDUPE_MS) == CODE_OK);
    check("launch: and it counted", dk_launches_of(a) == 2);
    check("launch: still one pending request", dk_pending_count() == 1);

    // ======================================================================
    // 5. resolving, the running rules, and the failure path
    // ======================================================================
    check("result: the app reports running", dk_result(a, true) == CODE_OK);
    check("result: nothing is pending", dk_pending_count() == 0);
    check("result: it is running", dk_running_count() == 1);
    check("result: a launch while running is E_BUSY", dk_launch(a, 9000) == E_BUSY);
    check("result: a running app cannot be unpinned", dk_unpin(a) == E_BUSY);
    check("result: a result with no request is E_STATE", dk_result(b, true) == E_STATE);
    check("result: an unknown id is E_NOTFOUND", dk_result(999, true) == E_NOTFOUND);

    check("running_off: the app exits", dk_running_off(a) == CODE_OK);
    check("running_off: twice is E_STATE", dk_running_off(a) == E_STATE);

    // A failed launch is still an outcome: not running, failures up, retry allowed.
    check("fail: launch files", dk_launch(b, 4000) == CODE_OK);
    check("fail: the supervisor reports failure", dk_result(b, false) == CODE_OK);
    check("fail: not running, failure counted", dk_running_count() == 0 && dk_failures_of(b) == 1);
    check("fail: a failed app can launch again", dk_launch(b, 6000) == CODE_OK);

    // ======================================================================
    // 6. the launch timeout, both sides
    // ======================================================================
    check("expire: one millisecond early expires nothing",
          dk_expire(6000 + DK_LAUNCH_TIMEOUT_MS - 1) == 0);
    check("expire: still pending", dk_pending_count() == 1);
    check("expire: exactly at the timeout expires it",
          dk_expire(6000 + DK_LAUNCH_TIMEOUT_MS) == 1);
    check("expire: nothing is pending", dk_pending_count() == 0);
    check("expire: counted as a failure", dk_failures_of(b) == 2);
    check("expire: and separately as an expiry", dk_expiries_of(b) == 1);
    check("expire: a second pass over nothing is zero", dk_expire(99999) == 0);
    check("expire: a launch after expiry is legal", dk_launch(b, 12000) == CODE_OK);

    // A pending launch must not be unpinned: the dock would lose the only handle to
    // the process that is about to exist.
    check("unpin: pending is E_BUSY", dk_unpin(b) == E_BUSY);
    check("unpin: resolve it first", dk_result(b, true) == CODE_OK);
    check("unpin: running is E_BUSY", dk_unpin(b) == E_BUSY);
    check("unpin: stop it", dk_running_off(b) == CODE_OK);
    check("unpin: now it comes off", dk_unpin(b) == CODE_OK);
    check("unpin: unknown id is E_NOTFOUND", dk_unpin(999) == E_NOTFOUND);

    // ======================================================================
    // 7. readers, including out of range
    // ======================================================================
    check("readers: a negative index is 0", dk_id_at(-1) == 0);
    check("readers: an index past the end has no name", dk_name_at(999).len == 0);
    check("readers: past the end is not running", !dk_running_at(999));
    check("readers: past the end is not pending", !dk_pending_at(999));
    check("readers: an unknown id has no launch count", dk_launches_of(999) == -1);
    check("readers: an unpinned name is not found", dk_find_by_name("files") == -1);

    // ======================================================================
    // 8. the table's ceiling
    // ======================================================================
    dk_init();
    var n: i64 = 0;
    var filled: i64 = 0;
    while n < DK_MAX {
        var nm: u8[..4] = [0; 4];
        nm[0] = 97;
        nm[1] = (97 + n) as u8;
        let _id, cpin = dk_pin(nm[..2]);
        if cpin == CODE_OK { filled = filled + 1; }
        n = n + 1;
    }
    check("cap: DK_MAX apps fit", filled == DK_MAX && dk_count() == DK_MAX);
    var over_nm: u8[..4] = [0; 4];
    over_nm[0] = 122;
    over_nm[1] = 122;
    let _, cf = dk_pin(over_nm[..2]);
    check("cap: the next pin is E_NO_SPACE", cf == E_NO_SPACE);
    check("cap: the refused pin did not grow the dock", dk_count() == DK_MAX);

    // ======================================================================
    // 9. load: a hundred launch handshakes, ten times a normal batch
    // ======================================================================
    dk_init();
    let lh, lc = dk_pin("load");
    check("load: one app pinned", lc == CODE_OK);
    var ops: i64 = 100;
    var ok_n: i64 = 0;
    var refused_n: i64 = 0;
    var t: i64 = 0;
    var li: i64 = 0;
    while li < ops {
        let cl = dk_launch(lh, t);
        if cl == CODE_OK {
            let _ = dk_result(lh, true);
            let _ = dk_running_off(lh);
            ok_n = ok_n + 1;
        } else {
            refused_n = refused_n + 1;
        }
        t = t + 2000;
        li = li + 1;
    }
    check("load: every handshake completed", ok_n == ops && refused_n == 0);
    check("load: the launch counter followed", dk_launches_of(lh) == ops);

    var lbuf: u8[>..] = [];
    let _ = append_str(lbuf, 512, "LOAD dock ops=");
    let _ = append_int(lbuf, 512, ops);
    let _ = append_str(lbuf, 512, " ok=");
    let _ = append_int(lbuf, 512, ok_n);
    let _ = append_str(lbuf, 512, " refused=");
    let _ = append_int(lbuf, 512, refused_n);
    say(lbuf[..]);
    say("\n");

    say("t117 done  pass=");
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
