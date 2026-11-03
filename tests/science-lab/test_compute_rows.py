"""Compute row parsing tests (CB2-157..158). Pure."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import compute  # noqa: E402


class RowTests(unittest.TestCase):
    def test_non_numeric_cell_reports_its_row_index(self):
        result = compute.parse_numeric_rows(
            [{"x": "1"}, {"x": "nope"}, {"x": "3"}], "x")
        self.assertEqual(result["bad_rows"], [1])
        self.assertEqual([row["value"] for row in result["rows"]],
                         [1.0, 3.0])

    def test_row_order_is_stable_through_parse_and_predict(self):
        rows = [{"x": value} for value in (5, 1, 4, 2, 3)]
        parsed = compute.parse_numeric_rows(rows, "x")
        self.assertEqual([row["index"] for row in parsed["rows"]],
                         [0, 1, 2, 3, 4])
        self.assertEqual([row["value"] for row in parsed["rows"]],
                         [5.0, 1.0, 4.0, 2.0, 3.0])


if __name__ == "__main__":
    unittest.main()
