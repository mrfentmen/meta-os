//! sleeper-killed: a sleeper plus a kill — BLOCKED BY THE ABI.
//! Expected kernel behaviour: cannot be stated; no kill syscall exists.
//! Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"sleeper-killed: no kill syscall; sleeping instead\n");
    user::sys_sleep(1000000);
    sys_write(b"sleeper-killed: slept (nothing could stop it)\n");
    sys_exit(0);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
