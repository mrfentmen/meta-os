# Memory map (OS-054) — real BootInfo data, QEMU 11.1.3 pc, 512M

From `K4-boot.txt` (16 regions, `mem region` lines):

- 0x0-0x1000 + 0x1000-0x5000 + 0x5000-0x15000: frame zero, EBDA/BIOS,
  bootloader stages — reserved.
- 0x15000-0x9f000 + 0x9f000-0xa0000 + 0xf0000-0x100000: conventional
  memory holes, VGA BIOS — reserved.
- 0x100000-0x2bf000: bootloader + boot info structures — reserved.
- **0x2bf000-0x400000: usable (~1.3M)** — the allocator's first pool.
- 0x400000-0x442000 + 0x442000-0x84e000: kernel image + page tables —
  reserved (this is why the heap lives in .bss, never in usable RAM).
- **0x84e000-0x1ffe0000: usable (~503M)** — the main pool.
- 0x1ffe0000-0x20000000 + 0xfffc0000-0x100000000: ACPI NVS, LAPIC/IOAPIC
  MMIO — reserved.
- 0xfd00000000-0x10000000000: 64-bit PCI window (~12G) — reserved.
  (This one entry is the whole "reserved 12590196K" headline.)

Totals: usable 516940K (129235 frames), all bitmap-covered.
Allocator choice (OS-057): bitmap over usable regions (Rowan's
`FrameAllocator`), lowest-frame-first; heap is his linked-list
`Heap` over a 256 KiB .bss buffer as the global allocator. No
external crate: `alloc` comes from `build-std`, not from crates.io.
