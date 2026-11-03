"""Full incident walk tests (CB2-021..022). Offline; stubbed transports."""
import os
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew  # noqa: E402
import crew_common  # noqa: E402
import crew_records  # noqa: E402

FRAME = b"\xff\xd8" + b"walk-frame"
CAM = {"id": "cam-a", "name": "A", "latitude": 40.0,
       "longitude": -73.0, "area": "Manhattan"}
NEAR = [{"id": f"cam-n{i}", "name": f"N{i}",
         "latitude": 40.0 + 0.001 * (i + 1),
         "longitude": -73.0 - 0.001 * (i + 1),
         "area": "Manhattan"} for i in range(5)]


def result(product, timestamp, category):
    return {
        "status": "ok", "job_id": crew_common.job_id_for(
            product, timestamp, FRAME),
        "model": "muse-spark-1.3", "latency_ms": 2,
        "assessment": {
            "product": product, "timestamp": timestamp,
            "observations": [{"category": category,
                              "description": "stub", "confidence": 0.8}],
            "assessment": {"category": category, "summary": "stub",
                           "uncertainty": [],
                           "requires_human_review": True},
            "processing": {"model": "muse-spark-1.3"},
        },
    }


class Assessor:
    def __init__(self):
        self.script = {"vigiles": ["person down", "person down",
                                   "normal activity"],
                       "ignis": ["no hazard visible"],
                       "medicus": ["normal activity"]}
        self.calls = []

    def __call__(self, product, frame, timestamp):
        self.calls.append((product, timestamp))
        entries = self.script[product]
        category = entries.pop(0) if len(entries) > 1 else entries[0]
        return result(product, timestamp, category)


class IncidentWalkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.records = crew_records.CrewRecords(
            directory=os.path.join(self.tmp, "crew-data"))
        self.assessor = Assessor()
        self.dispatched = []

        def dispatch(package):
            self.dispatched.append(package)
            return {"receipt_id": "sim-walk", "simulated": True}

        self.crew = crew.Crew(
            self.records, self.assessor, lambda camera: FRAME, dispatch,
            cameras=NEAR)
        self.outcome = self.crew.check_camera(CAM, "vigiles")
        self.incident = self.records.list_incidents()[0]

    def test_full_recorded_incident_reaches_simulated_response(self):
        self.assertEqual(self.outcome["outcome"], "dispatched-simulated")
        work = [s["step"] for s in self.incident["timeline"]
                if s["step"] != "decision"]
        self.assertEqual(work[0], "flag")
        self.assertEqual(work[1], "review")
        self.assertEqual(work[2], "reported")
        self.assertEqual(work[-3:], ["brief", "bolo", "dispatch"])
        self.assertEqual(len(self.dispatched), 1)
        self.assertIs(self.dispatched[0]["simulated"], True)

    def test_investigation_never_exceeds_six_calls(self):
        steps = [s for s in self.incident["timeline"]
                 if s["step"] == "investigation"]
        self.assertLessEqual(len(steps), crew.MAX_INVESTIGATION_CALLS)
        self.assertGreater(len(steps), 0)
        # Patrol + review + investigation are the only model calls.
        self.assertEqual(len(self.assessor.calls), 2 + len(steps))


if __name__ == "__main__":
    unittest.main()
