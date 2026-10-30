# DEM-012/DEM-013: the demo catch, measured (Milo, 2026-10-27)

DEM-013 first: the demo thresholds profile is
`intel/metaos-demo.env`, the same filename OS-038's unit
drop-in will load on the demo image, so there is exactly
one demo profile, not two. It changes only the two stall
windows (stall and progress-stall: 10 min production →
1 min demo); every other WATCHDOG_* variable is listed at
its production value so the profile is complete. Production
`intel/thresholds.py` is untouched — the profile overrides
through the environment only, which thresholds.py reads at
import time, so the demo loop must start with the profile
loaded (`set -a; . intel/metaos-demo.env; set +a`) and the
live loop must tick every 5 s (`--interval 5`), the interval
this measurement assumes.

DEM-012, measured by `python3 intel/drills/demo_catch_time.py`
(transcript: `intel/evals/demo_catch_time.log`, pinning tests:
`tests/test_intel_drill_demo_catch_time.py`, 3 tests). Each
rehearsal replays the DEM-011 staging (milo claims demo job
7, one progress note at T0+60, silent at the T0+120 cue)
and ticks every 5 s from the cue; the rehearsals differ
only in tick-grid phase, because a live loop's phase against
the cue is luck.

| Rehearsal (tick phase) | Catch after cue | Alert | Last progress shown |
| --- | --- | --- | --- |
| +0 s | 5 s | presence-stall milo/7 | 65 s ago |
| +2 s | 2 s | presence-stall milo/7 | 62 s ago |
| +4 s | 4 s | presence-stall milo/7 | 64 s ago |

Result: PASS, 3/3 rehearsals under the 90 s budget, with
85+ s of headroom in the worst phase. Why the catch is
seconds, not a minute: the progress note is already 60 s
old at the cue, so the 1-minute demo stall window is
already spent when silence starts — the first post-cue
tick past the threshold is the catch.

## What is NOT proven here

- The human-paced rehearsal: these are fake-clock ticks,
  not a live loop on stage. The live loop must actually run
  at `--interval 5` with the profile loaded; a 60 s loop
  interval would still pass the 90 s budget (worst catch
  ~61 s) but the measured 2–5 s figures assume the 5 s
  interval, and the script refuses to run if the profile's
  stated interval disagrees with its own.
- The displayed age is 62–65 s, not the "90 s" DEMO.md Shot
  8 and the WDG-030 narration line ("ninety seconds after
  the last progress note") suggest. Thresholds are whole
  minutes (INT-022 lock), so a 90-second stall window is not
  expressible without changing the locked production module,
  which DEM-013 forbids. Read DEMO.md's 90 s as the catch
  budget DEM-012 proves (catch 2–5 s, budget 90 s), and cue
  the shot-8 visual to the narration's catch line at
  rehearsal as TIMING.md already directs — the narration
  line and the live displayed age differ by ~25 s and the
  rehearsal must place them, not this measurement.
- No bus post was made; the ALERT line is held.
