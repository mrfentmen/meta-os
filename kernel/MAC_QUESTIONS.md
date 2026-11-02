# Mac build questions (R4) — exact API points for OpenCode / Mac build

Status: **QUESTIONS ONLY, UNCOMPILED, UNVERIFIED.** Written 2026-11-01
from `rowan/kernel` @ `fde1b05` (R1 review, kernel/REVIEW.md). This VM
has no Rust toolchain (`cargo`/`rustc` not installed), so nothing here
is answered from a build. Answers arrive as Mac build commits (a
committed `kernel/Cargo.lock`, a QEMU boot log) and are recorded in
follow-up commits — they are never filled in from memory or guesswork
in this file.

Standing context: Milo gate-1 GREEN (review-only) on R1 @ `fde1b05`
consumed 2026-11-01 (all 11 R1 assumptions verified against source).
**R2 is BLOCKED until Q1 is answered** — R2 as worded in
OS_BUILD_TASKS.md is written "against the bootloader version in the
lockfile", and no `kernel/Cargo.lock` exists yet (R1 A2). No R2 code
is written until then.

## Update 2026-11-01 ~08:21 EST — R2 drafted, Q1 hold superseded for drafting only

Boss layer order 2026-11-01 ~08:18 (Pax relay, room 1 index 498;
OS_BUILD_TASKS.md on main) assigns Rowan the R2/R3 modules unwired with
real behavior, parallel by layer, nobody stops. That order supersedes the
hold below ("no R2 code until Q1 is answered") for drafting purposes:
`kernel/src/framebuffer.rs` (K2 framebuffer console, UNWIRED, UNCOMPILED)
landed on `rowan/kernel` in the same commit as this note.

What did NOT change: `kernel/Cargo.lock` is still absent on main
(checked this run, main tip 992d7bf), so Q1 is still unanswered and Q5
(exact bootloader framebuffer accessor/type names) is still open. The R2
module therefore imports no bootloader type: its boundary types are
local (`FramebufferInfo`, `PixelFormat`), and the R5 wiring commit is the
thin adapter that answers Q5 against the resolved 0.9.x version. R5
still wires ONE module per commit, onto the proven tree only, after a K1
boot log exists. Nothing in the R2 commit claims a compile or a boot.

Also open at the Pax merge gate: license confirmation for the Terminus
16 glyph table embedded in `framebuffer.rs` (generated verbatim from
`Lat2-Terminus16.psf.gz`; see that file's header). Kernel merges go
through Pax personally until K2 lands, so this is gated, not assumed.

## Update 2026-11-01 ~08:28 EST — R3 drafted, Q9 opened

Boss layer order 2026-11-01 ~08:18 (same order as the R2 note above)
assigns Rowan the R2/R3 modules unwired with real behavior.
`kernel/src/interrupts.rs` (K3: IDT, PIC remap/EOI, PIT programming,
PS/2 keyboard ring buffer, handlers with real serial print behavior)
landed on `rowan/kernel` in the same commit as this note. UNWIRED into
`main.rs`, UNCOMPILED, no boot claim — same status as R2.

What did NOT change: `kernel/Cargo.lock` is still absent on main
(checked this run, main tip 89209d6), so Q1 is still unanswered and
Q6 (interrupt entry state) is still open. The R3 module therefore
imports no bootloader type and no `x86_64` crate type (that crate is
not in `kernel/Cargo.toml`): its IDT structures are local, defined
from the x86_64 long-mode gate layout, and it never asserts a Rust
function address into the IDT — a Rust `fn` is not a valid IDT entry
point (no `iretq` semantics), so the R5 wiring commit must supply
real asm trampoline addresses via `idt_set()`, under the trampoline
contract stated in the module header. R5 still wires ONE module per
commit, onto the proven tree only, after a K1 boot log exists.

Open at the Pax merge gate for R3: Q9 below (handler ABI +
assumed-device confirmation). Milo gate-1 on the R3 commit is invited
on the same review-only basis as R1/R2: source-level verification,
not a compile or boot verdict.

## Q1 — Resolved bootloader version + lockfile (BLOCKS R2)

`kernel/Cargo.toml` pins `bootloader` version `"0.9"` with feature
`map_physical_memory`; `kernel/src/main.rs` uses
`bootloader::entry_point!(kernel_main)` and takes
`&'static mut bootloader::BootInfo`.

Needed from the first Mac build commit:
- The committed `kernel/Cargo.lock` (or an explicit pinned version).
- The resolved bootloader version (exact `0.9.x`).
- Confirmation, at that resolved version, that the `entry_point!`
  macro, the `&'static mut BootInfo` entry signature, and the
  `map_physical_memory` feature name all exist unchanged.

Why: R1 A1/A2. If the macro or signature differs at the resolved
version, the fix is a version pin or a small entry-point edit,
recorded in the same commit as the build error.

## Q2 — Toolchain pin (nightly + bootimage + QEMU)

`kernel/.cargo/config.toml` sets `[unstable] build-std`, which
requires a nightly Rust toolchain, and the runner is `bootimage`.
`kernel/README.md` names `cargo install bootimage` but no toolchain
pin and no QEMU install step.

Needed:
- Exact nightly toolchain used (`rustc --version` string with date).
- `bootimage` version installed.
- QEMU version installed, and the install commands for all three.

Why: R1 A9. Without the pin, the next builder cannot reproduce the
build that produced the lockfile in Q1.

## Q3 — K1 proof capture (exact invocation + log location)

Needed:
- The exact QEMU command line used for the K1 boot.
- The exact serial-capture setup (serial to stdio, or to a file —
  which one, and the file path).
- The committed path of the QEMU serial log that constitutes the K1
  proof.

Why: R1 A3/A4. The code assumes a 16550 UART at `0x3F8` with no
presence check, and `serial_write_str` busy-waits on the transmitter
bit with no timeout — so an empty log proves nothing by itself, and
a hang and a crashed-before-print kernel look identical. The capture
setup must be stated before any "it printed nothing" result is
triaged as a boot failure.

## Q4 — Canonical proof string (gate-blocking for M1)

Code and `kernel/README.md` print/expect
`META OS KERNEL - alive (K1)`. KERNEL_SPEC.md says the kernel
"prints META OS KERNEL alive on the serial port" — no dash, no
`(K1)`.

Needed: a Pax/boss ruling, or a spec edit, naming the one canonical
string. Milo's M1 gate lines (exact boot-log lines per milestone)
cannot be written until this is settled.

Why: R1 A8. Until then, any "K1 proven" claim must quote the exact
line it matched.

## Q5 — K2 framebuffer API surface (needed before R2 code, after Q1)

Needed, at the Q1-resolved bootloader version, the exact answers to:
- How does K2 obtain the framebuffer from `BootInfo` — exact
  accessor and type names?
- What is the pixel-format info struct and its exact field names
  (format, stride, dimensions, buffer access)?
- Does the bootloader require an opt-in (config flag, feature, or
  mapping) for framebuffer support, and if so, what exactly?

This question asks for exact names; it does not assert them. R2 code
is written only against the answered names.

## Q6 — K3 interrupt entry state

Needed, at kernel_main entry under the Q1-resolved bootloader:
- Are interrupts enabled or disabled on entry?
- Does the bootloader leave an IDT in place, or none?
- What interrupt state must K3's IDT setup assume on entry?

Why: R1 A7. The K1 code neither enables nor disables interrupts and
never issues `hlt`; K3 must define its entry state explicitly
instead of inheriting whatever the bootloader left.

## Q7 — Panic path / init order (K1 debugging)

The panic handler calls `serial_write_str` unconditionally and drops
the panic info (no file, line, or message). A panic before
`serial_init()` in `kernel_main` prints at whatever the UART reset
state happens to be, or hangs per A4.

Needed: confirmation that the Mac build keeps the current
`kernel_main` order (serial_init first, then print), or, if any fix
commit changes the order, that the change is recorded in that commit.

Why: R1 A5. Until init order is guaranteed, panic output is
near-useless for debugging the Mac build.

## Q8 — NO MOCKS rule (KERNEL_SPEC.md rule 6, Pax room-1 2026-11-01)

Nothing fake anywhere in the OS: no mocked networks or services, no
fixture data in shipped surfaces, no stub presented as working. Test
data lives inside tests only and never ships.

Needed: confirmation at Milo gate that the K2 module, when written,
drives the real framebuffer (Q5) and stays unwired into `main.rs`
until a boot log proves it, per OS_BUILD_TASKS.md R5 (wire ONE module
per commit, onto the proven tree only).

## Q9 — K3 handler ABI + assumed devices (needed before R3 wiring, after Q1)

`kernel/src/interrupts.rs` defines the IDT layout, the PIC/PIT/
keyboard port map, and handlers with real serial print behavior, but
deliberately installs no handler address into the IDT: a Rust `fn`
cannot serve as an IDT entry point (it returns with `ret`, not
`iretq`, and does not build the interrupt frame).

Needed, at the Q1-resolved toolchain / QEMU setup:
- Handler ABI decision: `extern "x86-interrupt"` (nightly feature
  `abi_x86_interrupt`) with handler functions, or asm trampolines
  that build `InterruptFrame` and call `dispatch()` — which one the
  Mac build uses, and the exact trampoline source location if the
  second.
- Confirmation that the K1 QEMU target presents a dual 8259 PIC at
  0x20/0x21 + 0xA0/0xA1, a PIT channel 0 at 0x40/0x43 ticking at
  1,193,182 Hz, and a PS/2 keyboard at 0x60/0x64 — the three devices
  `interrupts.rs` programs. If any differs, the port map is wrong
  and the R5 commit must say so.
- Confirmation of the install sequence the module header documents
  (cli, PIC remap to 32/40, PIT rate, lidt, sti) against the
  bootloader's entry interrupt state (Q6).

Why: R3's `dispatch()` + `InterruptFrame` contract is written, but
the entry points that call it do not exist yet. Until Q9 is answered,
R3 stays unwired and no interrupt is claimed to work.

## Q10 — K4 memory wiring (needed before R5 wires memory.rs)

`kernel/src/memory.rs` (K4, drafted unwired) takes a plain
`MemoryMap` slice, a bitmap, a `TableMemory` implementation, and a
heap buffer. It asserts none of the bootloader names below; the R5
wiring commit must answer them from the Q1-resolved build, not from
this file.

Needed, at the Q1-resolved toolchain / bootloader version:
- Memory map source: which BootInfo accessor/field carries the
  physical memory map, and what its region-kind names are — in
  particular which kinds the R5 adapter may map to `RegionKind::Usable`
  (and which it must map to `Reserved`/`Other`, never allocated).
  The adapter must also state its rule for overlapping regions, if
  the map can report any.
- Physical-memory access for tables: how the R5 adapter implements
  `TableMemory` — how it obtains a writable view of a page-table
  frame at a physical address (the `map_physical_memory` feature's
  offset: a fixed value, or read from BootInfo, and the exact way
  the adapter reads it). `memory.rs` never guesses this address.
- Heap placement: which usable region the kernel heap buffer lives
  in, where it sits relative to the kernel image, and how that
  range is kept out of the frame allocator's hands (reserved region,
  allocator exclusion, or both — stated, not assumed).
- Root table: how R5 obtains the current top-level table's physical
  frame address for `Mapper::new` (register read vs BootInfo value,
  and the exact source). `memory.rs` takes the root as a parameter
  and never reads it from hardware.
- Translation-cache invalidation: what mechanism the Mac build uses
  after `Mapper::unmap_page` (the module documents that R5 must
  invalidate, and does not do it itself).

Why: K4's frame allocator, mapper, and heap are written, but none
of them can run until these five adapter points are answered. Until
then, K4 stays unwired and no mapped page or heap allocation is
claimed to work.

## Update 2026-11-01 ~09:18 EST — K5 drafted, Q11 opened

Boss layer order 2026-11-01 ~08:18 (same order as the R2 note above)
assigns Rowan the Layer 2 kernel-core modules unwired with real
behavior. `kernel/src/tasks.rs` (K5: task struct + scheduler
skeleton, written against what K4's draft exposes) landed on
`rowan/kernel` in the same commit as this note. UNWIRED into
`main.rs`, UNCOMPILED, no boot claim, no context switch claimed to
have run — same status as R2/R3/K4.

What did NOT change: `kernel/Cargo.lock` is still absent on main
(checked this run, live main tip), so Q1 is still unanswered and
Q11 below is still open. The K5 module therefore imports no
bootloader type, no `x86_64` crate type, and no K4 type (that
module is not wired either): its stack and entry addresses are
plain `u64` boundary values in K4's page units, and the R5 wiring
commit is the thin adapter that maps them onto K4's `VirtAddr`
and `FrameAllocator`. The module never asserts a Rust function as
a switch target — a Rust `fn` cannot switch stacks — so the R5
wiring commit must supply a real `asm` trampoline under the
contract stated in the module header. R5 still wires ONE module
per commit, onto the proven tree only, after a K1 boot log exists.

Open at the Pax merge gate for K5: Q11 below (context-switch ABI
+ initial stack frame + stack sourcing). Milo gate-1 on the K5
commit is invited on the same review-only basis as R1/R2/R3/K4:
source-level verification, not a compile, switch, or boot verdict.

## Q11 — Context-switch ABI, initial stack frame, stack sourcing (BLOCKS R5 wiring of K5)

`kernel/src/tasks.rs` records a `Context` (callee-saved registers
`rbx`, `rbp`, `r12`-`r15`, plus `rsp`, `rip`, `rflags`) and a
`Stack` range, and `Scheduler` makes pure state decisions. None of
that moves execution. The switch itself is R5's `asm` trampoline.

Needed, at the Q1-resolved toolchain / bootloader version:
- Switch ABI: the exact register save/restore order the trampoline
  must follow, which registers it must preserve beyond the
  callee-saved set (segment state, if any), and how `rflags` is
  handled across the switch (which bits the trampoline may set,
  which it must carry verbatim).
- Initial stack frame: the exact layout the trampoline builds for
  a first-run task (where the entry address sits, what return
  address a task that returns falls into — the exit path, since a
  task has no caller to return to — and the 16-byte alignment
  rule at entry, which `Context::initial` already enforces on the
  stack top).
- Stack sourcing: which K4 `FrameAllocator` frames back each task
  stack, how those frames are kept out of the heap buffer and out
  of other tasks' stacks, and what the R5 adapter does when the
  allocator is exhausted mid-spawn (spawn already returns `None`
  on no free slot; the frame-exhaustion answer must match that
  contract, not invent a fallback stack).
- Timer hookup: how the R5 wiring calls `Scheduler::on_timer_tick`
  from the K3 timer interrupt path (which handler, what runs at
  interrupt level vs deferred), and what the tick rate is, so a
  quantum in ticks means something measurable in a boot log.

Why: K5's scheduler decisions are written, but no task can run
until these four adapter points are answered. Until then, K5 stays
unwired and no context switch or scheduled task is claimed to work.

## Update 2026-11-01 ~09:35 EST — K6 drafted, Q12 opened

Boss layer order 2026-11-01 ~08:18 (same order as the R2 note above)
assigns Rowan the Layer 2 kernel-core modules unwired with real
behavior. `kernel/src/syscalls.rs` (K6: syscall dispatch for the six
v0 calls, first userspace process shape, start block, failure-final
end records, written against Pax's `os-build/layer1/K6_SERVICE_SHAPE.md`
DESIGNED shape and what the K2/K3/K4/K5 drafts expose) landed on
`rowan/kernel` in the same commit as this note. UNWIRED into
`main.rs`, UNCOMPILED, no boot claim, no trap claimed to have been
taken, no userspace program claimed to have run — same status as
R2/R3/K4/K5. Started after Milo gate-1 GREEN on K5 (`rowan/kernel` @
`4c48fab`, room 1 2026-11-01 ~09:28), the same queue rule K5 followed
after K4's gate; K4+K5 are now on main (tip `83e6c3a` this run).

What did NOT change: `kernel/Cargo.lock` is still absent on main
(checked this run, absent from the live main tree), there is still
no K1 boot log and no `os-build` branch, so Q1 is still unanswered
and Q12 below is still open. The K6 module therefore imports no
bootloader type, no `x86_64` crate type, and no K2/K3/K4/K5 type:
its syscall numbers are Pax's DRAFT numbers from the shape document
(six calls, no more), its framebuffer geometry mirrors K2's local
`FramebufferInfo` fields without importing them, and its trap entry,
privilege transition, user-buffer copy, binary format, and BootInfo
pointer convention are all left to the R5 wiring commit, which must
answer them from the Q1-resolved build, not from this file. R5 still
wires ONE module per commit, onto the proven tree only, after a K1
boot log exists.

Open at the Pax merge gate for K6: Q12 below (syscall transport +
privilege transition + user-copy rules + binary loading + start-block
convention). Milo gate-1 on the K6 commit is invited on the same
review-only basis as R1/R2/R3/K4/K5: source-level verification, not
a compile, trap, or boot verdict. Note for the gate: the shape
document's syscall numbers are DRAFT — if Pax revises them, this
module's constants change in a follow-up commit, not silently.

## Q12 — Syscall entry, privilege transition, user copy, binary loading (BLOCKS R5 wiring of K6)

`kernel/src/syscalls.rs` (K6, drafted unwired) defines the six-call
dispatch, the start block, and the failure-final end record. It
asserts none of the machine facts below; the R5 wiring commit must
answer them from the Q1-resolved build, not from this file.

Needed, at the Q1-resolved toolchain / bootloader version:
- Syscall transport: interrupt vector or the `syscall` instruction
  — which one the Mac build uses. This is the handler-ABI question
  already open as Q9, answered here for syscalls specifically: if an
  interrupt vector, which vector, and how the trap frame carries the
  syscall number, the scalar argument, and the user buffer address
  and length; if the `syscall` instruction, the `STAR`/`LSTAR`
  setup, the entry point's source location, and how the number and
  arguments arrive in registers.
- Privilege transition: how a service runs in userspace and returns
  to the kernel — code and data segment selectors for userspace,
  the kernel stack the trap switches to, how the user stack pointer
  is saved and restored, and how flags are handled across the
  transition (which bits the entry may set, which it must carry
  verbatim). `UserTaskStart` deliberately carries no privilege
  level, no selector, and no kernel-stack address until these are
  answered.
- User-buffer copy rules: how the R5 trap entry validates and
  copies the write buffer before calling `dispatch` — what address
  range counts as a valid user buffer against the K4 mappings, what
  happens on a bad user address (which `EndState` the service gets,
  and what is logged), and how writes longer than this module's
  4096-byte per-call cap are chunked (the module faults them; the
  chunking policy for a service that needs more is the wiring's
  answer, not an assumption here).
- Binary loading: how the Goose C-compiled freestanding service
  binary is loaded as a K5 task — its format, where its entry
  address comes from, which K4 `FrameAllocator` frames back its
  stack and how those frames are kept out of the heap buffer and
  out of other services' stacks, and the register or memory
  convention that carries the `BootInfoBlock` pointer at start
  (shape item 2, OPEN). `UserTaskStart` takes entry, stack top,
  and BootInfo address as plain values and never guesses them.
- Tick source: confirmation that syscall 4 reads the K3 `ticks()`
  counter, and the PIT rate actually programmed by `pit_set_hz`,
  so the `tick_rate_hz` the start block carries matches the rate
  the counter ticks at. A mismatched rate makes every tick count
  lie about time.
- Console instance: which K2 `FramebufferConsole` instance the
  `write_console` call drives, and how its writes interleave with
  the kernel's own console writes (one console, or a lock — stated,
  not assumed).
- Key semantics: confirmation that `read_key` returns raw K3
  scancode bytes with no decoding at K6, and that the `NO_KEY`
  empty-ring sentinel (`u64::MAX`) is returned to userspace
  unchanged rather than translated. Scancode decoding, if any, is
  a later layer's job, not K6's.
- Number stability: the six numbers in this module are Pax's DRAFT
  numbers from `os-build/layer1/K6_SERVICE_SHAPE.md` item 3. If
  Pax revises them, the module constants and this question are
  revised together in a follow-up commit; a service built against
  other numbers is not silently compatible.

Why: K6's dispatch, start block, and end records are written, but
no service can trap, run, or exit until these eight adapter points
are answered. Until then, K6 stays unwired and no syscall, no
userspace program, and no service exit is claimed to work.

## Update 2026-11-01 ~20:40 EST — Q12 partly answered, its premise moved

The merged tree no longer matches the frame Q12 was written
in: a live syscall path exists in `kernel/src/user.rs`, and
Pax's F1 ruling (2026-11-01) settles the number question.

- Number stability: ANSWERED, against this file's guess. The
  six numbers below were draft numbers for `syscalls.rs`; F1
  froze a different table (0 exit, 1 write, 2 sleep, 3 pid,
  4 yield, 5 read_key, 6–15 reserved), now recorded in
  `KERNEL_SPEC.md`. Do NOT revise the `syscalls.rs` constants
  to match: the module is frozen and the boss rules on it
  2026-11-02 (recommendation: `kernel/SYSCALLS_RS_RECOMMENDATION.md`).
- Syscall transport: answered in the live tree by source —
  `user.rs` registers its handler for vector 128; the trap
  frame carries the number (saved RAX) and arguments (RDI/RSI);
  the handler runs on the calling task's kernel stack
  (TSS.rsp0) and returns via `iretq`. Status: WRITTEN in
  source; the standing proof is the merged tree's boot logs,
  per the spec's proof rule.
- The remaining Q12 items (user-copy rules, binary loading,
  tick source, console instance, key semantics) now track the
  `user.rs` / `sched.rs` / `mem.rs` wiring that actually
  shipped, not the `syscalls.rs` dispatch. Two specifics
  changed meaning: syscall 4 in the live table is yield, not
  ticks; and `read_key` is F1 number 5 in `user.rs` (RW4-1
  work), not number 3 in `syscalls.rs`.

## Update 2026-11-01 ~21:05 EST — RW4-1 complete (R-8): console + read_key API points

R-1..R-7 are WRITTEN on `rowan/kernel-r1` (R-1 merged to main
1655d56 with the F1 table and the RW4-3/RW4-5 docs; R-2/R-3/R-4
and R-5/R-6 gate-1 GREEN per Milo bus notes; R-7 awaiting Milo
gate-1). All of it is WRITTEN, not compiled, on this VM (no
cargo/rustc/qemu here) — Mac gate-2 still owed, nothing below is
boot-proven. Exact points from `kernel/src` on this branch:

- Banner (R-1): `META OS 0.1 (K6)` at `kernel/src/main.rs:118`;
  the alive line `(K1)` is untouched. Milestone = last proven.
- Prompt (R-2): NONE, closed by Pax room-1 ruling (bus idx 514):
  NO-PROMPT STANDS. Hana HN4-1 verified no prompt exists in the
  frozen shell spec, and the old H2 `metaos> ` string was
  spec-only, never emitted, and is SUPERSEDED. The Mac build
  must not expect a prompt string; a prompt only arrives if Del
  orders one.
- Console input (`sched.rs` `console_task`, K3 ring buffer via
  `interrupts::keyboard_read`): backspace 0x0E erases the last
  buffered char and the screen cell; shift 0x2A/0x36 press and
  0xAA/0xB6 release, state only, no echo; `decode_scancode
  (scancode, shift)` shifts letters/digits; line buffer 80
  bytes, overlong lines print `line too long, truncated to 80`;
  an empty line prints nothing. No periodic uptime print: a
  quiet run stays quiet (R-4).
- Commands, exact output shapes on this branch:
  - `status`: `tasks {} ticks {} heap_free {}K`, then
    `STATUS tasks={} ticks={} heap_free_kb={}`
  - `help`: `commands: status help uptime mem ps`
  - `uptime`: `uptime {}s ticks {}` (seconds = ticks/100)
  - `mem`: `mem frames_free {} frames_total {} heap_free {}K
    heap_total {}K` (getters in `mem.rs`)
  - `ps`: one line per spawned task slot,
    `ps id {} state {:?} ticks_used {} prio {}`;
    `ticks_used` is current-run quantum usage — no lifetime CPU
    counter exists in `tasks.rs`, so none is claimed
  - unknown: `unknown command`, then the help listing re-listed
- Syscall 5 `read_key` (`user.rs`, vector 128 handler, number =
  saved RAX, args RDI/RSI): returns the next raw PS/2 set-1
  scancode byte (0..=255, release codes included, NOT decoded
  ASCII — decoding stays in the console task), or u64::MAX when
  the ring buffer is empty (non-blocking; a caller that wants
  to wait polls, or sleeps/yields between polls). It shares the
  console's K3 ring buffer: a byte read here is consumed and is
  not echoed by the console task. Unknown numbers print
  `user bad syscall {} refused` and return u64::MAX.
- Q12 remainder update: key semantics — ANSWERED in source
  (read_key + console decode rules above). Console instance —
  the `sched.rs` console task is the only console, and it shares
  the K3 ring buffer with read_key. Tick source — the uptime
  command divides `interrupts::ticks()` by 100 for seconds; the
  hardware tick rate itself is still a Mac-boot-log question.
  Still open, unchanged: user-copy rules, binary loading (track
  the `user.rs` wiring, not the `syscalls.rs` dispatch).
- Known divergence, NOT resolved here: this branch's help
  listing (`status help uptime mem ps`) is longer than Hana's
  frozen HN4-1 listing (`status help`), which predates
  uptime/mem/ps. Pax accepted `status help uptime` at idx 514
  and the mem/ps listing was flagged at idx 516 awaiting his
  ruling. RW4-2 reconciles the listing; do not treat either
  listing as final until Pax rules.

## What this file is not

- Not a design doc: it asks, it does not decide.
- Not build evidence: no answer here counts as proven until a Mac
  build commit or a QEMU boot log shows it.
- Not a substitute for Q1: no R2 code follows from this file alone.
