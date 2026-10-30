"""intel/brief.py: BRF-019 follow-up — with_previous_brief,
the morning-path caller.

Before this change no caller in the repo filled
`previous_brief`: a morning brief carried its Since
your last brief section only when the snapshot
hand-stated a "previous_brief" record, and a snapshot
that only carried the previous brief's job statuses
as a plain stated list carried no section at all. Now
the morning path fills the record first: jobs from the
snapshot's own stated previous_brief_entries list, each
entry a job id with the status that job carried in the
previous brief, with one as_of stamp for the whole
record. A snapshot that hand-states a record keeps it
untouched, and a snapshot that states no usable id gets
no record added, so older briefs keep their exact
shape. A job id named twice is one previous entry, and
malformed entries are skipped, never guessed. No
previous status is ever read from the current jobs
list: comparing the window against itself would report
nothing changed, always.
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
    "previous_brief_entries": [
        {"id": "7", "status": "done"},
        {"id": "7", "status": "claimed"},
        {"id": "3", "status": "claimed"},
        {"id": "11", "status": "done"}],
}


class WithPreviousBriefTest(unittest.TestCase):
    def test_fills_jobs_with_one_stamp(self):
        filled = brief.with_previous_brief(SNAPSHOT, now=1793093400)
        record = filled["previous_brief"]
        self.assertEqual(record["as_of"], 1793093400)
        self.assertEqual(record["jobs"],
                         [{"id": "7", "status": "done"},
                          {"id": "3", "status": "claimed"},
                          {"id": "11", "status": "done"}])

    def test_filled_record_renders_since_lines(self):
        filled = brief.with_previous_brief(SNAPSHOT, now=1793093400)
        lines = brief.since_last_brief_lines(
            filled["previous_brief"], SNAPSHOT["jobs"])
        self.assertEqual(len(lines), 1)
        self.assertIn("Changed since your last brief: 7 "
                      "spark client: done -> blocked", lines[0])

    def test_filled_record_renders_new_job(self):
        snapshot = {
            "messages": [],
            "jobs": [{"id": "5", "title": "watchman loop",
                      "status": "claimed"}],
            "previous_brief_entries": [
                {"id": "7", "status": "done"}],
        }
        filled = brief.with_previous_brief(snapshot, now=1793093400)
        lines = brief.since_last_brief_lines(
            filled["previous_brief"], snapshot["jobs"])
        self.assertIn("New since your last brief: 5 "
                      "watchman loop (claimed)", lines[0])

    def test_morning_template_brief_over_filled_snapshot_carries_section(self):
        filled = brief.with_previous_brief(SNAPSHOT, now=1793093400)
        text = brief.compose_template_brief(filled)
        self.assertIn("Since your last brief", text)
        self.assertIn("done -> blocked", text)

    def test_morning_brief_via_generate_carries_section(self):
        filled = brief.with_previous_brief(SNAPSHOT, now=1793093400)
        text, _record = brief.generate_brief(
            filled, "build", kind="morning", now=1793093400,
            dry_run=True)
        self.assertIn("done -> blocked", text)

    def test_unfilled_snapshot_carries_no_since_section(self):
        snapshot = {"messages": [], "jobs": SNAPSHOT["jobs"]}
        text = brief.compose_template_brief(snapshot)
        self.assertNotIn("Since your last brief", text)

    def test_hand_stated_record_wins_unchanged(self):
        stated = {"jobs": [{"id": "7", "status": "open"}],
                  "as_of": 1793093000}
        filled = brief.with_previous_brief(
            {"previous_brief": stated,
             "previous_brief_entries": [
                 {"id": "7", "status": "done"}]},
            now=1793093400)
        self.assertEqual(filled["previous_brief"], stated)

    def test_caller_snapshot_is_never_mutated(self):
        original = dict(SNAPSHOT)
        brief.with_previous_brief(SNAPSHOT, now=1793093400)
        self.assertEqual(SNAPSHOT, original)
        self.assertNotIn("previous_brief", SNAPSHOT)

    def test_snapshot_with_nothing_usable_gets_no_record(self):
        filled = brief.with_previous_brief({"messages": []},
                                           now=1793093400)
        self.assertNotIn("previous_brief", filled)
        filled = brief.with_previous_brief(
            {"previous_brief_entries": "7 done"},
            now=1793093400)
        self.assertNotIn("previous_brief", filled)

    def test_id_listed_twice_is_one_entry_first_status_wins(self):
        filled = brief.with_previous_brief(
            {"previous_brief_entries": [
                {"id": "7", "status": "done"},
                {"id": "7", "status": "claimed"}]},
            now=1793093400)
        self.assertEqual(filled["previous_brief"]["jobs"],
                         [{"id": "7", "status": "done"}])

    def test_malformed_entries_skipped_never_guessed(self):
        filled = brief.with_previous_brief(
            {"previous_brief_entries": [
                {"id": "7", "status": "done"},
                {"id": ""},
                {"id": 7, "status": "claimed"},
                None, "7 done", {"status": "open"}]},
            now=1793093400)
        self.assertEqual(filled["previous_brief"]["jobs"],
                         [{"id": "7", "status": "done"}])

    def test_junk_only_list_builds_no_record(self):
        filled = brief.with_previous_brief(
            {"previous_brief_entries": [None, {"id": ""},
                                        {"status": "done"}]},
            now=1793093400)
        self.assertNotIn("previous_brief", filled)

    def test_entry_without_status_is_still_usable(self):
        filled = brief.with_previous_brief(
            {"previous_brief_entries": [{"id": "7", "status": ""}]},
            now=1793093400)
        self.assertEqual(filled["previous_brief"]["jobs"],
                         [{"id": "7"}])
        lines = brief.since_last_brief_lines(
            filled["previous_brief"],
            [{"id": "7", "title": "spark client",
              "status": "blocked"}])
        self.assertIn("Changed since your last brief: 7 "
                      "spark client:  -> blocked", lines[0])

    def test_previous_statuses_never_read_from_current_jobs(self):
        filled = brief.with_previous_brief(
            {"messages": [], "jobs": SNAPSHOT["jobs"],
             "previous_brief_entries": [
                 {"id": "7", "status": "done"}]},
            now=1793093400)
        self.assertEqual(filled["previous_brief"]["jobs"],
                         [{"id": "7", "status": "done"}])

    def test_default_stamp_is_an_int(self):
        filled = brief.with_previous_brief(
            {"previous_brief_entries": [{"id": "7"}]})
        self.assertIsInstance(filled["previous_brief"]["as_of"], int)

    def test_non_dict_snapshot_gets_no_record_and_never_raises(self):
        filled = brief.with_previous_brief("not a snapshot",
                                           now=1793093400)
        self.assertEqual(filled, {})
        filled = brief.with_previous_brief(None, now=1793093400)
        self.assertEqual(filled, {})


if __name__ == "__main__":
    unittest.main()
