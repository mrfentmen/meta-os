"""Judge normalisation tests (CB2-048..049). Offline; pure."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew_common  # noqa: E402
import judge  # noqa: E402


def rule(first, review):
    return judge.combine("vigiles", first, review, True,
                         crew_common.is_flagged_category)


class NormalisationTests(unittest.TestCase):
    def test_mixed_case_and_whitespace_categories_normalise(self):
        verdict, _ = rule(" Person Down ", "  PERSON DOWN  ")
        self.assertEqual(verdict, "confirmed")

    def test_whitespace_baseline_still_clears(self):
        verdict, _ = rule("person down", " Normal Activity ")
        self.assertEqual(verdict, "cleared")

    def test_identical_duplicate_readings_do_not_double_count(self):
        verdict, reasons = rule("person down", "person down")
        self.assertEqual(verdict, "confirmed")
        self.assertEqual(len(reasons), 1)
        self.assertEqual(reasons[0].count("agree"), 1)


if __name__ == "__main__":
    unittest.main()
