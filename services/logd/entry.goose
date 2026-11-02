// services/logd/entry.goose — the program entry point for logd (B-1).
//
// Split out of the module on purpose: a program may export svc_entry exactly
// once, and any service that imports this module for its logic would otherwise
// drag a second svc_entry into its own program. The logic stays in logd.goose;
// only the entry symbol lives here.

import logd.logd;

export "svc_entry" fn service_main() -> i32 {
    storage_init();
    log_info("logd", "sink up");
    log_info("logd", "policy: high-water 48/64, error immediate, explicit flush");

    // Self-check: prove the round trip works while the port is still the only
    // thing that matters, then report the queue state honestly.
    log_info("logd", "self-check queued");
    let sent = flush();
    if sent < 3 {
        // The port refused most of the queue. Returning non-zero hands this to
        // the supervisor instead of pretending the log works.
        return 1;
    }

    // The service loop: with no IPC, the only thing to do is ensure the queue
    // drains. When the IPC transport exists (Q-B-L1-2), records arrive here and
    // the loop is unchanged.
    var spins: i64 = 0;
    while true {
        if should_flush() { flush(); }
        sys_yield();
        spins = spins + 1;
        // A service that only spins is not a service. B-L1-76 makes this loop
        // real by feeding it records; until then it is honest about being idle.
        if spins > 1000000 { break; }
    }
    flush();
    log_info("logd", "sink stopping");
    flush();
    return 0;
}
