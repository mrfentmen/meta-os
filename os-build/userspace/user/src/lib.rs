//! Userspace syscall wrappers (K6 contract: int 0x80,
//! eax=num, rdi/rsi/rdx=args, rax=return). `core` only.

#![no_std]

#[inline(always)]
fn syscall(num: u64, a1: u64, a2: u64, a3: u64) -> u64 {
    let ret: u64;
    unsafe {
        core::arch::asm!(
            "int 0x80",
            inout("rax") num => ret,
            in("rdi") a1,
            in("rsi") a2,
            in("rdx") a3,
            options(nostack, preserves_flags),
        );
    }
    ret
}

pub fn sys_exit(code: u64) -> ! {
    syscall(0, code, 0, 0);
    loop {}
}

pub fn sys_write(buf: &[u8]) -> u64 {
    syscall(1, buf.as_ptr() as u64, buf.len() as u64, 0)
}

pub fn sys_sleep(ticks: u64) -> u64 {
    syscall(2, ticks, 0, 0)
}

pub fn sys_getpid() -> u64 {
    syscall(3, 0, 0, 0)
}

pub fn sys_yield() -> u64 {
    syscall(4, 0, 0, 0)
}

/// Read one raw PS/2 set-1 scancode byte via syscall 5 (R-7 kernel
/// side; R5-2 readkey program side, restored from the unmerged
/// round-5 branch). Returns the byte (0..=255) or u64::MAX when the
/// kernel ring buffer is empty; non-blocking, caller polls/yields.
/// Since R-FP2 the kernel fans scancodes into a dedicated readkey
/// ring, so reads here never consume the console's copy.
pub fn sys_read_key() -> u64 {
    syscall(5, 0, 0, 0)
}

/// One page. The kernel's write arm refuses anything larger instead of
/// truncating, so a caller that wants to emit more must split.
pub const WRITE_CAP: usize = 4096;

/// Write every byte, splitting at `WRITE_CAP`.
///
/// Returns the number of bytes the kernel confirmed. A refusal (0) or a short
/// write stops the loop and is reported honestly through the return value --
/// this never pretends a dropped tail was written.
pub fn sys_write_all(mut buf: &[u8]) -> usize {
    let mut done = 0usize;
    while !buf.is_empty() {
        let n = if buf.len() > WRITE_CAP { WRITE_CAP } else { buf.len() };
        let r = sys_write(&buf[..n]) as usize;
        if r == 0 {
            break;
        }
        done += r;
        buf = &buf[r..];
    }
    done
}

/// Print an unsigned decimal. No formatting machinery in userspace.
pub fn print_u64(mut n: u64) {
    let mut buf = [0u8; 20];
    let mut i = 20;
    if n == 0 {
        sys_write(b"0");
        return;
    }
    while n > 0 {
        i -= 1;
        buf[i] = b'0' + (n % 10) as u8;
        n /= 10;
    }
    sys_write(&buf[i..]);
}

/// Print 16 lowercase hex digits, no prefix. Fixed width so two values can be
/// compared by eye in a boot log.
pub fn print_hex(mut n: u64) {
    let digits = b"0123456789abcdef";
    let mut buf = [0u8; 16];
    let mut i = 16;
    while i > 0 {
        i -= 1;
        buf[i] = digits[(n & 0xF) as usize];
        n >>= 4;
    }
    sys_write(&buf);
}

/// Print a signed decimal; `i64::MIN` is handled without overflowing.
pub fn print_i64(n: i64) {
    if n < 0 {
        sys_write(b"-");
        print_u64((n as i128).unsigned_abs() as u64);
    } else {
        print_u64(n as u64);
    }
}

pub fn sys_bad() -> u64 {
    syscall(99, 0, 0, 0)
}

/// Call an arbitrary number, for the refusal drill (`badcall`). Exists so the
/// reserved-range edges can be exercised without hand-writing asm in the bin.
pub fn sys_bad_n(number: u64) -> u64 {
    syscall(number, 0, 0, 0)
}
