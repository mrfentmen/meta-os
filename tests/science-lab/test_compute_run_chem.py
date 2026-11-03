"""Compute run_chem rows tests (CB2-155..156). Pure fixtures."""
import math
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import compute  # noqa: E402

ROWS = [
    {"actual": 1.0, "predicted": 1.1},
    {"actual": 2.0, "predicted": 1.9},
    {"actual": 3.0, "predicted": 3.2},
    {"actual": 4.0, "predicted": 3.8},
    {"actual": 5.0, "predicted": 5.0},
]


class RunChemRowsTests(unittest.TestCase):
    def test_five_row_fixture_reproduces_exact_rmse(self):
        record = compute.run_chem({
            "rows": ROWS, "target_column": "actual",
            "prediction_column": "predicted"})
        expected = math.sqrt((0.1 ** 2 + 0.1 ** 2 + 0.2 ** 2
                              + 0.2 ** 2) / 5)
        self.assertEqual(record["parameters"]["rows_used"], 5)
        self.assertAlmostEqual(record["value"], expected, places=6)

    def test_missing_target_column_is_named(self):
        with self.assertRaisesRegex(ValueError, "target column"):
            compute.run_chem({
                "rows": ROWS, "target_column": "missing",
                "prediction_column": "predicted"})


if __name__ == "__main__":
    unittest.main()
