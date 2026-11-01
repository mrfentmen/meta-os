# Redox OS — a Rust microkernel, years in, and what its structure teaches ours

Lane: Buffy, research and tools. Task B2 (Section H mirror, OS-110).
Written 2026-11-01. RESEARCH, nothing built or tested.

This is the closest system on the list to what we are building, so it gets the
most attention of the eight. It is also the only one whose structure we should
read before writing another line of kernel code.

## What it is

A Unix-like operating system written in Rust around a microkernel, under
active development since 2015. Not a research toy and not finished either: it
is pre-stable, runs on real hardware for many people, and has a coherent
architecture of its own rather than a Linux clone.

## The model, mechanically

- **Microkernel.** The kernel does scheduling, memory, and IPC. Drivers, the
  filesystem, and the network stack are userspace processes that talk to the
  kernel and to each other by messages.
- **A scheme based namespace.** Resources are addressed as
  `scheme:path`, so a file, a socket, a device and a display are all named the
  same way and opened the same way. There is no separate API per resource type.
- **relibc**, a C library written in Rust, so the userspace is Rust native
  rather than glibc with Rust on top.
- **RedoxFS** as its own filesystem, and `ion` as its shell.
- **Drivers in userspace** means a crashing driver is a dead process and a
  restart, not a dead machine.

## What it does better

1. **The kernel stays small**, and the boundary between kernel and services is
   drawn before the code exists, not after.
2. **A crash in a driver is survivable.** This is the structural argument for a
   microkernel and Redox demonstrates it in practice.
3. **The scheme namespace is genuinely better than paths** for a system with
   many kinds of resource, which an agent OS has.
4. **It proves a `no_std` Rust kernel is not a fantasy.** Years of it, with a
   working userland on top. When our K1 serial print lands, this is the proof
   that the road continues.
5. **Its honesty is instructive.** The project says pre-stable and means it.

## What it costs

1. **IPC is the tax.** Every driver operation is a message, so the fast paths
   are slower than a monolithic kernel's. Redox pays it and so would we.
2. **A decade in and still not daily-driver for most people.** That is the real
   number for a from-scratch OS by a small team, and it is worth reading twice
   before anybody promises a timeline.
3. **Its own C library means its own ecosystem gap.** Porting C software to
   relibc is ongoing work.
4. **Small contributor base**, so bus factor is low.

## One borrowable idea

**Name every resource the same way: `scheme:path`.**

For an agent first OS this is the single most borrowable idea on the whole
list. An agent does not want a different API for its memory, its tools, its bus
and its files. It wants one addressing scheme where a capability is opened by
name and then behaves like a stream. That is what makes a capability a
capability: the same verb (`open`, `read`, `write`, `call`) works on all of
them, and permissions attach to the name rather than to each API.

That reframes three of our design notes as one design:
- OS-120 agent memory, OS-121 tool registry, OS-123 the bus: three schemes, one
  namespace, `memory:`, `tool:`, `bus:`.
- OS-127 sandboxing: an agent's permissions are which scheme names it may open,
  which is a decision the OS can audit, unlike "the app checks a flag".
- OS-124 records: `record:` as an append-only scheme, so auditing is reading a
  stream, not querying an app.

**The structural lesson is the second one:** our KERNEL_SPEC already puts
services in Layer 1 and the kernel in Layer 0, which is a microkernel shape.
Redox shows what that costs (IPC everywhere) and what it buys (a small kernel
that keeps booting when a driver dies). That trade is worth stating in the
kernel spec's own words before K3, because a monolithic shortcut at K3 is much
easier than a course correction at K5.

## License position

- **Redox Kernel and core: MIT** (verified 2026-11-01, `LICENSE` in the repo,
  "Copyright (c) 2016 Redox OS Developers, MIT License"). **This is the one
  system on the list whose source code we could legally borrow from**, and we
  still should not copy it: KERNEL_SPEC rule 1 says the kernel is ours, and a
  copied kernel is not ours even when the license allows it.
- **Some userspace components differ per crate**, so MIT is the project's
  headline, not a guarantee for every file. Check a file's own header before
  reading it as a reference, and never copy at all.
- **`ion` and other pieces** carry their own licenses; do not assume MIT
  propagates.
- **Verdict: idea rich, code never. Read as architecture, write fresh.**

## Verdict for Meta OS

The scheme namespace goes into OS-120, OS-121 and OS-123 as one idea. The
driver-in-userspace boundary should be an explicit decision recorded before K3
lands, with its IPC cost written down. And the timeline honesty belongs at the
top of the OS build report: Redox has had years and is still pre-stable, and
our K1 is one serial line.
