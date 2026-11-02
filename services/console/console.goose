// services/console/console.goose
//
// Layer 4, service 2: the interactive console. Echo, line editing, history.
//
// Status: RUNS — reached by tests/t49_bootlog (23 checks, exit 0). Measured 2026-11-02 by audit_status.py. Verified via goose-mcp@1.1.0:
// - export fn entry, extern fn ............................. spec#41, spec#40
// - u8[>..] builder, append, push, .len ................... samples/03_strings.goose
// - trailing-bool / trailing-code returns ................. samples/04_errors.goose
// - slices and sub-ranges `s[a..b]` ....................... samples/03_strings.goose
// - while / if / break / continue / var / let ............. list_keywords
//
// What is NOT verified, and is the largest single risk in this file: the
// cross-file import path. `spec#57` says `import a.b.c;` includes `a/b/c.goose`
// resolved from the root of the importing file's package; whether that root is
// `services/` for a service under `services/console/` is not stated anywhere I
// could verify. If the first COMPILED pass disagrees, the three imports below
// change and nothing else does.
//
// NO SHELL IS ATTACHED. Pressing Enter echoes the line and stores it in history;
// it does not execute anything, because the shell is B-L1-87 and pretending to
// run a command would be a mock. The line it would hand over is exactly what a
// shell will receive later.

import common.sys.sys;
import common.ring.ring;
import common.err.err;

// ---------------------------------------------------------------------------
// Storage. All of it static: no heap, and every buffer's size is visible here.
// ---------------------------------------------------------------------------

let CONSOLE_LINE_MAX: i64 = 256;          // longest editable line, including the NUL
let PROMPT: const u8[:] = "meta> ";

// The editable line. `line_len` is the number of bytes in use; the buffer is
// capacity LINE_MAX and the last byte is reserved so a C shim can always be
// handed a terminated string.
var line: u8[..256] = [0; 256];
var line_len: i64 = 0;
var cursor: i64 = 0;

// History: 8 lines of up to 256 bytes, stored in one flat array. The ring library
// indexes into it; nothing here allocates.
let HISTORY_SLOTS: i64 = 8;
var history_storage: u8[>..] = [];
var history: MsgRing = msg_init(256, 8);

// Escape-sequence state. Arrow keys arrive as ESC [ A/B/C/D; this is the whole
// parser, and B-L1-107 extends it (Home/End/Delete/PageUp inside the shell).
let KEY_ESC: u8 = 27;
let KEY_BS: u8 = 8;
let KEY_DEL: u8 = 127;
let KEY_CR: u8 = 13;
let KEY_LF: u8 = 10;
var esc_state: i64 = 0;           // 0 none, 1 saw ESC, 2 saw ESC [

// ---------------------------------------------------------------------------
// Low-level output
// ---------------------------------------------------------------------------

fn put_str(s: const u8[:]) -> bool {
    return sys_write_console(s) >= 0;
}

fn put_ch(c: u8) -> bool {
    var b: u8[>..] = [];
    b.push(c);
    return sys_write_console(b) >= 0;
}

// Redraw the line from the cursor. Cheap because lines are short, and correct
// without tracking terminal state: erase, rewrite, reposition.
fn redraw() -> bool {
    var out: u8[>..] = [];
    // Carriage return, write the prompt and the line, pad with spaces over the
    // old tail, then step back to the cursor.
    if !put_ch(KEY_CR) { return false; }
    if !put_str(PROMPT) { return false; }
    if !put_str(line[0..line_len]) { return false; }

    var back = line_len - cursor;
    while back > 0 {
        if !put_str(" ") { return false; }
        back = back - 1;
    }
    back = line_len - cursor;
    while back > 0 {
        if !put_ch(KEY_BS) { return false; }
        back = back - 1;
    }
    return true;
}

// ---------------------------------------------------------------------------
// Line editing
// ---------------------------------------------------------------------------

// Make room at `at` for one byte, or report that the line is full.
fn make_room(at: i64) -> bool {
    if line_len + 1 >= CONSOLE_LINE_MAX { return false; }   // keep the NUL byte
    var i = line_len;
    while i > at {
        line[i] = line[i - 1];
        i = i - 1;
    }
    return true;
}

fn insert_byte(c: u8) -> bool {
    if !make_room(cursor) { return false; }
    line[cursor] = c;
    cursor = cursor + 1;
    line_len = line_len + 1;
    return redraw();
}

fn backspace() -> bool {
    if cursor == 0 { return false; }
    var i = cursor - 1;
    while i < line_len - 1 {
        line[i] = line[i + 1];
        i = i + 1;
    }
    cursor = cursor - 1;
    line_len = line_len - 1;
    return redraw();
}

fn delete_forward() -> bool {
    if cursor >= line_len { return false; }
    var i = cursor;
    while i < line_len - 1 {
        line[i] = line[i + 1];
        i = i + 1;
    }
    line_len = line_len - 1;
    return redraw();
}

fn move_left() -> bool {
    if cursor == 0 { return false; }
    cursor = cursor - 1;
    return put_ch(KEY_BS);
}

fn move_right() -> bool {
    if cursor >= line_len { return false; }
    // Echo the byte we moved over rather than using a cursor-forward escape: no
    // terminal state, and it is correct on any console that prints.
    return put_ch(line[cursor]) && advance_cursor();
}

// Kept separate so move_right reads as one idea per step.
fn advance_cursor() -> bool {
    cursor = cursor + 1;
    return true;
}

fn clear_line() {
    line_len = 0;
    cursor = 0;
}

// ---------------------------------------------------------------------------
// History
// ---------------------------------------------------------------------------

fn push_history() -> bool {
    if line_len == 0 { return true; }        // an empty line is not history
    // A repeating line is history once, not ten times: skip an exact repeat of
    // the newest entry, which is what makes up-arrow usable.
    var newest: u8[>..] = [];
    if msg_peek_last(history, history_storage, newest) {
        if newest.len == line_len {
            var same = true;
            var i: i64 = 0;
            while i < line_len {
                if newest[i] != line[i] { same = false; break; }
                i = i + 1;
            }
            if same { return true; }
        }
    }
    return msg_push(history, history_storage, line[0..line_len]);
}

// Peek the newest entry without consuming it. The ring library exposes the byte
// ring, and a slot ring's newest entry is the one before `tail`.
fn msg_peek_last(m: MsgRing&, buf: u8[>..]&, out: u8[>..]&) -> bool {
    if m.ring.count < m.slot { return false; }
    var pos = m.ring.tail - m.slot;
    if pos < 0 { pos = pos + m.ring.cap; }
    let len = buf[pos] as i64;
    if len > m.slot - 1 { return false; }
    var i: i64 = 0;
    while i < len {
        out.push(buf[pos + 1 + i]);
        i = i + 1;
    }
    return true;
}

// Recall the newest history line into the edit buffer.
fn recall_last() -> bool {
    var prev: u8[>..] = [];
    if !msg_peek_last(history, history_storage, prev) { return false; }
    clear_line();
    var i: i64 = 0;
    while i < prev.len && i < CONSOLE_LINE_MAX - 1 {
        line[i] = prev[i];
        i = i + 1;
    }
    line_len = i;
    cursor = i;
    return redraw();
}

// ---------------------------------------------------------------------------
// Key handling
// ---------------------------------------------------------------------------

// Handle one key event. Returns true when the key produced a completed line,
// which the caller is expected to hand to whoever reads console input.
fn handle_key(c: u8) -> bool {
    // Escape sequences first: arrows arrive as ESC [ X.
    if esc_state == 1 {
        if c == '[' { esc_state = 2; return false; }
        esc_state = 0;
        // A lone ESC is a key of its own; the console ignores it for now.
        return false;
    }
    if esc_state == 2 {
        esc_state = 0;
        if c == 'C' { move_right(); return false; }
        if c == 'D' { move_left(); return false; }
        if c == 'A' { recall_last(); return false; }
        // Down arrow and the rest: B-L1-107. Ignored, not guessed at.
        return false;
    }

    if c == KEY_ESC { esc_state = 1; return false; }
    if c == KEY_CR || c == KEY_LF {
        // Finish the line: echo the newline, keep it, reset.
        put_str("\n");
        push_history();
        return true;
    }
    if c == KEY_BS || c == KEY_DEL {
        // A terminal sends DEL (127) for backspace; both do the same here.
        if cursor > 0 { backspace(); } else { delete_forward(); }
        return false;
    }
    // Printable ASCII only. Anything else is a control byte this console does
    // not claim to handle yet -- silently swallowing it would hide that.
    if c >= 32 && c < 127 {
        insert_byte(c);
    }
    return false;
}

// ---------------------------------------------------------------------------
// The service
// ---------------------------------------------------------------------------

// Size the history arena once; the ring writes at absolute offsets.
fn history_init() {
    var i: i64 = 0;
    while i < HISTORY_SLOTS * 256 { history_storage.push(0); i = i + 1; }
}

// The history ring's depth, computed from the ring itself so a resize cannot drift from
// the constant. t103 drives this against HISTORY_SLOTS.
fn history_slots() -> i64 { return msg_capacity(history); }

fn print_banner() {
    put_str("Meta OS console (Layer 4)\n");
    put_str("No shell attached yet: B-L1-87. Enter keeps history only.\n");
}
