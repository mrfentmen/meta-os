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

## kernel/src/gdt.rs (Section C)

- `gdt::init`: writes our 5-slot GDT + TSS (IST[0] = DF stack top),
  `lgdt`, far return reloading CS to 0x08, data segments to 0x10,
  `ltr` 0x18. Interrupts must be off; single CPU at K3.

## kernel/src/traps.rs (Section C)

- `global_asm!` trampolines + `trap_common`: pushes are fixed-count
  (error-or-0, vector, 9 scratch regs); frame pointer math
  (rsp+72/80/88) matches that layout; 136-byte red-zone skip keeps
  the `call` 16-aligned; `iretq` drops vector+error.
- `dispatch_trampoline`: trusts the stub's triple; masked gate means
  no reentrancy. `trap_addr` match is total over VECTORS.
- `install` gates: selector 0x08 valid post-`gdt::init`; IST=1 only
  on vector 8. `debug_assert` round-trips every gate address.

## kernel/src/main.rs (Section C)

- `break-test`/`fault-test` hooks: `int3` and a volatile read of
  unmapped 0xdeadbeef, feature-gated test builds only (OS-058 style).
- `hlt` in the echo loop: valid with IF set, wakes on IRQ.
