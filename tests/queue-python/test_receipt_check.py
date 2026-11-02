"""Tests for tools/receipt_check.py (CB2-436..438)."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import receipt_check  # noqa: E402

SPARK = {
    "model": "muse-spark-1.3",
    "surface": "chat",
    "latency_ms": 6376,
    "est_cost_usd": 0.00565875,
}
WONDER = {
    "model": "muse-wonder-1.0",
    "surface": "chat",
    "latency_ms": 1164,
    "est_cost_usd": None,
}


def line(record):
    return json.dumps(record)


class ReceiptCheck(unittest.TestCase):
    def test_valid_file_reports_counts_only(self):
        result = receipt_check.check(line(SPARK) + "\n" + line(WONDER) + "\n")
        self.assertEqual(result["lines"], 2)
        self.assertEqual(result["valid"], 2)
        self.assertEqual(result["errors"], [])

    def test_negative_latency_is_flagged_with_its_line_number(self):
        result = receipt_check.check(line(SPARK) + "\n" + line(dict(WONDER, latency_ms=-5)) + "\n")
        self.assertEqual(len(result["errors"]), 1)
        self.assertTrue(result["errors"][0].startswith("line 2:"), result["errors"])
        self.assertIn("latency_ms", result["errors"][0])

    def test_spark_requires_an_estimate(self):
        broken = dict(SPARK)
        del broken["est_cost_usd"]
        result = receipt_check.check(line(broken) + "\n")
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("Spark", result["errors"][0])

    def test_non_spark_must_not_carry_an_estimate(self):
        result = receipt_check.check(line(dict(WONDER, est_cost_usd=0.2)) + "\n")
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("non-Spark", result["errors"][0])

    def test_malformed_line_is_reported_by_number(self):
        result = receipt_check.check(line(SPARK) + "\n{oops\n")
        self.assertTrue(result["errors"][0].startswith("line 2:"), result["errors"])


if __name__ == "__main__":
    unittest.main()
