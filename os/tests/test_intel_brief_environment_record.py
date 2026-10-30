"""intel/brief.py: OS-103 follow-up — build_environment_record.

Before this change the repo and jobs builders existed but no
caller in the repo combined them: a launch snapshot still had
to hand-state its environment record. Now
build_environment_record merges the two built parts into one
record — repo from git, jobs from the snapshot's own jobs
list, one as_of stamp for the whole record — so a boot brief
over that record carries both lines. Bus and budget are
deliberately absent (no bus or spend-ledger filler is claimed
here), so those two lines still read not reported, and a
part that yields nothing usable is left out, never padded:
a non-checkout repo leaves "repo" out, a snapshot with no
usable jobs list leaves "jobs" out, and the Working now line
then reads not reported instead of falsely reading nobody.
Tests use real temp git checkouts for the repo part, as the
repo-builder tests do.
"""

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import brief  # noqa: E402


def _run(path, *args):
    subprocess.run(["git", "-C", path, *args], check=True,
                   capture_output=True, text=True)


def _checkout():
    path = tempfile.mkdtemp()
    _run(path, "init", "-b", "testbranch")
    _run(path, "config", "user.email", "test@example.local")
    _run(path, "config", "user.name", "Test")
    with open(os.path.join(path, "note.txt"), "w",
              encoding="utf-8") as handle:
        handle.write("hello\n")
    _run(path, "add", "note.txt")
    _run(path, "commit", "-m", "first")
    return path


JOBS = [
    {"id": "5", "title": "brief panel", "status": "claimed",
     "claim": "rowan"},
    {"id": "6", "title": "open job", "status": "open"},
    {"id": "10", "title": "watchdog", "status": "claimed",
     "claim": "milo"},
]


class BuildEnvironmentRecordTest(unittest.TestCase):
    def test_merges_repo_and_jobs_with_one_stamp(self):
        path = _checkout()
        record = brief.build_environment_record(
            {"jobs": JOBS}, repo_path=path, now=1793093400)
        self.assertEqual(record["as_of"], 1793093400)
        self.assertEqual(record["repo"]["branch"], "testbranch")
        self.assertEqual(record["repo"]["as_of"], 1793093400)
        self.assertEqual(record["repo"]["dirty"], 0)
        self.assertEqual(
            [(entry["claim"], entry["title"])
             for entry in record["jobs"]],
            [("rowan", "brief panel"), ("milo", "watchdog")])
        self.assertNotIn("bus", record)
        self.assertNotIn("budget", record)

    def test_merged_record_renders_both_lines_and_bus_budget_not_reported(self):
        path = _checkout()
        record = brief.build_environment_record(
            {"jobs": JOBS}, repo_path=path, now=1793093400)
        lines = brief.environment_lines(record)
        self.assertIn("Repo: testbranch at ", lines[0])
        self.assertIn("rowan: brief panel", lines[2])
        self.assertIn("milo: watchdog", lines[2])
        self.assertIn("not reported", lines[1])
        self.assertIn("not reported", lines[3])

    def test_non_checkout_repo_is_left_out_not_padded(self):
        with tempfile.TemporaryDirectory() as path:
            record = brief.build_environment_record(
                {"jobs": JOBS}, repo_path=path, now=1793093400)
        self.assertNotIn("repo", record)
        self.assertIn("jobs", record)
        lines = brief.environment_lines(record)
        self.assertIn("not reported", lines[0])
        self.assertIn("rowan: brief panel", lines[2])

    def test_non_list_jobs_leaves_jobs_out_so_line_reads_not_reported(self):
        with tempfile.TemporaryDirectory() as path:
            record = brief.build_environment_record(
                {"jobs": "not a list"}, repo_path=path,
                now=1793093400)
        self.assertNotIn("jobs", record)
        lines = brief.environment_lines(record)
        self.assertIn("not reported", lines[2])
        self.assertNotIn("nobody holds", lines[2])

    def test_no_snapshot_gives_stamp_only_record(self):
        with tempfile.TemporaryDirectory() as path:
            record = brief.build_environment_record(
                None, repo_path=path, now=1793093400)
        self.assertEqual(record, {"as_of": 1793093400})
        lines = brief.environment_lines(record)
        self.assertTrue(all("not reported" in line for line in lines))

    def test_empty_jobs_list_kept_as_nobody_holds(self):
        with tempfile.TemporaryDirectory() as path:
            record = brief.build_environment_record(
                {"jobs": []}, repo_path=path, now=1793093400)
        self.assertEqual(record["jobs"], [])
        lines = brief.environment_lines(record)
        self.assertIn("nobody holds a claimed job", lines[2])

    def test_boot_template_brief_carries_merged_lines(self):
        path = _checkout()
        record = brief.build_environment_record(
            {"jobs": JOBS}, repo_path=path, now=1793093400)
        text = brief.compose_template_brief(
            {"messages": [], "jobs": [],
             "environment": record}, boot=True)
        self.assertIn("Repo: testbranch at ", text)
        self.assertIn("Working now: rowan: brief panel", text)
        self.assertIn("Bus state: not reported", text)
        self.assertIn("Budget: not reported", text)

    def test_default_stamp_is_an_int_when_now_is_not_given(self):
        with tempfile.TemporaryDirectory() as path:
            record = brief.build_environment_record(
                {"jobs": []}, repo_path=path)
        self.assertIsInstance(record["as_of"], int)


if __name__ == "__main__":
    unittest.main()
