# OC2B-111–118 — Soak B (120 min verdict run, text tree)
- Start (UTC): 2026-11-02T17:27Z. Tree: opencode2/500 (kernel/ untouched = combined current main tree bit-for-bit; same bootimage build as soak A, rebuilt from /tmp/oc2b-soak at branch tip).
- QEMU: 11.1.3, -m 512M -display none -no-reboot, serial os-build/logs/OC2B-soakB-serial.txt, monitor /tmp/oc2b-soakB-mon.sock.

## Checkpoint 1 — 30 min (17:56 UTC)
- drive.py `status` + `ps`: STATUS row present (tasks=8); ps shows one-shot userspace tasks Exited (hello/sleeper/crasher/readkey run-once by design), shell/idle Running.
- Panics+warnings (grep -c): 0 rows above. No new serial warnings.

## Checkpoint 2 — 60 min (18:26 UTC)
- drive.py `status` + `ps`: STATUS tasks=8 ticks=355915 heap_free_kb=255 (was 179789 at 30 min — advancing).
- Screendump `os-build/captures/OC2B-soakB-60m.png`. Panics+warnings: 0.

## Checkpoint 3 — 90 min (18:56 UTC)
- drive.py `status` + `ps`: STATUS row present (see serial tail above). Panics+warnings: 0 (count above).

## Close — 120 min (19:27 UTC)
- Final STATUS tasks=8 ticks=718062 heap_free_kb=255 (monotonic 179k→355k→536k→718k across checkpoints).
- Idle mem at end: `mem frames_free 126430 frames_total 126509 heap_free 255K heap_total 512K` (see serial tail above). Boot-time mem: heap_free 255K from the first STATUS row (unchanged — no leak); frames allocator steady (79 frames touched all run).
- Screendump `os-build/captures/OC2B-soakB-120m.png`.
- Panic count (grep -c panic over full serial): 0. Warnings: 0.

## 2-hour soak verdict (OC2B-118)
- 120 min, 0 panics, 0 warnings, tick continuity monotonic, heap flat, shell answering at every checkpoint — PASS. Text tree is soak-stable.
