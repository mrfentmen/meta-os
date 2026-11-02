# `kernel/src/framebuffer.rs` — unwired-surface inventory (B248)

Scope: the pixel console that exists in the tree but is not part of the
running kernel. Every claim cites a line range on `main`, 2026-11-02.

## Status, in the file's own words

- Header: **"UNCOMPILED, UNVERIFIED, NOT WIRED INTO `main.rs`"**
  (`framebuffer.rs:1-3`).
- It is absent from the kernel's module list: `main.rs:46-55` declares gdt,
  interrupts, logo_frames, mem, memory, sched, tasks, traps, user, vga — not
  framebuffer. So none of this code is in the shipped binary.
- Why it exists: bootloader 0.9.35 hands over no pixel framebuffer
  (`os-build/research/framebuffer.md`); the file is the prepared driver for
  the day the boot chain supplies a buffer and geometry.

## Public surface

| Item | Where | What it would do |
|---|---|---|
| `FONT_WIDTH = 8`, `FONT_HEIGHT = 16` | `framebuffer.rs:54-57` | Terminus 8x16 glyph cell |
| `FramebufferInfo` | `:63-73` | buffer geometry: width, height, stride (pixels), format |
| `PixelFormat` | `:74-87` | `Rgb`, `Bgr`, `Gray` |
| `Framebuffer<'a>` | `:88-96` | caller-supplied `&mut [u8]` + info |
| `Framebuffer::new` | `:97-101` | wraps the caller's buffer and geometry; no pixel is touched and no validation happens here |
| `Framebuffer::info` | `:102-104` | returns the geometry copy |
| `write_pixel` | `:130-167` | one pixel, format-aware; out-of-geometry or out-of-buffer writes are refused by `pixel_offset` (`:110-129`), not by a panic |
| `clear` | `:168-176` | fill the whole buffer |
| `fill_rect` | `:177-189` | rectangle fill |
| `scroll_up_pixels` | `:190-220` | pixel-row scroll |
| `draw_glyph` | `:221-236` | 8x16 glyph from the embedded table |
| `FramebufferConsole<'a>` | `:237-246` | text console over a `Framebuffer` |
| `FramebufferConsole::new` | `:247-254` | fg/bg colours + framebuffer |
| `cols` / `rows` | `:255-262` | grid size from geometry |
| `write_byte` | `:283-307` | newline/backspace/glyph drawing |
| `write_str` | `:308-...` | string loop |

All of it is currently **used by nothing**: the only references are its own
module and documentation; `main.rs` never names it.

## What would have to be true to wire it

1. The boot chain must provide a real pixel buffer, stride, and format. On
   bootloader 0.9.35 it does not (`os-build/research/framebuffer.md`).
2. An adapter must translate that buffer/geometry into `FramebufferInfo`;
   the file deliberately asserts no bootloader API name, so only the adapter
   would change on a bootloader bump (`os-build/face/KERNEL_FACE.md`).
3. `main.rs`'s `CONSOLE` would need a second implementation or a switch; the
   current `VgaConsole` is a text-buffer type (`vga.rs:59-64`).

Until all three are true this stays **NOT WIRED**. That is not a mock and not
a partial feature in the product: the live console is the VGA one, and the
boot logs prove that one.

## Findings

- The K2 milestone is named "framebuffer console" but is implemented on the
  VGA text buffer; the amendment in `KERNEL_SPEC.md` (2026-11-02) says so.
  Cite K2 as "the kernel has a console", not "the kernel has graphics".
- No test compiles this file (it is not a module), so a future wiring change
  would get its first compile on the Mac. Recorded, not fixed.
