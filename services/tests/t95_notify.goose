// services/tests/t95_notify.goose
//
// The top-bar feed, driven: dedupe, refusal, dismissal-as-record, and the dot that is derived.
//
// WHAT THIS PROVES THAT THE HAPPY PATH DOES NOT
// --------------------------------------------
// A feed is easy to get right once and wrong every retry after. The four checks that matter
// are the boundary of the dedupe window (inclusive at `NT_DEDUPE_MS`, exclusive one ms past
// it), the refusal at `NT_MAX` which must be counted rather than silently dropping the oldest,
// the dismissal that frees a slot while keeping a record of itself, and the severity dot that
// must fall back when the only error on screen is dismissed.
//
// Status: RUNS — set by `audit_status.py` from the runner's row, not by hand.

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

fn str(s: const u8[:]) -> u8[..128] {
    var b: u8[..128] = [0; 128];
    var i: i64 = 0;
    while i < s.len { b[i] = s[i]; i = i + 1; }
    return b;
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

fn main() {
    say("t95 notify\n");

    // ======================================================================
    // 1. empty feed
    // ======================================================================
    nt_init();
    check("notify: an empty feed has no notes", nt_count() == 0);
    check("notify: the dot is off", nt_worst() == 0);
    check("notify: nothing is unread", nt_unread(0) == 0);
    check("notify: nothing has been dismissed", nt_dismissal_total() == 0);
    check("notify: nothing was refused", nt_refusal_total() == 0);

    // ======================================================================
    // 2. one post, and the dedupe window at both edges
    // ======================================================================
    let n1, c1 = nt_post(str("board")[..5], SEV_INFO, str("post 1")[..6], 1000);
    check("notify: a post is accepted", c1 == CODE_OK && n1 == 1);
    check("notify: the feed holds one", nt_count() == 1);
    check("notify: it is unread from nothing", nt_unread(0) == 1);
    check("notify: the dot is info", nt_worst() == SEV_INFO);
    check("notify: the source came back", nt_source_at(0).len == 5);
    check("notify: the severity is readable by position", nt_sev_at(0) == SEV_INFO);
    check("notify: a position past the end is 0, not a note", nt_sev_at(5) == 0 && nt_id_at(5) == 0);
    check("notify: the text came back", nt_text_at(0).len == 6);
    check("notify: the time came back", nt_when_at(0) == 1000);

    let d1, cd1 = nt_post(str("board")[..5], SEV_INFO, str("post 1")[..6], 1500);
    check("notify: the same sentence is one note", cd1 == NT_DUPLICATE && d1 == 1);
    check("notify: the duplicate did not grow the feed", nt_count() == 1);
    check("notify: the duplicate was counted", nt_duplicate_total() == 1);

    // The window is inclusive: exactly NT_DEDUPE_MS old is still the same sentence.
    let d2, cd2 = nt_post(str("board")[..5], SEV_INFO, str("post 1")[..6], 1000 + NT_DEDUPE_MS);
    check("notify: at exactly the window it is still a duplicate", cd2 == NT_DUPLICATE && d2 == 1);
    // One ms later it is a new event, not a repeat: a board post repeated an hour later must
    // not be suppressed by a window nobody reset.
    let n2, c2 = nt_post(str("board")[..5], SEV_INFO, str("post 1")[..6], 1001 + NT_DEDUPE_MS);
    check("notify: one ms past the window it is a new note", c2 == CODE_OK && n2 == 2);

    // Same words, different source: not a duplicate.
    let n3, c3 = nt_post(str("updater")[..7], SEV_INFO, str("post 1")[..6], 1000);
    check("notify: the same text from another source is a new note", c3 == CODE_OK && n3 == 3);
    check("notify: three notes", nt_count() == 3);

    // ======================================================================
    // 3. refusals at the post
    // ======================================================================
    let bad1, cx1 = nt_post(str("board")[..5], 0, str("x")[..1], 2000);
    check("notify: severity 0 is refused", cx1 == E_INVAL && bad1 < 0);
    let bad2, cx2 = nt_post(str("board")[..5], 4, str("x")[..1], 2000);
    check("notify: severity 4 is refused", cx2 == E_INVAL && bad2 < 0);
    let bad3, cx3 = nt_post(str("")[..0], SEV_INFO, str("x")[..1], 2000);
    check("notify: an empty source is refused", cx3 == E_INVAL && bad3 < 0);
    let bad4, cx4 = nt_post(str("board")[..5], SEV_INFO, str("")[..0], 2000);
    check("notify: empty text is refused", cx4 == E_INVAL && bad4 < 0);
    let bad5, cx5 = nt_post(str("aaaaaaaaaaaaaaaa")[..16], SEV_INFO, str("x")[..1], 2000);
    check("notify: a source of exactly NT_SRC_MAX is refused", cx5 == E_NOROOM && bad5 < 0);
    let bad6, cx6 = nt_post(str("board")[..5], SEV_INFO,
        str("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")[..96], 2000);
    check("notify: text of exactly NT_TEXT_MAX is refused", cx6 == E_NOROOM && bad6 < 0);
    let bad7, cx7 = nt_post(str("bo\nrd")[..5], SEV_INFO, str("x")[..1], 2000);
    check("notify: a control byte in the source is refused", cx7 == E_INVAL && bad7 < 0);
    let bad8, cx8 = nt_post(str("board")[..5], SEV_INFO, str("two\nlines")[..9], 2000);
    check("notify: a newline in the text is refused", cx8 == E_INVAL && bad8 < 0);
    check("notify: no refusal grew the feed", nt_count() == 3);

    // ======================================================================
    // 4. the ceiling, and the refusal that is counted
    // ======================================================================
    // Nine more distinct notes fill the feed to NT_MAX (12).
    let f1, cf1 = nt_post(str("svc")[..3], SEV_WARN, str("f1")[..2], 2100);
    let f2, cf2 = nt_post(str("svc")[..3], SEV_INFO, str("f2")[..2], 2200);
    let f3, cf3 = nt_post(str("svc")[..3], SEV_INFO, str("f3")[..2], 2300);
    let f4, cf4 = nt_post(str("svc")[..3], SEV_INFO, str("f4")[..2], 2400);
    let f5, cf5 = nt_post(str("svc")[..3], SEV_INFO, str("f5")[..2], 2500);
    let f6, cf6 = nt_post(str("svc")[..3], SEV_INFO, str("f6")[..2], 2600);
    let f7, cf7 = nt_post(str("svc")[..3], SEV_INFO, str("f7")[..2], 2700);
    let f8, cf8 = nt_post(str("svc")[..3], SEV_INFO, str("f8")[..2], 2800);
    let f9, cf9 = nt_post(str("svc")[..3], SEV_INFO, str("f9")[..2], 2900);
    check("notify: nine more posts fill the feed",
          cf1 == CODE_OK && cf2 == CODE_OK && cf3 == CODE_OK && cf4 == CODE_OK
          && cf5 == CODE_OK && cf6 == CODE_OK && cf7 == CODE_OK && cf8 == CODE_OK
          && cf9 == CODE_OK);
    check("notify: twelve notes is the ceiling", nt_count() == NT_MAX);
    check("notify: the ids are monotonic", f1 == 4 && f9 == 12);
    let over, co = nt_post(str("svc")[..3], SEV_ERROR, str("too many")[..8], 3000);
    check("notify: the thirteenth is refused for space", co == E_NO_SPACE && over < 0);
    check("notify: the refusal is counted", nt_refusal_total() == 1);
    check("notify: the refused note did not displace anything", nt_count() == NT_MAX);
    check("notify: the dot is the highest on screen", nt_worst() == SEV_WARN);

    // ======================================================================
    // 5. dismissal is a record, and it frees the slot
    // ======================================================================
    check("notify: dismiss the first", nt_dismiss(n1, 5000) == CODE_OK);
    check("notify: the feed shrank", nt_count() == NT_MAX - 1);
    check("notify: the dismissal is recorded", nt_dismissal_total() == 1);
    check("notify: the ring names what was dismissed", nt_dismissal_at(0) == n1);
    check("notify: with its severity", nt_dismissal_sev_at(0) == SEV_INFO);
    check("notify: and its time", nt_dismissal_when_at(0) == 5000);
    check("notify: a dismissed id is gone from the feed", nt_unread(n1 - 1) == nt_count());
    check("notify: dismissing it again is E_NOTFOUND", nt_dismiss(n1, 5100) == E_NOTFOUND);
    check("notify: dismissing an id that never existed is E_NOTFOUND",
          nt_dismiss(999, 5100) == E_NOTFOUND);
    check("notify: a failed dismissal is not recorded", nt_dismissal_total() == 1);

    // The slot that just freed is usable, and the new note is newest.
    let n13, c13 = nt_post(str("svc")[..3], SEV_ERROR, str("disk failing")[..12], 5200);
    check("notify: a post after a dismissal fits", c13 == CODE_OK && n13 == 13);
    check("notify: the feed is full again", nt_count() == NT_MAX);
    check("notify: the dot is the error now", nt_worst() == SEV_ERROR);

    // ======================================================================
    // 6. the feed as lines for the bar
    // ======================================================================
    var feed: u8[>..] = [];
    let fn1, cff = nt_fetch(0, feed);
    check("notify: fetch returns every note", cff == CODE_OK && fn1 == NT_MAX);
    check("notify: the line carries the text", has(feed[..], str("disk failing")[..12]));
    check("notify: the line carries the severity word", has(feed[..], str("error")[..5]));
    // A cursor at the second-to-last id returns only the last one.
    var tail: u8[>..] = [];
    let tn, _ct = nt_fetch(n13 - 1, tail);
    check("notify: a cursor returns only what is newer", tn == 1);
    check("notify: and it is the error", has(tail[..], str("disk failing")[..12]));
    var none: u8[>..] = [];
    let zn, _cz = nt_fetch(n13, none);
    check("notify: a cursor at the newest returns nothing", zn == 0);

    // ======================================================================
    // 7. the dot falls back when the error is dismissed
    // ======================================================================
    check("notify: dismiss the error", nt_dismiss(n13, 5300) == CODE_OK);
    check("notify: the dot fell back to the warn", nt_worst() == SEV_WARN);
    check("notify: the dismissal log grew", nt_dismissal_total() == 2);

    // ======================================================================
    // 8. the ring is a log: eight slots, an unbounded total
    // ======================================================================
    // Seven more dismissals takes the total to nine, which wraps the ring and overwrites
    // the first record. The total is what counts; the ring is what a bar can show.
    let g1 = nt_id_at(0);
    check("notify: dismiss seven more", nt_dismiss(g1, 5400) == CODE_OK);
    check("notify: ten left", nt_count() == NT_MAX - 2);
    let g2 = nt_id_at(0);
    check("notify: second", nt_dismiss(g2, 5401) == CODE_OK);
    let g3 = nt_id_at(0);
    check("notify: third", nt_dismiss(g3, 5402) == CODE_OK);
    let g4 = nt_id_at(0);
    check("notify: fourth", nt_dismiss(g4, 5403) == CODE_OK);
    let g5 = nt_id_at(0);
    check("notify: fifth", nt_dismiss(g5, 5404) == CODE_OK);
    let g6 = nt_id_at(0);
    check("notify: sixth", nt_dismiss(g6, 5405) == CODE_OK);
    let g7 = nt_id_at(0);
    check("notify: seventh", nt_dismiss(g7, 5406) == CODE_OK);
    check("notify: nine dismissals are recorded", nt_dismissal_total() == 9);
    // Slot 0 was written by dismissal 1 and by dismissal 9 (9 % 8 == 1 ... the ninth write
    // lands on slot 0 because the slot is chosen before the increment).
    check("notify: the ring wrapped onto the newest", nt_dismissal_at(0) == g7);
    check("notify: the first dismissal is no longer in the ring", nt_dismissal_at(1) == n13);
    var found_first: bool = false;
    var r: i64 = 0;
    while r < NT_LOG_MAX {
        if nt_dismissal_at(r) == n1 { found_first = true; }
        r = r + 1;
    }
    check("notify: nothing in the ring is the first dismissal any more", !found_first);

    // ======================================================================
    // 9. a restart forgets everything, and says so by starting at id 1
    // ======================================================================
    nt_init();
    check("notify: a restart empties the feed", nt_count() == 0);
    check("notify: a restart clears the dot", nt_worst() == 0);
    check("notify: a restart clears the dismissal log", nt_dismissal_total() == 0);
    check("notify: a restart clears the counters",
          nt_refusal_total() == 0 && nt_duplicate_total() == 0);
    let n1b, c1b = nt_post(str("board")[..5], SEV_INFO, str("after")[..5], 9000);
    check("notify: ids are per-process and start at 1", c1b == CODE_OK && n1b == 1);
    check("notify: and the feed works after the restart", nt_count() == 1 && nt_unread(0) == 1);

    say("t95 done  pass=");
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
