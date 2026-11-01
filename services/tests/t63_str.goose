// services/tests/t63_str.goose
//
// B-L1-69 — test program for `common/str`.
//
// The cursor has exactly one hard job: terminate. So half these cases are about
// where the walk stops. `a,` has two fields (the second empty), `a` has one, `""`
// has one empty field, and `a,,b` has three. A splitter that answers two, one,
// zero and two is a config parser that silently loses the last value -- the kind
// of bug that shows up as "the setting does not stick".

import common.str.str;
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

// Walk a separator split and return how many fields it produced. Deliberately
// counts empty fields: the point of the exercise is that they are visible.
fn count_fields(s: const u8[:], sep: u8) -> i64 {
    var sp = st_sep(s, sep);
    var n: i64 = 0;
    var guard: i64 = 0;
    var more = true;
    while more && guard < 64 {
        let a, b, found = st_next(sp, s);
        if !found { more = false; } else { n++; }
        guard++;
    }
    if guard >= 64 { return -1; }   // a splitter that will not terminate is a bug
    return n;
}

// Is the FIRST field exactly `want`?
fn first_is(s: const u8[:], sep: u8, want: const u8[:]) -> bool {
    var sp = st_sep(s, sep);
    let a, b, found = st_next(sp, s);
    if !found { return false; }
    return by_eq_span(s, a, b, want);
}

fn by_eq_span(s: const u8[:], a: i64, b: i64, want: const u8[:]) -> bool {
    if b - a != want.len { return false; }
    var i: i64 = 0;
    while i < want.len {
        if s[a + i] != want[i] { return false; }
        i++;
    }
    return true;
}

fn main() {
    say("t63 str\n");

    // --- single separator: where the walk stops ---
    check("a,b is 2 fields", count_fields("a,b", ',') == 2);
    check("a, is 2 fields (trailing empty)", count_fields("a,", ',') == 2);
    check("a,,b is 3 fields", count_fields("a,,b", ',') == 3);
    check(",a is 2 fields (leading empty)", count_fields(",a", ',') == 2);
    check("empty input is 1 empty field", count_fields("", ',') == 1);
    check("no separator is 1 field", count_fields("abc", ',') == 1);
    check("first field is a", first_is("a,b", ',', "a"));
    check("first field of leading comma is empty", first_is(",a", ',', ""));
    check("count_sep agrees", st_count_sep("a,,b", ',') == 3);

    // --- whitespace: no empty tokens, runs collapse ---
    check("word count", st_count_word("  ls  -l  ") == 2);
    check("word count empty", st_count_word("   ") == 0);
    check("word walk first token", first_word_is("  ls -l ", "ls"));
    check("word walk second token", second_word_is("  ls -l ", "-l"));

    // --- multi-byte literal, one shot per step ---
    let a1, b1, n1 = st_lit_span("one\r\ntwo\r\n", "\r\n", 0);
    check("lit span first", a1 == 0 && b1 == 3 && n1 == 5);
    let a2, b2, n2 = st_lit_span("one\r\ntwo\r\n", "\r\n", n1);
    check("lit span second", a2 == 5 && b2 == 8 && n2 == 10);
    let a3, b3, n3 = st_lit_span("one\r\ntwo\r\n", "\r\n", n2);
    check("lit span final has no separator", n3 == -1 && b3 == 10);
    // `\r` on its own must NOT match: that is the whole reason for a multi-byte split.
    let _, bend, nend = st_lit_span("one\rtwo", "\r\n", 0);
    check("lone CR is not a CRLF match", nend == -1 && bend == 7);

    // --- clamping, not trusting ---
    let s0 = st_span("abcdef", -5, 3);
    check("span clamps negative start", s0.len == 3);
    let s1 = st_span("abcdef", 4, 99);
    check("span clamps end", s1.len == 2);
    let s2 = st_span("abcdef", 5, 2);
    check("span end<start is empty", s2.len == 0);

    // --- copy with a cap, and the partial case ---
    var d: u8[>..] = [];
    let copied = st_copy_span(d, 4, "abcdef", 1, 5);
    check("copy_span full", copied == 4 && by_eq_span(d[..], 0, d.len, "bcde"));
    var d2: u8[>..] = [];
    let partial = st_copy_span(d2, 2, "abcdef", 0, 6);
    check("copy_span partial reports what fit", partial == 2);

    // --- trim and case ---
    let ts, te = st_trim_span("  key  ");
    check("trim span", ts == 2 && te == 5);
    var lc: u8[>..] = [];
    let nl = st_to_lower(lc, 8, "MiXeD");
    check("to_lower count", nl == 5);
    check("to_lower content", by_eq_span(lc[..], 0, lc.len, "mixed"));
    var uc: u8[>..] = [];
    let nu = st_to_upper(uc, 3, "mixed");
    check("to_upper respects cap", nu == 3 && uc.len == 3);
    check("to_upper content", by_eq_span(uc[..], 0, uc.len, "MIX"));

    say("t63 done  pass=");
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

fn first_word_is(s: const u8[:], want: const u8[:]) -> bool {
    var sp = st_word(s);
    let a, b, found = st_next(sp, s);
    if !found { return false; }
    return by_eq_span(s, a, b, want);
}

fn second_word_is(s: const u8[:], want: const u8[:]) -> bool {
    var sp = st_word(s);
    let _a, _b, f1 = st_next(sp, s);
    if !f1 { return false; }
    let a, b, found = st_next(sp, s);
    if !found { return false; }
    return by_eq_span(s, a, b, want);
}
