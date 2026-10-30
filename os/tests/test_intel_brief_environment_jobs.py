"""intel/brief.py: OS-103 follow-up — environment_jobs_record.

Before this change no caller in the repo filled the
environment record's jobs part from a jobs list: the OS-103
Working now line rendered only from a hand-stated record.
Now environment_jobs_record reads the claimed jobs out of
the snapshot's own jobs list, in job order, so a caller can
merge it into the environment record. Only claimed jobs
with a nick and a title count — an open job is not work in
progress, and a claim-less or title-less entry is skipped,
never guessed into a name. Bus and budget still come from
their own sources (no bus or spend-ledger filler is claimed
here), and a record with only the jobs part still renders
the other three lines as not reported.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import brief  # noqa: E402


JOBS = [
    {"id": "5", "title": "brief panel", "status": "claimed",
     "claim": "rowan"},
    {"id": "6", "title": "open job", "status": "open"},
    {"id": "7", "title": "blocked job", "status": "blocked",
     "claim": "milo"},
    {"id": "8", "title": "no nick", "status": "claimed"},
    {"id": "9", "status": "claimed", "claim": "pax"},
    "not a job",
    {"id": "10", "title": "watchdog", "status": "claimed",
     "claim": "milo"},
]


class EnvironmentJobsRecordTest(unittest.TestCase):
    def test_only_claimed_jobs_with_nick_and_title_survive_in_order(self):
        record = brief.environment_jobs_record(JOBS)
        self.assertEqual(
            [(entry.get("id"), entry["claim"], entry["title"])
             for entry in record],
            [("5", "rowan", "brief panel"),
             ("10", "milo", "watchdog")])

    def test_unusable_id_is_left_out_not_invented(self):
        record = brief.environment_jobs_record(
            [{"id": "", "title": "job", "status": "claimed",
              "claim": "rowan"},
             {"title": "other", "status": "claimed",
              "claim": "milo"}])
        self.assertEqual(record[0], {"title": "job",
                                     "status": "claimed",
                                     "claim": "rowan"})
        self.assertNotIn("id", record[1])

    def test_no_claimed_job_returns_empty_not_none(self):
        self.assertEqual(brief.environment_jobs_record(
            [{"id": "6", "title": "open job", "status": "open"}]), [])

    def test_non_list_returns_none_so_line_reads_not_reported(self):
        self.assertIsNone(brief.environment_jobs_record(None))
        self.assertIsNone(brief.environment_jobs_record(
            {"id": "5", "title": "brief panel", "status": "claimed",
             "claim": "rowan"}))
        lines = brief.environment_lines({})
        self.assertIn("not reported", lines[2])

    def test_builder_record_renders_working_line_and_others_not_reported(self):
        jobs = brief.environment_jobs_record(JOBS)
        lines = brief.environment_lines(
            {"jobs": jobs, "as_of": 1793093400})
        self.assertIn("rowan: brief panel", lines[2])
        self.assertIn("milo: watchdog", lines[2])
        self.assertNotIn("open job", lines[2])
        self.assertIn("not reported", lines[0])
        self.assertIn("not reported", lines[1])
        self.assertIn("not reported", lines[3])

    def test_boot_template_brief_carries_builder_working_line(self):
        jobs = brief.environment_jobs_record(JOBS)
        text = brief.compose_template_brief(
            {"messages": [], "jobs": [],
             "environment": {"jobs": jobs, "as_of": 1793093400}},
            boot=True)
        self.assertIn("Working now: rowan: brief panel", text)


if __name__ == "__main__":
    unittest.main()
