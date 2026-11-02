# ROWAN — Layers 1–3 work order: boot, kernel core, drivers (Rust)

Renumbered 2026-11-01 ~09:02 on the boss's word: the OS has SEVEN layers (see `os-build/LAYERS.md`). This file's name and its task IDs keep the old digits as stable identifiers; only the layer numbers in the text changed.

The boss's order 2026-11-01 (~08:18): the OS build goes parallel by
layer. **Your layers are 1–3 — boot, the Rust kernel core, and the
drivers.** You write the
kernel code; OpenCode compiles it and QEMU-proves it on the boss's
Mac; Milo is gate-1; **Pax merges — no self-merge.** Branch:
`rowan/kernel` in `mrfentmen/meta-os`. Report to crew room 1 at every
stage boundary. Everyone's layer index: `os-build/LAYERS.md`.

## Landed (verified on main by Pax)

- K1 crate (`kernel/`): boots to serial print `META OS KERNEL - alive
  (K1)`. Status: **UNCOMPILED** — no QEMU boot log exists yet; the Mac
  build is OpenCode's lane and is still the #1 unblock.
- R1 review (`kernel/REVIEW.md`) and R4 questions
  (`kernel/MAC_QUESTIONS.md`) — on main.
- R2 framebuffer console + R3 interrupts — merged 2026-11-01
  (6c29370b), Milo gate-1 GREEN on both (standalone rustc clean),
  deliberately UNWIRED. The Terminus glyph-table license item is
  closed (`kernel/FONT_TABLE_LICENSE.md`).

## Tasks

- **RW-L0-01 — R5 wiring. BLOCKED.** Wire the Layer 3 drivers (R2
  framebuffer, R3 interrupts) into the Layer 2 kernel core in main.rs,
  one module per commit, only when BOTH exist: a K1 QEMU boot log
  from the Mac, and `kernel/Cargo.lock` committed by the Mac build
  (Q1). Until then the modules stay unwired and this task stays
  blocked — say so in those words when asked.
- **RW-L0-02 — K4 memory module, drafted unwired (Layer 2, kernel
  core).** Paging + heap in
  the R2/R3 pattern: real behavior, local boundary types, no
  bootloader API names asserted, honest status header. Milo gate-1,
  then Pax merges.
- **RW-L0-03 — K5 task module, drafted unwired (Layer 2, kernel
  core).** Task struct +
  scheduler skeleton the same way, written against what K4's draft
  exposes. Same gate + merge path.
- **RW-L0-04 — Keep MAC_QUESTIONS.md current.** Q1 (lockfile), Q5
  (bootloader accessors), Q9 (handler ABI) are open. Answers arrive
  only as Mac build artifacts (a committed lockfile, a boot log) —
  never fill an answer in from memory.

## Rules

1. **NO MOCKS** (KERNEL_SPEC rule 6). A module is code, not a running
   kernel, until the Mac boot log says otherwise.
2. Status words exactly: WRITTEN / COMPILED / VERIFIED / BLOCKED.
   Standalone rustc-clean is reported as exactly that.
3. Custos stays parked (boss's 08:18 order) — no Custos work in this
   lane until he re-opens it.
