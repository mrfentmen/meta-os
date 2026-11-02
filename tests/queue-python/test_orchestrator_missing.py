"""Missing-case tests for the Python orchestrator (B232).

Cases test_orchestrator.py does not cover: the counting rules, the
lifecycle-status mapping, tier normalisation, stop-condition
overrides, the unrecorded step, missing lenses and the loop-guard
count.

Offline and $0: the engine makes no model calls.
"""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
QUEUE_DIR = os.path.join(REPO, "server", "queue")
sys.path.insert(0, QUEUE_DIR)

import orchestrator  # noqa: E402


def record(timeline, status="candidate", division="vigiles",
           category="person down"):
    return {"id": "incident-missing", "status": status,
            "division": division, "category": category,
            "timeline": timeline}


class CountTests(unittest.TestCase):
    def test_actions_are_the_larger_of_emitted_and_executed(self):
        cnt = orchestrator.counts(record([
            {"step": "flag"},
            {"step": "review"},
            {"step": "decision",
             "actions": [{"agent": "review"},
                         {"agent": "investigation"}]},
            {"step": "investigation"},
        ]))
        self.assertEqual(cnt["model_calls"], 3)
        self.assertEqual(cnt["actions"], 2)
        self.assertAlmostEqual(cnt["est_cost_usd"], 0.03)

    def test_recorded_cost_wins_over_the_estimate(self):
        cnt = orchestrator.counts(record([
            {"step": "flag"},
            {"step": "decision", "actions": [],
             "est_cost_usd": 0.5},
        ]))
        self.assertEqual(cnt["est_cost_usd"], 0.5)

    def test_guardrail_average_is_used_when_calls_are_positive(self):
        cnt = orchestrator.counts(
            record([{"step": "flag"}, {"step": "review"}]),
            {"calls": 4, "est_cost_usd": 0.2})
        self.assertAlmostEqual(cnt["per_call_usd"], 0.05)
        self.assertAlmostEqual(cnt["est_cost_usd"], 0.1)

    def test_zero_guardrail_calls_fall_back_without_dividing(self):
        cnt = orchestrator.counts(
            record([{"step": "flag"}, {"step": "review"}]),
            {"calls": 0, "est_cost_usd": 0.0})
        self.assertEqual(cnt["per_call_usd"],
                         orchestrator.EST_COST_PER_CALL_USD)


class LifecycleTests(unittest.TestCase):
    def test_each_decision_maps_to_its_status(self):
        cases = {
            "close_candidate": "closed-false-positive",
            "prepare_response": "response_prepared",
            "continue_monitoring": "monitoring",
            "record_for_review": "yellow-review",
            "stop": "stopped",
            "reconcile": "investigating",
        }
        for decision, status in cases.items():
            self.assertEqual(
                orchestrator.lifecycle_status({"decision": decision}),
                status)
        self.assertEqual(
            orchestrator.lifecycle_status(
                {"decision": "investigate",
                 "actions": [{"agent": "review"}]}),
            "under_review")
        self.assertEqual(
            orchestrator.lifecycle_status(
                {"decision": "investigate",
                 "actions": [{"agent": "investigation"}]}),
            "investigating")
        self.assertIsNone(
            orchestrator.lifecycle_status({"decision": "unknown"}))


class TierTests(unittest.TestCase):
    def test_tier_is_case_and_space_insensitive(self):
        self.assertEqual(
            orchestrator.tier_for("vigiles", " Person Down "), "red")
        self.assertEqual(
            orchestrator.tier_for("ignis", "VISIBLE FLAME"), "red")

    def test_unknown_category_is_not_gated(self):
        self.assertIsNone(
            orchestrator.tier_for("vigiles", "not a real category"))

    def test_unknown_division_is_not_gated(self):
        self.assertIsNone(
            orchestrator.tier_for("unknown-division", "person down"))


class DecideEdgeTests(unittest.TestCase):
    def test_empty_timeline_orders_a_review(self):
        decision = orchestrator.decide(record([]))
        self.assertEqual(decision["decision"], "investigate")
        self.assertEqual([a["agent"] for a in decision["actions"]],
                         ["review"])

    def test_stop_conditions_can_stop_immediately(self):
        decision = orchestrator.decide(
            record([]),
            stop_conditions={"max_actions": 0, "max_model_calls": 12,
                             "max_cost_usd": 0.50})
        self.assertEqual(decision["decision"], "stop")
        self.assertIn("max_actions", decision["reason"])
        self.assertEqual(decision["actions"], [])

    def test_terminal_status_stops(self):
        decision = orchestrator.decide(record([], status="stopped"))
        self.assertEqual(decision["decision"], "stop")
        self.assertIn("complete", decision["reason"])

    def test_missing_lenses_names_only_other_divisions(self):
        rec = record([{"step": "investigation", "kind": "cross-lens",
                       "division": "ignis"}])
        self.assertEqual(orchestrator.missing_lenses(rec), ["medicus"])

    def test_investigations_of_counts_both_hash_fields(self):
        rec = record([
            {"step": "investigation", "frame_sha256": "abc"},
            {"step": "investigation", "evidence_hash": "abc"},
        ])
        self.assertEqual(
            orchestrator._investigations_of(rec, "abc"), 2)
        self.assertEqual(
            orchestrator._investigations_of(rec, "def"), 0)


class RecordingTests(unittest.TestCase):
    def test_step_without_a_records_store_is_unrecorded(self):
        engine = orchestrator.Orchestrator(
            records=None,
            guardrail_status={"calls": 1, "est_cost_usd": 0.01,
                              "remaining_usd": 1.0})
        decision = engine.step(record([]))
        self.assertEqual(decision["decision"], "investigate")
        self.assertEqual(decision["incident_id"], "incident-missing")


if __name__ == "__main__":
    unittest.main()
