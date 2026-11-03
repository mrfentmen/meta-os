"""Input bounds tests (CB2-072..073). Offline; no transport."""
import os
import sys
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import models  # noqa: E402


class InputBoundsTests(unittest.TestCase):
    def test_overlong_prompt_is_refused_before_transport(self):
        calls = []
        with unittest.mock.patch.object(
                models, "_post",
                side_effect=lambda *a: calls.append(a)):
            with self.assertRaises(ValueError):
                models.chat_text(models.SPARK,
                                 "x" * (models.MAX_PROMPT_CHARS + 1))
        self.assertEqual(calls, [])

    def test_empty_and_non_image_segment_inputs_are_refused(self):
        calls = []
        with unittest.mock.patch.object(
                models, "_post",
                side_effect=lambda *a: calls.append(a)):
            for data in (b"", b"not an image"):
                with self.assertRaises(ValueError):
                    models.segment(data, "person")
        self.assertEqual(calls, [])

    def test_png_is_accepted_for_segment(self):
        payload = {"model": models.SAM, "output": [
            {"type": "message", "content": [
                {"type": "output_text", "text": SAM_TEXT}]}]}
        with unittest.mock.patch.object(
                models, "_post", return_value=(payload, 1)), \
                unittest.mock.patch.object(
                    models.spark_guardrail, "record"):
            rec = models.segment(b"\x89PNG\r\n\x1a\nrest", "person")
        self.assertEqual(rec["region"]["w"], 1000)


SAM_TEXT = "<|box;x1=0;y1=0;x2=10;y2=10;w=10;h=10|>"


if __name__ == "__main__":
    unittest.main()
