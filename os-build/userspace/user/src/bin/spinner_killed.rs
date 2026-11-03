//! spinner-killed: a spinner plus a kill — BLOCKED BY THE ABI.
//! Expected kernel behaviour: cannot be stated; no kill syscall exists, so a
//! second program cannot end this one. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"spinner-killed: no kill syscall in this ABI\n");
    let mut n: u64 = 0;
    loop {
        n = n.wrapping_add(1);
        if n == 1_000_000 { sys_write(b"spinner-killed: still running\n"); }
    }
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
