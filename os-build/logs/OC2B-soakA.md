# OC2B-101–110 — Soak A (60 min, text tree)
- Start (UTC): 2026-11-02T16:26:24Z
- Tree: opencode2/500 @ 14faa6e5 (kernel/ untouched = main text tree)
- Tree choice: newest proven TEXT tree (graphics unlanded — no framebuffer code on main). Named per OC2B-101.
- QEMU: qemu-system-x86_64 11.1.3, -m 512M -display none -no-reboot, serial file, monitor unix socket.
- Image: kernel bootimage built from scratch worktree /tmp/oc2b-soak (same tip).

## Checkpoint 1 — 10 min (16:36 UTC)
- drive.py `status` → STATUS row in serial (tasks=8, ticks advancing, heap_free 255K steady).
- Screendump `os-build/captures/OC2B-soakA-10m.png` (early-failure catch). Panics: 0.

## Checkpoint 2 — 20 min (16:45 UTC, serial-only; screendumps required at 10/30/60 only)
- drive.py `status` → STATUS tasks=8 ticks=114297 heap_free_kb=255 (was 55696 at 10 min — advancing).
- Panics: 0. (A 20-min screendump was taken then deleted — not a required proof; the required set is 10/30/60m.)

## Checkpoint 3 — 30 min (16:56 UTC)
- drive.py `status` → STATUS row in serial (tasks=8, ticks advancing, heap_free 255K steady).
- Screendump `os-build/captures/OC2B-soakA-30m.png`. Panics: 0.

## Checkpoint 4 — 45 min (17:11 UTC, serial-only)
- drive.py `status` → STATUS row in serial (tasks=8, ticks advancing, heap steady). Panics: 0.

## Close — 60 min (17:26 UTC)
- Final drive.py status above. Screendump os-build/captures/OC2B-soakA-60m.png.
- Panic count (grep -c panic over full serial): 0. Final ticks 357758. Tick continuity: monotonic across all checkpoints (29k→55k→114k→182k→268k→~final).
- Soak A verdict: 60 min, 0 panics, no warnings, ticks advancing, heap steady — PASS.
