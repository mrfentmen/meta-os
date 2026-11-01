# R5 reference — Rowan's interrupt wiring (preserved verbatim)

`main.rs` in this directory is Rowan's R5 kernel entry verbatim, as merged
to main in f34b122 (2026-11-01, Milo gate-1 GREEN): 256 asm trampolines in
`global_asm!`, PIC remap to 32/40, PIT 100 Hz, and an IDT round-trip
fail-stop check before `sti`. It was written-only — never compiled or
boot-proven.

In the OpenCode merge (2026-11-01, through Pax), the live kernel entry
became OpenCode's modular wiring (`kernel/src/main.rs` + `gdt.rs`,
`traps.rs`, `sched.rs`, `user.rs`, `vga.rs`, `mem.rs`), because that line
carries the Mac compile and QEMU boot proofs K1–K6 (see
`os-build/logs/` and `os-build/OS_BUILD_REPORT.md`). R5's file is not a
module of the live kernel and is not compiled; it is kept here, byte for
byte, so its trampoline approach stays available for diffing against
`traps.rs` and nothing of the work is lost. The pre-merge version also
remains in git history at f34b122.
