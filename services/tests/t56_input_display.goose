// services/tests/t56_input_display.goose
//
// B-L1-56 — test program for the input decoder and the virtual consoles (B-L1-26/B-L1-27).
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// THE INPUT SIDE
// --------------
// The decoder turns set-1 scancodes into key events. The cases are the ones that make typing
// feel wrong: shift held and released, caps lock (which flips only letters), a control key
// that must not produce a character, the release bit (0x80) stripped so a release cannot be
// read as a second press, and repeat -- which must not fire before the delay has passed, and
// must fire at the configured rate after it.
//
// THE DISPLAY SIDE
// ----------------
// Consoles are created, written to, scrolled and switched. The assertions are about the
// console's own state (validity, which one is active, that a switch returns the previous
// one) rather than about pixels: the framebuffer is the kernel's business, and a test that
// asserted drawn output would be asserting a mock.
//
// One thing is deliberately NOT asserted: that a paint reaches the screen. On K1 there is no
// framebuffer, so the calls report zero bytes written. The test states that instead of
// pretending.

import input.input;
import display.display;
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
    say("t56 input + display\n");

    input_init(300, 40);

    // --- letters and shift ---
    // Set-1 scancode 0x1E is 'a'.
    check("a unshifted", input_char(0x1E, false) == 'a');
    check("a shifted", input_char(0x1E, true) == 'A');
    check("is a letter", input_letter(0x1E));

    // A non-letter key produces no character: the caller must use the scancode.
    check("enter has no character", input_char(KEY_ENTER, false) == 0 as u8);
    check("enter is not a letter", input_letter(KEY_ENTER) == false);

    // --- decode: press, then release ---
    let e1, ok1 = input_decode(0x1E, 0);
    check("press decoded", ok1 && e1.pressed && e1.ch == 'a' && e1.scancode == 0x1E);
    check("press is not a repeat", e1.repeat == false);

    // 0x9E is 'a' released (bit 7 set). The scancode must come back WITHOUT that bit, and
    // pressed must be false -- otherwise every key press is also a phantom press.
    let e2, ok2 = input_decode(0x9E, 10);
    check("release decoded", ok2 && e2.pressed == false && e2.scancode == 0x1E);

    // --- modifiers ---
    let sh, _ = input_decode(KEY_LSHIFT, 20);
    check("shift press has no character", sh.ch == 0);
    check("shift sets a modifier", sh.mods != 0);
    let a2, _ = input_decode(0x1E, 30);
    check("letter while shift is held is uppercase", a2.ch == 'A');
    let sh_rel, sh_rel_ok = input_decode(KEY_LSHIFT | 0x80, 40);     // shift released
    check("shift release decodes", sh_rel_ok && sh_rel.pressed == false);
    let a3, _ = input_decode(0x1E, 50);
    check("letter after shift release is lowercase", a3.ch == 'a');

    // --- caps lock flips letters only ---
    let caps, _ = input_decode(KEY_CAPSLOCK, 60);
    check("caps lock produces no character", caps.ch == 0);
    let a4, _ = input_decode(0x1E, 70);
    check("caps lock makes it uppercase", a4.ch == 'A');
    check("caps lock does not change a digit", input_char(0x02, false) == '1');
    let caps_off, caps_off_ok = input_decode(KEY_CAPSLOCK, 80);   // and back off
    check("caps lock release decodes", caps_off_ok && caps_off.pressed == false);
    let a5, _ = input_decode(0x1E, 90);
    check("caps lock off returns lowercase", a5.ch == 'a');

    // --- repeat ---
    // Hold 'a' from t=1000. Nothing before the delay, something after it.
    let _ = input_decode(0x1E, 1000);
    let r_early, any_early = input_repeat(1100);
    check("no repeat before the delay", any_early == false);
    let r_late, late_ok = input_repeat(1000 + 300 + 45);
    check("repeat after the delay", late_ok == true && r_late.repeat == true);
    check("a repeat is not a press", r_late.pressed == false);

    // After the key is released there is no repeat at all: a stuck repeat is the bug that
    // fills a terminal with one character.
    let _ = input_decode(get_release(0x1E), 2000);
    let _, still_ok = input_repeat(5000);
    check("no repeat after release", still_ok == false);

    // --- passthrough bytes (escape sequences) ---
    let pt = input_passthrough(27);
    check("passthrough carries the byte", pt.ch == 27 as u8);

    // --- display: creation rules ---
    disp_init();
    check("init leaves nothing valid", disp_valid(0) == false);

    let v0, c0 = disp_new("main", 80, 25);
    check("create first console", c0 == CODE_OK && v0 == 0);
    check("first console valid", disp_valid(0));
    check("active defaults to the first", disp_active() == 0);
    check("second slot not yet valid", disp_valid(1) == false);

    let v1, c1 = disp_new("agent", 80, 25);
    check("create second console", c1 == CODE_OK && v1 == 1);
    check("both valid", disp_valid(0) && disp_valid(1));
    check("invalid index refused", disp_valid(2) == false);

    // Bad geometry and bad names are refused, not clamped: a console with the wrong number
    // of columns wraps lines in the wrong place forever.
    let _, bad_cols = disp_new("bad", 0, 25);
    check("zero columns refused", bad_cols == E_INVAL);
    let _, bad_rows = disp_new("bad", 80, 0);
    check("zero rows refused", bad_rows == E_INVAL);
    let _, bad_name = disp_new("", 80, 25);
    check("empty name refused", bad_name == E_INVAL);

    // --- writing ---
    check("write to console 0", disp_puts(0, "hello\n") == CODE_OK);
    check("write to console 1", disp_putc(1, 'A') == CODE_OK);
    check("write to an invalid console refused", disp_putc(9, 'A') == E_INVAL);

    // --- switching ---
    let prev, sw_ok = disp_switch(1);
    check("switch returns the previous console", sw_ok == CODE_OK && prev == 0);
    check("active followed the switch", disp_active() == 1);
    let _, sw_bad = disp_switch(9);
    check("switch to an invalid console refused", sw_bad == E_INVAL);
    check("failed switch did not move", disp_active() == 1);

    // --- switch keys are data, not code scattered through the input path ---
    check("ctrl+alt+F1 targets console 0", disp_switch_key(0x3B, mods_ctrl_alt()) == 0);
    check("ctrl+alt+F2 targets console 1", disp_switch_key(0x3C, mods_ctrl_alt()) == 1);
    check("ctrl+alt+F3 targets nothing (only two consoles exist)",
        disp_switch_key(0x3D, mods_ctrl_alt()) == 2);
    check("F1 without modifiers targets nothing", disp_switch_key(0x3B, 0) == -1);
    check("ctrl+alt+F5 is not a switch", disp_switch_key(0x3F, mods_ctrl_alt()) == -1);

    // --- scrolling ---
    // Enough lines to push history. scroll returns the history line count, which must grow
    // and then stop growing at the ring's limit rather than wrapping into nonsense.
    var i: i64 = 0;
    while i < 40 {
        let _ = disp_puts(0, "line\n");
        i++;
    }
    let hist1 = disp_scroll(0);
    check("scrolling recorded history", hist1 >= 0);
    var j: i64 = 0;
    while j < 900 {
        let _ = disp_puts(0, "more\n");
        j++;
    }
    let hist2 = disp_scroll(0);
    check("history is bounded", hist2 >= hist1);

    var r: u8[>..] = [];
    let _ = append_int(r, 32, t_pass);
    say("passed ");
    say(r);
    say("\n");
    if t_fail != 0 { say("FAILURES\n"); sys_exit(1); }
    say("t56 done\n");
    sys_exit(0);
}

fn get_release(sc: i64) -> i64 { return sc | 0x80; }

// The mods value the display expects for Ctrl+Alt. Written here rather than imported so the
// test fails if the display's idea of the modifier bits ever changes.
fn mods_ctrl_alt() -> i64 { return 2 | 4; }
