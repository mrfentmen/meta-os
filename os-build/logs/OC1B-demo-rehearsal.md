# OC1B-272/273 — runbook rehearsal (timed) + gaps

Date: 2026-11-02. Rehearsal = replay of OC1B_RUNBOOK.md steps 0,1,3(probe),5
plus steps 2 and 4 as executed during today's capture (same commands,
same tree, same image — the capture IS the step 2/4 rehearsal).

- R0 film play/verify: ffprobe duration=180.000000 size=719410,
  sha a29bc47d...3ae13f0. PASS (<1 min).
- R1 frame re-extracts t=10/90/160: match committed oc1b-check set. PASS.
- R2 kernel rebuild+boot+typed session: executed 11:03-11:08 (build ~2 min
  on this Mac: userspace x4 + kernel bootimage, nightly) and boots
  11:08-11:18 (K1 readkey session + K2 shell/fetch session). PASS.
- R3 live egress re-probe: --list returns DOT cameras. PASS (<30s).
- R4 chain script: ran 11:16, outcome baseline. PASS (~1 min incl. model call).
- R5 fallback paths: all 11 resolve (checked above). PASS.
Total: ~20 min end to end (capture session 11:03-11:23 EST).

## Gaps (OC1B-273)

1. GOTCHA — Homebrew ffmpeg on this Mac has no drawtext filter (no
   libfreetype). Card rendering used PIL/Monaco instead (pip install
   pillow, one-time). Fix recorded here; future rebuilds reuse
   /tmp/oc1b-cards.py (kept outside repo intentionally — build tool, not proof).
   Owner: OC1 (done).
2. GOTCHA — VGA screendumps on this tree render garbled text/ribbon while
   the serial is correct (exhibit oc1b-vga-fetch.png). Film uses serial
   cards per the plan; no runbook step depends on VGA. Owner: Rowan to
   diagnose (kernel lane); not blocking the demo.
3. SLOW — HMP sendkey typing is ~1.5s/char through the monitor helper
   (settle delays); a 6-word shell session takes ~2 min wall. Fine for
   capture day; no fix needed. Owner: none.
4. MANUAL — SPARK_API_KEY export from the Mac key file (line 1) is a manual
   pre-step for R3/R4; key handling per the 500-list rule (length-only
   logging). Owner: Del's Mac (no change).
No gap blocks Nov 4: film + all fallbacks are committed and resolve.
