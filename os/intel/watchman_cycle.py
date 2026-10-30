"""OS-122 follow-up: the runner adapter for the watchman service loop.

intel/watchman_loop.py loop_cycle() judges one cycle, but it
takes runs that are already collected: {machine: (ok, stdout)}.
Nothing in the repo collected them. A production loop that
called a runner itself would have one failure mode loop_cycle()
never sees: the runner can raise, or return something that is
not a (ok, stdout) pair at all. Left uncontained, either one
crashes the loop, and a crashed loop watches nothing -- the
silent failure the watchdog exists to catch.

run_cycle() closes that gap. It takes a caller-supplied runner
and a machine list, calls the runner once per machine, and
turns whatever comes back into the runs loop_cycle() expects:

- A runner that raises for a machine yields a failed run for
  that machine, never a crash. The exception type is recorded
  in diagnostics["runner_errors"] and the machine folds
  through loop_cycle() exactly like any other failed run:
  a prior record is carried forward and ages honestly, a
  machine with no prior stays unjudged.
- A runner that returns something other than a (ok, stdout)
  pair (not a tuple/list of length >= 2, or a first element
  that is not exactly True/False) yields a failed run too,
  recorded as "bad-return". A truthy non-True first element
  is not accepted as success: only True means the run
  happened, matching loop_cycle()'s own rule.
- A runner that is not callable at all fails every machine
  the same way, recorded per machine, instead of raising
  on the first call.
- An empty machine list yields empty records and journal
  and diagnostics with empty lists; no runner_errors key
  appears when nothing went wrong with a runner, so a clean
  cycle's diagnostics keep loop_cycle()'s exact shape.

What this module does NOT claim. It starts no subprocess
itself: the runner is supplied by the caller, so the module
has no subprocess, network, bus, or Redis path. The
production loop that supplies a real relay_watchman --once
runner (the mechanical half of Pax OS-118) still does not
exist in this repo, and the live queue reader OS-118 still
owes is still the interface it will read from. It sends no
push, restarts nothing, and reassigns nothing; escalation
payloads built by the judge stay payloads, never sends.
Inputs are never mutated: runs, priors, and journal come
back unchanged, because loop_cycle() never mutates them
and this module builds its own runs dict.
"""

from intel import watchman_loop as _loop


def _collect_runs(runner, machines):
    """Call runner once per machine -> (runs, runner_errors).

    runs is the {machine: (ok, stdout)} mapping loop_cycle()
    expects. runner_errors is {machine: reason} for machines
    whose runner raised or returned a bad pair, empty when
    every runner call returned a usable pair.
    """
    runs = {}
    runner_errors = {}
    if not callable(runner):
        for name in machines:
            runs[name] = (False, "")
            runner_errors[name] = "not-callable"
        return runs, runner_errors
    for name in machines:
        try:
            result = runner(name)
        except Exception as exc:  # noqa: BLE001 - contained, named
            runs[name] = (False, "")
            runner_errors[name] = type(exc).__name__
            continue
        runs[name], error = _pair_or_failure(result)
        if error is not None:
            runner_errors[name] = error
    return runs, runner_errors


def _pair_or_failure(result):
    """A runner result -> ((ok, stdout), error-or-None)."""
    if isinstance(result, (list, tuple)) and len(result) >= 2:
        if result[0] is True:
            return (True, result[1]), None
        if result[0] is False:
            return (False, ""), None
    return (False, ""), "bad-return"


def run_cycle(runner, machines, now, priors=None, journal=None,
              restart_ok=None):
    """One service-loop cycle driven by a caller-supplied runner.

    runner is a callable taking a machine name and returning
    (ok, stdout), or raising. machines is the iterable of
    machine names to run this cycle. now, priors, journal,
    and restart_ok pass straight through to loop_cycle().

    Returns (records, new_journal, diagnostics): records is
    the board's latest picture, new_journal holds only this
    cycle's new records, diagnostics is loop_cycle()'s
    diagnostics plus a "runner_errors" key when any runner
    call raised, was not callable, or returned a bad pair.
    """
    if machines is None:
        machine_list = []
    elif isinstance(machines, (str, bytes)):
        machine_list = [machines]
    else:
        try:
            machine_list = list(machines)
        except TypeError:
            machine_list = []
    runs, runner_errors = _collect_runs(runner, machine_list)
    records, new_journal, diagnostics = _loop.loop_cycle(
        runs, now, priors=priors, journal=journal,
        restart_ok=restart_ok)
    if runner_errors:
        diagnostics = dict(diagnostics)
        diagnostics["runner_errors"] = runner_errors
    return records, new_journal, diagnostics
