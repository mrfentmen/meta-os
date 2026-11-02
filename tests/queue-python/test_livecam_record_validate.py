"""Tests for the livecam record validator (CB2-365..366).

Run from the repo root:

    python3 -m unittest discover -s tests/queue-python -p "test_livecam_record_validate.py"

The valid fixture mirrors server/queue/livecam_records/live-reading.json
(the real filed record). Its categories are read from js/products.js,
not copied, so the test cannot drift from the table the assessor uses.
"""

import copy
import hashlib
import os
import sys
import unittest

QUEUE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "server", "queue")
sys.path.insert(0, QUEUE_DIR)

import trio_repo  # noqa: E402
from livecam_record_validate import (  # noqa: E402
    categories_for,
    validate_livecam_record,
)

CATEGORIES = categories_for("vigiles")
OUTCOME = sorted(CATEGORIES)[0]


def fixture():
    return {
        "frame": {
            "camera_id": "0472fa7a-acd7-4510-a9e7-61307d4057cd",
            "camera_name": "Bay Pkwy @ 78 St (Kings Hwy)",
            "area": "Brooklyn",
            "latitude": 40.60632,
            "longitude": -73.989087,
            "source": "NYC DOT public traffic camera",
            "image_url": "https://webcams.nyctmc.org/api/cameras/x/image",
            "fetched_at": "2026-11-02T10:05:33-05:00",
            "image_sha256": hashlib.sha256(b"frame").hexdigest(),
            "image_bytes": 28402,
            "live": True,
        },
        "fetch_route": "browser download",
        "reading": {
            "result": {
                "product": "vigiles",
                "timestamp": "2026-11-02T10:05:33-05:00",
                "observations": [{
                    "category": OUTCOME,
                    "description": "Multiple vehicles on a multi-lane street",
                    "evidence": "Yellow buses and cars on the roadway",
                    "confidence": None,
                    "region": None,
                }],
                "assessment": {
                    "category": OUTCOME,
                    "summary": "Daytime view of an urban street",
                    "uncertainty": ["Distant details are unclear"],
                    "requires_human_review": True,
                },
                "processing": {"model": "muse-spark-1.3", "latency_ms": None},
            },
            "model": "muse-spark-1.3",
            "latency_ms": 9670,
        },
    }


class TestValid(unittest.TestCase):
    def test_real_shape_passes(self):
        self.assertEqual(validate_livecam_record(fixture()), [])

    def test_product_categories_come_from_products_js(self):
        self.assertEqual(
            CATEGORIES, frozenset(trio_repo.product_profile("vigiles")["categories"]))

    def test_explicit_categories_argument_is_honoured(self):
        record = fixture()
        self.assertEqual(
            validate_livecam_record(record, categories=frozenset({OUTCOME})), [])

    def test_validator_does_not_mutate(self):
        record = fixture()
        before = copy.deepcopy(record)
        validate_livecam_record(record)
        self.assertEqual(record, before)


class TestFrame(unittest.TestCase):
    def test_missing_camera_id_is_named(self):
        record = fixture()
        del record["frame"]["camera_id"]
        self.assertIn(
            "frame.camera_id: missing", validate_livecam_record(record))

    def test_missing_camera_name_is_named(self):
        record = fixture()
        record["frame"]["camera_name"] = ""
        self.assertIn(
            "frame.camera_name: must be a non-empty string",
            validate_livecam_record(record))

    def test_bad_timestamp_is_named(self):
        record = fixture()
        record["frame"]["fetched_at"] = "10:05"
        self.assertIn(
            "frame.fetched_at: must be an ISO-8601 string",
            validate_livecam_record(record))

    def test_short_digest_is_refused(self):
        record = fixture()
        record["frame"]["image_sha256"] = "abc123"
        self.assertIn(
            "frame.image_sha256: must be 64 lowercase hex chars",
            validate_livecam_record(record))

    def test_zero_image_bytes_is_refused(self):
        record = fixture()
        record["frame"]["image_bytes"] = 0
        self.assertIn(
            "frame.image_bytes: must be a positive integer",
            validate_livecam_record(record))

    def test_non_boolean_live_flag_is_refused(self):
        record = fixture()
        record["frame"]["live"] = "yes"
        self.assertIn(
            "frame.live: must be a boolean", validate_livecam_record(record))


class TestReading(unittest.TestCase):
    def test_unknown_reading_outcome_is_reported(self):
        record = fixture()
        record["reading"]["result"]["assessment"]["category"] = "mood: tense"
        self.assertIn(
            "reading.result.assessment.category: unknown category 'mood: tense'",
            validate_livecam_record(record))

    def test_unknown_observation_category_is_reported(self):
        record = fixture()
        record["reading"]["result"]["observations"][0]["category"] = "not-a-cat"
        self.assertIn(
            "reading.result.observations[0].category: unknown category "
            "'not-a-cat'",
            validate_livecam_record(record))

    def test_broken_v2_block_is_prefixed_with_its_path(self):
        record = fixture()
        del record["reading"]["result"]["processing"]
        self.assertIn(
            "reading.result.missing required field: processing",
            validate_livecam_record(record))

    def test_missing_reading_model_is_named(self):
        record = fixture()
        del record["reading"]["model"]
        self.assertIn(
            "reading.model: missing", validate_livecam_record(record))

    def test_extra_reading_key_is_named(self):
        record = fixture()
        record["reading"]["tokens"] = 42
        self.assertIn(
            "reading.tokens: unexpected field",
            validate_livecam_record(record))


class TestRecord(unittest.TestCase):
    def test_not_an_object(self):
        self.assertEqual(
            validate_livecam_record("reading"), ["record: must be an object"])

    def test_missing_top_level_key_is_named(self):
        record = fixture()
        del record["fetch_route"]
        self.assertIn(
            "missing required field: fetch_route",
            validate_livecam_record(record))

    def test_unexpected_top_level_key_is_named(self):
        record = fixture()
        record["camera"] = {}
        self.assertIn(
            "unexpected field: camera", validate_livecam_record(record))


if __name__ == "__main__":
    unittest.main()
