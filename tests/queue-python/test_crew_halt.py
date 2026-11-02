"""Crew halt test (CB2-093). Offline; real records, stubbed handler."""
import os
import sys
import tempfile
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew  # noqa: E402
import crew_records  # noqa: E402
import orchestrator  # noqa: E402

CAM = {"id": "cam-a", "name": "A", "area": "Manhattan",
       "latitude": 40.0, "longitude": -73.0}
FIRST = {"job_id": "j1", "status": "ok", "model": "m",
         "latency_ms": 1, "category": "physical contact",
         "assessment": {"summary": "s", "uncertainty": []}}


class HaltTests(unittest.TestCase):
    def test_judge_failure_writes_halt_step_and_stops(self):
        records = crew_records.CrewRecords(
            directory=tempfile.mkdtemp(prefix="halt-"))
        obj = object.__new__(crew.Crew)
        obj.records = records
        obj.orchestrator = orchestrator.Orchestrator(
            records, guardrail_status={"calls": 0, "est_cost_usd": 0.0,
                                       "test_budget_usd": 75.0,
                                       "remaining_usd": 75.0})
        obj.detector = None
        with unittest.mock.patch.object(
                crew.Crew, "_capture_evidence",
                return_value=([], None, None)), \
                unittest.mock.patch.object(
                    crew.Crew, "_run_review",
                    side_effect=RuntimeError("judge exploded")):
            out = obj._handle_flag(
                CAM, "vigiles", b"\xff\xd8\xffframe", FIRST,
                "physical contact", "2026-11-02T00:00:00Z")
        self.assertEqual(out["outcome"], "halted")
        rec = records.get_incident(out["incident_id"])
        self.assertEqual(rec["timeline"][-1]["step"], "halt")
        self.assertIn("judge exploded",
                      rec["timeline"][-1]["reason"])


if __name__ == "__main__":
    unittest.main()
