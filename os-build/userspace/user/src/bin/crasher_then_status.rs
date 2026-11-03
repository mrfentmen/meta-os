//! crasher-then-status: a crash followed by a status capture — BLOCKED.
//! Expected kernel behaviour: cannot be stated; this crate cannot start another
//! program or read its exit status. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"crasher-then-status: no wait/status syscall exists\n");
    unsafe { core::ptr::read_volatile(0x0 as *const u8); }
    sys_exit(2);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
