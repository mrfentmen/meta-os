"""OS-091: budget forecasting + preemption (pause, never kill).

OS-091's acceptance is twofold: a forecast line appears in
the daily brief with a stated confidence basis, and a
preempted job resumes cleanly when budget frees. These tests
pin both into the suite: the pure forecast math in
intel/forecast.py, the preempt/resume decisions, the brief
line through the real renderer, and the drill script as a
subprocess (so the drill's own PASS lines are part of the
suite, not just a transcript somebody eyeballed once).

The live ledger, the live daily brief run, and a real worker
pause are deliberately NOT pinned here: there is no spend
ledger in Redis for a forecast to read, no daily brief run
fills a forecast section yet, and no worker pause path exists
for a decision to drive. The drill's fake queue proves the
decisions; the live wiring is owed on those callers and named
as NOT proven in intel/evals/budget_forecast.md.
"""

import subprocess
import sys
import unittest

sys.path.insert(0, ".")

from intel import budgets
from intel import forecast


class ForecastMathTest(unittest.TestCase):
    def test_projection_scales_the_ledger_rate(self):
        self.assertEqual(forecast.project_end_of_day(80, 8), 240.0)
        self.assertEqual(forecast.project_end_of_day(50, 12), 100.0)

    def test_projection_at_or_past_day_end_is_spent(self):
        self.assertEqual(forecast.project_end_of_day(90, 24), 90.0)
        self.assertEqual(forecast.project_end_of_day(90, 30), 90.0)

    def test_unprojectable_inputs_yield_none(self):
        self.assertIsNone(forecast.project_end_of_day(-5, 8))
        self.assertIsNone(forecast.project_end_of_day(80, 0))
        self.assertIsNone(forecast.project_end_of_day(80, -2))
        self.assertIsNone(forecast.project_end_of_day("lots", 8))
        self.assertIsNone(forecast.project_end_of_day(80, 8, 0))

    def test_confidence_comes_from_elapsed_hours_alone(self):
        self.assertEqual(forecast.confidence_for(2), "low")
        self.assertEqual(forecast.confidence_for(4), "medium")
        self.assertEqual(forecast.confidence_for(8), "medium")
        self.assertEqual(forecast.confidence_for(12), "high")
        self.assertEqual(forecast.confidence_for(0), "unknown")
        self.assertEqual(forecast.confidence_for("soon"), "unknown")


class ForecastEntryTest(unittest.TestCase):
    def test_entry_carries_basis_and_verdict(self):
        entry = forecast.forecast_entry("spark", 80, 100, 8)
        self.assertEqual(entry["projected"], 240.0)
        self.assertTrue(entry["over_cap"])
        self.assertEqual(entry["confidence"], "medium")
        self.assertIn("8 hours of ledger", entry["basis"])

    def test_within_cap_entry_has_no_breach(self):
        entry = forecast.forecast_entry("spark", 20, 100, 8)
        self.assertEqual(entry["projected"], 60.0)
        self.assertFalse(entry["over_cap"])

    def test_unusable_entries_yield_none(self):
        self.assertIsNone(forecast.forecast_entry("", 80, 100, 8))
        self.assertIsNone(forecast.forecast_entry("spark", 80, 0, 8))
        self.assertIsNone(forecast.forecast_entry("spark", 80, 100, 0))
        self.assertIsNone(forecast.forecast_entry("spark", None, 100, 8))


class ForecastLinesTest(unittest.TestCase):
    def test_line_names_figures_basis_confidence_verdict(self):
        lines = forecast.forecast_lines(
            [{"lane": "spark", "spent": 80, "cap": 100,
              "elapsed_hours": 8}])
        self.assertEqual(len(lines), 1)
        self.assertIn("80 spent of 100 cap", lines[0])
        self.assertIn("projected 240", lines[0])
        self.assertIn("8 hours of ledger", lines[0])
        self.assertIn("medium confidence", lines[0])
        self.assertIn("breach expected before end of day", lines[0])
        self.assertFalse(lines[0].lstrip().startswith(("-", "*")))

    def test_within_cap_line_says_within_cap(self):
        lines = forecast.forecast_lines(
            [{"lane": "spark", "spent": 20, "cap": 100,
              "elapsed_hours": 8}])
        self.assertIn("within cap", lines[0])

    def test_unusable_entries_and_empty_input_yield_no_lines(self):
        lines = forecast.forecast_lines(
            [{"lane": "spark", "spent": 80, "cap": 100,
              "elapsed_hours": 0},
             {"lane": "", "spent": 80, "cap": 100,
              "elapsed_hours": 8},
             "not-a-dict"])
        self.assertEqual(lines, [])
        self.assertEqual(forecast.forecast_lines([]), [])


class PreemptDecisionTest(unittest.TestCase):
    def test_pause_only_low_running_in_warning_lane(self):
        low = {"priority": "low", "status": "running"}
        self.assertEqual(
            forecast.preempt_decision(low, "warning"), "pause")
        self.assertIsNone(
            forecast.preempt_decision(low, "ok"))
        self.assertIsNone(
            forecast.preempt_decision(low, "capped"))
        self.assertIsNone(
            forecast.preempt_decision(low, "unbudgeted"))

    def test_high_priority_never_paused(self):
        high = {"priority": "high", "status": "running"}
        self.assertIsNone(
            forecast.preempt_decision(high, "warning"))

    def test_already_paused_never_paused_twice(self):
        paused = {"priority": "low", "status": "paused"}
        self.assertIsNone(
            forecast.preempt_decision(paused, "warning"))

    def test_resume_only_when_budget_freed(self):
        paused = {"priority": "low", "status": "paused"}
        self.assertEqual(
            forecast.preempt_decision(paused, "ok"), "resume")
        self.assertEqual(
            forecast.preempt_decision(paused, "unbudgeted"), "resume")
        self.assertIsNone(
            forecast.preempt_decision(paused, "warning"))
        self.assertIsNone(
            forecast.preempt_decision(paused, "capped"))

    def test_malformed_job_yields_none(self):
        self.assertIsNone(forecast.preempt_decision(None, "warning"))
        self.assertIsNone(
            forecast.preempt_decision({"status": "running"}, "warning"))

    def test_pause_decision_uses_the_os085_warning_band(self):
        # The decision's "warning" state is exactly budgets.py's:
        # 80/100 is warning, 79/100 is ok, 100/100 is capped.
        self.assertEqual(
            budgets.budget_state({"lane": "x", "spent": 80,
                                  "cap": 100}), "warning")
        self.assertEqual(
            forecast.preempt_decision(
                {"priority": "low", "status": "running"},
                budgets.budget_state({"lane": "x", "spent": 80,
                                      "cap": 100})), "pause")

    def test_preempt_record_names_job_lane_action(self):
        record = forecast.preempt_record("job-1", "spark", "paused",
                                         "lane at warning")
        self.assertEqual(record["job"], "job-1")
        self.assertEqual(record["lane"], "spark")
        self.assertEqual(record["action"], "paused")


class BudgetForecastDrillTest(unittest.TestCase):
    def test_drill_passes(self):
        result = subprocess.run(
            [sys.executable, "intel/drills/budget_forecast.py"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("budget forecast drill complete (5/5 phases)",
                      result.stdout)


if __name__ == "__main__":
    unittest.main()
