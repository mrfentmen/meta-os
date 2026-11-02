# What QEMU cannot prove (2026-11-02)

Every kernel claim in this repo comes from `qemu-system-x86_64` 11.1.3. That is the proof
standard the spec sets, and it is worth stating exactly what the standard excludes, because
"it boots" is doing a lot of work in every status file.

## Proven by the logs, and genuinely so

- The kernel image is produced by the rust-osdev bootloader, enters long mode, and reaches
  our `kernel_main`.
- Physical memory map parsing, a bitmap frame allocator, 4-level paging, a heap under stress.
- Timer interrupts at the programmed divisor, keyboard scancodes arriving through IRQ1,
  VGA text output visible in a screen dump.
- Context switches among kernel tasks, a sleep that wakes on the tick counter.
- Ring-3 entry through vector 128, ELF loading, `exit` returning a code, a bad syscall refused
  without killing the caller, and a page fault killing only the faulting task.

## Not proven, and not provable this way

| Thing | Why QEMU cannot settle it |
|---|---|
| Real UART behaviour | QEMU's 16550 always drains instantly. The bounded write wait in `main.rs` exists for hardware that does not, and has never been exercised. |
| Real keyboard controller | The emulated i8042 is QEMU's, not a laptop's; scancode set, controller state and the `0x64` status port can all differ. |
| Real timer accuracy | QEMU's PIT is exact. The 100.0153 Hz divisor error is arithmetic, and no drift was measured against a reference clock. |
| Interrupt latency and nesting | QEMU serialises everything; a real board has SMI, APIC routing and devices that share lines. |
| SMP | The kernel assumes one CPU everywhere (`static mut` ledger). A second core is untested and would be unsound. |
| Memory above 256 MiB | Boots use `-m 256M`. The map is parsed, but nothing proves the allocator at 4 GiB or with holes. |
| Graphics | There is no pixel framebuffer under bootloader 0.9.35; K2 is VGA text. QEMU draws it, but there is no compositor to prove. |
| Persistence | No disk driver and no filesystem. A reboot loses everything; nothing has been written to a block device. |
| Networking | No NIC driver in the kernel. Any "network" claim belongs to the host services, not the OS. |
| Real hardware boot | Not attempted. The boss's Mac run is the first physical test, and a failure there is expected to be informative, not surprising. |

## Standing consequence

A green QEMU boot is a proof of the code path, not of the machine. Reports must say "boots in
QEMU" and never "boots". The first real-hardware result gets its own log file and its own
line in `KERNEL_STATUS.md`; until then the matrix has no hardware row at all, which is the
honest way to record "not attempted".
