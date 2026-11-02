// services/display/display.goose
//
// Layer 4, service 11: virtual consoles over the single framebuffer.
//
// Status: WRITTEN (not COMPILED). Verified via goose-mcp@1.1.0: structs with
// literals (reference#32), static arrays `T[..k]`, `while`/`if`, `T&` references
// (reference#46), multi-value returns, extern fn declarations.
//
// THE PROBLEM
// -----------
// The kernel has one display. A user wants a console to type in; the boot log wants
// somewhere to go; an agent's structured view (Layer 5) wants a third. If they share
// one cursor they overwrite each other, and the person reading the log sees half a
// command prompt in the middle of it.
//
// So: N consoles, each with its own text model, one of them visible. Switching is a
// replay, not a memory copy of pixels, because the framebuffer belongs to the kernel
// and this service never touches it.
//
// WHAT IS REAL AND WHAT IS NOT
// ----------------------------
// Real: the text model -- wrapping, scrolling, cursor, per-console history, switching
// with a defined redraw.
// NOT real yet: painting. `disp_paint` emits the visible console through
// sys_write_console; a kernel that can only append at a cursor cannot address a row,
// so a repaint is only truthful once the K2 console accepts positioning (B-L1-107
// owns the escape handling). Until then this file is correct text and an
// honest about-face on drawing, which is why every call below says so.

import common.err.err;
import common.sys.sys;

let VCON_MAX: i64 = 4;
let DISPLAY_LINE_MAX: i64 = 128;        // characters per line, before wrapping
let SCROLL_MAX: i64 = 256;      // lines of history per console (beyond the screen)

struct VCon {
    used: bool,
    cols: i64,
    rows: i64,
    cx: i64,                    // cursor column, 0..cols-1
    cy: i64,                    // cursor row on screen, 0..rows-1
    screen: u8[..2048] = [0; 2048],         // rows * LINE_MAX, the visible text
    screen_used: i64,
    // History is a ring of lines already scrolled off the top. Stored as bytes plus a
    // count rather than as a ring of line records: a console scrolls by the line, and
    // a ring of bytes would have to know where lines start, which is the same
    // bookkeeping in a worse place.
    hist: u8[..32768] = [0; 32768],
    hist_start: i64,            // ring head, in bytes
    hist_used: i64,             // bytes of history held
    hist_lines: i64,            // lines in history, for the scrollback count
    name: u8[..16] = [0; 16],
}

var vcons: VCon[..4] = [VCon { .. }; 4];
var vcon_count: i64 = 0;
var active: i64 = 0;            // index into vcons, never a handle: this service owns them

// Declared here with the same signature and symbol as services/common/sys/sys.goose
// so the C shim has ONE definition per call. Not imported: the sys module is a leaf
// and importing it into a service that also exports a symbol is how link-time
// surprises start.

// ---------------------------------------------------------------------------
// Creation
// ---------------------------------------------------------------------------

fn disp_init() {
    vcon_count = 0;
    active = 0;
}

fn disp_new(name: const u8[:], cols: i64, rows: i64) -> i64, i64 {
    if vcon_count >= VCON_MAX { return -1, E_NOROOM; }
    if cols <= 0 || rows <= 0 { return -1, E_INVAL; }
    // Bound the SCREEN, which is rows x cols. This multiplied rows by the maximum line
    // width instead, so an 80x25 console was rejected for asking for 3200 cells it never
    // asked for -- only consoles 16 rows or shorter were accepted.
    if cols > DISPLAY_LINE_MAX || rows * cols > 2048 { return -1, E_INVAL; }
    if name.len == 0 || name.len >= 16 { return -1, E_INVAL; }

    let v = vcon_count;
    vcons[v].used = true;
    vcons[v].cols = cols;
    vcons[v].rows = rows;
    vcons[v].cx = 0;
    vcons[v].cy = 0;
    vcons[v].screen_used = 0;
    vcons[v].hist_start = 0;
    vcons[v].hist_used = 0;
    vcons[v].hist_lines = 0;

    var i: i64 = 0;
    while i < name.len {
        vcons[v].name[i] = name[i];
        i = i + 1;
    }
    vcons[v].name[i] = 0;

    var j: i64 = 0;
    while j < 2048 {
        vcons[v].screen[j] = 0;
        j = j + 1;
    }

    vcon_count = vcon_count + 1;
    return v, CODE_OK;
}

fn disp_valid(v: i64) -> bool {
    return v >= 0 && v < vcon_count && vcons[v].used;
}

// ---------------------------------------------------------------------------
// Writing text
// ---------------------------------------------------------------------------

// Scroll one line: the top row moves into history, everything else shifts up.
//
// A full shift over 2048 bytes per scrolled line is not fast, but it happens once per
// line of output, and the alternative (a ring of rows with a moving origin) makes
// every read in this file into index arithmetic. Correctness first; B-L1-112 can make
// it a ring if a measurement says to.
fn disp_scroll(v: i64) -> i64 {
    if !disp_valid(v) { return E_INVAL; }
    let cols = vcons[v].cols;
    let line_bytes = cols;

    // Append the top row to history, dropping the oldest line when the ring is full.
    let top = 0;
    var i: i64 = 0;
    while i < line_bytes {
        let b = vcons[v].screen[top + i];
        let pos = (vcons[v].hist_start + vcons[v].hist_used) % 32768;
        vcons[v].hist[pos] = b;
        if vcons[v].hist_used < 32768 {
            vcons[v].hist_used = vcons[v].hist_used + 1;
        } else {
            vcons[v].hist_start = (vcons[v].hist_start + 1) % 32768;
        }
        i = i + 1;
    }
    vcons[v].hist_lines = vcons[v].hist_lines + 1;
    if vcons[v].hist_lines > SCROLL_MAX { vcons[v].hist_lines = SCROLL_MAX; }

    // Shift the screen up by one row.
    var row: i64 = 1;
    while row < vcons[v].rows {
        var c: i64 = 0;
        while c < cols {
            vcons[v].screen[(row - 1) * line_bytes + c] = vcons[v].screen[row * line_bytes + c];
            c = c + 1;
        }
        row = row + 1;
    }
    // Clear the bottom row: leaving the old text there means the cursor is over
    // characters that are no longer part of the console's content.
    var c2: i64 = 0;
    while c2 < cols {
        vcons[v].screen[(vcons[v].rows - 1) * line_bytes + c2] = 0x20;
        c2 = c2 + 1;
    }
    return CODE_OK;
}

fn disp_putc(v: i64, ch: u8) -> i64 {
    if !disp_valid(v) { return E_INVAL; }
    let cols = vcons[v].cols;
    let line_bytes = cols;

    if ch == 0x0A {                                   // newline
        vcons[v].cx = 0;
        if vcons[v].cy + 1 >= vcons[v].rows {
            disp_scroll(v);
            // After scrolling the cursor stays on the last row.
            vcons[v].cy = vcons[v].rows - 1;
        } else {
            vcons[v].cy = vcons[v].cy + 1;
        }
        return CODE_OK;
    }
    if ch == 0x0D {                                   // carriage return
        vcons[v].cx = 0;
        return CODE_OK;
    }
    // Control characters other than NL/CR are not text: writing them into the screen
    // buffer would put a byte a terminal interprets (a stray ESC) into stored content.
    if ch < 0x20 { return E_INVAL; }

    if vcons[v].cx >= cols {                          // wrap
        vcons[v].cx = 0;
        if vcons[v].cy + 1 >= vcons[v].rows {
            disp_scroll(v);
            vcons[v].cy = vcons[v].rows - 1;
        } else {
            vcons[v].cy = vcons[v].cy + 1;
        }
    }
    let at = vcons[v].cy * line_bytes + vcons[v].cx;
    if at < 0 || at >= 2048 { return E_NOROOM; }
    vcons[v].screen[at] = ch;
    vcons[v].cx = vcons[v].cx + 1;
    if vcons[v].cy * line_bytes + vcons[v].cx > vcons[v].screen_used {
        vcons[v].screen_used = vcons[v].cy * line_bytes + vcons[v].cx;
    }
    return CODE_OK;
}

fn disp_puts(v: i64, s: const u8[:]) -> i64 {
    var i: i64 = 0;
    while i < s.len {
        let code = disp_putc(v, s[i]);
        if code != CODE_OK { return code; }
        i = i + 1;
    }
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// Switching and painting
// ---------------------------------------------------------------------------

fn disp_active() -> i64 {
    return active;
}

// Switch to a console. Returns the previous one so the caller can log it.
//
// The repaint is the switch: there is no hidden framebuffer to swap, so the visible
// console has to be emitted again. Doing it here, not in the caller, is what keeps
// "switching" and "drawing the new one" from being two steps somebody can forget.
fn disp_switch(v: i64) -> i64, i64 {
    if !disp_valid(v) { return -1, E_INVAL; }
    let prev = active;
    active = v;
    disp_paint(v);
    return prev, CODE_OK;
}

// Paint the active console through the console syscall, one row at a time, trailing
// spaces trimmed.
//
// This is honest about its limits: the K2 console appends at a cursor, so the first
// paint after a switch starts at whatever row the kernel is on. A true in-place
// repaint needs cursor positioning, which is B-L1-107's escape handling plus a kernel
// that honours it. Recorded as requirement A12; not pretended here.
fn disp_paint(v: i64) -> i64 {
    if !disp_valid(v) { return E_INVAL; }
    let cols = vcons[v].cols;
    var row: i64 = 0;
    while row < vcons[v].rows {
        var end = cols;
        // Trim trailing spaces so a repaint does not emit a screenful of blanks.
        while end > 0 && (vcons[v].screen[row * cols + (end - 1)] == 0x20 || vcons[v].screen[row * cols + (end - 1)] == 0) {
            end = end - 1;
        }
        if end > 0 {
            sys_write_console(vcons[v].screen[row * cols .. row * cols + end]);
            sys_write_console("\n");
        }
        row = row + 1;
    }
    return CODE_OK;
}

// A switch key as data: Ctrl+Alt+F1..F4, the convention every console on earth uses,
// so nobody has to be taught it. Returns the console to switch to, or -1.
fn disp_switch_key(scancode: i64, mods: i64) -> i64 {
    let MOD_CTRL: i64 = 2;
    let MOD_ALT: i64 = 4;
    if (mods & MOD_CTRL) == 0 || (mods & MOD_ALT) == 0 { return -1; }
    // Set-1 scancodes for F1..F4.
    if scancode == 0x3B { return 0; }
    if scancode == 0x3C { return 1; }
    if scancode == 0x3D { return 2; }
    if scancode == 0x3E { return 3; }
    return -1;
}

// ---------------------------------------------------------------------------
// Deliberately absent
// ---------------------------------------------------------------------------
//
// - No direct framebuffer writes. The framebuffer belongs to the kernel; two writers
//   would each think they owned the cursor.
// - No colours or attributes: the K2 console has none yet, and storing attributes
//   nothing can render is a promise the display cannot keep.
// - No scrollback paging (a user scrolling up). The history is kept; showing it needs
//   the same positioning that B-L1-107 unlocks, so `disp_paint` is the wrong place to
//   fake it.
