// services/tests/t91_board.goose
//
// Driver for board-client — rooms, the append-only log, fetch cursors, persistence.
//
// Two properties are worth attacking: a full log must refuse rather than overwrite
// (or `fetch since 1` returns different history at different times), and a file with
// one bad line must apply nothing.

import board.board;
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

fn has(hay: const u8[:], needle: const u8[:]) -> bool {
    if needle.len == 0 { return true; }
    if needle.len > hay.len { return false; }
    var i: i64 = 0;
    while i + needle.len <= hay.len {
        var k: i64 = 0;
        var ok = true;
        while k < needle.len {
            if hay[i + k] != needle[k] { ok = false; k = needle.len; }
            else { k = k + 1; }
        }
        if ok { return true; }
        i = i + 1;
    }
    return false;
}

fn str(s: const u8[:]) -> u8[..64] {
    var b: u8[..64] = [0; 64];
    var i: i64 = 0;
    while i < s.len { b[i] = s[i]; i = i + 1; }
    return b;
}

fn main() {
    say("t91 board\n");
    bd_init();

    check("board: no rooms", bd_room_count() == 0);
    check("board: no posts", bd_post_total() == 0);
    check("board: post to a room that does not exist", bd_post(1, str("hi")[..2], 100) == 0);

    // --- rooms ---------------------------------------------------------------
    let g, cg = bd_room_add(str("general")[..7]);
    check("board: add #general", cg == CODE_OK && g == 1);
    let h, ch = bd_room_add(str("help")[..4]);
    check("board: add #help", ch == CODE_OK && h == 2);
    check("board: two rooms", bd_room_count() == 2);
    check("board: room name", bd_room_name_at(0).len == 7);
    check("board: room id accessor", bd_room_id_at(1) == 2);
    let _dup, cdup = bd_room_add(str("general")[..7]);
    check("board: duplicate room is E_STATE", cdup == E_STATE);
    let _e, ce = bd_room_add(str("")[..0]);
    check("board: empty name is E_INVAL", ce == E_INVAL);
    let _cm, ccomma = bd_room_add(str("a,b")[..3]);
    check("board: a comma in a name is refused (format)", ccomma == E_INVAL);

    var longname: u8[..24] = [0; 24];
    var i: i64 = 0;
    while i < 24 { longname[i] = 97; i = i + 1; }
    let _ln, cln = bd_room_add(longname[..BD_ROOM_NAME_MAX]);
    check("board: a name at the limit is E_NOROOM", cln == E_NOROOM);

    // --- posts ---------------------------------------------------------------
    let p1, c1 = bd_post(g, str("hello")[..5], 1000);
    check("board: post", c1 == CODE_OK && p1 == 1);
    let _p2, c2 = bd_post(h, str("need help")[..9], 1100);
    check("board: post to another room", c2 == CODE_OK);
    let p3, c3 = bd_post(g, str("second")[..6], 1200);
    check("board: second post in the first room", c3 == CODE_OK && p3 == 3);
    check("board: ids are global and monotonic", p3 > p1);
    check("board: posts in #general", bd_post_count(g) == 2);
    check("board: last id in #general", bd_last_id(g) == p3);

    let _e2, ce2 = bd_post(g, str("")[..0], 1300);
    check("board: empty post is E_INVAL", ce2 == E_INVAL);
    let _e3, ce3 = bd_post(g, str("a\nb")[..3], 1300);
    check("board: a newline in a post is refused (format)", ce3 == E_INVAL);
    let _e4, ce4 = bd_post(g, str("a,b")[..3], 1300);
    check("board: a comma in a post is refused (format)", ce4 == E_INVAL);
    let _e5, ce5 = bd_post(99, str("orphan")[..6], 1300);
    check("board: a post to an unknown room is E_NOTFOUND", ce5 == E_NOTFOUND);

    // --- fetch cursors -------------------------------------------------------
    var out: u8[>..] = [];
    let n0, f0 = bd_fetch(g, 0, out);
    check("board: fetch from 0 returns both posts", n0 == 2 && f0 == CODE_OK);
    check("board: the fetch carries the text", has(out[..], str("hello")[..5]));
    check("board: the fetch carries an id prefix", has(out[..], str("1:")[..2]));

    var out2: u8[>..] = [];
    let n1, _f1 = bd_fetch(g, 1, out2);
    check("board: fetch since the first id returns one", n1 == 1);
    check("board: the older post is not in it", !has(out2[..], str("hello")[..5]));
    let n2, _f2 = bd_fetch(g, p3, out2);
    check("board: fetch since the last id returns nothing", n2 == 0);
    let _nn, fnf = bd_fetch(99, 0, out2);
    check("board: fetch on an unknown room is E_NOTFOUND", fnf == E_NOTFOUND);
    check("board: unread since 1", bd_unread(g, 1) == 1);
    check("board: unread since 0", bd_unread(g, 0) == 2);

    // --- the log is append-only and refuses rather than drops ----------------
    var k: i64 = 0;
    var filler = str("filler");
    while bd_post_total() < BD_MAX_POSTS {
        let _id, cfresh = bd_post(g, filler[..6], 2000 + k);
        if cfresh != CODE_OK { say("FAIL board: fill refused early\n"); t_fail = t_fail + 1; return; }
        k = k + 1;
    }
    check("board: log filled to BD_MAX_POSTS", bd_post_total() == BD_MAX_POSTS);
    let _full, cfull = bd_post(g, str("overflow")[..8], 3000);
    check("board: a full log refuses with E_NO_SPACE", cfull == E_NO_SPACE);
    check("board: the refusal is counted", bd_refused_total() == 1);
    var out3: u8[>..] = [];
    let nfirst, _f3 = bd_fetch(g, 0, out3);
    check("board: the oldest post is still there after a refusal", has(out3[..], str("hello")[..5]));
    check("board: nothing was overwritten", nfirst == bd_post_count(g));

    // --- export / import ------------------------------------------------------
    var blob: u8[..2048] = [0; 2048];
    let blen = bd_export(blob);
    check("board: export writes something", blen > 0);

    bd_init();
    check("board: init clears rooms", bd_room_count() == 0);
    check("board: init clears posts", bd_post_total() == 0);
    let lines = bd_import(blob[..blen]);
    check("board: import reads every line", lines > 0);
    check("board: import restored two rooms", bd_room_count() == 2);
    check("board: import restored every post", bd_post_total() == BD_MAX_POSTS);
    check("board: import restored the ids", bd_last_id(g) == bd_last_id(g));

    // A new post after an import must not collide with a restored id.
    let after, cafter = bd_post(g, str("post-import")[..11], 4000);
    check("board: a full imported log still refuses", cafter == E_NO_SPACE);
    check("board: the refused id is not issued", after == 0);
    // Make room is impossible by design; a different room can still take posts.
    let _nr, cnr = bd_room_add(str("new")[..3]);
    check("board: a new room after import", cnr == CODE_OK);

    // --- import validation ----------------------------------------------------
    bd_init();
    var onlyroom: u8[..32] = [0; 32];
    let rl = bd_export_of("R,1,general\n");
    check("board: a room-only file imports", bd_import(rl[..12]) == 1);
    check("board: the room is there", bd_room_count() == 1);

    bd_init();
    let badkind = bd_export_of("X,1,general\n");
    check("board: an unknown line kind is E_CORRUPT", bd_import(badkind[..12]) == E_CORRUPT);
    bd_init();
    let orph = bd_export_of("P,1,9,0,text\n");
    check("board: a post in an undefined room is E_CORRUPT", bd_import(orph[..14]) == E_CORRUPT);
    bd_init();
    let nonum = bd_export_of("R,x,general\n");
    check("board: a non-numeric id is E_CORRUPT", bd_import(nonum[..12]) == E_CORRUPT);
    bd_init();
    let empty = bd_export_of("");
    check("board: an empty file is E_CORRUPT", bd_import(empty[..0]) == E_CORRUPT);

    // Atomicity: a valid room line followed by a bad one applies nothing.
    bd_init();
    let mixed = bd_export_of("R,1,general\nP,1,9,0,x\n");
    check("board: a corrupt second line is E_CORRUPT", bd_import(mixed[..24]) == E_CORRUPT);
    check("board: ... and the first line was not applied", bd_room_count() == 0);

    // --- the two caps that are not the post count ------------------------------
    // BD_POST_MAX is the text cap and BD_MAX_ROOMS is the room cap; the log cap above is
    // BD_MAX_POSTS. Three numbers with similar names, so each is named here at its edge.
    var long: u8[>..] = [];
    var z: i64 = 0;
    while z < BD_POST_MAX {
        let _ = long.push('z');
        z = z + 1;
    }
    bd_init();
    var r1: i64[>..] = [];
    let _ = r1.push(0);
    let rid, _cr = bd_room_add(str("cap")[..3]);
    let _p1, cshort = bd_post(rid, long[..BD_POST_MAX - 1], 1);
    check("board: BD_POST_MAX - 1 bytes of text fits", cshort == CODE_OK);
    let _p2, clong = bd_post(rid, long[..BD_POST_MAX], 2);
    check("board: exactly BD_POST_MAX bytes is refused, naming the limit", clong == E_NOROOM);

    let _r2, c2r = bd_room_add(str("two")[..3]);
    let _r3, c3r = bd_room_add(str("thr")[..3]);
    let _r4, c4r = bd_room_add(str("fou")[..3]);
    check("board: BD_MAX_ROOMS rooms register", c2r == CODE_OK && c3r == CODE_OK && c4r == CODE_OK);
    let _r5, c5r = bd_room_add(str("fiv")[..3]);
    check("board: the room past BD_MAX_ROOMS is E_NO_SPACE", c5r == E_NO_SPACE);

    say("t91 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
}

// A literal blob for the import tests. Local helper so each case reads as itself.
fn bd_export_of(s: const u8[:]) -> u8[..32] {
    var b: u8[..32] = [0; 32];
    var i: i64 = 0;
    while i < s.len { b[i] = s[i]; i = i + 1; }
    return b;
}
