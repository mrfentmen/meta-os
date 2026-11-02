// services/bootlog/entry.goose — the program entry point for bootlog (B-1).
//
// Split out of the module on purpose: a program may export svc_entry exactly
// once, and any service that imports this module for its logic would otherwise
// drag a second svc_entry into its own program. The logic stays in bootlog.goose;
// only the entry symbol lives here.

import bootlog.bootlog;

export "svc_entry" fn service_main() -> i32 {
    // Order matters: the first record proves the serial path works at all.
    stage(LEVEL_INFO, "start");
    stage(LEVEL_INFO, "serial path up");

    // Boot log retention is a ring in this service's static storage (B-L1-11
    // provides the ring). Until that library exists the records go straight to
    // the kernel, which is the honest minimum: nothing is buffered, nothing is
    // lost silently, and the gap is visible here rather than papered over.
    stage(LEVEL_INFO, "ready");
    return 0;
}
