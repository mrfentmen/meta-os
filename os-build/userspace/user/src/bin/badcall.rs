//! badcall: proves the refusal arm for reserved numbers, not just one of them.
//!
//! Spec-first (os-build/USERSPACE_PROGRAMS.md): expected kernel lines are
//! `user bad syscall 8 refused`, `... 15 refused`, `... 99 refused`, each
//! returning u64::MAX, with the task surviving all three and exiting 0.
//!
//! 8 and 15 are the edges of the reserved range (0-7 are allocated: exit,
//! write, sleep, pid, yield, read_key, ipc_send, ipc_recv); 99 is the proven
//! example from K1. A task that gets MAX back and keeps running is the claim.

#![no_std]
#![no_main]

use user::{print_u64, sys_bad_n, sys_exit, sys_write};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"badcall: reserved numbers\n");
    for number in [8u64, 15, 99] {
        let result = sys_bad_n(number);
        sys_write(b"badcall: ");
        print_u64(number);
        sys_write(b" returned ");
        print_u64(result);
        sys_write(b"\n");
    }
    sys_write(b"badcall: survived all three\n");
    sys_exit(0);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
