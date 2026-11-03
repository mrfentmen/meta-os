//! printer-flood: writes five thousand lines, past any console size.
//! Expected kernel behaviour: scroll or drop is the kernel's decision, and the
//! log must not grow without bound. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    let mut i = 0u64;
    while i < 5000 {
        sys_write(b"printer-flood: line ");
        print_u64(i);
        sys_write(b"\n");
        i += 1;
    }
    sys_exit(0);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
