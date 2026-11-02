# Kernel status — the honest matrix (2026-11-02)

Source of truth for "is the kernel real". A milestone is **PROVEN** only when a serial log from
our own binary shows its behavior. Everything else is WRITTEN, whatever it compiles to.

Build: see `kernel/BUILD_LOG.md`. Log: `os-build/logs/K1-boot.txt` (54 lines, captured
2026-11-02 from the image below).

| # | milestone | status | evidence |
|---|---|---|---|
| K1 | boot + alive line | **PROVEN** | `META OS KERNEL - alive (K1)`, `K1-boot.txt` line 2 |
| K2 | framebuffer console | **PROVEN** | `screendump` of the live VGA buffer: 196 of 2000 cells carry glyphs, rows 0-10 and 24 (`K2-boot.png`); 215 cells on the shell screen (`K2-shell.png`). Screen capture, not a serial line. |
| K3 | interrupts, timer, keyboard | **PROVEN** | `K3 timer: 10 ticks after 407902 spins` (measured against the handler's counter), `K3 keyboard: first scancode 0x1f`, then a typed `status` answered `STATUS tasks=7 ticks=169 heap_free_kb=287` (`K3-boot.txt`) |
| K4 | paging, frames, heap | **PROVEN** | 15-region memory map, `61660` frames, `mem probe page ok`, `Box+Vec ok`, `mem stress 10k ok`, `mem summary: K4 up` (`os-build/logs/K1-boot.txt`) |
| K5 | tasks, scheduling | **PROVEN** | `A` / `B` / `C sleeping 200 ticks` interleaving, then `C awake` (`os-build/logs/K1-boot.txt`) |
| K6 | syscalls, userspace | **PROVEN** | `HELLO FROM USERSPACE`, `user exit code 0`, `user bad syscall 99 refused` (refusal path), page fault with `err 0x4: task killed` (`os-build/logs/K1-boot.txt`) |

## What is not claimed

- **No hardware boot.** Every line comes from QEMU 11.1.3. The spec's proof standard is a QEMU
  log, and that is what this is; it says nothing about a physical machine, its UART, its
  framebuffer, or its keyboard controller. The keyboard evidence is QEMU's emulated i8042,
  driven by an RFB client — real scancodes through the kernel's IRQ1 handler, but emulated
  hardware. See the capture notes in `kernel/BUILD_LOG.md`.
- **The screenshots are of the VGA text buffer, not a compositor.** K2 is the kernel drawing
  its own text. There is no pixel framebuffer under bootloader 0.9.35, so there is no window,
  no font scaling and no graphics mode.
- **The syscall table is the one in `user.rs`.** `syscalls.rs` still carries the older draft
  numbers and is not wired in; it is retired by K21, not by this table.
- **The timer is 100.0153 Hz, not 100.** Divisor 11931 truncates; see the drift note in
  `kernel/BUILD_LOG.md`. Nothing derives wall-clock time from ticks.

## What comes next, in order

1. K7 is the next milestone to write, not to claim: the shell/service hand-off from kernel to
   userspace, which is what moves the boot past the kernel demo tasks.
2. The kernel still runs only demo tasks (`A`/`B`/`C`), the console shell and three ELF test
   programs. No Goose service has been loaded by the kernel yet, and that is the real gap
   between K6 and a usable OS.
3. Hardware proof stays with the boss's Mac run. Anything here that a real board would
   contradict is listed in `MAC_QUESTIONS.md`.
