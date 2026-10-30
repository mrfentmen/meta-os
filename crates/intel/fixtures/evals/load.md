# INT-006 load check

2,000-message room + 200-job queue, timed on the in-memory fake surface (see intel/load_check.py). Timings are sandbox wall times, not production hardware and not a live Redis round trip.

## Timings

| Operation | Measured (s) | Budget (s) | Result |
| --- | --- | --- | --- |
| snapshot | 0.004 | 5.0 | PASS |
| brief | 0.009 | 5.0 | PASS |
| tick | 0.001 | 5.0 | PASS |
| total (3 ops) | 0.014 | 15.0 | PASS |

## Counts

- Room messages in snapshot: 2000
- Jobs in snapshot: 200 (10 claimed with fresh progress, 190 open)
- Morning brief words: 218 (FND-034 morning budget 220)
- Watchdog tick alerts: 0 (healthy load room, zero expected)

## Budgets

The plan documents no per-operation wall-clock budget for snapshot, brief, or tick, so this check adopts one and records it here: 5 seconds per operation, 15 seconds for the three together. The 5 second figure is an order of magnitude inside the watchdog loop's documented 60 second default interval, so a tick that fits it can never fall behind the loop it feeds. The brief word budget is the plan's own: FND-034 caps a morning brief at 220 words.

## What this does not prove

- A live-reachable 2,000-message room: every jobs announcement runs bus_trim, which keeps only the newest 500 messages, so the 2,000-message state here is a beyond-cap stress state for the read path, seeded directly after the queue.
- A live Redis round trip: the fake backend has no network cost, so live timings will be higher.
- A Spark-composed brief: the brief here is a template brief, because GOV-001 leaves live Spark transport blocked.
- Alert behavior under load: the tick yields zero alerts here by design (every claimed job is healthy). Alert counts under a loaded, failing room are Milo's INT-023, not this check.
