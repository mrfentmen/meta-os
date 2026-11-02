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


## 6. KF-01 — bootloader spike, step 1: evidence synthesis (Rowan, 2026-11-02)

Status: **KF-01 STEP 1 ONLY — NOT THE KF-01 DECISION.** This section
is an evidence synthesis for Pax's KF-01 order
(`os-build/KERNEL_FACE_BUILD_ORDER.md` on main @07373f2, Pax room-1
posts 2026-11-02 10:32–10:36 EST). It pins no bootloader version, it
claims no build and no boot, and it changes no kernel file:
`syscalls.rs` is untouched and KF-01 consumes no syscall numbers.
The KF-01 decision — target version, what breaks, and either the
proven boot or a written failure — lands only with a Mac-lane boot
log and screendump, read by Pax. Milo gate-1 on this branch covers
evidence accuracy only, as with spike parts 1 and 2.

Base verified against live main this run: main
`d1d4c665ec346811ce687420bb9dca2bbc1e5e7d` (docs wording-audit
commit; this file's blob is unchanged from the K4-review tip
6e9a9a5, so the appendix applies cleanly).
Build order and K4 review are on that tip; spike part 2 is
`rowan/kernel-face-spike-2 @ 0a82f58` (evidence only, nothing wired).

### 6.1 Round7 failure evidence, as recorded — and a gap found this run

The build order records exactly two prior bootloader-upgrade
attempts, and this step starts from them, not around them:

- bootloader **0.11: std failure**;
- bootloader **0.10.9: API failure**.

Gap found this run, stated plainly: the verbatim error logs for
those two attempts were NOT located in the `opencode/round7` tip
tree searched this run (`OPENCODE_FACE_BUILD.md`: zero bootloader
hits; `KERNEL_FACE_TASKS.md`: only the generic A1–A3 route text;
tree-name search: no round7/bootloader evidence file). The labels
above are therefore quoted from the build order, not re-derived
from logs this run. The Mac lane must attach the verbatim logs
before any new attempt is counted — re-running either version
blind would violate the KF-01 order, and a root cause (toolchain
vs API) cannot be assigned from a two-word label. In particular,
this step does NOT assert that the 0.11 std failure was a missing
nightly/std target, only that the build order's label is "std
failure" and the cause is unproven until the log is attached.

### 6.2 Attempt budget — question to Pax, not decided here

The build order's timebox reads: "at most two version attempts
(the 0.10.9 API-fail and 0.11 std-fail already on record from the
earlier spike count as attempts)". Read literally, the budget is
already spent by those two attempts, and the next step would be
the hard fallback (restore the 0.9.35 pin, gate.sh GREEN 7/7,
file the failure evidence, stop) with route re-decision as Pax's
call. Read the other way, the Mac session gets two fresh attempts
and the candidate family is 0.11.x (spike part 2's recommendation,
unproven), with 0.10.x as fallback only if 0.11 fails. This step
does not choose between those readings. Pax to rule on the bus;
Rowan does not spend a Mac session on an ambiguous budget.

### 6.3 Starting point, re-verified this run

- `kernel/Cargo.toml`: `bootloader = { version = "0.9",
  features = ["map_physical_memory"] }`, package `metaos-kernel`
  0.1.0, edition 2021, standalone workspace.
- `kernel/Cargo.lock` pins bootloader **0.9.35** (checksum
  `e22d5a0b9e11dd5bee9d24a68885de6dc7ed367f897323b1c1286150fd469374`).
- BootInfo on 0.9.35 carries **no framebuffer** (spike part 1 §1,
  confirmed again this run from the main tree; `grep -c
  framebuffer` on the vendored 0.9.35 field list is 0).
- `kernel/src/framebuffer.rs` exists on main, UNWIRED (build
  order: 576 lines, `write_pixel`, `fill_rect`, `clear`,
  `scroll_up_pixels`, `draw_glyph`, pixel console with
  `write_str`). Nothing constructs it at boot today.
- Text boot stays FIRST at every step (build-order fence):
  banner, alive line, ring-3 programs, fault isolation, text
  shell, in that order, before any graphics. If a step cannot
  keep those claims true on the same boot, the step is not done.

### 6.4 Breakage bill carried from spike part 2 §5 (summary, not a re-derivation)

The full bill is in `os-build/face/KERNEL_FACE_PART2.md` §5; the
Mac lane works it top to bottom and reports each item green or
red, not just the final binary:

1. `kernel/Cargo.toml` + `kernel/Cargo.lock`: the `bootloader =
   "0.9"` line dies; the lockfile delta is the whole dependency
   subtree, recorded not hidden. `map_physical_memory` becomes
   the `map-physical-memory` config option, and
   `physical_memory_offset` becomes `Optional<u64>`.
2. `kernel/.cargo/config.toml` runner: `bootimage runner` is
   dead (no `bootimage` since 0.10.0); the QEMU launch path
   must be rebuilt around the builder crate's disk image, with
   the actual QEMU command and firmware (OVMF vs SeaBIOS/VESA)
   recorded by the Mac lane, not asserted here.
3. `relocation-model=static` was a workaround for a 0.9.35
   stage-2 mapper panic; the new loader must re-prove it.
4. `kernel/src/main.rs`: entry macro + signature
   (`bootloader_api::entry_point!`, `&'static mut BootInfo`),
   console construction under an `Optional` offset, and the
   `CONSOLE` static's type.
5. `kernel/src/mem.rs`: `mem_init`'s four touchpoints — new
   type path, new regions field, new region struct (field
   names from the pinned crate source, not guessed), `Optional`
   offset; the Mac lane prints converted map counts against
   the 0.9.35 boot log.
6. `kernel/src/sched.rs` console call sites (shell, attract,
   `clear`, panic path): `FramebufferConsole` has no
   `snapshot`/`restore`, no `set_pos`, no attribute colors,
   so a drop-in type swap is false — shell console and face
   surface stay separate statics until after the first
   screendump (part 2 §5 item 6 / §6 step 0).
7. `kernel/src/logo_frames.rs` attract art (46x17 ASCII cells
   via `set_pos` + write) does not transfer to pixels by
   itself; port is a post-first-rectangle decision.
8. VGA fallback, revised: do NOT assume `0xB8000` text mode is
   visible on a 0.10+/0.11 graphics-mode boot. Honest fallback
   order on the new loader: framebuffer if `Some`, else
   serial only. `vga.rs` stays in the tree, dormant on a
   pixel boot, not a fallback.
9. Unaffected: `kernel/build.rs` userspace ELF staging,
   `os-build/userspace/`, and `gdt.rs`, `interrupts.rs`,
   `traps.rs`, `tasks.rs`, `syscalls.rs`, `user.rs` (no
   `bootloader::` reference on main).

### 6.5 Proof still owed for KF-01 (from the build order, unchanged)

- QEMU serial log of the UNMODIFIED kernel on the new
  bootloader carrying the K6 banner and the alive line, plus
  a screendump of the text console.
- Fallback if the new bootloader breaks the proven boot:
  restore the 0.9.35 pin (`Cargo.toml` + `Cargo.lock` as on
  main today), re-run `gate.sh` to GREEN 7/7 on the restored
  stack, file the failure evidence in this decision record,
  and stop. Route re-decision (UEFI GOP re-spike) is Pax's
  call, not a retry loop.
- Captures land in `os-build/captures/`; boot logs in
  `os-build/logs/`; Pax reads the log and the screendumps
  before any milestone is marked.

### 6.6 Alignment note

This step follows Pax's Route 1 dispatch and del's 2026-11-02
real-OS ruling: the face is drawn by the kernel itself, with no
browser and no Linux underneath; the web face is design
reference only — no new web features. Nothing in this step
builds a web face, a browser shell, or a carrier-face feature.
