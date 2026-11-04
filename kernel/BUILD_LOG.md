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
| K1 | `META OS KERNEL - alive (K1)` (line 2 of `K1-boot.txt`) | **PROVEN** |
| K4 | `mem map: 15 regions, usable 246640K` … `mem heap: 512K` … `mem stress 10k ok` … `mem summary: K4 up` (`K1-boot.txt`) | **PROVEN** |
| K5 | `A` / `B` / `C sleeping 200 ticks` alternating, `C awake` after the sleep (`K1-boot.txt`) | **PROVEN** |
| K6 | `HELLO FROM USERSPACE`, `user exit code 0`, `user bad syscall 99 refused`, page fault `err 0x4: task killed` (`K1-boot.txt`) | **PROVEN** |
| K2 | `screendump` of the live VGA buffer: 196 of 2000 cells carry glyphs on rows 0-10 and 24 — the banner, the alive line and the memory summary as pixels (`os-build/logs/K2-boot.png`); 215 cells on the shell/attract screen (`K2-shell.png`) | **PROVEN** by capture, not by serial |
| K3 | `K3 timer: 10 ticks after 407902 spins` (measured, not asserted) and `K3 keyboard: first scancode 0x1f`, then a typed `status` answered `STATUS tasks=7 ticks=169 heap_free_kb=287` (`K3-boot.txt`) | **PROVEN** |

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

**The keyboard capture is timing-flaky, and that is recorded rather than hidden.** Three runs
of `prove_k2_k3.sh` against the same image gave one green run (scancode `0x1f`, typed `status`
answered) and two where the RFB client connected, reported all seven keys sent, and the guest
recorded nothing. The console task spawns only after the scheduler starts, and how long that
takes varies with machine load; the i8042 holds one byte until the ring is drained, so a burst
that arrives too early is lost. The green capture is committed as `K3-boot.txt`. The harness
now retries the command at three points and writes to a scratch file, promoting it to the
evidence name only on a full pass, so a flaky run can never overwrite a proven log again.

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

## Lane E entry (R5, 2026-11-04, branch agent-r5)

Status: **BUILT and BOOTED on this Mac. New proofs: K3 demand paging
(first-ever `page mapped, retry` from this tree), syscall-5 typed-key
delivery to userspace (`readkey got 35` … `enter seen`), read-only PCI
scan (6 real QEMU devices), kernel-side IPC self-test (all 6 legs),
framebuffer screendump (kernel-drawn desktop, 1280x720).** No new
syscall numbers; `user.rs` dispatch untouched; `syscalls.rs` untouched.

Toolchain (measured, same pins as the first entry above):

| item | value |
|---|---|
| rustc | `1.101.0-nightly (f9ceb4a4d 2026-10-31)` |
| cargo | `1.101.0-nightly (31d3246e0 2026-10-27)` |
| target | `x86_64-unknown-none` (installed; `rust-src` + `llvm-tools-preview` present) |
| bootloader | `0.11.17` (`kernel/Cargo.lock`) |
| QEMU | `11.1.3` |

Exact commands, in order (nightly pinning is the same one-liner as above):

```sh
export RUSTC="$(rustup which --toolchain nightly rustc)"
export PATH="$(dirname "$RUSTC"):$HOME/.cargo/bin:$PATH"
export RUSTUP_TOOLCHAIN=nightly RUSTC_BOOTSTRAP=1
python3 os-build/userspace/build_userspace.py   # 5 bins, first-LOAD == base verified
sh os-build/rk007/build.sh                      # kernel ELF + 0.11.17 BiosBoot disk.img
# boot 1 (serial evidence, typed help+status):
qemu-system-x86_64 -drive format=raw,file=os-build/rk007/disk.img \
  -serial file:kernel/logs/E-boot-20261104.txt -display none -m 512M -no-reboot \
  -monitor unix:$TMPDIR/E-mon.sock,server,nowait
python3 os-build/tools/drive.py --monitor $TMPDIR/E-mon.sock help status
# boot 2 (PCI + IPC + framebuffer evidence, typed help+status+ipc):
qemu-system-x86_64 -drive format=raw,file=os-build/rk007/disk.img \
  -serial file:kernel/logs/E-boot-vnc.txt -display none -vnc :43 -m 512M -no-reboot \
  -monitor unix:$TMPDIR/E-vnc-mon.sock,server,nowait
python3 os-build/tools/drive.py --monitor $TMPDIR/E-vnc-mon.sock help status ipc
# screendump through the monitor, then PPM->PNG with sips
```

Artifacts (this lane's evidence, committed under `kernel/`):

```
kernel/target/x86_64-unknown-none/debug/metaos-kernel  17588736 bytes
os-build/rk007/disk.img                                20415488 bytes (built, not committed)
kernel/logs/E-boot-20261104.txt  (boot 1: K1-K6 + demand + readkey typed proof)
kernel/logs/E-boot-vnc.txt       (boot 2: + PCI scan + ipc selftest + STATUS)
kernel/logs/E-framebuffer.png    (1280x720 screendump of the kernel desktop;
                                  converted from QEMU's PPM with sips, PPM not kept)
```

E20 regression quotes (all from `kernel/logs/E-boot-vnc.txt`):

| milestone | line |
|---|---|
| K1 | `META OS KERNEL - alive (K1)` (:26) |
| K2 | `KF-03 framebuffer: 1280x720 stride 1280 bpp 3 (screen live)` (:24) + `E-framebuffer.png` |
| K3 | `K3 timer: 10 ticks after 505620 spins` (:27), `K3 keyboard: first scancode 0x23` (:783), `STATUS tasks=9 ticks=1878 heap_free_kb=223` (:809) |
| K4 | `mem frames: 125449 usable total`, `mem probe page ok, unmapped`, `mem Box+Vec ok (box 42, vec sum 120)`, `mem summary: K4 up` (:143) |
| K5 | `A`/`B` interleave (:144-148), `C sleeping 200 ticks` (:146), `C awake` (:180) |
| K6 | `HELLO FROM USERSPACE` (:151), `user exit code 0` (:152, :167), page-fault kill (:163, :179) |

Known gap in this log (not a regression, stated): no `user bad syscall
99 refused` line — the current `sleeper.rs` no longer issues syscall 99
(the drill lives in `badcall.rs`, which is WRITTEN but not in
`build.rs` BINS and has no spawn slot; `MAX_TASKS` is full at 9/9).
The refusal arm in `user.rs` is byte-identical to the proven tree.

New-behavior quotes (same log unless noted):

- Demand: `demand: touching promised page` (:175),
  `INT user demand-fault addr 0x0000700000000000: page mapped, retry`
  (:176), `demand: zero-fill confirmed` (:177),
  `demand: writeback OK, touching outside region` (:178),
  `INT user page-fault addr 0x0000700000100000 ... task killed` (:179),
  then `C awake` (:180, other tasks continue).
- Readkey typed proof (boot 1, `kernel/logs/E-boot-20261104.txt`
  :912-937): `K3 keyboard: first scancode 0x23`, `readkey got 35`
  (0x23 press), `163` (release), … `readkey got 28` (Enter),
  `readkey: enter seen, done got=9`, `user exit code 0`, then the
  shell's own `commands:` + `STATUS` lines — both readers saw every byte.
- PCI (`:118-125`): `00:0.0 8086:1237`, `00:1.0 8086:7000`,
  `00:1.1 8086:7010 class 01/01/80` (IDE — the device the storage
  lane must drive), `00:1.3 8086:7113`, `00:2.0 1234:1111 class
  03/00/00` (VGA), `00:3.0 8086:100e class 02/00/00` (e1000 net).
- IPC self-test (`:811-817`): sent / full-box refusal / small-buffer
  refusal with message kept / received 10 bytes from self / empty /
  dead-peer (`id 1 not live`) / done. Prefix is `ipc selftest:`, NOT
  the pinned `user ipc ...` ring-3 gate lines — the talker/listener
  acceptance pair (Buffy) stays owed.

What was NOT done (Lane E findings, no paint):

- Syscall 6 collision: `os-build/KERNEL_SPEC.md:130` says 6 = cap_query,
  but Pax assigned 6/7 to K4 IPC (`os-build/K4_REVIEW_PAX.md:24-30`)
  and the tree implements 6 = ipc_send / 7 = ipc_recv. The caps kernel
  files were deliberately excluded from the merge for exactly this
  collision (merge `4fd9653c`). Lane E did NOT implement cap_query and
  added no syscall: E7 waits on the boss's syscall-6 call.
- Storage E9-E12 (sector read, FAT/ext2 mount, list/read file): no
  driver exists; the scan above is detection only. Nothing written to disk.
- Graphics E13 verdict: the E13 premise (no framebuffer under
  bootloader 0.9.35) is outdated — under 0.11 the bootloader supplies
  1280x720 Bgr and the kernel draws real rectangles on it (desktop,
  bars, window, dock; see PNG). Still true: no modesetting of its own,
  no windowing/compositor, no mouse — E25 holds, no desktop claimed.
- Driver gaps: timer rate measured every boot (100.0153 Hz by divisor);
  serial mirror is the dual-output `print!` (+ bounded UART drop after
  `SERIAL_TX_SPINS`); PS/2 mouse, ACPI shutdown, PCI storage/net
  drivers do not exist (`grep -ri mouse\|acpi kernel/src/` is empty
  save the icons.rs decorative note). QEMU exposes the ACPI PM device
  (`00:1.3 8086:7113`) and e1000 (`00:3.0`) for those lanes.
- Hardware-vs-QEMU (E22): NOTHING in this log has run on metal. QEMU
  11.1.3 TCG supplies the PIT at exact crystal rate, the i8042, the
  1280x720 Bgr framebuffer, SeaBIOS PCI topology above, and unbounded
  serial patience. A real board changes all five; the timer divisor,
  keyboard controller, GOP framebuffer format, PCI topology, and UART
  presence each need re-proof on hardware.
