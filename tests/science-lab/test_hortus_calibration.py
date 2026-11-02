"""CB2-220/221: calibration fixture count and missing-score reporting."""
import json
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

from hortus.calibration import check_scorer  # noqa: E402


class TestCalibrationLoading(unittest.TestCase):
    def test_fixture_loads_documented_count(self):
        parts = check_scorer.load_parts()
        self.assertEqual(len(parts), 14)
        subsets = {}
        for part in parts:
            subsets[part["subset"]] = subsets.get(part["subset"], 0) + 1
        self.assertEqual(subsets, {"calibration": 10, "validation": 4})

    def test_missing_score_is_skipped_and_counted(self):
        fixture = {"parts": [
            {"part_id": "OK-1", "subset": "calibration",
             "measured_thermal_resistance_c_per_w": 1.0},
            {"part_id": "BAD-1", "subset": "validation"},
        ]}
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "parts.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(fixture, fh)
            report = check_scorer.load_parts_report(path)
        self.assertEqual(report["count"], 1)
        self.assertEqual(report["skipped_count"], 1)
        self.assertEqual(report["skipped"][0]["part_id"], "BAD-1")
        self.assertIn("missing", report["skipped"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
