// services/time/entry.goose — the program entry point for time (B-1).
//
// Split out of the module on purpose: a program may export svc_entry exactly
// once, and any service that imports this module for its logic would otherwise
// drag a second svc_entry into its own program. The logic stays in time.goose;
// only the entry symbol lives here.

import time.time;

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

    return 0;
}
