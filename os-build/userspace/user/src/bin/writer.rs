//! writer: exercises the write cap, including the oversize case.
//!
//! Spec-first (os-build/USERSPACE_PROGRAMS.md): expected boot-log lines are
//! `writer: alive`, `writer: oversize returned 0`, `writer: cap returned 19`.
//!
//! The 4097-byte write is the interesting one. `user_write` returns 0 for a
//! length above one page, which is the same value it returns for a zero-length
//! write — the ABI spec records that as finding 1. This program makes the
//! behaviour visible in a boot log instead of leaving it in a document.

#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

/// One byte over the page cap. 'x' so a partial write would be obvious.
static OVER: [u8; 4097] = [b'x'; 4097];

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"writer: alive\n");

    let oversize = sys_write(&OVER);
    sys_write(b"writer: oversize returned ");
    print_u64(oversize);
    sys_write(b"\n");

    let within = sys_write(b"writer: within cap\n");
    sys_write(b"writer: cap returned ");
    print_u64(within);
    sys_write(b"\n");

    sys_exit(0);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
