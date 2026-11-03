"""Patrol frame flow tests (CB2-086..087). Offline; fake crew."""
import os
import sys
import tempfile
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew_common  # noqa: E402
import crew_records  # noqa: E402
import patrol  # noqa: E402

CAM = {"id": "cam-a", "name": "A", "latitude": 40.0,
       "longitude": -73.0, "area": "Manhattan"}


class FakeCrew:
    def check_camera(self, camera, division):
        return {"outcome": "baseline", "camera_id": camera["id"],
                "division": division}


class PatrolFrameTests(unittest.TestCase):
    def test_normal_activity_creates_no_incident(self):
        records = crew_records.CrewRecords(directory=tempfile.mkdtemp())
        obj = patrol.Patrol(
            FakeCrew(), [CAM], "fallback-subset", records, interval_s=0,
            guardrail_status=lambda: {
                "calls": 0, "est_cost_usd": 0.0,
                "test_budget_usd": 75.0, "remaining_usd": 75.0},
            sleep=lambda s: None)
        with unittest.mock.patch.object(
                patrol.spark_guardrail, "check", lambda: None):
            out = obj.run_cycle()
        self.assertEqual(out["outcome"], "baseline")
        self.assertEqual(records.list_incidents(), [])

    def test_division_category_list_comes_from_the_js_source(self):
        # The crew reads the category tables through crew_common; the
        # list is not copied into Python. These are the real look-alike
        # baselines from js/command-flag.js.
        ignis = crew_common.baseline_categories()["ignis"]
        self.assertIn("steam or fog", ignis)
        self.assertIn("flame-like lighting", ignis)


if __name__ == "__main__":
    unittest.main()
