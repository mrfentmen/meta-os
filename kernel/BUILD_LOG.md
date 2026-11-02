# Kernel build log — the first build and boot (2026-11-02)

Status: **BUILT and BOOTED on this Mac.** The kernel checks, links behind bootloader
0.9.35, produces a bootable image, and boots in QEMU. The serial log is committed at
`os-build/logs/K1-boot.txt` (54 lines, from this artifact).

This file exists because the project spent days calling the kernel UNCOMPILED. It is now
compiled, and the first thing that has to be written down is exactly how — including the
part that failed twice for a reason that had nothing to do with our code.

## Toolchain (measured, not assumed)

| item | value |
|---|---|
| rustc | `1.101.0-nightly (f9ceb4a4d 2026-10-31)` |
| cargo | `1.101.0-nightly (31d3246e0 2026-10-27)` |
| target | `x86_64-unknown-none` |
| bootloader | `0.9.35` (`kernel/Cargo.lock`) |
| bootimage | `0.10.5` |
| components | `rust-src`, `llvm-tools-preview` (nightly) |
| QEMU | `11.1.3` |

## The two failures, and the one fix

`cargo check` with the shell's `cargo` fails with **`can't find crate for core`**: `cargo` on
this Mac is Homebrew's, while the `x86_64-unknown-none` target is installed under rustup. The
Homebrew sysroot has no `core` for that target.

`rustup run nightly cargo check` gets further but dies with **`the option Z is only accepted on
the nightly compiler`** — because `cargo` spawns `rustc` from `PATH`, and `PATH` resolves to
Homebrew's stable `rustc`. The nightly cargo was running a stable compiler.

The fix is one line, and it is not obvious: **pin `RUSTC` and put the nightly toolchain first in
`PATH`**, so both the outer cargo and the ones `bootimage` spawns use the same compiler.

```sh
cd kernel
export RUSTC="$(rustup which --toolchain nightly rustc)"
export PATH="$(dirname "$RUSTC"):$HOME/.cargo/bin:$PATH"
export RUSTUP_TOOLCHAIN=nightly
rustup component add rust-src llvm-tools-preview --toolchain nightly
cargo bootimage
```

Without the `PATH` prefix the bootloader stage fails with `llvm-tools not found`: its build
script looks in the sysroot of the compiler cargo spawned, which was stable's.

## The artifact

```
kernel/target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin
8.0M   sha256 aeb1664d89c46d3560c011ec77b58ee182c175224e73834788f5f8dfb451b0f5
```

The image is a build output, not a committed binary. The hash is here so a different build can
be told apart from this one. Kernel warnings: **24, zero errors** (`cargo check` exit 0).

## The boot

```sh
qemu-system-x86_64 \
  -drive format=raw,file=kernel/target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin \
  -serial file:os-build/logs/K1-boot.txt \
  -display none -m 256M -no-reboot
```

Captured 2026-11-02. `-display none` is why the VGA console cannot be judged from this log: it
draws to a screen nobody captured.

## What this log proves, line by line

| milestone | evidence in `K1-boot.txt` | verdict |
|---|---|---|
| K1 | `META OS KERNEL - alive (K1)` (line 2) | **PROVEN** |
| K4 | `mem map: 15 regions, usable 246640K` … `mem heap: 512K` … `mem stress 10k ok` … `mem summary: K4 up` | **PROVEN** |
| K5 | `A` / `B` / `C sleeping 200 ticks` alternating, `C awake` after the sleep | **PROVEN** |
| K6 | `HELLO FROM USERSPACE`, `user exit code 0`, `user bad syscall 99 refused`, page fault `err 0x4: task killed` | **PROVEN** |
| K2 | nothing on serial — VGA is a screen, not a serial device | **NOT PROVEN by this log** |
| K3 | no timer-tick or key line; the only `tick` is `C sleeping 200 ticks` | **PARTIAL / NOT PROVEN** |

The distinction matters. K1, K4, K5 and K6 can be cited from this file. K2 and K3 cannot, and
the next task is to make them citable rather than to assume the code works because it compiled.

## Reproduce

`os-build/layer1/build_kernel.sh` runs the three steps above and refuses to continue if the
alive line is missing from the captured log.
