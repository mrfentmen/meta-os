// services/tests/t64_hex.goose
//
// B-L1-70 — test program for `common/hex`.
//
// The decode cases are the point. A digest check is a comparison against
// attacker-supplied text, so every refusal here is a refusal to compare against
// something that only looks like a digest: odd length, `0x`, whitespace, a
// non-hex character, a buffer that is one byte short.
//
// The last one gets its own case because it is the interesting failure: the
// decoder must leave the destination EMPTY on error, not half-written.

import common.hex.hex;
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
    say("t64 hex\n");

    // --- encode ---
    var e1: u8[>..] = [];
    let n1 = hex_encode(e1, 8, "\x00\x0f\xff", false);
    check("encode length", n1 == 6 && e1.len == 6);
    check("encode lowercase bytes", e1[0] == '0' && e1[1] == '0' && e1[4] == 'f' && e1[5] == 'f');
    var e2: u8[>..] = [];
    let _ = hex_encode(e2, 8, "\xab", true);
    check("encode uppercase", e2[0] == 'A' && e2[1] == 'B');
    var e3: u8[>..] = [];
    let n3 = hex_encode(e3, 3, "\x01\x02\x03", false);
    check("encode stops before a half byte fits", n3 == 2 && e3.len == 2);
    check("encoded_len", hex_encoded_len(32) == 64);

    // --- decode: the happy path ---
    var d1: u8[>..] = [];
    let m1 = hex_decode(d1, 8, "00ff10");
    check("decode count", m1 == 3 && d1.len == 3);
    check("decode values", d1[0] == 0 && d1[1] == 255 && d1[2] == 16);
    var d2: u8[>..] = [];
    check("decode accepts uppercase", hex_decode(d2, 4, "AB") == 1 && d2[0] == 0xab);
    var d3: u8[>..] = [];
    check("decode of empty is zero bytes", hex_decode(d3, 4, "") == 0);

    // --- decode: every refusal ---
    var r1: u8[>..] = [];
    check("odd length refused", hex_decode(r1, 8, "abc") == -1);
    check("odd length wrote nothing", r1.len == 0);
    var r2: u8[>..] = [];
    check("0x prefix refused", hex_decode(r2, 8, "0xff") == -1);
    check("0x prefix wrote nothing", r2.len == 0);
    var r3: u8[>..] = [];
    check("space refused", hex_decode(r3, 8, "de ad") == -1);
    var r4: u8[>..] = [];
    check("non-hex letter refused", hex_decode(r4, 8, "zz") == -1);
    var r5: u8[>..] = [];
    // "00ff" is 2 bytes; a cap of 1 must refuse BEFORE writing the first byte.
    check("short destination refused", hex_decode(r5, 1, "00ff") == -1);
    check("short destination wrote nothing", r5.len == 0);

    // --- exactness ---
    check("is_exact 32 bytes", hex_is_exact(
        "0000000000000000000000000000000000000000000000000000000000000000", 32));
    check("is_exact rejects 31", !hex_is_exact(
        "00000000000000000000000000000000000000000000000000000000000000", 32));
    var long_hex: u8[>..] = [];
    let _ = by_repeat_hex(long_hex, 64, 'a');
    check("is_exact rejects non-hex of right length", !hex_is_exact(long_hex[..], 32));

    // --- case-insensitive equality ---
    check("eq_ci same", hex_eq_ci("DEADBEEF", "deadbeef"));
    check("eq_ci differs", !hex_eq_ci("DEADBEEF", "deadbeee"));
    check("eq_ci odd length is false", !hex_eq_ci("abc", "abc"));
    check("eq_ci non-hex is false", !hex_eq_ci("zz", "zz"));

    say("t64 done  pass=");
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

fn by_repeat_hex(dst: u8[>..]&, n: i64, c: u8) -> i64 {
    var i: i64 = 0;
    while i < n {
        dst.push(c);
        i = i + 1;
    }
    return n;
}
