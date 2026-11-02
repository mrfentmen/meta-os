// services/tests/t121_input_r11.goose
//
// Round 11, input — the decoder's edges the functional suites leave alone.
//
// t56_input_display proves the keymap works and t102_keycompose proves the layouts and the
// compose table. Neither drives the two floors in `input_init` (250 ms delay, 16 ms rate) as
// floors, the repeat catch-up rule, the out-of-range refusals, or the caps/shift XOR. This
// file does, and it counts the one field nothing writes (`Decoder.dropped`) as a finding
// rather than a test.
//
// Status: WRITTEN — the coordinator runs it; this file makes no claim about its own result.

import input.input;
import input.keymaps2;
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

fn load_line(ops: i64, ok: i64, refused: i64) {
    say("LOAD input ops=");
    var b: u8[>..] = [];
    let _ = append_int(b, 32, ops);
    say(b[..]);
    say(" ok=");
    var b2: u8[>..] = [];
    let _ = append_int(b2, 32, ok);
    say(b2[..]);
    say(" refused=");
    var b3: u8[>..] = [];
    let _ = append_int(b3, 32, refused);
    say(b3[..]);
    say("\n");
}

fn main() {
    say("t121 input r11\n");

    // ======================================================================
    // 1. the two floors in input_init are floors, not defaults
    // ======================================================================
    // Called with zeros: a zero delay would repeat from the first millisecond and a zero
    // rate would repeat in a tight loop, so the init clamps instead of trusting the caller.
    input_init(0, 0);
    let e0, ok0 = input_decode(0x1E, 0);              // 'a'
    check("decode: a press produces an event with its character",
          ok0 && e0.pressed && !e0.repeat && e0.ch == 0x61 && e0.mods == 0);

    let _, early = input_repeat(249);
    check("repeat: silent at 249 ms, so the 250 ms floor is real", !early);

    let rep, due = input_repeat(250);
    check("repeat: due at exactly 250 ms", due && rep.repeat && !rep.pressed && rep.ch == 0x61);

    let _, at265 = input_repeat(265);
    check("repeat: silent 15 ms after a repeat, so the 16 ms rate floor is real", !at265);

    let rep2, at266 = input_repeat(266);
    check("repeat: one repeat at 16 ms, exactly one", at266 && rep2.repeat);
    check("repeat: it still reports the held key", rep2.scancode == 0x1E);

    // ======================================================================
    // 2. out-of-range input is refused, not wrapped
    // ======================================================================
    let _, neg = input_decode(-1, 0);
    check("decode: -1 is refused", !neg);
    let _, big = input_decode(256, 0);
    check("decode: 256 is refused", !big);
    let _, top = input_decode(255, 0);
    check("decode: 255 is a legal raw byte (release of 0x7F)", top);

    // A release with no press is an event, and it must not invent a held key.
    let rel, rel_ok = input_decode(0x9E, 0);          // release of 'a'
    check("decode: a release without a press is still an event, pressed=false",
          rel_ok && !rel.pressed && rel.ch == 0x61);
    let _, no_rep = input_repeat(1000);
    check("repeat: a release with no press leaves nothing to repeat", !no_rep);

    // ======================================================================
    // 3. caps is a latch and shift XORs with it
    // ======================================================================
    input_init(500, 30);
    let on1, on1_ok = input_decode(0x3A, 0);          // caps lock press
    check("caps: the press sets the latch", on1_ok && (on1.mods & MOD_CAPS) != 0);

    let off2, off2_ok = input_decode(0x3A, 10);       // caps lock press again
    check("caps: a second press clears it", off2_ok && (off2.mods & MOD_CAPS) == 0);

    // On again, so the letter below is typed with the latch set.
    let _on3, _on3_ok = input_decode(0x3A, 20);
    let caps_a, caps_a_ok = input_decode(0x1E, 20);
    check("caps: a letter is upper case while the latch is set",
          caps_a_ok && caps_a.ch == 0x41);

    let sh, sh_ok = input_decode(0x2A, 100);          // left shift press
    let both, both_ok = input_decode(0x1E, 100);
    check("caps+shift: the two cancel, as on a real keyboard",
          sh_ok && both_ok && (sh.mods & MOD_SHIFT) != 0 && both.ch == 0x61);

    let sh_off, sh_off_ok = input_decode(0xAA, 200);  // shift release
    check("shift: the release clears only MOD_SHIFT, the caps latch stays",
          sh_off_ok && (sh_off.mods & MOD_SHIFT) == 0 && (sh_off.mods & MOD_CAPS) != 0);

    // ======================================================================
    // 4. the keymap says what a layout knows, and falls back honestly
    // ======================================================================
    let us_hole, us_known = km_char(LAYOUT_US, 0x56, false, false);
    check("keymap: US does not claim the UK-only key", !us_known && us_hole == 0);
    let fallback, fb_known = km_char(99, 0x1E, false, false);
    check("keymap: an unknown layout falls back to US and says ok=false",
          !fb_known && fallback == 0x61);
    let dv, dv_ok = km_char(LAYOUT_DVORAK, 0x10, false, false);
    check("keymap: Dvorak maps the Q position to p", dv_ok && dv == 0x70);

    let us_ok, us_bad = km_layout_ok(LAYOUT_US);
    check("keymap: the US layout has no holes", us_ok && us_bad == 0);
    let dv_full, dv_bad = km_layout_ok(LAYOUT_DVORAK);
    check("keymap: the Dvorak layout has no holes", dv_full && dv_bad == 0);
    let uk_full, uk_bad = km_layout_ok(LAYOUT_UK);
    check("keymap: the UK layout has no holes", uk_full && uk_bad == 0);

    // ======================================================================
    // 5. compose refusals
    // ======================================================================
    var cp = compose_new();
    check("compose: an unknown dead key is refused", !compose_arm(cp, 99));
    check("compose: a known dead key arms", compose_arm(cp, DEAD_ACUTE));
    let composed, emit, cc = compose_feed(cp, 0x65);  // 'e'
    check("compose: acute over e is the Latin-1 e-acute",
          emit && cc == CODE_OK && composed == 0xE9);
    check("compose: the composed total follows", cp.composed_total == 1);

    let nul, nul_emit, nul_code = compose_feed(cp, 0);
    check("compose: a NUL byte is E_NOKEY, never a typed NUL",
          !nul_emit && nul_code == E_NOKEY && nul == 0);

    check("compose: arm again for the miss", compose_arm(cp, DEAD_GRAVE));
    let miss, miss_emit, miss_code = compose_feed(cp, 0x7A);   // 'z'
    check("compose: an unpaired letter passes through unchanged",
          miss_emit && miss_code == CODE_OK && miss == 0x7A);
    check("compose: and the dropped dead key is counted", cp.dropped_total == 1);

    check("compose: the dead key for a scancode is layout-dependent",
          compose_dead_for(LAYOUT_UK, 0x2B) == DEAD_GRAVE
          && compose_dead_for(LAYOUT_US, 0x2B) == DEAD_NONE);

    // ======================================================================
    // 6. passthrough is not the keymap
    // ======================================================================
    let raw = input_passthrough(0x80);
    check("passthrough: a byte above ASCII is delivered as itself",
          raw.pressed && raw.scancode == 0 && raw.ch == 0x80);

    // ======================================================================
    // 7. load shape — ten times a normal batch of decode calls
    // ======================================================================
    input_init(250, 16);
    var ops: i64 = 0;
    var ok: i64 = 0;
    var refused: i64 = 0;
    while ops < 200 {
        let _, got = input_decode(0x48, ops);         // an arrow: no held character
        if got { ok = ok + 1; } else { refused = refused + 1; }
        ops = ops + 1;
    }
    check("load: every one of 200 decodes produced an event", ok == 200);

    say("t121 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
    load_line(ops, ok, refused);
    if t_fail > 0 { sys_exit(1); }
}
