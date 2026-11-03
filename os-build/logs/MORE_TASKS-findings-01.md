# MORE_TASKS findings sweep (tips e5ce311b..54ee4353, 2026-11-02 ~08:00 EST)

Task 4 (K1-K6 proofs): K2 is the only item with a ready branch —
rowan/kernel-readkey-merge @ 419c209, gate GREEN on Mac
(entry 0x630000000010, 8 tasks, 0 panics, two-reader got=7;
logs on opencode/round6). Main does NOT spawn readkey yet
(sched.rs grep count 0 at 54ee4353): Pax merge pending, not a
proof gap. K1/K3/K4/K5/K6: no branches (hana/os-buildout is
DEMO/script work, no kernel); bootloader spike part 2 (the
version task 5 needs) has not landed — nothing to execute.
Task 8 (hog/talker/listener/quitter): hog/talker/listener absent
from os-build/userspace/user/src/bin/ (bins present: badcall,
crasher, hello, quitter, readkey, sleeper, writer). quitter
compiles but is unwired: kernel embeds+spawns 3 programs only,
tip boot log contains 0 quitter lines vs USERSPACE_PROGRAMS.md
spec — finding, wiring is Rowan's lane per
os-build/proposals/quitter-badcall-wiring.md. No kernel edits
made from this lane.
Task 7: UTM has no headless create/import (utmctl lists zero
VMs); QEMU boots stand as machine evidence. Toolchain in bake:
node+git+chromium present, opencode absent (finding stands).
