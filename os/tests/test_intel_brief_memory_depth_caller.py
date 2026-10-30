"""intel/brief.py: OS-092 follow-up — with_memory_depth,
the morning-path caller.

Before this change no caller in the repo filled
`memory_depth`: a morning brief carried its Long-term
memory section only when the snapshot hand-stated a
"memory_depth" record, and a snapshot that only
carried the raw lists carried no section at all. Now
the morning path fills the record first: aged
decisions from the snapshot's own stated
aged_decisions list, due commitments from its own
stated due_commitments list, and fresh-agent context
from its own stated fresh_context list, with one
as_of stamp for the whole record. A snapshot that
hand-states a record keeps it untouched, and a
snapshot that states nothing usable gets no record
added, so older briefs keep their exact shape. Dates
are never guessed: a dateless decision reads original
date not reported, and a dateless commitment reads
due date not reported. A down memory service is said
alone, with no item beside it.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import brief  # noqa: E402


SNAPSHOT = {
    "messages": [],
    "aged_decisions": [{"decision": "freeze the demo fixture at noon",
                        "original_date": "2026-10-01"}],
    "due_commitments": [{"commitment": "ship the demo cut",
                         "due": "2026-11-03"}],
    "fresh_context": ["the demo room is build only, "
                      "never a posting room"],
}


class WithMemoryDepthTest(unittest.TestCase):
    def test_fills_all_three_categories_with_one_stamp(self):
        filled = brief.with_memory_depth(SNAPSHOT, now=1793093400)
        record = filled["memory_depth"]
        self.assertEqual(record["as_of"], 1793093400)
        self.assertEqual(record["aged_decisions"],
                         [{"decision": "freeze the demo fixture at noon",
                           "original_date": "2026-10-01"}])
        self.assertEqual(record["due_commitments"],
                         [{"commitment": "ship the demo cut",
                           "due": "2026-11-03"}])
        self.assertEqual(record["fresh_context"],
                         ["the demo room is build only, "
                          "never a posting room"])

    def test_filled_record_renders_memory_depth_lines(self):
        filled = brief.with_memory_depth(SNAPSHOT, now=1793093400)
        lines = brief.memory_depth_lines(filled["memory_depth"])
        self.assertIn("Aged decision: freeze the demo fixture at noon "
                      "(from 2026-10-01)", lines[0])
        self.assertIn("Due commitment: ship the demo cut "
                      "(due 2026-11-03)", lines[1])
        self.assertIn("Fresh-agent context: the demo room is build only, "
                      "never a posting room", lines[2])

    def test_hand_stated_record_wins_unchanged(self):
        stated = {"aged_decisions": [{"decision": "Hand-stated decision",
                                      "original_date": "2026-09-01"}],
                  "as_of": 1793093400}
        filled = brief.with_memory_depth(
            {"memory_depth": stated,
             "aged_decisions": [{"decision": "stated list decision",
                                 "original_date": "2026-10-01"}]},
            now=1793093400)
        self.assertEqual(filled["memory_depth"], stated)

    def test_caller_snapshot_is_never_mutated(self):
        original = dict(SNAPSHOT)
        brief.with_memory_depth(SNAPSHOT, now=1793093400)
        self.assertEqual(SNAPSHOT, original)
        self.assertNotIn("memory_depth", SNAPSHOT)

    def test_snapshot_with_nothing_usable_gets_no_record(self):
        filled = brief.with_memory_depth(
            {"messages": []}, now=1793093400)
        self.assertNotIn("memory_depth", filled)
        self.assertEqual(set(filled), {"messages"})

    def test_malformed_entries_skipped_never_guessed(self):
        filled = brief.with_memory_depth({
            "aged_decisions": [{"decision": ""},
                               {"original_date": "2026-10-01"},
                               "not a dict",
                               42,
                               {"decision": "dateless decision",
                                "original_date": ""},
                               {"decision": "dated decision",
                                "original_date": 20261001}],
            "due_commitments": [{"commitment": ""},
                                {"due": "2026-11-03"},
                                {"commitment": "dateless commitment",
                                 "due": ""},
                                {"commitment": "dated commitment",
                                 "due": 20261103}],
            "fresh_context": ["real context", "", 42, None]},
            now=1793093400)
        record = filled["memory_depth"]
        self.assertEqual(record["aged_decisions"],
                         [{"decision": "dateless decision"},
                          {"decision": "dated decision"}])
        self.assertEqual(record["due_commitments"],
                         [{"commitment": "dateless commitment"},
                          {"commitment": "dated commitment"}])
        self.assertEqual(record["fresh_context"], ["real context"])
        lines = brief.memory_depth_lines(record)
        self.assertIn("Aged decision: dateless decision "
                      "(original date not reported)", lines[0])
        self.assertIn("Aged decision: dated decision "
                      "(original date not reported)", lines[1])
        self.assertIn("Due commitment: dateless commitment "
                      "(due date not reported)", lines[2])
        self.assertIn("Due commitment: dated commitment "
                      "(due date not reported)", lines[3])

    def test_memory_down_record_carries_no_item_beside_it(self):
        filled = brief.with_memory_depth(
            {"memory_down": True,
             "aged_decisions": [{"decision": "should not show",
                                 "original_date": "2026-10-01"}],
             "fresh_context": ["should not show"]},
            now=1793093400)
        self.assertEqual(filled["memory_depth"],
                         {"as_of": 1793093400, "memory_down": True})
        self.assertEqual(brief.memory_depth_lines(
            filled["memory_depth"]),
            ["Long-term memory: memory service down, "
             "so no aged decisions, due commitments, "
             "or fresh-agent context are shown"])

    def test_single_category_record_reads_other_categories_none_reported(self):
        filled = brief.with_memory_depth({
            "aged_decisions": [{"decision": "freeze the demo fixture",
                                "original_date": "2026-10-01"}]},
            now=1793093400)
        lines = brief.memory_depth_lines(filled["memory_depth"])
        self.assertIn("Aged decision: freeze the demo fixture "
                      "(from 2026-10-01)", lines[0])
        self.assertIn("Due commitments: none reported", lines[1])
        self.assertIn("Fresh-agent context: none reported", lines[2])

    def test_morning_template_brief_over_filled_snapshot_carries_section(self):
        filled = brief.with_memory_depth(SNAPSHOT, now=1793093400)
        text, _record = brief.generate_morning_brief(
            filled, "build", now=1793093400, dry_run=True)
        self.assertIn("Long-term memory", text)
        self.assertIn("Aged decision: freeze the demo fixture at noon "
                      "(from 2026-10-01)", text)
        self.assertIn("Due commitment: ship the demo cut "
                      "(due 2026-11-03)", text)
        self.assertIn("Fresh-agent context: the demo room is build only, "
                      "never a posting room", text)

    def test_default_stamp_is_an_int_when_now_is_not_given(self):
        filled = brief.with_memory_depth(SNAPSHOT)
        self.assertIsInstance(filled["memory_depth"]["as_of"], int)

    def test_non_dict_snapshot_gets_no_record(self):
        self.assertEqual(brief.with_memory_depth(None), {})


if __name__ == "__main__":
    unittest.main()
