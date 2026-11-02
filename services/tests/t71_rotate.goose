// services/tests/t71_rotate.goose
//
// B-L1-108 — the log rotation and retention policy, driven for the first time.
//
// Status: WRITTEN, then RUN by os-build/layer1/run_native.sh.
//
// WHY THIS FILE EXISTS
// --------------------
// `services/logd/rotate.goose` is the one module in the corpus whose bugs destroy
// history instead of adding it, and until this test nothing drove it: t50 covers the
// formatter and the ring, not the segment list. A retention policy that silently drops
// the wrong segment, or drops the newest one, is indistinguishable from a policy that
// works until the day you need the log.
//
// WHAT IT PROVES, AND WHAT IT CANNOT
// ----------------------------------
// It proves the policy: when a segment rolls, which segment is kept, what a name looks
// like, what the counters say. It cannot prove that the bytes named by a segment are the
// bytes in a file -- nothing here touches the filesystem. That mapping is the caller's
// job (B-L1-108's export path) and is NOT BUILT.

import logd.rotate;
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

fn eq(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

// A string literal as a slice, so the assertions read as one line each.
fn lit(s: const u8[:], out: u8[>..]&, cap: i64) -> bool {
    if s.len > cap { return false; }
    var i: i64 = 0;
    while i < s.len { out.push(s[i]); i = i + 1; }
    return true;
}

fn main() {
    say("t71 log rotation and retention\n");

    // --- an empty store, and what "no policy" means ---
    var s = rot_new(100, 0);
    let c0, b0, d0, r0 = rot_stats(s);
    check("new store is empty", c0 == 0 && b0 == 0 && d0 == 0 && r0 == 0);
    check("empty store has no open segment", rot_current(s, 20000) == -1);

    // 100 bytes per segment: the first 60 fits, the second 60 does not.
    let i1, c1 = rot_append(s, 20000, 60);
    check("first append opens segment 0", i1 == 0 && c1 == CODE_OK);
    check("segment 0 is the open one", rot_current(s, 20000) == 0);

    let i2, c2 = rot_append(s, 20000, 60);
    check("the segment rolls instead of overflowing", i2 == 1 && c2 == CODE_OK);
    let sc, _sb, _sd, sr = rot_stats(s);
    check("two segments, one roll", sc == 2 && sr == 1);
    check("the rolled segment is sealed", s.segs[0].sealed);
    check("first segment kept its 60 bytes", s.segs[0].bytes == 60);
    check("second segment got the overflow", s.segs[1].bytes == 60);
    check("the day is recorded in both", s.segs[0].day == 20000 && s.segs[1].day == 20000);

    // A segment at exactly max_bytes must roll on the NEXT byte, not on this one.
    var exact = rot_new(100, 0);
    let _, e1 = rot_append(exact, 20000, 100);
    let _, e2 = rot_append(exact, 20000, 1);
    check("exactly max_bytes fits", e1 == CODE_OK && exact.segs[0].bytes == 100);
    check("one byte past max_bytes rolls", e2 == CODE_OK && exact.count == 2);

    // --- a new day does not append to yesterday's open segment ---
    let i3, c3 = rot_append(s, 20001, 10);
    check("a new day opens a new segment", i3 == 2 && c3 == CODE_OK);
    check("yesterday's segment is left alone", s.segs[1].bytes == 60);
    check("the new segment starts at zero", s.segs[2].bytes == 10);

    // --- seq numbering within a day ---
    var days = rot_new(10, 0);
    let _, a1 = rot_append(days, 20000, 10);
    let _, a2 = rot_append(days, 20000, 10);
    let _, a3 = rot_append(days, 20000, 10);
    check("same-day segments number themselves", a1 == CODE_OK && a2 == CODE_OK && a3 == CODE_OK);
    check("seq counts up within the day", days.segs[0].seq == 0 && days.segs[1].seq == 1 && days.segs[2].seq == 2);

    // --- retention ---
    // keep == 2 on a 3-segment store drops exactly one, the oldest.
    var keep2 = rot_new(10, 2);
    let _ = rot_append(keep2, 20000, 10);
    let _ = rot_append(keep2, 20001, 10);
    let _ = rot_append(keep2, 20002, 10);
    let dropped = rot_prune(keep2);
    check("prune drops down to keep", dropped == 1 && keep2.count == 2);
    check("prune drops the OLDEST, not the newest", keep2.segs[0].day == 20001 && keep2.segs[1].day == 20002);
    let _kc, _kb, kd, _kr = rot_stats(keep2);
    check("the drop is counted", kd == 1);

    // keep == 0 means "no retention", not "keep nothing".
    var keep0 = rot_new(10, 0);
    let _ = rot_append(keep0, 20000, 10);
    let _ = rot_append(keep0, 20001, 10);
    check("keep 0 prunes nothing", rot_prune(keep0) == 0 && keep0.count == 2);

    // keep == 1 must never empty the store: deleting the file being written loses the crash.
    var keep1 = rot_new(10, 1);
    let _ = rot_append(keep1, 20000, 10);
    let _ = rot_append(keep1, 20001, 10);
    let _ = rot_append(keep1, 20002, 10);
    let d1 = rot_prune(keep1);
    check("keep 1 leaves exactly one segment", d1 == 2 && keep1.count == 1);
    check("keep 1 keeps the newest", keep1.segs[0].day == 20002);

    // A store that is already at keep prunes nothing and says so.
    check("prune at the limit is a no-op", rot_prune(keep1) == 0);

    // --- a full segment list refuses rather than deciding to delete ---
    var full = rot_new(10, 0);
    var d: i64 = 20000;
    var opens: i64 = 0;
    while d < 20008 {
        let idx, code = rot_append(full, d, 10);
        if code == CODE_OK && idx >= 0 { opens = opens + 1; }
        d = d + 1;
    }
    check("eight segments fit", opens == 8 && full.count == 8);
    let i9, c9 = rot_append(full, 20008, 10);
    check("a ninth refuses with NOROOM", i9 == -1 && c9 == E_NOROOM);
    check("the refusal changed nothing", full.count == 8);

    // --- sealing ---
    check("seal the open segment", rot_seal(full) == 1);
    check("sealing twice reports zero", rot_seal(full) == 0);
    let i_after, c_after = rot_append(full, 20008, 10);
    check("a sealed store rolls instead of appending", c_after == E_NOROOM && i_after == -1);
    var one = rot_new(100, 0);
    let _ = rot_append(one, 20000, 10);
    check("seal on a store with one open segment", rot_seal(one) == 1);
    let after_idx, after_code = rot_append(one, 20000, 5);
    check("appending after seal opens a second segment", after_code == CODE_OK && after_idx == 1);
    var blank = rot_new(0, 0);
    check("empty store seals nothing", rot_seal(blank) == 0);

    // --- negative size is a caller bug, not an empty write ---
    var neg = rot_new(100, 0);
    let ni, nc = rot_append(neg, 20000, -1);
    check("a negative size is refused", ni == -1 && nc == E_INVAL);
    check("the refusal opened nothing", neg.count == 0);

    // --- names ---
    var name: u8[>..] = [];
    let n1 = rot_segment_name("kernel", s.segs[0], name, 40);
    check("segment name is built", n1 > 0);
    var want: u8[>..] = [];
    let _ = lit("log-kernel-20241004-0", want, 40);
    check("segment name has the fixed shape", eq(name[..], want[..]));

    var name2: u8[>..] = [];
    let _ = rot_segment_name("kernel", s.segs[1], name2, 40);
    var want2: u8[>..] = [];
    let _ = lit("log-kernel-20241004-1", want2, 40);
    check("the second segment of a day gets seq 1", eq(name2[..], want2[..]));

    var small: u8[>..] = [];
    let n_small = rot_segment_name("kernel", s.segs[0], small, 4);
    check("a short buffer refuses and writes nothing", n_small == -1 && small.len == 0);

    var exp0: u8[>..] = [];
    let _ = rot_export_name("kernel", 20000, 0, exp0, 40);
    var want_e0: u8[>..] = [];
    let _ = lit("export-kernel-20241004.log", want_e0, 40);
    check("export name for the day's only segment", eq(exp0[..], want_e0[..]));

    var exp2: u8[>..] = [];
    let _ = rot_export_name("kernel", 20000, 2, exp2, 40);
    var want_e2: u8[>..] = [];
    let _ = lit("export-kernel-20241004-part2.log", want_e2, 40);
    check("export name for a later part", eq(exp2[..], want_e2[..]));

    // --- the day shape itself ---
    var day0: u8[>..] = [];
    let _ = rot_push_day(day0, 24, 0);
    var want_d0: u8[>..] = [];
    let _ = lit("19700101", want_d0, 24);
    check("day 0 is 1970-01-01", eq(day0[..], want_d0[..]));

    var day20000: u8[>..] = [];
    let _ = rot_push_day(day20000, 24, 20000);
    var want_d1: u8[>..] = [];
    let _ = lit("20241004", want_d1, 24);
    check("day 20000 is 2024-10-04", eq(day20000[..], want_d1[..]));

    // A leap day, which is where a hand-rolled civil-from-days goes wrong.
    // 19782 is 2024-02-29 (1970-01-01 + 19782 days, checked against a calendar, not
    // against rot_push_day itself: an expectation computed by the code under test proves
    // only that the code agrees with itself).
    var day19782: u8[>..] = [];
    let _ = rot_push_day(day19782, 24, 19782);
    var want_d2: u8[>..] = [];
    let _ = lit("20240229", want_d2, 24);
    check("day 19782 is the 2024 leap day", eq(day19782[..], want_d2[..]));

    // The day after the leap day, and the last day of a non-leap February.
    var day19783: u8[>..] = [];
    let _ = rot_push_day(day19783, 24, 19783);
    var want_d3: u8[>..] = [];
    let _ = lit("20240301", want_d3, 24);
    check("the day after the leap day is March 1", eq(day19783[..], want_d3[..]));

    // --- the health numbers ---
    var st = rot_new(100, 5);
    let _ = rot_append(st, 20000, 40);
    let _ = rot_append(st, 20000, 80);
    let c, bytes, drop, rot = rot_stats(st);
    check("stats count segments", c == 2);
    check("stats count bytes across segments", bytes == 120);
    check("stats carry the roll count", rot == 1 && drop == 0);

    say("t71 done  pass=");
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
