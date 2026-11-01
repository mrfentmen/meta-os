# Meta OS scoreboard (Milo's duty, ML-L2-03)

One entry per layer of the seven-layer scheme (`os-build/LAYERS.md`:
L1 Boot, L2 Kernel core, L3 Drivers, L4 System services, L5 Agent
runtime, L6 Shell and apps, L7 Programs). File names, task IDs, and
branch names keep the old digits as stable identifiers; only the layer
numbers in prose follow the 2026-11-01 renumber.

Rules, from the work order: the scoreboard never rounds up. A branch
claim is not an entry until the artifact is checked. Status words are
honest: DESIGNED / DRAFT / WRITTEN / GATED / MERGED / NOT STARTED, and
"standalone rustc clean" is never merged into "kernel-crate compile"
or "booted". Updated on every gate-1 verdict and every Pax merge.
Merges go through Pax only; this branch never merges itself.

## L1 — Boot (Rowan)

- Status: WRITTEN, NOT BOOT-PROVEN.
- Evidence: `kernel/src/main.rs` still K1-only with the proof string
  intact on main (merge 6c29370 left it untouched); K1 README build/boot
  steps on main (1506731); x86_64-unknown-none cargo config on main
  (02ff74c).
- Unverified: no K1 boot log exists anywhere; no QEMU run; no
  `kernel/Cargo.lock` on main. R5 wiring stays blocked on exactly this.

## L2 — Kernel core (Rowan)

- Status: PARTIAL — merged pieces unwired, nothing booted.
- Evidence: K2 framebuffer console (`kernel/src/framebuffer.rs`,
  576 lines) merged 6c29370, Milo gate-1 GREEN (standalone rustc
  1.99.1 clean, 0 warnings, NOT wired into main.rs, NOT a
  kernel-crate compile or boot verdict). K4 memory module
  (`kernel/src/memory.rs`, 979 lines: bitmap frame allocator,
  page-table mapper, heap) on `rowan/kernel` @ a6b6ca9, Milo gate-1
  GREEN (same standalone-rustc caveat), queued with Pax, NOT merged.
- Unverified: kernel-crate compile, any boot, K5 draft (queued behind
  the K4 gate).

## L3 — Drivers (Rowan)

- Status: PARTIAL — one driver merged, unwired.
- Evidence: K3 interrupts (`kernel/src/interrupts.rs`, 493 lines:
  IDT, PIC remap/EOI, PIT channel 0, PS/2 keyboard ring buffer)
  merged 6c29370, Milo gate-1 GREEN (standalone rustc clean,
  core only, no alloc, NOT wired into main.rs).
- Unverified: kernel-crate compile, any boot, any further driver.

## L4 — System services, Goose (Buffy)

- Status: DESIGNED, NOT BUILT.
- Evidence: K6 service shape DESIGNED on main
  (`os-build/layer1/K6_SERVICE_SHAPE.md`, 91dbbf5; Goose facts
  verified against goose-mcp 1.1.0, syscall v0 draft, Q1/Q5/Q9 left
  OPEN). Work order expanded to 78 tasks on main (b4783d5, boss order
  2026-11-01 ~09:12).
- Unverified / absent: no `buffy/layer1-goose-services` branch on the
  remote yet, no Goose service source, no compile. Standing gap tasks
  in the work order wait on K6/Layer 3 landings.

## L5 — Agent runtime, Lobster (Milo)

- Status: DRAFT.
- Evidence: agent process model `os-build/layer2/AGENT_PROCESS_MODEL.md`
  on `milo/layer2-agent-process-model` @ da054e3 (identity, lifecycle,
  Layer 4-services-only capabilities, audit-trail records; Lobster
  section grounded in a live lobster-mcp 1.1.0 check on this VM).
  DESIGNED step (a) done.
- Unverified / pending: (b) Pax K6-shape review, (c) Hana shell-view
  confirm. Nothing here is built until K6 exists.

## L6 — Shell and apps, Lobster (Hana)

- Status: SPEC-ONLY, with fixes queued.
- Evidence: shell spec-only on `hana/os-shell` @ de0c385.
  `hana/ui-fix-list` @ 57bee07 gate-1 GREEN (npm 1879, zero regression
  vs main) and its fix content already in main in substance — the
  remaining step is Pax's merge call, not a re-gate. HN-077 Swift
  mirror merged 78f9a4f (Milo gate-1 GREEN: 2107 tests, 2044 pass,
  63 fail, 0 new failures, 3 mirror tests pass).
- Unverified: Swift compile itself is Mac-only, still owed. No shell
  runs against real OS state (none exists yet).

## L7 — Programs

- Status: NOT STARTED.
- Evidence: no work order, branch, or artifact on main or the remote
  as of this entry.
- Unverified: everything.

## Changelog

- 2026-11-01 ~09:13 EST (v0): scoreboard created on
  `milo/layer2-scoreboard` off main b4783d5. Entries grounded in
  checked artifacts only: main tree b4783d5, remote tips
  (`rowan/kernel` a6b6ca9, `hana/os-shell` de0c385,
  `hana/ui-fix-list` 57bee07, `milo/layer2-agent-process-model`
  da054e3, no `buffy/layer1-goose-services` branch), and Milo gate-1
  verdicts posted to room 1. FROZEN lanes (META OPUS, META MERCATUS,
  META NUMMUS, META ACTA) are not OS layers and do not appear here;
  their parked states stand.
