"""intel/brief.py: OS-079 follow-up — with_memory_budget,
the brief-path caller.

Before this change no caller in the repo filled
`memory_budget`: a brief carried its settled-decisions
and spend-vs-budget lines only when the snapshot
hand-stated a "memory_budget" record, and a snapshot
that only carried the raw lists carried none of the
lines at all. Now the brief path fills the record
first: budgets from the snapshot's own budgets list
(every usable lane, in list order), settled decisions
from the snapshot's own settled_decisions list when
the caller states one, and memory_down when the
snapshot states the memory service did not answer,
with one as_of stamp for the whole record. A snapshot
that hand-states a record keeps it untouched, and a
snapshot that states nothing usable gets no record
added, so older briefs keep their exact shape.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import brief  # noqa: E402


SNAPSHOT = {
    "messages": [],
    "jobs": [],
    "budgets": [{"lane": "HANA", "spent": 120, "cap": 300},
                {"lane": "MILO", "remaining": 90, "cap": 200}],
    "settled_decisions": ["Morning brief format is final"],
}


class WithMemoryBudgetTest(unittest.TestCase):
    def test_fills_budgets_and_decisions_with_one_stamp(self):
        filled = brief.with_memory_budget(SNAPSHOT, now=1793093400)
        record = filled["memory_budget"]
        self.assertEqual(record["as_of"], 1793093400)
        self.assertEqual(record["settled_decisions"],
                         ["Morning brief format is final"])
        self.assertEqual(record["budgets"],
                         [{"lane": "HANA", "spent": 120, "cap": 300},
                          {"lane": "MILO", "remaining": 90, "cap": 200}])

    def test_filled_record_renders_settled_and_spend_lines(self):
        filled = brief.with_memory_budget(SNAPSHOT, now=1793093400)
        lines = brief.memory_budget_lines(filled["memory_budget"])
        self.assertIn("Morning brief format is final", lines[0])
        self.assertIn("Spend: HANA lane: 120 of 300 budget "
                      "(180 remaining)", lines[1])
        self.assertIn("Spend: MILO lane: 90 remaining of 200 cap",
                      lines[2])

    def test_hand_stated_record_wins_unchanged(self):
        stated = {"settled_decisions": ["Hand-stated call"],
                  "budgets": [{"lane": "HANA", "spent": 1, "cap": 2}],
                  "as_of": 1793093400}
        filled = brief.with_memory_budget(
            {"memory_budget": stated,
             "budgets": [{"lane": "MILO", "spent": 9, "cap": 9}]},
            now=1793093400)
        self.assertEqual(filled["memory_budget"], stated)

    def test_caller_snapshot_is_never_mutated(self):
        original = dict(SNAPSHOT)
        brief.with_memory_budget(SNAPSHOT, now=1793093400)
        self.assertEqual(SNAPSHOT, original)
        self.assertNotIn("memory_budget", SNAPSHOT)

    def test_snapshot_with_nothing_usable_gets_no_record(self):
        filled = brief.with_memory_budget(
            {"messages": [], "jobs": []}, now=1793093400)
        self.assertNotIn("memory_budget", filled)
        self.assertEqual(set(filled), {"messages", "jobs"})

    def test_malformed_budget_entries_skipped_never_guessed(self):
        filled = brief.with_memory_budget({
            "budgets": [{"lane": "HANA", "spent": True, "cap": 300},
                        {"lane": "MILO", "spent": -5, "cap": 300},
                        {"lane": "BUFFY", "spent": 10, "cap": 0},
                        {"spent": 10, "cap": 300},
                        {"lane": "ROWAN", "remaining": 40},
                        {"lane": "PAX", "spent": 350, "cap": 300},
                        "not a dict",
                        {"lane": "DEEP", "remaining": True}]},
            now=1793093400)
        self.assertEqual(filled["memory_budget"]["budgets"],
                         [{"lane": "ROWAN", "remaining": 40},
                          {"lane": "PAX", "spent": 350, "cap": 300}])

    def test_memory_down_passes_through_and_shows_no_decision(self):
        filled = brief.with_memory_budget(
            {"memory_down": True,
             "settled_decisions": ["Must not appear"],
             "budgets": [{"lane": "HANA", "spent": 10, "cap": 100}]},
            now=1793093400)
        record = filled["memory_budget"]
        self.assertIs(record["memory_down"], True)
        lines = brief.memory_budget_lines(record)
        self.assertIn("memory service down", lines[0])
        self.assertNotIn("Must not appear", "\n".join(lines))

    def test_morning_template_brief_over_filled_snapshot_carries_lines(self):
        filled = brief.with_memory_budget(SNAPSHOT, now=1793093400)
        text, _record = brief.generate_morning_brief(
            filled, "build", now=1793093400, dry_run=True)
        self.assertIn("Morning brief format is final", text)
        self.assertIn("Spend: HANA lane: 120 of 300 budget", text)

    def test_default_stamp_is_an_int_when_now_is_not_given(self):
        filled = brief.with_memory_budget(SNAPSHOT)
        self.assertIsInstance(filled["memory_budget"]["as_of"], int)

    def test_non_dict_snapshot_gets_no_record(self):
        self.assertEqual(brief.with_memory_budget(None), {})


if __name__ == "__main__":
    unittest.main()
