# K1 RUN SHEET — Mac + QEMU (Pax addendum to OPENCODE_OS_BUILD.md Section A)

Written 2026-11-01 by Pax when the boss reported QEMU installed on the
Mac. Section A (OS-001..OS-012) is the task list; this sheet is the
exact command path plus the three toolchain traps Section A does not
name. Main tip at writing: `cbe3e7d` (kernel K1 crate + K2–K6 drafts
all merged, `kernel/src/main.rs` is K1-only, proof string
`META OS KERNEL - alive (K1)`).

## Traps (hit these first, in this order)

1. **build-std needs nightly.** `kernel/.cargo/config.toml` sets
   `build-std = ["core", "compiler_builtins"]`, which is unstable:
   a stable toolchain fails before compiling anything. Use a nightly
   toolchain for every kernel command (`cargo +nightly ...`), and add
   the `rust-src` component (build-std compiles core from source).
2. **bootimage needs llvm-tools.** `cargo install bootimage` (0.10.x,
   the line that pairs with `bootloader = "0.9"` in
   `kernel/Cargo.toml`) shells out to `llvm-objcopy` from the
   `llvm-tools-preview` component. Missing component = a late,
   confusing failure at the image step, not the build step.
3. **`cargo run` hides the serial log in the QEMU window.** For the
   proof, boot the built image directly with serial to a file
   (step 5). That file is the K1 evidence, not a screenshot.

## Commands

```sh
git pull   # main @ cbe3e7d or later
git checkout -b opencode/os-build   # per OPENCODE_OS_BUILD.md rules

rustup toolchain install nightly
rustup target add x86_64-unknown-none --toolchain nightly
rustup component add rust-src llvm-tools-preview --toolchain nightly
cargo install bootimage

cd kernel
cargo +nightly bootimage
# image: target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin
# the build also resolves kernel/Cargo.lock — Q1 needs it committed.

mkdir -p ../os-build/logs
qemu-system-x86_64 \
  -drive format=raw,file=target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin \
  -serial file:../os-build/logs/K1-boot.txt \
  -display none -m 128M
# kernel prints then spins; kill QEMU after ~5 seconds.
grep "META OS KERNEL - alive (K1)" ../os-build/logs/K1-boot.txt
```

Boot 3 times (OS-008): same alive line in all 3 logs.

Notes: on Apple Silicon, `qemu-system-x86_64` emulates under TCG —
fine for a serial-print kernel, speed is not a proof factor. A panic
prints `META OS KERNEL - panic` on the same serial line; if that is
what the log shows, the log is still the report (OS-007).

## Hand-back

- First error list goes into `os-build/OS_BUILD_REPORT.md` verbatim
  BEFORE any fix (OS-003). Small fix commits, one error class each.
- Push to `opencode/os-build`: the boot log(s), `kernel/Cargo.lock`,
  the report. Post the outcome on room 1.
- Pax merges. The K1 log + Cargo.lock answer Q1 and unblock Rowan's
  R5 wiring (one module per commit onto the proven tree).
