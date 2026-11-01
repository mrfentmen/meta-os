# Unsafe ledger (OS-026, started Section B; every unsafe block, one line)

## kernel/src/vga.rs

- `VgaConsole::new`: caller must hand a writable 80x25 VGA text
  buffer; `clear` writes all 2000 cells through it.
- `VgaConsole::clear`: `write_volatile` over the full 80x25 range —
  in-bounds by the fixed geometry constants.
- `VgaConsole::scroll`: `read_volatile`/`write_volatile` row copy,
  indices bounded by VGA_WIDTH/VGA_HEIGHT math.
- `VgaConsole::write_byte`: single `write_volatile` at
  `y * 80 + x` with x < 80, y < 25 enforced by scroll/newline logic.

## kernel/src/main.rs

- `outb`/`inb`: raw port I/O via inline asm (COM1 0x3F8 range only).
- `print!` macro + `panic` handler: `addr_of_mut!(CONSOLE)` —
  sound because only `kernel_main` touches it, single CPU, no
  threads exist yet at K2.
- `kernel_main` VGA mapping: `physical_memory_offset + 0xB8000`
  cast to `*mut u16` — valid because the bootloader maps all
  physical memory at the offset and 0xB8000 is the VGA text buffer.

## kernel/src/framebuffer.rs (Rowan R2 draft, UNWIRED, not executed)

- No unsafe blocks execute on this branch; the file is not compiled
  into the K2 image path (module not declared in main.rs).
