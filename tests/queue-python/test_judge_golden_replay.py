"""Golden judge replay tests (CB2-040..041). Offline; table-driven."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew_common  # noqa: E402
import judge  # noqa: E402


def rule(division, first, review):
    return judge.combine(division, first, review, True,
                         crew_common.is_flagged_category)


EMERGENCIES = [
    ("vigiles", "person down", "person down"),
    ("vigiles", "physical contact", "possible altercation"),
    ("ignis", "visible flame", "visible flame"),
    ("ignis", "visible smoke", "dark smoke"),
    ("medicus", "person on ground", "person motionless"),
]

NON_EMERGENCIES = [
    ("vigiles", "person down", "normal activity"),
    ("vigiles", "person down", "indeterminate"),
    ("ignis", "visible flame", "no hazard visible"),
    ("ignis", "visible flame", "steam or fog"),
    ("ignis", "visible flame", "flame-like lighting"),
    ("ignis", "visible flame", "indeterminate"),
    ("medicus", "person on ground", "normal activity"),
    ("medicus", "person on ground", "indeterminate"),
]


class GoldenReplayTests(unittest.TestCase):
    def test_five_batch6_emergency_pairs_confirm(self):
        for division, first, review in EMERGENCIES:
            verdict, _ = rule(division, first, review)
            self.assertEqual(verdict, "confirmed",
                             (division, first, review))

    def test_eight_batch6_non_emergency_pairs_never_confirm(self):
        for division, first, review in NON_EMERGENCIES:
            verdict, _ = rule(division, first, review)
            self.assertNotEqual(verdict, "confirmed",
                                (division, first, review))


if __name__ == "__main__":
    unittest.main()
