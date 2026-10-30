# DEM-011: the staged silent failure (Milo, 2026-10-27)

Stages DEMO.md Shot 7 for rehearsal, on fixtures, via
`python3 intel/drills/demo_silent_failure.py`.
Transcript: `intel/evals/demo_silent_failure.log`.
Pinning tests: `tests/test_intel_drill_demo_silent_failure.py` (3 tests).

The staged worker is Milo's: it claims demo job 7, posts
exactly one progress note, then goes silent on cue — no
heartbeat, no message, no presence. The drill reuses the
WDG-020 kill_worker harness (same FakeWorker), so the demo
staging and the drill scenario cannot drift apart.

## Cue card (operator reads this at Shot 7)

| Item | Value |
| --- | --- |
| Shot | 7, the silent failure |
| Staged worker | milo, demo job 7 |
| Claim to cue | 120s fake-clock (claim, one progress note at 60s, cue at 120s) |
| Progress notes before the cue | exactly 1 |
| Cue line | On cue, the staged worker posts one progress note, then nothing. No error. No message. |
| Inside the stall window | tick yields zero alerts — silence is not yet a stall |
| Past the threshold (production thresholds) | exactly one presence-stall alert, milo/7, last progress 601s ago |
| Announcement | ALERT line held, not posted, per Dale's posting rule |

## Result

PASS, exit 0. Phases: healthy worker zero alerts; cue drops
presence with one progress note on record; in-window tick
zero alerts with no post-cue worker activity; past-threshold
tick exactly one presence-stall alert naming milo/7.

## NOT proven here

- DEM-012 (catch under 90s in demo configuration) and
  DEM-013 (the demo thresholds profile) are still open:
  the 601s figure above is under production thresholds
  (STALL_MINUTES = 10) on a fake clock, not a timed demo
  run, and no demo-profile timing is claimed.
- The human-paced rehearsal: fake-clock seconds are not
  rehearsal seconds. The drill proves the staging, not the
  pacing — DEM-011's acceptance is "drill runs to cue in
  rehearsal; timing on the cue card," and the cue card is
  this file plus the drill's printed CUE CARD line.
- No bus post was made; the announcement line is held.
