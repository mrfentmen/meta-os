"""Compute summary-stat tests (CB2-171..172). Pure."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import compute  # noqa: E402


class StatsTests(unittest.TestCase):
    def test_mean_and_count_match_hand_computation(self):
        stats = compute.summary_stats([1, 2, 3, 4])
        self.assertEqual(stats["count"], 4)
        self.assertEqual(stats["mean"], 2.5)

    def test_constant_series_has_zero_variance_without_crashing(self):
        stats = compute.summary_stats([7, 7, 7])
        self.assertEqual(stats["variance"], 0.0)
        self.assertEqual(stats["stddev"], 0.0)


if __name__ == "__main__":
    unittest.main()
