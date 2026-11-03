"""Image magic tests (CB2-056..057). Offline; stubbed transport."""
import base64
import os
import sys
import tempfile
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import models  # noqa: E402


class ImageMagicTests(unittest.TestCase):
    def test_png_jpeg_webp_labels(self):
        self.assertEqual(models.detect_image_format(
            b"\x89PNG\r\n\x1a\nrest"), "png")
        self.assertEqual(models.detect_image_format(
            b"\xff\xd8\xff\xe0rest"), "jpeg")
        self.assertEqual(models.detect_image_format(
            b"RIFFxxxxWEBPrest"), "webp")

    def test_unknown_payload_raises_not_placeholder(self):
        junk = base64.b64encode(b"????").decode()
        payload = {"model": models.IMAGE, "usage": {},
                   "output": [{"type": "image_generation_call",
                               "result": junk}]}
        with tempfile.TemporaryDirectory() as td:
            with unittest.mock.patch.dict(
                    os.environ, {"METAOS_MODEL_RECEIPTS":
                                 os.path.join(td, "r.jsonl")}), \
                    unittest.mock.patch.object(
                        models, "_post", return_value=(payload, 1)), \
                    unittest.mock.patch.object(
                        models.spark_guardrail, "record"):
                with self.assertRaises(ValueError):
                    models.generate_image("draw a sign")


if __name__ == "__main__":
    unittest.main()
