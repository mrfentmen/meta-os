"""Prediction extraction tests (CB2-134..135). Pure."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import reasoning  # noqa: E402


class PredictionTests(unittest.TestCase):
    def test_directional_prediction_sets_direction(self):
        result = reasoning.extract_prediction(
            "`Y` increases by 2 units under condition X")
        self.assertEqual(result["direction"], "increase")
        self.assertTrue(result["measurable"])
        self.assertFalse(result["needs_refinement"])

    def test_vague_prediction_needs_refinement(self):
        result = reasoning.extract_prediction("Something may change somehow")
        self.assertIsNone(result["direction"])
        self.assertTrue(result["needs_refinement"])


if __name__ == "__main__":
    unittest.main()
