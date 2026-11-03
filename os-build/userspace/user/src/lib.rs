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

/// Send one message via syscall 6 (K4 IPC, design §6). `dest` is
/// the peer's fixed spawn-order id from the gate build's loader
/// table; `msg` is 1..=64 bytes. Returns 0 on success,
/// `u64::MAX` on any refusal (dead destination, unmapped buffer,
/// length out of range, full box).
pub fn sys_ipc_send(dest: u64, msg: &[u8]) -> u64 {
    syscall(6, dest, msg.as_ptr() as u64, msg.len() as u64)
}

/// Receive one message via syscall 7 (K4 IPC, design §6). `buf`
/// must hold at least 72 bytes (8-byte sender header + up to 64
/// payload). Returns the total bytes copied (9..=72) on success,
/// `u64::MAX` when the box is empty or the call is refused. The
/// caller polls, yielding between polls, never spinning.
pub fn sys_ipc_recv(buf: &mut [u8]) -> u64 {
    syscall(7, buf.as_ptr() as u64, buf.len() as u64, 0)
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

pub fn sys_bad() -> u64 {
    syscall(99, 0, 0, 0)
}

/// Call an arbitrary number, for the refusal drill (`badcall`). Exists so the
/// reserved-range edges can be exercised without hand-writing asm in the bin.
pub fn sys_bad_n(number: u64) -> u64 {
    syscall(number, 0, 0, 0)
}
