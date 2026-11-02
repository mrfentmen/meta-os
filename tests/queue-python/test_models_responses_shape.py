"""Request shape tests (CB2-070..071). Offline; stubbed transport."""
import os
import sys
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import models  # noqa: E402

SAM_TEXT = "<|box;x1=0;y1=0;x2=10;y2=10;w=10;h=10|>"


class ResponseShapeTests(unittest.TestCase):
    def test_segment_uses_responses_input_items(self):
        seen = {}

        def fake_post(url, body, kind):
            seen.update(body)
            return {"model": models.SAM, "output": [
                {"type": "message", "content": [
                    {"type": "output_text", "text": SAM_TEXT}]}]}, 1

        with unittest.mock.patch.object(models, "_post", fake_post), \
                unittest.mock.patch.object(
                    models.spark_guardrail, "record"):
            models.segment(b"\x89PNG\r\n\x1a\nrest", "person")
        self.assertEqual(seen["model"], models.SAM)
        content = seen["input"][0]["content"]
        self.assertEqual(content[0]["type"], "input_text")
        self.assertEqual(content[1]["type"], "input_image")
        self.assertTrue(content[1]["image_url"].startswith(
            "data:image/jpeg;base64,"))

    def test_chat_uses_messages_and_no_responses_fields(self):
        seen = {}

        def fake_post(url, body, kind):
            seen.update(body)
            return {"model": models.SPARK,
                    "choices": [{"message": {"content": "ok"}}],
                    "usage": {}}, 1

        with unittest.mock.patch.object(models, "_post", fake_post), \
                unittest.mock.patch.object(
                    models.spark_guardrail, "record"):
            models.chat_text(models.SPARK, "hello")
        self.assertEqual(seen["messages"],
                         [{"role": "user", "content": "hello"}])
        self.assertEqual(seen["model"], models.SPARK)
        self.assertNotIn("input", seen)


if __name__ == "__main__":
    unittest.main()
