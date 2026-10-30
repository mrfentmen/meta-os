"""intel/brief.py: INT-027 follow-up — with_priority_order,
the morning-path caller.

Before this change no caller in the repo filled
`priority_order`: a morning brief carried its Priority
order section only when the snapshot hand-stated a
"priority_order" record, and a snapshot that only
carried the order as a plain priority_ids list carried
no section at all. Now the morning path fills the
record first: order from the snapshot's own stated
priority_ids list, in stated order, with one as_of
stamp for the whole record. A snapshot that hand-states
a record keeps it untouched, and a snapshot that states
no usable id gets no record added, so older briefs keep
their exact shape. A job id named twice is one entry,
and malformed ids are skipped, never guessed. The caller
does not filter ids against the snapshot's jobs list:
the renderer already skips an id with no matching job.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import brief  # noqa: E402


SNAPSHOT = {
    "messages": [],
    "jobs": [{"id": "7", "title": "spark client", "status": "open"},
             {"id": "3", "title": "brief panel", "status": "claimed"},
             {"id": "9", "title": "watchdog loop", "status": "open"}],
    "priority_ids": ["3", "7", "3"],
}


class WithPriorityOrderTest(unittest.TestCase):
    def test_fills_order_with_one_stamp(self):
        filled = brief.with_priority_order(SNAPSHOT, now=1793093400)
        record = filled["priority_order"]
        self.assertEqual(record["as_of"], 1793093400)
        self.assertEqual(record["order"], ["3", "7"])

    def test_filled_record_renders_priority_lines_in_order(self):
        filled = brief.with_priority_order(SNAPSHOT, now=1793093400)
        lines = brief.priority_order_lines(
            filled["priority_order"], SNAPSHOT["jobs"])
        self.assertIn("Priority 1: 3 brief panel", lines[0])
        self.assertIn("Priority 2: 7 spark client", lines[1])
        self.assertEqual(len(lines), 2)

    def test_morning_template_brief_over_filled_snapshot_carries_section(self):
        filled = brief.with_priority_order(SNAPSHOT, now=1793093400)
        text = brief.compose_template_brief(filled)
        self.assertIn("Priority order", text)
        self.assertIn("Priority 1: 3 brief panel", text)
        self.assertIn("Priority 2: 7 spark client", text)

    def test_morning_brief_via_generate_carries_section(self):
        filled = brief.with_priority_order(SNAPSHOT, now=1793093400)
        text, _record = brief.generate_brief(
            filled, "build", kind="morning", now=1793093400,
            dry_run=True)
        self.assertIn("Priority 1: 3 brief panel", text)
        self.assertIn("Priority 2: 7 spark client", text)

    def test_unfilled_snapshot_carries_no_priority_section(self):
        snapshot = {"messages": [], "jobs": SNAPSHOT["jobs"]}
        text = brief.compose_template_brief(snapshot)
        self.assertNotIn("Priority order", text)

    def test_hand_stated_record_wins_unchanged(self):
        stated = {"order": ["9"], "as_of": 1793093000}
        filled = brief.with_priority_order(
            {"priority_order": stated, "priority_ids": ["3", "7"]},
            now=1793093400)
        self.assertEqual(filled["priority_order"], stated)

    def test_caller_snapshot_is_never_mutated(self):
        original = dict(SNAPSHOT)
        brief.with_priority_order(SNAPSHOT, now=1793093400)
        self.assertEqual(SNAPSHOT, original)
        self.assertNotIn("priority_order", SNAPSHOT)

    def test_snapshot_with_nothing_usable_gets_no_record(self):
        filled = brief.with_priority_order({"messages": []},
                                           now=1793093400)
        self.assertNotIn("priority_order", filled)
        filled = brief.with_priority_order(
            {"priority_ids": "3, 7"}, now=1793093400)
        self.assertNotIn("priority_order", filled)

    def test_id_listed_twice_is_one_entry(self):
        filled = brief.with_priority_order(
            {"priority_ids": ["3", "7", "3", "7"]},
            now=1793093400)
        self.assertEqual(filled["priority_order"]["order"], ["3", "7"])

    def test_malformed_ids_skipped_never_guessed(self):
        filled = brief.with_priority_order(
            {"priority_ids": ["3", "", 7, None, "7"]},
            now=1793093400)
        self.assertEqual(filled["priority_order"]["order"], ["3", "7"])

    def test_junk_only_list_builds_no_record(self):
        filled = brief.with_priority_order(
            {"priority_ids": ["", 7, None, True]},
            now=1793093400)
        self.assertNotIn("priority_order", filled)

    def test_empty_list_builds_no_record(self):
        filled = brief.with_priority_order({"priority_ids": []},
                                           now=1793093400)
        self.assertNotIn("priority_order", filled)

    def test_unknown_id_kept_for_renderer_to_read_none_reported(self):
        filled = brief.with_priority_order({"priority_ids": ["99"]},
                                           now=1793093400)
        self.assertEqual(filled["priority_order"]["order"], ["99"])
        text = brief.compose_template_brief(
            dict(filled, jobs=SNAPSHOT["jobs"]))
        self.assertIn("Priority order: none reported", text)

    def test_default_stamp_is_an_int_when_now_is_not_given(self):
        filled = brief.with_priority_order(SNAPSHOT)
        self.assertIsInstance(filled["priority_order"]["as_of"], int)

    def test_non_dict_snapshot_gets_no_record(self):
        self.assertEqual(brief.with_priority_order(None), {})


if __name__ == "__main__":
    unittest.main()
