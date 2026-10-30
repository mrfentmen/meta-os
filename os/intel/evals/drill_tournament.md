# Drill tournament: INT-021 (Milo, 2026-10-27)

Runs the three watchdog drills back to back in one session,
in demo order, via `python3 intel/drills/tournament.py`.
Transcript: `intel/evals/drill_tournament.log`.
Pinning tests: `tests/test_intel_drill_tournament.py`.

| Order | Drill | Task | Result | Wall time |
| --- | --- | --- | --- | --- |
| 1 | kill_worker | WDG-020 | PASS, exit 0 | 0.04s |
| 2 | collision | WDG-021 | PASS, exit 0 | 0.04s |
| 3 | dead_dep | WDG-022 | PASS, exit 0 | 0.04s |
| - | **Total, one session** | INT-021 | **PASS** | **0.13s (limit 360s)** |

Acceptance: combined drill log under 6 minutes wall time,
met with wide headroom on fixtures.

NOT proven here: the live-demo pacing of the same sequence.
These are fixture drills (fake clocks, no network, no bus);
the 0.16s is machine time, not the human-paced demo run,
which DEM-011/DEM-012 rehearse separately. No drill posts
to the bus; critical announcement lines are held, per
Dale's posting rule.
