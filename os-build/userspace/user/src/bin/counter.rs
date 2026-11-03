//! counter: counts to one thousand and prints the total, then exits clean.
//! Expected kernel behaviour: a long compute loop is preempted but never lost.
//! Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    let mut n: u64 = 0;
    while n < 1000 { n += 1; }
    sys_write(b"counter: counted ");
    print_u64(n);
    sys_write(b"\n");
    sys_exit(0);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
