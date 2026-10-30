"""intel/brief.py: OS-103 follow-up — environment_budget_record.

Before this change no caller in the repo filled the
environment record's budget part from a budgets list:
the OS-103 Budget line rendered only from a hand-stated
record, and build_environment_record left it out, so a
merged record always read not reported for budget.
Now environment_budget_record reads the lane's figures
out of the snapshot's own budgets list (the OS-079
entries: lane, spent, cap, or remaining), and
build_environment_record merges that part in with one
stamp, so a boot brief over a merged record carries the
Budget line. The figures are the snapshot's stated
figures, never a live ledger: there is still no spend
ledger in this repo, so a snapshot with no budgets list
still reads not reported, and a malformed entry is
skipped, never guessed into a figure.
"""

import sys
import tempfile
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import brief  # noqa: E402


BUDGETS = [
    {"lane": "HANA", "spent": 120, "cap": 300},
    {"lane": "MILO", "spent": 50, "cap": 200},
]


class EnvironmentBudgetRecordTest(unittest.TestCase):
    def test_spent_and_cap_record_renders_remaining_with_cap(self):
        record = brief.environment_budget_record(
            BUDGETS, lane="HANA", now=1793093400)
        self.assertEqual(record["lane"], "HANA")
        self.assertEqual(record["spent"], 120)
        self.assertEqual(record["cap"], 300)
        self.assertEqual(record["as_of"], 1793093400)
        lines = brief.environment_lines(
            {"budget": record, "as_of": 1793093400})
        self.assertIn("Budget: HANA lane: 180 remaining of 300 cap",
                      lines[3])

    def test_named_lane_picked_among_many_unknown_lane_is_none(self):
        record = brief.environment_budget_record(
            BUDGETS, lane="MILO", now=1793093400)
        self.assertEqual(record["lane"], "MILO")
        lines = brief.environment_lines(
            {"budget": record, "as_of": 1793093400})
        self.assertIn("Budget: MILO lane: 150 remaining of 200 cap",
                      lines[3])
        self.assertIsNone(brief.environment_budget_record(
            BUDGETS, lane="PAX", now=1793093400))

    def test_no_lane_takes_first_usable_entry(self):
        record = brief.environment_budget_record(
            [{"lane": "", "spent": 1, "cap": 2}, BUDGETS[1]],
            now=1793093400)
        self.assertEqual(record["lane"], "MILO")

    def test_remaining_direct_renders_without_cap_part(self):
        record = brief.environment_budget_record(
            [{"lane": "HANA", "remaining": 75}], now=1793093400)
        self.assertEqual(record["remaining"], 75)
        self.assertNotIn("cap", record)
        lines = brief.environment_lines(
            {"budget": record, "as_of": 1793093400})
        self.assertIn("Budget: HANA lane: 75 remaining", lines[3])
        self.assertNotIn("cap", lines[3])

    def test_malformed_entries_skipped_never_guessed(self):
        malformed = [
            {"lane": "HANA", "spent": True, "cap": 300},
            {"lane": "HANA", "spent": -5, "cap": 300},
            {"lane": "HANA", "spent": 10, "cap": 0},
            {"lane": "HANA", "spent": "120", "cap": 300},
            {"lane": "HANA", "cap": 300},
            {"spent": 10, "cap": 300},
            "HANA",
            None,
        ]
        self.assertIsNone(brief.environment_budget_record(
            malformed, lane="HANA", now=1793093400))
        self.assertIsNone(brief.environment_budget_record(
            None, now=1793093400))
        self.assertIsNone(brief.environment_budget_record(
            [], now=1793093400))
        lines = brief.environment_lines({})
        self.assertIn("not reported", lines[3])

    def test_overspend_kept_as_honest_negative_remaining(self):
        record = brief.environment_budget_record(
            [{"lane": "HANA", "spent": 310, "cap": 300}],
            now=1793093400)
        lines = brief.environment_lines(
            {"budget": record, "as_of": 1793093400})
        self.assertIn("Budget: HANA lane: -10 remaining of 300 cap",
                      lines[3])

    def test_builder_record_renders_budget_line_and_others(self):
        record = brief.environment_budget_record(
            BUDGETS, lane="HANA", now=1793093400)
        lines = brief.environment_lines(
            {"budget": record, "as_of": 1793093400})
        self.assertIn("Budget: HANA lane: 180 remaining", lines[3])
        self.assertIn("not reported", lines[0])
        self.assertIn("not reported", lines[1])
        self.assertIn("not reported", lines[2])

    def test_merged_record_carries_budget_with_one_stamp(self):
        with tempfile.TemporaryDirectory() as path:
            record = brief.build_environment_record(
                {"messages": [], "jobs": [], "budgets": BUDGETS},
                repo_path=path, now=1793093400, room="main",
                lane="HANA")
        self.assertEqual(record["as_of"], 1793093400)
        self.assertEqual(record["budget"]["lane"], "HANA")
        self.assertEqual(record["budget"]["as_of"], 1793093400)
        self.assertNotIn("repo", record)
        lines = brief.environment_lines(record)
        self.assertIn("Budget: HANA lane: 180 remaining of 300 cap",
                      lines[3])
        self.assertIn("0 messages", lines[1])

    def test_merged_record_without_budgets_leaves_budget_out(self):
        with tempfile.TemporaryDirectory() as path:
            record = brief.build_environment_record(
                {"jobs": []}, repo_path=path, now=1793093400,
                room="main")
        self.assertNotIn("budget", record)
        lines = brief.environment_lines(record)
        self.assertIn("not reported", lines[3])

    def test_boot_template_brief_carries_merged_budget_line(self):
        with tempfile.TemporaryDirectory() as path:
            record = brief.build_environment_record(
                {"messages": [], "jobs": [], "budgets": BUDGETS},
                repo_path=path, now=1793093400, room="main",
                lane="HANA")
        text = brief.compose_template_brief(
            {"messages": [], "jobs": [],
             "environment": record}, boot=True)
        self.assertIn("Budget: HANA lane: 180 remaining of 300 cap",
                      text)


if __name__ == "__main__":
    unittest.main()
