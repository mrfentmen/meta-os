// services/console/esc.goose
//
// B-L1-107 — Console escape handling: an ANSI subset, as data.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHY THIS IS A SEPARATE FILE FROM console.goose
// ----------------------------------------------
// console.goose already sniffs escape sequences so a stray arrow key does not land in the
// line buffer. That is a *filter*. What a service needs is the other half: turn the bytes
// into a decision ("cursor to row 4, column 12", "set bold") instead of ignoring them.
//
// So this file is the data half: one small parser that yields a `Seq`, and emitters for the
// sequences we generate. console.goose can drive it without growing a second state machine.
//
// THE SUBSET, NAMED EXACTLY
// -------------------------
//   ESC [ n A          cursor up            ESC [ n B     down
//   ESC [ n C          cursor right         ESC [ n D     left
//   ESC [ r ; c H      cursor position      ESC [ r ; c f  the same (some emitters use f)
//   ESC [ n G          cursor to column     ESC [ n d     cursor to row
//   ESC [ 2 J          clear screen         ESC [ K / 1K  erase to end of line
//   ESC [ n m          SGR attributes (0,1,2,4,7,22,24,27)
//   ESC [ s / ESC [ u  save / restore cursor
//   ESC 7 / ESC 8      save / restore cursor (the pre-CSI spelling)
//
// Everything else is consumed and reported as UNKNOWN, with the bytes it consumed. An
// unknown sequence that is silently swallowed makes a program look broken on this console
// and working on another, which is the hardest kind of bug to be told about.
//
// NO SCROLLBACK, NO OSC, NO MOUSE. A console that accepts operating-system commands from a
// program is a console a program can use against the user; the ones we need are built as
// typed calls below, not as escape bytes a service may emit.

let ESC: u8 = 27;

let SEQ_NONE: i64 = 0;
let SEQ_UNKNOWN: i64 = 1;
let SEQ_CURSOR_UP: i64 = 2;
let SEQ_CURSOR_DOWN: i64 = 3;
let SEQ_CURSOR_RIGHT: i64 = 4;
let SEQ_CURSOR_LEFT: i64 = 5;
let SEQ_CURSOR_POS: i64 = 6;
let SEQ_CURSOR_COL: i64 = 7;
let SEQ_CURSOR_ROW: i64 = 8;
let SEQ_CLEAR_SCREEN: i64 = 9;
let SEQ_ERASE_LINE: i64 = 10;
let SEQ_SGR: i64 = 11;
let SEQ_SAVE_CURSOR: i64 = 12;
let SEQ_RESTORE_CURSOR: i64 = 13;

// Attribute bits. Data, not bytes: the mapping to SGR codes lives in esc_sgr_code, so a
// service sets "bold + reverse" and never spells "\x1b[1;7m".
let ATTR_BOLD: i64 = 0x01;
let ATTR_DIM: i64 = 0x02;
let ATTR_UNDERLINE: i64 = 0x04;
let ATTR_REVERSE: i64 = 0x08;

let ESC_PARAMS_MAX: i64 = 4;
let ESC_DEFAULT: i64 = -1;        // "the parameter was omitted", distinct from 0

struct Seq {
    kind: i64,
    p1: i64,                      // ESC_DEFAULT when omitted
    p2: i64,
    flags: i64,                   // for CSI J/K: the first parameter (0,1,2)
    sgr_set: i64,                 // SGR bits to turn on
    sgr_clear: i64,               // SGR bits to turn off
}

struct EscParser {
    state: i64,                   // 0 normal, 1 saw ESC, 2 saw CSI, 3 in parameters
    params: i64[..4] = [0; 4],
    nparams: i64,
    have: bool,                   // a digit has been seen for the current parameter
    last: Seq,
    consumed: i64,                // bytes eaten by the last sequence, for logging
}

fn esc_new() -> EscParser {
    var p: EscParser = EscParser {
        state: 0,
        params: [0; 4],
        nparams: 0,
        have: false,
        last: Seq { kind: 0,
        p1: 0,
        p2: 0,
        flags: 0,
        sgr_set: 0,
        sgr_clear: 0 },
        consumed: 0,
    };
    p.state = 0;
    var i: i64 = 0;
    while i < ESC_PARAMS_MAX { p.params[i] = ESC_DEFAULT; i = i + 1; }
    p.nparams = 0;
    p.have = false;
    p.consumed = 0;
    p.last = Seq { kind: SEQ_NONE, p1: ESC_DEFAULT, p2: ESC_DEFAULT, flags: 0, sgr_set: 0, sgr_clear: 0 };
    return p;
}

fn esc_last(p: EscParser&) -> Seq {
    return p.last;
}

// Feed one byte. Returns true when a complete sequence was recognised in `p.last`.
// Ordinary bytes (state 0, not ESC) return false and are the caller's to echo.
fn esc_feed(p: EscParser&, c: u8) -> bool {
    p.consumed = p.consumed + 1;

    if p.state == 0 {
        if c == ESC {
            p.state = 1;
            p.nparams = 0;
            p.have = false;
            p.consumed = 1;
            var i: i64 = 0;
            while i < ESC_PARAMS_MAX { p.params[i] = ESC_DEFAULT; i = i + 1; }
        }
        return false;
    }

    if p.state == 1 {
        if c == '[' { p.state = 2; return false; }
        if c == '7' { p.last = esc_seq(SEQ_SAVE_CURSOR); p.state = 0; return true; }
        if c == '8' { p.last = esc_seq(SEQ_RESTORE_CURSOR); p.state = 0; return true; }
        // A lone ESC followed by anything else is not a sequence we know; report it with
        // the byte, then let the byte be handled on its own -- dropping it loses input.
        p.last = esc_seq(SEQ_UNKNOWN);
        p.state = 0;
        return true;
    }

    if p.state == 2 {
        if c >= '0' && c <= '9' {
            p.state = 3;
            if p.nparams == 0 { p.nparams = 1; }
            p.params[0] = (c - '0') as i64;
            p.have = true;
            return false;
        }
        if c == 's' { p.last = esc_seq(SEQ_SAVE_CURSOR); p.state = 0; return true; }
        if c == 'u' { p.last = esc_seq(SEQ_RESTORE_CURSOR); p.state = 0; return true; }
        // A CSI with no parameters at all, e.g. ESC [ K.
        return esc_final(p, c);
    }

    // state 3: parameters, separated by ';'
    if c >= '0' && c <= '9' {
        if p.nparams == 0 { p.nparams = 1; }
        let idx = p.nparams - 1;
        var v: i64 = 0;
        if p.have { v = p.params[idx]; }
        p.params[idx] = v * 10 + ((c - '0') as i64);
        p.have = true;
        return false;
    }
    if c == ';' {
        if p.nparams < ESC_PARAMS_MAX { p.nparams = p.nparams + 1; p.params[p.nparams - 1] = ESC_DEFAULT; }
        p.have = false;
        return false;
    }
    return esc_final(p, c);
}

fn esc_final(p: EscParser&, c: u8) -> bool {
    var s = esc_seq(SEQ_NONE);
    let n = p.nparams;
    let p1 = esc_param(p, 0);
    let p2 = esc_param(p, 1);

    if c == 'A' { s.kind = SEQ_CURSOR_UP; s.p1 = p1; }
    else if c == 'B' { s.kind = SEQ_CURSOR_DOWN; s.p1 = p1; }
    else if c == 'C' { s.kind = SEQ_CURSOR_RIGHT; s.p1 = p1; }
    else if c == 'D' { s.kind = SEQ_CURSOR_LEFT; s.p1 = p1; }
    else if c == 'H' || c == 'f' { s.kind = SEQ_CURSOR_POS; s.p1 = p1; s.p2 = p2; }
    else if c == 'G' { s.kind = SEQ_CURSOR_COL; s.p1 = p1; }
    else if c == 'd' { s.kind = SEQ_CURSOR_ROW; s.p1 = p1; }
    else if c == 'J' { s.kind = SEQ_CLEAR_SCREEN; s.flags = esc_or_zero(p1); }
    else if c == 'K' { s.kind = SEQ_ERASE_LINE; s.flags = esc_or_zero(p1); }
    else if c == 'm' {
        s.kind = SEQ_SGR;
        var i: i64 = 0;
        var any = false;
        while i < n {
            let v = esc_param(p, i);
            let code = esc_or_zero(v);
            if code == 0 { s.sgr_set = 0; s.sgr_clear = ATTR_BOLD | ATTR_DIM | ATTR_UNDERLINE | ATTR_REVERSE; any = true; }
            else if code == 1 { s.sgr_set = s.sgr_set | ATTR_BOLD; any = true; }
            else if code == 2 { s.sgr_set = s.sgr_set | ATTR_DIM; any = true; }
            else if code == 4 { s.sgr_set = s.sgr_set | ATTR_UNDERLINE; any = true; }
            else if code == 7 { s.sgr_set = s.sgr_set | ATTR_REVERSE; any = true; }
            else if code == 22 { s.sgr_clear = s.sgr_clear | ATTR_BOLD | ATTR_DIM; any = true; }
            else if code == 24 { s.sgr_clear = s.sgr_clear | ATTR_UNDERLINE; any = true; }
            else if code == 27 { s.sgr_clear = s.sgr_clear | ATTR_REVERSE; any = true; }
            // Colour codes (30-37, 40-47, 90-97, 100-107) are deliberately NOT supported:
            // the framebuffer contract is monochrome until K3 says otherwise, and an
            // attribute the display cannot honour must not be reported as set.
            i = i + 1;
        }
        if !any { s.kind = SEQ_SGR; s.sgr_set = 0; }   // "ESC [ m" == reset
    } else {
        s = esc_seq(SEQ_UNKNOWN);
    }

    p.last = s;
    p.state = 0;
    return s.kind != SEQ_NONE;
}

// A defaulted parameter reads as 1 for counts and as 0 for take-no-argument sequences:
// ESC[B means "down one", ESC[J means "clear from here on".
fn esc_param(p: EscParser&, idx: i64) -> i64 {
    if idx >= p.nparams { return ESC_DEFAULT; }
    return p.params[idx];
}

fn esc_or_zero(v: i64) -> i64 {
    if v == ESC_DEFAULT { return 0; }
    return v;
}

fn esc_seq(kind: i64) -> Seq {
    return Seq { kind: kind, p1: ESC_DEFAULT, p2: ESC_DEFAULT, flags: 0, sgr_set: 0, sgr_clear: 0 };
}

// ---------------------------------------------------------------------------
// Emitters
// ---------------------------------------------------------------------------
// One function per thing we will actually do. A service that wants a new sequence adds a
// function here, where it is reviewable, rather than a literal string at the call site.

fn esc_emit(out: u8[>..]&, cap: i64, s: const u8[:]) -> bool {
    if s.len + 1 > cap { return false; }
    var i: i64 = 0;
    while i < s.len { out.push(s[i]); i = i + 1; }
    return true;
}

fn esc_put_num(out: u8[>..]&, cap: i64, v: i64) -> bool {
    var digits: i64 = 0;
    var x = v;
    if v <= 0 { if !esc_emit(out, cap, "0") { return false; } return true; }
    while x > 0 { digits = digits + 1; x = x / 10; }
    x = v;
    var i: i64 = 0;
    var buf: u8[..20] = [0; 20];
    while i < digits { buf[digits - 1 - i] = (48 + (x % 10)) as u8; x = x / 10; i = i + 1; }
    i = 0;
    while i < digits { if !esc_ch(out, cap, buf[i]) { return false; } i = i + 1; }
    return true;
}

fn esc_ch(out: u8[>..]&, cap: i64, c: u8) -> bool {
    if out.len + 1 > cap { return false; }
    out.push(c);
    return true;
}

fn esc_cursor_up(out: u8[>..]&, cap: i64, n: i64) -> bool {
    if !esc_ch(out, cap, ESC) || !esc_ch(out, cap, '[') { return false; }
    if !esc_put_num(out, cap, n) { return false; }
    return esc_ch(out, cap, 'A');
}

fn esc_cursor_down(out: u8[>..]&, cap: i64, n: i64) -> bool {
    if !esc_ch(out, cap, ESC) || !esc_ch(out, cap, '[') { return false; }
    if !esc_put_num(out, cap, n) { return false; }
    return esc_ch(out, cap, 'B');
}

// Rows and columns are 0-based on this side and 1-based on the wire: the conversion happens
// here, once, so no caller has to remember which one it is holding.
fn esc_goto(out: u8[>..]&, cap: i64, row: i64, col: i64) -> bool {
    if row < 0 || col < 0 { return false; }
    if !esc_ch(out, cap, ESC) || !esc_ch(out, cap, '[') { return false; }
    if !esc_put_num(out, cap, row + 1) { return false; }
    if !esc_ch(out, cap, ';') { return false; }
    if !esc_put_num(out, cap, col + 1) { return false; }
    return esc_ch(out, cap, 'H');
}

fn esc_clear_screen(out: u8[>..]&, cap: i64) -> bool {
    if !esc_ch(out, cap, ESC) || !esc_ch(out, cap, '[') { return false; }
    if !esc_ch(out, cap, '2') { return false; }
    return esc_ch(out, cap, 'J');
}

fn esc_erase_line(out: u8[>..]&, cap: i64) -> bool {
    if !esc_ch(out, cap, ESC) || !esc_ch(out, cap, '[') { return false; }
    return esc_ch(out, cap, 'K');
}

// Reset everything we support.
fn esc_attrs_reset(out: u8[>..]&, cap: i64) -> bool {
    if !esc_ch(out, cap, ESC) || !esc_ch(out, cap, '[') { return false; }
    if !esc_ch(out, cap, '0') { return false; }
    return esc_ch(out, cap, 'm');
}

// Set attributes from a bitfield. Unknown bits are ignored rather than rejected: the caller
// may have ORed them from a style table, and refusing the whole call would drop the leading
// attributes too.
fn esc_attrs(out: u8[>..]&, cap: i64, bits: i64) -> bool {
    if !esc_ch(out, cap, ESC) || !esc_ch(out, cap, '[') { return false; }
    var first = true;
    var i: i64 = 0;
    while i < 4 {
        let bit = esc_bit_at(i);
        let code = esc_sgr_code(i);
        if (bits & bit) != 0 && code > 0 {
            if !first { if !esc_ch(out, cap, ';') { return false; } }
            if !esc_put_num(out, cap, code) { return false; }
            first = false;
        }
        i = i + 1;
    }
    if first { if !esc_ch(out, cap, '0') { return false; } }
    return esc_ch(out, cap, 'm');
}

fn esc_bit_at(i: i64) -> i64 {
    if i == 0 { return ATTR_BOLD; }
    if i == 1 { return ATTR_DIM; }
    if i == 2 { return ATTR_UNDERLINE; }
    if i == 3 { return ATTR_REVERSE; }
    return 0;
}

fn esc_sgr_code(i: i64) -> i64 {
    if i == 0 { return 1; }        // bold
    if i == 1 { return 2; }        // dim
    if i == 2 { return 4; }        // underline
    if i == 3 { return 7; }        // reverse video
    return 0;
}
