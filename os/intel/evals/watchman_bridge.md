# Eval: watchman bridge (OS-122 follow-up to Pax OS-118)

Date: 2026-10-28. Pax OS-118 (9ce3e22) landed the real watchman
but publishes no per-machine watchman record, so Milo's OS-122
detector had nothing real to judge. This follow-up bridges the
two from Milo's side only; no Pax file was edited.

## What was built

- `intel/watchman_bridge.py`: `fold_tick(events, now, prior)` maps
  one relay_watchman tick to a watchman_watch record. One rule:
  a tick that ran proves aliveness at that time; a bell is a wake
  event and nothing else. The rung state file is deliberately
  never read as liveness proof (OS-118 writes it only when new
  rung keys appear).
- `intel/drills/watchman_bridge.py`: 4/4 phases PASS. Real tick
  rings once for a sleeping agent; bridged record reads ALIVE
  with no journal noise; aged past WATCHMAN_STALE_MINUTES with
  restart_ok True yields crew-dark + restart-succeeded and no
  escalation; a fresh fold after the episode yields
  watchman-recovered; a tick with no wake event reads UNKNOWN,
  never ALIVE.
- `tests/test_intel_watchman_bridge.py`: 6 pinning tests.

## Honesty notes

- A drill-fixture bug was caught by the drill itself: the first
  fixture addressed the job with `addressee`, but the real
  watchman reads `addressed_to`/`to` (mirroring intel/wake.py).
  Fixed in the fixture; the tick then rang as expected. This is
  exactly the kind of contract mismatch the bridge exists to
  catch early.
- NOT proven here: a live watchman on a booted test image,
  relay-watchman.service actually running, a systemd restart of
  a dead watchman, or the live queue reader OS-118 still owes.
  The bridge proves the record shape and detector path only.

## Follow-up still owed (not Milo's to claim)

- OS-118's live queue reader (snapshot files remain the
  interface); a caller that folds each real watchman cycle
  through this bridge and feeds watchman_watch_tick, so a
  silent service earns crew-dark for real.
