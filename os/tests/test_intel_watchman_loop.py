"""tests/test_intel_watchman_loop.py -- OS-122 follow-up.

Pins intel/watchman_loop.py loop_cycle(): the service-loop
caller that runs one relay_watchman --once cycle per machine
(supplied as (ok, stdout) pairs), folds successful runs
through watchman_tick(), and carries a failed run's prior
record unchanged into the judge so its bell ages honestly.
Uses the real relay_watchman tick() for wake events; the
loop itself is fixture-only.
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
from intel import watchman_loop as loop  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHMAN_PATH = os.path.join(ROOT, "os", "watchman",
                             "relay_watchman.py")
NOW = 1000000
STALE = thresholds.WATCHMAN_STALE_MINUTES * 60


def _load_watchman():
    spec = importlib.util.spec_from_file_location(
        "relay_watchman_loop_test", WATCHMAN_PATH)
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


class TestParseEventLines(unittest.TestCase):
    def test_valid_lines_parse(self):
        events, malformed = loop.parse_event_lines(
            '{"kind": "wake", "ts": 7}\n\n{"kind": "nudge"}\n')
        self.assertEqual(len(events), 2)
        self.assertEqual(malformed, 0)

    def test_junk_and_non_object_lines_counted(self):
        events, malformed = loop.parse_event_lines(
            "junk\n[1, 2]\n{\"kind\": \"wake\"}\n")
        self.assertEqual(len(events), 1)
        self.assertEqual(malformed, 2)

    def test_non_string_input_is_one_malformed(self):
        events, malformed = loop.parse_event_lines(None)
        self.assertEqual(events, [])
        self.assertEqual(malformed, 1)


class TestLoopCycle(unittest.TestCase):
    def test_successful_ring_and_quiet(self):
        records, new, diagnostics = loop.loop_cycle(
            {"alpha": (True, _stdout_for(NOW)), "beta": (True, "")},
            NOW, priors={}, journal=[])
        self.assertEqual(records["alpha"]["last_bell"], NOW)
        self.assertIsNone(records["beta"]["last_bell"])
        self.assertEqual(new, [])
        self.assertEqual(diagnostics["run_failures"], [])
        self.assertEqual(diagnostics["malformed_lines"], {})

    def test_failed_run_carries_prior_and_ages_dark(self):
        records, _, _ = loop.loop_cycle(
            {"alpha": (True, _stdout_for(NOW))}, NOW,
            priors={}, journal=[], restart_ok={"alpha": True})
        journal = []
        records, new, diagnostics = loop.loop_cycle(
            {"alpha": (False, "unused")}, NOW + STALE + 100,
            priors=records, journal=journal)
        self.assertEqual(diagnostics["run_failures"], ["alpha"])
        self.assertNotIn("restart_ok", records["alpha"])
        self.assertEqual(records["alpha"]["last_bell"], NOW)
        self.assertEqual(_kinds(new),
                         ["crew-dark", "watchman-restart", "escalation"])
        restart = [e for e in new
                   if e["kind"] == "watchman-restart"][0]
        self.assertIs(restart["restart_ok"], False)

    def test_open_episode_stays_silent_on_repeat_failure(self):
        records, _, _ = loop.loop_cycle(
            {"alpha": (True, _stdout_for(NOW))}, NOW,
            priors={}, journal=[])
        _, new, _ = loop.loop_cycle(
            {"alpha": (False, "")}, NOW + STALE + 100,
            priors=records, journal=[])
        journal = new
        _, new2, _ = loop.loop_cycle(
            {"alpha": (False, "")}, NOW + STALE + 200,
            priors=records, journal=journal)
        self.assertEqual(new2, [])

    def test_fresh_ring_recovers_after_failed_runs(self):
        records, _, _ = loop.loop_cycle(
            {"alpha": (True, _stdout_for(NOW))}, NOW,
            priors={}, journal=[])
        _, new, _ = loop.loop_cycle(
            {"alpha": (False, "")}, NOW + STALE + 100,
            priors=records, journal=[])
        journal = new
        _, new2, _ = loop.loop_cycle(
            {"alpha": (True, _stdout_for(NOW + STALE + 300))},
            NOW + STALE + 300, priors=records, journal=journal)
        self.assertEqual(_kinds(new2), ["watchman-recovered"])

    def test_malformed_stdout_contained_per_machine(self):
        dirty = _stdout_for(NOW) + "junk\n"
        records, new, diagnostics = loop.loop_cycle(
            {"alpha": (True, dirty), "beta": (True, "")},
            NOW, priors={}, journal=[])
        self.assertEqual(diagnostics["malformed_lines"], {"alpha": 1})
        self.assertEqual(records["alpha"]["last_bell"], NOW)
        self.assertEqual(new, [])

    def test_no_prior_failure_unjudged(self):
        records, new, diagnostics = loop.loop_cycle(
            {"gamma": (False, "")}, NOW, priors={}, journal=[])
        self.assertNotIn("gamma", records)
        self.assertEqual(new, [])
        self.assertEqual(diagnostics["run_failures"], ["gamma"])

    def test_failed_run_stdout_ignored(self):
        records, _, _ = loop.loop_cycle(
            {"alpha": (True, _stdout_for(NOW))}, NOW,
            priors={}, journal=[])
        records, new, _ = loop.loop_cycle(
            {"alpha": (False, _stdout_for(NOW + STALE + 100))},
            NOW + STALE + 100, priors=records, journal=[])
        self.assertEqual(records["alpha"]["last_bell"], NOW)
        self.assertEqual(_kinds(new),
                         ["crew-dark", "watchman-restart", "escalation"])

    def test_inputs_never_mutated(self):
        runs = {"alpha": (True, _stdout_for(NOW)),
                "beta": (False, "")}
        priors = {"beta": {"watchman_alive": True, "last_tick": NOW,
                           "last_bell": NOW, "last_wake": NOW}}
        journal = [{"kind": "crew-dark", "machine": "beta"}]
        runs_before = copy.deepcopy(runs)
        priors_before = copy.deepcopy(priors)
        journal_before = copy.deepcopy(journal)
        loop.loop_cycle(runs, NOW, priors=priors, journal=journal)
        self.assertEqual(runs, runs_before)
        self.assertEqual(priors, priors_before)
        self.assertEqual(journal, journal_before)


if __name__ == "__main__":
    unittest.main()
