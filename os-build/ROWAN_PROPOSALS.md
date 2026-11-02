# Proposals to Rowan — kernel lane items Buffy found

Lane rule (`os-build/BUFFY_OS_KERNEL_TASKS.md`): `kernel/src/*.rs` is Rowan's write lane, and
a change Buffy believes the kernel needs goes on room 1 as a proposal. This is the paper copy
so it is not lost if the bus is down. Nothing here is edited into `kernel/src` by me.

## Disclosure first: kernel edits already landed

Before the lane file arrived, the boss instructed me directly to work on the OS and kernel. Under
that instruction I committed changes in `kernel/src` (commits `432ddc4`, `3bf0235`, `c0e981e`):

1. `main.rs` — bounded serial transmit wait (`SERIAL_TX_SPINS`), and `prove_timer()` printing the
   measured `K3 timer:` line.
2. `main.rs` — panic handler writes `PanicInfo` (message and `file:line`) to serial.
3. `interrupts.rs` — first-scancode line on IRQ1.
4. `interrupts.rs` — double-fault handler prints once then halts (it used to return and re-fault;
   the drill log was 3.3 MB of one line).
5. `traps.rs` — compile-time assertions on `InterruptFrame` layout, which the asm stub's offsets
   depend on.

All five are proven by boot logs (`K9-panic-detail.txt`, `K16-doublefault-fixed.txt`,
`K3-boot.txt`). Rowan should review them as his lane's code; revert or rewrite freely, with the
logs as the acceptance test.

## Proposals, highest value first

1. **Halt on a ring-0 page fault.** `page_fault_handler` (`interrupts.rs` 467-500) prints and
   returns for kernel-mode faults, which re-executes the faulting instruction and loops. The
   ring-3 branch kills the task correctly. Proposal: for `code_segment & 3 != 3`, print then halt,
   the same shape the double-fault handler now uses.
2. **An allocation syscall.** The userspace ABI is six calls and 6-15 are reserved. `hog`
   (`os-build/USERSPACE_PROGRAMS.md`) cannot be written without a way to ask for memory. Needs a
   Pax number ruling first, then a kernel implementation.
3. **IPC.** `talker`/`listener` are blocked on the absence of any inter-task channel
   (`KERNEL_BUILDOUT_SPEC.md` K4 designs one). Nothing in userspace can currently talk to
   anything but the console.
4. **Allocator self-tests**: allocate/free/allocate returns the same lowest frame; allocate all
   covered frames and assert the next is `None`; double-free refused without changing `used`;
   undersized bitmap clamps `covered`.
5. **Reap path**: `tasks.rs` implements reap/respawn and `sched.rs` never calls it, so exited
   slots are permanent and `MAX_TASKS` (8) fills. Wire the policy or state the 8-task ceiling in
   the user-facing docs. Related hard cap: `user.rs::take_ustack` allows three userspace
   programs and refuses the fourth by panicking, not by returning an error.
6. **Stale headers**: `interrupts.rs` and `tasks.rs` still say UNWIRED/UNCOMPILED/never booted
   (lines 1-40 of each). Both are wired and proven. Outdated headers on proven code are how the
   next reader is misled.
7. **Oversize `write` returns 0**, indistinguishable from a zero-length write (`user.rs`,
   `user_write`). Proposal: `u64::MAX` for oversize, 0 only for zero-length.
8. **Wire the new programs** — five changes, not one. The `BINS` line alone only stages the
   ELF; `user.rs` caps user stacks at three and spawns each program by name, so a fourth spawn
   panics in `run_elf` at `expect("user: no stack left")` rather than failing loudly. Full
   proposal with line numbers and the exact patch shape:
   `os-build/proposals/quitter-badcall-wiring.md`.

   `quitter` proves a deliberate nonzero exit (expect `quitter: exiting 7`, `user exit code 7`).
   `badcall` proves the reserved edges 6 and 15 refuse, not just 99. `writer` and `readkey` are
   probes and stay out of `BINS` — `writer` dumps a 4097-byte write attempt and `readkey` polls
   200000 times.

## Filed by

Buffy, 2026-11-02. Evidence for each item is in `os-build/USERSPACE_ABI.md`,
`os-build/records/fault-path.md`, `os-build/records/memory-allocator.md`,
`os-build/records/task-lifecycle.md`.
