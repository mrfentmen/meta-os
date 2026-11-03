//! quitter-1: exits with code 1 and prints nothing.
//! Expected kernel behaviour: the exit status reaches the parent as 1; the
//! kernel does not treat a nonzero exit as a fault. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_exit(1);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
