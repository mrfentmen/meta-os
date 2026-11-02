# `crates/os-supervisor` — failure drill (B021)

What breaks first when inputs stop arriving, written from the code so
another agent can run it. The crate ships its own drills; this file is
the runnable procedure and the expected lines.

## Drill A — `kill_worker` (the primary failure drill)

Source: `src/drills/kill_worker.rs` (`run_drill` 442-552,
`run_drill_stdout` 564-…). Constants: job `7`, nick `pax`,
`T0 = 100_000`, stall 10 min, progress stall 10 min, lease 1800 s
(`kill_worker.rs:70-100`).

Fixture: job 7 "demo job", claimed by pax at `T0`; lease until
`T0 + 1800`; last heartbeat `T0 + 300`; last progress `T0 + 120`
(`kill_worker.rs:600-612`).

Run:

```
cargo test -p os-supervisor kill_worker
```

Expected, phase by phase (`kill_worker.rs:614-690`):

| Phase | Action | Expected |
|---|---|---|
| 1 | healthy worker at `T0 + 300` | **zero** alerts |
| 2 | kill the worker (presence removed, `alive = false`), tick at `T0 + 300 + 600 + 61 = 100961` | exactly **one** `presence-stall`; nick `pax`, job `7`, last-progress age `100961 - 100120 = 841` s; one `ALERT:` line |
| 3 | at the same time, sweep expired leases | **nothing** requeued: the lease is not expired, job stays `claimed`, claim stays `pax` |
| 4 | at `T0 + 1801`, sweep | job `7` requeued: status `open`, claim and lease cleared; a tick then yields **zero** alerts, so the alert stops firing |

`run_drill` returns a report with `alert.kind == "presence-stall"`,
`requeued == ["7"]`, and a four-line log; `run_drill_stdout` returns
exit 0 and the final line `kill_worker drill: PASS`
(`kill_worker.rs:614-640`).

## What breaks first, in order

1. **Presence stops** → presence-stall fires at `stall_minutes` (10 min)
   after the last progress, not after the last heartbeat
   (`detect_presence_stall`, `watchdog.rs:840-892`).
2. **Lease keeps running** → the job is still claimed, so nothing is
   requeued yet. This is the designed gap: an alert, not a takeover.
3. **Lease expires** (1800 s) → the sweep requeues the job; the
   presence-stall stops because the job is no longer claimed
   (`sweep_expired_leases`, `drills/kill_worker.rs:390-415`).
4. **No sweep runs** → the job stays claimed forever; the watchdog can
   only keep alerting. The crate never restarts a unit itself
   (`watchdog.rs:56-63`, OS-034).

## Drill B — watchman chain

Each drill is a set of phases returning pass/fail; run them by module
name.

| Drill | Run | Phases |
|---|---|---|
| `watchman_boot` | `cargo test -p os-supervisor watchman_boot` | arrivals ring, non-ringing jobs stay silent, malformed record not judged, no double ring, corrupted counter ignored, sweep reconciliation (`drills/watchman_boot.rs:154-265`) |
| `watchman_bridge` | `cargo test -p os-supervisor watchman_bridge` | real tick wake, bridge alive, aged dark then recover, unknown machine gets no bell (`drills/watchman_bridge.rs:84-133`) |
| `watchman_bridge_tick` | `… watchman_bridge_tick` | ring and quiet, silence and recovery, second episode realerts, malformed contained, absent machine unjudged (`drills/watchman_bridge_tick.rs:95-254`) |
| `watchman_cycle` | `… watchman_cycle` | well-behaved runner, raising runner, garbage runner, non-callable runner, empty machine list, truthy-is-not-true (`drills/watchman_cycle.rs:122-272`) |
| `watchman_loop` | `… watchman_loop` | parse and cycle phases (`drills/watchman_loop.rs:349-…`) |
| `watchman_runner` | `… watchman_runner` | real once rings, full cycle, hanging timeout, non-zero discarded, bad inputs contained, failed run ages (`drills/watchman_runner.rs:181-306`) |
| `watchman_service` | `… watchman_service` | state carries, zero cycles, stop, raising cycle contained, raising callback and stop, default path rings, inputs never mutated (`drills/watchman_service.rs:131-355`) |
| `watchman_service_cli` | `… watchman_service_cli` | plain command, empty machines, unit ExecStart, bad flag, bare machines (`drills/watchman_service_cli.rs:224-336`) |
| `watchman_watch` | `… watchman_watch` | kill and revive, kill beyond repair, revive then die again, alive and unknown, stale bell, no Dale (`drills/watchman_watch.rs:130-352`) |

A failing phase returns `false`; `run_drill` aggregates them into the
exit code and one `phase N` line per phase.
