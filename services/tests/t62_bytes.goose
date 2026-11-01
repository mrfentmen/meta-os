// services/tests/t62_bytes.goose
//
// B-L1-68 — test program for `common/bytes`.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// The cases that matter are the edges, not the happy path: an empty haystack, a
// needle longer than the haystack, a `from` past the end, a copy that only half
// fits, and a signed comparison across 0x80. Those are the five places a byte
// helper quietly returns the wrong answer while looking right in review.

import common.bytes.bytes;
import common.fmt.fmt;
import common.sys.sys;

var t_pass: i64 = 0;
var t_fail: i64 = 0;

fn say(s: const u8[:]) { let _ = sys_write_serial(s); }

fn check(name: const u8[:], cond: bool) {
    if cond { t_pass++; say("ok   "); }
    else { t_fail++; say("FAIL "); }
    say(name);
    say("\n");
}

fn main() {
    say("t62 bytes\n");

    // --- equality and ordering ---
    check("eq same", by_eq("abc", "abc"));
    check("eq differs in length", !by_eq("abc", "abcd"));
    check("eq differs in content", !by_eq("abc", "abd"));
    check("eq empty", by_eq("", ""));
    check("cmp equal", by_cmp("abc", "abc") == 0);
    check("cmp prefix is less", by_cmp("ab", "abc") < 0);
    check("cmp longer is greater", by_cmp("abd", "abc") > 0);
    // 0x80 sorts above 0x7f in byte order. A signed comparison would put it below.
    var hi: u8[>..] = [];
    hi.push(0x80);
    var lo: u8[>..] = [];
    lo.push(0x7f);
    check("cmp is unsigned at 0x80", by_cmp(hi[..], lo[..]) > 0);
    check("eq_ci folds ascii", by_eq_ci("Content-Type", "content-type"));
    check("eq_ci does not fold length", !by_eq_ci("ab", "abc"));

    // --- search ---
    check("find at 0", by_find("abcabc", "abc", 0) == 0);
    check("find second", by_find("abcabc", "abc", 1) == 3);
    // The no-progress case: `from` is the only thing that stops an infinite loop.
    check("find from past first match", by_find("aaa", "a", 1) == 1);
    check("find miss", by_find("abc", "xyz", 0) == -1);
    check("find empty needle returns from", by_find("abc", "", 2) == 2);
    check("find needle longer than hay", by_find("ab", "abc", 0) == -1);
    check("find from past end", by_find("abc", "a", 9) == -1);
    check("find_byte", by_find_byte("a/b", '/', 0) == 1);
    check("find_byte from", by_find_byte("a/a", 'a', 1) == 2);
    check("find_byte miss", by_find_byte("abc", 'z', 0) == -1);
    check("rfind_byte", by_rfind_byte("a/b/c", '/') == 3);
    check("rfind_byte miss", by_rfind_byte("abc", '/') == -1);
    check("count_byte", by_count_byte("a,b,,c", ',') == 3);

    // --- prefix / suffix ---
    check("starts_with", by_starts_with("meta-os", "meta"));
    check("starts_with empty", by_starts_with("meta", ""));
    check("starts_with too long", !by_starts_with("me", "meta"));
    check("ends_with", by_ends_with("meta-os", "-os"));
    check("ends_with whole", by_ends_with("os", "os"));
    check("ends_with too long", !by_ends_with("os", "meta-os"));

    // --- trim as span ---
    let s0, e0 = by_trim_span("   hi there  \t");
    check("trim start", s0 == 3);
    check("trim end", e0 == 11);
    let s1, e1 = by_trim_span("   ");
    check("trim all blank collapses to empty", s1 == e1);
    let s2, e2 = by_trim_span("");
    check("trim empty", s2 == 0 && e2 == 0);

    // --- copy and fill, both bounded ---
    var dst: u8[>..] = [];
    let n = by_copy(dst, 3, "abcdef");
    check("copy respects cap", n == 3 && dst.len == 3);
    check("copy took the prefix", by_eq(dst[..], "abc"));
    var dst2: u8[>..] = [];
    let n2 = by_copy(dst2, 10, "abc");
    check("copy all when room", n2 == 3 && dst2.len == 3);
    var fill: u8[>..] = [];
    let nf = by_fill(fill, 4, 'x', 10);
    check("fill respects cap", nf == 4 && fill.len == 4);
    by_clear(fill);
    check("clear zeroes", fill[0] == 0 && fill[3] == 0);

    // --- predicates ---
    check("is_blank spaces", by_is_blank(" \t\r\n"));
    check("is_blank empty", by_is_blank(""));
    check("is_blank rejects text", !by_is_blank(" \nx"));
    check("all_digits", by_all_digits("0123456789"));
    check("all_digits empty is false", !by_all_digits(""));
    check("all_digits rejects sign", !by_all_digits("-1"));
    check("all_hex", by_all_hex("deadBEEF01"));
    check("all_hex rejects g", !by_all_hex("deadbeeg"));

    // --- case ---
    check("lower_ascii", lower_ascii('Q') == 'q');
    check("lower_ascii leaves digits", lower_ascii('7') == '7');
    check("upper_ascii", upper_ascii('q') == 'Q');
    check("uppercase below a untouched", upper_ascii('@') == '@');

    say("t62 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
    if t_fail > 0 { let _ = sys_exit(1); }
}
