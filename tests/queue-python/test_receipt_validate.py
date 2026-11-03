"""Tests for server/queue/receipt_validate.py (CB2-359..361)."""

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "receipt_validate", ROOT / "server" / "queue" / "receipt_validate.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

SPARK = {
    "ts": "2026-11-02T14:30:21+00:00",
    "kind": "chat:muse-spark-1.3",
    "model": "muse-spark-1.3",
    "surface": "chat",
    "latency_ms": 6376,
    "est_cost_usd": 0.00565875,
}
WONDER = {
    "ts": "2026-11-02T14:26:20+00:00",
    "kind": "chat:muse-wonder-1.0",
    "model": "muse-wonder-1.0",
    "surface": "chat",
    "latency_ms": 1164,
    "est_cost_usd": None,
}


def line(record):
    return json.dumps(record)


class ReceiptValidate(unittest.TestCase):
    def test_valid_spark_and_wonder_lines_pass(self):
        result = mod.validate_text(line(SPARK) + "\n" + line(WONDER) + "\n")
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["lines"], 2)

    def test_spark_missing_estimate_fails(self):
        broken = dict(SPARK)
        del broken["est_cost_usd"]
        errors = mod.validate_line(line(broken), 1)
        self.assertTrue(any("Spark" in e and "est_cost_usd" in e for e in errors), errors)

    def test_non_spark_with_dollar_figure_fails(self):
        broken = dict(WONDER, est_cost_usd=0.25)
        errors = mod.validate_line(line(broken), 3)
        self.assertTrue(any("non-Spark" in e for e in errors), errors)

    def test_malformed_json_reports_its_line_number(self):
        result = mod.validate_text(line(SPARK) + "\nnot json\n")
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["errors"]), 1)
        self.assertTrue(result["errors"][0].startswith("line 2:"), result["errors"])

    def test_negative_latency_is_flagged(self):
        errors = mod.validate_line(line(dict(SPARK, latency_ms=-1)), 5)
        self.assertTrue(any("latency_ms" in e for e in errors), errors)

    def test_endpoint_alias_is_accepted(self):
        record = dict(WONDER)
        record.pop("surface")
        record["endpoint"] = "chat"
        self.assertEqual(mod.validate_line(line(record), 1), [])


if __name__ == "__main__":
    unittest.main()
