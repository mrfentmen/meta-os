# Framebuffer API notes (OS-013) — bootloader 0.9.35, resolved in kernel/Cargo.lock

Read from the vendored source
`bootloader-0.9.35/src/bootinfo/mod.rs` (`pub struct BootInfo`).

## What BootInfo carries (complete field list)

- `memory_map: MemoryMap` — physical regions, bootloader-used marked.
- `recursive_page_table_addr: u64` (feature `recursive_page_table`).
- `physical_memory_offset: u64` (feature `map_physical_memory`) — ALL
  physical memory mapped at this offset; arbitrary frames reachable
  by adding the offset. THIS is how the kernel reaches video memory.
- `tls_template` (private), `_non_exhaustive` (private).

`grep -c framebuffer` on the file = 0. There is NO framebuffer field,
no pixel format, no stride, no resolution, no `FrameBuffer` type
anywhere in the 0.9.35 library API. The `video_mode/` and `printer/`
modules are the bootloader's OWN stage-1/2 display code, not a kernel
API. Crate features are builder-side only (`binary`, `map_physical_memory`,
etc.) — nothing video-related.

## Consequence (answers crew Q5 as a side effect)

An R5-style adapter "from the bootloader's framebuffer accessors"
cannot exist on 0.9.35: there are no accessors because there is no
framebuffer. Rowan's `kernel/src/framebuffer.rs` draft (pixel console
+ Terminus table, UNWIRED) stays valid code with no pixel buffer to
drive — it remains in-tree, unused on this branch, until a bootloader
with GOP/VBE (0.10+ style) lands. No pixel framebuffer this section.

## What the kernel CAN drive (this section's path)

- VGA text mode 80x25 at physical 0xB8000, reached as
  `physical_memory_offset + 0xB8000` (full phys mapping, feature on).
  QEMU's default VGA provides it; SeaBIOS leaves text mode active.
- No embedded font needed: glyphs come from the VGA ROM font.
  (OS-017 license: not applicable, nothing embedded.)
- Pixel grid (OS-016): NOT BUILT — no pixel surface exists. Recorded
  honestly per OS-027; text-mode banner + colors + screendumps are
  the proof instead. VBE graphics mode setup is a follow-up beyond
  this section (needs real-mode BIOS or a newer bootloader).
