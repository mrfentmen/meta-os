// services/time/entry.goose — the program entry point for time (B-1).
//
// Split out of the module on purpose: a program may export svc_entry exactly
// once, and any service that imports this module for its logic would otherwise
// drag a second svc_entry into its own program. The logic stays in time.goose;
// only the entry symbol lives here.

import time.time;
import common.sys.sys;

export "svc_entry" fn service_main() -> i32 {
    let hz = requested_tick_hz();
    if hz <= 0 { return 1; }

    let start = sys_ticks();
    if !sleep_ms(10, hz) { return 2; }      // the clock did not advance
    let delta = elapsed(sys_ticks(), start);
    if delta <= 0 { return 3; }             // advanced backwards or not at all

    let ms, ok = ticks_to_ms(delta, hz);
    if !ok { return 4; }
    // 10 ms asked for; anything from one tick to a full second is accepted,
    // because the only claim being made here is "time moves".
    if ms > 1000 { return 5; }

    // One status line, because a service that starts silently cannot be told apart from one
    // that never ran: the boot rehearsal measured "exit 0, zero lines" and could not say more.
    // This is the line BOOT_PLAN S7 greps for, in the shape the other services emit.
    let _ = sys_write_serial("svc time: ready ticks ");
    var buf: u8[..24] = [0; 24];
    var n: i64 = 0;
    var v = delta;
    if v < 0 { v = 0; }
    if v == 0 {
        buf[n] = '0';
        n = 1;
    }
    var digits: u8[..20] = [0; 20];
    var d: i64 = 0;
    while v > 0 { digits[d] = (48 + (v % 10)) as u8; d = d + 1; v = v / 10; }
    while d > 0 { d = d - 1; buf[n] = digits[d]; n = n + 1; }
    let _ = sys_write_serial(buf[0..n]);
    let _ = sys_write_serial("\n");

    return 0;
}
