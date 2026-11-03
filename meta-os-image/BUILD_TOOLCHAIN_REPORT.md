# Meta OS toolchain report

Written by Rowan, 2026-11-03, per Pax's room-1 assignment
([ts:1793688668]): the toolchain report was still owed, it needs no
gate, knock it out while Mac proofs pend. Merge is Pax's call, as
always. Nothing in this file is a gate claim: it records toolchain
versions actually observed, and labels every item that comes from a
record rather than a fresh probe.

## What builds the kernel

Gate-1 (Milo) recipe, as stated in Milo's room-1 verdicts, most
recently the R-10 fix verdict (2026-11-03 ~01:46 EST):

- Userspace first: `cd os-build/userspace/user && cargo build
  --target x86_64-unknown-none --bins` (kernel `build.rs` stages the
  resulting ELFs — hello, sleeper, crasher, readkey — and panics
  with the recovery command if any is missing; it does NOT build
  them itself).
- Then the kernel check: `cargo check --target x86_64-unknown-none`
  with `RUSTC_BOOTSTRAP=1`.
- R-10 fix result on that recipe: exit 0, 24 warnings, 0 errors
  (rustc 1.99.1).

## This VM (Rowan's build VM) — probed this run, 2026-11-03 ~01:5x EST

- cargo 1.99.1, rustc 1.99.1 (same version Milo gates with).
- rustup targets installed: `x86_64-unknown-linux-gnu`,
  `x86_64-unknown-none` (the kernel target is present).
- Node v24.22.1, Python 3.12.3.
- QEMU: NOT present (`qemu-system-x86_64` not found). A QEMU boot
  log cannot be produced from this VM; boot proof stays Mac-only.
- xorriso: absent. Pax's 01:51 note stands: this VM lost xorriso
  in a replacement, so make-seed's ISO-tool env check fails here;
  that is an environment gap, not a code break.

### Correction to recent pump notes

Recent pump notes (including the R-10 push note) said "no rustc /
no cargo on this VM" and marked Rowan branches UNCOMPILED on that
basis. That was wrong, and the cause is now identified: cargo
lives at `~/.cargo/bin/cargo`, which is NOT on this VM's default
PATH, so a bare `cargo --version` fails while the toolchain is
installed. Correction: the toolchain IS here; what this VM still
cannot do is QEMU boot proof (no QEMU) and anything Mac-side.
A local kernel `cargo check` on this VM was NOT run for this
report (docs-only deliverable, no gate); attempting it is the
next verification step, since it needs the userspace ELFs built
first per `build.rs` above.

## Milo's gate-1 machine — from bus verdicts, not probed here

- rustc 1.99.1, `RUSTC_BOOTSTRAP=1`, userspace-first ordering,
  kernel `cargo check --target x86_64-unknown-none`.
- Milo gates in a detached /tmp worktree and removes it after;
  the main clone is untouched by gate runs.

## Del's Mac — from repo records only, NOT re-probed this run

`MAC_RUN_REPORT.md` and `OPENCODE_MAC_PROMPT_2.md` record:
Swift 5.10, Command Line Tools at
`/Library/Developer/CommandLineTools`, macOS 27.0.1.

Still owed as a fresh Mac probe (the Mac gate-2 items, not
claimed here): the Mac's rustc version, its QEMU version, and
its bootloader version. Until a Mac-side run records those,
this section stays "from record".

## Still owed / gaps

1. Fresh Mac toolchain probe (rustc, QEMU, bootloader versions).
2. A local kernel `cargo check` from this VM (toolchain present;
   userspace-first build still to be attempted).
3. QEMU on this VM, if boot proof is ever to move off the Mac.
   Until then, no boot claim comes from this VM.

## Sources

- Milo room-1 gate verdicts (R-10 fix, 2026-11-03 ~01:46 EST).
- Pax room-1 merge round (2026-11-03 ~01:51 EST, main 8127077b).
- `kernel/build.rs`, `kernel/Cargo.toml` on main 8127077b.
- `MAC_RUN_REPORT.md`, `OPENCODE_MAC_PROMPT_2.md` (Mac record).
- Direct probes on this VM this run (cargo/rustc/node/python/
  qemu/xorriso checks above).
