# Kernel build log — the first build and boot (2026-11-02)

Status: **BUILT and BOOTED on this Mac, all six milestones evidenced.** The kernel checks,
links behind bootloader 0.9.35, produces a bootable image, and boots in QEMU. The serial logs
are committed at `os-build/logs/K1-boot.txt` (K4/K5/K6 behavior) and `K3-boot.txt` (timer,
keyboard, typed shell command), with VGA captures at `K2-boot.png` / `K2-shell.png`.

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
| K2 | `screendump` of the live VGA buffer: 196 of 2000 cells carry glyphs on rows 0-10 and 24 — the banner, the alive line and the memory summary as pixels (`os-build/logs/K2-boot.png`); 215 cells on the shell/attract screen (`K2-shell.png`) | **PROVEN** by capture, not by serial |
| K3 | `K3 timer: 10 ticks after 407902 spins` (measured, not asserted) and `K3 keyboard: first scancode 0x1f`, then a typed `status` answered `STATUS tasks=7 ticks=169 heap_free_kb=287` | **PROVEN** |

All six milestones now have evidence. K2's evidence is a screen capture rather than a serial
line, which is the only form that can exist: the VGA console writes to memory that a serial
port never sees.

## Capturing the screen and the keyboard (K2/K3)

`os-build/layer1/prove_k2_k3.sh` boots the image with a headless VNC console, takes
`screendump`s at two moments, and types into the machine. `screen_evidence.py` converts each
dump to PNG and prints an 80x25 occupancy map, so a blank screen fails the check instead of
passing as "the file exists". `vnc_type.py` speaks RFB 3.8 with the standard library and sends
KeyEvent messages, which QEMU translates into set-2 scancodes for the emulated i8042 — the
same bytes a real keyboard produces, read by the kernel's own IRQ1 handler.

Three traps cost a run each and are recorded so nobody pays for them twice:

1. `-display none` has no graphical console, so the monitor's `sendkey` is accepted and
dropped. The kernel polls an empty ring buffer and the log looks like a broken driver.
2. `-vnc` alone is not enough: key events route through the display's input handler, which
exists only while a client is connected.
3. A VNC client must send `FramebufferUpdateRequest` before QEMU treats it as an input
source. It is 10 bytes: type, one byte incremental flag, then x/y/w/h. Packing incremental
as a u16 makes 11 and QEMU closes the connection mid-typing.

## Timer accuracy (K3, K14)

The PIT divisor is `1_193_182 / 100 = 11931`, so the real rate is 1193182 / 11931 =
**100.0153 Hz**, not exactly 100. That is +0.015 % — 1.3 seconds fast per day. It is a
programmed constant, not drift: the PIT crystal is exact in QEMU and nominally 14.31818 MHz on
a real board, so the honest statement is "100.0153 Hz by divisor, unmeasured against a
reference clock". Anything that needs wall time must not derive it from ticks alone.

## Reproduce

`os-build/layer1/build_kernel.sh` builds, boots, and refuses to continue if the alive line is
missing. `os-build/layer1/prove_k2_k3.sh` adds the screen and keyboard evidence and exits
non-zero unless the timer line, the typed command and both non-blank screens are all present.
