//! counter-big: counts to four billion, past the 32-bit range.
//! Expected kernel behaviour: the loop spans many ticks and the printed total
//! is a u64, so a 32-bit wrap would be visible. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    let mut n: u64 = 0;
    while n < 4_000_000_000 { n += 1; }
    sys_write(b"counter-big: counted ");
    print_u64(n);
    sys_write(b"\n");
    sys_exit(0);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
