//! hog-then-quit: touches every page of its arena, then exits 9.
//! Expected kernel behaviour: the exit status is 9 after all the faults, not a
//! fault-derived status. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

static mut ARENA: [u8; 32768] = [0; 32768];

#[no_mangle]
pub extern "C" fn _start() -> ! {
    let mut i = 0usize;
    unsafe {
        while i < 32768 {
            core::ptr::write_volatile(core::ptr::addr_of_mut!(ARENA[i]), 1);
            i += 4096;
        }
    }
    sys_write(b"hog-then-quit: exiting 9 after touching the arena\n");
    sys_exit(9);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
