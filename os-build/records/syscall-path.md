# Record — the syscall path, from the code

Scope: what actually happens on `int 0x80`, from the gate to the return. Files:
`kernel/src/traps.rs`, `kernel/src/interrupts.rs`, `kernel/src/user.rs`, `kernel/src/sched.rs`.
Function names are exact; line ranges are approximate where this week's changes moved them.

## Entry

1. `int 0x80` is vector 128. `traps::install` installs it with type/attr `0xEE` — present,
   DPL 3, interrupt gate — so ring 3 may use it while every other gate stays ring 0 (`0x8E`).
   It is installed separately from the exception/IRQ list, so a change to that list cannot
   silently drop the syscall gate.
2. `trap_128` pushes a dummy error code and the vector, then jumps to `trap_common`.
3. `trap_common` pushes nine scratch registers, then passes `(vector, &frame, error)` to
   `dispatch_trampoline`. The frame starts at `rip`, so the saved RAX/RDI/RSI sit at fixed
   negative offsets: `SAVED_RAX = -24`, `SAVED_RSI = -48`, `SAVED_RDI = -56` (`user.rs`).
   Those offsets are derived from the push order and are now asserted at compile time in
   `traps.rs`; before that assertion, a struct change would have handed the handler garbage.
4. `interrupts::dispatch` looks up the handler registered for 128 and calls
   `user::syscall_handler`.

## Dispatch

`syscall_handler` (`user.rs`) reads the number from saved RAX and two arguments from
RDI/RSI, then matches:

| # | arm | return |
|---|---|---|
| 0 | prints `user exit code N`, calls `sched::exit_task()` | never returns |
| 1 | `user_write(buf, len)` | length, 0, or `u64::MAX` (see below) |
| 2 | `sched::sleep_task(ticks)` | 0 |
| 3 | `sched::current_id().as_u64()` | task id |
| 4 | `sched::yield_task()` | 0 |
| 5 | `interrupts::keyboard_read()` | scancode `0..=255`, or `u64::MAX` |
| other | prints `user bad syscall N refused` | `u64::MAX` |

Returns are written into the saved RAX slot, so `iretq` hands them to the caller. The handler
runs on the calling task's own kernel stack (TSS `rsp0` was set on ring entry), which is why
calling the scheduler from inside it is the same as a task calling it: the switch saves the
task's context and resumes it later at the same place.

## `user_write`

- `len == 0` or `len > 4096` returns **0** without printing. Zero-length and oversize are
  therefore indistinguishable to the caller — finding 1 in `../USERSPACE_ABI.md`.
- The whole range must be mapped; otherwise it prints `user write: unmapped buffer refused`
  and returns `u64::MAX`.
- A mapped buffer is printed as UTF-8, or as `[non-utf8 N bytes]`, but the return is the
  length either way: the bytes were consumed.

## Findings

1. **Reserved numbers 6-15 are refused by the same arm as 99**, so the refusal is total, but
   nothing marks them as reserved in the reply — a caller gets `u64::MAX` and no reason.
2. **`read_key` cannot block.** A userspace reader must poll or sleep; a program written as a
   blocking reader will spin.
3. **The oversize write returns 0.** Proposed fix in `../ROWAN_PROPOSALS.md` item 7.
