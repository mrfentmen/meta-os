# Display record — `vga.rs` + `logo_frames.rs` (B246)

Scope: the text console and the attract-screen data. No framebuffer pixels
here; `kernel/src/framebuffer.rs` is an unwired surface and has its own
record. Every claim cites a line range on `main`, 2026-11-02.

## VGA text console (`kernel/src/vga.rs`)

The console drives the 80x25 text buffer at physical `0xB8000` through the
bootloader's physical-memory mapping (`vga.rs:1-7`).

| Item | Where | Detail |
|---|---|---|
| address / geometry | `vga.rs:10-14` | `VGA_PHYS_ADDR = 0xB8000`, 80 columns, 25 rows |
| palette | `vga.rs:21-38` | 16 VGA attribute colours; unused variants kept for the panic screen and shell |
| attribute pair | `vga.rs:42-47` | `ColorSpec(fg, bg)` packs `(bg << 4) \| fg` |
| snapshot type | `vga.rs:53` | `([u16; 2000], col, row)` — the whole screen plus cursor |
| console state | `vga.rs:59-64` | `col`, `row`, `spec`, raw `*mut u16` buffer |

Methods:

- `new` (`vga.rs:72-82`) — builds on a mapped address and clears to the
  background.
- `clear` (`:83-93`), `set_colors` (`:94-99`), `set_pos` (`:100-106`).
- `snapshot` / `restore` (`:107-126`) — used by the attract screen so the
  shell returns exactly as it was.
- `newline` (`:127-135`) and `scroll` (`:136-159`) — scroll at row 25 only.
- `backspace` (`:165-180`) — moves left one cell and blanks it; this is what
  makes `0x08` work on screen, not just on serial.
- `write_byte` (`:184-209`) — `\n` is newline, `0x08` is backspace,
  printable bytes draw through the ROM font; bounds are checked by the
  newline/scroll logic.
- `write_str` (`:210-216`) and the `core::fmt::Write` impl (`:218-220`) let
  `print!` target the console.

The console is constructed once in `main.rs:130-139` and stored in the
`CONSOLE` static; the `print!` macro writes to serial and, when present, the
console (`main.rs:22-33`).

## Attract screen data (`kernel/src/logo_frames.rs`)

- Data only (`logo_frames.rs:1-9`): it is the product's own
  `js/logo-background.js` render rasterized offline onto a 46x17 text grid.
- `FRAME_W = 46`, `FRAME_H = 17` (`:10-11`).
- `FRAMES` is a `&[&str]` of **12** frames (`:12-217`; frame blocks begin at
  lines 13, 30, 47, 64, 81, 98, 115, 132, 149, 166, 183, 200).

Who consumes it: `sched.rs`'s console task. `console_task`
(`sched.rs:329-410`) enters attract after `BOOT_IDLE_TICKS` (~2 s after
boot) and after `IDLE_TICKS` (~30 s) at the shell, advances one frame every
`FRAME_TICKS`, and restores the saved snapshot on the first keypress
(`sched.rs:398-408`). `attract_draw` centres the block using `FRAME_W/H`
(`sched.rs:414-450`). The frames are VGA-only: the serial log stays a clean
shell log.

## Refusals and limits

- A byte outside printable Latin-1 is swallowed by `write_byte`; it is not
  an error and prints nothing (`vga.rs:184-209`).
- The console cannot draw pixels. That is the K2 amendment, not a defect:
  bootloader 0.9.35 hands over no framebuffer
  (`KERNEL_SPEC.md` amendment 2026-11-02; `os-build/research/framebuffer.md`).
- If `CONSOLE` is `None`, `print!` degrades to serial only and never
  silently drops the line (`main.rs:22-33`).
