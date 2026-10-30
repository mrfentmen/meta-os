"""intel/brief.py: OS-075 follow-up — with_daily,
the morning-path caller.

Before this change no caller in the repo filled
`daily`: a morning brief carried its Daily brief
section only when the snapshot hand-stated a "daily"
record, and a snapshot that only carried the raw
lists carried no section at all. Now the morning
path fills the record first: overnight results from
the snapshot's own stated overnight_results list
(verbatim), today's queue from the snapshot's own
jobs list (open or claimed jobs with an id and a
title, each job once), and needs-word questions from
the snapshot's own stated needs_word list (verbatim),
with one as_of stamp for the whole record. A snapshot
that hand-states a record keeps it untouched, and a
snapshot that states nothing usable gets no record
added, so older briefs keep their exact shape.
Blocked jobs are never queue items and blocked
reasons are never questions: no question is invented
from a reason.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import brief  # noqa: E402


SNAPSHOT = {
    "messages": [],
    "jobs": [{"id": "7", "title": "boot shot", "status": "open"},
             {"id": "8", "title": "brief panel", "status": "claimed",
              "claim": "rowan"},
             {"id": "9", "title": "dispatch poster", "status": "done"}],
    "overnight_results": ["shipped the brief panel"],
    "needs_word": [{"question": "ship the demo cut?", "job": "7"}],
}


class WithDailyTest(unittest.TestCase):
    def test_fills_all_three_categories_with_one_stamp(self):
        filled = brief.with_daily(SNAPSHOT, now=1793093400)
        record = filled["daily"]
        self.assertEqual(record["as_of"], 1793093400)
        self.assertEqual(record["overnight_results"],
                         ["shipped the brief panel"])
        self.assertEqual(record["todays_queue"],
                         [{"id": "7", "title": "boot shot"},
                          {"id": "8", "title": "brief panel"}])
        self.assertEqual(record["needs_word"],
                         [{"question": "ship the demo cut?", "job": "7"}])

    def test_filled_record_renders_daily_section_lines(self):
        filled = brief.with_daily(SNAPSHOT, now=1793093400)
        lines = brief.daily_lines(filled["daily"])
        self.assertIn("Overnight result: shipped the brief panel",
                      lines[0])
        self.assertIn("Today's queue: job 7 boot shot", lines[1])
        self.assertIn("Today's queue: job 8 brief panel", lines[2])
        self.assertIn("Needs your word: ship the demo cut? (job 7)",
                      lines[3])

    def test_hand_stated_record_wins_unchanged(self):
        stated = {"overnight_results": ["Hand-stated result"],
                  "as_of": 1793093400}
        filled = brief.with_daily(
            {"daily": stated,
             "jobs": [{"id": "7", "title": "boot shot",
                       "status": "open"}]},
            now=1793093400)
        self.assertEqual(filled["daily"], stated)

    def test_caller_snapshot_is_never_mutated(self):
        original = dict(SNAPSHOT)
        brief.with_daily(SNAPSHOT, now=1793093400)
        self.assertEqual(SNAPSHOT, original)
        self.assertNotIn("daily", SNAPSHOT)

    def test_snapshot_with_nothing_usable_gets_no_record(self):
        filled = brief.with_daily(
            {"messages": [], "jobs": []}, now=1793093400)
        self.assertNotIn("daily", filled)
        self.assertEqual(set(filled), {"messages", "jobs"})

    def test_malformed_entries_skipped_never_guessed(self):
        filled = brief.with_daily({
            "jobs": [{"id": "7", "title": "boot shot", "status": "open"},
                     {"id": "7", "title": "boot shot", "status": "open"},
                     {"id": "8", "status": "open"},
                     {"title": "no id", "status": "claimed"},
                     {"id": "9", "title": "", "status": "open"},
                     "not a dict"],
            "overnight_results": ["real result", "", 42, None],
            "needs_word": ["plain question",
                           {"question": "jobless question"},
                           {"question": ""},
                           {"job": "7"},
                           42]},
            now=1793093400)
        record = filled["daily"]
        self.assertEqual(record["todays_queue"],
                         [{"id": "7", "title": "boot shot"}])
        self.assertEqual(record["overnight_results"], ["real result"])
        self.assertEqual(record["needs_word"],
                         ["plain question",
                          {"question": "jobless question"}])

    def test_blocked_job_is_neither_queue_nor_question(self):
        filled = brief.with_daily({
            "jobs": [{"id": "7", "title": "watchdog loop",
                      "status": "blocked",
                      "note": "needs the stall fixture from Buffy"}]},
            now=1793093400)
        self.assertNotIn("daily", filled)

    def test_queue_only_record_reads_other_categories_none_reported(self):
        filled = brief.with_daily({
            "jobs": [{"id": "7", "title": "boot shot", "status": "open"}]},
            now=1793093400)
        lines = brief.daily_lines(filled["daily"])
        self.assertIn("Overnight results: none reported", lines[0])
        self.assertIn("Today's queue: job 7 boot shot", lines[1])
        self.assertIn("Needs your word: none reported", lines[2])

    def test_morning_template_brief_over_filled_snapshot_carries_section(self):
        filled = brief.with_daily(SNAPSHOT, now=1793093400)
        text, _record = brief.generate_morning_brief(
            filled, "build", now=1793093400, dry_run=True)
        self.assertIn("Daily brief", text)
        self.assertIn("Overnight result: shipped the brief panel", text)
        self.assertIn("Today's queue: job 7 boot shot", text)
        self.assertIn("Needs your word: ship the demo cut? (job 7)",
                      text)

    def test_default_stamp_is_an_int_when_now_is_not_given(self):
        filled = brief.with_daily(SNAPSHOT)
        self.assertIsInstance(filled["daily"]["as_of"], int)

    def test_non_dict_snapshot_gets_no_record(self):
        self.assertEqual(brief.with_daily(None), {})


if __name__ == "__main__":
    unittest.main()
