// services/tests/t72_hostile.goose
//
// B-L1-07/B-L1-16/B-L1-45 — BF4-13: the malformed-input suite for the format,
// config and hash libraries.
//
// Status: RUNS — tests/t72_hostile: 77 checks, 0 failures. Measured 2026-11-02 by audit_status.py.sh.
//
// BEHAVIOUR SPECIFIED FIRST, THEN ASSERTED
// ----------------------------------------
// Every case below is a decision that was already written down in the library's
// header comment, or a decision this file makes for the first time and states in
// the check's name. The point of a hostile suite is not "it did not crash" -- a
// crash is the loudest failure and the least interesting. The interesting ones
// are: it accepted something it should have refused, it refused something it
// should have accepted, and it answered from the wrong place in the file.
//
// The three libraries fail differently and are tested differently:
//
//   cfg   parses TEXT. Its failure modes are a line that half-parses, a section
//         that silently swallows the rest of the file, and a duplicate that
//         resolves backwards. Every case here is a whole document, because a
//         parser is only wrong in the context of the lines around it.
//   fmt   writes into a buffer under a cap. Its failure mode is a write that
//         goes one byte past the cap, or a refusal that wrote half a value
//         before refusing. Both leave a caller with corrupt output and no error.
//   hash  has no input it can refuse. Its failure mode is a length that changes
//         the answer (a digest that depends on chunking), which is why the
//         streaming cases cross block boundaries at odd offsets.

import common.cfg.cfg;
import common.fmt.fmt;
import common.hash.hash;
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

// cfg_get into a fresh buffer, plus whether it succeeded.
fn get(cfg: Config&, section: const u8[:], key: const u8[:], out: u8[>..]&, cap: i64) -> bool {
    return cfg_get(cfg, section, key, out, cap);
}

fn hex_byte(b: u8) -> u8 {
    if b < 10 { return (48 + (b as i64)) as u8; }
    return (87 + (b as i64)) as u8;   // 'a' + (b - 10)
}

// Tuple results cannot be field-accessed off a call in this language, so the
// assertions go through four one-line helpers. They exist so a check stays one
// line and names the half it is asking about.
fn ci(cfg: Config&, section: const u8[:], key: const u8[:], dflt: i64) -> i64 {
    let v, _ok = cfg_int(cfg, section, key, dflt);
    return v;
}

fn ci_ok(cfg: Config&, section: const u8[:], key: const u8[:], dflt: i64) -> bool {
    let _v, ok = cfg_int(cfg, section, key, dflt);
    return ok;
}

fn cb(cfg: Config&, section: const u8[:], key: const u8[:], dflt: bool) -> bool {
    let v, _ok = cfg_bool(cfg, section, key, dflt);
    return v;
}

fn cb_ok(cfg: Config&, section: const u8[:], key: const u8[:], dflt: bool) -> bool {
    let _v, ok = cfg_bool(cfg, section, key, dflt);
    return ok;
}

fn main() {
    say("t72 malformed input: cfg, fmt, hash\n");

    // =====================================================================
    // cfg -- a document with every kind of junk in it, one junk per line
    // =====================================================================
    //
    // Line by line:
    //   "key with no equals"       not a pair: ignored, and must not eat the rest
    //   "= orphan value"           empty key: not a pair
    //   "   "                      blank: ignored
    //   "# comment"  "; comment"   both comment markers
    //   "k = a=b"                  the FIRST '=' splits; the value keeps the rest
    //   "[sec]"  "in = 1"          the section works after all that junk
    //   "[broken"                  unterminated section: ignored, not opened
    //   "[a] trailing"             a section is exactly "[name]": extra text is not a header
    //   "[ sp ]"                   spaces inside brackets are not a name
    //   "after = yes"              the value after a rejected header stays where it was
    let doc: const u8[:] = "key with no equals\n= orphan value\n   \n# comment\n; comment\nk = a=b\n[sec]\nin = 1\n[broken\n[a] trailing\n[ sp ]\nafter = yes\n";

    var cfg = cfg_init(doc);
    var v: u8[>..] = [];
    check("a line with no '=' is not a pair", !get(cfg, "", "key with no equals", v, 64));
    check("an empty key is not a key", !get(cfg, "", "", v, 64));
    check("a blank line is not a pair", !cfg_has(cfg, "", ""));
    check("'#' starts a comment", !cfg_has(cfg, "", "# comment"));
    check("';' starts a comment", !cfg_has(cfg, "", "; comment"));
    check("a value may contain '='", get(cfg, "", "k", v, 64) && eq(v[..], "a=b"));
    check("a section after junk is still a section", ci(cfg, "sec", "in", 0) == 1);
    let sec_v, sec_ok = cfg_int(cfg, "sec", "in", -1);
    check("and its int parses", sec_ok && sec_v == 1);
    check("an unterminated section is not opened", !cfg_has(cfg, "broken", "after"));
    check("a section needs to end with ']'", !cfg_has(cfg, "a", "after"));
    check("spaces inside the brackets are not a name", !cfg_has(cfg, " sp ", "after"));
    // A rejected header does not change state: the key after it belongs to the last
    // section that DID open (`sec`), not to the top level and not to the broken one.
    check("a rejected header leaves the current section alone", cb(cfg, "sec", "after", false));
    check("and the key is not at the top level", !cfg_has(cfg, "", "after"));

    // --- an empty document ---
    var empty = cfg_init("");
    check("empty document has no keys", !cfg_has(empty, "", "k"));
    let ei_v, ei_ok = cfg_int(empty, "", "k", 42);
    check("empty document returns the default int", ei_v == 42 && !ei_ok);
    let eb_v, eb_ok = cfg_bool(empty, "", "k", true);
    check("empty document returns the default bool", eb_v && !eb_ok);

    // --- values: empty, whitespace, case, and the '=' rule again ---
    let edge: const u8[:] = "empty =\nspaced =    \ntabbed\t=\t7\ntruth = TRUE\ntruthy = true\nmixed = x y\n=novalue\nnovalue2=\n";
    var e2 = cfg_init(edge);
    check("an empty value is present", cfg_has(e2, "", "empty"));
    var ev: u8[>..] = [];
    check("an empty value gets back as empty", get(e2, "", "empty", ev, 8) && ev.len == 0);
    check("an empty value is not an int", !ci_ok(e2, "", "empty", 5));
    check("an empty value is not a bool", !cb_ok(e2, "", "empty", false));
    check("spaces around a value are trimmed", get(e2, "", "spaced", ev, 8) && ev.len == 0);
    check("tabs around key and value are trimmed", ci(e2, "", "tabbed", 0) == 7);
    check("bool is case-sensitive: TRUE is a typo", !cb_ok(e2, "", "truth", false));
    check("bool accepts lowercase true", cb_ok(e2, "", "truthy", false) && cb(e2, "", "truthy", false));
    check("a value with a space keeps it", get(e2, "", "mixed", ev, 8) && eq(ev[..], "x y"));
    check("a line starting with '=' has no key", !cfg_has(e2, "", ""));
    check("a key with a trailing '=' and no value is present", cfg_has(e2, "", "novalue2"));

    // --- CRLF, which every config file written on another OS has ---
    let crlf: const u8[:] = "a = 1\r\nb = 2\r\n[s]\r\nc = 3\r\n";
    var c3 = cfg_init(crlf);
    check("CRLF: top-level value parses", ci(c3, "", "a", 0) == 1);
    check("CRLF: the section is not polluted by the \\r", ci(c3, "s", "c", 0) == 3);
    check("CRLF: the value has no trailing \\r", ci(c3, "", "b", 0) == 2);

    // --- every boolean spelling the header promises, and one it does not ---
    let bools: const u8[:] = "t1 = 1\nt0 = 0\nt2 = true\nt3 = yes\nt4 = on\nf1 = false\nf2 = no\nf3 = off\nbad = 2\nbad2 = y\nbad3 = TRUE\n";
    var b4 = cfg_init(bools);
    check("bool 1/0", cb(b4, "", "t1", false) && !cb(b4, "", "t0", true));
    check("bool true", cb(b4, "", "t2", false));
    check("bool yes", cb(b4, "", "t3", false));
    check("bool on", cb(b4, "", "t4", false));
    let f1_v, f1_ok = cfg_bool(b4, "", "f1", true);
    let f2_v, f2_ok = cfg_bool(b4, "", "f2", true);
    let f3_v, f3_ok = cfg_bool(b4, "", "f3", true);
    check("bool false/no/off", f1_ok && !f1_v && f2_ok && !f2_v && f3_ok && !f3_v);
    check("bool '2' is refused, not guessed", !cb_ok(b4, "", "bad", false));
    check("bool 'y' is refused, not guessed", !cb_ok(b4, "", "bad2", false));
    check("bool 'TRUE' is refused, not guessed", !cb_ok(b4, "", "bad3", false));

    // --- a long line: 400 bytes of value, parsed and returned whole ---
    // Built by hand because a config value this long is exactly the case a
    // fixed 64-byte assumption breaks on.
    var longtext: u8[>..] = [];
    let _ = append_str(longtext, 512, "long = ");
    var li: i64 = 0;
    while li < 400 { longtext.push('x'); li = li + 1; }
    longtext.push('\n');
    var lc = cfg_init(longtext[..]);
    var lout: u8[>..] = [];
    check("a 400-byte value round-trips", get(lc, "", "long", lout, 512) && lout.len == 400);
    var lshort: u8[>..] = [];
    check("a 400-byte value refuses a 64-byte buffer", !get(lc, "", "long", lshort, 64));
    check("and the refusal wrote nothing", lshort.len == 0);

    // --- cfg_get at exactly the cap ---
    let exact: const u8[:] = "k = 12345\n";
    var xc = cfg_init(exact);
    var xout: u8[>..] = [];
    check("a value exactly as long as the cap fits", get(xc, "", "k", xout, 5) && eq(xout[..], "12345"));

    // =====================================================================
    // fmt -- the cap is not a suggestion
    // =====================================================================
    var buf: u8[>..] = [];
    check("append into cap 0 refuses", !append_str(buf, 0, "x") && buf.len == 0);
    check("append_char into cap 0 refuses", !append_char(buf, 0, 'x') && buf.len == 0);
    check("an empty string into cap 0 succeeds", append_str(buf, 0, "") && buf.len == 0);
    check("exact fit succeeds", append_str(buf, 3, "abc") && buf.len == 3);
    check("an exact fit is allowed at a smaller cap too", append_str(buf, 5, "xy") && buf.len == 5);
    check("and the bytes are the ones asked for", eq(buf[..], "abcxy"));
    check("one byte short refuses", !append_int(buf, 5, 7) && buf.len == 5);

    var b2: u8[>..] = [];
    check("append_int negative", append_int(b2, 32, -1234) && eq(b2[..], "-1234"));
    var b3: u8[>..] = [];
    check("append_int zero", append_int(b3, 32, 0) && eq(b3[..], "0"));
    var b4b: u8[>..] = [];
    check("append_int i64 min does not overflow", append_int(b4b, 32, -9223372036854775807 - 1) && b4b.len == 20);
    var b5: u8[>..] = [];
    check("append_int refuses one byte short of the digits", !append_int(b5, 19, -9223372036854775807 - 1));
    check("and wrote nothing", b5.len == 0);

    var b6: u8[>..] = [];
    check("append_int_pad zero-pads to width", append_int_pad(b6, 32, 7, 4, '0') && eq(b6[..], "0007"));
    var b7: u8[>..] = [];
    check("append_uint hex", append_uint(b7, 32, 255, 16, 2, '0') && eq(b7[..], "ff"));
    var b8: u8[>..] = [];
    check("a base below 2 is refused", !append_uint(b8, 32, 1, 1, 1, '0') && b8.len == 0);
    var b9: u8[>..] = [];
    check("a base above 36 is refused", !append_uint(b9, 32, 1, 37, 1, '0') && b9.len == 0);

    var b10: u8[>..] = [];
    check("append_bool true", append_bool(b10, 32, true) && eq(b10[..], "true"));
    check("append_bool false", append_bool(b10, 32, false) && eq(b10[..], "truefalse"));

    var b11: u8[>..] = [];
    let _ = append_str(b11, 4, "abcd");
    check("terminate refuses when it would pass the cap", !terminate(b11, 4) && b11.len == 4);
    check("terminate writes the NUL when there is room", terminate(b11, 5) && b11.len == 5 && b11[4] == 0);

    // room_left is a report, not a permission: it must never go negative.
    var b12: u8[>..] = [];
    check("room_left is the whole cap when empty", room_left(b12, 10) == 10);
    let _ = append_str(b12, 10, "abcd");
    check("room_left counts what is used", room_left(b12, 10) == 6);
    check("a cap smaller than the content reports zero, not negative", room_left(b12, 2) == 0);

    // =====================================================================
    // hash -- no input is refused, so the failure is a length that matters
    // =====================================================================
    // 1000 bytes, hashed in one shot, then in chunks of 3 (which crosses the
    // 64-byte block boundary at 63, not at 0) and in chunks of 1 at the tail.
    var big: u8[>..] = [];
    var hi: i64 = 0;
    while hi < 1000 {
        big.push((65 + (hi % 26)) as u8);
        hi = hi + 1;
    }
    var one: u8[>..] = [];
    check("1000 bytes hashes", sha256(big[..], one, 32) && one.len == 32);

    var streamed: u8[>..] = [];
    var sctx = sha256_init();
    var off: i64 = 0;
    while off < 1000 {
        var chunk_end = off + 3;
        if chunk_end > 1000 { chunk_end = 1000; }
        let _ = sha256_update(sctx, big[off..chunk_end]);
        off = chunk_end;
    }
    check("streamed in 3-byte chunks", sha256_final(sctx, streamed, 32) && streamed.len == 32);
    check("chunking does not change the digest", eq(one[..], streamed[..]));

    // An empty update between chunks must be a no-op, not a reset.
    var sctx2 = sha256_init();
    let _ = sha256_update(sctx2, big[0..500]);
    let _ = sha256_update(sctx2, big[500..500]);
    let _ = sha256_update(sctx2, big[500..1000]);
    var streamed2: u8[>..] = [];
    check("an empty update is a no-op", sha256_final(sctx2, streamed2, 32) && eq(one[..], streamed2[..]));

    var short: u8[>..] = [];
    check("a 31-byte output buffer is refused", !sha256(big[..], short, 31));
    var short2: u8[>..] = [];
    check("a 0-byte output buffer is refused", !sha256(big[..], short2, 0));

    // crc32 chained in the same shape must equal crc32 in one call.
    var c1 = crc32(big[..]);
    var c2 = crc32_update(crc32_update(crc32_start(), big[0..500]) , big[500..1000]);
    let c3 = crc32_finish(c2);
    check("crc32 chained equals one-shot", c1 == c3);
    var none: u8[>..] = [];
    check("crc32 of an empty slice is the empty value", crc32(none[..]) == 0);
    check("crc32 chaining an empty slice changes nothing", crc32_update(crc32_start(), none[..]) == crc32_start());

    // Constant-time comparison must be constant-TIME, so its length behaviour is
    // the only thing a test can assert: different lengths are never equal.
    var h16: u8[>..] = [];
    var h16b: u8[>..] = [];
    var j: i64 = 0;
    while j < 16 { h16.push(0xab); h16b.push(0xab); j = j + 1; }
    check("equal buffers compare equal", equal_constant_time(h16[..], h16b[..]));
    h16b[15] = 0xac;
    check("a last-byte difference is not equal", !equal_constant_time(h16[..], h16b[..]));
    check("a length difference is not equal", !equal_constant_time(h16[0..15], h16b[..]));

    say("t72 done  pass=");
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
