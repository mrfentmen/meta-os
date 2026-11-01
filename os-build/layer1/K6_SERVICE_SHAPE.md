# Layer 1 — the K6 service shape (Pax)

Status: **DESIGNED** — written 2026-11-01 by Pax (Layer 1 pairing with
Buffy). Nothing here is built. KERNEL_SPEC.md K6 reads: "system calls,
first userspace program, the Goose services layer gets its first
process." This document fixes the kernel-side shape that first process
must fit, so Buffy's service contract (her B-L1-02) and the first
service source (her B-L1-03) are written against something concrete.
Items the Mac build must answer are marked OPEN and belong in
kernel/MAC_QUESTIONS.md — they are not guessed here.

## Goose facts this shape relies on (checked against goose-mcp 1.1.0)

- Entry point: `fn main() { }` in the global namespace of the root
  file is the entry point (reference, `main` entry). A runnable file
  doubles as a library.
- Build path: Goose compiles to C — `goose -o tour.c 01_tour.goose`,
  then a C compiler builds the program (sample 01_tour header). A
  service binary is therefore a C-compiled artifact the kernel loads;
  Goose itself never runs on the kernel.
- Error convention: several results with a trailing bool say whether
  the rest is meaningful (sample 01_tour). Service APIs in this layer
  follow the same convention instead of inventing an error type.
- The language is memory-safe with a flat data model and no GC
  (goose__overview, bundled aardappel/goose @ b781587) — services do
  not bring a runtime the kernel must host.

## The shape (v0 — every numbered item is a design decision, not code)

1. **A service is one compiled binary.** One Goose root file plus its
   imports, compiled to C, linked freestanding. The kernel loads it as
   a K5 task. OPEN: binary format and load address — depends on the
   resolved bootloader 0.9.x (Q1/Q5 in MAC_QUESTIONS).
2. **Start passes a BootInfo block.** The kernel hands the service a
   pointer to a boot info block at start: framebuffer info in the K2
   module's local `FramebufferInfo` shape, a memory-map summary, the
   PIT tick rate from the K3 module. OPEN: the register/location
   convention for the pointer — set at R5/K6 wiring time, not before.
3. **Syscall surface v0 (numbers DRAFT, six calls, no more):**
   0 exit, 1 write_serial, 2 write_console, 3 read_key (the K3 PS/2
   ring buffer), 4 ticks, 5 yield. OPEN: the transport (interrupt
   vector vs the `syscall` instruction) — it is the handler-ABI
   question already open as Q9; this draft asserts no answer.
4. **No service-to-service IPC at K6.** Services talk to the kernel
   only. Anything richer is a later design with its own document; it
   is not implied by this one.
5. **Failure is final at K6.** A service that faults or exits is
   logged to serial with its name and exit state, and its task ends.
   No restart policy exists at K6 — a restart policy is future work
   and will be designed, not assumed.
6. **First service: bootlog.** Prints the boot milestones carried in
   BootInfo to serial and console, then exits. It exercises BootInfo,
   both write calls, and exit — the smallest service that proves the
   shape end to end. Buffy writes its source as her B-L1-03.

## What Pax still owes on Layer 1

- Review Buffy's SERVICE_CONTRACT.md against this shape when it lands
  (her branch, gate-1, then Pax merges).
- The `services/` README once her MANIFEST.md lands, stating the
  layout this shape implies (one directory per service, source plus a
  README carrying its status word).
- The K6 wiring review with Rowan when R5 and the Mac answers exist.

Verified: the Goose claims above, against the wired goose-mcp 1.1.0.
Not verified: everything kernel-side — K6 is NOT BUILT, the K1 boot
proof is still outstanding, and Q1/Q5/Q9 remain open.
