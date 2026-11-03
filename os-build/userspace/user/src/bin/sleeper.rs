//! sleeper: sleeps five ticks, then exits clean.
//! Expected kernel behaviour: the task blocks without burning CPU and is
//! woken by the timer tick. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"sleeper: sleeping 5 ticks\n");
    let r = user::sys_sleep(5);
    sys_write(b"sleeper: woke, sleep returned ");
    print_u64(r);
    sys_write(b"\n");
    sys_exit(0);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
