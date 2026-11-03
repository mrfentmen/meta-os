"""No-fabrication tests (CB2-075). Offline; failure paths only."""
import os
import sys
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import models  # noqa: E402


class NoFabricationTests(unittest.TestCase):
    def test_transcribe_raises(self):
        with self.assertRaises(models.EndpointUnresolvedError):
            models.transcribe(b"audio")

    def test_segment_empty_raises(self):
        with self.assertRaises(ValueError):
            models.segment(b"", "person")

    def test_image_absent_item_raises(self):
        with unittest.mock.patch.object(
                models, "_post", return_value=({"output": []}, 1)), \
                unittest.mock.patch.object(
                    models.spark_guardrail, "record"):
            with self.assertRaises(models.EmptyResponseError):
                models.generate_image("draw")

    def test_chat_unknown_model_raises(self):
        with self.assertRaises(models.EndpointUnresolvedError):
            models.chat_text("unknown-model", "hello")

    def test_chat_empty_content_raises(self):
        with unittest.mock.patch.object(
                models, "_post",
                return_value=({"choices": [{"message": {"content": None}}]},
                              1)), \
                unittest.mock.patch.object(
                    models.spark_guardrail, "record"):
            with self.assertRaises(models.EmptyResponseError):
                models.chat_text(models.SPARK, "hello")


if __name__ == "__main__":
    unittest.main()
