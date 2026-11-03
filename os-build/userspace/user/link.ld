/* Userspace link script (OS-078): static programs linked at BASE.

   BASE IS NOT HARDCODED. Each program passes its own base with
   `-C link-arg=--defsym=__base=0x...` from os-build/userspace/build.sh,
   and `.` uses it when defined. The fallback below is crasher's historic
   base so a bare `cargo build` still produces something loadable.

   Why this changed: every bin used to link at this one address because
   .cargo/config.toml never passed -Tlink.ld at all, so the kernel loader
   refused the 2nd..4th program with `address in use` (RK-007 log). One
   base per program is the sanctioned fix (Pax: per-program, in the build
   pipeline, NOT the config patch alone).

   Only the four sections Rust emits for these bins are placed; lld's
   orphans (.eh_frame, .dynamic, RELRO...) land after them by default
   rules. The loader maps every LOAD at its linked address and skips
   pages an earlier segment of the SAME program already mapped. Across
   programs, an occupied page is a hard refusal. Far from the kernel's
   low mappings and the physmap. */
ENTRY(_start)
SECTIONS
{
    . = DEFINED(__base) ? __base : 0x0000620000000000;
    .text : { *(.text .text.*) }
    .rodata : { *(.rodata .rodata.*) }
    .data : { *(.data .data.*) }
    .bss : { *(.bss .bss.*) *(COMMON) }
}
