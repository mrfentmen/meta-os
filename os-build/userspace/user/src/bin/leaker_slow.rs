//! leaker-slow: touches one new page per second and exits after five — BLOCKED.
//! Expected kernel behaviour: cannot be stated; this ABI has no mmap, so no new
//! page can be requested and no leak can be produced. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

static mut ARENA: [u8; 40960] = [0; 40960];

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"leaker-slow: no mmap; touching one static page per tick\n");
    let mut p = 0usize;
    while p < 5 {
        unsafe {
            let at = p * 4096;
            core::ptr::write_volatile(core::ptr::addr_of_mut!(ARENA[at]), p as u8);
        }
        user::sys_sleep(1);
        p += 1;
    }
    sys_write(b"leaker-slow: five static pages touched, none requested\n");
    sys_exit(0);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
