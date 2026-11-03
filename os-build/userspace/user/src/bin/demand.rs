//! demand: K3 demand-paging program (design §4, build note
//! `os-build/K3_DEMAND_PAGING_BUILD.md`). Its only demand access
//! is one promised page: read it (faults, kernel maps a fresh
//! zero-filled page, instruction retries), prove the zero-fill,
//! write a value, read it back, then touch an address outside
//! its own promised region and be killed — proving the region
//! boundary is real and not a global "map anything" rule.
//! The kernel must log `INT user demand-fault ...: page mapped,
//! retry` for the first access and `INT user page-fault ...:
//! task killed` for the last one, on the same boot, with the
//! other tasks continuing. Static, no_std, own `_start`.

#![no_std]
#![no_main]

use user::sys_write;

/// The kernel's promised page for this program
/// (`kernel/src/user.rs` `DEMAND_PAGE`). This address is never
/// mapped at load: the first read below faults by construction,
/// and a gate log without the demand-fault line means this
/// program never actually faulted, not that demand paging works.
const DEMAND_PAGE: u64 = 0x0000_7000_0000_0000;
/// One MiB past the promised page: outside the region, unmapped,
/// so a read here must kill this task (gate leg 3).
const OUTSIDE_PAGE: u64 = DEMAND_PAGE + 0x100000;

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"demand: touching promised page\n");
    let first = unsafe { core::ptr::read_volatile(DEMAND_PAGE as *const u8) };
    if first != 0 {
        sys_write(b"demand: NONZERO first byte (must never print)\n");
        loop {}
    }
    sys_write(b"demand: zero-fill confirmed\n");
    unsafe { core::ptr::write_volatile(DEMAND_PAGE as *mut u8, 0x5A) };
    let back = unsafe { core::ptr::read_volatile(DEMAND_PAGE as *const u8) };
    if back != 0x5A {
        sys_write(b"demand: writeback mismatch (must never print)\n");
        loop {}
    }
    sys_write(b"demand: writeback OK, touching outside region\n");
    unsafe {
        core::ptr::read_volatile(OUTSIDE_PAGE as *const u8);
    }
    sys_write(b"demand: SURVIVED (must never print)\n");
    loop {}
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
