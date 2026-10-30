"""tests/test_intel_watchman_bridge_tick.py -- OS-122 follow-up.

Pins intel/watchman_bridge.py watchman_tick(): the one-call
service-loop entry point that folds every machine's
relay_watchman events into watchman_watch records and judges
them. Uses the real relay_watchman tick() for wake events;
the bridge itself is fixture-only.
"""

import copy
import importlib.util
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

from intel import thresholds  # noqa: E402
from intel import watchman_bridge as bridge  # noqa: E402
from intel import watchman_watch as ww  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHMAN_PATH = os.path.join(ROOT, "os", "watchman",
                             "relay_watchman.py")
NOW = 1000000
STALE = thresholds.WATCHMAN_STALE_MINUTES * 60


def _load_watchman():
    spec = importlib.util.spec_from_file_location(
        "relay_watchman_bridge_tick_test", WATCHMAN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WATCHMAN = _load_watchman()
JOBS = [{"id": "j1", "status": "open", "addressed_to": "hana"}]
AGENTS = {"hana": {"nick": "hana", "heartbeat_at": NOW - 3600}}


def _ring(at):
    events, _ = WATCHMAN.tick(JOBS, AGENTS, set(), at)
    return events


def _kinds(journal):
    return [entry["kind"] for entry in journal]


class WatchmanTickTest(unittest.TestCase):
    def test_ring_alive_quiet_unknown_no_journal(self):
        records, journal = bridge.watchman_tick(
            {"m1": _ring(NOW), "m2": []}, NOW)
        states = {s["machine"]: s["state"] for s in
                  ww.current_states(
                      bridge.machines_snapshot(records), NOW)}
        self.assertEqual(records["m1"]["last_bell"], NOW)
        self.assertIsNone(records["m2"]["last_bell"])
        self.assertEqual(states, {"m1": "alive", "m2": "unknown"})
        self.assertEqual(journal, [])

    def test_silence_journals_dark_and_restart_only_for_dark(self):
        records, _ = bridge.watchman_tick(
            {"m1": _ring(NOW), "m2": []}, NOW)
        late = NOW + STALE + 60
        _, dark = bridge.watchman_tick(
            {"m1": [], "m2": []}, late, priors=records,
            journal=[], restart_ok={"m1": True})
        self.assertEqual(_kinds(dark),
                         ["crew-dark", "watchman-restart"])
        self.assertTrue(all(e["machine"] == "m1" for e in dark))
        self.assertTrue(dark[1]["restart_ok"])

    def test_no_restart_fact_escalates_once(self):
        records, _ = bridge.watchman_tick(
            {"m1": _ring(NOW)}, NOW)
        late = NOW + STALE + 60
        _, dark = bridge.watchman_tick(
            {"m1": []}, late, priors=records, journal=[])
        self.assertEqual(_kinds(dark),
                         ["crew-dark", "watchman-restart",
                          "escalation"])

    def test_recovery_then_second_episode_realerts(self):
        records, _ = bridge.watchman_tick(
            {"m1": _ring(NOW)}, NOW)
        late = NOW + STALE + 60
        dark_records, dark = bridge.watchman_tick(
            {"m1": []}, late, priors=records, journal=[],
            restart_ok={"m1": True})
        journal = dark
        recovered_records, recovered = bridge.watchman_tick(
            {"m1": _ring(late + 60)}, late + 60,
            priors=dark_records, journal=journal)
        self.assertEqual(_kinds(recovered), ["watchman-recovered"])
        journal = journal + recovered
        later = late + 2 * STALE + 120
        dark2_records, dark2 = bridge.watchman_tick(
            {"m1": []}, later, priors=recovered_records,
            journal=journal, restart_ok={"m1": False})
        # The recovered record's bell (late+60) ages honestly
        # into a new episode at `later`, since the journal
        # closes the first episode with the recovered record.
        self.assertEqual(_kinds(dark2),
                         ["crew-dark", "watchman-restart",
                          "escalation"])
        _, again = bridge.watchman_tick(
            {"m1": []}, later + 60, priors=dark2_records,
            journal=journal + dark2)
        self.assertEqual(again, [])

    def test_malformed_input_contained_per_machine(self):
        records, journal = bridge.watchman_tick("junk", NOW)
        self.assertEqual(records, {})
        self.assertEqual(journal, [])
        records, journal = bridge.watchman_tick(
            {"m1": "junk", "m2": []}, NOW)
        states = {s["machine"]: s["state"] for s in
                  ww.current_states(
                      bridge.machines_snapshot(records), NOW)}
        self.assertEqual(states, {"m1": "unknown", "m2": "unknown"})
        self.assertEqual(journal, [])

    def test_absent_machine_unjudged(self):
        records, journal = bridge.watchman_tick({"m2": []}, NOW)
        self.assertEqual(list(records), ["m2"])
        self.assertEqual(journal, [])

    def test_inputs_never_mutated(self):
        events = {"m1": _ring(NOW)}
        priors = {"m1": {"watchman_alive": True,
                          "last_bell": NOW - 60}}
        journal = [{"kind": "crew-dark", "machine": "m1"}]
        events_copy = copy.deepcopy(events)
        priors_copy = copy.deepcopy(priors)
        journal_copy = copy.deepcopy(journal)
        bridge.watchman_tick(events, NOW, priors=priors,
                             journal=journal)
        self.assertEqual(events, events_copy)
        self.assertEqual(priors, priors_copy)
        self.assertEqual(journal, journal_copy)


if __name__ == "__main__":
    unittest.main()
