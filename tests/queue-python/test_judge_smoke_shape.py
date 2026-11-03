"""Staged flame reading test (CB2-046). Offline; pure judge."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew_common  # noqa: E402
import judge  # noqa: E402
import orchestrator  # noqa: E402


class SmokeShapeTests(unittest.TestCase):
    def test_visible_flame_pair_confirms_and_stays_red(self):
        verdict, reasons = judge.combine(
            "ignis", "visible flame", "visible flame", True,
            crew_common.is_flagged_category)
        self.assertEqual(verdict, "confirmed")
        self.assertIn("visible flame", " ".join(reasons))
        self.assertEqual(judge.service_route("ignis")["path"], "/fire")
        self.assertEqual(orchestrator.tier_for("ignis", "visible flame"),
                         "red")


if __name__ == "__main__":
    unittest.main()
