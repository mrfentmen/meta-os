//! abiprobe: the six-call ABI, checked from userspace.
//!
//! Every other program proves one thing by using a call. This one checks the
//! CONTRACT: the page cap refuses rather than truncates, chunking composes, a
//! yield returns to the same task, pid does not change under it, read_key's
//! empty sentinel is outside the byte range, and the reserved numbers refuse.
//!
//! Exit code is the number of failed checks (0 = green), so a boot log and an
//! `echo $?` agree. Diagnostic: not for `BINS`.

#![no_std]
#![no_main]

use user::{
    print_u64, sys_bad_n, sys_exit, sys_getpid, sys_read_key, sys_sleep, sys_write,
    sys_write_all, sys_yield,
};

static PAGE: [u8; 4096] = [b'a'; 4096];
static BIG: [u8; 10240] = [b'b'; 10240];

fn field(label: &[u8], value: u64) {
    sys_write(label);
    print_u64(value);
    sys_write(b"\n");
}

#[no_mangle]
pub extern "C" fn _start() -> ! {
    let mut checks: u64 = 0;
    let mut fails: u64 = 0;

    let pid = sys_getpid();
    field(b"abiprobe: pid ", pid);
    checks += 1;
    if pid == 0 {
        fails += 1;
    }

    let empty = sys_write(b"");
    field(b"abiprobe: empty write ", empty);
    checks += 1;
    if empty != 0 {
        fails += 1;
    }

    let cap = sys_write(&PAGE);
    field(b"abiprobe: page write ", cap);
    checks += 1;
    if cap != 4096 {
        fails += 1;
    }

    let over = sys_write(&BIG[..4097]);
    field(b"abiprobe: 4097 write ", over);
    checks += 1;
    if over != 0 {
        fails += 1;
    }

    let chunked = sys_write_all(&BIG) as u64;
    field(b"abiprobe: chunked write ", chunked);
    checks += 1;
    if chunked != BIG.len() as u64 {
        fails += 1;
    }

    sys_yield();
    let after_yield = sys_getpid();
    field(b"abiprobe: pid after yield ", after_yield);
    checks += 1;
    if after_yield != pid {
        fails += 1;
    }

    let slept = sys_sleep(2);
    field(b"abiprobe: sleep returned ", slept);
    let after_sleep = sys_getpid();
    checks += 1;
    if after_sleep != pid {
        fails += 1;
    }

    let key = sys_read_key();
    sys_write(b"abiprobe: readkey ");
    if key == u64::MAX {
        sys_write(b"empty\n");
    } else {
        field(b"byte ", key);
    }
    checks += 1;
    if key != u64::MAX && key > 255 {
        fails += 1;
    }

    // 6-15 are reserved by the F1 ruling; 99 is outside any table.
    for n in [6u64, 15, 99] {
        let r = sys_bad_n(n);
        sys_write(b"abiprobe: syscall ");
        print_u64(n);
        sys_write(b" -> ");
        print_u64(r);
        sys_write(b"\n");
        checks += 1;
        if r != u64::MAX {
            fails += 1;
        }
    }

    sys_write(b"abiprobe: checks ");
    print_u64(checks);
    sys_write(b" failures ");
    print_u64(fails);
    sys_write(b"\n");
    if fails == 0 {
        sys_write(b"abiprobe: ABI OK\n");
        sys_exit(0);
    }
    sys_write(b"abiprobe: ABI FAILED\n");
    sys_exit(fails);
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
