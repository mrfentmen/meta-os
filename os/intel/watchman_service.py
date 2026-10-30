"""OS-122 follow-up: the repeating production loop for the watchman.

intel/watchman_loop.py judges one cycle, intel/watchman_cycle.py
collects one cycle from a caller-supplied runner, and
intel/watchman_runner.py supplies the real subprocess runner.
What still did not exist was the loop itself: something that
runs those cycles again and again, carries the board picture
and the journal forward from cycle to cycle, and keeps
watching when one cycle goes wrong. A loop that dies on a
bad cycle watches nothing, which is the silent failure the
watchdog exists to catch. This module is that loop.

How it runs. serve_cycles() takes a machine list and repeats
one cycle per interval:

- Each cycle calls cycle_fn(machines, now, priors, journal)
  and gets back (records, new_journal, diagnostics). By
  default cycle_fn is run_cycle_with_subprocess() against
  the snapshot directory, so the production loop runs the
  real Pax OS-118 program once per machine per cycle with
  no judgment changed.
- The records of one cycle become the priors of the next,
  and each cycle's new journal entries accumulate into the
  loop's journal, so episode dedupe in the judge holds
  across cycles: a machine that recovers and dies again
  re-alerts, while a machine that stays dark does not
  re-escalate every cycle.
- now_fn supplies the clock (default time.time as an int).
  A fake clock in tests makes cycle timing exact, and the
  production loop never reads the wall clock twice for
  one cycle.
- sleep_fn sleeps between cycles only, never after the
  last cycle. max_cycles bounds a run; None means run
  until should_stop() says stop. should_stop(index,
  records, diagnostics) is checked after each cycle, so
  a caller can stop on a condition (for example, a
  recovered machine) instead of a fixed count.

What never kills the loop, stated plainly because each
one guards a silent-failure class:

- A cycle_fn that raises yields that cycle's diagnostics
  {"cycle_error": <exception type>} and the prior records
  carried forward unchanged, never a crash. The next
  cycle still runs, and the carried bell ages honestly
  through the judge on the next successful cycle.
- An on_cycle callback that raises is contained the same
  way: its exception type is collected in the result's
  callback_errors and the loop continues.
- A should_stop predicate that raises is treated as
  False: a stop check that crashes must not stop the
  watcher. A sleep_fn that raises is ignored: a missed
  sleep delays the next cycle, it never ends watching.
- A now_fn that raises yields a cycle_error cycle with
  the prior records carried, and the loop continues.

What this module does NOT claim. It posts nothing to the
bus, moves no claim, restarts no process (systemd under
OS-034), reassigns no job (OS-125 baton), and sends no
push (Hana OS-097): escalation payloads built by the
judge stay payloads, never sends. It reads no live queue:
the live queue reader OS-118 still owes is the interface
that will write the snapshot files the default cycle_fn
reads. It starts no agent session (OS-119). The loop
runs as a systemd unit in os/services/relay-watchman-watch.service
(OS-122 follow-up); the __main__ entry point below is the command
that unit execs. Running that command as a plain script used to
fail before any cycle ran: Python puts the script's own directory
(intel/) first on sys.path, not the repo root, so "from intel
import ..." raised ModuleNotFoundError and the unit's ExecStart
would have died at startup no matter what WorkingDirectory it
carried. The bootstrap below inserts the repo root (the parent
of this file's directory, /opt/relay on the image) so the unit
command runs with no PYTHONPATH set, the same bootstrap the
intel/* script entry points already use. A booted service is
still not proven here, but the command the unit execs is.
Inputs are never mutated: the machine list, priors, and
journal the caller passes in come back unchanged.
"""

import copy
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

from intel import watchman_runner as _runner

DEFAULT_INTERVAL_SECONDS = 60

__all__ = [
    "DEFAULT_INTERVAL_SECONDS",
    "default_cycle_fn",
    "serve_cycles",
]


def default_cycle_fn(machines, now, priors=None, journal=None,
                     snapshot_dir=None, timeout_seconds=None):
    """One production cycle through the real subprocess runner."""
    kwargs = {}
    if snapshot_dir is not None:
        kwargs["snapshot_dir"] = snapshot_dir
    if timeout_seconds is not None:
        kwargs["timeout_seconds"] = timeout_seconds
    return _runner.run_cycle_with_subprocess(
        machines, now, priors=priors, journal=journal, **kwargs)


def _machine_list(machines):
    if machines is None:
        return []
    if isinstance(machines, (str, bytes)):
        return [machines]
    try:
        return list(machines)
    except TypeError:
        return []


def _interval_seconds(value):
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return DEFAULT_INTERVAL_SECONDS
    if seconds != seconds or seconds < 0:  # NaN guard, negative -> 0
        return 0 if seconds < 0 else DEFAULT_INTERVAL_SECONDS
    return seconds


def serve_cycles(machines, cycle_fn=None, now_fn=None, sleep_fn=None,
                 max_cycles=None, interval_seconds=None,
                 should_stop=None, on_cycle=None, priors=None,
                 journal=None, snapshot_dir=None, timeout_seconds=None):
    """Run watchman cycles until max_cycles or should_stop().

    machines is the iterable of machine names run every
    cycle. cycle_fn(machines, now, priors, journal) returns
    (records, new_journal, diagnostics); when None, the
    default runs the real relay_watchman --once per machine
    against snapshot_dir (production default /run/metaos).
    now_fn() returns the cycle clock value; sleep_fn()
    sleeps between cycles; both default to the real clock
    and time.sleep. max_cycles None means unbounded until
    should_stop(index, records, diagnostics) returns True.
    on_cycle(index, records, new_journal, diagnostics) is
    called after every cycle for reporting.

    Returns {"cycles_run": n, "records": final records,
    "journal": accumulated journal, "diagnostics_by_cycle":
    [diagnostics per cycle], "callback_errors": [exception
    type names from on_cycle callbacks]}. A cycle whose
    cycle_fn raises contributes diagnostics {"cycle_error":
    <type>} and carries the prior records forward.
    """
    machine_list = _machine_list(machines)
    if cycle_fn is None:
        def _default(machines_arg, now, priors_arg, journal_arg):
            return default_cycle_fn(
                machines_arg, now, priors=priors_arg,
                journal=journal_arg, snapshot_dir=snapshot_dir,
                timeout_seconds=timeout_seconds)
        cycle_fn = _default
    if now_fn is None:
        now_fn = lambda: int(time.time())  # noqa: E731
    if sleep_fn is None:
        sleep_fn = time.sleep
    interval = (DEFAULT_INTERVAL_SECONDS if interval_seconds is None
                else _interval_seconds(interval_seconds))
    if max_cycles is not None:
        try:
            max_cycles = int(max_cycles)
        except (TypeError, ValueError):
            max_cycles = 0
        if max_cycles <= 0:
            return {"cycles_run": 0, "records": {},
                    "journal": list(journal) if isinstance(journal, list)
                    else [],
                    "diagnostics_by_cycle": [], "callback_errors": []}

    current_priors = copy.deepcopy(priors) if isinstance(priors, dict) \
        else {}
    accumulated = list(journal) if isinstance(journal, list) else []
    diagnostics_by_cycle = []
    callback_errors = []
    cycles_run = 0

    while True:
        try:
            now = now_fn()
        except Exception:  # noqa: BLE001 - contained, loop continues
            now = None
        if now is None:
            records = copy.deepcopy(current_priors)
            new_journal = []
            diagnostics = {"cycle_error": "clock"}
        else:
            try:
                raw = cycle_fn(
                    list(machine_list), now, copy.deepcopy(current_priors),
                    list(accumulated))
            except Exception as exc:  # noqa: BLE001 - contained, named
                records = copy.deepcopy(current_priors)
                new_journal = []
                diagnostics = {"cycle_error": type(exc).__name__}
            else:
                try:
                    records, new_journal, diagnostics = raw
                except Exception:  # noqa: BLE001 - a bad return is
                    records = copy.deepcopy(current_priors)  # not a crash
                    new_journal = []
                    diagnostics = {"cycle_error": "bad-cycle-return"}
        if not isinstance(records, dict):
            records = copy.deepcopy(current_priors)
        if not isinstance(new_journal, list):
            new_journal = []
        if not isinstance(diagnostics, dict):
            diagnostics = {"cycle_error": "bad-cycle-return"}
        diagnostics_by_cycle.append(diagnostics)
        accumulated = accumulated + list(new_journal)
        current_priors = copy.deepcopy(records)
        cycles_run += 1
        if on_cycle is not None:
            try:
                on_cycle(cycles_run - 1, copy.deepcopy(records),
                         list(new_journal), dict(diagnostics))
            except Exception as exc:  # noqa: BLE001 - contained, named
                callback_errors.append(type(exc).__name__)
        stop = False
        if should_stop is not None:
            try:
                stop = bool(should_stop(cycles_run - 1,
                                        copy.deepcopy(records),
                                        dict(diagnostics)))
            except Exception:  # noqa: BLE001 - a crashing stop check
                stop = False  # never stops the watcher
        if stop:
            break
        if max_cycles is not None and cycles_run >= max_cycles:
            break
        try:
            sleep_fn(interval)
        except Exception:  # noqa: BLE001 - a missed sleep never stops
            pass

    return {"cycles_run": cycles_run, "records": current_priors,
            "journal": accumulated,
            "diagnostics_by_cycle": diagnostics_by_cycle,
            "callback_errors": callback_errors}


def main(argv=None):
    """Command entry point: the command relay-watchman-watch.service execs.

    python3 intel/watchman_service.py --machines alpha,beta
        [--cycles N] [--interval SECONDS]
        [--snapshot-dir DIR]
    """
    import argparse
    parser = argparse.ArgumentParser(
        description="Watchman service loop (OS-122).")
    parser.add_argument("--machines", nargs="?", const="",
                        default="",
                        help="Comma-separated machine names. "
                        "A bare --machines (no value) reads as an "
                        "empty list: the unit's ExecStart passes "
                        "${WATCHMAN_WATCH_MACHINES}, and with no env "
                        "file systemd expands that to nothing, "
                        "leaving --machines directly before "
                        "--snapshot-dir; without nargs='?' argparse "
                        "would fail that shape with exit 2 and the "
                        "unit would restart-loop instead of cycling "
                        "empty.")
    parser.add_argument("--cycles", type=int, default=None,
                        help="Cycle count; omit to run until stopped.")
    parser.add_argument("--interval", type=float,
                        default=DEFAULT_INTERVAL_SECONDS,
                        help="Seconds between cycles.")
    parser.add_argument("--snapshot-dir", default=None,
                        help="Snapshot directory (default /run/metaos).")
    args = parser.parse_args(argv)
    machines = [name.strip() for name in args.machines.split(",")
                if name.strip()]

    def _report(index, records, new_journal, diagnostics):
        print("cycle %d: %d machines, %d new journal, %r"
              % (index, len(records), len(new_journal), diagnostics))

    try:
        result = serve_cycles(
            machines, max_cycles=args.cycles,
            interval_seconds=args.interval, on_cycle=_report,
            snapshot_dir=args.snapshot_dir)
    except KeyboardInterrupt:
        return 0
    print("service loop stopped after %d cycles"
          % result["cycles_run"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
