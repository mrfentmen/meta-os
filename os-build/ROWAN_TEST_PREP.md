# Rowan — testing slice prep (Pax assignment, room-1 [530])

Del's crew-wide testing directive, sliced to Rowan by Pax on room 1:
more testing on the programs and the OS, Meta API tests within ~$10,
an agentic end-to-end loop, programs autonomous too.

## Status: PREP ONLY

- **$0 spent. No live-key call from this VM. No SPARK key on this VM**
  (Del sets the key on the Mac himself; nothing key-related goes in
  commits or on the bus).
- Meta API billing returned **HTTP 402 (out of credits)** during Pax's
  live hunt #3. Until Del tops the account up, every live-key item is
  PREP ONLY — write it, fixture it, leave it ready to fire.
- **No key route is declared standing.** Route A (Del places the key)
  vs Route B (Pax executes the live run, the lane verdicts it) is
  Del's pick. This prep is route-agnostic: it specifies both routes'
  inputs and fires neither.
- This file is prep, not proof. It changes no kernel code, proves no
  boot, and merges nothing.

## Base state (verified this run)

- Main: 315542a (Pax release checklist; parent 80a7886, the 12-hour
  crew build plan doc; Buffy round13 merged at e2b2c587 before that).
- Del's orders, room 1: "pull main now we have less then 12 hours to
  finish this" and "read the 12 hour md file and begin working" —
  acted on: plan + release checklist read in full this run.
- 12-hour plan (H+0 = 2026-11-02 21:46 EST, H+12 ~09:46 EST Nov 3):
  Rowan is the kernel / 2.0 track, OFF the 12-hour critical path —
  keep the bare-metal kernel moving (K3 demand-paging fix, K4
  talker/listener, KF framebuffer pieces); nothing in the ISO waits
  on Rowan; acceptance is gate.sh GREEN on Rowan's branches;
  syscalls.rs FROZEN. Only Pax pushes main and merges.
- KF-03: rowan/kernel-kf03 @4d04623, parent rowan/bootloader-spike
  @717e7ff, exactly 3 files (framebuffer.rs, main.rs, sched.rs),
  syscalls.rs untouched.
- Milo GATE-1 GREEN on KF-03 @4d04623: cargo check clean, 0 errors,
  compile gate only — a check is not a link and proves nothing on
  screen.
- Pax ruling stands: KF-03 merge HELD, RK-008 merge HELD, until
  Mac/Buffy re-proof shows text on the framebuffer — and per Pax
  [536], that re-proof should target current main.

## Part 1 — KF-03 screen-proof checklist (RK-012)

Why this exists: Buffy's RK-007 boot (buffy/rk007-boot @40d1a050)
proved the 0.11 tree on serial — alive line, PIT ticks, memory map,
K4 up, scheduler rotates — but the screen stayed blank. Under
bootloader 0.11 the display is in graphics mode and VGA text at
0xB8000 is never shown, so RK-012 FAILED. KF-03 wires the 0.11 pixel
framebuffer as a second console beside VGA: `print!` mirrors every
line to serial, VGA, and the framebuffer; panic paints the framebuffer
too; `clear` and color changes in sched.rs mirror to it. VGA
snapshot/attract/set_pos machinery is untouched, and attract stays
VGA-only — invisible on 0.11 — so attract animation is NEVER
accepted as screen proof. Shell/console text is.

Buffy (or the Mac lane — Pax to confirm the runner) must capture
QEMU screendumps, not serial logs alone. Serial must match the
screen line-for-line for the boot sequence; serial-only text is a
FAIL for screen proof even when the serial log is perfect.

- **F1 — boot frame.** Screendump in graphics mode showing kernel
  boot text on screen: the alive line and the following boot lines
  rendered on the framebuffer, matching the serial boot log.
  Record: framebuffer geometry + pixel format as reported at boot,
  QEMU command/build, screendump file, serial log file.
- **F2 — scheduler/demo frame.** Screendump showing demo-task /
  scheduler rotation text and preserved shell/console text on
  screen after boot settles. Proves the framebuffer console survives
  past boot, not just the first lines.
- **F3 — clear frame.** Run `clear`, screendump: the framebuffer
  screen blanks and the cursor parks at 0,0; the next printed text
  appears at top-left. Proves the sched.rs clear mirror.
- **F4 — colors frame.** Change console colors, screendump: the new
  colors appear on the framebuffer, not VGA-only. Proves the sched.rs
  colors mirror.
- **F5 — panic frame (only if a panic drill is run by the Mac/Buffy
  lane).** Screendump: the PANIC screen painted on the framebuffer,
  matching the serial panic text. Not required for a normal boot
  pass; do not force a panic just to collect it.

Fail conditions (any one fails the screen proof):

- Blank screen = RK-012 still open, FAIL.
- Serial-only text, screen blank or stale = FAIL.
- Unsupported pixel format, if reported, = FAIL with format +
  geometry recorded, not a pass.
- VGA text alone on a 0.11 graphics-mode boot = FAIL (that text is
  never shown to the user).

Pass condition: F1–F4 captured on screendumps, each matched to the
serial log, with geometry/format recorded, plus F5 if a panic drill
ran. Verdict line per frame: `F<n> | PASS or FAIL | screendump |
serial log | geometry/format`.

## Part 2 — Loader-fix gate pack lines (RK-013/14/15)

Context, from Pax's RK-007 ruling: all four userspace programs were
loader-refused with 'address in use'. Cause diagnosed: the 0.11
kernel image occupies 0x200000–0xbfba2c, but the RK-007 ELFs were
plain-built with entry 0x201160 — inside the kernel image — because
link-base.ld is not on the plain build link line. Fix direction
(not yet built; a separate branch): wire per-program 0x6000...
bases into a repo build step.

These are the gate lines the Mac/Buffy lane runs AFTER Rowan's
loader-fix branch lands. This prep doc does not itself fix the
loader.

- **L1 — static.** Every userspace ELF entry lies outside the kernel
  image range, with distinct per-program bases; no two programs
  share a load address. Record each ELF's entry address.
- **L2 — build.** A repo build step (not a hand edit) produces those
  ELFs reproducibly; the link-base wiring is on the build link line,
  verified in the build log.
- **L3 — boot.** Zero 'address in use' loader refusals across all
  four programs; each program loads and enters userspace.
- **L4 — runtime.** Each program's own output is visible (serial
  and, after KF-03, framebuffer); the scheduler still rotates, and
  the K3 demand leg and K4 still prove on the same boot — no
  regression from the loader change.
- **L5 — gate.** Milo gate-1 compile check first, then Mac/Buffy
  boot proof; merge is Pax's call; syscalls.rs untouched.

## Open question to Pax

Confirm the screen-proof runner for F1–F5: Buffy (boot lane) or the
Mac lane — or both, with one verdict. No other question blocks this
prep; the loader fix itself is Rowan's next code branch, gated by
L1–L5 above.
