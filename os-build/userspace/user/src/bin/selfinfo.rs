//! selfinfo: what a task can know about itself, printed for a log.
//!
//! syscall 3 must return a nonzero id for a running task, and sleeping must
//! not change it. `selfinfo` is the smallest honest proof of the process
//! identity contract; a shell or an agent host needs that id to name work.
//!
//! Diagnostic: not for `BINS`.

#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_getpid, sys_sleep, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    let before = sys_getpid();
    sys_write(b"selfinfo: pid ");
    print_u64(before);
    sys_write(b"\n");

    sys_sleep(1);
    let after = sys_getpid();
    sys_write(b"selfinfo: pid after sleep ");
    print_u64(after);
    sys_write(b"\n");

    if before == 0 || after != before {
        sys_write(b"selfinfo: identity NOT held\n");
        sys_exit(1);
    }
    sys_write(b"selfinfo: identity held\n");
    sys_exit(0);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
