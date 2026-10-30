"""intel/brief.py: OS-103 follow-up — with_boot_environment,
the launch-path caller.

Before this change build_environment_record existed but no
caller in the launch path used it: `intel.py brief --boot`
— the path relay-brief.service runs — passed its snapshot
straight to generate_brief, so a boot brief carried
environment lines only when the snapshot hand-stated an
"environment" record, and a bare launch snapshot carried
none at all. Now the boot path fills the record first:
a snapshot with no "environment" key gets a copy with
one built from itself (repo from the checkout, jobs, bus,
and budget from the snapshot's own lists, one stamp), and
a snapshot that already carries one keeps it untouched,
so a hand-stated record is never overwritten. Tests use
real temp git checkouts for the repo part, as the
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


SNAPSHOT = {
    "messages": [{"nick": "pax", "text": "hello"},
                 "rowan: working", 42],
    "jobs": [{"id": "5", "title": "brief panel", "status": "claimed",
              "claim": "rowan"},
             {"id": "6", "title": "open job", "status": "open"}],
    "budgets": [{"lane": "HANA", "spent": 120, "cap": 300}],
}


class WithBootEnvironmentTest(unittest.TestCase):
    def test_fills_absent_environment_from_snapshot_and_checkout(self):
        path = _checkout()
        filled = brief.with_boot_environment(
            SNAPSHOT, room="build", repo_path=path, now=1793093400)
        env = filled["environment"]
        self.assertEqual(env["as_of"], 1793093400)
        self.assertEqual(env["repo"]["branch"], "testbranch")
        self.assertEqual(env["repo"]["as_of"], 1793093400)
        self.assertEqual(env["repo"]["dirty"], 0)
        self.assertEqual(
            [(entry["claim"], entry["title"])
             for entry in env["jobs"]],
            [("rowan", "brief panel")])
        self.assertEqual(env["bus"]["rooms"], ["build"])
        self.assertEqual(env["bus"]["messages"], 2)
        self.assertEqual(env["budget"]["lane"], "HANA")
        self.assertEqual(env["budget"]["spent"], 120)
        self.assertEqual(env["budget"]["cap"], 300)

    def test_filled_record_renders_all_four_lines(self):
        path = _checkout()
        filled = brief.with_boot_environment(
            SNAPSHOT, room="build", repo_path=path, now=1793093400)
        lines = brief.environment_lines(filled["environment"])
        self.assertIn("Repo: testbranch at ", lines[0])
        self.assertIn("Bus: 2 messages in room build", lines[1])
        self.assertIn("rowan: brief panel", lines[2])
        self.assertIn("Budget: HANA lane: 180 remaining of 300 cap",
                      lines[3])

    def test_hand_stated_environment_wins_unchanged(self):
        stated = {"repo": {"branch": "main", "commit": "a6c190f",
                           "dirty": 0, "as_of": 1793093400}}
        filled = brief.with_boot_environment(
            {"environment": stated, "jobs": []},
            room="build", repo_path="/nonexistent", now=1793093400)
        self.assertEqual(filled["environment"], stated)

    def test_caller_snapshot_is_never_mutated(self):
        path = _checkout()
        original = dict(SNAPSHOT)
        brief.with_boot_environment(
            SNAPSHOT, room="build", repo_path=path, now=1793093400)
        self.assertEqual(SNAPSHOT, original)
        self.assertNotIn("environment", SNAPSHOT)

    def test_empty_snapshot_and_non_checkout_reads_all_not_reported(self):
        with tempfile.TemporaryDirectory() as path:
            filled = brief.with_boot_environment(
                {}, repo_path=path, now=1793093400)
        self.assertEqual(filled["environment"],
                         {"as_of": 1793093400})
        lines = brief.environment_lines(filled["environment"])
        self.assertTrue(all("not reported" in line for line in lines))

    def test_non_dict_snapshot_gets_repo_only_environment(self):
        path = _checkout()
        filled = brief.with_boot_environment(
            None, repo_path=path, now=1793093400)
        self.assertEqual(set(filled), {"environment"})
        self.assertEqual(filled["environment"]["repo"]["branch"],
                         "testbranch")

    def test_boot_template_brief_over_filled_snapshot_carries_lines(self):
        path = _checkout()
        filled = brief.with_boot_environment(
            SNAPSHOT, room="build", repo_path=path, now=1793093400)
        text = brief.compose_template_brief(filled, boot=True)
        self.assertIn("Repo: testbranch at ", text)
        self.assertIn("Bus: 2 messages in room build", text)
        self.assertIn("Working now: rowan: brief panel", text)
        self.assertIn("Budget: HANA lane: 180 remaining", text)

    def test_room_list_passes_through_in_order(self):
        path = _checkout()
        filled = brief.with_boot_environment(
            SNAPSHOT, room=["main", "build"], repo_path=path,
            now=1793093400)
        self.assertEqual(filled["environment"]["bus"]["rooms"],
                         ["main", "build"])

    def test_default_stamp_is_an_int_when_now_is_not_given(self):
        with tempfile.TemporaryDirectory() as path:
            filled = brief.with_boot_environment(
                {"jobs": []}, repo_path=path)
        self.assertIsInstance(filled["environment"]["as_of"], int)


if __name__ == "__main__":
    unittest.main(verbosity=2)
