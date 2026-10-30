"""Watchman runner-adapter drill (Milo lane, OS-122 follow-up).

loop_cycle() judges runs that are already collected, but a
production loop must collect them by calling a runner per
machine -- and a runner can raise or return garbage. This
drill proves intel/watchman_cycle.py run_cycle() on fixtures,
in six checks:

1. Two machines through a well-behaved runner, real Pax tick
   output as stdout: the ringing machine reads its bell at
   the tick time, the quiet machine invents no bell, the
   journal stays empty, the runner is called once per
   machine, and clean diagnostics carry no runner_errors key.
2. A raising runner ages honestly: the ringing machine's
   runner raises on a later cycle, so its prior record is
   carried forward with restart_ok stripped and its bell
   unchanged; past the stale window it journals exactly one
   crew-dark, one restart reading restart failed, and one
   escalation; diagnostics name the machine in run_failures
   and the exception type in runner_errors. No crash.
3. A garbage-returning runner is contained: a machine whose
   runner returns a bare string (no prior record) earns no
   record and journals nothing, and diagnostics record it
   as a bad-return failure, not a success.
4. A non-callable runner fails every machine the same way:
   no record, no journal, runner_errors per machine reading
   not-callable, and still no raise.
5. An empty machine list yields empty records and journal
   and diagnostics with empty lists, and the runner is never
   called.
6. Truthy is not True, and inputs are never mutated: a
   runner returning (1, stdout) -- truthy, but not True --
   is a failed run, not a success; a short (True,) pair is
   a bad return; priors and journal come back unchanged,
   and a carried record is a copy, not the prior object.

What this drill does NOT claim, stated plainly. The
adapter proves the collection judgment, not a live service:
no booted test image, no relay-watchman.service actually
running (runners here are fixture callables, the module
starts no subprocess), no systemd restart of a dead
watchman, no agent session started (OS-119), no job
reassigned (OS-125), no push sent (Hana OS-097), and no
live queue reader (OS-118's snapshot files are still the
interface until it lands). A failed run here is a
diagnostics line, and the escalation is a payload, never a
send. No bus post, no live Redis, no network.

Runs unattended: python3 intel/drills/watchman_cycle.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import copy
import importlib.util
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import thresholds  # noqa: E402
from intel import watchman_cycle as cycle  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
WATCHMAN_PATH = os.path.join(ROOT, "os", "watchman",
                             "relay_watchman.py")
NOW = 1000000
STALE = thresholds.WATCHMAN_STALE_MINUTES * 60


def _load_watchman():
    spec = importlib.util.spec_from_file_location(
        "relay_watchman_cycle_drill", WATCHMAN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WATCHMAN = _load_watchman()
JOBS = [{"id": "j1", "status": "open", "addressed_to": "hana"}]
AGENTS = {"hana": {"nick": "hana", "heartbeat_at": NOW - 3600}}


def _stdout_for(at):
    events, _ = WATCHMAN.tick(JOBS, AGENTS, set(), at)
    return "".join(json.dumps(event, sort_keys=True) + "\n"
                   for event in events)


def _kinds(journal):
    return [entry["kind"] for entry in journal]


def _fail(msg):
    print("FAIL: %s" % msg)
    return 1


def main():
    journal = []

    # Phase 1: well-behaved runner, ring + quiet.
    calls = []

    def good_runner(name):
        calls.append(name)
        if name == "alpha":
            return (True, _stdout_for(NOW))
        return (True, "")

    records, new, diagnostics = cycle.run_cycle(
        good_runner, ["alpha", "beta"], NOW, priors={}, journal=journal,
        restart_ok={"alpha": True})
    journal = journal + new
    if sorted(calls) != ["alpha", "beta"]:
        return _fail("phase 1: runner not called once per machine")
    if records["alpha"]["last_bell"] != NOW:
        return _fail("phase 1: ringing machine bell is not the tick time")
    if records["beta"]["last_bell"] is not None:
        return _fail("phase 1: quiet machine invented a bell")
    if new or diagnostics["run_failures"]:
        return _fail("phase 1: quiet cycle journaled or failed")
    if "runner_errors" in diagnostics:
        return _fail("phase 1: clean cycle carries runner_errors")
    print("PASS phase 1: runner ring reads ALIVE bell, quiet reads "
          "UNKNOWN, clean diagnostics")
    priors = records

    # Phase 2: alpha's runner raises; the prior ages honestly.
    def raising_runner(name):
        if name == "alpha":
            raise RuntimeError("watchman binary missing")
        return (True, "")

    priors_before = copy.deepcopy(priors)
    journal_before = copy.deepcopy(journal)
    records, new, diagnostics = cycle.run_cycle(
        raising_runner, ["alpha", "beta"], NOW + STALE + 100,
        priors=priors, journal=journal)
    journal = journal + new
    if diagnostics["run_failures"] != ["alpha"]:
        return _fail("phase 2: raising runner not in run_failures")
    if diagnostics.get("runner_errors") != {"alpha": "RuntimeError"}:
        return _fail("phase 2: exception type not recorded, got %s"
                     % diagnostics.get("runner_errors"))
    if "restart_ok" in records["alpha"]:
        return _fail("phase 2: carried record re-spent restart_ok")
    if records["alpha"]["last_bell"] != NOW:
        return _fail("phase 2: carried record refreshed its bell")
    if records["alpha"] is priors["alpha"]:
        return _fail("phase 2: carried record is the prior object")
    if _kinds(new) != ["crew-dark", "watchman-restart",
                       "escalation"]:
        return _fail("phase 2: expected dark+restart+escalation, got %s"
                     % _kinds(new))
    if priors != priors_before or journal_before != journal[:len(journal_before)]:
        return _fail("phase 2: priors or journal mutated")
    print("PASS phase 2: raising runner contained, prior ages into "
          "one dark episode with one fail-closed escalation")
    priors = records

    # Phase 3: garbage return contained, unjudged without prior.
    def garbage_runner(name):
        return "oops, not a pair"

    records, new, diagnostics = cycle.run_cycle(
        garbage_runner, ["gamma"], NOW, priors={}, journal=[])
    if "gamma" in records or new:
        return _fail("phase 3: garbage runner earned a record")
    if diagnostics["run_failures"] != ["gamma"]:
        return _fail("phase 3: garbage run not in run_failures")
    if diagnostics.get("runner_errors") != {"gamma": "bad-return"}:
        return _fail("phase 3: bad return not recorded, got %s"
                     % diagnostics.get("runner_errors"))
    print("PASS phase 3: garbage runner return is a contained "
          "failure, never a success")

    # Phase 4: non-callable runner fails every machine, no raise.
    records, new, diagnostics = cycle.run_cycle(
        None, ["alpha", "beta"], NOW, priors={}, journal=[])
    if records or new:
        return _fail("phase 4: non-callable runner earned records")
    if diagnostics.get("runner_errors") != {"alpha": "not-callable",
                                            "beta": "not-callable"}:
        return _fail("phase 4: not-callable not recorded per machine")
    print("PASS phase 4: non-callable runner fails all machines, "
          "still no raise")

    # Phase 5: empty machine list runs nothing.
    calls = []

    def counting_runner(name):
        calls.append(name)
        return (True, "")

    records, new, diagnostics = cycle.run_cycle(
        counting_runner, [], NOW, priors={}, journal=[])
    if records or new or calls:
        return _fail("phase 5: empty machine list ran something")
    if diagnostics["run_failures"] or "runner_errors" in diagnostics:
        return _fail("phase 5: empty cycle carries failures")
    print("PASS phase 5: empty machine list yields empty cycle, "
          "runner never called")

    # Phase 6: truthy is not True; short pairs; inputs untouched.
    def tricky_runner(name):
        if name == "alpha":
            return (1, _stdout_for(NOW + 500))
        return (True,)

    priors_before = copy.deepcopy(priors)
    journal_before = copy.deepcopy(journal)
    records, new, diagnostics = cycle.run_cycle(
        tricky_runner, ["alpha", "beta"], NOW + 500,
        priors=priors, journal=journal)
    if diagnostics.get("runner_errors") != {"alpha": "bad-return",
                                            "beta": "bad-return"}:
        return _fail("phase 6: truthy/short pairs not bad-returns, "
                     "got %s" % diagnostics.get("runner_errors"))
    if priors != priors_before or journal != journal_before:
        return _fail("phase 6: priors or journal mutated")
    print("PASS phase 6: truthy is not True, short pairs fail, "
          "inputs unchanged")
    print("ALL PASS (6 phases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
