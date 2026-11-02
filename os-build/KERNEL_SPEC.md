# Meta OS — Kernel Spec (boss's order 2026-11-01, supersedes all earlier kernel specs)

This spec REPLACES the previous KERNEL_SPEC.md (stock Debian kernel,
never substitute). That spec is dead as of the boss's direct order on
2026-11-01: Meta OS is an actual operating system with its own kernel,
written by us. The boss's words: he did not want programs on Debian, he
wanted an operating system. That was the whole point.

## Who it is for

The operating system is built for agents and for users. Agents are
first class citizens of this OS: they live in it, work in it, hold
memory, tools, and jobs in it, the same way users live in a desktop
OS. Users run it and direct it. That dual nature is the whole point
of Meta OS, and it settles design questions when the two pull apart:
an OS feature that only makes sense for humans, with no way for an
agent to live in it, is not finished.

## The shape: a layered operating system, three languages

Amended 2026-11-01 ~09:02 on the boss's word: SEVEN layers (the
first version of this section drew three). `os-build/LAYERS.md` is the
index. The K1-K6 milestones below are build steps, not layers.

- Layer 1, BOOT: the bootloader hands the machine to the kernel.
- Layer 2, the KERNEL CORE: Rust. Ours, from zero, no_std. Owns
  memory, scheduling, interrupts. Directory: `kernel/` in this repo.
- Layer 3, DRIVERS: Rust, in `kernel/` alongside the core. The
  modules that talk to hardware: framebuffer console, keyboard, timer.
- Layer 4, the SYSTEM SERVICES: Goose. Ours. (Goose is its own
  language, the boss's word 2026-11-01, not Go.) The daemons and
  services that run the machine on top of the kernel: service
  supervision, updater, networking.
- Layer 5, the AGENT RUNTIME: Lobster. Ours. Where agent processes
  live: identity, lifecycle, capabilities, audit records.
- Layer 6, the SHELL AND APPS: Lobster. Ours. The home surface and
  the app side that users and agents touch, on top of the services.
- Layer 7, PROGRAMS: the applications that run on the OS (next
  bullet). Programs are not the OS.
- Everything already in this repo (Imperium, Custos, Officina, the
  Python and JavaScript code, the Rust service crates) is PROGRAMS.
  Programs are applications that will run on the OS. They are not the
  OS and must never be described as the OS.
- The program lineup grows by the boss's order (2026-11-01): a
  cybersecurity and IT program joins it, same class as the other
  programs, built into the OS as a bundled first class program, with
  agents doing the security and IT work. Its name and the exact jobs
  its agents do are the boss's to define; nothing about its scope is
  settled until he says it.

## Standing rules

1. The kernel is ours. No stock kernel, no borrowed kernel, in the
   product. Debian exists in this project only as a development
   carrier: a machine to build and test on. It is never the product.
2. Rust code written in the sandbox is UNCOMPILED and UNVERIFIED
   until it builds on the boss's Mac and the boot proof below exists.
   Nobody claims a working kernel from source alone.
3. Proof standard for every kernel milestone: a QEMU boot log from
   OUR kernel binary showing the milestone's behavior. No log, not
   done.
4. Small steps, pushed often. Mac compile errors are the next task,
   ahead of new features, same rhythm as the service ports.
5. The old stock-kernel spec text is retained in git history only.
   Do not resurrect it.
6. NO MOCKS (boss's order 2026-11-01): nothing fake anywhere in the
   OS. No mocked networks or services, no fixture data in shipped
   surfaces, no stub presented as working. Test data lives inside
   tests only and never ships. What is not real is NOT BUILT,
   stated in those words. An honest empty state beats invented
   data, every time.

## Milestones

- K1 (started 2026-11-01): kernel crate skeleton in `kernel/`. Boots
  under the rust-osdev bootloader, prints `META OS KERNEL - alive (K1)`
  on the serial port, halts cleanly. Proof: QEMU serial log.
  **PROVEN 2026-11-02** — `os-build/logs/K1-boot.txt` line 2.
- K2: framebuffer console, the kernel draws its own text.
  **PROVEN 2026-11-02** — VGA capture, `os-build/logs/K2-boot.png`
  (196 of 2000 cells carrying glyphs). Corrected on the same date: the
  bootloader hands over no pixel framebuffer, so K2 is the VGA text
  console at 0xB8000, not a graphics-mode framebuffer. The name stays;
  the mechanism is recorded in `kernel/BUILD_LOG.md`.
- K3: interrupts, timer, keyboard input.
  **PROVEN 2026-11-02** — `K3 timer: 10 ticks` and a typed `status`
  command answered in `os-build/logs/K3-boot.txt`.
- K4: memory management, paging, heap.
  **PROVEN 2026-11-02** — memory map, 61660 frames, heap stress and
  `mem summary: K4 up` in `K1-boot.txt`.
- K5: tasks and scheduling, first context switch.
  **PROVEN 2026-11-02** — A/B/C rotation and a 200-tick sleep/wake in
  `K1-boot.txt`.
- K6: system calls, first userspace program, the Goose services layer
  gets its first process.
  **PARTIALLY PROVEN 2026-11-02** — userspace ELF load, `int 0x80`
  entry, `user exit code 0`, a refused bad syscall and a page fault that
  kills only the faulting task are all in `K1-boot.txt`. The last clause
  is NOT met: the Goose services layer has no process yet, and no service
  binary is loaded by the kernel. K6 stays open until it is.

The honest per-milestone matrix, including what is written but unproven,
lives in `os-build/KERNEL_STATUS.md`.

## Amendment 2026-11-02: the name "framebuffer" in K2

K2 was specified as a framebuffer console. Bootloader 0.9.35 hands the
kernel no pixel framebuffer (`os-build/research/framebuffer.md`), so K2
was built on the VGA text buffer at physical 0xB8000 through the
bootloader's physical-memory mapping. It draws text, it is proven, and
it cannot do graphics. Anyone reading "K2 done" should read it as "the
kernel has a console", not "the kernel has a graphics layer".

## Syscall table (F1 freeze, ruled by Pax 2026-11-01)

The syscall numbers are frozen. A number is never reallocated.
The authoritative implementation is the inline dispatch in
`kernel/src/user.rs` (`syscall_handler`, entry via vector 128,
number in the saved RAX, arguments in RDI/RSI):

- 0 — exit: end the calling task, with its exit code.
- 1 — write: write a validated user buffer (mapped range checked,
  one page per call) to the console.
- 2 — sleep: sleep the calling task for the given tick count.
- 3 — pid: return the calling task's id.
- 4 — yield: yield the processor to the scheduler.
- 5 — read_key: return the next keyboard byte to the caller.
  Ruled by F1; implementation in `user.rs` is R-lane work
  (RW4-1). Until it lands, 5 falls in the refusal arm below.
- 6–15 — reserved. Never allocated without a Pax ruling and a
  spec update in the same commit.
- Every other number is refused: the kernel logs
  `user bad syscall <n> refused`, returns `u64::MAX`, and the
  task carries on. There is no silent compatibility.

`kernel/src/syscalls.rs` is NOT this table. It carries an older
set of DRAFT numbers (from the K6 shape document) that conflicts
with the table above at every number from 2 on, it is not declared
in `main.rs`, and it is frozen untouched while the boss rules on
it (2026-11-02; Rowan's recommendation is on file at
`kernel/SYSCALLS_RS_RECOMMENDATION.md`). Nobody builds userspace
against the numbers in `syscalls.rs`.

## Milestone evidence rule (2026-11-02)

A milestone mark in this file cites a committed artifact by path. A mark
without one is not a mark. `PROVEN` means the named file exists in the
repo and contains the behavior; `PARTIAL` means some of the milestone's
clauses are evidenced and at least one is not, and the clause that is
missing is named. No milestone is marked done on the strength of a build.

## Honest scope

A kernel is a long road measured in milestones, not days. Each
milestone above is real, testable, and provable by its boot log.
Nothing in this spec promises a finished OS on a hackathon clock; it
promises the OS is actually being built, in the open, one proven
milestone at a time.
