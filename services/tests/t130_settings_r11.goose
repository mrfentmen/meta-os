// services/tests/t130_settings_r11.goose
//
// Round 11 (R11-157..162): settings, the edges t86 does not drive.
//
// t86_settings owns the defaults, the range checks, the dirty count and the atomic import
// (67 checks). This driver adds: st_in_range as a pure function, text same-value writes,
// the import parser's key bounds (0, SK_MAX_ID+1, negative), control bytes in imported
// text, atomicity with a text line, and the finding that import accepts a hostname with a
// space although st_put_text refuses one.
//
// Status: WRITTEN — the coordinator compiles and runs this; nothing here has run yet.

import settings.settings;
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

fn eqs(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn blob(s: const u8[:]) -> u8[..512] {
    var b: u8[..512] = [0; 512];
    var i: i64 = 0;
    while i < s.len { b[i] = s[i]; i = i + 1; }
    return b;
}

fn main() {
    say("t130 settings r11\n");

    // ------------------------------------------------------------------
    // 1. st_in_range is the one gate: every kind and both sides of each edge
    // ------------------------------------------------------------------
    st_init();
    check("settings: wallpaper 0 is in range", st_in_range(SK_WALLPAPER, 0));
    check("settings: wallpaper at the max is in range", st_in_range(SK_WALLPAPER, SET_WALLPAPER_MAX));
    check("settings: wallpaper past the max is out", !st_in_range(SK_WALLPAPER, SET_WALLPAPER_MAX + 1));
    check("settings: wallpaper -1 is out", !st_in_range(SK_WALLPAPER, -1));
    check("settings: colour 0 is in range", st_in_range(SK_BG, 0));
    check("settings: colour at the max is in range", st_in_range(SK_BG, SET_COLOR_MAX));
    check("settings: colour past the max is out", !st_in_range(SK_BG, SET_COLOR_MAX + 1));
    check("settings: bar follows the colour range", st_in_range(SK_BAR, 0x123456) && !st_in_range(SK_BAR, -1));
    check("settings: mode dark and light are in range",
          st_in_range(SK_MODE, MODE_DARK) && st_in_range(SK_MODE, MODE_LIGHT));
    check("settings: mode 0 is out", !st_in_range(SK_MODE, 0));
    check("settings: animation 0 and 1 are in range", st_in_range(SK_ANIM, 0) && st_in_range(SK_ANIM, 1));
    check("settings: animation 2 is out", !st_in_range(SK_ANIM, 2));
    check("settings: a text key is never in a numeric range", !st_in_range(SK_HOSTNAME, 1));
    check("settings: an unknown id is never in range", !st_in_range(99, 1));

    // ------------------------------------------------------------------
    // 2. text writes: same bytes are not a change, one byte is
    // ------------------------------------------------------------------
    st_init();
    let h0, ch0 = st_get_text(SK_HOSTNAME);
    check("settings: hostname default is 'meta'", ch0 == CODE_OK && eqs(h0, "meta"));
    st_clear_dirty();
    check("settings: writing alpha is a change",
          st_put_text(SK_HOSTNAME, "alpha") == CODE_OK && st_dirty_count() == 1);
    st_clear_dirty();
    check("settings: rewriting the same text is not a change",
          st_put_text(SK_HOSTNAME, "alpha") == CODE_OK && st_dirty_count() == 0);
    check("settings: one different byte dirties",
          st_put_text(SK_HOSTNAME, "alphb") == CODE_OK && st_dirty_count() == 1);

    // ------------------------------------------------------------------
    // 3. import's key and value bounds
    // ------------------------------------------------------------------
    // FINDING: st_put_text refuses a space in a hostname, st_import accepts one. The
    // file path is a second validator, and it is weaker than the write path.
    var sp = blob("6=a b\n");
    check("settings: import accepts a hostname with a space (finding)", st_import(sp[..6]) == 1);
    let hs, chs = st_get_text(SK_HOSTNAME);
    check("settings: the imported hostname has the space", chs == CODE_OK && hs.len == 3 && hs[1] == 32);

    var z = blob("0=5\n");
    check("settings: key 0 is refused", st_import(z[..4]) == E_CORRUPT);
    var seven = blob("7=1\n");
    check("settings: key SK_MAX_ID+1 is refused", st_import(seven[..4]) == E_CORRUPT);
    var neg = blob("-1=5\n");
    check("settings: a negative key is refused", st_import(neg[..5]) == E_CORRUPT);
    var ev = blob("4=\n");
    check("settings: an empty value is refused", st_import(ev[..3]) == E_CORRUPT);
    var range = blob("4=16777216\n");
    check("settings: an out-of-range colour is refused", st_import(range[..11]) == E_CORRUPT);
    var ctl = blob("6=ab\n");
    ctl[3] = 7;
    check("settings: a control byte in imported text is refused", st_import(ctl[..5]) == E_CORRUPT);

    // ------------------------------------------------------------------
    // 4. atomicity across kinds: a valid int line and a valid text line
    //    before a corrupt line must both be discarded
    // ------------------------------------------------------------------
    st_init();
    st_put_text(SK_HOSTNAME, "keep");
    st_clear_dirty();
    let wall_before, _wb = st_get_int(SK_WALLPAPER);
    var bad = blob("1=2\n6=changed\n3=zzz\n");
    check("settings: a bad third line refuses the file", st_import(bad[..20]) == E_CORRUPT);
    check("settings: the valid first line was not applied (atomic)",
          st_get_int(SK_WALLPAPER) == wall_before);
    let hn, chn = st_get_text(SK_HOSTNAME);
    check("settings: the live hostname was not changed", chn == CODE_OK && eqs(hn, "keep"));

    // ------------------------------------------------------------------
    // 5. the closed key set: six ids, and no import can add a seventh
    // ------------------------------------------------------------------
    st_init();
    check("settings: six keys after init", st_count() == 6);
    var all = blob("1=1\n2=0\n3=0\n4=2\n5=0\n6=host\n");
    check("settings: a six-line import applies six lines", st_import(all[..27]) == 6);
    check("settings: the table is still six entries", st_count() == 6);

    // ------------------------------------------------------------------
    // 6. load: 120 writes, every ninth value out of range
    // ------------------------------------------------------------------
    st_init();
    var ops: i64 = 0;
    var ok: i64 = 0;
    var refused: i64 = 0;
    while ops < 120 {
        let v = ops % 9;
        let code = st_put_int(SK_WALLPAPER, v);
        if code == CODE_OK { ok = ok + 1; } else { refused = refused + 1; }
        ops = ops + 1;
    }
    check("settings: 120 writes with 13 refusals", ok == 107 && refused == 13);

    say("LOAD settings ops=");
    var lb: u8[>..] = [];
    let _ = append_int(lb, 32, ops);
    say(lb[..]);
    say(" ok=");
    var lob: u8[>..] = [];
    let _ = append_int(lob, 32, ok);
    say(lob[..]);
    say(" refused=");
    var lrb: u8[>..] = [];
    let _ = append_int(lrb, 32, refused);
    say(lrb[..]);
    say("\n");

    say("t130 done  pass=");
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
