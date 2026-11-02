// services/console/entry.goose — the program entry point for console (B-1).
//
// Split out of the module on purpose: a program may export svc_entry exactly
// once, and any service that imports this module for its logic would otherwise
// drag a second svc_entry into its own program. The logic stays in console.goose;
// only the entry symbol lives here.

import console.console;

export "svc_entry" fn service_main() -> i32 {
    history_init();
    print_banner();
    put_str(PROMPT);

    var running = true;
    while running {
        // Poll. There is no blocking key wait in the kernel surface
        // (Q-B-L1-1), so this loop yields between polls; that is the honest
        // cost of the current K6 shape. A fresh builder per poll keeps the
        // loop free of any unverified reset method.
        var buffer: u8[>..] = [];
        let got = sys_read_key(buffer);
        if !got || buffer.len == 0 {
            sys_yield();
            continue;
        }

        var i: i64 = 0;
        while i < buffer.len {
            let done = handle_key(buffer[i]);
            if done {
                // A completed line. With no shell the honest thing is to say so
                // rather than to pretend it ran.
                put_str("[console] line stored; no shell to run it (B-L1-87)\n");
                put_str(PROMPT);
            }
            i = i + 1;
        }
    }
    return 0;
}
