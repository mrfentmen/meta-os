"""intel/brief.py: OS-103 follow-up — environment_repo_record.

Before this change no caller in the repo filled the environment
record from git: the OS-103 lines rendered only from a stated
record, and a boot brief over a real checkout still read "not
reported" for its repo line. Now environment_repo_record reads
branch, short commit, and dirty count from a local checkout,
never raising, so a caller can merge it into the environment
record. Bus, jobs, and budget still come from their own
sources (no bus, queue, or spend-ledger filler is claimed
here), and a record with only the repo part still renders
the other three lines as not reported. Tests use real temp
git checkouts, not a stubbed git, so the commands are proven
against git itself; a non-checkout directory proves the
never-raises, empty-record path.
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


class EnvironmentRepoRecordTest(unittest.TestCase):
    def test_clean_checkout_names_branch_commit_and_zero_dirty(self):
        path = _checkout()
        record = brief.environment_repo_record(path, now=1793093400)
        self.assertEqual(record["branch"], "testbranch")
        self.assertTrue(record["commit"])
        self.assertEqual(record["dirty"], 0)
        self.assertEqual(record["as_of"], 1793093400)

    def test_modified_and_untracked_files_count_as_dirty(self):
        path = _checkout()
        with open(os.path.join(path, "note.txt"), "a",
                  encoding="utf-8") as handle:
            handle.write("more\n")
        with open(os.path.join(path, "new.txt"), "w",
                  encoding="utf-8") as handle:
            handle.write("untracked\n")
        record = brief.environment_repo_record(path, now=1793093400)
        self.assertEqual(record["dirty"], 2)

    def test_non_checkout_returns_empty_and_never_raises(self):
        with tempfile.TemporaryDirectory() as path:
            self.assertEqual(
                brief.environment_repo_record(path, now=1793093400),
                {})

    def test_builder_record_renders_repo_line_and_others_not_reported(self):
        path = _checkout()
        record = brief.environment_repo_record(path, now=1793093400)
        lines = brief.environment_lines({"repo": record})
        self.assertIn("Repo: testbranch at " + record["commit"],
                      lines[0])
        self.assertIn("clean", lines[0])
        self.assertIn("not reported", lines[1])
        self.assertIn("not reported", lines[2])
        self.assertIn("not reported", lines[3])

    def test_boot_template_brief_carries_builder_repo_line(self):
        path = _checkout()
        record = brief.environment_repo_record(path, now=1793093400)
        text = brief.compose_template_brief(
            {"messages": [], "jobs": [],
             "environment": {"repo": record}}, boot=True)
        self.assertIn("Repo: testbranch at " + record["commit"], text)


if __name__ == "__main__":
    unittest.main()
