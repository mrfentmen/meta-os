"""Tests for the autonomous orchestrator (orchestrator.py) — the
deterministic decision engine that replaced the crew's fixed
pipeline order (LANE B, 2026-10-30).

Run from the repo root (same command as the queue suite):

    python3 -m unittest discover -s tests/queue-python -v

Everything here is offline and $0: the orchestrator makes no model
calls by design; records are built by hand or through the real
CrewRecords store, and the guardrail is passed as a plain status
dict (the seam spark_guardrail.status() fills in production).
"""
import os
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
QUEUE_DIR = os.path.join(REPO, "server", "queue")
sys.path.insert(0, QUEUE_DIR)

import crew_records  # noqa: E402
import orchestrator  # noqa: E402

GUARDRAIL_OK = {"calls": 38, "est_cost_usd": 0.2543,
                "test_budget_usd": 75.0, "remaining_usd": 74.7457}


def record(timeline, status="candidate", division="vigiles",
           category="person down"):
    return {"id": "incident-test", "status": status,
            "created_at": "2026-10-30T06:00:00.000Z",
            "camera": {"id": "cam-a", "name": "1 Ave @ 84 St",
                       "area": "Manhattan"},
            "division": division, "category": category,
            "priority": "high", "timeline": timeline}


def flag_step(category="person down", **kw):
    return {"step": "flag", "division": "vigiles",
            "category": category, "job_id": "trio-flag", **kw}


def review_step(verdict="confirmed", category="person down", **kw):
    return {"step": "review", "verdict": verdict,
            "category": category, "job_id": "trio-review", **kw}


def investigation_step(division="ignis", kind="cross-lens", **kw):
    return {"step": "investigation", "kind": kind,
            "division": division, "camera_id": "cam-a",
            "category": "no hazard visible", "flagged": False,
            "job_id": f"trio-inv-{division}-{kind}", **kw}


class ContractShapeTests(unittest.TestCase):
    def test_decision_contract_shape(self):
        d = orchestrator.decide(record([flag_step()]),
                                guardrail_status=GUARDRAIL_OK)
        self.assertEqual(set(d), {"incident_id", "decision",
                                  "reason", "actions",
                                  "stop_conditions"})
        self.assertEqual(d["incident_id"], "incident-test")
        self.assertIsInstance(d["decision"], str)
        self.assertIsInstance(d["reason"], str)
        self.assertTrue(d["reason"])
        self.assertEqual(d["stop_conditions"],
                         {"max_actions": 8, "max_model_calls": 12,
                          "max_cost_usd": 0.50})
        for action in d["actions"]:
            self.assertEqual(set(action), {"agent", "task"})

    def test_first_decision_on_a_flag_is_review(self):
        d = orchestrator.decide(record([flag_step()]),
                                guardrail_status=GUARDRAIL_OK)
        self.assertEqual(d["decision"], "investigate")
        self.assertEqual([a["agent"] for a in d["actions"]],
                         ["review"])
        self.assertEqual(orchestrator.lifecycle_status(d),
                         "under_review")


class DecisionFlowTests(unittest.TestCase):
    def test_close_candidate_on_lookalike_review(self):
        rec = record([flag_step("possible altercation"),
                      review_step("cleared", "normal activity")])
        d = orchestrator.decide(rec, guardrail_status=GUARDRAIL_OK)
        self.assertEqual(d["decision"], "close_candidate")
        self.assertEqual([a["agent"] for a in d["actions"]],
                         ["records"])
        self.assertIn("look-alike", d["reason"])
        self.assertEqual(orchestrator.lifecycle_status(d),
                         "closed-false-positive")

    def test_inconclusive_review_monitors_without_spend(self):
        rec = record([flag_step(), review_step("inconclusive", None)])
        d = orchestrator.decide(rec, guardrail_status=GUARDRAIL_OK)
        self.assertEqual(d["decision"], "continue_monitoring")
        self.assertEqual(d["actions"], [])
        self.assertEqual(orchestrator.lifecycle_status(d),
                         "monitoring")

    def test_prepare_response_only_after_survival_and_investigation(self):
        # Confirmed review, NO investigation yet: the next decision
        # must be the investigation, never the response.
        rec = record([flag_step(), review_step()], status="reported")
        d = orchestrator.decide(rec, guardrail_status=GUARDRAIL_OK)
        self.assertEqual(d["decision"], "investigate")
        self.assertEqual([a["agent"] for a in d["actions"]],
                         ["investigation"])
        # Investigation recorded for both other lenses: NOW the
        # response may be prepared.
        rec2 = record([flag_step(), review_step(),
                       investigation_step("ignis"),
                       investigation_step("medicus"),
                       investigation_step("vigiles", "neighbour")],
                      status="investigating")
        d2 = orchestrator.decide(rec2, guardrail_status=GUARDRAIL_OK)
        self.assertEqual(d2["decision"], "prepare_response")
        self.assertEqual([a["agent"] for a in d2["actions"]],
                         ["response"])
        self.assertEqual(orchestrator.lifecycle_status(d2),
                         "response_prepared")

    def test_reconcile_on_conflicting_categories(self):
        rec = record([flag_step("person down"),
                      review_step("confirmed",
                                  "possible altercation")],
                     status="reported")
        d = orchestrator.decide(rec, guardrail_status=GUARDRAIL_OK)
        self.assertEqual(d["decision"], "reconcile")
        self.assertEqual([a["agent"] for a in d["actions"]],
                         ["review"])
        self.assertIn("conflicting", d["reason"])

    def test_reconcile_on_missing_lens(self):
        rec = record([flag_step(), review_step(),
                      investigation_step("ignis")],
                     status="investigating")
        d = orchestrator.decide(rec, guardrail_status=GUARDRAIL_OK)
        self.assertEqual(d["decision"], "reconcile")
        self.assertEqual([a["agent"] for a in d["actions"]],
                         ["investigation"])
        self.assertIn("medicus", d["actions"][0]["task"])

    def test_terminal_incident_stops(self):
        rec = record([flag_step(), review_step()],
                     status="dispatched-simulated")
        d = orchestrator.decide(rec, guardrail_status=GUARDRAIL_OK)
        self.assertEqual(d["decision"], "stop")
        self.assertEqual(d["actions"], [])


class StopConditionTests(unittest.TestCase):
    def test_max_actions_refuses_further_spend(self):
        # 8 emitted actions already on decision steps; a fresh flag
        # would need a review — refused, naming the limit.
        timeline = [flag_step()] + [
            {"step": "decision", "decision": "investigate",
             "actions": [{"agent": "review", "task": "x"}]}
            for _ in range(8)]
        d = orchestrator.decide(record(timeline),
                                guardrail_status=GUARDRAIL_OK)
        self.assertEqual(d["decision"], "stop")
        self.assertIn("max_actions", d["reason"])
        self.assertEqual(d["actions"], [])

    def test_max_model_calls_refuses_further_spend(self):
        # 12 model calls already (flag + 11 investigation steps)
        # and no review on record: the review would be call 13.
        timeline = [flag_step()] + [
            investigation_step("ignis", "neighbour",
                               job_id=f"trio-inv-{i}")
            for i in range(11)]
        # max_actions is raised so the model-call limit is the
        # one under test (the same record trips max_actions first
        # at the default limits — also correct, and covered by
        # the max_actions test above).
        d = orchestrator.decide(
            record(timeline), guardrail_status=GUARDRAIL_OK,
            stop_conditions={"max_actions": 99,
                             "max_model_calls": 12,
                             "max_cost_usd": 0.50})
        self.assertEqual(d["decision"], "stop")
        self.assertIn("max_model_calls", d["reason"])
        self.assertEqual(d["actions"], [])

    def test_max_cost_refuses_further_spend(self):
        # $0.495 already spent on this incident (recorded on its
        # own timeline); one more call at the planning estimate
        # takes it past the $0.50 incident cap.
        timeline = [flag_step(est_cost_usd=0.30),
                    {"step": "investigation", "kind": "neighbour",
                     "division": "vigiles", "camera_id": "cam-b",
                     "job_id": "trio-inv-x", "category": None,
                     "flagged": False, "est_cost_usd": 0.195}]
        d = orchestrator.decide(record(timeline),
                                guardrail_status=None)
        self.assertEqual(d["decision"], "stop")
        self.assertIn("max_cost_usd", d["reason"])
        self.assertEqual(d["actions"], [])

    def test_guardrail_exhaustion_refuses_further_spend(self):
        spent = {"calls": 9000, "est_cost_usd": 75.0,
                 "test_budget_usd": 75.0, "remaining_usd": 0.0}
        d = orchestrator.decide(record([flag_step()]),
                                guardrail_status=spent)
        self.assertEqual(d["decision"], "stop")
        self.assertIn("guardrail", d["reason"])
        self.assertEqual(d["actions"], [])


class LoopGuardTests(unittest.TestCase):
    def test_same_evidence_hash_twice_blocks_reinvestigation(self):
        # The incident's evidence frame was already investigated
        # twice (e.g. a frozen feed returning the identical frame)
        # and the investigation record still has a lens gap — the
        # orchestrator must monitor, not investigate a third time.
        timeline = [flag_step(frame_sha256="hash-x"),
                    review_step(),
                    investigation_step(
                        "ignis", frame_sha256="hash-x"),
                    investigation_step(
                        "vigiles", "neighbour",
                        frame_sha256="hash-x")]
        rec = record(timeline, status="investigating")
        d = orchestrator.decide(rec, guardrail_status=GUARDRAIL_OK,
                                evidence_hash="hash-x")
        self.assertEqual(d["decision"], "continue_monitoring")
        self.assertIn("loop guard", d["reason"])
        self.assertEqual(d["actions"], [])

    def test_new_evidence_hash_is_not_loop_guarded(self):
        timeline = [flag_step(frame_sha256="hash-x"),
                    review_step(),
                    investigation_step(
                        "ignis", frame_sha256="hash-x"),
                    investigation_step(
                        "vigiles", "neighbour",
                        frame_sha256="hash-x")]
        rec = record(timeline, status="investigating")
        d = orchestrator.decide(rec, guardrail_status=GUARDRAIL_OK,
                                evidence_hash="hash-new")
        self.assertEqual(d["decision"], "reconcile")


class RecordingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="trio-orchestrator-tests-")
        self.records = crew_records.CrewRecords(
            directory=os.path.join(self.tmp, "crew-data"))
        self.orch = orchestrator.Orchestrator(
            self.records, guardrail_status=lambda: GUARDRAIL_OK)

    def test_decision_appended_to_timeline_and_events(self):
        rec = record([flag_step()])
        self.records.create_incident(rec)
        self.records.append_timeline("incident-test", flag_step())
        before = self.records.get_incident("incident-test")
        d = self.orch.step(before)
        self.assertEqual(d["decision"], "investigate")
        after = self.records.get_incident("incident-test")
        # Append-only: the flag step is untouched, the decision
        # grew the timeline by exactly one step.
        self.assertEqual(after["timeline"][0]["step"], "flag")
        self.assertEqual(len(after["timeline"]),
                         len(before["timeline"]) + 1)
        step = after["timeline"][-1]
        self.assertEqual(step["step"], "decision")
        self.assertEqual(step["agent"], "orchestrator")
        self.assertEqual(step["decision"], "investigate")
        self.assertEqual(step["actions_count"], 1)
        self.assertEqual(after["status"], "under_review")
        events = self.records.recent_events(10)
        orch_events = [e for e in events
                       if e.get("type") == "orchestrator"]
        self.assertEqual(len(orch_events), 1)
        ev = orch_events[0]
        self.assertEqual(ev["agent"], "orchestrator")
        self.assertEqual(ev["decision"], "investigate")
        self.assertEqual(ev["actions"], 1)
        self.assertEqual(ev["incident_id"], "incident-test")
        self.assertIn("baseline", ev["reason"])

    def test_step_replans_from_current_state(self):
        # The same Orchestrator, consulted after each result lands,
        # walks flag -> review -> investigation -> response with
        # no predefined sequence anywhere in this test's control
        # flow — each call reads the record as it then stands.
        rec = record([flag_step()])
        self.records.create_incident(rec)
        self.records.append_timeline("incident-test", flag_step())
        d1 = self.orch.step(self.records.get_incident("incident-test"))
        self.assertEqual([a["agent"] for a in d1["actions"]],
                         ["review"])
        self.records.append_timeline(
            "incident-test",
            {**review_step(), "status": "reported"})
        d2 = self.orch.step(self.records.get_incident("incident-test"))
        self.assertEqual(d2["decision"], "investigate")
        self.assertEqual([a["agent"] for a in d2["actions"]],
                         ["investigation"])
        for s in (investigation_step("ignis"),
                  investigation_step("medicus")):
            self.records.append_timeline("incident-test", s)
        d3 = self.orch.step(self.records.get_incident("incident-test"))
        self.assertEqual(d3["decision"], "prepare_response")
        decisions = [s["decision"] for s in
                     self.records.get_incident("incident-test")
                     ["timeline"] if s["step"] == "decision"]
        self.assertEqual(decisions, ["investigate", "investigate",
                                     "prepare_response"])


if __name__ == "__main__":
    unittest.main()
