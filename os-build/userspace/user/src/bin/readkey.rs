//! readkey: fourth userspace program (R5-2). Polls syscall 5 in a
//! bounded drill, prints each scancode byte it gets back (decimal),
//! notes the empty case, exits early on Enter. Sleeps between passes
//! so the trap rate stays at normal-task levels.

#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_read_key, sys_write, sys_yield};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"readkey: polling syscall 5\n");
    let mut got = 0u32;
    let mut empties = 0u32;
    let mut i = 0u32;
    // Drain-all per pass, like the console task: whoever polls first
    // after a keystroke gets it (shared buffer, first-come).
    while i < 200000 {
        loop {
            let r = sys_read_key();
            if r == u64::MAX {
                break;
            }
            if got < 40 {
                sys_write(b"readkey got ");
                print_u64(r);
                sys_write(b"\n");
            }
            got += 1;
            if r == 0x1C {
                sys_write(b"readkey: enter seen, done got=");
                print_u64(got as u64);
                sys_write(b"\n");
                sys_exit(0);
            }
        }
        if empties < 3 {
            sys_write(b"readkey: empty\n");
        }
        empties += 1;
        sys_yield();
        i += 1;
        if i % 100 == 0 {
            sys_write(b"readkey progress ");
            print_u64(i as u64);
            sys_write(b"\n");
        }
    }
    sys_write(b"readkey done got=");
    print_u64(got as u64);
    sys_write(b" empties=");
    print_u64(empties as u64);
    sys_write(b"\n");
    sys_exit(0);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
