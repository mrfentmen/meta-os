// services/tests/t106_board_r11.goose
//
// Round 11 (R11-013..018): every room and post refusal, the full-log rule (refuse, never
// overwrite), the cursor, the export/import round trip, and an atomic import that must
// apply nothing when one line is bad.
//
// Status: written 2026-11-02; run by the coordinator's native pass.

import board.board;
import common.err.err;
import common.sys.sys;
import common.fmt.fmt;

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
    say("t106 board deepen\n");
    bd_init();

    // ======================================================================
    // 1. rooms: four fit, duplicates and bad names do not
    // ======================================================================
    let r1, c1 = bd_room_add("general");
    check("room: the first room gets id 1", c1 == CODE_OK && r1 == 1);
    let rd, cd = bd_room_add("general");
    check("room: a duplicate name is E_STATE", cd == E_STATE && rd == -1);
    let re, ce = bd_room_add("");
    check("room: an empty name is E_INVAL", ce == E_INVAL && re == -1);
    let rc, cc = bd_room_add("bad,name");
    check("room: a comma is E_INVAL", cc == E_INVAL);

    var longname: u8[..16] = [97; 16];
    let ln, lnc = bd_room_add(longname[..]);
    check("room: a 16-byte name is E_NOROOM", lnc == E_NOROOM && ln == -1);

    let r2, c2 = bd_room_add("r2");
    let r3, c3 = bd_room_add("r3");
    let r4, c4 = bd_room_add("r4");
    check("room: rooms 2-4 fit", c2 == CODE_OK && c3 == CODE_OK && c4 == CODE_OK);
    let r5, c5 = bd_room_add("r5");
    check("room: the fifth room is E_NO_SPACE", c5 == E_NO_SPACE && r5 == -1);
    check("room: the count did not move on a refusal", bd_room_count() == BD_MAX_ROOMS);

    // ======================================================================
    // 2. posts: the refusals, in the order the code checks them
    // ======================================================================
    let pu, puc = bd_post(99, "hello", 0);
    check("post: an unknown room is E_NOTFOUND", puc == E_NOTFOUND && pu == 0);
    let p0, p0c = bd_post(1, "", 0);
    check("post: empty text is E_INVAL", p0c == E_INVAL && p0 == 0);
    let pn, pnc = bd_post(1, "bad\ntext", 0);
    check("post: a newline is E_INVAL", pnc == E_INVAL && pn == 0);
    var longtext: u8[..96] = [97; 96];
    let pt, ptc = bd_post(1, longtext[..], 0);
    check("post: a 96-byte text is E_NOROOM", ptc == E_NOROOM && pt == 0);

    let p1, p1c = bd_post(1, "hello", 1);
    let p2, p2c = bd_post(1, "world", 2);
    check("post: ids are 1 and 2", p1c == CODE_OK && p1 == 1 && p2c == CODE_OK && p2 == 2);
    check("post: the room count follows", bd_post_count(1) == 2);
    check("post: the last id is the cursor", bd_last_id(1) == 2);
    check("post: unread from 0 is both", bd_unread(1, 0) == 2);
    check("post: unread from the last id is none", bd_unread(1, 2) == 0);

    // ======================================================================
    // 3. the fetch: "id:text" lines, appended, and its refusal
    // ======================================================================
    var out: u8[>..] = [];
    let fn1, fc1 = bd_fetch(1, 0, out);
    check("fetch: two posts", fn1 == 2 && fc1 == CODE_OK);
    check("fetch: the wire form is 16 bytes", out.len == 16);
    var out2: u8[>..] = [];
    let fn2, fc2 = bd_fetch(1, 1, out2);
    check("fetch: since the first id returns the second", fn2 == 1 && out2.len == 8);
    // The cursor is exclusive: a client that has id 2 already gets nothing back, which is
    // the property that makes "fetch since what I hold" idempotent on a retry.
    var out4: u8[>..] = [];
    let fn4, fc4 = bd_fetch(1, 2, out4);
    check("fetch: since the newest id returns nothing",
          fn4 == 0 && out4.len == 0 && fc4 == CODE_OK);
    var out3: u8[>..] = [];
    let fn3, fc3 = bd_fetch(99, 0, out3);
    check("fetch: an unknown room is E_NOTFOUND", fc3 == E_NOTFOUND && fn3 == 0);

    // ======================================================================
    // 4. the full log refuses; it does not overwrite
    // ======================================================================
    var i: i64 = 0;
    var added: i64 = 0;
    while i < 22 {
        let _p, pcode = bd_post(1, "p", 0);
        if pcode == CODE_OK { added = added + 1; }
        i = i + 1;
    }
    check("full: 22 more posts fit", added == 22 && bd_post_count(1) == BD_MAX_POSTS);
    let ov, ovc = bd_post(1, "overflow", 0);
    check("full: the 25th post is E_NO_SPACE", ovc == E_NO_SPACE && ov == 0);
    check("full: the refusal is counted", bd_refused_total() == 1);
    check("full: the count did not move", bd_post_count(1) == BD_MAX_POSTS);
    check("full: the oldest post is still the oldest", bd_last_id(1) == BD_MAX_POSTS);

    // ======================================================================
    // 5. export and import: a round trip, then an atomic refusal
    // ======================================================================
    bd_init();
    let rr, rrc = bd_room_add("r1");
    let e1, e1c = bd_post(1, "one", 10);
    let e2, e2c = bd_post(1, "two", 20);
    check("round trip: a small board", rrc == CODE_OK && e1c == CODE_OK && e2c == CODE_OK);

    var exp: u8[..2048] = [0; 2048];
    let en = bd_export(exp);
    check("round trip: export writes bytes", en > 0);

    bd_init();
    check("round trip: init clears the board", bd_room_count() == 0 && bd_post_total() == 0);
    let im = bd_import(exp[..en]);
    check("round trip: import returns the line count", im == 3);
    check("round trip: the room is back", bd_room_count() == 1 && bd_room_id_at(0) == 1);
    check("round trip: the posts are back", bd_post_total() == 2 && bd_post_count(1) == 2);
    check("round trip: the cursor skips what was read", bd_last_id(1) == 2);

    bd_init();
    let bad = bd_import("X,bad\n");
    check("import: a malformed line is E_CORRUPT", bad == E_CORRUPT);
    check("import: a malformed file applies nothing",
          bd_room_count() == 0 && bd_post_total() == 0);
    let orphan = bd_import("P,1,9,0,hello\n");
    check("import: a post in an undefined room is E_CORRUPT", orphan == E_CORRUPT);

    // ======================================================================
    // 6. load: ten times the log's capacity, and it saturates honestly
    // ======================================================================
    bd_init();
    let _lr, lrc = bd_room_add("load");
    var lok: i64 = 0;
    var lref: i64 = 0;
    i = 0;
    while i < 240 {
        let _pid, pcode = bd_post(1, "load", 0);
        if pcode == CODE_OK { lok = lok + 1; } else { lref = lref + 1; }
        i = i + 1;
    }
    check("load: the log saturates at BD_MAX_POSTS", lok == BD_MAX_POSTS && lref == 216);
    check("load: every refusal is counted", bd_refused_total() == 216);
    say("LOAD board ops=240 ok=24 refused=216\n");

    say("t106 done  pass=");
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
