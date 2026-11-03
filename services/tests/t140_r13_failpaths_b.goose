// services/tests/t140_r13_failpaths_b.goose
//
// Round 13, Section B — the two requested failure inputs that actually exist as code
// surfaces: an empty string into the display, and a second input_init on a live decoder.
//
// Neither is a refusal. The test records what the code really does:
//   - `disp_puts(v, "")` is a no-op that returns CODE_OK;
//   - `input_init` can be called twice and the second call resets modifiers and hold state.
//
// The other Section B conditions have no input surface in their service; their records
// say so and file a gap rather than inventing a call.

import display.display;
import input.input;
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
    say("t140 r13 failure inputs b\n");

    // --- R13-034: display empty input ---
    disp_init();
    let v, vc = disp_new("t", 40, 10);
    check("display console created", vc == CODE_OK && v == 0);
    check("empty puts returns CODE_OK", disp_puts(v, "") == CODE_OK);
    check("empty puts leaves history empty", disp_hist_lines(v) == 0);
    check("empty puts leaves the console valid", disp_valid(v));
    check("empty puts leaves the cursor at home", disp_active() == 0);

    // --- R13-040: input duplicate start ---
    input_init(500, 30);
    let a1, ok1 = input_decode(0x1E, 1000);
    check("first init decodes a", ok1 && a1.ch == 0x61 && a1.mods == 0);

    input_init(500, 30);
    let a2, ok2 = input_decode(0x1E, 2000);
    check("second init still decodes a", ok2 && a2.ch == 0x61 && a2.mods == 0);

    // A held shift before the second init must not survive it.
    input_init(500, 30);
    let _, sh = input_decode(0x2A, 100);      // shift press, no character
    let up, up_ok = input_decode(0x1E, 200);  // 'A'
    check("shift applies before the reset", up_ok && up.ch == 0x41);

    input_init(500, 30);
    let fresh, fresh_ok = input_decode(0x1E, 300);
    check("second init clears the held modifier", fresh_ok && fresh.ch == 0x61 && fresh.mods == 0);

    say("t140 done  pass=");
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
