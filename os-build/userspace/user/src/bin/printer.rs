//! printer: writes one hundred lines, then exits clean.
//! Expected kernel behaviour: the console accepts every line without dropping
//! the tail; scroll behaviour is the kernel's. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    let mut i = 0u64;
    while i < 100 {
        sys_write(b"printer: line ");
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
