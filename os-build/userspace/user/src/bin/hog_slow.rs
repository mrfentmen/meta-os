//! hog-slow: touches the same 16 pages one byte at a time, then exits 0.
//! Expected kernel behaviour: the faults are spread over 65,536 writes instead
//! of 16, and the task still exits clean. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

static mut ARENA: [u8; 65536] = [0; 65536];

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"hog-slow: 65536 single-byte writes\n");
    let mut i = 0usize;
    unsafe {
        while i < 65536 {
            core::ptr::write_volatile(core::ptr::addr_of_mut!(ARENA[i]), (i & 0xff) as u8);
            i += 1;
        }
    }
    sys_write(b"hog-slow: done\n");
    sys_exit(0);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
