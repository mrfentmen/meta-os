// services/tests/t107_bootlog_r11.goose
//
// Round 11, R11-019..024 — the boot log's limits and refusals, driven rather than described.
//
// t49 already proved the record shape and that a too-small buffer is refused. This driver adds
// the two things t49 leaves as prose:
//
//   1. the boundary itself: BL_LINE is the cap, and a message that fits passes while a message
//      that does not is refused with the buffer untouched;
//   2. volume: the boot emits a record per stage, and this runs ten times that volume through
//      the same call, counting what was written and what was refused.
//
// What this does not prove: that the serial port is there. A host shim accepts the write; the
// kernel's UART is K1's evidence, not this file's.
//
// Status: WRITTEN — not run. The coordinator runs it and records the result in
// os-build/layer1/r11/bootlog.md.

import bootlog.bootlog;
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
    say("t107 bootlog limits and refusals\n");

    // --- 1. the constants the record header is built from ---
    check("LEVEL_INFO is 1", LEVEL_INFO == 1);
    check("LEVEL_WARN is 2", LEVEL_WARN == 2);
    check("LEVEL_ERROR is 3", LEVEL_ERROR == 3);
    check("the levels are ordered", LEVEL_INFO < LEVEL_WARN && LEVEL_WARN < LEVEL_ERROR);
    check("BL_LINE is 200", BL_LINE == 200);

    // --- 2. a record that fits, and one that does not ---
    // 150 bytes of message leaves header room inside 200; 200 bytes does not. The two are far
    // enough apart that a change in tick width cannot flip either result.
    var big: u8[..256] = [0; 256];
    var i: i64 = 0;
    while i < 256 {
        big[i] = 65;
        i = i + 1;
    }

    var fits: u8[>..] = [];
    check("a 150-byte message fits BL_LINE", record(fits, BL_LINE, LEVEL_INFO, big[..150]));
    check("the record is not the message: it carries a header", fits.len > 150);

    var too_long: u8[>..] = [];
    check("a 200-byte message is refused at BL_LINE",
          record(too_long, BL_LINE, LEVEL_INFO, big[..200]) == false);
    check("a refused record writes nothing", too_long.len == 0);

    // A refusal must not disturb a builder that already holds bytes: `record` appends, and a
    // partial append is the half-line this service exists to prevent.
    var used: u8[>..] = [];
    used.push(0x58);                       // 'X'
    check("a refused record leaves earlier bytes alone",
          record(used, 8, LEVEL_ERROR, "storage") == false && used.len == 1 && used[0] == 0x58);

    // A caller cap of zero is not a special case: nothing fits, nothing is written.
    var none: u8[>..] = [];
    check("cap 0 refuses every record", record(none, 0, LEVEL_INFO, "") == false && none.len == 0);

    // --- 3. an overlong message is refused, not truncated ---
    var over: u8[>..] = [];
    check("a 256-byte message is refused, never cut",
          record(over, BL_LINE, LEVEL_WARN, big[..256]) == false && over.len == 0);

    // --- 4. the stage wrapper propagates the same answer ---
    check("stage writes a short line", stage(LEVEL_INFO, "boot start"));
    check("stage still writes at the error level", stage(LEVEL_ERROR, "storage down"));
    check("stage refuses an overlong message", stage(LEVEL_WARN, big[..256]) == false);

    // --- 5. load: ten times a boot's worth of records ---
    // A boot emits one record per stage; 22 stages is the published boot table, so 220 is ten
    // boots' volume through the same call. Nothing here allocates: every call makes its own
    // builder, as `stage` does.
    var ops: i64 = 0;
    var ok: i64 = 0;
    var refused: i64 = 0;
    while ops < 220 {
        var line: u8[>..] = [];
        if record(line, BL_LINE, LEVEL_INFO, "stage up") { ok = ok + 1; }
        else { refused = refused + 1; }
        ops = ops + 1;
    }
    check("220 records, all written", ok == 220 && refused == 0);

    say("LOAD bootlog ops=");
    var ob: u8[>..] = [];
    let _ = append_int(ob, 32, ops);
    say(ob[..]);
    say(" ok=");
    var kb: u8[>..] = [];
    let _ = append_int(kb, 32, ok);
    say(kb[..]);
    say(" refused=");
    var rb: u8[>..] = [];
    let _ = append_int(rb, 32, refused);
    say(rb[..]);
    say("\n");

    say("t107 done  pass=");
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
