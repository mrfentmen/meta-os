"""Incident record shape validator tests (CB2-013..014). Pure; no I/O."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew_records  # noqa: E402


def valid_record():
    return {
        "id": "incident-1", "status": "candidate", "evidence": {},
        "created_at": "2026-11-02T10:00:00.000Z",
        "camera": {"id": "cam-a", "name": "A"},
        "division": "vigiles", "category": "person down",
        "priority": "high", "patrol_job_id": "trio-1",
        "timeline": [],
    }


class IncidentRecordValidationTests(unittest.TestCase):
    def test_valid_record_has_no_errors(self):
        self.assertEqual(
            crew_records.validate_incident_record(valid_record()), [])

    def test_missing_key_is_named(self):
        record = valid_record()
        del record["patrol_job_id"]
        errors = crew_records.validate_incident_record(record)
        self.assertIn("missing required field: patrol_job_id", errors)

    def test_every_required_key_is_enforced(self):
        for key in crew_records.REQUIRED_INCIDENT_KEYS:
            record = valid_record()
            del record[key]
            errors = crew_records.validate_incident_record(record)
            self.assertIn(f"missing required field: {key}", errors)

    def test_unknown_key_is_reported_not_ignored(self):
        record = valid_record()
        record["surprise"] = True
        errors = crew_records.validate_incident_record(record)
        self.assertIn("unexpected field: surprise", errors)

    def test_non_object_is_refused(self):
        self.assertEqual(
            crew_records.validate_incident_record([]),
            ["incident record is not an object"])


if __name__ == "__main__":
    unittest.main()
