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


## 6. S1 decision record — bootloader spike, RK-001..RK-005 (Rowan, 2026-11-02)

Status: **RECORD ONLY — NOT THE KF-01 DECISION, NO PIN CHANGE.**
This section lands ROWAN_TASKS_500 S1 tasks RK-001..RK-005 on
`rowan/bootloader-spike`, off main `3452d24` (README
per-program expansion commit; `os-build/face/KERNEL_FACE.md` blob unchanged from the
earlier fetch, so this append applies cleanly). It changes no
kernel file, pins no bootloader version, claims no build and no
boot: `kernel/src/syscalls.rs` is untouched and no syscall
number is consumed. RK-006 (the pin change) does NOT start
until Pax approves or redirects target #1 on the bus, as
RK-005 requires.

Numbering note, stated to avoid a merge collision: the
KF-01 step-1 evidence synthesis lives as §6 on the separate
branch `rowan/kernel-kf01-spike @ 8e725f4`, which is NOT on
main. This record is §6 on THIS branch, written against
main's file (§1–§5). If Pax merges both branches, he
renumbers; this record cross-references the step-1 appendix
instead of duplicating it. Milo gate-1 on this branch covers
evidence accuracy only, as with the earlier spike branches.

### 6.1 RK-001 — round7 failure summary (carried, gap stands)

Carried from KF-01 step 1 §6.1 (`rowan/kernel-kf01-spike`
@ 8e725f4), not re-derived here, because the underlying
evidence has not changed:

- bootloader **0.10.9: API failure**;
- bootloader **0.11: std failure**.

Both labels are quoted from the build order
(`os-build/KERNEL_FACE_BUILD_ORDER.md` on main @07373f2).
The verbatim error logs for those two attempts were NOT
located in the `opencode/round7` tip tree searched for step 1
(`OPENCODE_FACE_BUILD.md`: zero bootloader hits;
`KERNEL_FACE_TASKS.md`: only the generic A1–A3 route text;
no round7/bootloader evidence file found), and no new log
has surfaced on main since. Pax's KF-01 budget ruling
(room-1, 2026-11-02) governs the consequence: the round7
pair neither consumes the Mac lane's fresh budget nor gets
blind re-run, and any fresh attempt must carry its verbatim
log or it does not count. RK-001 is complete to the extent
the tree allows; the verbatim-log gap is Pax/Mac-lane owned,
not closable from this VM.

### 6.2 RK-002 — current boot stack, verified against main this run

- `kernel/Cargo.toml`: `bootloader = { version = "0.9",
  features = ["map_physical_memory"] }`, package
  `metaos-kernel` 0.1.0, edition 2021, standalone workspace.
  There is NO `[package.metadata.bootloader]` table.
- `kernel/Cargo.lock` (386 bytes, whole file): pins
  bootloader **0.9.35**, checksum
  `e22d5a0b9e11dd5bee9d24a68885de6dc7ed367f897323b1c1286150fd469374`;
  the only other package is `metaos-kernel` itself.
- `kernel/.cargo/config.toml`: `build-std = ["core",
  "compiler_builtins", "alloc"]`, target
  `x86_64-unknown-none`, `rustflags =
  ["-C", "relocation-model=static"]` (workaround for the
  0.9.35 stage-2 mapper panic on static-PIE kernels, seen
  2026-11-01 on rustc 1.99.1), runner `"bootimage runner"`.
- `kernel/src/main.rs` BootInfo reads today:
  `bootloader::entry_point!(kernel_main)` (line 60);
  `fn kernel_main(boot_info: &'static bootloader::BootInfo)`
  (line 128); reads `boot_info.physical_memory_offset`
  (line 131, VGA console base); passes `boot_info` to
  `mem::mem_init` (line 163). It does NOT read
  `memory_map` directly, does NOT read
  `recursive_page_table_addr`, and reads no framebuffer —
  none exists on 0.9.35.
- `kernel/src/mem.rs` BootInfo reads today:
  `mem_init(boot_info: &'static bootloader::BootInfo)`
  (line 127); `boot_info.physical_memory_offset` (line 128);
  `boot_info.memory_map.iter()` (line 133); `kind_of`
  matches on `bootloader::bootinfo::MemoryRegionType`
  variants `Kernel | KernelStack | PageTable | Bootloader |
  BootInfo | FrameZero | InUse` (lines 106–110).
- `kernel/src/memory.rs`: imports NO bootloader type. It
  defines its own `MemoryRegion`/`MemoryMap`; the only
  bootloader adapter is `mem.rs`. A version bump therefore
  touches `memory.rs` not at all directly.

### 6.3 RK-003 — version table, 0.9.35 to newest 0.11.x (docs.rs)

| Family | BootInfo carries a framebuffer? | Framebuffer type | docs.rs citation |
|---|---|---|---|
| 0.9.x (0.9.35 pinned) | NO | — (no such field) | `bootloader` 0.9.34 `bootloader::bootinfo::BootInfo`: fields are exactly `memory_map`, `recursive_page_table_addr: u64`, `physical_memory_offset: u64` |
| 0.10.x (0.10.9 / 0.10.13) | YES — framebuffer mapping supported | Field spelling NOT pulled this run (see gap note) | `bootloader` 0.10.9 lib: entry takes `&'static mut BootInfo`, `bootimage` no longer used since 0.10.0; `bootloader` 0.10.9/0.10.13 `Config`: `map_framebuffer` (default true), `framebuffer_address`, `minimum_framebuffer_height/width` |
| 0.11.x (newest 0.11.17, lib.rs release list dated Jul 27, 2026) | YES | `FrameBuffer`, as `Optional<FrameBuffer>` | `bootloader_api` latest `bootloader_api::info::BootInfo`: `pub framebuffer: Optional<FrameBuffer>`; entry signature `fn(&'static mut BootInfo) -> !` |

Gap note (plain): the 0.10.x BootInfo framebuffer field's
exact spelling was not pulled from docs.rs this run, and
this record does not guess it. That gap is acceptable here
because 0.10.x is fallback target #2 only (RK-017); the
Mac lane confirms the spelling from the pinned crate
source at RK-007 before any 0.10 attempt counts. The pick
below rests on the 0.11.x row, which IS verified.

### 6.4 RK-004 — API delta, 0.9.35 to target #1 (0.11.x)

Rows cover every item `main.rs`, `memory.rs`, and `mem.rs`
touch, each marked used-by-us or unused. "Verify at
RK-007" means the exact new spelling is confirmed from the
pinned crate source on the Mac lane, not asserted here.

USED by us:

1. Crate path `bootloader::BootInfo` → `bootloader_api::BootInfo`
   (kernel dependency becomes `bootloader_api`; the
   `bootloader` crate becomes the disk-image builder lib).
   Touched: `main.rs:128`, `mem.rs:127`.
2. Entry macro `bootloader::entry_point!` →
   `bootloader_api::entry_point!`, and entry signature
   `&'static BootInfo` → `&'static mut BootInfo`.
   Touched: `main.rs:60`, `main.rs:128`.
3. `physical_memory_offset: u64` → `Optional<u64>`.
   Touched: `main.rs:131`, `mem.rs:128`. Both call sites
   must unwrap-or-fail, never silently default.
4. `memory_map: MemoryMap` (0.9, `.iter()` of regions) →
   `memory_regions: MemoryRegions`. Touched: `mem.rs:133`.
   Iteration shape to be confirmed at RK-007.
5. `bootloader::bootinfo::MemoryRegionType` and its
   variants (`Kernel | KernelStack | PageTable |
   Bootloader | BootInfo | FrameZero | InUse`) → the new
   region-kind type and values. Touched: `mem.rs:106–110`.
   Exact new spelling: verify at RK-007, not guessed here.
6. Cargo feature `map_physical_memory` → the
   `map-physical-memory` config option (config-driven
   mappings replace the feature flag). Touched:
   `kernel/Cargo.toml` dependency line.
7. `bootimage runner` (`kernel/.cargo/config.toml`) → DEAD
   since 0.10.0; the QEMU launch path must be rebuilt
   around the builder crate's disk image (0.10.9 docs:
   `cargo builder --kernel-manifest … --kernel-binary …`).
   Touched: `kernel/.cargo/config.toml` runner line.
8. `relocation-model=static` workaround → must be
   RE-PROVEN on the new loader; the 0.9.35 stage-2 mapper
   panic may not apply, and keeping the flag unexamined
   would hide that. Touched: `kernel/.cargo/config.toml`
   rustflags. Open question for RK-007/RK-011, not a row
   to close here.

UNUSED by us (no call site in `main.rs`, `memory.rs`, or
`mem.rs`):

- `recursive_page_table_addr: u64` → `recursive_index:
  Optional<u16>` (config `map-page-table-recursively`
  stays off unless a later task needs it).
- New `BootInfo` fields: `api_version`, `rsdp_addr`,
  `tls_template`, `ramdisk_addr`/`ramdisk_len`,
  `kernel_addr`/`kernel_len`, `kernel_image_offset`,
  `kernel_stack_bottom`/`kernel_stack_len` — none read.
- `memory.rs` itself: NO direct delta (imports no
  bootloader type); all adaptation flows through `mem.rs`.
- VGA console path (`main.rs` VGA base via the physical
  offset): not an API row but a behaviour question —
  spike part 2 §5 item 8 stands: do NOT assume `0xB8000`
  text mode is visible on a 0.10+/0.11 graphics-mode boot.
  Honest fallback order on the new loader: framebuffer
  if `Some`, else serial only. Decided at RK-011, not here.

### 6.5 RK-005 — target version #1 pick and rationale

**Target #1: newest 0.11.x (0.11.17 at time of writing;
the Mac lane pins the exact patch at RK-006 from lockfile
resolution). Target #2 fallback: 0.10.x (RK-017).**

Rationale: (a) Pax's KF-01 budget ruling orders 0.11.x
first for the Mac lane's two fresh attempts, and this
record does not override a boss ruling with a
fewest-delta heuristic; (b) 0.11.x is the only family
with a docs-verified framebuffer field spelling this run
(`Optional<FrameBuffer>`); (c) 0.10.x stays available as
the RK-017 fallback if the 0.11 probe fails. Tension
stated plainly: a pure fewest-delta reading could favor
0.10.x (one fewer major jump), so if Pax prefers the
fewest-delta criterion over the 0.11.x-first order, he
redirects on the bus and target #1 becomes 0.10.x with
no record rewrite beyond this paragraph.

**Pax approval requested (bus post with this branch's
SHA): approve target #1 = newest 0.11.x, or redirect to
0.10.x. RK-006 does not start until that approval lands.**
RK-025 will close S1 in `os-build/ROWAN_500_STATUS.md`
for RK-001..RK-025 once the spike resolves; no partial
status lines are written by this landing.
