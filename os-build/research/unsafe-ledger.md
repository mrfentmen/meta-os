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

## kernel/src/mem.rs (Section D)

- `PhysMem::read_entry/write_entry`: volatile u64 at
  `offset + table + index*8`, index asserted < 512; caller (mapper)
  supplies real table addresses.
- `cr3()`: `mov {}, cr3` read only.
- `invlpg`: invalidates one translation; correctness (un)mapping
  belongs to the caller.
- `KernelAlloc` (`Sync` shell over `static mut HEAP`): sound while
  single-CPU and handlers never allocate — stated, not assumed.
- Static roots (`REGIONS`, `MAP`, `BITMAP`, `HEAP`, `MAPPER`) via
  `addr_of!`/`addr_of_mut!`, never shared references.
- Probe write/read + guard-test read: volatile, on the mapped page.

## kernel/src/sched.rs (Section E)

- `switch_to`: saves callee-saved regs + resume-rip + rflags into
  `*old`, loads `*new`, jumps. Only `rax` clobbered (caller-saved);
  `rdi`/`rsi` still hold the pointers at the indirect jump. New
  contexts come from `Context::initial` (16-aligned top, IF set).
  Red zone: no stack slots used below rsp; `push [rsi+64]`/`popfq`
  run on the NEW stack. Callers: single CPU, no preemption, so no
  task can be switched away from mid-switch.
- `enter`/`goto`/`back_to_sched`: raw `Context` pointers from the
  owned `CTXS` table; `CUR` set-before/restored-after keeps the
  current-task identity exact across resume.
- `Box::leak` stacks: 16 KiB heap boxes, never freed in K5 (no reap
  yet); leaking is documented, not a silent loss — K6 reaps.
- `SCHED`/`SLOTS`/`CTXS` roots via `addr_of_mut!`, never references.

## kernel/src/user.rs + traps vector 128 (Section F)

- `load_elf`: ELF header/segment reads are bounds-checked
  (`get(..)`); mapping writes go through translated phys addresses;
  RELA writes likewise (entry revalidated after).
- `enter_userspace`: 5-push iretq frame (SS/SP/FLAGS/CS/IP, RPL 3);
  `nostack` is accurate only because the frame is consumed by
  `iretq` itself; `noreturn` true. TSS.rsp0 set to the entering
  task's own kernel stack top just before.
- `syscall_handler`: saved-register offsets (-24..-56) match
  `trap_common`'s push order exactly (9 regs, vector, error);
  return value written to the saved rax slot. Handler runs on the
  task's own kernel stack (rsp0), so scheduler switches are
  task-context switches, never stack transplants.
- Gate 128 is DPL 3 (0xEE); all other gates stay 0x8E.
- Page-fault CPL check: ring-3 faults exit the task instead of
  returning into it (no re-fault loop by design).

## Adopted files (OS-224 review — written by Rowan, reviewed here,
## wired by my branch; single-CPU discipline holds for all)

## kernel/src/interrupts.rs (16 unsafe sites)
- Raw port IO (`outb`/`inb` asm): COM1 + PIC + PIT + keyboard
  ports only; same shape as main.rs.
- `IDT.entries[...]` writes/reads in `idt_set`/`idt_get`: R5 wiring
  installs gates before `lidt`; never touched live.
- `load_idt` (unsafe fn): caller (my traps install path) calls it
  once, interrupts off, after gates are set.
- `disable`/`enable` (cli/sti asm).
- `TICKS`, `KEY_BUFFER/HEAD/TAIL`, `HANDLERS` statics: only the
  running handler or kernel_main touches them; no concurrency.
- `dispatch`: handler lookup from static table; called from the
  single trap path.

## kernel/src/memory.rs (17 unsafe sites)
- Heap free-list pointer chasing (`(*cur).span/next`): the heap
  owns its buffer exclusively (Heap::init contract); single
  threaded; GlobalAlloc shell adds no threads.
- All other sites are the same list walk in alloc/dealloc/split/
  coalesce paths — one invariant, reviewed once.

## kernel/src/tasks.rs
- Zero unsafe blocks (pure data + policy). Nothing to justify.
