# Section 20 — kernel-adjacent records, task map (B241-B252)

Every task in Section 20 of `os-build/BOND_TASKS.md` and where its
deliverable lives. Kernel source (`kernel/src/`) was read only; no kernel
file was edited by this lane.

| Task | Deliverable | Status |
|---|---|---|
| B241 memory.rs allocator record | `os-build/records/memory-allocator.md` | DONE (existing record, checked against `memory.rs`) |
| B242 tasks.rs lifecycle record | `os-build/records/task-lifecycle.md` | DONE (existing record, checked against `tasks.rs`) |
| B243 sched.rs policy record | `os-build/records/sched-rs.md` | DONE (new) |
| B244 user.rs dispatch record | `os-build/records/user-rs.md` | DONE (new) |
| B245 interrupts.rs + traps.rs fault path | `os-build/records/fault-path.md` | DONE (existing record, checked against both files) |
| B246 vga.rs + logo_frames.rs display | `os-build/records/display.md` | DONE (new) |
| B247 gdt.rs + main.rs boot sequence | `os-build/records/boot-sequence.md` | DONE (new) |
| B248 framebuffer.rs unwired inventory | `os-build/records/framebuffer.md` | DONE (new) |
| B249 syscalls.rs frozen inventory | `os-build/records/syscalls-frozen.md` | DONE (new) |
| B250 boot-log index | `os-build/BOOT_LOG_INDEX.md` | DONE (existing index; build-provenance section added) |
| B251 claim audit support pack | `os-build/records/claim-audit.md` | DONE (new) |
| B252 ABI worked examples, one per syscall | `os-build/USERSPACE_ABI.md` | DONE (examples 4-7 added for exit, sleep, pid, yield; 1-3 already covered write, read_key, bad number) |

## How the records divide

- `memory-allocator.md` — the bitmap frame allocator in `memory.rs`. The
  heap and mapper are described where they matter in `KERNEL_BEHAVIOUR.md`
  §2.2 and §2.3.
- `task-lifecycle.md` — states, identity, context, stack, and the spawn /
  switch / sleep / exit wiring. `sched-rs.md` goes deeper on the assembly
  and the parallel tables; it does not repeat the policy.
- `fault-path.md` — ring-0 and ring-3 faults, CR2, double-fault halt.
- `sched-rs.md`, `user-rs.md`, `display.md`, `boot-sequence.md`,
  `framebuffer.md`, `syscalls-frozen.md` — one file each, each citing only
  the source it names.
- `claim-audit.md` — the sentence-to-artifact map for `README.md`,
  `KERNEL_SPEC.md`, `os-build/SCOREBOARD.md`.

## Counts

Line counts are taken from the files themselves (`wc -l os-build/records/*.md`),
not estimated here. This record intentionally carries no guessed numbers.

## Findings raised by this section

1. `KERNEL_SPEC.md` K4 says 61660 frames; `K1-boot.txt` and
   `SCOREBOARD.md` say 127199. One of them is wrong; see
   `claim-audit.md` (CONFLICT).
2. `README.md`'s test table is stale against the 2026-11-02 run
   (Node 1933/1877/56 vs the measured 2048/1993/55).
3. `kernel/src/tasks.rs:1-30` still calls itself unwired and claims
   `Cargo.lock` is absent; both are false on this tree.
4. `os-build/gates.md:20` says K7 has no log while `K7-boot.txt` exists;
   the true statement is "no K7 banner".
5. `readkey`'s missing-wrapper finding is closed (`lib.rs` now defines
   `sys_read_key`); the program is still not in `kernel/build.rs`'s bin
   list, so it does not ship in the boot image.
