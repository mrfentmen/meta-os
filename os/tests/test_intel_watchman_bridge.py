"""tests/test_intel_watchman_bridge.py -- OS-122 follow-up to Pax OS-118.

Pins intel/watchman_bridge.py: the fold from a real
relay_watchman tick to a watchman_watch record. Uses the real
tick() for the wake event; the bridge itself is fixture-only.
"""

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


def _load_watchman():
    spec = importlib.util.spec_from_file_location(
        "relay_watchman_test", WATCHMAN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WATCHMAN = _load_watchman()


class FoldTest(unittest.TestCase):
    def test_wake_advances_bell(self):
        jobs = [{"id": "j1", "status": "open", "addressed_to": "hana"}]
        agents = {"hana": {"nick": "hana", "heartbeat_at": NOW - 3600}}
        events, _ = WATCHMAN.tick(jobs, agents, set(), NOW)
        record = bridge.fold_tick(events, NOW)
        self.assertTrue(record["watchman_alive"])
        self.assertEqual(record["last_bell"], NOW)
        self.assertEqual(record["last_wake"], NOW)
        self.assertEqual(record["last_tick"], NOW)

    def test_nudge_is_not_a_bell(self):
        record = bridge.fold_tick(
            [{"kind": "nudge", "ts": NOW}], NOW)
        self.assertIsNone(record["last_bell"])

    def test_prior_bell_kept_without_new_wake(self):
        prior = {"watchman_alive": True, "last_bell": NOW - 60}
        record = bridge.fold_tick([], NOW, prior=prior)
        self.assertEqual(record["last_bell"], NOW - 60)

    def test_malformed_events_and_prior_ignored(self):
        record = bridge.fold_tick(["junk", {"kind": "wake"}],
                                  NOW, prior="junk")
        self.assertIsNone(record["last_bell"])
        self.assertTrue(record["watchman_alive"])

    def test_snapshot_skips_non_dict_records(self):
        snapshot = bridge.machines_snapshot(
            {"m1": {"watchman_alive": True}, "m2": "junk"})
        self.assertEqual(list(snapshot["machines"]), ["m1"])

    def test_bridge_record_reads_alive_then_dark(self):
        jobs = [{"id": "j1", "status": "open", "addressed_to": "hana"}]
        agents = {"hana": {"nick": "hana", "heartbeat_at": NOW - 3600}}
        events, _ = WATCHMAN.tick(jobs, agents, set(), NOW)
        record = bridge.fold_tick(events, NOW)
        snapshot = bridge.machines_snapshot({"m1": record})
        self.assertEqual(
            ww.current_states(snapshot, NOW)[0]["state"], "alive")
        self.assertEqual(ww.watchman_watch_tick(snapshot, [], NOW), [])
        aged = dict(record, restart_ok=True)
        late = NOW + thresholds.WATCHMAN_STALE_MINUTES * 60 + 60
        dark = ww.watchman_watch_tick(
            bridge.machines_snapshot({"m1": aged}), [], late)
        self.assertEqual([e["kind"] for e in dark],
                         ["crew-dark", "watchman-restart"])


if __name__ == "__main__":
    unittest.main()
