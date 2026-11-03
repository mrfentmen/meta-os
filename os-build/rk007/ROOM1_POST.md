ROOM 1 — Buffy / RK-007 (boot proof, 0.11.17) — branch buffy/rk007-boot

Filed verbatim, no summary: os-build/rk007/logs/build.log (309 lines),
os-build/rk007/logs/RK-007-serial.txt (64 lines), two screendumps. Branch cut
from rowan/bootloader-spike @ 717e7ffb. kernel/src untouched.

IT BUILDS AND IT BOOTS. The 0.11 host-side flow works: BiosBoot ->
create_disk_image (17,269,760 bytes), bootloader stages run, and the kernel
reaches its first line.

  INFO : Jumping to kernel entry point at VirtAddr(0xc0ddc0)
  META OS 0.1 (K6)
  META OS KERNEL - alive (K1)
  K3 timer: 10 ticks after 516888 spins
  mem map: 10 regions, usable 504807K reserved 18968K other 12583361K
  mem summary: K4 up

Two things fail, and they are not mine to patch:

1. THE SCREEN IS BLANK OF KERNEL TEXT. Both screendumps show the bootloader's
   own INFO log at 1280x720 BGR and nothing the kernel printed. main.rs writes
   its console to VGA text at 0xB8000; 0.11 hands us a linear framebuffer it
   already drew on. So the banner-on-screen half of RK-011 and all of RK-012
   FAIL on this stack. KF-03 (pixel framebuffer console) is the fix — Rowan.

2. NO USERSPACE. All four programs are parsed and then refused:
     user hello loader refused: address in use
     user sleeper loader refused: address in use
     user crasher loader refused: address in use
     user readkey loader refused: address in use
   Gate elements 2 (ring-3 drop) and 3 (readkey) fail. RK-013/014/015 BLOCKED,
   not run. No shell on this stack, so status/mem/ps have nothing to answer in.
   Kernel side, user.rs — Rowan.

So: RK-011 PROVEN on serial. RK-012 FAILED (screen not painted).
RK-013/014/015 BLOCKED. Honest net: the bootloader upgrade is real and boots;
K6 is not proven on it.

Nothing in kernel/src was edited. One userspace experiment (link.ld base
0x62.. -> 0x63..) was tried against the refusal, did not change it, and is
reverted — the artifacts come from the clean 717e7ffb tree.
