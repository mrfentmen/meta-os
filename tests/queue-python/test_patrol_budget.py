"""Patrol budget tests (CB2-084..085). Offline; fake crew/guardrail."""
import os
import sys
import tempfile
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew_records  # noqa: E402
import patrol  # noqa: E402

CAM = {"id": "cam-a", "name": "A", "latitude": 40.0,
       "longitude": -73.0, "area": "Manhattan"}


class FakeCrew:
    def __init__(self):
        self.seen = []

    def check_camera(self, camera, division):
        self.seen.append((camera["id"], division))
        return {"outcome": "baseline"}


class PatrolBudgetTests(unittest.TestCase):
    def _patrol(self, remaining):
        tmp = tempfile.mkdtemp()
        records = crew_records.CrewRecords(directory=tmp)
        fake = FakeCrew()
        status = {"calls": 4, "est_cost_usd": 70.75,
                  "test_budget_usd": 75.0, "remaining_usd": remaining}
        obj = patrol.Patrol(
            fake, [CAM], "fallback-subset", records, interval_s=0,
            reserve_usd=5.0, guardrail_status=lambda: status,
            sleep=lambda s: None)
        return obj, fake, records

    def test_reserve_floor_stops_and_files_nothing(self):
        obj, fake, records = self._patrol(5.0)
        with unittest.mock.patch.object(
                patrol.spark_guardrail, "check", lambda: None):
            out = obj.run_cycle()
        self.assertEqual(out["outcome"], "paused-budget")
        self.assertEqual(fake.seen, [])
        self.assertEqual(records.read_status()["state"], "paused-budget")

    def test_stop_event_records_guardrail_cost(self):
        obj, _fake, records = self._patrol(4.0)
        with unittest.mock.patch.object(
                patrol.spark_guardrail, "check", lambda: None):
            obj.run_cycle()
        event = records.recent_events(5)[-1]
        self.assertEqual(event["state"], "paused-budget")
        self.assertEqual(event["guardrail"]["est_cost_usd"], 70.75)


if __name__ == "__main__":
    unittest.main()
