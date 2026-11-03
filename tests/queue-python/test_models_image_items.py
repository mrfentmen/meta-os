"""Image item tests (CB2-058..059). Offline; stubbed transport."""
import os
import sys
import tempfile
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import models  # noqa: E402


class ImageItemTests(unittest.TestCase):
    def _call(self, payload):
        with tempfile.TemporaryDirectory() as td:
            with unittest.mock.patch.dict(
                    os.environ, {"METAOS_MODEL_RECEIPTS":
                                 os.path.join(td, "r.jsonl")}), \
                    unittest.mock.patch.object(
                        models, "_post", return_value=(payload, 1)), \
                    unittest.mock.patch.object(
                        models.spark_guardrail, "record"):
                return models.generate_image("draw")

    def test_absent_image_item_is_named(self):
        with self.assertRaises(models.EmptyResponseError):
            self._call({"model": models.IMAGE, "usage": {}, "output": []})

    def test_truncated_base64_is_named(self):
        payload = {"model": models.IMAGE, "usage": {},
                   "output": [{"type": "image_generation_call",
                               "result": "abc"}]}
        with self.assertRaises(models.EmptyResponseError):
            self._call(payload)


if __name__ == "__main__":
    unittest.main()
