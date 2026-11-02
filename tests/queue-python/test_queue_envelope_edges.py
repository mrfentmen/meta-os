"""Queue envelope refusal tests (CB2-096). API boundary only."""
import base64
import hashlib
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import queue_service  # noqa: E402

FRAME = b"\xff\xd8\xff" + b"frame"


def envelope():
    data_url = ("data:image/jpeg;base64,"
                + base64.b64encode(FRAME).decode())
    return {
        "version": 1, "kind": "trio-assessment", "id": "job-1",
        "product": "vigiles", "timestamp": "2026-11-02T00:00:00Z",
        "image": {"dataUrl": data_url, "byteLength": len(FRAME),
                  "sha256": hashlib.sha256(FRAME).hexdigest()},
    }


class EnvelopeBoundaryTests(unittest.TestCase):
    def test_valid_envelope_is_accepted(self):
        self.assertIsNone(queue_service.validate_envelope(envelope()))

    def test_missing_id_is_refused(self):
        env = envelope()
        env.pop("id")
        self.assertEqual(queue_service.validate_envelope(env),
                         "envelope has no job id")

    def test_unknown_product_is_refused(self):
        env = envelope()
        env["product"] = "not-a-product"
        self.assertIn("unknown product",
                      queue_service.validate_envelope(env))

    def test_bad_image_hash_is_refused(self):
        env = envelope()
        env["image"]["sha256"] = "0" * 64
        self.assertIn("sha256",
                      queue_service.validate_envelope(env))


if __name__ == "__main__":
    unittest.main()
