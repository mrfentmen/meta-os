"""Missing cases for the Python queue service envelope check (B224).

`test_queue.py` and `test_envelope_edges.py` cover the real node-built
envelope, the byteLength/SHA mismatches, the JPEG prefix, the unknown
product, and the missing timestamp/id. This file covers the refusal and
boundary cases they do not:

- a missing or non-dict `image` object;
- a valid base64 payload under the wrong image type, and a wrong-case
  data URL header;
- a zero-byte frame accepted when its hash fields agree (the code has no
  minimum length);
- a one-byte frame whose `byteLength` is the boolean `true` (Python's
  `True == 1` passes the equality check);
- a string `byteLength`, an upper-case digest, an int `timestamp`, a
  wrong-case product, and a whitespace-only id;
- unknown extra envelope fields being ignored.

No live queue, no node, no network: the envelope is built in Python and
passed to the service's own `validate_envelope`.
"""
import base64
import hashlib
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import test_queue  # noqa: E402  (forces the local-fallback env)
import queue_service  # noqa: E402

PRODUCT = "ignis"
TIMESTAMP = "2026-10-30T06:00:00.000Z"


def data_url(frame):
    return "data:image/jpeg;base64," + base64.b64encode(frame).decode()


def envelope(frame=b"\xff\xd8\xff\xe0frame", **overrides):
    record = {
        "version": 1,
        "kind": "trio-assessment",
        "id": "trio-test",
        "product": PRODUCT,
        "timestamp": TIMESTAMP,
        "image": {
            "dataUrl": data_url(frame),
            "byteLength": len(frame),
            "sha256": hashlib.sha256(frame).hexdigest(),
        },
    }
    record.update(overrides)
    return record


class ImageShapeMissingTest(unittest.TestCase):
    def test_valid_python_built_envelope_passes(self):
        self.assertIsNone(queue_service.validate_envelope(envelope()))

    def test_missing_image_object_is_refused(self):
        env = envelope()
        del env["image"]
        self.assertEqual(queue_service.validate_envelope(env),
                         "envelope has no image object")

    def test_non_dict_image_is_refused(self):
        env = envelope()
        env["image"] = ["not", "an", "object"]
        self.assertEqual(queue_service.validate_envelope(env),
                         "envelope has no image object")

    def test_png_payload_is_refused_as_not_jpeg(self):
        env = envelope()
        env["image"]["dataUrl"] = (
            "data:image/png;base64," + base64.b64encode(b"png").decode())
        self.assertEqual(queue_service.validate_envelope(env),
                         "image.dataUrl is not a JPEG data URL")

    def test_upper_case_header_is_refused(self):
        env = envelope()
        env["image"]["dataUrl"] = "DATA:IMAGE/JPEG;BASE64,AAAA"
        self.assertEqual(queue_service.validate_envelope(env),
                         "image.dataUrl is not a JPEG data URL")


class FrameBoundaryMissingTest(unittest.TestCase):
    def test_zero_byte_frame_is_accepted_when_hashes_agree(self):
        env = envelope(frame=b"")
        self.assertEqual(env["image"]["byteLength"], 0)
        self.assertIsNone(queue_service.validate_envelope(env))

    def test_one_byte_frame_accepts_boolean_true_as_byte_length(self):
        env = envelope(frame=b"\xff")
        env["image"]["byteLength"] = True
        self.assertIsNone(queue_service.validate_envelope(env))

    def test_boolean_true_does_not_match_a_two_byte_frame(self):
        env = envelope(frame=b"\xff\xd8")
        env["image"]["byteLength"] = True
        self.assertEqual(queue_service.validate_envelope(env),
                         "image.byteLength does not match the decoded frame")

    def test_string_byte_length_is_refused(self):
        env = envelope(frame=b"\xff")
        env["image"]["byteLength"] = "1"
        self.assertEqual(queue_service.validate_envelope(env),
                         "image.byteLength does not match the decoded frame")

    def test_upper_case_sha_is_refused(self):
        env = envelope(frame=b"\xff")
        env["image"]["sha256"] = env["image"]["sha256"].upper()
        self.assertEqual(queue_service.validate_envelope(env),
                         "image.sha256 does not match the decoded frame")


class FieldShapeMissingTest(unittest.TestCase):
    def test_int_timestamp_is_refused(self):
        env = envelope(timestamp=12345)
        self.assertEqual(queue_service.validate_envelope(env),
                         "envelope has no timestamp")

    def test_wrong_case_product_is_unknown(self):
        env = envelope(product="IGNIS")
        self.assertEqual(queue_service.validate_envelope(env),
                         "unknown product 'IGNIS'")

    def test_whitespace_only_id_is_accepted(self):
        env = envelope(id=" ")
        self.assertIsNone(queue_service.validate_envelope(env))

    def test_int_id_is_refused(self):
        env = envelope(id=7)
        self.assertEqual(queue_service.validate_envelope(env),
                         "envelope has no job id")

    def test_unknown_extra_fields_are_ignored(self):
        env = envelope(unexpected="field", another={"nested": True})
        self.assertIsNone(queue_service.validate_envelope(env))


if __name__ == "__main__":
    unittest.main()
