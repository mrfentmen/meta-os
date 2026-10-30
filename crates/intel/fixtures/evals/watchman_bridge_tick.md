# Eval: watchman_tick service-loop entry point (OS-122 follow-up)

Milo lane, follow-up to the OS-122 bridge (ab4c675) and Pax OS-118.

## What changed

`intel/watchman_bridge.py` gains `watchman_tick(events_by_machine,
now, priors=None, journal=None, restart_ok=None)`: one call that
folds every machine's relay_watchman events into watchman_watch
records and judges them, returning (records, new_journal). Before
this, a service loop had to hand-assemble fold_tick, a snapshot,
and watchman_watch_tick per machine; now the loop passes the
whole mapping and gets the whole verdict. `fold_tick` and
`machines_snapshot` are untouched.

Rules pinned, all in the module docstring:

- A machine missing from the mapping is not judged at all.
  Silence in the input is not a dead watchman; a machine that
  stops reporting must be folded explicitly with an empty event
  list and its prior record, so its bell ages honestly into
  crew-dark instead of vanishing from the board.
- `restart_ok` is always a caller-supplied fact, exactly as
  OS-122 tests supply it, never something this module observes.
  A dark machine with no restart fact supplied carries no
  restart_ok key, so the judge reads the restart as failed and
  escalates once: fail closed toward Dale, stated plainly,
  rather than assuming a restart the caller never ran.
- Malformed input for one machine never breaks another, and
  inputs are never mutated.

## Drill

`intel/drills/watchman_bridge_tick.py` (5/5 PASS):

1. Two machines, one rings (real Pax tick), one quiet: ALIVE
   with bell at tick time vs UNKNOWN, journal empty.
2. Silence past the stale window (restart_ok True) journals
   exactly crew-dark + restart-succeeded for the dark machine
   only; a fresh ring journals exactly one recovered record.
3. Second dark episode after recovery (restart_ok False)
   journals a fresh crew-dark + restart-failed + exactly one
   escalation; an identical second tick journals nothing new.
4. Non-dict mapping yields no records and no journal; junk
   events for one machine leave the healthy machine untouched.
5. A machine missing from the mapping is unjudged.

## Tests

`tests/test_intel_watchman_bridge_tick.py`: 7 tests
(WatchmanTickTest), including the no-restart-fact escalation
case and the immutability case. Full suite run below.

## NOT proven here

A live watchman on a booted test image, the running service, a
systemd restart, or the live queue reader OS-118 still owes.
The loop that will call watchman_tick() in production does not
exist yet in this repo; this is the entry point it will call,
proven on fixtures only.
