//! capcheck: the K6.1 in-kernel capability drill.
//!
//! Every check below is made by asking the kernel and reading its
//! return value. The program cannot enforce anything itself; it proves
//! that the kernel's syscall path does. Expected kernel lines:
//!
//!   cap grant capcheck write=128 ticks=2000 sleep=100
//!   cap deny capcheck write 256 over 109
//!   cap deny capcheck syscall 5
//!   cap deny capcheck sleep 1000 over 100
//!
//! and then `capcheck: done`, `user exit code 0`.

#![no_std]
#![no_main]

use user::{sys_cap_query, sys_exit, sys_read_key, sys_sleep, sys_write, DENIED};

/// Deliberately larger than the 128-byte write cap in `caps.rs`.
static BIG: [u8; 256] = [b'x'; 256];

#[no_mangle]
pub extern "C" fn _start() -> ! {
    // The packed budget: low 32 bits are remaining console bytes. At
    // entry that must be the full 128-byte grant.
    let caps = sys_cap_query();
    if caps == u64::MAX || (caps & 0xFFFF_FFFF) != 128 {
        sys_write(b"capcheck: query bad\n");
        sys_exit(1);
    }
    sys_write(b"capcheck: query ok\n");

    // Allowed syscall, over-limit request: the kernel must refuse it
    // and must not print any of the 256 bytes. The query line above
    // already charged 19 bytes, so the remaining quota is 109.
    if sys_write(&BIG) != DENIED {
        sys_write(b"capcheck: write NOT denied\n");
        sys_exit(1);
    }
    sys_write(b"capcheck: write denied\n");

    // Syscall 5 is not in capcheck's allow mask. An empty key ring
    // would return u64::MAX, so DENIED is the unambiguous proof.
    if sys_read_key() != DENIED {
        sys_write(b"capcheck: syscall NOT denied\n");
        sys_exit(1);
    }
    sys_write(b"capcheck: syscall denied\n");

    // Sleep is allowed, 1000 ticks is over the 100-tick per-sleep cap.
    if sys_sleep(1000) != DENIED {
        sys_write(b"capcheck: sleep NOT denied\n");
        sys_exit(1);
    }
    sys_write(b"capcheck: sleep denied\n");

    sys_write(b"capcheck: done\n");
    sys_exit(0);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
