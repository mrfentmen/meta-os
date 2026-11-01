# Interrupt vector map (OS-042) — vectors we own on this branch

Wired by `traps.rs` to Rowan's `interrupts.rs` dispatch table:

| Vector | Source | Handler | Error code? |
|---|---|---|---|
| 0 | CPU divide error | divide_error_handler | no (push 0) |
| 1 | CPU debug | debug_handler | no |
| 3 | CPU breakpoint (`int3`) | breakpoint_handler | no |
| 6 | CPU invalid opcode | invalid_opcode_handler | no |
| 8 | CPU double fault | double_fault_handler | yes (CPU) |
| 10 | CPU invalid TSS | unhandled line | yes (CPU) |
| 11 | CPU segment not present | unhandled line | yes (CPU) |
| 12 | CPU stack fault | unhandled line | yes (CPU) |
| 13 | CPU general protection | general_protection_handler | yes (CPU) |
| 14 | CPU page fault | page_fault_handler | yes (CPU) |
| 32 | PIC IRQ 0 (PIT 100 Hz) | timer_handler (ticks++, EOI) | no |
| 33 | PIC IRQ 1 (PS/2 keyboard) | keyboard_handler (buffer+hex, EOI) | no |

Install order: `gdt::init` → `register_builtins` → `traps::install` →
`disable` (cli) → `pic_remap(32, 40)` → `pit_set_hz(100)` →
`load_idt` → `enable` (sti). All gates are present 64-bit interrupt
gates (0x8E, IF masked in handler); double fault rides IST stack 0
(4 KiB `DF_STACK` via our TSS, `ltr` loaded). Code selector for every
gate is our GDT 0x08.

Proven on QEMU 11.1.3 (this Mac): int3 line + return, PIT at exactly
100/200/300 ticks, keyboard scancodes, page-fault line (fault-test
build), 60 s+ tick run without stall.
