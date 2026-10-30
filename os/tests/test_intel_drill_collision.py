"""WDG-021: the collision drill passes unattended on fixtures.

The drill script itself (intel/drills/collision.py) is the
acceptance artifact — two fake workers claim overlapping-files
jobs, the watchdog raises exactly one critical file-collision
alert naming both jobs and the shared path before either
finishes, and the alert stops once one job finishes. These
tests pin the drill into the suite so a detector change that
breaks the demo scenario breaks the suite too.
"""

import io
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel.drills import collision  # noqa: E402


class CollisionDrillTest(unittest.TestCase):
    def test_drill_passes_and_reports_the_collision_alert(self):
        report = collision.run_drill()
        alert = report["alert"]
        self.assertEqual(alert["kind"], "file-collision")
        self.assertEqual(alert["severity"], "critical")
        self.assertEqual(alert["job"], "1")
        self.assertEqual(alert["other_job"], "2")
        self.assertEqual(alert["shared_path"], "intel/store.py")
        self.assertEqual(alert["dedupe_key"],
                         "file-collision:1:2:intel/store.py")
        self.assertEqual(len(report["log"]), 4)

    def test_cli_main_exits_zero_and_prints_pass(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = collision.main([])
        self.assertEqual(code, 0)
        self.assertIn("collision drill: PASS", out.getvalue())


if __name__ == "__main__":
    unittest.main()
