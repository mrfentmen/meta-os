"""Missing-case tests for the budget governor (B236).

Covers the boundaries tests/test_intel_budget_gate.py does not:
boolean and float inputs, the exact warning edge, overspend, the env
fallback, and every state precedence.

Run with: python3 -m pytest tests/queue-python/test_budget_governor_missing.py -q
"""
import importlib.util
import os
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_SPEC = importlib.util.spec_from_file_location(
    "intel_budgets", os.path.join(REPO, "os", "intel", "budgets.py"))
budgets = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(budgets)


class EnvIntTests(unittest.TestCase):
    def test_missing_blank_and_out_of_range_fall_back(self):
        for raw in (None, "", "abc", "0", "101", "-1"):
            env = {} if raw is None else {"TEST_BUDGET_INT": raw}
            with unittest.mock.patch.dict(os.environ, env, clear=True):
                self.assertEqual(
                    budgets._env_int("TEST_BUDGET_INT", 7, 1, 100), 7, raw)

    def test_valid_value_is_stripped_and_used(self):
        with unittest.mock.patch.dict(
                os.environ, {"TEST_BUDGET_INT": " 42 "}, clear=True):
            self.assertEqual(
                budgets._env_int("TEST_BUDGET_INT", 7, 1, 100), 42)


class SpendRatioTests(unittest.TestCase):
    def test_booleans_and_floats_are_not_usable_integers(self):
        self.assertIsNone(budgets.spend_ratio(True, 10))
        self.assertIsNone(budgets.spend_ratio(1, False))
        self.assertIsNone(budgets.spend_ratio(1.0, 10))
        self.assertIsNone(budgets.spend_ratio(1, 10.0))

    def test_zero_or_negative_cap_and_negative_spend_have_no_ratio(self):
        self.assertIsNone(budgets.spend_ratio(0, 0))
        self.assertIsNone(budgets.spend_ratio(0, -5))
        self.assertIsNone(budgets.spend_ratio(-1, 10))

    def test_overspend_is_a_ratio_above_one(self):
        self.assertEqual(budgets.spend_ratio(15, 10), 1.5)


class ThresholdTests(unittest.TestCase):
    def test_warning_band_is_inclusive_at_the_threshold_and_exclusive_at_cap(self):
        self.assertTrue(budgets.at_warning(8, 10))
        self.assertFalse(budgets.at_warning(7, 10))
        self.assertFalse(budgets.at_warning(10, 10))
        self.assertFalse(budgets.at_warning(11, 10))

    def test_at_cap_includes_overspend_and_refuses_unusable_input(self):
        self.assertTrue(budgets.at_cap(10, 10))
        self.assertTrue(budgets.at_cap(11, 10))
        self.assertFalse(budgets.at_cap(9, 10))
        self.assertFalse(budgets.at_cap(0, 0))
        self.assertFalse(budgets.at_cap(1.0, 10))

    def test_claim_allowed_is_the_inverse_of_at_cap(self):
        self.assertFalse(budgets.claim_allowed(10, 10))
        self.assertTrue(budgets.claim_allowed(9, 10))
        self.assertTrue(budgets.claim_allowed(None, 10))

    def test_explicit_zero_percent_warns_on_any_spend(self):
        self.assertTrue(budgets.at_warning(0, 10, warn_percent=0))


class StateTests(unittest.TestCase):
    def test_capped_wins_over_warning(self):
        self.assertEqual(
            budgets.budget_state({"spent": 10, "cap": 10}), "capped")

    def test_warning_then_ok_then_unbudgeted(self):
        self.assertEqual(
            budgets.budget_state({"spent": 8, "cap": 10}), "warning")
        self.assertEqual(
            budgets.budget_state({"spent": 1, "cap": 10}), "ok")
        self.assertEqual(
            budgets.budget_state({"spent": 1, "cap": 0}), "unbudgeted")
        self.assertEqual(budgets.budget_state("not an entry"), "unbudgeted")

    def test_snapshot_accepts_a_tuple_and_skips_unusable_entries(self):
        good = {"lane": "HANA", "spent": 1, "cap": 2}
        entries = budgets.budgets_from_snapshot({"budgets": (
            good,
            "not a dict",
            {"lane": "", "spent": 1, "cap": 2},
            {"lane": None, "spent": 1, "cap": 2},
        )})
        self.assertEqual(entries, [good])

    def test_snapshot_missing_or_non_list_yields_no_entries(self):
        self.assertEqual(budgets.budgets_from_snapshot(None), [])
        self.assertEqual(budgets.budgets_from_snapshot({}), [])
        self.assertEqual(
            budgets.budgets_from_snapshot({"budgets": "HANA"}), [])

    def test_hold_entry_sets_the_flag_from_the_cap(self):
        self.assertFalse(budgets.hold_entry("HANA", 1, 10)["held"])
        self.assertTrue(budgets.hold_entry("HANA", 10, 10)["held"])


if __name__ == "__main__":
    unittest.main()
