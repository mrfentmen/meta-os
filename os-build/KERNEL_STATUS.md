# Kernel status — the honest matrix (2026-11-02)

Source of truth for "is the kernel real". A milestone is **PROVEN** only when a serial log from
our own binary shows its behavior. Everything else is WRITTEN, whatever it compiles to.

Build: see `kernel/BUILD_LOG.md`. Log: `os-build/logs/K1-boot.txt` (54 lines, captured
2026-11-02 from the image below).

| # | milestone | status | evidence |
|---|---|---|---|
| K1 | boot + alive line | **PROVEN** | `META OS KERNEL - alive (K1)`, log line 2 |
| K2 | framebuffer console | **NOT PROVEN** | the code draws text on VGA; `-display none` captured nothing. Needs a VGA capture (screenshot or `-display curses` transcript), not a serial line. |
| K3 | interrupts, timer, keyboard | **PARTIAL** | IDT/GDT/PIC/PIT are installed before scheduling (the scheduler and sleep work, which needs the timer), but the log has no tick counter and no key event. Needs a `tick N` line and a key echo to be citable. |
| K4 | paging, frames, heap | **PROVEN** | 15-region memory map, `61660` frames, `mem probe page ok`, `Box+Vec ok`, `mem stress 10k ok`, `mem summary: K4 up` |
| K5 | tasks, scheduling | **PROVEN** | `A` / `B` / `C sleeping 200 ticks` interleaving, then `C awake` |
| K6 | syscalls, userspace | **PROVEN** | `HELLO FROM USERSPACE`, `user exit code 0`, `user bad syscall 99 refused` (refusal path), page fault with `err 0x4: task killed` |

## What is not claimed

- **No hardware boot.** Every line comes from QEMU 11.1.3. The spec's proof standard is a QEMU
  log, and that is what this is; it says nothing about a physical machine, its UART, its
  framebuffer, or its keyboard controller.
- **K2 is not "probably fine".** The VGA path compiles and runs, but a console that nobody
  captured is a console nobody has seen. It stays NOT PROVEN until there is a capture.
- **K3 is not proven by the scheduler.** Sleep works, so a timer interrupt is firing; that is
  an inference, not a log line. The matrix records the inference as PARTIAL.
- **The syscall table is the one in `user.rs`.** `syscalls.rs` still carries the older draft
  numbers and is not wired in; it is retired by K21, not by this table.

## The next proof, in order

1. Capture VGA: run QEMU with a display and a screenshot at 3 s, commit the image as K2 evidence.
2. Add a `tick <n>` line at 1 s and a key echo; boot with `-display none` and a scripted
   keystroke; commit the log as K3 evidence.
3. Then, and only then, mark K2 and K3 PROVEN in this table.
