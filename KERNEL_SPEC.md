# Meta OS — Kernel Spec (boss's order 2026-11-01, supersedes all earlier kernel specs)

This spec REPLACES the previous KERNEL_SPEC.md (stock Debian kernel,
never substitute). That spec is dead as of the boss's direct order on
2026-11-01: Meta OS is an actual operating system with its own kernel,
written by us. The boss's words: he did not want programs on Debian, he
wanted an operating system. That was the whole point.

## The shape: a layered operating system, three languages

- Layer 0, the KERNEL: Rust. Ours, from zero, no_std. Boots the
  machine, owns memory, scheduling, interrupts, drivers. Directory:
  `kernel/` in this repo.
- Layer 1, the SYSTEM SERVICES: Goose. Ours. (Goose is its own
  language, the boss's word 2026-11-01, not Go.) The daemons and services
  that run the machine on top of the kernel: service supervision,
  updater, networking, the agent runtime host.
- Layer 2, the AGENT AND APP LAYER: Lobster. Ours. The scripting
  layer agents and applications live in, on top of the services.
- Everything already in this repo (Imperium, Custos, Officina, the
  Python and JavaScript code, the Rust service crates) is PROGRAMS.
  Programs are applications that will run on the OS. They are not the
  OS and must never be described as the OS.

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

## Milestones

- K1 (started 2026-11-01): kernel crate skeleton in `kernel/`. Boots
  under the rust-osdev bootloader, prints META OS KERNEL alive on the
  serial port, halts cleanly. Proof: QEMU serial log.
- K2: framebuffer console, the kernel draws its own text.
- K3: interrupts, timer, keyboard input.
- K4: memory management, paging, heap.
- K5: tasks and scheduling, first context switch.
- K6: system calls, first userspace program, the Goose services layer
  gets its first process.

## Honest scope

A kernel is a long road measured in milestones, not days. Each
milestone above is real, testable, and provable by its boot log.
Nothing in this spec promises a finished OS on a hackathon clock; it
promises the OS is actually being built, in the open, one proven
milestone at a time.
