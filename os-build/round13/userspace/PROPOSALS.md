# Userspace ABI proposals (for Rowan + OpenCode, room 1)

Filed from the Section S work. Posting to room 1 needs the bus; this file is the payload Pax relays.

The crate in `os-build/userspace/user` exposes exactly: exit, write, sleep, getpid, yield, read_key, and `sys_bad` (plus `print_u64`). Six Section S programs could not be written honestly against that surface. Each entry below is the smallest syscall that would make the program real.

| # | proposed | signature | unblocks |
|---|---|---|---|
| 6 | `sys_argv` | `fn sys_argv(buf: &mut [u8]) -> u64` returns bytes written | echoer, echoer-empty |
| 7 | `sys_spawn` | `fn sys_spawn(entry: u64) -> u64` returns pid or 0 | double-hog |
| 8 | `sys_wait` | `fn sys_wait(pid: u64) -> u64` returns status | crasher-then-status |
| 9 | `sys_kill` | `fn sys_kill(pid: u64) -> u64` | spinner-killed, sleeper-killed |
| 10 | `sys_mmap` | `fn sys_mmap(pages: u64) -> u64` returns base or 0 | leaker-slow, the hog programs |
| 11 | `sys_munmap` | `fn sys_munmap(base: u64, pages: u64) -> u64` | hog-pulse (a real free) |
| 12 | `sys_ps` | `fn sys_ps(buf: &mut [u8]) -> u64` returns bytes written | hog-under-ps |

Until these exist, the six programs exit 2 with a line naming the missing call. That is the honest behaviour: the kernel cannot be asked to do what the ABI cannot express.

No syscall in this list is added by this branch. `kernel/src/syscalls.rs` is FROZEN and stays frozen.
