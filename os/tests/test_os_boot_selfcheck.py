"""OS-036: the watchdog boot self-check record pins.

The drill script itself (intel/drills/boot_selfcheck.py) is the
acceptance artifact — at relay-ready the watchdog runs each
detector once against the seeded fixture and writes a green
self-check record, and breaking a detector fails the boot
test. These tests pin the drill into the suite so a detector
or threshold change that breaks the self-check breaks the
suite too, and they pin the store record the boot checklist
reads (key shape + round-trip on the fake Redis).
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from helpers import RelayTestCase  # noqa: E402
from intel import boot_selfcheck  # noqa: E402
from intel import watchdog  # noqa: E402
from intel import store as istore  # noqa: E402
from intel.drills import boot_selfcheck as drill  # noqa: E402

T0 = 100000


class BootSelfcheckDrillTest(unittest.TestCase):
    def test_drill_passes_with_green_record(self):
        report = drill.run_drill()
        self.assertTrue(report["ok"])
        self.assertEqual(report["record"]["status"], "green")
        self.assertEqual(report["record"]["alert_count"], 10)
        self.assertEqual(len(report["log"]), 7)

    def test_seeded_fixture_ticks_to_exact_per_kind_counts(self):
        snapshot = boot_selfcheck.seeded_fixture(T0)
        alerts = watchdog.tick(snapshot, now=T0)
        kinds = sorted(a["kind"] for a in alerts)
        self.assertEqual(kinds, sorted(boot_selfcheck.EXPECTED))
        for kind, want in boot_selfcheck.EXPECTED.items():
            got = sum(1 for a in alerts if a["kind"] == kind)
            self.assertEqual(got, want, kind)

    def test_removed_detector_turns_record_red_naming_the_kind(self):
        snapshot = boot_selfcheck.seeded_fixture(T0)
        saved = list(watchdog.DETECTORS)
        try:
            watchdog.DETECTORS = [d for d in saved
                                  if d is not watchdog.detect_dead_dep]
            record = boot_selfcheck.run_self_check(snapshot, now=T0)
        finally:
            watchdog.DETECTORS = saved
        self.assertEqual(record["status"], "red")
        failing = [d["kind"] for d in record["detectors"]
                   if not d["ok"]]
        self.assertEqual(failing, ["dead-dep"])

    def test_crashing_detector_turns_record_red_not_silent(self):
        snapshot = boot_selfcheck.seeded_fixture(T0)
        saved = list(watchdog.DETECTORS)

        def _boom(snapshot, now):
            raise RuntimeError("detector exploded")

        try:
            watchdog.DETECTORS = [_boom if d is watchdog.detect_lease_risk
                                  else d for d in saved]
            record = boot_selfcheck.run_self_check(snapshot, now=T0)
        finally:
            watchdog.DETECTORS = saved
        self.assertEqual(record["status"], "red")
        failing = [d["kind"] for d in record["detectors"]
                   if not d["ok"]]
        self.assertEqual(failing, ["lease-risk"])

    def test_unexpected_kind_turns_record_red(self):
        snapshot = boot_selfcheck.seeded_fixture(T0)
        record = boot_selfcheck.run_self_check(
            snapshot, now=T0,
            expected={"presence-stall": 1})
        self.assertEqual(record["status"], "red")


class SelfcheckStoreTest(RelayTestCase):
    def test_key_shape_and_round_trip(self):
        self.assertEqual(istore.selfcheck_key("main", T0),
                         "muse-bus:intel:wd:selfcheck:main:100000")
        self.assertEqual(istore.selfcheck_key("", T0),
                         "muse-bus:intel:wd:selfcheck:main:100000")
        rec = boot_selfcheck.run_self_check(
            boot_selfcheck.seeded_fixture(T0), now=T0)
        key = istore.put_selfcheck("main", T0, rec)
        self.assertEqual(key, "muse-bus:intel:wd:selfcheck:main:100000")
        self.assertEqual(istore.get_selfcheck("main", T0), rec)
        self.assertIsNone(istore.get_selfcheck("main", T0 + 1))


if __name__ == "__main__":
    unittest.main()
