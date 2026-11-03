"""Judge never-red property test (CB2-047). Fixed seed; offline."""
import os
import random
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew_common  # noqa: E402
import judge  # noqa: E402
import orchestrator  # noqa: E402


class NeverRedPropertyTests(unittest.TestCase):
    def test_fifty_generated_pairs_never_emit_a_red_tier(self):
        rng = random.Random(7)
        baselines = crew_common.baseline_categories()
        counts = {"confirmed": 0, "cleared": 0, "inconclusive": 0}
        for _ in range(50):
            division = rng.choice(("vigiles", "ignis", "medicus"))
            allowed = list(baselines[division]) + \
                list(orchestrator.DISPLAY_TIERS[division]["yellow"])
            first = rng.choice(allowed)
            review = rng.choice(allowed)
            verdict, _ = judge.combine(
                division, first, review, True,
                crew_common.is_flagged_category)
            counts[verdict] += 1
            self.assertNotEqual(orchestrator.tier_for(division, review),
                                "red", (division, first, review))
        self.assertEqual(sum(counts.values()), 50)


if __name__ == "__main__":
    unittest.main()
