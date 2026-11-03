// services/tests/t141_clipboard.goose
//
// The clipboard's five rules, each asserted at the edge that matters:
// refusal without data loss, no partial paste, ownership, and a generation
// that moves on every change so a reader can trust its cache.
//
// Status: RUNS via tests/t141_clipboard.

import clipboard.clipboard;
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

fn same(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn main() {
    say("t141 clipboard\n");

    clip_init();
    check("init: empty, unowned, generation 0",
        clip_len_get() == 0 && clip_generation() == 0 && clip_owner_get() == CLIP_NO_OWNER);

    var out1: u8[>..] = [];
    let n0, c0 = clip_get(out1, 32);
    check("get: empty is NOTFOUND, not a zero-length success", n0 == 0 && c0 == E_NOTFOUND);

    check("set: hello owned by session 3", clip_set("hello", 3) == CODE_OK);
    check("set: length, generation, owner",
        clip_len_get() == 5 && clip_generation() == 1 && clip_owner_get() == 3);

    var out2: u8[>..] = [];
    let n1, c1 = clip_get(out2, 32);
    check("get: whole value", n1 == 5 && c1 == CODE_OK && same(out2[..5], "hello"));

    // A buffer that cannot hold the value must not receive a prefix.
    var small: u8[>..] = [];
    let n2, c2 = clip_get(small, 2);
    check("get: small buffer refused whole", n2 == 0 && c2 == E_NOROOM);

    check("clear: another session is denied", clip_clear(9) == E_DENIED);
    check("clear: denial did not change content",
        clip_len_get() == 5 && clip_generation() == 1);

    check("clear: owner may clear", clip_clear(3) == CODE_OK);
    check("clear: empty afterwards, generation moved",
        clip_len_get() == 0 && clip_owner_get() == CLIP_NO_OWNER && clip_generation() == 2);

    // Over capacity: refused, and the previous content must survive.
    check("set: restore a value", clip_set("keep", 1) == CODE_OK);
    var big: u8[..4097] = [0; 4097];
    check("set: 4097 bytes refused", clip_set(big, 1) == E_NOROOM);
    var out3: u8[>..] = [];
    let n3, c3 = clip_get(out3, 32);
    check("set: refusal left the old value",
        n3 == 4 && c3 == CODE_OK && same(out3[..4], "keep"));

    var zero: u8[..1] = [0; 1];
    check("set: empty is INVAL", clip_set(zero[..0], 1) == E_INVAL);
    check("set: negative owner is INVAL", clip_set("x", -1) == E_INVAL);

    // Unowned content may be cleared by anyone; after a clear, ownership is gone.
    check("clear: unowned clears for any caller", clip_clear(77) == CODE_OK);
    check("clear: generation still monotonic", clip_generation() == 4);

    say("t141 done  pass=");
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
