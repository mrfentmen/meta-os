# K3 demand paging — design note (design only, no kernel code)

**Assignment:** `os-build/ROWAN_NEXT_BLOCK.md` (Pax, 2026-11-02), item 1.
**Base checked:** origin/main `6524eba` (2026-11-02; parent `1485ee35`, a Pax Bond-records merge only — no kernel or design impact). **Status:** design only.
Nothing here is compiled, built, or booted. Proof is the Mac + QEMU boot
log through OpenCode 1's gate, read by Pax — same standard as every
kernel step before it. `syscalls.rs` is FROZEN (F1) and is not touched
by this design; step 1 needs no new syscall (see §6).

## 1. Today: the fault path this changes

Today (`kernel/src/interrupts.rs`, `page_fault_handler`, vector 14):

- The CPU pushes an error code; the handler reads the fault address
  from CR2 (the CPU does not push it) and logs address + error code.
- A ring-3 fault (`code_segment & 3 == 3`) logs
  `INT user page-fault addr 0x… err 0x…: task killed` and calls
  `sched::exit_task()`, which marks the slot `Exited` and never
  resumes it. The handler never irets back into the faulting context.
- A ring-0 fault falls through to the exception print; there is no
  ring-0 recovery path, and this design adds none.

The buildout spec's summary of today is the same: boot map parsed,
bitmap frame allocator, 4-level page tables per task, a 512 KiB kernel
heap — and a fault kills the task, cleanly, every time. Demand paging
is the spec's first K3 step, ahead of copy-on-write and swap (swap
rides K5 storage, which stays design-only until K3 lands).

## 2. What changes, in one sentence

For a defined class of faults (§3), the handler maps a fresh zero-filled
page for the faulting task and returns to the faulting instruction,
which retries and completes — instead of killing the task. Every other
fault keeps exactly today's behaviour: log, kill only that task, the
rest of the fleet carries on.

## 3. Retryable vs fatal — the exact class boundary

Page-fault error-code bits (x86_64): bit 0 P (present), bit 1 W/R
(write), bit 2 U/S (user), bit 3 RSVD (reserved-bit violation),
bit 4 I/D (instruction fetch).

A fault is **retryable** only if ALL of these hold:

1. P = 0 — the page is not present. A present-page fault is a
   protection violation (write to read-only, NX, supervisor page),
   never a demand fault.
2. U/S = 1 — a userspace fault. Supervisor faults stay fatal.
3. RSVD = 0 — a reserved-bit violation is a table-corruption signal,
   never demand.
4. I/D = 0 — a data access. Step 1 promises data pages only; code
   pages are mapped at load time, so an instruction-fetch fault on an
   unmapped page stays fatal.
5. The faulting address, rounded down to its page, lies inside a
   **promised demand region registered for the faulting task**
   (§4). An unmapped address outside any promised region is a wild
   access, not a demand — even if P = 0 and U/S = 1.
6. The faulting context is ring 3 (same `code_segment & 3 == 3` test
   today's kill path uses).

**Fatal, unchanged from today, if any of the above fails** — plus
these two guards, which are what keep a demand fault from looping:

7. Allocation or mapping failure is fatal: if no usable frame is
   available, or `map_page` returns an error, the task is killed with
   a distinct log line (§7), never left half-mapped and never retried
   in a loop.
8. The handler returns to the faulting instruction only after the map
   succeeded AND a translate confirms the page is now present. A
   fault that recurs on the same address with P = 0 after a claimed
   success is therefore impossible by construction; if it ever
   happened, it would fall through the same checks and be killed,
   not retried forever, because the second fault's address would
   already be present (P = 1) or outside the promised region.

## 4. What backs a demanded page, and what a "promised region" is

- **Backing, step 1: zero-fill only.** The new page is a fresh frame
  from the existing usable-region bitmap allocator, zeroed by the
  kernel before it is mapped, mapped user + writable + not
  executable. File-backed pages are K5, not K3 step 1. Copy-on-write
  is a later K3 step, not this one: step-1 demand pages are private
  to one task, never shared, so no COW interaction exists yet.
- **Promised region:** a per-task record, registered at task
  load/spawn time in the loader, naming a base page and a length in
  pages for that task only. It is deliberately NOT a global rule
  ("any unmapped user address is demand"): a global rule would turn
  every wild pointer into a silent allocation and would destroy the
  isolation claim this design must preserve.
- **Scope, smallest-first:** exactly one userspace program gets a
  promised region in the build step — a single new demand program
  whose only demand access is one promised page. The existing fleet
  (hello, sleeper, crasher, readkey) gets no promised region, so
  their faults behave exactly as today, with no code-path change
  for them beyond the handler's new branch.

## 5. Machinery reused, and the one open implementation question

Reused, all already on main:

- `kernel/src/memory.rs`: `Mapper::map_page(virt, frame, flags, user)`,
  `Mapper::translate`, `FrameAllocator::allocate` (bitmap over usable
  regions only — a frame outside the usable regions is never handed
  out), and the page-table entry flags the mapper already uses.
- `kernel/src/mem.rs`: `invlpg(addr)` after every map (the mapper
  itself never touches the TLB), and the physical-memory-offset
  mapping used to zero the fresh frame before mapping it.
- `kernel/src/sched.rs`: `current_id()` for the faulting task, and
  `exit_task()` for the unchanged fatal path.

**Open question Q-D1 (to be settled in the build step, not assumed
here): map in the handler, or park-and-map in scheduler context?**
Today's handlers only print and count — `mem.rs` states "interrupts
never allocate". The fatal path already switches tasks out of trap
context (`exit_task`), but allocating, zeroing, and mapping inside
the fault handler is new. The build step must pick one of:

- (a) Map in the handler: single CPU, interrupts masked by the
  interrupt gate, so the static allocator is not re-entered — but
  that safety argument must be written down and proven by the gate
  log, not asserted here.
- (b) Park the faulting task, do the map in scheduler context, then
  resume it at the faulting instruction.

Either way the observable gate behaviour (§7) is the same, and the
build step must name which one it chose. A second build-time
confirmation, also not assumed here: the map must go into the
faulting task's own page-table root, not the kernel's live CR3
mapping, and the frame must be released (or provably not leaked)
if `map_page` fails after allocation.

## 6. Fences respected

- `syscalls.rs`: untouched (F1 FROZEN). No syscall numbers used:
  syscall dispatch today is 0–5 in `user.rs` (exit, write, sleep,
  getpid, yield, read_key); 6–15 are reserved, and step 1 consumes
  none of them, because the promised region is loader-registered,
  not requested by userspace. If a later step ever lets userspace
  request demand pages, that step needs its own design argument for
  a reserved number.
- K4 IPC, K5 storage/filesystem, COW, and swap: all out of scope
  here. K5 stays a design-only note until K3 lands, per the
  assignment.

## 7. Gate pack for OpenCode 1 (the boot log must show all of this)

One boot, both behaviours, no panic, console task alive throughout:

1. **Demand leg:** the demand program touches its promised page;
   the log shows a demand-map line (task id, fault address, mapped
   page — wording to mirror the existing `INT user page-fault …`
   style, e.g. `INT user demand-fault addr 0x…: page mapped, retry`);
   the program reads back the zero-filled page, writes a value,
   reads it back, and exits normally.
2. **Containment leg, same boot:** crasher faults outside any
   promised region; the log shows the existing `…: task killed`
   line; the other tasks continue. This is the claim boundary: a
   wild fault still kills only its task, after demand paging lands.
3. **Negative leg (same boot if cheap, otherwise the next gate
   boot):** the demand program touches an address outside its own
   promised region and is killed, proving the region boundary is
   real and not a global "map anything" rule.

Gate failure modes that must NOT be papered over: a demand leg that
passes only because the program never actually faulted (the log
must show the fault + map, not just a successful exit); a boot where
crasher's kill line is missing; any panic or any other task dying.

## 8. Build order after this design

1. This note (this branch) — Pax review.
2. Build step: promised-region record in the loader, handler branch
   per §3, Q-D1 decision written down, one demand program.
3. Gate pack (§7) through OpenCode 1's Mac gate; Pax merges only on
   that gate log.
4. Then K4 IPC design (`os-build/K4_IPC_DESIGN.md`), then its build.
   K5 stays design-only until K3 lands.
