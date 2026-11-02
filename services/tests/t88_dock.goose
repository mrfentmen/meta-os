// services/tests/t88_dock.goose
//
// Driver for dock — pinning, order, the launch handshake, and the failure paths.
//
// The handshake is where the bugs live: a double click that spawns twice, a result
// for a launch that was never requested, and a launch nobody answers (which must
// become a visible failure rather than a permanent "starting…").

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

fn num(label: const u8[:], v: i64) {
    say(label);
    var b: u8[>..] = [];
    let _ = append_int(b, 32, v);
    say(b[..]);
    say("\n");
}

fn main() {
    say("t88 dock\n");
    dk_init();

    check("dock: empty", dk_count() == 0);
    check("dock: nothing running", dk_running_count() == 0);
    check("dock: nothing pending", dk_pending_count() == 0);

    // --- pinning -------------------------------------------------------------
    let a, ca = dk_pin("terminal");
    check("dock: pin terminal", ca == CODE_OK && a == 1);
    let b, cb = dk_pin("files");
    check("dock: pin files", cb == CODE_OK && b == 2);
    let c, cc = dk_pin("music");
    check("dock: pin music", cc == CODE_OK && c == 3);
    check("dock: three pinned", dk_count() == 3);
    check("dock: order preserved", dk_name_at(0).len == 8 && dk_name_at(1).len == 5 && dk_name_at(2).len == 5);

    let _d, cd = dk_pin("terminal");
    check("dock: duplicate pin is E_STATE", cd == E_STATE);
    let _e, ce = dk_pin("");
    check("dock: empty name is E_INVAL", ce == E_INVAL);
    var longname: u8[..20] = [0; 20];
    var i: i64 = 0;
    while i < 20 { longname[i] = 97; i = i + 1; }
    let _f, cf = dk_pin(longname[..DK_NAME_MAX]);
    check("dock: name at the limit is E_NOROOM", cf == E_NOROOM);
    check("dock: find by name", dk_find_by_name("files") == b);
    check("dock: find an unknown name", dk_find_by_name("nope") == -1);

    // --- ordering ------------------------------------------------------------
    check("dock: move music to the front", dk_move(c, 0) == CODE_OK);
    check("dock: music is first", dk_name_at(0).len == 5 && dk_name_at(0)[0] == 109);
    check("dock: terminal moved to second", dk_name_at(1)[0] == 116);
    check("dock: move terminal back to the front", dk_move(a, 0) == CODE_OK);
    check("dock: terminal first again", dk_name_at(0)[0] == 116);
    check("dock: move to a negative index refused", dk_move(a, -1) == E_INVAL);
    check("dock: move past the end refused", dk_move(a, dk_count()) == E_INVAL);
    check("dock: move an unknown id", dk_move(99, 0) == E_NOTFOUND);
    check("dock: moving to its own index is a no-op", dk_move(a, 0) == CODE_OK);
    check("dock: count unchanged by moves", dk_count() == 3);

    // --- the launch handshake ------------------------------------------------
    check("dock: launch terminal", dk_launch(a, 1000) == CODE_OK);
    check("dock: the launch is pending", dk_pending_count() == 1 && dk_pending_at(0));
    check("dock: the launch was counted", dk_launches_of(a) == 1);
    check("dock: a second click inside the window is E_BUSY", dk_launch(a, 1200) == E_BUSY);
    check("dock: the double click did not count a second launch", dk_launches_of(a) == 1);
    check("dock: a launch of an unknown id", dk_launch(99, 1000) == E_NOTFOUND);
    check("dock: a launch of an app that was never pinned", dk_launch(77, 1000) == E_NOTFOUND);

    check("dock: the result arrives", dk_result(a, true) == CODE_OK);
    check("dock: it is running", dk_running_count() == 1 && dk_running_at(0));
    check("dock: nothing pending", dk_pending_count() == 0);
    check("dock: a second launch while running is E_BUSY", dk_launch(a, 3000) == E_BUSY);
    check("dock: running app cannot be unpinned", dk_unpin(a) == E_BUSY);

    check("dock: a result with no request is E_STATE", dk_result(b, true) == E_STATE);
    check("dock: the bogus result did not mark it running", dk_running_count() == 1);

    // --- a failed launch ------------------------------------------------------
    check("dock: launch files", dk_launch(b, 4000) == CODE_OK);
    check("dock: the launch fails", dk_result(b, false) == CODE_OK);
    check("dock: it is not running", dk_running_count() == 1);
    check("dock: the failure was counted", dk_failures_of(b) == 1);
    check("dock: a failed app can be launched again", dk_launch(b, 5000) == CODE_OK);

    // --- expiry ---------------------------------------------------------------
    check("dock: expire before the timeout does nothing", dk_expire(5000 + DK_LAUNCH_TIMEOUT_MS - 1) == 0);
    check("dock: still pending", dk_pending_count() == 1);
    check("dock: expire at the timeout", dk_expire(5000 + DK_LAUNCH_TIMEOUT_MS) == 1);
    check("dock: nothing pending after expiry", dk_pending_count() == 0);
    check("dock: the expiry was counted as a failure", dk_failures_of(b) == 2);
    check("dock: the expiry is separately visible", dk_expiries_of(b) == 1);
    check("dock: a stale request can be launched again", dk_launch(b, 12000) == CODE_OK);

    // --- unpinning ------------------------------------------------------------
    check("dock: unpin while pending is E_BUSY", dk_unpin(b) == E_BUSY);
    check("dock: resolve the launch", dk_result(b, true) == CODE_OK);
    check("dock: stopping the app", dk_running_off(b) == CODE_OK);
    check("dock: stopping a stopped app is E_STATE", dk_running_off(b) == E_STATE);
    check("dock: unpin now works", dk_unpin(b) == CODE_OK);
    check("dock: count dropped", dk_count() == 2);
    check("dock: the order closed up", dk_name_at(1)[0] == 109);
    check("dock: the unpinned id is gone", dk_launch(b, 20000) == E_NOTFOUND);
    check("dock: unpin an unknown id", dk_unpin(99) == E_NOTFOUND);

    // --- the ceiling ----------------------------------------------------------
    dk_init();
    var n: i64 = 0;
    while n < DK_MAX {
        var nm: u8[..8] = [0; 8];
        nm[0] = 97;
        nm[1] = (97 + (n % 26)) as u8;
        let _id, c2 = dk_pin(nm[..2]);
        if c2 != CODE_OK { say("FAIL dock: fill refused early\n"); t_fail = t_fail + 1; return; }
        n = n + 1;
    }
    check("dock: filled to DK_MAX", dk_count() == DK_MAX);
    var over: u8[..8] = [0; 8];
    over[0] = 122; over[1] = 122;
    let _o, co = dk_pin(over[..2]);
    check("dock: DK_MAX+1 refused with E_NO_SPACE", co == E_NO_SPACE);
    check("dock: the refused pin did not grow the dock", dk_count() == DK_MAX);

    say("t88 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
}
