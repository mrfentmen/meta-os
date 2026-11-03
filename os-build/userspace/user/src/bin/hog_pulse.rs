//! hog-pulse: fills, clears, then fills again, and exits 0.
//! Expected kernel behaviour: the same pages are written three times and no
//! page is returned, because this ABI has no free. Boot NOT CLAIMED.
#![no_std]
#![no_main]

use user::{print_u64, sys_exit, sys_write};

static mut ARENA: [u8; 32768] = [0; 32768];

fn fill(v: u8) {
    let mut i = 0usize;
    unsafe {
        while i < 32768 {
            core::ptr::write_volatile(core::ptr::addr_of_mut!(ARENA[i]), v);
            i += 1024;
        }
    }
}

#[no_mangle]
pub extern "C" fn _start() -> ! {
    sys_write(b"hog-pulse: fill\n");
    fill(0xaa);
    sys_write(b"hog-pulse: clear\n");
    fill(0x00);
    sys_write(b"hog-pulse: fill again\n");
    fill(0x55);
    sys_write(b"hog-pulse: done\n");
    sys_exit(0);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
