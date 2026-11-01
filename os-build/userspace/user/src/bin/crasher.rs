//! crasher: third userspace program (OS-085). Reads address zero.
//! The kernel must kill this task, log it, and continue.

#![no_std]
#![no_main]

use user::sys_write;

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"crasher: about to read zero\n");
    unsafe {
        core::ptr::read_volatile(0x0 as *const u8);
    }
    sys_write(b"crasher: SURVIVED (must never print)\n");
    loop {}
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
