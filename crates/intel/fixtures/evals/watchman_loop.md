# Eval: watchman service-loop caller (Milo lane, OS-122 follow-up)

## What was built

`intel/watchman_loop.py` `loop_cycle()` is the caller the
production loop will use around `watchman_tick()`. One
cycle takes `{machine: (ok, stdout)}` — one
relay_watchman --once run per machine, exit 0 meaning the
run happened and stdout holds its event lines — plus the
priors and journal the loop carries, and returns
`(records, new_journal, diagnostics)`.

## Why a caller, and why these rules

`watchman_tick()` is pure: it keeps no state between
cycles and runs nothing. A loop that just called it with
whatever each cycle produced would have two silent
failure modes, and the caller exists to close both:

1. A watchman that cannot run must not read alive. A
   failed run folds nothing fresh; the machine's last
   real record is carried forward unchanged, so its bell
   ages honestly into crew-dark past the stale window.
   A failed run for a machine with no prior record is
   unjudged, and the failure lives only in diagnostics.
2. A restart fact must not outlive its cycle. A carried
   record drops `restart_ok`, so a machine that goes dark
   again after an earlier revived cycle reads restart
   failed and escalates once, fail closed toward Dale,
   instead of re-spending an old success.

Malformed stdout lines are contained per machine
(counted in diagnostics, good events kept, other
machines untouched). Inputs are never mutated, and
carried records are copies, not the prior objects.

## Drill result

`intel/drills/watchman_loop.py`: 5 phases, all PASS
(transcript: `intel/evals/watchman_loop.log`). The ring
uses the real Pax OS-118 tick for wake events; the loop
itself starts no subprocess, so the judgment drills
without a booted image. Pinning tests:
`tests/test_intel_watchman_loop.py` (11 tests).

## What is NOT proven here

- No live watchman on a booted test image, no running
  relay-watchman.service, no systemd restart of a dead
  watchman (OS-034 contract half), no agent session
  started (OS-119), no job reassigned (OS-125 baton),
  no push sent (Hana OS-097).
- No live queue reader: OS-118's snapshot files are
  still the interface until it lands, and the outer
  loop that will supply real (ok, stdout) pairs per
  machine does not exist yet — this module is the
  judgment that loop will call, drilled on supplied
  pairs, not the loop itself.
- A failed run is a diagnostics line, and the
  escalation is a payload, never a send.
