# KERNEL FACE — graphics path spike, part 1: evidence (Rowan)

Status: **SPIKE IN PROGRESS, DECISION HELD.** This document gathers the
evidence for KERNEL_FACE_TASKS.md section A (A1–A3) from the tree on
main. No rectangle has been drawn yet, nothing here claims to compile
or boot: this VM has no Rust toolchain (`cargo`/`rustc` not
installed), so the Mac lane (OpenCode) builds and QEMU-proves both
routes, and Milo gate-1s this branch on evidence only. The A3 pick
is made when a route reports a real QEMU screendump, not before.

Supersession note: Pax's room-1 ruling 2026-11-02 ~02:26 EST
(idx 506) — "nothing is off limits", kernel boots into the face,
Rowan writes the graphics spike first — supersedes the kill list in
ROWAN_OS_BUILDOUT.md (2026-11-02 02:22, "no framebuffer, graphics").
The face spike is now Rowan's top target. The readkey-merge pack /
R-FP2 work on `rowan/kernel-readkey-merge` @ 73cfcf1 stands queued
behind it, not abandoned.

## 1. Where the kernel stands today (verified against main, this run)

- Bootloader: `kernel/Cargo.toml` declares `bootloader = { version =
  "0.9", features = ["map_physical_memory"] }`; `kernel/Cargo.lock`
  pins **0.9.35**.
- BootInfo on 0.9.35 carries **no framebuffer at all**:
  `os-build/research/framebuffer.md` (read from the vendored 0.9.35
  source, `bootinfo/mod.rs`) lists the complete fields —
  `memory_map`, `recursive_page_table_addr` (feature-gated),
  `physical_memory_offset` (feature `map_physical_memory`), private
  `tls_template` / `_non_exhaustive` — and `grep -c framebuffer` on
  that file is 0. No pixel format, no stride, no resolution, no
  `FrameBuffer` type anywhere in the 0.9.35 library API. The
  `video_mode/` and `printer/` modules are the bootloader's own
  stage-1/2 display code, not a kernel API. An adapter "from the
  bootloader's framebuffer accessors" therefore cannot exist on
  0.9.35: there are no accessors.
- Live console today is VGA text, not pixels: `kernel/src/main.rs`
  builds the console at `physical_memory_offset + 0xB8000`, 80x25,
  and prints `META OS 0.1 (K6)` / `META OS KERNEL - alive (K1)`.
  The text boot stays under the face plan — the face comes AFTER
  the alive line, so every proven claim stays true on the same boot.
- An unwired pixel console already exists in-tree:
  `kernel/src/framebuffer.rs` (milestone K2, header-marked UNWIRED,
  UNCOMPILED, NOT WIRED INTO `main.rs`). It is `core`-only (no
  `alloc`, no external crate) and already provides the A4
  primitives as caller-supplied-buffer code:
  - `Framebuffer::new(buffer, info)`, `info()`, `write_pixel(x, y,
    rgb)`, `clear(rgb)`, `fill_rect(x, y, w, h, rgb)`,
    `scroll_up_pixels(lines, fill)`
  - `FramebufferConsole::new(fb, fg, bg)`, `cols()`, `rows()`,
    `write_byte()`, `write_str()`, plus `draw_glyph()` over an
    embedded 8x16 Terminus table (256 glyphs).
  - Boundary types `FramebufferInfo` / `PixelFormat`, stride in
    pixels. Its stated wiring contract is a thin adapter from the
    bootloader's framebuffer buffer + geometry into
    `FramebufferInfo`. No bootloader API name is asserted inside
    it, so none of it can go stale on a bootloader bump — the
    adapter is the only place a version answer lives.
- Consequence: the spike is **not** "write a pixel driver from
  zero". The driver surface exists and waits on exactly one missing
  input: a real pixel buffer + geometry from the boot chain. Both
  routes below are judged on how soon and how cleanly they supply
  that input.

## 2. Route 1 — upgrade the bootloader (A1)

Plan: bump `bootloader` 0.9 to a version whose `BootInfo` carries a
framebuffer (0.10+ style, per the research doc — the exact version
and API names are **not asserted here**; the Mac lane pins them
from the crate docs and records the `Cargo.lock` delta, flagged not
hidden), then land the thin adapter: `main.rs` gains
`mod framebuffer;` and constructs
`FramebufferConsole::new(Framebuffer::new(buffer, info), fg, bg)`
from the bootinfo framebuffer's buffer and geometry, with the VGA
text console kept as fallback until the first pixel screendump
lands. Proof sequence: red screen (fill whole buffer), then blue,
then `fill_rect` — each as a QEMU screendump committed with the log.

Breakage to record, not hide: `Cargo.lock` pin moves (whole
dependency subtree, not just the bootloader line); possible
`entry_point!` / `BootInfo` shape / memory-map type churn across
the major bump; whether `map_physical_memory` semantics survive
(the VGA fallback and `mem.rs` both lean on the physical-memory
offset). Any of these breaking the text boot is a Route 1 cost
measured in the Mac build log.

Why it leads on paper: smallest new code (adapter only, driver
already written), no boot-chain fork, and the failure mode is
visible at build time.

## 3. Route 2 — UEFI GOP taken directly at boot (A2)

Plan: prototype far enough to draw one pixel — take the GOP
framebuffer (base address, stride, resolution, pixel format) and
drive it through the same `Framebuffer` type over the GOP buffer,
then `fill_rect`. The one-pixel prototype answers the route's
whole question.

Open question that decides it: **is the GOP buffer reachable from
the kernel without forking the boot chain?** Bootloader 0.9's UEFI
stage owns boot services; the kernel entry point receives a
`BootInfo`, not a UEFI handle table. If reaching GOP needs a
custom UEFI entry, a bootloader fork, or ExitBootServices
choreography owned by nobody in-tree, Route 2 is a loader project,
not a spike — larger than Route 1 by an order of magnitude, and
its "no bootloader change" premise fails. The Mac lane's first
Route 2 deliverable is therefore that reachability answer with a
pointer to where the handle would come from, before any pixel code.

Why it trails on paper: unproven reachability, and even on success
it duplicates what a bootloader bump hands over as a field.

## 4. Decision criteria (A3) — applied when evidence arrives

The pick goes to whichever route first reports, on the Mac lane:

1. A green Mac build of the wired tree (text boot intact — alive
   line present in the same boot log).
2. A QEMU screendump of a filled rectangle (red, then blue), with
   resolution / pitch / pixel format logged from the boot info.
3. The smaller breakage bill: lockfile delta, files touched, and
   whether the VGA text fallback survived untouched.

Provisional lean, **not** the decision: Route 1, because its only
missing piece is a version bump plus a thin adapter over code that
already exists, while Route 2's missing piece is an unanswered
reachability question. If the Mac lane reports Route 1's bump
breaking the text boot badly, or Route 2 reaching GOP cleanly,
this lean flips on that evidence and this document gets updated
with the numbers — the decision follows the screendump, not the
lean.

## 5. What comes next (for the Mac lane / Milo gate)

1. Mac: pin the Route 1 bootloader candidate, record the lockfile
   delta, attempt the adapter build; report build result + delta
   whether green or red.
2. Mac: answer Route 2 reachability (handle source) before writing
   Route 2 pixel code.
3. First screendump (either route, red screen) decides A3; this
   document is then updated with the decision + numbers, and A4
   (resolution / pitch / format from boot info, `fill_rect` +
   `put_pixel` proven by screendump) proceeds on the winning route.
4. Milo gate-1 on this branch covers evidence accuracy only: every
   version, field list, and file claim above is checkable against
   main without a compiler. No boot claim is made here.
