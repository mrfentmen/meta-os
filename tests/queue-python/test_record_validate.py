"""Tests for the v2 incident record validator (CB2-351..355).

Run from the repo root:

    python3 -m unittest discover -s tests/queue-python -p "test_record_validate.py"
"""

import copy
import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "server", "queue"),
)

from record_validate import validate_v2_incident  # noqa: E402

# The shape a real assessor files (spark_gen prompt, live-reading.json).
VALID = {
    "product": "vigiles",
    "timestamp": "2026-11-02T10:05:33-05:00",
    "observations": [
        {
            "category": "normal activity",
            "description": "Multiple vehicles on a multi-lane urban street",
            "evidence": "Yellow buses, cars, a white truck and a van",
            "confidence": None,
            "region": None,
        },
    ],
    "assessment": {
        "category": "normal activity",
        "summary": "Daytime view of an urban street with vehicular traffic",
        "uncertainty": ["Distant pedestrians are not clearly discernible"],
        "requires_human_review": True,
    },
    "processing": {"model": "muse-spark-1.3", "latency_ms": 9670},
}


def fixture():
    return copy.deepcopy(VALID)


class TestValidRecord(unittest.TestCase):
    def test_full_fixture_passes_with_zero_errors(self):
        self.assertEqual(validate_v2_incident(fixture()), [])

    def test_null_latency_is_allowed(self):
        record = fixture()
        record["processing"]["latency_ms"] = None
        self.assertEqual(validate_v2_incident(record), [])

    def test_confidence_and_region_numbers_are_allowed(self):
        record = fixture()
        record["observations"][0]["confidence"] = 0.82
        record["observations"][0]["region"] = {"x": 10, "y": 20, "w": 30, "h": 40}
        self.assertEqual(validate_v2_incident(record), [])

    def test_empty_region_at_the_max_is_allowed(self):
        record = fixture()
        record["observations"][0]["region"] = {
            "x": 0, "y": 0, "w": 0, "h": 1000,
        }
        self.assertEqual(validate_v2_incident(record), [])


class TestTopLevel(unittest.TestCase):
    def test_not_an_object(self):
        self.assertEqual(validate_v2_incident([]), ["record: must be an object"])

    def test_extra_top_level_key_is_reported(self):
        record = fixture()
        record["tier"] = "gold"
        self.assertEqual(
            validate_v2_incident(record), ["unexpected field: tier"])

    def test_each_missing_required_field_is_named(self):
        for key in ("product", "timestamp", "observations",
                    "assessment", "processing"):
            record = fixture()
            del record[key]
            self.assertIn(
                "missing required field: " + key,
                validate_v2_incident(record), key)

    def test_empty_product_names_the_field(self):
        record = fixture()
        record["product"] = "  "
        self.assertIn(
            "product: must be a non-empty string",
            validate_v2_incident(record))

    def test_bad_timestamp_names_the_field(self):
        record = fixture()
        record["timestamp"] = "yesterday"
        self.assertIn(
            "timestamp: must be an ISO-8601 string",
            validate_v2_incident(record))

    def test_empty_observation_list_is_reported(self):
        record = fixture()
        record["observations"] = []
        self.assertIn(
            "observations: must not be empty", validate_v2_incident(record))


class TestObservation(unittest.TestCase):
    def test_missing_category_names_the_field(self):
        record = fixture()
        del record["observations"][0]["category"]
        self.assertIn(
            "observations[0].category: missing",
            validate_v2_incident(record))

    def test_second_observation_error_carries_its_index(self):
        record = fixture()
        record["observations"].append({"category": "normal activity"})
        errors = validate_v2_incident(record)
        self.assertIn("observations[1].description: missing", errors)

    def test_region_coordinate_over_1000_fails(self):
        record = fixture()
        record["observations"][0]["region"] = {
            "x": 1001, "y": 0, "w": 10, "h": 10,
        }
        self.assertIn(
            "observations[0].region.x: must be 0..1000",
            validate_v2_incident(record))

    def test_region_missing_coordinate_is_named(self):
        record = fixture()
        record["observations"][0]["region"] = {"x": 1, "y": 2, "w": 3}
        self.assertIn(
            "observations[0].region.h: missing",
            validate_v2_incident(record))

    def test_confidence_above_one_fails(self):
        record = fixture()
        record["observations"][0]["confidence"] = 1.5
        self.assertIn(
            "observations[0].confidence: must be 0..1",
            validate_v2_incident(record))

    def test_boolean_confidence_is_not_a_number(self):
        record = fixture()
        record["observations"][0]["confidence"] = True
        self.assertIn(
            "observations[0].confidence: must be a number or null",
            validate_v2_incident(record))


class TestAssessmentAndProcessing(unittest.TestCase):
    def test_missing_summary_names_the_field(self):
        record = fixture()
        del record["assessment"]["summary"]
        self.assertIn(
            "assessment.summary: missing", validate_v2_incident(record))

    def test_non_boolean_human_review_flag_fails(self):
        record = fixture()
        record["assessment"]["requires_human_review"] = "yes"
        self.assertIn(
            "assessment.requires_human_review: must be a boolean",
            validate_v2_incident(record))

    def test_processing_without_model_is_reported(self):
        record = fixture()
        del record["processing"]["model"]
        self.assertIn(
            "processing.model: missing", validate_v2_incident(record))

    def test_negative_latency_fails(self):
        record = fixture()
        record["processing"]["latency_ms"] = -1
        self.assertIn(
            "processing.latency_ms: must be a number >= 0 or null",
            validate_v2_incident(record))

    def test_validator_does_not_mutate_the_record(self):
        record = fixture()
        before = copy.deepcopy(record)
        validate_v2_incident(record)
        self.assertEqual(record, before)


if __name__ == "__main__":
    unittest.main()
