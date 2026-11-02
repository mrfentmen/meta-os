"""Judge combine edge tests (CB2-026..028). Offline; pure functions."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew_common  # noqa: E402
import judge  # noqa: E402


def rule(division, first, review, ok=True):
    return judge.combine(division, first, review, ok,
                         crew_common.is_flagged_category)


class CombineEdgeTests(unittest.TestCase):
    def test_agreeing_emergency_is_confirmed_with_a_reason(self):
        verdict, reasons = rule("vigiles", "person down", "person down")
        self.assertEqual(verdict, "confirmed")
        self.assertEqual(len(reasons), 1)
        self.assertIn("agree", reasons[0])

    def test_disagreeing_flagged_readings_confirm_and_name_both(self):
        verdict, reasons = rule("vigiles", "person down",
                                "possible altercation")
        self.assertEqual(verdict, "confirmed")
        joined = " ".join(reasons)
        self.assertIn("person down", joined)
        self.assertIn("possible altercation", joined)

    def test_missing_review_reading_is_inconclusive(self):
        for review, ok in ((None, True), ("person down", False)):
            verdict, reasons = rule("vigiles", "person down", review, ok)
            self.assertEqual(verdict, "inconclusive")
            self.assertIn("missing reading", reasons[0])

    def test_missing_patrol_reading_is_inconclusive(self):
        verdict, reasons = rule("vigiles", None, "person down")
        self.assertEqual(verdict, "inconclusive")
        self.assertIn("patrol reading", reasons[0])


if __name__ == "__main__":
    unittest.main()
