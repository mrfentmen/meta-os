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

## What this file is not

- Not a design doc: it asks, it does not decide.
- Not build evidence: no answer here counts as proven until a Mac
  build commit or a QEMU boot log shows it.
- Not a substitute for Q1: no R2 code follows from this file alone.
