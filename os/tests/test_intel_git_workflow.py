"""tests/test_intel_git_workflow.py -- INT-012 git workflow reconciliation.

GOV-003 was ruled by Dale 2026-10-24: the build lives in a NEW repo,
Mrfentmen/meta-os, with muse-relay merged in as the base layer, and all
work happens in the new repo. INT-012 notes that ruling in every lane
file. These tests pin the reconciliation:

- No lane file still says the workflow is UNDECIDED.
- Every lane file's workflow line carries RULED, GOV-003, and meta-os.
- Every lane file's Repo line names the meta-os repo.
- The master plan no longer calls the conflict parked for Dale.
- The inherited relay README's worker branch wording is deliberately
  untouched: it describes the base's own job flow, not crew workflow.
- Milo's reuse-audit dependency note records the ruling.
- The INT-012 eval doc exists and names the task and the ruling.

No bus post, no live Redis, no network: pure file reads.
"""

import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANES = ["BUFFY", "DALE", "HANA", "MILO", "PAX", "ROWAN"]


def _read(relpath):
    with open(os.path.join(ROOT, relpath), encoding="utf-8") as handle:
        return handle.read()


def _line_starting(text, prefix):
    for line in text.splitlines():
        if line.startswith(prefix):
            return line
    return None


class GitWorkflowTest(unittest.TestCase):
    def test_no_lane_file_still_undecided(self):
        for lane in LANES:
            text = _read("plan/lanes/%s.md" % lane)
            self.assertNotIn("UNDECIDED until Dale rules", text, lane)

    def test_every_lane_workflow_line_carries_ruling(self):
        for lane in LANES:
            text = _read("plan/lanes/%s.md" % lane)
            line = _line_starting(text, "- Git workflow:")
            self.assertIsNotNone(line, lane)
            self.assertIn("RULED", line, lane)
            self.assertIn("GOV-003", line, lane)
            self.assertIn("meta-os", line, lane)

    def test_every_lane_repo_line_names_meta_os(self):
        for lane in LANES:
            text = _read("plan/lanes/%s.md" % lane)
            line = _line_starting(text, "- Repo:")
            self.assertIsNotNone(line, lane)
            self.assertIn("Mrfentmen/meta-os", line, lane)

    def test_master_plan_conflict_no_longer_parked(self):
        text = _read("plan/MASTER_PLAN.md")
        self.assertIn("Git workflow conflict resolved (INT-012", text)
        self.assertNotIn("GOV-003 decides; nobody guesses", text)

    def test_relay_readme_job_flow_untouched(self):
        text = _read("README-MUSE-RELAY.md")
        self.assertIn("feature branch", text)

    def test_audit_note_records_ruling(self):
        text = _read("intel/notes/milo-reuse-audit.md")
        self.assertIn("RULED 2026-10-24", text)
        self.assertNotIn("local and unpushed", text)

    def test_eval_doc_exists_and_names_task(self):
        text = _read("intel/evals/int012_git_workflow.md")
        self.assertIn("INT-012", text)
        self.assertIn("GOV-003", text)


if __name__ == "__main__":
    unittest.main()
