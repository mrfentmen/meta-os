//! crasher-null: reads address zero.
//! Expected kernel behaviour: the kernel kills the task, logs the fault, and
//! keeps running; the second line must never print. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"crasher-null: about to read zero\n");
    unsafe {
        core::ptr::read_volatile(0x0 as *const u8);
    }
    sys_write(b"crasher-null: SURVIVED (must never print)\n");
    loop {}
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
