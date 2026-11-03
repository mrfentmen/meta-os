//! spinner: loops forever and never yields.
//! Expected kernel behaviour: the preemption path is the only thing that can
//! take the CPU back; nothing in this program gives it up. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"spinner: entered a loop that never yields\n");
    let mut n: u64 = 0;
    loop {
        n = n.wrapping_add(1);
        unsafe { core::ptr::read_volatile(&n) };
    }
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
