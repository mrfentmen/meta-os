# OS build report — opencode/os-build (boss order 2026-11-01)

One-paragraph KERNEL_SPEC (OS-001): Meta OS is a real operating system with its own Rust kernel (Layers 1–3: boot, kernel core, drivers), Goose system services (Layer 4), a Lobster agent runtime and shell (Layers 5–6), and programs that run on top (Layer 7, never the OS). Debian is only the workbench we build on. Every kernel milestone K1–K6 is proven only by a QEMU boot log from our own binary showing the milestone's behavior; nothing fake ships (NO MOCKS); what is not real is NOT BUILT, stated plainly.

Work branch: `opencode/os-build`. Ground: `kernel/`, `services/`, `lobster/`, `os-build/` + docs. Protected (never touched): `server/`, `js/`, `os/worlds/`, `crates/`.

## Standing lists (OS-226, updated per section)

- Proven: (none yet — K1 boot pending).
- Written but unproven: kernel/ K1 skeleton (Rowan R1), K2 framebuffer + K3 interrupts drafts (Rowan R2/R3, UNWIRED), K4 memory + K5 tasks drafts (Rowan R4/R5, UNWIRED). All UNCOMPILED on the Mac as of this writing.
- Not started: everything in OPENCODE_OS_BUILD.md Sections B–Q except research notes.

## Section A — K1 boot proof (OS-001..OS-012)

- OS-001: this file opened; spec paragraph above. DONE 2026-11-01.
- OS-002: Mac toolchain (this Mac, 2026-11-01): rustc 1.99.1 + cargo
  1.99.1 via rustup stable-aarch64-apple-darwin; `rustup target add
  x86_64-unknown-none`; components llvm-tools-preview + rust-src;
  cargo bootimage 0.10.5; QEMU 11.1.3 (`brew install qemu`); RUSTC_BOOTSTRAP=1
  (kernel/.cargo/config.toml uses build-std, nightly-only otherwise).
  Bootloader resolved to 0.9.35 (kernel/Cargo.lock, committed). DONE.
- OS-003: first build errors, verbatim. (1) `error:
  ".../lib/rustlib/src/rust/library/Cargo.lock" does not exist,
  unable to build with the standard library, try: rustup component
  add rust-src --toolchain stable-aarch64-apple-darwin`
  (toolchain-side, fixed by installing rust-src). (2)
  `error[E0308]: mismatched types --> src/main.rs:13:1 |
  bootloader::entry_point!(kernel_main); | types differ in
  mutability | expected fn pointer fn(&'static BootInfo) -> _,
  found fn(&'static mut BootInfo) -> _` (bootloader 0.9.35 wants a
  shared ref). DONE (recorded).
- OS-004: fixed in one commit (faae3ed): kernel_main now takes
  `&'static bootloader::BootInfo`. No other code changed. DONE.
- OS-005: `cargo bootimage` OK.
  Image: kernel/target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin,
  59904 bytes, valid DOS/MBR boot sector. DONE.
- OS-006/007: first QEMU boot in progress (2026-11-01). Notes:
  `-display none -serial file:` gave silence (killed at 15–55 s);
  `-nographic` shows SeaBIOS 1.17.0 -> iPXE -> "Booting from Hard
  Disk... (first stage)... (second stage)..", i.e. the bootloader IS
  loading but TCG x86_64-on-ARM is slow (100% CPU, stage 2 past 45 s).
  Giving it up to 9 min; serial captured to os-build/logs/K1-boot.txt.
  UPDATE 10:04: stage 2 was NOT slow — it was dead. Screendump via QMP
  showed the bootloader panicking on VGA (invisible on serial):
  `panicked at src/page_table.rs:105:25: Failed to map segment
  starting at Page[4KiB](0x1000): ... PageAlreadyMapped(...)`.
  Root cause (verified, not guessed): rustc 1.99.1 emits a static-PIE
  kernel (`file` says `pie executable, static-pie linked`; overlapping
  LOAD/RELRO segments), which bootloader 0.9.35's mapper double-maps.
  Fix (committed): `relocation-model=static` in
  kernel/.cargo/config.toml; `file` now says `statically linked`;
  image 58368 bytes. Reboot in progress.
  UPDATE 10:0x: K1 ALIVE — `META OS KERNEL - alive (K1)` on serial
  ~20 s after launch (fixed image). OS-006/007 DONE.
- OS-008: triple boot DONE 2026-11-01 (K1-boot-run1/2/3.txt):
  1 alive line each, all byte-identical
  (`META OS KERNEL - alive (K1)`).
- OS-009: K1 section. Built: kernel/ as written + 2 fixes (entry_point
  shared ref; static relocation model). Booted: QEMU 11.1.3 -nographic,
  512M, our bootimage .bin. Log: os-build/logs/K1-boot.txt (+ runs).
  Unproven: everything past printing one line (no console, no
  interrupts, no memory management — Sections B–F).
- OS-010: image 58368 bytes (static build); bootloader crate 0.9.35
  (bootimage 0.10.5 wraps it). DONE.
- OS-011: no blocker hit (toolchain + boot issues fixed in-section).
- OS-012: Section A summary. K1 proven on this Mac: our kernel binary
  prints the alive line on QEMU serial, 3/3 boots identical. Fixes:
  entry_point shared ref, static relocation model, rust-src + target
  + llvm-tools components. Logs: K1-boot.txt (+ run1/2/3). Next:
  Section B framebuffer. DONE — pushing.

## Section B — K2 text console (OS-013..OS-028) — DONE, with one honest NOT BUILT

- OS-013: `os-build/research/framebuffer.md` written from the
  vendored 0.9.35 source. Finding: BootInfo has NO framebuffer field
  (memory_map + recursive_page_table_addr + physical_memory_offset
  only; `grep -c framebuffer` = 0). This also answers crew Q5: no
  accessor exists to confirm. Rowan's pixel-console draft stays
  in-tree, unwired, with no buffer to drive. DONE.
- OS-014 (adapted): text cells come from VGA hardware at phys
  0xB8000 via physical_memory_offset, not from BootInfo pixels.
- OS-015: `VgaConsole::clear` to dark background at boot. DONE.
- OS-016: pixel grid NOT BUILT — no pixel surface exists under
  bootloader 0.9.35 (recorded per OS-027; VBE setup is a follow-up
  beyond this section, named in the next-steps list).
- OS-017: font = VGA ROM hardware font; nothing embedded, license
  N/A. DONE (no Terminus table needed on this branch).
- OS-018/019: `META OS - milestone K2` banner, writer with
  position/newline/scroll. DONE.
- OS-020: banner + `META OS KERNEL - alive (K1)` on screen AND
  serial (screendump + K2-boot.txt). DONE.
- OS-021: `print!`/`println!` dual-output macros (fmt::Write over
  serial + console; missing console degrades to serial). DONE.
- OS-022: panic handler paints red PANIC screen + serial line. DONE.
- OS-023: `K2-boot.txt` + `K2-console.png` screendump. DONE.
- OS-024: forced-panic drill via `panic-test` cargo feature:
  `K2-panic-drill.txt` + red `K2-panic.png`
  (`panicked at src/main.rs:110:5: K2 forced panic drill`); normal
  builds unaffected (feature off by default). DONE.
- OS-025: resolution recorded: 80x25 text cells (VGA mode 3), not a
  pixel format — no BootInfo geometry to report. DONE.
- OS-026: `os-build/research/unsafe-ledger.md` started. DONE.
- OS-027: fallback documented in framebuffer.md: serial + VGA text;
  pixel framebuffer absent, stated, not faked. DONE.
- OS-028: this summary. Pushing.

## Section C — K3 interrupts, timer, keyboard (OS-029..OS-044) — DONE

- OS-029/030: 256-entry IDT (`traps.rs` R5 wiring over Rowan's
  `interrupts.rs`); `int3` drill prints
  `INT exception breakpoint vector 0x3` and RETURNS into the uptime
  loop. DONE (K3-break.txt).
- OS-031: double fault on IST stack 0 (own GDT `gdt.rs` + TSS +
  `ltr`). Proven by `stack-test` overflow drill:
  `INT exception double-fault vector 0x8`. The first attempt
  triple-faulted — QEMU `-d int` trace showed #DF delivery raising
  #SS: plain `repr(C)` pads the TSS so IST[0] sat 4 bytes off
  (RSP0 is at byte 4, not 8). Fixed with `repr(C, packed(4))` +
  `write_unaligned` + a 104-byte size assert. DONE (K3-doublefault.txt).
- OS-032: PIC remap to 32/40, standard ICW sequence. DONE.
- OS-033/034: PIT 100 Hz exact (ticks 100/200/300...), `uptime Ns`
  printed each second from the echo loop's `hlt` sleep. DONE.
- OS-035/036/037: IRQ 1 scancodes into the 64-entry ring;
  set-1 decode for letters/digits/space/enter (shift NOT handled,
  stated limit); echo on screen + serial. DONE.
- OS-038: QMP `send-key` typed `hello123`+Enter; echoed back
  `\nhello123\n`, releases ignored, 18 IRQ lines. DONE.
- OS-039: 98 uptime lines (`uptime 98s ticks 9800`), zero stalls,
  EOI correct on both IRQs. DONE (K3-boot.txt).
- OS-040: `fault-test` read of 0xdeadbeef prints
  `addr 0xdeadbeef ... err 0x0`. Gap found and fixed on my branch:
  Rowan's `print_exception` never read CR2, so the address was
  missing — his `page_fault_handler` now reads CR2 first (marked
  Mac-build note). Handler returns, so the test build re-faults in
  a fast loop (expected; K6 adds kill semantics). DONE (K3-fault.txt).
- OS-041: unsafe ledger extended (gdt/traps/test hooks). DONE.
- OS-042: `os-build/research/interrupts.md` vector map. DONE.
- OS-043: sendkey scripting worked first try; no manual steps
  needed. DONE (moot).
- OS-044: this summary. Pushing.
