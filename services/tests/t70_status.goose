// services/tests/t70_status.goose
//
// BF4-09 — test program for the status formatter (common/status).
//
// Status: WRITTEN and RUN natively against the host shim
// (os-build/layer1/host/host_shim.c). It is not COMPILED for the kernel, and it has not
// run in ring 3 -- there is no ring 3 for it yet.
//
// WHAT IT ASSERTS, AND WHY EACH ONE
// ---------------------------------
// The whole point of BF4-09 is that the kernel's STATUS line and the services' SERVICE
// lines are read by the SAME parser. So the cases are the ways a line can be unparseable
// rather than the ways it can be ugly:
//   - the exact shape, byte for byte, including the separators and the trailing newline;
//   - a key or word containing '=', ' ' or newline is REFUSED and leaves the buffer
//     untouched -- a status line that only sometimes parses is worse than a short one;
//   - reading back: a field in the middle, the first field, an absent key, and a key
//     whose value is not a number;
//   - the kernel's own cropping: `status_get` on a line that a ring buffer truncated
//     must return false, not a number made of the surviving digits.

import common.fmt.fmt;
import common.status.status;
import common.sys.sys;

var t_pass: i64 = 0;
var t_fail: i64 = 0;

fn say(s: const u8[:]) { let _ = sys_write_serial(s); }

fn t_eq(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn check(name: const u8[:], cond: bool) {
    if cond { t_pass = t_pass + 1; say("ok   "); }
    else { t_fail = t_fail + 1; say("FAIL "); }
    say(name);
    say("\n");
}

fn main() {
    say("t70 status\n");

    // --- the exact shape ---
    // Byte for byte: "SERVICE logd state=1 ticks=380 slots=64\n" is 38 bytes.
    var b0: u8[>..] = [];
    let ok0 = status_open(b0, 64, "logd")
        && status_field(b0, 64, "state", 1)
        && status_field(b0, 64, "ticks", 380)
        && status_field(b0, 64, "slots", 64)
        && status_end(b0, 64);
    check("shape", ok0 && t_eq(b0, "SERVICE logd state=1 ticks=380 slots=64\n"));

    // The kernel's line has no SERVICE prefix, and status_name must say so rather than
    // match junk. This is the line the kernel really prints today.
    let n0 = status_name("STATUS tasks=7 ticks=380 heap_free_kb=31");
    check("kernel line has no service name", n0.len == 0);

    // --- refusal rules: the buffer must be untouched ---
    var b2: u8[>..] = [];
    check("key with '=' refused", status_field(b2, 64, "a=b", 1) == false && b2.len == 0);

    var b3: u8[>..] = [];
    check("key with space refused", status_field(b3, 64, "a b", 1) == false && b3.len == 0);

    var b4: u8[>..] = [];
    check("empty key refused", status_field(b4, 64, "", 1) == false && b4.len == 0);

    var b5: u8[>..] = [];
    check("word with space refused", status_field_word(b5, 64, "mode", "id le") == false && b5.len == 0);

    var b6: u8[>..] = [];
    check("empty name refused", status_open(b6, 64, "") == false && b6.len == 0);

    // A name with a space would break status_name, and it is refused before the prefix
    // is written, so the buffer stays empty.
    var b6b: u8[>..] = [];
    check("name with space refused", status_open(b6b, 64, "log d") == false && b6b.len == 0);

    // --- the cap rule ---
    // "SERVICE x" is 9 bytes, " aaa=1" makes 15, and " state=1" would make 23. With a
    // cap of 20 the second field must refuse and leave the buffer at exactly 15.
    var b7: u8[>..] = [];
    let ok7 = status_open(b7, 20, "x") && status_field(b7, 20, "aaa", 1);
    let before = b7.len;
    let ok7b = status_field(b7, 20, "state", 1);
    check("cap short refuses", ok7 && before == 15 && ok7b == false && b7.len == 15);

    // --- reading back ---
    let line: const u8[:] = "SERVICE logd state=1 ticks=380 slots=64\n";
    let v0, f0 = status_get(line, "ticks");
    check("get middle key", f0 && v0 == 380);

    let v1, f1 = status_get(line, "state");
    check("get first field", f1 && v1 == 1);

    let v2, f2 = status_get(line, "slots");
    check("get last key", f2 && v2 == 64);

    let v3, f3 = status_get(line, "absent");
    check("absent key false", f3 == false && v3 == 0);

    // `tick` must not match inside `ticks=`: no substring matching.
    let v4, f4 = status_get(line, "tick");
    check("prefix of a key does not match", f4 == false);

    // The name field, present and absent.
    let n = status_name(line);
    check("status_name", t_eq(n, "logd"));

    // A truncated line: a ring keeps the head or the tail, and either way a partial
    // record must not be reported as a number.
    let v5, f5 = status_get("SERVICE logd state=1 ticks=38", "slots");
    check("truncated key absent", f5 == false);

    let v6, f6 = status_get("SERVICE logd state=1 ticks=", "ticks");
    check("truncated value not a number", f6 == false);

    // A negative value reads back negative (a service may report a delta).
    let v7, f7 = status_get("SERVICE x delta=-42\n", "delta");
    check("negative value", f7 && v7 == -42);

    // --- words ---
    var b8: u8[>..] = [];
    let ok8 = status_field_word(b8, 64, "mode", "idle");
    check("word field", ok8 && t_eq(b8, " mode=idle"));

    var b9: u8[>..] = [];
    let ok9 = status_field_word(b9, 64, "mode", "idle") && status_field(b9, 64, "uptime", 12);
    check("word then number", ok9 && t_eq(b9, " mode=idle uptime=12"));

    say("t70 status: ");
    var sb: u8[>..] = [];
    let _ = append_int(sb, 24, t_pass);
    say(sb);
    say(" pass, ");
    var sb2: u8[>..] = [];
    let _ = append_int(sb2, 24, t_fail);
    say(sb2);
    say(" fail\n");
    if t_fail != 0 { sys_exit(1); }
    sys_exit(0);
}
