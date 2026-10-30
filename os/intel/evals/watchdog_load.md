# INT-023 watchdog under load

200-job queue under failure, three ticks on the in-memory fake surface (see intel/watchdog_load_check.py). Timings are sandbox wall times, not production hardware and not a live Redis round trip.

## Counts

| Tick | Detector alerts | Stored records | Kinds |
| --- | --- | --- | --- |
| 1 (stalled load) | 50 | 50 | 25 presence-stall, 25 progress-stall |
| 2 (inside cooldown) | 50 | 50 | 25 presence-stall, 25 progress-stall |
| 3 (workers recovered) | 0 | 50 | none |

## What the three ticks prove

- No alert storm: 50 stalled jobs yield exactly 50 alerts on tick 1 (25 presence-stall, 25 progress-stall), one per stalled job; 150 open jobs and 2,000 room messages yield zero more.
- Dedupe holds: tick 2, inside the 30-minute cooldown, re-fires the same 50 detector alerts but the store stays at 50 records, every record keeping its tick-1 created_at with last_seen advanced to the tick-2 time.
- Silence on recovery: tick 3, after fresh progress notes from both workers, yields zero alerts. The 50 tick-1 records remain in the store until the WDG-014 lifecycle resolves them; tick silence is not store resolution.

## Timings

| Tick | Measured (s) | Budget (s) | Result |
| --- | --- | --- | --- |
| 1 | 0.002 | 5.0 | PASS |
| 2 | 0.003 | 5.0 | PASS |
| 3 | 0.002 | 5.0 | PASS |
| total (3 ticks) | 0.007 | 15.0 | PASS |

## Budgets

The plan documents no per-tick wall-clock budget, so this check adopts INT-006's: 5 seconds per tick, 15 seconds for the three together. The 5 second figure is an order of magnitude inside the watchdog loop's documented 60 second default interval, so a tick that fits it can never fall behind the loop it feeds.

## What this does not prove

- A live-reachable 2,000-message room: every jobs announcement runs bus_trim, which keeps only the newest 500 messages, so the 2,000-message state here is a beyond-cap stress state for the read path, seeded directly after the queue.
- A live Redis round trip: the fake backend has no network cost, so live timings will be higher.
- A Spark-composed brief or polished explanations: no Spark client is passed to any tick here, so every alert carries its WDG-011 template text.
- Store resolution on recovery: tick 3 proves the detectors stop firing, not that the WDG-014 lifecycle marks the 50 records resolved.
