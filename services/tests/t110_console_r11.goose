// services/tests/t110_console_r11.goose
//
// R11-037..042 — the console's limits, its refusal booleans, and the escape parser
// in console/esc.goose, driven from a host process.
//
// WHAT IS ACTUALLY CROSSED HERE
// -----------------------------
// CONSOLE_LINE_MAX is reached the only way a caller can reach it: by inserting bytes
// until insert_byte refuses. HISTORY_SLOTS is read back from the ring, not restated.
// ESC_PARAMS_MAX is crossed with a six-parameter CSI: the first two parameters must
// survive and the rest must be dropped, which is the fix that stopped a hostile
// sequence aiming the cursor anywhere by appending digits.
//
// What this does not prove: that a user typed any of it. sys_read_key on the host
// returns 0 forever (host_shim.c), so these keys are fed to the same handle_key the
// keyboard path reaches, not read from a device.
//
// Status: written for Round 11; the coordinator runs it and records the result.

import console.console;
import console.esc;
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

fn put_num(v: i64) {
    var b: u8[>..] = [];
    let _ = append_int(b, 32, v);
    say(b[..]);
}

fn bytes_eq(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

// Feed a whole string, returning true when any byte completed a sequence.
fn feed(p: EscParser&, s: const u8[:]) -> bool {
    var done = false;
    var i: i64 = 0;
    while i < s.len {
        if esc_feed(p, s[i]) { done = true; }
        i = i + 1;
    }
    return done;
}

fn main() {
    say("t110 console r11\n");

    // ======================================================================
    // 1. the limits, as data
    // ======================================================================
    check("CONSOLE_LINE_MAX is 256", CONSOLE_LINE_MAX == 256);
    check("HISTORY_SLOTS is 8", HISTORY_SLOTS == 8);
    check("the history ring's capacity follows HISTORY_SLOTS",
          history_slots() == HISTORY_SLOTS);
    check("ESC_PARAMS_MAX is 4", ESC_PARAMS_MAX == 4);

    // The entry sizes the history arena before its loop; a test that does not call the
    // entry must do the same, or the ring has no arena to write into.
    history_init();

    // ======================================================================
    // 2. the editable line, and the cap reached by insertion
    // ======================================================================
    clear_line();
    var inserts_ok: i64 = 0;
    var i: i64 = 0;
    while i < CONSOLE_LINE_MAX {
        if insert_byte(0x61) { inserts_ok = inserts_ok + 1; }
        i = i + 1;
    }
    check("insert_byte accepts CONSOLE_LINE_MAX-1 bytes",
          inserts_ok == CONSOLE_LINE_MAX - 1);
    check("the byte past the line cap is refused", !insert_byte(0x61));

    check("Enter reports a completed line", handle_key(13));
    check("the completed line is recallable", recall_last());

    // Arrow-up is ESC [ A, and it recalls rather than completing a line.
    check("a lone ESC starts a sequence and completes nothing", !handle_key(27));
    check("CSI is consumed", !handle_key(91));
    check("arrow-up recalls without completing", !handle_key(65));

    // A control byte the console does not claim is swallowed, not inserted.
    clear_line();
    check("a bare control byte is not printable", !handle_key(1));

    // ======================================================================
    // 3. the escape parser: parameters, SGR, unknown, cursor save
    // ======================================================================
    var p = esc_new();
    let _ = esc_feed(p, 27);
    let _ = esc_feed(p, 91);
    let six = feed(p, "1;2;3;4;5;6H");
    let s = esc_last(p);
    check("a six-parameter CSI still parses", six && s.kind == SEQ_CURSOR_POS);
    check("the first two parameters survive the overflow", s.p1 == 1 && s.p2 == 2);

    p = esc_new();
    let _ = esc_feed(p, 27);
    let _ = esc_feed(p, 91);
    let sgr_done = feed(p, "1;7m");
    let g = esc_last(p);
    check("SGR 1;7 sets bold and reverse",
          sgr_done && g.kind == SEQ_SGR
          && g.sgr_set == (ATTR_BOLD | ATTR_REVERSE) && g.sgr_clear == 0);

    p = esc_new();
    let _ = esc_feed(p, 27);
    let _ = esc_feed(p, 91);
    let reset_done = feed(p, "0m");
    let r = esc_last(p);
    check("SGR 0 clears every supported attribute",
          reset_done && r.kind == SEQ_SGR
          && r.sgr_clear == (ATTR_BOLD | ATTR_DIM | ATTR_UNDERLINE | ATTR_REVERSE));

    p = esc_new();
    let _ = esc_feed(p, 27);
    let _ = esc_feed(p, 91);
    let unk_done = feed(p, "99X");
    let u = esc_last(p);
    check("an unsupported CSI is reported, not swallowed",
          unk_done && u.kind == SEQ_UNKNOWN);

    p = esc_new();
    let _ = esc_feed(p, 27);
    let save_done = esc_feed(p, 55);
    let sv = esc_last(p);
    check("ESC 7 is the pre-CSI save-cursor spelling",
          save_done && sv.kind == SEQ_SAVE_CURSOR);

    // ======================================================================
    // 4. the emitters produce the bytes the parser accepts
    // ======================================================================
    var out: u8[>..] = [];
    check("esc_goto emits 1-based row and column",
          esc_goto(out, 64, 3, 11) && out.len == 7
          && out[0] == 27 && out[1] == '[' && out[2] == '4' && out[3] == ';'
          && out[4] == '1' && out[5] == '2' && out[6] == 'H');

    var a: u8[>..] = [];
    check("esc_attrs emits only the supported codes",
          esc_attrs(a, 64, ATTR_BOLD | ATTR_UNDERLINE) && a.len == 6
          && a[2] == '1' && a[3] == ';' && a[4] == '4' && a[5] == 'm');

    var r2: u8[>..] = [];
    check("esc_attrs_reset emits SGR 0",
          esc_attrs_reset(r2, 64) && r2.len == 4 && r2[2] == '0' && r2[3] == 'm');

    var up: u8[>..] = [];
    check("esc_cursor_up emits ESC [ n A",
          esc_cursor_up(up, 64, 2) && up.len == 4 && up[2] == '2' && up[3] == 'A');

    var el: u8[>..] = [];
    check("esc_erase_line emits ESC [ K",
          esc_erase_line(el, 64) && el.len == 3 && el[2] == 'K');

    // ======================================================================
    // 5. load: ten times a normal keystroke batch, across the line cap
    // ======================================================================
    clear_line();
    var ops: i64 = 0;
    var ok: i64 = 0;
    var refused: i64 = 0;
    i = 0;
    while i < 320 {
        ops = ops + 1;
        if insert_byte(0x62) { ok = ok + 1; } else { refused = refused + 1; }
        i = i + 1;
    }
    check("the load loop crossed the line cap exactly once per byte",
          ok == CONSOLE_LINE_MAX - 1 && refused == 320 - (CONSOLE_LINE_MAX - 1));

    say("LOAD console ops="); put_num(ops);
    say(" ok="); put_num(ok);
    say(" refused="); put_num(refused);
    say("\n");

    clear_line();
    say("t110 done  pass="); put_num(t_pass);
    say(" fail="); put_num(t_fail);
    say("\n");
    if t_fail > 0 { sys_exit(1); }
}
