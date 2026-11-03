"""Compute RMSE tests (CB2-151..154). Pure."""
import math
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import compute  # noqa: E402


class RmseTests(unittest.TestCase):
    def test_identical_series_have_zero_error(self):
        self.assertEqual(compute.rmse([1, 2, 3], [1, 2, 3]), 0.0)

    def test_known_two_point_value(self):
        self.assertAlmostEqual(
            compute.rmse([1, 2], [2, 4]), math.sqrt(2.5), places=6)

    def test_different_lengths_are_refused(self):
        with self.assertRaisesRegex(ValueError, "equal-length"):
            compute.rmse([1, 2], [1])

    def test_empty_series_are_refused(self):
        with self.assertRaisesRegex(ValueError, "non-empty"):
            compute.rmse([], [])


if __name__ == "__main__":
    unittest.main()
