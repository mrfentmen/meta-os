"""Chat model tests (CB2-060..062). Offline; stubbed transport."""
import os
import sys
import tempfile
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import models  # noqa: E402


def payload(model):
    return {"model": model,
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1}}


class ChatModelTests(unittest.TestCase):
    def test_wonder_id_is_sent_verbatim(self):
        seen = {}

        def fake_post(url, body, kind):
            seen.update(body)
            return payload(models.WONDER), 3

        with tempfile.TemporaryDirectory() as td:
            with unittest.mock.patch.dict(
                    os.environ, {"METAOS_MODEL_RECEIPTS":
                                 os.path.join(td, "r.jsonl")}), \
                    unittest.mock.patch.object(models, "_post", fake_post), \
                    unittest.mock.patch.object(
                        models.spark_guardrail, "record"):
                text, reported, _latency = models.chat_text(
                    models.WONDER, "hello")
        self.assertEqual(text, "ok")
        self.assertEqual(reported, models.WONDER)
        self.assertEqual(seen["model"], models.WONDER)

    def test_spark_id_is_sent_verbatim(self):
        seen = {}

        def fake_post(url, body, kind):
            seen.update(body)
            return payload(models.SPARK), 3

        with tempfile.TemporaryDirectory() as td:
            with unittest.mock.patch.dict(
                    os.environ, {"METAOS_MODEL_RECEIPTS":
                                 os.path.join(td, "r.jsonl")}), \
                    unittest.mock.patch.object(models, "_post", fake_post), \
                    unittest.mock.patch.object(
                        models.spark_guardrail, "record"):
                models.chat_text(models.SPARK, "hello")
        self.assertEqual(seen["model"], models.SPARK)

    def test_unverified_spark_1_2_and_1_1_are_refused(self):
        for model in ("muse-spark-1.2", "muse-spark-1.1"):
            with self.assertRaises(models.EndpointUnresolvedError):
                models.chat_text(model, "hello")

    def test_empty_prompt_is_refused_before_transport(self):
        calls = []
        with unittest.mock.patch.object(
                models, "_post",
                side_effect=lambda *a: calls.append(a)):
            with self.assertRaises(ValueError):
                models.chat_text(models.SPARK, "   ")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
