"""Crew review seam tests (CB2-007..009). Offline; model call stubbed."""
import json
import os
import sys
import tempfile
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew  # noqa: E402
import crew_common  # noqa: E402
import crew_records  # noqa: E402

FRAME = b"\xff\xd8" + b"review-frame"
CAM = {"id": "cam-a", "name": "A", "latitude": 40.0,
       "longitude": -73.0, "area": "Manhattan"}


def result(product, timestamp, category="person down"):
    return {
        "status": "ok", "job_id": crew_common.job_id_for(
            product, timestamp, FRAME),
        "model": "muse-spark-1.3", "latency_ms": 3,
        "assessment": {
            "product": product, "timestamp": timestamp,
            "observations": [{"category": category,
                              "description": "stub",
                              "confidence": 0.8}],
            "assessment": {"category": category, "summary": "stub",
                           "uncertainty": [],
                           "requires_human_review": True},
            "processing": {"model": "muse-spark-1.3"},
        },
    }


class ReviewSeamTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.records = crew_records.CrewRecords(
            directory=os.path.join(self.tmp, "crew-data"))
        self.records.create_incident(
            {"id": "incident-review", "status": "candidate",
             "timeline": []})
        self.crew = crew.Crew(
            self.records,
            lambda product, frame, timestamp: result(
                product, timestamp),
            lambda camera: FRAME, lambda package: {"receipt_id": "sim-x"})

    def _review(self, first_category="person down"):
        return self.crew._run_review(
            "incident-review", CAM, "vigiles", FRAME,
            "2026-11-02T10:00:00.000Z", first_category=first_category,
            first_result={"category": first_category})

    def _step(self):
        return [s for s in self.records.get_incident(
            "incident-review")["timeline"] if s["step"] == "review"][-1]

    def test_transport_error_falls_back_and_names_the_fallback(self):
        with unittest.mock.patch.dict(
                os.environ, {"TRIO_JUDGE_MODEL": "1"}):
            with unittest.mock.patch.object(
                    crew.models, "chat_text",
                    side_effect=RuntimeError("transport down")):
                _review, verdict = self._review()
        self.assertEqual(verdict, "confirmed")
        step = self._step()
        self.assertEqual(step["judge_mode"], "deterministic")
        self.assertIn("model judge unavailable", step["judge_reasons"][0])

    def test_unset_model_env_uses_deterministic_mode(self):
        old = os.environ.pop("TRIO_JUDGE_MODEL", None)
        try:
            _review, verdict = self._review()
        finally:
            if old is not None:
                os.environ["TRIO_JUDGE_MODEL"] = old
        self.assertEqual(verdict, "confirmed")
        self.assertEqual(self._step()["judge_mode"], "deterministic")

    def test_model_mode_records_its_own_ruling(self):
        reply = json.dumps({"verdict": "confirm",
                            "category": "person down",
                            "reasons": ["both readings agree"]})
        with unittest.mock.patch.dict(
                os.environ, {"TRIO_JUDGE_MODEL": "1"}):
            with unittest.mock.patch.object(
                    crew.models, "chat_text",
                    return_value=(reply, None)):
                _review, verdict = self._review()
        self.assertEqual(verdict, "confirmed")
        step = self._step()
        self.assertEqual(step["judge_mode"], "model")
        self.assertTrue(any("model judge ruling" in r
                            for r in step["judge_reasons"]))


if __name__ == "__main__":
    unittest.main()
