//! reader-badkey: reads one key; exits 3 unless it is 'q'.
//! Expected kernel behaviour: an unknown scancode is delivered, not filtered;
//! the program decides what it means. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"reader-badkey: waiting for one key\n");
    let k = loop {
        let k = user::sys_read_key();
        if k != u64::MAX { break k; }
        user::sys_yield();
    };
    sys_write(b"reader-badkey: key = ");
    print_u64(k);
    sys_write(b"\n");
    if k == b'q' as u64 { sys_exit(0) } else { sys_exit(3) }
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
