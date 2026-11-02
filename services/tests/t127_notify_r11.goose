// services/tests/t127_notify_r11.goose
//
// Round 11 — notify: the dismissal ring at its wrap, the cursor across dismissals, and the
// derived dot falling back when the only error is closed.
//
// WHAT t95 ALREADY PROVES, AND WHAT THIS ADDS
// -------------------------------------------
// t95 drives the dedupe window's both edges, every shape refusal, the capacity refusal, and
// one dismissal. It does not wrap the dismissal ring (NT_LOG_MAX), does not assert which id
// survives in which slot after nine dismissals, does not check `nt_unread` against ids that
// were dismissed, and does not watch `nt_worst` fall when the only error leaves the feed.
// Those are the four properties a feed loses silently: the audit ring, the cursor, and the dot.
//
// The feed is in-memory by design; restart behaviour is a named gap in the record, not a
// claim here.

import notify.notify;
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

// Build "<prefix><n>" into a growable buffer, so the slice handed to nt_post is exactly
// the text and carries no trailing NULs (a NUL is not printable and would be refused).
fn text_into(out: u8[>..]&, prefix: const u8[:], n: i64) {
    var i: i64 = 0;
    while i < prefix.len {
        let _ = out.push(prefix[i]);
        i = i + 1;
    }
    let _ = append_int(out, 96, n);
}

fn t_dedupe_and_capacity() {
    say("-- dedupe before capacity, refusal counted\n");

    nt_init();
    check("notify: an empty feed", nt_count() == 0 && nt_worst() == 0);

    var i: i64 = 0;
    while i < NT_MAX {
        var t: u8[>..] = [];
        text_into(t, "n", i);
        let id, code = nt_post("src", SEV_INFO, t[..], 1000);
        if i == 0 {
            check("notify: the first post gets id 1", code == CODE_OK && id == 1);
        }
        i = i + 1;
    }
    check("notify: the feed fills to NT_MAX", nt_count() == NT_MAX);
    check("notify: the dot is info", nt_worst() == SEV_INFO);
    check("notify: everything is unread", nt_unread(0) == NT_MAX);

    // A duplicate while full is a duplicate, not a refusal: capacity is checked last, so a
    // retry is told the note exists instead of being told to grow a feed already showing it.
    var t0: u8[>..] = [];
    text_into(t0, "n", 0);
    let dup, dupc = nt_post("src", SEV_INFO, t0[..], 1000);
    check("notify: a duplicate in a full feed is NT_DUPLICATE", dupc == NT_DUPLICATE && dup == 1);
    check("notify: the duplicate did not count as a refusal", nt_refusal_total() == 0);
    check("notify: the duplicate was counted", nt_duplicate_total() == 1);

    var t999: u8[>..] = [];
    text_into(t999, "n", 999);
    let over, overc = nt_post("src", SEV_INFO, t999[..], 1000);
    check("notify: a new note in a full feed is E_NO_SPACE", overc == E_NO_SPACE && over < 0);
    check("notify: the refusal was counted", nt_refusal_total() == 1);
    check("notify: the feed did not grow", nt_count() == NT_MAX);
}

fn t_dismiss_ring() {
    say("-- the dismissal ring wraps, keeps counting\n");

    // Dismiss ids 1..9. The ring holds eight; the ninth overwrites slot 0.
    var i: i64 = 0;
    while i < 9 {
        check("notify: dismiss succeeds", nt_dismiss(i + 1, 3000 + i) == CODE_OK);
        i = i + 1;
    }
    check("notify: nine dismissals are counted", nt_dismissal_total() == 9);
    check("notify: nine dismissals leave three notes", nt_count() == 3);
    check("notify: the oldest dismissal was overwritten by the ninth", nt_dismissal_at(0) == 9);
    check("notify: the second slot still holds the second dismissal", nt_dismissal_at(1) == 2);
    check("notify: the eighth slot holds the eighth", nt_dismissal_at(7) == 8);
    check("notify: the dismissal time is kept", nt_dismissal_when_at(1) == 3001);
    check("notify: the dismissal severity is kept", nt_dismissal_sev_at(1) == SEV_INFO);
    check("notify: a position past the ring is 0", nt_dismissal_at(NT_LOG_MAX) == 0);

    check("notify: dismissing an id that is gone is E_NOTFOUND", nt_dismiss(1, 4000) == E_NOTFOUND);
    check("notify: a failed dismissal is not counted", nt_dismissal_total() == 9);

    // The cursor is an id, not an offset: ids 10, 11, 12 remain, and a cursor at 9 sees all
    // three while a cursor at 10 sees two.
    check("notify: three unread after the dismissals", nt_unread(9) == 3);
    check("notify: a cursor at 10 sees two", nt_unread(10) == 2);
    check("notify: a cursor at the newest sees none", nt_unread(12) == 0);
    check("notify: the first remaining note is id 10", nt_id_at(0) == 10);

    // The dot is derived: add an error, watch it rise; dismiss it, watch it fall back.
    let eid, ec = nt_post("sys", SEV_ERROR, "disk full", 20000);
    check("notify: an error posts", ec == CODE_OK);
    check("notify: the dot is the error", nt_worst() == SEV_ERROR);
    check("notify: the error is last", nt_id_at(nt_count() - 1) == eid);
    check("notify: the error dismissed", nt_dismiss(eid, 21000) == CODE_OK);
    check("notify: the dot fell back to info", nt_worst() == SEV_INFO);
    // The ring slot is dismissal_total % NT_LOG_MAX, and the total was 9 before this one:
    // 9 % 8 = 1, so the tenth dismissal overwrites slot 1 (the second dismissal).
    check("notify: the tenth dismissal took ring slot 1", nt_dismissal_at(1) == eid);
}

fn t_fetch() {
    say("-- fetch: lines after a cursor\n");

    var out: u8[>..] = [];
    let lines, fc = nt_fetch(9, out);
    check("notify: fetch after 9 returns the three remaining notes", fc == CODE_OK && lines == 3);
    check("notify: the line carries id, severity and text", has(out[..], "10 info n9"));
    check("notify: the next line follows", has(out[..], "11 info n10"));
    var none: u8[>..] = [];
    let nlines, _nc = nt_fetch(12, none);
    check("notify: fetch at the newest returns nothing", nlines == 0 && none.len == 0);
    var all: u8[>..] = [];
    let alines, _ac = nt_fetch(0, all);
    check("notify: fetch from zero returns the feed", alines == 3);
}

fn t_load() {
    say("-- load: 120 posts, capacity as the ceiling\n");

    nt_init();
    var ops: i64 = 0;
    var ok: i64 = 0;
    var refused: i64 = 0;
    var i: i64 = 0;
    while i < 120 {
        var t: u8[>..] = [];
        let _a = append_str(t, 96, "load-");
        let _b = append_int(t, 96, i);
        let _id, code = nt_post("load", SEV_INFO, t[..], 10000 + (i * 4000));
        ops = ops + 1;
        if code == CODE_OK { ok = ok + 1; } else { refused = refused + 1; }
        i = i + 1;
    }
    check("load: exactly NT_MAX posts were accepted", ok == NT_MAX);
    check("load: the rest were refused, none dropped silently", refused == ops - NT_MAX);
    check("load: the refusal counter agrees", nt_refusal_total() == refused);
    say("LOAD notify ops=");
    var ob: u8[>..] = [];
    let _ = append_int(ob, 32, ops);
    say(ob[..]);
    say(" ok=");
    ob = [];
    let _ = append_int(ob, 32, ok);
    say(ob[..]);
    say(" refused=");
    ob = [];
    let _ = append_int(ob, 32, refused);
    say(ob[..]);
    say("\n");
}

fn main() {
    say("t127 notify r11\n");
    t_dedupe_and_capacity();
    t_dismiss_ring();
    t_fetch();
    t_load();
    say("t127 done  pass=");
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
