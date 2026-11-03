"""Judge time and product tests (CB2-042..043). Offline; pure."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import judge  # noqa: E402


class TimeEdgeTests(unittest.TestCase):
    def test_earlier_timestamp_wins_even_when_listed_second(self):
        first = {"timestamp": "2026-11-02T10:05:00Z"}
        review = {"timestamp": "2026-11-02T10:00:00Z"}
        self.assertEqual(judge.incident_start(first, review),
                         "2026-11-02T10:00:00Z")

    def test_offset_timestamps_compare_as_instants(self):
        first = {"timestamp": "2026-11-02T12:00:00+02:00"}
        review = {"timestamp": "2026-11-02T09:30:00Z"}
        self.assertEqual(judge.incident_start(first, review),
                         "2026-11-02T09:30:00Z")

    def test_no_timestamp_returns_none(self):
        self.assertIsNone(judge.incident_start({}, {"timestamp": None}))


class ProductRefusalTests(unittest.TestCase):
    def test_unknown_product_is_refused(self):
        error = judge.validate_reading({"product": "custodes"})
        self.assertIn("unknown product", error)

    def test_prompt_refuses_an_unknown_product(self):
        with self.assertRaises(ValueError):
            judge.build_judge_prompt(
                "vigiles", {"product": "custodes",
                            "assessment": {"category": "person down"}},
                {"product": "vigiles",
                 "assessment": {"category": "person down"}})


if __name__ == "__main__":
    unittest.main()
