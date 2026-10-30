"""intel/brief.py: INT-027 follow-up — with_blocked_contacts,
the morning-path caller.

Before this change no caller in the repo filled
`blocked_contacts`: a morning brief carried its Blocked
contacts section only when the snapshot hand-stated a
"blocked_contacts" record, and a snapshot that only
carried the ask nicks as a plain stated list carried
no section at all. Now the morning path fills the
record first: contacts from the snapshot's own stated
blocked_contact_entries list, each entry a job_id with
an optional ask nick, with one as_of stamp for the
whole record. A snapshot that hand-states a record
keeps it untouched, and a snapshot that states no
usable entry gets no record added, so older briefs keep
their exact shape. A job_id named twice is one entry,
and malformed entries are skipped, never guessed. No
nick is ever read from the jobs list: a blocked job
carries no owner field (jobs.py deletes the claim on
block), so the ask nick comes only from the stated
entries. The caller does not filter entries against
the snapshot's jobs list: the renderer already ignores
a contact for a job that is not blocked.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import brief  # noqa: E402


SNAPSHOT = {
    "messages": [],
    "jobs": [{"id": "7", "title": "spark client", "status": "blocked"},
             {"id": "3", "title": "brief panel", "status": "claimed"},
             {"id": "9", "title": "watchdog loop", "status": "blocked"}],
    "blocked_contact_entries": [{"job_id": "7", "ask": "milo"},
                                {"job_id": "7", "ask": "pax"}],
}


class WithBlockedContactsTest(unittest.TestCase):
    def test_fills_contacts_with_one_stamp(self):
        filled = brief.with_blocked_contacts(SNAPSHOT, now=1793093400)
        record = filled["blocked_contacts"]
        self.assertEqual(record["as_of"], 1793093400)
        self.assertEqual(record["contacts"],
                         [{"job_id": "7", "ask": "milo"}])

    def test_filled_record_renders_contact_lines(self):
        filled = brief.with_blocked_contacts(SNAPSHOT, now=1793093400)
        lines = brief.blocked_contact_lines(
            filled["blocked_contacts"], SNAPSHOT["jobs"])
        self.assertIn("Ask milo about 7 spark client", lines[0])
        self.assertIn("9 watchdog loop: owner not reported",
                      lines[1])
        self.assertEqual(len(lines), 2)

    def test_morning_template_brief_over_filled_snapshot_carries_section(self):
        filled = brief.with_blocked_contacts(SNAPSHOT, now=1793093400)
        text = brief.compose_template_brief(filled)
        self.assertIn("Blocked contacts", text)
        self.assertIn("Ask milo about 7 spark client", text)

    def test_morning_brief_via_generate_carries_section(self):
        filled = brief.with_blocked_contacts(SNAPSHOT, now=1793093400)
        text, _record = brief.generate_brief(
            filled, "build", kind="morning", now=1793093400,
            dry_run=True)
        self.assertIn("Ask milo about 7 spark client", text)

    def test_unfilled_snapshot_carries_no_contacts_section(self):
        snapshot = {"messages": [], "jobs": SNAPSHOT["jobs"]}
        text = brief.compose_template_brief(snapshot)
        self.assertNotIn("Blocked contacts", text)

    def test_hand_stated_record_wins_unchanged(self):
        stated = {"contacts": [{"job_id": "9", "ask": "pax"}],
                  "as_of": 1793093000}
        filled = brief.with_blocked_contacts(
            {"blocked_contacts": stated,
             "blocked_contact_entries": [{"job_id": "7", "ask": "milo"}]},
            now=1793093400)
        self.assertEqual(filled["blocked_contacts"], stated)

    def test_caller_snapshot_is_never_mutated(self):
        original = dict(SNAPSHOT)
        brief.with_blocked_contacts(SNAPSHOT, now=1793093400)
        self.assertEqual(SNAPSHOT, original)
        self.assertNotIn("blocked_contacts", SNAPSHOT)

    def test_snapshot_with_nothing_usable_gets_no_record(self):
        filled = brief.with_blocked_contacts({"messages": []},
                                             now=1793093400)
        self.assertNotIn("blocked_contacts", filled)
        filled = brief.with_blocked_contacts(
            {"blocked_contact_entries": "7:milo"}, now=1793093400)
        self.assertNotIn("blocked_contacts", filled)

    def test_job_listed_twice_is_one_entry_first_ask_wins(self):
        filled = brief.with_blocked_contacts(
            {"blocked_contact_entries": [{"job_id": "7", "ask": "milo"},
                                         {"job_id": "7", "ask": "pax"}]},
            now=1793093400)
        self.assertEqual(filled["blocked_contacts"]["contacts"],
                         [{"job_id": "7", "ask": "milo"}])

    def test_malformed_entries_skipped_never_guessed(self):
        filled = brief.with_blocked_contacts(
            {"blocked_contact_entries": [
                {"job_id": "7", "ask": "milo"}, {"job_id": ""},
                {"job_id": 7, "ask": "pax"}, None, "7:milo",
                {"ask": "rowan"}]},
            now=1793093400)
        self.assertEqual(filled["blocked_contacts"]["contacts"],
                         [{"job_id": "7", "ask": "milo"}])

    def test_junk_only_list_builds_no_record(self):
        filled = brief.with_blocked_contacts(
            {"blocked_contact_entries": [{"job_id": ""}, None, 7,
                                         {"ask": "milo"}]},
            now=1793093400)
        self.assertNotIn("blocked_contacts", filled)

    def test_empty_list_builds_no_record(self):
        filled = brief.with_blocked_contacts(
            {"blocked_contact_entries": []}, now=1793093400)
        self.assertNotIn("blocked_contacts", filled)

    def test_entry_without_ask_reads_owner_not_reported(self):
        filled = brief.with_blocked_contacts(
            {"blocked_contact_entries": [{"job_id": "7"}]},
            now=1793093400)
        self.assertEqual(filled["blocked_contacts"]["contacts"],
                         [{"job_id": "7"}])
        lines = brief.blocked_contact_lines(
            filled["blocked_contacts"], SNAPSHOT["jobs"])
        self.assertIn("7 spark client: owner not reported",
                      lines[0])

    def test_contact_for_non_blocked_job_is_ignored_by_renderer(self):
        filled = brief.with_blocked_contacts(
            {"blocked_contact_entries": [{"job_id": "3", "ask": "pax"},
                                         {"job_id": "7", "ask": "milo"}]},
            now=1793093400)
        lines = brief.blocked_contact_lines(
            filled["blocked_contacts"], SNAPSHOT["jobs"])
        self.assertEqual(len(lines), 2)
        self.assertNotIn("pax", " ".join(lines))

    def test_default_stamp_is_an_int_when_now_is_not_given(self):
        filled = brief.with_blocked_contacts(SNAPSHOT)
        self.assertIsInstance(filled["blocked_contacts"]["as_of"], int)

    def test_non_dict_snapshot_gets_no_record(self):
        self.assertEqual(brief.with_blocked_contacts(None), {})


if __name__ == "__main__":
    unittest.main()
