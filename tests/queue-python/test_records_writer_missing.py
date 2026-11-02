"""Missing-case tests for the crew records writer (B238).

Covers what RecordsTests in test_crew.py does not: the create copy,
status advance through the timeline, ordering, the live-status filter,
evidence attach/purge receipts, the path-escape refusal, torn JSONL
lines, and the status snapshot.

Run with: python3 -m pytest tests/queue-python/test_records_writer_missing.py -q
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew_records  # noqa: E402


class RecordsEdgeTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="crew-records-")
        self.store = crew_records.CrewRecords(self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_create_defaults_a_timeline_and_stores_a_copy(self):
        source = {"id": "i1", "created_at": "2026-01-01"}
        created = self.store.create_incident(source)
        self.assertEqual(created["timeline"], [])
        source["status"] = "mutated"
        self.assertNotIn("status", self.store.get_incident("i1"))

    def test_append_to_an_unknown_incident_names_the_id(self):
        with self.assertRaises(KeyError) as caught:
            self.store.append_timeline("missing", {"step": "x"})
        self.assertIn("missing", str(caught.exception))

    def test_status_advances_only_when_a_step_carries_one(self):
        self.store.create_incident(
            {"id": "i1", "status": "flagged", "created_at": "2026-01-01"})
        self.store.append_timeline("i1", {"step": "patrol"})
        self.assertEqual(self.store.get_incident("i1")["status"], "flagged")
        record = self.store.append_timeline(
            "i1", {"step": "review", "status": "reported"})
        self.assertEqual(record["status"], "reported")
        self.assertEqual(len(record["timeline"]), 2)

    def test_list_orders_newest_first_and_missing_dates_last(self):
        self.store.create_incident(
            {"id": "old", "created_at": "2026-01-01"})
        self.store.create_incident(
            {"id": "new", "created_at": "2026-02-01"})
        self.store.create_incident({"id": "none"})
        ids = [r["id"] for r in self.store.list_incidents()]
        self.assertEqual(ids, ["new", "old", "none"])

    def test_open_incidents_keeps_live_statuses_only(self):
        live = ("flagged", "reported", "candidate", "under_review",
                "investigating", "monitoring", "response_prepared")
        closed = ("cleared-by-review", "dispatched-simulated", "stopped")
        for status in live + closed:
            self.store.create_incident(
                {"id": status, "status": status,
                 "created_at": "2026-01-01"})
        kept = {r["id"] for r in self.store.open_incidents()}
        self.assertEqual(kept, set(live))

    def test_attach_evidence_grows_the_list_and_the_timeline(self):
        self.store.create_incident({"id": "i1", "created_at": "2026-01-01"})
        ref = self.store.save_evidence_file("i1", "frame.jpg", b"jpeg")
        self.assertEqual(ref, "evidence/i1/frame.jpg")
        record = self.store.attach_evidence(
            "i1", [{"ref": ref, "kind": "frame"}], "2026-01-01T00:00:00Z")
        self.assertEqual(len(record["evidence"]["files"]), 1)
        self.assertEqual(record["timeline"][-1]["step"], "evidence")
        self.assertEqual(record["timeline"][-1]["files"], [ref])

    def test_attach_to_an_unknown_incident_raises(self):
        with self.assertRaises(KeyError):
            self.store.attach_evidence("missing", [], "now")

    def test_purge_removes_files_keeps_the_hash_and_records_a_receipt(self):
        self.store.create_incident({
            "id": "i1", "created_at": "2026-01-01",
            "evidence": {"frame_sha256": "abc", "detector": "face"}})
        first = self.store.save_evidence_file("i1", "a.jpg", b"a")
        second = self.store.save_evidence_file("i1", "b.jpg", b"b")
        self.store.attach_evidence(
            "i1", [{"ref": first}, {"ref": second}], "t0")
        receipt = self.store.purge_evidence("i1", "false positive", "t1")
        self.assertEqual(receipt["files_removed"], 2)
        record = self.store.get_incident("i1")
        self.assertEqual(record["evidence"]["files"], [])
        self.assertEqual(record["evidence"]["frame_sha256"], "abc")
        self.assertEqual(record["evidence"]["purged"]["reason"],
                         "false positive")
        self.assertEqual(record["timeline"][-1]["step"], "evidence-purged")
        self.assertFalse(os.path.exists(os.path.join(self.dir, first)))

    def test_purge_never_deletes_outside_the_data_dir(self):
        self.store.create_incident({
            "id": "i1", "created_at": "2026-01-01",
            "evidence": {"files": [{"ref": "../escape.txt"}]}})
        outside = os.path.join(os.path.dirname(self.dir), "escape.txt")
        with open(outside, "w") as f:
            f.write("keep me")
        try:
            receipt = self.store.purge_evidence("i1", "look-alike", "t1")
            self.assertEqual(receipt["files_removed"], 0)
            self.assertTrue(os.path.exists(outside))
        finally:
            os.remove(outside)

    def test_recent_events_skips_a_torn_line_and_honours_the_limit(self):
        self.store.append_event({"n": 1})
        self.store.append_event({"n": 2})
        with open(os.path.join(self.dir, "events.jsonl"), "a") as f:
            f.write("not json\n")
        self.store.append_event({"n": 3})
        self.assertEqual(self.store.recent_events(limit=2),
                         [{"n": 2}, {"n": 3}])

    def test_recent_dispatches_tails_the_log(self):
        for n in range(3):
            self.store.append_dispatch({"n": n})
        self.assertEqual(self.store.recent_dispatches(limit=2),
                         [{"n": 1}, {"n": 2}])

    def test_status_snapshot_round_trips_and_is_none_before_first_write(self):
        self.assertIsNone(self.store.read_status())
        self.store.write_status({"state": "patrolling"})
        self.assertEqual(self.store.read_status(), {"state": "patrolling"})
        with open(os.path.join(self.dir, "crew-status.json")) as f:
            self.assertEqual(json.load(f), {"state": "patrolling"})


if __name__ == "__main__":
    unittest.main()
