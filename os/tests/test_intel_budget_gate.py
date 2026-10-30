"""OS-085: budget config, pre-limit warnings, and the claim hold.

OS-085's acceptance is threefold: a fixture lane driven to
its warning threshold produces a budget warning alert; at
cap, the queue holds new claims for that lane; and the hold
is visible in the brief's budget line (OS-079). These tests
pin all three into the suite: the pure gate functions in
intel/budgets.py, the watchdog detector through a tick, the
brief line through the real renderer, and the drill script
as a subprocess (so the drill's own PASS lines are part of
the suite, not just a transcript somebody eyeballed once).

The live jobs.py claim path is deliberately NOT pinned
here: there is no spend ledger in Redis for it to read,
so wiring the gate into cmd_claim would refuse or allow
claims on figures nobody writes. The drill's fake queue
proves the gate; the live wiring is owed on the ledger
and named as NOT proven in intel/evals/budget_gate.md.
"""

import subprocess
import sys
import unittest

sys.path.insert(0, ".")

from intel import brief
from intel import budgets
from intel import watchdog


class BudgetGateFunctionsTest(unittest.TestCase):
    def test_warning_band_is_threshold_to_cap_exclusive(self):
        self.assertFalse(budgets.at_warning(79, 100))
        self.assertTrue(budgets.at_warning(80, 100))
        self.assertTrue(budgets.at_warning(99, 100))
        self.assertFalse(budgets.at_warning(100, 100))

    def test_cap_includes_overspend(self):
        self.assertFalse(budgets.at_cap(99, 100))
        self.assertTrue(budgets.at_cap(100, 100))
        self.assertTrue(budgets.at_cap(150, 100))

    def test_claim_gate_follows_cap_only(self):
        self.assertTrue(budgets.claim_allowed(99, 100))
        self.assertTrue(budgets.claim_allowed(80, 100))
        self.assertFalse(budgets.claim_allowed(100, 100))
        self.assertTrue(budgets.claim_allowed(None, None))

    def test_unbudgeted_and_malformed_are_never_warned_or_held(self):
        self.assertFalse(budgets.at_warning(None, None))
        self.assertFalse(budgets.at_cap(None, None))
        self.assertFalse(budgets.at_warning("lots", "none"))
        self.assertFalse(budgets.at_cap(90, 0))
        self.assertFalse(budgets.at_cap(-5, 100))
        self.assertEqual(budgets.budget_state({"lane": "x"}),
                         "unbudgeted")
        self.assertEqual(budgets.budget_state("not-a-dict"),
                         "unbudgeted")

    def test_budget_state_names_all_three_states(self):
        self.assertEqual(
            budgets.budget_state({"lane": "s", "spent": 50,
                                  "cap": 100}), "ok")
        self.assertEqual(
            budgets.budget_state({"lane": "s", "spent": 80,
                                  "cap": 100}), "warning")
        self.assertEqual(
            budgets.budget_state({"lane": "s", "spent": 100,
                                  "cap": 100}), "capped")

    def test_hold_entry_flags_only_at_cap(self):
        self.assertFalse(budgets.hold_entry("s", 80, 100)["held"])
        self.assertTrue(budgets.hold_entry("s", 100, 100)["held"])


class BudgetWarningDetectorTest(unittest.TestCase):
    NOW = 100000

    def _snapshot(self, spent, cap=100):
        return {"jobs": [], "messages": [], "presence": [],
                "caps": {},
                "budgets": [{"lane": "spark", "spent": spent,
                             "cap": cap}]}

    def test_warning_fires_at_threshold_with_lane_figures(self):
        alerts = [a for a in watchdog.tick(self._snapshot(80),
                                           now=self.NOW)
                  if a["kind"] == "budget-warning"]
        self.assertEqual(len(alerts), 1)
        alert = alerts[0]
        self.assertEqual(alert["severity"], "warning")
        self.assertEqual(alert["lane"], "spark")
        self.assertEqual(alert["spent"], 80)
        self.assertEqual(alert["cap"], 100)
        self.assertEqual(alert["remaining"], 20)
        self.assertEqual(alert["dedupe_key"], "budget-warning:spark")
        self.assertIn("spark", alert["explanation"])
        self.assertIn("80", alert["explanation"])

    def test_no_warning_below_threshold_or_at_cap(self):
        for spent in (0, 70, 100, 150):
            alerts = [a for a in watchdog.tick(self._snapshot(spent),
                                               now=self.NOW)
                      if a["kind"] == "budget-warning"]
            self.assertEqual(alerts, [], f"spent={spent}")

    def test_warning_never_announces(self):
        # WDG-015: only critical alerts announce; a warning
        # accumulates silently for the brief/dashboard.
        announced = []
        watchdog.tick(self._snapshot(80), now=self.NOW,
                      announce=announced.append)
        self.assertEqual(announced, [])

    def test_malformed_budget_entries_do_not_crash_the_tick(self):
        snapshot = {"jobs": [], "messages": [], "presence": [],
                    "caps": {},
                    "budgets": [{"lane": "bad", "spent": "lots",
                                 "cap": "none"},
                                {"spent": 90, "cap": 100},
                                "not-a-dict"]}
        alerts = watchdog.tick(snapshot, now=self.NOW)
        self.assertEqual(
            [a for a in alerts if a["kind"] == "budget-warning"], [])


class BudgetHoldBriefLineTest(unittest.TestCase):
    def test_held_lane_line_names_the_hold(self):
        lines = brief.memory_budget_lines(
            {"budgets": [budgets.hold_entry("spark", 100, 100)]})
        held = [line for line in lines if "spark" in line]
        self.assertEqual(len(held), 1)
        self.assertIn("new claims held", held[0])
        self.assertIn("100 of 100", held[0])

    def test_unheld_lane_line_unchanged(self):
        lines = brief.memory_budget_lines(
            {"budgets": [budgets.hold_entry("spark", 80, 100)]})
        held = [line for line in lines if "spark" in line]
        self.assertEqual(len(held), 1)
        self.assertNotIn("held", held[0])

    def test_entry_without_flag_renders_as_before(self):
        lines = brief.memory_budget_lines(
            {"budgets": [{"lane": "spark", "spent": 50,
                          "cap": 100}]})
        spark = [line for line in lines if "spark" in line]
        self.assertEqual(len(spark), 1)
        self.assertNotIn("held", spark[0])


class BudgetGateDrillTest(unittest.TestCase):
    def test_drill_exits_zero_and_passes(self):
        result = subprocess.run(
            [sys.executable, "intel/drills/budget_gate.py"],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0,
                         result.stdout + result.stderr)
        self.assertIn("budget_gate drill: PASS", result.stdout)
        self.assertIn("PASS phase 1", result.stdout)
        self.assertIn("PASS phase 2", result.stdout)
        self.assertIn("PASS phase 3", result.stdout)
        self.assertIn("PASS phase 4", result.stdout)


if __name__ == "__main__":
    unittest.main()
