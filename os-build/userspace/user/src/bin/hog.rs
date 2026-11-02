//! hog: memory containment drill (R12-011), written against the approved spec sentence:
//!
//!   "hog allocates memory in a loop until the kernel refuses; containment is the refusal
//!    (or the hog task's kill) while the shell still answers `status` afterwards."
//!
//! Honest limit, stated in the program and in os-build/USERSPACE_PROGRAMS.md: the ABI has no
//! allocation call. There is no mmap, brk or alloc in calls 0-5, and 6-15 are reserved. So this
//! program cannot ask for memory; it touches successive pages past its own image. The first
//! unmapped page is the refusal — a page fault that kills only this task.
//!
//! It is deliberately far from the known program bases (0x6000_0000_0000, 0x6100_0000_0000,
//! 0x6200_0000_0000) so the first touch is a fault rather than a collision with another image.
//! The kernel-side wiring and the boot proof are Rowan's and OpenCode's; this file compiles in
//! the userspace crate and is not in `kernel/build.rs`'s BINS list.

#![no_std]
#![no_main]

use user::{sys_exit, sys_write};

const START: u64 = 0x7000_0000_0000;
const STRIDE: u64 = 4096;
const STEPS: u64 = 64;

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"hog: allocating\n");
    let mut addr = START;
    let mut i = 0u64;
    while i < STEPS {
        // Volatile: the write must reach memory, not be optimised into nothing.
        unsafe { core::ptr::write_volatile(addr as *mut u8, 0xA5); }
        addr += STRIDE;
        i += 1;
    }
    // Reaching here means every touched page was mapped: the containment drill did not fire.
    // Say so instead of exiting 0, so a boot log cannot read as success.
    sys_write(b"hog: SURVIVED (containment did not fire)\n");
    sys_exit(1);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
