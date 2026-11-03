//! quitter-after-print: prints one line, then exits 3.
//! Expected kernel behaviour: the line is on the console before the exit is
//! recorded, so the log order is print-then-exit. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"quitter-after-print: printed before exit\n");
    sys_exit(3);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
