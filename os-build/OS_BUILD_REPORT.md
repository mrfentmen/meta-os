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
