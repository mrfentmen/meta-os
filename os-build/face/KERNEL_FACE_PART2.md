# KERNEL FACE — graphics path spike, part 2: Route 1 bootloader-upgrade evaluation (Rowan)

Status: **SPIKE IN PROGRESS, DECISION HELD.** This is part 2 of the
face spike, written on Pax's room-1 order 2026-11-02 ~06:18 EST
(idx 506, confirmed by del idx 508: "take pax order @rowan"):
evaluate Route 1 — upgrading the bootloader — against the real
tree. Part 1 (`os-build/face/KERNEL_FACE.md`) stands unchanged;
this document does not replace it, and it does not make the A3
decision. A3 still waits on a real Mac QEMU screendump, exactly as
part 1 set it. Nothing here claims to compile or boot: the sketch
in section 6 is a sketch inside this document only. It is NOT
wired into `kernel/src/main.rs`, NOT added to `kernel/src/`, and
no kernel file is touched by this branch. Proof rides the next Mac
boot, same as W6.

Base verified against live main this run: main
`21f9be68aba39cb72996fc1918bf76d5c31a43c8`. All tree claims
below were read from that tip through the GitHub API (tree +
blobs), not from a stale local copy.

## 1. The question Pax asked, answered in one paragraph

Route 1's missing input is a pixel buffer + geometry from the
boot chain. That input first exists in bootloader **0.10.0**:
the rust-osdev UEFI rewrite (April 2021) replaced the 0.9.x
`BootInfo` with a new struct and "a pixel-based framebuffer
instead of the VGA text mode", and broke compatibility with
0.9.x outright — `bootimage` is no longer used from 0.10.0 on.
The current docs line is **0.11.x** (0.11.17 listed July 2026),
where the kernel depends on the split `bootloader_api` crate,
not on `bootloader` directly. Recommendation, unproven until the
Mac build: the Mac lane pins **one** 0.11.x version first and
records the `Cargo.lock` delta; 0.10.x is the fallback only if
the 0.11 build fails. This document pins neither: a version
number written here without a Mac build log would be exactly
the kind of claim part 1 refused to make. The exact candidate
and its lockfile delta are Mac-lane output, flagged, not hidden.

Sources read this run (docs.rs, current pages): the
`bootloader_api` `BootInfo`, `FrameBuffer`, `FrameBufferInfo`
and `PixelFormat` pages; the `bootloader` 0.10.9 `Config` page
(`map_framebuffer`, minimum width/height); the rust-osdev
April 2021 note on the 0.10.0 UEFI rewrite; the `bootloader`
crate page (0.11.x usage: nightly + `llvm-tools-preview`,
`bootloader_api` dependency, `&'static mut BootInfo` entry,
`UefiBoot`/`BiosBoot` disk-image builders).

## 2. What the new API actually hands the kernel

`bootloader_api::BootInfo` (latest docs, `#[non_exhaustive]`):

- `framebuffer: Optional<FrameBuffer>` — "information about
  the framebuffer for screen output if available". Optional
  is load-bearing: the adapter must handle `None`, not assume
  a screen.
- `physical_memory_offset: Optional<u64>` — only present if
  the `map-physical-memory` config option is enabled. The
  current kernel reads this as a plain `u64`; under the new
  API it is an `Option` that must be unwrapped with a
  fallback, not read directly.
- `memory_regions` replaces 0.9.x `memory_map`
  (different type; the Mac lane records the new region
  struct's fields from the pinned crate source — they are
  NOT asserted here, because the 0.9 field names below do
  not carry over).
- Entry point: `bootloader_api::entry_point!(kernel_main)`
  with signature `fn kernel_main(boot_info: &'static mut
  BootInfo) -> !` — mutable, where 0.9.x passed
  `&'static BootInfo`.
- Configuration moves to a `BootloaderConfig` passed to the
  `entry_point!` macro (second argument), including a
  `mappings.framebuffer` mapping; the old
  `[package.metadata.bootloader]` + `bootimage` route is gone.

`FrameBuffer` methods (latest docs): `buffer()` (`&[u8]`),
`buffer_mut()` (`&mut [u8]`), `into_buffer()`
(`&'static mut [u8]`), `info()` (`FrameBufferInfo`).

`FrameBufferInfo` fields, verbatim from the docs page:
`byte_len`, `width`, `height`, `pixel_format`,
`bytes_per_pixel`, `stride` ("number of pixels between the
start of a line and the start of the next", possibly larger
than the width — padding). `PixelFormat` variants:
`Rgb`, `Bgr`, `U8` (single grayscale byte), and
`Unknown { red_position, green_position, blue_position }`
(bit offsets); the enum is `#[non_exhaustive]`, so any match
on it needs a wildcard arm.

## 3. The adapter fit: nearly exact, with one honest gap

The unwired driver in `kernel/src/framebuffer.rs` (41,355
bytes on main, header-marked UNWIRED / UNCOMPILED / NOT
WIRED INTO `main.rs`) was written with local boundary types
precisely so no bootloader API name could go stale inside
it — and that bet pays off here. Its `FramebufferInfo`
carries exactly the same six fields as the new
`FrameBufferInfo`, in the same meanings, stride in pixels
included; its `Framebuffer::new(buffer, info)`,
`write_pixel`, `clear`, `fill_rect`, `scroll_up_pixels`,
`draw_glyph` over the embedded 8x16 Terminus table, and
`FramebufferConsole::new(fb, fg, bg)` with `cols()` /
`rows()` / `write_byte()` / `write_str()` need no change
to accept the new API's output. The adapter is a field
copy plus a format match:

| bootloader_api `PixelFormat` | local `PixelFormat` | Notes |
|---|---|---|
| `Rgb` | `Rgb` | Same memory order; pad byte at 4 bpp per docs ("length might be larger than 3, check `bytes_per_pixel`"). |
| `Bgr` | `Bgr` | Same, mirrored. |
| `U8` | `Gray` | Single byte per pixel, luminance only. |
| `Unknown { .. }` | — (no mapping) | Leave unwritten, fall back (section 6). Never fake a format: the driver's no-mock rule forbids inventing channel order from bit offsets without a Mac-proven test. |
| (any future variant) | — | Wildcard arm: same fallback. The enum is non-exhaustive by design. |

`into_buffer()` returning `&'static mut [u8]` also
removes the one lifetime awkwardness in the old wiring
contract: a `Framebuffer<'static>` can live in a static
slot, where a borrowed slice could not. That does NOT make
the existing `CONSOLE` static reusable as-is — see section 5.

## 4. What is true on main today (the Route 1 starting point)

- `kernel/Cargo.toml`: `bootloader = { version = "0.9",
  features = ["map_physical_memory"] }`, package
  `metaos-kernel` 0.1.0, edition 2021, `[workspace]`
  (standalone), `panic = "abort"` profiles.
- `kernel/Cargo.lock` pins `bootloader` **0.9.35**
  (checksum `e22d5a0b…`). Part 1's field list for 0.9.35
  `BootInfo` is confirmed again: `memory_map`,
  `recursive_page_table_addr` (feature-gated),
  `physical_memory_offset` (feature-gated), private
  `tls_template` / `_non_exhaustive`, zero framebuffer
  fields (`os-build/research/framebuffer.md`, read from
  vendored 0.9.35 `bootinfo/mod.rs`).
- `kernel/src/main.rs` (`bootloader::entry_point!`,
  `kernel_main(boot_info: &'static bootloader::BootInfo)`):
  builds the console at
  `boot_info.physical_memory_offset + VGA_PHYS_ADDR`
  (`0xB8000`), 80x25, prints `META OS 0.1 (K6)` /
  `META OS KERNEL - alive (K1)`, then GDT/IDT/PIC/PIT,
  `mem::mem_init(boot_info)`, scheduler demo tasks.
  The `print!` macro writes serial AND the `CONSOLE`
  static (`Option<VgaConsole>`), degrading to serial only
  before console init.
- `kernel/src/vga.rs`: `VGA_PHYS_ADDR = 0xB8000`,
  `VGA_WIDTH = 80`, `VGA_HEIGHT = 25`, `VgaConsole` with
  `clear`, `set_colors`, `set_pos`, `snapshot`,
  `restore`, `write_byte`, `write_str`. Text console,
  `core`-only.
- `kernel/src/logo_frames.rs`: `FRAME_W = 46`,
  `FRAME_H = 17`, ASCII `FRAMES` rasterized from
  `js/logo-background.js`; the console idle task cycles
  them on a timer.
- `kernel/.cargo/config.toml`: `build-std = ["core",
  "compiler_builtins", "alloc"]`, target
  `x86_64-unknown-none`, runner `"bootimage runner"`,
  and `rustflags = ["-C", "relocation-model=static"]`
  with the comment that 0.9.35's ELF segment mapper
  panics on static-PIE kernels ("PageAlreadyMapped" in
  stage 2, seen 2026-11-01 on rustc 1.99.1).
- Toolchain on this VM, corrected from part 1: stable
  rustc/cargo **1.99.1** exist in `~/.cargo/bin` (not on
  the default PATH — part 1's "no toolchain" was the PATH,
  not the disk), but `rustup toolchain list` shows only
  stable, `rustup target list --installed` shows only
  `x86_64-unknown-linux-gnu`, and there is no nightly,
  no `x86_64-unknown-none` target, no `llvm-tools`.
  This VM still cannot build this kernel at all, and
  0.11.x additionally requires nightly +
  `llvm-tools-preview` per its docs. Verification stays
  the Mac lane's job; nothing below is a build claim.

## 5. Breakage bill: everything that moves off 0.9.35

In dependency order — the Mac lane works this list top to
bottom and reports each item green or red, not just the
final binary:

1. **`kernel/Cargo.toml` + `kernel/Cargo.lock`.** The
   `bootloader = "0.9"` line dies: the kernel's new
   dependency is `bootloader_api` (version = the pinned
   0.11.x, or 0.10.x on fallback), and the disk-image
   builder becomes a separate builder crate using
   `bootloader::UefiBoot` / `BiosBoot`. The lockfile
   delta is the whole dependency subtree, not one line,
   and it is recorded, not hidden. `map_physical_memory`
   as a cargo feature does not survive: it becomes the
   `map-physical-memory` config option in
   `BootloaderConfig`, and `physical_memory_offset`
   becomes `None` if that option is off — every reader
   of it must handle `None`.
2. **`kernel/.cargo/config.toml` — runner.** `runner =
   "bootimage runner"` is dead: `bootimage` is not used
   since 0.10.0. The QEMU launch path must be rebuilt
   around the builder crate's disk image (UEFI needs an
   OVMF image on the Mac; the BIOS path sets its graphics
   mode via VESA — the Mac lane records the actual QEMU
   command it used, it is not asserted here).
3. **`kernel/.cargo/config.toml` — relocation fix.**
   `relocation-model=static` was a workaround for a
   0.9.35 stage-2 mapper panic. The new loader is a
   different loader: the flag must be re-proven, not
   carried blindly. If the Mac build passes with it, keep
   it and say so; if it breaks the new loader, that is a
   Route 1 cost measured in the build log, and the
   replacement flag (if any) is recorded there.
4. **`kernel/src/main.rs` — entry + console.** Three
   changes, not one: (a) macro + signature
   (`bootloader_api::entry_point!`, `&'static mut
   BootInfo`); (b) the console construction line —
   `physical_memory_offset` is now `Optional<u64>` and
   the VGA address math no longer means "the display"
   once the bootloader sets a graphics mode; (c) the
   `CONSOLE` static's type. See item 6.
5. **`kernel/src/mem.rs` — memory map.** `mem_init`
   takes `&'static bootloader::BootInfo` and reads
   `boot_info.physical_memory_offset` (plain `u64`) and
   `boot_info.memory_map.iter()`, converting
   `bootloader::bootinfo::MemoryRegionType` via
   `kind_of()` and frame numbers
   (`range.start_frame_number * 4096`,
   `end_frame_number * 4096` — 0.9.35 reports frames,
   not byte addresses). All four touchpoints change:
   new type path, new regions field, new region struct
   (field names from the pinned crate source, not
   guessed here), `Optional` offset. The frame-count
   bookkeeping (`usable` / `reserved` / `other` sums,
   `REGIONS` 64-slot table) survives only if the new
   region representation converts cleanly — the Mac
   lane prints the converted map counts in the boot log
   and compares them against the 0.9.35 boot log.
6. **`kernel/src/sched.rs` — every console call site.**
   This is the largest hidden cost, and part 1's
   "VGA text console kept as fallback" needs revising
   in its light. The shell, attract screen (R-9),
   `clear` command (RW4-2), and panic path all touch
   the `CONSOLE` static, which is typed `VgaConsole`:
   `clear()`, `set_pos()`, `snapshot()` /
   `restore()` (attract entry/exit), `write_byte` /
   `write_str` (echo loop), `set_colors` (panic
   screen). `FramebufferConsole` provides `clear`
   (by RGB, not by attribute), `write_byte` /
   `write_str`, `cols` / `rows` — but it provides NO
   `snapshot` / `restore`, NO `set_pos`, NO attribute
   colors. A drop-in type swap is therefore false:
   either the pixel console gains snapshot/restore/
   cursor operations first, or the shell console and
   the face surface stay separate statics until after
   the first screendump. Section 6 recommends the
   second order. The W6 `fetch` screen is unaffected
   in content (it prints real ticks / tasks / frames /
   heap lines through the same console sink), but its
   sink type changes with everything else here.
7. **`kernel/src/logo_frames.rs` — attract art.**
   46x17 ASCII cells drawn through `set_pos` +
   `write` do not transfer to pixels by themselves.
   The pixel rendering is either `draw_glyph` at 8x16
   per cell (a 46x17 frame becomes a 368x272 pixel
   block, positioned, not full-screen) or a fresh
   rasterization — a face-design decision for after
   the first rectangle screendump, not a spike
   prerequisite. The text attract screen keeps working
   only on a text-mode boot; on a pixel-mode boot it
   is the first feature that needs the port in item 6.
8. **VGA fallback, revised.** Do NOT assume the VGA
   text buffer at `0xB8000` is a usable fallback display
   on a 0.10+/0.11 boot. Once the bootloader sets a
   graphics mode, the display is the framebuffer; a
   text-mode write to `0xB8000` may paint memory
   nothing shows. The honest fallback order on the new
   loader is: framebuffer if `Some`, else serial only.
   Whether QEMU's BIOS path leaves any text mode
   visible alongside the framebuffer is a Mac
   screendump observation, not a premise. `vga.rs`
   stays in the tree (it is real, proven code), but
   on a pixel boot it is dormant, not a fallback.
   This revision supersedes part 1 section 2's
   "VGA text console kept as fallback until the first
   pixel screendump lands" — the fallback it described
   cannot be assumed on the new loader, and the first
   pixel screendump is what replaces it, not what
   follows it.
9. **Unaffected, stated so the bill is complete.**
   `kernel/build.rs` (userspace ELF staging from
   `os-build/userspace/user`) touches no bootloader
   type; `os-build/userspace/` has its own
   `.cargo/config.toml` and target; `gdt.rs`,
   `interrupts.rs`, `traps.rs`, `tasks.rs`,
   `syscalls.rs`, `user.rs` contain no `bootloader::`
   reference on main. The text boot's alive line
   (`META OS KERNEL - alive (K1)`) must still appear
   in the same boot log as the first pixel proof —
   that is part 1's criterion 1, unchanged.

## 6. Code sketch (document only — NOT wired, NOT compiled)

Step 0 is deliberately NOT a console swap. The first
proof draws through a local `Framebuffer` and leaves the
shell console alone, so a failed pixel attempt cannot
take the proven text boot with it. Only after the red /
blue rectangle screendumps land does the console
unification in item 6 of section 5 begin.

```rust
// SKETCH — lives in this document only. Not in kernel/src,
// not compiled, not booted. Names below are the documented
// bootloader_api names (BootInfo.framebuffer,
// FrameBuffer::into_buffer / info, FrameBufferInfo fields,
// PixelFormat variants); the Mac lane confirms them
// against the pinned crate version before any wiring.

// 1. Adapter: bootloader_api framebuffer -> local driver types.
//    Returns None for Unknown / future formats: the caller
//    falls back to serial-only, never to invented pixels.
fn adapt_fb(
    fb: bootloader_api::FrameBuffer,
) -> Option<(Framebuffer<'static>, FramebufferInfo)> {
    let info = fb.info();
    let format = match info.pixel_format {
        bootloader_api::PixelFormat::Rgb => PixelFormat::Rgb,
        bootloader_api::PixelFormat::Bgr => PixelFormat::Bgr,
        bootloader_api::PixelFormat::U8 => PixelFormat::Gray,
        _ => return None, // Unknown + any future variant
    };
    let local = FramebufferInfo {
        width: info.width,
        height: info.height,
        stride: info.stride,
        bytes_per_pixel: info.bytes_per_pixel,
        pixel_format: format,
        byte_len: info.byte_len,
    };
    let buffer = fb.into_buffer(); // &'static mut [u8]
    Some((Framebuffer::new(buffer, local), local))
}

// 2. Proof step, inside kernel_main AFTER the alive line
//    and BEFORE the scheduler takes over (so a pixel fault
//    still prints on serial instead of triple-faulting
//    silently inside a task):
//      if let Some(fb) = boot_info.framebuffer.take() {
//          if let Some((mut px, info)) = adapt_fb(fb) {
//              // Log geometry to serial FIRST: resolution,
//              // stride, bytes_per_pixel, format — the numbers
//              // the screendump is checked against.
//              px.clear((255, 0, 0));          // red screen
//              // ... screendump 1 ...
//              px.clear((0, 0, 255));          // blue screen
//              // ... screendump 2 ...
//              px.fill_rect(100, 100, 200, 150, (0, 255, 0));
//              // ... screendump 3: rectangle, not just fill ...
//          }
//          // None from adapt_fb, or framebuffer None:
//          // serial-only. Do NOT construct VgaConsole at
//          // 0xB8000 on this path unless the Mac lane has
//          // proven a text mode visible on this loader.
//      }
//    Then the existing boot sequence continues unchanged:
//    GDT/IDT, mem_init (ported, section 5 item 5),
//    scheduler. The pixel surface is NOT yet CONSOLE.
```

Open details the sketch deliberately leaves to the
pinned-crate source (Mac lane fills them in, none guessed
here): the exact `Optional` accessor for
`framebuffer` (`take()` vs field move under `&mut`
`BootInfo`); the `MemoryRegions` element type and its
start/end representation for the `mem.rs` port; whether
`BootloaderConfig` must explicitly enable
`map-physical-memory` for `mem.rs` to keep working, and
what `physical_memory_offset = None` does to the VGA
path if any caller still reads it; the builder crate's
exact QEMU command and firmware (OVMF vs SeaBIOS/VESA).

## 7. Proof sequence for the Mac lane (unchanged criteria)

1. Pin one bootloader version; commit the `Cargo.lock`
   delta separately so the bill is reviewable.
2. Build the ported tree (section 5 items 1–5); report
   green or red with the log either way. A red build
   with the failing item named is a successful spike
   output, not a failure to report.
3. Boot under QEMU; the log must contain the alive line
   AND the framebuffer geometry line (width, height,
   stride, bytes_per_pixel, format) from the sketch's
   serial logging.
4. Screendumps: red screen, blue screen, then a
   `fill_rect` rectangle on a contrasting fill — each
   committed with its log, as part 1 required.
5. Only then: console unification (snapshot/restore/
   cursor on the pixel console, or a face surface beside
   the shell console), attract port, `clear` port — and
   the A3 decision document, updated with the numbers.

## 8. What this document does NOT do

- It does not pin a bootloader version, does not claim
  0.11.x (or 0.10.x) builds against this kernel, and
  does not claim the sketch compiles: the sketch uses
  documented API names, but names on a docs page are
  not a build.
- It does not decide A3. Route 2's reachability question
  (can the kernel reach GOP without forking the boot
  chain?) is still open, and Route 1's breakage bill
  above is still unpriced in build-log terms. The
  decision follows the first screendump, per part 1.
- It does not touch W6 (`rowan/kernel-w6` @ 9de854d,
  Milo gate-1 GREEN, queued with Pax) or C4
  (`rowan/kernel-c4` @ 6171d84, Milo gate-1 GREEN,
  queued with Pax under the Custos-in-bake-list caveat):
  both stay queued for Pax's merge call, and this
  branch is off main, not off either of them.
- It does not change the text boot. If the Mac lane
  reports the port breaking the alive line, that report
  goes on the bus verbatim and this document gets a
  correction note — the lean does not override the log.
