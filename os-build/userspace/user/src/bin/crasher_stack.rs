//! crasher-stack: recurses until the stack ends.
//! Expected kernel behaviour: the guard page faults, the kernel kills the task
//! and logs it, and the machine stays up. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

#[inline(never)]
fn deeper(n: u64) -> u64 {
    let pad = [0u8; 512];
    let v = unsafe { core::ptr::read_volatile(&pad[0]) } as u64;
    if n == u64::MAX { return v; }
    deeper(n + 1) + v as u64
}

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"crasher-stack: recursing\n");
    let answer = deeper(0);
    print_u64(answer);
    sys_write(b"crasher-stack: SURVIVED (must never print)\n");
    loop {}
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
