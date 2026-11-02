"""CB2-176/177: blind reproduction agreement and disagreement."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

import verify  # noqa: E402


class TestBlindCompare(unittest.TestCase):
    def test_identical_runs_agree_and_record(self):
        result = verify.compare_runs(
            {"numbers": [0.818, 1.25, 2.0]},
            {"numbers": [0.818, 1.25, 2.0]},
        )
        self.assertTrue(result["agree"])
        self.assertEqual(result["verdict"], verify.AGREE)
        self.assertEqual(result["rows"], 3)
        self.assertIn("compared_at", result)
        self.assertIn("original_hash", result)
        self.assertIn("re_run_hash", result)

    def test_different_numbers_disagree(self):
        result = verify.compare_runs(
            {"numbers": [0.818, 1.25]},
            {"numbers": [0.818, 1.90]},
            tolerance=1e-6,
        )
        self.assertFalse(result["agree"])
        self.assertEqual(result["verdict"], verify.DISAGREE)
        self.assertIn("exceeds", result["diff"])


if __name__ == "__main__":
    unittest.main()
