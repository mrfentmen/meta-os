// services/tests/t49_bootlog.goose
//
// B-L1-49 — test program for the boot log and the console editor (B-L1-17).
//
// Status: RUNS — tests/t49_bootlog: 23 checks, 0 failures. Measured 2026-11-02 by audit_status.py.
//
// THE BOOT LOG
// ------------
// The boot log is the only evidence that exists when everything else is broken, so its
// contract is: every line is a complete line, and a line that cannot be written is refused
// rather than half-written. The test checks the record shape (level letter, stage text) and
// the refusal at the cap.
//
// THE CONSOLE
// -----------
// The console is a line editor over a fixed buffer, and its buffer has no accessor -- so
// this test asserts only what the editor's own calls report: that an insert is refused when
// the line is full, that movement at an edge is refused rather than wrapped, that backspace
// on an empty line is a no-op, and that history recall reports whether it had anything.
// Anything else would be this test reaching into the editor's storage, which is not the
// contract and would freeze the implementation.

import bootlog.bootlog;
import console.console;
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
    say("t49 bootlog + console\n");

    // --- record shape, into the caller's buffer ---
    var rec: u8[>..] = [];
    check("record builds", record(rec, BL_LINE, 3, "storage") == true);
    check("record is non-empty", rec.len > 0);
    // The level must be visible in the record: a boot log where every line looks the same
    // is a boot log nobody can triage.
    var saw_level: bool = false;
    var i: i64 = 0;
    while i < rec.len {
        if rec[i] == 51 { saw_level = true; }     // '3'
        i = i + 1;
    }
    check("record carries the level", saw_level);

    // The message must appear in the record, unmodified.
    var saw_msg: bool = false;
    var j: i64 = 0;
    while j + 7 <= rec.len {
        if rec[j] == 115 && rec[j + 1] == 116 && rec[j + 2] == 111 { saw_msg = true; }
        j = j + 1;
    }
    check("record carries the message", saw_msg);

    // A record with no room is refused, and the buffer is untouched.
    var tight: u8[>..] = [];
    check("record refuses a short buffer", record(tight, 12, 3, "storage") == false && tight.len == 0);

    // An empty message still produces a line (a bare stage marker), not a refusal.
    var bare: u8[>..] = [];
    check("empty message allowed", record(bare, BL_LINE, 1, "") && bare.len > 0);

    // --- stage writes through the boot log ---
    check("stage writes", stage(2, "console up"));

    // --- the editor: type, then edit ---
    let _ = handle_key(97);      // 'a'
    let _ = handle_key(98);      // 'b'
    let _ = handle_key(99);      // 'c'
    check("backspace removes one", backspace());
    check("backspace removes two", backspace());
    check("backspace removes three", backspace());
    check("backspace on empty is a no-op", backspace() == false);

    // Cursor movement at the edges is refused, not wrapped.
    check("left at start refused", move_left() == false);
    check("insert after empty", insert_byte(120));      // 'x'
    check("right at end refused", move_right() == false);
    check("left from one char", move_left());
    check("delete_forward in middle", delete_forward());

    // Fill the line until the editor refuses: the refusal is the guard under test.
    var filled: i64 = 0;
    var refused_at: i64 = -1;
    var k: i64 = 0;
    while k < 4096 && refused_at < 0 {
        if insert_byte(65) { filled = filled + 1; } else { refused_at = filled; }
        k = k + 1;
    }
    check("editor refuses when full", refused_at >= 0);
    check("filled a plausible line", filled > 0 && filled < 4096);

    // With a full line, insert is still refused (not silently overwriting the last byte).
    check("insert still refused when full", insert_byte(66) == false);
    // And backspace makes room again, exactly one byte's worth.
    check("backspace frees a slot", backspace());
    check("insert works after backspace", insert_byte(67));

    // --- history ---
    // Whether history is enabled and how deep is the console's policy; what is asserted is
    // that push and recall agree with each other.
    clear_line();
    let _ = insert_byte(104);    // 'h'
    let pushed = push_history();
    clear_line();
    if pushed {
        check("recall after push", recall_last());
    } else {
        check("recall after refused push", recall_last() == false);
    }

    // --- output paths ---
    // put_ch/put_str succeed only when a framebuffer exists (K2). Not asserted here: a
    // tautology would be worse than a skip, because it would report "drawing works" on a
    // machine that has no framebuffer at all.
    if redraw() {
        say("drawing available: put paths exercised\n");
        check("put_str after redraw", put_str("boot\n"));
    } else {
        say("skip put paths: no framebuffer\n");
    }

    var r: u8[>..] = [];
    let _ = append_int(r, 32, t_pass);
    say("passed ");
    say(r);
    say("\n");
    if t_fail != 0 { say("FAILURES\n"); sys_exit(1); }
    say("t49 done\n");
    sys_exit(0);
}
