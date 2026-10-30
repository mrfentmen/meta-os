"""OS-122 follow-up: the real subprocess runner for the watchman loop.

intel/watchman_cycle.py run_cycle() collects one relay_watchman
--once run per machine from a caller-supplied runner, but every
runner it has ever seen was a fixture callable. The production
loop still had no runner that actually runs anything, so the
service loop could judge runs but never collect them. This
module is that runner: it runs the real Pax OS-118 program,
os/watchman/relay_watchman.py, once per machine, and turns
each subprocess result into the (ok, stdout) pair the loop
expects.

How one machine is run. By default a machine's snapshots
live under a snapshot directory (production default
/run/metaos, the directory the relay-watchman.service unit
reads from) as per-machine files:

    watchman-jobs-<machine>.json
    watchman-agents-<machine>.json
    watchman-state-<machine>.json

The runner builds [python, relay_watchman.py, --once,
--jobs-file ..., --agents-file ..., --state-file ...] for
that machine and runs it. The state file is per machine so
the watchman's own rung dedupe (a job rings once) holds
across cycles. A caller that keeps snapshots somewhere else
supplies its own command_for(machine) callable returning
an argv list instead; the default is only a convenience,
not a second interface.

What counts as success, stated plainly because the loop
depends on it:

- Exit 0 means the run happened and stdout holds the
  event lines. Only exit 0 counts: a nonzero exit means
  the run failed and its stdout is discarded, even when
  the program printed partial lines before failing. The
  loop's rule is that a failed run's stdout is unusable,
  and this runner enforces it instead of passing partial
  output along and hoping the loop ignores it.
- A timeout kills the process and counts as a failed run.
  A watchman that hangs must not hang the loop with it.
- A missing program, an unreadable argv, or any other
  subprocess error counts as a failed run, never a raise.
  The runner itself never raises for a bad machine name,
  a bad argv, or a command_for that raises: every failure
  is a (False, "") pair, so run_cycle() folds it exactly
  like any other failed run and the machine's prior record
  ages honestly into crew-dark instead of crashing the
  loop that watches it.

What this module does NOT claim. It runs the CLI locally
against snapshot files; it does not reach another machine
over the network, does not ssh anywhere, and does not
invent a transport for machines whose snapshots are not
on this host. A machine with no snapshot files on this
host yields a quiet successful run, not a phantom ring:
relay_watchman --once reads a missing file as an empty
snapshot with a stderr note, per OS-118, so the loop
folds it as a quiet run (UNKNOWN, no bell invented).
A malformed snapshot file is the failure case: --once
exits 2 and the runner reports a failed run. It posts
nothing to the bus, moves no claim,
restarts nothing, reassigns nothing, and sends no push:
escalation payloads built by the judge stay payloads.
It reads no live queue: the live queue reader OS-118
still owes is the interface that will write these
snapshot files, and until it lands the snapshots are
the interface. Inputs are never mutated, and no secret
appears on any command line.
"""

import os
import subprocess
import sys

from intel import watchman_cycle as _cycle

DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_SNAPSHOT_DIR = "/run/metaos"

_PROGRAM = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "os", "watchman", "relay_watchman.py")

__all__ = [
    "DEFAULT_SNAPSHOT_DIR",
    "DEFAULT_TIMEOUT_SECONDS",
    "default_program",
    "machine_argv",
    "make_subprocess_runner",
    "run_cycle_with_subprocess",
    "run_once",
]


def default_program():
    """Path of the repo's relay_watchman program."""
    return _PROGRAM


def machine_argv(machine, snapshot_dir=DEFAULT_SNAPSHOT_DIR,
                 program=None):
    """The --once argv for one machine's snapshot files.

    Returns None when the machine name is not a usable
    non-empty string, so callers can treat it as a failed
    run instead of building an argv out of garbage.
    """
    if not isinstance(machine, str) or not machine.strip():
        return None
    if not isinstance(snapshot_dir, str) or not snapshot_dir:
        snapshot_dir = DEFAULT_SNAPSHOT_DIR
    program = program or _PROGRAM
    base = os.path.join(snapshot_dir, "watchman-%s-%s.json")
    return [sys.executable, program, "--once",
            "--jobs-file", base % ("jobs", machine),
            "--agents-file", base % ("agents", machine),
            "--state-file", base % ("state", machine)]


def run_once(argv, timeout_seconds=DEFAULT_TIMEOUT_SECONDS):
    """Run one argv -> (ok, stdout, detail).

    ok is True only on exit 0. stdout is the program's
    stdout on success and "" on every failure, so a
    failed run never leaks partial lines downstream.
    detail is None on success and one of "timeout",
    "not-found", "bad-argv", "error", or "exit-<code>"
    on failure, so a caller can log why the run failed
    without treating the detail as a watchman record.
    This function never raises.
    """
    if (not isinstance(argv, (list, tuple)) or not argv
            or any(not isinstance(part, str) or not part
                   for part in argv)):
        return (False, "", "bad-argv")
    try:
        timeout = float(timeout_seconds)
    except (TypeError, ValueError):
        timeout = float(DEFAULT_TIMEOUT_SECONDS)
    if timeout <= 0:
        timeout = float(DEFAULT_TIMEOUT_SECONDS)
    try:
        proc = subprocess.run(
            list(argv), capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return (False, "", "timeout")
    except FileNotFoundError:
        return (False, "", "not-found")
    except (OSError, ValueError):
        return (False, "", "error")
    except Exception:  # noqa: BLE001 - contained, never raised
        return (False, "", "error")
    if proc.returncode != 0:
        return (False, "", "exit-%s" % proc.returncode)
    return (True, proc.stdout.decode("utf-8", "replace"), None)


def make_subprocess_runner(command_for=None,
                           timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
                           snapshot_dir=DEFAULT_SNAPSHOT_DIR,
                           program=None):
    """A run_cycle()-compatible runner over real subprocesses.

    command_for is a callable taking a machine name and
    returning an argv list; when omitted, machine_argv()
    over snapshot_dir supplies it. The returned runner
    takes a machine name and returns (ok, stdout), and
    never raises: a bad machine, a bad argv, a raising
    command_for, a timeout, or a nonzero exit all yield
    (False, ""). The detail run_once() reports is the
    runner's own concern, not the loop's: run_cycle()
    already records a failed run per machine in
    diagnostics["run_failures"].
    """
    if command_for is None:
        def _default(machine):
            return machine_argv(machine,
                                snapshot_dir=snapshot_dir,
                                program=program)
        command_for = _default

    def runner(machine):
        try:
            argv = command_for(machine)
        except Exception:  # noqa: BLE001 - contained, never raised
            return (False, "")
        if argv is None:
            return (False, "")
        ok, stdout, _detail = run_once(argv, timeout_seconds)
        return (ok, stdout)

    return runner


def run_cycle_with_subprocess(machines, now, priors=None, journal=None,
                              restart_ok=None, command_for=None,
                              timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
                              snapshot_dir=DEFAULT_SNAPSHOT_DIR,
                              program=None):
    """One service-loop cycle driven by real --once runs.

    Builds a subprocess runner and passes it straight to
    run_cycle(), so the production loop calls this one
    function with its machine list and gets back the same
    (records, new_journal, diagnostics) the fixture
    adapter returns, with no judgment changed. machines,
    now, priors, journal, and restart_ok pass through
    untouched to run_cycle().
    """
    runner = make_subprocess_runner(
        command_for=command_for, timeout_seconds=timeout_seconds,
        snapshot_dir=snapshot_dir, program=program)
    return _cycle.run_cycle(runner, machines, now, priors=priors,
                            journal=journal, restart_ok=restart_ok)
