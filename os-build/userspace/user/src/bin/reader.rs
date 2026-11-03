//! reader: reads keys until 'q', then exits clean.
//! Expected kernel behaviour: the readkey ring serves one byte per call and
//! returns u64::MAX on empty; the task yields while it waits. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"reader: press q\n");
    let mut seen: u64 = 0;
    loop {
        let k = user::sys_read_key();
        if k == u64::MAX {
            user::sys_yield();
            continue;
        }
        seen += 1;
        if k == b'q' as u64 { break; }
    }
    sys_write(b"reader: keys before q = ");
    print_u64(seen);
    sys_write(b"\n");
    sys_exit(0);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
