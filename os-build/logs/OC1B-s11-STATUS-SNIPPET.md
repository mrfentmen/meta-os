# OC1B-s11 STATUS SNIPPET (opencode/500-s11) — coordinator merges to OPENCODE1_500_STATUS.md

Branch: opencode/500-s11. Base: opencode/500 @ 94010c76. Fences kept:
no main push, no kernel/src edits, kernel-only film, loopback dispatch only,
measured (never estimated) numbers, every proof committed. Key used only as
SPARK_API_KEY env (length 48, never printed/logged/committed); no outage.

## §11 Demo capture — kernel only (OC1B-251..OC1B-275): DONE (commit 3f8e73cb)

Image under capture: bootimage-metaos-kernel.bin built on this tree,
sha256 58ed24c12202eef3e2d24cd3158567f66c626b50034a0f93828d8a6ac48ff.
Film: os-build/demo/demo-3min.mp4, 180.000000s measured, 719410 bytes,
sha256 a29bc47dd56e9f583d8af231d8d3908f3a4c4d6218fb1b3492ce5381b3ae13f0.

- OC1B-251 PROVEN: os-build/logs/OC1B-demo-shotlist.md (8-beat plan list).
- OC1B-252 PROVEN: backing column completed; conditionals (K3/K4/KF) have
  no gate logs at capture time so no shots (plan's rule, not cuts).
- OC1B-253 PROVEN: os-build/demo/oc1b-beat1-serial.txt + captures/oc1b-beat1.png.
- OC1B-254 PROVEN: loader lines quoted (3 addresses) + oc1b-beat2.png.
- OC1B-255 PROVEN: hello/sleeper/crasher quoted + oc1b-beat3.png.
- OC1B-256 PROVEN: fault L45 + survivor L48 + oc1b-beat4.png.
- OC1B-257 PROVEN: os-build/logs/OC1B-demo-beat5-serial.txt (STATUS
  ticks 2073->3719, mem, ps 8 rows id7 Running) + oc1b-beat5.png.
- OC1B-258 PROVEN: `user bad syscall 99 refused` (K1 L75, K2 L86).
- OC1B-259 PROVEN: os-build/logs/OC1B-demo-beat6-live.txt (live 11:14 EST,
  3 Ave @ 60 St, normal activity, muse-spark-1.3).
- OC1B-260 PROVEN: os-build/logs/oc1b-chain/live-baseline-chain.json
  (real all-flags chain, outcome baseline; no review/judge/response
  because nothing flagged — plan's honest shape).
- OC1B-261 PROVEN-AS-ZERO: no receipt exists (nothing dispatched); the
  close-up card states the honest shape with simulated=true legible.
  The retired staged receipt is nowhere shown.
- OC1B-262 PROVEN: SIMULATED on s08/s10/s11 footers + face (whole 138-164s).
- OC1B-263 PROVEN: os-build/demo/oc1b-cut.txt (12 segs, 180s).
- OC1B-264 PROVEN: film replaced; build command in OC1B-demo-capture.md.
- OC1B-265 PROVEN: ffprobe duration=180.000000, 1800 frames, 10fps.
- OC1B-266 PROVEN: oc1b-check/t{10,90,160}.png match claimed logs.
- OC1B-267 PROVEN: 12/12 segment midpoints match; 0 face/web/browser frames.
- OC1B-268 PROVEN: honesty pass; VGA ribbon garble disclosed with exhibit
  (captures/oc1b-vga-fetch.png); staged elements excluded; SIMULATED kept.
- OC1B-269 PROVEN: os-build/demo/CAPTURE_NOTES.md rewritten.
- OC1B-270 PROVEN: fallback table in OC1B-demo-capture.md (all resolve).
- OC1B-271 PROVEN: os-build/demo/OC1B_RUNBOOK.md.
- OC1B-272 PROVEN: os-build/logs/OC1B-demo-rehearsal.md (~20 min).
- OC1B-273 PROVEN: gaps block (ffmpeg no-drawtext, VGA anomaly, sendkey
  slowness, manual key step) with fixes/owners.
- OC1B-274 PROVEN: film record (sha+size+closing line) in capture log.
- OC1B-275 PROVEN: §11 commit 3f8e73cb on opencode/500-s11 (sha recorded
  here per coordinator instruction, not in OPENCODE1_500_STATUS.md).

## §12 Carrier image (OC1B-276..OC1B-300): IN PROGRESS

(settled below when the rebuild + checks land; §12 commit to follow)

- OC1B-276/277/280: recipe survey + before-state + inventory in
  os-build/logs/OC1B-carrier-recipe.md (committed at §12 checkpoint).
- OC1B-278: recipe diff (build-image.sh provision phase + pinned
  opencode 2.2.0; new provision-toolchain.sh) — in §12 commit.
- (remaining rows filled after the rebuild completes)
