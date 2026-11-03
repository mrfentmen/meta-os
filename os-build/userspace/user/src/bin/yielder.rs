//! yielder: give the CPU back, repeatedly, and come back as the same task.
//!
//! This is the load-bearing property for every service's wait loop: `yield`
//! must actually reschedule (another task runs) without losing the caller's
//! identity or stack. A yield that returns to the same tick without switching
//! would still pass a pid check, so the boot log pairs this with the scheduler's
//! own switch counter -- this program tests identity preservation, not fairness.
//!
//! Diagnostic: not for `BINS`.

#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_getpid, sys_write, sys_yield};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    let pid = sys_getpid();
    sys_write(b"yielder: pid ");
    print_u64(pid);
    sys_write(b"\n");

    let mut fails = 0u64;
    let mut i = 0u32;
    while i < 8 {
        sys_yield();
        let now = sys_getpid();
        if now != pid {
            fails += 1;
            sys_write(b"yielder: pid changed at ");
            print_u64(i as u64);
            sys_write(b" -> ");
            print_u64(now);
            sys_write(b"\n");
        }
        i += 1;
    }

    sys_write(b"yielder: yields 8 failures ");
    print_u64(fails);
    sys_write(b"\n");
    if fails == 0 {
        sys_write(b"yielder: identity stable\n");
    }
    sys_exit(fails);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
