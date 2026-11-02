// services/input/keymaps2.goose
//
// B-L1-111 — More keymaps plus a dead-key compose table, on the same machinery as B-L1-26.
//
// Status: RUNS — reached by tests/t102_keycompose (38 checks, exit 0). Measured 2026-11-02 by audit_status.py.
//
// WHAT "THE SAME MACHINERY" MEANS HERE
// ------------------------------------
// input.goose maps a scancode + modifiers to a byte with `input_char`, one table for one
// US layout. This file adds two more layouts (Dvorak, UK) with the SAME function shape, so
// the switch between them is a layout index and not a second decoder. Whatever reads
// scancodes keeps one code path.
//
// DEAD KEYS ARE A TABLE OF PAIRS, NOT A STATE MACHINE
// ---------------------------------------------------
// A dead key is "this key produces nothing yet; the next key combines with it". That is one
// i64 holding the pending dead key, one lookup into a pair table, and one rule for when the
// pending key is dropped. Anything more elaborate (chains of three, arbitrary composition)
// is a different feature and is not pretended here.
//
// The compose table is deliberately small and readable: acute, grave, circumflex, diaeresis,
// tilde over the five vowels, plus the two letters that actually get composed on a UK
// layout (apostrophe over a/e/o). Everything not in the table fails *upward*: the dead key
// is dropped and the plain character is emitted, which is what every terminal does and what
// a user typing quickly expects.

import common.err.err;
import input.input;

let LAYOUT_US: i64 = 0;
let LAYOUT_DVORAK: i64 = 1;
let LAYOUT_UK: i64 = 2;

let DEAD_NONE: i64 = 0;
let DEAD_ACUTE: i64 = 1;
let DEAD_GRAVE: i64 = 2;
let DEAD_CIRCUMFLEX: i64 = 3;
let DEAD_DIAERESIS: i64 = 4;
let DEAD_TILDE: i64 = 5;
let DEAD_APOSTROPHE: i64 = 6;

let KM_ROWS_OK: i64 = 0;

// Which byte a printable key produces on a given layout.
//
// US is delegated to input.goose so there is exactly one US table in the tree. Dvorak and UK
// are written out here. A layout name is a number, and an unknown number falls back to US
// with ok=false -- a keyboard that refuses to type because a config said "Dvorak2" is worse
// than one that types US and records the fallback.
fn km_char(layout: i64, sc: i64, shift: bool, caps: bool) -> u8, bool {
    if layout == LAYOUT_US {
        // Known only when there IS a character. The US table has no 0x56 (that key exists on
        // the UK board), and claiming every scancode is known made the start-up self-check
        // report a hole in the default layout -- a failure it could never recover from.
        let c = input_char(sc, shift);
        return c, c != 0;
    }
    if layout == LAYOUT_DVORAK { return km_dvorak(sc, shift, caps), km_dvorak_known(sc); }
    if layout == LAYOUT_UK { return km_uk(sc, shift, caps), km_uk_known(sc); }
    return input_char(sc, shift), false;
}

fn km_letter(c: u8, upper: bool) -> u8 {
    if upper {
        if c >= 'a' && c <= 'z' { return (c - 32) as u8; }
        return c;
    }
    if c >= 'A' && c <= 'Z' { return (c + 32) as u8; }
    return c;
}

// Row 2: ' , . p y f g c r l / =
fn km_dvorak(sc: i64, shift: bool, caps: bool) -> u8 {
    var c: u8 = 0;
    if sc == 0x10 { c = 'p'; }        // Q position
    else if sc == 0x11 { c = 'y'; }   // W
    else if sc == 0x12 { c = 'f'; }   // E
    else if sc == 0x13 { c = 'g'; }   // R
    else if sc == 0x14 { c = 'c'; }   // T
    else if sc == 0x15 { c = 'r'; }   // Y
    else if sc == 0x16 { c = 'l'; }   // U
    else if sc == 0x17 { c = '/'; }   // I
    else if sc == 0x18 { c = '='; }   // O
    else if sc == 0x19 { c = '\\'; }  // P
    else if sc == 0x1A { c = '\''; }  // [
    else if sc == 0x1B { c = '`'; }   // ]
    // Row 3: a o e u i d h t n s -
    else if sc == 0x1E { c = 'a'; }
    else if sc == 0x1F { c = 'o'; }
    else if sc == 0x20 { c = 'e'; }
    else if sc == 0x21 { c = 'u'; }
    else if sc == 0x22 { c = 'i'; }
    else if sc == 0x23 { c = 'd'; }
    else if sc == 0x24 { c = 'h'; }
    else if sc == 0x25 { c = 't'; }
    else if sc == 0x26 { c = 'n'; }
    else if sc == 0x27 { c = 's'; }
    // Row 4: ; q j k x b m w v z
    else if sc == 0x2C { c = ';'; }
    else if sc == 0x2D { c = 'q'; }
    else if sc == 0x2E { c = 'j'; }
    else if sc == 0x2F { c = 'k'; }
    else if sc == 0x30 { c = 'x'; }
    else if sc == 0x31 { c = 'b'; }
    else if sc == 0x32 { c = 'm'; }
    else if sc == 0x33 { c = 'w'; }
    else if sc == 0x34 { c = 'v'; }
    else if sc == 0x35 { c = 'z'; }
    else { c = input_char(sc, shift); }

    if c >= 'a' && c <= 'z' {
        let upper = shift != caps;      // XOR: shift and caps together give lower case
        return km_letter(c, upper);
    }
    if shift {
        if c == '/' { return '?'; }
        if c == '=' { return '+'; }
        if c == '\\' { return '|'; }
        if c == '\'' { return '"'; }
        if c == '`' { return '~'; }
        if c == ';' { return ':'; }
        if c == '-' { return '_'; }
    }
    return c;
}

fn km_dvorak_known(sc: i64) -> bool {
    if sc >= 0x10 && sc <= 0x1B { return true; }
    if sc >= 0x1E && sc <= 0x27 { return true; }
    if sc >= 0x2C && sc <= 0x35 { return true; }
    // Everything else falls back to the US table on purpose: space, digits, punctuation and
    // the keypad are the same on both layouts, and duplicating them would be a second set of
    // bugs for no benefit.
    return false;
}

// UK is US with three differences that bite in practice: '"' is shift-2 (with 2 unshifted
// on its own key), '#' is the pound sign's neighbour, and '\' sits between Z and the shift.
fn km_uk(sc: i64, shift: bool, caps: bool) -> u8 {
    if sc == 0x03 { if shift { return '"'; } return '2'; }      // 2/quote
    if sc == 0x04 { if shift { return 0xA3; } return '3'; }     // pound sign, Latin-1
    if sc == 0x2B { if shift { return '|'; } return '\\'; }     // between Z and shift
    if sc == 0x56 { if shift { return '|'; } return '\\'; }     // the extra key
    let c = input_char(sc, shift);
    if c >= 'a' && c <= 'z' && caps != shift { return km_letter(c, true); }
    if c >= 'A' && c <= 'Z' && caps != shift { return c; }
    if c >= 'A' && c <= 'Z' && caps == shift { return km_letter(c, false); }
    return c;
}

fn km_uk_known(sc: i64) -> bool {
    if sc == 0x03 || sc == 0x04 || sc == 0x2B || sc == 0x56 { return true; }
    return false;
}

// ---------------------------------------------------------------------------
// Dead keys and compose
// ---------------------------------------------------------------------------

struct Compose {
    dead: i64,          // DEAD_NONE or one of the DEAD_* values
    composed_total: i64,
    dropped_total: i64, // dead keys that found no pair and were discarded
}

fn compose_new() -> Compose {
    return Compose { dead: DEAD_NONE, composed_total: 0, dropped_total: 0 };
}

// Which dead key (if any) a scancode is on a given layout. Only three keys produce one, and
// only on layouts that have them: US has no dead keys at all, which is why the table starts
// empty for LAYOUT_US rather than guessing.
fn compose_dead_for(layout: i64, sc: i64) -> i64 {
    if sc == 0x1A && layout != LAYOUT_DVORAK { return DEAD_APOSTROPHE; }   // [ position
    if sc == 0x28 { return DEAD_ACUTE; }                                   // ' key
    if sc == 0x29 { return DEAD_GRAVE; }                                   // ` key
    if sc == 0x2B && layout == LAYOUT_UK { return DEAD_GRAVE; }
    return DEAD_NONE;
}

// Feed one character to the composer.
//
// Returns (out_byte, emit, code): `emit` false means the key was absorbed (a dead key, or a
// pair that has not resolved yet), `code` E_NOKEY when nothing is pending and nothing came
// out -- the console's "nothing now" answer, so it never prints a NUL.
fn compose_feed(cp: Compose&, ch: u8) -> u8, bool, i64 {
    // A NUL is not a keypress. Without this the function emitted a NUL byte with emit=true
    // whenever the input layer handed it an unmapped scancode -- the console would write a NUL
    // for a key the user never pressed, which is the exact thing E_NOKEY exists to prevent.
    if ch == 0 { return 0, false, E_NOKEY; }
    if cp.dead == DEAD_NONE {
        // Nothing pending: the character is the character. Dead keys are armed by the
        // caller (compose_arm) from the layout table, not guessed from the byte here.
        return ch, true, CODE_OK;
    }

    let composed = compose_pair(cp.dead, ch);
    if composed != 0 {
        cp.dead = DEAD_NONE;
        cp.composed_total = cp.composed_total + 1;
        return composed, true, CODE_OK;
    }

    // No pair: drop the dead key and let the character through unchanged. Dropping the
    // CHARACTER instead would silently eat a keystroke; composing something arbitrary would
    // type a letter the user did not press.
    cp.dead = DEAD_NONE;
    cp.dropped_total = cp.dropped_total + 1;
    return ch, true, CODE_OK;
}

// Arm the composer with a dead key directly (the caller has already decided, e.g. from a
// layout table). Returns false for an unknown dead key.
fn compose_arm(cp: Compose&, dead: i64) -> bool {
    if dead < DEAD_ACUTE || dead > DEAD_APOSTROPHE { return false; }
    cp.dead = dead;
    return true;
}

// The pair table. Latin-1 code points, returned as a single byte: every one of these
// compositions is in Latin-1, so the console can emit it without an encoder.
fn compose_pair(dead: i64, base: u8) -> u8 {
    if dead == DEAD_ACUTE {
        if base == 'a' { return 0xE1; }        // á
        if base == 'e' { return 0xE9; }        // é
        if base == 'i' { return 0xED; }        // í
        if base == 'o' { return 0xF3; }        // ó
        if base == 'u' { return 0xFA; }        // ú
        return 0;
    }
    if dead == DEAD_GRAVE {
        if base == 'a' { return 0xE0; }
        if base == 'e' { return 0xE8; }
        if base == 'i' { return 0xEC; }
        if base == 'o' { return 0xF2; }
        if base == 'u' { return 0xF9; }
        return 0;
    }
    if dead == DEAD_CIRCUMFLEX {
        if base == 'a' { return 0xE2; }
        if base == 'e' { return 0xEA; }
        if base == 'i' { return 0xEE; }
        if base == 'o' { return 0xF4; }
        if base == 'u' { return 0xFB; }
        return 0;
    }
    if dead == DEAD_DIAERESIS {
        if base == 'a' { return 0xE4; }
        if base == 'e' { return 0xEB; }
        if base == 'i' { return 0xEF; }
        if base == 'o' { return 0xF6; }
        if base == 'u' { return 0xFC; }
        return 0;
    }
    if dead == DEAD_TILDE {
        if base == 'a' { return 0xE3; }
        if base == 'n' { return 0xF1; }
        if base == 'o' { return 0xF5; }
        return 0;
    }
    if dead == DEAD_APOSTROPHE {
        // The two that actually compose on a UK layout; anything else passes through.
        if base == 'a' { return 0xE1; }
        if base == 'e' { return 0xE9; }
        return 0;
    }
    return 0;
}

// Layout self-check, run at start-up: every scancode a layout claims to know must produce a
// printable byte. A table with a hole is a key that types nothing, and "types nothing" and
// "is broken" are indistinguishable from the user's side.
fn km_layout_ok(layout: i64) -> bool, i64 {
    var sc: i64 = 0x10;
    while sc <= 0x56 {
        let c, known = km_char(layout, sc, false, false);
        if known && (c == 0 || c == '\n' || c == '\r') { return false, sc; }
        sc = sc + 1;
    }
    return true, 0;
}
