//! hog-under-ps: a hog running while ps is captured — BLOCKED BY THE ABI.
//! Expected kernel behaviour: cannot be stated; there is no ps program, no
//! process-list syscall, and no way to run two programs at once here.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

static mut ARENA: [u8; 16384] = [0; 16384];

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"hog-under-ps: no process-list syscall exists\n");
    unsafe {
        let mut i = 0usize;
        while i < 16384 {
            core::ptr::write_volatile(core::ptr::addr_of_mut!(ARENA[i]), 1);
            i += 4096;
        }
    }
    sys_exit(2);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
