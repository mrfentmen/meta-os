"""Trio store round-trip (CB2-097). Local SQLite temp file only."""
import os
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import trio_store  # noqa: E402


class JobPayloadTests(unittest.TestCase):
    def test_job_error_and_nested_result_round_trip(self):
        path = tempfile.mktemp(suffix=".db", prefix="trio-roundtrip-")
        store = trio_store.JobStore(trio_store.LocalSqliteStore(path))
        envelope = {"id": "job-1", "kind": "trio-assessment",
                    "version": 1, "product": "vigiles",
                    "timestamp": "2026-11-02T00:00:00Z",
                    "image": {"dataUrl": "data:image/jpeg;base64,AA=="}}
        jid, created = store.submit(envelope)
        self.assertTrue(created)
        self.assertEqual(store.job_envelope(jid), envelope)
        result = {"job_id": jid, "status": "ok",
                  "assessment": {"category": "physical contact"}}
        store.put_result(result)
        self.assertEqual(store.get_result(jid), result)

    def test_duplicate_submit_is_idempotent(self):
        path = tempfile.mktemp(suffix=".db", prefix="trio-dupe-")
        store = trio_store.JobStore(trio_store.LocalSqliteStore(path))
        envelope = {"id": "job-2", "kind": "trio-assessment",
                    "version": 1, "product": "vigiles",
                    "timestamp": "2026-11-02T00:00:00Z"}
        self.assertEqual(store.submit(envelope), ("job-2", True))
        self.assertEqual(store.submit(envelope), ("job-2", False))
        self.assertEqual(store.open_job_ids(), ["job-2"])


if __name__ == "__main__":
    unittest.main()
