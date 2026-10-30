"""intel/brief.py: OS-117 follow-up — with_federation,
the morning-path caller.

Before this change no caller in the repo filled
`federation`: a morning brief carried its Federation
section only when the snapshot hand-stated a
"federation" record, and a snapshot that only
carried the joined machines carried no section at
all. Now the morning path fills the record first:
machines from the snapshot's own stated
joined_machines list (names, completions verbatim,
cross-machine jobs with id, title, and status), and
trust events from the snapshot's own stated
trust_events list (joins and refusals), with one
as_of stamp for the whole record. A snapshot that
hand-states a record keeps it untouched, and a
snapshot that states fewer than two usable machines
gets no record added, so older briefs keep their
exact shape. A machine named twice is one machine,
not two, and malformed entries are skipped, never
guessed.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import brief  # noqa: E402


SNAPSHOT = {
    "messages": [],
    "joined_machines": [
        {"name": "machine-a",
         "completions": ["brief panel", "dispatch poster"],
         "cross_machine_jobs": [{"id": "3", "title": "watchdog loop",
                                  "status": "claimed"}]},
        {"name": "machine-b",
         "completions": ["board grouping"],
         "cross_machine_jobs": []}],
    "trust_events": [
        {"kind": "refusal", "machine": "machine-c",
         "detail": "unsigned job refused"},
        {"kind": "join", "machine": "machine-b",
         "detail": "signed jobs accepted"}],
}


class WithFederationTest(unittest.TestCase):
    def test_fills_machines_and_trust_events_with_one_stamp(self):
        filled = brief.with_federation(SNAPSHOT, now=1793093400)
        record = filled["federation"]
        self.assertEqual(record["as_of"], 1793093400)
        self.assertEqual(record["machines"],
                         [{"name": "machine-a",
                           "completions": ["brief panel",
                                           "dispatch poster"],
                           "cross_machine_jobs": [
                               {"id": "3", "title": "watchdog loop",
                                "status": "claimed"}]},
                          {"name": "machine-b",
                           "completions": ["board grouping"]}])
        self.assertEqual(record["trust_events"],
                         [{"kind": "refusal", "machine": "machine-c",
                           "detail": "unsigned job refused"},
                          {"kind": "join", "machine": "machine-b",
                           "detail": "signed jobs accepted"}])

    def test_filled_record_renders_federation_section_lines(self):
        filled = brief.with_federation(SNAPSHOT, now=1793093400)
        lines = brief.federation_lines(filled["federation"])
        self.assertIn("machine-a: completed brief panel, "
                      "dispatch poster", lines[0])
        self.assertIn("job 3 watchdog loop (claimed)", lines[0])
        self.assertIn("machine-b: completed board grouping",
                      lines[1])
        self.assertIn("machine-c was refused: unsigned job "
                      "refused", lines[2])
        self.assertIn("machine-b joined the federation: signed "
                      "jobs accepted", lines[3])

    def test_hand_stated_record_wins_unchanged(self):
        stated = {"machines": [{"name": "machine-a"},
                               {"name": "machine-b"}],
                  "as_of": 1793093400}
        filled = brief.with_federation(
            {"federation": stated,
             "joined_machines": SNAPSHOT["joined_machines"]},
            now=1793093400)
        self.assertEqual(filled["federation"], stated)

    def test_caller_snapshot_is_never_mutated(self):
        original = dict(SNAPSHOT)
        brief.with_federation(SNAPSHOT, now=1793093400)
        self.assertEqual(SNAPSHOT, original)
        self.assertNotIn("federation", SNAPSHOT)

    def test_single_machine_gets_no_record(self):
        filled = brief.with_federation(
            {"joined_machines": [{"name": "machine-a",
                                   "completions": ["brief panel"]}],
             "trust_events": [{"kind": "join", "machine": "machine-a",
                                "detail": "signed jobs accepted"}]},
            now=1793093400)
        self.assertNotIn("federation", filled)

    def test_snapshot_with_nothing_usable_gets_no_record(self):
        filled = brief.with_federation(
            {"joined_machines": [], "trust_events": []},
            now=1793093400)
        self.assertNotIn("federation", filled)
        filled = brief.with_federation({"messages": []},
                                       now=1793093400)
        self.assertNotIn("federation", filled)

    def test_malformed_entries_skipped_never_guessed(self):
        filled = brief.with_federation(
            {"joined_machines": [
                {"completions": ["no name, no machine"]},
                {"name": "machine-a",
                 "completions": ["brief panel", "", 7],
                 "cross_machine_jobs": [
                     {"title": "no id, skipped"},
                     {"id": "3"},
                     {"id": "4", "title": "watchdog loop",
                      "status": ""}]},
                {"name": "machine-b", "completions": []}],
             "trust_events": [
                 {"kind": "join", "detail": "no machine, skipped"},
                 {"kind": "mystery", "machine": "machine-c",
                  "detail": "unknown kind, skipped"},
                 {"kind": "refusal", "machine": "machine-c"}]},
            now=1793093400)
        record = filled["federation"]
        self.assertEqual(record["machines"],
                         [{"name": "machine-a",
                           "completions": ["brief panel"],
                           "cross_machine_jobs": [
                               {"id": "4",
                                "title": "watchdog loop"}]},
                          {"name": "machine-b"}])
        self.assertEqual(record["trust_events"],
                         [{"kind": "refusal",
                           "machine": "machine-c"}])

    def test_machine_named_twice_is_one_machine(self):
        filled = brief.with_federation(
            {"joined_machines": [
                {"name": "machine-a",
                 "completions": ["brief panel"]},
                {"name": "machine-a",
                 "completions": ["a second listing"]},
                {"name": "machine-b",
                 "completions": ["board grouping"]}]},
            now=1793093400)
        self.assertEqual(
            [machine["name"]
             for machine in filled["federation"]["machines"]],
            ["machine-a", "machine-b"])
        self.assertEqual(
            filled["federation"]["machines"][0]["completions"],
            ["brief panel"])

    def test_machine_with_no_completions_reads_none_reported(self):
        filled = brief.with_federation(
            {"joined_machines": [
                {"name": "machine-a"},
                {"name": "machine-b",
                 "completions": ["board grouping"]}]},
            now=1793093400)
        lines = brief.federation_lines(filled["federation"])
        self.assertIn("machine-a: no completions reported",
                      lines[0])

    def test_refusal_without_detail_reads_reason_not_reported(self):
        filled = brief.with_federation(
            {"joined_machines": [
                {"name": "machine-a"},
                {"name": "machine-b"}],
             "trust_events": [{"kind": "refusal",
                                "machine": "machine-c"}]},
            now=1793093400)
        lines = brief.federation_lines(filled["federation"])
        self.assertIn("machine-c was refused (reason not "
                      "reported)", lines[-1])

    def test_morning_template_brief_over_filled_snapshot_carries_section(self):
        filled = brief.with_federation(SNAPSHOT, now=1793093400)
        text, _record = brief.generate_morning_brief(
            filled, "build", now=1793093400, dry_run=True)
        self.assertIn("Federation", text)
        self.assertIn("machine-a: completed brief panel, "
                      "dispatch poster", text)
        self.assertIn("machine-c was refused: unsigned job "
                      "refused", text)

    def test_default_stamp_is_an_int_when_now_is_not_given(self):
        filled = brief.with_federation(SNAPSHOT)
        self.assertIsInstance(filled["federation"]["as_of"], int)

    def test_non_dict_snapshot_gets_no_record(self):
        self.assertEqual(brief.with_federation(None), {})


if __name__ == "__main__":
    unittest.main()
