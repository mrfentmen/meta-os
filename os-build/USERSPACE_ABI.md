# Userspace ABI — specced from the code (Bond lane 3, 2026-11-02)

Source of truth: `kernel/src/user.rs`. This document is read from
that file, not from an older plan. Where another document disagrees,
the disagreement is listed under **Findings** at the bottom; the code
wins and nothing here "fixes" the kernel.

Status words used here: **LIVE** (dispatched by `syscall_handler`),
**FROZEN** (present in the tree, deliberately not the ABI).

## The entry

- Vector 128 (`int 0x80`), DPL 3 so ring 3 may enter:
  `kernel/src/traps.rs:177-193` installs the gate at 0xEE; the other
  wired vectors stay ring-0 at 0x8E.
- The handler is registered once, before the demo tasks start:
  `kernel/src/sched.rs:650-662` (`register_handler(128, ...)`).
- The dispatch `match num` is at `kernel/src/user.rs:90`; its arms
  below are the only live syscall numbers. Anything not matched falls
  to the refusal arm.
- `trap_common` saves the nine scratch registers, then passes
  `rdi = vector`, `rsi = &InterruptFrame`, `rdx = error` to
  `dispatch_trampoline` (`kernel/src/traps.rs:75-126`).
- `syscall_handler` reads the caller's saved registers by fixed
  offsets below the frame pointer (`kernel/src/user.rs:60-80`):

| Saved register | Offset | Used as |
|---|---|---|
| `rax` | `-24` | syscall number, then return value |
| `rcx` | `-32` | not read by the handler |
| `rdx` | `-40` | not read by the handler (a3 is ignored) |
| `rsi` | `-48` | argument 2 (`a2`) |
| `rdi` | `-56` | argument 1 (`a1`) |

`set_return` writes the result back into the saved `rax`
(`kernel/src/user.rs:76-78`), so the value the user program sees in
`rax` after `int 0x80` is exactly what the handler stored.

## Register contract

```
rax = syscall number   (in)
rdi = a1               (in)
rsi = a2               (in)
rdx = a3               (in, ignored by every call today)
rax = return value     (out)
```

The userspace wrappers state the same contract in
`os-build/userspace/user/src/lib.rs:1-19` ("eax=num, rdi/rsi/rdx=args,
rax=return") and use `inout("rax") num => ret`.

## Calls — all LIVE

| # | name | args | returns |
|---|---|---|---|
| 0 | exit | RDI = code | never returns |
| 1 | write | RDI = buffer, RSI = length | bytes written, 0, or `u64::MAX` |
| 2 | sleep | RDI = ticks | 0 when the deadline has passed |
| 3 | pid | none | the current task id |
| 4 | yield | none | 0 |
| 5 | read_key | none | scancode `0..=255`, or `u64::MAX` when empty |
| other | refused | none | `u64::MAX` |

### 0 — exit

- Arguments: `a1` = exit code.
- Behaviour: prints `user exit code {a1}` and never returns; the task
  is ended through `sched::exit_task()` (`kernel/src/user.rs:91-94`).
- Return: none. A caller must treat the call as `-> !`.
- Refusal: none. Any `u64` is accepted as an exit code.

### 1 — write

- Arguments: `a1` = buffer address, `a2` = byte length.
- Behaviour: prints the bytes to the kernel console
  (`kernel/src/user.rs:136-150`).
- Returns:
  - `len` on success (the whole range printed),
  - `0` when `len == 0` or `len > 4096` (`user.rs:137-139`),
  - `u64::MAX` when any page in the range is not mapped
    (`user.rs:140-143`), after printing
    `user write: unmapped buffer refused`.
- Notes: at most one page (4096 bytes) per call. Non-UTF-8 input is
  not an error: the kernel prints `[non-utf8 N bytes]` and still
  returns `len` (`user.rs:145-149`).

### 2 — sleep

- Arguments: `a1` = ticks (100 ticks ≈ 1 s; PIT is programmed at
  100 Hz in `kernel/src/main.rs:162`).
- Behaviour: records a wake tick and blocks the task; the scheduler
  wakes it when `interrupts::ticks()` passes the deadline
  (`kernel/src/sched.rs:154-172`, `:191-201`).
- Returns: `0` once the task is resumed (`user.rs:99-102`).
- Refusal: none; a huge value saturates at `u64::MAX`
  (`sched.rs:160`, `saturating_add`).

### 3 — getpid

- Arguments: none.
- Returns: the current task id as `u64`
  (`kernel/src/user.rs:103-105`, `sched::current_id()`).
- Honest edge: ids start at 1; `0` is the scheduler context, never a
  user task (`kernel/src/tasks.rs:110-111`, `sched.rs:42`).

### 4 — yield

- Arguments: none.
- Behaviour: rotates to the next ready task at the same priority
  (`kernel/src/sched.rs:141-152`).
- Returns: `0` when the caller runs again (`user.rs:106-109`).
- Refusal: none.

### 5 — read_key

- Arguments: none.
- Returns: the next raw PS/2 set-1 scancode as `0..=255`, or
  `u64::MAX` when the buffer is empty
  (`kernel/src/user.rs:110-124`).
- Notes, stated in the code comment and true to the implementation:
  - non-blocking; a caller polls, or sleeps/yields between polls;
  - release codes are included — this is not ASCII;
  - the console's keyboard ring is shared, so a byte read here is
    consumed and is not echoed (`kernel/src/interrupts.rs:350-358`);
  - a full buffer drops the newest scancode, never overwrites an
    unread one (`interrupts.rs:337-347`).

### any other number — refused

- Prints `user bad syscall {n} refused` and returns `u64::MAX`
  (`kernel/src/user.rs:126-129`).
- The userspace probe is syscall `99`
  (`os-build/userspace/user/src/lib.rs:60-62`), and `sleeper` checks
  the return is `u64::MAX` before printing `sleeper: bad call
  refused` (`os-build/userspace/user/src/bin/sleeper.rs:19-23`).
- This is the only "error code" the ABI has for a bad number. There
  is no negative-errno convention.

## Refusal table

| Call | Condition | Return | Observable line |
|---|---|---|---|
| write | `len == 0` | `0` | none |
| write | `len > 4096` | `0` | none |
| write | range not fully mapped | `u64::MAX` | `user write: unmapped buffer refused` |
| write | bytes are not UTF-8 | `len` (not a refusal) | `[non-utf8 N bytes]` |
| unknown n | any number not 0–5 | `u64::MAX` | `user bad syscall {n} refused` |

## Worked examples

The wrappers below are the real userspace source, not invented.

### Example 1 — write, then exit

```rust
// os-build/userspace/user/src/lib.rs:7-19
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

// lib.rs:26-28 — returns len on success
pub fn sys_write(buf: &[u8]) -> u64 {
    syscall(1, buf.as_ptr() as u64, buf.len() as u64, 0)
}

// lib.rs:21-24 — does not return
pub fn sys_exit(code: u64) -> ! {
    syscall(0, code, 0, 0);
    loop {}
}
```

Observed round trip, `os-build/logs/MERGED-boot-2.txt:33-35`:

```
user hello: entry 0x600000000000 head [50, 48, bf, bd, ...]
HELLO FROM USERSPACE
user exit code 0
```

`sys_write` puts the buffer pointer in `rdi` and the length in `rsi`;
`sys_exit(0)` puts `0` in `rdi`; the kernel prints `user exit code 0`
from `a1` and ends the task.

### Example 2 — read_key with an empty buffer

```rust
// os-build/userspace/user/src/bin/readkey.rs:20-24
loop {
    let r = sys_read_key();
    if r == u64::MAX {
        break;          // empty buffer, not a scancode
    }
    ...
}
```

The kernel's return path (`kernel/src/user.rs:118-124`) is:

```rust
set_return(base, match crate::interrupts::keyboard_read() {
    Some(scancode) => scancode as u64,
    None => u64::MAX,
});
```

Empty → `0xFFFF_FFFF_FFFF_FFFF`. Every valid scancode is `<= 255`,
so the sentinel cannot collide with a key.

### Example 3 — the bad-syscall drill

```rust
// lib.rs:60-62
pub fn sys_bad() -> u64 {
    syscall(99, 0, 0, 0)
}

// sleeper.rs:19-23
let r = sys_bad();
if r == u64::MAX {
    sys_write(b"sleeper: bad call refused\n");
}
```

Observed, `os-build/logs/MERGED-boot-2.txt:52-53`:

```
user bad syscall 99 refused
sleeper: bad call refused
```

Both lines matter: the first is the kernel's refusal, the second is
the user program observing `u64::MAX`, so the contract is proven from
both sides.

### Example 4 — exit

```rust
// os-build/userspace/user/src/lib.rs, `sys_exit`
pub fn sys_exit(code: u64) -> ! {
    syscall(0, code, 0, 0);
    loop {}
}
```

The kernel prints `user exit code {code}` and calls `sched::exit_task()`
(`kernel/src/user.rs:91-94`). The call never returns; the userspace wrapper
repeats that contract with `-> !`. Observed: `user exit code 0` in
`os-build/logs/MERGED-boot-2.txt:35`.

### Example 5 — sleep

```rust
// lib.rs, `sys_sleep`
pub fn sys_sleep(ticks: u64) -> u64 {
    syscall(2, ticks, 0, 0)
}
```

The handler stores `now.saturating_add(a1)` and blocks the task
(`kernel/src/sched.rs:154-172`); the scheduler wakes it when
`interrupts::ticks()` passes the deadline. The return is `0` when the task
resumes (`kernel/src/user.rs:99-102`). Observed: `C sleeping 200 ticks`
then `C awake` in `os-build/logs/K5-boot.txt` (per
`os-build/records/task-lifecycle.md`).

### Example 6 — pid

```rust
// lib.rs, `sys_getpid`
pub fn sys_getpid() -> u64 {
    syscall(3, 0, 0, 0)
}
```

Returns `sched::current_id().as_u64()` (`kernel/src/user.rs:103-105`). Ids
start at 1; `0` is the scheduler context and is never a user task
(`kernel/src/tasks.rs:110-140`). The shell's `ps` prints these ids from the
same scheduler table (`os-build/logs/K7-boot.txt`, per
`os-build/BOOT_LOG_INDEX.md`).

### Example 7 — yield

```rust
// lib.rs, `sys_yield`
pub fn sys_yield() -> u64 {
    syscall(4, 0, 0, 0)
}
```

The handler calls `sched::yield_task()` (`kernel/src/user.rs:106-109`),
which rotates to the next ready task (`kernel/src/sched.rs:141-152`) and
returns `0` when the caller runs again. Observed: the A/B alternation in
`os-build/logs/K5-boot.txt` (`BOOT_LOG_INDEX.md`).

## What is NOT in this ABI

- `kernel/src/syscalls.rs` (484 lines, generic `KernelServices`
  dispatch, self-labelled UNWIRED) is **FROZEN and NOT live**. Pax's
  ruling in `os-build/PAX_12H.md` F1 (`:118`, `:153`, `:233`) is that
  the inline `match` in `user.rs:90` is the authoritative ABI and
  `syscalls.rs` is a wire-or-delete decision, not a second ABI.
  Nothing should be written against it meanwhile.
- No `read`, `open`, `close`, `mmap`, `fork`, `exec`, or `wait`. The
  only memory the user program can touch is what the loader mapped
  (`kernel/src/user.rs:271-387`), and the only I/O is `write` and
  `read_key`.
- `a3` (`rdx`) is passed by the wrapper but no call reads it. A future
  call that needs three arguments must say so here first.
- The cap of 4096 bytes per `write` is a kernel limit, not a page-size
  accident: both the cap and the mapped-range check are explicit
  (`kernel/src/user.rs:137-143`; `kernel/src/mem.rs:308-330`).

## Findings (reported, not fixed)

1. **`readkey` is source-only; the missing wrapper is fixed.** The
   earlier "cannot build" half is closed: `lib.rs` now defines
   `sys_read_key` (`syscall(5, 0, 0, 0)`), and `readkey.rs` imports it.
   What remains is finding 2: the bin is not in `kernel/build.rs`'s
   list, so it does not ship in the boot image.
2. **`readkey` is not in the boot image.** `kernel/build.rs:12`
   builds `["hello", "sleeper", "crasher"]` only, and
   `kernel/src/user.rs:19-25` embeds those three ELFs. So syscall 5
   is kernel-live but has no shipped userspace program yet; the
   `readkey` bin is source only.
3. **The ABI has no explicit error convention beyond `u64::MAX`.**
   `write` returns `0` for an invalid length and `u64::MAX` for an
   unmapped buffer, while a bad syscall number also returns
   `u64::MAX`. A caller cannot distinguish "bad number" from
   "unmapped buffer" by the return value alone; the serial line is the
   only discriminator. Stated here so nobody invents an errno.
