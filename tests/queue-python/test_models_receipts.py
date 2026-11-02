"""Model receipt tests (CB2-063..064). Offline; temp receipts file."""
import json
import os
import sys
import tempfile
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import models  # noqa: E402

USAGE = {"prompt_tokens": 1000, "completion_tokens": 1000}


class ReceiptTests(unittest.TestCase):
    def test_one_call_appends_one_line_with_model_surface_latency(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "receipts.jsonl")
            with unittest.mock.patch.dict(
                    os.environ, {"METAOS_MODEL_RECEIPTS": path}):
                models._receipt("chat:muse-wonder-1.0", models.WONDER,
                                "chat", USAGE, 12)
            with open(path) as handle:
                lines = handle.read().strip().splitlines()
        self.assertEqual(len(lines), 1)
        rec = json.loads(lines[0])
        for key in models.RECEIPT_FIELDS:
            self.assertIn(key, rec)
        self.assertEqual(rec["model"], models.WONDER)
        self.assertEqual(rec["surface"], "chat")
        self.assertEqual(rec["latency_ms"], 12)

    def test_spark_has_a_dollar_estimate_and_wonder_has_null(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "receipts.jsonl")
            with unittest.mock.patch.dict(
                    os.environ, {"METAOS_MODEL_RECEIPTS": path}):
                spark = models._receipt("chat:muse-spark-1.3", models.SPARK,
                                        "chat", USAGE, 1)
                wonder = models._receipt("chat:muse-wonder-1.0",
                                         models.WONDER, "chat", USAGE, 1)
                count = models.validate_receipts(path)
        self.assertIsNotNone(spark["est_cost_usd"])
        self.assertIsNone(wonder["est_cost_usd"])
        self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
