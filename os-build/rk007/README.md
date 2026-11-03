# RK-007 — boot proof on bootloader_api 0.11.17

Lane: Buffy (boot lane, per `os-build/BUFFY_PROMPT.md`). Branch:
`buffy/rk007-boot`, cut from `rowan/bootloader-spike` @ `717e7ffb`.
Nothing in `kernel/src` was touched; `git diff 717e7ffb..buffy/rk007-boot`
is new files only.

Labels: **VERIFIED** = a line in a log in this directory. **CODE-INSPECTED**
= read the source, not proven at runtime. **BLOCKED** = could not run.

## Reproduce

```sh
os-build/rk007/build.sh 2>&1 | tee os-build/rk007/logs/build.log   # exit 0
os-build/rk007/boot.sh                                             # exit 0
```

`build.sh` is the 0.11 flow: 4 userspace ELFs, kernel ELF, then the
HOST-side `bootloader` crate (`BiosBoot::create_disk_image`). There is no
`bootimage` flow in 0.11 and none is used.

## Proven

| claim | evidence | label |
|---|---|---|
| image builds on the 0.11.17 pin | `logs/build.log` tail: `image 17269760 bytes`, `build: done` | VERIFIED |
| 0.11.17 BIOS stages run to the kernel entry | serial: `INFO : Jumping to kernel entry point at VirtAddr(0xc0ddc0)` | VERIFIED |
| kernel reaches its first line | serial: `META OS KERNEL - alive (K1)` | VERIFIED |
| PIT actually fires (measured, not inferred) | serial: `K3 timer: 10 ticks after 516888 spins` | VERIFIED |
| boot memory map is read correctly | serial: `mem map: 10 regions, usable 504807K reserved 18968K other 12583361K`, `mem frames: 126201 usable total`, `mem summary: K4 up` | VERIFIED |
| scheduler rotates, sleeps, wakes | serial: `A` / `B` / `C sleeping 200 ticks` / … / `C awake` | VERIFIED |

The serial log is `logs/RK-007-serial.txt` (64 lines, 3137 bytes), from
power-on, including the bootloader's own INFO lines.

## NOT proven — read before merging

**1. The screen shows no kernel output.** Both screendumps
(`RK-007-shot-1.png`, `RK-007-shot-2.png`) carry the bootloader's INFO log at
1280x720 BGR and nothing the kernel printed: no `META OS 0.1 (K6)`, no alive
line, no timer line. That is VERIFIED from the images.

Why (CODE-INSPECTED): `kernel/src/main.rs` writes its console into VGA text
memory at `0xB8000` (`vga.rs`), but the 0.11 bootloader hands the display over
in 1280x720 linear-framebuffer mode and has already drawn its own log there.
The text buffer is not the displayed surface, so kernel prints reach serial and
never reach the panel. Consequences: the banner-on-screen half of RK-011 and
all of **RK-012 fail on this stack**. The fix is KF-03 (pixel framebuffer
console) — Rowan's pen, not this lane.

**2. All four userspace programs are refused.** Serial, all four:
`user hello loader refused: address in use`, and the same for `sleeper`,
`crasher`, `readkey`. Each ELF is read and parsed (`magic=0x464c457f`,
`type=Some(2)`, entry parsed) and then refused by the loader. Consequence:
gate elements 2 (ring-3 drop) and 3 (readkey) fail; RK-013, RK-014, RK-015 are
**BLOCKED**, not run. Kernel-side (`user.rs`) — Rowan's, not this lane.

**3. No shell exists on this stack**, so the `status` / `mem` / `ps` smoke and
the bad-syscall smoke have nothing to run in.

Net: **RK-011 PROVEN on serial. RK-012 FAILED. RK-013/14/15 BLOCKED.**

## Artifacts

- `logs/build.log` — full build output, 309 lines, verbatim.
- `logs/RK-007-serial.txt` — full boot serial, 64 lines, verbatim.
- `logs/RK-007-shot-1.png`, `logs/RK-007-shot-2.png` — screendump set (PNG is a
  lossless conversion of QEMU's PPM; the 2.7 MB PPMs are not committed).
- `build.sh`, `boot.sh` — the two drivers, kept so Pax can re-run this himself.
- `image-builder/` — the host-side image builder (`bootloader = "=0.11.17"`).

## What I changed, and reverted

One userspace experiment: `os-build/userspace/user/link.ld` link base
`0x620000000000` -> `0x630000000000`, tried while the loaders were refusing. It
did not change the refusal, so it is **reverted**; the tree behind these
artifacts is `717e7ffb` with no source edits. The refusal reproduces on the
clean tree (this rebuild did).
