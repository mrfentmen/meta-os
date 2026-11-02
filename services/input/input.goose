// services/input/input.goose
//
// Layer 4, service 10: scancodes to key events.
//
// Status: RUNS — reached by tests/t56_input_display (49 checks, exit 0). Measured 2026-11-02 by audit_status.py. Verified via goose-mcp@1.1.0: structs with
// literals (reference#32), `while`/`if` chains, `T&` references (reference#46),
// trailing-bool/trailing-code returns, `as` casts (keyword list).
//
// THE CONTRACT UNDER THIS FILE
// ----------------------------
// The kernel's PS/2 driver (K3, kernel/src/interrupts.rs) fills a ring of raw
// scancodes. It does not know what a key is: it delivers bytes. This service turns
// bytes into events -- which key, pressed or released, with which modifiers
// applied -- and that is where the meaning lives.
//
// Scan code set 1 is assumed because that is what the K3 driver configures the
// controller for. If the kernel ever switches sets, `input_decode` is the only
// function that changes; nothing above it names a scancode.
//
// WHY THE KEYMAP IS A FUNCTION, NOT A TABLE
// -----------------------------------------
// A 128-entry table would need initialisation at start-up, which is a loop over
// another table, which is two things to keep in step. An if-chain is uglier and
// cannot drift: one place says what 0x1E means. The cost is a handful of compares
// per keypress, which is not a cost at a human typing rate.
//
// WHY REPEAT LIVES HERE
// ---------------------
// The controller can generate repeat itself, but then the delay and rate are set by
// a hardware register that a user cannot change and a test cannot drive. Doing it in
// software means repeat is data (`repeat_delay_ms`, `repeat_rate_ms`) and B-L1-111
// can add per-user settings without touching a driver.

import common.err.err;

// ---------------------------------------------------------------------------
// Modifier bits
// ---------------------------------------------------------------------------

let MOD_SHIFT: i64 = 1;
let MOD_CTRL: i64 = 2;
let MOD_ALT: i64 = 4;
let MOD_CAPS: i64 = 8;       // a latch, not a moment: stays on across events

// ---------------------------------------------------------------------------
// The event
// ---------------------------------------------------------------------------

struct KeyEvent {
    scancode: i64,      // set 1, with the release bit stripped
    ch: u8,             // 0 when the key produces no character (arrows, shift itself)
    mods: i64,          // MOD_* at the moment of the event
    pressed: bool,
    repeat: bool,       // a generated repeat, not a fresh press
}

// Keys the layer cares about by name, so no service above this one has to know that
// 0x1C is Enter. Values are the set-1 scancodes, and this list is deliberately tiny:
// it grows when something needs it, not in anticipation.
let INPUT_KEY_ESC: i64 = 0x01;
let KEY_BACKSPACE: i64 = 0x0E;
let KEY_TAB: i64 = 0x0F;
let KEY_ENTER: i64 = 0x1C;
let KEY_CTRL: i64 = 0x1D;
let KEY_LSHIFT: i64 = 0x2A;
let KEY_RSHIFT: i64 = 0x36;
let KEY_ALT: i64 = 0x38;
let KEY_SPACE: i64 = 0x39;
let KEY_CAPSLOCK: i64 = 0x3A;
let KEY_UP: i64 = 0x48;
let KEY_LEFT: i64 = 0x4B;
let KEY_RIGHT: i64 = 0x4D;
let KEY_DOWN: i64 = 0x50;

// ---------------------------------------------------------------------------
// Decoder state
// ---------------------------------------------------------------------------

struct Decoder {
    mods: i64,
    held_sc: i64,       // the key currently generating repeat, -1 if none
    held_since_ms: i64,
    next_repeat_ms: i64,
    repeat_delay_ms: i64,
    repeat_rate_ms: i64,
    dropped: i64,       // events refused because no buffer was offered
}

var dec: Decoder = Decoder {
    mods: 0,
    held_sc: 0,
    held_since_ms: 0,
    next_repeat_ms: 0,
    repeat_delay_ms: 0,
    repeat_rate_ms: 0,
    dropped: 0,
};

fn input_init(repeat_delay_ms_in: i64, repeat_rate_ms_in: i64) {
    var repeat_rate_ms = repeat_rate_ms_in;
    var repeat_delay_ms = repeat_delay_ms_in;
    dec.mods = 0;
    dec.held_sc = -1;
    dec.held_since_ms = 0;
    dec.next_repeat_ms = 0;
    // Defaults chosen from what a terminal feels like: ~500 ms before repeat, then
    // ~30 per second. Clamped rather than trusted, because a zero rate would mean a
    // tight loop and a zero delay would mean repeat from the first millisecond.
    if repeat_delay_ms < 250 { repeat_delay_ms = 250; }
    if repeat_rate_ms < 16 { repeat_rate_ms = 16; }
    dec.repeat_delay_ms = repeat_delay_ms;
    dec.repeat_rate_ms = repeat_rate_ms;
}

// ---------------------------------------------------------------------------
// Keymap: set 1 scancode + shift -> character
// ---------------------------------------------------------------------------
//
// Only the keys a console needs. An unmapped key returns 0, which is "no character",
// not an error: a modifier or an arrow reaching this function is expected.
fn input_char(sc: i64, shift: bool) -> u8 {
    if sc >= 0x02 && sc <= 0x0B {
        // 1..9, 0
        let digits = "1234567890";
        let shifted = "!@#$%^&*()";
        let i = sc - 0x02;
        if shift { return shifted[i] as u8; }
        return digits[i] as u8;
    }
    if sc == 0x0C { if shift { return 0x5F; } return 0x2D; }   // - _
    if sc == 0x0D { if shift { return 0x2B; } return 0x3D; }   // = +
    if sc == 0x1A { if shift { return 0x7B; } return 0x5B; }   // [ {
    if sc == 0x1B { if shift { return 0x7D; } return 0x5D; }   // ] }
    if sc == 0x27 { if shift { return 0x3A; } return 0x3B; }   // ; :
    if sc == 0x28 { if shift { return 0x22; } return 0x27; }   // ' "
    if sc == 0x29 { if shift { return 0x7E; } return 0x60; }   // ` ~
    if sc == 0x2B { if shift { return 0x7C; } return 0x5C; }   // \ |
    if sc == 0x33 { if shift { return 0x3C; } return 0x2C; }   // , <
    if sc == 0x34 { if shift { return 0x3E; } return 0x2E; }   // . >
    if sc == 0x35 { if shift { return 0x3F; } return 0x2F; }   // / ?
    if sc == KEY_SPACE { return 0x20; }

    // Letters: two bands, because a set-1 keyboard is not laid out alphabetically.
    if sc >= 0x10 && sc <= 0x19 {
        let row = "qwertyuiop";
        let i = sc - 0x10;
        let base = row[i] as u8;
        if shift { return base - 32; }     // ASCII lower -> upper is a 32 step
        return base;
    }
    if sc >= 0x1E && sc <= 0x26 {
        let row = "asdfghjkl";
        let i = sc - 0x1E;
        let base = row[i] as u8;
        if shift { return base - 32; }
        return base;
    }
    if sc >= 0x2C && sc <= 0x32 {
        let row = "zxcvbnm";
        let i = sc - 0x2C;
        let base = row[i] as u8;
        if shift { return base - 32; }
        return base;
    }
    return 0;
}

// Caps lock is a latch: it uppercases letters and leaves symbols alone. Applied here
// rather than by folding it into MOD_SHIFT, because a shifted number is `!` and a
// capslocked one is still `1`.
fn input_letter(sc: i64) -> bool {
    if sc >= 0x10 && sc <= 0x19 { return true; }
    if sc >= 0x1E && sc <= 0x26 { return true; }
    if sc >= 0x2C && sc <= 0x32 { return true; }
    return false;
}

// ---------------------------------------------------------------------------
// Decoding one scancode
// ---------------------------------------------------------------------------
//
// `sc` is the raw byte from the kernel ring. The high bit means release.
//
// Returns (event, got_event). A modifier press updates state and produces an event
// with ch == 0 (the console wants to know shift went down, to redraw a cursor or a
// prompt); an unknown scancode produces nothing and is not an error, because set 1
// has gaps and a keyboard may be a different layout.
fn input_decode(sc_raw: i64, now_ms: i64) -> KeyEvent, bool {
    if sc_raw < 0 || sc_raw > 255 { return KeyEvent { scancode: 0, ch: 0, mods: dec.mods, pressed: false, repeat: false }, false; }

    var pressed = true;
    var sc = sc_raw;
    if sc >= 128 {
        pressed = false;
        sc = sc - 128;
    }

    if sc == KEY_CTRL {
        if pressed { dec.mods = dec.mods | MOD_CTRL; } else { dec.mods = dec.mods & ~MOD_CTRL; }
        return KeyEvent { scancode: sc, ch: 0, mods: dec.mods, pressed: pressed, repeat: false }, true;
    }
    if sc == KEY_LSHIFT || sc == KEY_RSHIFT {
        if pressed { dec.mods = dec.mods | MOD_SHIFT; } else { dec.mods = dec.mods & ~MOD_SHIFT; }
        return KeyEvent { scancode: sc, ch: 0, mods: dec.mods, pressed: pressed, repeat: false }, true;
    }
    if sc == KEY_ALT {
        if pressed { dec.mods = dec.mods | MOD_ALT; } else { dec.mods = dec.mods & ~MOD_ALT; }
        return KeyEvent { scancode: sc, ch: 0, mods: dec.mods, pressed: pressed, repeat: false }, true;
    }
    if sc == KEY_CAPSLOCK {
        if pressed {
            if (dec.mods & MOD_CAPS) != 0 { dec.mods = dec.mods & ~MOD_CAPS; } else { dec.mods = dec.mods | MOD_CAPS; }
        }
        // The latch flips on press only: flipping on release too would leave it where
        // it started.
        return KeyEvent { scancode: sc, ch: 0, mods: dec.mods, pressed: pressed, repeat: false }, true;
    }

    let shift = (dec.mods & MOD_SHIFT) != 0;
    var shift_for_char = shift;
    if (dec.mods & MOD_CAPS) != 0 && input_letter(sc) { shift_for_char = !shift; }

    let ch = input_char(sc, shift_for_char);

    if pressed {
        dec.held_sc = sc;
        dec.held_since_ms = now_ms;
        dec.next_repeat_ms = now_ms + dec.repeat_delay_ms;
        if ch == 0 { dec.held_sc = -1; }        // an arrow does not repeat characters
    } else if sc == dec.held_sc {
        dec.held_sc = -1;
    }

    return KeyEvent { scancode: sc, ch: ch, mods: dec.mods, pressed: pressed, repeat: false }, true;
}

// ---------------------------------------------------------------------------
// Repeat
// ---------------------------------------------------------------------------
//
// Called on each console loop, not per keypress: it answers "has the held key earned
// a repeat yet?". Returns the event to deliver, or got_event = false.
//
// The held key repeats as its own last character. If the modifiers changed while it
// was held (shift pressed mid-hold), the repeat uses the NEW modifiers, because that
// is what the user is looking at.
fn input_repeat(now_ms: i64) -> KeyEvent, bool {
    if dec.held_sc < 0 { return KeyEvent { scancode: 0, ch: 0, mods: dec.mods, pressed: false, repeat: false }, false; }
    if now_ms < dec.next_repeat_ms { return KeyEvent { scancode: 0, ch: 0, mods: dec.mods, pressed: false, repeat: false }, false; }

    let shift = (dec.mods & MOD_SHIFT) != 0;
    var shift_for_char = shift;
    if (dec.mods & MOD_CAPS) != 0 && input_letter(dec.held_sc) { shift_for_char = !shift; }
    let ch = input_char(dec.held_sc, shift_for_char);

    // Advance by exactly one rate, not to `now`: a console that was blocked for 500 ms
    // must not emit ten repeats at once. It emits one and the next is due a rate later.
    dec.next_repeat_ms = dec.next_repeat_ms + dec.repeat_rate_ms;
    if dec.next_repeat_ms < now_ms { dec.next_repeat_ms = now_ms + dec.repeat_rate_ms; }

    // `pressed: false, repeat: true`. A repeat is the key staying down, not the key going
    // down: anything that counts presses (a chord, a double-tap, a mode toggle) must not
    // see one key held for a second as thirty presses.
    return KeyEvent { scancode: dec.held_sc, ch: ch, mods: dec.mods, pressed: false, repeat: true }, true;
}

// ---------------------------------------------------------------------------
// Bytes to characters, for pasted or scripted input
// ---------------------------------------------------------------------------
//
// The console also receives bytes that are not scancodes: a service feeding a script,
// or a serial line. Those are already characters, and passing them through the keymap
// would mangle them. One call, so the console has exactly one place that decides what
// a byte means.
fn input_passthrough(byte: u8) -> KeyEvent {
    return KeyEvent { scancode: 0, ch: byte, mods: dec.mods, pressed: true, repeat: false };
}
