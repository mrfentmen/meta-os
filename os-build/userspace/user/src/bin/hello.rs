//! hello: first userspace program (OS-077/080/081). Writes one
//! line, exits 0. Static, no_std, own `_start`.

#![no_std]
#![no_main]

use user::{sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"HELLO FROM USERSPACE\n");
    sys_exit(0);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
