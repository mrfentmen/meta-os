//! writechain: repeated and chunked writes, counted.
//!
//! `writer` proves one refusal; this proves the loop around it. Eight full-page
//! writes must each report 4096 (no state leaking between calls), then one
//! 8192-byte buffer must land exactly through `sys_write_all` (two pages).
//! Output is ':' filler, so a short tail is visible as a missing newline.
//!
//! Diagnostic: not for `BINS`.

#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write, sys_write_all};

static PAGE: [u8; 4096] = [b':'; 4096];
static TWO: [u8; 8192] = [b'.'; 8192];

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"writechain: start\n");

    let mut total = 0u64;
    let mut fails = 0u64;
    let mut i = 0u32;
    while i < 8 {
        let r = sys_write(&PAGE);
        if r != 4096 {
            fails += 1;
        }
        total += r;
        i += 1;
    }
    sys_write(b"\nwritechain: pages ");
    print_u64(total);
    sys_write(b" page fails ");
    print_u64(fails);
    sys_write(b"\n");

    let chunked = sys_write_all(&TWO) as u64;
    sys_write(b"\nwritechain: chunked ");
    print_u64(chunked);
    sys_write(b"\n");

    let bad = (total != 8 * 4096) as u64 + (chunked != 8192) as u64;
    sys_write(b"writechain: failures ");
    print_u64(bad);
    sys_write(b"\n");
    if bad == 0 {
        sys_write(b"writechain: OK\n");
    }
    sys_exit(bad);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
