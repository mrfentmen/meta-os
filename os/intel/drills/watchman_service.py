"""Watchman service-loop drill (Milo lane, OS-122 follow-up).

loop_cycle() judged one cycle, run_cycle() collected one
cycle, and watchman_runner.py ran the real program for one
cycle. Nothing ran cycles again and again. This drill proves
intel/watchman_service.py is the loop that was missing.
Seven checks:

1. State carries across cycles: a fixture cycle_fn records
   the priors it receives; cycle 2 sees cycle 1's records
   as its priors, the journal accumulates across cycles,
   and exactly one sleep happens between two cycles.
2. max_cycles=0 runs nothing and never sleeps.
3. should_stop() stops the loop after the first cycle, with
   no sleep after the stopped cycle.
4. A raising cycle_fn is contained: cycle 1 raises and
   yields a cycle_error diagnostic with prior records
   carried, cycle 2 succeeds, and the loop finishes both
   cycles with the cycle 2 records as the final picture.
5. A raising on_cycle callback and a raising should_stop
   predicate are both contained and the loop still runs
   every cycle.
6. The default cycle_fn is the real production path: with
   a temp snapshot directory, a ringing machine rings on
   cycle 1, the watchman's own dedupe makes cycle 2 quiet,
   and the loop's final records carry the bell from
   cycle 1 into cycle 2.
7. Caller inputs are never mutated: the machines list,
   priors, and journal passed in come back unchanged.

What this drill does NOT claim, stated plainly. The loop
proves repeated cycles on fixtures and on one-shot --once
runs from a temp snapshot directory, not a live service:
no booted test image, no relay-watchman.service actually
running (the runs here are --once calls, not the unit),
no systemd restart of a dead watchman, no agent session
started (OS-119), no job reassigned (OS-125), no push
sent (Hana OS-097), and no live queue reader (OS-118's
snapshot files are still the interface until it lands).
A failed cycle here is a diagnostics line, and the
escalation is a payload, never a send. No bus post, no
live Redis, no network.

Runs unattended: python3 intel/drills/watchman_service.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import copy
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import watchman_service as service  # noqa: E402

NOW = 1000000


def _fail(message):
    print("FAIL: %s" % message)
    return 1


def _write_json(path, value):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle)


def main():
    # Phase 1: priors and journal carry across cycles; one
    # sleep between two cycles.
    seen_priors = []
    sleeps = []

    def _cycle(machines, now, priors, journal):
        seen_priors.append(copy.deepcopy(priors))
        record = {"watchman_alive": True, "last_tick": now}
        return ({"alpha": record}, ["note-%d" % now], {})

    result = service.serve_cycles(
        ["alpha"], cycle_fn=_cycle, now_fn=lambda: NOW,
        sleep_fn=lambda seconds: sleeps.append(seconds),
        max_cycles=2, interval_seconds=30)
    if result["cycles_run"] != 2 or sleeps != [30]:
        return _fail("phase 1: cycles/sleeps wrong: %r %r"
                     % (result["cycles_run"], sleeps))
    if seen_priors[0] != {} or seen_priors[1] != {
            "alpha": {"watchman_alive": True, "last_tick": NOW}}:
        return _fail("phase 1: priors did not carry: %r" % (seen_priors,))
    if result["journal"] != ["note-%d" % NOW, "note-%d" % NOW]:
        return _fail("phase 1: journal did not accumulate: %r"
                     % (result["journal"],))
    print("PASS phase 1: priors and journal carry, one sleep "
          "between two cycles")

    # Phase 2: max_cycles=0 runs nothing, never sleeps.
    sleeps = []

    def _never(machines, now, priors, journal):
        raise AssertionError("cycle_fn must not run")

    result = service.serve_cycles(
        ["alpha"], cycle_fn=_never, sleep_fn=lambda s: sleeps.append(s),
        max_cycles=0)
    if result["cycles_run"] != 0 or sleeps or result["records"] != {}:
        return _fail("phase 2: zero cycles ran something: %r %r"
                     % (result, sleeps))
    print("PASS phase 2: max_cycles=0 runs nothing, never sleeps")

    # Phase 3: should_stop stops after cycle 1, no sleep.
    sleeps = []
    result = service.serve_cycles(
        ["alpha"], cycle_fn=_cycle, now_fn=lambda: NOW,
        sleep_fn=lambda seconds: sleeps.append(seconds),
        max_cycles=5, interval_seconds=30,
        should_stop=lambda index, records, diagnostics: index == 0)
    if result["cycles_run"] != 1 or sleeps:
        return _fail("phase 3: should_stop did not stop cleanly: %r %r"
                     % (result["cycles_run"], sleeps))
    print("PASS phase 3: should_stop stops after cycle 1, no sleep")

    # Phase 4: a raising cycle_fn is contained, loop recovers.
    calls = []

    def _flaky(machines, now, priors, journal):
        calls.append(len(calls))
        if len(calls) == 1:
            raise RuntimeError("boom")
        return ({"alpha": {"watchman_alive": True}}, [], {})

    result = service.serve_cycles(
        ["alpha"], cycle_fn=_flaky, now_fn=lambda: NOW,
        sleep_fn=lambda seconds: None, max_cycles=2)
    if result["cycles_run"] != 2:
        return _fail("phase 4: raising cycle ended the loop: %r"
                     % (result,))
    if result["diagnostics_by_cycle"][0].get("cycle_error") \
            != "RuntimeError":
        return _fail("phase 4: cycle_error not recorded: %r"
                     % (result["diagnostics_by_cycle"],))
    if result["records"].get("alpha", {}).get("watchman_alive") is not True:
        return _fail("phase 4: loop did not recover: %r"
                     % (result["records"],))
    print("PASS phase 4: raising cycle contained, loop recovers "
          "on the next cycle")

    # Phase 5: raising on_cycle and raising should_stop contained.
    def _bad_callback(index, records, new_journal, diagnostics):
        raise ValueError("callback boom")

    def _bad_stop(index, records, diagnostics):
        raise KeyError("stop boom")

    result = service.serve_cycles(
        ["alpha"], cycle_fn=_cycle, now_fn=lambda: NOW,
        sleep_fn=lambda seconds: None, max_cycles=2,
        on_cycle=_bad_callback, should_stop=_bad_stop)
    if result["cycles_run"] != 2 or result["callback_errors"] != \
            ["ValueError", "ValueError"]:
        return _fail("phase 5: callback/stop raise escaped: %r"
                     % (result,))
    print("PASS phase 5: raising callback and stop predicate "
          "contained, loop runs every cycle")

    # Phase 6: the default cycle_fn is the real production
    # path over temp snapshots: ring once, quiet next.
    tmp = tempfile.mkdtemp(prefix="watchman-service-drill-")
    jobs = [{"id": "j1", "status": "open", "addressed_to": "hana",
             "title": "Write the brief"}]
    agents = {"hana": {"nick": "hana", "heartbeat_at": None}}
    _write_json(os.path.join(tmp, "watchman-jobs-alpha.json"), jobs)
    _write_json(os.path.join(tmp, "watchman-agents-alpha.json"), agents)
    clock = [NOW]

    def _tick_clock():
        value = clock[0]
        clock[0] += 60
        return value

    result = service.serve_cycles(
        ["alpha"], now_fn=_tick_clock,
        sleep_fn=lambda seconds: None, max_cycles=2,
        snapshot_dir=tmp)
    alpha = result["records"].get("alpha") or {}
    if not alpha.get("watchman_alive") or alpha.get("last_bell") is None:
        return _fail("phase 6: default loop lost the bell: %r"
                     % (result["records"],))
    if result["diagnostics_by_cycle"][0].get("run_failures"):
        return _fail("phase 6: real runs failed: %r"
                     % (result["diagnostics_by_cycle"],))
    print("PASS phase 6: default loop rings on real snapshots, "
          "bell carried into cycle 2")

    # Phase 7: caller inputs never mutated.
    machines = ["alpha"]
    priors = {"alpha": {"watchman_alive": False}}
    journal = ["old"]
    before = (list(machines), copy.deepcopy(priors), list(journal))
    service.serve_cycles(
        machines, cycle_fn=_cycle, now_fn=lambda: NOW,
        sleep_fn=lambda seconds: None, max_cycles=1,
        priors=priors, journal=journal)
    if (machines, priors, journal) != before:
        return _fail("phase 7: caller inputs mutated")
    print("PASS phase 7: caller inputs unchanged")

    print("ALL PASS: watchman service loop")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
