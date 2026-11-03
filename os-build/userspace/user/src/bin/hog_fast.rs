//! hog-fast: touches 16 pages in 4 KiB strides, then exits 0.
//! Expected kernel behaviour: sixteen faults land in one pass and the task
//! keeps its exit path. Boot NOT CLAIMED — the Mac gate owns that.
//! This crate has no allocator, so "allocate" here means touching BSS pages;
//! there is no syscall that grows a heap.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

static mut ARENA: [u8; 65536] = [0; 65536];

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"hog-fast: touching 16 pages\n");
    let mut i = 0usize;
    unsafe {
        while i < 65536 {
            core::ptr::write_volatile(core::ptr::addr_of_mut!(ARENA[i]), (i & 0xff) as u8);
            i += 4096;
        }
    }
    sys_write(b"hog-fast: done\n");
    sys_exit(0);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
