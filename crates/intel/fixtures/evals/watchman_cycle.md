# Eval: watchman runner adapter (Milo lane, OS-122 follow-up)

## What was built

`intel/watchman_cycle.py` `run_cycle()` is the adapter between a
production loop and `watchman_loop.loop_cycle()`. The loop
judged runs that were already collected; nothing collected
them. `run_cycle()` takes a caller-supplied runner and a
machine list, calls the runner once per machine, and turns
whatever comes back into the `{machine: (ok, stdout)}` runs
the loop expects.

## Why an adapter, and why these rules

A loop that calls a runner itself has one failure mode the
judge never sees: the runner can raise, or return something
that is not a pair at all. Uncontained, either crashes the
loop, and a crashed loop watches nothing -- the exact silent
failure the watchdog exists to catch. The adapter closes it
with three containment rules:

1. A raising runner yields a failed run for that machine,
   never a crash. The exception type is recorded in
   diagnostics["runner_errors"], and the machine folds
   through the loop exactly like any other failed run: a
   prior record is carried forward and ages honestly into
   crew-dark, a machine with no prior stays unjudged.
2. A bad return yields a failed run too, recorded as
   "bad-return". Only exactly True counts as success: a
   truthy 1 is a failure, matching loop_cycle()'s own rule
   that only True means the run happened. A non-callable
   runner fails every machine as "not-callable" instead of
   raising on the first call.
3. Clean cycles keep loop_cycle()'s exact diagnostics shape:
   the runner_errors key appears only when a runner actually
   misbehaved, so a clean cycle's diagnostics are unchanged.

Inputs are never mutated, carried records are copies, and
the module starts no subprocess, posts nothing, and sends
no push: the runner is caller-supplied, and the escalation
payloads the judge builds stay payloads.

## Drill result

`intel/drills/watchman_cycle.py`: 6 phases, all PASS
(transcript: `intel/evals/watchman_cycle.log`). The ring
reads ALIVE with its bell at the tick time, the quiet
machine reads UNKNOWN, a raising runner ages its prior into
one dark episode with one fail-closed escalation, garbage
and truthy returns are contained failures, a non-callable
runner fails all machines without raising, an empty machine
list runs nothing, and priors/journal come back unchanged.

## What is NOT proven here

A live watchman on a booted test image, the running service,
a systemd restart, the production loop that supplies a real
relay_watchman --once runner (the mechanical half of Pax
OS-118, still owed), or the live queue reader OS-118 still
owes. This adapter is the last pure piece before that
mechanical half: the production loop will call run_cycle()
with its runner and its machine list, and change no judgment
to do it.
