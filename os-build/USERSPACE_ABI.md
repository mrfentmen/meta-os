# Userspace ABI — specced from the code (2026-11-02)

Authority: `kernel/src/user.rs`, the inline dispatch that actually runs. `kernel/src/syscalls.rs`
is not this ABI and is frozen by ruling; nothing here describes it.

Every claim below cites the code it comes from. Where the code and the frozen table in
`KERNEL_SPEC.md` disagree, that is a finding in the last section, not a quiet correction.

## Entry

- Vector **128** (`int 0x80`), installed DPL 3 by `traps::install`, so ring 3 may enter.
- The handler runs on the calling task's kernel stack (TSS `rsp0`), which is why scheduler
  calls inside it switch exactly like task-called ones (`user.rs`, handler comment).
- Number: saved **RAX**. Arguments: **RDI** (a1), **RSI** (a2). Return: written back into the
  saved RAX slot, so `iretq` hands it to the caller.
- The saved-register offsets are load-bearing: `SAVED_RAX = -24`, `SAVED_RCX = -32`,
  `SAVED_RDX = -40`, `SAVED_RSI = -48`, `SAVED_RDI = -56`, relative to the interrupt frame's
  `rip`. They are derived from `trap_common`'s push order and are now also asserted at compile
  time by the frame-layout block in `traps.rs`.

## Calls

| # | name | args | returns | notes |
|---|---|---|---|---|
| 0 | exit | RDI = code | never returns | prints `user exit code <n>`, task ends |
| 1 | write | RDI = buffer, RSI = length | `len` on success, `u64::MAX` on refusal, `0` for a rejected length | one page per call (4096 max); validates the whole range is mapped; non-UTF-8 prints `[non-utf8 N bytes]` but still returns `len` |
| 2 | sleep | RDI = ticks | 0 | blocks until `ticks()` passes the deadline; the tick is 100.0153 Hz, not exactly 100 |
| 3 | pid | — | task id | the scheduler's id, monotonic, never reused in K5 |
| 4 | yield | — | 0 | rotates to the next ready task |
| 5 | read_key | — | scancode `0..=255`, or `u64::MAX` when empty | raw PS/2 set-1 bytes, release codes included, not decoded. Consumes from the same ring the console reads, so a byte read here is not echoed. Non-blocking by design |
| 6-15 | reserved | — | `u64::MAX` | never allocated without a Pax ruling and a spec update in the same commit |
| other | refused | — | `u64::MAX` | prints `user bad syscall <n> refused` and the task carries on; no silent compatibility |

The refusal arm is the proven one: `user bad syscall 99 refused` appears in `K1-boot.txt`,
followed by the caller continuing and exiting 0.

## Findings — where the code does not match a clean reading of the spec

1. **Oversize `write` returns 0, not `u64::MAX`.** `user_write` begins
   `if len == 0 || len > 4096 { return 0; }`, so a 5000-byte write and a zero-length write are
   indistinguishable to the caller: both get 0, which is also the "nothing written" value.
   The table above records the code as it is. Proposed to Rowan: return `u64::MAX` for
   oversize and keep 0 for zero-length, so a caller can tell refusal from nothing-to-do.
2. **`read_key` cannot be woken.** It never blocks, so a caller that wants a key must poll or
   sleep. The spec for it (`KERNEL_SPEC.md` F1) says "return the next keyboard byte"; it does,
   and the empty case is a sentinel rather than a block. Stated so nobody builds a blocking
   reader against it.
3. **Write is capped at one page per call.** Longer output needs multiple calls; the code
   refuses rather than chunking, and the refusal value is finding 1.

## What this spec is not

- Not a promise of stability: numbers 0-5 are frozen by the F1 ruling, but the argument
  convention and return values are only as stable as the code, and code changes go through
  Rowan's lane.
- Not a description of `syscalls.rs`. That file's draft numbers conflict with this table from
  2 onward and are not reachable from userspace.
