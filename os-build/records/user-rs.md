# `kernel/src/user.rs` — dispatch and loader record (B244)

Scope: `kernel/src/user.rs` only. The call-by-call contract is
`os-build/USERSPACE_ABI.md`; this record covers the file's structure, the
register plumbing, the ELF loader, and the refusals the ABI depends on.
Every claim cites a line range on `main`, 2026-11-02.

## The syscall handler

- `syscall_handler` is at `kernel/src/user.rs:84-134`; the dispatch `match`
  starts at `:90`. It is registered on vector 128 by
  `sched::start_demo_tasks` (`sched.rs:650-651`).
- The saved-register offsets are fixed constants at `user.rs:60-70`
  (`rax -24`, `rcx -32`, `rdx -40`, `rsi -48`, `rdi -56`) and are read
  through `saved` (`:72-74`); the return value is written back into the
  saved `rax` slot by `set_return` (`:76-78`).
- Calls 0-5 are served inline (`user.rs:91-125`): exit, write, sleep, pid,
  yield, read_key. Anything else prints `user bad syscall {n} refused` and
  returns `u64::MAX` (`:126-129`).
- `write` routes to `user_write` (`:136-150`): zero or more than 4096 bytes
  returns `0`; a range that is not fully mapped prints
  `user write: unmapped buffer refused` and returns `u64::MAX`; otherwise it
  prints the bytes and returns `len`. The mapping check is
  `mem::is_mapped_range` (`mem.rs:308-330`), which walks every covering page.
- `read_key` is a non-blocking getter over the keyboard ring
  (`interrupts.rs:350-358`), returning `u64::MAX` when empty.

## The loader

The three program images are embedded at build time
(`user.rs:20-25`, `include_bytes!(OUT_DIR/...)`). The userspace side has
only three stack slots: `NEXT_USTACK` (`:34`), `map_ustack` (`:37`), and
`take_ustack` refuses the fourth.

`load_elf` (`user.rs:271-387`) maps each PT_LOAD at its linked address with
fresh frames and W/R/X from `p_flags`, zeroes the BSS tail, and returns the
entry. It refuses, in this order:

| Refusal | Line |
|---|---|
| shorter than 64 bytes or not `\x7fELF` | `:277-279` |
| not `ET_EXEC`/`ET_DYN` | `:280-282` |
| not x86-64 (`e_machine != 62`) | `:286-288` |
| entry is zero | `:289-292` |
| missing program-header fields / `phentsize < 56` | `:293-301` |
| segment address overflow | `:322-325` |
| page already mapped | `:347-349` |
| out of frames | `:350` |

Static-PIE (`ET_DYN`) is accepted only because the loader maps at the linked
addresses, so relative relocations are identity (`:283-285`).

`enter_userspace` (`user.rs:389-419`) builds the `iretq` frame (user data
segments, `rflags 0x202`, user code, entry, stack) and never returns.
`run_elf` (`:421-471`) loads and enters, printing either the entry line or
`user {name} loader refused: {reason}`; a missing mapper exits the task
instead of pretending to run. `task_hello`, `task_sleeper`, `task_crasher`
are the three kernel-task entries (`:473-481`).

## What the boot logs show

- `user hello: entry 0x600000000000 head [...]`, `HELLO FROM USERSPACE`,
  `user exit code 0` — `os-build/logs/MERGED-boot-2.txt:33-35`.
- `user bad syscall 99 refused` — `MERGED-boot-2.txt:52-53`.
- `INT user page-fault ...: task killed` — `MERGED-boot-2.txt:45`.

These are the observed side of the ABI; the code above is the source side.

## Findings

1. `readkey` calls `sys_read_key` (`os-build/userspace/user/src/bin/readkey.rs:9`),
   and the checked-in wrapper now exists in `lib.rs` (`pub fn sys_read_key`);
   the earlier "missing wrapper" finding is closed on this tree. The remaining half is
   true: `kernel/build.rs` builds only hello/sleeper/crasher, so `readkey`
   is not in the boot image.
2. The ABI has only one error value, `u64::MAX`; an unmapped write and an
   unknown syscall are indistinguishable by return value alone. Stated in
   `USERSPACE_ABI.md`; recorded here as a design limit, not fixed.
3. A kernel-mode page fault has no halt policy (see
   `os-build/records/fault-path.md`); `user.rs` does not change that.
