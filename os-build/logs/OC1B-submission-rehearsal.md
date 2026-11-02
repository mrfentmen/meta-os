# OC1B-465 — full rehearsal from a clean clone (coordinator run, 2026-11-02)

Method: `git clone file:///tmp/oc500 -b opencode/500 /tmp/oc500-rehearse`
(local-path clean clone of the pushed tip — no build state, nothing
pre-built; target/ rebuilt from scratch in the clone). Tree TIP 37e85db3.
Start ~12:44 EST, end 12:48 EST. Total ~5 min for verify+live steps; kernel
rebuild finished ahead of the boot inside the same window (shared cargo
cache — recorded, not hidden).

## Step 0/1 — film numbers (OC1B-rehearsal-step1.log)
- ffprobe: duration=180.000000, size=719410.
- sha256: a29bc47dd56e9f583d8af231d8d3908f3a4c4d6218fb1b3492ce5381b3ae13f0.
- Frame extracts t=10/90/160: all byte-IDENTICAL (md5) to
  os-build/demo/oc1b-check/t{10,90,160}.png.

## Step 2 — kernel proofs, rebuilt in the clone (OC1B-rehearsal-serial.txt)
- Userspace hello/sleeper/crasher/readkey rebuilt at their link bases;
  `cargo bootimage` produced 11202048 B (same size as §1 baseline).
- QEMU boot, monitor-typed session (sendkey script — same keystrokes the
  runbook types by hand: a/b/ret early, status x2, mem, ps, fetch late).
  DEVIATION (no behavior change): `-display none` instead of `vnc=:21`;
  serial carried the proofs so no screendump was needed.
- Assertions, all present: alive (K1), HELLO FROM USERSPACE, task killed
  (fault isolated), `user bad syscall 99 refused`, readkey got=5
  (press+release, as §11 narrates), STATUS x2 ticks 6239→6545 (moving),
  mem summary K4 up, mem frames, ps rows. panic count 0, loader-refused 0.

## Step 3 — live beat-7 (OC1B-rehearsal-live-frame.jpg/.json)
- Real pull at 17:47:57Z: 3 Ave @ 60 St Brooklyn, 14485 B, sha ebb7d561…,
  spark reading "normal activity", current timestamp. Live, not fallback.

## Step 4 — chain proof (OC1B-rehearsal-chain.json)
- Outcome baseline on the normal-activity frame, events=2.
- DEVIATION: script needed PYTHONPATH=server/queue for the crew import
  (runbook notes the script lives outside the repo; one env var, recorded).

## OC1B-466 gaps block
- Failures: NONE. Every manual step hit; no fallback invoked (live steps
  both succeeded on the first attempt).
- Slow steps: none blocking. Slowest leg was the kernel rebuild inside the
  shared cache window; typing cadence (0.25s/key) is the floor, not a find.
- Owner of remaining risk: none from this rehearsal — film, proofs, and
  live path all replayed from scratch on the merged tip.
