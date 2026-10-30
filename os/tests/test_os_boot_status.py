"""OS-041: the watchdog status line for the boot screen pins.

The drill script itself (intel/drills/boot_status.py) is the
acceptance artifact — one line of live health (units up,
workers alive, last alert) for Rowan's boot checklist, going
stale within 30s of a unit being killed. These tests pin the
drill into the suite so a store or threshold change that
breaks the line breaks the suite too, and they pin the
store record the boot checklist reads (key shape + round-trip
on the fake Redis).
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from helpers import RelayTestCase  # noqa: E402
from intel import store as istore  # noqa: E402
from intel.drills import boot_status as drill  # noqa: E402

T0 = 100000

UNITS = [{"unit": "relay-bus", "state": "active"},
         {"unit": "relay-jobs", "state": "active"},
         {"unit": "relay-watchdog", "state": "active"}]


class BootStatusDrillTest(unittest.TestCase):
    def test_drill_passes_with_green_record(self):
        report = drill.run_drill()
        self.assertTrue(report["ok"])
        self.assertEqual(report["record"]["line"],
                         "Boot: 3/3 units up, 2 workers alive"
                         " — no open alerts")
        self.assertEqual(len(report["log"]), 8)


class BootStatusLineTest(unittest.TestCase):
    def test_down_unit_named_and_counted(self):
        units = [dict(u, state="failed") if u["unit"] == "relay-jobs"
                 else dict(u) for u in UNITS]
        record = istore.build_boot_status(units, ["milo"], [], ts=T0)
        self.assertEqual(record["units_up"], 2)
        self.assertEqual(record["units_down"], ["relay-jobs"])
        self.assertIn("down: relay-jobs", record["line"])

    def test_last_alert_is_latest_open_not_highest(self):
        alerts = [{"id": "a-crit", "severity": "critical",
                   "created_at": T0 - 50, "resolved_at": None},
                  {"id": "a-warn", "severity": "warning",
                   "created_at": T0 - 5, "resolved_at": None}]
        record = istore.build_boot_status(UNITS, [], alerts, ts=T0)
        self.assertEqual(record["last_alert"]["id"], "a-warn")
        self.assertIn("last alert: a-warn (warning)", record["line"])

    def test_non_dict_entries_skipped_not_counted(self):
        record = istore.build_boot_status(
            [None, {"unit": "relay-bus", "state": "active"}],
            ["milo", None, "milo"], ["junk"], ts=T0)
        self.assertEqual(record["units_total"], 1)
        self.assertEqual(record["workers_count"], 1)
        self.assertIsNone(record["last_alert"])

    def test_stale_boundary_30_fresh_31_stale(self):
        record = istore.build_boot_status(UNITS, [], [], ts=T0)
        self.assertFalse(istore.boot_status_is_stale(record, now=T0 + 30))
        self.assertTrue(istore.boot_status_is_stale(record, now=T0 + 31))
        self.assertTrue(istore.boot_status_is_stale({}, now=T0))
        self.assertTrue(istore.boot_status_is_stale(None, now=T0))


class BootStatusStoreTest(RelayTestCase):
    def test_key_shape_and_round_trip(self):
        self.assertEqual(istore.boot_status_key("main", T0),
                         "muse-bus:intel:wd:bootstatus:main:100000")
        self.assertEqual(istore.boot_status_key("", T0),
                         "muse-bus:intel:wd:bootstatus:main:100000")
        rec = istore.build_boot_status(UNITS, ["milo"], [], ts=T0)
        key = istore.put_boot_status("main", T0, rec)
        self.assertEqual(key, "muse-bus:intel:wd:bootstatus:main:100000")
        self.assertEqual(istore.get_boot_status("main", T0), rec)
        self.assertIsNone(istore.get_boot_status("main", T0 + 1))


if __name__ == "__main__":
    unittest.main()
