# Watchdog tuning table (WDG-027)

Run: 2026-10-27, by `python3 intel/evals/watchdog_tuning.py` from
the repo root. The harness is independent of the unit tests: it
rebuilds one positive and one or more negative snapshots per
detector from the snapshot shapes intel/brief.py documents, runs
`intel.watchdog.tick()` on each at now=10000, and reports false
positives (a kind fired that was not expected) and false
negatives (an expected kind that did not fire) per fixture.

Fixture source, stated plainly: there are no separate Buffy
synthetic-history files in this repo — no tests/fixtures/intel/
directory, no synthetic-history files under tests/ or intel/ —
so the suite's hand-written snapshot fixtures are the synthetic
histories this run covers, one case per fixture class below.
Thresholds in force at run time (intel/thresholds.py defaults):
stall 10 min, progress-stall 10 min, lease-risk window 5 min /
quiet 2 min, silent-room 60 min, dedupe cooldown 30 min.

Result: 26 cases, 0 false positives, 0 false negatives.
The WDG-027 pass requirement holds: the quiet fixture yields
zero alerts, and the healthy-busy fixture yields zero alerts.

One harness note, kept because it is evidence the detectors
work rather than a blemish: the first run flagged the
healthy-busy fixture itself — it was built with a claim 9,100s
old, and the progress-stall detector correctly fired on it.
The fixture was corrected to a fresh claim (100s old, matching
the suite's healthy-busy intent) and the rerun is the table
below. No detector code changed during this task; no threshold
changed either — the defaults above already give zero false
positives on every negative fixture, so there is nothing to
tune yet. INT-022 re-runs this table after integration
fixtures grow and locks thresholds then.

| Fixture | Detector | Expected | Got | FP | FN |
|---|---|---|---|---|---|
| quiet-empty | tick | — | — | 0 | 0 |
| healthy-busy | tick | — | — | 0 | 0 |
| presence-stall-positive | WDG-002 | presence-stall | presence-stall | 0 | 0 |
| presence-stall-negative-present | WDG-002 | progress-stall (WDG-003's case, not WDG-002's) | progress-stall | 0 | 0 |
| presence-stall-negative-fresh | WDG-002 | — | — | 0 | 0 |
| presence-stall-negative-walkon | WDG-002/WDG-025 | — | — | 0 | 0 |
| progress-stall-positive | WDG-003 | progress-stall | progress-stall | 0 | 0 |
| progress-stall-negative-fresh | WDG-003 | — | — | 0 | 0 |
| progress-stall-negative-absent | WDG-003 | presence-stall (WDG-002's case) | presence-stall | 0 | 0 |
| lease-risk-positive | WDG-004 | lease-risk | lease-risk | 0 | 0 |
| lease-risk-negative-live-heartbeat | WDG-004 | — | — | 0 | 0 |
| lease-risk-negative-far-expiry | WDG-004 | — | — | 0 | 0 |
| dead-dep-positive | WDG-005 | dead-dep | dead-dep | 0 | 0 |
| dead-dep-negative-live-dep | WDG-005 | — | — | 0 | 0 |
| missing-dep-positive | WDG-006 | missing-dep | missing-dep | 0 | 0 |
| missing-dep-negative-existing-dep | WDG-006 | — | — | 0 | 0 |
| file-collision-positive | WDG-007 | file-collision | file-collision | 0 | 0 |
| file-collision-negative-disjoint | WDG-007 | — | — | 0 | 0 |
| file-collision-negative-done-no-branch | WDG-007 | — | — | 0 | 0 |
| attempt-warning-positive | WDG-008 | attempt-warning | attempt-warning | 0 | 0 |
| attempt-exhaustion-positive | WDG-008 | attempt-exhaustion | attempt-exhaustion | 0 | 0 |
| attempt-negative-early | WDG-008 | — | — | 0 | 0 |
| attempt-negative-done | WDG-008 | — | — | 0 | 0 |
| silent-room-positive | WDG-009 | silent-room (info only) | silent-room | 0 | 0 |
| silent-room-negative-fresh-message | WDG-009 | — | — | 0 | 0 |
| silent-room-negative-no-claims | WDG-009 | — | — | 0 | 0 |

Per-detector verdicts:

- WDG-002 presence-stall: 1 positive caught, 3 negatives clean,
  and the present-but-idle case lands on WDG-003, never WDG-002.
- WDG-003 progress-stall: 1 positive caught, fresh-progress and
  walk-on negatives clean, absent-worker case lands on WDG-002.
- WDG-004 lease-risk: 1 positive caught, live-heartbeat and
  far-expiry negatives clean.
- WDG-005 dead-dep / WDG-006 missing-dep: each positive caught,
  each negative clean, and neither cross-fires into the other.
- WDG-007 file-collision: 1 positive caught, disjoint-files
  and done-without-branch negatives clean.
- WDG-008 attempt-exhaustion: warning at max-1 and critical at
  max both caught, early-attempt and done-job negatives clean.
- WDG-009 silent-room: 1 positive info record caught, fresh
  message and no-claims negatives clean; no critical or warning
  severity appears on any silent-room fixture.
- WDG-025 walk-on edge: the walk-on negative fixture yields
  zero stall alerts and a tracking record only, per WDG-025.

Threshold decision: NO CHANGE. Every negative fixture is
already clean at the defaults, so tuning the numbers now would
be guessing without a failing case. The numbers stay
provisional until INT-022, which re-runs this table against
the grown integration fixtures and locks them with a comment
citing this doc.

## INT-022 rerun and lock (2026-10-27)

Rerun after the integration fixtures grew: `python3
intel/evals/watchdog_tuning.py` from the repo root, same harness,
same thresholds in force. Result: 26 cases, 0 mismatches:
0 false positives, 0 false negatives, quiet fixture zero alerts,
healthy-busy fixture zero alerts. Grown integration fixtures
checked in the same run, all clean:

- INT-021 drill tournament (`python3 intel/drills/tournament.py`):
  kill_worker, collision, dead_dep back to back, 3/3 PASS,
  total 0.14s vs the 360s limit; each drill's alert fires
  exactly where its acceptance case expects it and nowhere else.
- INT-020 e2e surfaces (`python3 intel/e2e_watchdog_surfaces.py`):
  PASS: presence-stall fixture tick yields exactly one alert,
  id presence-stall:pax:7 severity critical, identical on store,
  brief, and dashboard row; quiet tick yields zero alerts.

No new detector case appeared in the grown fixtures that any
threshold misses, and no negative fixture trips at the current
values, so INT-022 locks the values UNCHANGED:

| Threshold | Locked value |
|---|---|
| STALL_MINUTES | 10 |
| PROGRESS_STALL_MINUTES | 10 |
| LEASE_RISK_WINDOW_MINUTES / QUIET_MINUTES | 5 / 2 |
| ALERT_DEDUPE_COOLDOWN_MINUTES | 30 |
| SILENT_ROOM_MINUTES | 60 |
| WATCHDOG_BEAT_TTL_SECONDS | 300 |
| TICK_PAGE_SIZE / TICK_MAX_MESSAGES | 1000 / 1000 |

Lock recorded in intel/thresholds.py (module header + per-value
comments citing this doc) and pinned by
tests/test_intel_watchdog.py LockedThresholdsTest. The demo
thresholds profile (DEM-013/OS-038) stays environment-only:
production thresholds.py is untouched by it. A future change
needs a failing fixture and a new table run, per the lock rule
in thresholds.py.
