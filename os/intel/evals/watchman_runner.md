# Eval: watchman subprocess runner (Milo lane, OS-122 follow-up)

## What was built

`intel/watchman_runner.py` is the production loop's runner
for the OS-122 service loop. `watchman_loop.loop_cycle()`
judged runs that were already collected, and
`watchman_cycle.run_cycle()` collected them from a
caller-supplied runner, but every runner it had ever
seen was a fixture callable. Nothing actually ran the
watchman. This module runs the real Pax OS-118 program,
`os/watchman/relay_watchman.py --once`, once per machine,
and turns each subprocess result into the `(ok, stdout)`
pair the loop expects, with no judgment changed:
`run_cycle_with_subprocess()` builds the runner and
passes it straight to `run_cycle()`.

## How one machine is run

By default a machine's snapshots live under a snapshot
directory (production default `/run/metaos`, the
directory the relay-watchman.service unit reads from)
as `watchman-jobs-<machine>.json`,
`watchman-agents-<machine>.json`, and
`watchman-state-<machine>.json`. The state file is per
machine so the watchman's own rung dedupe (a job rings
once) holds across cycles. A caller that keeps snapshots
somewhere else supplies its own `command_for(machine)`
callable returning an argv list; the default is only a
convenience, not a second interface.

## The success rules, and why each one is strict

- Only exit 0 counts as success. A nonzero exit means
  the run failed and its stdout is discarded, even when
  the program printed partial lines before failing. The
  loop's rule is that a failed run's stdout is unusable,
  and the runner enforces it instead of passing partial
  output along and hoping the loop ignores it.
- A timeout (default 30 seconds) kills the process and
  counts as a failed run. A watchman that hangs must not
  hang the loop with it.
- A missing program, a bad argv, a bad machine name, or
  a raising `command_for` counts as a failed run, never
  a raise. The runner itself never raises, so a bad
  collection can never crash the loop that watches for
  silent failures.
- A missing snapshot file is a quiet success, not a
  failure: relay_watchman --once reads a missing file
  as an empty snapshot with a stderr note, per OS-118,
  so the loop folds it as a quiet run (UNKNOWN, no bell
  invented). A malformed snapshot file is the failure
  case: --once exits 2 and the runner reports a failed
  run.

## Drill result

`intel/drills/watchman_runner.py`: 6 phases, all PASS
(transcript: `intel/evals/watchman_runner.log`). The
real --once run rings exactly once for an open job
addressed to a sleeping local agent and stays silent on
a second run over the same state file; the full cycle
through real runs gives the ringer a bell and the quiet
machine none, with an empty journal and no run
failures; a hanging program is killed at the timeout;
a nonzero exit's partial stdout is discarded; missing
programs, bad argv, bad machines, and raising
command_for callables are all contained; and a failed
run carries the prior bell forward with the old
restart success stripped, inputs unchanged.

## What is NOT proven here

A live watchman on a booted test image, the running
service (these runs are one-shot --once calls from a
temp snapshot directory, not the relay-watchman.service
unit), a systemd restart, the live queue reader OS-118
still owes (the snapshot files are still the interface
until it lands; the snapshots here are hand-written
fixtures), or a transport to machines whose snapshots
are not on this host: the runner runs the CLI locally
and invents no ssh or network path. It posts nothing,
moves no claim, restarts nothing, reassigns nothing,
and sends no push; escalation payloads built by the
judge stay payloads. The plan/META_OS.md spec line is
the integrator's to add under the crew folders rule.
