# Rowan Layer 0 — request for next tasks

From Rowan, 2026-11-01, branch `rowan/kernel`. Left here per del's
overnight order (2026-11-01 ~09:38 EST): if the Layer 0 queue empties,
Rowan does not stop — it asks Pax for more kernel/Layer 0 work, leaves
the request in the repo, and keeps verifying/hardening what exists.

## Queue state (verified against origin/main this run)

- K1–K6 are all merged to main. K6 landed via Pax's merge-everything
  run: `4bf2367` (kernel/src/syscalls.rs, 484 lines) and `cbe3e7d`
  (kernel/MAC_QUESTIONS.md +102, Q12) — both blobs byte-identical to
  `rowan/kernel @ b13a12c`, which Milo gate-1'd GREEN.
- R5 wiring stays BLOCKED on Mac-side items only: kernel/Cargo.lock
  plus a K1 boot log (MAC_QUESTIONS Q1/Q5/Q9–Q12). Nothing Rowan can
  do about those from this VM.
- No K7: the KERNEL_SPEC milestones end at K6, and none is invented.
- Custos stays PARKED per Pax's 08:18 OS BUILD ORDER (Rowan = Layer 0).
  No Custos block is resumed unless Pax assigns it.

## Ask

Pax (or del on waking): please scope Rowan's next Layer 0 block, or
confirm the hardening-only fallback stands until the Mac-side items
land.

## While waiting

Rowan keeps re-verifying/hardening K2–K6 (standalone rustc + rustfmt
+ host-harness re-checks; no new kernel code, no pushes except this
file) and owes del a test-ready list on waking: what is merged, what
he can run, and what only his Mac can prove.

This file is a note, not a kernel module: it changes no build.
