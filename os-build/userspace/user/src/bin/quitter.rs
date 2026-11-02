//! quitter: exits nonzero, so the shell's `ps` and the exit line have
//! something true to report. Spec-first: the expected boot-log line is
//! `user exit code 7` (os-build/USERSPACE_PROGRAMS.md), written before
//! this file.
//!
//! Why 7 and not 1: 1 is what a crashed or defaulted exit tends to look
//! like, so a deliberate nonzero code that is not 1 cannot be confused
//! with "something went wrong in the loader".

#![no_std]
#![no_main]

use user::{sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"quitter: exiting 7\n");
    sys_exit(7);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
