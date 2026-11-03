//! quitter-7: exits with code 7 and prints nothing.
//! Expected kernel behaviour: status 7 is recorded verbatim, distinct from a
//! killed task. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_exit(7);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
