"""tests/test_intel_baton_pass.py -- OS-125: the baton pass.

OS-125 passes a killed worker's job to the next agent
without restarting it: the baton carries the goal, the
deposited progress, the files already changed, the files
still to touch, what remains, and the acceptance checks,
and the continuation prompt names what remains instead
of restating the whole job. These tests pin the
composition, journal, brief, and zero-Dale-contact
halves on fixtures:

- A full job composes every section, and the remaining
  files exclude the completed files.
- Remaining files derive from a comma-separated files
  string, deduped in order.
- Remaining steps derive from steps minus completed
  steps, and the explicit remaining list wins.
- Acceptance checks parse from the accept string, and
  the acceptance_checks list wins over accept.
- The goal reads from the goal field, else the spec's
  Goal line, else None.
- A job with nothing deposited yields an honest baton:
  no invented progress, no invented completed files,
  every file still to touch.
- Malformed records and missing jobs yield no baton and
  no journal record, never a crash.
- A pass tick journals one baton-pass record, and a
  second tick over the same job journals nothing.
- The brief line names the job, both workers, and the
  remaining file count.
- A pass tick never mutates its input snapshot or
  journal.
- The baton module carries no push path: no push import,
  no network import.
- The drill script exists and passes; the eval note
  names OS-125.
- None of the new OS-125 files carries an em dash (the
  new-doc rule).

No bus post, no live Redis, no network, no systemd:
pure fixture calls plus file reads.
"""

import copy
import os
import subprocess
import sys
import unittest

sys.path.insert(0, ".")

from intel import baton  # noqa: E402

T0 = 100000
NEW_FILES = [
    "intel/baton.py",
    "intel/drills/baton_pass.py",
    "intel/evals/baton_pass.md",
    "intel/evals/baton_pass.log",
    "tests/test_intel_baton_pass.py",
]


def job(job_id="7", **overrides):
    record = {
        "id": job_id,
        "title": "Wire the watchdog status line",
        "goal": "Show one live health line on the boot screen",
        "claim": "pax",
        "status": "claimed",
        "last_progress_at": T0 + 300,
        "progress_notes": ["wrote a.txt", "tests pass for a.txt"],
        "files": ["a.txt", "b.txt", "c.txt"],
        "completed_files": ["a.txt"],
        "steps": ["write a.txt", "write b.txt", "write c.txt"],
        "completed_steps": ["write a.txt"],
        "acceptance_checks": ["b.txt renders", "c.txt renders"],
    }
    record.update(overrides)
    return record


class BatonTest(unittest.TestCase):
    def test_full_composition_names_what_remains(self):
        composed = baton.compose_baton(job())
        self.assertEqual(composed["goal"],
                         "Show one live health line on the boot screen")
        self.assertEqual(composed["progress_notes"],
                         ["wrote a.txt", "tests pass for a.txt"])
        self.assertEqual(composed["completed_files"], ["a.txt"])
        self.assertEqual(composed["remaining_files"],
                         ["b.txt", "c.txt"])
        self.assertEqual(composed["remaining_steps"],
                         ["write b.txt", "write c.txt"])
        self.assertEqual(composed["acceptance_checks"],
                         ["b.txt renders", "c.txt renders"])
        self.assertNotIn("a.txt", composed["prompt"].split(
            "Files still to touch:")[1].split("What remains:")[0])
        self.assertIn("write b.txt", composed["prompt"])

    def test_remaining_files_from_comma_string(self):
        composed = baton.compose_baton(job(
            files="a.txt, b.txt, a.txt, c.txt"))
        self.assertEqual(composed["files"],
                         ["a.txt", "b.txt", "c.txt"])
        self.assertEqual(composed["remaining_files"],
                         ["b.txt", "c.txt"])

    def test_remaining_steps_explicit_list_wins(self):
        composed = baton.compose_baton(
            job(remaining_steps=["polish c.txt"]))
        self.assertEqual(composed["remaining_steps"],
                         ["polish c.txt"])
        self.assertEqual(baton.remaining_steps(job()),
                         ["write b.txt", "write c.txt"])
        self.assertIsNone(baton.remaining_steps({"id": "1"}))

    def test_acceptance_parsing_order(self):
        self.assertEqual(baton.acceptance_checks(
            {"accept": "a renders\nb renders\n"}),
            ["a renders", "b renders"])
        self.assertEqual(baton.acceptance_checks(job(
            acceptance_checks=["list wins"],
            accept="string loses")),
            ["list wins"])
        self.assertEqual(baton.acceptance_checks({"id": "1"}), [])

    def test_goal_from_field_spec_or_none(self):
        self.assertEqual(baton.compose_baton(job())["goal"],
                         "Show one live health line on the boot screen")
        spec_job = {"id": "10", "title": "Spec goal",
                    "spec": "Goal: Ship the status line\nContext: boot"}
        self.assertEqual(baton.compose_baton(spec_job)["goal"],
                         "Ship the status line")
        self.assertIsNone(baton.compose_baton(
            {"id": "11", "title": "No goal"})["goal"])

    def test_no_progress_baton_is_honest(self):
        composed = baton.compose_baton(
            {"id": "8", "title": "Unstarted job", "claim": "pax",
             "files": ["x.txt", "y.txt"]})
        self.assertEqual(composed["progress_notes"], [])
        self.assertEqual(composed["completed_files"], [])
        self.assertEqual(composed["remaining_files"],
                         ["x.txt", "y.txt"])
        self.assertIn("no progress notes deposited",
                      composed["prompt"])

    def test_malformed_records_yield_nothing(self):
        self.assertIsNone(baton.compose_baton("not a record"))
        self.assertIsNone(baton.compose_baton({"title": "no id"}))
        self.assertIsNone(baton.compose_baton(None))
        snap = {"jobs": [job()]}
        self.assertEqual(baton.baton_pass_tick(snap, "99", "hana",
                                               [], T0), [])
        self.assertEqual(baton.baton_pass_tick(snap, "", "hana",
                                               [], T0), [])
        self.assertEqual(baton.baton_pass_tick(snap, "7", "", [],
                                               T0), [])

    def test_pass_tick_and_dedupe(self):
        snap = {"jobs": [job()]}
        first = baton.baton_pass_tick(snap, "7", "hana", [], T0)
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["kind"], "baton-pass")
        self.assertEqual(first[0]["to_worker"], "hana")
        self.assertEqual(first[0]["dedupe_key"], "baton:7")
        self.assertEqual(baton.baton_pass_tick(snap, "7", "hana",
                                               first, T0), [])

    def test_brief_lines(self):
        snap = {"jobs": [job()]}
        records = baton.baton_pass_tick(snap, "7", "hana", [], T0)
        lines = baton.baton_brief_lines(records)
        self.assertEqual(len(lines), 1)
        self.assertIn("7", lines[0])
        self.assertIn("pax", lines[0])
        self.assertIn("hana", lines[0])
        self.assertIn("2 file(s)", lines[0])
        self.assertEqual(baton.baton_brief_lines(
            [{"kind": "ladder-action"}]), [])

    def test_tick_never_mutates_inputs(self):
        snap = {"jobs": [job()]}
        journal = [{"kind": "baton-pass", "dedupe_key": "baton:9"}]
        before_snap = copy.deepcopy(snap)
        before_journal = copy.deepcopy(journal)
        baton.baton_pass_tick(snap, "7", "hana", journal, T0)
        self.assertEqual(snap, before_snap)
        self.assertEqual(journal, before_journal)

    def test_no_push_path(self):
        with open("intel/baton.py") as handle:
            source = handle.read()
        for banned in ("intel/push", "import push", "import requests",
                       "import urllib", "import socket"):
            self.assertNotIn(banned, source)

    def test_drill_passes(self):
        result = subprocess.run(
            [sys.executable, "intel/drills/baton_pass.py"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("ALL PHASES PASS", result.stdout)

    def test_eval_note_names_os125(self):
        with open("intel/evals/baton_pass.md") as handle:
            self.assertIn("OS-125", handle.read())

    def test_no_em_dash_in_new_files(self):
        for path in NEW_FILES:
            with open(path, encoding="utf-8") as handle:
                self.assertNotIn("\u2014", handle.read(), path)


if __name__ == "__main__":
    unittest.main()
