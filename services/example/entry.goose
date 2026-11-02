// services/example/entry.goose — the program entry point for example (B-1).
//
// Split out of the module on purpose: a program may export svc_entry exactly
// once, and any service that imports this module for its logic would otherwise
// drag a second svc_entry into its own program. The logic stays in example.goose;
// only the entry symbol lives here.

import example.example;

export "svc_entry" fn service_main(boot: BootInfo&) -> i32 {
    let code = run(boot);
    if code != CODE_OK { return 1; }
    return 0;
}
