"""Evidence purge tests (CB2-090..091). Temp data dir; real files."""
import os
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew_records  # noqa: E402


def record(iid="incident-p"):
    return {
        "id": iid, "status": "candidate",
        "evidence": {"frame_sha256": "abc", "detector": "injected",
                     "files": []},
        "created_at": "2026-11-02T00:00:00Z",
        "camera": {"id": "cam-a", "name": "A", "area": "Manhattan",
                   "latitude": 40.0, "longitude": -73.0},
        "division": "vigiles", "category": "physical contact",
        "priority": "high", "patrol_job_id": "j1", "timeline": [],
    }


class PurgeTests(unittest.TestCase):
    def setUp(self):
        self.records = crew_records.CrewRecords(
            directory=tempfile.mkdtemp(prefix="purge-"))
        self.records.create_incident(record())
        self.refs = [
            self.records.save_evidence_file("incident-p", "frame.jpg",
                                            b"frame"),
            self.records.save_evidence_file("incident-p", "crop.jpg",
                                            b"crop"),
        ]
        self.records.attach_evidence(
            "incident-p",
            [{"ref": self.refs[0], "kind": "flag-frame"},
             {"ref": self.refs[1], "kind": "face-crop"}],
            "2026-11-02T00:01:00Z")

    def test_files_are_deleted_and_receipt_is_recorded(self):
        receipt = self.records.purge_evidence(
            "incident-p", "closed-false-positive",
            "2026-11-02T00:02:00Z")
        self.assertEqual(receipt["files_removed"], 2)
        self.assertFalse(os.path.exists(
            os.path.join(self.records.dir, self.refs[0])))
        rec = self.records.get_incident("incident-p")
        self.assertEqual(rec["evidence"]["files"], [])
        self.assertEqual(rec["evidence"]["purged"]["reason"],
                         "closed-false-positive")
        self.assertEqual(rec["timeline"][-1]["step"], "evidence-purged")

    def test_second_purge_is_idempotent_and_removes_nothing(self):
        self.records.purge_evidence(
            "incident-p", "closed-false-positive", "t1")
        receipt = self.records.purge_evidence(
            "incident-p", "closed-false-positive", "t2")
        self.assertEqual(receipt["files_removed"], 0)


if __name__ == "__main__":
    unittest.main()
