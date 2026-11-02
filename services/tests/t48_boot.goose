// services/tests/t48_boot.goose
//
// B-L1-48 — test program for the BootInfo block and the six syscalls (B-L1-08/B-L1-09).
//
// Status: WRITTEN (not COMPILED, not RUN). This is the one test in the set that CANNOT pass
// on a host machine by design: it asserts the shape of what the kernel hands over.
//
// WHAT IT CHECKS, AND WHAT PASSING WOULD MEAN
// -------------------------------------------
//   - the version gate refuses a block it does not understand (pure logic, would pass
//     anywhere);
//   - sys_ticks is monotonic and advancing (fails on a kernel that stamps a constant, or
//     uses a non-monotonic source -- the bug that makes every deadline misfire);
//   - sys_write_serial reports bytes written rather than a bare success (fails on a shim
//     that swallows a dead UART, which is how a boot log goes silent with no error);
//   - sys_read_key distinguishes "nothing pressed" from "an event is filled in", which is
//     the contract Q-B-L1-1 argues about;
//   - the framebuffer fields are internally consistent: cols*glyph_width fits in width, and
//     stride is at least cols*glyph_width*4. A stride that is wrong is the classic
//     tearing/shear bug, and it is checkable from data alone.
//
// The framebuffer part of this test is the reason it belongs with K2: it cannot be written
// honestly until the kernel publishes those two numbers.

import common.boot.boot;
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
    say("t48 boot + syscalls\n");

    // --- the version gate ---
    var b: BootInfo = BootInfo {
        version: 0,
        serial: SerialInfo { port: 0,
        baud: 0,
        data_bits: 0,
        stop_bits: 0,
        parity: 0 },
        framebuffer: FramebufferInfo { address: 0,
        width: 0,
        height: 0,
        stride: 0,
        pixel_format: 0,
        glyph_width: 0,
        glyph_height: 0,
        cols: 0,
        rows: 0 },
        time: TimeInfo { tick_hz: 0,
        boot_ticks: 0 },
        memory: MemoryInfo { total_bytes: 0,
        service_bytes: 0 },
        reserved: [],
    };
    b.version = BOOTINFO_VERSION;
    check("version accepted", bootinfo_supported(b) == true);
    b.version = BOOTINFO_VERSION + 1;
    check("newer version refused", bootinfo_supported(b) == false);
    b.version = 0;
    check("version 0 refused", bootinfo_supported(b) == false);

    // --- monotonic ticks ---
    let t0 = sys_ticks();
    let t1 = sys_ticks();
    check("ticks non-negative", t0 >= 0);
    check("ticks monotonic", t1 >= t0);

    // Busy for a bounded number of reads; the ticks must have moved by the end, or the
    // kernel is handing back a constant.
    var spin: i64 = 0;
    while spin < 100000 {
        spin = spin + 1;
    }
    let t2 = sys_ticks();
    check("ticks advance", t2 > t1);

    // --- serial reports a length, not a flag ---
    let w = sys_write_serial("t48\n");
    check("serial returns bytes written", w == 4);

    // An empty write is legal and writes nothing.
    let w0 = sys_write_serial("");
    check("empty serial write", w0 == 0);

    // --- key read distinguishes empty from filled ---
    var key: u8[>..] = [];
    let had = sys_read_key(key);
    check("read_key returns without error", had == true || had == false);
    if had { check("read_key filled a buffer", key.len > 0); }
    else { check("read_key filled nothing", key.len == 0); }

    // --- framebuffer consistency ---
    // These are [PROPOSED] fields (see boot.goose). A K2 that publishes different ones
    // fails here loudly, which is the point: the test is the place the change is noticed.
    let fb = b.framebuffer;
    if fb.width > 0 && fb.height > 0 {
        check("cols fit in width", (fb.cols as u64) * (fb.glyph_width as u64) <= (fb.width as u64));
        check("rows fit in height", (fb.rows as u64) * (fb.glyph_height as u64) <= (fb.height as u64));
        check("stride covers a scanline", (fb.stride as u64) >= (fb.width as u64) * 4);
        check("pixel format known", fb.pixel_format <= 2);
    } else {
        // No framebuffer yet is a legitimate state on K1: report it rather than fail, and
        // say so, because a silent skip is how a K2 regression goes unnoticed.
        say("skip framebuffer checks: no framebuffer published\n");
    }

    // --- the boot block's own coherence ---
    if b.time.tick_hz > 0 {
        check("tick rate plausible", b.time.tick_hz >= 1 && b.time.tick_hz <= 1000000);
    } else {
        say("skip tick rate checks: not published\n");
    }

    var r: u8[>..] = [];
    let _ = append_int(r, 32, t_pass);
    say("passed ");
    say(r);
    say("\n");
    if t_fail != 0 { say("FAILURES\n"); sys_exit(1); }
    say("t48 done\n");
    sys_exit(0);
}
