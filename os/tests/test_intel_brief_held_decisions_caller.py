"""intel/brief.py: INT-027 follow-up — with_held_decisions,
the morning-path caller.

Before this change no caller in the repo filled
`held_decisions`: a morning brief carried its Held
decisions section only when the snapshot hand-stated a
"held_decisions" record, and a snapshot that only
carried the waiting questions as a plain stated list
carried no section at all. Now the morning path fills
the record first: decisions from the snapshot's own
stated held_decision_entries list, each entry a question
with an optional decider nick, with one as_of stamp for
the whole record. A snapshot that hand-states a record
keeps it untouched, and a snapshot that states no
usable question gets no record added, so older briefs
keep their exact shape. A question named twice is one
decision, and malformed entries are skipped, never
guessed. No question is ever read from the jobs list:
a blocked reason or a job title is not a question
waiting on Dale's word.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import brief  # noqa: E402


SNAPSHOT = {
    "messages": [],
    "jobs": [{"id": "7", "title": "spark client", "status": "blocked"},
             {"id": "3", "title": "brief panel", "status": "claimed"}],
    "held_decision_entries": [
        {"question": "Ship the brief panel first?", "decider": "del"},
        {"question": "Ship the brief panel first?", "decider": "pax"},
        {"question": "Which gateway for the demo?"}],
}


class WithHeldDecisionsTest(unittest.TestCase):
    def test_fills_decisions_with_one_stamp(self):
        filled = brief.with_held_decisions(SNAPSHOT, now=1793093400)
        record = filled["held_decisions"]
        self.assertEqual(record["as_of"], 1793093400)
        self.assertEqual(record["decisions"],
                         [{"question": "Ship the brief panel first?",
                           "decider": "del"},
                          {"question": "Which gateway for the demo?"}])

    def test_filled_record_renders_held_lines(self):
        filled = brief.with_held_decisions(SNAPSHOT, now=1793093400)
        lines = brief.held_decisions_lines(filled["held_decisions"])
        self.assertIn("Held decision: Ship the brief panel first? "
                      "(waiting on del)", lines[0])
        self.assertIn("Held decision: Which gateway for the demo? "
                      "(decider not reported)", lines[1])
        self.assertEqual(len(lines), 2)

    def test_morning_template_brief_over_filled_snapshot_carries_section(self):
        filled = brief.with_held_decisions(SNAPSHOT, now=1793093400)
        text = brief.compose_template_brief(filled)
        self.assertIn("Held decisions", text)
        self.assertIn("Ship the brief panel first?", text)

    def test_morning_brief_via_generate_carries_section(self):
        filled = brief.with_held_decisions(SNAPSHOT, now=1793093400)
        text, _record = brief.generate_brief(
            filled, "build", kind="morning", now=1793093400,
            dry_run=True)
        self.assertIn("Ship the brief panel first?", text)

    def test_unfilled_snapshot_carries_no_held_section(self):
        snapshot = {"messages": [], "jobs": SNAPSHOT["jobs"]}
        text = brief.compose_template_brief(snapshot)
        self.assertNotIn("Held decisions", text)

    def test_hand_stated_record_wins_unchanged(self):
        stated = {"decisions": [{"question": "Keep the old panel?",
                                 "decider": "pax"}],
                  "as_of": 1793093000}
        filled = brief.with_held_decisions(
            {"held_decisions": stated,
             "held_decision_entries": [
                 {"question": "Ship the brief panel first?",
                  "decider": "del"}]},
            now=1793093400)
        self.assertEqual(filled["held_decisions"], stated)

    def test_caller_snapshot_is_never_mutated(self):
        original = dict(SNAPSHOT)
        brief.with_held_decisions(SNAPSHOT, now=1793093400)
        self.assertEqual(SNAPSHOT, original)
        self.assertNotIn("held_decisions", SNAPSHOT)

    def test_snapshot_with_nothing_usable_gets_no_record(self):
        filled = brief.with_held_decisions({"messages": []},
                                           now=1793093400)
        self.assertNotIn("held_decisions", filled)
        filled = brief.with_held_decisions(
            {"held_decision_entries": "Ship first?"},
            now=1793093400)
        self.assertNotIn("held_decisions", filled)

    def test_question_listed_twice_is_one_entry_first_decider_wins(self):
        filled = brief.with_held_decisions(
            {"held_decision_entries": [
                {"question": "Ship first?", "decider": "del"},
                {"question": "Ship first?", "decider": "pax"}]},
            now=1793093400)
        self.assertEqual(filled["held_decisions"]["decisions"],
                         [{"question": "Ship first?", "decider": "del"}])

    def test_malformed_entries_skipped_never_guessed(self):
        filled = brief.with_held_decisions(
            {"held_decision_entries": [
                {"question": "Ship first?", "decider": "del"},
                {"question": ""},
                {"question": 7, "decider": "pax"},
                None, "Ship first?", {"decider": "rowan"}]},
            now=1793093400)
        self.assertEqual(filled["held_decisions"]["decisions"],
                         [{"question": "Ship first?", "decider": "del"}])

    def test_junk_only_list_builds_no_record(self):
        filled = brief.with_held_decisions(
            {"held_decision_entries": [None, {"question": ""},
                                       {"decider": "del"}]},
            now=1793093400)
        self.assertNotIn("held_decisions", filled)

    def test_entry_without_decider_reads_decider_not_reported(self):
        filled = brief.with_held_decisions(
            {"held_decision_entries": [
                {"question": "Which gateway?", "decider": ""}]},
            now=1793093400)
        lines = brief.held_decisions_lines(filled["held_decisions"])
        self.assertIn("(decider not reported)", lines[0])

    def test_default_stamp_is_an_int(self):
        filled = brief.with_held_decisions(
            {"held_decision_entries": [{"question": "Ship first?"}]})
        self.assertIsInstance(filled["held_decisions"]["as_of"], int)

    def test_non_dict_snapshot_gets_no_record_and_never_raises(self):
        filled = brief.with_held_decisions("not a snapshot",
                                           now=1793093400)
        self.assertEqual(filled, {})
        filled = brief.with_held_decisions(None, now=1793093400)
        self.assertEqual(filled, {})


if __name__ == "__main__":
    unittest.main()
