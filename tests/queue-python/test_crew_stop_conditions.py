"""Incident stop-condition tests (CB2-004..006). Offline; no model call."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import orchestrator  # noqa: E402

GUARDRAIL_OK = {"calls": 10, "est_cost_usd": 0.05,
                "test_budget_usd": 75.0, "remaining_usd": 74.95}


def record(timeline):
    return {
        "id": "incident-stop", "status": "candidate",
        "created_at": "2026-11-02T10:00:00.000Z",
        "camera": {"id": "cam-a", "name": "A"},
        "division": "vigiles", "category": "person down",
        "priority": "high", "timeline": timeline,
    }


def flag():
    return {"step": "flag", "division": "vigiles",
            "category": "person down", "job_id": "trio-flag"}


def decision():
    return {"step": "decision", "decision": "investigate",
            "actions": [{"agent": "review", "task": "look again"}]}


def investigation(i):
    return {"step": "investigation", "kind": "neighbour",
            "division": "vigiles", "camera_id": "cam-b",
            "job_id": f"trio-inv-{i}", "category": None,
            "flagged": False}


class StopConditionTests(unittest.TestCase):
    def test_eight_actions_stop_without_any_network_call(self):
        timeline = [flag()] + [decision() for _ in range(8)]
        out = orchestrator.decide(record(timeline),
                                  guardrail_status=GUARDRAIL_OK)
        self.assertEqual(out["decision"], "stop")
        self.assertIn("max_actions", out["reason"])
        self.assertEqual(out["actions"], [])

    def test_twelve_model_calls_stop_before_the_next_call(self):
        timeline = [flag()] + [investigation(i) for i in range(11)]
        out = orchestrator.decide(
            record(timeline), guardrail_status=GUARDRAIL_OK,
            stop_conditions={"max_actions": 99, "max_model_calls": 12,
                             "max_cost_usd": 0.50})
        self.assertEqual(out["decision"], "stop")
        self.assertIn("max_model_calls", out["reason"])
        self.assertEqual(out["actions"], [])

    def test_fifty_cent_cap_stops_before_the_next_action(self):
        timeline = [
            {"step": "flag", "division": "vigiles",
             "category": "person down", "job_id": "trio-flag",
             "est_cost_usd": 0.30},
            {"step": "investigation", "kind": "neighbour",
             "division": "vigiles", "camera_id": "cam-b",
             "job_id": "trio-inv-x", "category": None,
             "flagged": False, "est_cost_usd": 0.195},
        ]
        out = orchestrator.decide(record(timeline),
                                  guardrail_status=None)
        self.assertEqual(out["decision"], "stop")
        self.assertIn("max_cost_usd", out["reason"])
        self.assertEqual(out["actions"], [])


if __name__ == "__main__":
    unittest.main()
