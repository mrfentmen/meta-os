#!/usr/bin/env python3
"""tests/test_intel_drill_tournament.py -- INT-021, pinned.

The tournament runner in intel/drills/tournament.py is the
acceptance artifact; these tests pin it inside the unit
harness so a drill regression or a tournament-order change
fails the suite, not just the standalone run. The drills are
fixture-only (no network, no Redis, no bus posts), and the
tournament runs with write_log=False here, so the suite run
leaves no state behind.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel.drills import tournament  # noqa: E402


class DrillTournamentTest(unittest.TestCase):
    def test_tournament_passes_in_order_under_limit(self):
        result = tournament.run_tournament(write_log=False)
        self.assertTrue(result["ok"], result["transcript"])
        names = [d["name"] for d in result["drills"]]
        self.assertEqual(names, ["kill_worker", "collision",
                                 "dead_dep"])
        tasks = [d["task"] for d in result["drills"]]
        self.assertEqual(tasks, ["WDG-020", "WDG-021", "WDG-022"])
        for drill in result["drills"]:
            self.assertEqual(drill["exit_code"], 0, drill)
            self.assertIsNotNone(drill["pass_line"], drill)
        self.assertLess(result["total_seconds"], 360.0)
        self.assertIn("INT-021: PASS", result["transcript"])

    def test_tournament_twice_isolated(self):
        first = tournament.run_tournament(write_log=False)
        second = tournament.run_tournament(write_log=False)
        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(
            [d["name"] for d in first["drills"]],
            [d["name"] for d in second["drills"]])
        self.assertEqual(first["transcript"].split("--")[0],
                         second["transcript"].split("--")[0])


if __name__ == "__main__":
    unittest.main()
