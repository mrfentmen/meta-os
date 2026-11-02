"""Envelope/result edge cases for the Trio side of the OS queue.

Runs under the documented offline command:

    python3 -m unittest discover -s tests/queue-python -v

The node-dependent cases build the envelope with the REAL
server/queue.mjs buildQueueJob; the pure-Python cases mirror the
deterministic id and check the queue service's own refusal wording.
No live queue, no Spark call.
"""
import hashlib
import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import test_queue  # noqa: E402  (sets the local-fallback env, exposes helpers)
from test_queue import (  # noqa: E402
    FRAME,
    PRODUCT,
    TIMESTAMP,
    build_job_via_node,
    python_job_id,
)

import queue_service  # noqa: E402
import trio_store  # noqa: E402

NODE = shutil.which("node")


class IdEdgeTests(unittest.TestCase):
    """Pure Python: the deterministic id is bound to every input."""

    def test_same_inputs_same_id(self):
        self.assertEqual(
            python_job_id(PRODUCT, TIMESTAMP, FRAME),
            python_job_id(PRODUCT, TIMESTAMP, FRAME),
        )

    def test_product_timestamp_and_frame_each_change_the_id(self):
        base = python_job_id(PRODUCT, TIMESTAMP, FRAME)
        self.assertNotEqual(base, python_job_id("vigiles", TIMESTAMP, FRAME))
        self.assertNotEqual(
            base, python_job_id(PRODUCT, "2026-11-02T00:00:00.000Z", FRAME))
        self.assertNotEqual(base, python_job_id(PRODUCT, TIMESTAMP, FRAME + b"x"))

    def test_missing_result_is_none_not_a_fabricated_envelope(self):
        store = trio_store.LocalSqliteStore(
            os.path.join(test_queue._TMP, "edge-missing-result.db"))
        jobs = trio_store.JobStore(store)
        self.assertIsNone(jobs.get_result("trio-does-not-exist"))


@unittest.skipUnless(NODE, "node is required to build the real envelope")
class NodeEnvelopeEdgeTests(unittest.TestCase):
    """The real buildQueueJob's refusals and its honest size behaviour."""

    def test_bad_product_is_a_node_build_failure(self):
        with self.assertRaises(RuntimeError) as cm:
            build_job_via_node(product="not-a-product")
        message = str(cm.exception)
        self.assertIn("buildQueueJob failed", message)
        self.assertIn("not-a-product", message)

    def test_empty_frame_is_refused_with_the_real_builder_message(self):
        with self.assertRaises(RuntimeError) as cm:
            build_job_via_node(frame=b"")
        self.assertIn("without image bytes", str(cm.exception))

    def test_oversized_frame_is_accepted_and_measured_honestly(self):
        # The 4 KB per-call cap lives at the assess boundary, not in the
        # queue builder; the builder's contract is "bytes in, measured
        # bytes out". Pin that contract instead of inventing a cap.
        frame = b"\xff\xd8" + b"a" * 200_000
        env = build_job_via_node(frame=frame)
        self.assertIsNone(queue_service.validate_envelope(env))
        self.assertEqual(env["image"]["byteLength"], len(frame))
        self.assertEqual(env["image"]["sha256"],
                         hashlib.sha256(frame).hexdigest())
        self.assertTrue(env["image"]["dataUrl"].startswith(
            "data:image/jpeg;base64,"))

    def test_node_built_id_matches_the_python_mirror(self):
        env = build_job_via_node()
        self.assertEqual(env["id"],
                         python_job_id(PRODUCT, TIMESTAMP, FRAME))


class EnvelopeRefusalEdgeTests(unittest.TestCase):
    """queue_service.validate_envelope's typed refusal wording."""

    def test_non_object_is_refused(self):
        self.assertEqual(queue_service.validate_envelope(None),
                         "envelope is not a JSON object")
        self.assertEqual(queue_service.validate_envelope([]),
                         "envelope is not a JSON object")

    def test_missing_image_object_is_refused(self):
        env = {"version": 1, "kind": "trio-assessment", "id": "trio-x",
               "product": PRODUCT, "timestamp": TIMESTAMP}
        self.assertEqual(queue_service.validate_envelope(env),
                         "envelope has no image object")

    def test_non_jpeg_data_url_is_refused(self):
        env = {"version": 1, "kind": "trio-assessment", "id": "trio-x",
               "product": PRODUCT, "timestamp": TIMESTAMP,
               "image": {"dataUrl": "data:image/png;base64,AAAA",
                         "byteLength": 3, "sha256": "0" * 64}}
        self.assertEqual(queue_service.validate_envelope(env),
                         "image.dataUrl is not a JPEG data URL")

    def test_empty_timestamp_and_missing_id_are_refused(self):
        base = {"version": 1, "kind": "trio-assessment", "id": "trio-x",
                "product": PRODUCT, "timestamp": TIMESTAMP,
                "image": {"dataUrl": "data:image/jpeg;base64,AAAA",
                          "byteLength": 3, "sha256": "0" * 64}}
        self.assertEqual(
            queue_service.validate_envelope({**base, "id": ""}),
            "envelope has no job id")
        self.assertEqual(
            queue_service.validate_envelope({**base, "timestamp": ""}),
            "envelope has no timestamp")


if __name__ == "__main__":
    unittest.main()
