"""Judge region edge tests (CB2-037..039). Offline; pure validation."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew_common  # noqa: E402
import judge  # noqa: E402


def reading(region):
    return {"product": "vigiles",
            "assessment": {"category": "person down",
                           "observations": [{"category": "person down",
                                             "region": region}]}}


class RegionEdgeTests(unittest.TestCase):
    def test_null_region_is_valid(self):
        self.assertIsNone(judge.validate_reading(reading(None)))

    def test_full_scale_region_is_valid(self):
        self.assertIsNone(judge.validate_reading(reading(
            {"x": 0, "y": 0, "w": 1000, "h": 1000})))

    def test_out_of_scale_region_is_rejected(self):
        error = judge.validate_reading(reading(
            {"x": 0, "y": 0, "w": 1001, "h": 1000}))
        self.assertIn("0-1000", error)

    def test_inverted_or_negative_region_is_rejected(self):
        for region in ({"x": 900, "y": 0, "w": -1, "h": 10},
                       {"x": 0, "y": 900, "w": 10, "h": 1001}):
            self.assertIsNotNone(judge.validate_reading(reading(region)))

    def test_overlapping_boxes_do_not_create_two_confirmations(self):
        verdict, reasons = judge.combine(
            "vigiles", "person down", "person down", True,
            crew_common.is_flagged_category)
        self.assertEqual(verdict, "confirmed")
        self.assertEqual(len(reasons), 1)


if __name__ == "__main__":
    unittest.main()
