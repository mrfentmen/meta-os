# Record — the kernel's boot sequence, from the code

Scope: `kernel/src/main.rs::kernel_main` and the modules it calls. Function names exact; line
ranges approximate after this week's edits. Evidence: `os-build/logs/K1-boot.txt`,
`K3-boot.txt`, `K16-doublefault-fixed.txt`.

## Order, and why

1. **`serial_init()`** — first, before anything can fail. If the UART is not up, no later
   failure can be reported. 38400 8N1, FIFO on, DTR/RTS/OUT2.
2. **VGA console** — map `physical_memory_offset + 0xB8000`, build `VgaConsole`, store it in
   `CONSOLE`. Every `println!` after this point goes to both serial and screen.
3. **Banner and alive line** — `META OS 0.1 (K6)`, `META OS KERNEL - alive (K1)`. The alive
   line is the K1 proof and is printed before any subsystem can panic.
4. **`gdt::init()`** — own GDT and TSS, including the IST stacks a double fault needs.
5. **`interrupts::register_builtins()`** — fill the dispatch table (exceptions 0/1/3/6/8/13/14,
   IRQs 32/33, syscall 128). No gate is installed yet.
6. **`traps::install()`** — install one trampoline per wired vector, DPL 3 only for 128,
   then round-trip-check every address; `trampolines_match_cpu()` asserts the error-code set.
7. **`disable()` → `pic_remap(32, 40)` → `pit_set_hz(100)` → `load_idt()` → `enable()`** — the
   documented install sequence. `cli` first because the bootloader's interrupt state is not
   known; `sti` last, once every gate has a trampoline.
8. **`prove_timer()`** — waits, bounded, for the PIT to advance `ticks()` by 10 and prints
   `K3 timer: N ticks after N spins`, or the failure line. This is a measurement, not an
   assertion: the clock either moved or the log says it did not.
9. **`mem::mem_init(boot_info)`** — frames, mapper, heap. Runs with the IDT live, so a bad
   mapping prints instead of triple-faulting.
10. **`sched::sched_init()`** and **`start_demo_tasks()`** — the scheduler takes over; the
    kernel's own context becomes the idle context. `kernel_main` never returns.

## What the order buys

- **Serial before VGA**: a failure at any step is writable to the log even if the console
  mapping is the thing that failed.
- **Gates before `sti`**: no interrupt can arrive at an empty vector.
- **Timer proof before paging**: the tick counter is validated while the address space is
  still the bootloader's, so a timer failure is not confused with a mapping failure.
- **Memory after the IDT**: a page fault during init is a printed exception, not a reset.

## Findings

1. **`println!` writes serial and VGA in that order, unbounded in serial.** If the UART stops
   draining, the line is truncated after `SERIAL_TX_SPINS` and the VGA keeps going. That is
   deliberate, but it means serial and screen can disagree by a partial line.
2. **The banner says `(K6)` while K6 is partial** (`../KERNEL_STATUS.md`). The banner is the
   last milestone *named*, not the last one proven.
3. **No hardware check on COM1.** `serial_init` writes the divisor without reading back; a
   machine without a 16550 at 0x3F8 gets silence, not an error (`QEMU_LIMITS.md`).
