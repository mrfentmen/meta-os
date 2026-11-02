"""Tier mapping and audit-flag tests (CB2-019..020). Offline."""
import os
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew  # noqa: E402
import crew_common  # noqa: E402
import crew_records  # noqa: E402
import orchestrator  # noqa: E402

FRAME = b"\xff\xd8" + b"tier-frame"
CAM = {"id": "cam-a", "name": "A", "latitude": 40.0,
       "longitude": -73.0, "area": "Manhattan"}


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


class ScriptedAssessor:
    def __init__(self):
        self.script = {"vigiles": ["person down", "person down",
                                   "normal activity"],
                       "ignis": ["no hazard visible"],
                       "medicus": ["normal activity"]}
        self.calls = []

    def __call__(self, product, frame, timestamp):
        self.calls.append(product)
        entries = self.script[product]
        category = entries.pop(0) if len(entries) > 1 else entries[0]
        return result(product, timestamp, category)


class TierTests(unittest.TestCase):
    def test_small_finding_is_yellow(self):
        self.assertEqual(
            orchestrator.tier_for("vigiles", "staged verbal dispute"),
            "yellow")

    def test_emergency_finding_is_red(self):
        self.assertEqual(
            orchestrator.tier_for("vigiles", "physical contact"), "red")

    def test_yellow_decision_orders_no_actions(self):
        record = {
            "id": "incident-yellow", "status": "candidate",
            "division": "vigiles", "category": "staged verbal dispute",
            "timeline": [{"step": "flag", "category":
                          "staged verbal dispute"}],
        }
        decision = orchestrator.decide(record)
        self.assertEqual(decision["decision"], "record_for_review")
        self.assertEqual(decision["actions"], [])


class AuditFlagDispatchTests(unittest.TestCase):
    def test_requires_human_review_does_not_block_simulated_dispatch(self):
        tmp = tempfile.mkdtemp()
        records = crew_records.CrewRecords(
            directory=os.path.join(tmp, "crew-data"))
        dispatched = []

        def dispatch(package):
            dispatched.append(package)
            return {"receipt_id": "sim-test123", "simulated": True}

        crew_obj = crew.Crew(records, ScriptedAssessor(),
                             lambda camera: FRAME, dispatch, cameras=[])
        out = crew_obj.check_camera(CAM, "vigiles")
        self.assertEqual(out["outcome"], "dispatched-simulated")
        self.assertEqual(len(dispatched), 1)
        package = dispatched[0]
        self.assertIs(package["requires_human_review"], True)
        self.assertIs(
            package["brief"]["assessment"]["requires_human_review"], True)


if __name__ == "__main__":
    unittest.main()
