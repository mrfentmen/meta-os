"""Orchestrator decision-order tests (CB2-092). Pure decisions."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import orchestrator  # noqa: E402

FLAG = {"step": "flag", "division": "vigiles",
        "category": "physical contact"}
REVIEW = {"step": "review", "verdict": "confirmed",
          "category": "physical contact"}
INVESTIGATIONS = [
    {"step": "investigation", "kind": "cross-lens", "division": "ignis"},
    {"step": "investigation", "kind": "cross-lens", "division": "medicus"},
]


def record(timeline):
    return {
        "id": "incident-order", "status": "candidate",
        "evidence": {"files": []}, "created_at": "2026-11-02T00:00:00Z",
        "camera": {"id": "cam-a", "name": "A", "area": "Manhattan"},
        "division": "vigiles", "category": "physical contact",
        "priority": "high", "patrol_job_id": "j1", "timeline": timeline,
    }


class DecisionOrderTests(unittest.TestCase):
    def test_review_then_investigation_then_response(self):
        review = orchestrator.decide(record([FLAG]))
        self.assertEqual(review["decision"], "investigate")
        self.assertEqual(review["actions"][0]["agent"], "review")

        investigate = orchestrator.decide(record([FLAG, REVIEW]))
        self.assertEqual(investigate["decision"], "investigate")
        self.assertEqual(investigate["actions"][0]["agent"],
                         "investigation")

        response = orchestrator.decide(
            record([FLAG, REVIEW] + INVESTIGATIONS))
        self.assertEqual(response["decision"], "prepare_response")
        self.assertEqual(response["actions"][0]["agent"], "response")


if __name__ == "__main__":
    unittest.main()
