# Syscalls, first five (OS-075) — the whole userspace contract for K6

## Numbers and calling convention

Transport: `int 0x80` (software interrupt, vector 128), gate DPL 3.
Chosen over `syscall`/`sysret` because the IDT machinery already
exists and is proven (Section C); `syscall` needs STAR/LSTAR/SFMASK
MSR setup plus a separate MSR entry path, which is deferred and
named as a follow-up, not silently skipped.

Registers (all saved by `trap_common`, so the handler can trust them):
`eax` = number, `rdi` = arg1, `rsi` = arg2, `rdx` = arg3.
Return value in `rax` (written into the saved slot, so `iretq`
restores it into the program's `rax`).

| # | Name | Args | Returns | Notes |
|---|---|---|---|---|
| 0 | exit | rdi = code | never | logs code, task to Exited |
| 1 | write | rdi = buf, rsi = len | bytes written | kernel validates range, max 4 KiB/call |
| 2 | sleep | rdi = ticks | 0 | blocks the task, timer wakes it |
| 3 | getpid | — | task id | |
| 4 | yield | — | 0 | rotate to next ready task |
| 99 | (bad) | — | -1 | any unknown number: refused + logged, never a crash |

## Ring transition (OS-076/079)

Kernel adds user code/data segments to its GDT (0x2B/0x33) and
enters with `iretq` (SS/RSP/RFLAGS/CS/RIP, RPL 3). Before entry it
sets TSS.rsp0 to the entering task's OWN kernel stack top, so a
`trap` from ring 3 lands on that stack: scheduler calls made from
inside the syscall handler then switch exactly like task-called
ones, and `iretq` returns to the program. No separate kernel stack,
no resume patching — one userspace task per CPU is the honest
scope (single CPU today).

## Loader (OS-078)

Static non-PIE ELFs (userspace crates set `relocation-model=static`;
PIE would need RELA self-relocation at load — refused scope for K6).
The loader maps every LOAD segment at its linked address (allocated
frames, W/R/X from `p_flags` (one RWX section per program: x86 flags are per-page, so per-segment flags are unenforceable on tightly packed binaries; W^X returns with userspace maturity), copies file bytes through the
physmap, zeroes the BSS tail, and jumps to `e_entry`. Anything with
overlapping/zero addresses is refused, not mapped.

## Limits, stated (OS-087 inputs)

- One userspace address space shape: fixed linked addresses.
- `write` validates the range is mapped and caps at one page.
- A userspace page fault kills THAT task (log + exit path) while
  the kernel and the console task continue — proven, not claimed.
- `syscall`/`sysret` fast path: future. VDSO: none. Signals: none.
