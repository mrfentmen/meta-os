// services/tests/t45_fmt.goose
//
// B-L1-45 — test program for the format library (B-L1-10).
//
// Status: WRITTEN (not COMPILED, not RUN). It compiles and runs the moment K6 gives the
// six syscalls in common/sys/sys.goose a kernel to talk to; until then, nothing here has
// executed, and it must not be reported as passing.
//
// WHAT IT ASSERTS, AND WHY EACH ONE
// ---------------------------------
// A formatter is the one library whose bugs appear in every other service's output, so the
// cases are chosen for the ways it can be wrong rather than for coverage:
//   - zero and one (off-by-one in the digit loop);
//   - a negative number (sign handling, and whether '-' counts against the cap);
//   - the smallest i64 (the magnitude that has no positive counterpart -- the case that
//     aborts in a naive `n = -n`);
//   - hex with padding (the path append_uint takes, which the decimal path does not);
//   - a cap that is exactly one byte short (the refusal must happen BEFORE any write, so
//     the buffer must be untouched, not partially filled).
// The refusal case is the important one: a formatter that writes three bytes and then
// returns false has already corrupted the record it was building.
//
// Each case uses its own buffer. A builder cannot be cleared, so reusing one would make
// every later assertion depend on an earlier failure -- the test would pass or fail for the
// wrong reason.

import common.fmt.fmt;
import common.sys.sys;

var t_pass: i64 = 0;
var t_fail: i64 = 0;

fn say(s: const u8[:]) { let _ = sys_write_serial(s); }

fn t_eq(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn check(name: const u8[:], cond: bool) {
    if cond { t_pass = t_pass + 1; say("ok   "); }
    else { t_fail = t_fail + 1; say("FAIL "); }
    say(name);
    say("\n");
}

fn main() {
    say("t45 fmt\n");

    // --- decimal ---
    var b0: u8[>..] = [];
    check("append_int 0", append_int(b0, 32, 0) && t_eq(b0, "0"));

    var b1: u8[>..] = [];
    check("append_int 1", append_int(b1, 32, 1) && t_eq(b1, "1"));

    var b2: u8[>..] = [];
    check("append_int 1234567", append_int(b2, 32, 1234567) && t_eq(b2, "1234567"));

    var b3: u8[>..] = [];
    check("append_int -42", append_int(b3, 32, -42) && t_eq(b3, "-42"));

    var b4: u8[>..] = [];
    check("append_int i64 min", append_int(b4, 24, -9223372036854775807 - 1) && b4.len == 20 && b4[0] == '-');

    // --- unsigned, other bases ---
    var b5: u8[>..] = [];
    check("append_uint hex ff", append_uint(b5, 8, 255, 16, 2, '0') && t_eq(b5, "ff"));

    var b6: u8[>..] = [];
    check("append_uint hex 5", append_uint(b6, 8, 5, 16, 2, '0') && t_eq(b6, "05"));

    var b7: u8[>..] = [];
    check("append_uint bin 5", append_uint(b7, 16, 5, 2, 4, '0') && t_eq(b7, "0101"));

    // base out of range is refused, not guessed
    var b8: u8[>..] = [];
    check("append_uint base 1 refused", append_uint(b8, 8, 5, 1, 1, '0') == false && b8.len == 0);

    var b9: u8[>..] = [];
    check("append_uint base 37 refused", append_uint(b9, 8, 5, 37, 1, '0') == false && b9.len == 0);

    // --- the cap rule ---
    // "hello" is 5 bytes; a cap of 4 must refuse and leave the buffer EMPTY.
    var b10: u8[>..] = [];
    check("append_str over cap refused", append_str(b10, 4, "hello") == false && b10.len == 0);

    var b11: u8[>..] = [];
    check("append_str at cap", append_str(b11, 5, "hello") && t_eq(b11, "hello"));
    // A second write past the cap is refused and the first write survives.
    check("append after full refused", append_str(b11, 5, "!") == false && t_eq(b11, "hello"));

    // 20 digits need 20 bytes: cap 19 must refuse with nothing written.
    var b12: u8[>..] = [];
    check("append_int cap short refused",
        append_int(b12, 19, -9223372036854775807 - 1) == false && b12.len == 0);

    // --- padding ---
    var b13: u8[>..] = [];
    check("append_int_pad", append_int_pad(b13, 8, 7, 3, '0') && t_eq(b13, "007"));

    // --- bool ---
    var b14: u8[>..] = [];
    check("append_bool true", append_bool(b14, 8, true) && t_eq(b14, "true"));

    var b15: u8[>..] = [];
    check("append_bool false", append_bool(b15, 8, false) && t_eq(b15, "false"));

    // --- newline and terminator ---
    var b16: u8[>..] = [];
    check("append_nl", append_nl(b16, 4) && b16.len == 1 && b16[0] == 10);

    var b17: u8[>..] = [];
    let _ = append_str(b17, 16, "ab");
    check("terminate appends NUL", terminate(b17, 16) && b17.len == 3 && b17[2] == 0);
    // A terminator with no room must be refused rather than dropped silently.
    check("terminate at cap refused", terminate(b17, 3) == false && b17.len == 3);

    // --- helpers agree with the buffer ---
    var b18: u8[>..] = [];
    let _ = append_str(b18, 16, "abc");
    check("used()", used(b18, 16) == 3);
    check("room_left()", room_left(b18, 16) == 13);
    check("full() false", full(b18, 16) == false);
    check("full() true", full(b18, 3) == true);

    var r: u8[>..] = [];
    let _ = append_int(r, 32, t_pass);
    say("passed ");
    say(r);
    say("\n");
    if t_fail != 0 { say("FAILURES\n"); sys_exit(1); }
    say("t45 done\n");
    sys_exit(0);
}
