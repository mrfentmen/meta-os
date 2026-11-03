//! double-hog: two hogs at once — BLOCKED BY THE ABI.
//! Expected kernel behaviour: cannot be stated; this crate has no fork or exec,
//! so a second hog cannot be started from inside a program. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"double-hog: no fork/exec in this ABI; one process only\n");
    sys_write(b"double-hog: proposal filed for a spawn syscall; exiting 2\n");
    sys_exit(2);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
