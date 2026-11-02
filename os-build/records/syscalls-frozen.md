# `kernel/src/syscalls.rs` — frozen-file inventory (B249)

Scope: the drafted generic syscall layer that is **not** the live ABI. Read
only; this record never edits it. Every claim cites a line range on `main`,
2026-11-02.

## Status

- Header, in the file's own words: **"WRITTEN, NOT WIRED INTO `main.rs`,
  NOT A KERNEL-CRATE COMPILE, NOT A BOOT VERDICT, NOT A SYSCALL THAT HAS
  EVER RUN"** (`syscalls.rs:1-14`).
- It is absent from `main.rs:46-55`, so it is not in the kernel binary.
- It is frozen by Pax's F1 ruling (`os-build/PAX_12H.md:118`, `:153`,
  `:233`): the live ABI is the inline `match` in `user.rs:90`; this file is a
  wire-or-delete decision, not a second ABI
  (`KERNEL_SPEC.md`, "Syscall table (F1 freeze)").

## Draft numbers (they conflict with the live table)

Constants at `syscalls.rs:111-123`:

| Draft # | Name | Live # (F1) | Live name |
|---|---|---|---|
| 0 | `SYS_EXIT` | 0 | exit |
| 1 | `SYS_WRITE_SERIAL` | 1 | write |
| 2 | `SYS_WRITE_CONSOLE` | 2 | sleep |
| 3 | `SYS_READ_KEY` | 3 | pid |
| 4 | `SYS_TICKS` | 4 | yield |
| 5 | `SYS_YIELD` | 5 | read_key |

Only number 0 agrees. This is why nothing may be built against this file:
two different meanings for 1-5 is the exact merge hazard F1 closed.

## Public surface

| Item | Where | Purpose |
|---|---|---|
| six `SYS_*` constants, `NUM_SYSCALLS` | `syscalls.rs:111-123` | draft numbering |
| `MAX_WRITE_BYTES = 4096` | `:129-132` | one-page write cap |
| `NO_KEY = u64::MAX` | `:134-137` | empty-ring sentinel |
| `KernelServices` trait | `:146-160` | device side: serial/console write, key read, ticks |
| `FaultReason` | `:164-176` | `UnknownSyscall(u64)`, `WriteTooLong(usize)` |
| `Outcome` | `:178-195` | `Return`, `Yield`, `Exit { code }`, `Fault { reason }` |
| `dispatch` | `:197-250` | generic match; unknown number faults, oversize write faults |
| `EndState` / `ServiceRecord` | types immediately before `record_end` (`:263`) | final record for a service end |
| `record_end` | `:263-...` | `Some` for Exit/Fault, `None` for Return/Yield |
| `PixelFormatMirror`, `BootFramebuffer` | `:280-338` | start-block framebuffer geometry, mirrored |
| `BootInfoError` | `:340-360` | geometry/format/overflow/tick-rate/milestone refusals |
| `BootMilestone` | around `:400` | id + text for the bootlog service |
| `BootInfoBlock` | around `:420` | framebuffer + usable memory + tick rate + milestones |
| `StartError` | around `:445` | zero entry / zero stack / misaligned stack / zero boot info |
| `UserTaskStart` | around `:465` | task id, entry, stack top, boot-info address |

Everything above is **unused by the kernel today**. The types are a design
for the R5/K6 wiring, and the file says so.

## Refusal behaviour (as drafted)

- `dispatch`: a number outside 0-5 returns
  `Outcome::Fault { FaultReason::UnknownSyscall(n) }` (`:245-249`).
- A write longer than `MAX_WRITE_BYTES` returns
  `Outcome::Fault { FaultReason::WriteTooLong(len) }` (`:210-216`,
  `:225-230`).
- A short device write is reported as the real count, not padded
  (`:211-214`, `:226-229`).
- `BootFramebuffer::validate` refuses zero geometry, stride < width, an
  unsupported format/bytes-per-pixel pair, integer overflow, and a buffer
  shorter than the frame (`:344-368`).
- `BootInfoBlock::validate` refuses tick rate 0 and empty milestone text
  (`:434-444`).
- `UserTaskStart::validate` refuses zero entry, zero stack top, a stack top
  not 16-byte aligned, and zero boot-info address (`:470-484`).

## Findings

1. The draft table and the live table disagree at numbers 1-5. Documented
   here so no one "fixes" one to match the other without a Pax ruling.
2. The file is dead code by the repo's own dead-code count (484 lines). It is
   frozen, not deleted, and this record is an inventory, not a proposal.
3. `Outcome::Fault` is final; there is no retry convention. That matches the
   live ABI's single `u64::MAX` refusal value only in spirit, not in shape.
