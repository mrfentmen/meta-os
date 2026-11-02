/* Userspace link script (OS-078): static programs linked at BASE
   (one base per program via sed: hello 0x600000000000, sleeper
   0x610000000000, crasher 0x620000000000). Only the four sections
   Rust emits for these bins are placed; lld's orphans (.eh_frame,
   .dynamic, RELRO...) land after them by default rules. The loader
   maps every LOAD at its linked address and skips pages an earlier
   segment of the SAME program already mapped (tight packing shares
   pages; flags are per-page, so per-segment flags are best-effort —
   W^X is deferred past K6, stated in syscalls.md). Across programs,
   an occupied page is a hard refusal. Far from the kernel's low
   mappings and the physmap. */
ENTRY(_start)
SECTIONS
{
    . = BASE;
    .text : { *(.text .text.*) }
    .rodata : { *(.rodata .rodata.*) }
    .data : { *(.data .data.*) }
    .bss : { *(.bss .bss.*) *(COMMON) }
}
