// services/tests/t102_keycompose.goose
//
// The dead-key composer and the layout self-check (input/keymaps2).
//
// WHY THIS FILE EXISTS
// --------------------
// The census listed `compose_new`, `compose_dead_for`, `compose_feed` and `km_layout_ok` as
// functions nothing calls. A dead-key composer is small enough to look obviously correct and
// wrong in exactly one place: what happens when the second key has no pair. Dropping the
// *character* eats a keystroke silently; composing an arbitrary letter types something the user
// did not press. The only correct answer is to drop the dead key and pass the character through,
// and that is the case driven hardest below.
//
// `km_layout_ok` is the start-up self-check: a layout table with a hole is a key that types
// nothing, and from the user's side "types nothing" and "is broken" look the same. The driver
// runs it for every layout so a hole added later fails a test instead of shipping.
//
// Status: RUNS — set by `audit_status.py` from the runner's row, not by hand.

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

fn main() {
    say("t102 key compose\n");

    // ======================================================================
    // 1. a new composer has nothing pending
    // ======================================================================
    var cp = compose_new();
    check("compose_new: no dead key armed", cp.dead == DEAD_NONE);
    check("compose_new: no counts", cp.composed_total == 0 && cp.dropped_total == 0);

    // ======================================================================
    // 2. which keys are dead on which layout
    // ======================================================================
    check("compose_dead_for: the ' key is acute on every layout",
          compose_dead_for(LAYOUT_US, 0x28) == DEAD_ACUTE
          && compose_dead_for(LAYOUT_UK, 0x28) == DEAD_ACUTE
          && compose_dead_for(LAYOUT_DVORAK, 0x28) == DEAD_ACUTE);
    check("compose_dead_for: the ` key is grave",
          compose_dead_for(LAYOUT_US, 0x29) == DEAD_GRAVE);
    check("compose_dead_for: the [ position is apostrophe on US-style layouts only",
          compose_dead_for(LAYOUT_US, 0x1A) == DEAD_APOSTROPHE
          && compose_dead_for(LAYOUT_UK, 0x1A) == DEAD_APOSTROPHE
          && compose_dead_for(LAYOUT_DVORAK, 0x1A) == DEAD_NONE);
    check("compose_dead_for: backslash is grave on UK only",
          compose_dead_for(LAYOUT_UK, 0x2B) == DEAD_GRAVE
          && compose_dead_for(LAYOUT_US, 0x2B) == DEAD_NONE);
    check("compose_dead_for: an ordinary key is not dead",
          compose_dead_for(LAYOUT_US, 0x1E) == DEAD_NONE);   // 'a'

    // ======================================================================
    // 3. nothing armed: the character is the character
    // ======================================================================
    let c0, e0, r0 = compose_feed(cp, 'a');
    check("compose_feed: with nothing armed the key passes through",
          c0 == 'a' && e0 && r0 == CODE_OK);

    // A NUL is not a key. Emitting it would make the console print a NUL byte, which is the
    // exact thing the documented E_NOKEY answer exists to prevent.
    let c1, e1, r1 = compose_feed(cp, 0);
    check("compose_feed: a NUL key emits nothing", !e1 && r1 == E_NOKEY && c1 == 0);

    // ======================================================================
    // 4. a pair composes, and the dead key is spent
    // ======================================================================
    check("compose_arm: acute is a real dead key", compose_arm(cp, DEAD_ACUTE));
    let ca, ea, ra = compose_feed(cp, 'a');
    check("compose_feed: acute + a is a-acute", ca == 0xE1 && ea && ra == CODE_OK);
    check("compose_feed: the dead key is spent", cp.dead == DEAD_NONE);
    check("compose_feed: the composition is counted", cp.composed_total == 1);

    // A second character right after is itself: the composer does not stay in a mode.
    let cb, eb, _ = compose_feed(cp, 'b');
    check("compose_feed: the next key is plain", cb == 'b' && eb);

    // ======================================================================
    // 5. no pair: the dead key dies, the character lives
    // ======================================================================
    check("compose_arm: grave", compose_arm(cp, DEAD_GRAVE));
    let cx, ex, rx = compose_feed(cp, 'x');
    check("compose_feed: an unmatched pair passes the character through",
          cx == 'x' && ex && rx == CODE_OK);
    check("compose_feed: the dead key was dropped, not kept", cp.dead == DEAD_NONE);
    check("compose_feed: the drop is counted", cp.dropped_total == 1);
    check("compose_feed: a drop is not a composition", cp.composed_total == 1);

    // Arming twice replaces rather than stacks: there is one dead key at a time.
    check("compose_arm: arming again replaces", compose_arm(cp, DEAD_TILDE));
    check("compose_arm: arming circumflex replaces the tilde", compose_arm(cp, DEAD_CIRCUMFLEX));
    let ce, ee, _ = compose_feed(cp, 'e');
    check("compose_feed: circumflex + e is e-circumflex", ce == 0xEA && ee);

    check("compose_arm: an unknown dead key is refused", !compose_arm(cp, 99));
    check("compose_arm: a refused arm changes nothing", cp.dead == DEAD_NONE);

    // ======================================================================
    // 6. the pair table, one row at a time
    // ======================================================================
    check("compose_pair: acute", compose_pair(DEAD_ACUTE, 'o') == 0xF3
          && compose_pair(DEAD_ACUTE, 'u') == 0xFA);
    check("compose_pair: grave", compose_pair(DEAD_GRAVE, 'a') == 0xE0
          && compose_pair(DEAD_GRAVE, 'i') == 0xEC);
    check("compose_pair: circumflex", compose_pair(DEAD_CIRCUMFLEX, 'o') == 0xF4
          && compose_pair(DEAD_CIRCUMFLEX, 'i') == 0xEE);
    check("compose_pair: diaeresis", compose_pair(DEAD_DIAERESIS, 'u') == 0xFC
          && compose_pair(DEAD_DIAERESIS, 'a') == 0xE4);
    check("compose_pair: tilde, including n", compose_pair(DEAD_TILDE, 'n') == 0xF1
          && compose_pair(DEAD_TILDE, 'o') == 0xF5);
    check("compose_pair: apostrophe composes only the two UK pairs",
          compose_pair(DEAD_APOSTROPHE, 'a') == 0xE1
          && compose_pair(DEAD_APOSTROPHE, 'e') == 0xE9
          && compose_pair(DEAD_APOSTROPHE, 'o') == 0);
    check("compose_pair: no pair is zero, never a guess",
          compose_pair(DEAD_ACUTE, 'z') == 0 && compose_pair(DEAD_TILDE, 'p') == 0);
    check("compose_pair: an unknown dead key composes nothing", compose_pair(99, 'a') == 0);

    // ======================================================================
    // 7. the layout self-check
    // ======================================================================
    let us_ok, us_bad = km_layout_ok(LAYOUT_US);
    check("km_layout_ok: the US layout has no holes", us_ok && us_bad == 0);
    let uk_ok, uk_bad = km_layout_ok(LAYOUT_UK);
    check("km_layout_ok: the UK layout has no holes", uk_ok && uk_bad == 0);
    let dv_ok, dv_bad = km_layout_ok(LAYOUT_DVORAK);
    check("km_layout_ok: the Dvorak layout has no holes", dv_ok && dv_bad == 0);

    // The self-check is what turns a hole into a reported scancode, so the walk has to cover
    // the whole range a layout claims: the first key it checks is 0x10 and the last is 0x56.
    let first, first_known = km_char(LAYOUT_US, 0x10, false, false);
    check("km_char: the first checked scancode is a known key", first_known && first != 0);
    // 0x56 is the extra key between Z and shift on the UK board. The US table does not have
    // it, and saying it does is what made the US self-check fail.
    let last, last_known = km_char(LAYOUT_US, 0x56, false, false);
    check("km_char: the UK-only key is not in the US table", !last_known);
    let lastuk, lastuk_known = km_char(LAYOUT_UK, 0x56, false, false);
    check("km_char: the UK table has the extra key", lastuk_known && lastuk != 0);

    say("t102 done  pass=");
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
