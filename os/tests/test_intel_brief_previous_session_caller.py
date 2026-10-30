"""intel/brief.py: OS-051 follow-up — with_previous_session,
the boot-path caller.

Before this change no caller in the repo filled
`previous_session`: a boot brief carried its digest line
only when the snapshot hand-stated a "previous_session"
record, and a bare boot snapshot carried no digest even
when the caller knew the previous session. Now the boot
path fills the record first: from the snapshot's own
stated "last_brief" record (its generated_at time
becomes the last-brief time) and its own stated
"shutdown_jobs" list (done jobs completed, open or
claimed jobs open threads, blocked jobs neither). A
snapshot that hand-states a record keeps it untouched,
and a snapshot that states nothing usable gets no
record added, so older briefs keep their exact shape.
The current "jobs" list is never read as the shutdown
list, and the BRF-019 "previous_brief" diff record is
never read as a stored brief: both look similar and
neither is the previous session. A missing shutdown
list states nothing and yields no record, while an
explicitly empty one states a clean shutdown and
yields a 0/0 record. A last brief with no usable time
yields no record, never a digest on a guessed time.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import brief  # noqa: E402


SNAPSHOT = {
    "messages": [],
    "last_brief": {"room": "build", "generated_at": 1793000000,
                   "kind": "morning"},
    "shutdown_jobs": [
        {"title": "brief panel", "status": "done"},
        {"title": "dispatch poster", "status": "done"},
        {"title": "watchdog loop", "status": "claimed"},
        {"title": "spark client", "status": "blocked"},
        {"title": "open thread job", "status": "open"},
        "not a dict",
        {"status": "done"},
    ],
}


class WithPreviousSessionTest(unittest.TestCase):
    def test_fills_record_from_last_brief_and_shutdown_jobs(self):
        filled = brief.with_previous_session(SNAPSHOT)
        record = filled["previous_session"]
        self.assertEqual(record["last_brief_at"], "2026-10-26 03:33 ET")
        self.assertEqual(record["jobs_completed"],
                         ["brief panel", "dispatch poster"])
        self.assertEqual(record["open_threads"],
                         ["watchdog loop", "open thread job"])

    def test_filled_record_renders_the_digest_line(self):
        filled = brief.with_previous_session(SNAPSHOT)
        self.assertEqual(
            brief.previous_session_digest(filled["previous_session"]),
            "Previous session: last brief 2026-10-26 03:33 ET, "
            "2 jobs completed (brief panel; dispatch poster), "
            "2 open threads (watchdog loop; open thread job)")

    def test_boot_template_brief_over_filled_snapshot_carries_digest(self):
        filled = brief.with_previous_session(SNAPSHOT)
        text = brief.compose_template_brief(filled, boot=True)
        self.assertIn("Previous session: last brief 2026-10-26 03:33 ET, "
                      "2 jobs completed (brief panel; dispatch poster), "
                      "2 open threads (watchdog loop; open thread job)",
                      text)

    def test_non_boot_brief_over_filled_snapshot_carries_no_digest(self):
        filled = brief.with_previous_session(SNAPSHOT)
        text = brief.compose_template_brief(filled)
        self.assertNotIn("Previous session", text)

    def test_hand_stated_record_wins_unchanged(self):
        stated = {"last_brief_at": "2026-10-26 22:00 ET",
                  "jobs_completed": ["hand-stated job"],
                  "open_threads": []}
        filled = brief.with_previous_session(
            {"previous_session": stated,
             "last_brief": SNAPSHOT["last_brief"],
             "shutdown_jobs": SNAPSHOT["shutdown_jobs"]})
        self.assertEqual(filled["previous_session"], stated)

    def test_caller_snapshot_is_never_mutated(self):
        original = dict(SNAPSHOT)
        brief.with_previous_session(SNAPSHOT)
        self.assertEqual(SNAPSHOT, original)
        self.assertNotIn("previous_session", SNAPSHOT)

    def test_last_brief_with_no_usable_time_gets_no_record(self):
        for last_brief in ({}, None, "not a dict",
                           {"room": "build", "kind": "morning"}):
            filled = brief.with_previous_session(
                {"last_brief": last_brief,
                 "shutdown_jobs": SNAPSHOT["shutdown_jobs"]})
            self.assertNotIn("previous_session", filled)

    def test_missing_or_non_list_shutdown_jobs_gets_no_record(self):
        for snapshot in ({"last_brief": SNAPSHOT["last_brief"]},
                         {"last_brief": SNAPSHOT["last_brief"],
                          "shutdown_jobs": "not a list"},
                         {"last_brief": SNAPSHOT["last_brief"],
                          "shutdown_jobs": None}):
            filled = brief.with_previous_session(snapshot)
            self.assertNotIn("previous_session", filled)

    def test_explicitly_empty_shutdown_jobs_states_clean_shutdown(self):
        filled = brief.with_previous_session(
            {"last_brief": SNAPSHOT["last_brief"],
             "shutdown_jobs": []})
        record = filled["previous_session"]
        self.assertEqual(record["jobs_completed"], [])
        self.assertEqual(record["open_threads"], [])
        self.assertEqual(
            brief.previous_session_digest(record),
            "Previous session: last brief 2026-10-26 03:33 ET, "
            "0 jobs completed, 0 open threads")

    def test_current_jobs_are_never_read_as_shutdown_jobs(self):
        filled = brief.with_previous_session(
            {"last_brief": SNAPSHOT["last_brief"],
             "jobs": [{"id": "5", "title": "current window job",
                       "status": "done"}]})
        self.assertNotIn("previous_session", filled)
        filled = brief.with_previous_session(
            {"last_brief": SNAPSHOT["last_brief"],
             "shutdown_jobs": SNAPSHOT["shutdown_jobs"],
             "jobs": [{"id": "5", "title": "current window job",
                       "status": "done"}]})
        self.assertEqual(filled["previous_session"]["jobs_completed"],
                         ["brief panel", "dispatch poster"])

    def test_previous_brief_diff_record_is_never_read_as_last_brief(self):
        filled = brief.with_previous_session(
            {"previous_brief": {
                "jobs": [{"id": "5", "status": "done"}],
                "as_of": 1793000000},
             "jobs": [{"id": "5", "title": "current window job",
                       "status": "done"}]})
        self.assertNotIn("previous_session", filled)

    def test_non_dict_snapshot_gets_no_record_and_never_raises(self):
        for snapshot in (None, "not a dict", 42, ["a list"]):
            self.assertEqual(brief.with_previous_session(snapshot), {})


if __name__ == "__main__":
    unittest.main()
