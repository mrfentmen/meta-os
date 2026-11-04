#!/usr/bin/env python3
"""Unit tests for eval/surveyor/model_adapter.py.

Rates used here are TEST FIXTURES (plain numbers chosen to make the
arithmetic checkable), not vendor prices and not quotes for any real
provider. The operator sets real rates at run time from the provider's
current price page.

Run: python3 -m unittest discover -s eval/surveyor -p 'test_model_adapter.py'
"""

import sys
import unittest
from decimal import Decimal

sys.path.insert(0, __file__.rsplit("/test_model_adapter.py", 1)[0])

from model_adapter import (  # noqa: E402
    Budget, BudgetExceeded, ModelAdapter, RejectedInput, estimate_cost)

# Fixture rates: $2.00 / $6.00 per million tokens (test numbers only).
PROMPT_RATE = "2.00"
COMPLETION_RATE = "6.00"


def fake_transport(summary, prompt_tokens, completion_tokens):
    return {"triage": "flag-for-human", "reason": "test double"}


def good_summary():
    return {"field": "heat", "value": 34.0, "place": "block-A",
            "device_class": "node"}


def adapter(**over):
    kw = dict(prompt_rate_per_million=PROMPT_RATE,
              completion_rate_per_million=COMPLETION_RATE,
              key_present=True, transport=fake_transport)
    kw.update(over)
    return ModelAdapter(**kw)


class EstimateTests(unittest.TestCase):
    def test_exact_arithmetic(self):
        # 100k prompt + 10k completion at 2.00/6.00 per M = 0.20 + 0.06.
        self.assertEqual(
            estimate_cost(100_000, 10_000, PROMPT_RATE, COMPLETION_RATE),
            Decimal("0.26"))

    def test_zero_tokens_cost_zero(self):
        self.assertEqual(
            estimate_cost(0, 0, PROMPT_RATE, COMPLETION_RATE),
            Decimal("0"))

    def test_negative_tokens_rejected(self):
        with self.assertRaises(ValueError):
            estimate_cost(-1, 0, PROMPT_RATE, COMPLETION_RATE)

    def test_negative_rate_rejected(self):
        with self.assertRaises(ValueError):
            estimate_cost(0, 0, "-1.00", COMPLETION_RATE)

    def test_rates_required(self):
        with self.assertRaises(ValueError):
            ModelAdapter(key_present=True, transport=fake_transport)


class BudgetTests(unittest.TestCase):
    def test_charge_and_remaining(self):
        budget = Budget(Decimal("1.00"))
        budget.charge(Decimal("0.26"))
        self.assertEqual(budget.spent, Decimal("0.26"))
        self.assertEqual(budget.remaining, Decimal("0.74"))

    def test_exact_cap_allowed_then_next_refused(self):
        budget = Budget(Decimal("0.26"))
        budget.charge(Decimal("0.26"))
        self.assertEqual(budget.remaining, Decimal("0"))
        with self.assertRaises(BudgetExceeded):
            budget.charge(Decimal("0.01"))
        self.assertEqual(budget.spent, Decimal("0.26"))

    def test_refusal_charges_nothing(self):
        budget = Budget(Decimal("0.10"))
        with self.assertRaises(BudgetExceeded):
            budget.charge(Decimal("0.26"))
        self.assertEqual(budget.spent, Decimal("0"))


class AdapterTests(unittest.TestCase):
    def test_no_key_means_unconfigured_no_call_no_charge(self):
        calls = []
        ad = adapter(key_present=False,
                     transport=lambda *a: calls.append(a) or {})
        result = ad.request_verdict(good_summary(), 1000, 100)
        self.assertEqual(result["status"], "unconfigured")
        self.assertIsNone(result["verdict"])
        self.assertEqual(calls, [])
        self.assertEqual(ad.budget.spent, Decimal("0"))

    def test_no_transport_means_no_call_no_charge(self):
        ad = adapter(transport=None)
        result = ad.request_verdict(good_summary(), 1000, 100)
        self.assertEqual(result["status"], "no-transport")
        self.assertIsNone(result["verdict"])
        self.assertEqual(ad.budget.spent, Decimal("0"))

    def test_affordable_call_returns_verdict_and_charges(self):
        ad = adapter()
        result = ad.request_verdict(good_summary(), 100_000, 10_000)
        self.assertEqual(result["status"], "verdict")
        self.assertEqual(result["verdict"]["triage"], "flag-for-human")
        self.assertEqual(result["charged"], Decimal("0.26"))
        self.assertEqual(ad.budget.remaining, Decimal("0.74"))
        # A model verdict never publishes on its own.
        self.assertTrue(result["advisory_only"])
        self.assertFalse(result["publishes"])

    def test_over_budget_refused_transport_not_called_spent_unchanged(self):
        calls = []
        ad = adapter(transport=lambda *a: calls.append(a) or {},
                     budget=Budget(Decimal("0.10")))
        result = ad.request_verdict(good_summary(), 100_000, 10_000)
        self.assertEqual(result["status"], "refused-over-budget")
        self.assertIsNone(result["verdict"])
        self.assertEqual(calls, [])
        self.assertEqual(ad.budget.spent, Decimal("0"))

    def test_audio_summary_rejected_before_any_guard(self):
        ad = adapter()
        bad = good_summary()
        bad["field"] = "noise"
        bad["audio"] = "clip-bytes"
        with self.assertRaises(RejectedInput):
            ad.request_verdict(bad, 1000, 100)
        self.assertEqual(ad.budget.spent, Decimal("0"))

    def test_person_summary_rejected(self):
        ad = adapter()
        bad = good_summary()
        bad["person"] = "named individual"
        with self.assertRaises(RejectedInput):
            ad.request_verdict(bad, 1000, 100)


if __name__ == "__main__":
    unittest.main()
