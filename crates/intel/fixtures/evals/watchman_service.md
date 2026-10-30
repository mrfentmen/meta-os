# Eval: watchman service loop (Milo lane, OS-122 follow-up)

## What was built

`intel/watchman_service.py` is the repeating production loop
the OS-122 chain was waiting for. `watchman_loop.loop_cycle()`
judged one cycle, `watchman_cycle.run_cycle()` collected one
cycle from a caller-supplied runner, and `watchman_runner`
supplied the real subprocess runner, but nothing ran cycles
again and again. `serve_cycles()` is that loop: each cycle
calls `cycle_fn(machines, now, priors, journal)` and gets
back `(records, new_journal, diagnostics)`, the records of
one cycle become the priors of the next, and each cycle's
new journal entries accumulate, so episode dedupe in the
judge holds across cycles. By default `cycle_fn` is
`run_cycle_with_subprocess()` against the snapshot
directory (production default `/run/metaos`), so the
production loop runs the real Pax OS-118 program once per
machine per cycle with no judgment changed. The
`__main__` entry point is the command a unit would exec:
`python3 intel/watchman_service.py --machines alpha,beta`.

## The containment rules, and why each one is strict

- A cycle_fn that raises yields that cycle's diagnostics
  `{"cycle_error": <exception type>}` and carries the
  prior records forward, never a crash. The next cycle
  still runs, and the carried bell ages honestly through
  the judge on the next successful cycle.
- A raising on_cycle callback is contained with its
  exception type collected in `callback_errors`; the loop
  continues.
- A raising should_stop predicate is treated as False: a
  stop check that crashes must not stop the watcher.
- A raising sleep_fn is ignored: a missed sleep delays
  the next cycle, it never ends watching.
- A raising now_fn yields a `cycle_error: clock` cycle
  with priors carried, and the loop continues.
- Sleep happens between cycles only, never after the
  last cycle, and should_stop is checked before the
  sleep, so a stopped loop exits at once.

## Drill and tests

Drill: `intel/drills/watchman_service.py` (7 phases PASS:
state carries, zero cycles, should_stop, raising cycle
recovery, raising callback/stop containment, default path
rings on real snapshots with the bell carried into cycle
2, inputs unchanged). Tests:
`tests/test_intel_watchman_service.py` (13 pinning tests,
including the drill run and the no-em-dash check on the
new files).

## Not proven here

A live watchman on a booted test image, the running
service as a systemd unit (the `__main__` entry point is
the command a unit would exec, not a unit file), a
systemd restart, or the live queue reader OS-118 still
owes. The snapshots in the drill and the default-path
test are hand-written fixtures, not live queue output.
