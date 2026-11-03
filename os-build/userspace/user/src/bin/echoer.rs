//! echoer: echoes its arguments, exits clean — BLOCKED BY THE ABI.
//! Expected kernel behaviour: none can be stated, because this crate has no
//! argv syscall and `_start` receives nothing. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"echoer: no argv syscall exists in user/src/lib.rs\n");
    sys_write(b"echoer: nothing to echo; exiting 2\n");
    sys_exit(2);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
