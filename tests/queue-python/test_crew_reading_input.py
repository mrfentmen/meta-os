"""Second-reading input tests (CB2-023..024). Offline; stubbed assessor."""
import os
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew  # noqa: E402
import crew_common  # noqa: E402
import crew_records  # noqa: E402

FRAME = b"\xff\xd8" + b"reading-frame"
CAM = {"id": "cam-a", "name": "A", "latitude": 40.0,
       "longitude": -73.0, "area": "Manhattan"}


def reading(product, timestamp, category, confidence=0.8):
    assessment = None
    if category is not None:
        assessment = {
            "product": product, "timestamp": timestamp,
            "observations": [{"category": category,
                              "description": "stub",
                              "confidence": confidence}],
            "assessment": {"category": category, "summary": "stub",
                           "uncertainty": [],
                           "requires_human_review": True},
            "processing": {"model": "muse-spark-1.3"},
        }
    return {"status": "ok", "job_id": crew_common.job_id_for(
                product, timestamp, FRAME),
            "model": "muse-spark-1.3", "latency_ms": 2,
            "assessment": assessment}


class ReadingInputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.records = crew_records.CrewRecords(
            directory=os.path.join(self.tmp, "crew-data"))
        self.records.create_incident(
            {"id": "incident-reading", "status": "candidate",
             "timeline": []})
        self.category = "person down"
        self.crew = crew.Crew(
            self.records,
            lambda product, frame, timestamp: reading(
                product, timestamp, self.category),
            lambda camera: FRAME, lambda package: {"receipt_id": "sim-x"})

    def _review(self):
        return self.crew._run_review(
            "incident-reading", CAM, "vigiles", FRAME,
            "2026-11-02T10:00:00.000Z",
            first_category="person down",
            first_result={"category": "person down"})

    def _step(self):
        return [s for s in self.records.get_incident(
            "incident-reading")["timeline"] if s["step"] == "review"][-1]

    def test_missing_second_reading_category_rules_inconclusive(self):
        # The module's real shape: a category-less second reading is
        # recorded as unreadable and the judge rules inconclusive; it
        # is not silently treated as a confirmation.
        self.category = None
        _review, verdict = self._review()
        self.assertEqual(verdict, "inconclusive")
        step = self._step()
        self.assertIsNone(step["category"])
        self.assertIn("failed or carried no category",
                      " ".join(step["judge_reasons"]))

    def test_string_confidence_does_not_crash_or_change_the_verdict(self):
        self.category = "person down"
        self.crew.assess = lambda product, frame, timestamp: reading(
            product, timestamp, "person down", confidence="0.9")
        _review, verdict = self._review()
        self.assertEqual(verdict, "confirmed")
        self.assertEqual(self._step()["category"], "person down")


if __name__ == "__main__":
    unittest.main()
