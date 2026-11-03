# K3 demand paging — build step (build, not design)

**Assignment:** `os-build/ROWAN_NEXT_BLOCK.md` item 1–4, on Pax's
approval of `os-build/K3_DEMAND_PAGING_DESIGN.md` (bus, 2026-11-02:
"APPROVED to build", Q-D1 to be decided in writing in this step).
**Base:** origin/main at branch creation (see branch tip; parent
is the then-current main). **Status:** code, not proof. Nothing
here is booted: the gate pack in §5 runs through OpenCode 1's Mac
gate, read by Pax, exactly like every kernel step before it.
`syscalls.rs` is FROZEN (F1) and untouched; no syscall number is
consumed (the promised region is loader-registered, design §6).

## 1. Q-D1, decided in writing: (a) map in the handler

The fault handler allocates, zeroes, maps, invalidates, and
confirms, then returns normally so `trap_common` iretqs to the
faulting instruction. The safety argument, stated not asserted:

- The page-fault gate is a present 64-bit interrupt gate
  (`traps::install`, 0x8E), so IF is cleared on entry, and this
  handler never re-enables interrupts.
- Single CPU. The frame allocator is touched only from task
  context (the loader) and from this handler, never from IRQ
  context (the timer/keyboard handlers never allocate).
- There is therefore no reentrancy window in which a second
  allocation could interleave with this one. Option (b)
  (park-and-map in scheduler context) would need a trap-frame
  save/resume path that does not exist; inventing it for step 1
  would be a bigger, riskier change than the demand feature.

## 2. Q-D1's second confirmation, corrected against main

The design assumed the map must go into "the faulting task's own
page-table root, not the kernel's live CR3 mapping". Checked
against main, that distinction does not exist in this kernel:
there is ONE shared mapper root (`mem::MAPPER`), and
`enter_userspace` never loads a per-task CR3 — no per-task page
tables exist, whatever the design's §1 summary said. Mapping
through the shared mapper IS mapping into the faulting task's
tables, because all tasks share them. The isolation property
therefore rests on the per-task promised-region check (§3), not
on separate roots. Pax: if you want per-task roots before this
merges, that is a separate, larger step — this build does not
claim to have done it.

## 3. What was built

- `kernel/src/interrupts.rs`: `try_demand_map` + a
  `DemandOutcome` (NotDemand / Mapped / Failed) branch at the top
  of the ring-3 path in `page_fault_handler`. Class checks are
  design §3 verbatim: P=0, U/S=1, RSVD=0, I/D=0, faulting page
  inside the faulting task's promised region, ring 3. Mapped
  logs `INT user demand-fault addr 0x…: page mapped, retry` and
  returns (iretq retries). Failed logs a distinct
  `INT user demand-fault addr 0x… err 0x…: map failed, task
  killed` and exits the task — never half-mapped, never retried
  in a loop. NotDemand falls through to the unchanged
  `INT user page-fault …: task killed` line. A map is returned
  to the caller only after `translate` confirms present (§3.8).
- `kernel/src/user.rs`: the promised region. `DEMAND_PAGE`
  (`0x0000_7000_0000_0000`, one page) is far from every program
  base (the 0x6000… sequence), the user stacks (0x5000…), and
  the kernel's low mappings, so nothing else ever maps there.
  `task_demand` registers its own task id (it runs as that task
  before `run_elf` enters userspace) and `demand_region_for`
  answers only for that id. Ustack cap 4 → 5.
- `kernel/src/sched.rs`: `MAX_TASKS` 8 → 9; demand spawns
  LAST, after readkey, so every earlier id stays stable
  (console 7, readkey 8, demand 9). The R5-2 note said a 9th
  task needs a MAX_TASKS bump plus a heap review: the bump is
  here; the heap review is the Mac gate's (one more 16 KiB
  kernel stack box plus one more user stack — no heap-size
  constant changes in this branch).
- `kernel/src/memory.rs`: `Mapper::deallocate_frame`, used
  only when `map_page` fails after allocation, so a failed
  demand does not leak the leaf frame.
- `kernel/build.rs`: `demand` added to `BINS`.
- `os-build/userspace/user/src/bin/demand.rs`: the one demand
  program. Reads the promised page (faults by construction),
  proves zero-fill, writes `0x5A`, reads it back, then reads
  one MiB past the region and is killed. Its prints are the
  gate's checkpoints; the "must never print" lines are the
  failure detectors.

## 4. Pipeline note for the Mac build (OpenCode 1)

Build userspace first, as `kernel/build.rs` requires, with the
demand bin linked at base `0x640000000000` — the next slot
after hello/sleeper/crasher/readkey in the link-base sequence.
If readkey's base is not `0x630000000000` in the pipeline's
sed table, demand's base moves to the next free slot instead;
what must NOT change is `DEMAND_PAGE` (`0x7000…`), which is
outside every program base either way. The kernel check below
used stand-in ELF bytes for `include_bytes!` only (compile
check, not a boot); the real demand ELF must come from this
pipeline step, and a gate log without the demand-fault line
means the program never faulted, not that paging works.

## 5. Gate pack for OpenCode 1 (design §7, unchanged)

One boot, both behaviours, no panic, console task alive:

1. Demand leg: demand prints its touch line, the log shows
   the `page mapped, retry` line, demand prints zero-fill
   confirmed and writeback OK.
2. Containment leg, same boot: crasher faults outside any
   promised region, the log shows the existing `task killed`
   line, the other tasks continue.
3. Negative leg, same boot: demand touches outside its region
   and is killed (its `task killed` line), proving the region
   boundary is real.

Gate failure modes that must NOT be papered over: a demand
leg that passes only because the program never faulted; a boot
where crasher's kill line is missing; any panic or any other
task dying; a demand ELF built at a base that collides with
another program (the loader refuses the load — that is a
pipeline failure, not a gate pass).

## 6. Verification done on this branch (stated exactly)

- `cargo check --target x86_64-unknown-none` on the kernel
  crate, run on this VM (cargo 1.99.1, `RUSTC_BOOTSTRAP=1`
  for the crate's build-std config): clean, 24 warnings
  (2 duplicates) — the same count as Milo's main gate, zero
  new warnings from this branch's code. The kernel check used
  stand-in ELF bytes for `include_bytes!` (the real userspace
  ELFs are built by the Mac pipeline, §4), so this is a
  type/syntax check, not a boot claim.
- `cargo check --target x86_64-unknown-none --bins` on the
  userspace crate (hello + demand): clean.
- NOT done here, owed by the Mac lane: Milo gate-1 on this
  branch, the Mac build with real ELFs, and the OpenCode 1
  QEMU boot log for §5. Pax merges only on that gate log.
- Fences: `syscalls.rs` untouched, no reserved number used,
  K4 IPC / K5 / COW / swap untouched, no file under `os/os/`
  touched, nothing merged by this branch (branch only).
