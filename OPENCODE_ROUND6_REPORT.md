# OPENCODE ROUND 6 REPORT — queues behind Round 5, night 1

Branch: `opencode/round6`. Base tip: `173e265`.
Standing rules hold: scope, verbatim errors, key handling (no keys
needed; none used).

## R6-1 clean-room reproduction — DONE
- Fresh clone of main @ `1df6311` to /tmp/round6-clean, target/
  dirs wiped first, then `sh os-build/gate.sh` start to finish:
  72 s wall (pinned nightly 1.101.0, per-program userspace at
  3 bases, kernel bootimage 8389632 bytes, headless QEMU boot,
  drive.py typed help+status, 7/7 asserts).
- Full terminal record: os-build/logs/gate-run-main1df6311.txt
  (start 2026-11-02T06:56:03Z, end 2026-11-02T06:57:15Z);
  boot log os-build/logs/GATE-boot-main1df6311.txt (1979 bytes:
  alive, K6 banner, K4 summary, C awake, HELLO, sleeper sleep,
  2 clean exits, 1 task-killed fault isolation, STATUS line;
  0 loader-refused, 0 panic).
- Honesty note: one earlier attempt in the same clone was killed
  at 60 s by my foreground timeout; the recorded run resumed its
  in-progress build, so per-crate compile lines are fewer — all
  binaries were still built on this Mac from this clone's
  sources (fresh image timestamp verified), and the boot
  assertions re-ran live.
- Reproducibility: no human trick outside the repo — the PATH
  pin and per-program bases live in gate.sh itself.
## R6-2 demo capture — DONE (DEMO_SCRIPT landed; capture 2026-11-02 on merge 28e99285, GATE GREEN)
- Script: `os-build/DEMO_SCRIPT.md` (H-FP1, 3:00, 6 beats) present on origin/main; merged into this branch as 28e99285; gate GREEN 7/7 on the merged tree (log /tmp/demo-gate.log) before capture.
- Session: `os-build/demo-capture.sh` (committed) — one QEMU+VNC boot, HMP `screendump` per beat + full serial log. Artifacts in `os-build/logs/demo-beats/`: serial-all.txt (67 lines) + beat1-boot/beat2-ring3/beat3-programs/beat4-fault/beat4b-after-fault/beat5-status/beat5-mem/beat5-ps.ppm + beat6-drill.log/beat6-receipt.txt/beat6-package-sent.json/beat6-incident.json (copies of the R5-imperium record; receipt `sim-6623d237a90b3d9d` re-verified).
- Honest notes (verified viewing every dump): beats 1-4 print faster than HMP dump latency, so all four boot dumps show the loader/sleeper/crasher window (banners in serial lines 1-2, cut to log per the script's own fallback rule); the `task killed` fault line is serial-only (line 44), the screens show pre/post shell lines; beat 5 pixel-perfect on screen (status ticks 12574 heap 287K, mem 127147/127196, ps 7 rows id-7 Running); beat 6 is the committed record, not a re-run.
- Ticks note: beat-5 screen shows ticks=12574 (script's example numbers 11739/441232 are illustrative of movement, not assertions).
## R6-3 second live loop — DONE (Ignis)
- Same end-to-end shape as R5-4, different division: Ignis RED
  (`visible flame` x3 on cam-b; note: `visible smoke` is yellow
  tier and correctly never dispatches — verified by the drill's
  first attempt, which held at `flagged-yellow-review`).
  Patrol flagged, review confirmed, investigation ran, direct
  dispatch sent the package WITH picture to the SIMULATED
  endpoint. Captured in os-build/logs/R6-imperium-ignis/:
  incident.json (`dispatched-simulated`), package-sent.json
  (`simulated` true, `auto`, picture with flag-frame + face-crop,
  SIMULATED destination, audit flag true), receipt
  `sim-9da0ad66d87add2e`. Two divisions now proven live.
## R6-4 freeze support — OPEN (H+9 freeze 2026-11-02 05:12 EST = 10:12 UTC; 24-hour mark 2026-11-02 20:12 EST = 2026-11-03 01:12 UTC. Both in the future: gate the frozen tip + one line each when they land.)
## R6-5 submission package checks — DONE
- No tracked build artifacts: `git ls-files | grep -E "target/|\.bin$|\.elf$|\.ppm$|\.img$"` → empty.
- Secret sweep (git grep for sk-/ghp_/AKIA/private-key patterns): 5
  hits, all benign on inspection — `ghp_xxxx...` redacted
  placeholders in adversarial eval fixtures, a scanner's own
  marker list in `dispatch.rs`, a detector regex in
  `security_pass.rs`. Zero real secrets. No API keys used anywhere.
- Every report/log path cited in R5+R6 reports exists on disk
  (one regex artifact `gate-run-r5-1.txt.` with trailing period
  aside — the file itself is present).
- README links: os-build/README.md carries no markdown links;
  all 7 inline file refs (boot-test.sh, expected/, install-tools.sh,
  research/goose.md, research/lobster.md, mcp/WIRING.md,
  OS_BUILD_REPORT.md) resolve.
## R6-6 merge-watch — DONE (2 tips gated; watch stays open)
- `4702e5c`: GATE GREEN 7/7 (clean-clone run; logs
  GATE-boot-main4702e5c.txt, gate-run-main4702e5c.txt).
- `1df6311` (Buffy finish-tonight slice 2): GATE GREEN 7/7 via
  the R6-1 pristine run above (same logs double as the line).
- No RED this window. Standing rule for the rest of the window:
  each new main tip gets one gate run + one line here.
## Blockers for Pax
1. R6-2 CLEARED: `os-build/DEMO_SCRIPT.md` landed on main and the capture above is committed.
2. R5-2/R6 carry-over: typed bytes via syscall 5 not yet captured;
   intermittent 8-task exit panic + kernel NX-fault storm
   (evidence in R5-*.txt). readkey spawn stays held; one-line
   re-enable + gate re-run once the kernel lane clears it.
   K-all.txt `milestone K3` line is stale vs the truthful
   banner (Milo's file).
3. Queue suite cannot import on this Mac as committed
   (`dynamic_credentials` sandbox-only import in trio_store.py);
   drills used a /tmp-only stub under TRIO_STORE=local.
## What remains unverified
- Same list as R5 plus: R6-4 freeze
  lines (on the clock). Everything else on this sheet is DONE
  with named logs except R5-2 typed bytes (PARTIAL).
