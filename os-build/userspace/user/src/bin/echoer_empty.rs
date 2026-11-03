//! echoer-empty: invoked with no arguments at all.
//! Expected kernel behaviour: nothing can be printed from the arguments,
//! because the ABI delivers none; the program says so and exits 0.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"echoer-empty: no arguments (the ABI delivers none)\n");
    sys_exit(0);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
