"""CB2-178/179: tolerance boundary and unequal row counts."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

import verify  # noqa: E402


class TestTolerance(unittest.TestCase):
    def test_difference_exactly_at_tolerance_passes(self):
        result = verify.compare_runs([1.0], [1.5], tolerance=0.5)
        self.assertTrue(result["agree"])
        self.assertEqual(result["max_difference"], 0.5)

    def test_epsilon_beyond_tolerance_fails(self):
        result = verify.compare_runs([1.0], [1.5000001], tolerance=0.5)
        self.assertFalse(result["agree"])
        self.assertGreater(result["max_difference"], 0.5)

    def test_different_row_counts_refused(self):
        with self.assertRaisesRegex(ValueError, "row counts differ"):
            verify.compare_runs([1.0, 2.0], [1.0], tolerance=0.5)


if __name__ == "__main__":
    unittest.main()
