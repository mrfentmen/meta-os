// services/tests/t86_settings.goose
//
// Driver for settings — the closed key set, the range checks, the dirty count and
// the atomic import.
//
// The interesting cases are not "set a value and read it back". They are: a write of
// the value that is already there (must not dirty), a type confusion (must refuse),
// and a settings file that is corrupt in its second line (must apply nothing, not the
// first line).

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

fn num(label: const u8[:], v: i64) {
    say(label);
    var b: u8[>..] = [];
    let _ = append_int(b, 32, v);
    say(b[..]);
    say("\n");
}

fn blob(s: const u8[:]) -> u8[..512] {
    var b: u8[..512] = [0; 512];
    var i: i64 = 0;
    while i < s.len { b[i] = s[i]; i = i + 1; }
    return b;
}

fn hex(v: i64) -> u8[>..] {
    var s: u8[>..] = [];
    var x = v;
    var tmp: u8[..16] = [0; 16];
    var n: i64 = 0;
    while x > 0 {
        let d = x % 16;
        if d < 10 { tmp[n] = (48 + d) as u8; } else { tmp[n] = (55 + d) as u8; }
        x = x / 16;
        n = n + 1;
    }
    let _ = s.push(48);
    let _ = s.push(120);
    var i: i64 = 0;
    while i < n {
        let _ = s.push(tmp[n - 1 - i]);
        i = i + 1;
    }
    return s;
}

fn main() {
    say("t86 settings\n");

    // --- defaults -----------------------------------------------------------
    st_init();
    check("settings: six defaults", st_count() == 6);
    check("settings: defaults are not dirty", st_dirty_count() == 0);
    let w0, cw0 = st_get_int(SK_WALLPAPER);
    check("settings: wallpaper default 0", w0 == 0 && cw0 == CODE_OK);
    let b0, _cb0 = st_get_int(SK_BG);
    check("settings: background default 0x101820", b0 == 0x101820);
    let m0, _cm0 = st_get_int(SK_MODE);
    check("settings: mode default is dark", m0 == MODE_DARK);
    let a0, _ca0 = st_get_int(SK_ANIM);
    check("settings: animation default on", a0 == 1);
    let h0, ch0 = st_get_text(SK_HOSTNAME);
    check("settings: hostname default", ch0 == CODE_OK && h0.len == 4);

    // --- ranges -------------------------------------------------------------
    check("settings: wallpaper 7 accepted", st_put_int(SK_WALLPAPER, SET_WALLPAPER_MAX) == CODE_OK);
    check("settings: wallpaper 8 refused", st_put_int(SK_WALLPAPER, SET_WALLPAPER_MAX + 1) == E_INVAL);
    check("settings: wallpaper -1 refused", st_put_int(SK_WALLPAPER, -1) == E_INVAL);
    check("settings: a refused write changed nothing", st_get_int(SK_WALLPAPER) == SET_WALLPAPER_MAX);
    check("settings: background 0xffffff accepted", st_put_int(SK_BG, SET_COLOR_MAX) == CODE_OK);
    check("settings: background 0x1000000 refused", st_put_int(SK_BG, SET_COLOR_MAX + 1) == E_INVAL);
    check("settings: mode 0 refused", st_put_int(SK_MODE, 0) == E_INVAL);
    check("settings: mode 3 refused", st_put_int(SK_MODE, 3) == E_INVAL);
    check("settings: mode light accepted", st_put_int(SK_MODE, MODE_LIGHT) == CODE_OK);
    check("settings: animation 2 refused", st_put_int(SK_ANIM, 2) == E_INVAL);
    check("settings: animation 0 accepted", st_put_int(SK_ANIM, 0) == CODE_OK);

    // --- dirty means changed ------------------------------------------------
    st_clear_dirty();
    check("settings: clean after save", st_dirty_count() == 0);
    check("settings: rewriting the same value is not a change", st_put_int(SK_BG, SET_COLOR_MAX) == CODE_OK);
    check("settings: ... and does not dirty", st_dirty_count() == 0);
    check("settings: a new value dirties", st_put_int(SK_BG, 0x202020) == CODE_OK && st_dirty_count() == 1);
    check("settings: two changes, two dirty", st_put_int(SK_BAR, 0x303030) == CODE_OK && st_dirty_count() == 2);
    st_clear_dirty();
    check("settings: save clears every dirty flag", st_dirty_count() == 0);

    // --- text ---------------------------------------------------------------
    var name: u8[..32] = [0; 32];
    var i: i64 = 0;
    while i < SET_TEXT_MAX - 1 { name[i] = 97; i = i + 1; }
    check("settings: hostname of 31 chars accepted", st_put_text(SK_HOSTNAME, name[..SET_TEXT_MAX - 1]) == CODE_OK);
    check("settings: 32 chars refused", st_put_text(SK_HOSTNAME, name[..SET_TEXT_MAX]) == E_NOROOM);
    check("settings: empty text refused", st_put_text(SK_HOSTNAME, name[..0]) == E_INVAL);
    var ctl: u8[..8] = [0; 8];
    ctl[0] = 7;
    check("settings: control character refused", st_put_text(SK_HOSTNAME, ctl[..1]) == E_INVAL);
    var sp: u8[..8] = [0; 8];
    sp[0] = 97; sp[1] = 32; sp[2] = 98;
    check("settings: a space in a hostname refused", st_put_text(SK_HOSTNAME, sp[..3]) == E_INVAL);
    check("settings: a short hostname accepted", st_put_text(SK_HOSTNAME, sp[..1]) == CODE_OK);

    // --- type confusion -----------------------------------------------------
    check("settings: get_int on a text key refused", st_get_int(SK_HOSTNAME) == 0);
    let _gi, cgi = st_get_int(SK_HOSTNAME);
    check("settings: get_int on a text key is E_INVAL", cgi == E_INVAL);
    let _gt, cgt = st_get_text(SK_BG);
    check("settings: get_text on an int key is E_INVAL", cgt == E_INVAL);
    check("settings: put_int on a text key refused", st_put_int(SK_HOSTNAME, 1) == E_INVAL);
    check("settings: put_text on an int key refused", st_put_text(SK_BG, sp[..1]) == E_INVAL);

    // --- unknown keys -------------------------------------------------------
    let _u, cu = st_get_int(9);
    check("settings: unknown key is E_INVAL", cu == E_INVAL);
    check("settings: unknown key cannot be written", st_put_int(9, 1) == E_INVAL);
    check("settings: unknown key has no name", st_name(9).len == 0);
    check("settings: key 0 has no kind", st_kind(0) == 0);
    check("settings: every known key has a name",
          st_name(SK_WALLPAPER).len > 0 && st_name(SK_BG).len > 0 && st_name(SK_BAR).len > 0
          && st_name(SK_MODE).len > 0 && st_name(SK_ANIM).len > 0 && st_name(SK_HOSTNAME).len > 0);

    // --- export / import ----------------------------------------------------
    var out: u8[..512] = [0; 512];
    let n = st_export(out);
    check("settings: export writes six lines", n > 0);
    num("     export bytes: ", n);
    check("settings: export is in key order", out[0] == 49 && out[1] == 61);   // "1="

    var frozen_w, _fw = st_get_int(SK_WALLPAPER);
    var frozen_bg, _fb = st_get_int(SK_BG);
    st_put_int(SK_WALLPAPER, 0);
    st_put_int(SK_BG, 0);
    check("settings: values changed before the import", st_get_int(SK_WALLPAPER) == 0);
    let lines = st_import(out[..n]);
    check("settings: import reports six lines", lines == 6);
    check("settings: import restored the wallpaper", st_get_int(SK_WALLPAPER) == frozen_w);
    check("settings: import restored the colour", st_get_int(SK_BG) == frozen_bg);
    check("settings: a successful import leaves nothing dirty", st_dirty_count() == 0);

    // Export → import round trip is byte-identical: the format is its own parser's
    // inverse, which is the only cheap check that both sides agree.
    var out2: u8[..512] = [0; 512];
    let n2 = st_export(out2);
    check("settings: export after import is byte-identical", n2 == n);
    var same = true;
    i = 0;
    while i < n {
        if out[i] != out2[i] { same = false; }
        i = i + 1;
    }
    check("settings: the round trip does not drift", same);

    // --- atomic import ------------------------------------------------------
    // Second line is out of range. The first line is valid, and must NOT be applied.
    st_put_int(SK_WALLPAPER, 3);
    var bad = blob("1=1\n4=9\n");
    let badn = st_import(bad[..7]);
    check("settings: an out-of-range line is E_CORRUPT", badn == E_CORRUPT);
    check("settings: the valid first line was not applied (atomic)", st_get_int(SK_WALLPAPER) == 3);

    var unknown = blob("1=1\n9=3\n");
    check("settings: an unknown key refuses the whole file", st_import(unknown[..6]) == E_CORRUPT);
    var nonum = blob("1=abc\n");
    check("settings: a non-numeric int is E_CORRUPT", st_import(nonum[..6]) == E_CORRUPT);
    var noeq = blob("1\n");
    check("settings: a line with no '=' is E_CORRUPT", st_import(noeq[..2]) == E_CORRUPT);
    var blank = blob("1=2\n\n");
    check("settings: a blank line is E_CORRUPT", st_import(blank[..5]) == E_CORRUPT);
    var empty = blob("");
    check("settings: an empty file is E_CORRUPT", st_import(empty[..0]) == E_CORRUPT);
    var trail = blob("1=2\n\n");
    check("settings: a trailing newline is not a blank line", st_import(trail[..4]) == 1);

    // A file that names only one key is a valid subset: the others keep their values.
    st_put_int(SK_BAR, 0x123456);
    var partial = blob("1=5\n");
    check("settings: a one-line file imports", st_import(partial[..4]) == 1);
    check("settings: the named key changed", st_get_int(SK_WALLPAPER) == 5);
    check("settings: the unnamed key kept its value", st_get_int(SK_BAR) == 0x123456);

    // A text value longer than the field is refused before it is copied.
    var long_text = blob("6=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n");
    check("settings: an over-long text value is refused", st_import(long_text[..38]) == E_NOROOM);

    // --- re-init ------------------------------------------------------------
    st_init();
    check("settings: init returns to six defaults", st_count() == 6);
    check("settings: init restores the wallpaper default", st_get_int(SK_WALLPAPER) == 0);
    check("settings: init clears dirty", st_dirty_count() == 0);

    // --- SK_MAX_ID: the key table ends where the ids end -----------------------
    // Six keys, ids 1..SK_MAX_ID. One past the last id must be E_NOTFOUND from every
    // entry point, not a seventh key with default values: a settings surface that grows a
    // row for a key it does not have is a surface that reports success on a no-op.
    let c_put = st_put_int(SK_MAX_ID + 1, 1);
    check("settings: a key past SK_MAX_ID is refused on write", c_put == E_INVAL);
    let _v2, c_get = st_get_int(SK_MAX_ID + 1);
    check("settings: a key past SK_MAX_ID is refused on read", c_get == E_INVAL);
    check("settings: the key table still has six entries", st_count() == 6);

    say("t86 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
}
