// services/tests/t115_display_r11.goose
//
// Round 11 (R11-067..072) — display: the four consoles and their three limits, the text
// helpers' wrap/clip/scroll edge cases, and the switch key as data.
//
// WHAT IS ASSERTED
// ----------------
// VCON_MAX stops the fifth console; DISPLAY_LINE_MAX and the 2048-cell screen bound refuse
// an oversized request; SCROLL_MAX clamps the history counter; WRAP_MAX_LINES reports
// overflow instead of silently truncating. Painting is checked only for its return code —
// whether pixels appear is the kernel's contract, not this service's.
//
// Status: RUNS — measured by the coordinator's `run_native.sh` row; not claimed here.

import display.display;
import display.text;
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
    say("t115 display round 11\n");

    // ======================================================================
    // 1. VCON_MAX, and every way disp_new refuses
    // ======================================================================
    disp_init();
    check("init: no consoles, active is 0", disp_active() == 0 && !disp_valid(0));

    let v0, c0 = disp_new("console", 80, 25);
    let v1, c1 = disp_new("boot", 80, 25);
    let v2, c2 = disp_new("agent", 80, 25);
    let v3, c3 = disp_new("spare", 80, 25);
    check("four consoles fit VCON_MAX",
          c0 == CODE_OK && c1 == CODE_OK && c2 == CODE_OK && c3 == CODE_OK
          && v0 == 0 && v1 == 1 && v2 == 2 && v3 == 3);

    let v4, c4 = disp_new("fifth", 80, 25);
    check("the fifth console is E_NOROOM, not a resize", c4 == E_NOROOM && v4 == -1);
    check("a refused console left the count alone", !disp_valid(4));

    // The four successful consoles above fill VCON_MAX, so every refusal probe below
    // would hit the capacity check first and return E_NOROOM. Reset the count; the
    // refusals are about argument validation, not capacity, and a test that cannot tell
    // those apart proves neither.
    disp_init();

    let vz, cz = disp_new("zero", 0, 25);
    check("a zero-width console is E_INVAL", vz == -1 && cz == E_INVAL);
    let vr, cr = disp_new("zero", 80, 0);
    check("a zero-row console is E_INVAL", vr == -1 && cr == E_INVAL);
    let vw, cw = disp_new("wide", DISPLAY_LINE_MAX + 1, 1);
    check("a width past DISPLAY_LINE_MAX is E_INVAL", vw == -1 && cw == E_INVAL);
    let vt, ct = disp_new("tall", 80, 26);
    check("a screen over 2048 cells is E_INVAL", vt == -1 && ct == E_INVAL);
    let ve, ce = disp_new("", 80, 25);
    check("an empty name is E_INVAL", ve == -1 && ce == E_INVAL);
    let vn, cn = disp_new("0123456789abcdef", 80, 25);
    check("a name of 16 bytes is E_INVAL", vn == -1 && cn == E_INVAL);

    check("invalid console ids are not valid", !disp_valid(-1) && !disp_valid(4));

    // ======================================================================
    // 2. writing: control bytes are refused, NL and CR move the cursor
    // ======================================================================
    check("a control byte is E_INVAL, not text", disp_putc(0, 0x01) == E_INVAL);
    check("a tab is not stored as a byte a terminal would interpret",
          disp_putc(0, 0x09) == E_INVAL);
    check("newline is accepted", disp_putc(0, 0x0A) == CODE_OK);
    check("carriage return is accepted", disp_putc(0, 0x0D) == CODE_OK);
    check("text is accepted", disp_puts(0, "hello") == CODE_OK);
    check("writing to an invalid console is E_INVAL", disp_puts(9, "x") == E_INVAL);

    // ======================================================================
    // 3. switching, and the key as data
    // ======================================================================
    let prev, swc = disp_switch(1);
    check("switch returns the previous console",
          prev == 0 && swc == CODE_OK && disp_active() == 1);
    let _, bad_switch = disp_switch(9);
    check("a switch to an invalid console is E_INVAL and does not move",
          bad_switch == E_INVAL && disp_active() == 1);

    check("Ctrl+Alt+F1 is console 0", disp_switch_key(0x3B, 6) == 0);
    check("Ctrl+Alt+F4 is console 3", disp_switch_key(0x3E, 6) == 3);
    check("F4 without Ctrl is not a switch", disp_switch_key(0x3E, 4) == -1);
    check("F5 is not one of the four consoles", disp_switch_key(0x3F, 6) == -1);

    // ======================================================================
    // 4. SCROLL_MAX clamps the history counter
    // ======================================================================
    // A 25-row console scrolls on the 26th newline; push past 256 lines and the counter
    // must clamp rather than wrap or keep counting.
    var n: i64 = 0;
    while n < 25 + SCROLL_MAX + 20 {
        let _ = disp_putc(0, 0x0A);
        n = n + 1;
    }
    check("history clamps at SCROLL_MAX", disp_hist_lines(0) == SCROLL_MAX);
    check("history depth is invalid for an invalid console", disp_hist_lines(9) == -1);

    // ======================================================================
    // 5. text_wrap: the three decisions, and the overflow bound
    // ======================================================================
    let w1 = text_wrap("aaaa", 4);
    check("a word exactly the width is one line", w1.count == 1 && !w1.overflow);

    let w2 = text_wrap("abcdefgh", 4);
    check("a word longer than the width is broken at the width",
          w2.count == 2 && w2.spans[0].len == 4 && w2.spans[1].len == 4);

    let w3 = text_wrap("one two three", 7);
    check("wrapping prefers the space", w3.count >= 2 && w3.spans[0].len <= 7);

    let w4 = text_wrap("ab\ncd", 10);
    check("a newline starts a span and is consumed",
          w4.count == 2 && w4.spans[0].len == 2 && w4.spans[1].off == 3 && w4.spans[1].len == 2);

    let w5 = text_wrap("", 10);
    check("empty text is no lines", w5.count == 0 && !w5.overflow);

    let w6 = text_wrap("aaaa", 0);
    check("width zero is no lines and not an overflow", w6.count == 0 && !w6.overflow);

    // 80 'a's at width 4 is 20 lines, past WRAP_MAX_LINES: the list is a prefix and says so.
    let w7 = text_wrap("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", 4);
    check("past WRAP_MAX_LINES the list is a prefix and overflow is set",
          w7.count == WRAP_MAX_LINES && w7.overflow);
    check("text_line_count reports the overflow bound, not a false exact count",
          text_line_count("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", 4) == WRAP_MAX_LINES + 1);

    // ======================================================================
    // 6. text_clip: the ellipsis is inside the width
    // ======================================================================
    var clip: u8[>..] = [];
    let cut, clipped = text_clip("hello world", 8, clip, 64);
    check("a clip to 8 is 8 bytes, ellipsis included",
          cut == 8 && clipped && same(clip[..], "hello..."));

    var shortc: u8[>..] = [];
    let cut2, clipped2 = text_clip("hello", 2, shortc, 64);
    check("a width under the ellipsis degrades to a prefix", cut2 == 2 && clipped2 && same(shortc[..], "he"));

    var fits: u8[>..] = [];
    let cut3, clipped3 = text_clip("hello", 20, fits, 64);
    check("text that fits is not marked clipped", cut3 == 5 && !clipped3 && same(fits[..], "hello"));

    // ======================================================================
    // 7. scroll regions
    // ======================================================================
    let r, rc = scroll_new(2, 5);
    check("a region knows its rows", rc == CODE_OK && r.rows == 4);
    let _, invc = scroll_new(5, 2);
    check("an inverted region is E_INVAL, not silently swapped", invc == E_INVAL);
    let _, negc = scroll_new(-1, 3);
    check("a negative top is E_INVAL", negc == E_INVAL);

    var reg = r;
    check("contains the top and bottom, not the neighbours",
          scroll_contains(reg, 2) && scroll_contains(reg, 5)
          && !scroll_contains(reg, 1) && !scroll_contains(reg, 6));

    let first, pc = scroll_push(reg, 2);
    check("pushing two lines repaints from the first moved row",
          pc == CODE_OK && first == 4 && reg.lines_pushed == 2);
    check("a line scrolled off the top has no row", scroll_row_for(reg, 0) == -1);
    check("the first visible line sits at the region top", scroll_row_for(reg, 2) == 2);
    check("a line below the region has no row", scroll_row_for(reg, 6) == -1);

    let _, clampc = scroll_push(reg, 99);
    check("pushing more than a screenful scrolls a screenful",
          clampc == CODE_OK && reg.lines_pushed == 2 + 4);

    check("resize keeps the pushed count", scroll_resize(reg, 1, 6) == CODE_OK
          && reg.rows == 6 && reg.lines_pushed == 6);
    check("a resize to an inverted region is E_INVAL", scroll_resize(reg, 6, 1) == E_INVAL);

    // ======================================================================
    // 8. load: ten screens of text through one console
    // ======================================================================
    var ok: i64 = 0;
    var refused: i64 = 0;
    var line: u8[..80] = [0; 80];
    var li: i64 = 0;
    while li < 80 { line[li] = 0x78; li = li + 1; }     // 'x'
    var screen: i64 = 0;
    while screen < 10 {
        var p: i64 = 0;
        while p < 80 {
            if disp_putc(1, line[p]) == CODE_OK { ok = ok + 1; } else { refused = refused + 1; }
            p = p + 1;
        }
        screen = screen + 1;
    }
    check("load: ten screens written with no refusal", ok == 800 && refused == 0);

    say("LOAD display ops=800 ok=");
    var ob: u8[>..] = [];
    let _ = append_int(ob, 32, ok);
    say(ob[..]);
    say(" refused=");
    var rb: u8[>..] = [];
    let _ = append_int(rb, 32, refused);
    say(rb[..]);
    say("\n");

    say("pass=");
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
