# PROMPT FOR BUFFY — from Pax, 2026-11-02 (boss: Mrfentmen)

Pull the latest main of mrfentmen/meta-os and read this file first. It
supersedes your boot-lane and gate-pack assignments as previously posted.

## Your lane now: you are the boot lane

OpenCode 1 and OpenCode 2 are finished. You are the only QEMU-authorized
runner left. In this order, ahead of Round 13:

### 1. RK-007 — boot proof for the bootloader upgrade (do this first)
- Tree: branch `rowan/bootloader-spike` @ 717e7ffb (bootloader_api 0.11.17
  pin + RK-008 rewrite). Milo gate-1 is GREEN on it, compile only.
- Build the boot image on the Mac lane: the 0.11 flow uses the HOST-side
  `bootloader` crate as the image builder. There is no bootimage flow in
  0.11. `physical_memory_offset` is Optional in 0.11 — the rewrite already
  handles it.
- Boot the image in QEMU. File on your branch, verbatim, nothing summarized:
  the full build log, the full boot serial log, and a screendump set.
- Post to room 1 as it lands. Pax reads the logs himself; the merge decision
  is his after that.
- You never edit kernel/src (Rowan's pen). If the build or boot fails, file
  the verbatim error and stop that attempt — do not patch kernel code.

### 2. K3 and K4 gate packs — DONE, do not re-run them
- OpenCode 1 ran both packs; they are on main
  (os-build/logs/OC1B-k3-gatepack.md, OC1B-k4-gatepack.md).
- K3 @7bb72075: demand leg FAILED (promised-page touch faulted err 0x5,
  zero map lines). Fix is Rowan's. You re-gate only when Pax says a fix
  branch has landed.
- K4 @4a37f998: builds and boots, panic 0, but zero IPC lines — no
  talker/listener pair exists and no spawn swap is in Rowan's branch.
  Re-gate only when the pair + swap land on a Rowan branch and Pax calls it.

### 3. Then Round 13
- Read BUFFY_TASKS_ROUND13_500.md (repo root) and work it in order on
  branch buffy/round13. Keep os-build/BUFFY_ROUND13_STATUS.md current.
  Commit per section. Round 12 is fully merged — do not redo it.

## Fences (unchanged, absolute)
- Never edit kernel/src. kernel/src/syscalls.rs is FROZEN.
- Imperium dispatch is the labelled simulated loopback endpoint only.
  Never a real 911 service, never a non-loopback dispatch URL.
- No mock or placeholder work presented as done. Label every claim
  VERIFIED / CODE-INSPECTED / UNIMPLEMENTED / BLOCKED.
- All merges to main go through Pax. You commit to your branch; he merges.
- Post build status to room 1 as things land, not only at the end.
