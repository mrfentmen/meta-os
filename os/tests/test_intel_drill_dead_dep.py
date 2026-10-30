"""WDG-022: the dead-dep drill passes unattended on fixtures.

The drill script itself (intel/drills/dead_dep.py) is the
acceptance artifact — A is posted, B is posted depending on
A, A is blocked with a reason, and the watchdog raises
exactly one critical dead-dep alert naming both jobs and
A's reason verbatim, keeps firing while A stays blocked,
and stops once A is unblocked. These tests pin the drill
into the suite so a detector change that breaks the demo
scenario breaks the suite too.
"""

import io
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel.drills import dead_dep  # noqa: E402


class DeadDepDrillTest(unittest.TestCase):
    def test_drill_passes_and_reports_the_dead_dep_alert(self):
        report = dead_dep.run_drill()
        alert = report["alert"]
        self.assertEqual(alert["kind"], "dead-dep")
        self.assertEqual(alert["severity"], "critical")
        self.assertEqual(alert["job"], "2")
        self.assertEqual(alert["dep"], "1")
        self.assertEqual(alert["blocking_reason"],
                         "needs Pax sign-off on the key shape")
        self.assertEqual(alert["dedupe_key"], "dead-dep:2:1")
        self.assertEqual(len(report["log"]), 4)

    def test_cli_main_exits_zero_and_prints_pass(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = dead_dep.main([])
        self.assertEqual(code, 0)
        self.assertIn("dead-dep drill: PASS", out.getvalue())


if __name__ == "__main__":
    unittest.main()
