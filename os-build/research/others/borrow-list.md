# Borrow list, consolidated (OS-113)

Each system already has its own page under
`os-build/research/distros/` (OS-105..OS-112, Buffy lane, verified
present with idea + license position each). One line per system
here, with the take/skip call:

- NixOS → TAKE the generation/rollback idea (declared state,
  never mutate in place). NixOS itself: NO (LGPL toolchain, and
  the carrier stays Debian by spec).
- Arch → TAKE the small-base-plus-explicit-assembly discipline
  (every component chosen, nothing default). The distro: NO.
- Alpine → TAKE small/fast/boot-fast as a budget (musl lesson:
  libc choice is a size decision). The distro: NO.
- SteamOS → TAKE the appliance boot (power → the thing, no
  desktop in between). The distro: NO.
- ChromeOS → TAKE verified boot + powerwash (known-good state,
  one-button return). The browser-as-OS: NO.
- Redox → TAKE the microkernel structure lesson (what lives in
  the kernel vs out of it). The kernel code: NO (ours is ours,
  KERNEL_SPEC rule 1, even though Redox is MIT).
- Serenity → TAKE the steady-milestone rhythm (small provable
  steps, always bootable). The code: NO.
- Haiku → TAKE the single-purpose focus (one machine, one job,
  done well). The code: NO.

License posture for all eight: IDEAS ONLY. No code crosses over
(see clean-room.md rule 5 and the red list in ranking.md).
