"""Spark guardrail refusal tests (CB2-098..100). Temp state only."""
import os
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import spark_guardrail  # noqa: E402


class GuardrailTests(unittest.TestCase):
    def test_cumulative_records_add_up(self):
        path = tempfile.mktemp(suffix=".json",
                               prefix="guardrail-sum-")
        usage = {"prompt_tokens": 1_000_000,
                 "completion_tokens": 1_000_000}
        for _ in range(2):
            spark_guardrail.record("chat", "muse-spark-1.3", usage, 1,
                                   path=path)
        self.assertEqual(spark_guardrail.status(path)["calls"], 2)
        self.assertEqual(
            spark_guardrail.status(path)["est_cost_usd"], 11.0)

    def test_at_budget_is_refused_with_the_guardrail_wording(self):
        state = {"calls": 1, "est_cost_usd": 75.0, "log": []}
        with self.assertRaises(spark_guardrail.GuardrailStop) as raised:
            spark_guardrail.check(state=state)
        self.assertIn("GUARDRAIL STOP", str(raised.exception))
        self.assertIn("No call sent", str(raised.exception))

    def test_over_budget_is_refused(self):
        with self.assertRaises(spark_guardrail.GuardrailStop):
            spark_guardrail.check(
                state={"calls": 2, "est_cost_usd": 75.01, "log": []})

    def test_under_budget_is_allowed(self):
        spark_guardrail.check(
            state={"calls": 2, "est_cost_usd": 74.99, "log": []})


if __name__ == "__main__":
    unittest.main()
