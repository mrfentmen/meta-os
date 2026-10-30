"""tests/test_intel_watchman_service.py -- OS-122 follow-up.

Pins intel/watchman_service.py serve_cycles(): the repeating
production loop that runs watchman cycles again and again,
carries records and journal forward, sleeps only between
cycles, and never dies on a bad cycle, a bad callback, a
bad stop predicate, or a bad clock. Fixture cycle functions
only, plus one default-path test over temp snapshots; no
bus post, no live Redis, no network, no systemd.
"""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

from intel import watchman_service as service  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOW = 1000000
NEW_FILES = [
    os.path.join(ROOT, "intel", "watchman_service.py"),
    os.path.join(ROOT, "intel", "drills", "watchman_service.py"),
    os.path.join(ROOT, "intel", "evals", "watchman_service.md"),
]


def _cycle(records, journal_entry):
    def _run(machines, now, priors, journal):
        return (dict(records), [journal_entry], {})
    return _run


class ServiceLoopTest(unittest.TestCase):
    def test_priors_and_journal_carry_across_cycles(self):
        seen = []

        def _run(machines, now, priors, journal):
            seen.append((copy.deepcopy(priors), list(journal)))
            return ({"alpha": {"tick": now}}, ["n%d" % now], {})

        result = service.serve_cycles(
            ["alpha"], cycle_fn=_run, now_fn=lambda: NOW,
            sleep_fn=lambda seconds: None, max_cycles=2)
        self.assertEqual(result["cycles_run"], 2)
        self.assertEqual(seen[0], ({}, []))
        self.assertEqual(seen[1][0], {"alpha": {"tick": NOW}})
        self.assertEqual(seen[1][1], ["n%d" % NOW])
        self.assertEqual(result["journal"],
                         ["n%d" % NOW, "n%d" % NOW])

    def test_sleep_only_between_cycles(self):
        sleeps = []
        result = service.serve_cycles(
            ["alpha"], cycle_fn=_cycle({}, "x"), now_fn=lambda: NOW,
            sleep_fn=lambda seconds: sleeps.append(seconds),
            max_cycles=3, interval_seconds=45)
        self.assertEqual(result["cycles_run"], 3)
        self.assertEqual(sleeps, [45, 45])

    def test_zero_cycles_runs_nothing(self):
        def _never(machines, now, priors, journal):
            raise AssertionError("must not run")

        sleeps = []
        result = service.serve_cycles(
            ["alpha"], cycle_fn=_never,
            sleep_fn=lambda seconds: sleeps.append(seconds),
            max_cycles=0)
        self.assertEqual(result["cycles_run"], 0)
        self.assertEqual(sleeps, [])
        self.assertEqual(result["records"], {})

    def test_should_stop_stops_without_sleep(self):
        sleeps = []
        result = service.serve_cycles(
            ["alpha"], cycle_fn=_cycle({}, "x"), now_fn=lambda: NOW,
            sleep_fn=lambda seconds: sleeps.append(seconds),
            max_cycles=5,
            should_stop=lambda index, records, diagnostics: index == 0)
        self.assertEqual(result["cycles_run"], 1)
        self.assertEqual(sleeps, [])

    def test_raising_cycle_contained_and_loop_recovers(self):
        calls = []

        def _flaky(machines, now, priors, journal):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("boom")
            return ({"alpha": {"watchman_alive": True}}, [], {})

        result = service.serve_cycles(
            ["alpha"], cycle_fn=_flaky, now_fn=lambda: NOW,
            sleep_fn=lambda seconds: None, max_cycles=2)
        self.assertEqual(result["cycles_run"], 2)
        self.assertEqual(
            result["diagnostics_by_cycle"][0],
            {"cycle_error": "RuntimeError"})
        self.assertTrue(result["records"]["alpha"]["watchman_alive"])

    def test_raising_callback_and_stop_contained(self):
        def _bad_callback(index, records, new_journal, diagnostics):
            raise ValueError("callback boom")

        def _bad_stop(index, records, diagnostics):
            raise KeyError("stop boom")

        result = service.serve_cycles(
            ["alpha"], cycle_fn=_cycle({}, "x"), now_fn=lambda: NOW,
            sleep_fn=lambda seconds: None, max_cycles=2,
            on_cycle=_bad_callback, should_stop=_bad_stop)
        self.assertEqual(result["cycles_run"], 2)
        self.assertEqual(result["callback_errors"],
                         ["ValueError", "ValueError"])

    def test_raising_clock_contained(self):
        result = service.serve_cycles(
            ["alpha"], cycle_fn=_cycle({"alpha": {"a": 1}}, "x"),
            now_fn=lambda: (_ for _ in ()).throw(RuntimeError("clock")),
            sleep_fn=lambda seconds: None, max_cycles=1)
        self.assertEqual(result["cycles_run"], 1)
        self.assertEqual(
            result["diagnostics_by_cycle"][0],
            {"cycle_error": "clock"})

    def test_bad_cycle_return_contained(self):
        def _bad(machines, now, priors, journal):
            return "not a triple"

        result = service.serve_cycles(
            ["alpha"], cycle_fn=_bad, now_fn=lambda: NOW,
            sleep_fn=lambda seconds: None, max_cycles=1)
        self.assertEqual(result["cycles_run"], 1)
        self.assertEqual(
            result["diagnostics_by_cycle"][0],
            {"cycle_error": "bad-cycle-return"})

    def test_negative_interval_means_no_sleep_delay(self):
        sleeps = []
        service.serve_cycles(
            ["alpha"], cycle_fn=_cycle({}, "x"), now_fn=lambda: NOW,
            sleep_fn=lambda seconds: sleeps.append(seconds),
            max_cycles=2, interval_seconds=-5)
        self.assertEqual(sleeps, [0])

    def test_inputs_never_mutated(self):
        machines = ["alpha"]
        priors = {"alpha": {"watchman_alive": False}}
        journal = ["old"]
        before = (list(machines), copy.deepcopy(priors), list(journal))
        service.serve_cycles(
            machines, cycle_fn=_cycle({}, "x"), now_fn=lambda: NOW,
            sleep_fn=lambda seconds: None, max_cycles=1,
            priors=priors, journal=journal)
        self.assertEqual((machines, priors, journal), before)

    def test_default_path_rings_on_real_snapshots(self):
        tmp = tempfile.mkdtemp(prefix="watchman-service-test-")
        jobs = [{"id": "j1", "status": "open", "addressed_to": "hana",
                 "title": "Write the brief"}]
        agents = {"hana": {"nick": "hana", "heartbeat_at": None}}
        for name, value in (("jobs", jobs), ("agents", agents)):
            with open(os.path.join(
                    tmp, "watchman-%s-alpha.json" % name),
                    "w", encoding="utf-8") as handle:
                json.dump(value, handle)
        clock = [NOW]

        def _tick():
            value = clock[0]
            clock[0] += 60
            return value

        result = service.serve_cycles(
            ["alpha"], now_fn=_tick, sleep_fn=lambda seconds: None,
            max_cycles=2, snapshot_dir=tmp)
        alpha = result["records"].get("alpha") or {}
        self.assertTrue(alpha.get("watchman_alive"))
        self.assertIsNotNone(alpha.get("last_bell"))
        self.assertEqual(
            result["diagnostics_by_cycle"][0].get("run_failures"), [])

    def test_drill_passes(self):
        drill = os.path.join(ROOT, "intel", "drills",
                             "watchman_service.py")
        proc = subprocess.run(
            [sys.executable, drill], capture_output=True, text=True,
            timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("ALL PASS", proc.stdout)

    def test_no_em_dash_in_new_files(self):
        for path in NEW_FILES:
            with open(path, encoding="utf-8") as handle:
                self.assertNotIn("\u2014", handle.read(), path)


if __name__ == "__main__":
    unittest.main()
