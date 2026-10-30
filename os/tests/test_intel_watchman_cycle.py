"""tests/test_intel_watchman_cycle.py -- OS-122 follow-up.

Pins intel/watchman_cycle.py run_cycle(): the runner adapter
that collects one relay_watchman --once run per machine from a
caller-supplied runner and folds them through loop_cycle().
A runner that raises or returns a bad pair is a contained
failed run, never a crash and never a success. Uses the real
relay_watchman tick() for wake events; the adapter itself is
fixture-only and starts no subprocess.
"""

import copy
import importlib.util
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

from intel import thresholds  # noqa: E402
from intel import watchman_cycle as cycle  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHMAN_PATH = os.path.join(ROOT, "os", "watchman",
                             "relay_watchman.py")
NOW = 1000000
STALE = thresholds.WATCHMAN_STALE_MINUTES * 60


def _load_watchman():
    spec = importlib.util.spec_from_file_location(
        "relay_watchman_cycle_test", WATCHMAN_PATH)
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


def _ring_runner(name):
    if name == "alpha":
        return (True, _stdout_for(NOW))
    return (True, "")


class TestRunCycleSuccess(unittest.TestCase):
    def test_ring_and_quiet_clean_diagnostics(self):
        calls = []

        def runner(name):
            calls.append(name)
            return _ring_runner(name)

        records, new, diagnostics = cycle.run_cycle(
            runner, ["alpha", "beta"], NOW, priors={}, journal=[])
        self.assertEqual(sorted(calls), ["alpha", "beta"])
        self.assertEqual(records["alpha"]["last_bell"], NOW)
        self.assertIsNone(records["beta"]["last_bell"])
        self.assertEqual(new, [])
        self.assertEqual(diagnostics["run_failures"], [])
        self.assertNotIn("runner_errors", diagnostics)

    def test_list_pair_accepted_as_success(self):
        records, _, _ = cycle.run_cycle(
            lambda name: [True, _stdout_for(NOW)], ["alpha"], NOW,
            priors={}, journal=[])
        self.assertEqual(records["alpha"]["last_bell"], NOW)

    def test_false_pair_is_failed_not_runner_error(self):
        _, _, diagnostics = cycle.run_cycle(
            lambda name: (False, "unused"), ["alpha"], NOW,
            priors={}, journal=[])
        self.assertEqual(diagnostics["run_failures"], ["alpha"])
        self.assertNotIn("runner_errors", diagnostics)

    def test_string_machines_is_one_machine(self):
        records, _, _ = cycle.run_cycle(
            lambda name: (True, ""), "alpha", NOW, priors={}, journal=[])
        self.assertIn("alpha", records)

    def test_none_machines_is_empty_cycle(self):
        records, new, diagnostics = cycle.run_cycle(
            lambda name: (True, ""), None, NOW, priors={}, journal=[])
        self.assertEqual(records, {})
        self.assertEqual(new, [])
        self.assertEqual(diagnostics["run_failures"], [])


class TestRunCycleRunnerFailures(unittest.TestCase):
    def test_raising_runner_carries_prior_and_names_error(self):
        records, _, _ = cycle.run_cycle(
            _ring_runner, ["alpha"], NOW, priors={}, journal=[],
            restart_ok={"alpha": True})
        priors = records

        def raising(name):
            raise RuntimeError("binary missing")

        carried, new, diagnostics = cycle.run_cycle(
            raising, ["alpha"], NOW + STALE + 100,
            priors=priors, journal=[])
        self.assertEqual(diagnostics["run_failures"], ["alpha"])
        self.assertEqual(diagnostics["runner_errors"],
                         {"alpha": "RuntimeError"})
        self.assertNotIn("restart_ok", carried["alpha"])
        self.assertEqual(carried["alpha"]["last_bell"], NOW)
        self.assertIsNot(carried["alpha"], priors["alpha"])
        kinds = [entry["kind"] for entry in new]
        self.assertEqual(kinds, ["crew-dark", "watchman-restart",
                                 "escalation"])

    def test_garbage_string_is_bad_return_unjudged(self):
        records, new, diagnostics = cycle.run_cycle(
            lambda name: "oops", ["gamma"], NOW, priors={}, journal=[])
        self.assertNotIn("gamma", records)
        self.assertEqual(new, [])
        self.assertEqual(diagnostics["runner_errors"],
                         {"gamma": "bad-return"})

    def test_short_pair_is_bad_return(self):
        _, _, diagnostics = cycle.run_cycle(
            lambda name: (True,), ["alpha"], NOW, priors={}, journal=[])
        self.assertEqual(diagnostics["runner_errors"],
                         {"alpha": "bad-return"})

    def test_truthy_one_is_not_true(self):
        records, _, diagnostics = cycle.run_cycle(
            lambda name: (1, _stdout_for(NOW)), ["alpha"], NOW,
            priors={}, journal=[])
        self.assertNotIn("alpha", records)
        self.assertEqual(diagnostics["runner_errors"],
                         {"alpha": "bad-return"})

    def test_non_callable_fails_every_machine(self):
        records, new, diagnostics = cycle.run_cycle(
            None, ["alpha", "beta"], NOW, priors={}, journal=[])
        self.assertEqual(records, {})
        self.assertEqual(new, [])
        self.assertEqual(diagnostics["runner_errors"],
                         {"alpha": "not-callable",
                          "beta": "not-callable"})

    def test_empty_machines_never_calls_runner(self):
        calls = []

        def runner(name):
            calls.append(name)
            return (True, "")

        records, new, diagnostics = cycle.run_cycle(
            runner, [], NOW, priors={}, journal=[])
        self.assertEqual(calls, [])
        self.assertEqual(records, {})
        self.assertEqual(new, [])
        self.assertNotIn("runner_errors", diagnostics)


class TestRunCycleImmutability(unittest.TestCase):
    def test_priors_and_journal_unchanged(self):
        records, _, _ = cycle.run_cycle(
            _ring_runner, ["alpha"], NOW, priors={}, journal=[],
            restart_ok={"alpha": True})
        priors = copy.deepcopy(records)
        journal = [{"kind": "crew-dark", "machine": "alpha"}]
        journal_before = copy.deepcopy(journal)

        def raising(name):
            raise ValueError("boom")

        cycle.run_cycle(raising, ["alpha"], NOW + 10,
                        priors=records, journal=journal)
        self.assertEqual(records, priors)
        self.assertEqual(journal, journal_before)


if __name__ == "__main__":
    unittest.main()
