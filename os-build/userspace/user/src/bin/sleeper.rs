//! sleeper: second userspace program (OS-083) plus the bad-syscall
//! drill (OS-084). Write, sleep 100, write, call 99 (refused), exit.

#![no_std]
#![no_main]

use user::{print_u64, sys_bad, sys_exit, sys_getpid, sys_sleep, sys_write, sys_yield};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"sleeper: before sleep\n");
    sys_write(b"sleeper: pid ");
    print_u64(sys_getpid());
    sys_write(b"\n");
    sys_yield();
    sys_write(b"sleeper: yielded and back\n");
    sys_sleep(100);
    sys_write(b"sleeper: after sleep\n");
    let r = sys_bad();
    if r == u64::MAX {
        sys_write(b"sleeper: bad call refused\n");
    }
    sys_exit(0);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
