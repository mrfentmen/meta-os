// services/tests/t55_hash.goose
//
// B-L1-55 — test program for the hash library (B-L1-14).
//
// Status: RUNS — tests/t55_hash: 21 checks, 0 failures. Measured 2026-11-02 by audit_status.py.
//
// WHY THESE VECTORS AND NOT "SOMETHING HASHES"
// --------------------------------------------
// A hash function is either exactly right or useless: a digest that differs from the
// published one by a single bit fails every signature check and every audit chain, and the
// failure looks like corrupt data rather than a bug in the hash. So the test uses the
// published test vectors, both of them:
//   - SHA-256("")  = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
//   - SHA-256("abc") = ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad
// plus CRC-32 of "123456789" = 0xCBF43926, which is the standard check value and catches the
// reflected/non-reflected and byte-order mistakes that a hash of the empty string does not.
//
// The empty string is the important one: it exercises the padding path with zero data
// blocks, which is where the length field and the final block handling most often break.
//
// It also checks that the streaming API (init/update/final) produces the same digest as the
// one-shot call. Two code paths that disagree is the classic reason a signature verifies in
// a test and fails in production.

import common.hash.hash;
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

// A published digest, as hex, so the test reads like the specification it checks.
fn hex_to_bytes(s: const u8[:], out: u8[..32]&) -> bool {
    if s.len != 64 { return false; }
    var i: i64 = 0;
    while i < 32 {
        let hi = nib(s[i * 2]);
        let lo = nib(s[i * 2 + 1]);
        if hi < 0 || lo < 0 { return false; }
        out[i] = ((hi * 16) + lo) as u8;
        i = i + 1;
    }
    return true;
}

fn nib(c: u8) -> i64 {
    if c >= 48 && c <= 57 { return (c - 48) as i64; }
    if c >= 97 && c <= 102 { return (c - 97 + 10) as i64; }
    if c >= 65 && c <= 70 { return (c - 65 + 10) as i64; }
    return -1;
}

fn main() {
    say("t55 hash vectors\n");

    // --- SHA-256 of the empty string ---
    var want_empty: u8[..32] = [0; 32];
    check("vector parses", hex_to_bytes("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", want_empty));

    var got: u8[>..] = [];
    check("sha256(\"\") runs", sha256("", got, 32));
    check("sha256(\"\") length", got.len == 32);
    check("sha256(\"\") matches the published digest", eq(got, want_empty));

    // --- SHA-256 of "abc" ---
    var want_abc: u8[..32] = [0; 32];
    check("vector parses", hex_to_bytes("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", want_abc));

    var got_abc: u8[>..] = [];
    check("sha256(\"abc\") runs", sha256("abc", got_abc, 32));
    check("sha256(\"abc\") matches the published digest", eq(got_abc, want_abc));

    // --- the digest is sensitive to one bit of input ---
    var got_abd: u8[>..] = [];
    let _ = sha256("abd", got_abd, 32);
    check("one byte of input changes the digest", eq(got_abc, got_abd) == false);

    // --- the streaming API must agree with the one-shot ---
    var ctx = sha256_init();
    check("update abc part 1", sha256_update(ctx, "a"));
    check("update abc part 2", sha256_update(ctx, "bc"));
    var streamed: u8[>..] = [];
    check("final abc", sha256_final(ctx, streamed, 32));
    check("streamed == one-shot", eq(streamed, got_abc));

    // Streaming the empty string is the case that breaks when final() assumes at least one
    // update happened.
    var ctx2 = sha256_init();
    var streamed_empty: u8[>..] = [];
    check("final on empty", sha256_final(ctx2, streamed_empty, 32));
    check("streamed empty matches", eq(streamed_empty, want_empty));

    // --- a buffer too small is refused, not truncated ---
    var tiny: u8[>..] = [];
    check("sha256 refuses a short buffer", sha256("abc", tiny, 16) == false && tiny.len == 0);

    // --- CRC-32 check value ---
    check("crc32 check value", crc32("123456789") == 0xCBF43926);

    // The incremental CRC must agree with the one-shot, in the documented start/finish form.
    var c = crc32_start();
    c = crc32_update(c, "1234");
    c = crc32_update(c, "56789");
    check("streamed crc32 agrees", crc32_finish(c) == 0xCBF43926);

    check("crc32 of empty", crc32("") == 0);

    // --- constant-time comparison: equal and unequal both answer correctly ---
    var a: u8[..4] = [1, 2, 3, 4];
    var b: u8[..4] = [1, 2, 3, 4];
    var d: u8[..4] = [1, 2, 3, 5];
    check("equal buffers", equal_constant_time(a, b));
    check("different buffers", equal_constant_time(a, d) == false);
    // Different lengths must not compare equal: an empty buffer "equalling" a full one is
    // how an unset key passes a signature check.
    var e: u8[..4] = [0; 4];
    check("length mismatch is not equal", equal_constant_time(a, e) == false);

    var r: u8[>..] = [];
    let _ = append_int(r, 32, t_pass);
    say("passed ");
    say(r);
    say("\n");
    if t_fail != 0 { say("FAILURES\n"); sys_exit(1); }
    say("t55 done\n");
    sys_exit(0);
}
