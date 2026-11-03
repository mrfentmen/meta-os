"""Judge lookalike edge tests (CB2-029..030). Offline."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew_common  # noqa: E402
import judge  # noqa: E402
import orchestrator  # noqa: E402


def rule(division, first, review):
    return judge.combine(division, first, review, True,
                         crew_common.is_flagged_category)


class LookalikeTests(unittest.TestCase):
    def test_bench_sleeper_shape_clears(self):
        # A person sleeping on a bench is represented by the medicus
        # baseline in the product taxonomy; the judge clears it.
        verdict, reasons = rule("medicus", "person on ground",
                                "normal activity")
        self.assertEqual(verdict, "cleared")
        self.assertIn("look-alike", reasons[0])

    def test_ignis_steam_lookalike_clears(self):
        verdict, _ = rule("ignis", "visible flame", "steam or fog")
        self.assertEqual(verdict, "cleared")

    def test_crowd_gathered_is_flagged_but_never_red_tier(self):
        verdict, _ = rule("vigiles", "person down", "crowd gathered")
        self.assertEqual(verdict, "confirmed")
        # Real table: "crowd gathered" is not in the display tiers and
        # has no priority entry, so it is ungated (None), never red.
        self.assertIsNone(orchestrator.tier_for("vigiles",
                                                "crowd gathered"))


if __name__ == "__main__":
    unittest.main()
